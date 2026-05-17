import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { log } from './utils/logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export type DeviceState = 'ACTIVE' | 'QUEUED' | 'IDLE' | 'STOPPED';

export interface IoTDeviceConfig {
    id: string;
    name: string;
    vendor: string;
    type: string;
    mac: string;
    ip_start?: string;
    protocols: string[];
    enabled: boolean;
    traffic_interval: number;
    description?: string;
    gateway?: string;
    fingerprint?: {
        dhcp?: {
            hostname?: string;
            vendor_class_id?: string;
            client_id_type?: number;
            param_req_list?: number[];
        };
    };
    security?: {
        bad_behavior: boolean;
        behavior_type: string[];
    };
}

const MAX_RESTART_ATTEMPTS = 5;
const RESTART_BASE_DELAY_MS = 2000;
const RESTART_MAX_DELAY_MS = 30000;
const DEFAULT_MAX_CONCURRENT = 30;

export class IoTManager extends EventEmitter {
    // ── Daemon ───────────────────────────────────────────────────────────────
    private daemonProcess: ChildProcess | null = null;
    private daemonReady: boolean = false;
    private daemonInterface: string;
    private restartAttempts: number = 0;
    private restartTimer: ReturnType<typeof setTimeout> | null = null;
    private gaveUp: boolean = false;
    private pythonScriptPath: string;

    // ── Per-device state ─────────────────────────────────────────────────────
    private runningDevices: Map<string, IoTDeviceConfig> = new Map();  // in daemon
    private statsCache: Map<string, any> = new Map();
    private logsCache: Map<string, any[]> = new Map();

    // ── Concurrency throttle ─────────────────────────────────────────────────
    private maxConcurrentDevices: number = DEFAULT_MAX_CONCURRENT;
    private managedDevices: Map<string, IoTDeviceConfig> = new Map();  // all user-requested
    private deviceStates: Map<string, DeviceState> = new Map();
    private idleTimers: Map<string, NodeJS.Timeout> = new Map();
    private configDir: string;

    constructor(networkInterface: string = 'eth0', configDir?: string) {
        super();
        this.daemonInterface = networkInterface;
        this.configDir = configDir || path.join(process.cwd(), 'config');

        let scriptPath = path.resolve(path.join(__dirname, '../iot/iot_emulator.py'));
        if (!fs.existsSync(scriptPath)) {
            scriptPath = path.resolve(path.join(__dirname, './iot/iot_emulator.py'));
        }
        this.pythonScriptPath = scriptPath;
        this.loadSettings();
        log('IOT', `Manager initialized — interface: ${this.daemonInterface}, maxConcurrent: ${this.maxConcurrentDevices}`);
    }

    // ── Settings persistence ─────────────────────────────────────────────────

    private getSettingsPath(): string {
        return path.join(this.configDir, 'iot-settings.json');
    }

    private loadSettings(): void {
        try {
            const p = this.getSettingsPath();
            if (fs.existsSync(p)) {
                const data = JSON.parse(fs.readFileSync(p, 'utf8'));
                if (typeof data.maxConcurrentDevices === 'number' && data.maxConcurrentDevices > 0) {
                    this.maxConcurrentDevices = data.maxConcurrentDevices;
                }
            }
        } catch (e) { log('IOT', `Failed to load settings: ${e}`, 'warn'); }
    }

    private saveSettings(): void {
        try {
            fs.writeFileSync(this.getSettingsPath(), JSON.stringify({
                maxConcurrentDevices: this.maxConcurrentDevices
            }, null, 2));
        } catch (e) { log('IOT', `Failed to save settings: ${e}`, 'warn'); }
    }

    // ── Throttle helpers ─────────────────────────────────────────────────────

    private getActiveCount(): number {
        let n = 0;
        for (const s of this.deviceStates.values()) if (s === 'ACTIVE') n++;
        return n;
    }

    private async activateDevice(config: IoTDeviceConfig): Promise<void> {
        this.ensureDaemon();
        await this.waitForDaemonReady(8000);
        this.deviceStates.set(config.id, 'ACTIVE');
        this.runningDevices.set(config.id, config);
        this.sendCommand({ cmd: 'start', device: config });
        log('IOT', `Activated: ${config.id} [${this.getActiveCount()}/${this.maxConcurrentDevices}]`);
    }

    private promoteNextQueued(): void {
        if (this.getActiveCount() >= this.maxConcurrentDevices) return;
        for (const [id, state] of this.deviceStates.entries()) {
            if (state === 'QUEUED') {
                const cfg = this.managedDevices.get(id);
                if (cfg) {
                    this.activateDevice(cfg).catch(e => log('IOT', `Promote failed ${id}: ${e}`, 'error'));
                    return;
                }
            }
        }
    }

    private requeueDevice(deviceId: string): void {
        this.idleTimers.delete(deviceId);
        const cfg = this.managedDevices.get(deviceId);
        if (!cfg || this.deviceStates.get(deviceId) !== 'IDLE') return;

        if (this.getActiveCount() < this.maxConcurrentDevices) {
            this.activateDevice(cfg).catch(e => log('IOT', `Requeue activate failed ${deviceId}: ${e}`, 'error'));
        } else {
            this.deviceStates.set(deviceId, 'QUEUED');
            log('IOT', `Device ${deviceId} re-queued (slots full)`);
        }
    }

    // ── Public API ───────────────────────────────────────────────────────────

    async startDevice(deviceConfig: IoTDeviceConfig): Promise<void> {
        if (this.managedDevices.has(deviceConfig.id)) {
            log('IOT', `Device ${deviceConfig.id} already managed`, 'debug');
            return;
        }
        this.managedDevices.set(deviceConfig.id, deviceConfig);

        if (this.getActiveCount() < this.maxConcurrentDevices) {
            await this.activateDevice(deviceConfig);
        } else {
            this.deviceStates.set(deviceConfig.id, 'QUEUED');
            log('IOT', `Device ${deviceConfig.id} queued (${this.getActiveCount()}/${this.maxConcurrentDevices} slots used)`);
            this.emit('device:queued', { device_id: deviceConfig.id });
        }
    }

    async stopDevice(deviceId: string): Promise<void> {
        const timer = this.idleTimers.get(deviceId);
        if (timer) { clearTimeout(timer); this.idleTimers.delete(deviceId); }

        const state = this.deviceStates.get(deviceId);
        this.managedDevices.delete(deviceId);
        this.deviceStates.delete(deviceId);

        if (state === 'ACTIVE' && this.runningDevices.has(deviceId)) {
            this.runningDevices.delete(deviceId);
            this.sendCommand({ cmd: 'stop', device_id: deviceId });
            log('IOT', `Stopping active device: ${deviceId}`);
            setTimeout(() => this.promoteNextQueued(), 500);
        } else {
            log('IOT', `Device ${deviceId} removed from queue (was ${state || 'unknown'})`);
        }
    }

    async stopAll(): Promise<void> {
        log('IOT', `Stopping all ${this.managedDevices.size} managed devices...`);
        for (const timer of this.idleTimers.values()) clearTimeout(timer);
        this.idleTimers.clear();
        this.managedDevices.clear();
        this.deviceStates.clear();
        this.runningDevices.clear();
        this.sendCommand({ cmd: 'stop_all' });
    }

    setMaxConcurrent(max: number): void {
        const prev = this.maxConcurrentDevices;
        this.maxConcurrentDevices = Math.max(1, max);
        this.saveSettings();

        if (max > prev) {
            const slots = max - this.getActiveCount();
            let promoted = 0;
            for (const [id, state] of this.deviceStates.entries()) {
                if (promoted >= slots) break;
                if (state === 'QUEUED') {
                    const cfg = this.managedDevices.get(id);
                    if (cfg) {
                        this.activateDevice(cfg).catch(e => log('IOT', `Promote failed: ${e}`, 'error'));
                        promoted++;
                    }
                }
            }
            if (promoted > 0) log('IOT', `Promoted ${promoted} queued devices (limit → ${max})`);
        } else {
            log('IOT', `Limit reduced to ${max} — active devices finish naturally (no SIGKILL)`);
        }
    }

    getMaxConcurrent(): number { return this.maxConcurrentDevices; }

    getQueueStats(): { max: number; active: number; queued: number; idle: number } {
        let active = 0, queued = 0, idle = 0;
        for (const s of this.deviceStates.values()) {
            if (s === 'ACTIVE') active++;
            else if (s === 'QUEUED') queued++;
            else if (s === 'IDLE') idle++;
        }
        return { max: this.maxConcurrentDevices, active, queued, idle };
    }

    getDeviceStates(): Record<string, DeviceState> {
        const out: Record<string, DeviceState> = {};
        for (const [id, state] of this.deviceStates.entries()) out[id] = state;
        return out;
    }

    // ── Daemon lifecycle ─────────────────────────────────────────────────────

    private spawnDaemon(): void {
        if (this.daemonProcess) return;

        const args = [
            this.pythonScriptPath,
            '--daemon',
            '--interface', this.daemonInterface,
            '--dhcp-mode', 'auto',
            '--json-output',
            '--enable-bad-behavior',
        ];

        log('IOT', `Spawning daemon: python3 ${args.join(' ')}`, 'debug');

        this.daemonProcess = spawn('python3', args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            detached: false,
        });

        this.daemonProcess.stdout?.on('data', (data: Buffer) => {
            const lines = data.toString().split('\n').filter(l => l.trim());
            for (const line of lines) {
                try {
                    this.handlePythonMessage(JSON.parse(line));
                } catch {
                    if (line.includes('Permission denied')) {
                        this.emit('daemon:error', { error: 'Permission denied: Scapy requires root/sudo' });
                    }
                }
            }
        });

        this.daemonProcess.stderr?.on('data', (data: Buffer) => {
            const txt = data.toString();
            if (txt.includes('WARNING - Unknown protocol')) return;
            log('IOT-PY-ERR', txt, 'error');
        });

        this.daemonProcess.on('exit', (code, signal) => {
            log('IOT', `Daemon exited (code=${code}, signal=${signal})`, 'warn');
            this.daemonProcess = null;
            this.daemonReady = false;
            for (const id of this.runningDevices.keys()) {
                this.emit('device:stopped', { device_id: id, code });
            }
            if (!this.gaveUp) this.scheduleRestart();
        });

        this.daemonProcess.on('error', (err) => {
            log('IOT', `Daemon process error: ${err.message}`, 'error');
            this.emit('daemon:error', { error: err.message });
        });
    }

    private scheduleRestart(): void {
        this.restartAttempts++;
        if (this.restartAttempts > MAX_RESTART_ATTEMPTS) {
            log('IOT', `Daemon failed ${MAX_RESTART_ATTEMPTS} times — giving up`, 'error');
            this.gaveUp = true;
            this.emit('daemon:failed', {
                message: 'IoT daemon crashed repeatedly — manual restart required',
                attempts: this.restartAttempts - 1,
            });
            return;
        }

        const delay = Math.min(
            RESTART_BASE_DELAY_MS * Math.pow(2, this.restartAttempts - 1),
            RESTART_MAX_DELAY_MS
        );
        log('IOT', `Daemon restart attempt ${this.restartAttempts}/${MAX_RESTART_ATTEMPTS} in ${delay}ms`, 'warn');

        this.restartTimer = setTimeout(async () => {
            this.spawnDaemon();
            const recovered = new Map(this.runningDevices);
            await this.waitForDaemonReady(5000);
            if (this.daemonReady) {
                log('IOT', `Daemon recovered — re-sending ${recovered.size} device start commands`);
                this.restartAttempts = 0;
                for (const cfg of recovered.values()) {
                    this.sendCommand({ cmd: 'start', device: cfg });
                }
            }
        }, delay);
    }

    private waitForDaemonReady(timeoutMs: number): Promise<void> {
        return new Promise(resolve => {
            if (this.daemonReady) { resolve(); return; }
            const timer = setTimeout(resolve, timeoutMs);
            const onReady = () => { clearTimeout(timer); resolve(); };
            this.once('_daemon_ready', onReady);
        });
    }

    private sendCommand(cmd: object): void {
        if (!this.daemonProcess || !this.daemonProcess.stdin) {
            log('IOT', 'Cannot send command — daemon not running', 'warn');
            return;
        }
        try {
            this.daemonProcess.stdin.write(JSON.stringify(cmd) + '\n');
        } catch (e: any) {
            log('IOT', `Failed to write to daemon stdin: ${e.message}`, 'error');
        }
    }

    private ensureDaemon(): void {
        if (this.gaveUp) throw new Error('IoT daemon is in failed state — manual restart required');
        if (!this.daemonProcess) {
            this.restartAttempts = 0;
            this.gaveUp = false;
            this.spawnDaemon();
        }
    }

    // ── Message handler ───────────────────────────────────────────────────────

    private handlePythonMessage(msg: any): void {
        const { type, device_id } = msg;

        if (type === 'daemon_ready') {
            log('IOT', `Daemon ready (interface=${msg.interface})`);
            this.daemonReady = true;
            this.emit('_daemon_ready');
            return;
        }
        if (type === 'daemon_error') { log('IOT', `Daemon error: ${msg.error}`, 'error'); return; }
        if (type === 'daemon_status') { this.emit('daemon:status', msg); return; }
        if (!device_id) return;

        switch (type) {
            case 'started':
                this.emit('device:started', msg);
                break;
            case 'stopped': {
                this.runningDevices.delete(device_id);
                const cfg = this.managedDevices.get(device_id);
                const currentState = this.deviceStates.get(device_id);
                if (cfg && currentState === 'ACTIVE') {
                    // Device completed its cycle → IDLE → re-queue after traffic_interval
                    this.deviceStates.set(device_id, 'IDLE');
                    const delayMs = (cfg.traffic_interval || 60) * 1000;
                    const timer = setTimeout(() => this.requeueDevice(device_id), delayMs);
                    this.idleTimers.set(device_id, timer);
                    log('IOT', `Device ${device_id} idle for ${cfg.traffic_interval}s before re-queue`);
                    // Let another queued device fill the freed slot immediately
                    this.promoteNextQueued();
                }
                this.emit('device:stopped', msg);
                break;
            }
            case 'stats':
                this.statsCache.set(device_id, msg.stats);
                this.emit('device:stats', msg);
                break;
            case 'log': {
                const logs = this.logsCache.get(device_id) || [];
                logs.push(msg);
                if (logs.length > 100) logs.shift();
                this.logsCache.set(device_id, logs);
                this.emit('device:log', msg);
                break;
            }
            case 'dhcp_offer':
            case 'dhcp_ack':
            case 'dhcp_discover':
                this.emit(`device:${type}`, msg);
                break;
            case 'error':
                this.emit('device:error', msg);
                break;
        }
    }

    // ── Status helpers ────────────────────────────────────────────────────────

    getAllStats(): any {
        const result: any = {};
        this.statsCache.forEach((stats, id) => {
            result[id] = { running: this.runningDevices.has(id), ...stats };
        });
        return result;
    }

    getDeviceStatus(id: string): any {
        return {
            running: this.runningDevices.has(id),
            state: this.deviceStates.get(id) || 'STOPPED',
            stats: this.statsCache.get(id) || null,
            logs: this.logsCache.get(id) || [],
        };
    }

    getRunningDevices(): string[] { return Array.from(this.runningDevices.keys()); }

    setBadBehavior(enabled: boolean): void {
        if (!this.daemonProcess) { log('IOT', 'Cannot set bad behavior — daemon not running', 'warn'); return; }
        this.sendCommand({ cmd: enabled ? 'enable_bad_behavior' : 'disable_bad_behavior' });
        log('IOT', `Bad behavior ${enabled ? 'ENABLED' : 'DISABLED'} globally`);
    }

    isDaemonHealthy(): boolean { return this.daemonProcess !== null && this.daemonReady && !this.gaveUp; }

    setInterface(newInterface: string): void {
        if (this.daemonInterface !== newInterface) {
            log('IOT', `Interface change requested (${this.daemonInterface} → ${newInterface}) — ignored, restart Stigix to change interface`);
        }
    }
}

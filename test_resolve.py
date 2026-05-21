import ipaddress
import socket

def resolve_input(ip_input):
    try:
        if '/' in ip_input:
            network = ipaddress.ip_network(ip_input, strict=False)
            return (ip_input, [str(network)])
        else:
            try:
                ip = ipaddress.ip_address(ip_input)
                return (ip_input, [f"{ip}/32"])
            except ValueError:
                import socket
                addr_info = socket.getaddrinfo(ip_input, None, socket.AF_INET)
                ips = list(set([item[4][0] for item in addr_info]))
                if not ips:
                    raise ValueError(f"Could not resolve any IPv4 addresses for {ip_input}")
                
                return (ip_input, [f"{ip}/32" for ip in ips])
    except Exception as e:
        raise ValueError(f"Invalid IP address, prefix, or FQDN: {ip_input} ({e})")

print(resolve_input("target.stigix.io"))

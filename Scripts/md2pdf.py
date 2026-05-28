#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

# Auto-install/import handler for dependencies
try:
    from markdown_pdf import MarkdownPdf, Section
except ImportError:
    print("📦 Library 'markdown-pdf' not found. Installing it now...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "markdown-pdf"], check=True)
        from markdown_pdf import MarkdownPdf, Section
        print("✅ 'markdown-pdf' installed successfully!")
    except Exception as e:
        print(f"❌ Failed to install 'markdown-pdf': {e}")
        print("Please install it manually by running: pip install markdown-pdf")
        sys.exit(1)

# Default premium GitHub-like CSS styling
DEFAULT_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #333333;
    padding: 30px;
}
h1, h2, h3, h4, h5, h6 {
    color: #111111;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 16px;
}
h1 {
    font-size: 26px;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 8px;
}
h2 {
    font-size: 20px;
    border-bottom: 1px solid #eaecef;
    padding-bottom: 6px;
}
h3 {
    font-size: 16px;
}
a {
    color: #0366d6;
    text-decoration: none;
}
code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 85%;
    background-color: rgba(27,31,35,0.05);
    padding: 0.2em 0.4em;
    border-radius: 3px;
}
pre {
    background-color: #f6f8fa;
    padding: 16px;
    border-radius: 6px;
    overflow: auto;
    line-height: 1.45;
}
pre code {
    background-color: transparent;
    padding: 0;
    font-size: 100%;
    word-break: normal;
}
blockquote {
    border-left: 0.25em solid #dfe2e5;
    color: #6a737d;
    padding: 0 1em;
    margin: 0 0 16px 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 16px;
}
table th, table td {
    padding: 6px 13px;
    border: 1px solid #dfe2e5;
}
table tr:nth-child(even) {
    background-color: #f6f8fa;
}
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 16px auto;
}
"""

def convert_md_to_pdf(md_path, pdf_path, css_content=None):
    """Converts a single markdown file to PDF."""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Remove local/internal markdown anchor links (e.g. [Text](#anchor-name)) 
        # to prevent PyMuPDF layout engine failures on missing targets.
        import re
        md_content = re.sub(r'\[([^\]]+)\]\(\s*#[^)]+\)', r'\1', md_content)

        pdf = MarkdownPdf(toc_level=2)
        pdf.add_section(Section(md_content), user_css=css_content or DEFAULT_CSS)
        pdf.save(pdf_path)
        print(f"✓ Converted: {os.path.basename(md_path)} ➔ {os.path.basename(pdf_path)}")
        return True
    except Exception as e:
        print(f"✗ Failed to convert {md_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="🚀 Stigix Markdown to PDF Converter (Ready for NotebookLM)"
    )
    parser.add_argument(
        "input",
        help="Path to the input Markdown file (.md) or directory containing Markdown files"
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to the output PDF file or output directory (optional)"
    )
    parser.add_argument(
        "--css",
        help="Path to a custom CSS file for custom styling (optional)"
    )
    
    args = parser.parse_args()
    
    # Resolve custom CSS
    css_content = DEFAULT_CSS
    if args.css:
        if os.path.exists(args.css):
            with open(args.css, "r", encoding="utf-8") as f:
                css_content = f.read()
        else:
            print(f"⚠️ Custom CSS file not found at: {args.css}. Using default style.")

    # Check input type
    if not os.path.exists(args.input):
        print(f"❌ Input path does not exist: {args.input}")
        sys.exit(1)

    if os.path.isfile(args.input):
        # Single file mode
        pdf_path = args.output
        if not pdf_path:
            # Generate default PDF path
            base, _ = os.path.splitext(args.input)
            pdf_path = base + ".pdf"
        elif os.path.isdir(pdf_path):
            # Output is a folder, save in it
            base = os.path.basename(args.input)
            name, _ = os.path.splitext(base)
            pdf_path = os.path.join(pdf_path, name + ".pdf")
            
        convert_md_to_pdf(args.input, pdf_path, css_content)

    elif os.path.isdir(args.input):
        # Batch directory mode
        out_dir = args.output or args.input
        os.makedirs(out_dir, exist_ok=True)

        md_files = [f for f in os.listdir(args.input) if f.lower().endswith(".md")]
        if not md_files:
            print(f"⚠️ No markdown (.md) files found in: {args.input}")
            sys.exit(0)

        print(f"📂 Found {len(md_files)} markdown files in '{args.input}'...")
        success_count = 0
        for f in md_files:
            in_path = os.path.join(args.input, f)
            name, _ = os.path.splitext(f)
            out_path = os.path.join(out_dir, name + ".pdf")
            if convert_md_to_pdf(in_path, out_path, css_content):
                success_count += 1

        print(f"\n🎉 Batch conversion complete: {success_count}/{len(md_files)} files successfully converted.")

if __name__ == "__main__":
    main()

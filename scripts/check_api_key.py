"""Report whether an Anthropic API key is configured - WITHOUT revealing it.

Usage (project root):
    .venv\\Scripts\\python.exe scripts\\check_api_key.py
Prints only: where a key was found, its length, and whether it looks like a real key
(not the template placeholder). Never prints any part of the key. Makes no network call.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env_file = ROOT / ".env"
    from_file = None
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY") and "=" in line:
                from_file = line.split("=", 1)[1].strip().strip('"').strip("'")
    from_env = os.environ.get("ANTHROPIC_API_KEY")
    key = from_env or from_file
    print(f".env file present: {env_file.exists()}")
    print(f"key in process environment: {bool(from_env)}")
    print(f"key in .env: {bool(from_file) and from_file != 'your-api-key-here'}")
    if not key or key == "your-api-key-here":
        print("RESULT: no usable key configured.")
        return 1
    looks_ok = key.startswith("sk-ant-") and len(key) > 40 and " " not in key
    print(f"RESULT: key configured (length {len(key)}); format looks valid: {looks_ok}")
    return 0 if looks_ok else 1


if __name__ == "__main__":
    sys.exit(main())

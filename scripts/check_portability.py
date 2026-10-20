#!/usr/bin/env python3
"""Scan publishable Git files for private machine paths, credentials, and binaries."""

import argparse
import ipaddress
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    "personal absolute path": re.compile(r"(?:/home|/Users|/media)/[A-Za-z0-9_.-]+|[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|nvapi-[A-Za-z0-9_-]{30,})"),
    "embedded URL credential": re.compile(r"https?://[^/\s:@]+:[^/\s@]+@"),
}
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
EXCLUDED_PARTS = {"__pycache__", ".venv", "venv", "runtime", "runtime_pymol_whl"}
EXCLUDED_SUFFIXES = {".pyc", ".xtc", ".trr", ".tpr", ".cpt", ".edr", ".ckpt", ".pem", ".p12", ".pfx"}


def scan_text(text):
    for number, line in enumerate(text.splitlines(), 1):
        for label, pattern in RULES.items():
            if pattern.search(line):
                yield number, label
        for match in IPV4.finditer(line):
            try:
                address = ipaddress.ip_address(match.group())
            except ValueError:
                continue
            if not address.is_loopback and not address.is_unspecified:
                yield number, "literal host IP (review before publication)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Scan Git index content")
    args = parser.parse_args()
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    findings = []
    for name in filter(None, paths):
        path = Path(name)
        if EXCLUDED_PARTS.intersection(path.parts) or path.suffix in EXCLUDED_SUFFIXES or path.name in {".env", "credentials"}:
            findings.append(f"{name}: excluded runtime/private artifact")
            continue
        data = (subprocess.check_output(["git", "show", f":{name}"], cwd=ROOT)
                if args.staged else (ROOT / path).read_bytes())
        if b"\0" in data:
            findings.append(f"{name}: binary file requires explicit publication review")
            continue
        for line, label in scan_text(data.decode("utf-8", errors="replace")):
            findings.append(f"{name}:{line}: {label}")
    for finding in findings:
        print(finding)
    print(f"Scanned {len(list(filter(None, paths)))} tracked files; {len(findings)} findings.")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())

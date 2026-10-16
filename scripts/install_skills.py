#!/usr/bin/env python3
"""Install the bundled Codex skills without replacing existing installations."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCES = {"zy-ai4bio": REPO / "zy-ai4bio"}
SOURCES.update({path.name: path for path in (REPO / "skills").iterdir() if (path / "SKILL.md").is_file()})


def default_target() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home).expanduser() if codex_home else Path.home() / ".codex") / "skills"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=default_target(), help="Codex skills directory")
    parser.add_argument("--skills", nargs="+", help="Skill names to install; defaults to all bundled skills")
    parser.add_argument("--list", action="store_true", help="List bundled skills and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show planned copies without writing")
    args = parser.parse_args()

    if args.list:
        print("\n".join(sorted(SOURCES)))
        return 0

    names = list(dict.fromkeys(args.skills or sorted(SOURCES)))
    unknown = sorted(set(names) - SOURCES.keys())
    if unknown:
        parser.error(f"unknown skills: {', '.join(unknown)}")
    target = args.target.expanduser().resolve()
    existing = [name for name in names if (target / name).exists() or (target / name).is_symlink()]
    if existing:
        parser.error(f"already installed (left untouched): {', '.join(existing)}")

    for name in names:
        print(f"{SOURCES[name]} -> {target / name}")
    if args.dry_run:
        return 0

    target.mkdir(parents=True, exist_ok=True)
    for name in names:
        with tempfile.TemporaryDirectory(prefix=f".{name}.", dir=target) as temporary:
            staged = Path(temporary) / name
            shutil.copytree(SOURCES[name], staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            staged.rename(target / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

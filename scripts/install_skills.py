#!/usr/bin/env python3
"""Install or explicitly update bundled skills with backups and local runtimes preserved."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCES = {"zy-ai4bio": REPO / "zy-ai4bio"}
SOURCES.update({path.name: path for path in (REPO / "skills").iterdir() if (path / "SKILL.md").is_file()})
DEPENDENCIES = {
    "ppi-vscreen": ["lightdock"],
    "reverse-target-vscreen": ["unidock-vscreen"],
}
EXCLUDED = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".venv", "venv", "runtime", "runtime_pymol_whl",
    "runtime_manifest.json", ".env", ".env.*", "credentials", "*.key",
    "results", "screen", "models", "checkpoints",
)
LOCAL_RESOURCES = (
    "runtime", "runtime_pymol_whl", "runtime_manifest.json", ".venv", "venv",
    "models", "checkpoints", "credentials", ".env", ".env.*", "*.key",
    "*.local.json", "*.local.env", "results", "screen",
)


def prepare_skill(name: str, staged: Path, previous: Path | None) -> None:
    shutil.copytree(SOURCES[name], staged, ignore=EXCLUDED)
    if name == "zy-ai4bio":
        (staged / "scripts").mkdir(exist_ok=True)
        shutil.copy2(REPO / "scripts/check_environment.py", staged / "scripts")
        shutil.copytree(REPO / "config", staged / "assets/config", ignore=EXCLUDED)
        shutil.copy2(REPO / "docs/portable-installation.md", staged / "references")
    if previous:
        for resource in previous.iterdir():
            if not any(fnmatch.fnmatch(resource.name, pattern) for pattern in LOCAL_RESOURCES):
                continue
            destination = staged / resource.name
            if destination.exists() or destination.is_symlink():
                raise ValueError(f"Published file conflicts with local resource: {resource.name}")
            if resource.is_symlink():
                # Resolve relative links before the installed directory is moved.
                destination.symlink_to(resource.resolve(), target_is_directory=resource.is_dir())
            elif resource.is_dir():
                shutil.copytree(resource, destination, symlinks=True)
            else:
                shutil.copy2(resource, destination)
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    (staged / ".zy-ai4bio-install.json").write_text(json.dumps({
        "schema_version": 1,
        "skill": name,
        "source": "https://github.com/keyanzhu333-spec/zhuying-ai4bio",
        "commit": commit,
        "installed_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2) + "\n", encoding="utf-8")


def default_target() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home).expanduser() if codex_home else Path.home() / ".codex") / "skills"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=default_target(), help="Codex skills directory")
    parser.add_argument("--skills", nargs="+", help="Skill names to install; defaults to all bundled skills")
    parser.add_argument("--list", action="store_true", help="List bundled skills and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show planned copies without writing")
    parser.add_argument("--update", action="store_true", help="Back up and replace existing skills; preserve local runtimes/configuration")
    parser.add_argument("--backup-dir", type=Path, help="Parent for timestamped backups; default is beside the skills directory")
    args = parser.parse_args()

    if args.list:
        print("\n".join(sorted(SOURCES)))
        return 0

    names = list(dict.fromkeys(args.skills or sorted(SOURCES)))
    unknown = sorted(set(names) - SOURCES.keys())
    if unknown:
        parser.error(f"unknown skills: {', '.join(unknown)}")
    target = args.target.expanduser().resolve()
    for name in list(names):
        for dependency in DEPENDENCIES.get(name, []):
            if dependency not in names and not (target / dependency / "SKILL.md").is_file():
                names.append(dependency)
    existing = [name for name in names if (target / name).exists() or (target / name).is_symlink()]
    if existing and not args.update:
        parser.error(f"already installed (left untouched): {', '.join(existing)}")
    for name in existing:
        if (target / name).is_symlink() or not (target / name).is_dir():
            parser.error(f"cannot update a symlink or non-directory skill: {name}")

    for name in names:
        action = "Update with backup" if name in existing else "Install"
        print(f"{action}: {name} -> {target / name}")
    if args.dry_run:
        return 0

    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".zy-ai4bio-update-", dir=target) as temporary:
        stage_root = Path(temporary)
        for name in names:
            prepare_skill(name, stage_root / name, target / name if name in existing else None)
        backup = None
        if existing:
            backup_parent = (args.backup_dir.expanduser().resolve() if args.backup_dir
                             else target.parent / "skill-backups")
            if backup_parent == target or target in backup_parent.parents:
                parser.error("backup directory must be outside the active skills directory")
            backup_parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            backup = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_parent))
        installed = []
        moved = []
        try:
            for name in names:
                if name in existing:
                    (target / name).rename(backup / name)
                    moved.append(name)
                (stage_root / name).rename(target / name)
                installed.append(name)
        except BaseException:
            for name in reversed(installed):
                (target / name).rename(stage_root / name)
            for name in reversed(moved):
                (backup / name).rename(target / name)
            raise
        if backup:
            print(f"Backup: {backup}")
        print(f"Installed/updated {len(names)} skills. Available on your next Codex turn.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

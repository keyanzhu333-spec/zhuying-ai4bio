#!/usr/bin/env python3
"""Run GNINA and optionally build a PyMOL/PLIP analysis bundle.

The wrapper accepts PDB/SDF/MOL2/PDBQT inputs, supports native GNINA, WSL,
or Docker backends, and writes GNINA scores extracted from the output SDF.
It never modifies the input structures.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def resolve_executable(value: str) -> str:
    candidate = Path(value).expanduser()
    if candidate.exists():
        return str(candidate.resolve())
    found = shutil.which(value)
    if found:
        return found
    raise FileNotFoundError(f"Executable not found: {value}")


def find_runtime_python(skill_dir: Path) -> str:
    """Select the Python ABI used by the bundled PyMOL extension.

    The bundled PyMOL wheel currently contains a CPython 3.12 extension.  A
    launcher started with Python 3.13 can still run GNINA, but using that same
    interpreter for ``run_pymol.py`` fails with ``No module named pymol._cmd``.
    """
    override = os.environ.get("GNINA_PYTHON")
    if override:
        return resolve_executable(override)
    if not (skill_dir / "runtime_pymol_whl").is_dir():
        return sys.executable
    candidates = [
        os.environ.get("GNINA_PYTHON"),
        str(skill_dir / ".venv" / "bin" / "python"),
        shutil.which("python3.12"),
        shutil.which("python3.12.exe"),
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if probe.stdout.strip() == "3.12":
                return str(Path(candidate).resolve())
        except OSError:
            continue
    return sys.executable


def run_command(args: list[str], log_path: Path, manifest: list[list[str]]) -> None:
    manifest.append([str(item) for item in args])
    result = subprocess.run(
        [str(item) for item in args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(result.stdout, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        hint = ""
        if result.returncode == 139 and args[:2] == ["wsl.exe", "--"]:
            hint = (
                "\nHint: GNINA 在 WSL/CUDA 初始化阶段发生段错误；"
                "请勾选 CPU 模式，程序会自动隔离 CUDA。"
            )
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {' '.join(map(str, args))}\n"
            f"See {log_path}{hint}"
        )


def collect_plip_visuals(plip_dir: Path, pose_state: int) -> dict[str, str]:
    """Expose PLIP's generated site image/session under stable filenames."""
    visuals: dict[str, str] = {}
    images = sorted(path for path in plip_dir.glob("*.png") if path.is_file())
    sessions = sorted(path for path in plip_dir.glob("*.pse") if path.is_file())
    if images:
        target = plip_dir / f"plip_pose{pose_state}_interactions.png"
        if images[0].resolve() != target.resolve():
            shutil.copy2(images[0], target)
        visuals["plip_interaction_image"] = str(target.resolve())
    if sessions:
        target = plip_dir / f"plip_pose{pose_state}_interactions.pse"
        if sessions[0].resolve() != target.resolve():
            shutil.copy2(sessions[0], target)
        visuals["plip_interaction_session"] = str(target.resolve())
    return visuals


def parse_plip_interacting_residues(plip_dir: Path) -> list[str]:
    """Read residue identifiers from PLIP's report for pocket labels."""
    report_files = sorted(path for path in plip_dir.glob("*_report.txt") if path.is_file())
    if not report_files:
        return []
    residues: set[str] = set()
    try:
        report = report_files[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in report.splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")]
        # PLIP tables use: | RESNR | RESTYPE | RESCHAIN | ...
        if len(parts) >= 4 and parts[1].isdigit() and parts[2].isalpha() and len(parts[2]) <= 4:
            residues.add(f"{parts[2].upper()}{parts[1]}")
    return sorted(residues)


def build_pymol_label_commands(residues: list[str]) -> str:
    """Build clean residue labels in the same style as the ZYDock renderer."""
    commands: list[str] = []
    for residue in residues:
        split_at = 0
        while split_at < len(residue) and residue[split_at].isalpha():
            split_at += 1
        restype, resnr = residue[:split_at], residue[split_at:]
        if not resnr:
            continue
        selection = f"label_{restype}{resnr}"
        commands.append(f"select {selection}, resi {resnr} and name CA and polymer")
        commands.append(f"label {selection}, \"{restype} {resnr}\"")
    return "\n".join(commands) or "# No interacting residues found to label"


def build_pymol_contact_selection(residues: list[str]) -> str:
    """Select only PLIP-contact residues for the focused stick representation."""
    residue_numbers: list[str] = []
    for residue in residues:
        number = residue.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        if number.isdigit():
            residue_numbers.append(number)
    if not residue_numbers:
        return "select contact_residues, pocket_local"
    numbers = "+".join(dict.fromkeys(residue_numbers))
    return f"select contact_residues, complex_struct and polymer and resi {numbers}"


def make_plip_local_script(
    complex_pdb: Path,
    image: Path,
    session: Path,
    label_commands: str = "",
    plip_session: Path | None = None,
    contact_selection: str = "select contact_residues, pocket_local",
) -> str:
    """Build a ZYDock-style, publication-oriented local-pocket view."""
    plip_load = f"load {plip_session.resolve().as_posix()}, plip_interactions\n" if plip_session else ""
    return f"""{plip_load}load {complex_pdb.resolve().as_posix()}, complex_struct
bg_color white
set ray_trace_mode, 1
set ray_trace_fog, 0
set depth_cue, 0
set antialias, 2
set line_smooth, 1
set light_count, 8
set specular, 0.3
set shininess, 50
set ambient, 0.7
set direct, 0.4
set reflect, 0.1
set surface_quality, 1
hide everything, complex_struct
select ligand_local, complex_struct and organic and not polymer and not solvent
select pocket_local, byres ((complex_struct and polymer) within 5.0 of ligand_local)
{contact_selection}
show cartoon, complex_struct and polymer
show sticks, ligand_local
color lightblue, complex_struct and polymer
color yellow, ligand_local
color orange, contact_residues
set cartoon_oval_length, 1.2
set cartoon_oval_width, 0.4
set cartoon_rect_length, 1.2
set cartoon_rect_width, 0.5
set cartoon_loop_radius, 0.7
set cartoon_transparency, 0.8, complex_struct and polymer
set stick_radius, 0.18
show sticks, contact_residues
set label_font_id, 7
set label_size, 12
set label_color, black
set label_shadow_mode, 1
{label_commands}
distance plip_contacts, ligand_local, contact_residues, 3.6, mode=2
set dash_color, magenta
set dash_width, 3
orient ligand_local or contact_residues
zoom ligand_local or contact_residues, 5
save {session.resolve().as_posix()}
png {image.resolve().as_posix()}, width=2400, height=1800, dpi=300, ray=1
quit
"""


def render_plip_local_view(
    complex_pdb: Path,
    plip_dir: Path,
    pose_state: int,
    runtime_python: str,
    manifest: list[list[str]],
    pymol_bin: str | None = None,
) -> dict[str, str]:
    """Render a local PLIP-oriented pocket image and PyMOL session."""
    image = plip_dir / f"plip_pose{pose_state}_interactions.png"
    session = plip_dir / f"plip_pose{pose_state}_interactions.pse"
    script = plip_dir / f"plip_pose{pose_state}_interactions.pml"
    residues = parse_plip_interacting_residues(plip_dir)
    labels = build_pymol_label_commands(residues)
    contact_selection = build_pymol_contact_selection(residues)
    source_sessions = sorted(path for path in plip_dir.glob("*.pse") if path.is_file())
    source_session = next(
        (path for path in source_sessions if path.resolve() != session.resolve()),
        None,
    )
    script.write_text(
        make_plip_local_script(
            complex_pdb, image, session, labels, source_session, contact_selection,
        ),
        encoding="utf-8",
    )
    if pymol_bin:
        pymol_command = [resolve_executable(pymol_bin), "-cq", str(script)]
    else:
        pymol_command = [runtime_python, str(Path(__file__).with_name("run_pymol.py")), "-cq", str(script)]
    run_command(pymol_command, plip_dir.parent / "plip_local_view.log", manifest)
    return {
        "plip_interaction_image": str(image.resolve()),
        "plip_interaction_session": str(session.resolve()),
    }


def wsl_available() -> bool:
    return bool(shutil.which("wsl.exe") or shutil.which("wsl"))


def docker_available() -> bool:
    return bool(shutil.which("docker"))


def to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if drive and len(drive) == 1:
        return "/mnt/" + drive + resolved.as_posix()[2:]
    return resolved.as_posix()


def docker_mount(path: Path, container_path: str, read_only: bool = False) -> list[str]:
    mount = f"{path.resolve()}:{container_path}"
    if read_only:
        mount += ":ro"
    return ["-v", mount]


def find_gnina(
    requested: str | None,
    backend: str,
    skill_dir: Path,
    docker_image: str,
    receptor: Path,
    ligand: Path,
    autobox_ligand: Path | None,
    out_dir: Path,
    docker_gpus: bool,
) -> tuple[str, list[str], dict[str, Any]]:
    """Return backend, command prefix, and backend metadata."""
    local_native = skill_dir / "runtime" / "gnina.exe"
    local_linux = skill_dir / "runtime" / "gnina"

    if backend in {"auto", "native"}:
        native_value = requested
        if not native_value and local_native.is_file():
            native_value = str(local_native)
        if native_value:
            candidate = Path(native_value)
            if not (sys.platform == "win32" and candidate.exists() and candidate.suffix.lower() != ".exe"):
                native = resolve_executable(native_value)
                return "native", [native], {"gnina_executable": native}
        if backend == "native":
            raise FileNotFoundError("No native GNINA executable was found")
        path_gnina = shutil.which("gnina")
        if path_gnina:
            return "native", [path_gnina], {"gnina_executable": path_gnina}

    if backend in {"auto", "wsl"}:
        wsl_binary = requested
        if not wsl_binary and local_linux.is_file():
            wsl_binary = str(local_linux)
        if wsl_binary and wsl_available():
            binary_path = Path(wsl_binary)
            command = ["wsl.exe", "--", to_wsl_path(binary_path)]
            return "wsl", command, {
                "gnina_executable": str(binary_path.resolve()),
                "wsl_binary": to_wsl_path(binary_path),
            }
        if backend == "wsl":
            raise FileNotFoundError(
                "WSL backend requires wsl.exe and a GNINA Linux binary. "
                "Run install_gnina_runtime.py or pass --gnina-bin."
            )

    if backend in {"auto", "docker"}:
        if not docker_available():
            raise FileNotFoundError(
                "No GNINA backend found. Install native gnina.exe, enable WSL, "
                "or install Docker Desktop."
            )
        command = ["docker", "run", "--rm"]
        if docker_gpus:
            command.extend(["--gpus", "all"])
        command.extend(docker_mount(out_dir, "/out"))
        command.append(docker_image)
        metadata = {"docker_image": docker_image}
        return "docker", command, metadata

    raise ValueError(f"Unsupported GNINA backend: {backend}")


def append_gnina_inputs(
    command: list[str],
    backend: str,
    receptor: Path,
    ligand: Path,
    autobox_ligand: Path | None,
    out_dir: Path,
) -> None:
    if backend == "docker":
        mounted: dict[Path, str] = {}

        def container_file(path: Path, index: int) -> str:
            parent = path.resolve().parent
            if parent not in mounted:
                target = f"/in{len(mounted)}"
                command[3:3] = docker_mount(parent, target, read_only=True)
                mounted[parent] = target
            return f"{mounted[parent]}/{path.name}"

        receptor_arg = container_file(receptor, 0)
        ligand_arg = container_file(ligand, 1)
        autobox_arg = container_file(autobox_ligand, 2) if autobox_ligand else None
        command.extend(["-r", receptor_arg, "-l", ligand_arg])
        if autobox_arg:
            command.extend(["--autobox_ligand", autobox_arg])
        command.extend(["-o", "/out/docked.sdf"])
        return

    def local_or_wsl(path: Path) -> str:
        return to_wsl_path(path) if backend == "wsl" else str(path.resolve())

    command.extend(["-r", local_or_wsl(receptor), "-l", local_or_wsl(ligand)])
    if autobox_ligand:
        command.extend(["--autobox_ligand", local_or_wsl(autobox_ligand)])
    command.extend(["-o", local_or_wsl(out_dir / "docked.sdf")])


def make_pymol_script(
    receptor_pdb: Path,
    poses_sdf: Path,
    complex_pdb: Path,
    session: Path,
    image: Path,
    state: int,
) -> str:
    return f"""load {receptor_pdb.resolve().as_posix()}, receptor
load {poses_sdf.resolve().as_posix()}, ligand_poses
create complex_pose{state}, receptor or ligand_poses, {state}, 1
bg_color white
set ray_trace_mode, 1
set ray_trace_fog, 0
set depth_cue, 0
set antialias, 2
set line_smooth, 1
set light_count, 8
set specular, 0.3
set shininess, 50
set ambient, 0.7
set direct, 0.4
set reflect, 0.1
set surface_quality, 1
set cartoon_oval_length, 1.2
set cartoon_oval_width, 0.4
set cartoon_rect_length, 1.2
set cartoon_rect_width, 0.5
set cartoon_loop_radius, 0.7
show cartoon, receptor
show sticks, ligand_poses
color cyan, receptor
color yellow, ligand_poses
set cartoon_transparency, 0.0, receptor
orient complex_pose{state}
zoom complex_pose{state}, 3
save {complex_pdb.resolve().as_posix()}, complex_pose{state}
save {session.resolve().as_posix()}
ray 2400, 1800
png {image.resolve().as_posix()}, width=2400, height=1800, dpi=300, ray=1
quit
"""


def safe_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def prepare_runtime_dlls(skill_dir: Path) -> None:
    """Make bundled Windows extension modules discover their dependent DLLs."""
    runtime = skill_dir / "runtime"
    if runtime.is_dir():
        os.environ["PATH"] = str(runtime) + os.pathsep + str(runtime / "bin") + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        for directory in (
            runtime,
            runtime / "numpy.libs",
            runtime / "scipy.libs",
            runtime / "rdkit.libs",
            runtime / "openbabel.libs",
        ):
            if directory.is_dir():
                os.add_dll_directory(str(directory.resolve()))


def get_prop(mol: Any, names: tuple[str, ...]) -> str | None:
    for name in names:
        if mol.HasProp(name):
            return mol.GetProp(name)
    return None


def write_rankings(sdf_path: Path, out_dir: Path, skill_dir: Path) -> dict[str, Any]:
    """Extract GNINA properties with RDKit; keep the pipeline usable if RDKit is absent."""
    runtime = skill_dir / "runtime"
    prepare_runtime_dlls(skill_dir)
    if runtime.is_dir():
        sys.path.insert(0, str(runtime))
    try:
        from rdkit import Chem
    except Exception as exc:  # pragma: no cover - depends on local runtime
        return {"status": "skipped", "reason": f"RDKit import failed: {exc}"}

    records: list[dict[str, Any]] = []
    # GNINA can preserve unusual or input-specific valence assignments. Read
    # without RDKit sanitization so score properties are still recoverable;
    # chemical validity remains a separate review gate.
    supplier = Chem.SDMolSupplier(str(sdf_path), removeHs=False, sanitize=False)
    for pose_index, mol in enumerate(supplier, start=1):
        if mol is None:
            records.append({"pose": pose_index, "valid": False, "name": ""})
            continue
        cnn_score = safe_float(get_prop(mol, ("CNNscore", "cnnscore")))
        cnn_affinity = safe_float(get_prop(mol, ("CNNaffinity", "cnnaffinity")))
        minimized = safe_float(
            get_prop(mol, ("minimizedAffinity", "minimized_affinity", "Affinity"))
        )
        heavy_atoms = mol.GetNumHeavyAtoms()
        records.append(
            {
                "pose": pose_index,
                "valid": True,
                "name": mol.GetProp("_Name") if mol.HasProp("_Name") else f"pose_{pose_index}",
                "CNNscore": cnn_score,
                "CNNaffinity": cnn_affinity,
                "minimizedAffinity": minimized,
                "heavy_atoms": heavy_atoms,
                "ligand_efficiency": (-minimized / heavy_atoms)
                if minimized is not None and heavy_atoms
                else None,
                "cnnscore_gt_0.5": cnn_score is not None and cnn_score > 0.5,
            }
        )

    records.sort(
        key=lambda row: (
            not row.get("cnnscore_gt_0.5", False),
            -(row.get("CNNaffinity") if row.get("CNNaffinity") is not None else float("-inf")),
            row.get("minimizedAffinity") if row.get("minimizedAffinity") is not None else float("inf"),
        )
    )
    fields = [
        "pose", "valid", "name", "CNNscore", "CNNaffinity", "minimizedAffinity",
        "heavy_atoms", "ligand_efficiency", "cnnscore_gt_0.5",
    ]
    with (out_dir / "ranking.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    (out_dir / "ranking.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    return {"status": "complete", "poses": len(records), "ranking_csv": str(out_dir / "ranking.csv")}


def write_report(
    out_dir: Path,
    args: argparse.Namespace,
    backend: str,
    ranking: dict[str, Any],
    complex_pdb: Path | None,
    plip_visuals: dict[str, str] | None = None,
) -> Path:
    """Write a compact, portable Markdown summary for GUI and command-line users."""
    report_path = out_dir / "report.md"
    lines = [
        "# GNINA 对接分析报告",
        "",
        "## 输入与参数",
        "",
        f"- 受体：`{args.receptor}`",
        f"- 配体：`{args.ligand}`",
        f"- 后端：`{backend}`",
        f"- CNN scoring：`{args.cnn_scoring}`",
        f"- CNN 模型：`{args.cnn}`",
        f"- Exhaustiveness：`{args.exhaustiveness}`",
        f"- Num modes：`{args.num_modes}`",
        f"- Seed：`{args.seed}`",
    ]
    if args.autobox_ligand:
        lines.append(f"- Autobox 配体：`{args.autobox_ligand}`（扩展 {args.autobox_add} Å）")
    else:
        lines.append(f"- 搜索框中心：`{args.center}` Å")
        lines.append(f"- 搜索框尺寸：`{args.size}` Å")
    lines.extend([
        "",
        "## Pose 排名",
        "",
        "| Pose | Name | CNNscore | CNNaffinity | Minimized affinity | CNNscore > 0.5 |",
        "| ---: | --- | ---: | ---: | ---: | :---: |",
    ])
    ranking_csv = out_dir / "ranking.csv"
    if ranking_csv.is_file():
        with ranking_csv.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                lines.append(
                    "| {pose} | {name} | {score} | {affinity} | {minimized} | {selected} |".format(
                        pose=row.get("pose", ""),
                        name=row.get("name", "").replace("|", "\\|"),
                        score=row.get("CNNscore", ""),
                        affinity=row.get("CNNaffinity", ""),
                        minimized=row.get("minimizedAffinity", ""),
                        selected=row.get("cnnscore_gt_0.5", ""),
                    )
                )
    else:
        lines.append("| - | 未生成 ranking.csv | - | - | - | - |")
    lines.extend([
        "",
        "## 输出文件",
        "",
        f"- Docked SDF：`{out_dir / 'docked.sdf'}`",
        f"- 排名 CSV：`{out_dir / 'ranking.csv'}`",
        f"- Manifest：`{out_dir / 'manifest.json'}`",
    ])
    if complex_pdb:
        lines.append(f"- 复合物 PDB：`{complex_pdb}`")
    plip_report = out_dir / f"plip_pose{args.pose_state}" / f"complex_pose{args.pose_state}_report.txt"
    if plip_report.is_file():
        plip_visuals = plip_visuals or {}
        interaction_sections = {
            "Hydrophobic Interactions": "疏水相互作用",
            "Hydrogen Bonds": "氢键",
            "Salt Bridges": "盐桥",
            "pi-Stacking": "π-堆积",
            "pi-Cation Interactions": "π-阳离子相互作用",
            "Halogen Bonds": "卤键",
            "Metal Complexes": "金属配位",
            "Water Bridges": "水桥",
        }
        counts = {name: 0 for name in interaction_sections}
        residues: dict[str, list[str]] = {name: [] for name in interaction_sections}
        current: str | None = None
        for line in plip_report.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("**") and line.endswith("**"):
                current = line.strip("*")
                if current not in counts:
                    current = None
                continue
            if not current or not line.startswith("|") or "RESNR" in line or line.lstrip().startswith("|="):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not cells or not cells[0].isdigit():
                continue
            counts[current] += 1
            if len(cells) >= 3:
                residue = f"{cells[1]}{cells[0]}({cells[2]})"
                if residue not in residues[current]:
                    residues[current].append(residue)
        lines.extend([
            "",
            "## PLIP 相互作用分析",
            "",
            f"PLIP 文本报告：`{plip_report}`。以下为自动提取的相互作用计数，详细距离、角度和原子编号请查看该文件及同目录 XML。",
        ])
        if plip_visuals.get("plip_interaction_image"):
            lines.append(f"PLIP 局部相互作用图：`{plip_visuals['plip_interaction_image']}`。")
        if plip_visuals.get("plip_interaction_session"):
            lines.append(f"PLIP 局部相互作用 PyMOL 会话：`{plip_visuals['plip_interaction_session']}`。")
        for section, label in interaction_sections.items():
            if counts[section]:
                residue_text = ", ".join(residues[section][:12])
                suffix = f"；残基：{residue_text}" if residue_text else ""
                lines.append(f"- {label}：{counts[section]} 项{suffix}")
        lines.append("")
        lines.append("PLIP 结果需要结合受体质子化、配体电荷、金属/水分子保留策略和 PyMOL 几何检查进行复核。")
    lines.extend([
        "",
        "> 说明：CNNscore、CNNaffinity 和 Minimized affinity 是排序与复核指标，不能单独替代实验验证。",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receptor", type=Path, required=True)
    parser.add_argument("--ligand", type=Path, required=True)
    parser.add_argument("--autobox-ligand", type=Path)
    parser.add_argument("--center", nargs=3, type=float, metavar=("X", "Y", "Z"))
    parser.add_argument("--size", nargs=3, type=float, metavar=("SX", "SY", "SZ"))
    parser.add_argument("--autobox-add", type=float, default=4.0)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--gnina-bin",
        default=os.environ.get("GNINA_BIN"),
        help="GNINA executable or Linux binary used by WSL; defaults to GNINA_BIN",
    )
    parser.add_argument("--backend", choices=("auto", "native", "wsl", "docker"), default="auto")
    parser.add_argument("--docker-image", default="gnina/gnina:latest")
    parser.add_argument("--docker-gpus", action="store_true")
    parser.add_argument("--receptor-pdb", type=Path)
    parser.add_argument("--complex-pdb", type=Path)
    parser.add_argument("--pymol-bin", default=os.environ.get("PYMOL_BIN"))
    parser.add_argument("--plip-bin", default=os.environ.get("PLIP_BIN"))
    parser.add_argument("--cnn-scoring", choices=("none", "rescore", "refinement", "all"), default="rescore")
    parser.add_argument("--cnn", default="crossdock_default2018")
    parser.add_argument("--exhaustiveness", type=int, default=16)
    parser.add_argument("--num-modes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--minimize", action="store_true")
    parser.add_argument("--score-only", action="store_true")
    parser.add_argument("--no-gpu", action="store_true", help="Pass --no_gpu to GNINA")
    parser.add_argument("--pose-state", type=int, default=1)
    parser.add_argument("--run-pymol", action="store_true")
    parser.add_argument("--run-plip", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.receptor, args.ligand, args.autobox_ligand):
        if path is not None and not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")
    if bool(args.center) != bool(args.size):
        raise ValueError("--center and --size must be provided together")
    if not args.autobox_ligand and not args.center:
        raise ValueError("Provide --autobox-ligand or both --center and --size")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    commands: list[list[str]] = []
    skill_dir = Path(__file__).resolve().parents[1]

    backend, command, backend_meta = find_gnina(
        args.gnina_bin, args.backend, skill_dir, args.docker_image,
        args.receptor, args.ligand, args.autobox_ligand, args.out_dir, args.docker_gpus,
    )
    append_gnina_inputs(command, backend, args.receptor, args.ligand, args.autobox_ligand, args.out_dir)
    # Some older GNINA CUDA builds still call cuInit even with --no_gpu.  On
    # WSL this can crash inside the DXGKRNL adapter bridge (exit code 139),
    # especially after a driver or WSL restart.  Hide CUDA explicitly when
    # CPU mode is selected so GNINA takes its stable CPU path from startup.
    if backend == "wsl" and args.no_gpu:
        command[2:2] = ["env", "CUDA_VISIBLE_DEVICES="]
    if not args.autobox_ligand:
        prefix = "" if backend != "wsl" else ""
        del prefix
        center_flags = ("--center_x", "--center_y", "--center_z")
        size_flags = ("--size_x", "--size_y", "--size_z")
        for flag, value in zip(center_flags, args.center):
            command.extend([flag, str(value)])
        for flag, value in zip(size_flags, args.size):
            command.extend([flag, str(value)])
    else:
        command.extend(["--autobox_add", str(args.autobox_add)])
    command.extend([
        "--cnn_scoring", args.cnn_scoring,
        "--cnn", args.cnn,
        "--exhaustiveness", str(args.exhaustiveness),
        "--num_modes", str(args.num_modes),
        "--seed", str(args.seed),
    ])
    if args.minimize:
        command.append("--minimize")
    if args.score_only:
        command.append("--score_only")
    if args.no_gpu:
        command.append("--no_gpu")
    run_command(command, args.out_dir / "gnina.log", commands)

    docked_sdf = args.out_dir / "docked.sdf"
    if not docked_sdf.is_file():
        raise FileNotFoundError(f"GNINA completed but did not create {docked_sdf}")
    ranking = write_rankings(docked_sdf, args.out_dir, skill_dir)
    runtime_python = find_runtime_python(skill_dir)
    complex_pdb = args.complex_pdb
    plip_visuals: dict[str, str] = {}
    receptor_pdb = args.receptor_pdb or (args.receptor if args.receptor.suffix.lower() == ".pdb" else None)
    if args.run_pymol:
        if not receptor_pdb:
            raise ValueError("--run-pymol requires a PDB receptor or --receptor-pdb")
        complex_pdb = args.out_dir / f"complex_pose{args.pose_state}.pdb"
        pml = args.out_dir / "build_complex.pml"
        pml.write_text(
            make_pymol_script(
                receptor_pdb, docked_sdf, complex_pdb,
                args.out_dir / f"complex_pose{args.pose_state}.pse",
                args.out_dir / f"complex_pose{args.pose_state}.png",
                args.pose_state,
            ),
            encoding="utf-8",
        )
        if args.pymol_bin:
            pymol_cmd = [resolve_executable(args.pymol_bin), "-cq", str(pml)]
        else:
            pymol_cmd = [runtime_python, str(Path(__file__).with_name("run_pymol.py")), "-cq", str(pml)]
        run_command(pymol_cmd, args.out_dir / "pymol.log", commands)

    if args.run_plip:
        if not complex_pdb or not complex_pdb.is_file():
            raise ValueError("--run-plip requires --complex-pdb or a successful --run-pymol stage")
        plip_dir = args.out_dir / f"plip_pose{args.pose_state}"
        plip_dir.mkdir(exist_ok=True)
        plip_cmd = [resolve_executable(args.plip_bin)] if args.plip_bin else [runtime_python, str(Path(__file__).with_name("run_plip.py"))]
        run_command(
            plip_cmd + ["-f", str(complex_pdb), "-o", str(plip_dir), "--txt", "--xml"],
            args.out_dir / "plip.log", commands,
        )
        plip_visuals = render_plip_local_view(
            complex_pdb, plip_dir, args.pose_state, runtime_python, commands, args.pymol_bin,
        )

    report_path = write_report(args.out_dir, args, backend, ranking, complex_pdb, plip_visuals)
    manifest = {
        "receptor": str(args.receptor.resolve()),
        "ligand": str(args.ligand.resolve()),
        "autobox_ligand": str(args.autobox_ligand.resolve()) if args.autobox_ligand else None,
        "center_angstrom": args.center,
        "size_angstrom": args.size,
        "autobox_add_angstrom": args.autobox_add if args.autobox_ligand else None,
        "backend": backend,
        **backend_meta,
        "cnn_scoring": args.cnn_scoring,
        "cnn_model": args.cnn,
        "exhaustiveness": args.exhaustiveness,
        "num_modes": args.num_modes,
        "seed": args.seed,
        "pose_state": args.pose_state,
        "docked_sdf": str(docked_sdf.resolve()),
        "ranking": ranking,
        "report": str(report_path.resolve()),
        "complex_pdb": str(complex_pdb.resolve()) if complex_pdb else None,
        **plip_visuals,
        "commands": commands,
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

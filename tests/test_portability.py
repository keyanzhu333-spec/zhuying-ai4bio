"""Offline regression tests using fresh directories and controlled runtimes."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(module, arguments):
    with patch.object(sys, "argv", [module.__file__, *map(str, arguments)]):
        return module.main()


class InstallationTests(unittest.TestCase):
    def test_install_all_is_self_contained_and_excludes_runtime(self):
        installer = load("scripts/install_skills.py")
        with tempfile.TemporaryDirectory(prefix="portable install ") as temporary:
            root = Path(temporary)
            source = root / "skill"
            source.mkdir()
            (source / "SKILL.md").write_text("test")
            for name in ("runtime", "runtime_pymol_whl", ".venv"):
                (source / name).mkdir()
                (source / name / "private").write_text("local-only")
            (source / ".env").write_text("local-only")
            with patch.object(installer, "SOURCES", {"zy-ai4bio": source}):
                self.assertEqual(main(installer, ["--target", root / "installed"]), 0)
            installed = root / "installed/zy-ai4bio"
            self.assertTrue((installed / "scripts/check_environment.py").is_file())
            self.assertTrue((installed / "assets/config/tools.example.env").is_file())
            self.assertFalse((installed / "runtime").exists())
            self.assertFalse((installed / ".env").exists())
            proc = subprocess.run([sys.executable, "-I", str(installed / "scripts/check_environment.py")],
                                  cwd=root, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_selected_screen_installs_dependency(self):
        installer = load("scripts/install_skills.py")
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(main(installer, ["--target", temporary, "--skills", "ppi-vscreen"]), 0)
            self.assertTrue((Path(temporary) / "lightdock/SKILL.md").is_file())
            with self.assertRaises(SystemExit):
                main(installer, ["--target", temporary, "--skills", "ppi-vscreen"])

    def test_environment_invalid_override_is_not_ready(self):
        module = load("scripts/check_environment.py")
        with patch.dict(os.environ, {"GMX_BIN": "nonexistent-zy-test-command"}):
            self.assertFalse(module.resolve_command(("GMX_BIN",), ("gmx",))["available"])

    def test_update_keeps_backup_and_local_resources(self):
        installer = load("scripts/install_skills.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / "source", root / "installed"
            source.mkdir()
            (source / "SKILL.md").write_text("new version")
            old = target / "example"
            (old / "runtime").mkdir(parents=True)
            (old / "runtime/engine").write_text("local executable")
            (old / ".env").write_text("private configuration")
            (old / "SKILL.md").write_text("old version")
            with patch.object(installer, "SOURCES", {"example": source}):
                self.assertEqual(main(installer, ["--target", target, "--update"]), 0)
            self.assertEqual((old / "SKILL.md").read_text(), "new version")
            self.assertEqual((old / "runtime/engine").read_text(), "local executable")
            self.assertEqual((old / ".env").read_text(), "private configuration")
            backup = next((root / "skill-backups").iterdir()) / "example"
            self.assertEqual((backup / "SKILL.md").read_text(), "old version")
            self.assertTrue((backup / "runtime/engine").is_file())
            self.assertEqual(json.loads((old / ".zy-ai4bio-install.json").read_text())["skill"], "example")

    def test_failed_update_rolls_back_all_skills(self):
        installer = load("scripts/install_skills.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, target = {}, root / "installed"
            for name in ("a", "b"):
                source = root / "source" / name
                source.mkdir(parents=True)
                (source / "SKILL.md").write_text("new")
                old = target / name
                old.mkdir(parents=True)
                (old / "SKILL.md").write_text("old")
                sources[name] = source
            rename = Path.rename

            def fail_second(path, destination):
                if path.name == "b" and path.parent.name.startswith(".zy-ai4bio-update-"):
                    raise OSError("simulated installation failure")
                return rename(path, destination)

            with patch.object(installer, "SOURCES", sources), patch.object(Path, "rename", fail_second):
                with self.assertRaises(OSError):
                    main(installer, ["--target", target, "--update"])
            for name in sources:
                self.assertEqual((target / name / "SKILL.md").read_text(), "old")


class RuntimeTests(unittest.TestCase):
    def test_chai_output_is_empty_at_launch(self):
        module = load("skills/chai1-complex/scripts/run_chai1.py")
        with tempfile.TemporaryDirectory(prefix="space ' case ") as temporary:
            root = Path(temporary)
            fasta, output = root / "input.fasta", root / "prediction"
            fasta.write_text(">protein|A\nACDEFGHIK\n")

            def run(command, **kwargs):
                self.assertFalse(output.exists() and any(output.iterdir()))
                self.assertIn(str(fasta), command)
                output.mkdir(exist_ok=True)
                (output / "model.cif").write_text("mock model")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(module.subprocess, "run", side_effect=run):
                self.assertEqual(main(module, ["--input", fasta, "--out-dir", output,
                                               "--chai", sys.executable]), 0)
            self.assertTrue((output / "run_record.json").is_file())
            self.assertTrue(output.with_name(output.name + ".chai1.log").is_file())

    def test_haddock_command_resolves_before_cwd_change(self):
        module = load("skills/haddock3-nucleic-acid/scripts/run_haddock3.py")
        self.assertTrue(Path(module.command_prefix(sys.executable, "unused")[0]).is_absolute())
        with self.assertRaises(SystemExit):
            module.command_prefix("nonexistent-zy-haddock", "unused")

    def test_reverse_preflight_receives_override(self):
        module = load("skills/reverse-target-vscreen/scripts/run_reverse_screen.py")
        with patch.object(module, "run_command", return_value=subprocess.CompletedProcess([], 0, '{"core_ready":true}')) as run:
            self.assertTrue(module.run_preflight("custom udp")["core_ready"])
            self.assertEqual(run.call_args.args[0][-2:], ["--udp", "custom udp"])

    def test_plip_handles_quote_in_filename_without_shell(self):
        module = load("skills/diffdock/scripts/analyze_interactions.py")
        with patch.object(module.shutil, "which", return_value=sys.executable):
            with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
                module.run_in_plip_env(["obabel", "a'b ligand.sdf", "-O", "out.pdb"])
                self.assertEqual(run.call_args.args[0][1], "a'b ligand.sdf")
                self.assertNotIn("shell", run.call_args.kwargs)

    def test_igfold_accepts_long_literal_sequence(self):
        module = load("skills/igfold/scripts/predict_fab.py")
        sequence = "ACDEFGHIKLMNPQRSTVWY" * 30
        self.assertEqual(module.read_sequence(sequence), sequence)


class MDTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="md portable ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = self.root / "case"
        self.source = self.root / "input.pdb"
        self.source.write_text("END\n")
        self.initializer = load("skills/gromacs-md/scripts/init_md_case.py")
        self.runner = load("skills/gromacs-md/scripts/run_md_stages.py")
        main(self.initializer, ["--scenario", "single-protein", "--input", self.source,
                               "--out-dir", self.case])
        self.system = self.case / "simulation/system"
        (self.system / "topol.top").write_text('#include "local.itp"\n')
        (self.system / "local.itp").write_text("; test include\n")
        (self.system / "system.gro").write_text("mock coordinates\n")
        self.calls = []

    def fake_gmx(self, command, **kwargs):
        self.calls.append(command)
        self.assertEqual(kwargs["cwd"], self.system)
        if command[1] == "grompp":
            Path(command[command.index("-o") + 1]).write_text("compiled tpr")
        elif command[1] == "mdrun":
            stem = Path(command[command.index("-deffnm") + 1])
            stem.with_suffix(".gro").write_text("output coordinates")
            stem.with_suffix(".cpt").write_text("checkpoint")
        return subprocess.CompletedProcess(command, 0)

    def execute(self, *args):
        with patch.object(self.runner.subprocess, "run", side_effect=self.fake_gmx):
            return main(self.runner, ["--project", self.case, "--gmx", sys.executable, *args])

    def test_stage_progression_and_resume_dont_rebuild_tpr(self):
        self.execute("--from-stage", "em")
        self.execute("--from-stage", "nvt")
        self.execute("--from-stage", "npt")
        self.calls.clear()
        self.execute("--from-stage", "production", "--approve-production")
        self.assertEqual([call[1] for call in self.calls], ["grompp", "mdrun"])
        self.assertIn("-nb", self.calls[-1])
        self.assertEqual(self.calls[-1][self.calls[-1].index("-nb") + 1], "cpu")
        self.calls.clear()
        self.execute("--from-stage", "production", "--approve-production", "--resume")
        self.assertEqual([call[1] for call in self.calls], ["mdrun"])
        self.assertIn("-cpi", self.calls[0])
        (self.system / "local.itp").write_text("changed topology")
        with self.assertRaises(SystemExit):
            self.execute("--from-stage", "production", "--approve-production", "--resume")

    def test_existing_stage_and_unapproved_production_are_rejected(self):
        self.execute("--from-stage", "em")
        with self.assertRaises(SystemExit):
            self.execute("--from-stage", "em")
        with self.assertRaises(SystemExit):
            self.execute("--from-stage", "production")

    def test_dry_run_does_not_write(self):
        before = sorted(str(p) for p in self.case.rglob("*"))
        self.execute("--through", "npt", "--dry-run")
        self.assertEqual(before, sorted(str(p) for p in self.case.rglob("*")))
        self.assertFalse(self.calls)

    def test_bad_parameter_rejected_before_directory_creation(self):
        with self.assertRaises(SystemExit):
            main(self.initializer, ["--scenario", "single-protein", "--input", self.source,
                                   "--out-dir", self.root / "bad", "--temperature", "nan"])
        self.assertFalse((self.root / "bad").exists())


class PrivacyTests(unittest.TestCase):
    def test_package_version_is_not_a_host_ip(self):
        scanner = load("scripts/check_portability.py")
        version = ".".join(("3", "2", "0", "1"))
        self.assertFalse(list(scanner.scan_text("pip install example-wheel==" + version)))
        host = ".".join(("192", "168", "10", "20"))
        self.assertTrue(list(scanner.scan_text("SERVER_IP=" + host)))

    def test_detector_does_not_print_secrets(self):
        scanner = load("scripts/check_portability.py")
        private = "/".join(["", "home", "example-user", "project"])
        findings = list(scanner.scan_text(private + "\n" + "ghp_" + "a" * 30))
        self.assertEqual(len(findings), 2)
        self.assertNotIn(private, str(findings))


if __name__ == "__main__":
    unittest.main()

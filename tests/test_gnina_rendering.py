"""Offline checks of the overview renderer's PyMOL commands."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class OverviewTests(unittest.TestCase):
    def test_overview_has_no_annotations_and_keeps_selected_state(self):
        path = (Path(__file__).resolve().parents[1] / "skills/gnina-dock"
                / "scripts/run_gnina_pipeline.py")
        spec = importlib.util.spec_from_file_location("gnina_render_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cmd = Mock()
        pymol = types.ModuleType("pymol")
        pymol.cmd = cmd
        script = module.make_pymol_script(
            Path("receptor.pdb"), Path("poses.sdf"), Path("complex.pdb"),
            Path("overview.pse"), Path("overview.png"), 3)
        with patch.dict(sys.modules, {"pymol": pymol}):
            exec(compile(script, "overview.py", "exec"), {})
        cmd.create.assert_called_once_with(
            "complex_struct", "receptor or ligand_poses", 3, 1)
        for command in ("label", "pseudoatom", "load_cgo", "distance"):
            getattr(cmd, command).assert_not_called()
        cmd.hide.assert_any_call("labels", "all")
        cmd.show.assert_any_call("cartoon", "complex_struct and polymer")
        cmd.show.assert_any_call("sticks", "ligand_local")
        cmd.show.assert_any_call("sticks", "contact_residues")
        cmd.ray.assert_called_once_with(2400, 1800)
        cmd.save.assert_any_call(Path("overview.pse").resolve().as_posix())


if __name__ == "__main__":
    unittest.main()

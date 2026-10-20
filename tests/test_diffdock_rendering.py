"""Exercise both DiffDock entrypoints without an API key or a PyMOL install."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


class DiffDockOverviewTests(unittest.TestCase):
    def test_overview_discards_plip_annotations_and_pocket_sticks(self):
        for relative in ("skills/diffdock/scripts/analyze_interactions.py",
                         "scripts/analyze_interactions.py"):
            with self.subTest(entrypoint=relative), tempfile.TemporaryDirectory() as directory:
                spec = importlib.util.spec_from_file_location("diffdock_render_test", ROOT / relative)
                module = importlib.util.module_from_spec(spec)
                with patch.object(sys, "path", list(sys.path)):
                    spec.loader.exec_module(module)
                root = Path(directory)
                (root / "UNL_Z_1.pse").touch()
                complex_pdb = root / "complex.pdb"
                complex_pdb.write_text("END\n")
                cmd = Mock()
                pymol = types.ModuleType("pymol")
                pymol.cmd, pymol.cgo = cmd, Mock()
                script_calls = []

                def run(command, cwd):
                    script = (Path(cwd) / "_pymol_render.py").read_text()
                    with patch.dict(sys.modules, {"pymol": pymol}):
                        exec(compile(script, "render.py", "exec"), {})
                    script_calls.extend(cmd.mock_calls)
                    for name in ("interaction_bindingsite.png", "complex_overview.png"):
                        (root / name).write_bytes(b"rendered")
                    return subprocess.CompletedProcess(command, 0, "", "")

                labels = ("cmd.pseudoatom('callout_1', label='LYS 1')\n"
                          "cmd.show('sticks', 'contact_residues')\n")
                with patch.object(module, "run_in_plip_env", side_effect=run), \
                        patch.object(module, "_parse_interacting_residues", return_value=["LYS1"]), \
                        patch.object(module, "_build_label_commands", return_value=labels):
                    self.assertTrue(module.run_pymol_visualization(str(complex_pdb), directory))
                split = next(i for i, c in enumerate(script_calls)
                             if c == unittest.mock.call.delete("all"))
                before, after = script_calls[:split], script_calls[split + 1:]
                self.assertIn(unittest.mock.call.save("interaction_bindingsite.pse"), before)
                self.assertIn(unittest.mock.call.pseudoatom("callout_1", label="LYS 1"), before)
                self.assertIn(unittest.mock.call.load("complex.pdb", "complex_struct"), after)
                self.assertIn(unittest.mock.call.hide("everything", "all"), after)
                self.assertIn(unittest.mock.call.hide("labels", "all"), after)
                self.assertIn(unittest.mock.call.save("complex_overview.pse"), after)
                shown = [c for c in after if c[0] == "show"]
                self.assertEqual(shown, [
                    unittest.mock.call.show("cartoon", "complex_struct and polymer"),
                    unittest.mock.call.show("sticks", "ligand_local")])
                self.assertFalse(any(c[0] in {"label", "pseudoatom", "distance", "load_cgo"}
                                     for c in after))


if __name__ == "__main__":
    unittest.main()

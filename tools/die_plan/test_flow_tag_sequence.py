"""Flow release sequences remain valid after z (aa, ab, ...)."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class FlowSequenceTest(unittest.TestCase):
    def test_release_parsers_and_manifest(self):
        spec = importlib.util.spec_from_file_location("resign_sequence_test", ROOT / "tools/die_plan/resign.py")
        resign = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resign)
        tree = ast.parse((ROOT / "tools/autopilot/autopilot.py").read_text())
        selected = [n for n in tree.body if
                    isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("FLOW_TAG_RE", "DIE_FLOW_TAG") for t in n.targets)
                    or isinstance(n, ast.FunctionDef) and n.name == "tag_covers"]
        ns = {"re": re}
        exec(compile(ast.Module(body=selected, type_ignores=[]), "autopilot tag policy", "exec"), ns)
        with tempfile.TemporaryDirectory() as d:
            manifest = Path(d) / "tag.json"
            for seq in ("a", "z", "aa", "ah", "abc"):
                for suffix in ("", "-qc", "-s81", "-head", "-kv", "-hbm"):
                    tag = "flow-20261106-" + seq + suffix
                    manifest.write_text(json.dumps({"schema": resign.MANIFEST_SCHEMA, "tag": tag, "commit": "a" * 40}))
                    self.assertEqual(resign.tag_commit(str(manifest), tag), "a" * 40)
                    self.assertTrue(ns["tag_covers"](tag))
                    self.assertEqual(ns["tag_covers"](tag, "hbm"), suffix in ("", "-hbm"))
            for tag in ("flow-20261106-", "flow-20261106-AH", "flow-20261106-a1", "flow-20261106-ah-other", "flow-2026116-ah", "xflow-20261106-ah"):
                with self.assertRaises(resign.ResignError):
                    resign.tag_commit(str(manifest), tag)
                self.assertFalse(ns["tag_covers"](tag))

if __name__ == "__main__":
    unittest.main()

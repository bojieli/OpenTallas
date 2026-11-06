"""The generation-only option is captured before later LEC/async identity reads."""
import ast
import importlib.util
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent
KEY = "OT_LEC_SLANG_UNROLL_LIMIT"
tree = ast.parse((ROOT / "gen_phys.py").read_text())
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_lec_frontend_vars")
namespace = {"os": os, "re": re}
exec(compile(ast.Module(body=[node], type_ignores=[]), "gen_phys.py", "exec"), namespace)
capture = namespace[node.name]
spec = importlib.util.spec_from_file_location("lec", ROOT / "lec.py")
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)

class GenCaptureTests(unittest.TestCase):
    def test_default_and_invalid_match_reader(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(capture(), [])
        for value in ("0", "-1", "unlimited", "2.5", "1 --ignore-assertions", ""):
            with self.subTest(value=value), patch.dict(os.environ, {KEY: value}, clear=True):
                with self.assertRaises(ValueError):
                    capture()
                with self.assertRaises(lec.LecError):
                    lec.slang_unroll_args({})

    def test_gen_env_survives_without_runtime_env(self):
        with patch.dict(os.environ, {KEY: "32912"}, clear=True):
            lines = capture()
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {}, clear=True):
            (Path(d) / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = rtl/top.sv\n" + "\n".join(lines) + "\n")
            self.assertEqual(lec.slang_unroll_args(lec.parse_config(d)), ["--unroll-limit=32912"])

    def test_actual_partition_cfg_uses_capture(self):
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "cfg" for t in n.targets)
                 and isinstance(n.value, ast.List)
                 and any(isinstance(e, ast.Starred) and isinstance(e.value, ast.Call)
                         and isinstance(e.value.func, ast.Name) and e.value.func.id == "_lec_frontend_vars"
                         for e in n.value.elts)]
        self.assertEqual(len(calls), 1)
        self.assertIn("partition type", "".join(n.value for n in ast.walk(calls[0].value.elts[0])
                                                if isinstance(n, ast.Constant) and isinstance(n.value, str)))

if __name__ == "__main__":
    unittest.main()

"""KW-FIX-46 11-12 (COORD class 'No module named bind_elab' @kit_rtl): the src probe checks the import closure of
tools/die_plan/bind.py on each gen host and reports an unresolved module as a package problem of the tree"""
import os, subprocess, tempfile, unittest
from pathlib import Path
import kit_wave as K


def probe(tree):
    cmd = K._src_probe_cmd([str(tree)], [])
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout


class ImportProbe(unittest.TestCase):
    def mk(self, sibling=True):
        t = Path(tempfile.mkdtemp())
        dp = t / "tools" / "die_plan"
        dp.mkdir(parents=True)
        (dp / "bind.py").write_text("import json\nimport sys\ntry:\n    import nosuch_opt\nexcept ImportError:\n    pass\n"
                                    "import bind_elab as E\n")
        if sibling:
            (dp / "bind_elab.py").write_text("import os\nimport bind_util\n")
            (t / "tools" / "bind_util.py").write_text("import re\n")
        return t

    def test_complete_tree_clean(self):
        out = probe(self.mk(True))
        self.assertNotIn(" import ", out)

    def test_missing_sibling_reported(self):
        t = self.mk(False)
        out = probe(t)
        self.assertIn(f"P {t} import bind_elab", out)

    def test_missing_second_level(self):
        t = self.mk(True)
        (t / "tools" / "bind_util.py").unlink()
        self.assertIn(f"P {t} import bind_util", probe(t))


if __name__ == "__main__":
    unittest.main()

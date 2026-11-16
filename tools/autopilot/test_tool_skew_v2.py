import json
import tempfile
import unittest
from pathlib import Path
import tool_skew as TS

PIN = "a" * 40


def mk(root, files, main_sha=None):
    for rel, body in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    if main_sha:
        m = {k: TS.hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}
        (Path(root) / ".src-manifest.json").write_text(json.dumps({"main_sha": main_sha, "files": m, "version": 1}))


class V2(unittest.TestCase):
    def run_check(self, tree_files, main_sha):
        t = tempfile.mkdtemp(); rt = tempfile.mkdtemp()
        mk(t, tree_files, main_sha)
        ref = {"tools/a.py": TS.hashlib.sha256(b"A").hexdigest()}
        (Path(rt) / (PIN[:12] + ".manifest.json")).write_text(json.dumps({"files": ref}))
        return TS.check_die("d", t, t, tools_sha=PIN, rt_root=rt, strict=True)

    def test_v2_tree_with_extra_main_files_is_clean(self):
        r = self.run_check({"tools/a.py": "A", **{f"tools/x{i}.py": "x" for i in range(50)}}, PIN)
        self.assertTrue(r["ok"], r["refused"])

    def test_v2_tree_real_edit_of_a_baseline_file_is_reported(self):
        r = self.run_check({"tools/a.py": "EDITED", "tools/x.py": "x"}, PIN)
        self.assertEqual(r["refused"], {"tools/a.py": "differ"})

    def test_v1_tree_without_marker_keeps_only_die_detection(self):
        r = self.run_check({"tools/a.py": "A", "tools/x.py": "x"}, None)
        self.assertEqual(r["refused"], {"tools/x.py": "only_die"})

    def test_marker_for_another_main_is_not_trusted(self):
        r = self.run_check({"tools/a.py": "A", "tools/x.py": "x"}, "b" * 40)
        self.assertEqual(r["refused"], {"tools/x.py": "only_die"})

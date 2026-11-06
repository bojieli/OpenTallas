"""Real Git regressions for the rootctl pin failure and split-core files_at override."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import source_history as H


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "test")

    def tearDown(self):
        self.tmp.cleanup()

    def run_git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args]).decode().strip()

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, *names):
        self.run_git("add", "--", *names)
        self.run_git("commit", "-qm", "fixture")
        return self.run_git("rev-parse", "HEAD")

    def test_original_pin_and_later_per_file_override_survive_main_only_stage(self):
        self.write("rtl/old.sv", "module old; wire golden; endmodule\n")
        old = self.commit("rtl/old.sv")
        self.run_git("checkout", "-q", "--orphan", "staged-main")
        self.write("rtl/old.sv", "module old; wire different; endmodule\n")
        self.write("rtl/split.sv", "module split; old u_old(); endmodule\n")
        split = self.commit("rtl/old.sv", "rtl/split.sv")
        recipe = {"core": {"files": ["rtl/old.sv", "rtl/split.sv"], "read_at_commit": True,
                           "source_commit": old, "files_at": {"rtl/split.sv": split}}}
        self.write("physical/die_plan/hbm/recipes.json", json.dumps(recipe))
        tip = self.commit("physical/die_plan/hbm/recipes.json")
        expected = {old: ["rtl/old.sv"], split: ["rtl/split.sv"]}
        self.assertEqual(H.collect_pins(self.repo), expected)
        self.assertEqual(H.collect_pins(self.repo, tip), expected)
        report = H.pack_history(self.repo, self.repo, self.root / "packs", tip)
        self.assertEqual(report["missing"], [])
        target = self.root / "staged"
        subprocess.run(["git", "clone", "-q", "--no-local", "--single-branch", "--branch", "staged-main",
                        str(self.repo), str(target)], check=True)
        absent = subprocess.run(["git", "-C", str(target), "cat-file", "-e", old + "^{commit}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertNotEqual(absent.returncode, 0)  # historical recipe pin was outside fetched main
        H.install_pack(target, report["pack"])
        self.assertEqual(H.git(target, "show", old + ":rtl/old.sv"),
                         b"module old; wire golden; endmodule\n")
        self.assertEqual(H.git(target, "show", split + ":rtl/split.sv"),
                         b"module split; old u_old(); endmodule\n")
        self.assertEqual(H.git(target, "rev-parse", "HEAD").decode().strip(), tip)
        self.assertIn("different", (target / "rtl/old.sv").read_text())
        before = Path(report["pack"]).stat().st_mtime_ns
        again = H.pack_history(self.repo, self.repo, self.root / "packs", tip)
        self.assertEqual(again["identity"], report["identity"])
        self.assertEqual(Path(report["pack"]).stat().st_mtime_ns, before)

    def test_missing_historical_commit_never_substitutes_current_rtl(self):
        self.write("rtl/current.sv", "module current; endmodule\n")
        self.commit("rtl/current.sv")
        recipe = {"core": {"files": ["rtl/current.sv"], "read_at_commit": True,
                           "source_commit": "0" * 40}}
        self.write("physical/die_plan/hbm/recipes.json", json.dumps(recipe))
        report = H.pack_history(self.repo, self.repo, self.root / "packs")
        self.assertIsNone(report["pack"])
        self.assertEqual(report["missing"], [{"pin": "0" * 40,
                                               "reason": "historical commit unavailable"}])
        self.assertNotIn("verdict", report)  # source availability is not another sign-off gate


if __name__ == "__main__":
    unittest.main()

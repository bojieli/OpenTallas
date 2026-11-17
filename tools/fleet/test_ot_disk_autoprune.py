import json, os, pathlib, sys, tempfile, time, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ot_disk_autoprune as m


class AutoPrune(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp()).resolve(); self.root = self.t / "kw45"; self.root.mkdir(); self.md = self.t / "mk"; self.md.mkdir()
        for n in ("src_qc_pin_0a0b0c0d0e", "src_qc_pin_ee2ee2ee2", "src_kv_pin_ee2ee2ee2", "src_s81_pin_a1a1a1a1a1", "src_s81_main_x"):
            (self.root / n).mkdir(); (self.root / n / "f").write_text("x"); os.utime(self.root / n / "f", (time.time() - 90000,) * 2)
        def mk(die, tree, sha, age):
            p = self.md / f"tree_switch_{die}.json"; p.write_text(json.dumps({"die": die, "tree": str(self.root / tree), "tools_sha": sha})); os.utime(p, (time.time() - age,) * 2)
        mk("qwen_compute", "src_qc_pin_ee2ee2ee2", "ee2ee2ee2", 100); mk("qwen_kvsys", "src_kv_pin_ee2ee2ee2", "ee2ee2ee2", 100)    # s81 has no marker yet

    def test_superseded_only_when_die_has_newer_marker(self):
        s = [os.path.basename(x) for x in m.superseded(str(self.root), str(self.md))]
        self.assertEqual(s, ["src_qc_pin_0a0b0c0d0e"])                          # v1 s81 stays (no v2 marker), mains and current stay

    def test_verdicts(self):
        t = str(self.root / "src_qc_pin_0a0b0c0d0e")
        self.assertIsNone(m.verdict(t, "", set()))
        self.assertIn("live process", m.verdict(t, "x " + t + "/f y", set()))
        self.assertIn("referenced", m.verdict(t, "", {t + "/f"}))
        os.utime(t + "/f", None)
        self.assertIn("mtime", m.verdict(t, "", set()))
        link = self.t / "lnk"; link.symlink_to(t)
        self.assertIn("symlink", m.verdict(str(link), "", set()))

    def test_apply_deletes_only_cleared(self):
        refs = self.t / "refs.txt"; refs.write_text("")
        m.main(["apply", "--markers", str(self.md), "--refs", str(refs), "--root", str(self.root)])
        self.assertFalse((self.root / "src_qc_pin_0a0b0c0d0e").exists())
        self.assertTrue((self.root / "src_qc_pin_ee2ee2ee2").exists() and (self.root / "src_s81_pin_a1a1a1a1a1").exists())

    def test_trigger_noop_when_disk_free(self):
        self.assertEqual(m.main(["trigger", "--markers", str(self.md), "--root", str(self.root), "--below", "0", "--lock", str(self.t / "l")]), 0)
        self.assertTrue((self.root / "src_qc_pin_0a0b0c0d0e").exists())


if __name__ == "__main__":
    unittest.main()

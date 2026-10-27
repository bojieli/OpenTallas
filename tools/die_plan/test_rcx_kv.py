"""CLOCK-KV-R12: rcx_kv.py on a tiny synthetic build (one shared opposite-drop net) emits one VIA89 per shared root,
both drop pins and the ndr016 extraction, with the default (repo) tool dir."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent


class RcxKv(unittest.TestCase):
    def test_tiny_build(self):
        with tempfile.TemporaryDirectory() as d:
            b, o = Path(d) / "b", Path(d) / "o"
            b.mkdir()
            w = dict(name="ckm_w_n", drv="u", loads=["a", "c"], horiz=True, trunk_tap=[10.81, 21.249],
                     branches=[["a", 60., 10.395], ["c", 60., 30.375]],
                     segs=[["M8", 10.81, 21.249, 60., 21.249], ["M9", 60., 10.395, 60., 21.249],
                           ["M9", 60., 21.249, 60., 30.375]])
            (b / "mesh.json").write_text(json.dumps(dict(meta=dict(root_um=[0, 0]), taps=[], fixed_wires=[w])))
            (b / "place.json").write_text(json.dumps({"u": {"x": 10., "y": 20.25}, "a": {"x": 59., "y": 10.26},
                                                       "c": {"x": 59., "y": 30.24}}))
            r = subprocess.run([sys.executable, str(HERE / "rcx_kv.py"), str(b), str(o)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            t = (o / "rcx.tcl").read_text()
            self.assertEqual(t.count("set jd0 [$e addTechVia [V VIA89]]"), 1)
            self.assertIn("addITerm [IT a A]", t)
            self.assertIn("addITerm [IT c A]", t)
            self.assertIn("-ext_model_file /out/rcx_ndr.rules -lef_res", t)
            self.assertEqual((o / "rcx_nets.txt").read_text().split(), ["ckm_w_n"])


if __name__ == "__main__":
    unittest.main()

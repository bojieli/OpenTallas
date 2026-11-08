"""S81-LEAF5-1 11-08: leaf_facing.py vn field step.  Fixture = plan type ot_s81sl_leaf__t5 of the e9eda32d41c wave plan
(hard cores + outline; FT bit sites reduced to one point per 8.64-um site cell).  t5 a3 overflowed GRT (17610) in the
15.1-um vn_b / VP channel; the step moves the vn pair + ve_s + ve_m + vs 86.4 um east (field 101.52 um)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "leaf_facing_t5_fixture.json"


def run(plan, typ="ot_s81sl_leaf__t5"):
    return json.loads(subprocess.check_output([sys.executable, "-I", str(HERE / "leaf_facing.py"), str(plan), typ]))


class VnField(unittest.TestCase):
    def test_t5_field(self):
        d = run(FIX)
        self.assertEqual(d["vn_field"]["dx"], 86.4)
        self.assertEqual(d["vn_field"]["gap"], 101.52)
        self.assertEqual(sorted(d["vn_field"]["group"]), ["u_ve.u_m", "u_ve.u_s", "u_vn.u_a", "u_vn.u_b", "u_vs"])
        m = d["moves"]
        self.assertEqual(m["u_lf.u_vn.u_b"], [397.44, 34.56])
        self.assertEqual(m["u_lf.u_vn.u_a"], [397.44, 596.16])
        self.assertEqual(m["u_lf.u_ve.u_s"], [768.96, 43.2])
        self.assertEqual(m["u_lf.u_ve.u_m"], [950.4, 51.84])
        self.assertEqual(m["u_lf.u_vs"], [907.2, 414.72])
        self.assertEqual(m["u_lf.u_vq"], [639.36, 432.0])
        self.assertEqual(m["u_lf.u_vsw"], [794.88, 596.16])
        self.assertFalse(any("u_vp" in k for k in m))

    def test_wide_channel_untouched(self, tmp=None):
        import tempfile
        p = json.loads(FIX.read_text()); t = p["partition_types"]["ot_s81sl_leaf__t5"]
        # move the whole VP column 60 um west-free: vn_b already >= 24 um from the column -> no vn field step
        for h in t["hard_cores"]:
            if h["inst"].startswith("u_lf.u_vn."):
                h["origin_um"][0] += 34.56
        for h in t["hard_cores"]:
            if h["inst"] in ("u_lf.u_ve.u_s", "u_lf.u_ve.u_m", "u_lf.u_vs"):
                h["origin_um"][0] += 86.4
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(p, f)
        d = run(f.name)
        Path(f.name).unlink()
        self.assertIsNone(d["vn_field"])


if __name__ == "__main__":
    unittest.main()

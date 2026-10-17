#!/usr/bin/env python3
"""Q-CLUSTER 2026-10-17 (coordinator decision): opt-in TWO-LEVEL cluster layer contract ("cluster_level": 2) -- children
are clusters (PG <= M7), the cluster's PG = M8 stripes aligned to the die M8 grid, signals M2-M7, die M9.  One-level
kits are unchanged (also proven byte-identical on 22 regenerated kits: results/arch/qwen_cluster_1017/kit_identity.json)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ref_tile as RT  # noqa: E402

SPEC = RT.ROOT / "tools/ref_tile/specs_qcluster/qfd_c_b16_dv_diag.json"


def gen(mut=None):
    d = json.loads(SPEC.read_text())
    if mut:
        mut(d)
    tmp = SPEC.parent / f"_cl2_test_{id(d)}.json"
    tmp.write_text(json.dumps(d))
    try:
        out = Path(tempfile.mkdtemp())
        r = RT.gen(str(tmp), out_root=out)
        return out / r["kit"]
    finally:
        tmp.unlink()


class ClusterLevel2(unittest.TestCase):
    def test_level2_pdn_and_layers(self):
        kd = gen()
        try:
            pdn = (kd / "pdn.tcl").read_text()
            self.assertIn("-layer {M8} -width {0.48} -pitch {8.64}", pdn)
            self.assertIn("add_pdn_connect -grid {top} -layers {M7 M8}", pdn)
            self.assertIn("-pins {M8}", pdn)
            self.assertIn("add_pdn_connect -grid {hard_m7} -layers {M7 M8}", pdn)   # children (PG M7) strapped from M8
            env = (kd / "kit.env").read_text()
            self.assertIn("RLAYERS='M2 M7'", env)
        finally:
            shutil.rmtree(kd.parent, ignore_errors=True)

    def test_level1_cluster_refuses_m7_children(self):
        with self.assertRaises(RT.SpecError):
            gen(lambda d: d.pop("cluster_level"))

    def test_bad_level_and_tile_level2(self):
        with self.assertRaises(RT.SpecError):
            RT.cluster_level({"kind": "cluster", "cluster_level": 3})
        with self.assertRaises(RT.SpecError):
            RT.cluster_level({"kind": "tile", "cluster_level": 2})
        self.assertEqual(RT.cluster_level({"kind": "cluster"}), 1)

    def test_hold_budget_die_cluster_needs_level2(self):
        s = {"kind": "cluster", "hold_budget": "die", "pin_regs": {"enable": False, "reason": "rtl registers every pin"}}
        with self.assertRaises(RT.SpecError):
            RT.check_hold_budget(s)
        RT.check_hold_budget(dict(s, cluster_level=2))
        with self.assertRaises(RT.SpecError):
            RT.check_hold_budget(dict(s, cluster_level=2, inhold=True))


if __name__ == "__main__":
    unittest.main()

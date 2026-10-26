"""COORD 2026-10-26 05:42 CPPR ruling: mesh node = common point only when the regional mesh is one connected net."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as DM  # noqa: E402
import die_clock as DC  # noqa: E402


def _mesh(vias=None):
    M = {"meta": {"regions": [dict(k=0, i0=0, i1=4, j0=0, j1=3), dict(k=1, i0=4, i1=8, j0=0, j1=3)]}}
    if vias is not None:
        M["meta"]["mesh_vias"] = vias
    return M


class MeshConnected(unittest.TestCase):
    def test_no_vias_no_credit(self):
        self.assertEqual(DM.mesh_connected(_mesh()), {0: False, 1: False})

    def test_meta_vias_need_every_crossing(self):
        self.assertEqual(DM.mesh_connected(_mesh({"0": 12, "1": 11})), {0: True, 1: False})

    def test_db_count_from_combo_log_required_when_dir_given(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "combo_TT.log").write_text(f"OT_MESH_VIAS {DM.mesh_net(0)} 12\nOT_MESH_VIAS {DM.mesh_net(1)} 3\n")
            self.assertEqual(DM.mesh_connected(_mesh({"0": 12, "1": 12}), d), {0: True, 1: False})
            (d / "combo_FF.log").write_text(f"OT_MESH_VIAS {DM.mesh_net(0)} 0\n")   # min over corners
            self.assertEqual(DM.mesh_connected(_mesh({"0": 12, "1": 12}), d)[0], False)

    def test_credit_never_exceeds_tap_range(self):
        # stub-input range 98 ps, the tap's own late-early only 90: downstream stub range is never credited
        r = DC.pair_clock_damage(7500.0, 7410.0, 7480.0, 7390.0, 98.0)
        self.assertAlmostEqual(r["cppr_credit_ps"], 90.0)
        self.assertAlmostEqual(r["max_damage_ps"], 20.0)


if __name__ == "__main__":
    unittest.main()

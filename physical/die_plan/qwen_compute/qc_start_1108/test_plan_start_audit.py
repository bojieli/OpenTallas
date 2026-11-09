"""DIE-QC-97 11-09: plan_start.start_need / audit flag every type whose one-cycle START broadcast cannot close
(sle_hc0__cl05696ed1 G2 setup_tt -157.31: u_cland_origin -> u_cland_rsf_i ring across ~1.4 mm, no START transport)."""
import importlib.util, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("plan_start_dq97", HERE / "plan_start.py")
PS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PS)


def typ(bands, pins, outline=(622.08, 1339.2)):
    return {"outline_um": list(outline), "clock": {"landing_contract": {
        "bands": {b: {"rect_um": r} for b, r in bands.items()},
        "pins": [{"name": n, "xy_um": list(xy)} for n, xy in pins.items()]}}}


# hc0 geometry from plan_qc53v4w (bands) and io.tcl (tstart pin)
HC0 = typ({"rsf_i": [515.888, 1270.08, 604.8, 1321.92], "rsn_i": [17.28, 1270.08, 105.28, 1321.92],
           "x_hc1_i": [442.8, 182.832, 527.04, 191.472], "x_hc1_st_a_i": [552.96, 188.304, 604.8, 277.76]},
          {"cland_tstart_in": (158.176, 167.392)})


class StartNeed(unittest.TestCase):
    def test_hc0_far_rings_need_reader_start(self):
        n = PS.start_need(HC0, ["rsf_i", "rsn_i", "x_hc1_i", "x_hc1_st_a_i"], [], "strap")
        self.assertTrue(n["one_cycle_impossible"])
        self.assertGreater(n["one_cycle_lower_bound_um"], 405)
        self.assertGreaterEqual(n["reader_depth"], 3)
        self.assertEqual(n["writer_depth"], 0)

    def test_compact_rings_need_nothing(self):
        t = typ({"a_i": [17.28, 17.28, 60, 60], "b_i": [80, 17.28, 120, 60]}, {"cland_tstart_in": (50, 100)})
        n = PS.start_need(t, ["a_i", "b_i"], [], "strap")
        self.assertFalse(n["one_cycle_impossible"])
        self.assertEqual((n["reader_depth"], n["writer_depth"]), (0, 0))

    def test_far_fstart_pin_needs_writer(self):
        t = typ({"a_i": [17.28, 17.28, 60, 60]}, {"cland_tstart_in": (50, 100), "cland_fstart_out_z_o": (40, 1300)})
        n = PS.start_need(t, ["a_i"], ["z_o"], "strap")
        self.assertTrue(n["one_cycle_impossible"])
        self.assertGreater(n["writer_depth"], 0)

    def test_entry_pin_is_not_a_timed_end(self):
        # far entry (async synchroniser input) alone does not make the broadcast impossible
        t = typ({"a_i": [17.28, 17.28, 60, 60]}, {"cland_tstart_in": (600, 1300)})
        self.assertFalse(PS.start_need(t, ["a_i"], [], "strap")["one_cycle_impossible"])

    def test_no_rings(self):
        self.assertEqual(PS.start_need(HC0, [], [], "strap")["reader_depth"], 0)


class Audit(unittest.TestCase):
    class L:
        def __init__(self, masks):
            self.by_type = masks
            self.ca_type = {k: {"role": ("strap",)} for k in masks}

    def test_audit_selects_far_type_and_skips_knobbed(self):
        base = {"partition_types": {"hc0": HC0, "done": typ(HC0["clock"]["landing_contract"]["bands"],
                                                           {"cland_tstart_in": (158, 167)})}}
        base["partition_types"]["done"]["clock"]["landing_reader_start"] = {"depth": 3, "branches": {}}
        rings = ["rsf_i", "rsn_i", "x_hc1_i", "x_hc1_st_a_i"]
        L = self.L({"hc0": {"inputs": rings, "outputs": []}, "done": {"inputs": rings, "outputs": []}})
        self.assertEqual(sorted(PS.audit(base, None, L=L)), ["hc0"])


if __name__ == "__main__":
    unittest.main()

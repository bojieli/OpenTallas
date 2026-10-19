"""CHILD-FLOP (SM-RP4 2026-10-18): a hard child's clock pin is judged at its flops (pin arrival + the child's R)."""
import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "ref_tile"))
import ck_insertion as C

LIB = '''cell ("ot_kid") { pin("clk") { clock : true;
 timing() { timing_type : max_clock_tree_path; cell_rise(scalar) { values("374.6"); } cell_fall(scalar) { values("403.5"); } }
} }'''


class ChildFlop(unittest.TestCase):
    def test_refs_prefer_routed_boundary_then_lib_max(self):
        with tempfile.TemporaryDirectory() as td:
            a = pathlib.Path(td, "v/a"); a.mkdir(parents=True)
            (a / "ot_kid_tt.lib").write_text(LIB)
            b = pathlib.Path(td, "v/b"); b.mkdir(parents=True)
            (b / "ot_big_tt.lib").write_text(LIB.replace("ot_kid", "ot_big"))
            (b / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"n": 9, "mean": 315.0}}}))
            r = C.child_refs(td, ["/src/v/a/ot_kid_tt.lib", "/src/v/b/ot_big_tt.lib"], "tt")
        self.assertEqual(r["ot_kid"], (403.5, "lib max_clock_tree_path"))
        self.assertEqual(r["ot_big"], (315.0, "insertion.json boundary mean"))

    def test_gate_judges_child_flop_record_when_present(self):
        import pre_route_gate as G
        dom = {"tt": {"boundary": {"min": 1159.9, "max": 1565.9}, "all": {"min": 1159.9, "max": 1565.9},
                      "child_flop": {"boundary": {"min": 1520.0, "max": 1565.9}, "all": {"min": 1500.0, "max": 1570.0},
                                     "refs": {"ot_big": {"ref_ps": 315.0}}}},
               "ff": {"boundary": {"min": 900.0, "max": 1000.0}, "all": {"min": 900.0, "max": 1000.0}}}
        rec = G.corner_spreads({}, dom)
        self.assertEqual(rec["tt_pin_spread_ps"], 45.9)
        self.assertEqual(rec["tt_spread_ps"], 70.0)
        self.assertEqual(rec["ff_pin_spread_ps"], 100.0)      # no child_flop record: unchanged (raw)


if __name__ == "__main__":
    unittest.main()

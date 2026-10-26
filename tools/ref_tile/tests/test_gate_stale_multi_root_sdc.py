"""pre_route_gate refuses kit SDCs baked before the multi-mode deferral of the multi-root related-crossing proof."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE  # noqa: E402
import pre_route_gate as PRG  # noqa: E402

OLD = """      set paths [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
      if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
        error "OT_MULTI_ROOT: related crossing lacks actual finite $kind STA path $source_domain -> $target_domain"
      }
"""


class StaleMultiRootSdc(unittest.TestCase):
    def test_current_generator_body_is_not_stale(self):
        self.assertIn(PRG.MULTI_ROOT_PROOF, CE.LEAF_BODY)
        self.assertIn(PRG.MULTI_ROOT_DEFERRAL, CE.LEAF_BODY)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "clock.sdc").write_text(CE.LEAF_BODY)
            self.assertEqual(PRG.stale_multi_root_sdcs(Path(td)), [])

    def test_pre_deferral_body_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "clock_entry.sdc").write_text("set ::ot_ce_related_data 1\nproc ot_ce_leaf_ownership {} {\n" + OLD + "}\n")
            (Path(td) / "clock.sdc").write_text("set ::ot_ce_related_data 0\nproc ot_ce_leaf_ownership {} {\n" + OLD + "}\n")
            (Path(td) / "signoff.sdc").write_text("create_clock -period 770 [get_ports clk]\n")
            self.assertEqual(PRG.stale_multi_root_sdcs(Path(td)), ["clock_entry.sdc"])
            g = PRG.Gate()
            try:
                PRG.check_kit(g, Path(td), None)
            except Exception:
                pass  # no spec.json: only the stale-SDC finding (added first) matters here
            self.assertTrue(any(i["check"] == "kit_sdc" and i["severity"] == "FAIL" for i in g.items), g.items)


if __name__ == "__main__":
    unittest.main()

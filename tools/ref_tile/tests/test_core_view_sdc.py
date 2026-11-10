"""gen_core_view_sdc(): ref_tile kits carry a core-view golden constraint.sdc that sdc_lint accepts (S81-SVCRS-3 11-10,
COORD ruling: no get_ports that matches no port; standard signoff.py with the S81 core-view IO reference)."""
import pathlib
import re
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import ref_tile as RT  # noqa: E402
import sdc_lint  # noqa: E402

SPEC = {"name": "t_core", "clock_port": "ck"}


def lint(text, ins=("a", "rst_n"), outs=("y",), ck="ck"):
    su, hu = sdc_lint.policy_uncertainty()
    return sdc_lint.lint(text, period_ps=833.0, insertion_ps=250.0, insertion_tol_ps=40.0, clock_ports=[ck],
                         inputs=list(ins), outputs=list(outs), unc_setup_ps=su, unc_hold_ps=hu, time_unit_ps=1.0)


class CoreViewSdc(unittest.TestCase):
    def test_lint_clean_with_real_ports(self):
        self.assertEqual(lint(RT.gen_core_view_sdc(SPEC)), [])

    def test_only_clock_port_named(self):
        self.assertEqual(re.findall(r"get_ports \{?([^}\]]+)", RT.gen_core_view_sdc(SPEC)), ["ck"])

    def test_no_tcl_placeholder_vocabulary(self):
        t = RT.gen_core_view_sdc(SPEC)
        for bad in ("set clk_period", "expr", "set_max_fanout", "::env"):
            self.assertNotIn(bad, t)

    def test_gen_check_clean(self):
        self.assertEqual(RT.core_view_sdc_errors(SPEC, RT.gen_core_view_sdc(SPEC)), [])

    def test_tightened_io_budget(self):
        t = RT.gen_core_view_sdc({**SPEC, "io_budget": {"in": 0.3, "out": 0.25}})
        self.assertIn("set_input_delay -max 249.9000", t)
        self.assertIn("set_output_delay -max 208.2500", t)
        self.assertEqual(lint(t), [])

    def test_old_placeholder_fails_lint(self):
        old = ("set clk_period 770\ncreate_clock -name core_clk -period $clk_period [get_ports ck]\n"
               "set_max_fanout 32 [current_design]\n")
        self.assertTrue(lint(old))

    def test_clock_entry_modes_skip(self):
        self.assertFalse(RT.core_view_sdc_applies({**SPEC, "clock": "entries"}))
        self.assertFalse(RT.core_view_sdc_applies({**SPEC, "sdc_extra": ["x.sdc"]}))
        self.assertTrue(RT.core_view_sdc_applies(SPEC))

    def test_ff_hold_frame_matches_signoff(self):
        t = RT.gen_core_view_ff_sdc(SPEC)
        self.assertIn("set_clock_latency -source 202.5000 [get_clocks vclk]", t)
        self.assertIn("set_input_delay -min -40.0000 -clock vclk [all_inputs -no_clocks]", t)
        self.assertIn("set_output_delay -min 0.0000 -clock vclk [all_outputs]", t)
        self.assertNotIn("get_ports", t)
        self.assertIn("set_load 2 [all_outputs]", t)

    def test_route_hold_reads_ff_frame(self):
        spec = {**SPEC, "route": {}}
        self.assertTrue(RT.route_hold_context(spec, "k")["OT_MM_FF_SDC"].endswith(" k/core_view_ff.sdc"))
        self.assertNotIn("core_view_ff", RT.route_hold_context({**spec, "clock": "entries"}, "k")["OT_MM_FF_SDC"])


if __name__ == "__main__":
    unittest.main()

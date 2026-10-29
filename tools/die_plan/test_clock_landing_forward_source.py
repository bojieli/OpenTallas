"""DIE-KV-13 / COORD 10-28 ruling (1): opt-in compose forward_source="clk" -- a forwarded clock output's landing
contract names the type's ONE RTL clock input 'clk' (KV binder: one clk port per partition; ROOT-MERGE-125
clock_landings rejects a tap name 'clk_t4' that is not an input of the type).  Default "tap" is unchanged."""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402
import gen_phys as GP  # noqa: E402


def _raw():
    t = dict(outline_um=[100.0, 100.0], clock=dict(edge_clocks=[]),
             buses=[dict(name="fclk_out_a", dir="out", kind="clock", face="W", window_um=[80.0, 82.0], width=1)])
    return dict(partition_types={"T": t}, ports=[], clock={})


def _bytype():
    return {"T": dict(bands=[], base_type="T", mask=dict(active=True), tree=[], local_sources=[], children=[])}


class ForwardSource(unittest.TestCase):
    def setUp(self):
        self.saved = (GP._snap_tap, GP.clock_pins)
        GP._snap_tap = lambda P, x, y, **k: (x, y)
        GP.clock_pins = lambda P, tn: [("clk_t0", 10.0, 10.0), ("clk_t4", 5.0, 80.0)]
        self.P = types.SimpleNamespace(layer_budget=dict(partition_signal_max="M7"))

    def tearDown(self):
        GP._snap_tap, GP.clock_pins = self.saved
        CP.FORWARD_SOURCE = "tap"

    def _pin(self):
        raw, _ = CP._finish(_raw(), self.P, _bytype(), set(), dict(collector=dict(observer={})))
        return raw["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]

    def test_default_is_the_nearest_tap_name(self):
        self.assertEqual(CP.FORWARD_SOURCE, "tap")
        pin = self._pin()
        self.assertEqual(pin["source_clock_port"], "clk_t4")
        self.assertNotIn("source_clock_tap", pin)

    def test_clk_mode_names_the_rtl_clock_input_and_keeps_the_tap(self):
        CP.FORWARD_SOURCE = "clk"
        pin = self._pin()
        self.assertEqual((pin["source_clock_port"], pin["source_clock_tap"]), ("clk", "clk_t4"))

    def test_compose_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            CP.compose({}, {}, forward_source="nearest")


if __name__ == "__main__":
    unittest.main()

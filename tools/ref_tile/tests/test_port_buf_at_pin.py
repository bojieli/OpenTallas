"""port_buf_at_pin (S81-SVCRS-3 11-10): default on for s81svc_* kits only, explicit bool overrides, hook files exist."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ref_tile as R  # noqa: E402

ROOT = HERE.parents[2]


class PortBufAtPin(unittest.TestCase):
    def test_default_svc_only(self):
        self.assertTrue(R.port_buf_at_pin({"name": "s81svc_irg_hsfp", "io_flop_at_pins": {"cols": 4}}))
        self.assertFalse(R.port_buf_at_pin({"name": "qfd_hub_fr", "io_flop_at_pins": {"cols": 4}}))
        self.assertFalse(R.port_buf_at_pin({"name": "s81svc_x"}))

    def test_explicit(self):
        self.assertFalse(R.port_buf_at_pin({"name": "s81svc_x", "io_flop_at_pins": {"port_buf_at_pin": False}}))
        self.assertTrue(R.port_buf_at_pin({"name": "qfd_x", "io_flop_at_pins": {"port_buf_at_pin": True}}))
        with self.assertRaises(R.SpecError):
            R.port_buf_at_pin({"name": "qfd_x", "io_flop_at_pins": {"port_buf_at_pin": 1}})

    def test_hook_files(self):
        hook = (ROOT / R.PBP_DPL_TCL).read_text()
        self.assertIn("source /src/physical/qwen_die_masters/out_flop_release.tcl", hook)
        self.assertIn("source /src/" + R.PBP_TCL, hook)
        self.assertTrue((ROOT / R.PBP_TCL).is_file())

    def test_irg_kit_uses_hook(self):
        kit = (ROOT / "physical/ref_tile/s81svc_irg_hsfp/kit.env").read_text()
        self.assertIn("PRE_DETAIL_PLACE=" + R.PBP_DPL_TCL, kit)


if __name__ == "__main__":
    unittest.main()

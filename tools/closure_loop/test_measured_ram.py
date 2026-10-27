"""MEASURED RAM (el1013-loop-sizing): a route estimate >= 2x the block's measured peak is admitted at
max(1.25 x peak, peak + 4 GB); unmeasured blocks and near estimates keep the spec value."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import closure_loop as cl


class MeasuredRam(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        p = pathlib.Path(self.d.name)
        (p / "measured_peaks.json").write_text(json.dumps({"blocks": {"vm_cp_slice3_cx": {"peak_gb": 6.8, "n": 3},
                                                                      "big": {"peak_gb": 40.0, "n": 1},
                                                                      "hbm_svc_SW_s6_rob": {"peak_gb": 2.0, "n": 1}}}))
        self.patch = patch.object(cl, "__file__", str(p / "closure_loop.py"))
        self.patch.start()
        cl._MEASURED_PEAKS[:] = [None, None]

    def tearDown(self):
        self.patch.stop()
        cl._MEASURED_PEAKS[:] = [None, None]
        self.d.cleanup()

    def test_gross_overestimate_lowered(self):
        self.assertEqual(cl.sized_ram({"name": "vm_cp_slice3_cx-cx1-2c31a0533"}, 48), 11)      # 6.8 + 4
        self.assertEqual(cl.sized_ram({"name": "big-r1-0123456789"}, 160), 50)                # 40 x 1.25
        self.assertEqual(cl.sized_ram({"name": "hbm_svc_SW_s6_rob_2ac2226ca_tc_hm10_pdn-cl"}, 40), 6)

    def test_kept(self):
        self.assertEqual(cl.sized_ram({"name": "big-r1-0123456789"}, 64), 64)                 # < 2x measured
        self.assertEqual(cl.sized_ram({"name": "unmeasured-r1-0123456789"}, 96), 96)
        self.assertEqual(cl.sized_ram({"name": "vm_cp_slice3_cx-cx1-2c31a0533", "measured_ram": False}, 48), 48)

    def test_stage_list_route_and_calibrate(self):
        spec = {"name": "vm_cp_slice3_cx-cx1-2c31a0533", "peak_ram_gb": 48,
                "stages": {"calibrate": {"cmd": "c", "base": "b"}, "route": {"cmd": "r", "peak_ram_gb": 48},
                           "signoff": {"cmd": "s"}}}
        ram = {s["key"]: s.get("ram") for s in cl.stage_list(spec)}
        self.assertEqual((ram["calibrate"], ram["route"], ram["signoff"]), (11, 11, 16))


if __name__ == "__main__":
    unittest.main()

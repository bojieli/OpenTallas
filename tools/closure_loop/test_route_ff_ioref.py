"""VM8-TIMING 2026-10-08: the route-time FF hold scene reads io_ref_routed.sdc by default (OT_MM_FF_SDC)."""
import sys, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl


def run_launch(spec_extra):
    spec = {"name": "t", "block": "b", "route_hold_corners": "mm",
            "verdict": {"post_sdc": ["physical/x/signoff_unc60.sdc"]},
            "source": {"branch": "main", "commit": "c" * 40}, "stages": {}, **spec_extra}
    j = {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": spec, "commit_full": "c" * 40, "attempt": 1,
         "created": "2026-10-08T15:00:00-07:00"}
    bodies = []

    def fake_ssh(host, c, input=None, **k):
        if input is not None:
            bodies.append(input)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
        cl.launch_stage(j, {"kind": "route", "key": "route", "threads": 4}, "echo route")
    return [l for l in bodies[0].splitlines() if l.startswith("export OT_MM_FF_SDC=") or "/.ot_mm/" in l]


class RouteFfIoref(unittest.TestCase):
    def test_default_appends_ioref(self):
        lines = "\n".join(run_launch({}))
        self.assertIn("cp /r/cl/io_ref_routed.sdc /r/src/.ot_mm/", lines)
        self.assertIn("export OT_MM_FF_SDC='physical/x/signoff_unc60.sdc .ot_mm/io_ref_routed.sdc'", lines)

    def test_explicit_listing_kept(self):
        lines = "\n".join(run_launch({"route_ff_sdc": ["physical/x/a.sdc", "physical/common_flow/io_ref_routed.sdc"]}))
        self.assertNotIn("/r/cl/io_ref_routed.sdc", lines)
        self.assertIn("physical/x/a.sdc physical/common_flow/io_ref_routed.sdc", lines)

    def test_opt_out(self):
        lines = "\n".join(run_launch({"route_ff_ioref": False}))
        self.assertNotIn("io_ref_routed", lines)


if __name__ == "__main__":
    unittest.main()

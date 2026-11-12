import json, tempfile, time, unittest
from pathlib import Path
import kit_wave as KW


class VisualStale(unittest.TestCase):
    """KW-FIX-46 11-12: VISUAL-QUEUE lists only rows placed after the gate on the die's current plan"""

    def rec(self, started, plan):
        td = Path(tempfile.mkdtemp())
        (td / "spec.json").write_text(json.dumps({"plan": plan}))
        return {"die": "s81", "item": "t", "dir": str(td), "started": started}

    def test_stale(self):
        cfg = {"dies": {"s81": {"plan": "/p/new.json"}}}
        t0 = KW.visual_gate_t0(cfg)
        self.assertIn("before", KW.stale_visual_why(cfg, self.rec(t0 - 60, "/p/new.json"), t0))
        self.assertIn("die plan", KW.stale_visual_why(cfg, self.rec(t0 + 60, "/p/old.json"), t0))
        self.assertEqual(KW.stale_visual_why(cfg, self.rec(t0 + 60, "/p/new.json"), t0), "")


if __name__ == "__main__":
    unittest.main()

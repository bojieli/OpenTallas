"""FRESH-ECO-DIR (drive-1010 2026-10-10): requeue_hold_only archives the dropped ECO so the re-run gets a new dir."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="fresheco_"))
import closure_loop as cl  # noqa: E402


class FreshEcoDir(unittest.TestCase):
    def test_requeue_archives_dead_eco(self):
        d = Path(tempfile.mkdtemp()); (d / "jobs").mkdir()
        spec = {"name": "j", "block": "b", "source": {}, "stages": {"route": {"cmd": "x"}}}
        j = dict(name="j", status="NEEDS_RTL", spec=spec, events=[], host="h", run="/r/j",
                 eco={"tried": True, "result": None, "out": "/r/j/cl/eco-combo1", "kind": "combo"})
        with patch.object(cl, "STATE", d), patch.object(cl, "log"), patch.object(cl, "ledger"), \
                patch.object(cl, "stage_list", return_value=[{"kind": "route", "key": "route"}, {"kind": "verdict", "key": "verdict"}]):
            cl.save_job(j)
            cl.requeue_hold_only(cl.all_jobs())
            x = cl.load_job("j")
        self.assertEqual(x["status"], "READY")
        self.assertEqual(x["eco"], {})
        self.assertEqual(len(x["eco_history"]), 1)
        self.assertEqual(x["eco_history"][0]["out"], "/r/j/cl/eco-combo1")
        n = len(x.get("eco_history") or []) + 1          # start_combo_eco's naming
        self.assertEqual(f"/r/j/cl/eco-combo{n}", "/r/j/cl/eco-combo2")


if __name__ == "__main__":
    unittest.main()

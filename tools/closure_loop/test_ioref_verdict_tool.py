"""IOREF-VERDICT-TOOL (ROOT-CORNER 2026-10-19): the routed re-STA (ioref-rejudge / verdict) runs the loop's current
meas_resta.py from cl_ioref/, never the frozen cl/ copy, and records the shipped bytes; cl/ is not written."""
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl


class IorefVerdictTool(unittest.TestCase):
    def test_frozen_job_rejudges_with_current_meas_resta(self):
        j = dict(name="t", host="h", run="/r", attempt=1, events=[], freeze_helper_overlay=True,
                 spec=dict(name="t", block="b", stages={}))
        m = dict(orfs_dir="/r/routes/x/work/orfs")
        res = dict(setup_tt=dict(worst_slack_ps=198.74), hold_ff=dict(worst_slack_ps=18.21))
        calls = []

        def ssh(host, cmd, **k):
            calls.append((cmd, k.get("input")))
            return subprocess.CompletedProcess([], 0, json.dumps(res) + "\n" if "meas_resta.py --orfs" in cmd else "", "")

        with patch.object(cl, "ssh", side_effect=ssh), patch.object(cl, "ship_helpers") as sh:
            rr = cl.routed_ioref(j, m)
        sh.assert_called_once()
        body = (Path(cl.__file__).resolve().parent / "meas_resta.py").read_bytes()
        shipped = [c for c in calls if c[0].endswith("cat > /r/cl_ioref/meas_resta.py")]
        self.assertEqual(len(shipped), 1)
        self.assertEqual(shipped[0][1], body.decode())
        run = [c[0] for c in calls if "meas_resta.py --orfs" in c[0]]
        self.assertEqual(len(run), 1)
        self.assertTrue(run[0].startswith("python3 /r/cl_ioref/meas_resta.py "), run[0])
        self.assertFalse(any("> /r/cl/meas_resta.py" in c[0] for c in calls))      # frozen cl/ untouched
        self.assertEqual(rr["meas_resta_sha256"], hashlib.sha256(body).hexdigest())
        self.assertTrue(rr["key"].endswith("|ae0410-cecorner-1015-pfhc1019"))


if __name__ == "__main__":
    unittest.main()

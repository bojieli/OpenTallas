"""BENCH TIMEOUT OVERRIDE (drive-0849 2026-10-09, from hgi-takeover): a spec bench's timeout_s reaches the bench stage, so
bench_timed_out() honours it (stage_list() dropped it: idx_score taps / ot_hgi_vm_unit died at the 2 h default)."""
import datetime as dt
import unittest
from unittest.mock import patch

import closure_loop as cl


def spec(**b):
    bench = dict(name="long", cmd="true", expect="pass", **b)
    return dict(stages=dict(bench=[bench, dict(name="neg", cmd="false", expect="fail")], route=dict(cmd="true")))


class BenchTimeoutOverride(unittest.TestCase):
    def test_copied(self):
        st = cl.stage_list(spec(timeout_s=6 * 3600))
        self.assertEqual(st[0]["timeout_s"], 6 * 3600)
        self.assertIsNone(st[1]["timeout_s"])          # no override -> default applies

    def test_honoured(self):
        st = cl.stage_list(spec(timeout_s=6 * 3600))[0]
        started = (dt.datetime.now() - dt.timedelta(hours=3)).isoformat()
        with patch.object(cl, "ssh") as s:
            self.assertIsNone(cl.bench_timed_out(dict(host="h", run="/r", stage_tag="t"), st, started))   # 3 h < 6 h
            s.assert_not_called()
        dflt = cl.stage_list(spec())[0]
        with patch.object(cl, "ssh") as s:
            s.return_value.returncode, s.return_value.stdout = 0, ""
            self.assertIsNotNone(cl.bench_timed_out(dict(host="h", run="/r", stage_tag="t"), dflt, started))  # 3 h > 2 h


if __name__ == "__main__":
    unittest.main()

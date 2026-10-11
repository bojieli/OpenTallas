"""drive-1010 2026-10-10: a resumed stage must not be judged on the previous launch's .tmp.log series."""
import datetime as dt
import time
import unittest
from unittest.mock import patch

import stuckscan as ss


def base(mtime):
    ser = [[i * 100, i * 10, -11.4, -500.0] for i in range(30)]
    return dict(current="4_1_cts.tmp.log", corner="TT", logs=[("3_5_place_dp.log", mtime - 6000, 1), ("4_1_cts.tmp.log", mtime, 9)],
                hold=dict(found=[53457], series=ser, cur_last=["5780", 12713, 0, 0, 0, -11.4]))


class StaleLog(unittest.TestCase):
    def test_previous_launch_log_is_not_judged(self):
        now = time.time()
        b = base(now - 600)                       # log last written 10 min ago
        j = dict(stage_started=dt.datetime.fromtimestamp(now - 120).astimezone().isoformat())   # relaunched 2 min ago
        self.assertTrue(ss.stale_current_log(b, j))
        with patch.object(ss, "hold_verdict", return_value="hold repair not converging") as hv, \
             patch.object(ss, "gate_metrics", return_value=None):
            self.assertEqual(ss.hopeless(b, j, now), [])
            hv.assert_not_called()

    def test_current_launch_log_is_judged(self):
        now = time.time()
        b = base(now - 5)
        j = dict(stage_started=dt.datetime.fromtimestamp(now - 7200).astimezone().isoformat())
        self.assertFalse(ss.stale_current_log(b, j))
        with patch.object(ss, "hold_verdict", return_value="hold repair not converging"), \
             patch.object(ss, "hold_stop_plan", return_value=None), patch.object(ss, "gate_metrics", return_value=None):
            self.assertEqual([v for v, _ in ss.hopeless(b, j, now)], ["EARLY_FAIL_HOLD"])

    def test_no_launch_time_keeps_old_behaviour(self):
        self.assertFalse(ss.stale_current_log(base(time.time()), {}))
        self.assertFalse(ss.stale_current_log(base(time.time()), None))


if __name__ == "__main__":
    unittest.main()

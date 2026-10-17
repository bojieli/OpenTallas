import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import su_pinreg as S
from qwen_static_schedule.calendar import ScheduleError

# contracts exactly as recorded by Q-ELEM-SUC (claude/qelem-suc-1016 c0cf2cf57 schedule_delta.json)
CONTRACTS = [
    {"contract": "embedding requests (external_a_re/addr)", "delta": -1},
    {"contract": "status sd (fault, rows, progress, kv_we copy, idle, ready, inflight, active)", "delta": 1},
    {"contract": "copy command cp -> copy start", "delta": 1},
    {"contract": "copy VM read beats at va (from cp)", "delta": 2},
    {"contract": "copy VM write beats at va / xsw copy beats (from cp)", "delta": 3},
    {"contract": "cp_done (from cp)", "delta": 2},
    {"contract": "cp_active", "delta": 1, "note": "rises +1, falls +2 (one edge longer copy pipe)"},
]


def write(root, contracts=CONTRACTS, **kw):
    f = Path(root) / S.DELTA
    f.parent.mkdir(parents=True, exist_ok=True)
    d = dict(schema=S.SCHEMA, master='qfd_sp_su64_sfu', su_op_latency_delta=0, contracts=contracts)
    d.update(kw)
    f.write_text(json.dumps(d))


class SuPinreg(unittest.TestCase):
    def test_measured_deltas_and_windows(self):
        with tempfile.TemporaryDirectory() as t:
            write(t)
            d = S.load(t, 1)
            self.assertEqual((d['start'], d['reads'], d['writes'], d['done'], d['active_rise'], d['active_fall']),
                             (1, 2, 3, 2, 1, 2))
            self.assertEqual((d['embed'], d['status'], d['su_op']), (-1, 1, 0))
            w0 = S.copy_windows(4, S.load(t, 0))
            w1 = S.copy_windows(4, d)
            # PINREG=0 straight from qfd_su_static_copy: reads E+1..E+4, writes E+17..E+20, done E+21, internal occupancy E+0..E+20 (pin cp_active +1: E+1..E+21)
            self.assertEqual(w0, dict(reads=(1, 4), writes=(17, 20), done=21, active=(1, 21)))
            self.assertEqual(w1, dict(reads=(3, 6), writes=(20, 23), done=23, active=(2, 23)))
            # back-to-back copies: +2 controller edges per copy at PINREG=1 (fall +2), relays from the allocator
            self.assertEqual(S.next_copy_edge(100, 4, S.load(t, 0), 3, 2), 100 + 3 + 21 + 1 + 2 + 1)
            self.assertEqual(S.next_copy_edge(100, 4, d, 3, 2), 100 + 3 + 23 + 1 + 2 + 1)
            self.assertTrue(S.check_copies([(100, 4), (130, 64)], d, 3, 2))
            with self.assertRaises(ScheduleError):
                S.check_copies([(100, 4), (129, 64)], d, 3, 2)   # legal at PINREG=0 (128), one edge short at 1
            self.assertTrue(S.check_copies([(100, 4), (128, 64)], S.load(t, 0), 3, 2))

    def test_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ScheduleError):
                S.load(t, 1)                                   # no file: never a silent zero
            write(t, contracts=CONTRACTS[:-1])
            with self.assertRaises(ScheduleError):
                S.load(t, 1)
            bad = [dict(c) for c in CONTRACTS]
            bad[4]['delta'] = 2                                # writes not reads+1: inconsistent with the RTL change
            write(t, contracts=bad)
            with self.assertRaises(ScheduleError):
                S.load(t, 1)
            write(t, master='other')
            with self.assertRaises(ScheduleError):
                S.load(t, 1)
            with self.assertRaises(ScheduleError):
                S.next_copy_edge(0, 4, S.load(t, 0), -1, 0)
            with self.assertRaises(ScheduleError):
                S.copy_windows(0, S.load(t, 0))


if __name__ == '__main__':
    unittest.main()

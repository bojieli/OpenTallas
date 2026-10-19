"""MU-QW-AMIX 10-19: tests of mu_opcal.check_root_merge (the op-granular periodic calendar's root-merge assertion; the
file itself is owned by MU-QW-B1) against the RTL-derived root window of the calendar of record (mu_calendar)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import mu_calendar as M
from qwen_static_schedule import mu_opcal as O
from qwen_static_schedule.calendar import ScheduleError

H = 100000


def cal(*heads):
    sched = {}
    for u, t in heads:
        sched.setdefault(u, []).append(("head", t, None))
    return dict(H=H, schedule=sched)


class OpcalRootMerge(unittest.TestCase):
    def test_span_covers_the_rtl_window(self):
        lo, hi = M.am_root_window()
        self.assertGreaterEqual(O.AM_ROOT_SPAN, hi - lo)       # 48 >= 46 (emit-to-emit separation the RTL needs)
        self.assertEqual(O.AM_EMIT_T, M.AM_EMIT_T)

    def test_legal_passes(self):
        self.assertEqual(O.check_root_merge(cal((0, 0), (1, O.AM_ROOT_SPAN), (2, 5000), (3, 9000))), 4)
        self.assertEqual(O.check_root_merge(cal((0, 0), (0, 3))), 2)          # one user's emits: not a mix

    def test_forced_mix_raises(self):
        with self.assertRaisesRegex(ScheduleError, "mixes users 0 and 1"):
            O.check_root_merge(cal((0, 0), (1, O.AM_ROOT_SPAN - 1)))
        with self.assertRaisesRegex(ScheduleError, "mixes users"):              # cyclic: across the frame edge
            O.check_root_merge(cal((2, 10), (3, H - 20)))


if __name__ == "__main__":
    unittest.main()

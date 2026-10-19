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


class OpcalEmbAfterResult(unittest.TestCase):
    """MU-OPCAL-EMB 10-19: the token-start LOCAL EMB issues only once the user's argmax result is in tok_b[user]"""
    def test_derived_edge(self):
        self.assertEqual(O.tok_slice0_edge(), 48)               # root merge + TOK broadcast to W5, worst root position
        self.assertEqual((O.RES_SSQ, O.RES_BANK, O.EMB_T), (51, 52, 60))
        lo, hi = M.am_root_window()
        self.assertGreaterEqual(O.tok_slice0_edge(), hi - 1)     # never before the last merge

    def test_image_emb_after_result(self):
        c = O.compile_frame(16, layers=2)
        seg0 = c["segs"][0]
        self.assertEqual([t for t, w in seg0 if O._is_emb(w)], [O.EMB_T])
        self.assertEqual(c["emb_checked"], sum(c["tokens_per_frame"].values()))
        self.assertEqual(c["T"], M.single_user_period(c["inputs"], 2))   # latency user = the (fixed) single-user token

    def test_old_image_raises(self):
        for et in (O.EMB_T_SMOKE, O.EMB_T - 1):
            with self.assertRaisesRegex(ScheduleError, "precedes its argmax result"):
                O.compile_frame(16, layers=2, p=dict(emb_t=et, head_tok_ofs=O.EMB_T))


if __name__ == "__main__":
    unittest.main()

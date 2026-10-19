"""MU-QWEN 10-18: the 4-user static calendar (tools/qwen_static_schedule/mu_calendar.py)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import mu_calendar as M
from qwen_static_schedule.calendar import ScheduleError

OF_RECORD = dict(users=4, occupancy="measured", head_chunks=8)


class MuCalendar(unittest.TestCase):
    def test_inputs_required(self):
        p = dict(M.SOURCED)
        del p["kv_service"]
        with self.assertRaises(ScheduleError):
            M._need(p)

    def test_single_user_token_is_the_composed_one(self):
        self.assertEqual(M.single_user_period(dict(M.SOURCED)), 251615)     # rom_multiuser_1018 Q["T"]

    def test_latency_user_identical_and_no_collision(self):
        cal = M.compile_calendar(OF_RECORD, tokens=3, policy="priority")
        self.assertTrue(cal["latency_user_identical"])
        self.assertEqual(cal["schedule_collisions"], 0)
        clashes, ident = M.verify(cal["schedule"], cal["schedule"][0])
        self.assertEqual(clashes, [])
        self.assertAlmostEqual(cal["users"][0]["tok_s"], 4769.19, places=1)

    def test_verify_catches_a_moved_window(self):
        cal = M.compile_calendar(dict(OF_RECORD, users=2), tokens=2, policy="priority")
        sched = {u: list(v) for u, v in cal["schedule"].items()}
        name, t0, b = sched[1][5]
        sched[1][5] = (name, cal["schedule"][0][5][1], b)                    # onto the latency user's same op
        clashes, _ = M.verify(sched, cal["schedule"][0])
        self.assertTrue(clashes)

    def test_pure_shift_four_users_does_not_exist(self):
        for occ in ("measured", "priced"):
            f = M.frame_feasible_shifts(dict(occupancy=occ))
            self.assertIsNone(f["four_user_pure_shift"])
            self.assertEqual(f["per_resource"]["me"]["windows"], 4)          # the lemma's one-window premise fails
        self.assertGreater(M.frame_feasible_shifts(dict(occupancy="measured"))["feasible_pair_shifts"], 0)

    def test_unchunked_head_admits_no_filler_token(self):
        cal = M.compile_calendar(dict(OF_RECORD, head_chunks=1), tokens=3, policy="priority")
        self.assertTrue(all(u["tokens_completed"] == 0 for u in cal["users"][1:]))

    def test_of_record_numbers(self):
        cal = M.compile_calendar(OF_RECORD, tokens=6, policy="priority")
        self.assertGreater(cal["aggregate_tok_s"], 13500)
        self.assertLess(cal["aggregate_tok_s"], 18416)                       # below the study's pure-shift 18.4k

    def test_collective_sets_refuse_double_booking(self):
        with self.assertRaises(ScheduleError):
            M._runs([5, 6, 6])

    def test_bench_window_has_overlapping_epochs_and_all_users(self):
        cal = M.compile_calendar(OF_RECORD, tokens=3, policy="priority")
        bc = M.bench_cases(cal)
        self.assertEqual(bc["window"]["users"], [0, 1, 2, 3])
        self.assertGreater(bc["window"]["overlapping_epoch_pairs"], 0)
        self.assertLessEqual(len(bc["cases"][0]["cmds"]), 30)

    def test_kv_user_bases_disjoint(self):
        b = M.kv_user_bases(4)
        self.assertEqual(len(set(b.values())), 4 * 36)

    def test_kv_user_rows_match_rtl_rowoff(self):
        # coordinator 0jc: the RTL row (qkd_kv_mu_wrow/rrow: row[9:8] |= user on the today row 64 + l) is the reference
        r = M.kv_user_rows(4)
        for u in range(4):
            for l in range(36):
                rtl = (64 + l) | (u << 8)                 # bit insertion as the leaves do it
                self.assertEqual(r[(u, l)], rtl)
                self.assertEqual(r[(u, l)], 64 + l + 256 * u)
                self.assertEqual((r[(u, l)] & 0xFF) - 64, l)   # closed read-return tag row[7:0] - ROW0 = layer
        self.assertEqual(M.kv_user_bases(4)[(3, 35)], (64 + 35 + 768) << 10)
        self.assertEqual(M.kv_user_rows(1), {(0, l): 64 + l for l in range(36)})   # 1 user = today's rows
        with self.assertRaises(ScheduleError):
            M.kv_user_rows(5)
        with self.assertRaises(ScheduleError):
            M.kv_user_rows(4, layers=200)

    def test_dv_user_fields_match_rtl(self):
        # MU-ADOPT-CTLM 10-19: the strides the compiler writes = the RTL defaults of the die-bound DV control cluster
        import re
        root = Path(__file__).resolve().parents[2]
        f = M.dv_user_fields(4)
        for rtl in ("rtl/qwen_dv/qfd_tt_ctlm_dv_lpf.sv", "rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv", "rtl/qwen_dv/qfd_tt_ctlm_dv.sv"):
            src = (root / rtl).read_text()
            for name, want in (("UVM_STRIDE", f["uvm_stride"]), ("PIDX_STRIDE", f["pidx_stride"]), ("UTAG_LSB", f["utag_lsb"])):
                got = [int(v) for v in re.findall(rf"parameter integer {name} = (\d+)", src)]
                self.assertTrue(got and all(g == want for g in got), (rtl, name, got, want))
        self.assertEqual(4 * f["uvm_stride"], 16384)
        self.assertEqual(4 * f["pidx_stride"], 512)
        with self.assertRaises(ScheduleError):
            M.dv_user_fields(5)

    # MU-QW-AMIX 10-19: the argmax root merges one user's candidates at a time (compiler assertion; the RTL faults too)
    def test_root_window_derivation(self):
        self.assertEqual(M.am_root_window(12), (2, 48))         # root at W5: own at +2, slice 11 at +4*11+3 = +47
        self.assertEqual(M.am_root_window(2), (2, 8))
        lo, hi = M.am_root_window(12)
        for r in range(12):                                      # every root position inside the worst-case window
            arr = [2 * r + 2] + [2 * k + 2 * abs(k - r) + 3 for k in range(12) if k != r]
            self.assertTrue(lo <= min(arr) and max(arr) < hi)

    def test_root_merge_legal_schedule_passes(self):
        cal = M.compile_calendar(OF_RECORD, tokens=3, policy="priority")
        self.assertGreater(cal["root_merge"]["emits_checked"], 3)
        self.assertEqual(cal["root_merge"]["mixed"], 0)
        self.assertEqual(M.check_root_merge(cal["schedule"]), cal["root_merge"]["emits_checked"])
        span = M.am_root_window()[1] - M.am_root_window()[0]
        self.assertEqual(M.check_root_merge({0: [("head", 1000, None)], 1: [("head", 1000 + span, None)]}), 2)
        self.assertEqual(M.check_root_merge({0: [("head", 1000, None), ("head", 1001, None)]}), 2)   # one user: legal

    def test_root_merge_forced_mix_raises(self):
        span = M.am_root_window()[1] - M.am_root_window()[0]
        with self.assertRaisesRegex(ScheduleError, r"mixes users 0 and 1: emits at cycles 1008 and 1053"):
            M.check_root_merge({0: [("head", 1000, None)], 1: [("head", 1000 + span - 1, None)]})
        cal = M.compile_calendar(OF_RECORD, tokens=3, policy="priority")
        sched = {u: list(v) for u, v in cal["schedule"].items()}
        h0 = next(t0 for n, t0, _ in sched[0] if n == "head")
        i1 = next(i for i, (n, _, _) in enumerate(sched[1]) if n == "head")
        n, _, b = sched[1][i1]
        sched[1][i1] = (n, h0 + 10, b)                           # user 1's emit 10 cycles after user 0's
        with self.assertRaisesRegex(ScheduleError, "argmax root merge mixes users 0 and 1"):
            M.check_root_merge(sched)


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

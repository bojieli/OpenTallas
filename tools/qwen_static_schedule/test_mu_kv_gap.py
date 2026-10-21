"""MU-KV-BOOT 10-19: the KV layer programme GAP table, its MU boot image and the KV programme's own checks
(tools/qwen_static_schedule/mu_calendar.py kv_*; qkd_static_kv_layer_programme_mu)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import mu_calendar as M
from qwen_static_schedule import mu_opcal as O
from qwen_static_schedule.calendar import ScheduleError

WORDS = [int(x, 16) for x in (M.ROOT / M.KV_SRC_IMAGE).read_text().split()]
ROWS = M.kv_rows_from_image(WORDS)
CAL, GAPS, STARTS, CHK, PER_USER = M.kv_frame_of_record(ROWS)


class KvGap(unittest.TestCase):
    def test_frame_of_record_passes(self):
        self.assertEqual(len(GAPS), 4)
        self.assertTrue(all(len(g) == 36 for g in GAPS))
        self.assertEqual(GAPS[0], [0] * 36)                                  # the latency user: all 0
        self.assertTrue(all(min(g) >= 0 for g in GAPS))
        self.assertEqual(CHK["collisions"], 0)
        self.assertEqual(CHK["events"], 1800)                                # 5 tokens x 36 stages x 10 events
        self.assertTrue(all(v["patterns"] == 1 for v in PER_USER.values()))
        self.assertEqual(CAL["H"] % M.KV_HBM_BEAT, 0)
        self.assertEqual(CAL["T"] % M.KV_HBM_BEAT, 0)                         # padded like the single-user image
        self.assertGreater(CAL["aggregate_tok_s"], 11900)

    def test_frame_of_record_f16_refused(self):
        with self.assertRaisesRegex(ScheduleError, "different KV stage patterns"):
            M.kv_gap_table(O.compile_frame(16, p=M.kv_frame_params(ROWS)))

    def test_user0_nonzero_refused(self):
        g = [list(x) for x in GAPS]
        g[0][5] = 7
        with self.assertRaisesRegex(ScheduleError, "latency user gaps not all 0"):
            M.check_kv_programme(ROWS, g, STARTS, CAL["H"])

    def test_collision_refused(self):
        # user 1's stage 1 begin moved onto user 0's stage 1 kgo edge (a calendar the compiler must never emit)
        g = [list(x) for x in GAPS]
        b1 = STARTS[1][0] + g[1][0]
        g[1][0] += (ROWS[0]["kgo"] - b1) % CAL["H"]
        with self.assertRaises(ScheduleError):
            M.check_kv_programme(ROWS, g, STARTS, CAL["H"])

    def test_same_edge_collision_named(self):
        st = {0: [0], 1: [ROWS[0]["kgo"]]}
        g = [[0] * 36 for _ in range(4)]
        with self.assertRaisesRegex(ScheduleError, "KV programme collision on cycle"):
            M.check_kv_programme(ROWS, g, st)

    def test_without_kv_constraints_collides(self):
        # the same frame without the KV programme's resources: users 2 and 3 lock one stage apart (done == start)
        p = {k: v for k, v in M.kv_frame_params(ROWS).items() if k not in ("kv_lp_rows", "kv_phase_quantum")}
        cal = O.compile_frame(2, p=p)
        g, _ = M.kv_gap_table(cal)
        with self.assertRaises(ScheduleError):
            M.check_kv_programme(ROWS, g, M.kv_frame_starts(cal), cal["H"])

    def test_mu_image_layout(self):
        img = M.kv_layer_image_mu(WORDS, GAPS)
        self.assertEqual(len(img), 471)
        self.assertEqual(img[:326], WORDS[:326])
        self.assertEqual(img[470], M.KV_LP_SEAL)
        for u in range(4):
            for s in range(36):
                self.assertEqual(img[326 + 36 * u + s], GAPS[u][s])
        with self.assertRaises(ScheduleError):
            M.kv_layer_image_mu(WORDS, GAPS[:3])

    def test_ownership_roots(self):
        own, per = M.kv_ownership_roots_mu(ROWS, GAPS)
        self.assertEqual(per["leave_per_user"][0], 0x3B0E3)                  # single-user roots (die target3.hex)
        self.assertEqual(per["deadline_per_user"][0], 0x3C239)
        self.assertEqual(own[0], 3)
        self.assertEqual(own[3], M.KV_OWN_SEAL)
        self.assertEqual(own[1], max(per["leave_per_user"]))
        self.assertEqual(own[2], max(per["deadline_per_user"]))

    def test_launch_phase_of_image(self):
        b = 0
        for r in ROWS:                                                        # user 0's launches: legal at phase 0
            self.assertTrue(M.kv_launch_legal(r, b))
            b += r["stage_end"]

    def test_receipt_states_epoch_convention(self):
        r = M.kv_gap_receipt(WORDS)
        self.assertIn("authority_epoch[1:0]", r["epoch_convention"])
        self.assertTrue(r["user0_gaps_all_zero"])
        self.assertIn("different KV stage patterns", r["frame_of_record_refused"])

    def test_event_list(self):
        ev = M.kv_event_list(ROWS, GAPS, STARTS)
        self.assertEqual(len({c for c, *_ in ev}), len(ev))
        self.assertEqual(ev[0][:2], (0, 0))                                   # user 0 stage 1 start at cycle 0


if __name__ == "__main__":
    unittest.main()

"""MU-KV-TOKLIST 10-19 (option b): per-token KV stage-start gap lists (mu_calendar kv_token_lists / kv_toklist_*;
qkd_static_kv_layer_programme_mu TOKLIST 1)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import mu_calendar as M
from qwen_static_schedule.calendar import ScheduleError
from qwen_static_kv import program_target_frames as PTF

WORDS = [int(x, 16) for x in (M.ROOT / M.KV_SRC_IMAGE).read_text().split()]
ROWS = M.kv_rows_from_image(WORDS)
CAL, LISTS, STARTS, CHK = M.kv_toklist_frame(ROWS)


class KvTokList(unittest.TestCase):
    def test_frame_f16_passes(self):
        self.assertEqual(CAL["frame_tokens"], 16)
        self.assertEqual(CAL["tokens_per_frame"], {0: 16, 1: 15, 2: 8, 3: 6})
        self.assertAlmostEqual(CAL["aggregate_tok_s"], 13480.2, places=1)
        self.assertEqual(CHK["collisions"], 0)
        self.assertEqual([len(L) for L in LISTS], [16, 15, 8, 6])
        self.assertTrue(all(not any(t) for t in LISTS[0]))                   # latency user all 0
        self.assertEqual(len({tuple(t) for t in LISTS[1]}), 15)              # one pattern per filler token

    def test_one_table_refused_lists_accepted(self):
        with self.assertRaisesRegex(ScheduleError, "different KV stage patterns"):
            M.kv_gap_table(CAL)

    def test_image_layout(self):
        img = M.kv_layer_image_toklist(WORDS, LISTS)
        self.assertEqual(len(img), 328 + 12 * 29)
        self.assertEqual(img[:326], WORDS[:326])
        self.assertEqual(img[326], (15 << 8) | (8 << 16) | (6 << 24))
        self.assertEqual(img[-1], M.KV_LP_SEAL)
        ent = [g for u in (1, 2, 3) for t in LISTS[u] for g in t]
        for e in (0, 1, 2, 500, len(ent) - 1):
            self.assertEqual((img[327 + e // 3] >> (20 * (e % 3))) & 0xFFFFF, ent[e])
        self.assertTrue(all(w >> 60 == 0 for w in img[327:-1]))
        self.assertEqual(PTF.encode_image(1, 0x0b0b, img, [], mu='toklist')['program_words'], len(img))
        with self.assertRaises(ValueError):
            PTF.encode_image(1, 0x0b0b, img[:-2] + img[-1:], [], mu='toklist')

    def test_user0_nonzero_refused(self):
        L = [[list(t) for t in x] for x in LISTS]
        L[0][3][5] = 7
        with self.assertRaisesRegex(ScheduleError, "latency user gaps not all 0"):
            M.check_kv_programme(ROWS, L, STARTS, CAL["H"])
        with self.assertRaisesRegex(ScheduleError, "latency user gaps not all 0"):
            M.kv_toklist_words(L)

    def test_collision_refused(self):
        L = [[list(t) for t in x] for x in LISTS]
        b1 = STARTS[1][0] + L[1][0][0]
        L[1][0][0] += (ROWS[0]["kgo"] - b1) % CAL["H"]
        with self.assertRaises(ScheduleError):
            M.check_kv_programme(ROWS, L, STARTS, CAL["H"])

    def test_capacity_refused(self):
        L = [LISTS[0], LISTS[1] * 3, LISTS[2], LISTS[3]]                    # 59 filler tokens > 42 (512 words)
        with self.assertRaisesRegex(ScheduleError, "SRAM"):
            M.kv_toklist_words(L)

    def test_gap_mode_unchanged(self):
        cal, gaps, st, chk, per = M.kv_frame_of_record(ROWS)
        self.assertEqual(chk["events"], 1800)
        own, perr = M.kv_ownership_roots_mu(ROWS, gaps)
        self.assertEqual(perr["leave_per_user"][0], 0x3B0E3)


if __name__ == "__main__":
    unittest.main()

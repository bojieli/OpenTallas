import unittest
import kit_wave as K

CFG = {"dies": {"qwen_compute": {"unfixed_classes": {r"INFRA\|.*HDL source missing": "qwen_missing_phy not on every host"}}}}


def rec(cls_attempt=1):
    return {"die": "qwen_compute", "item": "sle_x", "attempt": cls_attempt, "status": "RETRY-INFRA"}


class UnfixedClass(unittest.TestCase):
    def test_match_counts_infra_and_ignores_unlisted(self):
        self.assertEqual(K.unfixed_match(CFG, "qwen_compute", "INFRA", "bind: ERROR preferred HDL source missing: /x")[0],
                         r"INFRA\|.*HDL source missing")
        self.assertIsNone(K.unfixed_match(CFG, "qwen_compute", "FLOW", "some other failure"))
        self.assertIsNone(K.unfixed_match(CFG, "qwen_kvsys", "INFRA", "HDL source missing"))

    def test_marker_blocks_until_key_deleted(self):
        st = {}
        m = K.note_unfixed(CFG, st, rec(), "INFRA", "preferred HDL source missing")
        self.assertTrue(m)
        why = K.blocked_why(CFG, st, "qwen_compute", "sle_x")
        self.assertTrue(why.startswith("BLOCKED-UNFIXED"), why)
        # an input change does not reset it (unlike the retry cap)
        self.assertTrue(K.blocked_why(CFG, st, "qwen_compute", "sle_x"))
        # the class is declared fixed: key deleted -> released and the marker is dropped
        cfg2 = {"dies": {"qwen_compute": {"unfixed_classes": {}}}}
        self.assertEqual(K.blocked_why(cfg2, st, "qwen_compute", "sle_x"), "")
        self.assertNotIn("qwen_compute|sle_x", st["unfixed"])

    def test_a_different_failure_clears_the_marker(self):
        st = {}
        K.note_unfixed(CFG, st, rec(), "INFRA", "preferred HDL source missing")
        self.assertIsNone(K.note_unfixed(CFG, st, rec(2), "FLOW", "a different failure"))
        self.assertEqual(K.blocked_why(CFG, st, "qwen_compute", "sle_x"), "")

    def test_bad_regex_is_ignored(self):
        cfg = {"dies": {"d": {"unfixed_classes": {"([": "bad"}}}}
        self.assertIsNone(K.unfixed_match(cfg, "d", "INFRA", "x"))


if __name__ == "__main__":
    unittest.main()

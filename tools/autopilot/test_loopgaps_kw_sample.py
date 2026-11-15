import unittest

import loopgaps as LG

TEXT = """- 2026-11-01 09:12 PST GEOM REQ [KIT-WAVE-1 sample qwen_kvsys/kv3_phy_v1 event28w_c 3_place] intel1:/x/geom
2026-11-01 10:04 PST GEOM-104: REPLY [GEOM REQ 09:12 KIT-WAVE-1 sample qwen_kvsys/kv3_phy_v1 event28w_c 3_place] = CONCUR PASS-COND (exception release; route stays enqueued)
"""
NOW = LG.parse_ts("2026-11-01 14:00 PST")


class KitWaveSampleGap(unittest.TestCase):
    def notrouted(self, kits):
        return [s for _, s in LG.gaps_geom(TEXT, NOW, set(), frozenset(), kits) if "GEOM-PASS-NOT-ROUTED" in s]

    def test_sample_pass_flagged_without_submit(self):
        self.assertEqual(len(self.notrouted(set())), 1)

    def test_sample_pass_not_flagged_when_kit_submitted(self):
        self.assertEqual(self.notrouted({("qwen_kvsys", "kv3_phy_v1")}), [])

    def test_other_kit_submitted_still_flagged(self):
        self.assertEqual(len(self.notrouted({("qwen_kvsys", "kv3_phy")})), 1)


if __name__ == "__main__":
    unittest.main()

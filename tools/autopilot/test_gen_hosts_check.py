import unittest
import gen_hosts_check as G


class Gaps(unittest.TestCase):
    CFG = {"dies": {"s81": {"src": "/k/d5", "gen_hosts": ["e10", "e8", "i1"]}, "kv": {"src": "/k/kv10", "gen_hosts": ["e10"]},
                    "hbm": {"src": "/k/h", "src_manifest": False, "gen_hosts": ["e10", "e2"]}}}

    def test_host_without_the_current_source_is_a_gap(self):
        have = {("e10", "/k/d5/.src-manifest.json"), ("e8", "/k/d5/.src-manifest.json"), ("i1", "/k/d4/.src-manifest.json"), ("e10", "/k/kv10/.src-manifest.json")}
        g = G.gaps(self.CFG, lambda h, p: (h, p) in have)
        self.assertEqual(g, {"s81": ["i1"]})                       # intel1 holds D4 only; kv ok; hbm without manifest policy is not judged

    def test_dies_filter_and_clean_config(self):
        self.assertEqual(G.gaps(self.CFG, lambda h, p: True), {})
        self.assertEqual(G.gaps(self.CFG, lambda h, p: False, dies=["kv"]), {"kv": ["e10"]})

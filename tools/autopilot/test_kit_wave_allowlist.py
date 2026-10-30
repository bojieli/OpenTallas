import unittest
from test_kit_wave import KW, cfg, OWN

class ExactAllowlist(unittest.TestCase):
    def rows(self):
        return KW.parse_owners(OWN)
    def test_allowlist_matches_expanded_exact_plan_class(self):
        c=cfg(only_items=["kv3_hg_v1__clgood"])
        p,s=KW.select(self.rows(),c,"qwen_kvsys",{}, {"kv3_hg_v1__clgood":"a","kv3_hg_v1__clother":"b"})
        self.assertEqual([r["item"] for r in p],["kv3_hg_v1__clgood"])
        self.assertEqual(p[0]["parent_item"],"kv3_hg_v1")
    def test_base_alias_does_not_admit_unlisted_classes(self):
        p,s=KW.select(self.rows(),cfg(only_items=["kv3_hg_v1"]),"qwen_kvsys",{}, {"kv3_hg_v1__clgood":"a"})
        self.assertEqual(p,[])
    def test_allowlist_does_not_override_live_claim_or_empty(self):
        c=cfg(only_items=["kv3_io_cor_v1"])
        p,s=KW.select(self.rows(),c,"qwen_kvsys",{}, {"kv3_io_cor_v1":"a"})
        self.assertEqual(p,[])
        self.assertIn("live job (another lane)",s)
        p,s=KW.select(self.rows(),cfg(only_items=[]),"qwen_kvsys",{},None)
        self.assertEqual(p,[])

if __name__ == "__main__":unittest.main()

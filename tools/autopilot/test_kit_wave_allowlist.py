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

    def test_class_in_flight_is_not_picked_by_its_retry_row(self):
        # QC 11-04 11:30: retry rows @1 and @2 launched 12 RUNNING classes twice in one pass
        names={"kv3_hg_v1__clgood":"a"*12}
        key=KW.item_key("qwen_kvsys","e","kv3_hg_v1__clgood","a"*12)
        for status,picked in (("RUNNING",[]),("LAUNCHING",[]),("FAIL",["kv3_hg_v1__clgood"])):
            c=cfg(only_items=["kv3_hg_v1__clgood"],retry=["kv3_hg_v1__clgood@2"])
            st={"items":{key:{"die":"qwen_kvsys","item":"kv3_hg_v1__clgood","attempt":2,"status":status}}}
            p,s=KW.select(self.rows(),c,"qwen_kvsys",st,names)
            self.assertEqual([r["item"] for r in p],picked,status)

class WorkRootProblem(unittest.TestCase):
    ROOT="/srv/opentallas-scratch2/claude/lane/kit-wave"; LANE="/srv/opentallas-scratch2/claude/lane"
    def c(self,**k):
        c=cfg(work_root=self.ROOT,gen_host="epyc4",**k)
        return c
    def test_all_gen_hosts_marked_is_a_problem(self):
        c=self.c(); c["_spill_marked"]={"epyc4":{self.LANE}}
        self.assertIn("no host",KW.work_root_problem(c,"qwen_kvsys",lambda p:True))
    def test_clean_or_unknown_host_is_no_problem(self):
        c=self.c(); self.assertIsNone(KW.work_root_problem(c,"qwen_kvsys",lambda p:True))
        c["_spill_marked"]={"epyc4":{"/srv/opentallas-scratch2/claude/other"}}
        self.assertIsNone(KW.work_root_problem(c,"qwen_kvsys",lambda p:True))
    def test_mount_missing_on_hub_is_a_problem(self):
        self.assertIn("not on the hub",KW.work_root_problem(self.c(),"qwen_kvsys",lambda p:False))
    def test_marked_gen_host_leaves_when_another_stays(self):
        c=self.c(gen_hosts=["epyc4","epyc2"]); c["_spill_marked"]={"epyc4":{self.LANE}}
        self.assertEqual(KW.gen_hosts(c,"qwen_kvsys"),["epyc2"])
        self.assertIsNone(KW.work_root_problem(c,"qwen_kvsys",lambda p:True))

if __name__ == "__main__":unittest.main()

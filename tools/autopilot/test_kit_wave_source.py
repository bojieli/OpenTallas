import json,tempfile,unittest
from pathlib import Path
from test_kit_wave import KW,cfg,FakeAP
class AP:
    DRY=True
    def __init__(self):self.logs=[]
    def log(self,x):self.logs.append(x)
class PinnedSource(unittest.TestCase):
    def run_case(self,pinned,retry=False):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup)
        if pinned is not None:(Path(td.name)/"spec.json").write_text(json.dumps(pinned))
        c=cfg(src_sha="newsha",retry=["kv3_hg_v1@1"] if retry else [])
        r=dict(die="qwen_kvsys",item="kv3_hg_v1",attempt=1,dir=td.name,event="event28w_c",geom_dir="/g",kit="intel1:/k",cells=100,status="PASS")
        ap=AP();KW.enqueue_pass(ap,c,{},r,{})
        return r,ap
    def test_changed_config_cannot_relabel_old_result(self):
        r,a=self.run_case(dict(src_sha="oldsha"))
        self.assertIn("main@oldsha",a.logs[0]);self.assertNotIn("main@newsha",a.logs[0])
    def test_explicit_flow_retry_preserves_old_result_without_enqueue(self):
        r,a=self.run_case(dict(src_sha="oldsha"),True)
        self.assertEqual(r["class"],"FLOW");self.assertEqual(a.logs,[])
    def test_missing_identity_does_not_use_current_config(self):
        for p in (None,dict(src_sha="")):
            r,a=self.run_case(p);self.assertEqual(r["class"],"FLOW");self.assertEqual(a.logs,[])
if __name__=="__main__":unittest.main()

class RetryOutput(unittest.TestCase):
    def test_second_attempt_keeps_first_output_and_identity(self):
        with tempfile.TemporaryDirectory() as td:
            ap=FakeAP(td,"");c=cfg();st={"items":{}};r=dict(item="kv3_hg_v1",kind="type",block_sha="abc",replicas=2)
            a=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp1=json.loads((Path(a["dir"])/"spec.json").read_text())
            b=KW.launch(ap,c,st,"qwen_kvsys",r,"intel2");sp2=json.loads((Path(b["dir"])/"spec.json").read_text())
            self.assertNotEqual(sp1["work"],sp2["work"]);self.assertTrue(sp2["work"].endswith("/attempt_2"))
            self.assertEqual(json.loads((Path(a["dir"])/"spec.json").read_text()),sp1)

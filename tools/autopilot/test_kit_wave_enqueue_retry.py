"""KW6-CODE 11-04: a coord transport failure on enqueue keeps a PASS kit; later ticks send it, once."""
import json,tempfile,unittest
from pathlib import Path
from test_kit_wave import KW,cfg


class AP:
    DRY=False
    def __init__(self,d,results):self.AP_DIR=Path(d);self.results=list(results);self.calls=[];self.logs=[];self.appends=[]
    def log(self,x):self.logs.append(x)
    def coord_append(self,*a):self.appends.append(a)
    def sh(self,cmd,timeout=0,input=None):
        self.calls.append(cmd)
        return self.results.pop(0)

DENIED=(1,"","enqueue: NOT SUBMITTED: git@github.com: Permission denied (publickey).")


class EnqueueRetry(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);self.d=td.name
        (Path(self.d)/"spec.json").write_text(json.dumps(dict(src_sha="abc")))
    def rec(self,item="kv3_hg_v1",**over):
        r=dict(die="qwen_kvsys",item=item,attempt=2,dir=self.d,event="event28w_c",geom_dir="/g",kit="intel1:/k/"+item,cells=100,status="PASS",stage="geom")
        r.update(over);return r
    def st(self,*recs):return {"items":{r["item"]:r for r in recs},"pass_n":0}
    def run_pass(self,results,c=None,rec=None):
        c=c or cfg();r=rec or self.rec();ap=AP(self.d,results);st=self.st(r);n={}
        KW.enqueue_pass(ap,c,st,r,n)
        return r,ap,st,n,c
    def test_transport_keeps_kit_pass_with_one_notice(self):
        r,ap,st,n,c=self.run_pass([DENIED])
        self.assertEqual((r["status"],r["enqueue_pending"],r["class"]),("PASS",1,""))
        self.assertIn("retried next tick",n["qwen_kvsys"][0])
    def test_timeout_is_transport(self):
        r,*_=self.run_pass([(124,"","timeout")])
        self.assertEqual(r["status"],"PASS");self.assertTrue(r["enqueue_pending"])
    def test_refused_row_stays_terminal(self):
        r,*_=self.run_pass([(1,"","enqueue: REFUSED: bad row")])
        self.assertEqual((r["status"],r["class"]),("FAIL","FLOW"));self.assertNotIn("enqueue_pending",r)
    def test_next_tick_sends_and_clears(self):
        r,ap,st,n,c=self.run_pass([DENIED])
        c.pop("_enqueue_down");ap.results=[(0,"","")];n2={}
        self.assertEqual(KW.retry_enqueue(ap,c,st,n2),1)
        self.assertEqual(r["status"],"ENQUEUED");self.assertNotIn("enqueue_pending",r);self.assertEqual(r["reason"],"")
        self.assertEqual(len(ap.calls),2)
        self.assertEqual(ap.calls[0],ap.calls[1])    # the same row: publish finds it if the first push did land
        self.assertEqual(KW.retry_enqueue(ap,c,st,{}),0)
    def test_down_remote_costs_one_backoff_per_tick(self):
        c=cfg();a=self.rec("a");b=self.rec("b");ap=AP(self.d,[DENIED]);st=self.st(a,b);n={}
        KW.enqueue_pass(ap,c,st,a,n);KW.enqueue_pass(ap,c,st,b,n)
        self.assertEqual(len(ap.calls),1);self.assertEqual((a["status"],b["status"]),("PASS","PASS"))
        self.assertTrue(a["enqueue_pending"] and b["enqueue_pending"])
    def test_repeat_failure_is_silent_for_the_owner(self):
        r,ap,st,n,c=self.run_pass([DENIED])
        c.pop("_enqueue_down");ap.results=[DENIED];n2={}
        KW.retry_enqueue(ap,c,st,n2)
        self.assertEqual(n2,{});self.assertEqual(r["enqueue_pending"],2)
    def test_hold_items_not_sent(self):
        c=cfg(hold_items={"kv3_*":"die owner hold"});r=self.rec(enqueue_pending=1);ap=AP(self.d,[]);st=self.st(r)
        self.assertEqual(KW.retry_enqueue(ap,c,st,{}),0)
        self.assertEqual(ap.calls,[]);self.assertEqual(r["status"],"PASS")
    def test_die_stop_not_sent(self):
        (Path(self.d)/"kit_wave.qwen_kvsys.stop").write_text("")
        r=self.rec(enqueue_pending=1);ap=AP(self.d,[]);st=self.st(r)
        self.assertEqual(KW.retry_enqueue(ap,cfg(),st,{}),0);self.assertEqual(ap.calls,[])
    def test_old_fail_rows_are_not_swept(self):
        # 11-04: 9 S81 FAIL FLOW NOT SUBMITTED kits predate busfit; KW-FIX-6 left them out on purpose
        r=self.rec(status="FAIL",**{"class":"FLOW"},reason="enqueue rc 1: enqueue: NOT SUBMITTED: denied");ap=AP(self.d,[]);st=self.st(r)
        self.assertEqual(KW.retry_enqueue(ap,cfg(),st,{}),0);self.assertEqual(r["status"],"FAIL")
    def test_superseded_block_closed_not_sent(self):
        c=cfg();d=c["dies"]["qwen_kvsys"]
        r=self.rec(enqueue_pending=1,block_sha="old");ap=AP(self.d,[]);st=self.st(r)
        st["plans"]={f"{d['gen_host']}:{d['plan']}|{d['event']}":{"blocks":{"kv3_hg_v1":"new"}}}
        self.assertEqual(KW.retry_enqueue(ap,c,st,{}),0)
        self.assertEqual((r["status"],r["class"]),("CANCELLED","SUPERSEDED"));self.assertEqual(ap.calls,[])
    def test_pending_counts_as_inflight_for_pilot_gate(self):
        c=cfg();r=self.rec(enqueue_pending=1)
        _,live=KW.pilot_classes_state(c["dies"]["qwen_kvsys"],"qwen_kvsys",self.st(r))
        self.assertEqual(sum(live.values()),1)


if __name__=="__main__":unittest.main()

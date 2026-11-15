"""KW-FIX-33 11-08: place_mem_gb_by_item (fnmatch, first match wins) sets one item's PLACE memory in the spec and the
autopilot enqueue --mem; absent = the die's place_mem_gb.  QC hc tap-pair kits need >= 96 GB for their kit LEC."""
import json,tempfile,unittest
from pathlib import Path
from test_kit_wave import KW,cfg
from test_kit_wave_enqueue_retry import AP


class ItemMem(unittest.TestCase):
    def spec(self,c,item):return KW.spec_for(c,"qwen_kvsys",item,"intel2")
    def test_absent_is_die_value(self):
        self.assertEqual(self.spec(cfg(),"kv3_pc")["place_mem_gb"],KW.DEFAULTS["place_mem_gb"])
        self.assertEqual(self.spec(cfg(place_mem_gb=64),"kv3_pc")["place_mem_gb"],64)
        self.assertEqual(KW.place_mem_gb(cfg(place_mem_gb=64),"qwen_kvsys","kv3_pc"),64)
    def test_die_pattern_first_match_wins(self):
        c=cfg(place_mem_gb=48,place_mem_gb_by_item={"sle_hc*":112,"sle_*":80,"slw_hc*":112})
        self.assertEqual(self.spec(c,"sle_hc3")["place_mem_gb"],112)
        self.assertEqual(self.spec(c,"sle_t1")["place_mem_gb"],80)
        self.assertEqual(self.spec(c,"slw_hc0")["place_mem_gb"],112)
        self.assertEqual(self.spec(c,"kv3_pc")["place_mem_gb"],48)
    def test_global_pattern_and_die_precedence(self):
        c=cfg();c["place_mem_gb_by_item"]={"kv3_*":96}
        self.assertEqual(self.spec(c,"kv3_pc")["place_mem_gb"],96)
        c["dies"]["qwen_kvsys"]["place_mem_gb_by_item"]={}
        self.assertEqual(self.spec(c,"kv3_pc")["place_mem_gb"],KW.DEFAULTS["place_mem_gb"])
    def test_input_hash_unchanged(self):
        a=self.spec(cfg(),"sle_hc3");b=self.spec(cfg(place_mem_gb_by_item={"sle_hc*":112}),"sle_hc3")
        self.assertNotEqual(a["place_mem_gb"],b["place_mem_gb"])
        self.assertEqual(KW.input_hash(a),KW.input_hash(b))
    def enq_mem(self,c,item):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"spec.json").write_text(json.dumps(dict(src_sha="abc")))
            r=dict(die="qwen_kvsys",item=item,attempt=1,dir=d,event="event28w_c",geom_dir="/g",kit="intel1:/k/"+item,
                   cells=100,status="PASS",stage="geom")
            ap=AP(d,[(0,"","")]);KW.enqueue_pass(ap,c,{"items":{item:r},"pass_n":0},r,{})
            argv=ap.calls[0];return argv[argv.index("--mem")+1]
    def test_enqueue_mem(self):
        c=cfg(place_mem_gb=48,place_mem_gb_by_item={"sle_hc*":112})
        self.assertEqual(self.enq_mem(c,"sle_hc3"),"112")
        self.assertEqual(self.enq_mem(c,"kv3_pc"),"48")
        self.assertEqual(self.enq_mem(cfg(),"sle_hc3"),str(KW.DEFAULTS["place_mem_gb"]))


if __name__=="__main__":
    unittest.main()

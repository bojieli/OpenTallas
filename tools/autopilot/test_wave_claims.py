import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import copy
import unittest
from unittest.mock import patch
import kit_wave as KW
from test_kit_wave import cfg, OWN

class ProducerClaims(unittest.TestCase):
    def test_parent_expansion_and_allowlist_are_one_producer(self):
        classes={'kv3_pc__claa':'a'*64,'kv3_pc__clbb':'b'*64}
        c=cfg(plan_items_from_allowlist=True,only_items=list(classes),pilot_gate=False)
        rows=[dict(r,last_activity='9999m') for r in KW.parse_owners(OWN) if r['item']=='kv3_pc']
        picked,skip=KW.select(rows,c,'qwen_kvsys',{'items':{}},classes)
        self.assertEqual([r['item'] for r in picked],list(classes))
        self.assertEqual([r['parent_item'] for r in picked],['kv3_pc']*2)
    def test_allowlist_keeps_parent_foreign_live_claim(self):
        classes={'kv3_pc__claa':'a'*64}
        c=cfg(plan_items_from_allowlist=True,only_items=list(classes),pilot_gate=False)
        rows=[dict(r,last_activity='9999m',live_job='foreign live producer') for r in KW.parse_owners(OWN) if r['item']=='kv3_pc']
        picked,skip=KW.select(rows,c,'qwen_kvsys',{'items':{}},classes)
        self.assertEqual(picked,[])
        self.assertIn('live job (another lane)',skip)
    def test_synthetic_class_without_parent_still_selected(self):
        c=cfg(plan_items_from_allowlist=True,only_items=['new__claa'],pilot_gate=False)
        picked,_=KW.select([],c,'qwen_kvsys',{'items':{}},{'new__claa':'a'*64})
        self.assertEqual([r['item'] for r in picked],['new__claa'])
    def test_repeat_launch_retains_exact_active_record(self):
        class AP:
            messages=[]
            @classmethod
            def log(cls,message):cls.messages.append(message)
        c=cfg();r={'item':'kv3_pc','kind':'type','block_sha':'a'*64}
        key=KW.item_key('qwen_kvsys','event28w_c',r['item'],r['block_sha'])
        active={'status':'RUNNING','unit':'original','attempt':16}
        st={'items':{key:copy.deepcopy(active)}}
        with patch.object(KW,'scheduler_current',return_value=True),patch.object(KW,'spec_for',side_effect=AssertionError('must not capture second spec')):
            self.assertIsNone(KW.launch(AP,c,st,'qwen_kvsys',r,'intel2'))
        self.assertEqual(st['items'][key],active)
        self.assertIn('active producer original',AP.messages[-1])

if __name__=='__main__':unittest.main()

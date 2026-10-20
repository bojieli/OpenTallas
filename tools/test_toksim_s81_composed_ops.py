import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import toksim_s81_compose as C

class Composite(unittest.TestCase):
 def setUp(self):
  self.dag=dict(groups=[dict(id='S',kind='layer'),dict(id='W',kind='wave')],nodes=[dict(id='body',group='S',cls='field',op='field',cycles=2,critical=True),dict(id='wave',group='W',cls='wave',op='wave.busy',cycles=5,critical=True)],edges=[dict(src='body',dst='wave',cycles=0)])
  self.base=dict(workloads={'mtp':dict(terms=[],tau=1,T_token_cycles=7,tok_s=1,price_of_record='test')})
  self.ops={('field','field'):dict(cycles=3,tail_priced=1,grade='measured-release-RTL'),('wave','wave.busy'):dict(compose_hook=dict(group='S',exclude=[],handoff_cycles=0),evidence='proof')}
 def test_inherits_grades(self):
  r=C.compose('mtp',self.base,self.dag,self.ops,{})
  self.assertEqual(r['T_cycles_fixed'],8)
  self.assertEqual(r['by_grade']['measured-release-RTL'],6)
  self.assertEqual(r['by_grade']['priced'],2)
  self.assertEqual(r['composed_ops'][0]['cycles'],4)
 def test_recomputes_after_component_change(self):
  self.ops[('field','field')]['cycles']=7
  r=C.compose('mtp',self.base,self.dag,self.ops,{})
  self.assertEqual(r['composed_ops'][0]['cycles'],8)
  self.assertEqual(r['T_cycles_fixed'],16)
 def test_empty_or_recursive_group_rejected(self):
  self.ops[('wave','wave.busy')]['compose_hook']['group']='missing'
  with self.assertRaises(ValueError):C.compose('mtp',self.base,self.dag,self.ops,{})
 def test_real_mtp_matches_component_receipt(self):
  b=json.loads(C.BASE.read_text());ops,slots,xparts,_,_,inserts=C.load_elements(C.OUT/'elements')
  for o in inserts:ops[(o.get('dag_cls'),o['op'])]=o
  d=C.insert_nodes(json.loads(C.DAGS['mtp'].read_text()),inserts)
  r=C.compose('mtp',b,d,ops,slots,xparts)
  waves=r['composed_ops'];self.assertEqual(len(waves),5)
  for w in waves:self.assertAlmostEqual(w['cycles'],47136.2,places=1)
  oldops={k:v for k,v in ops.items() if not v.get('compose_hook')}
  old=C.compose('mtp',b,d,oldops,slots,xparts)
  self.assertAlmostEqual(r['T_cycles_fixed']-old['T_cycles_fixed'],74135.0,places=1)
  self.assertAlmostEqual(sum(r['by_grade'].values()),r['T_cycles_fixed'],places=0)

if __name__=='__main__':unittest.main(verbosity=2)

import copy
import json
from pathlib import Path
import sys
import subprocess
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import toksim_s81_compose as C

class Composite(unittest.TestCase):
 def setUp(self):
  C.EDGES=None
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
  current=C.compose('mtp',b,d,ops,slots,xparts)
  self.assertAlmostEqual(sum(current['by_grade'].values()),current['T_cycles_fixed'],places=0)
  C.EDGES=None
  ops[('field','attn.wq_b')]=json.loads((C.OUT/'elements/WQBG.json').read_text())['ops'][0]
  # Reproduce the source receipt's original two-view GATH input; current32-view result is checked above.
  oldg=copy.deepcopy(ops[('select','attn.gather')]);oldg['per_layer']['L20']=618;oldg['by_old']['819.0']=618
  ops[('select','attn.gather')]=oldg
  ops[('field','attn.a_proj')]=json.loads((C.OUT/'elements/FSMALL.json').read_text())['ops'][0]
  r=C.compose('mtp',b,d,ops,slots,xparts)
  waves=r['composed_ops'];self.assertEqual(len(waves),5)
  for w in waves:self.assertAlmostEqual(w['cycles'],47136.2,places=1)
  oldops={k:v for k,v in ops.items() if not v.get('compose_hook')}
  old=C.compose('mtp',b,d,oldops,slots,xparts)
  self.assertAlmostEqual(r['T_cycles_fixed']-old['T_cycles_fixed'],74135.0,places=1)
  self.assertAlmostEqual(sum(r['by_grade'].values()),r['T_cycles_fixed'],places=0)

 def ledger(self):
  C.EDGES=dict(edge_ledger=dict(CAPC2_PINPIPE=dict(edges=2),CAP_EDLD=dict(edges=24)),included_by_record={'FWOA.json':{'attn.wo_a':dict(CAPC2_PINPIPE=2,CAP_EDLD=24)},'FDOWN.json':{'ffn.down':dict(CAP_EDLD=24)}})
 def test_explicit_included_edges_not_double_charged(self):
  self.ledger()
  add,included=C.edge_delta(dict(id='L0.attn.wo_a',cls='field',op='attn.wo_a'),dict(file='elements/FWOA.json'))
  self.assertEqual(add,{});self.assertEqual(sum(included.values()),26)
  add,included=C.edge_delta(dict(id='L0.ffn.down',cls='field',op='ffn.down'),dict(file='elements/FDOWN.json'))
  self.assertEqual(add,{'CAPC2_PINPIPE':2});self.assertEqual(included,{'CAP_EDLD':24})
 def test_su_qbank_and_merged_ops_not_field_charged(self):
  self.ledger()
  self.assertEqual(C.edge_delta(dict(id='L2.attn.idx.q',cls='field',op='attn.idx.q'))[0],{})
  self.assertEqual(C.edge_delta(dict(id='L2.eng.dot',cls='field',op='eng.dot'),dict(cycles=0))[0],{})
  self.assertEqual(sum(C.edge_delta(dict(id='L2.attn.idx.q_field',cls='field',op='attn.idx.q_field'))[0].values()),26)
 def test_wave_inherits_source_age_cost_once_per_position(self):
  self.ledger();r=C.compose('mtp',self.base,self.dag,self.ops,{})
  self.assertEqual(r['T_cycles_fixed'],60)
  self.assertEqual(r['by_grade']['priced-edge'],52)
  self.assertEqual(r['edge_delta_total'],52)
  self.assertEqual(sum(r['edge_deltas'].values()),52)

 def test_rate_and_percentage_use_same_resolved_path(self):
  self.dag['groups'].append(dict(id='N',kind='other'))
  self.dag['nodes'].append(dict(id='slow',group='N',cls='ctl',op='slow',cycles=100,critical=False))
  self.dag['edges'].append(dict(src='slow',dst='wave',cycles=0))
  r=C.compose('mtp',self.base,self.dag,self.ops,{})
  self.assertEqual(r['T_cycles_fixed'],8);self.assertEqual(r['T_cycles_solved'],104)
  self.assertEqual(r['T_cycles'],104);self.assertLess(r['tok_s'],r['tok_s_fixed'])
  self.assertEqual(r['by_grade']['priced'],101);self.assertEqual(r['by_grade']['measured-release-RTL'],3)
  self.assertAlmostEqual(r['pct_measured'],round(100*3/104,2))
 def test_unqualified_pipeline_is_scenario_only(self):
  ops,_,_,_,excluded,_=C.load_elements(C.OUT/'elements')
  self.assertEqual(C.node_cycles(dict(cycles=1039.9,layer=0),ops[('field','attn.wq_b')])[0],3359)
  self.assertTrue(any(o['grade']=='proposed-component-RTL' for o in excluded))
  baseline=C.build(C.OUT/'elements');proposed=C.build(C.OUT/'elements','wqbp-p126')
  self.assertIn('PROPOSED ONLY',proposed['release_qualification'])
  self.assertNotIn('proposed-component-RTL',baseline['workloads']['ar']['by_grade'])
  self.assertGreater(proposed['workloads']['ar']['by_grade']['proposed-component-RTL'],0)
  before=(C.OUT/'cycles.json').read_bytes()
  p=subprocess.run([sys.executable,str(Path(C.__file__)),'--scenario','wqbp-p126'],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual((C.OUT/'cycles.json').read_bytes(),before)

if __name__=='__main__':unittest.main(verbosity=2)

"""Source control timing/priority/tree and binding tests. No HDL/arithmetic gate."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import model_dsrom_issue_return_calendar as M
OUT=ROOT/'results/rtl/dsrom_issue_return_calendar_prepare_20261002'
class CalendarTests(unittest.TestCase):
 def test_full_forest_single_complete_latency(self):
  roots,r=M.full_return([(0,0,(0,0,0,0,1),'value')])
  self.assertEqual((16256,128),(r['nodes'],r['roots']))
  self.assertEqual(23,r['last_root_retire']);self.assertEqual(1,r['retired_rows']);self.assertEqual(0,r['root_held_end'])
 def test_full_forest_sibling_latency_and_wrong_tag_mutant(self):
  roots,r=M.full_return([(0,0,(0,0,0,0,2),'left'),(0,1,(0,0,1,0,2),'right')])
  self.assertEqual(27,r['last_root_retire']);self.assertEqual(('left','right'),roots[0].rows[0][2])
  roots,bad=M.full_return([(0,0,(0,0,0,0,2),'left'),(0,1,(0,1,1,0,2),'right')])
  self.assertEqual(0,bad['retired_rows']);self.assertEqual(2,bad['root_held_end']) # explicittagDIFF,no crash
 def test_source_root_registered_launch_and_result_priority(self):
  r=M.ReturnRoot()
  for t in range(10):r.step(t,((0,0,t,0,2),'AB'[t]) if t<2 else None)
  self.assertEqual(8,r.rows[0][0]);self.assertEqual(('A','B'),r.rows[0][2])
 def test_segment_event_latency_and_padded_tree(self):
  s=M.Segment()
  for t in range(60):
   s.step(t,(0,0,t==2,'ABC'[t],0) if t<3 else None)
  self.assertEqual([(27,0,0,(('A','B'),'C'))],s.outputs)
  self.assertFalse(s.faults);self.assertFalse(s.have);self.assertEqual(0,sum(s.infl.values()))
 def test_source_boundary_latency_operations(self):
  elem=(ROOT/'rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv').read_text()
  bf=(ROOT/'rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv').read_text()
  for text in ('i1_v <= issue; i2x_v <= i1_v;','i3_v <= i2x_v;','D(LAT)','o_v <= t_v'):
   self.assertIn(text,elem)
  self.assertIn('D(11)',(ROOT/'rtl/v41rom/ot_v41_bterm2_w10.sv').read_text())
  self.assertIn('lv < 4',bf);self.assertIn('v_r <= v;',bf);self.assertIn('D(5)',bf)
 def test_independent_first_XFIFO_witness(self):
  d=json.loads((OUT/'FP4_XFIFO_first_fault_witness.json').read_text())
  self.assertEqual(61,d['pair_control_model']['overflow'][0]['t'])
  q=0;first=None
  for t in range(130):
   p=t in d['independent_recurrence']['push_times'];pop=t in d['independent_recurrence']['pop_times'] and q>0
   if p and q==4 and not pop and first is None:first=t
   q+=int(p)-int(pop)
  self.assertEqual(61,first);self.assertTrue(d['no_expectation_or_source_change'])
 def test_BF_placement_binding(self):
  f=M.I.Field(8192,128,1024,active=6899);hw=set(range(0,8192,8));image={int(i) for i,v in enumerate(f.bf) if v}
  self.assertEqual(243,len(hw&image));self.assertEqual(781,len(image-hw));self.assertEqual(128,sum(not f.act[i] for i in hw))
  full=M.I.Field(8192,128,1024,active=8192);self.assertEqual(hw,{int(i) for i,v in enumerate(full.bf) if v})
 def test_preserved_full_case_scope_and_first_failure(self):
  for name,count in [('fp8_8192x5120_r2.json',8192),('bf16_2048x4096_mtp6_r1.json',12288)]:
   d=json.loads((OUT/name).read_text());self.assertTrue(d['retire_tag_exact']);self.assertEqual(count,d['independent_symbolic_padded_tree_matches']);self.assertFalse(d['independent_symbolic_tree_DIFF'])
   self.assertEqual(16256,d['return']['nodes']);self.assertEqual(128,d['return']['roots'])
  bad=json.loads((OUT/'fp4_4608x2304_mtp6_r1.json').read_text());self.assertFalse(bad['retire_tag_exact']);self.assertTrue(bad['XFIFO_overflow_pairs'])
if __name__=='__main__':unittest.main()

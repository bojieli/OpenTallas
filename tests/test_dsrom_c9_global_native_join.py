import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c9_global_native_join as g
class FullNativeJoin(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=g.B.load(g.BASE/'global_join.json');cls.roots=g.B.load(g.BASE/'root_input_join.json')
 def test_exact_full_source_pools_and_all_masks(self):
  for s,count in [('0',167687),('1',134252)]:
   p=g.B.load(g.BASE/f'inputs/global_shard{s}_problem.json.gz');v=g.B.lines(g.BASE/f'shard{s}_full_native_site_masks.jsonl.gz');c=self.m['cases'][s]
   self.assertEqual(len(v),count);self.assertEqual(len(p['sites']),count);self.assertEqual([r['site'] for r in v],list(range(count)))
   self.assertTrue(all(0<r['A_mask']<(1<<r['A_options']) and 0<r['Y_mask']<(1<<r['Y_options']) for r in v))
   self.assertEqual(c['site_masks_sha256'],g.B.sha(g.BASE/f'shard{s}_full_native_site_masks.jsonl.gz'))
   self.assertEqual(c['frozen_problem_sha256'],g.B.sha(g.BASE/f'inputs/global_shard{s}_problem.json.gz'))
   self.assertEqual(p['node_count'],38383 if s=='0' else 30231)
 def test_root_A_is_explicit_and_no_upstream_invented(self):
  for s,r in self.roots.items():
   self.assertEqual(r['pin'],'A');self.assertEqual(r['instance'],f's{s}_clock_upper_L5_0')
   self.assertEqual(r['neighbor_clear_contact_count'],4);self.assertIsNone(r['upstream_driver_arrival_slew_phase'])
   self.assertFalse(r['physical_build_admitted'])
 def test_failures_empty_only_with_declared_geometric_scope(self):
  for s in ('0','1'):
   self.assertEqual(g.B.lines(g.BASE/f'shard{s}_original_native_contact_failures.jsonl.gz'),[])
   self.assertTrue(self.m['cases'][s]['baseline_unplaced_common_control_not_excluded'])
   self.assertTrue(self.m['cases'][s]['full_reset_clock_waveforms_global_upper_stack_PG_supply_current_and_route_EOLOBS_not_qualified'])
  self.assertTrue(self.m['source_graph_and_counts_unchanged']);self.assertFalse(self.m['second_solver_launched']);self.assertFalse(self.m['physical_build_admitted'])
 def test_index_covers_wide_cells_and_both_sides_of_boundary(self):
  cells=[dict(bbox_DBU=[539,269,1081,541]),dict(bbox_DBU=[2000,0,2100,270])];idx=g.neighbors_index(cells)
  self.assertEqual({k for k,v in idx.items() if 0 in v},{(x,y) for x in (0,1,2) for y in (0,1,2)})
  self.assertEqual([k for k,v in idx.items() if 1 in v],[(3,0)])
if __name__=='__main__':unittest.main()

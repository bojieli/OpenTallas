import gzip,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c9_selected_clock_access as g
class SelectedAccess(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.x=json.loads((g.BASE/'model.json').read_text())
 def test_exact_selected_candidate_and_single_bank(self):
  x=self.x;self.assertEqual(x['selected_source_commit'],'c9d19ed598077e4a4941c8548273f15deefb8c1a')
  self.assertEqual(x['selected_selector_bank']['source_commit'],'d4a3deb550aa71afec39e0549adb0e0a7f4c2894')
  self.assertEqual(x['selected_selector_bank']['core_clock70406'],70406);self.assertEqual(x['prior51ae_annex_charge_mm2'],0)
  self.assertEqual(x['source_relay_and_pad_count'],68614);self.assertEqual(x['additional_bank_or_cells'],0)
 def test_optimistic_nearest_matches_exhaustive_literal_rectangle_distance(self):
  source=[dict(bbox_DBU=[0,0,20,40]),dict(bbox_DBU=[15,25,50,60])]
  rows={(60,90,10):[(70,'a'),(120,'b')],(100,130,30):[(-80,'c'),(40,'d'),(90,'e')]};C={'M8':.103962,'M9':.0928446}
  actual=g.nearest_pin_lower_bound(source,rows,C)
  brute=min((g.gap(s['bbox_DBU'][0],s['bbox_DBU'][2],x,x+w)*C['M8']+g.gap(s['bbox_DBU'][1],s['bbox_DBU'][3],y,Y)*C['M9'])/1000 for s in source for (y,Y,w),items in rows.items() for x,name in items)
  self.assertAlmostEqual(actual['optimistic_M8_M9_metal_C_fF'],brute)
  indexed={key:[p[0] for p in value] for key,value in rows.items()}
  self.assertEqual(actual,g.nearest_pin_lower_bound(source,rows,C,indexed))
 def test_rectangle_overlap_has_zero_optimistic_distance_not_assumed_native_access(self):
  p=g.nearest_pin_lower_bound([dict(bbox_DBU=[10,10,20,20])],{(15,25,20):[(15,'a')]},{'M8':1,'M9':2})
  self.assertEqual(p['optimistic_M8_M9_metal_C_fF'],0)
 def test_all_relay_branches_counted_with_selected_counts_and_necessary_failures(self):
  self.assertEqual([self.x['shards'][s]['selected_correction_site_count'] for s in ['0','1']],[38383,30231])
  for s in ['0','1']:
   c=self.x['shards'][s];branches=g.load(f'shard{s}_clock_branches.json.gz')
   self.assertEqual(c['relay_branches_checked'],sum(b['proposed_relay_BUF']>0 for b in branches))
   p=g.BASE/f'shard{s}_first_hop_deficits.json.gz';v=json.loads(gzip.decompress(p.read_bytes()))
   self.assertEqual(g.sha(p),c['artifact_sha256']);self.assertEqual(len(v),c['branches_with_no_first_hop_site_inside_selected_metal_budget'])
   self.assertTrue(all(r['optimistic_M8_M9_metal_C_fF']>r['first_branch_metal_budget_fF'] for r in v))
   self.assertTrue(all(r['source_contact_stub_budget_preserved'] for r in v))
 def test_branch_budget_is_actual_source_half_wire_divided_by_fanout(self):
  for s in ['0','1']:
   b={(r['net'],r['destination']):r for r in g.load(f'shard{s}_clock_branches.json.gz')}
   v=json.loads(gzip.decompress((g.BASE/f'shard{s}_first_hop_deficits.json.gz').read_bytes()))
   for r in v:
    a=b[(r['net'],r['destination'])]
    self.assertAlmostEqual(r['first_branch_metal_budget_fF'],a['first_driver_total_wire_budget_fF']/2/a['source_fanout'])
 def test_inventory_extent_is_not_complete_distributed_tree(self):
  for s in ['0','1']:
   c=self.x['shards'][s];a=c['selected_site_y_range_DBU'];b=c['raw_bbox_DBU']
   self.assertLess(a[1]-a[0],(b[3]-b[1])/3)
   self.assertTrue(c['one_to_one_assignment_not_attempted_if_necessary_bound_fails'])
 def test_source_pins_match_and_no_admission_or_architecture_minimum_claim(self):
  for r in self.x['source_origins']:self.assertEqual(g.sha(g.BASE/'inputs'/r['copy']),r['sha256'])
  self.assertFalse(self.x['physical_build_admitted']);self.assertFalse(self.x['clock_reset_PG_or_escape_qualified'])
  self.assertTrue(self.x['actual_consumer_deadline_not_supplied']);self.assertEqual(self.x['new_jobs'],[])
  self.assertIn('no architecture impossibility claim',self.x['rejection_scope'])
 def test_raw_rectangle_cut_requires_outside_sites_not_added_buffers(self):
  for s in ['0','1']:
   c=self.x['shards'][s];v=c['raw_only_first_hop_cut_witnesses']
   self.assertEqual(c['minimum_first_relay_BUF_sites_outside_raw_rectangle_at_unchanged_source_graph'],len(v))
   self.assertGreater(len(v),0);self.assertTrue(all(r['optimistic_C_to_any_point_in_raw_rectangle_fF']>r['first_branch_metal_budget_fF'] for r in v))
   self.assertAlmostEqual(c['minimum_buffer_body_to_relocate_outside_raw_um2'],len(v)*.10206)
   self.assertEqual(c['additional_BUF_count'],0)
if __name__=='__main__':unittest.main()

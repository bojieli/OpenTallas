import collections,gzip,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c9_clock_branch_site_binding as g
import dsrom_c9_clock_assignment_access as a
class IndependentDiagnostic(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.ART=g.BASE/'attempt_r4_independent_assignment'
  cls.model=g.load(cls.ART/'model.json');cls.access=g.load(cls.ART/'access_model.json')
  cls.cells={s:g.lines(cls.ART/f'shard{s}_assigned_cells.jsonl.gz') for s in ('0','1')}
  cls.edges={s:g.lines(cls.ART/f'shard{s}_assigned_edges.jsonl.gz') for s in ('0','1')}
  cls.C=g.load(g.CUT/'inputs/model.json')['restricted_route_family_RC_fF_per_um']
 def test_exact_graph_bank_count_and_no_annex(self):
  self.assertEqual(self.model['source_c9'],'c9d19ed598077e4a4941c8548273f15deefb8c1a')
  self.assertEqual(self.model['preserved_selector_bank']['source_commit'],'d4a3deb550aa71afec39e0549adb0e0a7f4c2894')
  self.assertEqual(self.model['preserved_selector_bank']['core_clock70406'],70406)
  self.assertEqual([len(self.cells[s]) for s in ('0','1')],[38383,30231])
  for key in ('added_BUF','removed_BUF','annex_charge_mm2'):self.assertEqual(self.model[key],0)
 def test_contract_every_assigned_branch_to_original_source_and_sink(self):
  for s in ('0','1'):
   branches=g.load(g.CUT/f'inputs/shard{s}_clock_branches.json.gz');pads,D=g.topology(branches)
   groups=collections.defaultdict(list)
   for e in self.edges[s]:groups[(e['branch_net'],e['destination'])].append(e)
   orig={n['name']:n for n in g.lines(g.OLD/f'shard{s}_clock_nets.jsonl.gz')}
   expected=0
   for b in branches:
    n=b['proposed_relay_BUF']+pads[(b['net'],b['destination'])]
    if n==0:continue
    expected+=1;ee=sorted(groups[(b['net'],b['destination'])],key=lambda e:e['ordinal'])
    self.assertEqual(len(ee),n+1);self.assertEqual(ee[0]['source'],orig[b['net']]['source'])
    self.assertEqual(ee[-1]['sink'],next(v for v in orig[b['net']]['sinks'] if v['instance']==b['destination']))
    for x,y in zip(ee,ee[1:]):self.assertEqual(x['sink']['instance'],y['source']['instance'])
   self.assertEqual(len(groups),expected)
 def test_literal_pin_bound_every_edge_and_source_fanout_budget(self):
  for s in ('0','1'):
   branches={(b['net'],b['destination']):b for b in g.load(g.CUT/f'inputs/shard{s}_clock_branches.json.gz')}
   for e in self.edges[s]:
    self.assertLessEqual(g.literal_cap(e['source']['literal_rectangles'],e['sink']['literal_rectangles'],self.C),e['metal_budget_fF']+1e-8)
    if e['ordinal']==0:
     b=branches[(e['branch_net'],e['destination'])];self.assertAlmostEqual(e['metal_budget_fF'],b['first_driver_total_wire_budget_fF']/2/b['source_fanout'])
 def test_distinct_legal_sites_original_body_and_local_supply_union(self):
  for s in ('0','1'):
   cells=self.cells[s];self.assertEqual(len({p['instance'] for p in cells}),len(cells));self.assertEqual(len({tuple(p['bbox_DBU']) for p in cells}),len(cells))
   self.assertTrue(all(p['master']==g.BUF for p in cells))
   self.assertEqual(self.access['cases'][s]['fixed_height_row_overlap_pairs'],[])
   self.assertEqual(self.access['cases'][s]['literal_M1_supply_missing'],[])
   self.assertTrue(self.access['cases'][s]['PG_upfeed_current_IR_EM_not_qualified'])
 def test_real_native_via_enclosure_filters_horizontal_pin_slivers(self):
  via=[-9,-11,9,11]
  self.assertEqual(a.contact_centers([dict(layer='M1',bbox_DBU=[0,0,212,18])],via),[])
  self.assertEqual(a.contact_centers([dict(layer='M1',bbox_DBU=[0,0,18,144])],via),[dict(layer='M1_contact_centers',bbox_DBU=[9,11,9,133])])
 def test_native_contact_failure_is_retained_and_not_timing_claim(self):
  for s in ('0','1'):
   v=g.lines(self.ART/f'shard{s}_enclosed_VIA12_failures.jsonl.gz');c=self.access['cases'][s]
   self.assertEqual(len(v),c['enclosed_VIA12_failures'])
   self.assertTrue(all(r['enclosed_VIA12_M8_M9_lower_bound_fF'] is None or r['enclosed_VIA12_M8_M9_lower_bound_fF']>r['budget_fF'] for r in v))
  self.assertFalse(self.access['physical_build_admitted']);self.assertFalse(self.access['actual_root_skew_and_reset_release_qualified'])
 def test_logical_depth_and_complete_pad_census_no_capture_cycle_change(self):
  for s,relay,pad,depth in [('0',24500,13883,25),('1',19449,10782,23)]:
   roles=collections.Counter(p['role'] for p in self.cells[s]);self.assertEqual(roles,dict(relay=relay,depth_pad=pad))
   self.assertEqual(self.model['cases'][s]['logical_source_root_cell_depth'],depth)
   self.assertTrue(self.model['cases'][s]['equal_depth_not_skew'])
  self.assertFalse(self.model['clock_or_capture_cycle_change']);self.assertFalse(self.model['physical_build_admitted'])
 def test_evidence_hashes_and_preserved_negative_attempts(self):
  for r in g.load(g.BASE/'inputs/origins.json'):self.assertEqual(g.sha(g.BASE/'inputs'/r['copy']),r['sha256'])
  for s in ('0','1'):
   c=self.model['cases'][s]
   self.assertEqual(c['cell_artifact_sha256'],g.sha(self.ART/f'shard{s}_assigned_cells.jsonl.gz'))
   self.assertEqual(c['edge_artifact_sha256'],g.sha(self.ART/f'shard{s}_assigned_edges.jsonl.gz'))
   self.assertEqual(c['assignment_failures'],0)
  old=g.load(g.BASE/'attempt_r1/model.json');self.assertEqual([old['cases'][s]['assignment_failures'] for s in ('0','1')],[358,294])
  old=g.load(g.BASE/'attempt_r3_centroid_matching/model.json');self.assertEqual([old['cases'][s]['assignment_failures'] for s in ('0','1')],[320,256])
  self.assertFalse(g.load(g.BASE/'attempt_r2_tool_failure/receipt.json')['physical_failure'])
class SelectedSuccessor(unittest.TestCase):
 def test_selected_source_and_entire_site_set_locked(self):
  m=g.load(g.BASE/'model.json')
  self.assertEqual(m['selected_reallocation_source_commit'],'53dfdf1c9d2bdc4d6a88a24fd785529b1ffad75d')
  self.assertTrue(m['selected_first_relay_sites_locked']);self.assertTrue(m['selected_entire_site_inventory_unchanged'])
  for s in ('0','1'):
   sites=g.load(g.BASE/f'inputs/selected_shard{s}_sites.json.gz');cells=g.lines(g.BASE/f'shard{s}_assigned_cells.jsonl.gz')
   allowed={(tuple(v['bbox_DBU']),v['orientation']) for v in sites}
   self.assertTrue(all((tuple(p['bbox_DBU']),p['orientation']) in allowed for p in cells))
   locked={(p['branch_net'],p['branch_destination']):p for p in sites if p['role']=='first_relay'}
   first={(p['source_net'],p['destination']):p for p in cells if p['ordinal']==0}
   for key,p in locked.items():
    self.assertEqual(first[key]['bbox_DBU'],p['bbox_DBU']);self.assertEqual(first[key]['orientation'],p['orientation'])
 def test_selected_failure_keeps_pad_only_common_cut_and_no_admission(self):
  m=g.load(g.BASE/'model.json')
  for s,count in [('0',320),('1',256)]:
   f=g.load(g.BASE/f'shard{s}_assignment_failures.json')
   self.assertEqual(sum(p.get('domain')=='common' and p.get('candidate_sites')==0 for p in f),4)
   self.assertEqual(sum(p.get('reason')=='selected_first_hop_fails_combined_first_and_remaining_reach' for p in f),count)
   self.assertEqual(len(f),m['cases'][s]['assignment_failures'])
   self.assertLess(m['cases'][s]['assigned_BUF_count'],m['cases'][s]['expected_existing_BUF_count'])
  self.assertFalse(m['physical_build_admitted']);self.assertEqual(m['annex_charge_mm2'],0)
 def test_access_record_matches_current_assignment_not_diagnostic(self):
  a=g.load(g.BASE/'access_model.json');self.assertEqual(a['source_assignment_sha256'],g.sha(g.BASE/'model.json'))
  self.assertFalse(a['physical_build_admitted'])
if __name__=='__main__':unittest.main()


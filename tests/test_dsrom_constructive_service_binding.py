import importlib.util
import unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('binding',Path(__file__).resolve().parents[1]/'tools/dsrom_constructive_service_binding.py')
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
class ServiceBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model,cls.field,cls.shapes=m.build()
 def test_disjoint_refuses_overlap_not_abutting(self):
  m.disjoint([('a',[0,0,10,10]),('b',[10,0,20,10])])
  with self.assertRaises(ValueError):m.disjoint([('a',[0,0,10,10]),('b',[9,0,20,10])])
 def test_actual_counts_and_immutable_ids_preserved(self):
  self.assertEqual(len(self.field),4096)
  self.assertEqual(sum(x['physical4096_leaves'] for x in self.field),16384)
  self.assertEqual(self.model['representative']['HE_source_record']['pairs'],[1792,1824,1856,1888,1920,1952,1984,2016])
  self.assertEqual(len(self.model['representative']['HE_leaf_bodies']),32)
 def test_all_named_reservations_disjoint_and_charged(self):
  r=self.model['representative'];self.assertTrue(r['no_inherited_or_residual_charge_removed'])
  rows=[('pair'+str(x['pair_id']),x['bbox_DBU']) for x in self.field]
  additional=r['additional_disjoint_named_rectangles']
  self.assertEqual(len(additional),4)
  self.assertTrue(all(x['reserved_mm2']>=x['priced_mm2'] for x in additional))
  self.assertLess(max(x['bbox_DBU'][3] for x in additional),16000000)
  m.disjoint(rows+[(x['name'],x['bbox_DBU']) for x in additional])
 def test_source_BF_predicate_not_contiguous_prefix(self):
  bf={x['pair_id'] for x in self.field if x['source_class']=='BF16_column_pair'}
  self.assertEqual(len(bf),724)
  self.assertIn(4090,bf)
  self.assertNotEqual(bf,set(range(724)))
 def test_oriented_pin_translation(self):
  self.assertEqual(m.translate([1,2,3,4],100,200,[10,20],'MX'),[101,216,103,218])
  self.assertEqual(m.translate([1,2,3,4],100,200,[10,20],'MY'),[107,202,109,204])
  self.assertEqual(m.translate([1,2,3,4],100,200,[10,20],'R180'),[107,216,109,218])
 def test_actual_LEF_pins_and_PG_included(self):
  uses={r.get('use') for r in self.shapes if r['kind']=='pins'}
  self.assertTrue({'POWER','GROUND','SIGNAL','CLOCK'}<=uses)
  self.assertEqual({r['layer'] for r in self.shapes if r['kind']=='OBS'}, {'M1','M2','M3','M4'})
 def test_ledger_not_containment_credit(self):
  a=self.model['inherited_area_reconciliation']
  self.assertAlmostEqual(sum(a['source_equation_terms_mm2'].values()),418.26916414007)
  self.assertAlmostEqual(a['service_rectangle_union_mm2'],131.24731428864)
  self.assertEqual(a['containment_credit_mm2'],0)
 def test_actual_capacity_never_equals_half_reserve(self):
  c=self.model['collector']
  self.assertEqual(c['old_assumed_half_reserve_margin'],4)
  self.assertEqual(c['maximum_additional_blocked_tracks_for_screen'],20918)
  self.assertFalse(c['percentage_reserve_used'])
  self.assertIsNone(c['admissible_capacity'])
  self.assertFalse(self.model['physical_GO'])
 def test_HBM_PG_not_transferred_to_ROM(self):
  r=self.model['retained_ODB_scope']
  self.assertEqual(r['die_DBU'],[0,0,1400000,1640000])
  self.assertFalse(r['current_ROM_exclusion_credit'])
  self.assertGreater(sum(r['PG_shape_counts'].values()),1000000)
if __name__=='__main__':unittest.main()

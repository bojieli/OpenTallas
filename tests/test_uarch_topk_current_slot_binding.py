import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_current_slot_binding as M

class SlotBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full,_=M.load(ROOT,M.FULL,M.PATHS['full'])
        cls.parent,_=M.load(ROOT,M.PARENT,M.PATHS['parent'])
        cls.policy,_=M.load(ROOT,M.POLICY,M.PATHS['policy'])
    def test_complete_area_deficit_and_no_admission(self):
        r=M.reconcile(self.full,self.parent,self.policy)
        self.assertAlmostEqual(r['uncovered_complete_proxy_mm2'],0.17199693576)
        self.assertAlmostEqual(r['complete_proxy_extra_over_current_charged_proxy_mm2'],0.17358111108)
        self.assertFalse(r['area_pass']);self.assertFalse(r['engine_RTL_admitted']);self.assertFalse(r['PR_admitted'])
        self.assertEqual(r['clock_branch_basis'],{'ss':15,'ff':17})
    def test_minimum_box_really_contains_area_and_no_location_admission(self):
        r=M.reconcile(self.full,self.parent,self.policy);b=r['minimum_area_only_bbox_DBU']
        area=(b[2]-b[0])*(b[3]-b[1])/1e12
        self.assertGreaterEqual(area,r['required_complete_construction_proxy_mm2'])
        self.assertLess(area-r['required_complete_construction_proxy_mm2'],(b[2]-b[0])/1e12)
        self.assertTrue(r['minimum_bbox_is_not_placement_or_corridor_acceptance'])
    def test_corrupted_current_bbox_refused(self):
        p=copy.deepcopy(self.parent);p['selector']['single_full_slot_bbox_DBU'][3]+=1
        with self.assertRaisesRegex(ValueError,'area mismatch'):M.reconcile(self.full,p,self.policy)
    def test_larger_area_never_grants_clock_or_route_admission(self):
        p=copy.deepcopy(self.parent);b=p['selector']['single_full_slot_bbox_DBU'];b[3]+=200000
        p['selector']['reserved_rectangle_mm2']=(b[2]-b[0])*(b[3]-b[1])/1e12
        r=M.reconcile(self.full,p,self.policy)
        self.assertTrue(r['area_pass']);self.assertFalse(r['PR_admitted']);self.assertFalse(r['engine_RTL_admitted'])
    def test_pooled_local_tau_not_headline(self):
        r=M.reconcile(self.full,self.parent,self.policy)
        self.assertTrue(r['MTP_headline']['numeric_provenance_pending']);self.assertIsNone(r['MTP_headline']['qualified_rate'])
        p=copy.deepcopy(self.policy);p['headline_qualified_rate']=3001
        with self.assertRaisesRegex(ValueError,'policy'):M.reconcile(self.full,self.parent,p)

if __name__=='__main__':unittest.main()

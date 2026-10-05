import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w10_conditional_interface_audit as a

class ConditionalInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads(json.dumps(a.size()))
        cls.result=a.audit(cls.model)

    def test_all_conditional_joins_are_rectangles(self):
        self.assertEqual(self.result['classifications']['connected_pin_union_RECTONLY'],{'PROVABLE':1152})
        self.assertFalse(self.result['physical_admission'])
        self.assertEqual(self.model['current_fixed_density_budget']['rows'],617)
        self.assertEqual(self.model['capture_boundary']['width_sites'],192)
        self.assertEqual(self.model['physical_ICGs'],8)

    def test_bad_density_receipt_rejected(self):
        bad=copy.deepcopy(self.model);bad['current_fixed_density_budget']['density']=.51
        with self.assertRaisesRegex(ValueError,'sizing receipt mismatch'):
            a.audit(bad)

    def test_phase_shift_restores_union_refutation(self):
        data=list(a.inputs());data[0]=copy.deepcopy(data[0])
        for m in data[0]['conditional']['macros']:
            if m['orientation'] in {'MX','R180'}:
                m['bbox_nm'][1]+=6;m['bbox_nm'][3]+=6
        with patch.object(a,'inputs',return_value=tuple(data)):
            result=a.audit(self.model)
        self.assertEqual(result['classifications']['connected_pin_union_RECTONLY'],{'PROVABLE':576,'REFUTED':576})
        self.assertTrue(any(r['constraints']['connected_pin_union_RECTONLY']['witness']['pin_nm'] for r in result['records'] if r['orientation']=='MX'))

    def test_candidate_power_collision_negative(self):
        phase,local,slot,dims,ports,obs,via,tracks,_=a.inputs()
        shapes=a.E.escape_shapes(ports,dims,phase['conditional']['macros'],tracks,via)
        m5=shapes[0]['rects']['M5']
        # Deliberate local power-metal insertion at a signal landing. No source
        # PDN edited, no offset search or alternate candidate constructed.
        original=a.candidate_stripes
        def inserted(*args,**kwargs):
            return original(*args,**kwargs)+[dict(rect_nm=m5,center_x_nm=(m5[0]+m5[2])//2,phase=-1,index=-1)]
        with patch.object(a,'candidate_stripes',side_effect=inserted):
            model=json.loads(json.dumps(a.size()))
            result=a.audit(model)
        self.assertGreater(result['classifications']['M5_source_stripe_PRL_bound'].get('REFUTED',0),0)
        witness=next(r['constraints']['M5_source_stripe_PRL_bound'] for r in result['records'] if r['constraints']['M5_source_stripe_PRL_bound']['classification']=='REFUTED')
        self.assertTrue(witness['witness']['conflicts'])

    def test_source_keepout_growth_updates_bound(self):
        text=(ROOT/a.E.OUT/'actual_db.lef').read_text()
        self.assertEqual(a.source_rect_bound(text,'M4'),48)
        self.assertEqual(a.source_rect_bound(text.replace('0.048','0.096'),'M4'),96)

    def test_missing_keepout_rule_cannot_be_waived(self):
        text=(ROOT/a.E.OUT/'actual_db.lef').read_text().replace('LEF58_EOLKEEPOUT','UNKNOWN_PROPERTY')
        with self.assertRaisesRegex(ValueError,'missing actual rectangular rule'):
            a.source_rect_bound(text,'M4')

    def test_generated_PG_and_clock_qualification_remain_missing(self):
        for r in self.result['records']:
            for key in ['candidate_generated_PG','Vx_EOL_specific_enclosure','capture_mux_clock_SSFF']:
                self.assertEqual(r['constraints'][key]['classification'],'MISSING')
        self.assertTrue(all(c['after_120nm_PG_72nm_spacing_24nm_wire']>=239 for c in self.model['channels']))

if __name__=='__main__':unittest.main(verbosity=2)

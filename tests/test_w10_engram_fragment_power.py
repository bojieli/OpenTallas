import copy
import json
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_engram_fragment_power import build
from tools.w10_engram_192_power import read,typed_inputs
class FragmentPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,_=read('ca5a444d0934833f2e9f16096cb368fadab16aee','results/quality/w16_engram_rom_constructive_home_20261001/two_fragment_contract_consumed_once.json')
        cls.p,cls.k,cls.a,_,_=typed_inputs(Path('/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1'))
        cls.x=build(cls.c,cls.p,cls.k,cls.a)
    def test_all_physical_endpoints_and_old_cones(self):
        self.assertEqual(self.x['aggregate_FF_bits'],3595629118)
        self.assertEqual(self.x['aggregate_new_FF_bits'],1522003968)
        self.assertEqual(self.x['actual_macros'],1500067)
        for h,s in zip(self.x['homes'],self.c['homes']):
            p=h['priced_reservation']
            self.assertEqual(p['total_NAND2_cells'],4*(p['FF_bits']+s['preserved_response_MUX2_bits'])+2*s['request_demux_AND2_bits'])
        c=copy.deepcopy(self.c);c['homes'][0]['new_fragment_reassembly_and_control_FF_bits']=318*49
        with self.assertRaises(ValueError):build(c,self.p,self.k,self.a)
    def test_typed_static_is_not_actual_admission(self):
        self.assertGreater(D(self.x['homes'][0]['clock_plus_leak_W']),D(319))
        self.assertGreater(D(self.x['all192_ungated_clock_W']),D(60000))
        for k in ('physical_admission','actual_power_qualified','selected_data_energy_qualified'):self.assertFalse(self.x[k])
        self.assertEqual(self.x['historical_power_subtraction_W'],0)
        self.assertEqual(self.x['root_stop_credit'],0)
        self.assertEqual(self.x['max_conditional_row_cycles'],2360)
    def test_receipt_matches_computed_fields(self):
        x=json.loads(Path('results/uarch/w10_engram_fragment_power_r1/budget.json').read_text())
        for k,v in self.x.items():self.assertEqual(x[k],v)

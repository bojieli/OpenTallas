import copy
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_engram_epoch32_power import build
from tools.w10_engram_192_power import read,typed_inputs
class EpochPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,_=read('9ef36f6542cc91b1a48ff274101372d063c580ef','results/quality/w16_engram_rom_constructive_home_20261001/epoch32_fragment_contract.json')
        cls.p,cls.k,cls.a,_,_=typed_inputs(Path('/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1'))
        cls.x=build(cls.c,cls.p,cls.k,cls.a)
    def test_full_inventory_no_old_margin(self):
        self.assertEqual(self.x['aggregate_FF_bits'],4361491198)
        self.assertEqual(self.x['image_session_row_state_FF_bits'],73920)
        self.assertEqual(self.x['all_old_FF_retained'],2073625150)
        self.assertGreater(D(self.x['homes'][0]['clock_plus_leak_W']),D(369))
        self.assertLess(D(self.x['homes'][0]['margin_before_data_control_hub_PHY_W']),D(106))
        for r in self.x['homes']:
            s=r['source_state'];p=r['priced_reservation']
            self.assertEqual(p['total_NAND2_cells'],4*(p['FF_bits']+s['preserved_response_MUX2_bits'])+2*s['request_demux_AND2_bits'])
    def test_missing_request_setup_rejected(self):
        c=copy.deepcopy(self.c);c['state_inventory']['homes'][0]['request_setup_FF_bits']=0
        with self.assertRaises(ValueError):build(c,self.p,self.k,self.a)
    def test_no_physical_or_average_power_claim(self):
        for k in ('physical_admission','actual_power_qualified','selected_data_energy_qualified','fullE32_setup_and_fourphase_ACK_actual_provider'):self.assertFalse(self.x[k])
        self.assertEqual(self.x['macro_CE_clock_credit_W'],0)
        self.assertEqual(self.x['historical_power_subtraction_W'],0)
        self.assertIsNone(self.x['whole_token_latency_cycles'])

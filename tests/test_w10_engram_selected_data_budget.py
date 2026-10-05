import copy
import json
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_engram_selected_data_budget import budget
from tools.w10_engram_192_power import read, typed_inputs

class SelectedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract,_=read('c8ea5395d','results/quality/w16_engram_rom_constructive_home_20261001/repacked_192_enable_mask_contract.json')
        cls.power,cls.clock,cls.area,_,_=typed_inputs(Path('/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1'))
        cls.x=budget(cls.contract,cls.power,cls.clock,cls.area)
    def test_both_children_and_disabled_hold_are_charged(self):
        e=self.x['per_lookup_event_counts']
        self.assertEqual(e['both_child_demux_raw_input_events'],1924)
        self.assertEqual(e['disabled_feedback_MUX_D_raw_input_events'],962)
        self.assertEqual(e['NAND_raw_input_events_upper'],sum(e[k] for k in ('feedback_NAND_raw_input_events','demux_NAND_raw_input_events','selected_response_MUX_NAND_raw_input_events','disabled_feedback_MUX_D_raw_input_events')))
        c=copy.deepcopy(self.contract)
        c['finite_runtime_transition_bounds_per_lookup']['inactive_request_sibling_raw_input_bit_transitions_upper']+=100
        y=budget(c,self.power,self.clock,self.area)
        self.assertGreater(D(y['per_lookup_data_energy_allocation_J']['total_including_ceiling']),D(self.x['per_lookup_data_energy_allocation_J']['total_including_ceiling']))
        self.assertEqual(y['all192_ungated_clock_W'],self.x['all192_ungated_clock_W'])
    def test_current_inventory_and_no_ce_clock_credit(self):
        self.assertEqual(self.x['aggregate_FF_bits'],2073625150)
        self.assertTrue(self.x['all_macro_clock_internal_energy_retained'])
        self.assertGreater(D(self.x['all192_ungated_clock_W']),D(41068))
    def test_conditional_not_serialized_admission(self):
        self.assertFalse(self.x['physical_admission'])
        self.assertFalse(self.x['physical_data_provider_proven'])
        self.assertFalse(self.x['serialized_256_model_data_qualified'])
        self.assertEqual(self.x['root_stop_credit'],0)
        self.assertIsNone(self.x['whole_token_average_power_W'])
        self.assertEqual(json.loads(Path('results/uarch/w10_engram_selected_data_budget_r1/budget.json').read_text())['per_lookup_event_counts'],self.x['per_lookup_event_counts'])

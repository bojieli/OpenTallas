import copy
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_engram_sync_drain_power import build
from tools.w10_engram_192_power import read,typed_inputs
class SyncDrainPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,_=read('5b8c456a34965043ae9c6656725ca0565a5ce905','results/quality/w16_engram_rom_constructive_home_20261001/sync_branch_drain_inventory.json')
        cls.prior,_=read('e3a1a53db','results/uarch/w10_engram_epoch32_power_r1/budget.json')
        cls.p,cls.k,cls.a,_,_=typed_inputs(Path('/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1'))
        cls.x=build(cls.c,cls.prior,cls.p,cls.k,cls.a)
    def test_complete_declared_roles_and_branch_gates(self):
        self.assertEqual(self.x['conditional_total_FF_bits'],4378995838)
        self.assertEqual(self.x['added_FF_bits'],17504640)
        self.assertEqual(self.x['additional_branch_NAND2_cells'],20444736)
        self.assertEqual(self.x['homes'][0]['additional_branch_gates']['NAND2_cells_per_home'],106483)
        self.assertGreater(D(self.x['homes'][0]['clock_plus_all_leak_W']),D(370))
    def test_nonzero_disabled_pin_and_no_qualified_saving(self):
        g=self.x['homes'][0]['additional_branch_gates']
        self.assertGreater(D(g['data_input_pin_full_activity_upper_W']),0)
        for k in ('physical_admission','complete_inventory','actual_power_qualified','reservation_is_minimum','selected_data_qualified'):self.assertFalse(self.x[k])
        self.assertEqual(self.x['historical_power_subtraction_W'],0)
        self.assertEqual(self.x['root_stop_credit'],0)
    def test_missing_idle_state_cannot_pass_inventory(self):
        c=copy.deepcopy(self.c);c['control_storage']['per_home_roles']['registered_leaf_idle']=0
        with self.assertRaises(ValueError):build(c,self.prior,self.p,self.k,self.a)

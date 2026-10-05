import copy
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_engram_ack_queue_power import build
from tools.w10_engram_192_power import read,typed_inputs
class AckQueuePowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,_=read('ddc93f3789ef2b3b7d1313a5512797334a3a3f3f','results/quality/w16_engram_rom_constructive_home_20261001/epoch32_ACK_source_receipts.json')
        cls.prior,_=read('e3a1a53db','results/uarch/w10_engram_epoch32_power_r1/budget.json')
        cls.p,cls.k,cls.a,_,_=typed_inputs(Path('/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1'))
        cls.x=build(cls.c,cls.prior,cls.p,cls.k,cls.a)
    def test_all_queues_clocked(self):
        self.assertEqual(self.x['aggregate_provisional_FF_bits'],4844894974)
        self.assertEqual(self.x['aggregate_ACK_extra_FF_bits'],483403776)
        self.assertGreater(D(self.x['homes'][0]['clock_plus_leak_W']),D(400))
        for r in self.x['homes']:self.assertEqual(r['ACK_queue_extra_FF_bits'],24928*101)
    def test_incomplete_not_admission(self):
        for k in ('complete_state_inventory','physical_admission','actual_power_qualified','actual_ACK_transport_provider'):self.assertFalse(self.x[k])
        self.assertEqual(self.x['historical_power_subtraction_W'],0)
        self.assertIsNone(self.x['whole_token_average_power_W'])
    def test_stale_inventory_fails(self):
        p=copy.deepcopy(self.prior);p['aggregate_FF_bits']=3595629118
        with self.assertRaises(ValueError):build(self.c,p,self.p,self.k,self.a)

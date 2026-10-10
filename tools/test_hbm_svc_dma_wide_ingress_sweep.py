import unittest
from hbm_svc_dma_wide_ingress_sweep import sweep,native_inventory


class IngressInventoryTests(unittest.TestCase):
    def test_all_beats_are_reserved_and_protected_storage_is_additive(self):
        i,_=native_inventory()
        self.assertFalse(i['native_return_backpressure_allowed'])
        self.assertTrue(i['reserve_every_burst_beat_before_native_issue'])
        self.assertEqual(i['entries_per_PC'],4*32)
        self.assertEqual(i['protected_storage_bits_per_PC'],128*(256+32+30))
        s=sweep()
        self.assertEqual(s['storage']['total_protected_bits_per_pc'],40704)
        self.assertTrue(s['storage']['additional_to_cache_context_and_native_CAM'])
        self.assertEqual(s['current_total_fit'].split(':')[0],'UNKNOWN')
        self.assertFalse(s['route_admission'])
        self.assertFalse(s['bulk_jobs_launched'])
        self.assertIsNone(s['storage']['logic_area_um2'])
        typed=[p for p in s['points'] if p['ingress_FF_policy']=='data_ECC_unreset_metadata_reset']
        self.assertEqual(len(typed),3)
        for p in typed:
            self.assertAlmostEqual(p['ingress_FF_area_floor_um2_per_pc'],12205.2096)
            self.assertFalse(p['fits_all_floor_reservations_at_percent']['70'])
            self.assertTrue(p['fits_all_floor_reservations_at_percent']['75'])
            for t in p['tiles']:
                self.assertEqual(t['protected_ingress_storage_bits'],40704*len(t['pc_ids']))
                self.assertGreater(t['complete_inventory_area_floor_um2'],t['existing_bank_cache_native_relay_reservation_um2'])
                self.assertIsNone(t['ingress_mux_protection_control_logic_um2'])
        reset=[p for p in s['points'] if p['ingress_FF_policy']=='all_storage_reset_conservative']
        self.assertFalse(reset[-1]['fits_all_floor_reservations_at_percent']['75'])
        self.assertTrue(reset[-1]['fits_all_floor_reservations_at_percent']['80'])


if __name__=='__main__':unittest.main()

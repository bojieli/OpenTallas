import unittest
from hbm_svc_dma_actual_cache_inventory import model


class ActualCacheInventoryTests(unittest.TestCase):
    def test_mapped_cache_epoch_ingress_and_unknown_full_area(self):
        s=model()
        self.assertAlmostEqual(s['cache_mapped_controller_um2_per_pc'],8417.63178)
        self.assertAlmostEqual(s['cache_actual_four_bank_eight_macro_um2_per_pc'],71445.57882)
        self.assertEqual(s['ingress_bits']['total_bits_per_pc'],40960)
        self.assertEqual(s['ingress_bits']['paired_slot_index_epoch_fault_bits_per_pc'],4096)
        self.assertEqual(s['current_total_fit'],'UNKNOWN')
        self.assertFalse(s['route_admission'])
        self.assertFalse(s['die']['outline_changed_in_this_revision'])
        self.assertAlmostEqual(s['die']['horizontal_reticle_headroom_um'],1265.712)
        typed=next(p for p in s['points'] if p['ingress_FF_policy']=='payload_ECC_unreset_metadata_reset'
                   and p['native_reserve_policy']=='provisional1000_protected_reserve')
        self.assertAlmostEqual(typed['ingress_FF_floor_um2_per_pc'],12302.25408)
        self.assertTrue(typed['fits_all_floors_at_percent']['75'])
        self.assertFalse(typed['fits_all_floors_at_percent']['70'])
        for t in typed['tiles']:
            self.assertAlmostEqual(t['actual_total_cache_pc_area_um2'],71445.57882*len(t['pc_ids']))
            self.assertEqual(t['physical_face_traffic_bits'],8952)
            self.assertGreater(t['relay_reservation_ff_count'],0)
            self.assertEqual(t['epoch_protected_ingress_storage_bits'],40960*len(t['pc_ids']))
            self.assertIsNone(t['ingress_decoder_publication_slots'])
            self.assertIsNone(t['native_protected_uplift_um2'])
            self.assertIsNone(t['clock_CTS_hold_routing_added_area_um2'])
        reset=next(p for p in s['points'] if p['ingress_FF_policy']=='all_ingress_storage_reset'
                   and p['native_reserve_policy']=='provisional1000_protected_reserve')
        self.assertEqual(len(reset['failures_by_percent']['75']),2)
        self.assertTrue(reset['fits_all_floors_at_percent']['80'])


if __name__=='__main__':unittest.main()

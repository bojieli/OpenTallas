import unittest
from hbm_svc_dma_wide_control_sweep import sweep


class ControlReserveTests(unittest.TestCase):
    def test_historical_reserve_is_disproved_and_native_is_separate(self):
        s=sweep()
        self.assertGreater(s['protected_cache_minimum']['metadata_ff_area_floor_um2'],2000)
        self.assertGreater(s['protected_cache_minimum']['combined_cache_ff_area_floor_um2'],3500)
        self.assertFalse(s['supersedes_current_fit_claim']['current_adopted_total_fit'])
        self.assertAlmostEqual(s['native_control']['reference_mapped_area_um2_per_pc'],495.18054)
        self.assertFalse(s['native_control']['reference_metadata_protected'])
        self.assertIsNone(s['native_control']['protected_uplift_um2_per_pc'])
        self.assertFalse(s['route_admission'])
        self.assertEqual([len(p['failures_by_percent']['60']) for p in s['points']],[1,4,12])
        for point in s['points']:
            self.assertEqual(len(point['tiles']),16)
            self.assertFalse(point['fits_all_tiles_at_percent']['60'])
            self.assertTrue(point['fits_all_tiles_at_percent']['65'])
            self.assertTrue(point['fits_all_tiles_at_percent']['70'])
            self.assertTrue(point['fits_all_tiles_at_percent']['75'])
            for tile in point['tiles']:
                self.assertEqual(tile['native_control_reservation_um2'],1000*len(tile['pc_ids']))
        self.assertLess(s['points'][0]['maximum_prospective_utilization'],s['points'][-1]['maximum_prospective_utilization'])


if __name__=='__main__':unittest.main()

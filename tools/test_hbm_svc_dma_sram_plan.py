import unittest
from hbm_svc_dma_sram_plan import plan


class SRAMPlanTests(unittest.TestCase):
    def test_real_macro_inventory_and_geometry(self):
        p=plan()
        self.assertEqual(len(p['tiles']),16)
        self.assertEqual(sum(t['macro_count'] for t in p['tiles']),256)
        self.assertEqual(p['macro']['total_macros'],512)
        self.assertTrue(p['geometry_fit'])
        self.assertTrue(p['area_reservation_fit'])
        self.assertFalse(p['route_admission'])
        tail=next(t for t in p['tiles'] if t['master']=='hfd_svc_dma_SE_s7')
        self.assertEqual(tail['pc_ids'],[29,30,31])
        self.assertEqual(tail['legacy_service_seam_local_taps_um'],[470.016])
        self.assertGreater(tail['remaining_comb_clock_buffer_area_um2'],8000)
        for t in p['tiles']:
            for m in t['macros']:
                self.assertAlmostEqual(m['bbox_um'][2]-m['bbox_um'][0],94.824)
                self.assertAlmostEqual(m['bbox_um'][3]-m['bbox_um'][1],41.064)
        self.assertLess(p['storage']['data_row_range'][1],p['storage']['ecc_row_range'][0])
        self.assertLessEqual(p['storage']['required_sectors_per_pc'],p['storage']['sector_capacity_per_pc'])


if __name__=='__main__': unittest.main()

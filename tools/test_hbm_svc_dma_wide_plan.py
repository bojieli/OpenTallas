import unittest
from hbm_svc_dma_wide_plan import plan,pin_plan


class WidePhysicalTests(unittest.TestCase):
    def test_source_footprints_inventory_and_actual_area(self):
        p=plan()
        self.assertTrue(p['geometry_fit'])
        self.assertTrue(p['die']['reticle_fit'])
        self.assertLessEqual(p['die']['proposed_outline_um'][1],26000)
        self.assertGreater(p['die']['naive_360um_band_insertion_height_um'],26000)
        self.assertAlmostEqual(p['die']['added_area_mm2'],31734.288*2*358.56/1e6)
        self.assertTrue(p['area_budget_fit'])
        self.assertFalse(p['route_admission'])
        self.assertEqual(sum(len(t['macros']) for t in p['tiles']),512)
        self.assertEqual(p['sram']['total_macros_four_stacks'],1024)
        self.assertEqual(p['logical_face_bits_per_stack'],8790)
        self.assertEqual(p['physical_replicated_slice_face_bits_per_stack'],8952)
        for tile in p['tiles']:
            self.assertAlmostEqual(tile['bank_controller_wide_mapped_area_um2'],tile['banks']*1563.29676)
            self.assertTrue(tile['pin_fit'])
            self.assertFalse(tile['macro_geometry_conflicts'])
        for i in p['relocated_instances']:
            for k in (0,1):
                self.assertAlmostEqual(i['bbox_um'][k+2]-i['bbox_um'][k],
                    i['original_bbox_um'][k+2]-i['original_bbox_um'][k])
        for stack in p['stack_reservations'].values():
            self.assertTrue(stack['placement_fit'])
            self.assertGreater(stack['companion_to_SM_clearance_um'],4)
        b=p['bandwidth']
        self.assertEqual(b['owner_90pct_nominal_gate_Bcycle'],3000)
        self.assertLess(b['WP128_FP8_INT8_raw_Bcycle'],3000)
        self.assertFalse(b['shared128lane_corridor_fits_existing_spine'])

    def test_four_slice_edges_and_unsupported_shape(self):
        ports,bits=pin_plan(400.032,480,32,6)
        self.assertEqual(bits,8952)
        for face in ['W','E']:
            self.assertEqual(sum(p['bits'] for n,p in ports.items() if p['face']==face and not n.startswith(('ck','rst'))),8952)
        with self.assertRaises(AssertionError):plan(lanes=8)


if __name__=='__main__':unittest.main()

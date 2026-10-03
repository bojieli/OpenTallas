"""Accounting and guard checks for the model-only clock seam overlay."""
import unittest
import uarch_rom_gals_mesh as M

class ClockSeamModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.d=M.build()
    def test_source_geometry_inside_existing_die(self):
        ds=self.d['geometry']['ds']
        self.assertEqual(ds['candidate'],'DS4096-TP4-S58-PAR2-NP2048')
        self.assertEqual(sum(r['pairs'] for r in ds['roots']),2048)
        for r in ds['roots']:
            x0,y0,x1,y1=r['bbox_um']
            self.assertTrue(0 <= x0 < x1 <= 33000)
            self.assertTrue(0 <= y0 < y1 <= 26000)
    def test_no_free_crossing_and_monotone_latency(self):
        mesh,gals,slow,ratio=self.d['variants']
        for design in ['qwen','ds_dag']:
            key='added_us' if design=='qwen' else 'delta_us'
            values=[v[design][key] for v in [mesh,gals,slow]]
            self.assertTrue(0 < values[0] < values[1] < values[2])
        self.assertGreater(ratio['qwen']['added_us'],gals['qwen']['added_us'])
        self.assertAlmostEqual(gals['roundtrip_ns'],10)
    def test_fifo_inventory_and_area_conservation(self):
        for name in ['qwen','ds']:
            cost=self.d['gals_cost'][name];seams=self.d['seam_boundaries'][name]
            self.assertEqual(cost['fifos'],sum(s['replicas'] for s in seams))
            self.assertEqual(cost['memory_storage_bits'],sum(s['storage_bits'] for s in seams))
            for s in seams:
                self.assertEqual(s['wire_word_bits'],s['payload_bits']+s['identity_bits'])
                self.assertEqual(s['storage_bits'],s['replicas']*16*s['wire_word_bits'])
                self.assertGreater(s['routing']['tracks_per_bank'],s['wire_word_bits'])
                self.assertGreater(s['placement']['required_height_um'],0)
            self.assertAlmostEqual(cost['total_incremental_area_mm2'],cost['incremental_fifo_area_mm2']+cost['incremental_root_reset_reserve_mm2'])
    def test_contract_does_not_promote_closure(self):
        self.assertFalse(self.d['selected']['physical_fit'])
        self.assertFalse(self.d['selected']['fulltoken_rate'])
        self.assertTrue(self.d['selected']['default_off'])
        self.assertEqual(self.d['related_cdc']['fast_to_slow_cycles'],2)
        self.assertEqual(self.d['related_cdc']['slow_to_fast_cycles'],2)
        self.assertLess(self.d['related_cdc']['ds_rate_gain_in_source'],.01)
        self.assertIn('independent',self.d['related_cdc']['prohibit'])
        self.assertEqual(self.d['retained_ds_par2']['total_dies'],508)
    def test_retained_par2_delta_does_not_remove_existing_links(self):
        gals=self.d['variants'][1]
        self.assertAlmostEqual(gals['ds_retained_par2']['1048576']['conservative_serial_added_us'],4.07)
        for row in gals['ds_retained_par2'].values():
            self.assertGreater(row['overlay_us'],row['baseline_us'])
            self.assertLess(row['overlay_ar_tokens_s'],1e6/row['baseline_us'])

if __name__=='__main__':unittest.main()

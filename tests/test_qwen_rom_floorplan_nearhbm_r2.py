"""Focused checks for the r2 near-HBM Qwen ROM floorplan margins (model only)."""
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import qwen_rom_floorplan_nearhbm as F
import qwen_rom_floorplan_nearhbm_r2 as F2

REC, _ = F2.build()


class LineageTests(unittest.TestCase):
    def test_committed_record_matches_a_rebuild(self):
        committed = json.loads((F2.OUT / F2.RECORD).read_text())
        self.assertEqual(committed, json.loads(json.dumps(REC)))

    def test_r1_is_untouched(self):
        r1 = json.loads((F.OUT / F.RECORD).read_text())
        rebuilt, _ = F.build()
        self.assertEqual(r1, json.loads(json.dumps(rebuilt)))
        self.assertEqual(REC['predecessor']['sha256'], F2.sha(F2.P2['r1_record']))


class KvServiceTests(unittest.TestCase):
    def test_decomposition_has_zero_residual(self):
        kv = REC['kv_service']
        self.assertAlmostEqual(kv['total_mm2'], 19.22131, places=4)
        self.assertAlmostEqual(kv['kept_mm2'] + kv['ambiguous_mm2'] + kv['removed_mm2'], kv['total_mm2'], places=2)
        self.assertAlmostEqual(kv['reservation_mm2'], kv['kept_mm2'] + kv['ambiguous_mm2'], places=3)

    def test_pending_depth_covers_bandwidth_delay(self):
        s = REC['kv_service']['scheduling_check']
        self.assertLessEqual(max(s['pending_depth_needed'].values()), s['pending_depth_built'])


class CorridorTests(unittest.TestCase):
    def test_no_corridor_is_narrowed_and_all_fit_70pct(self):
        for k, c in REC['corridors'].items():
            self.assertGreaterEqual(c['width_r2_um'], c['width_r1_um'], k)
            self.assertGreaterEqual(c['netted_target_tracks_at_r1_width'], c['demand_tracks'], k)
            for l, v in c['per_layer_at_r1_width'].items():
                self.assertEqual(v['netted'], v['raw'] - v['pg'] - v['via_obs'] - v['clock'])
                self.assertEqual(v['target'], math.floor(0.70 * v['netted']))

    def test_strip_pg_coverage_from_ir(self):
        g = REC['pg_coverage']['regions']
        self.assertAlmostEqual(g['strip']['m8m9_coverage_per_net'], 0.1639, places=3)
        self.assertGreaterEqual(g['hub']['m8m9_coverage_per_net'], 0.025)
        for r in ('tile_field', 'strip'):
            self.assertLessEqual(g[r]['drop_mv_at_coverage'], 35.0 + 1e-6)

    def test_evidence_bracket_is_reported(self):
        ev = REC['targets']['corridor_evidence']
        self.assertEqual(ev['passed']['grt_overflow'], 0)
        self.assertLess(ev['passed']['demand_over_raw_same_direction'], ev['unresolved']['demand_over_raw_same_direction'])
        s = REC['evidence_sized_sensitivity']
        self.assertFalse(s['within_815'])
        self.assertGreater(s['density_that_just_fits_815'], ev['passed']['demand_over_raw_same_direction'])


class FrameTests(unittest.TestCase):
    def test_selected_frame_fits(self):
        f = REC['floorplan']
        self.assertEqual(REC['selected_variant'], 'kv_kept_plus_ambiguous')
        self.assertTrue(f['fits_26x33'] and f['within_815'])
        self.assertAlmostEqual(f['margin_to_815_mm2'], 815.0 - f['die_mm2'], places=2)
        self.assertTrue(REC['floorplan_variants']['kv_full_19p22']['within_815'])

    def test_util_after_cts_and_repair(self):
        u = REC['cts']['util_after_cts_and_repair']
        self.assertLessEqual(u['tile_slot'], 0.70)
        self.assertGreater(u['hub_element'], 0.70)          # hence the hub element frame growth
        self.assertGreater(REC['floorplan']['spine']['hub_element_cts_growth_mm2'], 0)


class HotspotTests(unittest.TestCase):
    def test_limit_is_sourced(self):
        h = REC['hotspot']
        self.assertEqual(h['limit_w_per_mm2']['nominal'], 2.0)
        self.assertTrue(h['sources'][0]['url'].startswith('https://eps.ieee.org'))

    def test_strip_and_phy_verdicts(self):
        c = {(x['region'], x['scenario']): x for x in REC['hotspot']['checks']}
        self.assertTrue(c[('strip', 'A')]['verdict_avg']['nominal'])
        self.assertFalse(c[('strip', 'A')]['verdict_sustained_peak']['nominal'])
        for k in F2.HOST_PHY_PJ_B:
            self.assertTrue(c[(f'PHY ({k})', '-')]['verdict_sustained_peak']['nominal'])
        m = REC['hotspot']['mitigation_if_sustained']
        self.assertLess(m['duty_governor_max'], 0.5)
        self.assertGreater(m['strip_at_0p9GHz']['peak_w_per_mm2'], 2.0)


if __name__ == '__main__':
    unittest.main()

"""Focused checks for the near-HBM Qwen ROM floorplan model (model only)."""
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import qwen_rom_floorplan_nearhbm as F

REC, _ = F.build()


class SourceTests(unittest.TestCase):
    def test_tile_kv_macros_have_no_other_user(self):
        u = REC['tile_kv_macro_users']
        self.assertEqual(u['per_tile_in_rtl'], 2)
        self.assertEqual(u['per_die'], 3072)
        self.assertEqual(len(u['read_users']), 2)       # scores and P.V
        self.assertEqual(len(u['write_users']), 2)      # new-token K and V
        self.assertEqual(u['other_users'], [])
        self.assertTrue(u['credit_valid'])

    def test_kv_credit_is_per_tile_not_per_group(self):
        k = REC['area']['removed']['tile_KV_macros']
        self.assertAlmostEqual(k['macro_mm2'], 3072 * 94.824 * 41.04 / 1e6, places=2)
        self.assertAlmostEqual(k['pricing_figure_mm2'] / k['macro_mm2'], 2.0, places=2)

    def test_committed_record_matches_a_rebuild(self):
        committed = json.loads((F.OUT / F.RECORD).read_text())
        self.assertEqual(committed, json.loads(json.dumps(REC)))


class FrameTests(unittest.TestCase):
    def frames(self):
        return {f"{f['variant']}-{f['hbm_edges']}": f for f in REC['frames']}

    def test_selected_frame_is_legal_and_within_budget(self):
        f = REC['floorplan']
        self.assertEqual(REC['selected_frame'], 'B2-EW')
        self.assertTrue(f['legal'])
        self.assertLessEqual(f['die_um'][0], 26000)
        self.assertLessEqual(f['die_um'][1], 33000)
        self.assertLessEqual(f['die_mm2'], 815.0)
        self.assertLessEqual(f['shoreline']['beachfront_fraction_12mm'], f['shoreline']['beachfront_ceiling'])

    def test_current_slot_and_ns_shoreline_are_refused(self):
        fr = self.frames()
        self.assertFalse(fr['A-EW']['legal'])
        self.assertTrue(any('deficit 325' in e for e in fr['A-EW']['errors']))
        for k in ('A-NS', 'B1-NS', 'B2-NS', 'B1-EW'):
            self.assertFalse(fr[k]['legal'], k)

    def test_tile_reframe_keeps_utilisation_and_lattice(self):
        t = REC['floorplan']['tile_slot']
        self.assertTrue(t['lattice_ok'])
        self.assertEqual(t['logic_util'], 0.5)
        self.assertGreaterEqual(t['cell_capacity_at_util_um2'], t['cell_ceiling_um2'])
        self.assertTrue(t['corridor']['fits'])
        self.assertEqual(t['corridor_demand_tracks'], 637)


class RouteTests(unittest.TestCase):
    def test_every_corridor_fits(self):
        c = REC['routes']['corridors']
        for k in ('horizontal', 'vertical_in_spine', 'tile_column_corridor'):
            self.assertTrue(c[k]['allotment']['fits'], k)
        self.assertEqual(c['per_link_tracks'], 1056)

    def test_stages_at_ss_reach(self):
        h = REC['routes']['hub_to_stack']
        self.assertEqual(h['reach_um_per_stage'], 504.0)
        self.assertEqual(h['trunk_stages'], math.ceil(h['manhattan_um'] / 504.0))
        self.assertEqual(h['total_stages'], h['trunk_stages'] + h['in_strip_fan_stages'])
        self.assertEqual(h['per_layer_cycle_delta_vs_model'], 2 * (h['total_stages'] - h['model_stages']))


class ElementTests(unittest.TestCase):
    def test_elements_in_order_and_on_lattice(self):
        el = REC['hardened_elements']
        self.assertEqual([e['order'] for e in el], [1, 2, 3, 4])
        self.assertTrue(el[0]['name'].startswith('near-HBM row-engine'))
        self.assertEqual(el[0]['replicas_per_die'], 24)
        w, h = el[0]['frame_um']
        self.assertAlmostEqual(w / F.SNAP_X, round(w / F.SNAP_X), places=6)
        self.assertAlmostEqual(h / F.SNAP_Y, round(h / F.SNAP_Y), places=6)
        self.assertLessEqual(6 * h, 12000.096)
        self.assertEqual(el[0]['macros'][0]['orientations_allowed'], ['R0', 'MY'])
        self.assertEqual(el[0]['macros'][0]['origin_rule_mod_48nm']['R0'], [0])
        self.assertLessEqual(el[1]['util_target']['cell_util'], F.CELL_UTIL_TARGET)

    def test_hotspot_limit_is_flagged_not_invented(self):
        self.assertIsNone(REC['power']['sourced_hotspot_limit'])
        self.assertAlmostEqual(REC['power']['reference_die_average_w_per_mm2']['h200'], 0.675, places=3)


if __name__ == '__main__':
    unittest.main()

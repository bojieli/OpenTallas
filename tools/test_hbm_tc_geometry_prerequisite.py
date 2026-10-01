#!/usr/bin/env python3
"""Geometry guards: real overlaps, directional cuts, source identity, area caps."""
import copy
import json
import unittest
from pathlib import Path
import hbm_tc_geometry_prerequisite as G

class Geometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=G.build()
    def test_failed_sources_and_legacy_are_distinct(self):
        q=self.model['models']['qwen'];d=self.model['models']['deepseek_v41']
        self.assertEqual(q['failed_source_outline_um'],[220,220])
        self.assertEqual(d['failed_source_outline_um'],[164,164])
        self.assertEqual(d['retained_global_outline_um'],[180,180])
        self.assertEqual(d['retained_global_column_grid_hard_overlap_count'],161)
        self.assertEqual(q['retained_global_column_grid_hard_overlap_count'],0)
        self.assertGreater(q['retained_global_grid_halo_overlap_count'],0)
        self.assertFalse(d['failed_LEF_qualification_transfer'])
    def test_corrected_grid_has_real_halo_clearance(self):
        for m in self.model['models'].values():
            self.assertEqual(G.conflicts(m['placements'],G.HALO),[])
            self.assertFalse(m['existing_slot_fits'])
            w,h=m['minimum_slot_for_declared_grid_um']
            self.assertTrue(all(r['x']>=G.EDGE and r['y']>=G.EDGE and r['x']+r['w']<=w-G.EDGE+1e-8 and r['y']+r['h']<=h-G.EDGE+1e-8 for r in m['placements']))
            self.assertTrue(all(abs(r['x']/G.SX-round(r['x']/G.SX))<1e-6 and abs(r['y']/G.SY-round(r['y']/G.SY))<1e-6 for r in m['placements']))
    def test_overlap_guard_catches_bad_dimension_pairing(self):
        rows=[dict(name='a',x=0,y=0,w=180,h=180),dict(name='b',x=170,y=0,w=180,h=180)]
        self.assertEqual(G.conflicts(rows)[0][2],10)
        rows[1]['x']=192
        self.assertEqual(G.conflicts(rows,6),[])
        rows[1]['x']=191.999
        self.assertEqual(len(G.conflicts(rows,6)),1)
    def test_tracks_are_directional_PDN_debited_and_not_free_capacity(self):
        layers=self.model['ASAP7_directional_grid'];rails=self.model['PDN_source_parameters']
        self.assertEqual(layers['M8']['offset'],.116)
        self.assertEqual(layers['M4']['direction'],'HORIZONTAL')
        for m in self.model['models'].values():
            r=m['reservations']
            for key in ['vertical_bound','horizontal_bound']:
                self.assertGreaterEqual(r[key]['reserved_capacity'],r['vertical_spine_demand_bits'] if key=='vertical_bound' else r['horizontal_row_demand_bits'])
                self.assertEqual(r[key]['actual_available_track_lower_bound'],0)
            for c in m['corridor_track_grid']:
                self.assertTrue(all(layers[t['layer']]['direction']==c['direction'] for t in c['tracks']))
                self.assertTrue(all(t['remaining_geometric_ceiling']<=t['track_count'] and t['actual_available_track_lower_bound']==0 for t in c['tracks']))
        a=G.mask(0,1,'M5',layers,rails)
        self.assertEqual(a['first_track_index'],0)
        self.assertEqual(a['last_track_index'],20)
        self.assertLessEqual(a['remaining_geometric_ceiling'],21)
    def test_full_fragment_spokes_conserve_and_clear_OBS(self):
        for m in self.model['models'].values():
            sp=m['global_fragment_spines'];self.assertEqual(len(sp),8)
            total=m['parent_full_fragment_trunk_prerequisite']['total_fragment_bits_per_cycle']
            self.assertEqual(sum(s['fragment_slice_bits'][1]-s['fragment_slice_bits'][0]+1 for s in sp),total)
            self.assertEqual(sp[0]['fragment_slice_bits'][0],0)
            self.assertEqual(sp[-1]['fragment_slice_bits'][1],total-1)
            for s in sp:
                x0,y0,x1,y1=s['rectangle_um']
                self.assertGreater(x1,x0);self.assertGreater(y1,y0)
                for r in m['placements']:
                    self.assertTrue(x1<=r['x']-G.HALO+1e-7 or x0>=r['x']+r['w']+G.HALO-1e-7)
    def test_platform_tamper_rejected(self):
        pdata=json.loads((G.ROOT/G.OUT/'platform_source.json').read_text())
        pdata['files']['openRoad/make_tracks.tcl']['text']+='bad'
        with self.assertRaises(ValueError):G.platform(pdata,{})
    def test_lane_ports_and_cell_caps_are_bound(self):
        for m in self.model['models'].values():
            b=m['bounded_added_overhead'];a=b['area_upper_um2']
            self.assertGreaterEqual(b['west_annex_um']*m['failed_source_outline_um'][1]*G.UTIL,a-1e-7)
            banks=m['lane_predecode_cut_banks'];self.assertIn(len(banks),[16,32])
            self.assertEqual(sum(x['cut_bits'] for x in banks),40*len(banks))
            for x in banks:
                self.assertEqual(len(x['source_edge_access']['w']['pin_rectangles_um']),16)
                self.assertEqual(x['source_edge_access']['w']['edge'],'N')
                self.assertEqual(x['source_edge_access']['x']['edge'],'W')
            self.assertFalse(b['hold_budget_is_timing_cure'])
    def test_wire_delta_and_admission_are_separate(self):
        self.assertTrue(self.model['no_admission'])
        f=self.model['failure_unchanged']
        self.assertEqual(f['engineering_verdict'],'FAIL')
        self.assertEqual(f['SS_setup_wns_ps'],-102.65510663742816)
        self.assertEqual(f['FF_hold_wns_ps'],-.9053036098549683)
        for m in self.model['models'].values():
            self.assertEqual(m['token_wire_sensitivity']['local_new_cut_stage'],1)
            for c in m['token_wire_sensitivity']['paths']:
                self.assertGreaterEqual(c['delta_stages_upper'],0)
                self.assertEqual(c['candidate_stages_upper_SS504'],__import__('math').ceil(c['candidate_distance_upper_um']/504))

if __name__=='__main__':unittest.main()

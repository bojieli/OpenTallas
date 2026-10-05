import gzip
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_gateway_via_arrays as m

class GatewayViaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=m.inputs();cls.model=m.build();cls.tech=cls.sources['tech.lef'].decode()

    def test_actual_arrays_source_spacing_and_stripe_widths(self):
        a,b=self.model['PG_array_rules']
        self.assertEqual((a['columns'],a['rows'],a['contacts']),(7,3,21))
        self.assertEqual((b['columns'],b['rows'],b['contacts']),(7,7,49))
        self.assertEqual(a['metal_extent_um'],{'M6':[.522,.188],'M7':[.5,.21]})
        self.assertEqual(b['metal_extent_um'],{'M7':[.5,.5],'M8':[.522,.5]})
        self.assertEqual(b['source_min_cut_spacing_um'],.046)
        for r in (a,b):
            self.assertTrue(r['fits_existing_reserved_envelope'])
            self.assertLessEqual(max(r['envelope_um']),.544)

    def test_excess_array_refused_by_source_width_and_envelope(self):
        self.assertFalse(m.array_rule(self.tech,'M7_M6',8,3,.288,.544)['fits_existing_reserved_envelope'])
        self.assertFalse(m.array_rule(self.tech,'M7_M6',7,5,.288,.544)['fits_existing_reserved_envelope'])
        self.assertFalse(m.array_rule(self.tech,'M8_M7',8,7,.544,.544)['fits_existing_reserved_envelope'])

    def test_single_clock_vias_fit_real_min_area_pads(self):
        for name in ('VIA45','VIA56','VIA67'):
            via=m.block(self.tech,'VIA',name)
            for layer,rect in re.findall(r'LAYER (M\d+)\s*;\s*RECT ([^;]+);',via):
                x,y,x2,y2=map(float,rect.split());p=self.model['clock_pad_source_rules'][layer]
                w,h=p['extent_um'];self.assertGreaterEqual(w/2,max(abs(x),abs(x2)))
                self.assertGreaterEqual(h/2,max(abs(y),abs(y2)))
                self.assertGreaterEqual(p['area_um2'],p['source_min_area_um2'])

    def test_all_real_clock_sites_body_safe_and_passive_limit(self):
        for name,count in [('Qwen',4160),('DeepSeek',4416)]:
            d=self.model['models'][name];self.assertEqual(d['macro_contacts'],count)
            self.assertEqual({r['SM'] for r in d['macro_clock_contacts']},set(range(32)))
            for r in d['macro_clock_contacts']:
                self.assertEqual(r['source_macro_body_conflicts'],[])
                self.assertTrue(r['inside_existing4um_halo'])
                self.assertLessEqual(r['passive_clock_last_leg_with_escape_um'],215)
                self.assertGreaterEqual(r['source_pin_escape_um'],.999)
            self.assertLessEqual(d['maximum_passive_last_leg_with_escape_um'],206.002)

    def test_clock_pads_do_not_overlap_other_clock_sites(self):
        for d in self.model['models'].values():
            for sm in range(32):
                rows=[r for r in d['macro_clock_contacts'] if r['SM']==sm]
                for i,r in enumerate(rows):
                    self.assertFalse(any(m.overlap(r['contact_bbox_um'],q['contact_bbox_um']) for q in rows[i+1:]))

    def test_context_capacities_no_new_tracks_or_timing_credit(self):
        q=self.model['models']['Qwen'];d=self.model['models']['DeepSeek']
        self.assertEqual(q['selected_L2_capacities'],[12919,13013,12919,13013])
        self.assertEqual(d['selected_L2_capacities'],[12919]*4)
        self.assertFalse(self.model['hardware_admitted']);self.assertFalse(self.model['engine_build_allowed'])
        self.assertIsNone(self.model['physical_wait_bounds']);self.assertEqual(self.model['extra_signal_tracks'],0)
        self.assertTrue(self.model['source_array_contact_and_distributed_cut_pass'])
        self.assertFalse(self.model['source_geometry_pass'])

    def test_long_M8_spacing_priced_and_old_masks_retained(self):
        self.assertFalse(self.model['inherited_PG_recipe_long_M8_spacing_pass'])
        self.assertEqual(self.model['selected_optin_M8_spacing_um'],.5)
        self.assertEqual(self.model['ring_edge_growth_um'],.404)
        self.assertIsNone(self.model['ring_guard_binding_in_parent_context'])
        for d in self.model['models'].values():
            self.assertTrue(d['optin_M8_spacing_all_cut_capacity_fits'])
            for c in d['optin_M8_spacing_corrected_local_cuts']+d['optin_M8_spacing_corrected_L2_cuts']:
                self.assertGreaterEqual(c['tracks_lost_vs_inherited'],0)
                self.assertGreaterEqual(c['margin_tracks'],0)
        d=m.BASE/'selected_optin_pdn.tcl'
        self.assertEqual(m.sha(d.read_bytes()),self.model['selected_optin_PDN_tcl_sha256'])
        self.assertIn('-widths {0.544 0.544} -spacings {0.5}',d.read_text())

    def test_shifted_clock_contacts_are_charged_in_existing_cut_masks(self):
        for d in self.model['models'].values():
            cuts=d['optin_M8_spacing_corrected_local_cuts'];stride=len(cuts)//32
            # Each source placement occupies one contiguous group of cuts.
            sm_order=[]
            for e in d['macro_clock_contacts']:
                if e['SM'] not in sm_order:sm_order.append(e['SM'])
            for j,sm in enumerate(sm_order):
                sites=[e['clock_contact_centre_um'] for e in d['macro_clock_contacts'] if e['SM']==sm]
                for c in cuts[j*stride:(j+1)*stride]:
                    axis=0 if c['axis']=='X' else 1
                    for layer in c['layers'].values():
                        lo,hi=layer['track_index_extent']
                        for point in sites:
                            track=round((point[axis]*1000-layer['origin_DBU'])/layer['pitch_DBU'])
                            if lo<=track<=hi:
                                self.assertTrue(any(a<=track<=b for a,b in layer['explicit_excluded_index_intervals']))

    def test_pin_guard_rejects_source_mutation(self):
        import shutil
        old=m.BASE
        with tempfile.TemporaryDirectory() as t:
            shutil.copytree(old,Path(t)/'archive');m.BASE=Path(t)/'archive'
            try:
                p=m.BASE/'inputs/tech.lef';p.write_bytes(p.read_bytes()+b'\n')
                with self.assertRaisesRegex(ValueError,'source pin'):m.build()
            finally:m.BASE=old

if __name__=='__main__':unittest.main()

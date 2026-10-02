import gzip,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_native_clock_access as g
from dsrom_noECC_hold_station_geometry import pin_rects
class NativeClock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads((g.BASE/'model.json').read_text());cls.e=json.loads(g.ENABLE.read_text());cls.c=json.loads(g.CLOCK.read_text());cls.h=json.loads(g.HOLD.read_text())
    def test_literal_RC_lowercase_exponents_and_cut_resistance(self):
        rc,vr=g.parse_rc((g.CTX/'inputs/setRC.tcl').read_text())
        self.assertEqual(rc['M1'][1],1e-10);self.assertEqual(vr['V1'],.0172);self.assertEqual(vr['V7'],.0082)
        self.assertEqual(self.x['source_parser_correction']['old_M1_C_fF_per_um'],1.0)
        self.assertEqual(rc,self.x['layer_RC_kohm_fF_per_um'])
    def test_rectangle_union_and_connected_components(self):
        self.assertEqual(g.union_area([[0,0,10,10],[5,0,15,10]]),150)
        self.assertEqual(g.union_area([[0,0,10,10],[0,0,10,10]]),100)
        self.assertEqual(len(g.components([[0,0,10,10],[10,0,20,10],[30,0,40,10]])),2)
    def test_all_source_clock_endpoints_and_cuts_accounted_once(self):
        for k,c in self.x['cases'].items():
            self.assertEqual(c['native_endpoint_contact_occurrence_count'],9936);self.assertEqual(c['native_contact_count'],9888);self.assertEqual(c['native_access_endpoint_count'],1242)
            old={n['name']:{(v['instance'],v['pin']) for v in [n['source']]+n['sinks']} for n in self.c['cases'][k]['clock_leaf_nets']+self.c['cases'][k]['clock_spine_nets']}
            for n in c['nets']:
                self.assertEqual({(p['instance'],p['pin']) for p in n['endpoints']},old[n['name']])
                self.assertEqual(sum(n['via_counts'].values()),8*len(n['endpoints']))
    def test_shared_native_contact_union_is_not_replica_doublecount(self):
        for c in self.x['cases'].values():
            total=0
            for n in c['nets']:
                contacts={(v['master'],*v['center_DBU']) for ep in n['endpoints'] for v in ep['native_vias']}
                self.assertEqual(len(contacts),n['unique_physical_contact_count']);total+=len(contacts)
            self.assertEqual(total,c['native_contact_count']);self.assertEqual(c['native_endpoint_contact_occurrence_count']-total,48)
    def test_landing_containment_against_actual_source_pin(self):
        for case,c in self.x['cases'].items():
            placements=self.e['cases'][case]['placements']+self.h['cases'][case]['placements']+self.c['cases'][case]['new_clock_buffer_placements']+self.c['cases'][case]['retained_original_scalar_placements'];pd={p['instance']:p for p in placements}
            for n in c['nets']:
                self.assertFalse(n['literal_landing_failures'])
                for ep in n['endpoints']:
                    actual=pin_rects(pd[ep['instance']],self.e['physical_master_templates'][pd[ep['instance']]['master']],ep['pin'])
                    self.assertIn(ep['chosen_literal_M1_rectangle_DBU'],[p['bbox_DBU'] for p in actual if p['layer']=='M1'])
                    xx,yy=ep['native_vias'][0]['center_DBU'];r=ep['chosen_literal_M1_rectangle_DBU'];lo=g.move(self.x['source_native_via_templates']['VIA12'][0]['bbox_DBU'],xx,yy)
                    self.assertTrue(r[0]<=lo[0]<=lo[2]<=r[2] and r[1]<=lo[1]<=lo[3]<=r[3])
    def test_minarea_per_connected_polygon_independently_reconstructed(self):
        for c in self.x['cases'].values():
            for n in c['nets']:
                self.assertFalse(n['minarea_failures'])
                for ep in n['endpoints']:
                    metal={l:[] for l in self.x['source_min_metal_area_DBU2']}
                    for v in ep['native_vias']:
                        for p in self.x['source_native_via_templates'][v['master']]:
                            if p['layer'] in metal:metal[p['layer']].append(g.move(p['bbox_DBU'],*v['center_DBU']))
                    for p in ep['native_join_wires']+ep['minarea_extensions']:metal[p['layer']].append(p['bbox_DBU'])
                    for layer,rs in metal.items():
                        for comp in g.components(rs):self.assertGreaterEqual(g.union_area(comp),self.x['source_min_metal_area_DBU2'][layer])
    def test_clear_native_PG_OBS_and_distinct_driven_nets(self):
        for c in self.x['cases'].values():
            self.assertEqual(c['raw_inter_net_short_pair_count'],0)
            self.assertEqual(sum(n['source_OBS_PG_intersection_count'] for n in c['nets']),0)
    def test_native_lower_metal_does_not_touch_other_owner_signal_pins(self):
        from dsrom_noECC_enable_distribution import overlap
        for case,c in self.x['cases'].items():
            placements=self.e['cases'][case]['placements']+self.h['cases'][case]['placements']+self.c['cases'][case]['new_clock_buffer_placements']+self.c['cases'][case]['retained_original_scalar_placements'];pd={p['instance']:p for p in placements}
            for n in c['nets']:
                for ep in n['endpoints']:
                    item=pd[ep['instance']];template=self.e['physical_master_templates'][item['master']];metal=[]
                    for v in ep['native_vias']:
                        metal.extend(dict(layer=p['layer'],bbox_DBU=g.move(p['bbox_DBU'],*v['center_DBU'])) for p in self.x['source_native_via_templates'][v['master']])
                    metal+=ep['native_join_wires']+ep['minarea_extensions']
                    for pin in template['pins']:
                        if pin['name'] in (ep['pin'],'VDD','VSS'):continue
                        for r in pin_rects(item,template,pin['name']):
                            for m in metal:
                                if m['layer']==r['layer']:self.assertFalse(overlap(m['bbox_DBU'],r['bbox_DBU']),(ep['instance'],ep['pin'],pin['name'],m,r))
    def test_source_native_resistance_and_positive_metal_C(self):
        for c in self.x['cases'].values():
            for n in c['nets']:
                self.assertAlmostEqual(n['via_cut_R_sum_over_all_contacts_kohm'],sum(self.x['cut_R_kohm'][k]*v for k,v in n['via_counts'].items()))
                cap=sum(v['area_equivalent_C_fF'] for v in n['metal_area_by_layer'].values())
                self.assertGreater(cap,0)
                for v in n['corners'].values():
                    self.assertAlmostEqual(cap,v['native_metal_area_C_proxy_fF']);self.assertGreater(v['source_native_series_R_driver_plus_receiver_kohm'],0)
                    self.assertTrue(v['source34p56_load_screen']);self.assertTrue(v['slew320_screen'])
    def test_old_tight_budget_is_retained_as_FAIL_not_ignored(self):
        for c in self.x['cases'].values():
            n=next(n for n in c['nets'] if n['name']=='capture_clock_s1b0_root_Y')
            v=n['corners']['ff'];self.assertAlmostEqual(v['old_283_native_C_budget_fF'],.13560311)
            self.assertEqual(v['old_budget_area_screen'],'FAIL');self.assertGreater(v['native_metal_area_C_proxy_fF'],v['old_283_native_C_budget_fF'])
            self.assertAlmostEqual(v['literal_source_native_C_budget_fF'],11.264616614)
    def test_negative_geometry_evidence_remains_immutable(self):
        for name,count in [('prior_nearest_track_PG_OBS_FAIL',2412),('prior_native_A_Y_short_FAIL',69)]:
            r=json.loads((g.BASE/(name+'.json')).read_text());raw=gzip.decompress((g.BASE/(name+'_model.json.gz')).read_bytes())
            import hashlib
            self.assertEqual(hashlib.sha256(raw).hexdigest(),r['model_sha256'])
            self.assertFalse(r['physical_measurement'])
            x=json.loads(raw)
            for c in x['cases'].values():
                if count==2412:self.assertEqual(sum(n['source_OBS_PG_intersection_count'] for n in c['nets']),2412)
                else:self.assertEqual(c['raw_inter_net_short_pair_count'],69)
    def test_no_clock_area_credit_or_physical_scope_transfer(self):
        self.assertEqual(self.x['candidate'],self.c['candidate']);self.assertFalse(self.x['physical_build_admitted'])
        self.assertIn('Analytical proxy',self.x['capacitance_method'])
        for c in self.x['cases'].values():
            self.assertEqual(c['clock_area_credit_um2'],0);self.assertEqual(c['added_buffer_or_FF_count'],0);self.assertEqual(c['added_capture_edges'],0)
            self.assertTrue(all(not n['actual_extracted_C'] and not n['inter_net_native_access_spacing_qualified'] for n in c['nets']))
if __name__=='__main__':unittest.main()

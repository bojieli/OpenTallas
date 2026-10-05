#!/usr/bin/env python3
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hbm_tc_retained_def_metadata as D
import hbm_tc_retained_placement_model as M


class RetainedPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.model=M.build()

    def test_bounded_text_parser_and_section_counts(self):
        text='''DESIGN test ;
UNITS DISTANCE MICRONS 1000 ;
COMPONENTS 1 ;
- g_lane\\[0\\].r DFFHQNx1_ASAP7_75t_R
 + PLACED ( 54 270 ) FS ;
END COMPONENTS
NETS 1 ;
- clk ( g_lane\\[0\\].r CLK ) + ROUTED M2 ( 0 0 ) ( 54 0 ) ;
END NETS
END DESIGN
'''
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'sample.def';p.write_text(text)
            d=D.extract(p)
            self.assertEqual(d['components'][0][2:],[54,270,'FS','PLACED'])
            self.assertEqual(d['parsed_counts'],{'COMPONENTS':1,'NETS':1})
            self.assertEqual(d['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(len(d['selected_nets']),1)
            p.write_text(text.replace('COMPONENTS 1','COMPONENTS 2'))
            with self.assertRaisesRegex(ValueError,'count mismatch'):D.extract(p)
            with self.assertRaisesRegex(ValueError,'textual'):D.extract(Path(t)/'sample.odb')
            with patch.object(D,'MAX_BYTES',1):
                with self.assertRaisesRegex(ValueError,'budget'):D.extract(p)

    def test_pin_orientation_transform(self):
        master={'size_um':[2,1],'pins':{'D':{'rectangles':[{'rect_um':[.1,.2,.3,.4]}]}}}
        c=['r','FF',1000,2000,'FS','PLACED']
        self.assertAlmostEqual(M.pin_position(c,master,'D')[0],1.2)
        self.assertAlmostEqual(M.pin_position(c,master,'D')[1],2.7)
        c[4]='FN';self.assertAlmostEqual(M.pin_position(c,master,'D')[0],2.8)
        self.assertEqual(M.gaps([(0,5),(3,8),(10,12)],0,15),[(8,10),(12,15)])

    def test_actual_census_and_power_metadata(self):
        for label,n,cts,hold in [('DS',270479,2287,12792),('Qwen',491591,4515,23839)]:
            v=self.model['models'][label]
            self.assertEqual(v['sections']['COMPONENTS'],n)
            self.assertEqual(v['counts']['CTS_named'],cts)
            self.assertEqual(v['counts']['hold_named'],hold)
            self.assertEqual(v['sections']['SPECIALNETS'],2)
            self.assertEqual(v['sections']['VIAS'],5)
            self.assertEqual({p['net'] for p in v['power']['nets']},{'VDD','VSS'})
            self.assertTrue(all(p['no_track_availability_inferred'] for p in v['power']['nets']))
            self.assertTrue(v['actual_tracks'])
            self.assertEqual(v['terminal_abstract_binding']['exact_signal_pin_rectangles_matched'],583 if label=='DS' else 1095)

    def test_real_row_space_does_not_inherit_arithmetic_white_area(self):
        for label,v in self.model['models'].items():
            p=v['placement']
            self.assertEqual(p['genuine_unoccupied_area_um2'],0)
            self.assertEqual(p['largest_pure_filler_removal_gap_width_um'],.162)
            self.assertTrue(all(not l['candidate_FF_sites_dbu'] for l in p['lanes']))
            self.assertEqual(p['alignment_FF_sites_unallocated'],19)
            self.assertFalse(p['safe_cut_established'])

    def test_conditional_sites_are_disjoint_and_preserve_logic_clock_hold(self):
        platform=json.loads(M.PLATFORM.read_text())['files']['lef/asap7sc7p5t_28_R_1x_220121a.lef']['text']
        import re
        widths={n:round(float(re.search(r'SIZE ([\d.]+)',b)[1])*1000) for n,b in re.findall(r'MACRO\s+(\S+)(.*?)END\s+\1',platform,re.S)}
        for label,v in self.model['models'].items():
            d=json.loads(gzip.decompress((M.DEST/(label+'_placement.json.gz')).read_bytes()))
            rows={}
            for c in d['components']:
                if not c[1].startswith(('FILLER','DECAP')): rows.setdefault(c[3],[]).append((c[2],c[2]+widths[c[1]]))
            seen={}
            for lane in v['placement']['lanes']:
                self.assertEqual(len(lane['conditional_decap_release_FF_sites_dbu']),40)
                self.assertTrue(lane['conditional_decap_instances_to_replace'])
                for x,y,o in lane['conditional_decap_release_FF_sites_dbu']:
                    self.assertFalse(any(a<x+1404 and b>x for a,b in rows.get(y,[])))
                    self.assertFalse(any(a<x+1404 and b>x for a,b in seen.get(y,[])))
                    seen.setdefault(y,[]).append((x,x+1404))

    def test_actual_lane_driver_clock_and_failed_hold_endpoint_binding(self):
        for v in self.model['models'].values():
            for lane in v['placement']['lanes']:
                self.assertEqual(len(lane['existing_s1_e_D_pins']),11)
                for pin in lane['existing_s1_e_D_pins']:
                    self.assertEqual(len(pin['data_net']['drivers']),1)
                    self.assertEqual(len(pin['clock_net']['drivers']),1)
        ff=self.model['models']['Qwen']['placement']['critical_paths']['ff_min']['placed_path_pins']
        self.assertEqual(ff[1]['instance'],'u_tree.g_lv[1].g_add[5].u_add.g_w11.u.u_cc.g_r.r[43]$_DFF_PN0_')
        self.assertEqual(ff[2]['instance'],'_287171_')
        self.assertAlmostEqual(ff[3]['first_access_center_um'][0],193.744)
        self.assertAlmostEqual(ff[3]['first_access_center_um'][1],90.855)

    def test_missing_parent_and_all97_cost_provider_contracts(self):
        p=self.model['parent'];self.assertIn('sm_q15',p['absent_paths']);self.assertIn('sm_v15',p['absent_paths'])
        self.assertEqual(p['old_sm_v12_mismatched_TC_pin_count'],70)
        events=self.model['DS_dependency_endpoint_plan']
        self.assertEqual(len(events),97)
        self.assertEqual(len({e['binding_provider_id'] for e in events}),97)
        self.assertEqual(sum(e['nested_WK_opt_in_mapping_required'] for e in events),4)
        self.assertTrue(all(e['TC_drains_delta_cycles']==1 for e in events))
        self.assertTrue(all(e['endpoint_cost_status']=='AWAITING_EXACT_PARENT_ENDPOINT_PROVIDER' for e in events))
        self.assertTrue(all(not e['whole_broadcast_counts_used'] for e in events))

    def test_reproducible_inputs_failure_and_no_admission(self):
        self.assertTrue(self.model['no_admission']);self.assertTrue(self.model['no_RTL_PnR_retry'])
        self.assertEqual(self.model['failed_unchanged']['engineering_verdict'],'FAIL')
        for label,v in self.model['models'].items():
            p=M.DEST/(label+'_placement.json.gz')
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),v['metadata_sha256'])
        self.assertEqual(self.model['next_source_plan']['status'],'MODEL_INPUT_EXTRACTION_PLAN_ONLY_NO_RUN')
        self.assertEqual(self.model['model_tool_sha256'],hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest())


if __name__=='__main__': unittest.main()

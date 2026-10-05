#!/usr/bin/env python3
import copy
import unittest
import hbm_tc_unique_net_sourceplan as U

class Sourceplan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model,cls.manifest=U.build()
    def test_fragment_distinctness_and_weight_sharing(self):
        for name,data in self.manifest.items():
            nets=data['nets'];q=name=='qwen';fragment=[n for n in nets.values() if n['role']=='input_fragment']
            self.assertEqual(len(fragment),32768 if q else 25216)
            self.assertEqual({n['bit'] for n in fragment},set(range(len(fragment))))
            self.assertTrue(all(len(n['endpoints'])==1 for n in fragment))
            weights=[n for n in nets.values() if n['role']=='input_weight']
            self.assertTrue(all(len(n['endpoints'])==(16 if q else 8) for n in weights))
            self.assertEqual(sum(not n['constant_zero'] for n in weights),1920 if q else 2640)
    def test_unconsumed_tags_and_valids_not_charged_as_routes(self):
        for name,data in self.manifest.items():
            self.assertEqual(len(data['unconsumed_output_ports']),48)
            used=[n for n in data['nets'].values() if n['role']=='output']
            self.assertEqual(len(used),2384)
            for n in used:
                if n['family'].endswith(('.ov','.otag')):self.assertIn('g_sub[0]',n['family'])
            self.assertEqual(len(used)+48*17,3200)
    def test_all_power_rectangles_preserved_and_OBS_not_free(self):
        for name,m in self.model['models'].items():
            a=m['actual_macro_abstract'];self.assertEqual(len(a['power_rectangles']),44 if name=='qwen' else 34)
            self.assertGreater(a['power_union_area_by_layer_um2']['M6'],1000)
            self.assertEqual({r['layer'] for r in a['OBS'] if r['layer'].startswith('M')},{'M'+str(i) for i in range(1,7)})
            self.assertTrue(a['upper_layer_no_OBS_is_not_free_capacity'])
            self.assertEqual(m['parent_PDN']['actual_parent_route_occupancy'],'NOT_RETAINED')
        test='SIZE 2 BY 2 ;\n  PIN VDD\n USE POWER ;\n PORT\n LAYER M6 ;\n RECT 0 0 1 1 ;\n RECT 1 0 2 1 ;\n END\n  END VDD\n'
        self.assertEqual(len(U.full_lef(test)['pins']['VDD']['rectangles']),2)
        self.assertEqual(U.union_area([[0,0,2,2],[1,1,3,3]]),7)
    def test_cut_demand_counts_unique_identity_and_preserves_driver_uncertainty(self):
        for m in self.model['models'].values():
            for c in m['partition_channel_demand']:
                self.assertEqual(c['total_unique_lower'],len(set(c['mandatory_spanning_net_ids'])))
                self.assertLessEqual(c['total_unique_lower'],c['total_unique_upper'])
                self.assertNotIn('input_fragment',c['source_bound_unique_crossing_lower_by_role'])
        q=self.model['models']['qwen']['partition_channel_demand'][0]
        self.assertEqual(q['total_unique_lower'],499) # 480 shared variable weight nets +19 metadata.
    def test_alignment_and_area_do_not_invent_a_safe_placement(self):
        for name,m in self.model['models'].items():
            p=m['cut_plan'];L=32 if name=='qwen' else 16
            self.assertEqual(sum(p['fields_per_lane'].values()),40)
            self.assertEqual(sum(p['alignment_added_FF'].values()),19)
            self.assertEqual(p['minimum_added_FF_bits'],40*L+19)
            self.assertLess(p['FF_area_upper_um2'],p['unused_core_area_arithmetic_um2'])
            self.assertEqual(p['safe_physical_cut_location'],'NOT_ESTABLISHED_FROM_RETAINED_SOURCES')
            self.assertEqual(len(p['lane_source_endpoints']),L)
            self.assertEqual(p['clock_assumptions']['new_clock_loads'],40*L+19)
    def test_all_97_DS_event_dependencies_bound_without_broadcast_counts(self):
        events=self.model['event_dependency_plan'];ds=[e for e in events if e['model']=='deepseek_v41'];q=[e for e in events if e['model']=='qwen']
        self.assertEqual(len(ds),97);self.assertEqual(len({e['pc'] for e in ds}),97)
        self.assertEqual(sum(e['nested_WK_opt_in_mapping_required'] for e in ds),4)
        self.assertEqual({e['pc'] for e in ds if e['nested_WK_opt_in_mapping_required']},{121,449,782,1110})
        self.assertTrue(all(e['TC_drains_delta_cycles']==1 and not e['whole_broadcast_counts_used'] for e in events))
        self.assertEqual(len(q),434)
        self.assertEqual(sum(e['requires_general_BF16_weight_feed_not_existing_W8_SM_decode'] for e in q),144)
        self.assertTrue(all(e['binding_provider_id'] and e['actual_graph_consumers_PCs'] for e in ds))
        self.assertTrue(all('EXPOSED_INPUT_READY_SHIFT(event)' in e['result_visible_delta_expression'] for e in events))
    def test_constant_and_failure_limits(self):
        self.assertTrue(all(U.i8word(c)&1==0 for c in range(256)))
        self.assertEqual(U.i8word(0),0);self.assertEqual(U.i8word(1),0x3f80);self.assertEqual(U.i8word(128),0xc300)
        self.assertEqual(self.model['models']['qwen']['constant_zero_input_bit_incidences'],2048)
        self.assertEqual(self.model['models']['deepseek_v41']['constant_zero_input_bit_incidences'],4096)
        self.assertTrue(self.model['no_admission']);self.assertTrue(self.model['no_RTL_PnR_retry'])
        self.assertEqual(self.model['failed_unchanged']['engineering_verdict'],'FAIL')
        self.assertEqual(self.model['review_gate']['status'],'SOURCEPLAN_FOR_PARENT_REVIEW_NOT_BUILD_READY')
    def test_rejects_bubble_gate_elimination_source_drift(self):
        texts={k:v for k,v in self.model['source_contract_checks'].items()}
        U.source_contract(texts)
        texts['bubble']='wire [15:0] wg = w_q;'
        with self.assertRaises(ValueError):U.source_contract(texts)

if __name__=='__main__':unittest.main()

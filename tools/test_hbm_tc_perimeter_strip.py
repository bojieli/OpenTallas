#!/usr/bin/env python3
import copy
import json
import unittest
import hbm_tc_perimeter_strip_model as P


class PerimeterStrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model,cls.nets=P.build()

    def test_budget_counts_actual_cells_and_no_decap_credit(self):
        for name,m in self.model['models'].items():
            L=m['lanes'];b=m['area_budget'];t=b['terms']
            self.assertEqual(b['FF_count'],40*L+19)
            self.assertEqual(t['hold_buffers_cap']['count'],2*(40*L+19)+2)
            self.assertEqual(t['signal_buffers_cap']['count'],40*L+19)
            self.assertAlmostEqual(t['hold_buffers_cap']['area_each'],.0729)
            self.assertAlmostEqual(t['CTS_buffers_cap']['area_each'],.4374)
            self.assertAlmostEqual(t['lane_and_alignment_FF']['area_each'],.37908)
            self.assertEqual(b['decap_replacement_credit_um2'],0)
            self.assertEqual(b['clock_tree_level_counts'],[82,21,6,2,1] if L==32 else [42,11,3,1])

    def test_strip_stays_outside_retained_core_and_packs_FFs(self):
        for name,m in self.model['models'].items():
            side=220 if m['lanes']==32 else 164
            for alt in m['alternatives']:
                x,y=alt['old_core_translation_um'];core=[x,y,x+side,y+side]
                for bank in alt['banks']:
                    a,b,c,d=bank['bank_rect_um']
                    self.assertFalse(min(c,core[2])>max(a,core[0]) and min(d,core[3])>max(b,core[1]))
                    self.assertGreaterEqual(bank['largest_FF_rectangular_packing_capacity'],40)
                    self.assertEqual(len(bank['existing_semantic_D_pins']),31)
                self.assertGreaterEqual(alt['bank_cell_area_capacity_at_policy_um2'],m['area_budget']['total_cell_area_cap_um2'])
                self.assertEqual(len(alt['alignment_paths']),19)
                self.assertEqual(alt['parent']['halo_overlaps'],0)

    def test_actual_aliases_and_exponent_add_not_direct_aliases(self):
        for m in self.model['models'].values():
            for alt in m['alternatives']:
                for bank in alt['banks']:
                    pp=bank['existing_semantic_D_pins']
                    self.assertEqual(sum(p['merged_valid_alias'] for p in pp),1)
                    self.assertEqual(sum(p['synthesized_synchronous_reset_mux_before_D'] for p in pp),2)
                    self.assertIn('not direct pin aliases',bank['field_bindings']['da[9:0],db[9:0]'])

    def test_parent_outline_origins_halo_and_modest_policy_cost(self):
        expected={'qwen':([225.184,230.8],[1900.8,2175.12]),'deepseek_v41':([164,174.8],[1400,1661.04])}
        for name,m in self.model['models'].items():
            alt=next(a for a in m['alternatives'] if a['id']==m['selected_model_alternative_id'])
            self.assertEqual(alt['edge'],'N')
            self.assertEqual(alt['outline_um'],expected[name][0])
            self.assertEqual(alt['parent']['inventory_slot_cost_um'],expected[name][1])
            self.assertFalse(alt['parent']['inventory_fits_existing_slot'])
            self.assertEqual(len(alt['parent']['placements']),85 if name=='qwen' else 168)
            self.assertGreater(alt['parent']['candidate_32SM_die_slot_area_delta_mm2'],0)
            self.assertTrue(m['selection_is_not_adoption'])

    def test_unique_parent_nets_and_directional_ceiling_are_not_free_tracks(self):
        for name,m in self.model['models'].items():
            n=self.nets[name]['nets']
            self.assertEqual(sum(v['role']=='input_fragment' for v in n.values()),32768 if name=='qwen' else 25216)
            for cut in m['parent_partition_channel_demand']:
                self.assertEqual(cut['total_unique_lower'],len(set(cut['mandatory_spanning_net_ids'])))
                self.assertLessEqual(cut['total_unique_lower'],cut['total_unique_upper'])
            for alt in m['alternatives']:
                grid=alt['seam_directional_track_ceiling']
                self.assertEqual({g['layer'] for g in grid['directional_grid']},{'M3','M5'} if alt['edge'] in ('N','S') else {'M4','M6'})
                self.assertTrue(all(g['available_track_lower_bound']==0 for g in grid['directional_grid']))
            self.assertEqual(m['seam_declared_net_demand']['alignment_D_and_Q'],38)

    def test_all97_DS_and_Qwen_ready_commit_dependencies_preserved(self):
        events=self.model['event_dependency_plan'];ds=[e for e in events if e['model']=='deepseek_v41'];q=[e for e in events if e['model']=='qwen']
        self.assertEqual(len(ds),97);self.assertEqual(len(q),434)
        self.assertEqual(sum(e['nested_WK_opt_in_mapping_required'] for e in ds),4)
        for e in events:
            self.assertIn('EXPOSED_INPUT_READY_SHIFT(event)',e['composed_delta_expression'])
            self.assertIn('OUTPUT_COMMIT_STAGE_SHIFT(event)',e['composed_delta_expression'])
            self.assertEqual(e['parent_readiness_status'],'MISSING_PROVIDER_BLOCKS_COMPOSITION; NO_FREE_READY_SLACK')
            self.assertTrue(e['TC_plus1_replaced_not_added_twice'])
            self.assertFalse(e['whole_broadcast_counts_used'])
            self.assertEqual(e['TC_delta_cases'],{'1.0':1,'1.25':1})
        self.assertTrue(all(e['parent_drain_cycles_by_case']['1.0']==e['old_parent_drain_cycles']+1 for e in ds))

    def test_co_resident_capacity_excludes_hard_halos_and_preserves_unknowns(self):
        for name,m in self.model['models'].items():
            c=m['co_resident_parent_capacity']
            self.assertGreater(c['hard_outline_and_halo_union_clipped_to_core_um2'],c['hard_macro_area_um2'])
            self.assertGreater(c['residual_geometric_area_ceiling_um2'],0)
            self.assertEqual(c['usable_row_area_verified_um2'],0)
            self.assertFalse(c['actual_fit_verified'])
            self.assertFalse(c['route_readiness_verified'])
            self.assertFalse(c['old_TT_arithmetic_counterfactual_qualification_transfer'])
            self.assertEqual(c['resident_declared_register_bits'],sum(t['declared_register_bits'] for t in c['resident_declaration_ledger']))
            self.assertEqual(c['arithmetic_instances_outside_columns']['stack_FP32_add'],80 if name=='qwen' else 32)
            self.assertIn('RF/SIMD credit',c['SIMD_RF_scope'])
            self.assertEqual(len(c['minimal_bounded_provider']['absent_current_parent_route_paths']),2)
        q=self.model['models']['qwen']['co_resident_parent_capacity']
        self.assertLess(q['residual_at_50pct_policy_after_declarations_and_TT_arithmetic_interval_um2'][1],0)
        self.assertTrue(q['counterfactual_is_not_actual_nonfit_or_architectural_impossibility'])
        d=self.model['models']['deepseek_v41']['co_resident_parent_capacity']
        self.assertEqual(d['historical_DS_mapped_stdcell_count'],317108)

    def test_extra_stages_reported_instead_of_silently_keeping_plus1(self):
        # Exercise a route contract longer than the tested 1.25 policy: its
        # precise lane/phase counts must change the column latency expression.
        m=self.model['models']['qwen'];ref=m['alternatives'][2]
        sem=[]
        for b in ref['banks']:
            # Rebuild one representative semantic group in original coordinates.
            fields={}
            for p in b['existing_semantic_D_pins']:fields.setdefault('all',[]).append({'first_access_center_um':p['first_access_center_um']})
            sem.append(dict(lane=b['lane'],consumers=fields,operand_Q_anchors={'all':b['existing_operand_Q_pins']},field_bindings=b['field_bindings'],actual_decode_output_coordinates='unbound'))
        policy=copy.deepcopy(P.POLICY);policy['route_length_ratio_cases']=[3.]
        a=P.propose('N',220,m['area_budget'],sem,[],policy)
        expected=max(b['transport_cases'][0]['predecode_input_reference_stages'] for b in a['banks'])+max(b['transport_cases'][0]['return_transport_stages'] for b in a['banks'])-1
        self.assertEqual(a['maximum_reference_TC_delta_by_ratio']['3.0'],expected)
        self.assertGreater(expected,1)
        self.assertIn('reprice CTS/hold/strip',a['extra_stage_rule'])

    def test_actual_path_specific_timing_and_hold_stay_unqualified(self):
        for name,m in self.model['models'].items():
            for alt in m['alternatives']:
                r=alt['setup_critical_path_reference']
                self.assertEqual(r['startpoint'],'v_q$_DFF_PN0_' if name=='qwen' else 'u.w_q[25]$_DFF_P_')
                self.assertAlmostEqual(r['old_clkq_ps_rounded_report'],130.2 if name=='qwen' else 97.5)
                if name=='qwen':
                    hold=alt['old_tree_hold_strip_candidate']
                    self.assertGreater(hold['via_strip_Manhattan_um'],hold['direct_Manhattan_um'])
                    self.assertTrue(hold['old_tree_setup_and_new_skew_provider_required'])
            if name=='qwen':
                hybrid=next(a for a in m['alternatives'] if a['id']=='N_PLUS_E_HOLD_TAB')
                north=next(a for a in m['alternatives'] if a['id']=='N')
                self.assertEqual(m['selected_model_alternative_id'],hybrid['id'])
                self.assertLess(hybrid['old_tree_hold_strip_candidate']['wire_fit_setup_cost_sensitivity_ps'],40)
                self.assertLessEqual(hybrid['parent']['inventory_slot_cost_um'][0]-north['parent']['inventory_slot_cost_um'][0],1.)
                self.assertEqual(hybrid['parent']['inventory_slot_cost_um'][1],north['parent']['inventory_slot_cost_um'][1])
                self.assertEqual(m['seam_declared_net_demand']['east_hold_tab_seam_declared_incidence_cap'],52)
        self.assertTrue(self.model['timing']['geometry_never_closes_logic_or_hold'])
        self.assertEqual(self.model['failed_unchanged']['engineering_verdict'],'FAIL')
        self.assertTrue(self.model['no_admission']);self.assertTrue(self.model['no_RTL_PnR'])


if __name__=='__main__':unittest.main()

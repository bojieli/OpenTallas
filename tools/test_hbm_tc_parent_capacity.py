#!/usr/bin/env python3
import unittest
import hbm_tc_parent_capacity_model as M
from hbm_tc_parent_retained_extract import census, category


class ParentCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=M.build()

    def test_live_census_matches_retained_import_and_counts_FF_once(self):
        for name,m in self.m['models'].items():
            c=m['actual_retained_mapped_census']
            self.assertEqual(c['unique_FF']['count'],185341 if name=='qwen' else 77192)
            self.assertEqual(c['mapped_stdcell']['count'],899542 if name=='qwen' else 317108)
            self.assertEqual(c['dead_instance_count'],0 if name=='qwen' else 63653)
            self.assertAlmostEqual(c['unique_FF']['area_um2']+sum(v['area_um2'] for v in c['combinational_cones_by_unique_owner_mask'].values()),c['mapped_stdcell']['area_um2'])
            self.assertEqual(c['unsupported_assignments'],[])

    def test_actual_rows_and_missing_vias_are_not_free_capacity(self):
        for name,m in self.m['models'].items():
            row=m['row_and_PDN_evidence'];r=row['actual_retained_row_cut_records'][0]
            self.assertEqual(r['remaining_sites'],73312707 if name=='qwen' else 33820593)
            self.assertLess(r['remaining_sites'],r['initial_sites'])
            self.assertEqual(row['DEF_paths'],[])
            self.assertGreater(len(row['actual_PDN_warning_records']),0)
            self.assertFalse(row['complete_PDN_via_geometry_available'])
            self.assertEqual(m['free_directional_tracks_verified'],0)

    def test_full_macro_inventory_and_actual_mapped_resident_area(self):
        for name,m in self.m['models'].items():
            b=m['parent_capacity']
            self.assertEqual(m['inventory_macro_count'],85 if name=='qwen' else 168)
            self.assertGreater(b['mandatory_parent_cell_reservation_cap_um2'],b['live_mapped_cell_area_um2'])
            self.assertGreaterEqual(b['protected_band_nominal_row_area_um2']*.5,b['mandatory_parent_cell_reservation_cap_um2'])
            self.assertTrue(b['zero_old_whitespace_credit'])
            self.assertFalse(b['actual_fit_verified'])
        self.assertGreater(self.m['models']['qwen']['parent_capacity']['necessary_minimum_height_delta_at_fixed_width_um'],0)

    def test_all97_and434_endpoint_cases_carry_unknown_old_readiness(self):
        self.assertEqual(self.m['DS_event_count'],97);self.assertEqual(self.m['Qwen_event_count'],434)
        for e in self.m['event_dependency_plan']:
            self.assertIn('actual_input_arrival_new',e['dependency_composition'])
            self.assertTrue(e['old_parent_readiness_never_assumed_free'])
            self.assertFalse(e['target_mapping_admission'])
            self.assertEqual(e['per_macro_ready_commit_transport_table_ref'],e['model']+'.per_macro_ready_commit_transport_cases')
            table=self.m['models'][e['model']]['per_macro_ready_commit_transport_cases']
            self.assertEqual(len(table),64 if e['model']=='qwen' else 32)
            for r in table:
                self.assertFalse(r['actual_endpoint_coordinates'])
                self.assertEqual(r['old_ready_commit_wire_stages'],'ABSENT_PLACED_PROVIDER')

    def test_transport_reserves_unique_nets_and_reprices_FF_CTS_hold_to_fixed_point(self):
        for m in self.m['models'].values():
            for case in m['transport_and_slot_reservation_cases'].values():
                self.assertLessEqual(case['balanced_transport_FF_count_interval'][0],case['priced_transport_FF_upper'])
                self.assertEqual(case['fixed_point_trace'][-1]['extra_transport_FF_priced'],case['priced_transport_FF_upper'])
                self.assertLessEqual(case['fixed_point_trace'][-1]['required_branch_FF_upper'],case['priced_transport_FF_upper'])
                self.assertEqual(case['parent_capacity_with_transport']['live_mapped_FF_count'],m['actual_retained_mapped_census']['unique_FF']['count']+case['priced_transport_FF_upper'])
                self.assertTrue(case['physical_topology_and_alignment_gate_required'])
                self.assertGreater(case['per_source_unique_family']['input_fragment']['unique_nets'],0)
            self.assertFalse(m['full_goal_inventory_verified'])
            self.assertEqual(m['full_goal_missing_resident_obligations']['SIMT_FP32_lanes'],128)

    def test_shared_arithmetic_failure_blocks_adoption_without_duplicate_repair(self):
        d=self.m['arithmetic_admission_dependency']
        self.assertEqual(d['owner'],'Epicurus')
        self.assertEqual(d['source_sha256'],d['witness']['source_sha256'])
        self.assertFalse(d['repair_hardware_work_duplicated'])
        self.assertTrue(self.m['no_admission'])
        self.assertTrue(self.m['no_checkpoint_payload_reads'])
        self.assertEqual(self.m['failed_unchanged']['engineering_verdict'],'FAIL')

    def test_netlist_pruning_handles_vector_aliases_dead_logic_and_shared_cones(self):
        lib={'DFFHQNx1_ASAP7_75t_R':dict(area_um2=.2916,outputs=['QN']),
             'BUFx2_ASAP7_75t_R':dict(area_um2=.0729,outputs=['Y'])}
        text='''  input din;
  output [1:0] out;
  wire [1:0] out;
  assign out = {b,a};
  BUFx2_ASAP7_75t_R common (
    .A(din),
    .Y(n)
  );
  DFFHQNx1_ASAP7_75t_R g_col[0].u_comb.u_add.ff (
    .D(n),
    .CLK(clk),
    .QN(a)
  );
  DFFHQNx1_ASAP7_75t_R g_col[0].u_stack.u_add.ff (
    .D(n),
    .CLK(clk),
    .QN(b)
  );
  BUFx2_ASAP7_75t_R dead (
    .A(din),
    .Y(unused)
  );
'''
        c=census(text,lib)
        self.assertEqual(c['dead_instance_count'],1)
        self.assertEqual(c['unique_FF']['count'],2)
        self.assertEqual(c['combinational_cones_by_unique_owner_mask']['3']['count'],1)
        self.assertEqual(category('g_scale[1].u_mul.ff'),4)


if __name__=='__main__':unittest.main()

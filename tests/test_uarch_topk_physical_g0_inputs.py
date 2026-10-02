import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_physical_g0_inputs as M

class FullPhysicalInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=M.build(ROOT);cls.pins={}
        cls.grid=M.load(ROOT,M.GRID,'results/uarch/dsrom_l20_hierarchical_reservation_20261002/grid_inputs/DS_grid.json',cls.pins)
    def test_full_shape_and_state_not_runtime_mask(self):
        r=self.result;self.assertEqual(r['compiled']['NMAX'],2048);self.assertEqual(r['runtime_counts'],[512,2048])
        self.assertEqual(r['full_state_bits'],698354);self.assertEqual(r['candidate_memory_bits'],524288)
        ledger=r['register_ledger'];self.assertEqual(sum(ledger['retained'].values())+sum(ledger['additional_integer'].values())+sum(ledger['additional_filter'].values()),r['full_state_bits'])
        self.assertEqual(ledger['released_or_aliased_state_credit'],0);self.assertEqual(r['source_contexts'],1)
    def test_complete_logic_area_exact_once(self):
        a=self.result['area'];self.assertAlmostEqual(sum(a['cell_area_groups_um2'].values()),a['full_cell_master_construction_um2'])
        self.assertAlmostEqual(a['full_proxy_core_mm2_50pct'],1.68241961736)
        self.assertAlmostEqual(a['new_complete_selector_charge_over_already_priced_state_mm2']+a['already_priced_state_core_mm2'],a['row_aligned_complete_slot_mm2'])
        self.assertAlmostEqual(a['increment_over_current_parent_selector_charge_mm2'],0.1744561152)
    def test_existing_pins_and_metadata_included(self):
        r=self.result;self.assertEqual(r['ports']['signal_pin_tracks'],4210)
        self.assertEqual(sum(sum(x.values()) for x in r['ports']['bit_inventory'].values()),4210)
        self.assertEqual(r['ports']['new_product_ports'],0);self.assertEqual(r['ports']['load_result_wire_alias_credit'],0)
    def test_grid_phase_aliases_deduplicated(self):
        grid={'grids':[dict(layer='M2',Y=[[9,10,36]]*7)]}
        r=M.track_count(grid,['M2'],'Y',0,360)
        self.assertEqual(r['unique_phased_raw_tracks'],10)
        self.assertEqual(r['signal_tracks_after_50pct_reserve'],5)
    def test_actual_M2_interleaved_grid_agrees_with_independent_enumeration(self):
        lo=8953200;hi=9134640
        r=M.track_count(self.grid,['M2'],'Y',lo,hi)
        patterns=next(x for x in self.grid['grids'] if x['layer']=='M2')['Y']
        expected=sum(any((pos-start)%step==0 for start,count,step in patterns) for pos in range(lo,hi))
        self.assertEqual(r['per_layer']['M2'],expected)
    def test_minimum_corridor_is_row_aligned_and_admits_all_distinct_pins(self):
        r=self.result;n=r['ports']['signal_pin_tracks'];p=r['placement']
        for axis,field,layers in [('Y','horizontal_escape_bbox_DBU',['M2','M4']),('X','vertical_escape_to_collective_lower_boundary_bbox_DBU',['M3','M5'])]:
            b=p[field];lo=b[1] if axis=='Y' else b[0];hi=b[3] if axis=='Y' else b[2]
            span=hi-lo
            self.assertEqual(span%2160,0);self.assertGreaterEqual(M.track_count(self.grid,layers,axis,lo,hi)['signal_tracks_after_50pct_reserve'],n)
            self.assertLess(M.track_count(self.grid,layers,axis,lo,hi-2160)['signal_tracks_after_50pct_reserve'],n)
    def test_clear_geometry_is_not_route_admission(self):
        r=self.result;self.assertEqual(r['placement']['positive_retained_rectangle_overlaps'],[])
        self.assertEqual(r['placement']['retained_geometry_checked'],dict(bands=4,cfg=14336,field=2048,macros=8192,services=14))
        self.assertFalse(r['G0']['RTL_admitted']);self.assertFalse(r['G0']['PR_admitted'])
        self.assertIsNone(r['tracks']['actual_full_die_routed_capacity']);self.assertTrue(r['placement']['unknown_allocations_not_assumed_free'])
    def test_corridor_union_and_no_duplicate_intersection(self):
        p=self.result['placement'];a=p['horizontal_escape_bbox_DBU'];b=p['vertical_escape_to_collective_lower_boundary_bbox_DBU']
        shared=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
        self.assertAlmostEqual(M.area(a)+M.area(b)-M.area(shared),2.6571105216)
        self.assertAlmostEqual(self.result['area']['selector_plus_corridor_increment_no_containment_credit_mm2'],2.8315666368)
    def test_full_actual_call_order_and_latency(self):
        l=self.result['latency'];c=l['calls'];self.assertEqual([(x['layer'],x['runtime_n']) for x in c],[(2,512),(8,512),(14,512),(20,512),(20,2048),(24,512),(28,512),(32,512),(36,512)])
        self.assertEqual(l['serial_service_envelope_edges_per_position'],3531)
        self.assertEqual(l['minimum_burst_load_edges_per_position'],768)
        self.assertEqual(l['burst_load_plus_service_envelope_edges_per_position'],4299)
        self.assertEqual(l['added_service_edges_per_position'],1278);self.assertEqual(l['added_ns_at_policy_1p2GHz'],1065)
        self.assertIsNone(l['actual_relocated_transport_latency_delta']);self.assertIsNone(l['fulltoken_or_MTP_rate'])
    def test_internal_buses_not_fake_common_bisection(self):
        i=self.result['tracks']['internal_planes'];self.assertEqual(i['hist_first_registered_payload_bits'],16384)
        self.assertEqual(i['sort_lane_bisection_record_tracks_one_distance32_level'],2496)
        self.assertEqual(i['prefix_lane_bisection_remote_count_tracks_distance32_level'],224)
        self.assertIn('not summed',i['scope'])
    def test_long_hops_are_explicitly_unadmitted_not_free(self):
        r=self.result;w=r['clock']['wire_context_screen']
        self.assertAlmostEqual(w['maximum_hop_um_before_stage_logic'],767.7631578947369)
        self.assertAlmostEqual(w['flat64lane_over_entire_slot_max_xor32_hop_um'],1062.72)
        self.assertFalse(w['flat64lane_wholewidth_hop_passes_nonlogic_wire_screen'])
        self.assertEqual(w['endpoint_rectangle_conditional_minimum_segment_counts'],{'collective':19,'VM':22})
        self.assertFalse(w['existing_physical_register_or_link_segments_verified'])
        self.assertIsNone(r['latency']['actual_relocated_transport_latency_delta'])
    def test_RF_intensity_and_no_compute_credit(self):
        r=self.result;i=r['integer_and_communication_intensity']
        self.assertEqual(i['internal_RF_read_bytes_to_load_byte_ratio'],3)
        self.assertEqual(i['hist_add_nodes_per_issued_row'],16128)
        self.assertEqual(i['filter_sort_compare_exchange_nodes_per_row'],672)
        self.assertEqual(r['MACs_per_edge'],0)
    def test_uncertainties_and_headline_policy_unchanged(self):
        c=self.result['clock'];self.assertEqual(c['period_ps'],833);self.assertEqual(c['setup_uncertainty_ps'],60);self.assertEqual(c['hold_uncertainty_ps'],25)
        self.assertFalse(c['SS_FF_closed']);self.assertEqual(self.result['headline_policy']['status'],'AGENTIC_MEDIAN_SOURCE_PENDING')
    def test_known_overlap_not_clear_credit(self):
        self.assertTrue(M.overlap([0,0,10,10],[9,0,20,10]))
        self.assertFalse(M.overlap([0,0,10,10],[10,0,20,10]))
        self.assertEqual(M.closest_L1([0,0,10,10],[20,30,40,50]),30)

if __name__=='__main__':unittest.main()

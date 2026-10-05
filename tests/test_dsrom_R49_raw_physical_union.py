import gzip,json,sys,unittest
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_R49_raw_physical_union as g
class RawPhysical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.load(open(g.BASE/'model.json'))
        cls.cells={str(s):[json.loads(v) for v in gzip.decompress((g.BASE/f'shard{s}_cells.jsonl.gz').read_bytes()).decode().splitlines()] for s in (0,1)}
        cls.nets={str(s):[json.loads(v) for v in gzip.decompress((g.BASE/f'shard{s}_clock_nets.jsonl.gz').read_bytes()).decode().splitlines()] for s in (0,1)}
    def test_physical_shards_and_source_owned_seats(self):
        for s,c in self.x['physical_shards'].items():
            self.assertEqual(c['seats'],320 if s=='0' else 256)
            self.assertEqual(len(c['rows']),c['seats'])
            for r in c['rows']:
                self.assertEqual((r['owned_global_row']%256)//2,r['logical_root'])
                self.assertEqual(r['logical_root']//64,int(s))
                self.assertEqual(r['logical_root']%64,r['local_root'])
    def test_feedback_width_and_cost_are_once(self):
        self.assertEqual(self.x['raw_bit_width_DBU'],2970);self.assertEqual(self.x['raw_word_width_DBU'],204930)
        self.assertEqual(self.x['mandatory_width_delta_DBU'],52164)
        for s,c in self.x['physical_shards'].items():
            feedback=[p for p in self.cells[s] if p['role'] in ('feedback0','feedback1')]
            self.assertEqual(len(feedback),2*c['seats']*69)
            self.assertTrue(all(p['master']==g.BUF for p in feedback))
            self.assertTrue(c['feedback_cells_in_width_not_recharged'])
    def test_complete_disjoint_body_sites_and_no_clock_cell_aliasing(self):
        for s,pp in self.cells.items():
            names=[p['instance'] for p in pp];self.assertEqual(len(names),len(set(names)))
            rows=defaultdict(list)
            for p in pp:
                x,y,X,Y=p['bbox_DBU'];self.assertEqual(x%54,0);self.assertEqual(y%270,0);self.assertEqual(Y-y,270)
                rows[y].append((x,X,p['instance']))
            for rs in rows.values():
                rs.sort()
                for a,b in zip(rs,rs[1:]):self.assertLessEqual(a[1],b[0],(s,a,b))
    def test_placement_inside_raw_or_explicit_upper_clock_row(self):
        for s,pp in self.cells.items():
            c=self.x['physical_shards'][s]
            for p in pp:
                region=c['upper_clock_site_row_reservation_DBU'] if p['role']=='raw_clock_upper' else c['raw_slot_bbox_DBU']
                a,b,A,B=region;x,y,X,Y=p['bbox_DBU']
                self.assertTrue(a<=x<X<=A and b<=y<Y<=B)
    def test_every_raw_FF_clocked_once_and_all_buffer_inputs_connected_except_one_root(self):
        for s,nets in self.nets.items():
            pp={p['instance']:p for p in self.cells[s]};sinklist=[(p['instance'],p['pin']) for n in nets for p in n['sinks']]
            self.assertEqual(len(sinklist),len(set(sinklist)))
            self.assertEqual({n for n,p in sinklist if p=='CLK'},{n for n,p in pp.items() if p['role']=='dataFF'})
            clockbuf={n for n,p in pp.items() if p['role'] in ('raw_clock_buffer','raw_clock_upper')}
            self.assertEqual(clockbuf-{n for n,p in sinklist if p=='A'},{self.x['physical_shards'][s]['raw_clock_root_input']['instance']})
            self.assertTrue(all(1<=len(n['sinks'])<=8 for n in nets))
    def test_source_hierarchical_clock_cost_has_no_embedding_credit(self):
        self.assertEqual(self.x['raw_only_constructed_clock_buffers'],6521)
        self.assertEqual(self.x['source_body_clock_buffers_whole_owner'],5894)
        self.assertEqual(self.x['minimum_extra_clock_buffers_vs_whole_owner_floor'],627)
        self.assertAlmostEqual(self.x['minimum_extra_clock_cell_area_um2'],63.99162)
        self.assertTrue(self.x['extra_control_clock_tree_not_free'])
        self.assertTrue(self.x['no_automatic_tree_embedding_credit'])
    def test_M1_rails_include_final_MX_VSS_and_clock_pin_supply_phase(self):
        for c in self.x['physical_shards'].values():
            rr=c['PG_M1_literal_rails'];self.assertEqual(len(rr),2*c['seats']+1)
            self.assertEqual(rr[-1]['net'],'VSS');self.assertEqual(rr[-1]['bbox_DBU'][1],c['raw_slot_bbox_DBU'][3]-9)
            self.assertTrue(all(p['layer']=='M1' for p in rr));self.assertEqual(c['raw_resettable_FF_count'],0)
            self.assertFalse(c['parent_PG_via_feeds_and_current_capacity_qualified'])
            self.assertEqual(c['literal_supply_pins_not_in_same_net_rail'],[])
            self.assertTrue(c['upper_clock_rail_bridge_covers_moat'])
    def test_old_control_collision_is_retained_and_new_control_disjoint(self):
        for c in self.x['physical_shards'].values():
            self.assertGreater(c['prior_control_overlap_area_um2'],0)
            self.assertFalse(g.overlap(c['raw_slot_bbox_DBU'],c['shifted_control_bbox_DBU']))
            self.assertEqual(c['prior_control_overlap_bbox_DBU'][2]-c['prior_control_overlap_bbox_DBU'][0],47844)
        self.assertEqual(self.x['complete_parent_known_rectangle_conflicts'],[])
        self.assertTrue(self.x['inside_26x33mm'])
        self.assertEqual(self.x['joined_Maxwell_capture_home_DBU'],[10974906,15562800,11298906,15995610])
        self.assertEqual(self.x['enclosure_delta_per_die_mm2'],0)
        self.assertTrue(self.x['reviewed_Maxwell_R49_home_bound'])
    def test_typed_feedback_endpoints_match_Maxwell_and_forward_bypasses_BUF(self):
        source=g.load('Maxwell_R49_home.json')
        self.assertEqual([p['L1_projection_um'] for p in self.x['typed_feedback_literal_endpoint_template']],[p['L1_projection_um'] for p in source['proposed_feedback_only_pin_routes_per_bit']])
        roles=self.x['source_raw_role_order_from_Maxwell'];self.assertEqual([v['role'] for v in roles],['storage','restore','forward_NAND','feedback_NAND','final_NAND','feedback_BUF0','feedback_BUF1'])
        self.assertEqual([v['x_offset_DBU'] for v in roles],[0,1080,1242,1566,1890,2214,2592])
        self.assertEqual(self.x['forward_path_contract']['new_forward_buffer_count'],0)
        self.assertTrue(self.x['forward_does_not_traverse_feedback_BUF'])
        for write in (False,True):
            for incoming in (False,True):
                for held in (False,True):
                    n0=not(incoming and write);n1=not(held and not write);D=not(n0 and n1)
                    self.assertEqual(D,incoming if write else held)
    def test_finite_capture_and_read_credit_guards_not_assumed_service(self):
        c=self.x['finite_credit_contract']
        self.assertFalse(c['raw_capture_READY']);self.assertTrue(c['reserve_all576_owned_seats_before_phase_GO'])
        self.assertTrue(c['read_sink_seat_reserved_before_issue_required']);self.assertTrue(c['ACK_not_home_visibility'])
        self.assertEqual(c['per_shard_capacity'],[320,256])
        self.assertTrue(c['implemented_read_credit_count_and_token_FIFO_capacity_not_bound'])
        self.assertTrue(c['actual_accepted_consumer_and_capture_deadline_not_bound'])
    def test_local_read_runs_never_create_cross_die_comb_tree(self):
        rr=self.x['proposed_ordered_read_runs'];self.assertEqual([v['physical_shard'] for v in rr],[0,1,0,1,0])
        self.assertEqual([(v['row_begin'],v['row_end_exclusive']) for v in rr],[(0,128),(128,256),(256,384),(384,512),(512,576)])
        self.assertEqual([c['source_local_read_mux_node_count'] for c in self.x['physical_shards'].values()],[319,255])
        self.assertTrue(self.x['read_runs_do_not_prove_service_rate_or_deadlines'])
    def test_finite_port_and_storage_counts(self):
        for c in self.x['physical_shards'].values():
            self.assertEqual(c['raw_record_bits'],c['seats']*69)
            self.assertEqual(c['maximum_root_boundary_bits_per_stream_cycle'],4416)
            self.assertEqual(c['maximum_root_boundary_bytes_per_stream_cycle'],552)
            self.assertEqual(c['MACs_per_cycle'],0)
            self.assertEqual(c['control_reset_count_not_silently_split_or_replicated'],1483)
    def test_source_receipts_and_artifacts(self):
        for r in self.x['source_origins']:self.assertEqual(g.sha(g.BASE/'inputs'/r['copy']),r['sha256'])
        for s,c in self.x['physical_shards'].items():
            self.assertEqual(g.sha(g.BASE/f'shard{s}_cells.jsonl.gz'),c['cell_artifact_sha256'])
            self.assertEqual(g.sha(g.BASE/f'shard{s}_clock_nets.jsonl.gz'),c['net_artifact_sha256'])
    def test_finite_clock_wire_screen_preserves_failed_source_allowance(self):
        for c in self.x['physical_shards'].values():
            bad=c['clock_nets_exceeding_source_5p76_wire_allowance'];self.assertGreater(len(bad),0)
            for n in bad:
                self.assertGreater(n['M8_M9_family_minimum_metal_C_fF'],5.76)
                self.assertAlmostEqual(n['M8_M9_family_minimum_metal_C_fF'],n['spanning_L1_um']*.0928446)
        self.assertTrue(self.x['clock_wire_RC_is_not_extracted'])
    def test_Epic_literal_cut_and_core_intake_remains_preparation(self):
        s=self.x['selector_source_join'];self.assertEqual([h['EDGES'] for h in s['literal_packet_cut_helpers']],[99,99,28])
        self.assertEqual(s['transport_tie_providers'],229)
        self.assertEqual(s['additional_core_ASR_and_tie_providers'],35)
        self.assertEqual(s['core_added_state_bits'],127140)
        self.assertTrue(s['mapped_primitive_and_backend_qualification_not_supplied'])
        self.assertFalse(s['source_compile_admitted'])
        self.assertIsNone(s['actual_consumer_deadline'])
        self.assertTrue(s['source_capture_timing_FAIL_preserved'])
    def test_complete_core_and_transport_state_and_cost_counted_once(self):
        c=self.x['selector_complete_known_cost_once']
        self.assertEqual(c['core_state_gross'],698354);self.assertEqual(c['core_state_increment'],127140)
        self.assertEqual(c['original_core_state_inferred'],571214)
        self.assertEqual(c['transport_payload_and_present_FF'],476180)
        self.assertEqual(c['core_plus_transport_state_gross'],1174534)
        self.assertAlmostEqual(c['old_station_body_exact_reproduced_um2'],311689.62162)
        self.assertTrue(c['old_station_not_recharged_as_new_transport'])
        self.assertAlmostEqual(c['transport229_tie_body_um2'],10.01646)
        self.assertAlmostEqual(c['transport19_guard_body_um2'],1.66212)
        self.assertAlmostEqual(c['core35_ASR_replacement_and_ties_delta_um2'],4.5927)
        self.assertAlmostEqual(c['complete_known_construction_body_um2'],1152915.70158)
        self.assertAlmostEqual(c['complete_known_construction_at50pct_reserve_mm2'],2.30583140316)
        self.assertTrue(c['source_constructor_not_mapped_physical_area'])
        self.assertTrue(c['old_station_containment_inside_fixed418_debit_not_proven'])
        self.assertTrue(c['parent_review_is_static_only'])
    def test_no_physical_or_timing_transfer(self):
        self.assertFalse(self.x['physical_build_admitted']);self.assertFalse(self.x['actual_pipeline_adopted'])
        self.assertEqual(self.x['added_capture_edges'],0)
        self.assertEqual(self.x['SS_setup_uncertainty_ps'],60);self.assertEqual(self.x['FF_hold_uncertainty_ps'],25)
        self.assertTrue(self.x['complete_element_M2_PG_not_transferred'])
        for c in self.x['physical_shards'].values():
            self.assertTrue(c['equal_depth_is_not_skew']);self.assertTrue(c['no_shared_576_comb_tree'])
            self.assertFalse(c['clock_SKew_and_RC_qualified'])
    def test_selector_complete_clock_home_and_no_implicit_area_credit(self):
        c=self.x['selector_additional_core_clock_bank']
        self.assertEqual(c['total_selector_state_bits'],1174534)
        self.assertEqual(c['separately_added_core_clock_buffers'],70406)
        self.assertEqual(c['already_priced_transport_clock_buffers'],48007)
        self.assertAlmostEqual(c['core_rectangle_local_colocation_deficit_mm2'],.01192127868)
        self.assertAlmostEqual(c['source_full_reservation_mm2'],2.32020267588)
        self.assertGreaterEqual(c['legal_site_reservation_mm2'],c['source_additional_core_clock_50pct_mm2'])
        self.assertTrue(c['full_bank_debited_not_only_core_rectangle_deficit'])
        self.assertTrue(c['no_corridor_borrowing_or_core_headroom_credit'])
        self.assertEqual(c['conflicts_with_known_field_service_cfg_band_selector_rectangles'],[])
        self.assertGreaterEqual(c['minimum_selector_to_clock_bank_gap_DBU'],4320)
        self.assertTrue(c['parent_PG_feed_vias_current_and_pin_escape_not_qualified'])
        self.assertTrue(c['actual_core_sink_assignment_routes_parent_root_and_matched_skew_not_bound'])
    def test_selector_all_clock_cells_have_unique_disjoint_sites_and_literal_supply_rails(self):
        c=self.x['selector_additional_core_clock_bank'];p=g.BASE/'selector_core_clock_cells.jsonl.gz'
        cells=[json.loads(v) for v in gzip.decompress(p.read_bytes()).decode().splitlines()]
        self.assertEqual(len(cells),70406);self.assertEqual(len({v['instance'] for v in cells}),70406)
        self.assertEqual(g.sha(p),c['cell_artifact_sha256'])
        rows=defaultdict(list);a,b,A,B=c['named_site_bank_bbox_DBU']
        for v in cells:
            x,y,X,Y=v['bbox_DBU'];self.assertEqual(x%54,0);self.assertEqual(y%270,0)
            self.assertTrue(a<=x<X<=A and b<=y<Y<=B);rows[y].append((x,X))
        for values in rows.values():
            values.sort()
            for first,second in zip(values,values[1:]):self.assertLessEqual(first[1],second[0])
        self.assertTrue(c['literal_supply_pin_union_checked']);self.assertTrue(c['no_new_resettable_cells'])
        self.assertTrue(c['existing_selector_RESETN_SETN_union_still_required'])
if __name__=='__main__':unittest.main()

import json
import unittest
from pathlib import Path
from report import area, pack
from private_pin_screen import center, edge
from clear_space import search

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'results/arch/hbm_die_feasibility_1014/geometry_source_report.json'

class GeometryTests(unittest.TestCase):
    def test_literal_pin_layer_and_shape_fail_closed(self):
        self.assertEqual(center([['M4',[0,0,0.084,0.024]]]),('M4',[0.042,0.012]))
        with self.assertRaises(ValueError): center([['M6',[0,0,1,1]]])
        with self.assertRaises(ValueError): center([])
        with self.assertRaises(ValueError): center([['M4',[0,0,float('inf'),1]]])
        with self.assertRaises(ValueError): center([['M4',[0,0,float('nan'),1]]])
        with self.assertRaises(ValueError): center([['M4',[3,0,2,1]]])
        with self.assertRaises(ValueError): center([['M4',[0,0,1,1]],['M4',[2,2,3,3]]])

    def test_literal_screen_covers_all_internal_bits_without_rc_credit(self):
        d=json.loads((REPORT.parent/'private_pin_screen_summary.json').read_text())
        self.assertEqual(d['covered_internal_edge_bits'],1280)
        self.assertEqual(d['covered_clock_reset_roots'],160)
        self.assertEqual(d['max_manhattan_um'],354.06)
        self.assertFalse(d['wire_delay_measured']);self.assertFalse(d['qualified'])
        self.assertTrue(all(e['measured_wire_ps'] is None for e in d['representative_window_edges']))

    def test_search_includes_obstacle_beyond_origin_range(self):
        c={'die_um':[100,100],'children':[{'instance':'neighbor','xy_um':[21,10],'w_um':5,'h_um':20}],'routing_corridor_reservations':[],'ring_device_column_reservations':[]}
        count,valid=search(c,10,10,[10,10,20,20],10)
        self.assertEqual(count,1);self.assertEqual(valid,[])

    def test_touching_faces_are_not_overlap(self):
        self.assertEqual(area([0,0,10,10],[10,0,20,10]),0)
        self.assertEqual(area([0,0,10,10],[9,9,20,20]),1)

    def test_real_report_census_and_reservations(self):
        d=json.loads(REPORT.read_text()); rows=d['hc_scalar_proposals']
        self.assertEqual(len(rows),160)
        self.assertEqual(len({r['source_path'] for r in rows}),160)
        self.assertEqual(sum(r['master']=='ot_hgi_hc_win_ctl' for r in rows),32)
        self.assertEqual(sum(r['master']=='ot_hgi_hc_win_sector' for r in rows),128)
        self.assertEqual(d['hc_summary']['overlapping_existing_children'],0)
        self.assertEqual(d['hc_summary']['overlapping_reserved_corridors'],0)
        self.assertFalse(d['qualified']); self.assertTrue(all(not r['assigned'] for r in rows))
        self.assertTrue(all(not r['source_quarter_to_geography_proven'] for r in rows))
        self.assertEqual(d['all_13_source_blobs_verified'],13)
        self.assertEqual(d['hc_summary']['per_reservation_used_envelope_um'],[1231.2,470.88])
        self.assertFalse(d['private_pin_binding_qualified'])

    def test_actual_clock_probe_retains_negative_paths_and_offset_conservation(self):
        import gzip
        from clock_ratio_check import validate
        p=REPORT.parent/'clock_ratio_probe'
        logs={m:gzip.decompress((p/(m+'.log.gz')).read_bytes()).decode() for m in ['ROUNDED','DERIVED','SHIFT100']}
        d=validate(logs)
        self.assertGreater(d['negative_path_count'],0)
        self.assertEqual(len(d['offset_differences']),8)
        self.assertFalse(d['qualified'])
        with self.assertRaises(ValueError):validate({**logs,'DERIVED':logs['DERIVED'].replace('PAIR_BEGIN C V min','MISSING C V min')})
        with self.assertRaises(ValueError):validate({**logs,'SHIFT100':logs['DERIVED'].replace('PROBE_COMPLETE DERIVED','PROBE_COMPLETE SHIFT100')})
        with self.assertRaises(ValueError):validate({**logs,'ROUNDED':logs['ROUNDED']+' STA-1010'})

    def test_frontc_exact_geometry_flags_stale_metadata_without_grant(self):
        d=json.loads((REPORT.parent/'frontc_geometry_binding_audit.json').read_text())
        self.assertEqual(d['exact_bound_LEF_count'],9)
        self.assertEqual(d['stale_candidate_hash_count'],8)
        self.assertEqual(d['geometry_overlap_count'],0)
        self.assertFalse(d['qualified'])
        self.assertEqual(len({r['clock_port'] for r in d['children']}),9)
        self.assertTrue(all(r['actual_clock_source_driver'] is None and r['fixed_TT_source_phase_ps'] is None for r in d['children']))
        self.assertTrue(all(set(r['raw_corner_clock_measurements'])=={'tt','ff','ss'} for r in d['children']))

    def test_frontc_bound_bytes_or_outline_mismatch_refused(self):
        from frontc_screen import check_child,sha
        c={'w_um':10,'h_um':20,'logical_instance':'p/u','xy_um':[0,0],'orientation':'R0','view_sha256':'stale'}
        b={'instance':'u','master':'leaf','clock_port':'raw_u','reset_port':'rst_u','view':{'w_um':10,'h_um':20,'hashes':{'lef':sha(b'actual')}}}
        self.assertFalse(check_child(c,b,b'actual',[])['candidate_recorded_hash_matches_actual'])
        with self.assertRaises(ValueError):check_child(c,b,b'tampered',[])
        c['w_um']=11
        with self.assertRaises(ValueError):check_child(c,b,b'actual',[])

    def test_actual_idx_cut_counts_and_lower_bound_remain_unqualified(self):
        d=json.loads((REPORT.parent/'idx_cut_source_screen.json').read_text())
        self.assertEqual(d['all_source_hashes_verified'],43)
        self.assertEqual(d['actual_clock_names'],2353)
        self.assertEqual(d['actual_catalog_macro_instances'],124)
        self.assertEqual(d['max_retained_glue_bits_per_root'],13860)
        self.assertGreater(d['lower_bound_ratio_vs_legacy_slots'],1.80)
        self.assertFalse(d['fresh_ready_physical_accepted']);self.assertFalse(d['qualified'])

    def test_full_sfu_prototype_preserves_selected_master_and_is_not_grant(self):
        d=json.loads((REPORT.parent/'sfu_full_geometry_prototype.json').read_text())
        self.assertEqual(d['master_count'],36)
        self.assertEqual(sum(r['master']=='ot_su12_sfu' for r in d['children']),16)
        self.assertEqual(d['selected_body_LEF_sha256'],'414fdd99a70a45fdb7c73440a7dabc9d4699d7c84c2be1a4dcf3d5902e4de9f3')
        self.assertEqual(d['nearest_ring_clearance_um'],1.44)
        self.assertTrue(all(not r['assigned'] and not r['existing_child_overlap']['count'] and not r['forbidden_corridor_overlap'] for r in d['children']))
        self.assertFalse(d['source_quarter_to_SW_proven'])

    def test_full_sfu_competition_does_not_grant_clear_trial_row(self):
        d=json.loads((REPORT.parent/'sfu_legacy_overlay.json').read_text())
        self.assertEqual(d['full_quarter_area_screen']['body_count'],16)
        self.assertGreater(d['full_quarter_area_screen']['leaf_area_fraction_before_gutters_ownlogic_PG'],0.95)
        self.assertFalse(d['full_quarter_area_screen']['full_rectangular_packing_proven'])
        self.assertTrue(d['full_quarter_area_screen']['closed_body_stands'])
        self.assertTrue(all(not r['assigned'] for r in d['SW_geometry_only_control_row']))

    def test_actual_rejections_remain_quantified(self):
        d=json.loads(REPORT.read_text())
        self.assertEqual(d['legacy_slot_overlay']['hb_quant/u_qdq']['real_view_count'],14)
        self.assertEqual(d['legacy_slot_overlay']['idx_score_SW']['real_view_count'],107)
        self.assertGreater(d['idx_lower_bound']['area_ratio'],1.73)
        self.assertIsNone(d['clock_reset_policy']['source_binding'])

    def test_missing_source_path_and_small_slot_fail_closed(self):
        d=json.loads(REPORT.read_text()); q=[r for r in d['hc_scalar_proposals'] if r['candidate_reservation']=='UNRESOLVED_HC_SW']
        rows=[]
        for r in q:
            path=r['source_path']; wi=int(path.split('g_win[')[1].split(']')[0])
            rows.append(dict(path=path,master=r['master'],window_index=wi,bank=wi//4,clock=r['clock'],reset_driver=r['reset_driver']))
        outlines={'ot_hgi_hc_win_sector':[140.832,88.56],'ot_hgi_hc_win_ctl':[30.24,25.92]}
        with self.assertRaises(ValueError): pack(rows[:-1],dict(xy_um=[0,0],w_um=1356.48,h_um=756),outlines)
        with self.assertRaises(ValueError): pack(rows,dict(xy_um=[0,0],w_um=500,h_um=756),outlines)
        duplicate=rows[:-1]+[rows[0]]
        with self.assertRaises(ValueError): pack(duplicate,dict(xy_um=[0,0],w_um=1356.48,h_um=756),outlines)

if __name__=='__main__': unittest.main()

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import model_dsrom_selector_causal_timing_join as T

class TimingJoin(unittest.TestCase):
    def test_exact168_branch_demands_existing_first_relay(self):
        m=T.build();items=m['relocation_requirements']
        self.assertEqual(len(items),168)
        self.assertEqual([sum(x['shard']==s for x in items) for s in (0,1)],[102,66])
        self.assertEqual(len({(x['shard'],x['net'],x['destination']) for x in items}),168)
        for x in items:
            self.assertEqual(x['first_relay_ordinal'],0)
            self.assertGreater(x['existing_branch_relay_count'],0)
            self.assertEqual(x['added_graph_cells'],0)
            self.assertGreater(x['optimistic_C_to_any_raw_fF'],x['first_branch_metal_budget_fF'])
            self.assertIsNone(x['needed_new_site'])
            self.assertEqual(len(x['source_Y_literal_rect_DBU']),4)

    def test_moved_bodies_not_new_area_or_core_bank_duplication(self):
        m=T.build()
        self.assertEqual(m['unchanged_graph']['existing_relay_pad_BUF'],68614)
        self.assertEqual((m['unchanged_graph']['added_BUF'],m['unchanged_graph']['removed_BUF']),(0,0))
        self.assertEqual(m['unchanged_graph']['core_clock_BUF'],70406)
        self.assertEqual(m['unchanged_graph']['transport_clock_BUF'],48007)
        self.assertAlmostEqual(m['moved_existing_cell_body_um2'],17.14608)
        self.assertAlmostEqual(m['outside_raw_50pct_space_for_moved_bodies_screen_mm2'],0.00003429216)
        self.assertEqual(m['additional_body_area_um2'],0)
        self.assertIsNone(m['actual_owner_space_or_total_reticle_delta_mm2'])

    def test_causal_stages_exact_control_widths(self):
        m=T.build();stages=m['selector_source_stages']
        self.assertEqual(len(stages),60)
        expected={'hist':6,'suffix_up':8,'suffix_down':8,'choose':2,'winner':7,'winner_root':1,'equal_prefix':6,'quota_feedback':1,'stable_compaction':21}
        self.assertEqual({k:sum(x['family']==k for x in stages) for k in expected},expected)
        self.assertEqual(m['largest_pick_stage_raw_control_receiver_bits'],3840)
        quota=next(x for x in stages if x['family']=='quota_feedback')
        self.assertEqual(quota['feedback_width_bits'],14)
        self.assertFalse(quota['returned_credit_or_ACK'])
        self.assertTrue(all(x['loaded_timing'] is None for x in stages))

    def test_source_control_or_order_mutants_refused(self):
        src=(T.ROOT/T.CORE).read_text()
        for old,new in [('if(st==S_PICK && pk==16) choose_lower_sum','if(st==S_PICK && pk==15) choose_lower_sum'),
                        ("CB'(eq_count_5[l-1])<eq_left","CB'(eq_count_5[l-1])<=eq_left"),
                        ('if (st == S_DRAIN && !fpipe && stn == 0 && !out_valid)','if (st == S_DRAIN)')]:
            self.assertIn(old,src)
            with self.assertRaises(ValueError):T.pipeline(src.replace(old,new))

    def test_retained_RF_emit_paths_and_no_credit(self):
        m=T.build();cones=m['retained_source_cones']
        self.assertEqual(cones[0]['memory_bits'],524288)
        self.assertEqual(cones[0]['bytes_per_load_edge'],256)
        self.assertEqual(cones[2]['bytes_per_filter_read_edge'],512)
        self.assertEqual(cones[3]['bytes_per_result_edge'],256)
        self.assertEqual(cones[4]['sink_VM_ready_required'],1)
        self.assertIsNone(cones[4]['actual_visibility_deadline'])
        for key in ('SSFF','physical_admitted','full_token_credit','hardware_source_modified','frontend_sim_STA_PR_launched'):
            self.assertFalse(m[key])
        self.assertIsNone(m['current_job'])
        self.assertFalse(m['unchanged_graph']['timeout4096_adopted'])

    def test_fixed_constraints_and_loaded_path_unknowns_explicit(self):
        t=T.build()['timing_contract']
        self.assertEqual((t['period_ps'],t['SS_setup_uncertainty_ps'],t['FF_hold_uncertainty_ps'],t['matched_skew_budget_ps']),(833,60,25,25))
        for key in ('loaded_clock_to_QN_INV_wire_logic_setup','FF_earliest_path_and_hold','decoded_control_fanout_tree_actual_pin_load','reset_recovery_removal','via_contact_OBS_and_PG_extracted_RC'):
            self.assertIsNone(t[key])

    def test_fresh_model_replay_no_git_reads(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'model.json'
            subprocess.run([sys.executable,str(T.ROOT/'tools/model_dsrom_selector_causal_timing_join.py'),'--out',str(out)],cwd=d,check=True,capture_output=True)
            self.assertEqual(out.read_bytes(),(T.BASE/'model_r2.json').read_bytes())
        self.assertEqual(json.loads((T.BASE/'model_r2.json').read_text()),T.build())

if __name__=='__main__':unittest.main()

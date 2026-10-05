import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_buffered_station_source_model as M
class BufferedSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=M.build()
    def test_exact_reproduction(self):self.assertEqual(self.model,json.loads((M.BASE/'model_r2.json').read_bytes()))
    def test_full_geometry_and_source_chain(self):
        m=self.model;self.assertEqual(m['selector_bits_unchanged'],698354)
        self.assertEqual(m['fixed_geometry'],dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14,NBIN=256))
        self.assertEqual(m['owner37cc_proposal_preserved']['ninecall_cycles'],918)
        self.assertEqual(m['owner37cc_proposal_preserved']['segments_each_direction'],46)
    def test_ff_truth_and_buf_only_negative_witness(self):
        for corner in ['SS','FF']:
            f=self.model['cell_facts'][corner]
            for label in ['data_FF','valid_FF']:
                self.assertEqual(f[label]['source_state']['next_state'],'!D')
                self.assertEqual(f[label]['source_state']['output_function'],'IQN')
            self.assertEqual(f['INV']['output_function'],'!A')
            self.assertEqual(f['BUF']['output_function'],'A');self.assertEqual(f['hold']['output_function'],'A')
            for bit in [0,1]:
                qn=1-bit;buf_only=qn;corrected=1-qn
                self.assertNotEqual(buf_only,bit);self.assertEqual(corrected,bit)
    def test_actual_polarity_mutant_refused(self):
        s=(M.C.BASE/'inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib').read_text()
        cell=M.C.group(s,'cell','DFFHQNx1_ASAP7_75t_R')
        altered=s.replace(cell,cell.replace('next_state : "!D"','next_state : "D"'))
        with self.assertRaisesRegex(ValueError,'polarity changed'):M.seq(altered,'DFFHQNx1_ASAP7_75t_R')
    def test_asr_reset_truth(self):
        f=self.model['cell_facts']['SS']['valid_FF']['source_state']
        self.assertEqual(f['preset'],'!RESETN');self.assertEqual(f['clear'],'!SETN')
        qn_when_RESETN_low=1
        self.assertEqual(1-qn_when_RESETN_low,0)
        self.assertTrue(self.model['architecture']['valid_SETN_tied_high'])
    def test_load_and_receiver_domains_include_wire(self):
        s=self.model['SS_conditional_screen']
        for label,limit in [('INV_input',80),('first_BUF_input',160),('repeated_BUF_or_HB_input',160),('destination_FF_input',320)]:
            self.assertLessEqual(s['receiver_slew_ps'][label],limit)
        for link in s['wire_links'].values():
            self.assertAlmostEqual(link['length_ceiling_um']*s['C_fF_per_um']+link['sink_cap_fF'],link['load_ceiling_fF'])
            self.assertAlmostEqual(link['slew_growth_ps_2p2_RC_screen'],2.2*link['RC_delay_upper_ps_uniform_template'])
    def test_mandatory_hb_and_inv_inside_SS_cost(self):
        s=self.model['SS_conditional_screen'];n=self.model['architecture']['repeaters_per_segment']
        expected=s['clkq_ps']+s['INV_delay_ps']+n*s['BUF_delay_ps']+s['HB_delay_ps']+s['setup_ps']+60+25
        expected+=sum(s['wire_links'][k]['RC_delay_upper_ps_uniform_template'] for k in ['FF_to_INV_local','INV_to_first_BUF','HB_to_FF_local'])+n*s['wire_links']['BUF_to_BUF_or_HB']['RC_delay_upper_ps_uniform_template']
        self.assertAlmostEqual(s['stage_upper_ps'],expected)
        self.assertEqual(n,2);self.assertLessEqual(s['stage_upper_ps'],833)
        self.assertGreater(s['one_more_repeater_stage_upper_ps'],833)
    def test_source_valid_FF_worst_clock_and_setup_charged(self):
        s=self.model['SS_conditional_screen'];self.assertEqual(s['clkq_ps'],151.05);self.assertEqual(s['setup_ps'],69.4434)
        self.assertEqual(s['period_ps'],833);self.assertEqual(s['setup_uncertainty_ps'],60)
    def test_hold_is_conditional_not_closed(self):
        h=self.model['FF_conditional_screen']
        self.assertAlmostEqual(h['zero_wire_hold_margins_ps']['data_FF'],9.29656)
        self.assertAlmostEqual(h['zero_wire_hold_margins_ps']['valid_FF'],10.69906)
        self.assertTrue(h['actual_min_wire_and_clock_skew_unqualified'])
        self.assertTrue(h['minimum_actual_net_cap_must_be_at_least0p72fF']);self.assertTrue(h['no_subgrid_earliest_extrapolation_credit'])
    def test_nine_exact_source_calls_and_envelopes(self):
        c=self.model['cost'];calls=c['source_calendar_calls']
        self.assertEqual(len(calls),9);self.assertEqual([x['runtime_n'] for x in calls],[512,512,512,512,2048,512,512,512,512])
        self.assertEqual([x['layer'] for x in calls],[2,8,14,20,20,24,28,32,36])
        self.assertTrue(all(x['additional_transport_cycles']==226 for x in calls))
        self.assertEqual(sum(x['load_service_plus_transport_cycles'] for x in calls),6333)
        self.assertEqual(c['ninecall_cycles'],2034);self.assertEqual(c['ninecall_selector_plus_transport_increment_cycles'],3312)
        self.assertTrue(c['source_deadline_acceptance_not_proven'])
    def test_exact_cell_price_and_retirement(self):
        m=self.model;c=m['cost'];p=m['placement_contract'];a=p['LEF_master_dimensions']
        self.assertEqual(p['segments_each_direction'],100);self.assertEqual(p['formed_write_segments'],29)
        self.assertEqual(c['intermediate_data_FF_bits'],4210*99+2113*28)
        self.assertEqual(c['additional_ASR_valid_FF_bits'],226)
        self.assertEqual(m['architecture']['formed_write_busy_retirement_delay_edges'],28)
        cell=c['intermediate_data_FF_bits']*a['data_FF']['area_um2']+226*a['valid_FF']['area_um2']+c['INV_cells']*a['INV']['area_um2']+(c['data_BUF_cells']+c['clock_BUF_floor_cells'])*a['BUF']['area_um2']+c['terminal_HB_cells']*a['hold']['area_um2']
        self.assertAlmostEqual(c['station_cell_area_um2'],cell)
    def test_clock_floor_not_spatial_credit(self):
        c=self.model['clock_contract'];self.assertEqual(c['BUF_cells'],48007)
        self.assertTrue(c['global_root_to_station_wire_paths_not_in_pin_fanout_floor']);self.assertTrue(c['actual_clock_skew_unqualified'])
        self.assertLess(c['declared_fanout_tree_only_max_spatial_reach_um'],200)
        self.assertTrue(c['matching_launch_and_capture_clock_tree_required'])
    def test_reset_recovery_removal_retained(self):
        r=self.model['reset_contract'];self.assertEqual(r['ASR_source_constraints']['SS']['removal_rising_max_ps'],107.064)
        self.assertEqual(r['ASR_source_constraints']['FF']['removal_rising_max_ps'],67.5064)
        self.assertTrue(r['deassertion_must_meet_recovery_removal_on_actual_clock_tree'])
    def test_no_admission_or_hardware(self):
        m=self.model;self.assertFalse(m['G0']['RTL_admitted']);self.assertFalse(m['G0']['PR_admitted']);self.assertEqual(m['jobs_launched'],0)
        self.assertEqual(m['new_PVE2_PVE3_jobs'],0);self.assertTrue(m['no_variant_sweep'])
        self.assertTrue(m['SS_conditional_screen']['59bb_propagated_dcalc_slew_disagreement_not_resolved_by_model'])
    def test_lut_refuses_uncharacterized(self):
        with self.assertRaisesRegex(ValueError,'outside characterized'):M.lut(self.model['cell_facts']['SS']['BUF']['delay_transition_tables'],'cell_',1000,1000)
    def test_owner_manifest_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'owner_input_manifest.json').write_bytes((M.BASE/'owner_input_manifest.json').read_bytes()+b' ')
            with mock.patch.object(M,'BASE',d):
                with self.assertRaisesRegex(ValueError,'owner manifest changed'):M.owner_inputs()
    def test_archive_only_replay(self):
        with mock.patch.object(M.C.T.F.A.SourceArchive,'commit_available',side_effect=AssertionError('no git dependency')):self.assertEqual(M.build(),self.model)
if __name__=='__main__':unittest.main()

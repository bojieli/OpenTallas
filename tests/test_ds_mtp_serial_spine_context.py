import importlib.util
import json
import unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/'tools/ds_mtp_serial_spine_context.py'
s=importlib.util.spec_from_file_location('spine_reply',P)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class SerialSpine(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.x=m.build()

    def test_actual_scalar_not_BF16(self):
        x=self.x['actual_source']
        self.assertIn('S_SEL FP32',x['X_SEL1_static_draft_path'])
        self.assertEqual((x['current_scalar_IW'],x['required_scalar_IW'],x['TOPK']),(16,21,512))
        self.assertEqual(len(x['missing_widened_points']),4)

    def test_index_counterexample(self):
        witnesses=self.x['actual_source']['finite_witnesses']
        self.assertEqual(witnesses[1],dict(index=65536,retained16=0,required21=65536))
        self.assertEqual(witnesses[2]['retained16'],63743)
        self.assertLess(witnesses[2]['index'],129280)

    def test_full_K_state_not_candidate_K1(self):
        a=m.scalar_state(512,16);b=m.scalar_state(512,21)
        self.assertEqual(a['total'],61536)
        self.assertEqual(b['total'],69226)
        self.assertEqual(b['total']-a['total'],7690)
        self.assertEqual(b['sections']['pass_entries'],511*55)
        self.assertEqual(b['sections']['bank'],512*23)

    def test_increment_each_index_site(self):
        for K in [2,8,512]:
            old=m.scalar_state(K,16);new=m.scalar_state(K,21)
            self.assertEqual(new['total']-old['total'],5*(3*K+2))

    def test_named_trees_exact_1944_sinks(self):
        levels=self.x['local_clock']['prospective_CLK_tree']
        self.assertEqual([len(g) for g in levels],[243,31,4,1])
        sinks=[i for g in levels[0] for i in range(g['first'],g['stop'])]
        self.assertEqual(sinks,list(range(1944)))
        self.assertEqual(self.x['local_clock']['clock_plus_reset_buffers'],558)
        self.assertFalse(self.x['local_clock']['equal_depth_skew_credit'])

    def test_actual_corner_clock_loads(self):
        x=self.x['local_clock']
        self.assertAlmostEqual(x['clock_pin_SS_fF'],843.661008)
        self.assertAlmostEqual(x['clock_pin_FF_fF'],978.127488)
        self.assertEqual((x['SS_setup_ps'],x['FF_hold_ps']),(60,25))
        self.assertEqual(x['new_clock_buffer_area_added_again'],0)

    def test_request_not_reservation_and_scalar_separate(self):
        x=self.x['request']
        self.assertAlmostEqual(x['rectangle_mm2'],.02356992)
        self.assertAlmostEqual(x['unused_geometric_um2'],5.8698)
        self.assertFalse(x['physical_fit'])
        self.assertIsNone(x['actual_reserved_rectangle'])
        self.assertTrue(x['excludes_added_scalar_provider'])
        self.assertAlmostEqual(self.x['scalar_provider_debit']['FF_body_floor_mm2'],.002242404)

    def test_no_link_NTP_core_replication(self):
        x=self.x['replicas']
        self.assertEqual(x['per_selected_source_die'],1)
        self.assertEqual(x['new_enrolled_hardware_instances'],0)
        self.assertIn('not core replicas',x['source_hierarchy'])

    def test_no_unreserved_tracks_or_protection_timing_credit(self):
        x=self.x['channels']
        self.assertEqual(x['signal_union'],636)
        self.assertAlmostEqual(x['unexcluded_width_floor_um'],30.528)
        self.assertIsNone(x['actual_legal_capacity'])
        self.assertFalse(self.x['local_clock']['loaded_SS_FF'])
        self.assertFalse(self.x['admission']['physical_G0'])

    def test_CDC_whole_shadow_state_not_singleclock_claim(self):
        x=self.x['CDC'];self.assertEqual(x['full_state_bits'],2936)
        for e in x['edges']:
            self.assertEqual((e['packet_bits'],e['reverse_packet_bits']),(121,56))
            self.assertEqual((e['DEPTH'],e['HOLD']),(4,2))
            self.assertFalse(e['realized_in_parent'])
            self.assertEqual(e['extra_separate_TOKX_FIFO'],0)
        self.assertFalse(x['phase_exceptions'])

    def test_tail_not_runtimek1_or_leaf_II(self):
        self.assertEqual(self.x['actual_source']['full_selector_tail_edges_after_last'],1026)
        self.assertEqual(self.x['actual_source']['full_selector_busy_edges_after_last'],1537)
        self.assertEqual(self.x['latency']['added_min_serial_edges'],2)
        self.assertIsNone(self.x['latency']['whole_MTP_or_AR_gain'])

    def test_model_exact(self):
        self.assertEqual(self.x,json.loads((m.BASE/'model.json').read_text()))

if __name__=='__main__': unittest.main()

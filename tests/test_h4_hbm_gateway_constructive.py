import copy
import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PATH=Path(__file__).resolve().parents[1]/'tools/h4_hbm_gateway_constructive.py'
spec=importlib.util.spec_from_file_location('constructor',PATH)
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class ConstructiveService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=M.build();cls.sources=M.sources()
        cls.overlay=json.loads(gzip.decompress(cls.sources['results/uarch/h4_c0_group_operand_tiles_20261002/r2/operand_span_overlay.json.gz']))
        cls.selected=json.loads(gzip.decompress(cls.sources['results/uarch/h4_hbm_selected_intervals_20261002/DS_selected_r1/selected_calls.json.gz']))

    def test_all_source_distributed_cuts_and_selected_die_fit(self):
        for name,d in self.model['models'].items():
            with self.subTest(name=name):
                self.assertEqual(d['SMs'],32)
                self.assertEqual(len(d['distributed_gateway_and_bank_cuts']),6688)
                self.assertTrue(d['source_geometry_fit'])
                self.assertTrue(all(c['margin_tracks']>=0 for c in d['distributed_gateway_and_bank_cuts']))
                self.assertEqual(len(d['L2_controller_slots']),4)
                self.assertTrue(all(not s['macro_halo_conflicts'] for s in d['L2_controller_slots']))
                self.assertEqual(d['selected_controller_width_um'],1024)

    def test_actual_service_macro_clock_pins_and_DS_frames(self):
        for name,d in self.model['models'].items():
            for c in d['clock_source_allocations']:
                endpoints=c['macro_clock_endpoints']
                self.assertEqual(len(endpoints),138 if name=='DeepSeek' else 130)
                self.assertEqual(len({e['macro'] for e in endpoints}),len(endpoints))
                self.assertTrue(all(e['clock_pin_layer']=='M4' for e in endpoints))
                self.assertEqual(c['max_fanout'],24)
                self.assertTrue(c['area_fit'])
                self.assertGreater(c['incremental_buffer_footprint_um2'],0)
                self.assertTrue(c['SS_slew_and_clock_pin_cap_bound']['SS_clock_slew_screen_pass'])
                self.assertGreater(c['actual_parent_FF_clock_receivers']['clock_receiver_count'],0)
                self.assertTrue(all(r['max_segment_um']<=8 for r in c['buffered_source_routes']))
                self.assertTrue(c['macro_driver_geometry_fit'])
                self.assertTrue(all(not e['clock_driver_macro_halo_conflict'] for e in endpoints))

    def test_header_includes_actual_lease_and_reference(self):
        self.assertEqual(self.model['request_fields']['lease'],64)
        self.assertEqual(self.model['request_fields']['provider_reference'],32)
        self.assertEqual(self.model['L2_endpoint_composed_tracks'],11072)
        for d in self.model['models'].values():
            s=d['L2_controller_slots'][0]
            self.assertEqual(s['cut']['signal_capacity_tracks'],12919)
            self.assertGreater(s['footprint_um2'],31013.42)

    def test_PG_clock_via_exclusions_never_credit_more_than_old50pct(self):
        for d in self.model['models'].values():
            for c in d['distributed_gateway_and_bank_cuts']:
                for r in c['layers'].values():
                    self.assertLessEqual(r['signal_tracks'],r['old50pct_signal_tracks'])
                    self.assertEqual(r['signal_tracks']+r['PG_via_clock_extra_excluded_signal_tracks'],r['old50pct_signal_tracks'])
                    self.assertGreaterEqual(r['signal_tracks'],0)

    def test_clock_PG_masks_union_no_double_subtraction(self):
        old=dict(axis='X',coordinate_um=0,span_um=[0,10],demand_tracks=1,
                 layers={'M7':dict(origin_DBU=16,pitch_DBU=64)})
        a=M.constructive_cut(old,anchor=0,clock_x=[5])
        b=M.constructive_cut(old,anchor=0,clock_x=[5,5,5])
        self.assertEqual(a['signal_capacity_tracks'],b['signal_capacity_tracks'])

    def test_source_group_input_output_spans_not_runtime_wait_proof(self):
        s=self.model['source_group_span_join']
        self.assertEqual(s['source_span_bound_calls'],3840)
        self.assertEqual(s['remaining_calls_without_this_span_plan'],189476)
        self.assertEqual(s['planned_shared64_transactions'],35389440)
        self.assertEqual(s['production_calls_with_actual_interval_upper_bounds'],0)
        self.assertIsNone(s['actual_backend_consumer_reverse_upper_bounds'])
        self.assertFalse(s['whole_operator_interval_composition_verified'])

    def test_gap_overlap_flatten_and_versions_reject(self):
        for change in ('gap','flatten','version','output'):
            overlay=copy.deepcopy(self.overlay)
            tile=overlay[0]['tiles'][0]
            if change=='gap': overlay[0]['tiles'].pop()
            elif change=='flatten': tile['source_spans'][0]['LOAD_flat_word_first']=128
            elif change=='version': tile['source_spans'][0]['source_version']='stale'
            elif change=='output': tile['destination_version']='stale'
            if change!='gap':
                tile['C0_tile_template_id']=M.sha(M.canonical({k:v for k,v in tile.items() if k!='C0_tile_template_id'}))
            with self.subTest(change=change),self.assertRaises(ValueError):
                M.group_span_join(overlay,self.selected)

    def test_missing_call_and_stale_parent_reject(self):
        selected=copy.deepcopy(self.selected)
        selected['calls']=[c for c in selected['calls'] if not(c['PC']==10 and c['rank']==95)]
        with self.assertRaises(ValueError):M.group_span_join(self.overlay,selected)

    def test_no_circular_RTL_CTS_prebuild_gate_or_automatic_delta(self):
        self.assertTrue(self.model['current_installed_endpoint_not_a_G0_prerequisite'])
        self.assertTrue(self.model['installed_CTS_not_a_G0_prerequisite'])
        self.assertFalse(self.model['engine_build_allowed'])
        self.assertFalse(self.model['automatic_latency_delta'])
        self.assertFalse(self.model['hardware_admitted'])
        self.assertEqual(self.model['SS_setup_uncertainty_ps'],60)
        self.assertEqual(self.model['FF_hold_uncertainty_ps'],25)

    def test_SS_clock_bounds_and_actual_via_geometry(self):
        c=self.model['SS_clock_source_bounds']
        self.assertEqual(len(c['actual_source_FF_CLK_capacitance_ff']),2)
        self.assertTrue(c['SS_clock_slew_screen_pass'])
        self.assertTrue(c['via_single_contact_fits_reserved_envelope'])
        self.assertEqual(c['default_via_metal_envelope_um'],[.054,.054])
        self.assertFalse(c['FF_hold_admission'])
        self.assertIsNone(c['actual_CTS_skew'])
        self.assertTrue(c['conditional_on_constructor_branch_lengths_and_input_slew'])

    def test_additive_wrapper_pin_and_explicit_external_ownership_gap(self):
        r=self.model['additive_source_wrapper']
        self.assertEqual(M.sha((M.ROOT/r['path']).read_bytes()),r['sha256'])
        self.assertEqual(r['SM_instances'],32)
        self.assertTrue(r['external_source_owner_grant_required'])
        self.assertFalse(r['full_provider_ownership_implemented'])
        self.assertFalse(r['matrix_and_L2_endpoint_connected'])

    @unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'),'Icarus unavailable')
    def test_real32SM_storage_connectivity_without_arithmetic_oracle(self):
        names=['rtl/test/tb_h4_hbm_rf_shared_context.sv',
               'rtl/gpu/ot_gpu_hbm_rf_shared_context.sv',
               'rtl/gpu/ot_gpu_full_sm_service.sv','rtl/gpu/ot_gpu_rf_service.sv',
               'rtl/gpu/ot_gpu_scratch_service.sv','rtl/test/full_sm_service/sram_models.sv']
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'storage.vvp'
            subprocess.run(['iverilog','-g2012','-s','tb_h4_hbm_rf_shared_context','-o',str(out)]+names,
                           cwd=M.ROOT,check=True,capture_output=True,text=True)
            result=subprocess.run(['vvp',str(out)],cwd=M.ROOT,check=True,capture_output=True,text=True)
            self.assertIn('PASS_32SM_SOURCE_RF_SHARED_STORAGE_CONNECTIVITY_ONLY',result.stdout)


if __name__=='__main__':unittest.main()

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_finite_source_context as M

class FiniteContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=M.build();cls.records,_=M.inputs()
    def test_exact_reproduction(self):
        self.assertEqual(self.model,json.loads((M.BASE/'model_r3.json').read_bytes()))
    def test_geometry_and_component_capacity(self):
        m=self.model;p=m['placement']
        self.assertEqual(m['frozen_selector_state_bits'],698354)
        self.assertEqual(m['frozen_selector_slot_DBU'],[1000000,8953200,3125440,9745920])
        self.assertTrue(p['component_area_sum_exact']);self.assertTrue(p['component_capacity_pass'])
        self.assertAlmostEqual(sum(p['component_cell_area_um2'].values()),841209.80868)
        boxes=list(p['regions'].values())
        for i,a in enumerate(boxes):
            for b in boxes[i+1:]:
                self.assertTrue(a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])
    def test_real_site_and_prior_refusal_preserved(self):
        self.assertEqual(self.model['placement']['site_width_DBU'],54)
        prior=json.loads((M.BASE/'model_r2.json').read_bytes())
        self.assertFalse(prior['placement']['component_capacity_pass'])
        p=prior['placement'];key='hist_suffix_choice_control'
        self.assertAlmostEqual(p['component_cell_area_um2'][key]-p['region_cell_capacity_um2_50pct'][key],50.78214,places=4)
    def test_all_sort_levels_independent_enumeration(self):
        levels=M.sort_crossings()['stages'];self.assertEqual(len(levels),21)
        x=y=0
        for k in [2,4,8,16,32,64]:
            for j in [2**p for p in range(k.bit_length()-2,-1,-1)]:
                for lane in range(64):
                    peer=lane^j
                    if peer>lane:
                        x+=78*int((lane//8//4)!=(peer//8//4))
                        y+=78*int((lane%8//4)!=(peer%8//4))
        self.assertEqual((x,y),(2496,9984))
        self.assertEqual(sum(l['column_midcut_tracks'] for l in levels),x)
        self.assertEqual(sum(l['row_midcut_tracks'] for l in levels),y)
    def test_wire_screens_are_not_closure(self):
        m=self.model
        self.assertEqual(m['external_tracks']['signal_tracks_after_50pct_reserve']-m['external_signal_demand'],32)
        self.assertFalse(m['internal_tracks']['all_sort_select_prefix_clock_reset_vias_allocated'])
        self.assertFalse(m['G0']['RTL_admitted']);self.assertFalse(m['G0']['PR_admitted'])
        self.assertIsNone(m['transport_model']['actual_transport_station_placement'])
    def test_native_anchor_mutants_refused(self):
        changes=[('rtl/chip/ot_w15_coll_dma.sv','if (tk_done) begin busy <= 0;','if (tk_ov) begin busy <= 0;'),
                 ('rtl/chip/ot_w15_coll_dma.sv',"? tr_ready : 1'b1;","? tr_ready : vm_ready4;"),
                 ('rtl/chip/ckvsel/ot_chip_v41x_die.sv',".vm_ready4(1'b1)",".vm_ready4(1'b0)"),
                 ('rtl/chip/ckvsel/ot_chip_v41x_die.sv','VWA = VM_AW - 4;','VWA = VM_AW - 3;')]
        for path,old,new in changes:
            with self.subTest(path=path,old=old):
                records=dict(self.records);self.assertIn(old.encode(),records[path])
                records[path]=records[path].replace(old.encode(),new.encode())
                with self.assertRaisesRegex(ValueError,'anchor absent'):M.source_contract(records)
    def test_widths_and_added_registers(self):
        t=self.model['transport_model'];d=t['additional_delay_edges']
        self.assertEqual(t['pipeline_width_bits'],dict(input=2122,selector_return=2088,formed_VM_write=2112))
        self.assertEqual((t['minimum_wireonly_launch_segments'],t['minimum_wireonly_return_segments'],t['conditional_direct_rectangle_sink_segments']),(19,19,6))
        self.assertEqual(d,dict(input=18,selector_return=18,formed_VM_write=5,retirement_delay=5))
        self.assertEqual(t['additional_pipeline_bits'],2122*18+2088*18+2112*5+5)
        self.assertEqual(t['additional_pipeline_bits'],86345)
        self.assertEqual(t['additional_cycles_per_call_if_this_chain_admitted'],41)
    def test_constant_delay_preserves_order_requires_retirement_alignment(self):
        # Event algebra control, not an RTL waveform or universal native delay.
        # Source formed writes carry their addresses: each payload is immutable.
        writes=[(n,100+n,[n]*16) for n in range(4)]
        delayed=[(cycle+5,addr,payload) for cycle,addr,payload in writes]
        self.assertEqual([(a,p) for _,a,p in writes],[(a,p) for _,a,p in delayed])
        native_release=max(c for c,_,_ in writes)+1
        self.assertLess(native_release,max(c for c,_,_ in delayed))
        self.assertGreater(native_release+5,max(c for c,_,_ in delayed))
        self.assertFalse(self.model['native_contract']['retiming_data_alone_legal'])
        self.assertFalse(self.model['native_contract']['new_ACK_wire'])
    def test_current_area_replacement_charged_once(self):
        a=self.model['area_join']
        self.assertTrue(a['selector_replacement_already_charged_once'])
        self.assertAlmostEqual(a['no_containment_credit_subtotal_screen_mm2'],a['current_Maxwell_screen_mm2']+2.6571105216+0.050356404)
    def test_archive_corruption_refuses_before_model(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td);(target/'source_manifest.json').write_bytes((M.BASE/'source_manifest.json').read_bytes()+b' ')
            with mock.patch.object(M,'BASE',target):
                with self.assertRaisesRegex(ValueError,'manifest changed'):M.inputs()
    def test_no_git_dependency_for_model_origins(self):
        with mock.patch.object(M.A.SourceArchive,'commit_available',side_effect=AssertionError('no historical git probe')):
            self.assertEqual(M.build(),self.model)
    def test_no_jobs_or_credit(self):
        self.assertEqual(self.model['jobs_launched'],0);self.assertEqual(self.model['new_PVE2_PVE3_jobs'],0)
        self.assertFalse(self.model['optional_variant_sweep'])
        self.assertTrue(self.model['transport_model']['no_current_token_latency_or_MTP_credit'])

if __name__=='__main__':unittest.main()

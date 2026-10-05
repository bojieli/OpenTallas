"""Pin, opcode, replication and geometry guards; no hardware tests."""
from collections import Counter
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import hbm_tc_nested_dot_delta as M

OUT=M.ROOT/'results/uarch/hbm_tc_nested_dot_delta_20261001_r2'


class NestedDotDelta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.summary,cls.events=M.build()

    def test_index_events_keep_RF_and_zero_TC_delta(self):
        s=self.summary['index_phase_join'];self.assertEqual(s['source_events'],20492)
        self.assertEqual(len(s['phases']),50);self.assertEqual(len(s['node_bindings']),8)
        self.assertEqual(len(self.events['index_phase_events']),20492)
        self.assertTrue(all(e['TC_successor_delta_cycles']==0 for e in self.events['index_phase_events']))
        for branch in ['finite','exceptional']:
            phases=[p for p in s['phases'] if p['branch']==branch]
            cost=s['branch_resource_totals'][branch]
            self.assertEqual(sum(p['RF_read_bits'] for p in phases),cost['RF_read_bits'])
            self.assertEqual(sum(p['RF_logical_write_bits'] for p in phases),cost['RF_write_bits'])
            self.assertEqual(sum(p['shared_warp_instructions'] for p in phases),cost['shared_warp_instructions'])
        self.assertFalse(s['finite_and_exceptional_summed'])

    def test_scalar_BF16_or_product_does_not_become_TC(self):
        for op in ['BF16','BF16_WIDEN','FMUL','FADD','dots_q4','SIMD_QK','SIMD_PV']:
            self.assertEqual(M.tc_delta(op),0)
        self.assertEqual(M.tc_delta(M.TC_OPCODE),1)
        with self.assertRaises(ValueError):M.tc_delta('MMA_GENERIC_UNBOUND')

    def test_nested_calls_and_shape_latency(self):
        calls=self.summary['nested_compressor_projection_events']
        self.assertEqual([e['pc'] for e in calls],[121,449,782,1110])
        self.assertEqual([e['participants'] for e in calls],[[63],[63],[63],[31]])
        for e in calls:
            self.assertEqual(e['matrix_shape'],[4096,512])
            self.assertEqual(e['groups'],1);self.assertEqual(e['call_count'],1)
            self.assertEqual(e['parent_SM_drain_from_last_issue_cycles_structural'],60)
            self.assertEqual(e['new_parent_SM_drain_cycles_structural'],61)
            self.assertEqual(e['issue_plus_drain_cycles_structural'],1084)
        matrices=self.summary['explicit_BF16_matrix_events']
        self.assertEqual(len(matrices),93)
        self.assertEqual({e['shape_specific_parent_drain_cycles_structural'] for e in matrices},{60,88})
        self.assertEqual(self.summary['composition_delta']['proposal_TC_total_nodes'],97)
        self.assertEqual(Counter(e['event_id'].split('.')[1] for e in self.summary['ordinary_SIMD_nested_events']),{'attention':80,'hc_mix_projection':80,'engram_norm_similarity':2})

    def test_index_rank_and_SM_tail_conservation(self):
        for node in self.summary['index_phase_join']['node_bindings']:
            self.assertEqual(sum(r['keys'] for r in node['ranks']),node['global_keys'])
            for rank in node['ranks']:
                self.assertEqual(sum(rank['local2_calls_by_SM'])*2,rank['keys'])
                self.assertEqual(rank['query_template_calls_per_SM'],1)

    def test_geometry_rejects_false_local_fit(self):
        geo=self.summary['directional_geometry']
        self.assertEqual(geo['v41']['LEFs']['v_tc']['size_um'],[180,180])
        self.assertGreater(len(geo['v41']['grid_LEF_overlap_pairs']),0)
        self.assertLess(min(geo['v41']['raw_horizontal_column_gaps_um']),0)
        self.assertLess(geo['qwen']['Qwen_halo_free_gap_um'],0)
        self.assertEqual(geo['v41']['retained_die_DEF_vertical_SM_gaps_um'],[293.76])
        self.assertEqual(geo['v41']['required_provider'],'W13_CONTEXT_TC_LANE_AND_SM_CHANNEL_GEOMETRY')
        self.assertFalse(self.summary['no_admission']['adoption'])

    def test_rejects_tampered_phase_artifact(self):
        original=M.subprocess.check_output
        def show(args,**kw):
            b=original(args,**kw)
            if args[-1]==M.PHASE_REV+':'+M.PHASE_PATH:return b[:-1]+bytes([b[-1]^1])
            return b
        with patch.object(M.subprocess,'check_output',show):
            with self.assertRaisesRegex(ValueError,'phase pin mismatch'):M.build()

    def test_summary_reproduces(self):
        stored=json.loads((OUT/'summary.json').read_text());stored.pop('event_artifact_sha256')
        self.assertEqual(stored,self.summary)


if __name__=='__main__':unittest.main()

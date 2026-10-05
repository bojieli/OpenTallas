from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_blas_model as M
class ExpandedModel(unittest.TestCase):
    def test_full64_capacity_rejected_and_unknown_costs_preserved(self):
        model=M.build()
        self.assertFalse(model['eager_single_SM']['capacity_fit'])
        self.assertGreater(model['eager_single_SM']['peak_live_payload_bytes'],65536)
        self.assertIn('AND',model['unpriced_opcode_counts'])
        self.assertIn('BEQ',model['unpriced_opcode_counts'])
        self.assertIsNone(model['whole_token_cycles'])
        self.assertFalse(model['hardware_build_authorized'])
        self.assertFalse(model['partition_proposal']['floorplan_and_schedule_admission'])
        self.assertEqual(model['scale_handoff_bridge']['shared_bytes'],35328)
        self.assertEqual(model['scale_handoff_bridge']['warp_issues'],524)
        parts=model['source_stage_traffic_decomposition']
        self.assertEqual(sum(x['shared_bytes'] for x in parts.values()),3792896)
        self.assertEqual(sum(x['warp_issues'] for x in parts.values()),37568)
        self.assertEqual(len(model['source_kernel_phase_bindings']),36)
    def test_layout_allocation_alignment_and_distinct_regions(self):
        for count in [1,2,32,64]:
            regions,total=M.layout(count);previous=0
            for region in regions.values():
                self.assertEqual(region['base']%256,0)
                self.assertGreaterEqual(region['base'],previous)
                self.assertLessEqual(region['end'],total)
                previous=region['end']
        self.assertGreater(M.layout(64)[1],65536)
        self.assertLess(M.layout(2)[1],65536)
    def test_actual_source_operand_address_and_bank_contract(self):
        regions,_=M.layout(64);lanes=list(range(32))
        for block in range(4):
            for warp in range(32):
                for stage in ['q_sanitize','q_sanitize_store']:
                    a=M.addresses(regions,stage,'input',warp,lanes,block)
                    self.assertEqual(len({(x//4)%32 for x in a}),32)
            for term in range(32):
                for warp in range(2):
                    a=M.addresses(regions,'k_decode',f'v{term}',warp,lanes,block)
                    self.assertEqual(len({(x//4)%32 for x in a}),32)
                for warp in range(64):
                    q=M.addresses(regions,'exception_block',f'q{term}',warp,lanes,block)
                    k=M.addresses(regions,'exception_block',f'k{term}',warp,lanes,block)
                    self.assertEqual(len(set(k)),1)
                    self.assertEqual(len({(x//4)%32 for x in q}),32)
                    self.assertTrue(all(regions['query']['base']<=x<regions['query']['end'] for x in q))
                    self.assertTrue(all(regions['keys']['base']<=x<regions['keys']['end'] for x in k))
        with self.assertRaises(ValueError):M.addresses(regions,'invented','v0',0,lanes)
    def test_partition_replication_not_free_divide_of_traffic(self):
        m=M.build();p=m['partition_proposal']
        self.assertEqual(p['replicated_query_bytes_per_die'],540672)
        self.assertEqual(p['query_refill_extra_shared_copy_bytes_per_tile'],1047552)
        self.assertEqual(p['query_scale_and_unit_compute_replica_count'],32)
        self.assertIsNone(p['whole_phase_cycles'])
        self.assertEqual(p['regions_per_SM']['k_sanitized']['bytes'],4224)
        self.assertEqual(p['regions_per_SM']['k_units']['bytes'],4224)
        self.assertEqual(p['key_decoder_padding_rows_per_SM'],30)
        self.assertEqual(m['HBM_ingress']['safe_max_sectors_per_command'],16)

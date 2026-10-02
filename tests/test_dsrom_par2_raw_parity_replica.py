import importlib.util
import unittest
import ast
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/dsrom_par2_raw_parity_replica.py'
S=importlib.util.spec_from_file_location('parity',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)

class ReplicaDemand(unittest.TestCase):
    def test_shared_word_reuse(self):
        r=dict(compiled_NP=4096,format='fp4',ecc_bit_base=0,
            plans=[[0,2048,0,1,128,0,1],[0,2049,0,1,128,0,1]])
        d=M.demand(r,dict(bits=1000))
        self.assertEqual(d['requested_remote_parity_bits'],32)
        self.assertEqual(d['unique_raw256_reads'],1)
        self.assertEqual(d['simultaneous_run_start_bank_conflict_lower_bound'],1)
    def test_same_leaf_distinct_rows_conflict(self):
        r=dict(compiled_NP=4096,format='fp4',ecc_bit_base=0,
            plans=[[0,2048,0,1,128,0,32],[0,2049,0,1,128,0,32]])
        d=M.demand(r,dict(bits=1024))
        self.assertEqual(d['unique_raw256_reads'],4)
        self.assertEqual(d['prefetch_single_read_port_per_leaf_cycles'],2)
        self.assertEqual(d['simultaneous_run_start_bank_conflict_lower_bound'],2)
    def test_bank_boundary_physical4096(self):
        spans=M.leaf_intervals(8191*256,512)
        self.assertEqual(spans,[((0,0,1),(4095,4095)),((0,1,0),(0,0))])
        self.assertEqual(M.leaf_intervals(16384*256,256),[((1,0,0),(0,0))])
    def test_interval_union_nested(self):
        self.assertEqual(M.union_count([(1,3),(2,2),(3,5),(8,8)]),6)
    def test_capacity_refusal(self):
        r=dict(compiled_NP=4096,format='fp4',ecc_bit_base=100,
            plans=[[0,2048,0,1,128,0,1]])
        with self.assertRaises(ValueError):M.demand(r,dict(bits=110))
    def test_positive_service_required(self):
        for i in range(7):
            a=[1]*7;a[i]=0
            with self.assertRaises(ValueError):M.selected_cost(dict(prefetch_single_read_port_per_leaf_cycles=2,unique_raw256_reads=3),*a)
    def test_global_grant_bottleneck(self):
        d=dict(prefetch_single_read_port_per_leaf_cycles=2,unique_raw256_reads=20)
        slow=M.selected_cost(d,1,2,3,4,5,1,9)
        fast=M.selected_cost(d,1,2,3,4,5,20,9)
        self.assertEqual(slow['nonoverlap_positive_cost_cycles'],33)
        self.assertEqual(fast['nonoverlap_positive_cost_cycles'],15)
        self.assertGreater(slow['nonoverlap_positive_cost_cycles'],fast['nonoverlap_positive_cost_cycles'])
    def test_credit_shortfall_refused(self):
        with self.assertRaises(ValueError):
            M.selected_cost(dict(prefetch_single_read_port_per_leaf_cycles=2,unique_raw256_reads=2),1,2,3,4,5,4,1)
    def test_canonical_export_address_identity(self):
        tree=ast.parse((M.OUT/'inputs/cfg_export_f607.py').read_text())
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='sidecar_address')
        ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'frozen-sidecar','exec'),ns)
        provider=dict(kind='ECC_FP4_SIDECAR',bits=432013312,stage=1,pairs=list(range(103)))
        for w in (0,1,2,8191,8192,8193,16383,16384,16385,103*16384-1):
            a=ns['sidecar_address'](provider,w*256)
            [(bank,span)]=M.leaf_intervals(w*256,16)
            self.assertEqual(bank,(a['pair'],a['mb'],a['parity']))
            self.assertEqual(span,(a['physical_row'],a['physical_row']))
    def test_complete_model_preserves_credits_and_charge(self):
        d=M.build()
        self.assertEqual(d['full_resident_census']['remote_bits'],8178892800)
        self.assertEqual(d['full_resident_census']['local_bits'],9437184000)
        self.assertEqual(d['full_resident_census']['fp4_phases'],46080)
        self.assertTrue(d['full_resident_census']['all_fp4_have_remote'])
        self.assertEqual(d['replica']['raw4096x274_macros_per_shard1_die'],412)
        self.assertAlmostEqual(d['replica']['body_only_mm2'],3.2471222976)
        self.assertFalse(d['replica']['adjacent_q_compute_replication'])
        self.assertEqual(d['replica']['added_compiled_weight_sites'],0)
        self.assertEqual(d['replica']['additive_macro_body_mm2'],0)
        self.assertEqual(d['replica']['extra_macros_all58x4_shard1_dies'],0)
        self.assertEqual(d['replica']['remaining_padding_q_pairs_per_shard1'],281)
        self.assertEqual(d['finite_calendar']['source_root_packet_bits'],108)
        self.assertEqual(d['finite_calendar']['nonbackpressured64root_burst_capture_bits'],6912)
        self.assertEqual(d['finite_calendar']['VM_request_sequence_bits'],10)
        self.assertEqual(d['finite_calendar']['result_identity_bits'],58)
        self.assertFalse(d['build_admitted']);self.assertFalse(d['fulltoken_rate_qualified'])

if __name__=='__main__':unittest.main()

from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_consumer as I
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_packed_index_provider as P
import deepseek_hbm_complete_memory as M

class Consumer(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(253512)
        q=np.stack([C.V.qdq_fp4_e8m0(row) for row in rng.normal(size=(32,128)).astype(np.float32)])
        k=np.stack([C.V.qdq_fp4_e8m0(row) for row in rng.normal(size=(17,128)).astype(np.float32)])
        w=C.G.to_bf16(rng.normal(size=32).astype(np.float32))
        return q,k,w
    def test_finite_ordinary_path_exact_chunk8_source_no_global_mutation(self):
        q,k,w=self.fixture();mode=C.V.ARITH
        ids=np.arange(17,dtype=np.int64)*768+8*95
        got,r=I.route_scores(q,k,w,ids=ids);expected=I.reference_scores(q,k,w,ids)
        self.assertTrue(np.array_equal(got.view(np.uint64),expected.view(np.uint64)))
        self.assertEqual(r['path'],'ordinary INT32/FP32 index score shader')
        self.assertEqual(C.V.ARITH,mode);self.assertIsNone(r['GPU_cycles'])
    def test_actual_source_nonfinite_rows_reach_score_oracle_exact_bits(self):
        q,k,w=self.fixture();state=P.PackedIndexStateArray(np.zeros((17,128),np.float32),M.PersistentMemory(),'ik',0)
        inputs=np.zeros(128,np.float32);inputs[0]=np.array(0x7fc12345,np.uint32).view(np.float32)
        produced=C.ProducerBinding().qdq_fp4_e8m0(inputs)
        state[0]=produced;k[0]=state[0]
        got,r=I.route_scores(q,k,w)
        ref=I.reference_modules();score=C.G.to_bf16(ref.dots_q4(q,k))
        with np.errstate(invalid='ignore'):
            terms=C.G.to_bf16(C.G.mul(np.maximum(score,np.float32(0)),w[:,None]))
            expected=C.G.to_bf16(ref.reduce_rows(terms.T,cls='idx')).astype(np.float64)
        self.assertTrue(np.array_equal(got.view(np.uint64),expected.view(np.uint64)))
        self.assertFalse(r['ordinary_GPU_score_lowered']);self.assertTrue(r['CPU_reference_FP64_macro_used'])
        self.assertFalse(r['reference_injection']);self.assertIsNone(r['GPU_cycles'])
    def test_packed_scale253_Inf_cannot_bypass_nonfinite_consumer_route(self):
        q,k,w=self.fixture()
        produced=C.ProducerBinding().qdq_fp4_e8m0(np.full(128,np.finfo(np.float32).max,np.float32))
        self.assertEqual(produced.format_tag,C.PACKED)
        k[0]=C.decode_payload(produced.format_tag,produced.wire_payload)
        got,r=I.route_scores(q,k,w)
        expected=I.reference_scores(q,k,w)
        self.assertTrue(np.array_equal(got.view(np.uint64),expected.view(np.uint64)))
        self.assertTrue(r['CPU_reference_FP64_macro_used']);self.assertIsNone(r['GPU_cycles'])
    def test_query_and_weight_exceptions_use_actual_source_roundings(self):
        q,k,w=self.fixture();q[3,7]=np.array(0xffc12345,np.uint32).view(np.float32)
        w[7]=np.inf
        got,r=I.route_scores(q,k,w);expected=I.reference_scores(q,k,w)
        self.assertTrue(np.array_equal(got.view(np.uint64),expected.view(np.uint64)))
        self.assertFalse(r['ordinary_GPU_score_lowered']);self.assertGreater(len(r['classification_programs']),0)

if __name__=='__main__':unittest.main()

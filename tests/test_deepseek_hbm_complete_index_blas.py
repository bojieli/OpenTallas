from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_blas as B
import deepseek_hbm_complete_index_codec as C

class PinnedBLAS(unittest.TestCase):
    def test_production_shapes_source_produced_exceptional_blocks(self):
        # Actual QDQ source, not arbitrary replacement decoded operands.
        q=[];keys=[]
        for head in range(32):
            raw=np.ones(128,np.float32);bits=raw.view(np.uint32)
            bits[head%32]=[0x7fc10001,0xffc20002,0x7f800000,0xff800000][head%4]
            if head%3==0:bits[(head+17)%32]=0x7fc30003
            q.append(C.V.qdq_fp4_e8m0(raw))
        for special in [0x7fc40004,0xffc50005,0x7f800000,0xff800000,0x7f7fffff,0,0x80000000]:
            raw=np.ones(128,np.float32);raw.view(np.uint32)[7]=special
            keys.append(C.V.qdq_fp4_e8m0(raw))
        q=np.array(q);keys=np.array(keys)
        produced=[B.block(q[:,:32],key[:32])[0] for key in keys]
        for n in [5456,5464,10920,10928,16384]:
            k=keys[np.arange(n)%len(keys)]
            with np.errstate(invalid='ignore',over='ignore'):
                source=((q[:,:32].astype(np.float64)@k[:,:32].astype(np.float64).T).astype(np.float32)+np.float32(0)).view(np.uint32)
            for j,want in enumerate(produced):
                # Zero state means finite sum delegated to separate exact dyadic recipe.
                active=want!=0
                self.assertTrue(np.all(source[active,j::len(keys)]==want[active,None]))
    def test_finite_fp32_product_overflow_is_not_block_rounding(self):
        raw=np.zeros(128,np.float32);raw[0]=np.float32(2.**100);raw[1]=-raw[0]
        keyraw=np.zeros(128,np.float32);keyraw[:2]=np.float32(2.**100)
        q=C.V.qdq_fp4_e8m0(raw);k=C.V.qdq_fp4_e8m0(keyraw)
        with np.errstate(over='ignore',invalid='ignore'):
            early=np.sum(q[:32]*k[:32],dtype=np.float32)
            exact=np.float32(q[:32].astype(np.float64)@k[:32].astype(np.float64))
        self.assertTrue(np.isnan(early));self.assertEqual(int(exact.view(np.uint32)),0)
        import deepseek_hbm_complete_index as X
        qs=np.tile(q[:32],(32,1));qu,qe,_=X.decode(qs);ku,ke,_=X.decode(k[None,:32])
        got,_=X.block(qu,ku,qe,ke)
        self.assertTrue(np.all(got.view(np.uint32)==0))
    def test_connected_finish_matches_original_fullrank_batch(self):
        import deepseek_hbm_complete_index_consumer as Consumer
        q=[];keys=[]
        for head in range(32):
            raw=np.linspace(-3,5,128,dtype=np.float32)
            if head%4!=3:raw.view(np.uint32)[head%32]=[0x7fc10001,0xff800000,0x7f7fffff][head%4]
            q.append(C.V.qdq_fp4_e8m0(raw))
        for special in [0x7fc40004,0x7f800000,0xff800000,0x7f7fffff,0,0x80000000]:
            raw=np.ones(128,np.float32);raw.view(np.uint32)[7]=special
            keys.append(C.V.qdq_fp4_e8m0(raw))
        q=np.array(q);keys=np.array(keys);weights=np.ones(32,np.float32)
        weights.view(np.uint32)[1]=0xffc60000;weights[3]=-np.inf
        for n in [5456,5464,10920,10928,16384]:
            with np.errstate(invalid='ignore',over='ignore'):
                got,programs=B.source_sized_scores(q,keys,weights,n)
                fullkeys=keys[np.arange(n)%len(keys)]
                expected=Consumer.reference_scores(q,fullkeys,weights,np.arange(n))[:len(keys)]
            self.assertTrue(np.array_equal(got.astype(np.float64).view(np.uint64),expected.view(np.uint64)))
            self.assertGreater(len(programs),0)
        with self.assertRaises(ValueError):B.source_sized_scores(q,keys,weights,1)

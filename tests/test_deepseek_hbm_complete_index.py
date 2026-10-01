from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index as I
import hdc_golden as G
import hdc_golden_v41 as V

class CompleteIndex(unittest.TestCase):
    def test_decoder_all_codes_scale_boundaries_and_not_qdq_rejection(self):
        units=np.array(I.K.UNITS*2,np.float64)
        rows=[]
        for e in [-126,-125,-75,0,124,125]:rows.append(G.to_bf16((units*np.exp2(e-1)).astype(np.float32)))
        rows=np.asarray(rows,np.float32);u,e,m=I.decode(rows)
        recovered=(u.astype(np.float64)*np.exp2(e.astype(np.float64)[:,None]-1)).astype(np.float32)
        self.assertTrue(np.array_equal(recovered.view(np.uint32),np.where(rows==0,np.float32(0),rows).view(np.uint32)))
        with self.assertRaises(ValueError):I.decode(np.full((1,32),np.float32(.6875)))
        self.assertNotIn('FMAX',m.counts)
    def test_block_normal_subnormal_ties_zero_overflow(self):
        r=np.random.default_rng(9632)
        for eq,ek in [(-126,-126),(-74,-74),(-73,-74),(0,0),(124,124)]:
            q=r.choice(I.K.UNITS,(32,32)).astype(np.int32);k=r.choice(I.K.UNITS,(17,32)).astype(np.int32)
            got,m=I.block(q,k,np.full(32,eq,np.int32),np.full(17,ek,np.int32))
            with np.errstate(over='ignore',under='ignore'):
                expected=((q.astype(np.float64)*np.exp2(eq-1))@(k.astype(np.float64)*np.exp2(ek-1)).T).T.astype(np.float32)+np.float32(0)
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)))
            self.assertGreater(m.counts['IMUL'],0)
    def test_full32head128dim_score_order_exact(self):
        r=np.random.default_rng(96128);q=np.stack([V.qdq_fp4_e8m0(row) for row in r.normal(size=(32,128)).astype(np.float32)])
        keys=np.stack([V.qdq_fp4_e8m0(row) for row in r.normal(size=(37,128)).astype(np.float32)])
        weights=G.to_bf16(r.normal(size=32).astype(np.float32))
        got,models=I.scores(q,keys,weights)
        s=G.to_bf16(V.dots_q4(q,keys));terms=G.to_bf16(G.mul(np.maximum(s,np.float32(0)),weights[:,None]));expected=G.to_bf16(V.reduce_rows(terms.T,cls='idx'))
        self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)))
        self.assertTrue(all('FMAX' not in m.counts for m in models))
        with self.assertRaises(ValueError):I.scores(q,np.tile(keys,(28,1)),weights)

if __name__=='__main__':unittest.main()

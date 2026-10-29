"""The actual HGI gate includes scale then canonical signed-root sigmoid."""
import unittest
import numpy as np
import prod_compile as C
import hdc_golden_v41 as G

class ActualEngramGate(unittest.TestCase):
    def test_actual_stage_order_and_adjacent_controls(self):
        rng=np.random.default_rng(17)
        a=(rng.standard_normal(8192)*3).astype(C.F)
        b=(rng.standard_normal(8192)*3).astype(C.F)
        a[:6]=[0.,-0.,1e-8,-1e-8,1.,-1.]; b[:6]=1
        zero=np.zeros_like(a)
        mods=C.RECS['ds_hgi_engram_gate_n6'][4]
        self.assertEqual(mods['cm_imm1'],1013250350)
        dot=G.mul(G.mul(a,b),C.f32(1013250350))
        root=G.sqrt(np.maximum(np.abs(dot),C.f32(0x358637bd)).astype(C.F))
        reference=G.sigmoid(np.where(dot<0,G.neg(root),root).astype(C.F)).view(np.uint32)
        np.testing.assert_array_equal(C.golden(mods,a,b,zero,zero),reference)
        for omitted in ('cm_m2','ci_sfu'):
            changed=dict(mods); changed[omitted]=0
            self.assertGreater(np.count_nonzero(C.golden(changed,a,b,zero,zero)!=reference),0)

if __name__=='__main__': unittest.main()

from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_isa as I
import hdc_golden as G
import hdc_golden_v41 as V

class CompleteISA(unittest.TestCase):
    def test_exact_primitives_and_nonfree_costs(self):
        b=I.WarpBackend();r=np.random.default_rng(1996);a=r.normal(size=77).astype(np.float32);c=r.normal(size=77).astype(np.float32)
        for kind,fn,args in [('FADD',G.add,(a,c)),('FMUL',G.mul,(a,c)),('DIV',V.div,(a,c)),('NEG',G.neg,(a,)),('BF16',G.to_bf16,(a,)),('EXP',G.exp,(a,)),('RSQRT',G.rsqrt,(np.abs(a)+np.float32(.001),)),('MAX',np.maximum,(a,c)),('MIN',np.minimum,(a,c))]:
            got=b.call(kind,*args);expected=fn(*args)
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)),kind)
        s=b.summary();self.assertGreater(s['metrics']['shared_requested_bytes'],0);self.assertNotIn('FMAX',s['warp_opcodes'])
        self.assertLessEqual(s['peak_live_value_regs']+8,32);self.assertIsNone(s['full_graph_cycles'])
    def test_fullshape_norm_and_routed_shared_swiglu_exact(self):
        b=I.WarpBackend();gp,vp,_=I.clone_numeric_modules(b,lambda f,p:None)
        r=np.random.default_rng(805120)
        for n in [512,1280,5120]:
            x=G.to_bf16(r.normal(size=n).astype(np.float32));w=G.to_bf16(r.normal(size=n).astype(np.float32))
            got=vp.rmsnorm_bf16(x,w,np.float32(1e-6));expected=V.rmsnorm_bf16(x,w,np.float32(1e-6))
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)),n)
        g=r.normal(size=77).astype(np.float32)*10;u=r.normal(size=77).astype(np.float32)*10;g[:2]=[0,-0.];u[:2]=[-0.,0.]
        limit=np.float32(7)
        for route in [None,np.float32(.27)]:
            expected=G.mul(V.silu(np.minimum(g,limit).astype(np.float32)),np.clip(u,-limit,limit).astype(np.float32))
            if route is not None:expected=G.mul(route,expected)
            expected=G.to_bf16(expected);got=b.swiglu(g,u,limit,route)
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)))
        self.assertGreater(b.launches['RSQRT'],0);self.assertGreater(b.launches['SWIGLU_ROUTED'],0)
        self.assertNotIn('FMAX',b.opcodes);self.assertLessEqual(b.max_live+8,32)

    def test_cloned_numeric_functions_propagate_primitives_without_mutation(self):
        b=I.WarpBackend();old=V.sigmoid.__globals__['exp'];gp,vp,ve=I.clone_numeric_modules(b,lambda f,p:None)
        x=np.array([-4,-0.,0,4],np.float32)
        for name in ['sigmoid','silu','softplus','log1p_unit']:
            y=np.abs(x)/4 if name=='log1p_unit' else x
            got=getattr(vp,name)(y);expected=getattr(V,name)(y)
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)),name)
        self.assertIs(V.sigmoid.__globals__['exp'],old);self.assertGreater(b.launches['EXP'],0)

if __name__=='__main__':unittest.main()

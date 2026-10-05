import unittest
from unittest.mock import patch
import numpy as np
import hdc_golden_v41 as V
from h4_c0_ds_reference_observers import observe_expert
from h4_c0_ds_comparison_backend import bind_comparison
from h4_c0_ds_reference_observers import ExpertFragments

class ObserverTests(unittest.TestCase):
    def test_off_returns_exact_provider_without_inputs_or_side_effects(self):
        p=object();q,w=bind_comparison(p);self.assertIs(q,p);self.assertIsNone(w)
    def test_original_expert_exact_calls_and_postclip_activation(self):
        m=V.Model.__new__(V.Model);m.limit=np.float32(7)
        m.w={'e.w1.weight':'g','e.w3.weight':'u','e.w2.weight':'d'}
        def linear(w,x):
            return np.array([9,-3],dtype='<f4') if w=='g' else np.array([10,-10],dtype='<f4') if w=='u' else np.asarray(x,dtype='<f4')
        with patch.object(V,'linear_q',linear):
            original=V.Model.expert(m,'e.',np.ones(2,dtype='<f4'),np.float32(.5))
            captured=observe_expert(m,'e.',np.ones(2,dtype='<f4'),np.float32(.5))
            self.assertIs(V.linear_q,linear)
        np.testing.assert_array_equal(captured['d'].view('<u4'),original.view('<u4'))
        np.testing.assert_array_equal(captured['a'].view('<u4'),original.view('<u4'))
        np.testing.assert_array_equal(captured['g'],[9,-3]);np.testing.assert_array_equal(captured['u'],[10,-10])
    def test_exception_restores_original_function(self):
        def fail(*a):raise RuntimeError('preserve')
        m=V.Model.__new__(V.Model);m.w={'e.w1.weight':None}
        with patch.object(V,'linear_q',fail):
            with self.assertRaises(RuntimeError):observe_expert(m,'e.',np.ones(2,dtype='<f4'))
            self.assertIs(V.linear_q,fail)
    def test_cumulative_sparse_rank_ownership_and_gather_alias(self):
        # Source-shape protocol control, never a production execution verdict.
        writes=[dict(version='ea'+str(s),producer_extent=dict(rank_local_slice=[[s*2304+r*24,s*2304+(r+1)*24] for r in range(96)])) for s in (0,1)]
        ops=[dict(pc=s,source_op=dict(layer=0,slot=s),family='swiglu',writes=[writes[s]],rank_bindings=[dict(rank=r) for r in range(96)]) for s in (0,1)]
        ops.append(dict(pc=2,source_op=dict(layer=0,bufs=['ea']),family='all_gather',
            writes=[dict(version='whole',native_result_binding={}),dict(version='slice',native_result_binding=dict(flat_slice=[2304,4608]))],rank_bindings=[dict(rank=0)]))
        c=[dict(a=np.full(2304,s+1,dtype='<f4')) for s in range(7)]
        class Store:
            def __init__(self):self.rows={}
            def append(self,k,a,p):self.rows[k]=a.copy()
        store=Store();ExpertFragments(dict(instructions=ops),0,c,store,{}).emit()
        v=store.rows[(1,'ea1',3,'data')]
        self.assertEqual(np.count_nonzero(v),48)
        np.testing.assert_array_equal(v[72:96],1);np.testing.assert_array_equal(v[2304+72:2304+96],2)
        np.testing.assert_array_equal(store.rows[(2,'slice',0,'data')],2)
if __name__=='__main__':unittest.main()

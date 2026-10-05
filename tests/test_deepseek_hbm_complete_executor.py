from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_executor as E
import deepseek_hbm_complete_program as P
import w19_hbm_tp96_isa as H
import w19_attention_opcode_proof as Oracle

class CompleteExecutor(unittest.TestCase):
    def test_finite_row_initial_read_then_produced_write_no_alias(self):
        a=np.arange(3*128,dtype=np.float32).reshape(3,128);m=E.PersistentMemory();v=E.StateArray(a,m,'ik',2)
        self.assertTrue(np.array_equal(v[[0,2]],a[[0,2]]));self.assertFalse(m.values)
        row=np.full(128,7,np.float32);v[1]=row;self.assertTrue(np.array_equal(v[1],row))
        self.assertTrue(np.array_equal(v[0],np.arange(128,dtype=np.float32)))
        with self.assertRaises(ValueError):v[3]=row
    def test_attention_consumes_current_produced_query_and_rows(self):
        from hdc_golden import to_bf16
        r=np.random.default_rng(661);q=to_bf16(r.normal(size=512).astype(np.float32));rows=to_bf16(r.normal(size=(128,512)).astype(np.float32))
        cs=(np.ones(32,np.float32),np.zeros(32,np.float32));scale=np.float32(512**-.5)
        # Invoke the production companion handler; no golden activation written.
        ex=E.Executor.__new__(E.Executor);ex.m=SimpleNamespace(attn_scale=scale,lw=lambda L,n:np.zeros(64,np.float32))
        ex.cs=lambda L:cs;ex.primitive_counts={};rk=H.Rank(0);rk.win[0]=rows;rk.put('q_own',q)
        ex.f_attend(rk,{'layer':0,'yarn':False})
        expected=Oracle.reference(q,rows,np.float32(0),cs,scale)['final']
        self.assertTrue(np.array_equal(rk.get('o_own').view(np.uint32),expected.view(np.uint32)))
        self.assertGreater(ex.primitive_counts['FADD'],0);self.assertNotIn('FMAX',ex.primitive_counts)
        q2=to_bf16(q*np.float32(-1));rk.put('q_own',q2);ex.f_attend(rk,{'layer':0,'yarn':False})
        self.assertFalse(np.array_equal(rk.get('o_own').view(np.uint32),expected.view(np.uint32)))
    def test_original_backend_globals_not_modified(self):
        self.assertIs(H.Executor.f_index_q.__globals__['V'],H.V)
        self.assertEqual(P.compile_program()['coverage']['operations'],2213)

if __name__=='__main__':unittest.main()

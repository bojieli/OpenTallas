import unittest
import numpy as np
import hdc_golden as G
import w19_norm_opcode_proof as N
import w19_gpu_attention_finish as C
import w19_gpu_compare_lowering as L
from w19_gpu_compare_vm import Machine
from w19_attention_typed_vm import wire_f32


class CompareLowering(unittest.TestCase):
    def test_standard_two_source_shape_and_finite_ports(self):
        p=L.compare('out','a','b',True,'p_')
        self.assertEqual(len(p),19);self.assertLessEqual(max(len(i['src']) for i in p),2)
        b=L.build()
        for pr in b['profiles']:
            for name,p in pr['recipes'].items():
                self.assertFalse(any(i['op'] in ['FMAX','FMIN'] for i in p))
                self.assertLessEqual(pr['calendars'][name]['peak_live_value_registers']+8,32)
        self.assertIsNone(b['full_token_cycles'])

    def test_exact_nan_tie_zero_bits_random_and_special(self):
        r=np.random.default_rng(41)
        a=r.integers(0,1<<32,10000,dtype=np.uint32);b=r.integers(0,1<<32,10000,dtype=np.uint32)
        a[:8]=[0,0x80000000,0x7fc00001,0x7f800001,0xffc00002,0x3f800000,0x7fc12345,0x7f800000]
        b[:8]=[0x80000000,0,0x3f800000,0x7fc12345,0xff800001,0x3f800000,0x7fc54321,0xff800000]
        for maximum,fn in [(True,np.maximum),(False,np.minimum)]:
            p=[C.ins('LOAD','a',source='a'),C.ins('LOAD','b',source='b')]+L.compare('out','a','b',maximum,'cmp_')+[C.ins('STORE32',src=['out'])]
            m=Machine(p,{'a':N.Value('U32',a),'b':N.Value('U32',b)},1,32).run()
            with np.errstate(invalid='ignore'):expected=fn(a.view(np.float32),b.view(np.float32))
            self.assertTrue(np.array_equal(wire_f32(m.stores[-1]).view(np.uint32),expected.view(np.uint32)))
            self.assertEqual(len(m.trace),22)

    def test_lowered_exp_numerical_and_priced_delta(self):
        x=np.array([-100,-87,-40,-0.,0,1,40,88,100],np.float32)
        p=L.lower([C.ins('LOAD','x',source='x')]+C.exp_program()+[C.ins('STORE32',src=['e'])])
        m=Machine(p,{'x':N.f32(x)},1,9).run()
        self.assertTrue(N.equal(wire_f32(m.stores[-1]),G.exp(x)))
        for pr in L.build()['profiles']:
            self.assertGreater(pr['calendars']['probabilities']['cycles'],pr['original_calendar_cycles']['probabilities'])
            self.assertGreater(pr['calendars']['max_global']['cycles'],pr['original_calendar_cycles']['max_global'])

    def test_predicated_tree_keeps_unselected_raw_values(self):
        a=np.arange(32,dtype=np.float32);p=L.lower(C.max_program(5,True))
        m=Machine(p,{'SMpartialmax paddedNEG_INF':N.f32(a)},1,32).run()
        self.assertEqual(m.regs['v'].f32()[0],np.float32(31))
        self.assertEqual(m.regs['v'].f32()[1],np.float32(1))

    def test_connected_lowered_fullshape_no_source_mutation(self):
        from w19_attention_lowered_proof import connected
        import w19_attention_opcode_proof as P
        old=dict(P.connected.__globals__)
        r=np.random.default_rng(42);q=G.to_bf16(r.normal(size=512).astype(np.float32))
        cs=(r.normal(size=32).astype(np.float32),r.normal(size=32).astype(np.float32))
        for n in [128,640]:
            rows=G.to_bf16(r.normal(size=(n,512)).astype(np.float32));args=(q,rows,np.float32(0),cs,np.float32(512**-.5))
            got,m=connected(*args);expected=P.reference(*args)
            for k in got:self.assertTrue(N.equal(np.asarray(got[k],np.float32),np.asarray(expected[k],np.float32)))
            self.assertFalse(any(t['op'] in ['FMAX','FMIN'] for v in m.values() for t in v.trace))
        self.assertIs(P.connected.__globals__['Machine'],old['Machine'])
        self.assertIs(P.connected.__globals__['C'],old['C'])


if __name__=='__main__':unittest.main()

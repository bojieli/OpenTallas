import unittest
import numpy as np
import hdc_golden as G
import hdc_golden_v41 as V
import w19_norm_opcode_proof as N
import w19_gpu_attention_finish as C
from w19_gpu_attention_dots import dot_program
from w19_attention_typed_vm import Machine,collector,dot_memory,gpu_max_min,wire_f32


class TypedAttention(unittest.TestCase):
    def equal(self,a,b):self.assertTrue(N.equal(np.asarray(a,np.float32),np.asarray(b,np.float32)))

    def test_max_min_operand_bits_nan_and_zero(self):
        a=np.array([0,0x80000000,0x7fc00011,0x3f800000,0x7fc00022,0x7f800033],np.uint32).view(np.float32)
        b=np.array([0x80000000,0,0x3f800000,0x7fc00033,0x7fc00044,0x7fc00055],np.uint32).view(np.float32)
        for maximum,ref in [(True,np.maximum),(False,np.minimum)]:
            got=gpu_max_min(a,b,maximum)
            with np.errstate(invalid='ignore'):expected=ref(a,b)
            self.equal(got,expected)
            self.assertEqual(got.view(np.uint32)[0],0x80000000)
            self.assertEqual(got.view(np.uint32)[1],0)
            self.assertEqual(got.view(np.uint32)[2],0x7fc00011)

    def test_exp_published_opcodes_bit_exact(self):
        x=np.array([-100,-87,-80,-20,-1,-0.,0,1,20,80,88,100],np.float32)
        p=[C.ins('LOAD','x',source='x')]+C.exp_program()+[C.ins('STORE32',src=['e'])]
        m=Machine(p,{'x':N.f32(x)},1,12).run()
        self.equal(wire_f32(m.stores[-1]),G.exp(x))
        self.assertEqual(len(m.trace),len(p))

    def test_f2i_integral_range_and_typed_modulo_scale(self):
        p=[C.ins('LOAD','x',source='x'),C.ins('F2I','i',['x']),C.ins('SHL','shift',['i','@U23']),
           C.ins('LOAD','bits',source='bits'),C.ins('IADD','out',['bits','shift'],typed_bit_view=True)]
        m=Machine(p,{'x':N.f32([-126,-1,0,127]),'bits':N.Value('U32',np.array([0x3f800000]*4,np.uint32))},1,4).run()
        want=((np.array([0x3f800000]*4,np.int64)+(np.array([-126,-1,0,127],np.int64)<<23))&0xffffffff).astype(np.uint32)
        self.assertTrue(np.array_equal(m.regs['out'].u32(),want))
        for x in [1.5,128,np.nan,np.inf]:
            with self.assertRaises(ValueError):Machine(p,{'x':N.f32(x),'bits':N.f32(1)},1,1).run()

    def test_chunk8_and_warp32_dot_actual_instructions(self):
        r=np.random.default_rng(13)
        a=G.to_bf16(r.normal(size=(2,32,8)).astype(np.float32));b=G.to_bf16(r.normal(size=a.shape).astype(np.float32))
        m=Machine(dot_program(32),dot_memory(a,b),1,32,dot=True).run()
        expected=V.csum(G.mul(a.reshape(2,256),b.reshape(2,256)))
        self.equal(m.regs['sum'].f32()[...,0],expected)

    def test_subwarp16_does_not_combine_distinct_outputs(self):
        r=np.random.default_rng(14)
        a=G.to_bf16(r.normal(size=(2,32,8)).astype(np.float32));b=G.to_bf16(r.normal(size=a.shape).astype(np.float32))
        m=Machine(dot_program(16),dot_memory(a,b),1,32,dot=True).run()
        expected=V.csum(G.mul(a.reshape(4,128),b.reshape(4,128)))
        self.equal(m.regs['sum'].f32()[...,::16].reshape(-1),expected)

    def test_collector_no_host_sum(self):
        a=np.array([1,-0.,1e10],np.float32);b=np.array([-1,0.,-1e10],np.float32)
        m=collector(a,b);self.equal(wire_f32(m.stores[-1]),G.add(a,b))
        self.assertEqual([t['op'] for t in m.trace],['LOAD','LOAD','FADD','STORE32'])

    def test_inverse_rope_source_pairing_and_rounding(self):
        r=np.random.default_rng(15)
        x=G.to_bf16(r.normal(size=512).astype(np.float32));c=r.normal(size=32).astype(np.float32);s=r.normal(size=32).astype(np.float32)
        mem={'outputBF16dim448+pair*2':N.bf16_memory(x[-64::2]),
             'outputBF16dim449+pair*2':N.bf16_memory(x[-63::2]),'actual position coefficient COS':N.f32(c),
             'actual position coefficient SIN':N.f32(s)}
        m=Machine(C.inverse_rope(),mem,1,8).run()
        reference=V.rope_tail(x,(c,s),inverse=True)
        self.equal(wire_f32(m.stores[0]),reference[-64::2]);self.equal(wire_f32(m.stores[1]),reference[-63::2])

    def test_unbound_load_and_bad_bf16_rejected(self):
        with self.assertRaises(ValueError):Machine([C.ins('LOAD','x',source='missing')],{},1,1).run()
        with self.assertRaises(ValueError):N.bf16_memory(np.array([1.0001],np.float32))

    def test_connected_actual_phase_programs_both_fullshapes(self):
        from w19_attention_opcode_proof import connected,reference
        r=np.random.default_rng(16)
        q=G.to_bf16(r.normal(size=512).astype(np.float32))
        cs=(r.normal(size=32).astype(np.float32),r.normal(size=32).astype(np.float32))
        for n in [128,640]:
            rows=G.to_bf16(r.normal(size=(n,512)).astype(np.float32))
            got,m=connected(q,rows,np.float32(.125),cs,np.float32(512**-.5))
            expected=reference(q,rows,np.float32(.125),cs,np.float32(512**-.5))
            for k in got:self.equal(got[k],expected[k])
            self.assertGreater(sum(len(v.trace) for v in m.values()),100)


if __name__=='__main__':unittest.main()

import copy
import unittest
import numpy as np
import fused_image_lower as F
import isa_rows as IR
from hgi_sim import records as R
from hgi_sim import machine as M
from fused_phase_check import check_fused


def pre():
    return R.Rec('FUSED','HC_PRE_NORM',desc={
        'A':R.MDesc(base=0,n=20480),
        'B':R.MDesc(space='HBM',base=0x400000,n=5120),
        'C':R.MDesc(base=100004,n=4),
        'O':R.MDesc(base=120048,n=5120,fmt='BF16')})


class Lower(unittest.TestCase):
    def test_real_gain_and_aligned_materialization(self):
        r=pre(); out,ledger=F.lower_one(r,None,np.zeros(F.LIMIT,bool))
        self.assertEqual(out[1][0].unit,'DMA')
        self.assertEqual(out[1][0].desc['A'].space,'HBM')
        native=next(rr for rr,rx in out if rr.unit=='FUSED')
        self.assertFalse(check_fused(native,None))
        self.assertEqual(native.desc['B'].space,'VM')
        self.assertEqual(ledger[0]['hbm_load_words'],5120)
        self.assertEqual(out[-1][0].desc['O'].base,r.desc['O'].base)

    def test_post_c_is_a_real_copy(self):
        r=R.Rec('FUSED','HC_POST',desc={
            'A':R.MDesc(base=220048,n=5120), 'B':R.MDesc(base=130096,n=20480),
            'C':R.MDesc(base=280004,n=20), 'O':R.MDesc(base=0,n=20480)})
        out,_=F.lower_one(r,None,np.zeros(F.LIMIT,bool))
        cp=out[2][0]; native=out[3][0]
        self.assertEqual(cp.unit,'SU');self.assertEqual(cp.desc['A'].base,280004)
        self.assertEqual(cp.desc['O'].base,native.desc['C'].base)
        self.assertEqual(cp.desc['A'].n,20);self.assertEqual(native.desc['C'].base%8,0)

    def test_no_capacity_refuses(self):
        with self.assertRaises(ValueError):F.lower_one(pre(),None,np.ones(F.LIMIT,bool))

    def test_model_bypass_bits_and_address_mutant(self):
        rng=np.random.default_rng(91)
        vals=rng.uniform(-1000,1000,64).astype(np.float32)
        h=M.Hbm();die=M.Die(0,h);machine=M.Machine([die])
        die.vm[100:164]=vals.view(np.uint32)
        cp=F.copy_rec(R.MDesc(base=100,n=64),R.MDesc(base=1000,n=64),'copy')
        machine.cur=cp;M.u_su_vop(machine,cp,0)
        np.testing.assert_array_equal(die.vm[1000:1064],vals.view(np.uint32))
        bad=copy.deepcopy(cp);bad.desc['A'].base+=1
        machine.cur=bad;M.u_su_vop(machine,bad,0)
        self.assertTrue(np.any(die.vm[1000:1064]!=vals.view(np.uint32)))

    def test_two_row_payload_lockstep(self):
        r=pre();rx=IR.RowX(n=2,rs={'A':20480,'C':8,'O':5120})
        rng=np.random.default_rng(7);h=M.Hbm();gain=rng.uniform(.5,2,5120).astype(np.float32)
        h.add(r.desc['B'].base,gain.view(np.uint8),'gain')
        die=M.Die(0,h);machine=M.Machine([die]);original=[]
        for row,rr in IR.expand(r,rx):
            a=rng.uniform(-2,2,20480).astype(np.float32)
            c=rng.uniform(-2,2,4).astype(np.float32)
            die.vm[rr.desc['A'].base:rr.desc['A'].base+20480]=a.view(np.uint32)
            die.vm[rr.desc['C'].base:rr.desc['C'].base+4]=c.view(np.uint32)
            original.append((a,c))
        emitted,_=F.lower_one(r,rx,np.zeros(F.LIMIT,bool)); expected=[]
        for rr,xx in emitted:
            machine.cur=rr
            if rr.unit=='SU':M.u_su_vop(machine,rr,0)
            elif rr.unit=='DMA':M.u_dma_load(machine,rr,0)
            else:
                row=rr.slot;a,c=original[row]
                for key,values in [('A',a),('B',gain),('C',c)]:
                    base=rr.desc[key].base
                    np.testing.assert_array_equal(die.vm[base:base+len(values)],values.view(np.uint32))
                values=np.arange(5120,dtype=np.float32)+row
                expected.append(values.view(np.uint32));base=rr.desc['O'].base
                die.vm[base:base+5120]=values.view(np.uint32)
        for row,bits in enumerate(expected):
            base=r.desc['O'].base+row*5120
            np.testing.assert_array_equal(die.vm[base:base+5120],bits)

    def test_batch_payload_and_broadcast_gain(self):
        r=pre();rx=IR.RowX(n=2,rs={'A':20480,'C':8,'O':5120})
        rng=np.random.default_rng(8);h=M.Hbm();gain=rng.uniform(.5,2,5120).astype(np.float32)
        h.add(r.desc['B'].base,gain.view(np.uint8),'gain')
        die=M.Die(0,h);machine=M.Machine([die]);original=[]
        for row,rr in IR.expand(r,rx):
            a=rng.uniform(-2,2,20480).astype(np.float32);c=rng.uniform(-2,2,4).astype(np.float32)
            die.vm[rr.desc['A'].base:rr.desc['A'].base+20480]=a.view(np.uint32)
            die.vm[rr.desc['C'].base:rr.desc['C'].base+4]=c.view(np.uint32)
            original.append((a,c))
        emitted,ledger=F.lower_batched_chunks(r,rx,np.zeros(F.LIMIT,bool));expected={}
        self.assertEqual(sum(rr.unit=='DMA'for rr,xx in emitted),1)
        self.assertEqual(sum((xx.n if xx else 1) for rr,xx in emitted if rr.unit=='FUSED'),2)
        for rec,xx in emitted:
            for row,rr in IR.expand(rec,xx):
                machine.cur=rr
                if rr.unit=='SU':M.u_su_vop(machine,rr,0)
                elif rr.unit=='DMA':M.u_dma_load(machine,rr,0)
                else:
                    a,c=original[row]
                    for key,values in [('A',a),('B',gain),('C',c)]:
                        base=rr.desc[key].base
                        np.testing.assert_array_equal(die.vm[base:base+len(values)],values.view(np.uint32))
                    values=np.arange(5120,dtype=np.float32)+row;expected[row]=values.view(np.uint32)
                    base=rr.desc['O'].base;die.vm[base:base+5120]=values.view(np.uint32)
        for row,bits in expected.items():
            base=r.desc['O'].base+row*5120
            np.testing.assert_array_equal(die.vm[base:base+5120],bits)

    def test_copy_decode_and_phase_mutant(self):
        out,_=F.lower_one(pre(),None,np.zeros(F.LIMIT,bool))
        for r,rx in out:
            raw=IR.encode(r,rx);rr,xx,end=IR.decode_one(raw,0)
            self.assertEqual(end,len(raw));self.assertEqual(IR.encode(rr,xx),raw)
        native=next(rr for rr,rx in out if rr.unit=='FUSED');native.desc['O'].base+=8
        self.assertTrue(check_fused(native,None))

    def test_hidden_attention_plan_extent_from_actual_producer(self):
        producer=R.Rec('IDX','KVUNION',desc={'R':R.MDesc(base=250000,n=128,m=32,stride=128,fmt='U32')})
        att=R.Rec('ATT','QK',desc={'A':R.MDesc(base=60000,n=16)})
        rows=IR.RowX(n=2,rsel=1,rtab=250000)
        recs=[(0,producer,None,b''),(1,pre(),None,b''),(2,att,rows,b'')]
        live=F.live_at_fused(recs)[1]
        self.assertTrue(live[250000:254096].all())
        self.assertFalse(live[254096])
        recs[2][2].rtab+=10000
        with self.assertRaises(ValueError):F.live_at_fused(recs)

    def test_rid_copy_precedes_actual_users(self):
        topk=R.Rec('IDX','TOPK',param=4102,desc={'A':R.MDesc(base=1000,n=384),'O':R.MDesc(base=2000,n=6,fmt='U32')})
        union=R.Rec('IDX','UNION',imm_a=384,imm_b=7,desc={'A':R.MDesc(base=9000,n=6,m=2,stride=8,fmt='U32')})
        idx=R.Rec('SU','VOP',desc={'A':R.MDesc(base=1000,n=1,indexed=1,dyn_mul=1),'I':R.MDesc(base=9001,n=1,fmt='U32')})
        recs=[(n,r,None,IR.encode(r,None))for n,r in enumerate([topk,union,idx])]
        out,fix=F.repair_rid_tables(recs,100000)
        self.assertEqual(out[1][1].unit,'SU')
        self.assertEqual(out[1][1].desc['A'].base,2000)
        self.assertEqual(out[2][1].desc['A'].base,100000)
        self.assertEqual(out[3][1].desc['I'].base,100001)

if __name__=='__main__':unittest.main()

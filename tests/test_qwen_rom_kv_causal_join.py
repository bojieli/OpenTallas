"""Directed causal fixtures only: no trained token or hardware qualification."""
import os
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_persistent_kv_g0 import Owner
from qwen_rom_kv_identity_binding import identity, pack, unpack, reverse_credit
from qwen_rom_kv_production_join import ProducerJoin
from qwen_rom_kv_causal_join import CausalJoin


def event(owner, pc, key, op, generation=1, beat=0, base=None, t=0, write=False, payload=bytes(32), sectors=1):
    base = key[3] if base is None else base
    i = identity(owner, key[2], base if op in ('allocate','retire') else base+beat,
                 generation, 1, 0, pc=pc)
    word = pack(i)
    return dict(event=op, owner=vars(owner), producer_pc=pc, identity=hex(word),
                endpoint=key[0], stack=key[2], physical_tag=3, service_cycle=t,
                sectors=sectors, write=write, payload_hex=payload.hex(), beat=beat,
                sector=base+beat, reverse_wire_hex=hex(reverse_credit(word,3,beat,int(write))))


class CausalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['QWEN_O4_TP']='4'
        os.environ['QWEN_O4_GROUPS']='6144'
        os.environ['HDC_SU_WIDTH']='64'
        import hdc_qwen_fullshape_program_w12 as source
        cls.image=('\n'.join(source.profile(0)['program_hex'])+'\n').encode()

    def producer(self):
        p=ProducerJoin(self.image,Owner(0,3,35,7),0)
        for pc, addresses in p.expected.items():
            p.issue(pc)
            for a in addresses: p.lane_write(pc,a,0x3f800000)
        return p

    def test_unrelated_write_allocation_cannot_join_real_producer(self):
        c=CausalJoin(); p=self.producer(); plan=c.submit(p)
        r=plan['requests'][0]; key=(r['endpoint'],r['die'],r['stack'],r['sector'])
        e=event(p.owner,r['producer_pc'],key,'allocate',write=True,payload=bytes.fromhex(r['payload_hex']))
        wrong=dict(e,payload_hex=bytes(32).hex())
        with self.assertRaisesRegex(ValueError,'producer PC/home/payload'): c.apply(wrong)
        wrong=event(p.owner,r['producer_pc']+1,key,'allocate',write=True,payload=bytes.fromhex(r['payload_hex']))
        with self.assertRaisesRegex(ValueError,'producer PC/home/payload'): c.apply(wrong)
        with self.assertRaisesRegex(ValueError,'drain before reuse'): c.submit(p)
        c.apply(e)
        with self.assertRaises(ValueError): c.apply(e)
        self.assertEqual(c.debts()['planned_write_sectors'],8)

    def test_write_row_requires_backing_reverse_wire_grant_and_retirement(self):
        c=CausalJoin(); p=self.producer(); plan=c.submit(p)
        for n,r in enumerate(plan['requests']):
            key=(r['endpoint'],r['die'],r['stack'],r['sector'])
            def e(op, t):
                return event(p.owner,r['producer_pc'],key,op,generation=n+1,t=t,
                             write=True,payload=bytes.fromhex(r['payload_hex']))
            c.apply(e('allocate',n*8)); c.apply(e('write_command',n*8))
            c.apply(e('backing',(n+1)*8)); c.apply(e('return',(n+1)*8))
            with self.assertRaises(ValueError): c.apply(e('retire',(n+1)*8))
            bad=e('credit',(n+1)*8); bad['reverse_wire_hex']='0x0'
            with self.assertRaisesRegex(ValueError,'wire404'): c.apply(bad)
            for op in ('credit','grant_consumed','retire'): c.apply(e(op,(n+1)*8))
        self.assertEqual(c.debts()['completed_rows'],1)
        self.assertEqual(c.debts()['live_allocations'],0)
        self.assertEqual(len(c.residence.tails[p.owner][1]),1)

    def test_literal_owned_sector_rewrite_burst_and_real_read_state(self):
        c=CausalJoin(); owner=Owner(0,3,35,7)
        base=(1,1,2,100); keys=[base,(1,1,2,101)]
        def data(o,k): return bytes([k[3]])*32
        with self.assertRaisesRegex(ValueError,'actual descriptor'): c.apply(event(owner,67,base,'allocate',sectors=2))
        c.expect_reads(owner,67,keys,data)
        c.apply(event(owner,67,base,'allocate',sectors=2))
        for beat in range(2):
            ret=event(owner,67,base,'return',beat=beat,payload=bytes([100+beat])*32)
            bad=dict(ret,payload_hex=bytes(32).hex())
            with self.assertRaisesRegex(ValueError,'actual declared state'): c.apply(bad)
            if beat:
                wrong=dict(ret,identity=event(owner,67,base,'allocate')['identity'])
                with self.assertRaisesRegex(ValueError,'base\+beat'): c.apply(wrong)
            c.apply(ret)
            a=event(owner,67,base,'acquire',beat=beat); a['reader']=2; c.apply(a)
            with self.assertRaisesRegex(ValueError,'undrained'): c.apply(event(owner,67,base,'credit',beat=beat))
            a['event']='drain'; c.apply(a)
            c.apply(event(owner,67,base,'credit',beat=beat))
            c.apply(event(owner,67,base,'grant_consumed',beat=beat))
        c.apply(event(owner,67,base,'retire'))
        self.assertEqual(c.debts()['pending_read_sectors'],0)

    def test_current_single_data_port_cannot_accept_heterogeneous_write_burst(self):
        c=CausalJoin(); p=self.producer(); plan=c.submit(p); r=plan['requests'][0]
        key=(r['endpoint'],r['die'],r['stack'],r['sector'])
        e=event(p.owner,r['producer_pc'],key,'allocate',write=True,sectors=2,payload=bytes([56])*64)
        with self.assertRaisesRegex(ValueError,'data256 requires LEN1'): c.apply(e)
        self.assertEqual(c.debts()['live_allocations'],0)


if __name__=='__main__': unittest.main()

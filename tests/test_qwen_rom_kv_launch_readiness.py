"""Directed source-boundary fixtures; no actual owned launch qualification."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_kv_launch_readiness import (FIELDS, instruction, AcceptedInstruction,
                                         fifo_released_empty, startup_ready, kv_admission, StartupBarrier)
from qwen_rom_kv_causal_join import CausalJoin
from uarch_model_qwen_kv_rate_risk import FinitePrefetchReplay


def fields():
    return {n:(128 if n=='nout' else 6 if n=='split' else 0) for n,_ in FIELDS}


def fifo():
    return dict(wrsync=3,rrsync=3,won=1,ron=1,ronw2=1,wonr2=1,
                wb=0,rb=0,wg=0,rg=0,rgw2=0,wgr2=0)


def snapshot():
    states=('ingress','wr_live','wr_backed','wr_mapped','grant_valid','live_tags',
            'owner_state','owner_held','route_held')
    return dict(epoch=7,domains={d:dict(epoch=7,released=True,acknowledged=True)
             for d in ('stream','serial','service')},
        stacks=[dict(stack=s,enabled=1,fault=0,qcount=[0]*32,rcount=[0]*32,
                     **{n:0 for n in states}) for s in range(4)],
        bridges=[fifo(),fifo()],serial=dict(active=0,inflight=0,fault=0),
        kv=dict(used=0,fl_v=0,boot_busy=0,boot_any_v=0,desc_pending=0,kvd_v=0,
                fault=0,adapter_idle=1,tail_state_bound=1))


def edge(n,go=0,go_q=0,ready=1,ib=None):
    return dict(edge=n,rst_n=1,request_go=go,ib_go=go & ready,parent_domains_ready=ready,go_q=go_q,
                active=0,pend=0,ib=ib or instruction(fields()),ib_q=instruction(fields()),
                xl='0'*128,xl_q='0'*128,owner='fixture-owner',pc=67)


class LaunchTests(unittest.TestCase):
    def held(self):
        c=AcceptedInstruction();c.offer('fixture-owner',67,fields(),'0'*128)
        return c

    def test_all379bits_roundtrip_source_order_no_defaults(self):
        f={n:(1<<w)-1 for n,w in FIELDS}
        self.assertEqual(instruction(f),'1'*379)
        f['nout']=1; f['mbase']=2
        w=instruction(f);self.assertEqual(w[:18],format(1,'018b'))
        self.assertEqual(w[-24:],format(2,'024b'))
        del f['rmax']
        with self.assertRaisesRegex(ValueError,'all24'):instruction(f)

    def test_waiting_request_then_exact_nextedge_accept(self):
        c=self.held();c.edge(edge(0,go=1,ready=0));self.assertEqual(c.accepted,0)
        c.edge(edge(1,go=1));self.assertEqual(c.accepted,0)
        c.edge(edge(2,go_q=1));self.assertEqual(c.accepted,1)
        self.assertIsNone(c.request)

    def test_unknown_high_and_low_bits_refused(self):
        for bit in (0,378):
            c=self.held();e=edge(0,go=1)
            e['ib']=e['ib'][:bit]+'z'+e['ib'][bit+1:]
            with self.assertRaisesRegex(ValueError,'X/Z'):c.edge(e)

    def test_parent_must_hold_payload_through_registered_accept(self):
        c=self.held();c.edge(edge(0,go=1));e=edge(1,go_q=1)
        e['ib']=e['ib'][:-1]+'1'
        with self.assertRaisesRegex(ValueError,'retain exact'):c.edge(e)

    def test_ireg_mismatch_and_pending_engine_refused(self):
        for kind in ('ib_q','pend'):
            c=self.held();c.edge(edge(0,go=1));e=edge(1,go_q=1)
            e[kind]='0'*379 if kind=='ib_q' else 1
            with self.assertRaises(ValueError):c.edge(e)

    def test_queued_go_cannot_outlive_readiness_epoch(self):
        c=self.held();c.edge(edge(0,go=1))
        with self.assertRaisesRegex(ValueError,'retained readiness'):c.edge(edge(1,go_q=1,ready=0))

    def test_FIFO_release_and_crossed_pointers_are_required(self):
        f=fifo();self.assertTrue(fifo_released_empty(f))
        for key,value in (('wonr2',0),('wrsync',1),('rgw2',1),('wb',1)):
            wrong=dict(f);wrong[key]=value;self.assertFalse(fifo_released_empty(wrong))

    def test_startup_cannot_use_zero_tags_as_drain_or_disabled_service(self):
        s=snapshot();c=CausalJoin();r=FinitePrefetchReplay()
        self.assertTrue(startup_ready(s,c,r))
        c.pending['fixture']=dict(requests={'uncredited':1})
        self.assertFalse(startup_ready(s,c,r));c.pending.clear()
        r.assembly[0]=1;self.assertFalse(startup_ready(s,c,r));r.assembly.clear()
        for change in ('disabled','epoch','tail','PC31','release'):
            wrong=copy.deepcopy(s)
            if change=='disabled':wrong['stacks'][0]['enabled']=0
            elif change=='epoch':wrong['domains']['serial']['epoch']=6
            elif change=='tail':wrong['kv']['tail_state_bound']=0
            elif change=='PC31':wrong['stacks'][3]['rcount'][31]=1
            else:wrong['bridges'][0]['ronw2']=0
            self.assertFalse(startup_ready(wrong,c,r))

    def test_literal_KV_descriptor_edge_excludes_previous_ok(self):
        s=dict(kvs_ok=1,kv_write_drained=1,boot_any_v=0,boot_busy=0,desc_pending=0,kvd_v=0)
        self.assertTrue(kv_admission(s))
        for n in ('boot_any_v','boot_busy','desc_pending','kvd_v'):
            bad=dict(s);bad[n]=1;self.assertFalse(kv_admission(bad))
        s['kv_write_drained']=0;self.assertFalse(kv_admission(s))

    def test_registered_join_cannot_credit_current_sample_or_change_epoch(self):
        b=StartupBarrier();s=snapshot();c=CausalJoin();r=FinitePrefetchReplay()
        first=b.sample(0,s,c,r)
        self.assertFalse(first['parent_domains_ready_preedge'])
        self.assertTrue(first['registered_ready_afteredge'])
        second=b.sample(1,s,c,r);self.assertTrue(second['parent_domains_ready_preedge'])
        s['epoch']=8
        with self.assertRaisesRegex(ValueError,'quarantine'):b.sample(2,s,c,r)

    def test_actual_tile_go_cannot_bypass_provider_barrier(self):
        c=self.held();e=edge(0,go=1,ready=0);e['ib_go']=1
        with self.assertRaisesRegex(ValueError,'actual tile ib_go'):c.edge(e)


if __name__=='__main__':unittest.main()

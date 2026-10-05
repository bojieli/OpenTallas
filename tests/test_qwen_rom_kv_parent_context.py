"""Finite interface fixtures only; actual provider/physical admission stays FAIL."""
import copy
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_parent_context as M

PARENT='28d01b35ac5c82595e5c8a96200cd1f6ecb4269f'

def owner():
    return dict(user=1,rank=2,layer=35,epoch=7,producer_pc=4095,sequence=19)

def status():return dict.fromkeys(M.STATUS_FIELDS,1)

def fifo():
    return dict(wrsync=3,rrsync=3,won=1,ron=1,ronw2=1,wonr2=1,
                wb=0,rb=0,wg=0,rg=0,rgw2=0,wgr2=0)

def service():
    return dict(qcount=[0]*32,rcount=[0]*32,owners=[dict(live_tags=0,state=0,held=0) for _ in range(1)],
        **dict.fromkeys(('ingress','wr_live','wr_backed','wr_mapped','grant_valid','live_tags',
        'owner_state','owner_held','route_live','quarantine_debt','flight_debt','bank_lease_debt','inflight_beat_debt','fault'),0),
        bridges=[fifo(),fifo()],local_release=1,state_bound=1,enabled=1)

class InterfaceTests(unittest.TestCase):
    def test_complete_owner_aperture_and_every_identity_bit(self):
        o=owner();self.assertLess(M.owner_word(o),1<<100)
        for k,_ in M.OWNER_FIELDS:
            c=dict(o);c[k]^=1;self.assertNotEqual(M.owner_word(o),M.owner_word(c))
        for bad in (dict(o,layer=36),dict(o,producer_pc=4096),dict(o,epoch=True)):
            with self.assertRaises(ValueError):M.owner_word(bad)
        del o['sequence']
        with self.assertRaises(ValueError):M.owner_word(o)

    def test_source_snapshot_requires_last_owner_credit_and_every_PC(self):
        s=service();self.assertTrue(all(M.service_status(s).values()))
        for field in ('qcount','rcount'):
            bad=copy.deepcopy(s);bad[field][31]=1
            self.assertEqual(M.service_status(bad)['drained'],0)
        for field in ('live_tags','state','held'):
            bad=copy.deepcopy(s);bad['owners'][0][field]=1
            self.assertEqual(M.service_status(bad)['drained'],0)
        for field in ('quarantine_debt','grant_valid','route_live'):
            bad=copy.deepcopy(s);bad[field]=1
            self.assertEqual(M.service_status(bad)['drained'],0)
        s['bridges'][1]['wgr2']=1
        self.assertEqual(M.service_status(s)['released'],0)

    def test_unknown_or_missing_provider_refused(self):
        for value in ('z',True,2):
            s=service();s['state_bound']=value
            with self.assertRaises(ValueError):M.service_status(s)
        s=service();s['owners'].pop()
        with self.assertRaises(ValueError):M.service_status(s)
        s=service();s['bridges']=[]
        with self.assertRaises(ValueError):M.service_status(s)

    def test_stream_fold_requires_all1536_and_KV_debt(self):
        base=dict(local_release=1,state_bound=1,fault=0)
        kv=dict(base,used=0,fl_v=0,boot_busy=0,boot_any_v=0,desc_pending=0,kvd_v=0,
            live_assembly=0,live_readers=0,reverse_credit_debt=0,adapter_idle=1)
        array=dict(base,broadcast_go_debt=0,x_valid_debt=0,tree_valid_debt=0,
            tiles=[dict(active=0,pend=0,go_q=0,kv_rd_q=0,rom_inflight=0) for _ in range(1536)])
        self.assertTrue(all(M.stream_status(kv,array).values()))
        array['tiles'][1535]['rom_inflight']=1
        self.assertEqual(M.stream_status(kv,array)['drained'],0)
        array['tiles'][1535]['rom_inflight']=0;kv['reverse_credit_debt']=1
        self.assertEqual(M.stream_status(kv,array)['drained'],0)
        array['tiles'].pop()
        with self.assertRaises(ValueError):M.stream_status(kv,array)

    def test_mailbox_source_and_destination_guard_then_return_ACK(self):
        b=M.OwnedMailbox();o=owner();b.offer(o)
        provider=lambda:(o,status())
        self.assertFalse(b.source_edge(provider));self.assertFalse(b.source_edge(provider))
        self.assertTrue(b.source_edge(provider))
        self.assertFalse(b.stream_edge());self.assertFalse(b.stream_edge());self.assertTrue(b.stream_edge())
        b.consume()
        for _ in range(2):
            b.source_edge(provider)
            with self.assertRaises(ValueError):b.offer(o)
        b.source_edge(provider);self.assertFalse(b.leased)
        b.stream_edge();b.stream_edge()
        with self.assertRaises(ValueError):b.offer(o)
        b.stream_edge();b.offer(dict(o,sequence=20))

    def test_mailbox_rejects_wrong_PC_and_waits_for_actual_drain(self):
        b=M.OwnedMailbox();o=owner();b.offer(o)
        b.source_edge(lambda:None);b.source_edge(lambda:None)
        with self.assertRaises(ValueError):b.source_edge(lambda:(dict(o,producer_pc=0),status()))
        self.assertFalse(b.source_edge(lambda:(o,dict(status(),drained=0))))
        self.assertEqual(b.ack,0)
        self.assertTrue(b.source_edge(lambda:(o,status())))
        with self.assertRaisesRegex(ValueError,'lease changed'):
            b.source_edge(lambda:(o,dict(status(),drained=0)))

    def test_registered_join_no_sampling_edge_launch_or_replay(self):
        p=M.ParentJoin();o=owner();p.offer(o)
        for name in M.EXPORTS:p.receipt(name,(M.owner_word(o),status()))
        self.assertFalse(p.edge(True,True)['launch_registered'])
        self.assertTrue(p.edge(True,True)['launch_registered'])
        self.assertTrue(p.edge(False,True)['launch_consumed'])
        with self.assertRaises(ValueError):p.edge(True,True)
        with self.assertRaises(ValueError):p.retire(M.EXPORTS[:-1])
        p.retire(M.EXPORTS);p.offer(dict(o,sequence=20))

    def test_join_owner_mismatch_and_reset_need_quarantine(self):
        p=M.ParentJoin();o=owner();p.offer(o)
        with self.assertRaises(ValueError):p.receipt('service0',(M.owner_word(dict(o,epoch=8)),status()))
        p.receipt('service0',(M.owner_word(o),status()))
        with self.assertRaises(ValueError):p.edge(False,False)
        self.assertFalse(p.edge(True,True)['launch_registered'])

    def test_single_owner_uses_actual12bit_namespace_and_finite_bank_contexts(self):
        q=M.TaggedOwnerPipeline()
        for t in range(128):q.allocate(t,{0:{0}})
        with self.assertRaisesRegex(ValueError,'128context'):q.allocate(128,{0:{0}})
        q.allocate(4095,{31:{31}})
        with self.assertRaises(ValueError):q.allocate(4096,{31:{31}})

    def test_LEN16_partition_keeps_addresses_and_final_aperture(self):
        for base,n in ((15,34),(0,1024),(703124983,17)):
            parts=M.partition_read(base,n)
            self.assertEqual(sum(p['sectors'] for p in parts),n)
            cursor=base
            for p in parts:
                self.assertEqual(p['base_sector'],cursor)
                self.assertLessEqual(p['sectors'],16-cursor%16);cursor+=p['sectors']
            self.assertEqual(cursor,base+n)
        with self.assertRaises(ValueError):M.partition_read(703124999,2)

    def test_new_finite_pipeline_latency_and_stalled_lossless_order(self):
        route=M.ElasticRoute();received=[]
        for e in range(139):
            accepted,out=route.edge(e if e<100 else None,True)
            if e<100:self.assertTrue(accepted)
            if out is not None:received.append((e,out))
        self.assertEqual(received,[(e+39,e) for e in range(100)])
        route=M.ElasticRoute();rng=random.Random(7);sent=[];received=[];next_packet=0
        for _ in range(4000):
            accepted,out=route.edge(next_packet if next_packet<300 else None,rng.randrange(4)==0)
            if accepted:sent.append(next_packet);next_packet+=1
            if out is not None:received.append(out)
            self.assertLessEqual(sum(map(len,route.q)),78)
        for _ in range(200):
            _,out=route.edge(None,True)
            if out is not None:received.append(out)
        self.assertEqual(sent,list(range(300)));self.assertEqual(received,sent)

    def test_joint_model_preserves_source_failures_and_single_debit(self):
        m=M.build(PARENT);s=m['joint_service_architecture']
        self.assertEqual(s['owners_per_stack'],1);self.assertEqual(s['area']['extra_context_macros'],0)
        self.assertEqual(s['tagged_pipeline']['first_lookup_edges'],12)
        self.assertLess(s['tagged_pipeline']['comparisons']['pipeline_cells_before_collectors_mm2'],s['tagged_pipeline']['comparisons']['existing14owner_known_macro_state_collector_mm2'])
        self.assertEqual(s['owner_source_II_edges'],14);self.assertEqual(s['CDC']['current_route_II_edges'],40)
        self.assertAlmostEqual(s['lower_bounds']['owned_data_plus_grant_s'],.002356992)
        self.assertGreater(s['lower_bounds']['perfect_compute_overlap_transport_s'],1/3000)
        self.assertFalse(s['producer_CDC']['retained_source_FIFO_recharged'])
        self.assertFalse(m['hardware_admitted']);self.assertFalse(m['new_decode'])
        self.assertEqual(m['peer_join']['export_count'],6)
        self.assertFalse(m['ports']['existing_capture_recharged'])
        self.assertEqual(m['ports']['existing_capture_bits'],780288)
        self.assertGreater(s['area']['useful_full_residency_min_increment_mm2'],131)
        self.assertEqual(m['wire']['shared_tile_cut_tracks_required'],1685)
        self.assertEqual(m['wire']['deficit'],325)
        self.assertFalse(m['baseline_debit_join']['complete_slot_fit'])

    def test_tagged_pipeline_retains12latency_and_constructive_interleaved_II1(self):
        q=M.TaggedOwnerPipeline();q.allocate(0,{p:{p} for p in range(16)})
        calls=[];returned=[]
        for e in range(40):
            r=dict(tag=0,pc=e,beat=e,data=bytes([e])*32,
                read_context=lambda e=e:(calls.append((q.cycle,e)) or bytes([e])*32)) if e<16 else None
            accepted,out=q.edge(r,True)
            if e<16:self.assertTrue(accepted)
            if out:returned.append((e,out))
        self.assertEqual(calls,[(12+p,p) for p in range(16)])
        self.assertEqual([(e,r['pc']) for e,r in returned],[(13+p,p) for p in range(16)])
        self.assertEqual(q.live_tags,0);self.assertIn(0,q.quarantine)

    def test_tagged_pipeline_bank_hold_and_duplicate_inflight_protection(self):
        q=M.TaggedOwnerPipeline();q.allocate(0,{0:{0}});q.allocate(1,{0:{0}})
        r=dict(tag=0,pc=0,beat=0,data=b'a'*32,read_context=lambda:b'b'*32)
        self.assertTrue(q.edge(r)[0])
        with self.assertRaisesRegex(ValueError,'duplicate'):q.edge(r)
        for _ in range(11):self.assertFalse(q.edge(dict(r,tag=1))[0])
        self.assertTrue(q.edge(dict(r,tag=1))[0])

    def test_tagged_pipeline_backpressure_reserves_output_and_quarantines_reuse(self):
        q=M.TaggedOwnerPipeline();q.allocate(0,{p:{p} for p in range(32)})
        for p in range(32):
            self.assertTrue(q.edge(dict(tag=0,pc=p,beat=p,data=b'a'*32,read_context=lambda:b'b'*32))[0])
        q.allocate(1,{0:{0}})
        for _ in range(20):
            self.assertFalse(q.edge(dict(tag=1,pc=0,beat=0,data=b'a'*32,read_context=lambda:b'b'*32))[0])
            self.assertLessEqual(len(q.flight)+len(q.output),32)
        for _ in range(32):q.edge(take=True)
        with self.assertRaises(ValueError):q.allocate(0,{0:{0}})
        with self.assertRaises(ValueError):q.release(0,False,True)
        q.release(0,True,True);q.allocate(0,{0:{0}})

    def test_tagged_pipeline_joint_allocation_and_final_retire_count(self):
        q=M.TaggedOwnerPipeline();q.allocate(0,{0:{0}})
        q.edge(dict(tag=0,pc=0,beat=0,data=b'a'*32,read_context=lambda:b'b'*32))
        for _ in range(12):q.edge()
        _,out=q.edge(take=True,allocation=(1,{1:{1}}))
        self.assertEqual(out['tag'],0);self.assertEqual(q.live_tags,1)
        self.assertEqual(q.remaining,{1:1});self.assertIn(0,q.quarantine)

if __name__=='__main__':unittest.main()

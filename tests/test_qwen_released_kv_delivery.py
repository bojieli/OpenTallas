"""Original KV control methods over directed physical-byte service fixtures."""
import ast
from collections import Counter
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h4_qwen_released_provider_delivery as D
from h4_qwen_released_kv_delivery import KVStorageDelivery


class BytePorts:
    def __init__(self):
        self.data={};self.stages={};self.calls=[];self.corrupt=None
    def transact(self,kind,request):
        self.calls.append((kind,request))
        r=dict(request,accepted=True,fault=False,writer_retained=True,owner_retained=True)
        if kind=='kv_state_read':
            r.update(captured=True,payload=bytes(self.data.get((request['rank'],request['address']+i),0)
                                               for i in range(request['bytes'])))
        elif kind=='kv_state_write':
            for i,b in enumerate(request['payload']):self.data[request['rank'],request['address']+i]=b
            r.update(visible=True,payload_sha256=D.sha(request['payload']))
        elif kind=='kv_stage_write':
            self.stages.setdefault(request['tag'],{}).update(zip(request['addresses'],request['payload']))
            r.update(staged=True,payload_sha256=D.sha(request['payload']))
        elif kind=='kv_commit':
            for a,b in self.stages[request['tag']].items():self.data[request['key'][1],a]=b
            r['all_writes_visible']=True
        elif kind=='kv_publish':r.update(published=True,state_visible=True)
        elif kind=='kv_payload_read':
            r.update(captured=True,payload=bytes(self.data[request['rank'],a] for a in request['addresses']))
        elif kind=='kv_consumer_done':r.update(consumer_accepted=True,reverse_validated=True)
        elif kind=='kv_reader_release':
            r.update(all_consumers_accepted=True,all_reverse_validated=True,all_copies_drained=True)
        if self.corrupt:self.corrupt(kind,r)
        return r


def original_classes():
    base=ROOT/'results/uarch/c0_pc40_payload_lease_20261003/inputs'
    ns=dict(np=np,Counter=Counter)
    def extent(p,rank,role):return p['extents'][rank,role]
    ns['extent']=extent
    for filename,name in [('h3_qwen_complete_native.py','Storage'),('h3_qwen_bounded_native.py','BoundKVStorage')]:
        path=base/filename;tree=ast.parse(path.read_bytes())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
    return ns['BoundKVStorage']


class KVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.BoundKV=original_classes()
    def fixture(self):
        p=dict(context_capacity=8192,config=dict(num_key_value_heads=2,head_dim=2),extents={})
        for rank in range(2):
            p['extents'][rank,'KV_provider_state']=dict(base=100000+rank*100000,bytes=37504)
            p['extents'][rank,'L0.K']=dict(base=1000+rank*40000,bytes=16384)
            p['extents'][rank,'L0.V']=dict(base=20000+rank*40000,bytes=16384)
        memory=self.BoundKV(p)
        delivery=D.ReleasedProviderDelivery.__new__(D.ReleasedProviderDelivery)
        delivery.native_module=SimpleNamespace(BoundKVStorage=self.BoundKV)
        delivery.machine=SimpleNamespace(memory=memory,current_pc=21)
        delivery.transport=BytePorts();delivery.sequence=0;delivery.pending=False;delivery.stopped=False;delivery.counts={}
        client=KVStorageDelivery(delivery).attach()
        return delivery,client,memory

    def published(self):
        d,c,m=self.fixture();tag=m.begin(0,0,0)
        # K uses the original16-position swizzle: dim1 at base+16.
        addresses=np.array([1000,1016,20000,20001],np.int64)
        m.write(tag,addresses,np.array([1,2,3,4],np.uint8));fence=m.commit(tag)
        lease=m.acquire(fence,0,0,0)
        return d,c,m,lease,addresses

    def test_actual_bytes_not_local_shadow(self):
        d,c,m,lease,a=self.published()
        m.bytes.clear()
        result=m.read(lease,a)
        self.assertEqual(result.dtype,np.uint8);self.assertEqual(result.tolist(),[1,2,3,4])
        self.assertTrue(c.installed_on(m,d.transport))

    def test_physical_state_not_local_zero_fallback(self):
        d,c,m=self.fixture();base=m.state[0]['base']
        d.transport.data[0,base]=1
        with self.assertRaises(ValueError):m.begin(0,0,0)
        self.assertTrue(d.pending and d.stopped)
        self.assertFalse(any(k=='kv_begin' for k,_ in d.transport.calls))

    def test_bad_packed_reader_blocks_payload_access(self):
        d,c,m,lease,a=self.published();base=m.state[0]['base']+36864
        for i in range(16):d.transport.data[0,base+i]=0
        with self.assertRaises(ValueError):m.read(lease,a)
        self.assertFalse(any(k=='kv_payload_read' for k,_ in d.transport.calls))

    def test_commit_visibility_precedes_bitmap_publication(self):
        d,c,m,lease,a=self.published();kinds=[k for k,_ in d.transport.calls]
        commit=kinds.index('kv_commit');publish=kinds.index('kv_publish')
        self.assertLess(commit,publish);self.assertIn('kv_state_write',kinds[commit+1:publish])

    def test_shared_sequence_all_kv_transactions(self):
        d,c,m,lease,a=self.published();m.read(lease,a);m.done(lease,'SCORES');m.done(lease,'PV')
        self.assertEqual([r['sequence'] for _,r in d.transport.calls],list(range(d.sequence)))
        self.assertFalse(d.pending);self.assertNotIn(lease,m.leases)
        self.assertFalse(c.held_readers);self.assertFalse(c.held_writers)

    def test_payload_response_length_fault(self):
        d,c,m,lease,a=self.published()
        d.transport.corrupt=lambda k,r:r.update(payload=b'') if k=='kv_payload_read' else None
        with self.assertRaises(ValueError):m.read(lease,a)
        self.assertTrue(d.pending and d.stopped)
        self.assertIsInstance(m.bytes,dict)

    def test_wrong_lease_fault(self):
        d,c,m,lease,a=self.published()
        d.transport.corrupt=lambda k,r:r.update(lease=lease+1) if k=='kv_payload_read' else None
        with self.assertRaises(ValueError):m.read(lease,a)
        self.assertTrue(d.stopped)

    def test_pv_before_scores_refused(self):
        d,c,m,lease,a=self.published()
        with self.assertRaises(ValueError):m.done(lease,'PV')
        self.assertIn(lease,m.leases)
        self.assertFalse(any(k=='kv_consumer_done' for k,_ in d.transport.calls))

    def test_missing_reverse_keeps_reader(self):
        d,c,m,lease,a=self.published()
        d.transport.corrupt=lambda k,r:r.update(reverse_validated=False) if k=='kv_consumer_done' else None
        with self.assertRaises(ValueError):m.done(lease,'SCORES')
        self.assertIn(lease,m.leases);self.assertTrue(d.pending)

    def test_missing_final_drain_fault(self):
        d,c,m,lease,a=self.published();m.done(lease,'SCORES')
        d.transport.corrupt=lambda k,r:r.update(all_copies_drained=False) if k=='kv_reader_release' else None
        with self.assertRaises(ValueError):m.done(lease,'PV')
        self.assertTrue(d.pending and d.stopped)
        self.assertEqual(c.held_readers[lease],(0,0,0))

    def test_failed_publication_keeps_physical_writer_debt(self):
        d,c,m=self.fixture();tag=m.begin(0,0,0)
        m.write(tag,np.array([1000,1016,20000,20001]),np.array([1,2,3,4],np.uint8))
        d.transport.corrupt=lambda k,r:r.update(published=False) if k=='kv_publish' else None
        with self.assertRaises(ValueError):m.commit(tag)
        self.assertEqual(c.held_writers[tag],(0,0,0))
        self.assertTrue(d.pending and d.stopped)

    def test_marker_cannot_run_full_token(self):
        d,c,m=self.fixture();d.attached=True
        d.transport.native_dispatch_program_sha256=D.PROGRAM_SHA
        m.rtl_transport=d.transport
        with self.assertRaises(ValueError):d.run_full_token(9707,0)
        # Missing client installation fails before machine.run is consulted.

    def test_marker_is_not_installation(self):
        d,c,m=self.fixture();m.rtl_transport=d.transport
        m.read=c.original['read']
        self.assertFalse(c.installed_on(m,d.transport))

    def test_no_physical_state_response_no_zero(self):
        d,c,m=self.fixture()
        d.transport.corrupt=lambda k,r:r.pop('payload',None) if k=='kv_state_read' else None
        with self.assertRaises(ValueError):m.state_read(0,0,1)
        self.assertTrue(d.stopped)

    def test_control_methods_keep_original_class(self):
        d,c,m,lease,a=self.published()
        self.assertIs(type(m),self.BoundKV)
        self.assertEqual(c.original['acquire'].__func__,self.BoundKV.acquire)
        self.assertEqual(c.original['done'].__func__,self.BoundKV.done)


if __name__=='__main__':unittest.main()

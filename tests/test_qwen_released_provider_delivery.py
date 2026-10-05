"""Live delivery unit tests; synthetic bytes are never a full-token verdict."""
import ast
from collections import Counter
import copy
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h4_qwen_released_provider_delivery as D
from h4_c0_source_operand_views_r1 import source_contract


class PortFixture:
    def __init__(self):
        self.pages={}; self.events=[]; self.corrupt=None
    def transact(self,kind,request):
        self.events.append((kind,request))
        result={k:copy.deepcopy(v) for k,v in request.items() if k!='payload'}
        result.update(accepted=True,fault=False,owner_retained=True)
        if kind=='source_page_write':
            self.pages[tuple(request['source_key'])]=request['payload']
            result['visible_copies']=request['mirrors']
        elif kind=='source_page_read':
            result.update(payload=self.pages[tuple(request['source_key'])],captured=True)
        elif kind=='source_publish': result['all_writes_visible']=True
        elif kind=='source_retire':
            result.update(all_consumers_accepted=True,all_reverse_validated=True,all_copies_drained=True)
        if self.corrupt is not None:self.corrupt(kind,result)
        return result


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native,_=source_contract()
        path=ROOT/'results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_bounded_native.py'
        tree=ast.parse(path.read_bytes()); node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TileWords')
        ns=dict(np=np,F=np.float32,math=math,Counter=Counter,copy=copy)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
        cls.TileWords=ns['TileWords']

    def fixture(self):
        store=self.TileWords(self.native)
        relay=D.ReleasedProviderDelivery.__new__(D.ReleasedProviderDelivery)
        relay.machine=SimpleNamespace(current_pc=39,store=store)
        relay.store=store; relay.sequence=0; relay.pending=False;relay.stopped=False;relay.counts={}
        relay.transport=PortFixture()
        relay.original={k:getattr(store,k) for k in ('write','read_indices','publish','retire')}
        version=self.native['operations'][39]['writes'][0]
        store.reserve(version,0)
        for start in range(0,12288,128):
            relay.write(version,start,np.arange(start,start+128,dtype=np.float32))
        relay.publish(version)
        relay.machine.current_pc=40
        return relay,version

    def test_all_canonical_source_commands(self):
        ops=D.validate_program(self.native)
        self.assertEqual(len(ops),1737)
        self.assertEqual(sum(o['opcode']=='SILU_GATE' for o in ops),72)
        self.assertEqual(ops[-1]['pc'],1736)

    def test_reduced_program_refused(self):
        reduced=dict(self.native,operations=self.native['operations'][:41])
        with self.assertRaises(ValueError):D.validate_program(reduced)

    def test_live_gate_up_routes_and_byte_payload(self):
        relay,v=self.fixture()
        gate=relay.read_indices(v,np.arange(128));up=relay.read_indices(v,np.arange(6144,6272))
        self.assertTrue(np.array_equal(gate,np.arange(128,dtype=np.float32)))
        self.assertTrue(np.array_equal(up,np.arange(6144,6272,dtype=np.float32)))
        reads=[r for k,r in relay.transport.events if k=='source_page_read']
        self.assertEqual(reads[0]['source_key'],['RF',0,0,38])
        self.assertEqual(reads[1]['source_key'],['RF',0,24,32])
        self.assertTrue(reads[1]['remote']);self.assertEqual(reads[1]['destination_SM'],0)
        self.assertIn(v,relay.store.live)

    def test_return_corruption_stops_reuse(self):
        relay,v=self.fixture()
        relay.transport.corrupt=lambda k,r:r.update(payload=bytes(512)) if k=='source_page_read' else None
        with self.assertRaises(ValueError):relay.read_indices(v,np.arange(128))
        self.assertTrue(relay.pending and relay.stopped)
        with self.assertRaises(ValueError):relay.exchange('source_page_read')

    def test_wrong_owner_stops_reuse(self):
        relay,v=self.fixture()
        relay.transport.corrupt=lambda k,r:r.update(lease='old-generation') if k=='source_page_read' else None
        with self.assertRaises(ValueError):relay.read_indices(v,np.arange(128))
        self.assertTrue(relay.stopped)

    def test_retire_needs_real_reverse(self):
        relay,v=self.fixture()
        relay.transport.corrupt=lambda k,r:r.update(all_reverse_validated=False) if k=='source_retire' else None
        with self.assertRaises(ValueError):relay.retire(40)
        self.assertIn(v,relay.store.published);self.assertTrue(relay.pending)

    def test_full_pc_retirement_after_reverse(self):
        relay,v=self.fixture();relay.retire(40)
        self.assertNotIn(v,relay.store.live)
        retirement=[r for k,r in relay.transport.events if k=='source_retire'][0]
        self.assertEqual(retirement['versions'],[v]);self.assertEqual(retirement['retire_PC'],40)

    def test_stale_sequence_blocks_read(self):
        relay,v=self.fixture()
        relay.transport.corrupt=lambda k,r:r.update(sequence=r['sequence']-1)
        with self.assertRaises(ValueError):relay.read_indices(v,np.arange(128))

    def test_existing_one_page_capture_reused_only_while_owned(self):
        relay,v=self.fixture()
        relay.read_indices(v,np.arange(128));relay.read_indices(v,np.arange(8))
        reads=[r for k,r in relay.transport.events if k=='source_page_read']
        self.assertEqual(len(reads),1)
        relay.write(v,0,np.ones(128,np.float32));relay.read_indices(v,np.arange(8))
        reads=[r for k,r in relay.transport.events if k=='source_page_read']
        self.assertEqual(len(reads),2)

    def test_default_off(self):
        with self.assertRaises(ValueError):D.ReleasedProviderDelivery(None,None,None,None)

    def test_no_software_vm_fulltoken_substitute(self):
        relay,_=self.fixture();relay.attached=True
        relay.transport.native_dispatch_program_sha256='reduced-model'
        with self.assertRaises(ValueError):relay.run_full_token(9707,0)

    def test_wire_preserves_actual_source_bits(self):
        x={'payload':bytes(range(256))*2,'control':np.uint64(2**64-1),
           'operand':np.array([0x80000000,0xc2ae0000],np.uint32).view(np.float32)}
        y=D.wire_decode(D.wire_encode(x))
        self.assertEqual(y['payload'],x['payload'])
        self.assertEqual(y['control'].dtype,np.uint64)
        self.assertEqual(y['control'].tobytes(),x['control'].tobytes())
        self.assertEqual(y['operand'].tobytes(),x['operand'].tobytes())


if __name__=='__main__':unittest.main()

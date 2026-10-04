"""Directed protocol controls, not installed RTL or token qualification."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from tools.gpu_sys import canonical_qwen_native_factory as N
from tools.gpu_sys.canonical_qwen_transport import W2PrimaryPort, TransportError

ROOT = Path(__file__).resolve().parents[1]

class Clock:
    def __init__(self): self.edges=0; self.ports=[]
    def tick(self):
        for p in self.ports: p.edge()
        self.edges+=1

class Pins:
    def __init__(self, root, parameters=None):
        self.root=root;root.ports.append(self);self.v={};self.parameters=parameters or {};self.accepts=[]
    def parameter(self,k): return self.parameters[k]
    def set(self,k,v): self.v[k]=v
    def get(self,k):
        if k=='fault':return 0
        if k=='held_session':return 2
        if k in ('publish_ready','source_native_retire_ready'):
            return int(self.root.edges>=2)
        return self.v.get(k,0)
    def settle(self): pass
    def tick(self):self.root.tick()
    def edge(self):
        for valid,ready in (('publish_valid','publish_ready'),('source_native_retire_valid','source_native_retire_ready')):
            if self.v.get(valid) and self.get(ready):self.accepts.append((valid,dict(self.v)))

class Engine(Pins):
    def __init__(self,root,fingerprint,wrong=False,change=False):
        super().__init__(root,dict(NATIVE_RPC_ABI=1,INSTRUCTION_SHA256=int(fingerprint,16)))
        self.phase='command';self.words=[];self.wrong=wrong;self.change=change;self.captured=0;self.reversed=0
    def get(self,k):
        if k=='cmd_ready':return int(self.phase=='command' and self.root.edges>=2)
        if k=='operand_ready':return int(self.phase=='operands')
        if k=='result_valid':return int(self.phase=='result')
        if k=='result_PC':return 40
        if k=='result_sequence':return 91 if self.wrong else 90
        if k=='result_dtype':return 0
        if k=='result_bytes':return 4
        # Chosen deliberately unrelated to operand addition, proving no host
        # numerical callback can silently replace the physical response.
        if k=='result_data':return 0x7fc12345 + int(self.change and self.v.get('result_ready',0))
        if k=='reverse_valid':return int(self.phase=='reverse' and self.root.edges>=8)
        if k=='reverse_PC':return 40
        if k=='reverse_sequence':return 90
        return super().get(k)
    def edge(self):
        if self.phase=='command' and self.v.get('cmd_valid') and self.get('cmd_ready'):self.phase='operands'
        elif self.phase=='operands' and self.v.get('operand_valid') and self.get('operand_ready'):
            self.words.append((self.v['operand_index'],self.v['operand_data']))
            if len(self.words)==2:self.phase='result'
        elif self.phase=='result' and self.v.get('result_ready'):
            self.captured+=1;self.phase='reverse'
        elif self.phase=='reverse' and self.v.get('reverse_ready') and self.get('reverse_valid'):
            self.reversed+=1;self.phase='done'

class W2Pins(Pins):
    def __init__(self,root):
        super().__init__(root,dict(NC=6,MAX_OUT=16,AW=34,CTAGW=32,GENW=4,PTAGW=35,
                                  OPT_EXACT=1,OPT_RESET_QUARANTINE=1,PC_ID=4))
        self.phase='offer';self.captured=False
    def set_client(self,client,k,v):self.set(k,v)
    def get(self,k):
        if k=='c_req_rdy':return 1 if self.phase=='offer' and self.root.edges>=2 else 0
        if k=='c_rsp_v':return 1 if self.phase=='return' else 0
        if k=='c_rsp_tag':return 17
        if k=='c_rsp_gen':return 3
        if k=='c_rsp_data':return int.from_bytes(bytes(range(32)),'little')
        return super().get(k)
    def edge(self):
        if self.phase=='offer' and self.v.get('c_req_v') and self.get('c_req_rdy'):self.phase='return'
        elif self.phase=='return' and self.v.get('c_rsp_rdy'):
            self.phase='reverse';self.captured=True

class NativeFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with gzip.open(ROOT/'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz','rt') as f:
            cls.program=json.load(f)
    def setUp(self):
        self.root=Clock()
        home=NS(rank=0,sm=0,first=38,end=39,birth=40,retire=41)
        self.owner=Pins(self.root,dict(ENABLE=1,SM_INDEX=0))
        self.placement=NS(rf={('v',0,0):home},version_ids={'v':1})
        self.binding=None
        self.authority=NS(canonical_native=self.program,
                          RF=NS(placement=self.placement,owners=[NS(physical=self.owner)]*64),
                          native_binding=lambda kind,r:self.binding)
        self.contexts=tuple(NS(root=self.root,rank=i//32,SM=i%32) for i in range(64))
    def request(self,**kw):return dict(program_sha256=N.PROGRAM_SHA,source_PC=40,sequence=90,**kw)
    def handlers(self):return N.native_factory(self.authority,self.contexts)
    def primitive(self):
        return self.request(template='add',ordered_step=0,source_node=deepcopy(self.program['microcode']['add'][0]),
              lowered_primitive='FADD',attrs={},explicit_shape=[],source_result_dtype='<f4',
              operands=[dict(dtype='<f4',shape=[],payload=b'\0\0\x80?')]*2)
    def engine(self,r,**kwargs):
        digest=N.sha(N.canonical(N.descriptor(r,[])))
        p=Engine(self.root,digest,**kwargs);self.binding=N.PrimitiveBinding(p,digest,())
        return p
    def test_constructor_no_writes_edges_hooks_or_second_contexts(self):
        h=self.handlers();self.assertEqual(set(h),set(N.KINDS))
        self.assertEqual(self.root.edges,0);self.assertFalse(self.owner.v)
    def test_primitive_returns_only_held_bits_after_stalls_capture_and_reverse(self):
        r=self.primitive();p=self.engine(r)
        out=self.handlers()['native_primitive'](r)
        self.assertEqual(out['payload'],b'E#\xc1\x7f')
        self.assertEqual((p.captured,p.reversed),(1,1));self.assertGreaterEqual(self.root.edges,9)
        self.assertEqual(p.words,[(0,0x3f800000),(1,0x3f800000)])
        self.assertEqual((p.v['result_ready'],p.v['reverse_ready']),(0,0))
    def test_stale_result_fails_before_capture_and_blocks_reuse(self):
        r=self.primitive();p=self.engine(r,wrong=True);h=self.handlers()
        with self.assertRaisesRegex(TransportError,'identity/dtype/span'):h['native_primitive'](r)
        self.assertEqual(p.captured,0)
        with self.assertRaisesRegex(TransportError,'debt/fault'):h['native_primitive'](r)
    def test_result_changes_when_ready_fail_closed_and_withdraw_ready(self):
        r=self.primitive();p=self.engine(r,change=True)
        with self.assertRaisesRegex(TransportError,'stable'):self.handlers()['native_primitive'](r)
        self.assertEqual(p.captured,0);self.assertEqual(p.v['result_ready'],0)
    def test_mutated_source_reference_rejected_without_edge(self):
        r=self.primitive();r['source_node']['op']='FMUL'
        with self.assertRaisesRegex(TransportError,'template/node'):self.handlers()['native_primitive'](r)
        self.assertEqual(self.root.edges,0)
    def test_missing_engine_is_not_pc40_or_software_completion(self):
        with self.assertRaisesRegex(TransportError,'endpoint missing'):self.handlers()['native_primitive'](self.primitive())
        self.assertEqual(self.root.edges,0)
    def test_i64_payload_not_narrowed(self):
        r=self.primitive();r['operands'][0]=dict(dtype='<i8',shape=[1],payload=b'\0'*4)
        with self.assertRaisesRegex(TransportError,'operand span'):self.handlers()['native_primitive'](r)
        self.assertEqual(self.root.edges,0)
    def test_publication_waits_actual_owner_not_page_count(self):
        t=(2<<175)|(40<<164)|(1<<19)|(38<<10)|39
        self.binding=(N.SourceRange(0,t,123,'v'),)
        r=self.request(version='v',lease='value:v',retire_PC=41,
                       source_pages=[dict(source_key=['RF',0,0,38],version='v',lease='value:v')])
        out=self.handlers()['source_publish'](r)
        self.assertTrue(out['all_writes_visible']);self.assertEqual(self.root.edges,3)
        self.assertEqual(len(self.owner.accepts),1)
        self.assertEqual(self.owner.v['publish_page_mask'],1)
    def test_missing_page_and_wrong_owner_span_are_not_published(self):
        t=(2<<175)|(40<<164)|(1<<19)|(37<<10)|39
        self.binding=(N.SourceRange(0,t,123,'v'),)
        r=self.request(version='v',lease='value:v',retire_PC=41,
                       source_pages=[dict(source_key=['RF',0,0,38],version='v',lease='value:v')])
        with self.assertRaisesRegex(TransportError,'producer group'):self.handlers()['source_publish'](r)
        self.assertEqual(self.root.edges,0)
    def test_retirement_uses_actual_retire_ready(self):
        self.binding=(N.RetiredRange(0,2,123,'v'),)
        r=self.request(versions=['v'],leases=['value:v'],retire_PC=41);r['source_PC']=41
        out=self.handlers()['source_retire'](r)
        self.assertTrue(out['all_reverse_validated']);self.assertEqual(self.root.edges,3)
        self.assertEqual(self.owner.v['source_native_retire_valid'],0)
    def test_control_publication_refused_not_empty_success(self):
        r=self.request(version='control',lease='value:control',source_pages=[],retire_PC=40)
        with self.assertRaisesRegex(TransportError,'control/VM'):self.handlers()['source_publish'](r)
    def test_immutable_actual_w2_capture_and_reverse_not_expected_payload(self):
        p=W2Pins(self.root)
        a=NS(completion_ready=lambda *args:True,
             reverse_validated=lambda *args:p.captured and self.root.edges>=7)
        w2=W2PrimaryPort(p,a)
        self.binding=N.ImmutableBinding(((N.ImmutableSector(w2,0,128,17,3,3,7),),))
        r=self.request(source_request=dict(lease_state='visible',provider_ref='weight',lease='lease',
                       byte_ranges=[dict(address=131,bytes=7)]),source_payloads=[bytes(range(3,10))])
        out=self.handlers()['immutable_source_transfer'](r)
        self.assertEqual(out['payloads'],[bytes(range(3,10))]);self.assertGreaterEqual(self.root.edges,7)
        self.assertIsNone(w2.pending)
    def test_wrong_checkpoint_bytes_fail_after_actual_capture(self):
        p=W2Pins(self.root);a=NS(completion_ready=lambda *args:True,reverse_validated=lambda *args:p.captured)
        w2=W2PrimaryPort(p,a)
        self.binding=N.ImmutableBinding(((N.ImmutableSector(w2,0,128,17,3,0,4),),))
        r=self.request(source_request=dict(lease_state='visible',provider_ref='weight',lease='lease',
                       byte_ranges=[dict(address=128,bytes=4)]),source_payloads=[b'fake'])
        with self.assertRaisesRegex(TransportError,'checkpoint'):self.handlers()['immutable_source_transfer'](r)
        self.assertTrue(p.captured)

if __name__=='__main__':unittest.main()

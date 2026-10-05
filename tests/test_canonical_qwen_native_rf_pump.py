"""Protocol fixtures only; no hardware/token/arithmetic qualification."""
import unittest
from types import SimpleNamespace as NS
from tools.gpu_sys.canonical_qwen_native_rf_pump import OwnedPage,PageInitializer,RFCommandPump,HeldRFCommand,compile_command,InitialSourcePages
from tools.gpu_sys.canonical_qwen_rf_ports import RFPorts
from tools.gpu_sys.canonical_qwen_range_owner_bindings import RangeOwnerPort
from tools.gpu_sys.canonical_qwen_transport import TransportError

class Root:
    def __init__(self):self.edges=0;self.hooks=[object()];self.ports=[]
    def tick(self):
        for p in self.ports:p.edge()
        self.edges+=1

class Query:
    def __init__(self,root,stale=False):self.root=root;self.stale=stale;self.v={};root.ports.append(self)
    def parameter(self,k):return {'ENABLE':1,'SM_INDEX':0}[k]
    def get(self,k):
        return {'query_result_valid':1,'source_owner_retained':int(not(self.stale and self.root.edges>=1)),
                'query_result_tuple':40<<164,'query_result_owner':77,'query_result_slot':38,
                'fault':0}.get(k,0)
    def set(self,k,v):self.v[k]=v
    def settle(self):pass
    def tick(self):self.root.tick()
    def edge(self):pass

class RF:
    def __init__(self,root,wrong=False):self.root=root;self.v={};self.phase='request';self.wrong=wrong;root.ports.append(self)
    def parameter(self,k):return 1
    def set(self,k,v):self.v[k]=v
    def settle(self):pass
    def tick(self):self.root.tick()
    def get(self,k):
        return {'wr_ready':int(self.phase=='request' and self.root.edges>=2),
                'ack_valid':int(self.phase=='ACK'),'ack_owner':78 if self.wrong else 77,
                'ack_slot':38,'ack_identity_fault':0}.get(k,0)
    def edge(self):
        if self.phase=='request' and self.v.get('wr_valid') and self.get('wr_ready'):self.phase='ACK'
        elif self.phase=='ACK' and self.v.get('ack_ready'):self.phase='done'

class Engine:
    def __init__(self,root,wrong=False):self.root=root;root.ports.append(self);self.phase='command';self.v={};self.wrong=wrong
    def parameter(self,k):return 1 if k=='ENABLE' else int('ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354',16)
    def set(self,k,v):self.v[k]=v
    def settle(self):pass
    def get(self,k):
        if k=='cmd_ready':return int(self.phase=='command' and self.root.edges>=2)
        if k=='result_valid':return int(self.phase=='result')
        if k=='reverse_valid':return int(self.phase=='reverse' and self.root.edges>=7)
        if k in ('result_PC','reverse_PC'):return 40
        if k in ('result_sequence','reverse_sequence'):return 91 if self.wrong and k.startswith('reverse') else 90
        if k in ('result_tuple','reverse_tuple'):return 40<<164
        if k in ('result_owner','reverse_owner'):return 7
        if k=='result_dtype':return 2
        if k=='result_bytes':return 8
        if k=='result_data':return 0x8000000100000002
        return 0
    def edge(self):
        if self.phase=='command' and self.v.get('cmd_valid') and self.get('cmd_ready'):self.phase='result'
        elif self.phase=='result' and self.v.get('result_ready'):self.phase='reverse'
        elif self.phase=='reverse' and self.v.get('reverse_ready') and self.get('reverse_valid'):self.phase='done'

class RFPumpTests(unittest.TestCase):
    def setUp(self):self.root=Root()
    def page(self,stale=False,wrong=False):
        query=RangeOwnerPort(Query(self.root,stale),0);rf=RFPorts(RF(self.root,wrong))
        return OwnedPage(rf,query,40<<164,38,77)
    def request(self):return dict(program_sha256='ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354',source_PC=40,sequence=90,source_result_dtype='<i8',explicit_shape=[],
                                 template='exp',ordered_step=7,lowered_primitive='IADD')
    def binding(self,wrong=False):
        p=Engine(self.root,wrong);fields=dict(cmd_PC=40,cmd_sequence=90,cmd_tuple=40<<164,cmd_owner=7,cmd_descriptor=2)
        return HeldRFCommand(p,tuple(fields.items()),dict.fromkeys(fields,'input'),40<<164,7,(),'<i8')
    def test_positive_pagewrite_ack_and_queryseat_only(self):
        page=self.page();hooks=list(self.root.hooks);physical=page.RF.ports
        result=PageInitializer(self.root).write(page,b'x'*512)
        self.assertEqual(result['visible_copies'],2);self.assertTrue(result['query_seat_consumed'])
        self.assertEqual(self.root.hooks,hooks);self.assertIs(page.RF.ports,physical)
        self.assertEqual(page.query.physical.v['query_result_ready'],0)
        self.assertIsNone(page.RF.pending)
    def test_owner_dropped_during_wait_stops_before_ack(self):
        page=self.page(stale=True);init=PageInitializer(self.root)
        with self.assertRaisesRegex(TransportError,'physically held'):init.write(page,b'x'*512)
        self.assertTrue(init.stopped);self.assertEqual(page.RF.ports.phase,'request')
        self.assertEqual(len(self.root.hooks),1)
    def test_wrong_ack_retains_debt(self):
        page=self.page(wrong=True);init=PageInitializer(self.root)
        with self.assertRaisesRegex(TransportError,'ACK slot/owner'):init.write(page,b'x'*512)
        self.assertTrue(init.stopped);self.assertIsNotNone(page.RF.pending)
    def test_full_held_result_and_reverse_without_stream(self):
        b=self.binding();out=RFCommandPump(self.root).run(self.request(),b)
        self.assertEqual(out['payload'],bytes.fromhex('0200000001000080'))
        self.assertEqual(b.ports.phase,'done');self.assertGreaterEqual(self.root.edges,8)
        self.assertFalse(any(k.startswith('operand_') for k in b.ports.v))
        self.assertEqual(len(self.root.hooks),1)
    def test_stale_reverse_not_success_or_owner_reuse(self):
        b=self.binding(wrong=True);pump=RFCommandPump(self.root)
        with self.assertRaisesRegex(TransportError,'reverse full identity'):pump.run(self.request(),b)
        self.assertTrue(pump.stopped);self.assertEqual(b.ports.v['reverse_ready'],0)
    def test_output_ownership_cannot_be_driven(self):
        b=self.binding();fields=b.fields+(('RF_source_owner_held',1),)
        b=HeldRFCommand(b.ports,fields,dict(b.directions,RF_source_owner_held='input'),b.tuple239,b.owner55,b.result_shape,b.dtype)
        with self.assertRaisesRegex(TransportError,'only real'):RFCommandPump(self.root).run(self.request(),b)
        self.assertEqual(self.root.edges,0)
    def test_descriptor_wire_cannot_be_output(self):
        b=self.binding();b.directions['cmd_descriptor']='output'
        with self.assertRaisesRegex(TransportError,'only real'):RFCommandPump(self.root).run(self.request(),b)
    def test_short_page_cannot_overwrite_retained_tail(self):
        with self.assertRaisesRegex(TransportError,'complete admitted'):PageInitializer(self.root).write(self.page(),b'x')
        self.assertEqual(self.root.edges,0)

class InitialCallerTests(unittest.TestCase):
    def root(self,bad=False):
        import threading
        t=(2<<175)|(2047<<164)|(1<<19)|(38<<10)|39
        class InitialRoot:
            def __init__(_):_.lock=threading.RLock();_.captured=False;_.ready=0;_.edges=0
            def get(_,k):return {'issuer_initial_go_valid':int(not _.captured),
                                'issuer_initial_go_ready':_.ready,'issuer_initial_go_tuple':t,
                                'issuer_initial_go_owner':7}.get(k,0)
            def set(_,k,v):
                if k=='issuer_initial_go_ready':_.ready=v
            def settle(_):pass
            def tick(_):_.captured=bool(_.ready);_.edges+=1
        root=InitialRoot()
        class InitialOwner:
            def get(_,k):return {'fault':0,'inputs_bound_valid':int(not root.captured),
                                'inputs_bound_tuple':t+int(bad),'issued_input_live':1,
                                'issued_input_started':int(root.captured)}.get(k,0)
        home=NS(birth=-1,first=38,end=39)
        authority=NS(RF=NS(pins=root,placement=NS(rf={('initial',0,0):home},version_ids={'initial':1}),
                          owners=[NS(physical=InitialOwner())]))
        return root,InitialSourcePages(authority)
    def test_initial_pc2047_real_offer_capture_and_ready_withdraw(self):
        root,caller=self.root();out=caller.begin(0,'initial')
        self.assertEqual((out['tuple239']>>164)&2047,2047)
        self.assertEqual(root.edges,1);self.assertEqual(root.ready,0);self.assertTrue(root.captured)
    def test_wrong_initial_bound_tuple_never_sets_ready(self):
        root,caller=self.root(bad=True)
        with self.assertRaisesRegex(TransportError,'not bound'):caller.begin(0,'initial')
        self.assertEqual(root.edges,0);self.assertEqual(root.ready,0)
    def test_native_pc_does_not_alias_initial(self):
        root,caller=self.root()
        with self.assertRaisesRegex(TransportError,'explicit INITIAL'):caller.write(dict(source_PC=0))
        self.assertEqual(root.edges,0)

class CommandCompileTests(unittest.TestCase):
    def request(self):
        return dict(program_sha256='ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354',
                    source_PC=40,sequence=90,template='exp',ordered_step=7,source_node={'op':'IADD64'},
                    lowered_primitive='IADD',attrs={'dtype':'I64'},explicit_shape=None,source_result_dtype='<i8',
                    operands=[dict(dtype='<i8',shape=[128],payload=b'x'*1024),
                              dict(dtype='<i8',shape=[],payload=b'x'*8)])
    def row(self,r):return dict(id=31,template_id=3,substep=0,**{k:r[k] for k in
                           ('template','ordered_step','source_node','lowered_primitive','attrs')})
    def compile(self,r,**kw):
        return compile_command(r,self.row(r),tuple239=40<<164,owner55=7,source_slots=[[17,18],[19]],
                               source_owners=[77,78],result_slots=kw.get('result_slots',[20,21]),
                               result_owner=79,result_shape=[128])
    def test_real_fields_pack_i64_two_pages_scalar_and_full_ids(self):
        fields=self.compile(self.request())
        self.assertEqual(fields['cmd_counts'],128|(1<<8));self.assertEqual(fields['cmd_scalars'],2)
        self.assertEqual(fields['cmd_source_slots'],17|(18<<9)|(19<<18))
        self.assertEqual(fields['cmd_types'],2|(2<<2));self.assertEqual(fields['cmd_result_type'],2)
        self.assertEqual(fields['cmd_result_slots'],20|(21<<9))
        self.assertFalse(any(k.startswith('authority_') for k in fields))
    def test_live_input_overlap_rejected(self):
        with self.assertRaisesRegex(TransportError,'live operand'):self.compile(self.request(),result_slots=[18,20])
    def test_rom_reference_source_mutant_rejected(self):
        r=self.request();row=self.row(r);row['ordered_step']=8
        with self.assertRaisesRegex(TransportError,'ROM descriptor'):
            compile_command(r,row,tuple239=40<<164,owner55=7,source_slots=[[17,18],[19]],
                            source_owners=[77,78],result_slots=[20,21],result_owner=79,result_shape=[128])

if __name__=='__main__':unittest.main()

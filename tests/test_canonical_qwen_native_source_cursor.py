"""Literal source controls and finite protocol driver controls, no RTL credit."""
import copy
import threading
import unittest

from tools.gpu_sys.canonical_qwen_native_source_cursor import (
    SourceCompiler, SourceCursorProducer, compile_command)
from tools.gpu_sys.canonical_qwen_primitive_control import PROGRAM_SHA
from tools.gpu_sys.canonical_qwen_transport import TransportError


class Root:
    def __init__(self): self.lock=threading.RLock(); self.edges=0; self.ports=[]
    def settle(self): pass
    def tick(self):
        for p in self.ports: p.edge()
        self.edges+=1


class Collector:
    """Directed handshake control, deliberately not a physical qualification."""
    def __init__(self,root,t,owner):
        self.root=root;root.ports.append(self);self.v={};self.t=t;self.owner=owner
        self.live=False;self.terminal=False;self.reverse=False;self.command_accepted=False
        self.advance_count=0;self.bad_sequence=False;self.lose_scope=False
    def set(self,k,v): self.v[k]=v
    def get(self,k):
        if k=='fault': return 0
        if k=='issuer_held_fault': return int(self.lose_scope)
        if k=='issuer_held_valid': return 1
        if k in ('issuer_held_tuple','authority_tuple'): return self.t
        if k in ('issuer_held_owner','authority_owner'): return self.owner
        if k=='authority_PC': return (self.t>>164)&2047
        if k=='authority_sequence': return self.v.get('cursor_load_sequence',0)+int(self.bad_sequence)
        if k=='cursor_load_ready': return int(not self.live and self.root.edges>=2)
        if k=='source_cursor_valid': return int(self.live and not(self.terminal and self.reverse))
        if k=='source_cursor_advance_valid': return int(self.live and self.terminal and self.reverse)
        if k.startswith('source_'):
            f={'ordered_step':'step','signed_i8_mask':'signed_i8'}.get(k[7:],k[7:])
            return self.v.get('cursor_load_'+f,0)
        return 0
    def edge(self):
        if self.v.get('cursor_load_valid') and self.get('cursor_load_ready'): self.live=True
        if self.v.get('source_cursor_advance_ready') and self.get('source_cursor_advance_valid'):
            self.advance_count+=1;self.live=False;self.terminal=False;self.reverse=False


class SourceCursorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.compiler=SourceCompiler()
    def row(self,template='add',substep=0):
        return next(r for r in self.compiler.source['descriptors'] if r['template']==template and r['substep']==substep)
    def request(self,row=None,shape=None,dtype='<f4',sequence=11):
        row=row or self.row();shape=[] if shape is None else shape
        pc=next(pc for pc,m in enumerate(self.compiler.source['pc_template_masks']) if m&(1<<row['template_id']))
        arity=2 if row['source_node']['op']=='NEG' and row['substep']==1 else len(row['source_node']['src'])
        size={'<f4':4,'<u4':4,'<i8':8,'|u1':1,'|i1':1}[dtype]
        n=shape[0] if shape else 1
        return dict(program_sha256=PROGRAM_SHA,source_PC=pc,sequence=sequence,
                    **{k:copy.deepcopy(row[k]) for k in ('template','ordered_step','source_node','lowered_primitive','attrs')},
                    explicit_shape=None,source_result_dtype='<f4',
                    operands=[dict(dtype=dtype,shape=list(shape),payload=bytes([128])*size*n) for _ in range(arity)])
    def test_all1737_admissions_literal116_descriptors(self):
        self.assertEqual(len(self.compiler.source['descriptors']),116)
        for pc,mask in enumerate(self.compiler.source['pc_template_masks']):
            row=next(r for r in self.compiler.source['descriptors'] if mask&(1<<r['template_id']))
            request=self.request(row);request['source_PC']=pc
            self.assertEqual(self.compiler.seed(request).PC,pc)
        for row in self.compiler.source['descriptors']:
            self.assertEqual(self.compiler.seed(self.request(row)).descriptor,row['id'])
    def test_scalar_vector1_and_tail_are_distinct(self):
        scalar=self.compiler.seed(self.request());vector=self.compiler.seed(self.request(shape=[1]))
        self.assertEqual(scalar.counts,vector.counts)
        self.assertEqual((scalar.vector_mask,vector.vector_mask),(0,3))
        self.assertEqual((scalar.scalars,vector.scalars),(3,3))
        s=self.compiler.seed(self.request(shape=[127]))
        self.assertEqual((s.counts,s.tail),(127|(127<<8),15))
        self.assertEqual(self.compiler.seed(self.request(shape=[128])).tail,0)
    def test_signed_i8_raw_carrier_and_fingerprint(self):
        row=self.row('convert');request=self.request(row,[3],'|i1')
        before=copy.deepcopy(request);seed=self.compiler.seed(request)
        self.assertEqual((seed.types,seed.signed_i8,seed.counts,seed.vector_mask),(3,1,3,1))
        fields=compile_command(request,row,tuple239=request['source_PC']<<164,owner55=3,
                               source_slots=[[0]],source_owners=[4],result_slots=[8],result_owner=5,result_shape=[3])
        self.assertEqual((fields['cmd_types'],fields['cmd_signed_i8_mask']),(3,1))
        unsigned=copy.deepcopy(request);unsigned['operands'][0]['dtype']='|u1'
        other=compile_command(unsigned,row,tuple239=request['source_PC']<<164,owner55=3,
                              source_slots=[[0]],source_owners=[4],result_slots=[8],result_owner=5,result_shape=[3])
        self.assertNotEqual(fields['cmd_shape_sha'],other['cmd_shape_sha'])
        self.assertEqual(request,before)
    def test_false_recipe_count_and_program_fail_closed(self):
        for key,value in [('program_sha256','0'*64),('source_node',{}),('attrs',{'dtype':'I64'}),('source_PC',1737)]:
            r=self.request();r[key]=value
            with self.assertRaises(TransportError):self.compiler.seed(r)
        r=self.request();r['operands'].pop()
        with self.assertRaisesRegex(TransportError,'arity'):self.compiler.seed(r)
        r=self.request(shape=[129])
        with self.assertRaisesRegex(TransportError,'type/rank/count'):self.compiler.seed(r)
    def test_signed_other_opcode_or_truncated_payload_refused(self):
        with self.assertRaisesRegex(TransportError,'I2F'):self.compiler.seed(self.request(dtype='|i1'))
        r=self.request();r['operands'][0]['payload']=b''
        with self.assertRaisesRegex(TransportError,'payload extent'):self.compiler.seed(r)
    def setup_driver(self):
        request=self.request();root=Root();p=Collector(root,request['source_PC']<<164,7)
        producer=SourceCursorProducer(root,p,self.compiler)
        self.assertEqual((root.edges,p.v),(0,{}))
        producer.prepare(request,p.t,p.owner)
        return request,root,p,producer
    def test_first_next_after_matching_terminal_reverse_only(self):
        r,root,p,producer=self.setup_driver()
        self.assertGreaterEqual(root.edges,2)
        p.command_accepted=True;p.terminal=True
        self.assertEqual(p.get('source_cursor_advance_valid'),0)
        with self.assertRaisesRegex(TransportError,'retained'):producer.prepare(r,p.t,p.owner)
        p.reverse=True;producer.finish()
        self.assertEqual(p.advance_count,1)
        self.assertFalse(any(k.startswith('cmd_') or k.startswith('profile_') for k in p.v))
        r['sequence']=13;producer.prepare(r,p.t,p.owner)
        self.assertEqual(p.get('authority_sequence'),13)
    def test_stale_reverse_sequence_never_advanced(self):
        r,root,p,producer=self.setup_driver();p.terminal=p.reverse=True;p.bad_sequence=True
        with self.assertRaisesRegex(TransportError,'stale source'):producer.finish()
        self.assertEqual(p.advance_count,0);self.assertTrue(producer.stopped)
    def test_scope_loss_preserves_debt(self):
        r,root,p,producer=self.setup_driver();p.lose_scope=True
        with self.assertRaisesRegex(TransportError,'retained'):producer.finish()
        self.assertTrue(producer.stopped);self.assertIsNotNone(producer.active)
        self.assertEqual(p.advance_count,0)
    def test_reused_sequence_refused_after_reverse(self):
        r,root,p,producer=self.setup_driver();p.terminal=p.reverse=True;producer.finish()
        with self.assertRaisesRegex(TransportError,'stale'):producer.prepare(r,p.t,p.owner)
    def test_neg_three_substeps_cannot_be_skipped_or_reordered(self):
        rows=[r for r in self.compiler.source['descriptors'] if r['template']=='neg']
        seeds=[self.compiler.seed(self.request(r)) for r in rows]
        self.assertEqual([s.substep for s in seeds],[0,1,2])
        self.compiler.require_next(None,seeds[0])
        self.compiler.require_next(seeds[0],seeds[1])
        self.compiler.require_next(seeds[1],seeds[2])
        with self.assertRaisesRegex(TransportError,'skipped'):self.compiler.require_next(seeds[0],seeds[2])
        with self.assertRaisesRegex(TransportError,'first'):self.compiler.require_next(None,seeds[1])
        with self.assertRaisesRegex(TransportError,'skipped'):self.compiler.require_next(seeds[1],self.compiler.seed(self.request()))

if __name__=='__main__':unittest.main()

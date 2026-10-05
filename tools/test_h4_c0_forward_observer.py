import unittest,gzip,json,hashlib
from unittest.mock import patch
import numpy as np
import h3_deepseek_streaming_linear as S
from h4_c0_forward_observer import ForwardObserver,ProviderTap
import h4_c0_forward_observer as F
from h4_c0_ordered_movement import DISPATCH

class ForwardTests(unittest.TestCase):
    def parent_control(self):
        # Protocol control, never claimed as one of the actual full-program PCs.
        b=S.N.Builder();b.output('out',b.load('x',(32,)));program=b.finish()
        binding={'kind':'versioned_operand','version':'x_v0','native_address_view':'exact32'}
        native={'templates':{'t':program},'instructions':[{'pc':0,'rank_bindings':[{'rank':0,'template':'t','buffer_programs':[]}],
            'writes':[{'version':'y_v1'}],'provider_bindings':{'t':{'x':binding}}}]}
        raw=gzip.compress(json.dumps(native).encode(),mtime=0)
        dispatch={'source_program_sha256':hashlib.sha256(raw).hexdigest(),'templates':{'t':{'execution_path':'forward_streaming_Q8_matvec'}},
            'PC_dispatch':[{'calls':[{'rank':0,'template':'t'}]}]}
        context=dict(program_sha256=dispatch['source_program_sha256'],dispatch_sha256=hashlib.sha256(json.dumps(dispatch,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            PC=0,template='t',rank=0,SM=0,generation=0,version=['y_v1'],expected_execution_path='forward_streaming_Q8_matvec')
        views={'x':dict(field='x',rank=0,generation=0,kind='versioned_operand',version='x_v0',view_contract='exact32',
            provenance_certified=True,data=np.arange(32,dtype=np.float32))}
        original=F.pinned
        def blobs(path,pin=None):
            if path==F.DPATH:return raw
            if path==DISPATCH:return gzip.compress(json.dumps(dispatch).encode(),mtime=0)
            return original(path) if pin is None else original(path,pin)
        return context,views,blobs
    def test_parent_control_requires_typed_view_and_actual_owner(self):
        context,views,blobs=self.parent_control()
        with patch.object(F,'pinned',side_effect=blobs):
            with self.assertRaisesRegex(ValueError,'typed views'):ForwardObserver(parent_context=context)
            observer=ForwardObserver(parent_context=context,typed_views=views,checkpoint_revision='released_image_revision')
            with self.assertRaisesRegex(ValueError,'verified parent owner'):
                observer.attach(S.StreamingLinear((0,('wrong',),0,0,0)))
            observer.attach(S.StreamingLinear((0,('y_v1',),0,0,0)))
            self.assertEqual(observer.parent_bindings['x']['version'],'x_v0')
    def test_parent_control_stale_view_version_rejected(self):
        context,views,blobs=self.parent_control();views['x']['version']='stale'
        with patch.object(F,'pinned',side_effect=blobs):
            with self.assertRaisesRegex(ValueError,'version/view mismatch'):
                ForwardObserver(parent_context=context,typed_views=views,checkpoint_revision='released_image_revision')
    def test_actual_streaming_leaf_order_and_bits_preserved(self):
        x=np.arange(32,dtype=np.float32)/32
        codes=np.full((1,32),0x38,np.uint32);scales=np.full((1,1),127,np.uint32)
        baseline=S.StreamingLinear(('fixture','out',0,0,1));expected,br=baseline.run(x,codes,scales)
        obs=ForwardObserver(parent_context={'scope':'test fixture only'},fixture=True)
        actual,ar=obs.attach(S.StreamingLinear(('fixture','out',0,0,1))).run(x,codes,scales)
        np.testing.assert_array_equal(expected.view(np.uint32),actual.view(np.uint32))
        self.assertEqual(br['executed_primitive_scalars'],ar['executed_primitive_scalars'])
        self.assertEqual(br['kernel_calls'],ar['kernel_calls'])
        self.assertEqual(br['provider'],ar['provider'])
        r=obs.receipt();self.assertGreater(len(r['leaves']),0);self.assertTrue(r['fixture'])
        self.assertFalse(r['whole_program_movement_qualified'])
        self.assertFalse(r['hardware_qualification'])
        for leaf in r['leaves']:
            self.assertEqual(len(leaf['source_order_refs']),len(leaf['generated_program']['code']))
            self.assertFalse(leaf['parent_forward_shared_join_qualified'])
        quant=next(leaf for leaf in r['leaves'] if leaf['kind']=='quantize32')
        self.assertEqual(quant['actual_LOAD_input_mapping']['x']['origin']['kind'],'actual_streaming_read')
        dot=next(leaf for leaf in r['leaves'] if leaf['kind']=='dot32')
        for name in ('weight_codes','weight_scale_codes'):
            self.assertEqual(dot['actual_LOAD_input_mapping'][name]['origin']['kind'],'ordered_source_row_reads')
        for name in ('units','exponent'):
            origin=dot['actual_LOAD_input_mapping'][name]['origin']
            self.assertIsNotNone(origin['matched_writeback_sequence'])
            self.assertEqual(origin['source_output_origin']['fields'],['units','exponent'])
        for event in r['actual_provider_calls']:
            self.assertIsNone(event['validated_reverse_grant'])
            self.assertIsNone(event['actual_address_receipt'])
    def test_unbound_parent_handle_rejected(self):
        with self.assertRaisesRegex(ValueError,'parent native instruction context'):
            ForwardObserver(parent_context={})
    def test_no_attachment_to_started_runner(self):
        runner=S.StreamingLinear(('fixture','out',0,0,1));runner.kernel_calls['started']=1
        obs=ForwardObserver(parent_context={},fixture=True)
        with self.assertRaisesRegex(ValueError,'running leaf'):obs.attach(runner)
    def test_provider_stale_or_changed_return_rejected(self):
        backend=S.N.PersistentMemory(credits=1);tap=ProviderTap(backend)
        tap.transact(('owned',1),write=True,payload=b'actual')
        backend.values[('owned',1)]=b'changed'
        with self.assertRaisesRegex(ValueError,'differs from observed source writeback'):tap.transact(('owned',1))
    def test_trace_limit_refuses_before_next_provider_command(self):
        backend=S.N.PersistentMemory(credits=1);tap=ProviderTap(backend,max_events=1)
        tap.transact(('owned',1),write=True,payload=b'actual');before=backend.next_epoch
        with self.assertRaisesRegex(ValueError,'trace capacity'):tap.transact(('owned',1))
        self.assertEqual(backend.next_epoch,before)
    def test_native_writeback_payload_change_rejected(self):
        obs=ForwardObserver(parent_context={},fixture=True)
        runner=obs.attach(S.StreamingLinear(('fixture','out',0,0,1)))
        outputs=runner.execute(S.quant_program(),{'x':np.arange(32,dtype=np.float32)/32},'quantize32')
        bad=outputs['units'].tobytes()+np.asarray(outputs['exponent'],np.uint32).tobytes()
        bad=bytes([bad[0]^1])+bad[1:]
        with self.assertRaisesRegex(ValueError,'not actual native leaf output'):
            runner.memory.transact(('Q8block',*runner.owner,0),write=True,payload=bad)
    def test_leaf_limit_refuses_before_arithmetic(self):
        obs=ForwardObserver(parent_context={},fixture=True,max_leaves=1)
        runner=obs.attach(S.StreamingLinear(('fixture','out',0,0,1)))
        program=S.add_program(1);inputs={'a':np.zeros(1,np.float32),'b':np.zeros(1,np.float32)}
        runner.execute(program,inputs,'FADD128');counts=dict(runner.counts)
        with self.assertRaisesRegex(ValueError,'leaf trace capacity'):runner.execute(program,inputs,'FADD128')
        self.assertEqual(dict(runner.counts),counts)

if __name__=='__main__':unittest.main()

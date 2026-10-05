"""Orchestration controls only; real numerical evidence is captured separately."""
import types,unittest
from h4_c0_ds_native_execution import NativeExecution

class DriverTests(unittest.TestCase):
    def driver(self):
        d=NativeExecution.__new__(NativeExecution);d.generation=1;d.revision='exact';d.retired=set();d.journal=[];d.native_calls=[];d.expected_outputs=None;d.last_use={'input':2};d.homes=[dict(version='output',rank_group=[0])];calls=[]
        def retire(pc,g):calls.append(('retire',pc));return dict(PC=pc,generation=g,pending_obligations=0,source_consumers_released=True)
        def read(op,owned,g):calls.append(('read',op['pc']));return {'data':'orchestration-only'}
        d.provider=types.SimpleNamespace(read_views=read,retire_operation=retire,release_version=lambda v,g:calls.append(('release',v)),drain=lambda g:dict(generation=g,pending_obligations=0,live_consumers=0))
        d.groups=types.SimpleNamespace(plan=types.SimpleNamespace(parents={2}))
        def group(pc,rank,*,generation,identity,source_store_view):
            calls.append(('tile',pc,rank));return dict(publication=dict(identity=identity,payload_sha256={'data':'hash'},pending_obligations=0,events=[dict(event=e,identity=identity,sequence=i+1) for i,e in enumerate(('software_backing_visible','consumer_accept','validated_reverse_grant'))]))
        d.groups.run=group
        d.run_buffer=lambda op,*args:calls.append(('original_numeric_and_publication',op['pc'],op['family']))
        return d,calls
    def op(self,pc,family,deps):
        return dict(pc=pc,family=family,dependencies=deps,reads=[dict(version='input')],writes=[dict(version='output',home_indices=[0],native_result_binding={'result':'out'})],rank_bindings=[dict(rank=0,template='actual-template')],provider_bindings={'actual-template':{}})
    def test_group_route_never_requests_full_parts_view(self):
        d,c=self.driver();d.retired={1};d.execute_operation(self.op(2,'all_reduce',[1]))
        self.assertEqual(c,[('tile',2,0),('retire',2),('release','input')]);self.assertEqual(len(d.native_calls),1)
    def test_query_compressor_keep_original_numeric_publication(self):
        for family in ('index_q','compressor'):
            d,c=self.driver();d.execute_operation(self.op(0,family,[]))
            self.assertEqual(c,[('read',0),('original_numeric_and_publication',0,family),('retire',0)])
    def test_dependency_and_duplicate_refuse_before_provider(self):
        d,c=self.driver()
        with self.assertRaisesRegex(ValueError,'dependency'):d.execute_operation(self.op(2,'all_reduce',[1]))
        self.assertFalse(c);d.retired={2}
        with self.assertRaisesRegex(ValueError,'duplicate'):d.execute_operation(self.op(2,'all_reduce',[1]))
        self.assertFalse(c)
    def test_prefix_retains_later_consumer_version(self):
        d,c=self.driver();d.native={'instructions':[self.op(0,'compressor',[]),self.op(2,'all_reduce',[0])]}
        r=d.run(stop_after=0);self.assertEqual(r['status'],'ACTUAL_NATIVE_PREFIX_RETIRED');self.assertNotIn(('release','input'),c);self.assertFalse(r['full_token_qualified'])
    def test_allPC_and_drain_do_not_qualify_exactness(self):
        d,c=self.driver();d.native={'instructions':[self.op(0,'compressor',[]),self.op(2,'all_reduce',[0])]}
        r=d.run();self.assertEqual(r['status'],'FULL_SOURCE_NATIVE_SOFTWARE_EXECUTED_UNCOMPARED');self.assertFalse(r['full_token_exact_qualified']);self.assertIsNone(r['numerical_comparison'])

if __name__=='__main__':unittest.main()

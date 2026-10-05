import ast, bisect, collections, copy, hashlib, os, pathlib, tempfile, unittest
from h4_c0_parent_provider_join import ParentProviderJoin

class SourceJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.join=ParentProviderJoin()
    def test_all3950PC51families_bound_to_actual_source(self):
        r=self.join.report();self.assertEqual(r['programs'],{'Qwen':{'PCs':1737,'families':21},'DeepSeek':{'PCs':2213,'families':30}})
        self.assertFalse(r['full_program_movement_executed']);self.assertFalse(r['RTL_allowed'])
    def test_Qwen_actual_leaf_not_generic_family_callback(self):
        c=self.join.context('Qwen',0,0,0,1)
        rows=self.join.bind_Qwen_leaf(c,kernel='convert',microstep=0)
        self.assertTrue(rows)
        with self.assertRaises(ValueError):self.join.bind_Qwen_leaf(c,kernel='convert',microstep=100000)
    def test_source_version_and_SM_owner_cannot_be_invented(self):
        c=self.join.context('DeepSeek',0,0,0,1)
        r=dict(status='SOFTWARE_ADDRESSED_MOVEMENT_REVERSE_DRAINED',model='DeepSeek',PC=0,rank=0,generation=1,native_owner=[0,tuple(c['writes']),0,0,1])
        self.assertTrue(self.join.bind_actual_receipt(c,r)['source_binding_verified'])
        r['native_owner'][3]=1
        with self.assertRaisesRegex(ValueError,'version/SM owner'):self.join.bind_actual_receipt(c,r)
    def test_Qwen_real_pinned_byte_reader_preserves_unaligned64B_contract(self):
        from h4_c0_model import pinned
        raw=pinned('tools/qwen_trained_byte_provider.py','9fb3ba94186bde39ebaee62895d9f55b557daed5')
        nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='TrainedByteBackend']
        ns=dict(bisect=bisect,os=os,sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest())
        # Compile exact class with the retained real source filename below.
        # Exact real file/page read methods; fixture manifest only, no released
        # checkpoint or producer/codec qualification from this page control.
        with tempfile.TemporaryDirectory() as root:
            source_path=pathlib.Path(root)/'qwen_trained_byte_provider.py';source_path.write_bytes(raw)
            exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source_path),'exec'),ns)
            path=pathlib.Path(root)/'page';data=bytes(range(130));path.write_bytes(data)
            context=self.join.context('Qwen',0,0,0,1)
            ref=self.join.q['operations'][0]['provider_binding']['external_providers'][0]['provider_ref']
            image=dict(base=1024,bytes=130,segments=[dict(start=0,bytes=130,file='page',sha256=hashlib.sha256(data).hexdigest())])
            b=ns['TrainedByteBackend'].__new__(ns['TrainedByteBackend'])
            b.directory=pathlib.Path(root);b.manifest={'images':{ref:image}};b.indices={id(image):[0]};b.verified={};b.handles=collections.OrderedDict()
            b.active=None;b.transactions=0;b.range_counts=0;b.bytes_read=0
            request=dict(provider_ref=ref,base=1024,bytes=130,lease_state='visible',producer_dependency=ref+'.codec_backing_visible',lease='PAGE_CONTROL',byte_ranges=[dict(address=1025,bytes=127)])
            try:
                result,record=self.join.observe_Qwen_immutable_tile(context,b,request)
                self.assertEqual(result['payloads'],[data[1:128]])
                self.assertEqual([f['payload_bytes'] for f in record['fragments']],[63,64])
                self.assertFalse(record['actual_addressed_reverse_qualified'])
                self.assertIsNone(record['fragments'][0]['addressed_sector_reverse_receipt'])
                stamp=path.stat();path.write_bytes(b'x'*130)
                os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+1000000000))
                with self.assertRaisesRegex(ValueError,'changed after visibility'):self.join.observe_Qwen_immutable_tile(context,b,request)
            finally:b.close()
    def test_forward_operand_uses_actual_Dewey_leaf_ref(self):
        j=self.join
        for pc in j.catalog['PC_bindings']:
            for binding in pc['bindings']:
                template=binding['template'];record=j.catalog['templates'][template]
                if not record['execution_path'].startswith('forward_'):continue
                for ci,call in enumerate(record['calls']):
                    if call['dynamic_source_parameters']:continue
                    leaf=j.catalog['leaves'][call['leaf']]
                    if 'program' not in leaf:continue
                    node=leaf['program']['code'][0];value=node['dst']
                    api=__import__('h4_c0_ordered_movement').strict_api()
                    specs=api.native_value_specs({'templates':{call['leaf']:leaf['program']}},call['leaf'])
                    if not specs[value]['bytes']:continue
                    ref=dict(parent_template=template,call_index=ci,invocation_index=0,template=call['leaf'],code_index=0,
                        opcode=node['op'],attrs=node['attrs'],result_shape=node['shape'],operand='dst',value=value,
                        logical_byte_offset=0,payload_bytes=specs[value]['width'])
                    context=j.context('DeepSeek',pc['pc'],binding['rank'],0,1)
                    self.assertEqual(j.bind_DS_forward_operand(context,ref)[1],value)
                    ref['attrs']={'FAKE':True}
                    with self.assertRaises(ValueError):j.bind_DS_forward_operand(context,ref)
                    return
        self.fail('actual forward program not found')

if __name__=='__main__':unittest.main()

import copy,gzip,json,pathlib,shutil,tempfile,unittest,os
from unittest.mock import patch
import numpy as np
import h4_c0_r33_source_adapter as A

BUNDLE=os.environ.get('H4_C0_R33_BUNDLE','/tmp/claude-1000/queue/h4-c0-bridge-20261002/r33-metadata-only-inputs-r1')

class R33Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.join=A.R33SourceJoin(BUNDLE)
    def test_exact_successor_hashes_and_once_count_delta(self):
        report=self.join.report()
        self.assertEqual(report['changed_window_PCs'],40)
        self.assertEqual(report['typed_initial_homes'],3840)
        self.assertEqual(report['source_RoPE_views'],264)
        self.assertEqual(report['actual_scalar_count_delta'],{'LOAD':-1966080})
        self.assertFalse(report['calendar_admitted']);self.assertFalse(report['hardware_qualified'])
    def test_all40_PC_reject_old_template_and_bind_last127_row(self):
        j=self.join
        for witness in j.r33_bridge['window_template_joins']:
            pc=witness['PC'];context=j.context('DeepSeek',pc,0,0,1)
            tid=witness['new_template'];leaf=j.catalog['templates'][tid]['calls'][0]['leaf']
            code=j.d['templates'][tid]['code'];index=next(i for i,n in enumerate(code) if n['op']=='LOAD' and n['attrs'].get('name')=='window')
            node=code[index]
            reference=dict(parent_template=tid,template=leaf,call_index=0,invocation_index=0,code_index=index,opcode='LOAD',attrs=node['attrs'],result_shape=[127,512],operand='dst',value=node['dst'],logical_byte_offset=127*512*4-4,payload_bytes=4)
            self.assertEqual(j.bind_DS_forward_operand(context,reference)[-1],4)
            old=dict(reference,parent_template=witness['old_template'])
            with self.assertRaisesRegex(ValueError,'old template rejected'):j.bind_DS_forward_operand(context,old)
            over=dict(reference,logical_byte_offset=127*512*4)
            with self.assertRaisesRegex(ValueError,'typed span'):j.bind_DS_forward_operand(context,over)
    def test_wrong_original_native_rejected_before_join(self):
        with tempfile.TemporaryDirectory() as root:
            p=pathlib.Path(root)
            raw=A.pinned('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz')
            (p/'lowered_native.json.gz').write_bytes(raw)
            (p/'lowered_dispatch.json.gz').write_bytes((pathlib.Path(BUNDLE)/'lowered_dispatch.json.gz').read_bytes())
            with self.assertRaisesRegex(ValueError,'old source rejected'):A.R33SourceJoin(p)
    def test_actual127_typed_initial_view_and_concrete_home(self):
        j=self.join;w=j.r33_bridge['window_template_joins'][0];pc=w['PC'];rank=0
        op=j.d['instructions'][pc];tid=w['new_template'];required=op['provider_bindings'][tid]['window']
        view=dict(field='window',rank=rank,generation=1,kind='versioned_operand',provenance_certified=True,
            version=required['version'],view_contract=required['native_address_view'],data=np.zeros((127,512),np.float32),concrete_home=j.initial_index[pc,rank])
        # Test array is a shape/ownership control, never released initial history.
        self.assertEqual(j.validate_initial_view(pc,rank,1,view,'CONTROL_ONLY').shape,(127,512))
        bad=dict(view,data=np.zeros((128,512),np.float32))
        with self.assertRaisesRegex(ValueError,'shape/dtype'):j.validate_initial_view(pc,rank,1,bad,'CONTROL_ONLY')
        bad=dict(view,concrete_home=dict(view['concrete_home'],base=0))
        with self.assertRaisesRegex(ValueError,'source-owned initial address'):j.validate_initial_view(pc,rank,1,bad,'CONTROL_ONLY')
    def test_actual_r33_class_rejects_old128_native_before_read(self):
        import h3_ds_checkpoint_provider_r33 as P
        # Source-constructor control only: no checkpoint open/provider phase.
        provider=P.Provider.__new__(P.Provider);provider.native=self.join.d;provider.generation=1
        self.assertTrue(self.join.bind_current_provider(provider,self.join.dispatch)['source_identity_bound'])
        provider.native={'old128':'refused'}
        with self.assertRaisesRegex(ValueError,'cannot bind old128'):self.join.bind_current_provider(provider,self.join.dispatch)
    def test_old_calendar_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError,'once-only reprice'):
            self.join.accept_Dewey_reprice(A.R33,A.BASE+'verification.json')
    def test_source_bound_once_reprice_control_never_hardware(self):
        j=self.join
        receipt=dict(schema='H4_R33_DEWEY_ONCE_REPRICE_V1',**j.report()['required_reprice_fields'])
        with patch.object(A,'pinned',return_value=json.dumps(receipt).encode()):
            try:
                j.accept_Dewey_reprice('CONTROL_ONLY','CONTROL_ONLY')
                with self.assertRaisesRegex(ValueError,'already admitted once'):j.accept_Dewey_reprice('CONTROL_ONLY','CONTROL_ONLY')
                self.assertFalse(j.report()['hardware_qualified'])
            finally:j.calendar_admitted=False

if __name__=='__main__':unittest.main()

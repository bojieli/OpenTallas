import hashlib,json,pathlib,tempfile,unittest
import numpy as np
from h4_c0_ds_expected_outputs import ExpectedOutputs
from hbm_bound_event_journal_r30 import JournalBudget

class ExpectedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'expected.json';self.budget=JournalBudget(pathlib.Path(self.tmp.name)/'journal',1<<20)
        self.a=np.array([1.,-0.],np.float32);self.native={'instructions':[dict(pc=0,source_op={'out':'logits'},rank_bindings=[dict(rank=0)],writes=[dict(version='logits')]),dict(pc=1,source_op={},rank_bindings=[dict(rank=0)],writes=[dict(version='token')])]}
        self.r=dict(status='INDEPENDENT_EXPECTED_OUTPUTS_COMMITTED',native_program_sha256='native',checkpoint_revision='revision',generation=1,input_manifest_sha256='input',reference_source_sha256={'independent.py':'pin'},outputs=[dict(PC=pc,version=v,rank=0,field='data',shape=[2],dtype='float32',payload_sha256=hashlib.sha256(self.a.tobytes()).hexdigest()) for pc,v in ((0,'logits'),(1,'token'))])
        source=pathlib.Path(self.tmp.name)/'independent.py';source.write_text('# independently declared test expectation\n');self.r['reference_source_sha256']['independent.py']=hashlib.sha256(source.read_bytes()).hexdigest()
    def tearDown(self):self.budget.db.close();self.tmp.cleanup()
    def witness(self):
        self.path.write_text(json.dumps(self.r));return ExpectedOutputs(self.path,native_sha256='native',checkpoint_revision='revision',generation=1,input_manifest_sha256='input',native=self.native,journal_budget=self.budget)
    def observe(self,w,pc,version,a):
        identity=dict(PC=pc,version=version,rank=0,generation=1);receipt=dict(identity=identity,payload_sha256={'data':hashlib.sha256(a.tobytes()).hexdigest()},pending_obligations=0,events=[dict(event=e,identity=identity,sequence=i+1) for i,e in enumerate(('software_backing_visible','consumer_accept','validated_reverse_grant'))]);w.observe(identity,{'data':a},receipt)
    def test_complete_byte_exact_comparison_required(self):
        w=self.witness();self.observe(w,0,'logits',self.a)
        with self.assertRaisesRegex(ValueError,'incomplete'):w.finish()
        self.observe(w,1,'token',self.a);self.assertEqual(w.finish()['compared_outputs'],2)
    def test_signed_zero_mismatch_retains_failed_witness(self):
        w=self.witness();a=self.a.copy();a[1]=0.
        with self.assertRaisesRegex(ValueError,'differs'):self.observe(w,0,'logits',a)
        with self.assertRaisesRegex(ValueError,'incomplete'):w.finish()
    def test_wrong_input_contract_and_missing_head_coverage(self):
        self.r['input_manifest_sha256']='wrong'
        with self.assertRaisesRegex(ValueError,'source binding'):self.witness()
        self.r['input_manifest_sha256']='input';self.r['outputs']=self.r['outputs'][1:]
        with self.assertRaisesRegex(ValueError,'coverage'):self.witness()

if __name__=='__main__':unittest.main()

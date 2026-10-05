import unittest
from h4_c0_ds_stage_witness import required_outputs,input_identity,SOURCE_KEYS,StageWitness
import hashlib
import numpy as np
from h4_c0_ds_runtime_bindings import canonical

class StageScopeTests(unittest.TestCase):
    def test_compound_and_rank_coverage_cannot_be_omitted(self):
        n=dict(instructions=[dict(pc=0,writes=[dict(version='v',native_result_binding=dict(result='iqf'))],
            compound_output_fields=dict(iqf=['query_codes','query_exp']),rank_bindings=[dict(rank=0),dict(rank=1)])])
        self.assertEqual(len(required_outputs(n,0,0)),6)
        self.assertIn((0,'v',1,'query_exp'),required_outputs(n,0,0))
    def test_zero_publication_does_not_create_reference_credit(self):
        n=dict(instructions=[dict(pc=0,writes=[],rank_bindings=[dict(rank=0)])])
        self.assertEqual(required_outputs(n,0,0),set())
    def test_journal_location_not_source_payload_but_view_bindings_are(self):
        m={k:None for k in SOURCE_KEYS};m['journal_root']='old'
        n=dict(m,journal_root='new');self.assertEqual(input_identity(m),input_identity(n))
        n['view_bindings']={'oracle':'forbidden'};self.assertNotEqual(input_identity(m),input_identity(n))
    def test_signed_zero_byte_mismatch_refuses_retry(self):
        # Observer-only fixture, never a production provider/initializer.
        w=StageWitness.__new__(StageWitness);w.first=0;w.last=0;w.failed=False;w.generation=1;w.seen=set();w.events=[]
        w.native=dict(instructions=[dict(writes=[dict(version='v',native_result_binding=dict(result='out'))])])
        w.native_content_sha256=hashlib.sha256(canonical(w.native)).hexdigest()
        w.expected={(0,'v',0,'data'):dict(shape=[1],dtype='<f4',payload_sha256=hashlib.sha256(np.array([0.],dtype='<f4').tobytes()).hexdigest(),reference_sha256='fixture')}
        identity=dict(PC=0,version='v',rank=0,generation=1,home_indices=[0]);a=np.array([-0.],dtype='<f4')
        receipt=dict(identity=identity,payload_sha256={'data':hashlib.sha256(a.tobytes()).hexdigest()},pending_obligations=0,
            events=[dict(event=name,identity=identity,sequence=i) for i,name in enumerate(['software_backing_visible','consumer_accept','validated_reverse_grant'])])
        with self.assertRaisesRegex(ValueError,'mismatch'):w.observe(identity,{'data':a},receipt)
        with self.assertRaisesRegex(ValueError,'no retry'):w.observe(identity,{'data':a},receipt)

    def test_missing_context_identity_refuses(self):
        with self.assertRaises(ValueError):input_identity({})

if __name__=='__main__':unittest.main()

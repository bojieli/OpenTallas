import unittest
import numpy as np
import h3_deepseek_streaming_linear as S
from h4_c0_forward_observer import ForwardObserver

class ForwardTests(unittest.TestCase):
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
    def test_unbound_parent_handle_rejected(self):
        with self.assertRaisesRegex(ValueError,'parent native instruction context'):
            ForwardObserver(parent_context={})
    def test_no_attachment_to_started_runner(self):
        runner=S.StreamingLinear(('fixture','out',0,0,1));runner.kernel_calls['started']=1
        obs=ForwardObserver(parent_context={},fixture=True)
        with self.assertRaisesRegex(ValueError,'running leaf'):obs.attach(runner)

if __name__=='__main__':unittest.main()

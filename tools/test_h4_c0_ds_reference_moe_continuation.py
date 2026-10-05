import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import hdc_golden_v41 as V
from h4_c0_ds_reference_moe_continuation import observe_moe

class MoeContinuationTests(unittest.TestCase):
    def test_original_failure_restores_arithmetic_hooks(self):
        mv,sqrt=V.mv,V.sqrt
        model=SimpleNamespace(lw=lambda layer,name: np.zeros((384,5120),dtype='f4'))
        with patch.object(V.Model,'moe',side_effect=ValueError('original MoE failed')):
            with self.assertRaisesRegex(ValueError,'original MoE failed'):
                observe_moe(model,np.zeros(5120,dtype='f4'),None,lambda n:None)
        self.assertIs(V.mv,mv);self.assertIs(V.sqrt,sqrt)
    def test_concurrent_observer_refused(self):
        with patch('h4_c0_ds_reference_moe_continuation.threading.active_count',return_value=2):
            with self.assertRaisesRegex(ValueError,'single-thread'):
                observe_moe(None,None,None,None)

if __name__=='__main__':unittest.main()

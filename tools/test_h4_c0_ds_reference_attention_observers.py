import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import hdc_golden_v41 as V
from h4_c0_ds_reference_attention_observers import observe_attention

class AttentionObserverTests(unittest.TestCase):
    def test_failure_restores_every_original_function(self):
        names=('linear_q','rmsnorm_fold','rope_tail','matvec_c')
        original={k:getattr(V,k) for k in names}
        with patch.object(V.Model,'attention',side_effect=ValueError('original golden failure')):
            with self.assertRaisesRegex(ValueError,'original golden failure'):
                observe_attention(SimpleNamespace(ratio=[0,0]),np.zeros(5120,dtype='f4'),np.zeros((127,512),dtype='f4'))
        for k in names:self.assertIs(getattr(V,k),original[k])
    def test_refuse_compressed_stage(self):
        with self.assertRaisesRegex(ValueError,'sliding attention'):
            observe_attention(SimpleNamespace(ratio=[0,8]),None,None)

if __name__=='__main__':unittest.main()

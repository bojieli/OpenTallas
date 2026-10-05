import unittest
from h4_c0_ds_checkpoint_operator_bindings import gate

class HeaderGateTests(unittest.TestCase):
    def test_parameter_view_mismatch_stays_gap(self):
        self.assertEqual(gate(dict(dtype='BF16',shape=[20480]),dict(kind='immutable_parameter_provider'),dict(shape=[4,5120]),'gamma'),['parameter_source_view_needed'])
    def test_packed_expert_codec_not_silently_bf16(self):
        b=dict(kind='immutable_weight_provider',format='fp4',logical_tensor=[0,'w1'])
        self.assertEqual(gate(dict(dtype='BF16',shape=[2304,2560]),b,dict(shape=[24,2560]),'weight_codes'),['weight_source_codec_mismatch'])
    def test_full_K_floating_source_mismatch_remains(self):
        b=dict(kind='immutable_weight_provider',format='bf16',logical_tensor='head.weight')
        self.assertEqual(gate(dict(dtype='BF16',shape=[129280,5120]),b,dict(shape=[1346,5120]),'weight'),[])
        self.assertEqual(gate(dict(dtype='BF16',shape=[129280,4096]),b,dict(shape=[1346,5120]),'weight'),['weight_K_source_view_needed'])

if __name__=='__main__':unittest.main()

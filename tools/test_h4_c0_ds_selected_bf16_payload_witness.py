import hashlib,struct,unittest
import numpy as np
from h4_c0_ds_selected_bf16_payload_witness import widen_bits,compare_selected_weight

class SourceBitsTests(unittest.TestCase):
    def test_exact_widen_preserves_zero_nan_infinity_and_subnormal_bits(self):
        words=[0,0x8000,0x7fc1,0x7f81,0xff80,1,0x3f80]
        raw=b''.join(struct.pack('<H',w) for w in words)
        self.assertEqual(list(struct.unpack('<7I',widen_bits(raw))),[w<<16 for w in words])
        with self.assertRaises(ValueError):widen_bits(b'x')
    def test_actual_output_byte_comparison_signed_zero(self):
        plan=dict(PC=115,rank=0,template='source',shape=[1,2])
        expected=widen_bits(struct.pack('<HH',0x8000,0x3f80))
        proof=dict(plan=plan,expected_F32_bits_sha256=hashlib.sha256(expected).hexdigest())
        value=np.frombuffer(expected,dtype='<f4').reshape(1,2)
        self.assertEqual(compare_selected_weight(proof,plan,value)['status'],'PASS_ACTUAL_SELECTED_BF16_EXPANSION_BITS')
        wrong=value.copy();wrong[0,0]=0.
        with self.assertRaisesRegex(ValueError,'bytes differ'):compare_selected_weight(proof,plan,wrong)
    def test_wrong_owner_shape_and_codec_refuse(self):
        plan=dict(PC=115,rank=0,template='source',shape=[1,2]);value=np.ones((1,2),dtype='<f4')
        proof=dict(plan=plan,expected_F32_bits_sha256=hashlib.sha256(value.tobytes()).hexdigest())
        with self.assertRaisesRegex(ValueError,'caller plan'):compare_selected_weight(proof,dict(plan,rank=1),value)
        with self.assertRaisesRegex(ValueError,'codec/shape'):compare_selected_weight(proof,plan,value.astype('<f8'))
        with self.assertRaisesRegex(ValueError,'codec/shape'):compare_selected_weight(proof,plan,value.reshape(2,1))

if __name__=='__main__':unittest.main()

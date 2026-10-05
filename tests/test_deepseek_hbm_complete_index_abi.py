from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_abi as A
class ABI(unittest.TestCase):
    def test_all_BF16_output_bits_including_nonfinite_signedzero(self):
        bits=np.arange(65536,dtype=np.uint32)<<16
        words,m=A.widen(bits.view(np.float32))
        with np.errstate(invalid='ignore'):reference=bits.view(np.float32).astype('<f8').view('<u4').reshape(-1,2)
        self.assertTrue(np.array_equal(words,reference))
        self.assertEqual(m.counts['STORE'],2*2048)
        self.assertNotIn('FP64',m.counts)
    def test_rawF32_subnormal_and_NaN_payloads(self):
        rng=np.random.default_rng(20261001)
        bits=np.concatenate([rng.integers(0,2**32,size=4096,dtype=np.uint32),
            np.array([0,0x80000000,1,0x807fffff,0x7fffff,0x800000,0x7f800001,0xffc12345,0x7fff8000],np.uint32)])
        words,_=A.widen(bits.view(np.float32))
        with np.errstate(invalid='ignore'):reference=bits.view(np.float32).astype('<f8').view('<u4').reshape(-1,2)
        self.assertTrue(np.array_equal(words,reference))

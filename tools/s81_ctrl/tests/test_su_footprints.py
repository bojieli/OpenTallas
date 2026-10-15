import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'s81_ftok'))
from su_footprints import footprint

SH={'QN_N':256,'KV_N':512,'QB_NB':32,'SW_W':1024,'SM_H':16,'SM_LPH':16,'S_RD':16}

def desc(words):
    return sum(v<<(32*i) for i,v in enumerate(words))

class Footprints(unittest.TestCase):
    def test_qr_real_strides_and_hierarchical_pairs(self):
        f=footprint('QR',(10<<20)|64,{64:desc([256,256,8])},SH,{})
        self.assertEqual(f['operand_rows'][:8],[284,285,286,287,316,317,318,319])
        self.assertEqual(f['operand_groups'][0],[284,285])
        self.assertEqual(len(f['operand_rows']),32)
        self.assertEqual(f['output_rows'],f['operand_rows'])
        self.assertFalse(f['native_allocation'])

    def test_rw_actual_masked_descriptor_producer(self):
        f=footprint('RW',(11<<20)|64,{64:desc([512,256,25,0,5,6])},SH,{512:0})
        self.assertEqual(f['operand_rows'],list(range(256,281)))
        self.assertEqual(f['output_final_word_masks'],{'512':0x7e0})
        self.assertEqual(len(f['operand_groups']),25)

    def test_rb_pairs_preserve_score_bias_ownership(self):
        f=footprint('RB',(9<<20)|64,{64:desc([512,256,3])},SH,{512:0,513:0,514:0})
        self.assertEqual(f['operand_groups'],[[256,259],[257,260],[258,261]])

if __name__=='__main__': unittest.main()

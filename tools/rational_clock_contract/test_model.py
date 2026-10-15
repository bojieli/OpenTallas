import copy, unittest
from pathlib import Path
from fractions import Fraction as F
from model import contract, validate, windows, clocks_tcl, CORE
ROOT=Path(__file__).resolve().parents[2]
class Test(unittest.TestCase):
    def test_guards_and_fragments(self):
        r=windows()
        self.assertEqual(r['minimum_guards_ps'],dict(tx_setup_ps='2000',tx_hold_ps='4000',rx_setup_ps='9000',rx_hold_ps='2000'))
        self.assertEqual(sum(f['bit_hi']-f['bit_lo']+1 for f in r['fragments']),3588)
        self.assertEqual(r['bank_payload_flop_bits'],17940)
    def test_source_ratio_phase_mutants(self):
        c=contract(ROOT);self.assertTrue(validate(c,ROOT))
        for key,value in [('ratios',{'core':6,'fdi':6}),('reset_first_edge_delta_ps',['0','1000']),('source_sha256',{}),('timing_policy','false_path'),('roots',{}),('shared_input_roots',{})]:
            m=copy.deepcopy(c);m[key]=value
            with self.assertRaises(ValueError):validate(m,ROOT)
    def test_early_read_mutant(self):
        with self.assertRaises(ValueError):windows(early_read_edges=3)
    def test_no_exception_and_phase_limit(self):
        for i in range(-5,6):
            text=clocks_tcl(F(500*i,3))
            self.assertEqual(text.count('create_generated_clock'),5)
            for forbidden in ['false_path','multicycle','clock_groups']:self.assertNotIn(forbidden,text)
        with self.assertRaises(ValueError):clocks_tcl(CORE+1)
if __name__=='__main__':unittest.main()

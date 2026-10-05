import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_noECC_slew_fanin_probe import prior_path
class PriorPath(unittest.TestCase):
    def test_actual_receipt_keys(self):
        p=Path('/tmp/fixture')
        self.assertEqual(prior_path(p,'macro_ff_lib'),p/'macro_ff.lib')
        self.assertEqual(prior_path(p,'simple_ss_prepared'),p/'simple_ss.lib')
        self.assertEqual(prior_path(p,'q_mapped_verilog'),p/'q/mapped.v')
        self.assertIsNone(prior_path(p,'q_mapped_archive'))
if __name__=='__main__':unittest.main()

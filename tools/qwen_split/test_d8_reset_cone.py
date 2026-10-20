import unittest
from d8_reset_cone import extract

LANE=dict(bid='x',landing='land',stations=[])
BASE='''qfd_landh0_1 land (.en(s), .rs(r), .ck_s(a), .ck(b));
qfd_rst_rep sr (.clk(a), .d(ext), .q0(s));
qfd_rstseq seq (.ck(b), .rsi(ext), .rso_seq(r));
'''
class ConeTests(unittest.TestCase):
    def test_follows_actual_producers_stops_at_boundary(self):
        d=extract(BASE,LANE)
        self.assertEqual(set(d['root_inputs']),{'ext'})
        self.assertEqual(len(d['exact_instances']),2)
        self.assertFalse(d['qualified'])
        self.assertEqual(d['en_trace']['clock_pin'],'sr/clk')
    def test_duplicate_driver_refused(self):
        with self.assertRaises(ValueError):extract(BASE+'qfd_rst_rep sr2 (.clk(a), .d(ext), .q0(s));\n',LANE)
    def test_reset_cycle_refused(self):
        with self.assertRaises(ValueError):extract(BASE.replace('.d(ext)', '.d(s)'),LANE)
    def test_unknown_producer_not_invented(self):
        d=extract(BASE.replace('qfd_rstseq seq','unknown seq'),LANE)
        self.assertIn('r',d['root_inputs'])
        self.assertIn('UNMEASURED_NATIVE_ROOT_EPOCH:r',d['blockers'])
if __name__=='__main__':unittest.main()

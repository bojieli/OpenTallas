"""Actual historical die STA failure: scalar Verilog clock, indexed LEF pin."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import die_sta_libs as D


class ClockPinSpelling(unittest.TestCase):
    def test_actual_missing_station_clock_is_refused_before_sta(self):
        with self.assertRaisesRegex(ValueError,'missing from generated physical LEF'):
            D.assumed_clock_refs('qfd_xcst_s',{'ck':'input'},{'a_d':516})

    def test_scalar_and_indexed_clock_entries_keep_exact_view_names(self):
        with patch.object(D.E, 'IDX', {('qfd_xcst_s','ck')}):
            refs=D.assumed_clock_refs('qfd_xcst_s',{'ck':'input','a_d':'input'})
            self.assertEqual(refs,{'ck[0]':0.0})
            self.assertEqual(D.assumed_clock_refs('real_scalar',{'ck':'input'}),{'ck':0.0})
        leaf={'qfd_xcst_s':{c:dict(refs)for c in ('tt','ff','ss')}}
        text=D.clock_tcl({'stream':[('s_2_0/ck[0]','qfd_xcst_s','ck[0]')]},leaf,'tt')
        self.assertIn('get_pins -quiet {s_2_0/ck[0]}',text)
        self.assertNotIn('get_pins -quiet {s_2_0/ck}',text)
        self.assertIn('clock boundary pin missing or ambiguous',text)


if __name__=='__main__':unittest.main()

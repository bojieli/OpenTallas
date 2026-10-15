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

    def test_generated_scalar_index_and_multibit_roots_keep_every_pin(self):
        self.assertEqual(D.assumed_clock_refs('qfd_d2d_static', {'ck':'input'}, {'ck[0]':1}), {'ck[0]':0.0})
        pins={f'ck[{k}]':1 for k in range(12)}
        self.assertEqual(list(D.assumed_clock_refs('vector', {'ck':'input'}, pins)), list(pins))
        with self.assertRaisesRegex(ValueError, 'incomplete physical clock bus'):
            D.assumed_clock_refs('broken', {'ck':'input'}, {'ck[0]':1,'ck[2]':1})

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

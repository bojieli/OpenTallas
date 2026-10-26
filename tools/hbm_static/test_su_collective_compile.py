#!/usr/bin/env python3
import unittest
from su_collective_compile import compile_sum
from su_red_carry_calendar import CalendarError


class SequentialCompile(unittest.TestCase):
    def roots(self):
        return [dict(quarter=q, source_addr=80+q, ready_serial=20) for q in range(4)]

    def test_phase_and_return_visibility(self):
        # Cover every residue of both related clocks independently of fixture.
        for e in range(20, 212):
            r = compile_sum(self.roots(), e)
            self.assertEqual(r['lp_sample_stream'] % 2, 1)
            for q, p in r['rr_update_stream'].items():
                self.assertNotEqual((p+1) % 4, 2)
                n = (3*(p+1)+6)//4
                self.assertEqual(r['rf_commit_serial'][q], n+2)
            self.assertEqual(r['arithmetic_order'], '(((q0+q1)+q2)+q3)')
            self.assertEqual(len(r['native_lowering']['events']), 36)

    def test_actual_producer_addresses(self):
        r = compile_sum(self.roots(), 100)
        for e in r['export_plan']['exports']:
            self.assertEqual(e['source_addr'], 80+e['quarter'])
            self.assertNotIn('value', e)
        self.assertFalse(r['whole_layer_native_qualified'])

    def test_missing_quarter_refused(self):
        with self.assertRaises(CalendarError):
            compile_sum(self.roots()[:3], 100)

    def test_unready_native_producer_refused(self):
        with self.assertRaises(CalendarError):
            compile_sum(self.roots(), 19)


if __name__ == '__main__':
    unittest.main()

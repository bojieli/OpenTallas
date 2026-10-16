#!/usr/bin/env python3
"""Directed reservation counterexamples for the native RED fork lowering."""
import unittest
from su_red_carry_calendar import CalendarError, lower


def fixture():
    exports = [dict(quarter=0, command_edge=100+w, source_addr=80+w,
                    source_ready_serial=99, carry_word=w) for w in range(8)]
    exports[-1].update(emit=True, collective_tag=3, return_destination=0,
                       lp_sample_stream=162, rf_addr=0)
    return dict(rf_relay=36, exports=exports,
                returns=[dict(quarter=0, tag=3, coll_update_stream=220)])


class RedCarryCalendar(unittest.TestCase):
    def reject(self, change):
        p = fixture()
        change(p)
        with self.assertRaises(CalendarError):
            lower(p)

    def test_distinct_consumers(self):
        r = lower(fixture())
        e = r['events'][7]
        self.assertEqual(e['scalar_capture_serial'], 119)
        self.assertEqual(e['rf_commit_serial'], 156)
        self.assertEqual(e['rc_update_stream'], 161)
        self.assertEqual(e['lp_sample_stream'], 162)
        self.assertEqual(e['tag'] & 0x300, 0x300)
        self.assertEqual(int(e['red_cmd_hex'], 16) >> 8 & 0xffffffff, e['tag'])
        self.assertEqual(r['events'][8]['rf_commit_serial'], 169)

    def test_late_phase2(self):
        p = fixture()
        p['exports'][-1]['lp_sample_stream'] = 163
        e = lower(p)['events'][7]
        self.assertEqual((e['late'], e['rc_update_stream'] % 4), (1, 2))

    def test_equal_path_depth_mutant(self):
        self.reject(lambda p: p.update(rf_relay=0))

    def test_bad_lp_slot(self):
        self.reject(lambda p: p['exports'][-1].update(lp_sample_stream=198))

    def test_incomplete_native_packet(self):
        self.reject(lambda p: p['exports'].pop(0))

    def test_forbidden_return_phase(self):
        self.reject(lambda p: p['returns'][0].update(coll_update_stream=221))

    def test_rf_return_bank_collision(self):
        # E107 export bank0 at pins155; RR registered154 writes bank0..7 at155.
        self.reject(lambda p: p['returns'][0].update(coll_update_stream=203))

    def test_unmatched_return(self):
        self.reject(lambda p: p['returns'][0].update(tag=4))

    def test_missing_upstream_producer_reservation(self):
        self.reject(lambda p: p['exports'][0].pop('source_ready_serial'))

    def test_late_upstream_producer(self):
        self.reject(lambda p: p['exports'][0].update(source_ready_serial=101))

    def test_no_golden_arithmetic(self):
        p = fixture()
        p['exports'][-1]['rf_addr'] = 17
        r = lower(p)
        self.assertFalse(r['whole_layer_native_qualified'])
        self.assertFalse(r['production_rate_qualified'])
        self.assertFalse(any('value' in e for e in r['events']))


if __name__ == '__main__':
    unittest.main()

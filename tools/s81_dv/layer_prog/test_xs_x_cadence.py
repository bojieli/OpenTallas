#!/usr/bin/env python3
"""TOK-VERIFY-2 11-12 (BUS-GEAR S81 x feed 2:1): the xs compiler's x cadence knob (OT_XS_X_CADENCE).

cadence 1 (default) must reproduce the ungeared calendars exactly; cadence 2 must put every x stream word of a phase on
the word-edge grid (anchor + 2k, at least 2 edges apart), keep that parity across phases (period even) and across op
segments (segment starts even), and derive floors / tails that never undercut the measured cadence-1 record.
"""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import xs_calendar as XC  # noqa: E402
import xs_field_calendar as XF  # noqa: E402
import xs_wqb_die as WD  # noqa: E402


class _Cad:
    def __init__(self, c):
        self.c = c

    def __enter__(self):
        self.old = os.environ.get('OT_XS_X_CADENCE')
        if self.c is None:
            os.environ.pop('OT_XS_X_CADENCE', None)
        else:
            os.environ['OT_XS_X_CADENCE'] = str(self.c)

    def __exit__(self, *a):
        if self.old is None:
            os.environ.pop('OT_XS_X_CADENCE', None)
        else:
            os.environ['OT_XS_X_CADENCE'] = self.old


def _ref_spine_offsets(words, fam, K, stall=True):
    """the pre-knob spine_offsets (main 8eeefa4716dd), verbatim logic"""
    go_bt = XC.P0 + 1 + XC.CFG_TO_GO
    L = XC.LB if fam else XC.LQ
    out, prev = [], None
    for w in words:
        b = go_bt + XC.GO_TO_BEAT if prev is None else prev + 1
        n = XC.need_elems(w, fam)
        if stall and n:
            b = max(b, XC.P0 + L + -(-n // 64))
        out.append(b - go_bt)
        prev = b
    return out


class XCadence(unittest.TestCase):
    def test_default_is_one_and_bad_values_refused(self):
        with _Cad(None):
            self.assertEqual(XC.x_cadence(), 1)
        for bad in ('0', '3'):
            with _Cad(bad):
                with self.assertRaises(ValueError):
                    XC.x_cadence()

    def test_cadence1_offsets_equal_pre_knob(self):
        for op in ('ffn.experts_gu', 'attn.wo_a', 'ffn.down'):
            ph, st = XF._synthetic(op, 3, nb=40)
            for k in range(3):
                pw = XC.phase_word(ph, k)
                words = st[pw['sbase']:pw['sbase'] + pw['nb']]
                self.assertEqual(XC.spine_offsets(words, pw['bf'], pw['K']),
                                 _ref_spine_offsets(words, pw['bf'], pw['K']), op)

    def test_cadence1_calendar_byte_identical_keys(self):
        ph, st = XF._synthetic('ffn.experts_gu', 6)
        with _Cad(None):
            a = XF.op_calendar('ffn.experts_gu', ph, st, range(6))
        with _Cad(1):
            b = XF.op_calendar('ffn.experts_gu', ph, st, range(6))
        self.assertEqual(a['packed'], b['packed'])
        self.assertEqual(XF.record(a), XF.record(b))
        self.assertNotIn('x_cadence', XF.record(a))
        self.assertEqual(a['period'], XF.FLOORS['ffn.experts_gu'][1])

    def test_cadence2_word_grid_parity_and_spacing(self):
        ph, st = XF._synthetic('ffn.experts_gu', 6, nb=40)
        with _Cad(2):
            c = XF.op_calendar('ffn.experts_gu', ph, st, range(6))
        self.assertEqual(c['period'] % 2, 0)
        with _Cad(2):
            pipe = XC.compile_pipeline(ph, st, list(range(6)), 0, c['period'], cfg_lead=XF.CFG_LEAD)
        reqs = sorted(t for t, r in pipe['rows'].items() if r.get('stream_req'))
        self.assertEqual(len(reqs), 6 * 40)
        self.assertEqual(len({t % 2 for t in reqs}), 1, 'one word-edge parity over all phases')
        for p in pipe['phases']:
            ts = [t for t in reqs if p['stream'][0] <= t <= p['stream'][1]]
            self.assertEqual(len(ts), 40)
            self.assertTrue(all(b - a >= 2 for a, b in zip(ts, ts[1:])))

    def test_cadence2_floor_and_tail_derived_not_below_measured(self):
        for op in ('ffn.experts_gu', 'ffn.down', 'attn.wo_b', 'attn.wo_a'):
            ph, st = XF._synthetic(op, 6)
            with _Cad(1):
                c1 = XF.op_calendar(op, ph, st, range(6))
            with _Cad(2):
                c2 = XF.op_calendar(op, ph, st, range(6))
            self.assertGreaterEqual(c2['floor'], c1['floor'], op)
            self.assertEqual(c2['floor_c1_measured'], c1['floor'])
            self.assertEqual(c2['floor'] % 2, 0)
            self.assertGreater(c2['x_stream_delta_max'], 0, op)
            self.assertGreater(c2['predicted_span'], c1['predicted_span'], op)
            self.assertEqual(c2['span_tail'], c1.get('span_tail', XF.floor_rec(op)[3]) + c2['x_stream_delta_last'])
            r = XF.record(c2)
            self.assertEqual(r['x_cadence'], 2)

    def test_cadence2_expected_rule_between_measured_and_bound(self):
        old = os.environ.get('OT_XS_X_CADENCE_FLOOR')
        try:
            for op in ('ffn.experts_gu', 'ffn.down', 'attn.wo_a'):
                ph, st = XF._synthetic(op, 6, nb=40)
                with _Cad(2):
                    os.environ['OT_XS_X_CADENCE_FLOOR'] = 'bound'
                    b = XF.op_calendar(op, ph, st, range(6))
                    os.environ['OT_XS_X_CADENCE_FLOOR'] = 'expected'
                    e = XF.op_calendar(op, ph, st, range(6))
                self.assertLessEqual(e['floor'], b['floor'], op)
                self.assertGreaterEqual(e['floor'], e['floor_c1_measured'], op)
                self.assertEqual(e['floor'] % 2, 0)
                self.assertIn('expected', e['x_cadence_floor_rule'])
            os.environ['OT_XS_X_CADENCE_FLOOR'] = 'nope'
            with _Cad(2):
                with self.assertRaises(ValueError):
                    XC.x_cadence_floor_rule()
        finally:
            if old is None:
                os.environ.pop('OT_XS_X_CADENCE_FLOOR', None)
            else:
                os.environ['OT_XS_X_CADENCE_FLOOR'] = old

    def test_cadence2_odd_period_is_a_compile_fault(self):
        ph, st = XF._synthetic('ffn.experts_gu', 6)
        with _Cad(2):
            c = XF.op_calendar('ffn.experts_gu', ph, st, range(6))
            with self.assertRaises(XF.CalendarFault):
                XF.op_calendar('ffn.experts_gu', ph, st, range(6), period=c['period'] + 1)
            with self.assertRaises(XF.CalendarFault):      # below the derived floor
                XF.op_calendar('ffn.experts_gu', ph, st, range(6), period=c['period'] - 2)

    def test_cadence2_layer_segments_keep_parity(self):
        with _Cad(2):
            c1 = XF.op_calendar('attn.wo_b', *XF._synthetic('attn.wo_b', 6), range(6))
            c2 = XF.op_calendar('ffn.down', *XF._synthetic('ffn.down', 6), range(6))
            lc = XF.layer_calendar([c1, c2])
            self.assertTrue(all(w['start'] % 2 == 0 for w in lc['windows']))
            with self.assertRaises(XF.CalendarFault):
                XF.layer_calendar([c1, c2], starts={'attn.wo_b': 0, 'ffn.down': lc['windows'][1]['start'] + 1})

    def test_wqb_cadence(self):
        ph, st = XF._synthetic('attn.wq_b', 6)
        with _Cad(1):
            a = WD.wqb_calendar(ph, st, list(range(6)), slc=0)
        with _Cad(None):
            b = WD.wqb_calendar(ph, st, list(range(6)), slc=0)
        self.assertEqual(a['packed'], b['packed'])
        self.assertEqual(WD.calendar_record(a), WD.calendar_record(b))
        self.assertEqual(a['period'], WD.PIPE_PERIOD)
        with _Cad(2):
            c = WD.wqb_calendar(ph, st, list(range(6)), slc=0)
            self.assertEqual(c['period'] % 2, 0)
            self.assertGreater(c['predicted_span'], a['predicted_span'])
            self.assertEqual(WD.calendar_record(c)['x_cadence'], 2)
            with self.assertRaises(AssertionError):        # CalendarFault (both modules subclass AssertionError)
                WD.wqb_calendar(ph, st, list(range(6)), slc=0, period=c['period'] - 2)


if __name__ == '__main__':
    unittest.main()

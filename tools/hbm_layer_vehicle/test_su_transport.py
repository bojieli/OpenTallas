"""HBM-TRANSPORT-1 11-09: SU-face VM lane-group transport terms (su_transport.py) and the calendar compiler shift.

Unit part: the bind_F5b profile (committed extract of its bus_groups.json), refusals, and compile_calendar's per-bank
selector advance.  RTL part (needs iverilog): the real-RTL bench bench/tb_vmlg_su_bound.sv (2 leaves, pair tap, 2
native VM banks with the SRAM model) at bound depth, driven by the profile's terms; the profile form passes, every
+-1 mutant of the selector advance, the owner lag and the epoch guard/tail fails, and the as-built form fails.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/hbm_layer_vehicle')]
import su_transport as T  # noqa: E402

FIX = HERE / 'fixtures/su_transport_bind_F5b.json'
BENCH = HERE / 'bench/tb_vmlg_su_bound.sv'
RTL = ['rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv',
       'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv',
       'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv',
       'rtl/hbm_accel/generic/adapters/static_su/ot_hbm_su_static_vm_ports.sv',
       'rtl/hbm_accel/generic/vm/static/faces_q0/hfd_vms_bank_native_q0_faces.sv',
       'rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_core.sv',
       'rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv',
       'rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv',
       'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']


class Profile(unittest.TestCase):
    def setUp(self):
        self.bg = json.loads(FIX.read_text())
        self.p = T.profile(self.bg)

    def test_bind_F5b_terms(self):
        nw, ne = self.p['quarters']['NW'], self.p['quarters']['NE']
        self.assertEqual(nw['d_cmd'], [12, 12, 2, 2, 25, 25, 2, 2])
        self.assertEqual(nw['d_cal'], [35] * 8)
        self.assertEqual(ne['d_req'], [27, 27, 2, 2, 31, 31, 2, 2])
        self.assertEqual(nw['selector_advance_by_bank'], [23, 23, 33, 33, 10, 10, 33, 33])
        self.assertEqual(ne['selector_advance_by_bank'], [12, 12, 32, 32, 15, 15, 32, 32])
        self.assertEqual(nw['request_lane_edges_by_bank'], [30, 30, 4, 4, 54, 54, 4, 4])
        self.assertEqual(ne['request_lane_edges_by_bank'], [49, 49, 4, 4, 50, 50, 4, 4])
        self.assertEqual((self.p['su_start_guard'], self.p['epoch_tail']), (66, 118))
        kw = T.calendar_kwargs(self.p, 'NW')
        self.assertEqual(sorted(kw), ['request_lane_edges_by_bank', 'selector_advance_by_bank',
                                      'write_lane_edges_by_bank', 'write_selector_advance_by_bank'])

    def test_refuses_torn_leg_and_missing_bank(self):
        bad = copy.deepcopy(self.bg)
        g = next(g for g in bad['landing'] if g['sink'] == 'su_NW1.u_slice.g_leaf[1].u_leaf')
        bad['landing'].append(dict(sink='su_NW1.u_slice.g_leaf[1].u_leaf',
                                   members=[dict(g['members'][0], landed_stages=g['members'][0]['landed_stages'] + 1)]))
        with self.assertRaisesRegex(ValueError, 'two landed depths'):
            T.profile(bad)
        miss = copy.deepcopy(self.bg)
        miss['landing'] = [g for g in miss['landing'] if g['sink'] != 'vmb_NE5']
        with self.assertRaisesRegex(ValueError, 'all 8 banks'):
            T.profile(miss)

    def test_epoch_terms_never_below_as_built(self):
        import cx_layer_1021 as CX
        self.assertEqual(CX.su_epoch_terms(None), (33, 64))
        self.assertEqual(CX.su_epoch_terms(self.p), (66, 118))
        self.assertEqual(CX.su_epoch_terms(dict(su_start_guard=10, epoch_tail=10)), (33, 64))


class Compiler(unittest.TestCase):
    """compile_calendar on a synthetic quarter image: one read of bank b per command (bank b, sector b)."""

    @staticmethod
    def commands():
        words = []
        for b in range(8):
            cmd = (1 << 29) | (b << 13)                 # read valid, sector b (bank b)
            words.append(cmd << (440 + 30 * b))
        return words

    def compile(self, **extra):
        import native_su_calendar as N
        kw = dict(first_serial=100, bridge_serial=100, bridge_stream=200, host_launch=100, rows=256)
        return N.compile_calendar(self.commands(), **kw, **extra)

    def test_default_and_zero_advance_identical(self):
        w0, m0 = self.compile()
        w1, m1 = self.compile(selector_advance_by_bank=[0] * 8)
        self.assertEqual(w0, w1)
        self.assertNotIn('selector_row', json.dumps(m0['events']))

    def test_selector_row_moves_by_advance_owner_by_lane(self):
        p = T.profile(json.loads(FIX.read_text()))
        kw = T.calendar_kwargs(p, 'NW')
        _, m = self.compile(**kw)
        first = m['calendar_row0_consumer']
        for e in m['events']:
            b = e['bank']
            at = e['lg_sample'] - first
            self.assertEqual(e['selector_row'], at - kw['selector_advance_by_bank'][b])
            self.assertEqual(e['vm_pin_sample'], e['lg_sample'] + 2 + kw['request_lane_edges_by_bank'][b])
        w_as, _ = self.compile()
        w_tp, _ = self.compile(**kw)
        self.assertNotEqual(w_as, w_tp)

    def test_selector_row_before_calendar_refused(self):
        with self.assertRaisesRegex(ValueError, 'selector row'):
            self.compile(selector_advance_by_bank=[200] * 8)
        with self.assertRaisesRegex(ValueError, 'eight integers'):
            self.compile(selector_advance_by_bank=[1] * 7)


@unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'), 'iverilog not installed')
class RtlBench(unittest.TestCase):
    """Real RTL at bound depth; taps NW1 (D_CMD 2 / D_CAL 35, the largest selector advance) and NE0 (deep request)."""
    TAPS = (('NW', 2), ('NE', 0))
    NOPS = int(os.environ.get('OT_VMLG_NOPS', '600'))

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.p = T.profile(json.loads(FIX.read_text()))
        cls.sims = {}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def sim(self, rr, wr):
        if (rr, wr) not in self.sims:
            out = Path(self.tmp.name) / f'sim_{rr}_{wr}'
            subprocess.run(['iverilog', '-g2012', '-o', str(out), '-P', f'tb_vmlg_su_bound.RR={rr}',
                            '-P', f'tb_vmlg_su_bound.WR={wr}', str(BENCH)] + [str(ROOT / f) for f in RTL],
                           check=True, capture_output=True)
            self.sims[(rr, wr)] = out
        return self.sims[(rr, wr)]

    def run_bench(self, q, b, *args, rr_delta=0):
        Q = self.p['quarters'][q]
        dq, dr = Q['d_req'][b], self.resp[(q, b)]
        rr, wr = 11 + dq + dr + rr_delta, 8 + dq + dr + rr_delta
        r = subprocess.run(['vvp', '-n', str(self.sim(rr, wr)), f'+NOPS={self.NOPS}', f"+D_CMD={Q['d_cmd'][b]}",
                            f"+D_CAL={Q['d_cal'][b]}", f'+D_REQ={dq}', f'+D_RESP={dr}', *args],
                           capture_output=True, text=True, timeout=1800)
        line = [x for x in r.stdout.splitlines() if x.startswith('VMLG ')]
        self.assertTrue(line, r.stdout[-2000:])
        return line[-1].split()[1]

    # bank response legs are not in the request-side profile; bind_F5b values (vmb rr0 -> tap near_rr)
    resp = {('NW', 2): 2, ('NE', 0): 55}

    def test_profile_form_passes_and_every_mutant_fails(self):
        for q, b in self.TAPS:
            Q = self.p['quarters'][q]
            adv, lag = Q['selector_advance_by_bank'][b], Q['request_lane_edges_by_bank'][b]
            own = 2 + lag
            with self.subTest(tap=f'{q}{b // 2}'):
                self.assertEqual(self.run_bench(q, b, f'+SEL_ADV={adv}', f'+OWN_LAG={own}'), 'PASS')
                self.assertEqual(self.run_bench(q, b, '+SEL_ADV=0', '+OWN_LAG=2'), 'FAIL')        # as built
                for sa, ol in ((adv - 1, own), (adv + 1, own), (adv, own - 1), (adv, own + 1)):
                    self.assertEqual(self.run_bench(q, b, f'+SEL_ADV={sa}', f'+OWN_LAG={ol}'), 'FAIL', (sa, ol))
                for d in (-1, 1):
                    self.assertEqual(self.run_bench(q, b, f'+SEL_ADV={adv}', f'+OWN_LAG={own}', rr_delta=d), 'FAIL')

    def test_epoch_guard_and_tail(self):
        for q, b in self.TAPS:
            Q = self.p['quarters'][q]
            g, t = max(0, Q['selector_advance_by_bank'][b]), 2 + Q['request_lane_edges_by_bank'][b]
            with self.subTest(tap=f'{q}{b // 2}'):
                self.assertEqual(self.run_bench(q, b, '+EPOCH', f'+GUARD={g}', f'+TAIL={t}'), 'PASS')
                self.assertEqual(self.run_bench(q, b, '+EPOCH', f'+GUARD={g}', f'+TAIL={t - 1}'), 'FAIL')
                if g > 0:
                    self.assertEqual(self.run_bench(q, b, '+EPOCH', f'+GUARD={g - 1}', f'+TAIL={t}'), 'FAIL')


if __name__ == '__main__':
    unittest.main()

"""Causal regression for EP7's 2026-10-21 earlyoom burst after a paused 490 GiB build."""
import contextlib
import copy
import importlib.machinery
import importlib.util
import io
import pathlib
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('growth_reconcile', str(pathlib.Path(__file__).with_name('ot-heavy-reconcile')))
R = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(R)
# OWNER 10-22 20:10 zeroed the growth reservation defaults; these tests pin the pre-20:10 values to keep the rules tested
R.DEFAULTS.update(GROWTH_CAP_AVAIL_FRAC=0.25, SETTLED_FLOOR_FRAC=0.02, PHASE_MARGIN=1.0)


def row(unit, now, req, age):
    return dict(unit=unit, active=True, now=now, obs=now, req=float(req), res=req,
                age=age, cls='unmeasured', file='', file_age=0, sampled=True, rate=0.0)


def initial_rows():
    # The stopped compiler's scope remains active.  v13: its RSS is flat, so it is charged nothing itself; the settled
    # floor (2 % of RAM) covers the settled units' combined slack.
    paused = row('paused-tp192', 490.25, 512, 5000)
    return [paused] + [row(f'route{i}', 100, 128, 5000) for i in range(4)]


class GrowthAccounting(unittest.TestCase):
    def setUp(self):
        env = patch.dict(R.os.environ, {'GROWTH_FACTOR': '0.5', 'NEED_FACTOR': '0.7',
                                      'MIN_AVAIL_FRAC': '0.05', 'REAL_FLOOR_GB': '50.4',
                                      'GROW_WINDOW_S': '600', 'GROWING_FACTOR': '1.0', 'LAUNCH_HOLD_S': '120'})
        env.start()
        self.addCleanup(env.stop)

    def gate(self, rows, available, inv='1'):
        out = io.StringIO()
        with patch.object(R, 'sizes', return_value={}), patch.object(R, 'meminfo', return_value=(1008, available)), \
             patch.object(R, 'read_units', return_value=copy.deepcopy(rows)), patch.object(R, 'die_like', return_value=False), \
             patch.object(R, 'die_hold', return_value=0), patch.dict(R.os.environ, {'OT_HEAVY_PRIO': '', 'HARD_INVARIANT': inv}), \
             patch.object(R, 'holds_admit_lock', return_value=True), contextlib.redirect_stdout(out):
            R.gate(64, ['bash', 'run_replay.sh'])
        return out.getvalue()

    def test_full_sum_is_not_capped_by_ram_or_legacy_configuration(self):
        with patch.dict(R.os.environ, {'GROWTH_CAP_FRAC': '0.10'}):
            self.assertEqual(R.charged_growth({'grow': 193}, 1008), 193)
            self.assertEqual(R.charged_growth({'grow': 193}, 256), 193)

    def test_five_rapid_replays_reproduce_old_failure_and_stop_new_burst(self):
        # Actual admission avail readings: 190,187,178,163,146 GiB at 11:52:52..11:53:13.
        # Young scopes have not yet taken their measured ~38.5 GiB each; the former cap erased that future growth.
        observed_avail = [190, 187, 178, 163, 146]
        old_rows, fixed_rows = initial_rows(), initial_rows()
        old_admitted, fixed_admitted, inv_rows, inv_admitted = [], [], initial_rows(), []
        for i, available in enumerate(observed_avail):
            old_book = R.books(copy.deepcopy(old_rows), 1008, available, {})
            old_can = min(available - min(old_book['grow'], .10 * 1008), available - 50.4) / .7
            old_ok = old_can >= 64
            old_admitted.append(old_ok)
            if old_ok:
                old_rows.append(row(f'old-replay{i}', 0, 64, 10))
            fixed_ok = self.gate(fixed_rows, available, inv='0').startswith('OK ')
            inv_ok = self.gate(inv_rows, available).startswith('OK ')
            inv_admitted.append(inv_ok)
            if inv_ok:
                inv_rows.append(row(f'inv-replay{i}', 0, 64, 10))
            fixed_admitted.append(fixed_ok)
            if fixed_ok:
                fixed_rows.append(row(f'replay{i}', 0, 64, 10))
        self.assertEqual(old_admitted, [True] * 5)
        # v12 GROWING RESERVATION: each young replay is charged its whole 64 GB until it holds it -> #3..#5 refused
        self.assertEqual(fixed_admitted, [True, True, False, False, False])
        # v17 HARD INVARIANT (TOKc-ADM 10-22): 818 in use + 20 floor + 64 <= 944 admits #1; #2 adds its fresh 64 -> 966 > 944
        self.assertLessEqual(sum(inv_admitted), sum(fixed_admitted))
        self.assertEqual(inv_admitted, [True, False, False, False, False])
        self.assertEqual(fixed_rows[0]['res'], 512)
        self.assertEqual(fixed_rows[0]['now'], 490.25)

    def test_free_and_admission_report_same_uncapped_budget(self):
        rows = initial_rows() + [row(f'young{i}', 0, 64, 10) for i in range(4)]
        book = R.books(rows, 1008, 146, {})
        self.assertGreater(book['grow'], .10 * 1008)
        self.assertAlmostEqual(R.admissible(1008, 146, book, 50.4, .7), (146 - book['grow']) / .7)
        text = self.gate(rows, 146)
        self.assertTrue(text.startswith('NO '), text)
        self.assertIn('v16 measured reserve', text)      # v16: young replays are charged in full, running growth capped
        self.assertNotIn('cap 0.1', text)

    def test_low_growth_job_is_still_admitted_and_real_floor_remains(self):
        self.assertTrue(self.gate(initial_rows(), 300).startswith('OK '))
        self.assertTrue(self.gate([], 60).startswith('NO '))


class GrowingReservation(unittest.TestCase):
    def setUp(self):
        env = patch.dict(R.os.environ, {'GROWTH_FACTOR': '0.5', 'NEED_FACTOR': '0.7', 'MIN_AVAIL_FRAC': '0.05',
                                      'REAL_FLOOR_GB': '50.4', 'GROW_WINDOW_S': '600', 'GROWING_FACTOR': '1.0',
                                      'LAUNCH_HOLD_S': '120', 'OT_HEAVY_PRIO': ''})
        env.start()
        self.addCleanup(env.stop)

    def test_matured_replay_is_charged_only_what_it_has_not_taken(self):
        b = R.books([row('r', 38.5, 64, 60)], 1008, 300, {})
        self.assertAlmostEqual(b['grow'], 64 - 38.5)
        b = R.books([row('r', 38.5, 64, 4000)], 1008, 300, {})       # settled after the window: v8 rule
        self.assertLess(b['grow'], 64 - 38.5)

    def test_not_started_launcher_alive_holds_full_reservation(self):
        r = dict(row('w', 0, 64, 0), active=False, file_age=90, launcher_alive=True)
        self.assertEqual(R.books([r], 1008, 300, {})['grow'], 64)
        r['launcher_alive'] = False
        self.assertEqual(R.books([r], 1008, 300, {})['grow'], 0)

    def test_die_job_is_charged_pending_reservations(self):
        rows = initial_rows() + [row(f'replay{i}', 0, 64, 10) for i in range(2)]
        out = io.StringIO()
        with patch.object(R, 'sizes', return_value={}), patch.object(R, 'meminfo', return_value=(1008, 178)), \
             patch.object(R, 'read_units', return_value=copy.deepcopy(rows)), patch.object(R, 'die_like', return_value=True), \
             patch.object(R, 'die_hold', return_value=0), patch.object(R, 'holds_admit_lock', return_value=True), \
             contextlib.redirect_stdout(out):
            R.gate(64, ['bash', 'die_sta.sh'])
        # v13: pending 128 (two young replays) + settled floor 20.16: (178 - 148.16) / 0.7 = 42.6 < 64
        self.assertTrue(out.getvalue().startswith('NO '), out.getvalue())

    def test_gate_takes_the_lock_when_caller_does_not(self):
        import fcntl, tempfile, threading
        with tempfile.TemporaryDirectory() as d:
            lock = d + '/admit.lock'
            calls = []
            with patch.object(R, 'LOCK', lock), patch.object(R, 'holds_admit_lock', return_value=False), \
                 patch.object(R, 'gate_locked', side_effect=lambda m, a: calls.append(m)):
                lk = open(lock, 'a')
                fcntl.flock(lk, fcntl.LOCK_EX)
                t = threading.Thread(target=R.gate, args=(64, ['x']))
                t.start()
                t.join(0.5)
                self.assertTrue(t.is_alive())            # blocked behind the held host lock
                self.assertEqual(calls, [])
                fcntl.flock(lk, fcntl.LOCK_UN)
                lk.close()
                t.join(5)
                self.assertEqual(calls, [64])


if __name__ == '__main__':
    unittest.main()

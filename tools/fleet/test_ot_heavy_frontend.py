"""Actual frontend-phase accounting, including Gold2's 720/476 and 200/152 GiB incidents."""
import contextlib
import copy
import importlib.machinery
import importlib.util
import io
import pathlib
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('frontend_reconcile', str(pathlib.Path(__file__).with_name('ot-heavy-reconcile')))
R = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(R)


def scope(now, req, res=None, frontend=True, age=4000):
    return dict(unit='u', active=True, now=float(now), obs=float(now), req=float(req),
                declared=req, res=req if res is None else res, age=age, cls='unknown', sampled=True,
                rate=0.0, frontend_pids=[123] if frontend else [], file='', file_age=0)


class FrontendPhase(unittest.TestCase):
    def setUp(self):
        env = patch.dict(R.os.environ, {'GROWTH_FACTOR': '0.5', 'NEED_FACTOR': '0.7', 'MIN_AVAIL_FRAC': '0.05',
                                      'REAL_FLOOR_GB': '50.4', 'GROW_WINDOW_S': '600', 'GROWING_FACTOR': '1.0',
                                      'RATE_HORIZON_S': '600', 'RATE_MULT': '2', 'SETTLED_FLOOR_FRAC': '0.02',
                                      'OT_HEAVY_PRIO': ''})
        env.start()
        self.addCleanup(env.stop)

    def book(self, rows, avail=268):
        return R.books(rows, 1008, avail, {})

    def test_old_flat_720_frontend_retains_full_244_remaining(self):
        rows = [scope(476, 720)]
        b = self.book(rows)
        self.assertEqual(rows[0]['grow'], 244)
        self.assertEqual(b['pending'], 244)
        self.assertEqual(b['grow'], 244)
        # The actual 200 GiB head build was admitted at 268 avail with the flat frontend's slack omitted.
        self.assertLess(R.admissible(1008, 268, b, 50.4, .7), 200)
        old = self.book([scope(476, 720, frontend=False)])
        self.assertGreaterEqual(R.admissible(1008, 268, old, 50.4, .7), 200)

    def test_old_flat_200_head_frontend_retains_full_48(self):
        rows = [scope(152, 200)]
        self.assertEqual(self.book(rows)['pending'], 48)
        self.assertEqual(rows[0]['grow'], 48)

    def test_young_lowered_class_res_does_not_hide_declared_128(self):
        rows = [scope(2, 128, res=10, age=20)]
        self.assertEqual(self.book(rows)['pending'], 126)
        self.assertEqual(rows[0]['grow'], 126)

    def test_frontend_exit_restores_normal_policy_and_long_yosys_stays_settled(self):
        rows = [scope(7, 700, frontend=False, age=34*3600)]
        b = self.book(rows)
        self.assertEqual(rows[0]['grow'], 0)
        self.assertEqual(b['pending'], 0)
        self.assertEqual(b['grow'], 20.16)
        exited = [scope(476, 720, frontend=False)]
        self.assertEqual(self.book(exited)['pending'], 0)

    def test_die_priority_also_charges_frontend_pending(self):
        rows = [scope(476, 720)]
        out = io.StringIO()
        with patch.object(R, 'sizes', return_value={}), patch.object(R, 'meminfo', return_value=(1008, 268)), \
             patch.object(R, 'read_units', return_value=rows), patch.object(R, 'die_like', return_value=True), \
             patch.object(R, 'holds_admit_lock', return_value=True), contextlib.redirect_stdout(out):
            R.gate(200, ['bash', 'run_head_die.sh'])
        self.assertTrue(out.getvalue().startswith('NO '), out.getvalue())

    def test_no_negative_growth_when_current_is_above_declared(self):
        self.assertEqual(self.book([scope(52, 48)])['pending'], 0)

    def test_executable_and_cgroup_membership_classify_hier_and_flat_frontends(self):
        cg = '/fake/cgroup/unit.scope'
        files = {cg+'/cgroup.procs': '7\n8\n9\n10\n',
                 '/proc/7/comm': 'verilator_bin', '/proc/7/cmdline': 'verilator_bin\0-f\0top__hierMkArgs.f\0',
                 '/proc/8/comm': 'verilator_bin', '/proc/8/cmdline': 'verilator_bin\0--binary\0-f\0kit.f\0',
                 '/proc/9/comm': 'verilator_bin', '/proc/9/cmdline': 'python\0verilator_bin\0',
                 '/proc/10/comm': 'bash', '/proc/10/cmdline': 'bash\0verilator_bin\0',
                 '/proc/11/comm': 'verilator_bin', '/proc/11/cmdline': 'verilator_bin\0--binary\0'}
        exes = {'/proc/7/exe': '/pinned/verilator_bin', '/proc/8/exe': '/pinned/verilator_bin_dbg',
                '/proc/9/exe': '/usr/bin/python3', '/proc/10/exe': '/usr/bin/bash',
                '/proc/11/exe': '/pinned/verilator_bin'}
        with patch.object(R, 'rd', side_effect=lambda p: files.get(p, '')), \
             patch.object(R.os, 'readlink', side_effect=lambda p: exes[p]):
            # PID11 has a real frontend but is NOT a member of this scope and must not be charged to it.
            self.assertEqual(R.active_verilator_frontends(cg), [7, 8])


if __name__ == '__main__':
    unittest.main()

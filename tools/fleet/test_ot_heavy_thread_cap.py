"""THREADCAP_1116: ot-heavy holds a job that memory admits while committed threads + its threads > THREAD_CAP_FACTOR x nproc."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ThreadCap(unittest.TestCase):
    def setUp(self):
        self.d = d = Path(tempfile.mkdtemp())
        (d / 'bin').mkdir()

        def w(name, body):
            p = d / 'bin' / name
            p.write_text('#!/bin/bash\n' + body + '\n')
            p.chmod(0o755)
            return p
        self.rec = w('reconcile', '[ "$1" = --is-die ] && exit 1; [ "$1" = --is-plan ] && exit 1; echo "OK 4 cls | need 4, available 100 GB, growth charged 0 GB"')
        self.prot = w('protect', 'exit 1')
        w('systemd-run', 'printf "%s\\n" "$@" > "$OUT_ARGS"')
        w('nproc', 'echo 10')
        self.load = d / 'loadavg'
        s = (HERE / 'ot-heavy').read_text()
        s = s.replace('/usr/local/bin/ot-heavy-reconcile', str(self.rec)).replace('/usr/local/bin/ot-protect-die', str(self.prot))
        s = s.replace('/proc/loadavg', str(self.load)).replace('D=/var/tmp/ot-heavy', f'D={d}/state')
        s = s.replace('/etc/ot-heavy.conf', str(d / 'conf')).replace('/usr/local/lib/ot-heavy', str(d / 'nolib'))
        s = s.replace('sudo -n ' + str(self.prot), str(self.prot))
        s = s.replace('sleep 20', 'sleep 0.2').replace('sleep 5;', 'sleep 0.2;')
        self.h = d / 'ot-heavy'
        self.h.write_text(s)
        self.h.chmod(0o755)
        (d / 'conf').write_text('LOAD_GATE_FACTOR=0\nLOAD_CAP_FACTOR=0\n')
        (d / 'state').mkdir()

    def commit(self, n, threads, live=True):
        for i in range(n):
            (self.d / 'state' / f'cthr.u{i}').write_text(f'{threads}\n')
            if live:
                (self.d / 'state' / f'res.u{i}').write_text(f'u{i} 1\n')

    def run_(self, threads='8', extra=None):
        self.load.write_text('1.0 1.0 1.0 1/1 1\n')
        env = dict(os.environ, PATH=f'{self.d}/bin:' + os.environ['PATH'], OUT_ARGS=str(self.d / 'args'), OT_VL_JCAP='0',
                   OT_HEAVY_SYSTEM_TOOLS='1', OT_HEAVY_THREADS=threads)
        for k in ('OT_HEAVY_CPU', 'OT_HEAVY_PRIO', 'OT_HEAVY_CONF', 'OT_HEAVY_DIRECT', 'OT_HEAVY_PARENT_UNIT'):
            env.pop(k, None)
        env.update(extra or {})
        try:
            (self.d / 'args').unlink()
        except FileNotFoundError:
            pass
        r = subprocess.run([str(self.h), '--mem', '4', '--max-wait', '1', '--', 'true'], capture_output=True, text=True, env=env, timeout=60)
        return r, ((self.d / 'args').exists())

    def test_empty_host_takes_a_job_even_larger_than_the_host(self):
        r, ran = self.run_('32')
        self.assertTrue(ran, r.stderr)

    def test_fits_under_cores(self):
        self.commit(1, 2)
        r, ran = self.run_('8')                           # 2 + 8 = 10 <= 1.0 x 10
        self.assertTrue(ran, r.stderr)
        self.assertEqual((self.d / 'state' / 'cthr.u0').read_text().strip(), '2')

    def test_over_cores_waits(self):
        self.commit(1, 3)
        r, ran = self.run_('8')                           # 3 + 8 = 11 > 10
        self.assertFalse(ran)
        self.assertEqual(r.returncode, 75)
        self.assertIn('thread cap: committed 3 threads + this job 8 > 1.0 x 10 = 10', r.stderr)

    def test_dead_unit_does_not_count(self):
        self.commit(3, 8, live=False)                     # no res.<unit>: finished
        r, ran = self.run_('8')
        self.assertTrue(ran, r.stderr)
        self.assertEqual(list((self.d / 'state').glob('cthr.u*')), [])

    def test_admission_records_committed_threads(self):
        r, ran = self.run_('8')
        self.assertTrue(ran, r.stderr)
        self.assertEqual([p.read_text().strip() for p in (self.d / 'state').glob('cthr.*')], ['8'])

    def test_plan_direct_crit_exempt(self):
        for env in ({'OT_HEAVY_PRIO': 'plan'}, {'OT_HEAVY_DIRECT': '1'}, {'OT_HEAVY_CPU': 'crit'}):
            self.commit(1, 9)
            r, ran = self.run_('8', env)
            self.assertTrue(ran or env.get('OT_HEAVY_DIRECT'), (env, r.stderr))   # --direct has its own memory rule
            self.assertNotIn('thread cap', r.stderr, env)

    def test_factor_zero_disables(self):
        (self.d / 'conf').write_text('LOAD_GATE_FACTOR=0\nLOAD_CAP_FACTOR=0\nTHREAD_CAP_FACTOR=0\n')
        self.commit(1, 9)
        r, ran = self.run_('8')
        self.assertTrue(ran, r.stderr)

    def test_idle_cpu_admits_past_the_declared_ceiling(self):
        self.commit(4, 8)                                 # 32 declared threads on 10 cores, load1 1.0
        r, ran = self.run_('8')                           # measured 1 + 8 = 9 > 0.6 x 10 = 6: held
        self.assertFalse(ran)
        self.assertIn('measured CPU', r.stderr)
        r, ran = self.run_('8', {'THREAD_MEASURED_FACTOR': '1.0'})   # 9 < 10: measured CPU has room
        self.assertTrue(ran, r.stderr)
        self.assertIn('admitted on measured CPU', (self.d / 'state' / 'admit.log').read_text())

    def test_busy_cpu_holds_and_factor_zero_restores_declared_cap(self):
        self.commit(4, 8)
        r, ran = self.run_('8', {'THREAD_MEASURED_FACTOR': '0'})
        self.assertFalse(ran)
        self.assertEqual(r.returncode, 75)
        (self.d / 'state' / 'admit.log').unlink(missing_ok=True)
        self.load.write_text('9.0 9.0 9.0 1/1 1\n')
        env = dict(os.environ, PATH=f'{self.d}/bin:' + os.environ['PATH'], OUT_ARGS=str(self.d / 'args'), OT_VL_JCAP='0', OT_HEAVY_SYSTEM_TOOLS='1',
                   OT_HEAVY_THREADS='8', THREAD_MEASURED_FACTOR='1.0')
        r = subprocess.run([str(self.h), '--mem', '4', '--max-wait', '1', '--', 'true'], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 75)                # load1 9 + 8 > 10: busy host still holds


    def test_child_of_an_admitted_unit_is_not_held_by_the_declared_cap(self):
        self.commit(4, 8)                                         # declared 32 > cap 10, load 1.0: a plain job at 8 threads is held (measured 9 > 6)
        r, ran = self.run_('8')
        self.assertFalse(ran)
        (self.d / 'state' / 'res.parentunit').write_text('parentunit 4\n')
        r, ran = self.run_('8', {'OT_HEAVY_PARENT_UNIT': 'parentunit'})
        self.assertTrue(ran, r.stderr)
        self.assertIn('child of admitted parentunit', (self.d / 'state' / 'admit.log').read_text())

    def test_child_of_a_dead_or_unnamed_parent_is_a_plain_job(self):
        self.commit(4, 8)
        r, ran = self.run_('8', {'OT_HEAVY_PARENT_UNIT': 'gone'})     # no res.gone
        self.assertFalse(ran)
        (self.d / 'state' / 'res.parentunit').write_text('parentunit 4\n')
        r, ran = self.run_('8', {'OT_HEAVY_PARENT_UNIT': 'parentunit', 'THREAD_CHILD_FACTOR': '0'})
        self.assertFalse(ran)                                          # factor 0: children obey the cap

    def test_child_still_waits_when_the_host_is_really_busy(self):
        self.commit(4, 8); (self.d / 'state' / 'res.parentunit').write_text('parentunit 4\n')
        self.load.write_text('9.0 9.0 9.0 1/1 1\n')
        env = dict(os.environ, PATH=f'{self.d}/bin:' + os.environ['PATH'], OUT_ARGS=str(self.d / 'args'), OT_VL_JCAP='0', OT_HEAVY_SYSTEM_TOOLS='1',
                   OT_HEAVY_THREADS='8', OT_HEAVY_PARENT_UNIT='parentunit')
        r = subprocess.run([str(self.h), '--mem', '4', '--max-wait', '1', '--', 'true'], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 75)                             # load1 9 + 8 > 1.5 x 10


    def test_ancestry_fallback_finds_the_parent_scope_without_the_env_token(self):
        fake = self.d / 'proc'; pid = os.getpid()
        (fake / str(pid)).mkdir(parents=True)
        (fake / str(pid) / 'cgroup').write_text('0::/user.slice/user-1000.slice/user@1000.service/app.slice/oth-parentunit.scope\n')
        (fake / str(pid) / 'status').write_text('Name:\tpytest\nPPid:\t1\n')
        self.h.write_text(self.h.read_text().replace('/proc/$_p/', f'{fake}/$_p/')); self.h.chmod(0o755)
        self.commit(4, 8)
        r, ran = self.run_('8')                                        # parent has no res.<unit> yet: plain job, held
        self.assertFalse(ran)
        (self.d / 'state' / 'res.oth-parentunit').write_text('oth-parentunit 4\n')
        r, ran = self.run_('8')                                        # no OT_HEAVY_PARENT_UNIT in the env: found through the ancestry
        self.assertTrue(ran, r.stderr)
        self.assertIn('child of admitted oth-parentunit', (self.d / 'state' / 'admit.log').read_text())


if __name__ == "__main__":
    unittest.main()

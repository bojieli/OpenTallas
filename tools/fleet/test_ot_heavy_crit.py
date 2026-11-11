"""CRIT_1101 / LOADCAP_1101 (FLOW-21, COORD 11-01 09:1x/09:2x): --crit CPU weight and the non-crit host load cap."""
import os, subprocess, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent


class Shim(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        fake = self.d / 'fake'; fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n'); fake.chmod(0o755)
        sh = self.d / 'docker'
        sh.write_text((HERE / 'ot-heavy-docker').read_text().replace('REAL=/usr/bin/docker', f'REAL={fake}')); sh.chmod(0o755)
        self.sh = sh

    def run_(self, *a, crit=False):
        env = dict(os.environ, OT_HEAVY_MEM_GB='12'); env.pop('OT_HEAVY_CPU', None); env.pop('OT_HEAVY_PRIO', None)
        if crit: env['OT_HEAVY_CPU'] = 'crit'
        return subprocess.run([str(self.sh), *a], capture_output=True, text=True, env=env).stdout.split('\n')[:-1]

    def test_crit_weight(self):
        out = self.run_('run', '--rm', 'img', 'bash', '-c', 'x', crit=True)
        self.assertIn('--cpu-shares=17600', out)
        self.assertEqual(out[-4:], ['img', 'bash', '-c', 'x'])

    def test_default_unchanged(self):
        self.assertNotIn('--cpu-shares=17600', self.run_('run', '--rm', 'img', 'bash', '-c', 'x'))

    def test_explicit_shares_kept(self):
        out = self.run_('run', '--cpu-shares', '512', 'img', crit=True)
        self.assertNotIn('--cpu-shares=17600', out); self.assertIn('512', out)


class Heavy(unittest.TestCase):
    def setUp(self):
        self.d = d = Path(tempfile.mkdtemp())
        (d / 'bin').mkdir()
        def w(name, body):
            p = d / 'bin' / name; p.write_text('#!/bin/bash\n' + body + '\n'); p.chmod(0o755); return p
        self.rec = w('reconcile', '[ "$1" = --is-die ] && exit 1; echo "OK 4 cls | need 4, available 100 GB, growth charged 0 GB"')
        self.prot = w('protect', '[ "$1" = --pid ] && { echo "$2" > "$OUT_ARGS.prot"; exit 0; }; [ -n "${DIE_TEST:-}" ]')
        w('systemd-run', 'printf "%s\\n" "$@" > "$OUT_ARGS"')
        w('nproc', 'echo 10')
        self.load = d / 'loadavg'
        s = (HERE / 'ot-heavy').read_text()
        s = s.replace('/usr/local/bin/ot-heavy-reconcile', str(self.rec)).replace('/usr/local/bin/ot-protect-die', str(self.prot))
        s = s.replace('/proc/loadavg', str(self.load)).replace('D=/var/tmp/ot-heavy', f'D={d}/state')
        s = s.replace('/etc/ot-heavy.conf', str(d / 'conf')).replace('/usr/local/lib/ot-heavy', str(d / 'nolib'))
        s = s.replace('sudo -n ' + str(self.prot), str(self.prot))
        s = s.replace('sleep 20', 'sleep 0.2').replace('sleep 5;', 'sleep 0.2;')
        self.h = d / 'ot-heavy'; self.h.write_text(s); self.h.chmod(0o755)

    def run_(self, load, crit=False, maxwait='1', mem='4', **extra):
        self.load.write_text(f'{load} 1.0 1.0 1/1 1\n')
        env = dict(os.environ, PATH=f'{self.d}/bin:' + os.environ['PATH'], OUT_ARGS=str(self.d / 'args'), OT_VL_JCAP='0',
                   OT_HEAVY_SYSTEM_TOOLS='1')
        for k in ('OT_HEAVY_CPU', 'OT_HEAVY_PRIO', 'OT_HEAVY_DIRECT', 'OT_HEAVY_THREADS', 'LOAD_GATE_FACTOR', 'LOAD_CAP_FACTOR'):
            env.pop(k, None)
        if crit: env['OT_HEAVY_CPU'] = 'crit'
        env.update(extra)
        try: (self.d / 'args').unlink()
        except FileNotFoundError: pass
        r = subprocess.run([str(self.h), '--mem', mem, '--max-wait', maxwait, '--', 'true'], capture_output=True, text=True, env=env, timeout=60)
        a = (self.d / 'args').read_text().split('\n') if (self.d / 'args').exists() else None
        return r, a

    def test_below_cap_runs_default_weight(self):
        r, a = self.run_('12.4')      # below LOADCAP (15) and LOADGATE_1110 (12.5)
        self.assertIsNotNone(a, r.stderr); self.assertNotIn('CPUWeight=1000', a)

    def test_at_cap_non_crit_waits(self):
        r, a = self.run_('15.0')
        self.assertIsNone(a); self.assertEqual(r.returncode, 75)
        self.assertIn('waiting for load', r.stderr); self.assertIn('load1 15 >= 1.5 x 10 = 15', r.stderr)

    def test_crit_bypasses_cap_and_gets_weight(self):
        # crit passes LOADCAP_1101 (15 here) but not LOADGATE_1110 (1.25 x 10 = 12.5): conf cap 1.0 -> 10 <= 12 < 12.5
        (self.d / 'conf').write_text('LOAD_CAP_FACTOR=1.0\n')
        r, a = self.run_('12', crit=True)
        self.assertIsNotNone(a, r.stderr); self.assertIn('CPUWeight=1000', a)
        r, a = self.run_('12')
        self.assertIsNone(a); self.assertIn('load cap', r.stderr)

    # LOADGATE_1110 (KW-FIX-44, COORD 11-10: epyc8 load1 507 on 96 threads; crit + direct FTRES-FIX runs admitted at any load)
    def test_gate_holds_crit(self):
        r, a = self.run_('500', crit=True)
        self.assertIsNone(a); self.assertEqual(r.returncode, 75)
        self.assertIn('waiting for load', r.stderr); self.assertIn('load gate: load1 500.0', r.stderr)
        self.assertIn('1.25 x 10 = 12', r.stderr)

    def test_gate_holds_direct_and_drops_its_record(self):
        r, a = self.run_('500', crit=True, OT_HEAVY_DIRECT='1')
        self.assertIsNone(a); self.assertIn('load gate', r.stderr)
        self.assertEqual(list((self.d / 'state').glob('direct.*')), [])

    def test_gate_holds_short_pool_and_frees_the_slot(self):
        r, a = self.run_('500', OT_HEAVY_THREADS='2')
        self.assertIsNone(a); self.assertIn('load gate', r.stderr)
        r, a = self.run_('1', OT_HEAVY_THREADS='2')       # the lease was released: the next short stage gets slot 1
        self.assertIsNotNone(a, r.stderr)

    def test_fresh_admits_count_before_load1_shows_them(self):
        import time
        st = self.d / 'state'; st.mkdir(exist_ok=True)
        (st / 'thr.u1').write_text('8\n'); (st / 'thr.u2').write_text('8\n')
        old = st / 'thr.u0'; old.write_text('64\n'); t = time.time() - 400; os.utime(old, (t, t))
        r, a = self.run_('0.5', crit=True)               # 0.5 + 16 >= 12.5
        self.assertIsNone(a); self.assertIn('fresh admits 16 threads', r.stderr)
        self.assertFalse(old.exists())                   # older than LOAD_FRESH_S (300 s): dropped, not counted
        (st / 'thr.u2').unlink()
        r, a = self.run_('0.5', crit=True, OT_HEAVY_THREADS='6')   # 0.5 + 8 < 12.5
        self.assertIsNotNone(a, r.stderr)
        units = [p for p in st.glob('thr.*') if p.name != 'thr.u1']
        self.assertEqual([p.read_text().strip() for p in units], ['6'])   # the admitted job counts as fresh load

    def test_gate_factor_from_conf_and_off(self):
        (self.d / 'conf').write_text('LOAD_CAP_FACTOR=0\nLOAD_GATE_FACTOR=2\n')
        r, a = self.run_('19', crit=True)
        self.assertIsNotNone(a, r.stderr)
        r, a = self.run_('20', crit=True)
        self.assertIsNone(a)
        (self.d / 'conf').write_text('LOAD_CAP_FACTOR=0\nLOAD_GATE_FACTOR=0\n')
        r, a = self.run_('500', crit=True)
        self.assertIsNotNone(a, r.stderr)

    def test_die_job_is_protected(self):
        # DIE_WATCHDOG_1021 restored (FLOW-21 11-01): a host-classified die job gets ot-protect-die --pid before its scope
        os.environ['DIE_TEST'] = '1'
        try:
            r, a = self.run_('1', crit=True)
        finally:
            os.environ.pop('DIE_TEST', None)
        self.assertIsNotNone(a, r.stderr)
        self.assertTrue((self.d / 'args.prot').exists(), r.stderr)

    def test_non_die_not_protected(self):
        r, a = self.run_('1')
        self.assertIsNotNone(a, r.stderr)
        self.assertFalse((self.d / 'args.prot').exists())

    def test_cap_disabled(self):
        (self.d / 'conf').write_text('LOAD_CAP_FACTOR=0\n')
        r, a = self.run_('12')
        self.assertIsNotNone(a, r.stderr)


class Run(unittest.TestCase):
    def test_crit_env(self):
        import importlib.machinery, importlib.util
        ld = importlib.machinery.SourceFileLoader('otrun_crit', str(HERE / 'ot-run'))
        m = importlib.util.module_from_spec(importlib.util.spec_from_loader('otrun_crit', ld)); ld.exec_module(m)
        old = os.environ.pop('OT_RUN_CRIT', None)
        try:
            self.assertFalse(m.crit_job())
            os.environ['OT_RUN_CRIT'] = '1'; self.assertTrue(m.crit_job())
        finally:
            os.environ.pop('OT_RUN_CRIT', None)
            if old is not None: os.environ['OT_RUN_CRIT'] = old
        self.assertIn('elif o == "--crit": os.environ["OT_RUN_CRIT"] = "1"', (HERE / 'ot-run').read_text())
        self.assertIn('("OT_HEAVY_CPU=crit " if crit_job() else "")', (HERE / 'ot-run').read_text())


if __name__ == '__main__':
    unittest.main()

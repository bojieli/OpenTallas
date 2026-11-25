"""LOADCAP_FRESH_1125 (FLEET-ADMIT-CAP, COORD 11-25 02:4x: epyc11 load 169-236 on 96 cores against LOAD_CAP_FACTOR 1.2).
The admission load cap compares load1 + the declared threads of jobs admitted in the last LOAD_CAP_FRESH_S + this job's threads with
LOAD_CAP_FACTOR x (nproc - DIE_SLICE_CORES); a non-die job over it waits (exit 75 at --max-wait), die class never waits.  nproc is 10 here: cap 12."""
import os, subprocess, time
import test_ot_heavy_crit as T


class LoadCap(T.unittest.TestCase):
    setUp = T.Heavy.setUp

    def go(self, load, threads='8', prio=None, crit=False, short=False, conf=None, mem='4'):
        (self.d / 'conf').write_text('LOAD_GATE_FACTOR=0\nLOAD_CAP_FACTOR=1.2\n' + ('' if short else 'OT_HEAVY_SHORT_POOL=0\n') + (conf or ''))
        self.load.write_text(f'{load} 1.0 1.0 1/1 1\n')
        env = dict(os.environ, PATH=f'{self.d}/bin:' + os.environ['PATH'], OUT_ARGS=str(self.d / 'args'), OT_VL_JCAP='0',
                   OT_HEAVY_SYSTEM_TOOLS='1', OT_HEAVY_THREADS=threads)
        for k in ('OT_HEAVY_CPU', 'OT_HEAVY_PRIO', 'OT_HEAVY_CONF', 'OT_HEAVY_DIRECT'):
            env.pop(k, None)
        if prio: env['OT_HEAVY_PRIO'] = prio
        if crit: env['OT_HEAVY_CPU'] = 'crit'
        for f in ('args', 'args.sudo'):
            try: (self.d / f).unlink()
            except FileNotFoundError: pass
        r = subprocess.run([str(self.h), '--mem', mem, '--max-wait', '1', '--', 'true'], capture_output=True, text=True, env=env, timeout=60)
        return r, (self.d / 'args').exists()

    def fresh(self, n, threads=8, age=0):
        st = self.d / 'state'; st.mkdir(exist_ok=True)
        for i in range(n):
            p = st / f'thr.burst{i}'; p.write_text(f'{threads}\n')
            t = time.time() - age; os.utime(p, (t, t))

    def test_below_cap_admits_and_records_its_threads(self):
        r, ran = self.go('3'); self.assertTrue(ran, r.stderr)
        self.assertEqual(len(list((self.d / 'state').glob('thr.oth-*'))), 1)

    def test_load1_plus_own_threads_over_cap_waits(self):    # 5 + 8 = 13 > 12
        r, ran = self.go('5'); self.assertFalse(ran); self.assertEqual(r.returncode, 75)
        self.assertIn('load cap: load1 5 + fresh admits 0 threads + this job 8 = 13 > 1.2 x 10 = 12', r.stderr)

    def test_burst_of_fresh_admits_is_counted_before_load1_shows_it(self):    # the 09:22-09:25 epyc11 burst: load1 still 1
        self.fresh(3)
        r, ran = self.go('1'); self.assertFalse(ran); self.assertEqual(r.returncode, 75)
        self.assertIn('fresh admits 24 threads', r.stderr)

    def test_stale_admits_are_not_counted(self):
        self.fresh(3, age=600)
        r, ran = self.go('1'); self.assertTrue(ran, r.stderr)

    def test_idle_host_always_takes_one_job(self):
        r, ran = self.go('0', threads='64'); self.assertTrue(ran, r.stderr)

    def test_die_class_never_waits(self):
        self.fresh(3)
        r, ran = self.go('500', prio='die'); self.assertTrue(ran, r.stderr)
        r, ran = self.go('500', prio='plan'); self.assertTrue(ran, r.stderr)

    def test_short_pool_stage_keeps_its_bounded_slot_pool(self):    # unchanged 11-02 rule: <= 2 threads, <= 10 GB
        r, ran = self.go('500', threads='2', short=True); self.assertTrue(ran, r.stderr)
        r, ran = self.go('500', threads='8', short=True); self.assertFalse(ran)

    def test_crit_kit_waits_only_above_the_crit_ceiling(self):    # ceiling 2.0 x 10 = 20
        r, ran = self.go('500', crit=True); self.assertFalse(ran); self.assertIn('crit ceiling', r.stderr)
        r, ran = self.go('5', crit=True); self.assertTrue(ran, r.stderr)
        r, ran = self.go('500', crit=True, conf='LOAD_CAP_CRIT_FACTOR=0\n'); self.assertTrue(ran, r.stderr)

    def test_die_slice_cores_are_not_for_kits(self):    # nproc 10 - 5 = 5 cores x 1.2 = 6
        r, ran = self.go('0.1', conf='DIE_SLICE_CORES=5\n'); self.assertFalse(ran)
        r, ran = self.go('0.1'); self.assertTrue(ran, r.stderr)

    def test_factor_zero_disables(self):
        r, ran = self.go('500', conf='LOAD_CAP_FACTOR=0\n'); self.assertTrue(ran, r.stderr)

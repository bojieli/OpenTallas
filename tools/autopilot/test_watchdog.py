#!/usr/bin/env python3
"""tests for watchdog.py (hung-job watchdog, OWNER 12.22 item 1): fake job dirs + fake stall_watch rows, no fleet access"""
import json, os, sys, tempfile, time, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import watchdog as wd  # noqa: E402

H = 3600


def row(**kw):
    r = {'host': 'epyc2', 'kind': 'ot-run', 'id': 'oth-ubuntu-1-2.scope [drt-x-1]', 'lane': 'QC-SU-LAT', 'dir': 'qc',
         'stage': '5_2_route.tmp', 'drt': True, 'idle_s': 3 * H, 'age_s': 10 * H,
         'log': '/srv/opentallas-scratch2/claude/qc-su-lat/k/run/logs/asap7/d/base/5_2_route.tmp.log',
         'run': '/srv/opentallas-scratch2/claude/qc-su-lat/k', 'last': 'elapsed time = 39:51:12', 'note': '',
         'cmd': '/usr/bin/docker run --name drt-x-1 ...', 'verdict': 'STALLED'}
    r.update(kw)
    return r


VERIFY_OK = {'ok': True, 'log_mtime': time.time() - 3 * H, 'tail': '[INFO DRT-0195] Start 3rd optimization iteration.',
             'unit_alive': True, 'argv': ['bash', '/srv/opentallas-scratch2/claude/qc-su-lat/k/run.sh'], 'cwd': '/srv/x', 'mem_gb': 56,
             'env': ['PATH=/usr/bin', 'SSH_CLIENT=1', 'FOO=a b'], 'openroad': True, 'procs': ['openroad -exit x.tcl']}


class StepTest(unittest.TestCase):
    def test_orfs_stages(self):
        self.assertEqual(wd.step_of('5_2_route.tmp', '', ''), 'DRT')
        self.assertEqual(wd.step_of('5_1_grt', '', ''), 'GRT')
        self.assertEqual(wd.step_of('4_1_cts', '', ''), 'CTS')
        self.assertEqual(wd.step_of('3_3_place_gp', '', ''), 'PLACE')
        self.assertEqual(wd.step_of('1_2_yosys', '', ''), 'SYNTH')
        self.assertIsNone(wd.step_of('2_1_floorplan', '', ''))

    def test_custom_script_tail(self):
        self.assertEqual(wd.step_of('-', '/x/die_grt.log', '[INFO GRT-0101] Running extra iterations'), 'GRT')
        self.assertEqual(wd.step_of('-', '/x/eco.log', '[INFO DPL-0001] Placed 3 instances'), 'PLACE')
        self.assertEqual(wd.step_of('-', '/x/lec.log', 'miter cones'), 'LEC')
        self.assertEqual(wd.step_of('5_2_route', '/k/lec/hyp3_failed.txt', ''), 'LEC')
        self.assertEqual(wd.step_of('-', '/k/out.txt', '', ['123 python3 -I /work/lec.py']), 'LEC')
        # a wrapper naming lec.py is not LEC: DRT in the kit's own container (ot_hgi_coll_gq_land dry run 11-03)
        self.assertEqual(wd.step_of('-', '/k/run_finish.log', 'Completing 30% DRT-0199',
                                    ['1 bash -c bash run_kit.sh; python3 /work/lec.py', '2 /tools/openroad -exit x']), 'DRT')
        self.assertEqual(wd.step_of('-', '/k/gen_lint_yosys.log', ''), 'SYNTH')
        self.assertEqual(wd.step_of('-', '/k/x.txt', '', ['9 /tools/yosys -v 3']), 'SYNTH')
        self.assertIsNone(wd.step_of('-', '/x/sta.log', 'report_checks'))


class ClassifyTest(unittest.TestCase):
    def test_hung_drt_acts(self):
        self.assertEqual(wd.classify(row(), {}, [], 120)[0], 'ACT')

    def test_young_idle_ignored(self):
        self.assertIsNone(wd.classify(row(idle_s=1.5 * H), {}, [], 120))

    def test_codex_report_only(self):
        c = wd.classify(row(lane='CODEX', run='/srv/opentallas-scratch2/claude/codex-hbm/x'), {}, [], 120)
        self.assertEqual(c[0], 'REPORT')
        self.assertIn('Codex', c[2])

    def test_deleted_and_synth_report(self):
        self.assertEqual(wd.classify(row(run='/srv/a/k (deleted)'), {}, [], 120)[0], 'REPORT')
        self.assertEqual(wd.classify(row(stage='2_1_floorplan'), {}, [], 120)[0], 'REPORT')
        self.assertEqual(wd.classify(row(log='-'), {}, [], 120)[0], 'REPORT')

    def test_skip_list(self):
        self.assertEqual(wd.classify(row(), {}, ['qc-su-lat/k'], 120)[0], 'REPORT')

    def test_stop_only(self):
        self.assertEqual(wd.classify(row(), {}, ['stop-only qc-su-lat/'], 120)[0], 'STOP')

    def test_second_hang_is_fix(self):
        st = {wd.kit_key(row()): {'relaunches': [{'at': '2026-10-30 19:13 PDT'}]}}
        self.assertEqual(wd.classify(row(), st, [], 120)[0], 'FIX')


class WaveClassifyTest(unittest.TestCase):
    W = '/srv/opentallas-scratch2/claude/codex-s81-wave-1345/kit-wave/s81/b1a/items/t6/attempt_8/gen/t6'

    def test_codex_wave_root_is_a_normal_wave_job(self):
        c = wd.classify(row(lane='CODEX', run=self.W, log=self.W + '/run/logs/asap7/t6/base/3_3_place_gp.log', stage='3_3_place_gp',
                            wave_paths=[self.W]), {}, [], 120)
        self.assertEqual(c[:2], ('STOP', 'PLACE'))
        self.assertIn('kit-wave client', c[2])

    def test_hand_codex_stays_report(self):
        c = wd.classify(row(lane='CODEX', run='/srv/opentallas-scratch2/claude/codex-s81-vs8-1131', wave_paths=['/srv/opentallas-scratch2/claude/codex-s81-vs8-1131']), {}, [], 120)
        self.assertEqual(c[0], 'REPORT')
        self.assertIn('Codex', c[2])

    def test_lane_job_also_writing_elsewhere_has_no_wave_identity(self):
        self.assertIsNone(wd.job_wave(row(wave_paths=[self.W, '/srv/opentallas-scratch2/claude/hbm60-lec/out'])))
        self.assertIsNone(wd.job_wave(row(wave_paths=[])))
        self.assertEqual(wd.job_wave(row(wave_paths=[self.W]))[2], 't6')

    def test_hung_lec_and_synth_stop_no_relaunch(self):
        self.assertEqual(wd.classify(row(log='/srv/k/lec/raw_gate_16.aig', stage='-'), {}, [], 120)[:2], ('STOP', 'LEC'))
        self.assertEqual(wd.classify(row(stage='1_2_yosys'), {}, [], 120)[:2], ('STOP', 'SYNTH'))

    def test_limit(self):
        self.assertEqual(wd.silent_limit_s(61 * H, 25), 3 * 61 * H / 25)   # die GRT, it 25 after 61 h: 7.3 h
        self.assertEqual(wd.silent_limit_s(20 * H, 200), 6 * H)              # DRT with many early lines (prd-bf-v1 dry run 11-03)
        self.assertEqual(wd.silent_limit_s(40 * H, 1), 12 * H)
        self.assertEqual(wd.silent_limit_s(40 * H, 0), 12 * H)
        self.assertEqual(wd.silent_limit_s(None, 5), 12 * H)

    def test_duplicates_stop_only_a_client_less_older_job(self):
        a, b, c = row(id='old', age_s=50 * H, work=['/k'], client_gone=True), row(id='new', host='intel1', age_s=2 * H, work=['/k']), row(id='solo', work=['/j'])
        d = wd.duplicates([a, b, c], {})
        self.assertEqual(list(d), [id(a)])
        self.assertTrue(d[id(a)][0])
        self.assertIn('new', d[id(a)][1])
        self.assertEqual(wd.duplicates([a, b], {id(a): ('STOP', 'x')}), {})
        a2 = dict(a, client_gone=False)
        self.assertFalse(wd.duplicates([a2, b], {})[id(a2)][0])


class ScriptTest(unittest.TestCase):
    def test_unit_relaunch_same_command(self):
        s = wd.relaunch_script(VERIFY_OK, 'oth-u-1.scope', ['c1'], '10301913')
        self.assertIn('/usr/local/bin/ot-heavy --mem 56 -- bash /srv/opentallas-scratch2/claude/qc-su-lat/k/run.sh', s)
        self.assertIn("'FOO=a b'", s)
        self.assertNotIn('SSH_CLIENT', s)
        self.assertTrue(s.startswith('cd /srv/x && { setsid nohup env -i'))
        self.assertTrue(s.endswith(' < /dev/null & }'))

    def test_unit_relaunch_detaches_from_caller(self):
        # 10-30 20:33 epyc2 hubne relaunch held ssh 300 s (TimeoutExpired, tick state lost): the shell must return at once
        import subprocess, tempfile, time
        d = tempfile.mkdtemp()
        v = dict(VERIFY_OK, cwd=d, argv=['sleep', '5'], env=[])
        s = wd.relaunch_script(v, 'oth-u-1.scope', [], 't').replace('/usr/local/bin/ot-heavy --mem 56 -- ', '')
        t0 = time.time()
        subprocess.run(['bash', '-c', s], capture_output=True, text=True, timeout=20)
        self.assertLess(time.time() - t0, 3)

    def test_ssh_timeout_returns_rc(self):
        rc, msg = wd.ssh_sh('localhost', 'sleep 5', timeout=1)
        self.assertEqual(rc, 124)

    def test_driver_command_not_relaunched(self):
        v = dict(VERIFY_OK, cwd='/srv/die-ci/wt', argv=['bash', '-lc', 'python3 tools/die_plan/die_ci.py run --g2 all --out /srv/die-ci/results'])
        self.assertFalse(wd.names_kit(v, 'epyc2:/srv/die-ci/results/x/work/hbm/g2/part_q_su01/grt.log'))
        self.assertTrue(wd.names_kit(VERIFY_OK, 'epyc2:/srv/opentallas-scratch2/claude/qc-su-lat/k'))
        self.assertTrue(wd.names_kit(dict(VERIFY_OK, cwd='/srv/q/kits', argv=['make']), 'h:/srv/q/kits/f4a'))

    def test_unit_relaunch_needs_argv(self):
        self.assertIsNone(wd.relaunch_script(dict(VERIFY_OK, argv=None), 'oth-u-1.scope', [], 't'))

    def test_docker_relaunch_from_inspect(self):
        ins = {'Name': '/probe-1', 'HostConfig': {'AutoRemove': True, 'Memory': 8 << 30, 'NanoCpus': 8e9},
               'Config': {'Image': 'openroad/orfs:v1', 'Env': ['A=1'], 'WorkingDir': '/work', 'User': '1000:1000',
                          'Entrypoint': ['bash', '-c'], 'Cmd': ['make do-5_2_route']},
               'Mounts': [{'Type': 'bind', 'Source': '/srv/k', 'Destination': '/work', 'RW': True}]}
        s = wd.relaunch_script({'inspect': ins}, None, ['probe-1'], 't')
        self.assertIn('docker run -d --name probe-1 --rm --memory 8589934592b --cpus 8', s)
        self.assertIn('-v /srv/k:/work', s)
        self.assertTrue(s.endswith("--entrypoint bash openroad/orfs:v1 -c 'make do-5_2_route'"))

    def test_stop_exact_handles_only(self):
        s = wd.stop_script('oth-u-1.scope', ['c1'])
        self.assertIn('systemctl --user stop oth-u-1.scope', s)
        self.assertIn('docker stop -t 30 c1', s)
        self.assertNotIn('pkill', s)

    def test_handles(self):
        self.assertEqual(wd.job_handles(row()), ('oth-ubuntu-1-2.scope', ['drt-x-1']))
        self.assertEqual(wd.job_handles(row(kind='docker', id='probe-1')), (None, ['probe-1']))


class VerifyFakeDirTest(unittest.TestCase):
    def one(self, cs=0, **job):
        job.setdefault('unit', None); job.setdefault('containers', [])
        return wd.ssh_py('localhost', wd.VERIFY, {'jobs': [job], 'cpu_sample_s': cs})[0]

    def test_verify_reads_fake_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, 'run/logs/asap7/x/base/5_1_grt.log')
            os.makedirs(os.path.dirname(log))
            with open(log, 'w') as f:
                f.write('[INFO GRT-0101] Running extra iterations to remove overflow.\n[INFO GRT-0102] Start extra iteration 7/50\n'
                        '[INFO DRT-0199]   Completing 10% with 3 violations.\n')
            old = time.time() - 4 * H
            os.utime(log, (old, old))
            v = self.one(log=log)
            self.assertAlmostEqual(v['log_mtime'], old, delta=2)
            self.assertIn('GRT-0101', v['tail'])
            self.assertEqual(v['progress_n'], 2)
            self.assertFalse(v['openroad'])

    def _maxwire(self, text):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, 'run_route.log')
            with open(log, 'w') as f:
                f.write(text)
            return self.one(log=log)['maxwire']

    def test_verify_maxwire_open_until_end_marker(self):
        self.assertTrue(self._maxwire('OT_MAXWIRE repair_design -verbose -max_wire_length 100\n  1000 | +0.5%\n'))
        self.assertFalse(self._maxwire('OT_MAXWIRE repair_design -verbose\n  1000 |\nOT_MAXWIRE leaf instances 5 -> 6\nnext\n'))
        self.assertFalse(self._maxwire('[INFO GRT-0101] no marker\n'))

    def test_batch_keeps_order_and_shares_one_sample(self):
        with tempfile.TemporaryDirectory() as d:
            logs = [os.path.join(d, '%d.log' % i) for i in range(5)]
            for l in logs:
                open(l, 'w').write(l)
            t0 = time.time()
            res = wd.ssh_py('localhost', wd.VERIFY, {'jobs': [{'log': l, 'unit': None, 'containers': [], 'sample': True} for l in logs],
                                                     'cpu_sample_s': 1})
            self.assertEqual([r['tail'] for r in res], logs)
            self.assertLess(time.time() - t0, 5)

    def test_verify_cpu_sample_without_openroad_is_absent(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, 'x.log'); open(log, 'w').write('GRT-0101\n')
            self.assertNotIn('cpu_delta_s', self.one(cs=1, log=log, sample=True))

    def test_verify_no_process_no_sleep(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, 'x.log'); open(log, 'w').write('x\n')
            t = time.time()
            self.one(cs=30, log=log, sample=False)
            self.assertLess(time.time() - t, 20)

    def test_verify_cpu_sample_counts_busy_process(self):
        import subprocess
        busy = subprocess.Popen([sys.executable, '-c', 'import time\nt=time.time()\nwhile time.time()-t<20: pass'])
        try:
            ns = {}
            src = wd.VERIFY.split('def cpu_s(pids):')[1].split('PROGRESS =')[0]
            exec('import os\ndef cpu_s(pids):' + src, ns)
            c0 = ns['cpu_s']([busy.pid]); time.sleep(2); c1 = ns['cpu_s']([busy.pid])
            self.assertGreater(c1 - c0, 1.0)
            self.assertIsNone(ns['cpu_s']([999999999]))
        finally:
            busy.kill()


class MainTest(unittest.TestCase):
    def setUp(self):
        self._orig = (wd.ssh_py, wd.ssh_sh)

    def tearDown(self):
        wd.ssh_py, wd.ssh_sh = self._orig

    def run_main(self, rows, verify, act, coord):
        calls = []
        wd.ssh_py = lambda host, script, args, timeout=120: [verify for _ in args['jobs']]
        wd.ssh_sh = lambda host, sh, timeout=300: (calls.append((host, sh)), (0, ''))[1]
        p = os.path.join(coord, 'rows.json')
        json.dump(rows, open(p, 'w'))
        wd.main(['--rows', p, '--coord', coord] + (['--act'] if act else []))
        return calls

    def test_dry_run_touches_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([row()], VERIFY_OK, False, d)
            self.assertEqual(calls, [])
            self.assertFalse(os.path.exists(os.path.join(d, 'autopilot', 'WATCHDOG.state.json')))

    def test_act_once_then_fix(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'lanes'))
            open(os.path.join(d, 'lanes', 'QC-SU-LAT.md'), 'w').close()
            calls = self.run_main([row()], VERIFY_OK, True, d)
            self.assertEqual(len(calls), 2)  # stop, relaunch
            self.assertIn('systemctl --user stop oth-ubuntu-1-2.scope', calls[0][1])
            self.assertIn('ot-heavy --mem 56 -- bash /srv/opentallas-scratch2/claude/qc-su-lat/k/run.sh', calls[1][1])
            st = json.load(open(os.path.join(d, 'autopilot', 'WATCHDOG.state.json')))
            self.assertEqual(len(st[wd.kit_key(row())]['relaunches']), 1)
            # the relaunched kit hangs again: stop only, FIX lines, no third launch
            calls = self.run_main([row(id='oth-ubuntu-9-9.scope [drt-x-9]')], VERIFY_OK, True, d)
            self.assertEqual(len(calls), 1)
            self.assertIn('stop oth-ubuntu-9-9.scope', calls[0][1])
            q = open(os.path.join(d, 'lanes', 'COORD-REVIEW-QUEUE.md')).read()
            self.assertIn('FIX [WATCHDOG', q)
            self.assertIn('FIX [WATCHDOG', open(os.path.join(d, 'lanes', 'QC-SU-LAT.md')).read())
            log = open(os.path.join(d, 'autopilot', 'WATCHDOG.log')).read()
            self.assertIn('RELAUNCH', log)
            self.assertIn('FIX', log)

    def test_stop_only_never_relaunches(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'autopilot'))
            open(os.path.join(d, 'autopilot', 'WATCHDOG.skip'), 'w').write('stop-only qc-su-lat/  # 12.22 item 4\n')
            calls = self.run_main([row()], VERIFY_OK, True, d)
            self.assertEqual(len(calls), 1)
            self.assertIn('systemctl --user stop', calls[0][1])

    def test_fresh_log_at_recheck_not_acted(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([row()], dict(VERIFY_OK, log_mtime=time.time() - 60), True, d)
            self.assertEqual(calls, [])

    def test_grt_cpu_advancing_reported_not_stopped(self):
        # DIE-HBM-57 11-01: single-thread FastRoute silent > 2 h per late iteration while at 100% CPU
        with tempfile.TemporaryDirectory() as d:
            for stage in ('5_1_grt', '5_2_route.tmp'):
                calls = self.run_main([row(stage=stage)], dict(VERIFY_OK, cpu_delta_s=59.5, cpu_pids=[42]), True, d)
                self.assertEqual(calls, [])
                self.assertNotIn('RELAUNCH', open(os.path.join(d, 'autopilot', 'WATCHDOG.log')).read())

    def test_grt_cpu_flat_still_acted(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([row(stage='5_1_grt')], dict(VERIFY_OK, cpu_delta_s=0.4, cpu_pids=[42]), True, d)
            self.assertEqual(len(calls), 2)  # stop, relaunch: the old rule

    def test_cpu_probe_missing_keeps_old_rule(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([row(stage='5_1_grt')], dict(VERIFY_OK, cpu_error='no pid'), True, d)
            self.assertEqual(len(calls), 2)

    def test_cpu_sample_requested_for_grt_and_place(self):
        seen = []
        wd.ssh_py = lambda host, script, args, timeout=120: (seen.append((args, timeout)), [dict(VERIFY_OK, log_mtime=time.time()) for _ in args['jobs']])[1]
        wd.ssh_sh = lambda host, sh, timeout=300: (0, '')
        with tempfile.TemporaryDirectory() as d:
            for st in ('5_1_grt', '3_3_place_gp'):
                p = os.path.join(d, 'rows.json')
                json.dump([row(stage=st)], open(p, 'w'))
                wd.main(['--rows', p, '--coord', d])
        self.assertEqual(seen[0][0]['cpu_sample_s'], 60)
        self.assertTrue(seen[0][0]['jobs'][0]['sample'])
        self.assertGreaterEqual(seen[0][1], 180)
        # KW-FIX-25: VERIFY gets the sample length, and sleeps only if it finds a process to sample (PLACE: only an async LEC)
        self.assertEqual(seen[1][0]['cpu_sample_s'], 60)
        self.assertTrue(seen[1][0]['jobs'][0]['sample'])     # KW-FIX-46 11-12: PLACE is sampled too

    def test_no_openroad_not_acted(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([row()], dict(VERIFY_OK, openroad=False), True, d)
            self.assertEqual(calls, [])

    def test_busy_grt_past_limit_is_not_hung(self):
        # KW-FIX-46 11-12 (COORD): hung = no log AND no CPU; a CPU-busy GRT is reported, never stopped (PHY_NC 6h18)
        with tempfile.TemporaryDirectory() as d:
            r = row(stage='5_1_grt', idle_s=13 * H, age_s=20 * H)  # past the old 12 h cap
            calls = self.run_main([r], dict(VERIFY_OK, cpu_delta_s=59.5, cpu_pids=[42], progress_n=20), True, d)
            self.assertEqual(calls, [])

    MAXWIRE_V = dict(VERIFY_OK, cpu_delta_s=59.5, cpu_pids=[42], progress_n=9)

    def _maxwire_calls(self, idle_h, stage='5_1_grt', **verify):
        with tempfile.TemporaryDirectory() as d:
            return self.run_main([row(stage=stage, idle_s=idle_h * H, age_s=idle_h * H + 5 * H)], dict(self.MAXWIRE_V, **verify), True, d)

    def test_busy_maxwire_repair_kept_between_6_and_12_h(self):
        # KW43-63: leaf t30 stopped at 6 h 02 in this step, 984 nets from the end
        self.assertEqual(self._maxwire_calls(7, maxwire=True), [])
        self.assertEqual(self._maxwire_calls(11.5, maxwire=True), [])

    def test_busy_maxwire_repair_kept_past_12_h(self):
        self.assertEqual(self._maxwire_calls(13, maxwire=True), [])     # KW-FIX-46 11-12: CPU-busy is never hung

    def test_maxwire_idle_cpu_still_stops(self):
        self.assertTrue(self._maxwire_calls(7, maxwire=True, cpu_delta_s=0.0))

    def test_other_grt_and_drt_busy_not_stopped_idle_stopped(self):
        self.assertEqual(self._maxwire_calls(7, maxwire=False), [])
        self.assertEqual(self._maxwire_calls(7, stage='5_2_route.tmp', maxwire=True), [])
        self.assertTrue(self._maxwire_calls(7, maxwire=False, cpu_delta_s=0.0))

    LEC_V = dict(VERIFY_OK, openroad=False, tool=True, tail='', procs=['123 python3 -I /work/lec.py /work', '124 /tools/yosys-abc -f x'])

    def _lec_row(self, **kw):
        return row(**dict(dict(log='/srv/k/lec/raw_gate_16.aig', stage='-'), **kw))

    def test_cpu_busy_lec_never_stopped_however_long(self):
        # KW-FIX-25: serdes__t4_vB, 8 h CPU-bound, stopped at 2h02 for a flat log (11-06 17:53)
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([self._lec_row(idle_s=40 * H, age_s=50 * H)], dict(self.LEC_V, cpu_delta_s=59.5, cpu_pids=[42]), True, d)
            self.assertEqual(calls, [])

    def test_lec_cpu_unread_not_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_main([self._lec_row()], dict(self.LEC_V, cpu_error='no pid'), True, d), [])

    def test_lec_one_abc_after_another_not_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            v = dict(self.LEC_V, cpu_delta_s=1.0, cpu_pids=[42], tool_churn=True)
            self.assertEqual(self.run_main([self._lec_row()], v, True, d), [])

    def test_lec_idle_alive_still_stopped_no_relaunch(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([self._lec_row()], dict(self.LEC_V, cpu_delta_s=0.2, cpu_pids=[42]), True, d)
            self.assertEqual(len(calls), 1)
            self.assertIn('systemctl --user stop', calls[0][1])

    def test_async_lec_beside_place_stage_log_not_stopped(self):
        # the first look says PLACE (stale ORFS stage log), the process list says LEC
        with tempfile.TemporaryDirectory() as d:
            v = dict(VERIFY_OK, openroad=False, tool=True, procs=['123 python3 -I /work/lec.py /work'], cpu_delta_s=60.0, cpu_pids=[123])
            self.assertEqual(self.run_main([row(stage='3_3_place_gp')], v, True, d), [])

    def test_lec_tool_pids_found_in_verify(self):
        ns = {'os': os}
        exec('def is_lec_tool(av):' + wd.VERIFY.split('def is_lec_tool(av):')[1].split('def or_pids')[0], ns)
        for av in (['/usr/bin/abc', '-f', 'x'], ['python3', '-I', '/work/lec.py', '/work']):
            self.assertTrue(ns['is_lec_tool'](av), av)
        for av in ([], ['bash', '-c', 'python3 /work/lec.py'], ['python3', '/work/gen.py'], ['sleep', '5']):
            self.assertFalse(ns['is_lec_tool'](av), av)

    def test_stdout_moved_not_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_main([row()], dict(VERIFY_OK, stdout_recent=True), True, d), [])

    def _wave_state(self, d, **kw):
        os.makedirs(os.path.join(d, 'autopilot'), exist_ok=True)
        r = dict(die='s81', event='e8c', item='t18', attempt=4, status='CANCELLED', block_sha='a' * 40, updated=time.time() - H, reason='x')
        r.update(kw)
        json.dump({'items': {'k': r}}, open(os.path.join(d, 'autopilot', 'kit_wave_state.json'), 'w'))

    W = '/srv/opentallas-scratch2/claude/kit-wave/s81/e8c/items/t18/attempt_4/gen/t18'

    def test_cancelled_row_stops_a_moving_log_without_relaunch(self):
        with tempfile.TemporaryDirectory() as d:
            self._wave_state(d)
            calls = self.run_main([row(idle_s=60, log=self.W + '/x.log', wave_paths=[self.W])], VERIFY_OK, True, d)
            self.assertEqual(len(calls), 1)
            self.assertIn('stop oth-ubuntu-1-2.scope', calls[0][1])

    def test_superseded_report_only_for_plan_current_no(self):
        with tempfile.TemporaryDirectory() as d:
            self._wave_state(d, status='RUNNING')
            open(os.path.join(d, 'autopilot', 'kit_wave_stages.tsv'), 'w').write(
                'die\titem\tblock_sha\tplan_current\ns81\tt18\t%s\tno\n' % ('a' * 12))
            calls = self.run_main([row(idle_s=60, log=self.W + '/x.log', wave_paths=[self.W])], VERIFY_OK, True, d)
            self.assertEqual(calls, [])

    def test_skip_blocks_a_superseded_stop(self):
        with tempfile.TemporaryDirectory() as d:
            self._wave_state(d)
            open(os.path.join(d, 'autopilot', 'WATCHDOG.skip'), 'w').write('items/t18/\n')
            r = row(idle_s=60, log=self.W + '/x.log', wave_paths=[self.W])
            self.assertEqual(self.run_main([r], VERIFY_OK, True, d), [])

    def test_older_duplicate_on_one_kit_is_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            a = row(id='oth-a.scope [dpkit-a]', idle_s=60, age_s=50 * H, log=self.W + '/x.log', wave_paths=[self.W], work=[self.W], client_gone=True)
            b = row(id='oth-b.scope [dpkit-b]', idle_s=60, age_s=2 * H, log=self.W + '/x.log', wave_paths=[self.W], work=[self.W])
            calls = self.run_main([a, b], VERIFY_OK, True, d)
            self.assertEqual(len(calls), 1)
            self.assertIn('oth-a.scope', calls[0][1])

    def test_client_owned_older_duplicate_only_reported(self):
        with tempfile.TemporaryDirectory() as d:
            a = row(id='oth-a.scope [dpkit-a]', idle_s=60, age_s=50 * H, log=self.W + '/x.log', wave_paths=[self.W], work=[self.W])
            b = row(id='oth-b.scope [dpkit-b]', idle_s=60, age_s=2 * H, log=self.W + '/x.log', wave_paths=[self.W], work=[self.W], client_gone=True)
            self.assertEqual(self.run_main([a, b], VERIFY_OK, True, d), [])

    def test_stop_cap(self):
        with tempfile.TemporaryDirectory() as d:
            self._wave_state(d)
            calls = []
            wd.ssh_sh = lambda host, sh, timeout=300: (calls.append(sh), (0, ''))[1]
            rows = [row(id='oth-%d.scope [c%d]' % (i, i), idle_s=60, log=self.W + '/x.log', wave_paths=[self.W]) for i in range(3)]
            p = os.path.join(d, 'rows.json'); json.dump(rows, open(p, 'w'))
            wd.main(['--rows', p, '--coord', d, '--act', '--max-stops', '2'])
            self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()


class SealedOtJobTest(unittest.TestCase):
    def test_sealed_ot_job_is_stop_not_relaunch(self):
        c = wd.classify(row(run='/srv/opentallas-scratch2/claude/ot-jobs/PHY_NC-route-aware-parakeet-3317157-1794474529/work'),
                        {}, [], 120)
        self.assertEqual(c[0], 'STOP')
        self.assertIn('sealed ot-job', c[2])


class CpuBusyIsNotHungTest(unittest.TestCase):
    """KW-FIX-46 11-12: PHY_NC GRT 6h18 silent, container 12h48m CPU in 12h wall, was stopped by the busy cap"""

    def test_busy_grt_past_every_limit_is_report(self):
        H = 3600
        r = wd.cpu_busy_reason('GRT', 59.0, 30, 60, 6.3 * H, wd.BUSY_MIN_S, [123], 23)
        self.assertIsNotNone(r)
        self.assertIn('not stopped', r)
        self.assertIn('silent past', r)
        self.assertIsNotNone(wd.cpu_busy_reason('GRT', 59.0, 30, 60, 30 * H, wd.BUSY_CAP_S))

    def test_no_cpu_progress_or_unread_is_not_busy(self):
        self.assertIsNone(wd.cpu_busy_reason('GRT', 2.0, 30, 60, 3 * 3600, wd.BUSY_MIN_S))
        self.assertIsNone(wd.cpu_busy_reason('GRT', None, 30, 60, 3 * 3600, wd.BUSY_MIN_S))
        self.assertIsNone(wd.cpu_busy_reason('GRT', 59.0, 30, 0, 3 * 3600, wd.BUSY_MIN_S))

    def test_place_cts_count_cpu_too(self):
        self.assertIsNotNone(wd.cpu_busy_reason('PLACE', 59.0, 30, 60, 3 * 3600, wd.BUSY_MIN_S))
        self.assertIsNotNone(wd.cpu_busy_reason('CTS', 59.0, 30, 60, 3 * 3600, wd.BUSY_MIN_S))
        self.assertIsNone(wd.cpu_busy_reason(None, 59.0, 30, 60, 3 * 3600, wd.BUSY_MIN_S))

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
        self.assertIsNone(wd.step_of('1_2_yosys', '', ''))
        self.assertIsNone(wd.step_of('2_1_floorplan', '', ''))

    def test_custom_script_tail(self):
        self.assertEqual(wd.step_of('-', '/x/die_grt.log', '[INFO GRT-0101] Running extra iterations'), 'GRT')
        self.assertEqual(wd.step_of('-', '/x/eco.log', '[INFO DPL-0001] Placed 3 instances'), 'PLACE')
        self.assertIsNone(wd.step_of('-', '/x/lec.log', 'miter cones'))


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
        self.assertEqual(wd.classify(row(stage='1_2_yosys'), {}, [], 120)[0], 'REPORT')
        self.assertEqual(wd.classify(row(log='-'), {}, [], 120)[0], 'REPORT')

    def test_skip_list(self):
        self.assertEqual(wd.classify(row(), {}, ['qc-su-lat/k'], 120)[0], 'REPORT')

    def test_stop_only(self):
        self.assertEqual(wd.classify(row(), {}, ['stop-only qc-su-lat/'], 120)[0], 'STOP')

    def test_second_hang_is_fix(self):
        st = {wd.kit_key(row()): {'relaunches': [{'at': '2026-10-30 19:13 PDT'}]}}
        self.assertEqual(wd.classify(row(), st, [], 120)[0], 'FIX')


class ScriptTest(unittest.TestCase):
    def test_unit_relaunch_same_command(self):
        s = wd.relaunch_script(VERIFY_OK, 'oth-u-1.scope', ['c1'], '10301913')
        self.assertIn('/usr/local/bin/ot-heavy --mem 56 -- bash /srv/opentallas-scratch2/claude/qc-su-lat/k/run.sh', s)
        self.assertIn("'FOO=a b'", s)
        self.assertNotIn('SSH_CLIENT', s)
        self.assertTrue(s.startswith('cd /srv/x && setsid nohup env -i'))

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
    def test_verify_reads_fake_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, 'run/logs/asap7/x/base/5_1_grt.log')
            os.makedirs(os.path.dirname(log))
            with open(log, 'w') as f:
                f.write('[INFO GRT-0101] Running extra iterations to remove overflow.\n')
            old = time.time() - 4 * H
            os.utime(log, (old, old))
            v = wd.ssh_py('localhost', wd.VERIFY, {'log': log, 'unit': None, 'containers': []})
            self.assertAlmostEqual(v['log_mtime'], old, delta=2)
            self.assertIn('GRT-0101', v['tail'])
            self.assertFalse(v['openroad'])


class MainTest(unittest.TestCase):
    def setUp(self):
        self._orig = (wd.ssh_py, wd.ssh_sh)

    def tearDown(self):
        wd.ssh_py, wd.ssh_sh = self._orig

    def run_main(self, rows, verify, act, coord):
        calls = []
        wd.ssh_py = lambda host, script, args, timeout=120: verify
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

    def test_no_openroad_not_acted(self):
        with tempfile.TemporaryDirectory() as d:
            calls = self.run_main([row()], dict(VERIFY_OK, openroad=False), True, d)
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()

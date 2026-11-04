#!/usr/bin/env python3
"""tests for wave_jobs.py and the cancel / resubmit paths of WATCHDOG-1 (HUNG-1103); fake rows, no fleet access"""
import json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW  # noqa: E402
import wave_jobs as WJ  # noqa: E402

P = '/srv/opentallas-scratch2/claude/kit-wave/s81/e8c/items/t18/attempt_4/gen/t18/run_route.log'


def rows(*rs):
    out = {}
    for r in rs:
        r = dict({'die': 's81', 'event': 'e8c', 'item': 't18', 'attempt': 4, 'status': 'RUNNING', 'updated': 1000.0,
                  'plan_current': 'yes'}, **r)
        out.setdefault((r['die'], r['event'], r['item']), []).append(r)
    return out


class Identity(unittest.TestCase):
    def test_paths(self):
        self.assertEqual(WJ.wave_id([P]), ('s81', 'e8c', 't18', 4))
        self.assertEqual(WJ.wave_id(['/srv/x/kit-wave/hbm/d44v/items/ot_a/gen/ot_a_12/run.log']), ('hbm', 'd44v', 'ot_a', 1))
        self.assertEqual(WJ.wave_id(['/home/ubuntu/scratch-root/claude/codex-s81-wave-1345/kit-wave/s81/b1a/items/t6__cl0/attempt_8/gen/x']),
                         ('s81', 'b1a', 't6__cl0', 8))
        self.assertIsNone(WJ.wave_id(['/srv/x/hbm60-lec/c6kit/ot', None]))


class Judge(unittest.TestCase):
    wid = ('s81', 'e8c', 't18', 4)

    def test_cancelled_stops(self):
        self.assertEqual(WJ.judge(rows(dict(status='CANCELLED')), self.wid, 500.0)[0], 'STOP')

    def test_current_running_row_keeps_job(self):
        self.assertIsNone(WJ.judge(rows({}), self.wid, 500.0))

    def test_older_than_live_current_attempt_stops(self):
        self.assertEqual(WJ.judge(rows(dict(attempt=6, started=900.0)), self.wid, 500.0)[0], 'STOP')

    def test_older_attempt_started_after_the_live_one_is_a_resume(self):
        self.assertEqual(WJ.judge(rows(dict(attempt=6, started=900.0)), self.wid, 950.0)[0], 'REPORT')

    def test_older_than_live_not_current_only_reports(self):
        self.assertEqual(WJ.judge(rows(dict(attempt=6, plan_current='no')), self.wid, 500.0)[0], 'REPORT')
        self.assertEqual(WJ.judge(rows(dict(attempt=6, plan_current='')), self.wid, 500.0)[0], 'REPORT')

    def test_enqueued_done_is_not_live(self):
        v = WJ.judge(rows(dict(attempt=6, status='ENQUEUED', q_status='DONE-CRASH')), self.wid, 500.0)
        self.assertIsNone(v)

    def test_variant_item_or_other_event_is_never_compared(self):
        self.assertIsNone(WJ.judge(rows(dict(attempt=9, item='t18__cl1')), self.wid, 500.0))
        self.assertIsNone(WJ.judge(rows(dict(attempt=9, event='other')), self.wid, 500.0))

    def test_fail_stops_only_a_job_that_predates_it(self):
        self.assertEqual(WJ.judge(rows(dict(status='FAIL')), self.wid, 500.0)[0], 'STOP')
        self.assertEqual(WJ.judge(rows(dict(status='FAIL')), self.wid, 2000.0)[0], 'REPORT')   # stage resume after the FAIL
        self.assertEqual(WJ.judge(rows(dict(status='FAIL')), self.wid, None)[0], 'REPORT')

    def test_plan_current_no_reports_only(self):
        self.assertEqual(WJ.judge(rows(dict(plan_current='no')), self.wid, 500.0)[0], 'REPORT')

    def test_exact_attempt_wins_over_other_block_row(self):
        # attempts run through the blocks of one item: 3 FAIL on the old block, 7 live on the new one
        rs = rows(dict(attempt=3, status='FAIL'), dict(attempt=7, started=900.0))
        self.assertIsNone(WJ.judge(rs, ('s81', 'e8c', 't18', 7), 500.0))
        self.assertEqual(WJ.judge(rs, ('s81', 'e8c', 't18', 3), 500.0)[0], 'STOP')

    def test_unknown_newer_attempt_and_no_row(self):
        self.assertIsNone(WJ.judge(rows({}), ('s81', 'e8c', 't18', 9), 500.0))
        self.assertIsNone(WJ.judge({}, self.wid, 500.0))
        self.assertIsNone(WJ.judge(rows({}), None, 500.0))


class LoadRows(unittest.TestCase):
    def test_join_plan_current(self):
        with tempfile.TemporaryDirectory() as d:
            json.dump({'items': {'k': {'die': 's81', 'event': 'e', 'item': 't', 'block_sha': 'a' * 40, 'status': 'FAIL'}}},
                      open(os.path.join(d, 'kit_wave_state.json'), 'w'))
            open(os.path.join(d, 'kit_wave_stages.tsv'), 'w').write(
                'die\titem\tblock_sha\tplan_current\ts81\tt\t%s\tno\n'.replace('current\ts81', 'current\ns81') % ('a' * 12))
            self.assertEqual(WJ.load_rows(d)[('s81', 'e', 't')][0]['plan_current'], 'no')
            self.assertEqual(WJ.load_rows(os.path.join(d, 'none')), {})


class StopKit(unittest.TestCase):
    def test_host_script_dry_on_no_match(self):
        # real docker if present; a root nothing mounts matches nothing and nothing is stopped
        p = subprocess.run(['python3', '-I', '-', json.dumps({'roots': ['/nonexistent/kit-wave-test'], 'dry': True})],
                           input=WJ.STOP_KIT, capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            self.assertEqual(json.loads(p.stdout), {'containers': [], 'scopes': []})

    def test_attempt_1_root_excludes_later_attempts(self):
        src = WJ.STOP_KIT.split("ids = subprocess")[0].replace("a = json.loads(sys.argv[1]); ", "")
        ns = {'a': {'roots': ['/k/items/t']}}
        exec(src.replace("roots = [r.rstrip('/') for r in a['roots']]; dry = a.get('dry')",
                         "roots = ['/k/items/t']; dry = True"), ns)
        self.assertTrue(ns['under']('/k/items/t/gen/t'))
        self.assertFalse(ns['under']('/k/items/t/attempt_2/gen/t'))
        self.assertFalse(ns['under']('/k/items/t2'))

    def test_stop_on_fleet_all_hosts_and_error(self):
        seen = []

        def sh(cmd, timeout=None, input=None):
            seen.append(cmd)
            if 'epyc4' in cmd:
                return 255, '', 'no route'
            return 0, json.dumps({'containers': ['c1'], 'scopes': []}), ''
        res = WJ.stop_on_fleet(sh, 'intel2', ['/k', '', None], hosts=['intel2', 'epyc4'])
        self.assertEqual(WJ.stopped_names(res), ['intel2:c1'])
        self.assertIn('error', res['epyc4'])
        self.assertEqual(next(c for c in seen if 'ssh' not in c)[:3], ['python3', '-I', '-'])
        self.assertEqual(WJ.stop_on_fleet(sh, 'intel2', ['']), {})

    def test_never_pkill(self):
        self.assertNotIn('pkill', WJ.STOP_KIT)


class CancelSuperseded(unittest.TestCase):
    def test_cancel_stops_remote_attempt_root(self):
        t = Path(tempfile.mkdtemp())
        (t / 'w').mkdir()
        (t / 'w' / 'spec.json').write_text(json.dumps({'work': '/srv/k/kit-wave/d/e/items/t/attempt_4'}))
        (t / 'state.json').write_text(json.dumps({'jobs': {'j1': {'status': 'RUNNING', 'unit': 'ap-j1-a1'}}}))
        remote, logs, units = [], [], []

        def sh(cmd, timeout=None, input=None):
            if input:
                remote.append(json.loads(cmd[-1].strip("'"))['roots'])
                return 0, json.dumps({'containers': ['dpkit-t-1'], 'scopes': []}), ''
            units.append(cmd[-1])
            return 0, '', ''
        AP = SimpleNamespace(DRY=False, log=logs.append, sh=sh, HUB_NAME='intel2')
        cur, old = 'a' * 40, 'b' * 40
        cfg = {'dies': {'d': {'plan': '/p', 'event': 'e', 'gen_host': 'h'}}}
        st = {'plans': {'h:/p|e': {'blocks': {'t': cur}}},
              'items': {KW.item_key('d', 'e', 't', old): dict(die='d', item='t', attempt=4, status='ENQUEUED', q_id='j1', dir=str(t / 'w'))}}
        self.assertEqual(KW.cancel_superseded(AP, cfg, st, {}, t), 1)
        self.assertEqual(units, ['ap-j1-a1'])
        self.assertEqual(len(remote), len(WJ.FLEET))
        self.assertEqual(remote[0], ['/srv/k/kit-wave/d/e/items/t/attempt_4'])
        self.assertTrue(any('remote stop' in x and 'dpkit-t-1' in x for x in logs))

    def test_dry_stops_nothing(self):
        t = Path(tempfile.mkdtemp())
        (t / 'state.json').write_text(json.dumps({'jobs': {'j1': {'status': 'RUNNING', 'unit': 'ap-j1-a1'}}}))
        calls = []
        AP = SimpleNamespace(DRY=True, log=lambda x: None, sh=lambda *a, **k: calls.append(a) or (0, '', ''), HUB_NAME='intel2')
        cfg = {'dies': {'d': {'plan': '/p', 'event': 'e', 'gen_host': 'h'}}}
        st = {'plans': {'h:/p|e': {'blocks': {'t': 'a' * 40}}},
              'items': {KW.item_key('d', 'e', 't', 'b' * 40): dict(die='d', item='t', attempt=1, status='ENQUEUED', q_id='j1', kit='h:/k')}}
        KW.cancel_superseded(AP, cfg, st, {}, t)
        self.assertEqual(calls, [])


class AutopilotResubmit(unittest.TestCase):
    """HUNG-1103: CANCEL-SUPERSEDED at 09:30 -> client lost -> CRASH infra-orphan -> resubmit at 09:34 on the same /work"""

    def setUp(self):
        import autopilot as AP
        self.AP = AP
        self.saved = {k: getattr(AP, k) for k in ('AP_DIR', 'log', 'set_status', 'submit', 'classify', 'after_class', 'launch_unit', 'stop_survivors')}
        self.t = Path(tempfile.mkdtemp())
        AP.AP_DIR = self.t
        AP.log = lambda m: None
        self.status, self.submits = [], []
        AP.set_status = lambda st, j, s, why='': self.status.append(s)
        AP.after_class = lambda st, j: None
        AP.classify = lambda c, client: ('CRASH', 'infra-orphan', 'client lost')
        self.j = {'id': 'j1', 'die': 's81', 'type': 't18', 'started': 500.0, 'mem_gb': 8, 'path': '/srv/x/kit-wave/s81/e8c/items/t18/attempt_4/gen/t18'}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(self.AP, k, v)

    def state(self, **kw):
        r = dict(die='s81', event='e8c', item='t18', attempt=4, status='CANCELLED', updated=1000.0)
        r.update(kw)
        (self.t / 'kit_wave_state.json').write_text(json.dumps({'items': {'k': r}}))

    def test_cancelled_row_is_not_resubmitted(self):
        self.state()
        self.AP.submit = lambda st, j, note='': self.submits.append(note)
        self.AP.finish({}, self.j, {}, {'orphan': True, 'msg': 'client lost'})
        self.assertEqual((self.submits, self.status), ([], ['CANCELLED']))

    def test_row_that_wants_the_job_is_resubmitted(self):
        self.state(status='ENQUEUED')
        self.AP.submit = lambda st, j, note='': self.submits.append(note)
        self.AP.finish({}, self.j, {}, {'orphan': True, 'msg': 'client lost'})
        self.assertEqual(len(self.submits), 1)

    def test_resubmit_stops_survivors_first_attempt_does_not(self):
        calls = []
        self.AP.stop_survivors = lambda j: calls.append('stop')
        self.AP.launch_unit = lambda unit, logf, argv: calls.append('launch') or True
        j = dict(self.j, runner='/r/run.sh', mem_gb=8, threads=2, goal='cts', kit='h:/k', src='s', geom='g', geom_ref='r')
        self.AP.submit({}, dict(j))
        self.assertEqual(calls, ['launch'])
        calls.clear()
        self.AP.submit({}, dict(j, attempts=1))
        self.assertEqual(calls, ['stop', 'launch'])


if __name__ == '__main__':
    unittest.main()

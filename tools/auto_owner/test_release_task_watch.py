#!/usr/bin/env python3
"""Tests for release_task_watch.py (TASK-WATCH, owner 10-19).  Run: python3 -m pytest -q tools/auto_owner/test_release_task_watch.py"""
import json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_task_watch as w          # noqa: E402
import release_tree_render as rtr       # noqa: E402

NOW = 1_800_000_000.0
TREE = """# tree
## DIE s81 · S81 · rev p4l · est. x
- [x] S81.BIND ~~Strict bind~~ · S81-DIE6 · PASS · bind9
- [ ] S81.GRT Die GRT overflow 0 · S81-DIE8 · RUNNING · p4l3 chain ot-epyc5 /srv/opentallas-scratch/claude/s81die8/case_p4l3_rv
- [ ] S81.STA Die STA TT/FF · S81-DIE8 · RUNNING · same chain
  - [ ] S81.STA.PAR Landed parents · PL-X · RUNNING · gates
    - [ ] S81.STA.PAR.1 Slice · PL-SLICE · RUNNING · gate dsdv_slice_ve-g1-0123456ab
- [ ] S81.CLK Die clock check · S81-DIE8 · WAITS · after parents → S81.STA.PAR
## TOKEN · decode
- [ ] TOK.FREEZE Record at freeze · TOKEN-PASS · WAITS · waits → S81.GRT
- [ ] TOK.DS Owner call · OWNER · OWNER · scope decision
- [ ] TOK.NEXT Next die · HN · WAITS · NEXT RELEASE (owner 10-18)
- [ ] TOK.IDLE Old work · LANE-OLD · RUNNING · nothing named
## WAITS · who
### Waiting on the coordinator
- something
"""


def mk_tasks(tree=TREE, pending=(), lane_texts=None):
    ts = [t for t in w.load_tasks(tree) if not t['checked']]
    for t in ts: t['refs'] = w.build_refs(t, lane_texts or {}, list(pending))
    return ts


def run(path, state, rc=None, t_end=None, newest=None, procs=(), primary=True, kind=2, tag=None):
    marks = [] if state not in ('OK', 'FAIL') else [dict(f='run_all.done', t=t_end, rc=rc)]
    return dict(path=path, isdir=True, mtime=newest, newest=newest or t_end or 0, marks=marks,
                procs=[list(p) for p in procs], nprocs=len(procs), hits=[[tag or path, kind]])


def evaluate(tasks, probes=None, jobs=None, hand=(), lane_mtimes=None, fleet=(), md_mtime=NOW - 7200):
    ev = w.gather(tasks, md_mtime, {}, lane_mtimes or {}, list(hand), [], jobs or {}, list(fleet), probes or {}, {}, now=NOW)
    return {r['id']: r for r in w.classify(tasks, ev, now=NOW)}


class Parse(unittest.TestCase):
    def test_open_tasks_and_tree(self):
        ts = mk_tasks()
        ids = [t['id'] for t in ts]
        self.assertNotIn('S81.BIND', ids)                     # ticked lines are not watched
        self.assertIn('S81.STA.PAR.1', ids)
        par = next(t for t in ts if t['id'] == 'S81.STA.PAR')
        self.assertEqual(par['parent'], 'S81.STA'); self.assertEqual(par['kids'], ['S81.STA.PAR.1'])
        g = {t['id']: t['gate'] for t in ts}
        self.assertTrue(g['S81.GRT']); self.assertFalse(g['S81.STA.PAR'])
        self.assertEqual(next(t for t in ts if t['id'] == 'TOK.FREEZE')['section'], 'TOKEN')

    def test_refs(self):
        r = w.refs_of('relaunched kvs14p-90dedf84f (claude/hkv-die-1019, ot-epyc5) chain_d4g2d.sh pid 769697 dv2f14bi TT -3907 '
                      '10-18 22:40 64x64 0452bc027 → Q.STA.GEN /srv/opentallas-scratch/claude/s81die8/case_p4l3_rv, lanes/S81-SLICEP.md')
        self.assertIn('kvs14p-90dedf84f', r['jobs']); self.assertIn('kvs14p-90dedf84f', r['tags'])
        self.assertIn('dv2f14bi', r['tags']); self.assertIn('chain_d4g2d.sh', r['tags'])
        self.assertNotIn('hkv-die-1019', r['tags'])           # branch
        self.assertNotIn('ot-epyc5', r['tags']); self.assertNotIn('10-18', r['tags']); self.assertNotIn('64x64', r['tags'])
        self.assertIn('0452bc027', r['hashes']); self.assertIn(769697, r['pids'])
        self.assertIn('/srv/opentallas-scratch/claude/s81die8/case_p4l3_rv', r['paths'])
        self.assertIn('Q.STA.GEN', r['ids']); self.assertIn('S81-SLICEP.md', r['lanefiles'])
        self.assertFalse(w.refs_of('/home/ubuntu/OpenTallas/tools/x.py')['paths'])

    def test_owner_lanes(self):
        self.assertEqual(w.owner_lanes('OWN-S81/SLICEPAR'), ['OWN-S81', 'SLICEPAR'])
        self.assertEqual(w.owner_lanes('QXPQ-FIX/coordinator'), ['QXPQ-FIX'])
        self.assertEqual(w.owner_lanes('H-D4G / DIE-HBM-LEAD'), ['H-D4G', 'DIE-HBM-LEAD'])
        self.assertEqual(w.owner_lanes('COORD'), [])

    def test_handoff_times(self):
        now = 1_792_400_000.0   # a fixed local time
        hl = w.handoff_lines('- [S81-DIE8] 10-19 00:07 relaunch\n- 10-19 ~01:05 (0jf) OWNER: x\nnot a line\n', now=now)
        self.assertEqual([h[0] for h in hl if h[0]], ['S81-DIE8'])
        self.assertTrue(all(h[1] for h in hl))


class RunState(unittest.TestCase):
    def test_states(self):
        self.assertEqual(w.run_state(dict(nprocs=1))[0], 'RUNNING')
        self.assertEqual(w.run_state(dict(nprocs=0, marks=[dict(t=1, rc=3)]))[:2], ('FAIL', 3))
        self.assertEqual(w.run_state(dict(nprocs=0, marks=[dict(t=1, rc=3), dict(t=2, rc=0)]))[:2], ('OK', 0))
        self.assertEqual(w.run_state(dict(nprocs=0, marks=[dict(t=1, rc=None)]))[0], 'OK')
        self.assertEqual(w.run_state(dict(nprocs=0, marks=[]))[0], 'IDLE')


class Classify(unittest.TestCase):
    P = '/srv/opentallas-scratch/claude/s81die8/case_p4l3_rv'

    def test_dead_chain_whatever_the_status(self):
        ts = mk_tasks()
        probes = {'ot-epyc5': dict(runs={self.P: run(self.P, 'FAIL', rc=3, t_end=NOW - 5 * 3600)})}
        # the owner lane was touched recently, but not about this run: still DEAD
        res = evaluate(ts, probes, lane_mtimes={})
        self.assertEqual(res['S81.GRT']['cls'], 'DEAD'); self.assertTrue(res['S81.GRT']['mismatch'])
        self.assertTrue(res['S81.GRT']['needs_agent'])
        self.assertEqual(res['S81.STA']['cls'], 'DEAD')     # 'same chain': inherits the die's gate runs
        self.assertIn('exit rc 3', res['S81.STA']['why'])

    def test_owner_reacting_after_failure_keeps_live(self):
        ts = mk_tasks()
        probes = {'ot-epyc5': dict(runs={self.P: run(self.P, 'FAIL', rc=3, t_end=NOW - 5 * 3600)})}
        hand = [('S81-DIE8', NOW - 600, '- [S81-DIE8] 10-19 00:07 S81.GRT relaunching after rc 3')]
        res = evaluate(ts, probes, hand=hand)
        self.assertEqual(res['S81.GRT']['cls'], 'LIVE'); self.assertIn('owner reacting', res['S81.GRT']['why'])
        old = [('S81-DIE8', NOW - 3 * 3600, '- [S81-DIE8] 10-18 21:00 S81.GRT note')]
        self.assertEqual(evaluate(ts, probes, hand=old)['S81.GRT']['cls'], 'DEAD')

    def test_relaunch_is_live(self):
        ts = mk_tasks()
        probes = {'ot-epyc5': dict(runs={self.P: run(self.P, 'RUNNING', newest=NOW - 7200, procs=[(11, NOW - 60, 'bash run_all.sh')])})}
        self.assertEqual(evaluate(ts, probes)['S81.GRT']['cls'], 'LIVE')

    def test_job_children_waits_owner_stale(self):
        ts = mk_tasks()
        jobs = {'dsdv_slice_ve-dsdv_slice_ve-0123456ab': dict(name='dsdv_slice_ve-dsdv_slice_ve-0123456ab', status='RUNNING', t=NOW - 9000)}
        probes = {'ot-epyc5': dict(runs={self.P: run(self.P, 'RUNNING', procs=[(11, NOW - 60, 'bash run_all.sh')])})}
        res = evaluate(ts, probes, jobs=jobs)
        self.assertEqual(res['S81.STA.PAR.1']['cls'], 'LIVE')            # closure job named by short name
        self.assertEqual(res['S81.STA.PAR']['cls'], 'LIVE')              # via its live child
        self.assertEqual(res['TOK.FREEZE']['cls'], 'WAITS-OK')           # waits → S81.GRT which is LIVE
        self.assertEqual(res['TOK.DS']['cls'], 'BLOCKED-ON-OWNER')
        self.assertEqual(res['TOK.NEXT']['cls'], 'BLOCKED-ON-OWNER')
        self.assertEqual(res['TOK.IDLE']['cls'], 'STALE'); self.assertTrue(res['TOK.IDLE']['needs_agent'])

    def test_failed_job_dead_and_wait_on_dead_is_stale(self):
        ts = mk_tasks()
        jobs = {'dsdv_slice_ve-dsdv_slice_ve-0123456ab': dict(name='dsdv_slice_ve-dsdv_slice_ve-0123456ab', status='NEEDS_RTL', t=NOW - 9000)}
        probes = {'ot-epyc5': dict(runs={self.P: run(self.P, 'FAIL', rc=3, t_end=NOW - 5 * 3600)})}
        res = evaluate(ts, probes, jobs=jobs)
        self.assertEqual(res['S81.STA.PAR.1']['cls'], 'DEAD')
        self.assertEqual(res['TOK.FREEZE']['cls'], 'STALE'); self.assertIn('S81.GRT (DEAD)', res['TOK.FREEZE']['why'])

    def test_lane_names_never_make_dead(self):
        tree = '## INFRA · x\n- [ ] INF.9 Sweep · SWEEP · RUNNING · nothing named\n'
        ts = mk_tasks(tree, pending=[('SWEEP', 'other_blk-r1-abcdef012 | x | SWEEP')])
        jobs = {'other_blk-r1-abcdef012': dict(name='other_blk-r1-abcdef012', status='NEEDS_RTL', t=NOW - 600)}
        res = evaluate(ts, jobs=jobs)
        self.assertEqual(res['INF.9']['cls'], 'LIVE')       # activity 10 min ago, but not DEAD from a lane-tier job
        jobs['other_blk-r1-abcdef012']['t'] = NOW - 5 * 3600
        self.assertEqual(evaluate(ts, jobs=jobs)['INF.9']['cls'], 'STALE')

    def test_fresh_lane_file_is_live(self):
        with tempfile.TemporaryDirectory() as d:
            old = w.LANES; w.LANES = Path(d)
            try:
                (Path(d) / 'LANE-OLD.md').write_text('x\n')
                ts = mk_tasks()
                res = evaluate(ts, lane_mtimes={str(Path(d) / 'LANE-OLD.md'): NOW - 300})
                self.assertEqual(res['TOK.IDLE']['cls'], 'LIVE')
                res = evaluate(ts, lane_mtimes={str(Path(d) / 'LANE-OLD.md'): NOW - 7200})
                self.assertEqual(res['TOK.IDLE']['cls'], 'STALE')
            finally:
                w.LANES = old

    def test_harvest_flag(self):
        ts = mk_tasks()
        probes = {'ot-epyc5': dict(runs={self.P: run(self.P, 'OK', rc=0, t_end=NOW - 1800)})}
        res = evaluate(ts, probes, md_mtime=NOW - 7200)
        self.assertIn('finished rc 0', res['S81.GRT']['harvest'] or '')


class Probe(unittest.TestCase):
    def test_local_probe_finds_rc_and_live_process(self):
        with tempfile.TemporaryDirectory(prefix='twprobe_') as d:
            a = Path(d) / 'scr' / 'case_tw_dead1'; a.mkdir(parents=True)
            (a / 'run_all.done').write_text('Sun Oct 18 19:38:07 PDT 2026\n'); (a / 'run_all.log').write_text('grt rc 3\n')
            b = Path(d) / 'scr' / 'case_tw_live2'; b.mkdir()
            (b / 'chain.log').write_text('step 1\n')
            p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], cwd=str(b))
            try:
                time.sleep(0.3)
                res, err = w.run_probe('localhost', w.probe_script({str(a), str(b) + '/chain.log'}, set(), set()))
                self.assertIsNone(err)
                ra = res['runs'][str(a)]; rb = res['runs'][str(b)]
                self.assertEqual(w.run_state(ra)[:2], ('FAIL', 3))
                self.assertEqual(w.run_state(rb)[0], 'RUNNING')       # parent dir of a named file, process cwd inside it
            finally:
                p.kill(); p.wait()


class Render(unittest.TestCase):
    def test_banner(self):
        with tempfile.TemporaryDirectory() as d:
            old = rtr.TASKS_JSON; rtr.TASKS_JSON = Path(d) / 'TASKS_STALE.json'
            try:
                rtr.TASKS_JSON.write_text(json.dumps(dict(generated='x', generated_t=time.time(),
                    counts=dict(open=3, LIVE=1, STALE=1, DEAD=1, needs_agent=2),
                    tasks=[dict(id='S81.GRT', cls='DEAD', status_text='RUNNING', owner='S81-DIE8', why='rc 3', last_evidence_min=300),
                           dict(id='TOK.X', cls='STALE', status_text='WAITS', owner='T', why='no evidence', last_evidence_min=90),
                           dict(id='Q.GEN', cls='LIVE', status_text='RUNNING', owner='Q', why='run', last_evidence_min=1)])))
                h = rtr.task_banner()
                self.assertIn('LIVE 1', h); self.assertIn('STALE 1', h); self.assertIn('DEAD 1', h)
                self.assertIn('S81.GRT', h); self.assertIn('TOK.X', h); self.assertNotIn('Q.GEN', h)
            finally:
                rtr.TASKS_JSON = old


class LaneEvidence(unittest.TestCase):
    """2026-10-24 INFRA.WATCH: team owners (QC/KV/HBM/TOK-QK/COORD) map to lane files, lane run dirs and HANDOFF lines"""
    TREE2 = """# tree
## DIE kv · KV · rev x · est. x
- [ ] KV.G3.CORES KV hard cores · KV · RUNNING · none signed
- [ ] KV.G5 Boot + token · TOK-QK · RUNNING · boot stalls
- [ ] KV.IDLE Nothing · KV-NOBODY · TODO · nothing
## INFRA · fleet
- [ ] INFRA.DISK epyc2 scratch 87% · COORD · RUNNING · prune pass 2
"""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.old = w.LANES; w.LANES = Path(self.d.name)
        (w.LANES / 'KV-G3.md').write_text('# KV-G3\n2026-10-24 21:33 PDT KV-G3: eco on /srv/opentallas-scratch2/claude/kv-cores/eco\n')
        (w.LANES / 'TOK-QW.md').write_text('# TOK-QW\nno timestamps\n')

    def tearDown(self):
        w.LANES = self.old; self.d.cleanup()

    def texts(self):
        return {str(f): f.read_text() for f in w.LANES.glob('*.md')}

    def test_aliases_and_dirs(self):
        self.assertEqual([p.name for p in w.lane_paths('KV')], ['KV-G3.md'])
        self.assertEqual([p.name for p in w.lane_paths('TOK-QK')], ['TOK-QW.md'])
        self.assertIn('KV-TOK', w.owner_lane_names('TOK-QK'))
        self.assertEqual(w.lane_dirs_of('/x/KV-G3.md', '/srv/opentallas-scratch/claude/wt/a /srv/opentallas-scratch2/claude/kv-cores/eco'),
                         {'kv-g3', 'kv-cores'})

    def test_dated_lines(self):
        hl = w.handoff_lines('2026-10-24 21:14 PDT COORD: x\n- 2026-10-24 21:20 PDT S81: PARKED\n', now=2e9)
        self.assertEqual([h[0] for h in hl], ['COORD', 'S81'])
        self.assertEqual(hl[1][1] - hl[0][1], 360)

    def gather(self, ts, now, lane_mtimes=None, probes=None, hand=()):
        ev = w.gather(ts, now - 7200, self.texts(), lane_mtimes or {}, list(hand), [], {}, [], probes or {}, {}, now=now)
        return {r['id']: r for r in w.classify(ts, ev, now=now)}

    def test_lane_activity_and_run_dirs(self):
        lt = self.texts()
        ts = [t for t in w.load_tasks(self.TREE2) if not t['checked']]
        for t in ts: t['refs'] = w.build_refs(t, lt, [])
        t0 = w.handoff_lines(lt[str(w.LANES / 'KV-G3.md')], now=2e9)[0][1]
        res = self.gather(ts, t0 + 100 * 60)                       # lane line 100 min old: LIVE (< 2 h)
        self.assertEqual(res['KV.G3.CORES']['cls'], 'LIVE'); self.assertIn('KV-G3.md', res['KV.G3.CORES']['why'])
        self.assertEqual(res['KV.IDLE']['cls'], 'STALE')
        res = self.gather(ts, t0 + 150 * 60)                       # 2.5 h: STALE (the epyc1 mirror mtime does not count)
        self.assertEqual(res['KV.G3.CORES']['cls'], 'STALE')
        d = '/srv/opentallas-scratch2/claude/kv-cores'
        probes = {'intel2': dict(lanedirs={'kv-cores': [dict(path=d, newest=t0, nprocs=2, procs=[[5, t0, 'bash run_eco.sh']])]})}
        res = self.gather(ts, t0 + 150 * 60, probes=probes)        # a live ot-run unit in the lane's run dir: LIVE
        self.assertEqual(res['KV.G3.CORES']['cls'], 'LIVE'); self.assertIn('run_eco', res['KV.G3.CORES']['why'])
        res = self.gather(ts, t0 + 150 * 60, lane_mtimes={str(w.LANES / 'TOK-QW.md'): t0 + 140 * 60})
        self.assertEqual(res['KV.G5']['cls'], 'LIVE')              # TOK-QK -> TOK-QW.md (no timestamps: mtime)
        self.assertEqual(res['INFRA.DISK']['cls'], 'STALE')
        hand = [('COORD', t0 + 60 * 60, '2026-10-24 22:33 PDT COORD: disk prune pass 2 done on epyc2')]
        self.assertEqual(self.gather(ts, t0 + 150 * 60, hand=hand)['INFRA.DISK']['cls'], 'LIVE')
        hand = [('COORD', t0 + 60 * 60, '2026-10-24 22:33 PDT COORD: hourly, nothing about it')]
        self.assertEqual(self.gather(ts, t0 + 150 * 60, hand=hand)['INFRA.DISK']['cls'], 'STALE')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Native entry HOST jobs on an existing built cut (TOK-FUNC3-S81, 10-21).

Replays entry_boot.py --replay-job programme dirs (real 515-b host boot words on
u_seqhost.f_host, one KS start on f_ks) through a cut that contains u_seqhost
(cut_3S_ctl), with the KS descriptor derived from fixture metadata + an explicit
incoming user (ks_descriptor.py codec, RTL wiring user[51:42]/tok[41:21]/pos[20:0]).
Never builds: the cut binary (OBJ/sim) and its idle run must already exist, so a
live build is consumed, not duplicated.  Each job: gen -> sim -> strict check;
optional mutants (same binary) must FAIL.  Grade: RTL-functional (source assembly),
cut scope only (no global clock/route phase, no whole-stage/token claim).

  run_entry_replay.py --src ROOT --die-v die.v.gz --cut CUTDIR --kit KIT --obj OBJ
      --idle-run RUN --progs DIR(replay_jobK) --fixture-meta meta.json --ks-user 0 --out OUT
      [--jobs 15 16 ...] [--mutant K:SPEC ...]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sh(args, log, cwd, env=None):
    with open(log, 'w') as f:
        return subprocess.run([str(a) for a in args], cwd=cwd, env=env, stdout=f,
                              stderr=subprocess.STDOUT, check=False).returncode


FACES = {  # cut output face -> (receiving slice, its line input port): the line beat leaving the cut
    'W': ('w_xrW_2S_l', 'u_s_2S', 'ri_e'),   # u_s_3S.ro_w -> u_s_2S.ri_e
    'E': ('w_xrE_4S_l', 'u_s_5S', 'ri_w'),   # u_s_4S.ro_e -> u_s_5S.ri_w
}


def line_check(src, die_v, cut, prog, run):
    """Bit-exact CTL line stream leaving the cut on both line faces vs the host programme's templates.

    The 72-frame die abuts the slice line (0-station plan links), so dv_cut_replay encodes no output checks for it;
    here every scheduled CTL row must leave each face exactly once, in calendar order, with the template beat as the
    next stop receives it (ctl_beat: hops/src rewritten), at ONE constant issue->face offset (static schedule)."""
    sys.path.insert(0, str(src / 'tools/s81_dv'))
    import dv_cut_replay as R
    die = R.DieBuild(die_v)
    S = json.loads((prog / 'schedule.json').read_text())
    T = {t['i']: t for t in json.loads((prog / 'prog/ctl_templates.json').read_text())['templates']}
    tb = json.loads((cut / 'tb_ports.json').read_text())
    sp = json.loads((cut / 'slice_ports.json').read_text())['ports']
    # only S-tier beats reach the cut's S line faces (TOKd-S81 10-23: jobs 17/22 carry 51 S + 51 N beats; the N-tier
    # line is outside cut_3S_ctl, its rung word is checked by the bench on w_tvN_seqhost_lnd)
    evs = sorted((e for e in S['events'] if e['kind'] == 'CTL' and e['dir'] == 'in' and e['inst'][5:6] == 'S'),
                 key=lambda e: e['cycle'])
    res = {}
    for face, (pre, inst, port) in FACES.items():
        idx = {p['index']: int(sp[p['port']]['net'][len(pre):].split('_')[0]) for p in tb
               if p['dir'] == 'output' and sp[p['port']]['net'].startswith(pre)}
        cur, beats = {i: 0 for i in idx}, {}
        lines = (run / 'trace.txt').read_text().split('\n')
        bycyc = {}
        for ln in lines:
            f = ln.split()
            if len(f) == 3 and int(f[1]) in idx:
                bycyc.setdefault(int(f[0]), []).append((int(f[1]), int(f[2], 16)))
        for c in sorted(bycyc):
            for i, v in bycyc[c]:
                cur[i] = v
            beat = sum(cur[i] << (276 * idx[i]) for i in idx)
            if beat:
                beats[c] = beat
        exp = [(e, R.ctl_beat(T, dict(e, inst=inst, port=port), die, inst)[0]) for e in evs]
        obs = sorted(beats.items())
        ok_n = len(obs) == len(exp)
        mism = [dict(row=e.get('from_row'), tag=e['tag'], cycle=c, exp=f'{b:x}', got=f'{v:x}')
                for (e, b), (c, v) in zip(exp, obs) if b != v]
        offs = sorted({c - e['cycle'] for (e, _), (c, _) in zip(exp, obs)})
        res[face] = dict(receiver=f'{inst}.{port}', expected=len(exp), observed=len(obs), mismatches=len(mism),
                         first_mismatch=mism[:2], offsets=offs, first_cycle=obs[0][0] if obs else None,
                         last_cycle=obs[-1][0] if obs else None,
                         verdict='PASS' if ok_n and not mism and len(offs) == 1 else 'FAIL')
    return res


def host_status(cut, replay, run):
    """u_seqhost t_host status {alive, fault, wf 4, sq 6 = {fault, code 4, busy}} changes, read on the landed lane
    the replay derived seqhost_live from; accepted = the issuer went busy with no fault."""
    lv = (replay.get('host_boot') or {}).get('seqhost_live')
    if not lv:
        return None
    tb = json.loads((cut / 'tb_ports.json').read_text()); sp = json.loads((cut / 'slice_ports.json').read_text())['ports']
    ports = [p for p in tb if p['dir'] == 'output' and sp[p['port']]['net'] == f'w_{lv["lane"]}_lnd']
    if not ports or not (run / 'trace.txt').exists():
        return None
    idx, ch, last = ports[0]['index'], [], None
    for ln in (run / 'trace.txt').read_text().split('\n'):
        f = ln.split()
        if len(f) == 3 and int(f[1]) == idx:
            st = (int(f[2], 16) >> 65) & 0xFFF
            if st != last:
                ch.append((int(f[0]), st)); last = st
    busy = any(st & 1 for _, st in ch)
    fault = any((st >> 10) & 1 for _, st in ch)
    code = next(((st >> 1) & 15 for _, st in ch if (st >> 10) & 1), 0)
    return dict(changes=[(c, f'{st:03x}') for c, st in ch], accepted=busy and not fault, fault_code=code)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('src', 'die-v', 'cut', 'kit', 'obj', 'idle-run', 'progs', 'fixture-meta', 'out'):
        p.add_argument('--' + k, type=Path, required=True)
    p.add_argument('--ks-user', type=int, required=True)
    p.add_argument('--jobs', type=int, nargs='*')
    p.add_argument('--mutant', action='append', default=[], help='JOB:SPEC (dv_cut_replay --mutant), must FAIL')
    p.add_argument('--ks', type=int, default=None, help='landed f_ks edge for every job (dv_cut_replay gen --ks)')
    p.add_argument('--ks-probe', action='store_true',
                   help='measure the issuer start phase first: replay the first job with KS = default + 0..3 and take the '
                        'one u_seqhost accepts (t_host sq busy, no fault); every job then uses that --ks')
    a = p.parse_args()
    src, out = a.src.resolve(), a.out.resolve()
    if not (a.obj / 'sim').exists():
        sys.exit(f'no built cut binary {a.obj}/sim: consume the existing build, never start a duplicate')
    if not (a.idle_run / 'trace.txt').exists():
        sys.exit(f'no idle-run trace {a.idle_run}/trace.txt (u_seqhost live edge is derived from it)')
    out.mkdir(parents=True, exist_ok=False)
    jobs = a.jobs or sorted(int(d.name[len('replay_job'):]) for d in a.progs.glob('replay_job*'))
    rep = dict(schema='opentallas.s81_tokfunc.entry_replay.v1', grade='RTL-functional (source assembly)',
               scope='cut_3S_ctl native entry HOST jobs: u_seqhost boot + KS start -> bk_sel/column-4 CTL -> slices',
               die_v=str(a.die_v), die_v_sha256=hashlib.sha256(a.die_v.read_bytes()).hexdigest(),
               kit=str(a.kit), obj=str(a.obj), idle_run=str(a.idle_run), ks_user=a.ks_user,
               fixture_meta_sha256=hashlib.sha256(a.fixture_meta.read_bytes()).hexdigest(),
               full_stage=False, full_token=False, global_clock_route_phase_qualified=False,
               verdict='RUNNING', jobs=[], mutants=[])

    def save():
        (out / 'entry_replay.json.tmp').write_text(json.dumps(rep, indent=1) + '\n')
        (out / 'entry_replay.json.tmp').replace(out / 'entry_replay.json')

    env = dict(os.environ, OBJ=str(a.obj.resolve()))

    def one(job, mutant=None, name=None, ks=None, probe=False):
        name = name or (f'job{job}' + (f'_mut_{mutant.replace(":", "_")}' if mutant else ''))
        d = out / name
        d.mkdir()
        ks = a.ks if ks is None else ks
        row = dict(job=job, mutant=mutant, dir=str(d))
        gen = ['python3', src / 'tools/s81_dv/dv_cut_replay.py', 'gen', '--die-v', a.die_v,
               '--prog', a.progs / f'replay_job{job}', '--cut', a.cut, '--out', d,
               '--idle-run', a.idle_run, '--ks-fixture-meta', a.fixture_meta, '--ks-user', a.ks_user]
        if mutant:
            gen += ['--mutant', mutant]
        if ks is not None:
            gen += ['--ks', ks]
        row['gen_rc'] = sh(gen, d / 'gen.log', src)
        if row['gen_rc']:
            row.update(verdict='FAIL', reason='generator refused: ' + (d / 'gen.log').read_text()[-400:])
            return row
        r = json.loads((d / 'replay.json').read_text())
        for k in ('verdict_kind', 'partial', 'in_events', 'out_check_lines', 'ncyc', 'unencoded_total', 'by_kind'):
            row[k] = r.get(k)
        row['host_boot'] = {k: r['host_boot'].get(k) for k in ('boot_start', 'words', 'ks', 'ks_word', 't0', 'ks_provenance')} \
            if r.get('host_boot') else None
        row['sim_rc'] = sh(['bash', src / 'tools/s81_dv/run_dv_slice.sh', a.kit, d / 'run', f'+IN={d}/in.txt',
                            f'+OUT={d}/out.txt', f'+TRACE={d}/run/trace.txt', f'+NCYC={r["ncyc"]}'],
                           d / 'sim.log', src, env)
        if probe:
            row['t_host'] = host_status(a.cut, r, d / 'run')
            return row
        # this replay IS the selected-XRT HOST/control runtime proof (xr_timing guard 28ae20d13): the check keeps every
        # source pin and the job verdict below still needs bench fault 0 + line bit-exact
        row['check_rc'] = sh(['python3', src / 'tools/s81_dv/dv_cut_replay.py', 'check', '--replay', d,
                              '--run', d / 'run', '--out', d / 'check.json', '--xrt-runtime-proof', 'self-entry'],
                             d / 'check.log', src)
        tc = r.get('timing_contract') or {}
        if tc.get('transport_sources') and not mutant:
            prev = rep.setdefault('xrt_transport_sources', dict(tc['transport_sources']))
            if prev != tc['transport_sources']:
                rep['xrt_transport_sources_conflict'] = True
        if row['check_rc'] and (d / 'check.log').exists():
            row['check_error'] = (d / 'check.log').read_text().strip().split('\n')[-1][-300:]
        if (d / 'check.json').exists():
            c = json.loads((d / 'check.json').read_text())
            row['check'] = {k: c.get(k) for k in ('verdict', 'checked', 'mismatch', 'missing', 'extra',
                                                    'first_mismatch', 'last_cycle') if k in c}
        # The cut bench fails itself on zero encoded checks (abutted line); its fault count and applied-input
        # accounting still hold, and the line stream is checked bit-exact from the trace here.
        log = (d / 'run' / 'run.log').read_text() if (d / 'run' / 'run.log').exists() else ''
        import re
        m = re.search(r'DV_SLICE cycles=(\d+) in_events=(\d+) out_checks=(\d+) mismatches=(\d+) fault_cycles=(\d+) '
                      r'first_fault=(-?\d+)', log)
        row['bench'] = dict(zip(('cycles', 'in_events', 'out_checks', 'mismatches', 'fault_cycles', 'first_fault'),
                                map(int, m.groups()))) if m else None
        row['inputs_all_applied'] = 'left unapplied' not in log
        row['line'] = line_check(src, a.die_v, a.cut, a.progs / f'replay_job{job}', d / 'run') \
            if (d / 'run' / 'trace.txt').exists() else None
        ok = bool(row['bench']) and row['bench']['fault_cycles'] == 0 and row['inputs_all_applied'] \
            and row['line'] is not None and all(f['verdict'] == 'PASS' for f in row['line'].values()) \
            and (row['check_rc'] == 0 or row.get('out_check_lines') == 0)
        if mutant:
            row['verdict'] = 'CAUGHT' if not ok else 'MISSED'
        else:
            row['verdict'] = 'FAIL' if not ok else ('PARTIAL' if r.get('partial') or r.get('verdict_kind') != 'SCHEDULE'
                                                     else 'PASS')
        row['layer_cycles'] = r['ncyc'] - r['t0'] if 't0' in r else None
        return row

    save()
    if a.ks_probe and a.ks is None:
        from concurrent.futures import ThreadPoolExecutor
        base = None
        with ThreadPoolExecutor(1) as ex:
            r0 = ex.submit(one, jobs[0], None, 'probe_default', None, True).result()
        if r0.get('gen_rc') or not r0.get('host_boot'):
            rep.update(verdict='FAIL', reason='KS phase probe: generator refused'); save(); return 1
        base = r0['host_boot']['ks']
        with ThreadPoolExecutor(3) as ex:
            rows = [r0] + list(ex.map(lambda k: one(jobs[0], None, f'probe_ks{base + k}', base + k, True), (1, 2, 3)))
        rep['ks_probe'] = [dict(ks=r['host_boot']['ks'], t_host=r['t_host']) for r in rows]
        acc = [r['host_boot']['ks'] for r in rows if r['t_host'] and r['t_host']['accepted']]
        if len(acc) != 1:
            rep.update(verdict='FAIL', reason=f'KS phase probe: {len(acc)} of 4 phases accepted ({acc})'); save()
            print('ENTRY_REPLAY FAIL ks probe', rep['ks_probe']); return 1
        a.ks = acc[0]; rep['ks'] = a.ks; save()
    for j in jobs:
        rep['jobs'].append(one(j)); save()
    for m in a.mutant:
        j, spec = m.split(':', 1)
        rep['mutants'].append(one(int(j), spec)); save()
    v = [r['verdict'] for r in rep['jobs']]
    rep['verdict'] = ('FAIL' if 'FAIL' in v or not v else 'PARTIAL' if 'PARTIAL' in v else 'PASS_CUT_COMPONENT')
    if rep.get('xrt_transport_sources_conflict'):
        rep['verdict'] = 'FAIL'; rep['reason'] = 'jobs disagree on the selected transport sources'
    if any(m['verdict'] != 'CAUGHT' for m in rep['mutants']):
        rep['verdict'] = 'FAIL'
        rep['reason'] = 'a negative control was not caught'
    save()
    print('ENTRY_REPLAY', rep['verdict'], [(r['job'], r['verdict']) for r in rep['jobs']],
          [(r['mutant'], r['verdict']) for r in rep['mutants']])
    return 0 if rep['verdict'] == 'PASS_CUT_COMPONENT' else 1


if __name__ == '__main__':
    sys.exit(main())

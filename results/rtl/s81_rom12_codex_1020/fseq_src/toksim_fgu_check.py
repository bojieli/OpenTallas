#!/usr/bin/env python3
"""TOKSIM-S81B/FGU (10-19): check a phase-sequence run of tb_toksim_fgu_seq (and summarise single-phase runs).

seq:    every RET word of the run is assigned to the phase whose compiled return calendar, shifted by that phase's
        actual go offset (GO i edge - GO 0 edge), predicts a word on that edge; each phase's words then go through the
        unchanged xs_place check (golden segment-tree node values bit-exact, segment coverage of every row once, one op
        tag, cycle-exact calendar, fixture BF16 tie of every row).  Unassigned words / GO_LATE / XO / FAULT fail.
single: go -> first / last RET edge of a single-phase run (xs_place check run separately).

    toksim_fgu_check.py seq --seq VEC/seq_experts_gu --vec VEC --log RUN.LOG --out RES.json
    toksim_fgu_check.py single --log RUN.LOG
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import xs_place as XP  # noqa: E402


def gos(log):
    return [(int(i), int(e), int(p), int(o)) for i, e, p, o in re.findall(r'^GO (\d+) (\d+) (\d+) (\d+)$', log, re.M)]


def rets(log):
    return [(int(e), w) for e, w in re.findall(r'^RET (\d+) ([0-9a-f]+)$', log, re.M)]


def cmd_single(a):
    log = Path(a.log).read_text()
    g, r = gos(log), rets(log)
    res = dict(go=g[0][1] if g else None, first_ret=r[0][0] if r else None, last_ret=r[-1][0] if r else None, words=len(r))
    print('TOKSIM_FGU_SINGLE', json.dumps(res))
    return 0


def cmd_seq(a):
    log = Path(a.log).read_text()
    sq = json.loads((Path(a.seq) / 'seq.json').read_text())
    g = gos(log)
    errs = []
    if len(g) != len(sq['phases']):
        errs.append(f'GO_COUNT {len(g)} != {len(sq["phases"])}')
    errs += re.findall(r'^GO_LATE .*$', log, re.M)[:4]
    errs += re.findall(r'^XO_MISMATCH .*$', log, re.M)[:4] + re.findall(r'^FAULT .*$', log, re.M)[:4]
    end = re.search(r'^END .*$', log, re.M)
    if not end:
        errs.append('NO_END')
    # reference go edge of the single-phase bench (the calendar's edge numbering): GO 0 of a 1-phase run = P0
    ref = a.ref_go
    owner = {}
    metas = []
    for (i, e, ph, ops), vec in zip(g, sq['vectors']):
        m = json.loads((Path(a.vec) / vec / 'meta.json').read_text())
        assert m['field_phase'] == ph, (vec, m['field_phase'], ph)
        d = e - ref
        metas.append((i, vec, m, d))
        for w in m['plan']['ret']:
            t = w[0] + d
            if t in owner:
                errs.append(f'CALENDAR_COLLISION edge {t} phases {owner[t][0]} {vec}')
            owner[t] = (vec, d)
    per = {vec: [] for _, vec, _, _ in metas}
    for e, w in rets(log):
        if e not in owner:
            errs.append(f'UNASSIGNED_RET edge {e} {w}')
            continue
        vec, d = owner[e]
        per[vec].append(f'RET {e - d} {w}')
    out = Path(a.out)
    wd = out.parent / (out.stem + '_phases')
    wd.mkdir(parents=True, exist_ok=True)
    phases = []
    for i, vec, m, d in metas:
        pd = wd / vec
        pd.mkdir(exist_ok=True)
        (pd / 'meta.json').write_text(json.dumps(m) + '\n')
        (pd / 'run.log').write_text('\n'.join(per[vec]) + '\n' + (end.group(0) if end else '') + '\n')
        rc = XP.cmd_check(argparse.Namespace(dir=str(pd), log=str(pd / 'run.log'), fixtures=a.fixtures))
        chk = json.loads((pd / 'check.json').read_text())
        if rc:
            errs.append(f'PHASE_FAIL {vec}: {chk["errors"][:2]}')
        phases.append(dict(i=i, vec=vec, phase=m['field_phase'], mat=m['mat'], rows=m['nrows'], go=g[i][1], shift=d,
                           words=len(per[vec]), first_ret=min(int(x.split()[1]) for x in per[vec]) + d if per[vec] else None,
                           last_ret=max(int(x.split()[1]) for x in per[vec]) + d if per[vec] else None,
                           fixture_rows=chk['fixture_rows'], pass_=chk['pass']))
    r = rets(log)
    res = dict(op=sq['op'], frame=sq['frame'], per=a.per, nph=len(sq['phases']), rows=sum(sq['rows']),
               go0=g[0][1] if g else None, last_go=g[-1][1] if g else None, first_ret=r[0][0] if r else None,
               last_ret=r[-1][0] if r else None, words=len(r),
               go0_to_last_ret=(r[-1][0] - g[0][1]) if (r and g) else None,
               fixture_rows=sum(p['fixture_rows'] for p in phases), errors=errs[:40], phases=phases, end=end.group(0) if end else None)
    res['pass'] = not errs
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(f'TOKSIM_FGU_SEQ {"PASS" if res["pass"] else "FAIL"} op {sq["op"]} PER {a.per} phases {res["nph"]} rows {res["rows"]} '
          f'fixture_rows {res["fixture_rows"]} go0 {res["go0"]} last_ret {res["last_ret"]} span {res["go0_to_last_ret"]} '
          f'errors {len(errs)} {errs[:3]}')
    return 0 if res['pass'] else 1


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest='cmd', required=True)
    q = s.add_parser('seq')
    q.add_argument('--seq', required=True)
    q.add_argument('--vec', required=True)
    q.add_argument('--log', required=True)
    q.add_argument('--out', required=True)
    q.add_argument('--per', type=int, default=None)
    q.add_argument('--ref-go', type=int, required=True, help='GO 0 edge of the single-phase bench (calendar numbering)')
    q.add_argument('--fixtures', default=None)
    t = s.add_parser('single')
    t.add_argument('--log', required=True)
    a = p.parse_args()
    return cmd_seq(a) if a.cmd == 'seq' else cmd_single(a)


if __name__ == '__main__':
    sys.exit(main())

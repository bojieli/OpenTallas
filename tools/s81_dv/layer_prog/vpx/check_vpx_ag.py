#!/usr/bin/env python3
"""LB2-S81/CC fork VPX: check a tb_vpx_ag run (run.log) against expect.json (gen_vpx_ag.py).

PASS = (1) every compiled leg beat leaves the slice's outward port on EXACTLY its compiled edge, bit-exact (header +
4 row pairs of the fixture), and nothing else leaves; (2) the peer's leaf 0 receives every pair of the beat as row-pair
writes on the edges LRI + RX_WR_AFTER_PIN + j (one constant for every beat: fixed on-die latency after the link), rows and
data bit-exact; (3) the read-back of all gathered rows (own + received part) through the real leaf store matches the
fixture bit-exact, each beat on its compiled edge; (4) no slice fault.  Writes check.json; exit 0 = PASS.
    check_vpx_ag.py --dir RUNDIR [--log run.log] [--out check.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path


def parse(log):
    ev = dict(SEND={'A': [], 'B': []}, LRI={'A': [], 'B': []}, WR={'A': [], 'B': []}, OUT={'A': [], 'B': []},
              CTL={'A': [], 'B': []}, LO={'A': [], 'B': []}, FAULT={})
    done = None
    for ln in log.read_text(errors='replace').splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] in ('SEND', 'LRI', 'OUT'):
            ev[t[0]][t[1]].append((int(t[2]), int(t[3], 16)))
        elif t[0] == 'WR':
            ev['WR'][t[1]].append(dict(cycle=int(t[2]), leaf=int(t[3]), row=int(t[4]), mask=t[5], data=int(t[6], 16)))
        elif t[0] in ('CTL', 'LO'):
            ev[t[0]][t[1]].append((int(t[2]), t[3]))
        elif t[0] == 'FAULT':
            ev['FAULT'][t[1]] = int(t[2])
        elif t[0] == 'DONE':
            done = int(t[1])
    return ev, done


def check(d, logname='run.log'):
    exp = json.loads((d / 'expect.json').read_text())
    ev, done = parse(d / logname)
    errs, info = [], {}
    if done is None:
        errs.append('run did not reach DONE')
    for die, f in ev['FAULT'].items():
        errs.append(f'slice fault on die {die} at edge {f}')
    rx = exp['consts']['RX_WR_AFTER_PIN']
    for die in ('A', 'B'):
        es = exp['sends'][die]
        got = [x for x in ev['SEND'][die]]
        info[f'sends_{die}'] = dict(expected=len(es), got=len(got),
                                    edge_delta=sorted({g[0] - e['cycle'] for g, e in zip(got, es)}))
        if len(got) != len(es):
            errs.append(f'{die}: {len(got)} outward beats, expected {len(es)}')
        for i, (g, e) in enumerate(zip(got, es)):
            if g[0] != e['cycle']:
                errs.append(f'{die} send {i}: edge {g[0]} != compiled {e["cycle"]}')
            if g[1] != int(e['beat'], 16):
                errs.append(f'{die} send {i}: beat differs (xor {g[1] ^ int(e["beat"], 16):x})'[:200])
    for die in ('A', 'B'):
        peer = 'B' if die == 'A' else 'A'
        lri = [c for c, b in ev['LRI'][die]]
        ew = exp['wr'][die]
        t1 = exp['t1']
        wr = [w for w in ev['WR'][die] if exp['t0'] <= w['cycle'] < t1]
        info[f'rx_{die}'] = dict(lri=len(lri), writes=len(wr), expected=len(ew))
        if len(wr) != len(ew):
            errs.append(f'{die}: {len(wr)} received row-pair writes, expected {len(ew)}')
        deltas = set()
        for k, (g, e) in enumerate(zip(wr, ew)):
            if g['leaf'] != 0 or g['row'] != e['row'] or g['data'] != int(e['data'], 16) or g['mask'] != 'ff':
                errs.append(f'{die} rx pair {k}: leaf {g["leaf"]} row {g["row"]} (exp {e["row"]}) data/mask mismatch'
                            if g['data'] != int(e['data'], 16) else f'{die} rx pair {k}: row {g["row"]} exp {e["row"]}')
            if e['beat'] < len(lri):
                deltas.add(g['cycle'] - lri[e['beat']] - e['pair'])
        info[f'rx_{die}']['wr_minus_lri'] = sorted(deltas)
        if deltas and deltas != {rx}:
            errs.append(f'{die}: receive latency {sorted(deltas)} != compiled RX_WR_AFTER_PIN {rx}')
        if len(lri) != len(exp['sends'][peer]):
            errs.append(f'{die}: {len(lri)} beats from the lep, expected {len(exp["sends"][peer])}')
    for die in ('A', 'B'):
        er = exp['readback'][die]
        got = ev['OUT'][die]
        info[f'readback_{die}'] = dict(expected=len(er), got=len(got),
                                       edge_delta=sorted({g[0] - e['cycle'] for g, e in zip(got, er)}))
        if len(got) != len(er):
            errs.append(f'{die}: {len(got)} read-back beats, expected {len(er)}')
        for i, (g, e) in enumerate(zip(got, er)):
            data = (g[1] >> 52) & ((1 << 1024) - 1)
            if data != int(e['data'], 16):
                errs.append(f'{die} read-back {i} rows {e["rows"][0]}..{e["rows"][-1]}: data differs from the fixture')
            if g[0] != e['cycle']:
                errs.append(f'{die} read-back {i}: edge {g[0]} != compiled {e["cycle"]}')
    res = dict(schema='opentallas.s81_dv.vpx_ag_check.v1', pass_=not errs, errors=errs[:40], n_errors=len(errs),
               info=info, mut=exp.get('mut'), consts=exp['consts'])
    res['pass'] = res.pop('pass_')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--log', default='run.log')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    r = check(Path(a.dir), a.log)
    Path(a.out or Path(a.dir) / 'check.json').write_text(json.dumps(r, indent=1) + '\n')
    print(('PASS' if r['pass'] else 'FAIL') + ' vpx_ag ' + json.dumps(r['info'])[:1500])
    for e in r['errors'][:12]:
        print('  ' + e)
    sys.exit(0 if r['pass'] else 1)


if __name__ == '__main__':
    main()

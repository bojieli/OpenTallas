#!/usr/bin/env python3
"""Classify the failing endpoints of an HBM die STA by cause (owner 2026-10-13: die timing first, classify before fixing;
method of the S81 pilot, tools/s81/sta_path_classes.py on claude/el1011-s81dieit).

usage: hbm_die_sta_classes.py <plan dir> <paths_<corner>.txt> [...] --out OUT.json [--md OUT.md]
  plan dir     tools/hbm_accel_die_fp.py check --ds-var <preset> --out <plan dir>: plan.json.gz (insts, hops with the
               pin-to-pin length of every driver -> load pair) and clock_delivery.json (view kind per master)
  paths_*.txt  written by the die STA Tcl (tools/hbm_die_relay_sta.py report()): one line per endpoint with slack
               < 15 ps: "<startpoint> <endpoint> <slack ns>"

Every endpoint gets its launch instance from the STA startpoint and its hop from the plan (driver instance -> load
instance); the class key is (cause, launch master.port -> capture master.port, view kind -> view kind).  Causes, in the
order they are tested:
  reset_net        the endpoint or startpoint is a reset relay (hfd_rrl) or the hop's class is reset
  no_plan_hop      the pair is not a die hop of the plan (a path through a block ETM, a clock pin, a top port)
  placeholder_lib  either end is a placeholder master (generated timing: not evidence about a tile)
  hop_over_reach   pin-to-pin hop > 500 um (the die rule: needs a relay; contract work)
  relay_chain      station -> station within the reach (the relay family's own launch / capture + wire)
  master_pair_hop  real block <-> real block / station within the reach: clock phase / insertion (R of the two views)
                   or a tile launch / capture defect; judge these rows FIRST (real -> real)
Rows: endpoints, violators (slack < 0), worst, TNS, hop length max / mean, an example."""
import argparse
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path


def norm(m):
    return re.sub(r'_u\w+$', '', re.sub(r'(hfd_stn_q)[a-z]*\d+[NSEW]?$', r'\1N', re.sub(r'(hfd_(?:meso|mcast|gath|stn)_r?)\d+\w*$', r'\1N', m)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--md')
    ap.add_argument('--reach', type=float, default=500.0)
    a = ap.parse_args()
    p = json.load(gzip.open(Path(a.plan) / 'plan.json.gz', 'rt'))
    cd = json.loads((Path(a.plan) / 'clock_delivery.json').read_text())['tiles']
    mst = {i[0]: i[1] for i in p['insts']}
    hop = {}
    for bus, cls, bits, si, sp, di, dp, um in p['hops']:
        hop.setdefault((si, di), []).append((sp, dp, cls, um, bus))
    names = sorted(mst, key=len, reverse=True)
    name_re = re.compile(r'^(.*?)/([^/]+)$')

    def split(full):
        """die instance + pin of an STA pin name (the die is flat: <inst>/<pin>[bit])"""
        m = name_re.match(full)
        if not m:
            return None, full
        inst, pin = m.groups()
        while inst not in mst and '/' in inst:
            inst, rest = inst.rsplit('/', 1)
            pin = rest + '/' + pin
        return (inst if inst in mst else None), re.sub(r'\[\d+\]$', '', pin)

    res = {}
    for path in a.paths:
        agg = defaultdict(lambda: dict(n=0, viol=0, wns=1e9, tns=0.0, Lmax=0.0, Lsum=0.0, Ln=0, ex=None))
        tot = dict(n=0, viol=0)
        for ln in open(path, errors='ignore'):
            f = ln.split()
            if len(f) < 3:
                continue
            sl = float(f[2]) * 1000.0
            (si, sp), (di, dp) = split(f[0]), split(f[1])
            sm, dm = mst.get(si, 'TOP'), mst.get(di, 'TOP')
            sv, dv = cd.get(sm, {}).get('view', '?'), cd.get(dm, {}).get('view', '?')
            hs = hop.get((si, di)) or []
            h = next((x for x in hs if x[0] == sp.split('_s')[0] or x[1] == dp), hs[0] if hs else None)
            L = h[3] if h else None
            if 'hfd_rrl' in (sm, dm) or (h and 'reset' in h[2]):
                cause = 'reset_net'
            elif h is None:
                cause = 'no_plan_hop'
            elif 'placeholder' in (sv, dv):
                cause = 'placeholder_lib'
            elif L is not None and L > a.reach:
                cause = 'hop_over_reach'
            elif sv == 'relay' and dv == 'relay':
                cause = 'relay_chain'
            else:
                cause = 'master_pair_hop'
            k = (cause, f'{norm(sm)}.{sp}', f'{norm(dm)}.{dp}', f'{sv}->{dv}')
            r = agg[k]
            r['n'] += 1
            tot['n'] += 1
            if L is not None:
                r['Lmax'] = max(r['Lmax'], L)
                r['Lsum'] += L
                r['Ln'] += 1
            if sl < 0:
                r['viol'] += 1
                r['tns'] += sl
                tot['viol'] += 1
            if sl < r['wns']:
                r['wns'], r['ex'] = sl, f'{f[0]} -> {f[1]}'
        rows = [dict(cause=k[0], launch=k[1], capture=k[2], views=k[3], endpoints=r['n'], violators=r['viol'],
                     wns_ps=round(r['wns'], 1), tns_ns=round(r['tns'] / 1000, 2), len_max_um=round(r['Lmax'], 1),
                     len_mean_um=round(r['Lsum'] / r['Ln'], 1) if r['Ln'] else None, example=r['ex']) for k, r in agg.items()]
        rows.sort(key=lambda r: (-r['violators'], r['wns_ps']))
        by_cause = defaultdict(lambda: dict(endpoints=0, violators=0, wns_ps=1e9, tns_ns=0.0, classes=0))
        for r in rows:
            c = by_cause[r['cause']]
            c['endpoints'] += r['endpoints']
            c['violators'] += r['violators']
            c['wns_ps'] = min(c['wns_ps'], r['wns_ps'])
            c['tns_ns'] = round(c['tns_ns'] + r['tns_ns'], 2)
            c['classes'] += 1
        res[Path(path).name] = dict(endpoints_listed=tot['n'], violators=tot['viol'], by_cause=dict(by_cause), classes=rows)
    Path(a.out).write_text(json.dumps(dict(schema='opentallas.hbm_die_sta_classes.v1', plan=a.plan, reach_um=a.reach,
                                           note='endpoints listed = slack < 15 ps (the STA Tcl writes only those)',
                                           reports=res), indent=1) + '\n')
    md = ['# HBM die STA: failing endpoints by cause', '']
    for nm, r in res.items():
        md += [f'## {nm}: {r["violators"]} violators of {r["endpoints_listed"]} endpoints below 15 ps', '',
               '| cause | classes | endpoints | violators | worst ps | TNS ns |', '|---|---:|---:|---:|---:|---:|']
        md += [f'| {c} | {v["classes"]} | {v["endpoints"]} | {v["violators"]} | {v["wns_ps"]} | {v["tns_ns"]} |'
               for c, v in sorted(r['by_cause'].items(), key=lambda kv: -kv[1]['violators'])]
        md += ['', '| cause | launch -> capture | views | endpoints | violators | worst ps | TNS ns | hop max / mean um |',
               '|---|---|---|---:|---:|---:|---:|---|']
        md += [f'| {x["cause"]} | {x["launch"]} -> {x["capture"]} | {x["views"]} | {x["endpoints"]} | {x["violators"]} | '
               f'{x["wns_ps"]} | {x["tns_ns"]} | {x["len_max_um"]} / {x["len_mean_um"]} |' for x in r['classes'][:60]]
        md.append('')
    if a.md:
        Path(a.md).write_text('\n'.join(md) + '\n')
    for nm, r in res.items():
        print(nm, r['violators'], 'violators;', {c: v['violators'] for c, v in r['by_cause'].items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

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
  clock_phase      the two ends' flops are clocked at different planned times (region flop targets of
                   <case>/relay_clock_context.json: entry + internal insertion) and the endpoint passes once that
                   difference is taken out: die clock delivery (phi - R per tile), not a tile or a wire
  placeholder_lib  either end is timed by a PLACEHOLDER Liberty (generated boundary-registered recipe: not evidence
                   about a tile)
  hop_over_reach   pin-to-pin hop > 500 um (the die rule: needs a relay; contract work)
  relay_chain      relay -> relay within the reach (STA wire stage or closed station view at both ends)
  master_pair_hop  real block <-> real block / relay within the reach: a tile launch / capture defect or the wire;
                   judge these rows FIRST (real -> real)

View kind of an end = what the STA case BOUND for its master (--case: the Liberty files of the case directory and its
manifest), not the generator's table: real (closed view with Liberty), real_station (closed box-era station view),
interim (indexed, not closed: hfd_sm), hard_macro (PHY Liberty), placeholder_lib (<master>_ph_<corner> library),
sta_relay (hfd_rly_<n>: a register stage the STA case added on a cut bus; relays.json gives its bus, ends and hop
lengths), untimed (no Liberty: a black box, its pins are not endpoints).  Without --case the kinds fall back to the
plan's clock_delivery.json (over-counts placeholder rows: the generator knows 2 real masters, the case binds 31).
The coverage block says how much of the plan the STA times at all: plan hops with both ends timed / one / none.
Rows: endpoints, violators (slack < 0), worst, TNS, hop length max / mean, an example."""
import argparse
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path


def norm(m):
    return re.sub(r'_u\w+$', '', re.sub(r'(hfd_stn_q)[a-z]*\d+[NSEW]?$', r'\1N', re.sub(r'(hfd_(?:meso|mcast|gath|stn)_r?)\d+\w*$', r'\1N', m)))


STATION_VIEW = re.compile(r'hfd_(stn_r|meso_r|mcast_r|gath_r|cdist_r)\d')
RELAY_KINDS = ('sta_relay', 'real_station', 'relay', 'relay_ph')
DIGITS = re.compile(r'\d+')


def case_bind_map(case):
    """{master: kind} from what the STA case directory binds, {relay instance: metadata}, chains by relay instance"""
    case = Path(case)
    kinds = {}
    man = json.loads((case / 'manifest.json').read_text()) if (case / 'manifest.json').exists() else {}
    interim = set(man.get('interim_views') or ())
    for lib in sorted(case.glob('*_ss.lib')) + sorted(case.glob('*_ff.lib')):
        n = lib.name[:-7]
        with open(lib, errors='ignore') as f:
            head = f.readline()
        if n == 'hfd_rly':
            continue
        if f'{n}_ph_' in head:
            kinds[n] = 'placeholder_lib'
        elif n.startswith(('ot_pdie_serdes', 'ot_hbm_host_phy', 'ot_hbm3e_phy')):
            kinds[n] = 'hard_macro'
        elif STATION_VIEW.match(n):
            kinds[n] = 'real_station'
        elif n == 'hfd_sm' or n in interim:
            kinds[n] = 'interim'
        else:
            kinds[n] = 'real'
    pj = case / 'placeholder_masters.json'      # die --placeholder-all: one bundled library, kinds listed here
    if pj.exists():
        for n, k in json.loads(pj.read_text())['masters'].items():
            kinds.setdefault(n, k)
    meta, chain_of = {}, {}
    rj = case / 'relays.json'
    if rj.exists():
        r = json.loads(rj.read_text())
        meta = r.get('instance_metadata') or {}
        for ch in r.get('chains', []):
            for k, reg in enumerate(ch.get('regs', [])):
                chain_of[reg] = (ch, k)
    ctx = None
    cj = case / 'relay_clock_context.json'
    if cj.exists():
        ctx = json.loads(cj.read_text())
    return kinds, meta, chain_of, ctx


def flop_times(ctx):
    """{instance: {corner: planned flop time ps}} = clock entry at the pin + the view's internal insertion"""
    out = {}
    if not ctx:
        return out
    sinks = dict(ctx.get('sinks') or {})
    for k in ('view_sinks', 'relay_sinks', 'relays', 'added'):
        sinks.update(ctx.get(k) or {})
    for k, s in sinks.items():
        e, i = s.get('entry_ps') or {}, s.get('internal_ps') or {}
        if not e:
            continue
        if not isinstance(i, dict):
            i = dict(ss=i, ff=i, tt=i)
        out.setdefault(s.get('instance') or k.rsplit('/', 1)[0], {}).update(
            {c: e[c] + (i.get(c) or 0.0) for c in e})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--md')
    ap.add_argument('--reach', type=float, default=500.0)
    ap.add_argument('--case', help='the STA case directory: view kinds from the libs it bound, relays.json, clock context')
    ap.add_argument('--phase-min-ps', type=float, default=20.0)
    a = ap.parse_args()
    p = json.load(gzip.open(Path(a.plan) / 'plan.json.gz', 'rt'))
    cd = json.loads((Path(a.plan) / 'clock_delivery.json').read_text())['tiles']
    mst = {i[0]: i[1] for i in p['insts']}
    hop = {}
    for bus, cls, bits, si, sp, di, dp, um in p['hops']:
        hop.setdefault((si, di), []).append((sp, dp, cls, um, bus))
    name_re = re.compile(r'^(.*?)/([^/]+)$')
    kinds, meta, chain_of, ctx = case_bind_map(a.case) if a.case else ({}, {}, {}, None)
    ft = flop_times(ctx)

    def kind_of(inst, m_):
        if inst in meta or m_.startswith('hfd_rly_'):
            return 'sta_relay'
        if a.case:
            return kinds.get(m_, 'untimed')
        return cd.get(m_, {}).get('view', '?')

    def split(full):
        """die instance + pin of an STA pin name (the die is flat: <inst>/<pin>[bit])"""
        m = name_re.match(full)
        if not m:
            return None, full
        inst, pin = m.groups()
        while inst not in mst and inst not in meta and '/' in inst:
            inst, rest = inst.rsplit('/', 1)
            pin = rest + '/' + pin
        return (inst if inst in mst or inst in meta else None), re.sub(r'\[\d+\]$', '', pin)

    def master(inst):
        if inst in mst:
            return mst[inst]
        if inst in meta:
            return 'hfd_rly'
        return 'TOP'

    def find_hop(si, sp, di, dp):
        """(length um, class, bus, launch end master, capture end master) of the die hop behind a start / end pair"""
        if si in meta or di in meta:        # a wire stage the STA case added: its chain gives the hop
            reg = si if si in meta else di
            ch, k = chain_of.get(reg, (None, 0))
            if ch is None:
                md = meta[reg]
                return None, 'sta_relay', md.get('original_bus'), None, None
            hops = ch.get('hops_um') or []
            # regs[k] sits between hop k (into it) and hop k + 1 (out of it)
            kk = (k + 1) if reg == si else k
            if si in meta and di in meta and chain_of.get(di, (None, 0))[0] is ch:
                kk = chain_of[di][1]
            L = hops[kk] if kk < len(hops) else None
            return L, 'sta_relay', ch.get('bus'), mst.get(ch.get('src')), mst.get(ch.get('dst'))
        hs = hop.get((si, di)) or []
        h = next((x for x in hs if x[0] == sp.split('_s')[0] or x[1] == dp), hs[0] if hs else None)
        if h is None:
            return None, None, None, None, None
        return h[3], h[2], h[4], None, None

    # coverage: how much of the plan the STA case times at all
    cov = None
    if a.case:
        c3 = defaultdict(lambda: [0, 0])
        un = defaultdict(lambda: [0, 0])
        for bus, cls, bits, si, sp, di, dp, um in p['hops']:
            ks, kd = kind_of(si, mst.get(si, 'TOP')), kind_of(di, mst.get(di, 'TOP'))
            n = (ks != 'untimed') + (kd != 'untimed')
            key = {2: 'both_ends_timed', 1: 'one_end_timed', 0: 'no_end_timed'}[n]
            c3[key][0] += 1
            c3[key][1] += bits
            for i_, k_ in ((si, ks), (di, kd)):
                if k_ == 'untimed':
                    u = un[norm(mst.get(i_, 'TOP'))]
                    u[0] += 1
                    u[1] += bits
        nm = defaultdict(int)
        for i_, m_ in mst.items():
            nm[kind_of(i_, m_)] += 1
        cov = dict(plan_hops={k: dict(hops=v[0], bits=v[1]) for k, v in c3.items()},
                   instances_by_kind=dict(nm), sta_relays_added=len(meta),
                   untimed_masters=[dict(master=k, hop_ends=v[0], bits=v[1])
                                    for k, v in sorted(un.items(), key=lambda kv: -kv[1][1])[:40]])

    res = {}
    for path in a.paths:
        corner = (re.search(r'paths_(ss|ff|tt)', Path(path).name) or [None, 'tt'])[1]
        hold = corner == 'ff'
        agg = defaultdict(lambda: dict(n=0, viol=0, wns=1e9, tns=0.0, Lmax=0.0, Lsum=0.0, Ln=0, ex=None, dphi=0.0))
        tot = dict(n=0, viol=0)
        for ln in open(path, errors='ignore'):
            f = ln.split()
            if len(f) < 3:
                continue
            sl = float(f[2]) * 1000.0
            (si, sp), (di, dp) = split(f[0]), split(f[1])
            sm, dm = master(si), master(di)
            sv, dv = kind_of(si, sm), kind_of(di, dm)
            L, hcls, bus, osm, odm = find_hop(si, sp, di, dp)
            # planned clock phase between the two flops: launch later than capture hurts setup, earlier hurts hold
            tl, tc = ft.get(si, {}).get(corner), ft.get(di, {}).get(corner)
            dphi = (tl - tc) if tl is not None and tc is not None else None
            sl0 = sl if dphi is None else (sl - dphi if hold else sl + dphi)
            if 'hfd_rrl' in (sm, dm) or (hcls and 'reset' in hcls) or sp.startswith('rst') or dp.startswith('rst'):
                cause = 'reset_net'
            elif hcls is None:
                cause = 'no_plan_hop'
            elif dphi is not None and abs(dphi) >= a.phase_min_ps and sl < 0 <= sl0:
                cause = 'clock_phase'
            elif 'placeholder_lib' in (sv, dv) or 'placeholder' in (sv, dv):
                cause = 'placeholder_lib'
            elif L is not None and L > a.reach:
                cause = 'hop_over_reach'
            elif sv in RELAY_KINDS and dv in RELAY_KINDS:
                cause = 'relay_chain'
            else:
                cause = 'master_pair_hop'
            via = f' [{re.sub(DIGITS, "#", bus or "?")}: {norm(osm or "?")} => {norm(odm or "?")}]' if sm == 'hfd_rly' or dm == 'hfd_rly' else ''
            k = (cause, f'{norm(sm)}.{sp}', f'{norm(dm)}.{dp}' + via, f'{sv}->{dv}')
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
                r['dphi'] = dphi
        rows = [dict(cause=k[0], launch=k[1], capture=k[2], views=k[3], endpoints=r['n'], violators=r['viol'],
                     wns_ps=round(r['wns'], 1), tns_ns=round(r['tns'] / 1000, 2), len_max_um=round(r['Lmax'], 1),
                     len_mean_um=round(r['Lsum'] / r['Ln'], 1) if r['Ln'] else None,
                     clock_phase_ps=None if r['dphi'] is None else round(r['dphi'], 1), example=r['ex']) for k, r in agg.items()]
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
    Path(a.out).write_text(json.dumps(dict(schema='opentallas.hbm_die_sta_classes.v2', plan=a.plan, reach_um=a.reach,
                                           case=a.case, view_kinds='STA case bind map' if a.case else 'generator table',
                                           coverage=cov,
                                           note='endpoints listed = slack < 15 ps (the STA Tcl writes only those)',
                                           reports=res), indent=1) + '\n')
    md = ['# HBM die STA: failing endpoints by cause', '']
    if cov:
        ph = cov['plan_hops']
        md += ['## Coverage: what the STA case times', '',
               'Plan hops (driver pin -> load pin) by how many of the two ends carry a Liberty in the case: ' +
               ', '.join(f'{k.replace("_", " ")} {v["hops"]:,} hops / {v["bits"]:,} b' for k, v in sorted(ph.items())) +
               f'; instances by bound kind {cov["instances_by_kind"]}; register stages the STA case added on cut buses '
               f'(hfd_rly, analytic recipe) {cov["sta_relays_added"]:,}.', '',
               'Largest untimed masters (hop ends / bits): ' +
               ', '.join(f'{u["master"]} {u["hop_ends"]:,} / {u["bits"]:,}' for u in cov['untimed_masters'][:16]), '']
    for nm, r in res.items():
        md += [f'## {nm}: {r["violators"]} violators of {r["endpoints_listed"]} endpoints below 15 ps', '',
               '| cause | classes | endpoints | violators | worst ps | TNS ns |', '|---|---:|---:|---:|---:|---:|']
        md += [f'| {c} | {v["classes"]} | {v["endpoints"]} | {v["violators"]} | {v["wns_ps"]} | {v["tns_ns"]} |'
               for c, v in sorted(r['by_cause'].items(), key=lambda kv: -kv[1]['violators'])]
        md += ['', '| cause | launch -> capture | views | endpoints | violators | worst ps | TNS ns | hop max / mean um | phase ps |',
               '|---|---|---|---:|---:|---:|---:|---|---:|']
        md += [f'| {x["cause"]} | {x["launch"]} -> {x["capture"]} | {x["views"]} | {x["endpoints"]} | {x["violators"]} | '
               f'{x["wns_ps"]} | {x["tns_ns"]} | {x["len_max_um"]} / {x["len_mean_um"]} | {x["clock_phase_ps"]} |' for x in r['classes'][:60]]
        md.append('')
    if a.md:
        Path(a.md).write_text('\n'.join(md) + '\n')
    for nm, r in res.items():
        print(nm, r['violators'], 'violators;', {c: v['violators'] for c, v in r['by_cause'].items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

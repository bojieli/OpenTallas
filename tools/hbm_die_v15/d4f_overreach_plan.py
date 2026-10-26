#!/usr/bin/env python3
"""d4f r3 over-reach classification + reset/config plan (H-DIE-R3 2026-10-17).

Every die net whose placed driver -> farthest-load Manhattan span exceeds the planning hop (405 um) gets one class:
  a_RELAY   single-driver bus the die_relay_stations exporter registers (data / control / status; cfg_no_pad host cfg)
  b_RESET   reset / por net (driver port or top input) -> regional synchronous reset tree (exporter skips them)
  c_CONFIG  static config / programme / mode net -> registered copy per region (load-time chain; exporter skips
            su_programme and would pad the rest as equal-age data, which is wrong for static fields)
  d_OTHER   top-input non-reset, multi-driver / undriven / inout nets, relay-tile hops (station home displaced)
For b and c a plan is derived per bus (driver instance + port family): sink instances -> DIE-CLOCK regional root sites
(nearest site, Manhattan), rectilinear Prim tree driver -> region sites, one registered stage every HOP of tree
distance (shared trunk counted once), plus one regional reset relay / config copy per region.
    d4f_overreach_plan.py CASE_DIR CONTRACT ROOT_SITES [--hop 405] --out FILE"""
import argparse, collections, json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_relay_pass as RP  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('case'); ap.add_argument('contract'); ap.add_argument('sites')
ap.add_argument('--hop', type=float, default=405.0); ap.add_argument('--out', required=True)
a = ap.parse_args()
C = json.loads(Path(a.contract).read_text())
pl, nets, directions, top_inputs = RP.load_case(Path(a.case), C)
SITES = [(s['region'], (s['x'], s['y'])) for s in json.loads(Path(a.sites).read_text())['sites']]
RST = re.compile(r'(^|_)(rst|reset|por)(_|n|$)|rst_n|_rstn', re.I)
CFGM = {'ot_hbm_su_programme', 'ot_static_program_target', 'ot_hbm_static_cfg_collar'}
CFGP = re.compile(r'^(cfg|io_cfg|desc|prog|strap)|(^|_)(mode|cfg|config|layer_id|group_id|sm_id|base_addr)(_|$)', re.I)
STAT = re.compile(r'(status|fault|_done$|done_|vmstat)', re.I)


def region(p):
    return min(SITES, key=lambda s: RP.md(s[1], p))


def cls(dm, dp, n):
    if n in top_inputs:
        return ('b_RESET', 'top_input_reset') if RST.search(n.split('[')[0]) else ('d_OTHER', 'top_input_nonreset')
    if dm.startswith('hbfd_rly'):
        return 'd_OTHER', 'relay_tile_hop'
    if RST.search(dp):
        return 'b_RESET', 'reset_port'
    if dm in CFGM:
        return 'c_CONFIG', 'programme_or_cfg_master'
    if CFGP.search(dp):
        return 'c_CONFIG', 'cfg_port'
    if STAT.search(dp):
        return 'a_RELAY', 'status'
    return 'a_RELAY', 'bus'


def prim(root, pts):
    P = [root] + pts; inT = {0}; dist = {0: 0.0}; L = 0.0
    best = {i: (RP.md(P[0], P[i]), 0) for i in range(1, len(P))}
    while best:
        i = min(best, key=lambda k: best[k][0]); d, u = best.pop(i); inT.add(i); dist[i] = dist[u] + d; L += d
        for j in best:
            dj = RP.md(P[i], P[j])
            if dj < best[j][0]:
                best[j] = (dj, i)
    return L, max(dist.values())


cnt = collections.Counter(); sub = collections.Counter(); grp = collections.Counter(); worst = {}
buses = collections.defaultdict(lambda: dict(bits=0, sinks=set(), span=0.0, dpt=None, cls=None, sub=None, master=None))
for n, ends in nets.items():
    if len(ends) < 2:
        continue
    drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']; lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
    if n in top_inputs:
        span = max(RP.md(x[2], y[2]) for x in lds for y in lds) if len(lds) > 1 else 0.0
        if span <= a.hop:
            continue
        k, s = cls('', '', n); dk = ('TOP', n.split('[')[0]); dm = 'TOP'
    elif len(drv) == 1 and lds and len(drv) + len(lds) == len(ends):
        d0 = drv[0]; span = max(RP.md(d0[2], l[2]) for l in lds)
        if span <= a.hop:
            continue
        dm = pl[d0[0]]['master']; k, s = cls(dm, RP.base(d0[1]), n); dk = (d0[0], RP.base(d0[1]))
    else:
        allp = [e[2] for e in ends]
        span = max(RP.md(x, y) for x in allp for y in allp)
        if span <= a.hop:
            continue
        k, s = 'd_OTHER', ('multi_driver' if len(drv) > 1 else ('undriven' if not drv else 'inout')); dm = '?'; dk = None
    cnt[k] += 1; sub[(k, s)] += 1
    if dk:
        grp[(k, f'{dm}.{dk[1]}')] += 1
    if span > worst.get(k, (0, ''))[0]:
        worst[k] = (round(span, 1), n)
    if k in ('b_RESET', 'c_CONFIG') and dk:
        b = buses[(k,) + dk]; b['bits'] += 1; b['span'] = max(b['span'], span); b['cls'] = k; b['sub'] = s; b['master'] = dm
        if dm != 'TOP':
            b['dpt'] = drv[0][2]
        for l in lds:
            b['sinks'].add(l[0])
            b.setdefault('spt', {})[l[0]] = l[2]

plan = []
for key, b in sorted(buses.items(), key=lambda kv: (kv[0][0], -kv[1]['bits'])):
    regs = collections.defaultdict(list)
    for s_, p in b['spt'].items():
        r, sp = region(p); regs[r].append(s_)
    rs = {r: dict(SITES)[r] for r in regs}
    root = b['dpt'] if b['dpt'] else (min(p[0] for p in b['spt'].values()), min(p[1] for p in b['spt'].values()))
    L, depth = prim(root, list(rs.values()))
    trunk_stages = max(0, math.ceil(L / a.hop) - len(rs))  # registered stages along the shared tree (excl. regional end)
    plan.append(dict(cls=key[0], sub=b['sub'], driver=f'{key[1]}.{key[2]}', driver_master=b['master'], bits=b['bits'],
                     sinks=len(b['sinks']), regions=sorted(regs), n_regions=len(regs), span_um=round(b['span'], 1),
                     tree_um=round(L, 1), depth_hops=max(0, math.ceil(depth / a.hop) - 1),
                     regional_relays=len(regs), trunk_stages=trunk_stages,
                     flops=b['bits'] * (len(regs) + trunk_stages)))
out = dict(schema='opentallas.hbm.d4f_overreach_plan.v1', case=str(a.case), hop_um=a.hop, sites=a.sites,
           nets_over=sum(cnt.values()), by_class=dict(cnt), by_subclass={f'{k}/{s}': v for (k, s), v in sub.most_common()},
           worst=worst, top_groups={k: [dict(driver=g, nets=v) for (kk, g), v in grp.most_common() if kk == k][:15]
                                    for k in sorted(cnt)},
           plan_totals={k: dict(buses=sum(1 for p in plan if p['cls'] == k), bits=sum(p['bits'] for p in plan if p['cls'] == k),
                                regional_relays=sum(p['regional_relays'] for p in plan if p['cls'] == k),
                                trunk_stages=sum(p['trunk_stages'] for p in plan if p['cls'] == k),
                                flops=sum(p['flops'] for p in plan if p['cls'] == k)) for k in ('b_RESET', 'c_CONFIG')},
           plan=plan)
Path(a.out).write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ('nets_over', 'by_class', 'by_subclass', 'worst', 'plan_totals')}, indent=1))
for k, v in out['top_groups'].items():
    print(k, v[:8])

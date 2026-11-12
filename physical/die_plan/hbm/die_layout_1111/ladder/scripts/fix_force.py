"""Ladder post-step (c17): lanes launched from a native internal-station bus (asbuilt internal_stations_types) must keep
fixed_cycles == source chain + receiver chain (native_istations.annotate).  For those lanes the ladder's lat pad moves
from fixed_cycles into extra FT stations on the lane's longest crossed bank slot (re-solved under the check.py station
model), so the lane's total cycles are unchanged.
usage: fix_native.py TOOLS BINDTOOLS ASBUILT IN.json OUT.json REPORT.json"""
import json, sys, copy
TOOLS, BT, ABP, INP, OUTP, REPP, BASEP = sys.argv[1:8]
sys.argv = [sys.argv[0], TOOLS]
sys.path.insert(0, BT)
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import native_istations as NI
import ladder as LD
S, LA = LD.S, LD.LA
ab = json.load(open(ABP)); sel = set(ab.get('internal_stations_types', []))
raw = json.load(open(INP))
_base = json.load(open(BASEP))['partition_types']
LADDER_TYPES = {n for n, t in raw['partition_types'].items() if _base.get(n) != t and not n.startswith('q_b000')}
del _base
P0 = S.Plan(copy.deepcopy(raw))
T = raw['partition_types']; parts = {p['name']: p for p in raw['partitions']}
pm = {p['id']: p for p in raw['ports']}; lanes = {l['id']: l for l in raw['lanes']}
outb = {}
for ln in raw['lanes']:
    a, z = pm[ln['ports'][0]], pm[ln['ports'][-1]]
    outb.setdefault((a['src']['part'], a['src']['bus']), []).append((ln, z['dst']['part'], z['dst']['bus']))
req = {}
for part, p in parts.items():
    if p['type'] not in sel: continue
    t = T[p['type']]
    for e in NI.source_entries(t, NI.selected_buses(ab, p['type'], t.get('split_of', p['type']))):
        name = e['conn'][4:]
        m = outb.get((part, name), [])
        if len(m) != 1: continue
        ln, dpart, dbus = m[0]
        tgt = T.get(parts.get(dpart, {}).get('type'), {})
        rows = [r for r in tgt.get('internal_stations', []) if r.get('conn') == 'bus:' + dbus]
        req[ln['id']] = len(e['regs_um']) + max({len(r['regs_um']) for r in rows}, default=0)
req = {k: int(v) for k, v in (x.split(":") for x in os.environ["FORCE"].split(","))} if os.environ.get("FORCE") else req
lat = raw['latency']['lanes']
old_cyc = {l: int(lat[l]['cycles']) for l in lanes}
B = LA.Builder(raw, guard_um=2.0)
P = B.P
rep = dict(moved=[], up=[], failed=[])
for lid, need in sorted(req.items()):
    ln = lanes[lid]; fx = int(ln.get('fixed_cycles', 0))
    if fx == need: continue
    extra = fx - need
    if need: ln['fixed_cycles'] = need
    else: ln.pop('fixed_cycles', None)
    if extra < 0:
        rep['up'].append(dict(lane=lid, fixed_was=fx, fixed_now=need, cycles_up=-extra)); continue
    # longest crossed slot, bank partitions first
    cands = []
    for part, slot, a, b in P0.lane_crossings(lid):
        s = P0.slot(part, slot)
        if not s: continue
        fi, wi, _, _ = P0.geom_to_die(part, (s['in_face'], s['in_window_um'], s['in_layers'], 'lsb_low'))
        fo, wo, _, _ = P0.geom_to_die(part, (s['out_face'], s['out_window_um'], s['out_layers'], 'lsb_low'))
        pa, pb = LA.Builder.face_pt(P0, part, fi, wi), LA.Builder.face_pt(P0, part, fo, wo)
        L = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
        if parts[part]['type'] not in LADDER_TYPES:
            continue          # only types the ladder already changes (never q_b000*, never an untouched type)
        cands.append(('_b0' in part, L, part, slot, fi, wi, fo, wo, pa, pb))
    cands.sort(key=lambda c: (not c[0], -c[1]))
    done = False
    for isb, L, part, slot, fi, wi, fo, wo, pa, pb in cands:
        sl = next(x for x in T[parts[part]['type']]['ft_slots'] if x['name'] == slot)
        k = int(sl['stations'])
        got = LD.slot_dp(B, part, pa, abs(wi[1] - wi[0]) / 2.0, pb, k - 1 + extra)
        if got is None or len(got) + 1 != k + extra:
            continue
        s0 = (pa[0] + LD.INSET[fi][0], pa[1] + LD.INSET[fi][1])
        sl['stations'] = k + extra
        sl['regs_um'] = [[LD.r4(v) for v in P.to_type(part, q)] for q in [s0] + got]
        for kk in ('bit_sites_um', 'bit_site_cell_um'): sl.pop(kk, None)
        sl['note'] = (sl.get('note', '') + f' | DIE-LAYOUT-HBM LADDER c18 11-11: +{extra} station(s) = lat pad moved '
                      f'from fixed_cycles (native internal-station lane: fixed_cycles = source + receiver = {need})').strip(' |')
        rep['moved'].append(dict(lane=lid, extra=extra, part=part, slot=slot, stations=[k, k + extra], route_um=round(L)))
        done = True
        break
    if not done:
        rep['failed'].append(dict(lane=lid, extra=extra))
P2 = S.Plan(raw)
for lid in req:
    new = P2.lane_latency(lid)
    lat[lid] = dict(new, param=lat[lid].get('param', 'LAT_' + lid.upper()))
rep['cycles_changed'] = {l: [old_cyc[l], int(lat[l]['cycles'])] for l in req if old_cyc[l] != int(lat[l]['cycles'])}
open(OUTP, 'w').write(json.dumps(raw, indent=1) + '\n')
json.dump(rep, open(REPP, 'w'), indent=1)
print(json.dumps(rep, indent=1))

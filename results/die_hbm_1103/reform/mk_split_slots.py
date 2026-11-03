#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 2 (1): sub-block slots of the DIE-HBM-61/SPLIT READY cores inside their parent slots.

The SPLIT lane cut each core into sub-blocks behind a composition module with the SAME ports as the kit core
(<core>__split.sv), so the parent slot, its pins, stations and die taps stay; this places the sub-blocks INSIDE the slot:
tiles along the slot's long axis, areas by the sub cell estimates (identical subs equal), one 8.64-um street between
tiles, every tile edge on the 8.64 lattice of the core frame (parent origins are on it), each sub gets its own centre
clock entry (one clock per sub) and the per-instance die-type position (orient applied).  Pin demand per sub (split.json)
vs its perimeter at 5 pins/um (M4 W/E + M5 N/S) and est fill (census cell area x sub share) are reported as targets.
The hard_cores swap (one entry per sub) lands with the composition RTL in the partition content (source event), so bind /
G0C see one hierarchy; until then this sidecar is the plan of record for the sub floorplan.  Cores not READY
(rp3lp3h_n/s, q3_body/edge, fused_lane, tkm) keep their slot as placeholder.
    python3 mk_split_slots.py PLAN_DIR SPLIT_SPEC.json REFORM_CENSUS.json   (writes PLAN_DIR/split_slots.json)"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); SPEC = json.loads(Path(sys.argv[2]).read_text()); C = {c['module']: c for c in json.loads(Path(sys.argv[3]).read_text())}
P = json.loads((d / 'die_plan.json').read_text())
G, ST = 8.64, 8.64
snap = lambda v: round(round(v / G) * G, 3)
out = dict(schema='opentallas.hbm_split_slots.v1', street_um=ST, cores=[])
for sp in SPEC:
    m = sp['core']
    insts = [(tn, h) for tn, t in P['partition_types'].items() for h in t.get('hard_cores') or [] if h['module'] == m]
    if not insts:
        out['cores'].append(dict(core=m, status='NOT IN PLAN')); continue
    W, H = insts[0][1]['outline_um']
    subs = [(s['module'], s.get('cells', 0)) for s in sp['subs'] for _ in range(s.get('count', 1))]
    tot = sum(c for _, c in subs) or len(subs)
    ax = 0 if W >= H else 1
    L = (W, H)[ax]; free = L - ST * (len(subs) - 1)
    cuts, pos = [], 0.0
    for i, (sm, c) in enumerate(subs):
        ln = free * (c or 1) / tot if tot else free / len(subs)
        end = L if i == len(subs) - 1 else snap(pos + ln)
        cuts.append((pos, end)); pos = end + ST
    ca = (C.get(m) or {}).get('cell_area')
    tiles = []
    for (sm, c), (a, b) in zip(subs, cuts):
        o = [a, 0.0] if ax == 0 else [0.0, a]
        wh = [round(b - a, 3), H] if ax == 0 else [W, round(b - a, 3)]
        sinfo = next(s for s in sp['subs'] if s['module'] == sm)
        pins = sinfo.get('pins')
        cap = int(2 * (wh[0] + wh[1]) * 5)
        fill = round(ca * (c or 1) / tot / (wh[0] * wh[1]), 3) if ca else None
        tiles.append(dict(module=sm, offset_um=[round(o[0], 3), round(o[1], 3)], outline_um=wh,
                          aspect=round(max(wh) / min(wh), 2), cells_est=c, est_fill=fill, pins=pins, pin_capacity_5um=cap,
                          pins_fit=(pins is None or pins <= cap), clock=sinfo.get('clock'),
                          clock_entry_core_frame=[round(o[0] + snap(wh[0] / 2), 3), round(o[1] + snap(wh[1] / 2), 3)]))
    per = []
    for tn, h in insts:
        ox, oy = h['origin_um']; orr = h.get('orient', 'R0')
        rows = []
        for k, tl in enumerate(tiles):
            x0, y0 = tl['offset_um']; w, hh = tl['outline_um']
            if orr in ('MY', 'R180'): x0 = W - x0 - w
            if orr in ('MX', 'R180'): y0 = H - y0 - hh
            rows.append(dict(sub=k, module=tl['module'], inst=f"{h['inst']}.u_s{k}", origin_um=[round(ox + x0, 3), round(oy + y0, 3)],
                             outline_um=tl['outline_um'], orient=orr))
        per.append(dict(type=tn, inst=h['inst'], orient=orr, subs=rows))
    out['cores'].append(dict(core=m, sha=sp['sha'], status='READY (sub slots planned)', composition=sp.get('composition'),
                             slot_um=[W, H], axis='x' if ax == 0 else 'y', tiles=tiles, instances=len(per),
                             new_designs=sorted({t['module'] for t in tiles}), placements=per,
                             added_cycles=sp.get('added_cycles'), note=sp.get('note')))
(d / 'split_slots.json').write_text(json.dumps(out, indent=1) + '\n')
for c in out['cores']:
    print(c['core'], c.get('status'), [(t['module'][-6:], t['outline_um'], t['est_fill'], t['pins'], t['pin_capacity_5um']) for t in c.get('tiles', [])])

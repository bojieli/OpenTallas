#!/usr/bin/env python3
"""DIE-HBM-41 d41a widen-in-window delta (results script, no shared tool change).
Widens EXISTING plan lanes in place: every hop window of the lane must already hold the new width (+epoch) at the
plan face budget (schema.window_for, face_pins_per_um / pin_track_max); windows, faces, layers, stations, cycles,
outlines and cores do not change.  Port widths, the src/dst type buses (once per type for mirror lanes on a shared
type) and the crossed ft slots grow; explicit ft bit sites (bit_sites_um) get the new payload bits on the nearest free
legal row sites to the stage centroid (RowAllocator, cores + 1.08 keep-off blocked, every existing site/station
reserved; same lattice as ft_corridor/ft_nudge), the epoch site stays last.
    widen.py PLANDIR actions.json OUTDIR      actions = [{"lane": id, "add": bits}, ...]
"""
import json, os, sys, hashlib, shutil
from pathlib import Path
import numpy as np
T = '/srv/opentallas-scratch2/claude/wt/die-hbm-41/tools/die_plan'
sys.path.insert(0, T); sys.path.insert(0, str(Path(T).parents[1]))
import schema as S
from tools.die_trial.legal_sites import RowAllocator
KEEPOFF = 1.08; CELL = (1.404, .27)

def sha12(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]

def maxpins(P, lo, hi, layers):
    per = float(P.budgets.get('face_pins_per_um', 6.0)); tm = float(P.budgets.get('pin_track_max', 0.6))
    a, b = 1, int((hi - lo) * per) + 2
    while S.window_for(lo, b, layers, P.layers, per_um=per, track_max=tm) <= hi + 1e-6: b *= 2
    while a < b:
        m = (a + b + 1) // 2
        if S.window_for(lo, m, layers, P.layers, per_um=per, track_max=tm) <= hi + 1e-6: a = m
        else: b = m - 1
    return a

def main():
    plan, acts, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), Path(sys.argv[3])
    raw = json.loads((plan / 'die_plan.json').read_text()); P = S.Plan(raw)
    T_ = raw['partition_types']
    rep = dict(base=str(plan), base_sha=sha12(plan / 'die_plan.json'), lanes=[], buses={}, slots={}, failed=[])
    done_bus, done_slot = {}, {}
    for a in acts:
        lid, add = a['lane'], int(a['add'])
        ln = P.lanes[lid]; ports = [P.ports[q] for q in ln['ports']]
        w0 = ports[0]['width']; w1 = w0 + add
        bad = []
        for x in ports:
            if x['width'] != w0: bad.append(f"{x['id']} width {x['width']} != {w0}")
            for _, _, win in S.port_segments(x):
                lo, hi = sorted(win); cap = maxpins(P, lo, hi, x['layers'])
                if cap < w1 + 1: bad.append(f"{x['id']} window {hi-lo:.2f} um holds {cap} pins < {w1+1}")
        if bad:
            rep['failed'].append(dict(lane=lid, add=add, why=bad)); continue
        rp = {p['id']: p for p in raw['ports']}
        for x in ports:
            rp[x['id']]['width'] = w1
            x['width'] = w1
        ends = [(ports[0]['src']['part'], ports[0]['src']['bus']), (ports[-1]['dst']['part'], ports[-1]['dst']['bus'])]
        for part, bus in ends:
            tn = P.parts[part]['type']; key = (tn, bus)
            b = next(b for b in T_[tn]['buses'] if b['name'] == bus)
            if key in done_bus:
                assert done_bus[key] == (w0, w1), (key, done_bus[key], w0, w1); continue
            assert b['width'] == w0, (key, b['width'], w0)
            if b.get('window_um'):
                lo, hi = sorted(b['window_um']); cap = maxpins(P, lo, hi, b['layers'])
                assert cap >= w1 + 1, (key, cap)
            b['width'] = w1; done_bus[key] = (w0, w1); rep['buses'][f'{tn}/{bus}'] = [w0, w1]
        for part, slot, _, _ in P.lane_crossings(lid):
            if not slot: continue
            tn = P.parts[part]['type']; key = (tn, slot)
            if key in done_slot:
                assert done_slot[key] == (w0, w1), key; continue
            s = next(s for s in T_[tn]['ft_slots'] if s['name'] == slot)
            assert s['width'] == w0, (key, s['width'], w0)
            for k in ('in_window_um', 'out_window_um'):
                lo, hi = sorted(s[k]); cap = maxpins(P, lo, hi, s[k.replace('window_um', 'layers')])
                assert cap >= w1 + 1, (key, k, cap)
            s['width'] = w1; done_slot[key] = (w0, w1)
            rep['slots'][f'{tn}/{slot}'] = dict(width=[w0, w1], bit_sites=bool(s.get('bit_sites_um')))
        rep['lanes'].append(dict(lane=lid, width=[w0, w1], cycles=raw['latency']['lanes'].get(lid, {}).get('cycles')))
    # bit sites for widened slots, per type
    by_type = {}
    for k, v in rep['slots'].items():
        if v['bit_sites']:
            tn, sl = k.split('/', 1); by_type.setdefault(tn, []).append(sl)
    for tn, sls in by_type.items():
        t = T_[tn]; w, h = t['outline_um']
        boxes = list(S.placed_macro_boxes(t, halo=KEEPOFF).values())
        al = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL, column_pitch=2.16,
                          row_pitch=.27, origin=(4.32, 4.32))
        for s in t['ft_slots']:
            cw, ch = s.get('bit_site_cell_um', CELL)
            for st in s.get('bit_sites_um') or []:
                for x, y in st: al.reserve_rectangle((x, y, x + cw, y + ch))
            if not s.get('bit_sites_um'):
                for x, y in s.get('regs_um') or []: al.reserve_rectangle((x - 2, y - 2, x + 2, y + 2))
        for s_ in t.get('internal_stations', []) or []:
            for x, y in s_.get('regs_um', []) or []: al.reserve_rectangle((x - 2, y - 2, x + 2, y + 2))
        for bb in (t.get('clock') or {}).get('branch_buffers') or []:
            xy = bb.get('xy_um') or bb.get('at_um') or bb.get('xy')
            if xy: al.reserve_rectangle((xy[0] - 2.5, xy[1] - 2.5, xy[0] + 2.5, xy[1] + 2.5))
        for sl in sls:
            s = next(s for s in t['ft_slots'] if s['name'] == sl)
            cw, ch = s.get('bit_site_cell_um', CELL)
            n_new = s['width'] + 1 - len(s['bit_sites_um'][0]); dmax = 0.0
            for j, st in enumerate(s['bit_sites_um']):
                c = np.mean([[x + cw / 2, y + ch / 2] for x, y in st], axis=0)
                pts, info = al.allocate(c, n_new, max_radius_um=60.)
                assert len(pts) == n_new, (tn, sl, j, len(pts))
                new = [[round(float(p[0] - cw / 2), 6), round(float(p[1] - ch / 2), 6)] for p in pts]
                for x, y in new: al.reserve_rectangle((x, y, x + cw, y + ch))
                dmax = max(dmax, float(np.max(np.abs(pts - c).sum(axis=1))))
                s['bit_sites_um'][j] = st[:-1] + new + [st[-1]]
            rep['slots'][f'{tn}/{sl}']['new_sites_per_stage'] = n_new
            rep['slots'][f'{tn}/{sl}']['max_new_site_from_centroid_um'] = round(dmax, 2)
    raw['die']['label'] = 'DIE-HBM-41 d41a widen-in-window | ' + raw['die'].get('label', '')
    out.mkdir(parents=True, exist_ok=False)
    for f in plan.iterdir():
        if f.name in ('die_plan.json',): continue
        try: os.link(f, out / f.name) if f.is_file() else os.symlink(f.resolve(), out / f.name)
        except OSError: shutil.copy2(f, out / f.name)
    (out / 'die_plan.json').write_text(json.dumps(raw, indent=1))
    rep['out_sha'] = sha12(out / 'die_plan.json')
    (out / 'd41a_widen_report.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(lanes=len(rep['lanes']), failed=rep['failed'], out_sha=rep['out_sha']), indent=1))
    for k, v in rep['slots'].items(): print('SLOT', k, v)

if __name__ == '__main__':
    main()

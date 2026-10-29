#!/usr/bin/env python3
"""DIE-QC-36 M6-entry backbone re-derivation on the legal re-sited clock cells (QC-001 fix order step 3).

Fork of Codex jog_backbones.py --joint-clock --all-bases (same Index/covered/TrackRouter geometry, same island
coverage + M6/M7 SIGNAL/OBS/PG/future-column clearance, same 0.192x0.08 M8 landing / 0.08/0.32 shielded-tree witness).
One change of intent (DIE-QC-35 root cause 1): the M8 witness is the ROUTER'S OWN trunk/driver track for that pin
(fixed_wires stacks[].riser_from y of a no-backbone prebuild on the same sites), so the M7 window always contains the
track the shared trunk actually uses; neighbouring trunks no longer compete for per-pin witnesses. Only when no column
works at the router track does it fall back to the nearest witness (counted, reported).
The per-pin M1..M7 clock base stacks (clock_base_access26_minarea.json, old sites) are shifted with their cell.
usage: dqc36_backbone.py --fixed-wires E1/fixed_wires.json --resite-report R --old-tree T --new-tree T2 --lef L
        --cell-windows W --geometry G --pg PG --clock-base CB [--reserved-metal F] [--max-jog 1.5] --out DIR
"""
import argparse, json, math, sys, re, collections
from pathlib import Path

ap = argparse.ArgumentParser()
for a in ('fixed-wires', 'old-tree', 'new-tree', 'netlist', 'lef', 'cell-windows', 'geometry', 'pg', 'clock-base', 'out', 'jog-src'):
    ap.add_argument('--'+a, required=True)
ap.add_argument('--reserved-metal', action='append', default=[])
ap.add_argument('--max-jog', type=float, default=1.5)
a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, a.jog_src)
import jog_backbones as J

# cell x shifts (old tree -> new tree)
old = json.load(open(a.old_tree))['sites']; new = json.load(open(a.new_tree))['sites']
dx = {('ck_'+k): round(new[k][0]-old[k][0], 6) for k in new if abs(new[k][0]-old[k][0]) > 1e-9}
text = open(a.netlist).read(); pinnet = {}
for master, name, pins in re.findall(r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\w+)\s*\(([^;]+)\);', text):
    pp = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', pins)); pinnet[name] = (master, pp)
lef = open(a.lef).read(); acc = {}
import importlib.util
def lef_access(master):
    if master not in acc:
        m = re.search(r'(?ms)^MACRO\s+'+re.escape(master)+r'\s*\n(.*?)^END\s+'+re.escape(master)+r'\s*$', lef); body = m[1]; d = {}
        for pin in ('A', 'Y'):
            pm = re.search(r'(?ms)^\s*PIN\s+'+pin+r'\s*\n(.*?)^\s*END\s+'+pin+r'\s*$', body)
            layers = re.findall(r'LAYER\s+(\w+)\s*;(.*?)(?=LAYER|\Z)', pm[1], re.S)
            rects = [tuple(map(float, r)) for l, c in layers if l == 'M1' for r in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', c)]
            ty = .09 if pin == 'A' else .18
            bars = [r for r in rects if r[3]-r[1] > r[2]-r[0] and r[2]-r[0] >= .0179 and r[1]+.008 <= ty <= r[3]-.008]
            ch = min(bars, key=lambda r: r[0]) if pin == 'A' else max(bars, key=lambda r: r[2]); d[pin] = (ch[0]+ch[2])/2
        acc[master] = d
    return acc[master]
# old pin x per (net) occurrences for moved cells -> shift map keyed (net, round(old_px,3))
shift_at = {}
for cell, d in dx.items():
    master, pp = pinnet[cell]; k = cell[3:]; ox = old[k][0]
    for p in ('A', 'Y'):
        shift_at[(pp[p], round(ox+lef_access(master)[p], 3))] = d

holes = json.load(open(a.cell_windows))['cells']
print('STAGE geometry', flush=True)
g = json.load(open(a.geometry)); dbu = g['dbu']; ix = J.Index()
for inst, pin, l, *xy in g['signal_shapes']:
    if l in ('M6', 'M7'): ix.add([f'SIGNAL:{inst}/{pin}', l, *[v/dbu for v in xy]])
for inst, l, *xy in g['obstructions']:
    if l in ('M6', 'M7'): ix.add([f'OBS:{inst}', l, *[v/dbu for v in xy]])
for net, l, *xy in g['existing_supplies']:
    if l in ('M6', 'M7'): ix.add([net, l, *[v/dbu for v in xy]])
phase, count, pitch = g['tracks']['M7']['X'][0]; phase /= dbu; pitch /= dbu
del g
base = json.load(open(a.clock_base)); shifted_base = 0; new_base = []
for i in range(0, len(base), 7):
    grp = base[i:i+7]; net = grp[0][0]; cx = round((grp[0][2]+grp[0][4])/2, 3)
    d = shift_at.get((net, cx), 0.0)
    if d: shifted_base += 1
    for r in grp:
        r2 = [r[0], r[1], r[2]+d, r[3], r[4]+d, r[5]]; new_base.append(r2); ix.add(r2)
print('BASE stacks', len(base)//7, 'shifted', shifted_base, 'expected', len(shift_at), flush=True)
json.dump(new_base, open(out/'clock_base_resite.json', 'w'))
del base

wires = json.load(open(a.fixed_wires)); pins = {}
for w in wires:
    for s in w['stacks']:
        if s['cell'].startswith('port:'): continue
        key = s['cell'], s['pin']
        if key in pins: raise ValueError('duplicate base '+str(key))
        pins[key] = dict(cell=key[0], pin=key[1], net=w['name'], base_xy_um=s['xy'], router_ty=s['riser_from'][1])
for w in wires:
    for s in w['stacks']:
        x, y = s.get('m6_entry_xy', s['xy']); ix.add([w['name'], 'M7', x-.016, y-8.667, x+.016, y+8.667])
del wires
print('ALL_ACTUAL_BASES', len(pins), flush=True)
router = J.C128.TrackRouter(dict(width=.08, space=.32, rf=.5, cf=1.15), 'VSS', J.DCM.DEFAULT_TRACKS, 8.64)
router.reserve(J.C128.pg_shapes(json.load(open(a.pg))))
for f in a.reserved_metal:
    sh = json.load(open(f))
    for s in sh: ix.add(s)
    router.reserve(J.C128.pg_shapes(sh))
records, bad, mode = [], [], collections.Counter()
for n, f in enumerate(pins.values()):
    cell, pin, net = f['cell'], f['pin'], f['net']; x, y = f['base_xy_um']; parts = holes[cell.removeprefix('ck_')]
    if any(q['in_core'] for q in parts): raise ValueError('clock island intersects hardcore')
    hs = [q['rect_die_um'] for q in parts]
    columns = sorted({round(phase+k*pitch, 6) for k in range(math.ceil((x-a.max_jog-phase)/pitch), math.floor((x+a.max_jog-phase)/pitch)+1)}, key=lambda q: abs(q-x))
    rty = round(f['router_ty'], 6)
    ys_all = sorted({round(.04+k*.08, 6) for k in range(math.ceil((min(h[1] for h in hs)+.027-.04)/.08), math.floor((max(h[3] for h in hs)-.027-.04)/.08)+1)}, key=lambda q: abs(q-y))
    found = None
    for tag, ys in (('router_track', [rty]), ('fallback_nearest', [q for q in ys_all if abs(q-rty) > 1e-6])):
        for bx in columns:
            local = [[net, 'M6', min(x, bx)-.016, y-.016, max(x, bx)+.016, y+.016], [net, 'M6', bx-.035, y-.016, bx+.035, y+.016], [net, 'M7', bx-.016, y-.036, bx+.016, y+.036]]
            if any(not J.covered(r, hs) or ix.hits(r) for r in local): continue
            for ty in ys:
                riser = [net, 'M7', bx-.016, min(y, ty)-.027, bx+.016, max(y, ty)+.027]
                if not J.covered(riser, hs) or ix.hits(riser): continue
                if router.place('M8', ty, bx-.096, bx+.096, net, keep=(ty, ty), dry=True)[0] is None: continue
                found = dict(cell=cell, pin=pin, net=net, entry_xy_um=[x, y], backbone_xy_um=[bx, y], m7_window_um=[min(y, ty), max(y, ty)],
                             m8_witness_y_um=ty, m6_jog_um=round(abs(bx-x), 6), geometry=local+[riser], witness_mode=tag, router_track_y_um=rty,
                             proof='DIE-QC-36 re-sited cells; witness = router trunk/driver track; island union + M6/M7 SIGNAL/OBS/PG/future-column clear; M8 .08/.32 witness')
                for r in local+[riser]: ix.add(r)
                router.reserve([*J.C128.pg_shapes([[net, 'M8', bx-.096, ty-.04, bx+.096, ty+.04]])])
                break
            if found: break
        if found: break
    if found: records.append(found); mode[found['witness_mode']] += 1
    else: bad.append(f)
    if n % 5000 == 0: print(f'JOG_PROGRESS {n+1}/{len(pins)} pass={len(records)} fail={len(bad)} {dict(mode)}', flush=True)
reserved = []
for r in records:
    reserved.extend(r['geometry']); x, y = r['backbone_xy_um'][0], r['m8_witness_y_um']
    reserved.append([r['net'], 'M8', x-.376, y-.32, x+.376, y+.32])
(out/'joint_clock_reserved.json').write_text(json.dumps(reserved)+'\n')
res = dict(status='FAIL' if bad else 'PASS_GEOMETRY', physical_route=False, records=records, failures=bad, clock_width_um=.08, tree_spacing_um=.32,
           m6_width_um=.032, max_jog_um=a.max_jog, witness_modes=dict(mode), shifted_base_stacks=shifted_base,
           note='DIE-QC-36: witness = router track; no physical route; prebuild with --backbone-plan is the check')
(out/'backbone_plan.json').write_text(json.dumps(res)+'\n')
summ = {k: v for k, v in res.items() if k not in ('records', 'failures')}; summ.update(records=len(records), unresolved=len(bad), sample_fail=bad[:20])
(out/'summary.json').write_text(json.dumps(summ, indent=1)+'\n'); print(res['status'], len(records), len(bad), dict(mode), flush=True)

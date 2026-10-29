#!/usr/bin/env python3
"""DIE-QC-37 RANGE-WINDOW M6-entry backbone (QC-001, COORD ruling [DIE-QC-36-PARK] (2)).

Same geometry contract as dqc36_backbone.py / Codex jog_backbones.py (island union coverage, M6/M7 SIGNAL/OBS/PG/
future-column clearance, M6 jog <= --max-jog, clock width .08 / space .32 downstream), ONE change of intent:
  * no per-pin M8 witness and NO pre-route M8 landing reservation (bb1 reserved a .192x.08 pad per pin with a
    shielded dry-place -> 25,204 pins forced to a fallback single track -> E2 17,859 no_clock_track);
  * each pin gets an allowed-track RANGE m7_window_um = [lo, hi]: every M8 track y on its backbone column bx whose
    M7 riser from the pin row is island-covered and clear of other-net M6/M7 shapes, within STACK_RISER_MAX_UM
    (2.5 um, the island window the fixed tree is sized for); pins of DIFFERENT nets on the same column split the
    column at the midpoint (disjoint windows -> no riser short whichever track the router picks).
  The fixed-tree router then picks the trunk track inside the driver window; M8 landings are reserved after that
  pick (two-pass: joint reserve is derived from the prebuild's fixed_wires, not here).
Variants (12.17(3), one pass, two outputs): R1 = full range; R2 = range clipped to [min(y,rty)-1, max(y,rty)+1]
around the E1 router track rty (shorter risers, closer to the proven E1 track solution).
Clock base stacks: the row-keyed re-sited seed clock_base_resite_v2.json (exactly 8,156 moved stacks; fixes the
(net,x) aliasing Codex flagged) is read as-is, not re-shifted.
"""
import argparse, json, math, sys, collections
from pathlib import Path

ap = argparse.ArgumentParser()
for a in ('fixed-wires', 'cell-windows', 'geometry', 'clock-base-resited', 'out', 'jog-src'):
    ap.add_argument('--'+a, required=True)
ap.add_argument('--reserved-metal', action='append', default=[])
ap.add_argument('--max-jog', type=float, default=1.5)
ap.add_argument('--riser-max', type=float, default=2.5)
ap.add_argument('--r2-margin', type=float, default=1.0)
ap.add_argument('--riser-island', choices=('on', 'off'), default='on', help='off: M7 riser need not lie in the PG island union (still clear of every actual PG/signal/OBS/other-pin M6/M7 shape); PG access is replanned around it')
ap.add_argument('--tags', default='R1,R2')
ap.add_argument('--column-select', choices=('nearest', 'track'), default='nearest', help='track: among columns within max-jog take the nearest whose clear riser range contains the E1 router track, else the widest range')
a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, a.jog_src)
import jog_backbones as J

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
base = json.load(open(a.clock_base_resited))
for r in base: ix.add(r)
print('BASE stacks', len(base)//7, flush=True)
del base
for f in a.reserved_metal:
    for s in json.load(open(f)): ix.add(s)

wires = json.load(open(a.fixed_wires)); pins = {}
for w in wires:
    for s in w['stacks']:
        if s['cell'].startswith('port:'): continue
        key = s['cell'], s['pin']
        if key in pins: raise ValueError('duplicate base '+str(key))
        pins[key] = dict(cell=key[0], pin=key[1], net=w['name'], base_xy_um=s['xy'], router_ty=s['riser_from'][1])
future = {}
for w in wires:
    for s in w['stacks']:
        x, y = s.get('m6_entry_xy', s['xy']); r = [w['name'], 'M7', x-.016, y-8.667, x+.016, y+8.667]
        if not s['cell'].startswith('port:'): future[(s['cell'], s['pin'])] = (len(ix.rows), x)
        ix.add(r)
del wires
print('ALL_ACTUAL_BASES', len(pins), flush=True)

tracks_y = lambda lo, hi: [round(.04+k*.08, 6) for k in range(math.ceil((lo-.04)/.08-1e-9), math.floor((hi-.04)/.08+1e-9)+1)]
def near_m7(net, bx, ylo, yhi, sp=.032):
    """every other-net M7 row within spacing of the column strip and the y span (one bin scan per pin)"""
    x0, x1 = bx-.016, bx+.016; out, seen = [], set()
    for v in range(math.floor((x0-sp)/ix.B), math.floor((x1+sp)/ix.B)+1):
        for k in ix.bins.get(('M7', v), ()):
            if k in seen: continue
            seen.add(k); q = ix.rows[k]
            if q[0] == net or q[5] < ylo-sp or q[3] > yhi+sp: continue
            if max(0, max(x0, q[2])-min(x1, q[4])) < sp: out.append(q)
    return out
def clear_range(net, bx, x, y, hs):
    ys = tracks_y(y-a.riser_max, y+a.riser_max); cand = near_m7(net, bx, y-a.riser_max-.03, y+a.riser_max+.03)
    def clear(ty):
        r = [net, 'M7', bx-.016, min(y, ty)-.027, bx+.016, max(y, ty)+.027]
        if a.riser_island == 'on' and not J.covered(r, hs): return False
        for q in cand:
            dx = max(0, max(r[2], q[2])-min(r[4], q[4])); dy = max(0, max(r[3], q[3])-min(r[5], q[5]))
            if math.hypot(dx, dy) < .032-1e-7: return False
        return True
    hi = lo = y
    for t in [t for t in ys if t >= y]:
        if not clear(t): break
        hi = t
    for t in [t for t in ys if t < y][::-1]:
        if not clear(t): break
        lo = t
    return [lo, hi]
if a.column_select == 'track':   # every pin gets a record column -> default-column guards are moot (pass 1b releases them anyway)
    for key, (k, fx) in future.items():
        r = ix.rows[k]; ix.rows[k] = [r[0], r[1], -1e9, -1e9, -1e9+.001, -1e9+.001]
# pass 1: backbone column per pin (local M6 jog + pad + M7 stub only; nothing above M7 reserved)
chosen, bad = {}, []
for n, f in enumerate(pins.values()):
    cell, pin, net = f['cell'], f['pin'], f['net']; x, y = f['base_xy_um']; parts = holes[cell.removeprefix('ck_')]
    if any(q['in_core'] for q in parts): raise ValueError('clock island intersects hardcore')
    hs = [q['rect_die_um'] for q in parts]
    columns = sorted({round(phase+k*pitch, 6) for k in range(math.ceil((x-a.max_jog-phase)/pitch), math.floor((x+a.max_jog-phase)/pitch)+1)}, key=lambda q: abs(q-x))
    why = collections.Counter(); got = None
    for bx in columns:
        local = [[net, 'M6', min(x, bx)-.016, y-.016, max(x, bx)+.016, y+.016], [net, 'M6', bx-.035, y-.016, bx+.035, y+.016], [net, 'M7', bx-.016, y-.036, bx+.016, y+.036]]
        if not all(J.covered(r, hs) for r in local): why['local_outside_island'] += 1; continue
        h = next((ix.hits(r) for r in local if ix.hits(r)), None)
        if h: why['local_hit:'+str(h[0]).split(':')[0][:8]] += 1; continue
        if a.column_select == 'nearest': got = (bx, local); break
        lo, hi = clear_range(net, bx, x, y, hs); rty = f['router_ty']
        score = (lo-1e-6 <= rty <= hi+1e-6, hi-lo)
        if got is None or score > got[2]: got = (bx, local, score)
        if score[0]: break
    if got:
        for r in got[1]: ix.add(r)
        chosen[(cell, pin)] = (got[0], got[1], hs)
    else:
        bad.append(dict(f, diagnosis=dict(why)))
    if n % 10000 == 0: print(f'COL_PROGRESS {n+1}/{len(pins)} pass={len(chosen)} fail={len(bad)}', flush=True)
print('PASS1 columns', len(chosen), 'fail', len(bad), flush=True)
# pass 1b: a pin moved to another backbone column no longer needs its old future column (default-column guard);
# release those guards and retry only the failed pins (same contract otherwise)
released = 0
for key, (bx, _, _) in chosen.items():
    k, fx = future.get(key, (None, None))
    if k is not None and abs(bx-fx) > 1e-6:
        r = ix.rows[k]; ix.rows[k] = [r[0], r[1], -1e9, -1e9, -1e9+.001, -1e9+.001]; released += 1
retry, bad = bad, []
for f in retry:
    cell, pin, net = f['cell'], f['pin'], f['net']; x, y = f['base_xy_um']; hs = [q['rect_die_um'] for q in holes[cell.removeprefix('ck_')]]
    columns = sorted({round(phase+k*pitch, 6) for k in range(math.ceil((x-a.max_jog-phase)/pitch), math.floor((x+a.max_jog-phase)/pitch)+1)}, key=lambda q: abs(q-x))
    got = None
    for bx in columns:
        local = [[net, 'M6', min(x, bx)-.016, y-.016, max(x, bx)+.016, y+.016], [net, 'M6', bx-.035, y-.016, bx+.035, y+.016], [net, 'M7', bx-.016, y-.036, bx+.016, y+.036]]
        if all(J.covered(r, hs) for r in local) and not any(ix.hits(r) for r in local): got = (bx, local); break
    if got:
        for r in got[1]: ix.add(r)
        chosen[(cell, pin)] = (got[0], got[1], hs)
    else: bad.append(f)
print('PASS1b released future columns', released, 'recovered', len(retry)-len(bad), 'still fail', len(bad), flush=True)

# pass 2: maximal clear riser range per pin on its column (ix now holds every pin's local geometry)
rng = {}
for n, (key, (bx, local, hs)) in enumerate(chosen.items()):
    f = pins[key]; x, y = f['base_xy_um']; lo, hi = clear_range(f['net'], bx, x, y, hs)
    rng[key] = [lo, hi]
    if n % 10000 == 0: print(f'RANGE_PROGRESS {n+1}/{len(chosen)}', flush=True)
# split columns shared by different nets at the midpoint between pin rows
bycol = collections.defaultdict(list)
for key, (bx, _, _) in chosen.items(): bycol[round(bx, 4)].append(key)
split = 0
for col, keys in bycol.items():
    if len(keys) < 2: continue
    keys.sort(key=lambda k: pins[k]['base_xy_um'][1])
    for k0, k1 in zip(keys, keys[1:]):
        if pins[k0]['net'] == pins[k1]['net']: continue
        y0, y1 = pins[k0]['base_xy_um'][1], pins[k1]['base_xy_um'][1]
        if True:
            mid = (y0+y1)/2; gap = .16 + .04  # half clock space + half width each side of the midpoint
            h0 = min(rng[k0][1], mid-gap); l1 = max(rng[k1][0], mid+gap)
            if h0 < rng[k0][1] or l1 > rng[k1][0]: split += 1
            rng[k0][1] = max(h0, y0); rng[k1][0] = min(l1, y1)
print('PASS2 ranges; column splits', split, flush=True)

def emit(tag, clip):
    records, cover = [], collections.Counter()
    for key, (bx, local, hs) in chosen.items():
        f = pins[key]; x, y = f['base_xy_um']; lo, hi = rng[key]; rty = round(f['router_ty'], 6)
        if clip:
            lo = max(lo, min(min(y, rty)-a.r2_margin, y)); hi = min(hi, max(max(y, rty)+a.r2_margin, y))
        lo, hi = round(min(lo, y), 6), round(max(hi, y), 6)
        ntr = len([t for t in tracks_y(lo, hi)])
        cover['router_track_in_window' if lo-1e-6 <= rty <= hi+1e-6 else 'router_track_outside'] += 1
        cover['tracks_%s' % ('0' if ntr == 0 else '1' if ntr == 1 else '2-4' if ntr <= 4 else '5+')] += 1
        records.append(dict(cell=key[0], pin=key[1], net=f['net'], entry_xy_um=[x, y], backbone_xy_um=[bx, y], m7_window_um=[lo, hi],
                            m8_witness_y_um=None, m6_jog_um=round(abs(bx-x), 6), geometry=local, router_track_y_um=rty, witness_mode='range',
                            proof='DIE-QC-37 range window: island union + M6/M7 SIGNAL/OBS/PG/future-column/other-pin clear riser on every track in window; '
                                  'different-net column split at midpoint; M8 landing reserved after the router pick'))
    o = out/tag; o.mkdir(exist_ok=True)
    reserved = [r for rec in records for r in rec['geometry']]
    (o/'joint_clock_local_reserved.json').write_text(json.dumps(reserved)+'\n')
    res = dict(status='FAIL' if bad else 'PASS_GEOMETRY', physical_route=False, records=records, failures=bad, clock_width_um=.08, tree_spacing_um=.32,
               m6_width_um=.032, max_jog_um=a.max_jog, riser_max_um=a.riser_max, variant=tag, r2_margin_um=a.r2_margin if clip else None,
               window_census=dict(cover), column_splits=split, riser_island=a.riser_island, column_select=a.column_select,
               note='DIE-QC-37: range windows, no M8 witness/pad pre-reserve; prebuild with --backbone-plan is the check')
    (o/'backbone_plan.json').write_text(json.dumps(res)+'\n')
    summ = {k: v for k, v in res.items() if k not in ('records', 'failures')}; summ.update(records=len(records), unresolved=len(bad), sample_fail=bad[:20])
    (o/'summary.json').write_text(json.dumps(summ, indent=1)+'\n'); print(tag, res['status'], len(records), len(bad), dict(cover), flush=True)
t1, t2 = a.tags.split(','); emit(t1, False); emit(t2, True)

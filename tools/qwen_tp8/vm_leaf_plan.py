#!/usr/bin/env python3
"""VM leaf plan (claude/qwen-tp8-vm-1013, 2026-10-13): ot_qfd_vm_grp x 8 as directly die-assembled hard leaves.

  python3 tools/qwen_tp8/vm_leaf_plan.py NET_DUMP OUT.json

Per region (= one ot_qfd_vm_grp): 8 ot_qfd_vm_bank_t, 6 ot_qfd_vm_su_t, 16 ot_qfd_vm_xfifo8_t, 3 ot_qfd_vm_su1024_t
(closed views, bytes unchanged, R0), plus sized register leaves, every one its own clock root:
  bx relay   8 x ot_qwen_tree_delay1_t (512 b, the grp's NRX - 1 relay, free-running)       bank q (E) -> xfifo8 bx (S)
  in relay   14 x ot_qwen_tree_delay2_t (512 b x 2: pin flop + NRI - 1; wd per bank, swd per SU bank)
  rowrd      1 x NEW ot_qfd_vm_rowrd_t (registered 8:1 of bx -> ro, 512 b; 3 x 512 + selects)
  ctl        1 x NEW ot_qfd_vm_gctl_t  (address / mask / enable pin flops + NRI relays, tags, cnt / ovf, rtg / pgw / xg)
Die-level x transport (the parent's rot1 / rot2 rebuilt, see vm_plane_lanes.py): 32 x NEW ot_qfd_vm_xplane_t in the band
between the two region rows (two rows of 16 over the middle two region columns: an outer column cut then carries 8,192 b,
the centre cut 16,384 b) + me-enabled relay leaves ot_qfd_vm_xrelay_t in explicit bays: full-height double-column strips
at <= 432 um pitch (a 260-um window admits ~2.4k new bits at 0.60, so the centre cut needs relays over the whole height) (free-running delay tiles
cannot carry x: xo moves on engine edges only).
Region map (parent analysis 1): region r at column slot FOLD[r % 4], row r // 4 (r and r + 4 stacked); bank ring folded.
Geometry verdict against the it2 placement: 0 hard overlaps, >= 20 um to every kept it2 hard instance, 2.16 um grid.
PLAN ONLY: no view of a NEW leaf exists; sizes are from measured cell areas (see 'sizing')."""
import json, sys, hashlib, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_lef_pins as L
ROOT = Path(__file__).resolve().parents[2]
VIEW = {'ot_qfd_vm_bank_t': 'physical/ref_tile/qfd_vm_bank_t/views/ot_qfd_vm_bank_t/ot_qfd_vm_bank_t.lef',
        'ot_qfd_vm_su_t': 'physical/ref_tile/qfd_vm_su_t/views/ot_qfd_vm_su_t/ot_qfd_vm_su_t.lef',
        'ot_qfd_vm_xfifo8_t': 'physical/ref_tile/qfd_vm_xfifo8_codex/views/ot_qfd_vm_xfifo8_t/ot_qfd_vm_xfifo8_t.lef',
        'ot_qfd_vm_su1024_t': 'physical/ref_tile/qfd_vm_su1024_codex/views/ot_qfd_vm_su1024_t/ot_qfd_vm_su1024_t.lef'}
# clock sinks per root: closed leaves from their routed records / RTL; planned leaves from the RTL they replace
SINKS = {'ot_qfd_vm_bank_t': 1600, 'ot_qfd_vm_su_t': 1600, 'ot_qfd_vm_xfifo8_t': 3523, 'ot_qfd_vm_su1024_t': 1100,
         'ot_qwen_tree_delay1_t': 512, 'ot_qwen_tree_delay2_t': 1024, 'ot_qfd_vm_rowrd_t': 1536 + 16 * 8,
         'ot_qfd_vm_gctl_t': 2 * (8 * 8 * 2 + 8 * 16 + 6 * 10 + 2 * 10 + 2 * 16 + 30) + 120, 'ot_qfd_vm_xplane_t': 3 * 1024 + 80,
         'ot_qfd_vm_xrelay_t': 512 + 16}
NEW = {'ot_qwen_tree_delay1_t': (10.8, 64.8), 'ot_qwen_tree_delay2_t': (17.28, 64.8), 'ot_qfd_vm_rowrd_t': (86.4, 64.8),
       'ot_qfd_vm_gctl_t': (86.4, 43.2), 'ot_qfd_vm_xplane_t': (129.6, 43.2), 'ot_qfd_vm_xrelay_t': (17.28, 64.8)}
X0, Y0, RW, RH, GAP, BAND = 13284.0, 17249.76, 1166.4, 1080.0, 0.0, 187.92
UX = (47.52, 475.2)                    # unit columns (in relay | bank | bx relay | xfifo8 pair), 380.16 wide, between the relay strips
FOLD = (0, 3, 1, 2)                     # column slot of r % 4: shift 8 hops 2,1,2,1 slots, shift 16 hops 3,1
BFOLD = (0, 7, 1, 6, 2, 5, 3, 4)        # physical bank slot (unit column = slot % 2, row = slot // 2) of bank b: ring folded
G = lambda v: round(round(v / 2.16) * 2.16, 6)

def region_origin(r):
    return G(X0 + FOLD[r % 4] * (RW + GAP)), G(Y0 + (r // 4) * (RH + BAND))

def build():
    size = {m: L.read(ROOT / p)[0] for m, p in VIEW.items()}; size.update(NEW)
    ch = []; bays = []
    def add(n, m, x, y, **k):
        ch.append(dict(n=n, m=m, x=G(x), y=G(y), w=size[m][0], h=size[m][1], orient='R0', layer_cap='M5', **k))
    def strip(n, x, y, r):   # full-height double column of x relay leaves: 8 nodes of 2 x 2 tiles (2,048 b), pitch 133.92
        for k in range(8): bays.append(dict(n=f'{n}_{k}', x=G(x), y=G(y + 4.32 + 133.92 * k), w=36.72, h=131.76, tiles=4, region=r))
    for r in range(8):
        X, Y = region_origin(r)
        for b in range(8):
            s = BFOLD[b]; ux = X + UX[s % 2]; yb = Y + 10.8 + (s // 2) * 205.2; bank = 8 * r + b
            add(f'vm_g{r}_b{b}_in', 'ot_qwen_tree_delay2_t', ux, yb + 60.48, region=r, role='wd pin flop + NRI relay')
            add(f'vm_g{r}_b{b}', 'ot_qfd_vm_bank_t', ux + 21.6, yb, region=r, logical_bank=bank)
            add(f'vm_g{r}_b{b}_bx', 'ot_qwen_tree_delay1_t', ux + 244.08, yb + 60.48, region=r, role='bx NRX relay')
            for h in range(2):
                add(f'vm_g{r}_b{b}_xf{h}', 'ot_qfd_vm_xfifo8_t', ux + 259.2, yb + (21.6, 108.0)[h], region=r, logical_bank=bank, bits=[256 * h, 256 * h + 255])
        su = [(924.48, 10.8 + 257.04 * k) for k in range(4)] + [(UX[0] + 21.6, 831.6), (UX[1] + 21.6, 831.6)]
        for k, (sx, sy) in enumerate(su):
            add(f'vm_g{r}_su{k}', 'ot_qfd_vm_su_t', X + sx, Y + sy, region=r, operand=k // 2, su_bank=k % 2)
            add(f'vm_g{r}_su{k}_in', 'ot_qwen_tree_delay2_t', X + sx - 21.6, Y + sy + 86.4, region=r, role='swd pin flop + NRI relay (per SU bank replica)')
        for k in range(3): add(f'vm_g{r}_ans{k}', 'ot_qfd_vm_su1024_t', X + UX[0] + 265.68, Y + 831.6 + 43.2 * k, region=r, operand=k)
        add(f'vm_g{r}_rowrd', 'ot_qfd_vm_rowrd_t', X + UX[1] + 265.68, Y + 831.6, region=r)
        add(f'vm_g{r}_gctl', 'ot_qfd_vm_gctl_t', X + UX[1] + 265.68, Y + 918.0, region=r)
        for nm, bx in (('sW', 4.32), ('sA', 432.0), ('sB', 859.68)) + ((('sE', RW + 4.32),) if FOLD[r % 4] == 3 else ()):
            strip(f'vm_g{r}_{nm}', X + bx, Y, r)
    yb = Y0 + RH
    # 32 plane leaves in 8 groups of 4 (two abutting pairs, one per band row) centred on the eight middle relay strips, so a
    # lane's last hop is vertical from the strip (a horizontal jog inside the band windows is what saturated the first cut)
    PX = [X0 + sl * RW + bx for sl, bx in ((0, 859.68), (1, 4.32), (1, 432.0), (1, 859.68), (2, 4.32), (2, 432.0), (3, 4.32), (3, 432.0))]   # not (2, 859.68): 1.1-2.2k existing vertical bits per window there
    for j in range(32): add(f'vm_xplane_{j}', 'ot_qfd_vm_xplane_t', PX[j // 4] + (-114.48, 19.44)[j % 2], yb + (4.32, 129.6)[(j % 4) // 2], plane=j, region=-1)
    # centre-cut relief: the strips of the two middle columns continue two nodes (268 um, one fine window) below the bottom
    # row and above the top row wherever the it2 placement leaves >= 20 um (main() drops the others)
    for r in range(8):
        if FOLD[r % 4] in (1, 2):
            X, Y = region_origin(r)
            for nm, bx in (('sW', 4.32), ('sA', 432.0), ('sB', 859.68)) + ((('sE', RW + 4.32),) if FOLD[r % 4] == 2 else ()):
                for k in range(2):
                    y = Y - 4.32 - 133.92 * (k + 1) if r < 4 else Y + RH + 4.32 + 133.92 * k
                    bays.append(dict(n=f'vm_g{r}_{nm}_x{k}', x=G(X + bx), y=G(y), w=36.72, h=131.76, tiles=4, region=r, optional=True))
    return ch, bays, size

def ov(a, b, gap=0.0):
    return a['x'] < b['x'] + b['w'] + gap - 1e-6 and b['x'] < a['x'] + a['w'] + gap - 1e-6 and a['y'] < b['y'] + b['h'] + gap - 1e-6 and b['y'] < a['y'] + a['h'] + gap - 1e-6

def main():
    net, out = sys.argv[1:]; d = json.loads(Path(net).read_text()); ch, bays, size = build()
    gone = ('sp_vector_memory', 'sp_su64_sfu'); rly = ('qfd_rly', 'qkd_rly')
    old = [i for i in d['insts'] if i['n'] not in gone and not i['m'].startswith(rly)]
    relays = [i for i in d['insts'] if i['m'].startswith(rly)]
    env = dict(x=X0, y=Y0, w=4 * RW + 43.2, h=2 * RH + BAND)
    su64 = dict(n='sp_su64_sfu_reservation', m='UNSIZED_SU64_ACTUAL_LEAF_ENVELOPE', x=16424.64, y=19662.72, w=1991.52, h=2829.6)
    dropped = [b['n'] for b in bays if b.get('optional') and any(ov(b, o, 20.0) for o in old + [su64])]
    bays = [b for b in bays if b['n'] not in dropped]
    objs = ch + [dict(b, m='ot_qfd_vm_xrelay_t_BAY') for b in bays]
    hard = sum(ov(a, o) for a in objs for o in old); near = sum(ov(a, o, 20.0) for a in objs for o in old)
    peer = sum(ov(a, b) for k, a in enumerate(objs) for b in objs[k + 1:]); tight = sum(ov(a, b, 2.16) for k, a in enumerate(objs) for b in objs[k + 1:])
    offgrid = sum(abs(v / 2.16 - round(v / 2.16)) > 1e-6 for a in objs for v in (a['x'], a['y']))
    xs = [a['x'] for a in objs] + [a['x'] + a['w'] for a in objs]; ys = [a['y'] for a in objs] + [a['y'] + a['h'] for a in objs]
    tl = [i for i in d['insts'] if i['m'] == 'qfd_tile_nk']; cols = sorted({i['x'] for i in tl}); j = max(range(len(cols) - 1), key=lambda k: cols[k + 1] - cols[k])
    spine = (cols[j] + tl[0]['w'], cols[j + 1])
    cnt = collections.Counter(c['m'] for c in ch); area = {m: round(n * size[m][0] * size[m][1] / 1e6, 4) for m, n in cnt.items()}
    relay_tiles = sum(b['tiles'] for b in bays)
    roots = {m: dict(instances=n, sinks_per_root=SINKS[m], new_leaf=m in NEW and not m.startswith('ot_qwen_tree')) for m, n in cnt.items()}
    roots['ot_qfd_vm_xrelay_t'] = dict(instances_max=relay_tiles, sinks_per_root=SINKS['ot_qfd_vm_xrelay_t'], new_leaf=True)
    pins = {m: {b: dict(n=v['n'], dir=v['dir'], faces=v['faces'], layers=v['layers'], centroid=v['centroid'], bbox=v['bbox'])
                for b, v in L.groups(ROOT / p)[1].items()} for m, p in VIEW.items()}
    ok = hard == 0 and near == 0 and peer == 0 and offgrid == 0 and min(xs) > spine[0] + 20 and max(xs) < spine[1] - 20 and not any(ov(a, su64, 20.0) for a in objs)
    rep = dict(status='LEAF_PLAN_ONLY', owner='claude/qwen-tp8-vm-1013',
        inputs={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [net, __file__] + [str(ROOT / v) for v in VIEW.values()]},
        slot=dict(shape='4 x 2 regions of 1166.4 x 1080 um (three full-height x-relay strips each) + 187.92 um x-plane band between the rows (r and r + 4 stacked); planes in 8 groups of 4 on the middle strips',
                  origin_um=[round(min(xs), 3), round(min(ys), 3)], size_um=[round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3)],
                  area_mm2=round((max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6, 4), spine_x_um=[round(spine[0], 3), round(spine[1], 3)],
                  region_origins={r: list(region_origin(r)) for r in range(8)}, fold=dict(column_slot_of_r_mod_4=FOLD, bank_slot_of_b=BFOLD),
                  old_slot_um=[2332.776, 2073.576], core_envelope=dict(origin_um=[X0, Y0], size_um=[round(4 * RW + 43.2, 3), round(2 * RH + BAND, 3)], area_mm2=round((4 * RW + 43.2) * (2 * RH + BAND) / 1e6, 4),
                      note='regions + band; origin_um / size_um above is the bounding box including the centre-cut relief bays below and above the middle columns')),
        geometry=dict(verdict='PASS' if ok else 'FAIL', hard_overlaps_it2=hard, within_20um_of_it2_hard=near, peer_overlaps=peer, peer_pairs_closer_than_2p16=tight,
                      off_2p16_grid=offgrid, kept_it2_hard_instances=len(old), removed=list(gone), su64_reservation=su64,
                      it2_relay_objects_inside_envelope=sum(ov(env, i) for i in relays),
                      note='it2 relay objects (qfd_rly* / qkd_rly*) are regenerated with their chains, as in the Codex plans; they are counted, not checked.'),
        leaf_count=dict(cnt), leaf_area_mm2=area, closed_child_area_mm2=round(sum(area[m] for m in VIEW), 4),
        placed_leaf_area_mm2=round(sum(area.values()), 4), x_relay_bay_tiles=relay_tiles, x_relay_bay_area_mm2=round(relay_tiles * 17.28 * 64.8 / 1e6, 4),
        clock_roots=roots, max_sinks_per_root=max(v['sinks_per_root'] for v in roots.values()), root_rule='<= 15000 sinks per root: every leaf is its own root; no group-level tree',
        sizing=dict(delay_tiles='closed-kit outlines (physical/ref_tile/qfd_tree_delay{1,2}_t), views under closure as qfd_tree_delay{N}_t-u52-baaa52fff',
                    xplane='3 x 1024 flops (pin, rot1, rot2) + 2 x 1024 mux8: ~2.9k um2 cells in 5,599 um2 (util 0.52)',
                    xrelay='512 enabled flops + 16 me replicas in 1,120 um2 (delay2 outline; mux + DFF per bit ~0.55 um2 -> util ~0.27)',
                    rowrd='1,536 flops + 512 x (4:1 AND-OR x 2 + 2:1) in 5,599 um2', gctl='~1,000 flops in 3,732 um2'),
        optional_bays_dropped_for_clearance=dropped, real_pins=pins, children=ch, x_relay_bays=bays)
    Path(out).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('slot', 'geometry', 'leaf_count', 'leaf_area_mm2', 'closed_child_area_mm2', 'placed_leaf_area_mm2', 'x_relay_bay_tiles', 'max_sinks_per_root')}, default=str)[:2600])

if __name__ == '__main__': main()

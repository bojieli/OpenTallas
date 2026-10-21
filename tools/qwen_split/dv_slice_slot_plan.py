"""Resize the 12 dv_slice2 slots of a DV receiver plan inside the reticle (QW2-NEXTGEN 10-21).

The die is 12 columns (W5..W0 | seam | E0..E5) on a 2592-um pitch; each column stacks cluster rows 0-1, the dvs slice
row and cluster rows 2-3, and a slice's N / S faces carry its own column's cw / rs words face to face (dv_case: the
slice N / S pins mirror the cluster contract x ranges).  A slot wider than the column pitch therefore cannot be placed
by moving columns: the whole row would grow by 12 x the extra width.  Growing the slot in y keeps every face-to-face
link and only moves cluster rows 2-3 (everything above the slice row in the array) N by the extra height; the W-column
service / PHY origins stay where they are.

usage: dv_slice_slot_plan.py SOURCE.json OUT.json --slot-w W --slot-h H --sgap G [--record REC.json]
The die outline follows dv_case.apply_dv: slice row +G, rows 2-3 +2G, W/H = max extent + 21.6 um.
"""
import argparse
import copy
import json
import math

RETICLE_W, RETICLE_H = 33000.0, 26000.0
EDGE = 21.6          # dv_case.apply_dv die margin
LAT = 43.2


def _on_lattice(v):
    return abs(v / LAT - round(v / LAT)) < 1e-6


def outline(insts, sgap):
    """die W/H as dv_case.apply_dv computes them (slice gap applied)."""
    ys = next(i['y'] for i in insts if i['n'] == 'dvs_W0')
    xs, ye = [], []
    for i in insts:
        y = i['y']
        if i['n'].startswith('dvs_'):
            y += sgap
        elif i['n'].startswith('c16_') and i['y'] > ys:
            y += 2 * sgap
        xs.append(i['x'] + i['w'])
        ye.append(y + i['h'])
    return round(max(xs) + EDGE, 3), round(max(ye) + EDGE, 3)


def plan(source, slot_w, slot_h, sgap):
    out = copy.deepcopy(source)
    I = out['insts']
    sl = [i for i in I if i['n'].startswith('dvs_')]
    w0, h0 = sl[0]['w'], sl[0]['h']
    if any(abs(i['w'] - w0) > .01 or abs(i['h'] - h0) > .01 for i in sl):
        raise ValueError('slices are not one slot size')
    W0, H0 = outline(I, sgap)
    dw, dh = round(slot_w - w0, 3), round(slot_h - h0, 3)
    pitch = sorted(i['x'] for i in sl)
    pitch = min(b - a for a, b in zip(pitch, pitch[1:]))
    rec = dict(source_slot_um=[w0, h0], requested_slot_um=[slot_w, slot_h], slice_gap_um=sgap,
               baseline_die_um=[W0, H0], reticle_um=[RETICLE_W, RETICLE_H], column_pitch_um=round(pitch, 3), slices=len(sl))
    if dw > 1e-6:
        # every column is one slice wide: x growth widens the whole row by n_slices * dw
        rec['x_growth_die_w_um'] = round(W0 + len(sl) * dw, 3)
        raise ValueError(f'slot +{dw} um in x widens all {len(sl)} columns: die W {rec["x_growth_die_w_um"]} > '
                         f'{RETICLE_W} (column pitch {pitch}); grow the slot in y instead')
    if dh < 0 or not _on_lattice(dh) or not _on_lattice(sgap):
        raise ValueError('slot height growth and slice gap must be nonnegative multiples of 43.2 um')
    ys = next(i['y'] for i in I if i['n'] == 'dvs_W0')
    moved = 0
    for i in I:
        if i['n'].startswith('dvs_'):
            i['h'] = round(slot_h, 3)
            i['w'] = round(slot_w, 3)
        elif i['n'].startswith('c16_') and i['y'] > ys:
            i['y'] = round(i['y'] + dh, 3)
            moved += 1
    # W-column (x < array west edge) must not collide with the moved rows: it is left of the array by construction
    ax = min(i['x'] for i in I if i['n'].startswith(('c16_', 'dvs_')))
    for i in I:
        if not i['n'].startswith(('c16_', 'dvs_')) and i['x'] + i['w'] > ax + 1e-3 and i['m'] != 'outline_marker':
            raise ValueError(f'{i["n"]} overlaps the array columns (x {i["x"]}+{i["w"]} > {ax})')
    W1, H1 = outline(I, sgap)
    if W1 > RETICLE_W + 1e-6 or H1 > RETICLE_H + 1e-6:
        raise ValueError(f'die {W1} x {H1} exceeds the reticle {RETICLE_W} x {RETICLE_H}')
    rec.update(slot_um=[slot_w, slot_h], slot_area_mm2=round(slot_w * slot_h / 1e6, 4),
               cluster_rows_moved_north_um=dh, moved_cluster_instances=moved,
               die_um=[W1, H1], die_mm2=round(W1 * H1 / 1e6, 3),
               headroom_um=[round(RETICLE_W - W1, 3), round(RETICLE_H - H1, 3)],
               kept='every slice <-> cluster cw / rs link stays face to face; slice <-> slice lateral pitch unchanged; '
                    'W-column service / PHY origins unchanged',
               scope='planned slot only; GEN relay / reach / clock / bind gates decide')
    out['slice_slot_plan'] = rec
    out['source'] = out.get('source', '') + f' | QW2-NEXTGEN slice slot {slot_w} x {slot_h} (rows 2-3 N +{dh} um)'
    return out, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('out')
    ap.add_argument('--slot-w', type=float, required=True)
    ap.add_argument('--slot-h', type=float, required=True)
    ap.add_argument('--sgap', type=float, default=0.0)
    ap.add_argument('--record')
    a = ap.parse_args()
    out, rec = plan(json.load(open(a.source)), a.slot_w, a.slot_h, a.sgap)
    json.dump(out, open(a.out, 'w'), indent=1)
    if a.record:
        json.dump(rec, open(a.record, 'w'), indent=2)
    print('SLICE_SLOT', json.dumps(rec))


if __name__ == '__main__':
    main()

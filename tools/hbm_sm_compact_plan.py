#!/usr/bin/env python3
"""HBM SM compact-first parent plan (owner 10-14 18:45, HANDOFF 0ag): remove the pt_w / pt_e pass-through band of every
SM tile cluster, keep their real transport registers as distributed slices (rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv,
OT_SMH_COMPACT_PT), route the E-W transit buses over the tiles, and measure what the SM parent then occupies with the
CLOSED leaf outlines (LEF SIZE) in the native relative placement.

Inputs (all on main): the native child origins (results/arch/hier_contract_1011/handoff/r25gq_sm_child_origins.json),
the leaf LEFs of the kits it names, and the compact transport slice map (candidate.json).  Nothing here re-routes a closed
view or changes RTL.  Output: exact tile / SM child origins (0.864 x 2.16 lattice), overlap + outside checks, the E-W cut
(bus bits vs free horizontal tracks at every 2.16-um vertical cut through a tile, from the leaves' own M6 obstructions),
and the per-SM / per-die area against the hfd_sm slot.

    python3 tools/hbm_sm_compact_plan.py --out results/arch/hbm_die_v14/compact_sm_plan_1014
"""
import argparse, json, math, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / 'results/arch/hier_contract_1011/handoff/r25gq_sm_child_origins.json'
CAND = ROOT / 'results/arch/hbm_native_1013/sm/compact_transport_1014/candidate.json'
LEAF_KIT = dict(xs='smh_xs_ref_p45m', bdc='smh_bdc_ref_p50', tct='smh_tct_ref_p45', tcl='smh_tcl_ref_p45',
                pt_w='smh_pt_w_ref_p45h', pt_e='smh_pt_e_ref_p40s')
GX, GY = 0.864, 2.16                  # placement lattice (site grid and M5 pitch), as every SM origin on main
M6_PITCH, M8_PITCH = 0.064, 0.080     # platform make_tracks (horizontal layers)
SLOT = (3214.08, 1131.84)             # hfd_sm in v12-v14
DIE_FREE_MM2 = 341.25                 # v14 area table (hbmdie-v13/win15/cuts/area_v14.json, 100-um grid)


def up(v, g):
    return math.ceil(round(v / g, 6)) * g


def lef(kit, cell):
    t = (ROOT / f'physical/ref_tile/{kit}/views/{cell}/{cell}.lef').read_text()
    w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t).groups())
    obs, cur = [], None
    for line in t[t.index('\n  OBS') if '\n  OBS' in t else t.index('OBS'):].splitlines():
        m = re.match(r'\s*LAYER (\S+)', line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r'\s*RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', line)
        if m and cur == 'M6':
            obs.append(tuple(map(float, m.groups())))
    faces = dict(W=0, E=0, N=0, S=0)
    for m in re.finditer(r'PIN (\S+)(.*?)END \1', t, re.S):
        if re.search(r'USE (POWER|GROUND)', m.group(2)):
            continue
        r = re.search(r'RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', m.group(2))
        if r:
            x0, y0, x1, y1 = map(float, r.groups())
            dd = dict(W=x0, E=w - x1, S=y0, N=h - y1)
            faces[min(dd, key=dd.get)] += 1
    return dict(w=w, h=h, m6=obs, faces=faces)


def xform(r, o, w, h):
    x0, y0, x1, y1 = r
    if o in ('MY', 'R180'):
        x0, x1 = w - x1, w - x0
    if o in ('MX', 'R180'):
        y0, y1 = h - y1, h - y0
    return x0, y0, x1, y1


def dense_tile(kids, L, a, slice_a, mirror):
    """Leaf group lf[0] above the slice strip (xs S face down onto it), lf[1] its MX image below; per group: xs | tct
    side by side (gap cs), bdc above xs and the two tcl above tct (gap cb); tile margin = halo."""
    w = lambda k: L[k]['w']
    h = lambda k: L[k]['h']
    m, cb, cs = a.halo, a.cb, a.cs
    lfw = w('xs') + cs + max(w('tct'), 2 * w('tcl') + cs)
    lfh = max(h('xs') + cb + h('bdc'), h('tct') + cb + h('tcl'))
    W = up(2 * m + lfw, GX * 5)
    strip_h = up(slice_a / lfw, GY)
    lo0 = m                                   # lower group base
    s0 = up(lo0 + lfh + m, GY)                # strip
    hi0 = up(s0 + strip_h + m, GY)            # upper group base
    Hn = up(hi0 + lfh + m, GY)
    rel = dict(xs=(0.0, 0.0), bdc=(86.4, h('xs') + cb), tct=(w('xs') + cs, 0.0),
               h0=(w('xs') + cs, h('tct') + cb), h1=(w('xs') + cs + w('tcl') + cs, h('tct') + cb))
    out = []
    for c in kids:
        g = 0 if 'g_lf[0]' in c['name'] else 1
        key = c['name'].split('.')[-1]
        key = dict(u_xs='xs', u_bdc='bdc', u_tr='tct', u_h0='h0', u_h1='h1')[key]
        k = c['cell'].replace('ot_hbm_accel_smh_', '')
        rx, ry = rel[key]
        x = m + rx
        if g == 0:
            y = hi0 + ry
        else:                                  # MX image about the strip
            y = lo0 + lfh - ry - h(k)
        if mirror:
            x = W - x - w(k)
        out.append(dict(c, x=round(up(x, GX) if not mirror else x, 4), y=round(up(y, GY) if g == 0 else y, 4)))
    xs_ = [c['x'] for c in out] + [c['x'] + c['outline_um'][0] for c in out]
    return out, W, Hn, min(xs_), max(xs_), s0, strip_h


def field_fit(model, Wsm, Hsm, clear=21.6):
    import hashlib, pickle
    raw = model.read_bytes()
    I = pickle.loads(raw)['insts']
    blk = [(n, x, y, w, h) for n, (mst, k, x, y, w, h, o) in I.items() if k not in ('waypoint', 'sm')]
    sms = {n: (x, y, w, h) for n, (mst, k, x, y, w, h, o) in I.items() if k == 'sm'}
    sw, sh = Hsm, Wsm                      # R90
    res = dict(model=str(model), model_sha256=hashlib.sha256(raw).hexdigest(), orientation='R90',
               sm_rotated_um=[round(sw, 4), round(sh, 4)], clearance_um=clear, quadrants={})
    for q, lo in (('SW', 0), ('SE', 8), ('NW', 16), ('NE', 24)):
        ns = [f'sm{i}' for i in range(lo, lo + 8)]
        x0 = min(sms[n][0] for n in ns)
        x1 = max(sms[n][0] + sms[n][2] for n in ns)
        y0 = min(sms[n][1] for n in ns)
        y1 = max(sms[n][1] + sms[n][3] for n in ns)
        rows = []
        for n in (8, 7, 6, 5, 4):
            g = ((x1 - x0) - n * sw) / (n - 1)
            if g < 0:
                rows.append(dict(n=n, fits=False, why=f'{n} x {sw:.2f} > field width {x1 - x0:.2f}'))
                continue
            best = None
            for k in range(-60, 61):
                yy = (y0 + y1) / 2 - sh / 2 + 27 * k
                hit = sorted({b[0] for i in range(n) for b in blk
                              if x0 + i * (sw + g) - clear < b[1] + b[3] and b[1] < x0 + i * (sw + g) + sw + clear
                              and yy - clear < b[2] + b[4] and b[2] < yy + sh + clear})
                if best is None or len(hit) < len(best[1]):
                    best = (yy, hit)
            rows.append(dict(n=n, gap_um=round(g, 2), y_um=round(best[0], 2), blocking=best[1]))
        res['quadrants'][q] = dict(field_um=[round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)], rows=rows)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--halo', type=float, default=21.6, help='leaf <-> slice strip clearance (um)')
    ap.add_argument('--util', type=float, default=0.45, help='slice strip std-cell utilisation')
    ap.add_argument('--reset-overhead', type=float, default=1.20, help='slice std area vs the old pt std cells')
    ap.add_argument('--m8-share', type=float, default=0.75, help='M8 fraction left for signals after die PG')
    ap.add_argument('--dense', action='store_true', help='also re-pack each leaf group with tighter channels '
                    '(xs-bdc / tct-tcl --cb, xs-tct and tcl-tcl --cs, tile margin --halo); native orientations kept')
    ap.add_argument('--cb', type=float, default=43.2)
    ap.add_argument('--cs', type=float, default=21.6)
    ap.add_argument('--model', type=Path, help='v14 die model pickle (hbm_r25gq_windows --dump-model): R90 field fit of the '
                    'compact SM in each quadrant SM field with every non-SM block (relays / stations excluded) as obstacle')
    a = ap.parse_args(argv)
    orig = json.loads(ORIG.read_text())
    cand = json.loads(CAND.read_text())
    L = {k: lef(kit, f'ot_hbm_accel_smh_{k}') for k, kit in LEAF_KIT.items()}
    out = dict(schema='opentallas.hbm.compact_sm_plan.v1', status='PLAN_NOT_QUALIFIED',
               owner_rule='HANDOFF 0ag (owner 18:45): compact SM first, 32 SMs, pass-through band removed, buses over tiles',
               sources=dict(origins=str(ORIG.relative_to(ROOT)), transport=str(CAND.relative_to(ROOT)),
                            leaf_kits=LEAF_KIT), tiles={})
    # ------------------------------------------------------------------ compact tile (both tile_eg / tile_wg)
    pt_std = cand['area']['old_pt_std_cells_um2_per_tile']
    slice_a = pt_std * a.reset_overhead / a.util
    for tname, tc in orig['tile_clusters'].items():
        W, H = tc['parent_outline_um']
        ch = [c for c in tc['children'] if c['cell'] not in ('ot_hbm_accel_smh_pt_w', 'ot_hbm_accel_smh_pt_e')]
        band = [c for c in tc['children'] if c not in ch]
        by0 = min(c['y'] for c in band)
        lo = [c for c in ch if c['y'] < by0]
        hi = [c for c in ch if c['y'] >= by0]
        lo_top = max(c['y'] + c['outline_um'][1] for c in lo)
        hi_bot = min(c['y'] for c in hi)
        hi_top = max(c['y'] + c['outline_um'][1] for c in hi)
        x0s = min(c['x'] for c in ch)
        x1s = max(c['x'] + c['outline_um'][0] for c in ch)
        strip_w = x1s - x0s
        strip_h = up(slice_a / strip_w, GY)
        s0 = up(lo_top + a.halo, GY)
        new_hi_bot = up(s0 + strip_h + a.halo, GY)
        dy = new_hi_bot - hi_bot
        Hn = up(hi_top + dy + (H - hi_top), GY)
        kids = []
        for c in ch:
            k = c['cell'].replace('ot_hbm_accel_smh_', '')
            kids.append(dict(name=c['name'], cell=c['cell'], kit=LEAF_KIT[k], x=c['x'], y=round(c['y'] + (dy if c in hi else 0), 4),
                             orient=c['orient'], outline_um=[L[k]['w'], L[k]['h']]))
        if a.dense:
            kids, W, Hn, x0s, x1s, s0, strip_h = dense_tile(kids, L, a, slice_a, mirror=tname.endswith('_wg'))
        strip = dict(name='u_pt_slices', kind='distributed transport slices (96 x <=128 b per tile, std cells)',
                     box_um=[round(x0s, 4), round(s0, 4), round(x1s, 4), round(s0 + strip_h, 4)],
                     std_area_um2=round(pt_std * a.reset_overhead, 1), util=a.util,
                     slices=len(cand['slices_per_tile']))
        # overlap / outside
        boxes = [(c['name'], c['x'], c['y'], c['x'] + c['outline_um'][0], c['y'] + c['outline_um'][1]) for c in kids]
        boxes.append(('u_pt_slices', *strip['box_um']))
        ov = [(p[0], q[0]) for i, p in enumerate(boxes) for q in boxes[i + 1:]
              if p[1] < q[3] - 1e-6 and q[1] < p[3] - 1e-6 and p[2] < q[4] - 1e-6 and q[2] < p[4] - 1e-6]
        outside = [b[0] for b in boxes if b[1] < -1e-6 or b[2] < -1e-6 or b[3] > W + 1e-6 or b[4] > Hn + 1e-6]
        off = [c['name'] for c in kids if abs(c['x'] / GX - round(c['x'] / GX)) > 1e-4 or abs(c['y'] / GY - round(c['y'] / GY)) > 1e-4]
        # E-W cut: free horizontal M6 tracks at every vertical cut (leaf M6 obstructions only; M6 between leaves free)
        obs = []
        for c in kids:
            k = c['cell'].replace('ot_hbm_accel_smh_', '')
            for r in L[k]['m6']:
                x0, y0, x1, y1 = xform(r, c['orient'], L[k]['w'], L[k]['h'])
                obs.append((c['x'] + x0, c['y'] + y0, c['x'] + x1, c['y'] + y1))
        demand = max(L['pt_w']['faces']['W'], L['pt_w']['faces']['E'], L['pt_e']['faces']['W'], L['pt_e']['faces']['E'])
        worst = None
        xs = [i * GY for i in range(int(W / GY) + 1)]
        for x in xs:
            iv = sorted((y0, y1) for x0, y0, x1, y1 in obs if x0 <= x < x1)
            cov, cy0, cy1 = 0.0, None, None
            for y0, y1 in iv:
                if cy1 is None or y0 > cy1:
                    if cy1 is not None:
                        cov += cy1 - cy0
                    cy0, cy1 = y0, y1
                else:
                    cy1 = max(cy1, y1)
            if cy1 is not None:
                cov += cy1 - cy0
            free6 = (Hn - cov) / M6_PITCH
            if worst is None or free6 < worst[1]:
                worst = (x, free6)
        m8 = Hn / M8_PITCH * a.m8_share
        cut = dict(bus_bits=demand, demand_source='max W/E face signal pins of the closed pt_w / pt_e LEFs',
                   worst_cut_x_um=round(worst[0], 3), free_m6_tracks=int(worst[1]), m8_tracks=int(m8),
                   ratio_m6_only=round(demand / worst[1], 3), ratio_m6_m8=round(demand / (worst[1] + m8), 3),
                   rule='bits per cut / tracks <= 0.55-0.60 (owner 10-12 cut rule)')
        out['tiles'][tname] = dict(native_outline_um=[W, H], compact_outline_um=[W, round(Hn, 4)],
                                   native_mm2=round(W * H / 1e6, 4), compact_mm2=round(W * Hn / 1e6, 4),
                                   leaf_mm2=round(sum(c['outline_um'][0] * c['outline_um'][1] for c in kids) / 1e6, 4),
                                   children=kids, slice_strip=strip, overlaps=ov, outside=outside, off_lattice=off, ew_cut=cut)
    # ------------------------------------------------------------------ SM parent: 8 columns x 2 rows + front column
    comp = orig['sm_component']
    Ht = max(t['compact_outline_um'][1] for t in out['tiles'].values())
    Hn_t = {k: t['native_outline_um'][1] for k, t in out['tiles'].items()}
    row_p1 = 86.4
    gap = 1347.84 - (86.4 + 1252.8)
    row_p0 = up(row_p1 + Ht + gap, GY)
    kids = []
    # column pitch follows the compact tile width (native: 630.72 + 8.64); the front column keeps its native internal
    # placement, 12.96 um E of column 3, and columns 4-7 start 10.8 um E of it (the native seams)
    Wt = max(t['compact_outline_um'][0] for t in out['tiles'].values())
    pitch = up(Wt + 8.64, GX)
    fr_x0 = min(c['x'] for c in comp['children'] if 'g_fd' in c['name'])
    fr_x1 = max(c['x'] + c['outline_um'][0] for c in comp['children'] if 'g_fd' in c['name'])
    new_fr_x0 = up(3 * pitch + Wt + 12.96, GX)
    east0 = up(new_fr_x0 + (fr_x1 - fr_x0) + 10.8, GX)
    for c in comp['children']:
        c = dict(c)
        col = re.match(r'g_c\[(\d+)\]', c['name'])
        if col:
            i = int(col.group(1))
            c['x'] = round(i * pitch if i < 4 else east0 + (i - 4) * pitch, 4)
        else:
            c['x'] = round(c['x'] - fr_x0 + new_fr_x0, 4)
        if c['cell'].startswith('ot_hbm_accel_smh_tile_'):
            c['y'] = row_p0 if '.g_p[0].' in c['name'] else row_p1
            c['outline_um'] = out['tiles'][c['cell']]['compact_outline_um']
        kids.append(c)
    fr = [c for c in kids if '.g_fd.' in c['name'] or c['name'].startswith('g_fd')]
    Wsm = max(c['x'] + c['outline_um'][0] for c in kids)
    Hsm = up(max(c['y'] + c['outline_um'][1] for c in kids) + 0.0, GY)
    boxes = [(c['name'], c['x'], c['y'], c['x'] + c['outline_um'][0], c['y'] + c['outline_um'][1]) for c in kids]
    ov = [(p[0], q[0]) for i, p in enumerate(boxes) for q in boxes[i + 1:]
          if p[1] < q[3] - 1e-6 and q[1] < p[3] - 1e-6 and p[2] < q[4] - 1e-6 and q[2] < p[4] - 1e-6]
    sm_mm2 = Wsm * Hsm / 1e6
    leaf = sum(t['leaf_mm2'] for t in out['tiles'].values()) / len(out['tiles']) * 16 + \
        sum(c['outline_um'][0] * c['outline_um'][1] for c in kids if not c['cell'].startswith('ot_hbm_accel_smh_tile_')) / 1e6
    front_top = max(c['y'] + c['outline_um'][1] for c in fr)
    out['sm'] = dict(native_frame_um=comp['frame_outline_um'], native_frame_mm2=comp['frame_area_mm2'],
                     compact_frame_um=[round(Wsm, 4), round(Hsm, 4)], compact_mm2=round(sm_mm2, 4),
                     leaf_plus_slice_mm2=round(leaf + 16 * out['tiles']['ot_hbm_accel_smh_tile_eg']['slice_strip']['std_area_um2']
                                               / a.util / 1e6, 4),
                     front_column_top_um=round(front_top, 4), tile_rows_y_um=[row_p1, row_p0],
                     children=kids, overlaps=ov,
                     slot_um=list(SLOT), slot_mm2=round(SLOT[0] * SLOT[1] / 1e6, 4),
                     compact_over_slot=round(sm_mm2 / (SLOT[0] * SLOT[1] / 1e6), 3))
    n = 32
    grow = n * (sm_mm2 - SLOT[0] * SLOT[1] / 1e6)
    out['die'] = dict(sm_count=n, slots_mm2=round(n * SLOT[0] * SLOT[1] / 1e6, 2), compact_sms_mm2=round(n * sm_mm2, 2),
                      growth_mm2=round(grow, 2), v14_free_mm2=DIE_FREE_MM2,
                      free_after_mm2=round(DIE_FREE_MM2 - grow, 2),
                      owner_estimate=dict(sm_mm2=4.3, growth_mm2=21.0,
                                          basis='sum of closed leaf areas with the band deleted (no channels / strips)'),
                      sms_in_owner_budget=int((n * SLOT[0] * SLOT[1] / 1e6 + 21.0) // sm_mm2))
    if a.model:
        out['die']['field_fit'] = field_fit(a.model, Wsm, Hsm)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'plan.json').write_text(json.dumps(out, indent=1) + '\n')
    s = out['sm']
    print(f"tile compact {out['tiles']['ot_hbm_accel_smh_tile_eg']['compact_outline_um']} "
          f"({out['tiles']['ot_hbm_accel_smh_tile_eg']['compact_mm2']} mm2, native "
          f"{out['tiles']['ot_hbm_accel_smh_tile_eg']['native_mm2']}); cut {out['tiles']['ot_hbm_accel_smh_tile_eg']['ew_cut']}")
    print(f"SM compact {s['compact_frame_um']} = {s['compact_mm2']} mm2 (native {s['native_frame_mm2']}, slot {s['slot_mm2']},"
          f" leaf+slice {s['leaf_plus_slice_mm2']}); overlaps {len(s['overlaps'])} tile overlaps "
          f"{[len(t['overlaps']) for t in out['tiles'].values()]} outside {[t['outside'] for t in out['tiles'].values()]}")
    print('die', out['die'])


if __name__ == '__main__':
    main()

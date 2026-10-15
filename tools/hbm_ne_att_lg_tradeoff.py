#!/usr/bin/env python3
"""NE VM bank: attention PV gather (WG write) vs LG tap chain face trade-off (GEO-H, 2026-10-15).

Both clients of the NE VM bank are placed jointly, per bank, inside a whole-die D_local candidate:
  * LG tap chain: CLOSED LG leaf LEF (R0 only), LG0 + LG1 + LG2 abutted westward (5.4 um clearance);
    link = rq<rg>/rr<rg> + one write slot (556 bits).
  * Attention registered bank gather (ot_hbm_attn_pv_bank_gather_registered, R0, 250.02 x 225.18,
    requested pin TSV): outputs bank_flags[0..7] -> wq<s>[0..7], bank_data[i] -> wq<s>[8+i],
    output_v -> wq<s>[280] (265 bits; the 16 address bits come from the calendar, not the gather);
    inputs: 2,048 tile_data + 64 tile_flags from logical tiles 4k+g (k = bundle), sourced at the
    centroid of the tile's placed PV banks in the candidate (no tile drain pin view exists).
The bank is the actual RG7/WG3 ODB pin readback. RG3 (ATT query) stays where it is.
For every (LG read group, LG write slot, gather write slot) the two leaf origins are searched on a grid
(separable Manhattan cost) under: >= 5.4 um clearance to the bank, to each other and to every other box
of the candidate (all LG_NE prototypes are re-placed, so they are not obstacles). Pin-centre Manhattan
bit-um only: no route, congestion, timing, PG or cut claim. Requested gather pins are not actual pins.
"""
import argparse, csv, json, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_vm_lg_face_search as fs

CLR = 5.4
GW, GH = 250.02, 225.18

def gather_pins(tsv):
    pins = {}
    for r in csv.DictReader(open(tsv), delimiter='\t'):
        if r['bank_leaf'] != '0': continue
        a = float(r['requested_along_um']); f = r['face']
        pins[r['port_bit']] = (0.0, a) if f == 'W' else (GW, a) if f == 'E' else (a, GH)
    return pins

def axis_cost(a, grid):
    # sum_i |a_i - g| for every grid value g (a = target - pin offset)
    a = np.sort(np.asarray(a, dtype=np.float64)); c = np.concatenate([[0.0], np.cumsum(a)])
    k = np.searchsorted(a, grid); n = len(a)
    return grid * k - c[k] + (c[n] - c[k]) - grid * (n - k)

def blocked(grid_x, grid_y, w, h, rects):
    # mask[i, j] True if a w x h box at (grid_x[i], grid_y[j]) comes within CLR of any rect
    m = np.zeros((len(grid_x), len(grid_y)), bool)
    for (x0, y0, x1, y1) in rects:
        bx = (grid_x + w + CLR > x0) & (grid_x < x1 + CLR)
        by = (grid_y + h + CLR > y0) & (grid_y < y1 + CLR)
        m |= bx[:, None] & by[None, :]
    return m

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lg-lef', required=True); ap.add_argument('--bank-pins', required=True)
    ap.add_argument('--gather-tsv', required=True); ap.add_argument('--candidates', nargs='+', required=True)
    ap.add_argument('--grid', type=float, default=2.16); ap.add_argument('--span', type=float, default=900.0)
    ap.add_argument('--out', required=True); a = ap.parse_args()
    leaf, lp = fs.lef_pins(a.lg_lef); (BW, BH), bp = fs.bank_pins(a.bank_pins); gp = gather_pins(a.gather_tsv)
    LW, LH = leaf; chain_w = 3 * LW + 2 * CLR  # LG2..LG0 extent; LG0 is the east leaf
    out = dict(schema='opentallas.hbm.geo.ne_att_lg_tradeoff.v1',
               inputs=dict(lg_lef=a.lg_lef, lg_lef_sha256=fs.sha(a.lg_lef), bank_pins=a.bank_pins,
                           bank_pins_sha256=fs.sha(a.bank_pins), gather_tsv=a.gather_tsv, gather_tsv_sha256=fs.sha(a.gather_tsv),
                           candidates={c: fs.sha(c) for c in a.candidates}),
               grid_um=a.grid, clearance_um=CLR, lg_hop=fs.chain(lp, leaf), results={})
    combos = [(rg, wl, wg) for rg in (0, 1, 2, 4, 5, 6) for wl in ('wq0', 'wq1', 'wq2') for wg in ('wq0', 'wq1', 'wq2') if wl != wg]
    for cpath in a.candidates:
        raw = json.loads(Path(cpath).read_text())
        cands = raw['candidates'] if 'candidates' in raw else [raw]
        for cand in cands:
            if 'VM_NE_0' not in cand['boxes'] or sum(1 for b in cand['boxes'].values() if b['role'] == 'PV_memory') != 2048: continue
            B = cand['boxes']; res = {}
            pre = {}
            for vb in range(8):
                bank = B[f'VM_NE_{vb}']; X, Y = bank['x'], bank['y']; g, half = vb // 2, vb % 2
                # tile drain sources, relative to the bank origin
                src = {}
                for k in range(8):
                    t = 4 * k + g; pv = [b for n, b in B.items() if n.startswith('ATT_PVbank') and b.get('bank', -1) // 64 == t]
                    cx = np.mean([b['x'] + b['w'] / 2 for b in pv]) - X; cy = np.mean([b['y'] + b['h'] / 2 for b in pv]) - Y
                    src[k] = (cx, cy)
                gin = [(src[int(m[2]) // (256 if m[1] == 'data' else 8)], gp[n]) for n in gp
                       for m in [re.fullmatch(r'tile_(data|flags)\[(\d+)\]', n)] if m]
                near = [(b['x'] - X, b['y'] - Y, b['x'] + b['w'] - X, b['y'] + b['h'] - Y) for n, b in B.items()
                        if not n.startswith('LG_NE_') and n != f'VM_NE_{vb}'
                        and b['x'] < X + BW + a.span + 300 and b['x'] + b['w'] > X - a.span - 300
                        and b['y'] < Y + BH + a.span + 300 and b['y'] + b['h'] > Y - a.span - 300]
                bank_r = (0.0, 0.0, BW, BH)
                gx = np.arange(-a.span - chain_w, BW + a.span, a.grid); gy = np.arange(-a.span, BH + a.span, a.grid)
                # LG0 origin legality: whole chain [ox - 2(LW+CLR), ox + LW]
                lg_bad = blocked(gx - 2 * (LW + CLR), gy, chain_w, LH, near + [bank_r])
                g_bad = blocked(gx, gy, GW, GH, near + [bank_r])
                gin_c = axis_cost([s[0] - p[0] for s, p in gin], gx)[:, None] + axis_cost([s[1] - p[1] for s, p in gin], gy)[None, :]
                pre[vb] = (X, Y, gx, gy, lg_bad, g_bad, gin_c, gin)
            res = {f'VM_NE_{vb}': {} for vb in range(8)}
            for rg, wl, wg in combos:
                placed = []  # earlier banks' leaves (abs), sequential greedy so leaves never overlap
                for vb in range(8):
                    X, Y, gx, gy, lg_bad0, g_bad0, gin_c, gin = pre[vb]
                    rel = [(r[0] - X, r[1] - Y, r[2] - X, r[3] - Y) for r in placed]
                    lg_bad = lg_bad0 | blocked(gx - 2 * (LW + CLR), gy, chain_w, LH, rel) if rel else lg_bad0
                    g_bad = g_bad0 | blocked(gx, gy, GW, GH, rel) if rel else g_bad0
                    lpairs = fs.plan_pairs(bp, lp, rg, wl)
                    lc = axis_cost([b[0] - l[0] for b, l in lpairs], gx)[:, None] + axis_cost([b[1] - l[1] for b, l in lpairs], gy)[None, :]
                    names = [(f'bank_flags[{j}]', f'{wg}[{j}]') for j in range(8)] + \
                            [(f'bank_data[{i}]', f'{wg}[{8 + i}]') for i in range(256)] + [('output_v', f'{wg}[280]')]
                    gpairs = [(bp[d], gp[s]) for s, d in names]
                    gc = axis_cost([b[0] - p[0] for b, p in gpairs], gx)[:, None] + axis_cost([b[1] - p[1] for b, p in gpairs], gy)[None, :]
                    lcm = np.where(lg_bad, np.inf, lc); gtot = np.where(g_bad, np.inf, gc + gin_c)
                    best = None
                    gord = np.argsort(gtot, axis=None)[:20000]; gv = gtot.ravel()[gord]
                    keep = np.isfinite(gv); gord, gv = gord[keep], gv[keep]
                    gi_, gj_ = np.unravel_index(gord, gtot.shape); gxs, gys = gx[gi_], gy[gj_]
                    for idx in np.argsort(lcm, axis=None)[:2000]:
                        i, j = np.unravel_index(idx, lcm.shape)
                        if not np.isfinite(lcm[i, j]) or not len(gv): break
                        if best and lcm[i, j] + gv[0] >= best[0]: break
                        x0, y0, x1, y1 = gx[i] - 2 * (LW + CLR), gy[j], gx[i] + LW, gy[j] + LH
                        ok = ~((gxs + GW + CLR > x0) & (gxs < x1 + CLR) & (gys + GH + CLR > y0) & (gys < y1 + CLR))
                        if not ok.any(): continue
                        k = int(np.argmax(ok))
                        if best is None or lcm[i, j] + gv[k] < best[0]:
                            best = (lcm[i, j] + gv[k], (gx[i], gy[j]), (gxs[k], gys[k]))
                    if best is None: res[f'VM_NE_{vb}'][f'RG{rg}+{wl}|ATT:{wg}'] = dict(legal=False); continue
                    _, (lx, ly), (ox, oy) = best
                    ld = [abs(b[0] - l[0] - lx) + abs(b[1] - l[1] - ly) for b, l in lpairs]
                    go = [abs(b[0] - p[0] - ox) + abs(b[1] - p[1] - oy) for b, p in gpairs]
                    gi = [abs(s[0] - p[0] - ox) + abs(s[1] - p[1] - oy) for s, p in gin]
                    res[f'VM_NE_{vb}'][f'RG{rg}+{wl}|ATT:{wg}'] = dict(
                        legal=True, hc_engine_slot_conflict=(rg == 4 or 'wq2' in (wl, wg)), lg0_origin_rel=[round(lx, 3), round(ly, 3)], gather_origin_rel=[round(ox, 3), round(oy, 3)],
                        lg_link_bit_um=round(sum(ld), 1), lg_link_max_um=round(max(ld), 1),
                        att_out_bit_um=round(sum(go), 1), att_out_max_um=round(max(go), 1),
                        att_in_bit_um=round(sum(gi), 1), att_in_max_um=round(max(gi), 1),
                        total_bit_um=round(sum(ld) + sum(go) + sum(gi), 1),
                        lg_rect_abs=[X + lx - 2 * (LW + CLR), Y + ly, X + lx + LW, Y + ly + LH], gather_rect_abs=[X + ox, Y + oy, X + ox + GW, Y + oy + GH],
                        lg_faces=sorted({fs.face(b, BW, BH) for b, _ in lpairs}), att_face=fs.face(bp[f'{wg}[8]'], BW, BH))
                    placed += [[X + lx - 2 * (LW + CLR), Y + ly, X + lx + LW, Y + ly + LH], [X + ox, Y + oy, X + ox + GW, Y + oy + GH]]
            # quadrant totals over the eight banks
            keys = list(next(iter(res.values())))
            tot = {}
            for kk in keys:
                rr = [res[b][kk] for b in res]
                if not all(r['legal'] for r in rr): tot[kk] = dict(legal=False, illegal_banks=[b for b in res if not res[b][kk]['legal']]); continue
                tot[kk] = {m: round(float(sum(r[m] for r in rr)), 1) for m in ('lg_link_bit_um', 'att_out_bit_um', 'att_in_bit_um', 'total_bit_um')}
                rects = [r[n] for r in rr for n in ('lg_rect_abs', 'gather_rect_abs')]
                tot[kk]['cross_bank_leaf_overlaps'] = sum(1 for i in range(len(rects)) for j in range(i + 1, len(rects))
                    if min(rects[i][2], rects[j][2]) - max(rects[i][0], rects[j][0]) > -CLR + 1e-6 and min(rects[i][3], rects[j][3]) - max(rects[i][1], rects[j][1]) > -CLR + 1e-6)
                tot[kk].update(lg_link_max_um=max(r['lg_link_max_um'] for r in rr), att_out_max_um=max(r['att_out_max_um'] for r in rr), legal=True)
            base = tot.get('RG0+wq0|ATT:wq1')
            for kk, v in tot.items():
                if v['legal'] and base and base['legal']:
                    v['delta_total_vs_current_pct'] = round(100 * (v['total_bit_um'] - base['total_bit_um']) / base['total_bit_um'], 2)
                    v['delta_lg_vs_current'] = round(v['lg_link_bit_um'] - base['lg_link_bit_um'], 1)
                    v['delta_att_vs_current'] = round(v['att_out_bit_um'] + v['att_in_bit_um'] - base['att_out_bit_um'] - base['att_in_bit_um'], 1)
            ranked = sorted([k for k in tot if tot[k]['legal']], key=lambda k: tot[k]['total_bit_um'])
            out['results'][cand['name']] = dict(per_bank=res, ne_quadrant_totals=tot, ranked=ranked[:12])
            print(cand['name'], 'current', base)
            for k in ranked[:6]: print('  ', k, tot[k])
            for k in ('RG0+wq1|ATT:wq0', 'RG0+wq1|ATT:wq2', 'RG4+wq2|ATT:wq1'): print('  *', k, tot.get(k))
    out['scope'] = ('per-bank joint placement of LG chain + ATT bank gather beside one actual RG7 bank inside each D_local '
                    'whole-die candidate; Manhattan pin-centre bit-um; tile drain = PV bank centroid; requested gather pins; '
                    'no route/timing/PG/cut claim; the LG far end (hub/ring) and RG3 query source are not in the metric.')
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')

if __name__ == '__main__': main()

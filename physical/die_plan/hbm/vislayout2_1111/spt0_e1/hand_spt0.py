"""VISLAYOUT2-HBM hand form q_spt0 / q_spt0__physical_v1 'E1' (positions only, register counts kept, 0 cycles).

INTENT: q_spt0 is the xcal/SPT tile: two xcal macros u_xc_Q0 (SW) / u_xc_Q1 (SE) at the S face, wide transit N-S
(L8x2 3070 b, L21x4 2560 b) through the middle.  Its S-face output buses L41_o (1064 b) / L88_o (68 b) and inputs
L50_i / L84_i are carried to/from u_xc_Q0 by internal stations sited ON the S face row (y = 0) across the whole
width, plus the 512-b L1271x8 S->S slot at y 8.64: every one of these bundles runs along the bottom edge, under and
between the macros and through the S face pin field.  Real GRT (a10, 963k overflow) puts 44% of it on the face.
E1 lifts every edge-row station chain to a macro-free row ABOVE the xcal macros (y = ROW, default 330 um): face ->
up to ROW -> along ROW -> down to the core pin, registers evenly by arc length (count unchanged, hop <= 395 um).
Every long S->S slot (L1271x8; pv1 L5076x2 653 b, L5096x9) follows the same row.  Windows, cores, outline unchanged."""
import json, sys, math
src, dst = sys.argv[1], sys.argv[2]
ROW = float(sys.argv[3]) if len(sys.argv) > 3 else 330.0
TYPES = sys.argv[4].split(',') if len(sys.argv) > 4 else ['q_spt0', 'q_spt0__physical_v1']
LIM = 395.0
LOWROW = 140.0  # fallback row for S->S slots whose register count cannot reach ROW (pv1 L5076x2: 4 regs)
p = json.load(open(src))
def path_pts(a, b, row):
    return [tuple(a), (a[0], row), (b[0], row), tuple(b)]
def along(pts, k):
    seg = [abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    L = sum(seg); out = []
    for j in range(1, k + 1):
        d = L * j / (k + 1); i = 0
        while i < len(seg) - 1 and d > seg[i]:
            d -= seg[i]; i += 1
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        f = d / seg[i] if seg[i] else 0
        out.append([round(x0 + (x1 - x0) * f, 2), round(y0 + (y1 - y0) * f, 2)])
    return out, L / (k + 1)
def at(pts, d):
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        sl = abs(x1 - x0) + abs(y1 - y0)
        if d <= sl or i == len(pts) - 2:
            f = d / sl if sl else 0
            return [round(x0 + (x1 - x0) * f, 2), round(y0 + (y1 - y0) * f, 2)]
        d -= sl
def anchored(pts, k, d0, dl):
    L = sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
    if k == 1:
        return [at(pts, d0)], max(d0, L - d0)
    e = L - dl
    ds = [d0 + (e - d0) * j / (k - 1) for j in range(k)]
    return [at(pts, d) for d in ds], (e - d0) / (k - 1)
rep = []
for tn in TYPES:
    t = p['partition_types'][tn]
    for s in t.get('internal_stations', []):
        if max(r[1] for r in s['regs_um']) > 10:
            continue
        regs, hop = along(path_pts(s['from_um'], s['to_um'], ROW), len(s['regs_um']))
        if hop > LIM:
            rep.append((tn, s['conn'], 'KEPT hop', round(hop, 1))); continue
        s['regs_um'] = regs
        s['note'] = (s.get('note', '') + f' | VISLAYOUT2-HBM E1: chain lifted off the S face row to y {ROW:g} (macro-free), even hops {hop:.0f} um').strip(' |')
        rep.append((tn, s['conn'], s['bits'], round(hop, 1)))
    for s in t.get('ft_slots', []):
        if s.get('in_face') == 'S' and s.get('out_face') == 'S' and abs(sum(s['in_window_um']) - sum(s['out_window_um'])) / 2 > 300 and max(r[1] for r in s['regs_um']) < 10:
            a = [sum(s['in_window_um']) / 2, 0.0]; b = [sum(s['out_window_um']) / 2, 0.0]
            k = len(s['regs_um'])
            r0, rl = s['regs_um'][0], s['regs_um'][-1]
            d0 = abs(r0[0] - a[0]) + abs(r0[1] - a[1]); dl = abs(rl[0] - b[0]) + abs(rl[1] - b[1])
            for row in (ROW, LOWROW):
                # anchored: first/last register keep their distance from the in/out window (upstream/downstream
                # reach unchanged), the middle registers spread evenly along the lifted path
                if k >= 3:  # first/last register stay exactly where they are; interior ones ride the lifted row
                    # normal FT: S0 is the input pin itself (die_hop_scan.station_site), so the interior
                    # registers are spaced from the in-window centre, not from regs_um[0]
                    mid, hop = along(path_pts(a, rl, row), k - 2)
                    hop += (s['in_window_um'][1] - s['in_window_um'][0]) / 2
                    regs = [list(r0)] + mid + [list(rl)]
                else:
                    regs, hop = anchored(path_pts(a, b, row), k, d0, dl)
                if hop <= LIM:
                    break
            if hop > LIM:
                rep.append((tn, s['name'], 'KEPT hop', round(hop, 1))); continue
            s['regs_um'] = regs
            s.pop('bit_sites_um', None); s.pop('bit_site_cell_um', None)
            s['note'] = (s.get('note', '') + f' | VISLAYOUT2-HBM E1: off the S edge to y {row:g}, even hops {hop:.0f} um').strip(' |')
            rep.append((tn, s['name'], s['width'], round(hop, 1)))
    t['note'] = (t.get('note', '') + ' | VISLAYOUT2-HBM 11-11 E1: S-edge station rows lifted to a macro-free row').strip(' |')
json.dump(p, open(dst, 'w'), indent=1)
for r in rep: print(*r)

#!/usr/bin/env python3
"""S81 VM A2: structured full-VM floorplan candidate + area / cut / reach audit (S-VM -> S-DIE).

Places every hard leaf of the A2 source overlay (results/arch/s81_vm_area_1417/a2_inventory.json, 543 leaves; the
single landing leaf is replaced by the five CLOSED landing hardleaves 4 x 95.04^2 + 21.6^2) inside one rectangle of
fixed width, with a uniform channel CH (default 21.6 um, the die/VM >=20 um macro-channel rule) between every pair of
hard leaves.  No rotation (R0/MX/MY only); quarter interiors are re-packed at CH (Codex's 5.4 um stripe gaps are
NOT used).

Structure (y up, N = MIX4 face, W = SU face, E = capture face, S = HC/PQ/WFC/collective):
  slice block x (1663.2 wide): payload x in the middle row, quarters q0,q1 north / q2,q3 south of it, each quarter's
  storage unit (8 banks, its b4 pair, b8, scatter) on the far side of the quarter.  Slice blocks 2 x 2.
  Remaining leaves (reads, FSR, return lanes, capture lanes, x34/x43, landing, seq, rsched, header, cap_ctl) are
  shelf-packed in bands, ordered by the face they talk to.

Audit (same estimator family as tools/s81/global_fp/score.py): every ONE_DRIVER bitnet of a2_pin_join.jsonl.gz
(clock/reset/A2 clock nets excluded: delivered by the die clock tree at phi-R), pins at leaf centres, parent ports on
their assigned face; nets routed as a Prim tree of L-segments onto a 200-um gcell grid, capacity 21.09 bits/um at
<= 0.60; leaf-to-leaf links whose Manhattan length exceeds REACH (500 um) need a registered relay = +1 fixed edge.

Screen only: no native view, no GRT, no PG/IR run.  PG is accounted as the M7/M8 parent strap rule (no area) and
reported, not proven.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AREA = ROOT / 'results/arch/s81_vm_area_1417'
GC = 200.0
CAP_PER_UM = 5484.375 / 260.0
REACH = 500.0
CLOCKISH = ('ck_', 'rss_', 'rst_', 'A2_')
LANDING = [('lane0', 95.04, 95.04), ('lane1', 95.04, 95.04), ('lane2', 95.04, 95.04), ('lane3', 95.04, 95.04),
           ('fault_join', 21.6, 21.6)]
FACE_OF_PORT = {  # S-DIE 14:04 face plan: SU long face W, capture long face E, MIX4 short face N, rest S
    'f_su': 'W', 't_su': 'W', 'f_capture': 'E', 'f_mx': 'N', 't_mx': 'N'}


def port_face(p):
    for k, f in FACE_OF_PORT.items():
        if p.startswith(k):
            return f
    return 'S'


def load():
    inv = json.load(open(AREA / 'a2_inventory.json'))['leaves']
    leaves = [dict(name=l['path'], master=l['master'], w=l['outline_um'][0], h=l['outline_um'][1]) for l in inv]
    land = [i for i, l in enumerate(leaves) if l['master'] == 'dsfd_vm_static_landing']
    assert len(land) == 1
    li = land[0]
    base = leaves[li]['name']
    leaves[li] = dict(name=base + '.lane0', master='dsfd_vm_static_landing_lane0', w=95.04, h=95.04)
    extra = []
    for nm, w, h in LANDING[1:]:
        extra.append(len(leaves))
        leaves.append(dict(name=base + '.' + nm, master='dsfd_vm_static_landing_' + nm, w=w, h=h))
    lanes = [li] + extra[:3]
    nets = []
    k = 0
    for line in gzip.open(AREA / 'a2_pin_join.jsonl.gz', 'rt'):
        if not line.strip():
            continue
        r = json.loads(line)
        if r['status'] != 'ONE_DRIVER':
            continue
        ends = r['drivers'] + r['consumers']
        if any(e[0] < 0 and e[1].startswith(CLOCKISH) for e in ends):
            continue
        ls = []
        for e in ends:
            if e[0] == li:  # landing bits spread over the four lane leaves (lane = bit quarter)
                ls.append(lanes[k % 4])
            elif e[0] >= 0:
                ls.append(e[0])
        k += 1
        ps = sorted(set(port_face(re.sub(r'\[.*', '', e[1])) for e in ends if e[0] < 0))
        nets.append((sorted(set(ls)), ps))
    return leaves, nets


class Plan:
    def __init__(self, leaves, ch):
        self.leaves, self.ch, self.pos = leaves, ch, {}

    def put(self, i, x, y):
        assert i not in self.pos, self.leaves[i]['name']
        self.pos[i] = (round(x, 4), round(y, 4))

    def rect(self, i):
        x, y = self.pos[i]
        return x, y, self.leaves[i]['w'], self.leaves[i]['h']

    def check(self, W, H):
        bad, outside = 0, 0
        rs = [(i,) + self.rect(i) for i in self.pos]
        rs.sort(key=lambda r: r[1])
        for a in range(len(rs)):
            i, x, y, w, h = rs[a]
            if x < -1e-6 or y < -1e-6 or x + w > W + 1e-6 or y + h > H + 1e-6:
                outside += 1
            for b in range(a + 1, len(rs)):
                j, x2, y2, w2, h2 = rs[b]
                if x2 >= x + w + self.ch - 1e-6:
                    break
                if y2 < y + h + self.ch - 1e-6 and y < y2 + h2 + self.ch - 1e-6:
                    bad += 1
        return bad, outside


def classify(leaves, nets):
    """unit (slice x, write group q) of every storage/write leaf from the actual connectivity."""
    N = [l['name'] for l in leaves]
    M = [l['master'] for l in leaves]
    pb = collections.defaultdict(collections.Counter)
    for ls, _ in nets:
        for a in ls:
            for b in ls:
                if a != b:
                    pb[a][b] += 1
    unit = {}
    for i, n in enumerate(N):
        m = re.search(r'a2\.payload\[(\d)\]\.quarter\[(\d)\]', n)
        if m:
            unit[i] = (int(m.group(1)), int(m.group(2)))

    def adopt(prefix, via):
        for i, m in enumerate(M):
            if m.startswith(prefix):
                c = [(v, j) for j, v in pb[i].items() if j in unit and M[j].startswith(via)]
                assert c, N[i]
                unit[i] = unit[max(c)[1]]
    adopt('dsfd_vm_static_scatter', 's81_a2_stripe')
    adopt('dsfd_vm_static_relay128_b8', 'dsfd_vm_static_scatter')
    adopt('dsfd_vm_static_relay128_b4', 'dsfd_vm_static_relay128_b8')
    adopt('dsfd_vm_static_bank128', 'dsfd_vm_static_relay128_b4')
    return unit, pb


def skyline(P, items, W, y0, ch):
    """bottom-left skyline packing at channel ch inside [0, W] from y0 upward; returns the top."""
    sky = [(0.0, W + ch, y0)]          # (x0, x1, y) segments; widths include one trailing channel
    for grp in items:
        grp = grp if isinstance(grp, tuple) else (grp,)
        w = sum(P.leaves[i]['w'] for i in grp) + ch * len(grp)
        h = max(P.leaves[i]['h'] for i in grp) + ch
        best = None
        for k, (x0, _, _) in enumerate(sky):
            if x0 + w > W + ch + 1e-6:
                break
            top, x = 0.0, x0
            for (a, b, y) in sky[k:]:
                if a >= x0 + w - 1e-9:
                    break
                top = max(top, y)
            if best is None or top + h < best[0] - 1e-9 or (abs(top + h - best[0]) < 1e-9 and x0 < best[1]):
                best = (top + h, x0, top)
        _, x, y = best
        xx = x
        for i in grp:     # composite: members side by side, facing pin faces one channel apart
            P.put(i, xx, y)
            xx += P.leaves[i]['w'] + ch
        nsky = []
        for (a, b, yy) in sky:
            if b <= x or a >= x + w:
                nsky.append((a, b, yy))
            else:
                if a < x:
                    nsky.append((a, x, yy))
                if b > x + w:
                    nsky.append((x + w, b, yy))
        nsky.append((x, x + w, y + h))
        nsky.sort()
        merged = []
        for seg in nsky:
            if merged and abs(merged[-1][2] - seg[2]) < 1e-9 and abs(merged[-1][1] - seg[0]) < 1e-9:
                merged[-1] = (merged[-1][0], seg[1], seg[2])
            else:
                merged.append(seg)
        sky = merged
    return max(y for _, _, y in sky) - ch


def composites(N, rest):
    """capture lane = cap leaf | x34_s | x34_t; CDC pairs s|t; everything else single."""
    by = {N[i]: i for i in rest}
    used, out = set(), []
    for n, i in by.items():
        m = re.match(r'(dut\.u_cap\.lane\[\d+\])\.u_l$', n)
        if m:
            g = tuple(by[k] for k in (n, m.group(1) + '.u_x.u_s', m.group(1) + '.u_x.u_t') if k in by)
            out.append(g); used.update(g)
    for pre, order in (('dut.u_xsel', ('u_s', 'u_t')), ('dut.u_xcol', ('u_s', 'u_t')),
                       ('dut.u_wfc.u_xi', ('u_s', 'u_t')), ('dut.u_wfc.u_xo', ('u_t', 'u_s'))):
        g = tuple(by[pre + '.' + o] for o in order if pre + '.' + o in by and by[pre + '.' + o] not in used)
        if g:
            out.append(g); used.update(g)
    for n, i in by.items():
        if re.search(r'landing\.lane0$', n):
            g = tuple(by[k] for k in sorted(by) if re.search(r'u_land\.(lane\d|fault_join)$', k))
            out.append(g); used.update(g)
    out += [(i,) for i in rest if i not in used]
    return out


def unit_members(unit, xs):
    return [i for i, u in unit.items() if u[0] in xs]


def build(leaves, nets, W=3369.6, ch=21.6, band_mode='middle'):
    P = Plan(leaves, ch)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    unit, pb = classify(leaves, nets)
    QW, QH = 820.8, 324.0
    SH = 3 * 0 + 4 * 75.6 + 3 * ch          # storage unit height (8 banks 2x4)
    BW = 2 * QW + ch
    BH = 2 * SH + 2 * QH + 86.4 + 4 * ch
    assert 2 * BW + ch <= W + 1e-6, (BW, W)
    x0 = (W - (2 * BW + ch)) / 2
    def place_slice(x, by):
        bx = x0 + (x % 2) * (BW + ch)
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])]
        assert len(pay) == 1
        P.put(pay[0], bx + (BW - 1166.4) / 2, by + SH + ch + QH + ch)
        for q in range(4):
            north = q < 2
            ux = bx + (q % 2) * (QW + ch)
            qy = by + SH + ch + QH + ch + 86.4 + ch if north else by + SH + ch
            sy = qy + QH + ch if north else by
            mem = [i for i, u in unit.items() if u == (x, q)]
            byk = collections.defaultdict(list)
            for i in mem:
                byk[M[i]].append(i)
            # quarter interior: controller row next to the payload, 3 x 3 stripes, fault join in the spare corner
            stripes = sorted(byk['s81_a2_stripe_data16'], key=lambda i: N[i]) + byk['s81_a2_stripe_meta26']
            ctrl = [i for i in mem if M[i].startswith('s81_a2_controller')]
            fj = byk['s81_area_id_fault_join']
            assert len(stripes) == 9 and len(ctrl) == 1 and len(fj) == 1, (x, q, {k: len(v) for k, v in byk.items()})
            rows = [0, 1, 2, 3] if not north else [0, 1, 2, 3]
            ry = [qy + r * (54 + ch) for r in rows]
            if not north:
                ry = ry[::-1]       # controller row adjacent to the payload in both halves
            P.put(ctrl[0], ux + (QW - 172.8) / 2, ry[0])
            P.put(fj[0], ux + QW - 21.6, ry[0] + 16.2)
            sx0 = ux + (QW - (3 * 237.6 + 2 * ch)) / 2
            for k, i in enumerate(stripes):
                P.put(i, sx0 + (k % 3) * (237.6 + ch), ry[1 + k // 3])
            # storage unit: banks 2 x 4, b8 + scatter column, b4 pair column; scatter faces the quarter
            banks = sorted(byk['dsfd_vm_static_bank128'], key=lambda i: N[i])
            b8, sc, b4 = byk['dsfd_vm_static_relay128_b8'], byk['dsfd_vm_static_scatter_b8_out'], \
                sorted(byk['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
            assert len(banks) == 8 and len(b8) == 1 and len(sc) == 1 and len(b4) == 2, (x, q)
            for k, i in enumerate(banks):
                yy = (k // 2) * (75.6 + ch)
                P.put(i, ux + (k % 2) * (220.32 + ch), sy + (yy if north else SH - 75.6 - yy))
            cx = ux + 2 * 220.32 + 2 * ch
            if north:
                P.put(sc[0], cx, sy)
                P.put(b8[0], cx, sy + 86.4 + ch)
            else:
                P.put(sc[0], cx, sy + SH - 86.4)
                P.put(b8[0], cx, sy + SH - 86.4 - ch - 172.8)
            bx4 = cx + 172.8 + ch
            for k, i in enumerate(b4):
                yy = k * (129.6 + ch)
                P.put(i, bx4, sy + (yy if north else SH - 129.6 - yy))
            assert bx4 + 129.6 <= ux + QW + 1e-6
    rest_all = None
    if band_mode == 'top':
        for x in range(4):
            place_slice(x, (x // 2) * (BH + ch))
        rest = [i for i in range(len(N)) if i not in P.pos]
        rest = composites(N, rest)
        rest.sort(key=lambda g: (-max(leaves[i]['h'] for i in g), -sum(leaves[i]['w'] for i in g), N[g[0]]))
        H = skyline(P, rest, W, 2 * BH + 2 * ch, ch)
    else:   # 'middle': read/capture/control band between the two slice-block rows (halves band->payload reach)
        place_slice(0, 0.0)
        place_slice(1, 0.0)
        rest = [i for i in range(len(N)) if i not in P.pos and not re.search(r'w0_payload\[[23]\]|payload\[[23]\]\.quarter', N[i])]
        later = set(unit_members(unit, (2, 3)))
        rest = [i for i in rest if i not in later]
        rest = composites(N, rest)
        rest.sort(key=lambda g: (-max(leaves[i]['h'] for i in g), -sum(leaves[i]['w'] for i in g), N[g[0]]))
        top = skyline(P, rest, W, BH + ch, ch)
        place_slice(2, top + ch)
        place_slice(3, top + ch)
        H = top + ch + BH
    return P, W, H, unit, dict(slice_block_um=[BW, BH], quarter_um=[QW, QH], storage_unit_um=[QW, SH],
                               write_storage_core_um=[2 * BW + ch, 2 * BH + ch])


def facing(a, b):
    pa, pb = [0, 0], [0, 0]
    for k in (0, 1):
        a0, a1 = a[k], a[k] + a[k + 2]
        b0, b1 = b[k], b[k] + b[k + 2]
        if a1 < b0:
            pa[k], pb[k] = a1, b0
        elif b1 < a0:
            pa[k], pb[k] = a0, b1
        else:
            pa[k] = pb[k] = (max(a0, b0) + min(a1, b1)) / 2
    return pa, pb


def audit(P, nets, W, H):
    L = P.leaves

    def ctr(i):
        x, y, w, h = P.rect(i)
        return (x + w / 2, y + h / 2)
    face_pt = {}

    def port_pt(f, p):
        # parent pin at the face, nearest the net's first leaf (pins packed opposite the consumer)
        if f == 'W':
            return (0.0, p[1])
        if f == 'E':
            return (W, p[1])
        if f == 'N':
            return (p[0], H)
        return (p[0], 0.0)
    nx, ny = int(math.ceil(W / GC)), int(math.ceil(H / GC))
    hcut = collections.Counter()   # vertical gcell boundary crossings by horizontal segments: key (gx boundary, gy)
    vcut = collections.Counter()
    face_bits = collections.Counter()
    over = 0
    over_bits_by = collections.Counter()
    worst_link = 0.0
    total_bit_um = 0.0

    def seg(a, b):
        nonlocal total_bit_um
        (x1, y1), (x2, y2) = a, b
        total_bit_um += abs(x1 - x2) + abs(y1 - y2)
        gy = min(int(y1 // GC), ny - 1)
        for gx in range(int(min(x1, x2) // GC) + 1, int(max(x1, x2) // GC) + 1):
            hcut[(gx, gy)] += 1
        gx = min(int(x2 // GC), nx - 1)
        for gyy in range(int(min(y1, y2) // GC) + 1, int(max(y1, y2) // GC) + 1):
            vcut[(gx, gyy)] += 1
    for ls, ps in nets:
        pts = [ctr(i) for i in ls]
        if not pts:
            continue
        if len(ls) >= 2:   # registered pin to registered pin at the facing faces (score.py convention)
            r0 = P.rect(ls[0])
            for i in ls[1:]:
                pa, pb_ = facing(r0, P.rect(i))
                d = abs(pa[0] - pb_[0]) + abs(pa[1] - pb_[1])
                worst_link = max(worst_link, d)
                if d > REACH:
                    over += 1
                    over_bits_by[(L[ls[0]]['master'], L[i]['master'])] += 1
        for f in ps:   # parent face pins: counted in the face demand, not in the interior gcell cut
            face_bits[f] += 1
        # Prim tree
        done = [pts[0]]
        todo = pts[1:]
        while todo:
            best = None
            for k, p in enumerate(todo):
                for q in done:
                    d = abs(p[0] - q[0]) + abs(p[1] - q[1])
                    if best is None or d < best[0]:
                        best = (d, k, q)
            _, k, q = best
            p = todo.pop(k)
            seg(q, p)
            done.append(p)
    cap = GC * CAP_PER_UM
    shares = [v / cap for v in list(hcut.values()) + list(vcut.values())]
    worst = max(shares) if shares else 0.0
    over060 = sum(s > 0.60 for s in shares)
    # straight-line cuts across the whole rectangle (horizontal lines y = k*GC and vertical lines)
    row_cut = collections.Counter()
    col_cut = collections.Counter()
    for (gx, gy), v in vcut.items():
        row_cut[gy] += v
    for (gx, gy), v in hcut.items():
        col_cut[gx] += v
    line_h = max((v / (W * CAP_PER_UM), k) for k, v in row_cut.items()) if row_cut else (0, 0)
    line_v = max((v / (H * CAP_PER_UM), k) for k, v in col_cut.items()) if col_cut else (0, 0)
    face_len = dict(W=H, E=H, N=W, S=W)
    faces = {f: dict(bits=face_bits[f], length_um=round(face_len[f], 1),
                     bits_per_um=round(face_bits[f] / face_len[f], 2)) for f in 'NSEW'}
    return dict(parent_face_pin_demand=faces,
                face_note='one parent pin per (bitnet, face); native pin pitch 0.096 um on M5 (N/S) / M4 (W/E) = 10.4 bits/um per layer',
                gcell_um=GC, cap_bits_per_um=round(CAP_PER_UM, 4), util_limit=0.60,
                worst_gcell_edge_share=round(worst, 3), gcell_edges_over_060=over060,
                gcell_edges_total=len(shares),
                worst_full_width_line_share=dict(share=round(line_h[0], 3), y_um=line_h[1] * GC),
                worst_full_height_line_share=dict(share=round(line_v[0], 3), x_um=line_v[1] * GC),
                leaf_links_over_reach=over, reach_um=REACH, worst_leaf_link_um=round(worst_link, 1),
                over_reach_by_master_pair=[dict(driver=a, consumer=b, links=v)
                                           for (a, b), v in over_bits_by.most_common(25)],
                sum_bit_um=round(total_bit_um))


def area_accounting(P, W, H, unit):
    fam = collections.defaultdict(lambda: [0, 0.0])
    for i in P.pos:
        l = P.leaves[i]
        m = l['master']
        stage = ('A2 write front (quarters: ctrl/stripes/meta/fault)' if m.startswith(('s81_a2_controller', 's81_a2_stripe', 's81_area_id'))
                 else 'A2 W0 payload/header' if m.startswith('s81_a2_w0')
                 else 'storage banks (128 real SRAM)' if 'bank128' in m
                 else 'storage transport (scatter/b8/b4)' if ('relay128' in m or 'scatter' in m)
                 else 'read path (q/v leaves, FSR, return, rsched)' if any(k in m for k in ('read_', 'fsr', 'return', 'rsched'))
                 else 'capture/landing/CDC (cap leaves, x34/x43, landing, ctl)' if any(k in m for k in ('cap_', 'x34', 'x43', 'landing'))
                 else 'sequencer' if 'seq' in m else m)
        fam[stage][0] += 1
        fam[stage][1] += l['w'] * l['h']
    bare = sum(v[1] for v in fam.values())
    halo = sum((P.leaves[i]['w'] + P.ch) * (P.leaves[i]['h'] + P.ch) for i in P.pos)
    return dict(rectangle_um=[round(W, 3), round(H, 3)], rectangle_mm2=round(W * H / 1e6, 4),
                leaves=len(P.pos), bare_leaf_mm2=round(bare / 1e6, 4),
                channel_lower_bound_mm2=round((halo - (W + H) * P.ch) / 1e6, 4),
                fill_bare=round(bare / (W * H), 4),
                per_stage=[dict(stage=k, leaves=v[0], bare_mm2=round(v[1] / 1e6, 4)) for k, v in
                           sorted(fam.items(), key=lambda kv: -kv[1][1])])


def svg(P, W, H, path):
    col = lambda m: ('#c9a227' if 'bank' in m else '#4e79a7' if m.startswith('s81_a2') else '#f28e2b' if ('relay' in m or 'scatter' in m)
                     else '#59a14f' if ('read' in m or 'fsr' in m or 'return' in m or 'rsched' in m)
                     else '#e15759' if any(k in m for k in ('cap', 'x34', 'x43', 'landing')) else '#9c755f')
    s = 0.2
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %g %g">' % (W * s + 4, H * s + 4, W + 20, H + 20),
           '<rect x="10" y="10" width="%g" height="%g" fill="none" stroke="#000" stroke-width="4"/>' % (W, H)]
    for i in P.pos:
        x, y, w, h = P.rect(i)
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" stroke="#222" stroke-width="1"><title>%s</title></rect>'
                   % (10 + x, 10 + H - y - h, w, h, col(P.leaves[i]['master']), P.leaves[i]['name']))
    out.append('</svg>')
    Path(path).write_text('\n'.join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--width', type=float, default=3369.6)
    ap.add_argument('--channel', type=float, default=21.6)
    ap.add_argument('--band', choices=('top', 'middle'), default='middle')
    ap.add_argument('--out', default=str(AREA / 'a2_floorplan.json'))
    ap.add_argument('--svg', default=str(AREA / 'a2_floorplan.svg'))
    a = ap.parse_args()
    leaves, nets = load()
    P, W, H, unit, struct = build(leaves, nets, a.width, a.channel, a.band)
    bad, outside = P.check(W, H)
    res = dict(schema='opentallas.s81.vm-a2-floorplan.v1', band=a.band,
               status='SCREEN_ONLY_STRUCTURED_CANDIDATE_NOT_ROUTED',
               inputs={p: hashlib.sha256((AREA / p).read_bytes()).hexdigest() for p in ('a2_inventory.json', 'a2_pin_join.jsonl.gz')},
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               channel_um=a.channel, legality=dict(spacing_violations=bad, outside=outside),
               structure=struct, budget=dict(max_mm2=14.0, max_width_um=3369.6, max_height_um=4150.0),
               area=area_accounting(P, W, H, unit), cuts_and_reach=audit(P, nets, W, H),
               placement={P.leaves[i]['name']: [P.leaves[i]['master']] + list(P.rect(i)) for i in sorted(P.pos)})
    res['fits_budget'] = (res['area']['rectangle_mm2'] <= 14.0 and W <= 3369.6 + 1e-6 and H <= 4150.0 and bad == 0 and outside == 0)
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    svg(P, W, H, a.svg)
    s = {k: res[k] for k in ('channel_um', 'legality', 'structure', 'fits_budget')}
    s['area'] = {k: v for k, v in res['area'].items() if k != 'per_stage'}
    s['cuts'] = {k: v for k, v in res['cuts_and_reach'].items() if k != 'over_reach_by_master_pair'}
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    main()

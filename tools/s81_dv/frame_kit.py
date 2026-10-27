#!/usr/bin/env python3
"""TW3-S81-FRAMEGATE 10-19: the S81 frame (col_h9 / col_h10, landed 3-region LP RTL) as a ref_tile LANDED cluster kit.

COORD 0jy (HANDOFF 10-19 ~05:10): frame landing = option A (every region crossing landed as a compiler re-schedule,
bench-proved on claude/tw3-frame-1019).  This tool builds the physical side of the landed-regions standard:
  * floorplan: every hard child of the _l4 frame (q elements, compact199 bf_col (u_<bf>.u_view inside the dsfd_bf_col
    wrapper), bf front roots, qbanks + their ot_rom_4096x72_m8 macros, stations, return-tree nodes, relays, cfg7, rstg,
    crs4) legalised from the c26l GEN placement (the only frame placement that exists) into the frame outline under the
    ref_tile rules (>= 20 um channels, macro edge, child lattice); the x / xo / ret lanes enter on the E face where the
    p4l plan puts them (frame-local y 235-460), so crs4 (the x landing) moves beside them;
  * region centres (child-area centroid per lp region) -> lp spec "centre" + reach_um 405 -> lp.py re-emits the LP RTL
    with reset-hop runs sized to the measured centre distance (the hop count per region = ceil(manhattan / 405));
  * ref_tile spec (kind cluster, clock multiple_cts_roots = ck_r0..2, landed_record = the lp record, per-region clock
    entry domains, E-face pin plan) -> tools/ref_tile/ref_tile.py gen -> pre_route_gate --remote auto --cts.

  frame_kit.py place --master col_h9 [--height H] [--png OUT.png]     floorplan only (prints fit + displacement + bit-mm)
  frame_kit.py kit   --master col_h9 [--height H]                      place + lp centres + LP re-emit + ref_tile spec

The outline width is the p4l slot (1,436.832 um); the height is the smallest lattice height that legalises every child
(--height overrides).  A height above the p4l slot (h9 2,695.68 / h10 3,000.24) is a SLOT CHANGE: the spec carries
slot_change_request and the die plan must grow the frame pitch (coordinator).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/landed_parent'), str(ROOT / 'tools/ref_tile')]
import frame_regions as FR  # noqa: E402

W_SLOT = 1436.832
H_SLOT = {'col_h9': 2695.68, 'col_h10': 3000.24}
LAT = 43.2           # hard-child origin lattice (ref_tile CHILD_LATTICE_UM)
MG = (0.432, 2.16)   # macro lattice
CH = 20.0            # ref_tile CHANNEL_UM / PIN_EDGE_UM
CORE = 2.16
RES = 2.16           # occupancy bitmap resolution
REC = 'results/arch/s81_dv_1016/frame_l4_cluster'
LPDIR = 'rtl/dsrom_sys/s81_dv/frame_lp'
# S81-FRAME4 10-19: kept-copy reset forest primitives (lp landing_reset_forest), synthesised with the frame
LP_FOREST_RTL = ['rtl/common/landed_parent/ot_pl_land_field_copies.sv', 'rtl/common/landed_parent/ot_pl_land_reset_forest.sv']
ROM = 'ot_rom_4096x72_m8'
ROM_VIEW = 'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8'

# master -> view directory (closed views on origin/main; the bf_col / qxpq / front views are the die views the frame
# binds: compact199 (COORD 0gs; pin-band re-route of the same RTL pending, outline/pins unchanged), qxpq efs (COORD 0gs:
# the non-RSTP closed view stands in until the RSTP ob2 re-route closes: same outline 510.84 x 221.4)
VIEWS = {
    'dsfd_bf_col': 'physical/s81_die_views/frame_restub_1019/ot_v41_bf_col',
    'dsfd_bf_front_roots': 'physical/s81_die_views/bf_roots_1016_fg/dsfd_bf_front_roots',
    'ot_v41_rom_elem_q_qxpq_w10': 'physical/s81_die_views/q_elem_qs5f_efs_view/ot_v41_rom_elem_q_qxpq_w10',
    'dsfd_cfifo_crs4': 'physical/ref_tile/s81coll_cfifo_crs4/views/dsfd_cfifo_crs4',
    'dsfd_dvrly_276_NS': 'physical/ref_tile/s81dv_rly_276_ns/views/dsfd_dvrly_276_NS',
    'dsfd_qbank_N': 'physical/ref_tile/s81fill2_qbank_n/views/dsfd_qbank_N',
    'dsfd_qbank_S': 'physical/ref_tile/s81fill2_qbank_s/views/dsfd_qbank_S',
    'dsfd_rstg': 'physical/ref_tile/s81net_rstg/views/dsfd_rstg',
    'ot_s81_cfg7_seq': 'physical/ref_tile/s81coll_cfg7_seq_pr/views/ot_s81_cfg7_seq',
    'ot_s81_cfg7_seq_bfp': 'physical/ref_tile/s81coll_cfg7_seq_bfp_pr/views/ot_s81_cfg7_seq_bfp',
    'ot_s81_sstn_base566': 'physical/s81_die_views/frame_restub_1019/ot_s81_sstn_base566',
    'ot_s81_sstn_payload536': 'physical/ref_tile/s81_sstn_payload536/views/ot_s81_sstn_payload536',
}
for _n in ('LLd', 'LLfd', 'LLfu', 'NNfd', 'NNfu'):
    VIEWS[f'dsfd_node_{_n}'] = f'physical/ref_tile/s81net_node_{_n.lower()}/views/dsfd_node_{_n}'
# hard sub-instance inside a soft wrapper (the frame binds dsfd_bf_col = assigns + ot_v41_bf_col u_view)
SUBINST = {'dsfd_bf_col': 'u_view'}
BIG = ('ot_v41_rom_elem_q_qxpq_w10', 'dsfd_bf_col', 'dsfd_bf_front_roots')


def view_of(master):
    if master in VIEWS:
        return VIEWS[master]
    m = re.fullmatch(r'dsfd_rly_(\d+)_([NSEW]{2})', master)
    if m:
        return f'physical/ref_tile/s81_rly_{m.group(1)}_{m.group(2).lower()}/views/{master}'
    raise SystemExit(f'frame_kit: no view for {master}')


def lef_of(view):
    p = ROOT / view
    if p.is_file():
        return p
    c = sorted(x for x in p.glob('*.lef'))
    if not c:
        raise SystemExit(f'frame_kit: no LEF under {view}')
    return c[0]


def lef_size(view):
    t = lef_of(view).read_text()
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t)
    return float(m.group(1)), float(m.group(2))


# ------------------------------------------------------------------------------------------------ netlist + c26l
def frame_graph(master):
    """l4 children {inst: master}, c26l boxes (frame-local names), neighbour-mean centres for added children, nets"""
    FW = FR.FW
    fn, mod, *_ = FW.CLASSES[master]
    text = gzip.decompress((FW.SRC / fn).read_bytes()).decode()
    _, insts = FW.parse_column(text, mod)
    cl = json.loads(gzip.decompress((FW.SRC / 'c26l_sel_clusters.json.gz').read_bytes()))
    cluster = next(c for c in cl['clusters'] if c['master'] == mod)
    names, _ = FW.local_names(cluster['children'], insts)
    box = {c['instance']: (c['box_um'], c.get('orient', 'R0')) for c in cluster['children']}
    pos = {names[i['name']]: box[i['name']] for i in insts if i['name'] in box}
    s = (ROOT / f'rtl/dsrom_sys/s81_dv/frame_l4/{master}_l4.sv').read_text()
    body = s[s.index(');') + 2:]
    inst_re = re.compile(r"^    ([a-z]\w*)\s*(?:#\((?:[^()]|\([^()]*\))*\))?\s*(u_\w+)\s*\((.*?)\);\s*$", re.M | re.S)
    nets, kids = collections.defaultdict(lambda: collections.Counter()), {}
    for m in inst_re.finditer(body):
        mst, inst, conns = m.groups()
        kids[inst] = mst
        for pin, expr in re.findall(r"\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", conns):
            if pin in FR.CLOCK_PINS or pin == 'xk':
                continue
            for n in re.findall(r"\b(n\d+(?:\[\d+\])?|(?:x|xo|ret|xok)\[\d+\])", expr):
                nets[re.sub(r'\[\d+\]', '', n) if n.startswith('n') else n][inst] += 1
    cen = {k: (b[0] + b[2] / 2, b[1] + b[3] / 2) for k, (b, _o) in pos.items() if k in kids}
    orient = {k: o for k, (_b, o) in pos.items()}
    nb = collections.defaultdict(set)
    for ks in nets.values():
        if len(ks) < 40:
            for a in ks:
                nb[a] |= set(ks) - {a}
    for _ in range(8):
        for k in kids:
            if k not in cen:
                ps = [cen[o] for o in nb[k] if o in cen]
                if ps:
                    cen[k] = (statistics.mean(p[0] for p in ps), statistics.mean(p[1] for p in ps))
    miss = [k for k in kids if k not in cen]
    if miss:
        raise SystemExit(f'frame_kit: no position for {miss[:5]}')
    return kids, cen, orient, nets


# ------------------------------------------------------------------------------------------------ legaliser
class Occ:
    """occupancy bitmap at RES: placed blocks are marked expanded by CH (the channel every neighbour must keep)"""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.nx, self.ny = int(math.ceil(W / RES)), int(math.ceil(H / RES))
        self.m = np.zeros((self.ny, self.nx), dtype=np.int32)

    def mark(self, x, y, w, h, pad=CH):
        x0 = max(0, int(math.floor((x - pad) / RES)))
        y0 = max(0, int(math.floor((y - pad) / RES)))
        x1 = min(self.nx, int(math.ceil((x + w + pad) / RES)))
        y1 = min(self.ny, int(math.ceil((y + h + pad) / RES)))
        self.m[y0:y1, x0:x1] = 1

    def free_origins(self, w, h, lo, hi):
        """(ok, y0cell): bool map over origin cells in the window rows lo[1]..hi[1] (block clear of marks, inside)"""
        bw, bh = int(math.ceil(w / RES)), int(math.ceil(h / RES))
        r0 = max(0, int(math.floor(lo[1] / RES)))
        r1 = min(self.ny, int(math.ceil(hi[1] / RES)) + 1)
        sub = self.m[r0:r1]
        nyw = sub.shape[0]
        S = np.zeros((nyw + 1, self.nx + 1), dtype=np.int64)
        S[1:, 1:] = sub.cumsum(0).cumsum(1)
        ny, nx = nyw - bh + 1, self.nx - bw + 1
        if ny <= 0 or nx <= 0:
            return None, r0
        tot = S[bh:bh + ny, bw:bw + nx] - S[0:ny, bw:bw + nx] - S[bh:bh + ny, 0:nx] + S[0:ny, 0:nx]
        ok = tot == 0
        ys = (np.arange(ny) + r0) * RES
        xs = np.arange(nx) * RES
        ok &= (ys[:, None] >= lo[1] - 1e-6) & (ys[:, None] + h <= hi[1] + 1e-6)
        ok &= (xs[None, :] >= lo[0] - 1e-6) & (xs[None, :] + w <= hi[0] + 1e-6)
        return ok, r0


def nearest(occ, w, h, tx, ty, lat, lo, hi, maxd=None):
    ok, r0 = occ.free_origins(w, h, lo, hi)
    if ok is None:
        return None
    ys = (np.arange(ok.shape[0]) + r0) * RES
    xs = np.arange(ok.shape[1]) * RES
    # origins on the lattice only (RES divides both lattices: 43.2 = 20 x 2.16, macro x 0.432 -> nearest RES cell)
    ly = np.abs(ys / lat[1] - np.round(ys / lat[1])) < 1e-6
    lx = np.abs(xs / lat[0] - np.round(xs / lat[0])) < 1e-6 if lat[0] >= RES else np.ones_like(xs, dtype=bool)
    ok = ok & ly[:, None] & lx[None, :]
    if not ok.any():
        return None
    d = np.abs(ys[:, None] + h / 2 - ty) + np.abs(xs[None, :] + w / 2 - tx)
    d = np.where(ok, d, np.inf)
    i = np.unravel_index(np.argmin(d), d.shape)
    if maxd is not None and d[i] > maxd:
        return None
    return float(xs[i[1]]), float(ys[i[0]]), float(d[i])


def place(master, H=None, pins_y=(140.0, 620.0), e_split=1040.0, soft=(), small_lat=LAT):
    """row-structured legalisation of the c26l arrangement: bottom-up, each big row (q pair / bf pair + front) above its
    band (the c26l content between the previous row and this one, W of e_split), every band as short as its content
    allows under the 20-um channel rule; the E strip content (c26l x >= e_split: return-tree nodes, rstg ...) and crs4
    (beside the E-face x pins) go in last, at their c26l y mapped onto the new row positions."""
    kids, cen, orient, nets = frame_graph(master)
    kids = {k: m for k, m in kids.items() if not any(re.fullmatch(p, m) for p in soft)}
    nets = {n: collections.Counter({k: v for k, v in ks.items() if k in kids}) for n, ks in nets.items()}
    size = {m: lef_size(ROM_VIEW if m == ROM else view_of(m)) for m in set(kids.values())}
    W = W_SLOT
    Hmax = H or 6000.0
    lo = (CORE + CH, CORE + CH)
    hi = (W - CORE - CH, Hmax - CORE - CH)
    occ = Occ(W, Hmax)
    big = [k for k in kids if kids[k] in BIG]
    ys = sorted({round(cen[k][1] - size[kids[k]][1] / 2) for k in big})
    rows = []
    for y in ys:
        if rows and y - rows[-1][-1] < 30:
            rows[-1].append(y)
        else:
            rows.append([y])
    rbot = [min(r) for r in rows]
    rtop = [max(min(r) + max(size[kids[k]][1] for k in big if abs(cen[k][1] - size[kids[k]][1] / 2 - min(r)) < 30), 0)
            for r in rows]
    row_of = {k: next(i for i, r in enumerate(rows) if any(abs(cen[k][1] - size[kids[k]][1] / 2 - y) < 30 for y in r)) for k in big}
    crs = [k for k in kids if kids[k] == 'dsfd_cfifo_crs4']
    east = [k for k in kids if k not in big and k not in crs and cen[k][0] >= e_split]
    band = collections.defaultdict(list)
    for k in kids:
        if k in big or k in crs or k in east:
            continue
        cy = cen[k][1]
        band[sum(cy > t for t in rtop[:-1]) if cy > rbot[0] else 0].append(k)   # band i = below row i
        if cy > rtop[-1]:
            band[len(rows)].append(band[sum(cy > t for t in rtop[:-1])].pop())
    out = {}

    def put(k, x, y, d):
        m = kids[k]
        w, h = size[m]
        occ.mark(x, y, w, h)
        o = orient.get(k, 'R0') if (m in BIG or m == ROM) else 'R0'
        out[k] = dict(master=m, x=round(x, 3), y=round(y, 3), w=w, h=h, orient=o if o in ('R0', 'MX', 'MY', 'R180') else 'R0',
                      disp=round(d, 1))

    def lat(m):
        return MG if m == ROM else (LAT, LAT) if m in BIG else (small_lat, small_lat)

    for k in crs:      # crs4 first: bottom-right, beside the E-face x pin band
        m = kids[k]
        r = nearest(occ, *size[m], W - CORE - CH - size[m][0] / 2, 0.0, (LAT, LAT), (1080.0, lo[1]), (hi[0], 130.0))
        put(k, *r)

    y_cur = lo[1]
    ymap = []          # (c26l y, new y) anchors for the E strip
    for i in range(len(rows) + 1):
        items = sorted(band.get(i, []), key=lambda k: -size[kids[k]][0] * size[kids[k]][1])
        c_lo = rtop[i - 1] if i else 0.0
        c_hi = rbot[i] if i < len(rows) else max(cen[k][1] for k in kids) + 40
        if items:
            hb = max(size[kids[k]][1] for k in items)
            while True:
                snap = occ.m.copy()
                ok = True
                tmp = {}
                for k in items:
                    m = kids[k]
                    ty = y_cur + (cen[k][1] - c_lo) / max(c_hi - c_lo, 1) * hb
                    r = nearest(occ, *size[m], cen[k][0] + LAT, ty, lat(m), (lo[0], y_cur), (hi[0], y_cur + hb))
                    if r is None:
                        ok = False
                        break
                    tmp[k] = r
                    occ.mark(r[0], r[1], *size[m])
                occ.m = snap
                if ok:
                    break
                hb += RES * 2
            print(f'  band {i}: {len(items)} items, height {hb:.1f}', flush=True)
            for k, (x, y, d) in tmp.items():
                put(k, x, y, d)
            top = max(out[k]['y'] + out[k]['h'] for k in items) + CH
        else:
            top = y_cur
        ymap.append((c_lo, y_cur))
        if i == len(rows):
            ymap.append((c_hi, top))
            y_end = top
            break
        ry = math.ceil((top - 1e-6) / LAT) * LAT
        ymap.append((rbot[i], ry))
        for k in sorted((k for k in big if row_of[k] == i), key=lambda k: cen[k][0]):
            m = kids[k]
            off = (cen[k][1] - size[m][1] / 2) - rbot[i]
            r = nearest(occ, *size[m], cen[k][0] + LAT, ry + off + size[m][1] / 2, (LAT, LAT), (lo[0], ry), (hi[0], ry + off + size[m][1] + LAT))
            if r is None:
                return dict(ok=False, master=master, W=W, H=Hmax, failed=k, placed=len(out), n=len(kids))
            put(k, *r)
        y_cur = max(out[k]['y'] + out[k]['h'] for k in big if row_of[k] == i) + CH
        ymap.append((rtop[i], y_cur - CH))
    Hn = math.ceil((y_end + CH + CORE) / LAT) * LAT if H is None else H
    hi = (W - CORE - CH, Hn - CORE - CH)
    ymap.sort()

    def mapy(y):
        for (a0, b0), (a1, b1) in zip(ymap, ymap[1:]):
            if a0 <= y <= a1 and a1 > a0:
                return b0 + (y - a0) / (a1 - a0) * (b1 - b0)
        return ymap[-1][1] if y > ymap[-1][0] else ymap[0][1]
    for k in sorted(east, key=lambda k: -size[kids[k]][0] * size[kids[k]][1]):
        m = kids[k]
        r = nearest(occ, *size[m], cen[k][0] + LAT, mapy(cen[k][1]), lat(m), lo, (hi[0], Hmax - CORE - CH))
        if r is None:
            return dict(ok=False, master=master, W=W, H=Hn, failed=k, placed=len(out), n=len(kids))
        put(k, *r)
    if H is None:
        Hn = math.ceil((max(v['y'] + v['h'] for v in out.values()) + CH + CORE) / LAT) * LAT
    if max(v['y'] + v['h'] for v in out.values()) > Hn - CORE - CH + 1e-6:
        return dict(ok=False, master=master, W=W, H=Hn, failed='height', placed=len(out), n=len(kids))
    bitmm = 0.0
    for n, ks in nets.items():
        if not ks:
            continue
        if n.startswith(('x[', 'xo[', 'ret[', 'xok[')):
            pts = [(W, statistics.mean(pins_y))] + [(out[k]['x'] + out[k]['w'] / 2, out[k]['y'] + out[k]['h'] / 2) for k in ks]
            bits = 1
        else:
            pts = [(out[k]['x'] + out[k]['w'] / 2, out[k]['y'] + out[k]['h'] / 2) for k in ks]
            bits = max(ks.values())
        if len(pts) > 1:
            bitmm += bits * ((max(p[0] for p in pts) - min(p[0] for p in pts)) + (max(p[1] for p in pts) - min(p[1] for p in pts))) / 1000
    disp = sorted(v['disp'] for v in out.values())
    worst = max((v['disp'], k) for k, v in out.items())
    return dict(ok=True, master=master, W=W, H=round(Hn, 3), n=len(out), insts=out, worst_disp=worst,
                disp_p50=disp[len(disp) // 2], disp_p90=disp[int(len(disp) * 0.9)], bit_mm=round(bitmm, 1),
                c26l_height=round(max(cen[k][1] for k in kids), 1), y_scale=round(Hn / (max(cen[k][1] for k in kids) + 40), 4),
                rows=len(rows))


def fit(master, h0=None, step=LAT):
    return place(master, h0)


def png(r, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    col = {'ot_v41_rom_elem_q_qxpq_w10': '#4c72b0', 'dsfd_bf_col': '#dd8452', 'dsfd_bf_front_roots': '#c44e52', ROM: '#8172b3',
           'dsfd_cfifo_crs4': '#55a868'}
    fig, ax = plt.subplots(figsize=(6, 6 * r['H'] / r['W']))
    ax.add_patch(Rectangle((0, 0), r['W'], r['H'], fill=False, lw=1))
    for k, v in r['insts'].items():
        c = col.get(v['master'], '#937860' if v['master'].startswith(('dsfd_node', 'ot_s81')) else '#999999')
        ax.add_patch(Rectangle((v['x'], v['y']), v['w'], v['h'], color=c, lw=0))
    for nm, y in (r.get('cuts') or {}).items():
        ax.axhline(y, color='red', lw=0.6, ls='--')
    for nm, c in (r.get('centres') or {}).items():
        ax.plot(*c, 'k+', ms=10)
        ax.text(c[0] + 10, c[1] + 10, nm, fontsize=8)
    ax.set_xlim(-20, r['W'] + 20)
    ax.set_ylim(-20, r['H'] + 20)
    ax.set_aspect('equal')
    ax.set_title(f"{r['master']} frame {r['W']} x {r['H']} um ({r['n']} hard children)", fontsize=8)
    fig.savefig(path, dpi=110, bbox_inches='tight')


def centres(r, spec):
    out = {}
    for reg in spec['regions']:
        ks = [k for k in reg['insts'] if k in r['insts']]
        a = sum(r['insts'][k]['w'] * r['insts'][k]['h'] for k in ks)
        cx = sum((r['insts'][k]['x'] + r['insts'][k]['w'] / 2) * r['insts'][k]['w'] * r['insts'][k]['h'] for k in ks) / a
        cy = sum((r['insts'][k]['y'] + r['insts'][k]['h'] / 2) * r['insts'][k]['w'] * r['insts'][k]['h'] for k in ks) / a
        out[reg['name']] = [round(cx, 1), round(cy, 1)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('cmd', choices=['place', 'kit'])
    ap.add_argument('--master', choices=['col_h9', 'col_h10'], required=True)
    ap.add_argument('--height', type=float)
    ap.add_argument('--png')
    ap.add_argument('--small-lat', type=float, default=LAT, help='origin lattice of the small hard children (default 43.2)')
    ap.add_argument('--soft', action='append', default=[], help='regex of masters synthesised in the frame (not hard)')
    ap.add_argument('--kit-suffix', help='kit name suffix (default _sr with --soft, else none): a parallel variant kit')
    a = ap.parse_args()
    r = place(a.master, a.height, soft=tuple(a.soft), small_lat=a.small_lat)
    if not r['ok']:
        raise SystemExit(f"no fit at H {r['H']}: {r['failed']}")
    spec = json.loads((ROOT / REC / 'compiler' / f'{a.master}_spec.json').read_text())
    r['centres'] = centres(r, spec)
    print(json.dumps({k: v for k, v in r.items() if k != 'insts'}, indent=1))
    if a.png:
        png(r, a.png)
    if a.cmd == 'place':
        return
    kit(a.master, r, spec, tuple(a.soft), a.kit_suffix)


# ------------------------------------------------------------------------------------------------ kit
HARD_STRIP = re.compile(r"^(\s*)([a-zA-Z]\w*)\s*#\((?:[^()]|\([^()]*\))*\)\s*(u_\w+)\s*\(", re.M)


def kit_rtl(master, hard):
    """kit copy of the benched LP RTL: hard children instantiated WITHOUT #() overrides (a hard view has no parameters;
    INSTANCE is a simulation label only).  Same netlist otherwise; sha of the benched source recorded in the spec."""
    src = ROOT / LPDIR / f'{master}_l4_lp.sv'
    t = src.read_text()
    t2, n = HARD_STRIP.subn(lambda m: f"{m.group(1)}{m.group(2)} {m.group(3)} (" if m.group(2) in hard else m.group(0), t)
    # Yosys (ORFS read_verilog -sv) rejects `parameter string` (gate s81frame_col_h9_sr-20261019-074831: kit .sv:9 syntax
    # error); INSTANCE is a simulation label, an untyped parameter holds the same string
    t2 = re.sub(r'\bparameter\s+string\s+', 'parameter ', t2)
    out = ROOT / LPDIR / 'kit' / f'{master}_l4_lp_kit.sv'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'// GENERATED by tools/s81_dv/frame_kit.py from {src.relative_to(ROOT)} (sha256 '
                   f'{hashlib.sha256(t.encode()).hexdigest()}): hard-child #() overrides removed ({n} sites)\n' + t2)
    bf = ROOT / 'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv'
    b = bf.read_text()
    b2 = re.sub(r"ot_v41_bf_col\s*#\((?:[^()]|\([^()]*\))*\)\s*u_view", "ot_v41_bf_col u_view", b)
    bo = ROOT / LPDIR / 'kit' / 'dsfd_bf_col_kit.sv'
    bo.write_text(f'// GENERATED by tools/s81_dv/frame_kit.py from {bf.relative_to(ROOT)}: ot_v41_bf_col #() removed '
                  f'(the compact199 view = the hardened config)\n' + b2)
    return [str(out.relative_to(ROOT)), str(bo.relative_to(ROOT))], hashlib.sha256(t.encode()).hexdigest()


def kit(master, r, spec, soft=(), suffix=None):
    import subprocess
    # 1. region centres -> lp spec -> LP RTL re-emitted with measured reset-hop runs
    for reg in spec['regions']:
        reg['centre'] = r['centres'][reg['name']]
    spec['reach_um'] = 405
    sp = ROOT / REC / 'compiler' / f'{master}_spec.json'
    sp.write_text(json.dumps(spec, indent=1) + '\n')
    import lp
    lp.gen(lp.load(str(sp)))
    rec = json.loads((ROOT / REC / 'compiler' / f'{master}_l4_lp_record.json').read_text())
    print('lp reset', json.dumps(rec['reset']))
    kids = {k: v['master'] for k, v in r['insts'].items()}
    hard = set(kids.values()) | {'ot_v41_bf_col'}
    srcs, sha = kit_rtl(master, hard)
    # 2. domains: core = r0 (crs4, x landing, reset root); outputs in their driver's region
    reg_of = {k: reg['name'] for reg in spec['regions'] for k in reg['insts']}
    _, _, _, nets = frame_graph(master)
    drv = {}
    for p in ('xo', 'xok', 'ret'):
        ks = collections.Counter()
        for n, kk in nets.items():
            if n.startswith(p + '['):
                ks.update(reg_of[k] for k in kk)
        drv[p] = ks.most_common(1)[0][0] if ks else 'r0'
    names = {'r0': 'core', 'r1': 'r1', 'r2': 'r2'}
    dom = {names[g]: dict(ratio=[1, 1], ports=[f'ck_{g}'], inputs=[], outputs=[]) for g in ('r0', 'r1', 'r2')}
    dom['core']['inputs'] = ['x', 'xk', 'lk', 'rst_n']
    for p, g in drv.items():
        dom[names[g]]['outputs'].append(p)
    # 3. pins: E face (p4l plan: frame-local y 235-460 for x / xo / ret); one clock entry per region at its centre y
    c = r['centres']
    rng = {'xo': [140, 330], 'xok': [331, 334], 'xk': [336, 339], 'x': [341, 531], 'ret': [534, 552], 'lk': [555, 561],
           'rst_n': [563, 566]}
    for g in ('r0', 'r1', 'r2'):
        y = min(max(c[g][1], 600), r['H'] - 60) if g == 'r0' else min(c[g][1], r['H'] - 60)
        rng[f'ck_{g}'] = [round(y, 1), round(y + 3, 1)]
    children, macros = [], []
    for k, v in sorted(r['insts'].items()):
        if v['master'] == ROM:
            macros.append(dict(view=ROM_VIEW, inst=k, at=[v['x'], v['y']], orient=v['orient']))
        else:
            inst = f"{k}.{SUBINST[v['master']]}" if v['master'] in SUBINST else k
            children.append(dict(view=view_of(v['master']), inst=inst, at=[v['x'], v['y']], orient=v['orient']))
    name = f's81frame_{master}' + (suffix if suffix is not None else ('_sr' if soft else ''))
    soft_src = []
    if soft:
        # relays synthesised in the frame (soft): the RTL the benches compiled (lp spec child_sources), minus files that
        # define a module that stays hard (dv276 = the forwarded-clock relays u_xo*)
        for f in spec['child_sources']:
            t = (ROOT / f).read_text()
            mods = re.findall(r'^module\s+(\w+)', t, re.M)
            if mods and all(any(re.fullmatch(p, m) for p in soft) for m in mods):
                soft_src.append(f)
        soft_src = ['rtl/dsrom_sys/s81_glue/ot_s81_rly.sv'] + soft_src
    over = r['H'] > H_SLOT[master] + 1e-6
    ks = dict(
        name=name, top=f'{master}_l4_lp', kind='cluster',
        sources=['rtl/common/landed_parent/ot_pl_land.sv'] + (LP_FOREST_RTL if spec.get('landing_reset_forest') else [])
                + soft_src + srcs + [f'{ROM_VIEW}/{ROM}_bb.v'],
        params={}, defines=[],
        clock='multiple_cts_roots', clock_port='ck_r0', clock_ports=['ck_r0', 'ck_r1', 'ck_r2'],
        clock_data_paths='related_same_frequency',
        clock_relationship=dict(kind='same_pll_fixed_phase', ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dom,
        landed_record=f'{REC}/compiler/{master}_l4_lp_record.json',
        reset_ports=['rst_n'], static_ports=['lk'],
        # S81-FRAME4 10-19: xk[3:0] is the forwarded x lane clock (crs4 write side + dvrly u_xo* relays), not a region
        # root: ref_tile clock entries judge its 8 child clock pins as the forwarded class (per bit, child flops, <=80)
        forwarded_clock_ports=['xk'],
        reset_landing={'enable': False, 'reason': 'the RTL lands it: rst_n -> dsfd_cfifo_crs4 rst (2-stage rsync_q on cr) -> crs4 rs = n257 -> lp.py regional reset runs (ot_pl_pad chains per region, reach 405 hops from the measured centres); rst_n also reaches the 4 xo forwarded-clock relays u_xo* (.rs, async assert, their own RSREG). A kit landing would shift the crs4 release against the lane hop-0 gate the frame calendar is benched on'},
        outline=dict(w=r['W'], h=r['H'], exact=True), cluster_level=2,
        cluster_level_why='children include the q element (PG top M7, legacy closed view): two-level cluster contract (PG M8 aligned to the die grid, signals M2-M7)',
        children=children, macros=macros,
        pins=dict(E=list(rng)), pin_ranges=rng,
        route=dict(pd=0.5, threads=32, peak_ram_gb=192),
        structural_change=(f'TW3-S81-FRAMEGATE 10-19 (COORD 0jy option A): {master} landed frame (3 regions r0/r1/r2, '
                           f'every crossing landed as a compiler re-schedule, {rec["audit"]["landings"]} landings, reset hops '
                           f'{rec["reset"]["hops"]} at reach 405 from measured region centres {c}); hard children legalised '
                           f'from the c26l GEN placement (tools/s81_dv/frame_kit.py)'),
        frame=dict(lp_rtl=f'{LPDIR}/{master}_l4_lp.sv', lp_rtl_sha256=sha, bench='results/arch/s81_dv_1016/frame_l4_cluster/'
                   'compiler/bench_lp_1019 (claude/tw3-frame-1019 2911edcc2)', placement=dict(
                       worst_disp_um=r['worst_disp'], disp_p50=r['disp_p50'], disp_p90=r['disp_p90'], bit_mm=r['bit_mm'],
                       c26l_height=r['c26l_height'], y_scale=r['y_scale']),
                   stand_ins={'ot_v41_rom_elem_q_qxpq_w10': 'non-RSTP efs view (COORD 0gs) until the RSTP ob2 re-route closes',
                              'ot_v41_bf_col': 'compact199 closed view; pin-band re-route (same outline / pins) being submitted'},
                   xk_note='xk (forwarded x clock, preserved port) feeds crs4 xk[0..3] + dvrly u_xo0..3/ck; data-timed as a core input, '
                   'its child clock pins judged as the forwarded-clock class (forwarded_clock_ports)'),
        soft_children=dict(patterns=list(soft), why=('the 1-283 b frame relays are plain register stages (ot_s81_rly); as '
                           'hard 15-56 um tiles under the 20-um channel rule they set the frame height (hard-relay '
                           'legalisation needs 3.67 mm vs 3.20 mm soft, p4l slot 2.70): synthesised in the frame, placed '
                           'by the placer on their region tree') if soft else None),
        job=dict(owner='Claude:S81-FRAME4', branch='claude/s81-frame4-1019', tag='fg4',
                 purpose=f'S81 {master} landed frame cluster (COORD 0jy, landed-regions standard) -- physical gate',
                 no_bench_reason='frame lockstep + plan benches: frame_l4_cluster/compiler/bench_lp_1019; gate only (critical review)',
                 extra_paths=['results/arch/s81_dv_1016/frame_l4_cluster/compiler'],
                 views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}'),
    )
    if over:
        ks['slot_change_request'] = (f'frame height {r["H"]} > p4l slot {H_SLOT[master]}: the c26l arrangement under the '
                                     f'ref_tile 20-um channel rule needs it; die plan frame pitch must grow (coordinator)')
    out = ROOT / 'tools/ref_tile/specs_s81frame' / f'{name}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ks, indent=1) + '\n')
    print('wrote', out.relative_to(ROOT))


# ------------------------------------------------------------------------------------------------ variant (FRH10 10-20)
RST_LAND = ('    // FRH10 10-20 (safe-design item 1, textbook reset_landing): rst_n lands in 2 plain registered stages on the\n'
            '    // core root ck_r0 before crs4 rst and the u_xo* forwarded-clock relays (rst_n port -> 1 flop).  Assertion and\n'
            '    // release +2 ck_r0 edges for the whole frame (crs4 then gates every regional reset run): a die-schedule constant.\n'
            '    wire rst_n__frl;\n'
            '    ot_pl_pad #(.W(1), .N(2)) u_frl_rst (.ck(ck_r0), .d(rst_n), .q(rst_n__frl));\n')
LK_PAD = ('    // FRH10 10-20 fallback: lk (static strap, crs4 only) relayed by {n} plain stages on ck_r0 so the E-face pin ->\n'
          '    // u_cf wire (790 um) is split under the 405 um reach; static, so the added edges are irrelevant after config.\n'
          '    wire [11:0] lk__frp;\n'
          '    ot_pl_pad #(.W(12), .N({n})) u_frp_lk (.ck(ck_r0), .d(lk), .q(lk__frp));\n')


XK_LAND = ('    // FRRST 10-20 (COORD 21:29 (c), reset crossings land in the receiving region own clock): each u_xo relay runs on\n'
           '    // its forwarded lane clock xk[k] (die-phase foreign to ck_r0), so rst_n__frl (ck_r0) is synchronised onto xk[k] by an\n'
           '    // async-assert / sync-deassert 2-flop ot_reset_sync (assertion needs no xk edge: the lane clock is gated until the\n'
           '    // source release).  Release depth +2 xk[k] edges on the xo relays only (datapath pass-through, boot constant);\n'
           '    // the u_xrl*/reset_pipe CLR pins are the declared reset-synchroniser endpoints (die reset_sync.sdc).\n'
           '    wire [{n1}:0] rst_n__xk;\n')
XK_SYNC = '    ot_reset_sync #(.ASYNC_STAGES(2)) u_xrl{k} (.clk(xk[{k}]), .async_rst_n(rst_n__frl), .sync_rst_n(rst_n__xk[{k}]));\n'
XO_RS = re.compile(r'(u_xo(\d+) \(\.ck\(xk\[(\d+)\]\), \.rs\()rst_n__frl\)')


def xk_land_rtl(t2):
    """FRRST: every u_xo<k> (.ck(xk[k]), .rs(rst_n__frl)) -> .rs(rst_n__xk[k]) behind an xk[k] ot_reset_sync."""
    hits = XO_RS.findall(t2)
    if not hits or any(a != b for _, a, b in hits) or sorted(int(a) for _, a, _ in hits) != list(range(len(hits))):
        raise SystemExit(f'xk_land: expected u_xo<k> on xk[k] with rs(rst_n__frl), found {hits}')
    t2 = XO_RS.sub(lambda m: f'{m[1]}rst_n__xk[{m[3]}])', t2)
    add = XK_LAND.format(n1=len(hits) - 1) + ''.join(XK_SYNC.format(k=k) for k in range(len(hits)))
    return t2, add, len(hits)


def variant_rtl(master, base_kit, out, lk_stages=0, xk_land=False):
    """kit RTL of a variant: the base kit RTL + the 2-stage rst_n landing (+ optional lk relay).  Exactly the listed
    port-pin rewrites; everything else byte-identical (asserted)."""
    t = (ROOT / base_kit).read_text()
    n_rs = len(re.findall(r'\.(rs|rst)\(rst_n\)', t))
    if n_rs != 5:
        raise SystemExit(f'{base_kit}: expected 5 rst_n child pins (crs4 rst + 4 u_xo rs), found {n_rs}')
    t2 = re.sub(r'\.(rs|rst)\(rst_n\)', r'.\1(rst_n__frl)', t)
    add = RST_LAND
    if xk_land:
        t2, xadd, _ = xk_land_rtl(t2)
        add += xadd
    if lk_stages:
        if t2.count('.lk(lk)') != 1:
            raise SystemExit(f'{base_kit}: expected one .lk(lk)')
        t2 = t2.replace('.lk(lk)', '.lk(lk__frp)')
        add += LK_PAD.format(n=lk_stages)
    # declared before first use (`default_nettype none): right after the top module's port list
    m = re.search(r'^module\s+\w+\s*#\((?:[^()]|\([^()]*\))*\)\s*\((?:[^()]|\([^()]*\))*\);\n', t2, re.M)
    if not m:
        raise SystemExit(f'{base_kit}: top module header not found')
    t2 = t2[:m.end()] + add + t2[m.end():]
    hdr = (f'// FRH10 VARIANT of {base_kit} (sha256 {hashlib.sha256(t.encode()).hexdigest()}) by tools/s81_dv/frame_kit.py '
           f'variant: rst_n 2-stage landing{f", lk {lk_stages}-stage relay" if lk_stages else ""}'
           f'{", xo relay reset synchronised onto xk (FRRST)" if xk_land else ""}\n')
    (ROOT / out).write_text(hdr + t2)
    return hashlib.sha256(t.encode()).hexdigest()


def frame_benches(master, name, base_kit, out):
    """FRRST 10-20: the exact frame bench (tools/s81_dv/frame_bench.sh FRAME_LP=1, Verilator 5.050) on the bench twin of
    this variant (the same variant transform applied to the parameterised LP RTL), its landed mutants, and the reset
    crossing audit (tools/s81_dv/frame_reset_audit.py) on the kit RTL; the audit mutant is the rf3 kit RTL (u_xo reset
    straight from ck_r0 into the xk relays), which must FAIL."""
    sfx = name.split('_')[-1]
    twin = f'rtl/dsrom_sys/s81_dv/frame_lp/{master}_l4_lp_{sfx}.sv'
    # LDLY 0 (measured 10-20 ep7: h9 rf3r plan PASS at LDLY 0, FAIL at LDLY 2 -- the bench sees the reset epoch)
    env = f'VFLAGS=-DOT_S81_RLY_RSSLICE FRAME_LP=1 FRAME_LP_SV={twin} LDLY=0'
    b = []
    for st, kk in (('plan', 2048), ('each', 1024)):
        b.append(dict(name=f'frame_{master[4:]}_{st}_exact', expect='pass', threads=8, peak_ram_gb=64, needs=['verilator'],
                      cmd=f'{env} SET={st} KK={kk} J=8 bash tools/s81_dv/frame_bench.sh {{RUN}}/build_{st} {master} 0'))
    for m in ('unland', 'landread', 'reset'):
        line = f'NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT={m} {master}'
        b.append(dict(name=f'frame_{master[4:]}_{m}_mutant', expect='fail', threads=8, peak_ram_gb=64, needs=['verilator'],
                      fail_regex='^' + re.escape(line) + '$',
                      cmd=(f'mkdir -p {{RUN}}; {env} SET=plan KK=2048 J=8 bash tools/s81_dv/frame_bench.sh {{RUN}}/build_{m} '
                           f'{master} {m} > {{RUN}}/mutant.log 2>&1; frame_rc=$?; cat {{RUN}}/mutant.log; if [ "$frame_rc" -eq 0 ] '
                           f'&& grep -qx "{line}" {{RUN}}/mutant.log; then exit 1; fi; exit 0')))
    pre = base_kit.replace('_l4_lp_kit.sv', '_l4_lp_kit_rf3.sv')
    b.append(dict(name='reset_crossing_audit', expect='pass', threads=1, peak_ram_gb=2,
                  cmd=f'python3 tools/s81_dv/frame_reset_audit.py {out}'))
    b.append(dict(name='reset_crossing_audit_mutant_rf3', expect='fail', threads=1, peak_ram_gb=2,
                  fail_regex=r'^RESET_AUDIT FAIL .* foreign=[1-9]',
                  cmd=f'python3 tools/s81_dv/frame_reset_audit.py {pre}'))
    return b


def variant(base, name, lk_stages=0, pins_near_cf=False, xk_land=False):
    """FRH10 10-20: a gate variant of an existing frame kit spec (tools/ref_tile/specs_s81frame/<base>.json):
      * raw ot_rom_4096x72_m8 macros clocked by their region root (main clock_entries.tcl ot_ce_raw_memory_sink: CTS root
        ck_r0 'must reach only standard-cell clock pins' failed rf2n h9 CTS): soft_root_macro_masters + exact bindings,
        root read from the kit RTL .clk(ck_rX) of every instance;
      * kit RTL with rst_n landed in 2 stages (textbook reset_landing FAIL rf2n h9: rst_n -> 5 hard pins);
      * lk reach (rf2n h9: lk -> u_cf/lk 790 um comb): pins_near_cf moves the lk / rst_n E-face pins beside crs4 (u_cf
        lk/rst pins are on its W edge at y + 34.6..37.7), else lk_stages > 0 relays lk in the kit RTL."""
    sp = ROOT / 'tools/ref_tile/specs_s81frame' / f'{base}.json'
    s = json.loads(sp.read_text())
    master = s['top'].removesuffix('_l4_lp')
    base_kit = next(f for f in s['sources'] if f.endswith('_l4_lp_kit.sv'))
    out = base_kit.replace('_l4_lp_kit.sv', f'_l4_lp_kit_{name.split("_")[-1]}.sv')
    variant_rtl(master, base_kit, out, lk_stages, xk_land)
    s['sources'] = [out if f == base_kit else f for f in s['sources']]
    if xk_land:
        s['sources'].insert(0, 'rtl/lib/ot_reset_sync.sv')
        # the bench twin: the same transform on the parameterised LP RTL the frame bench (FRAME_LP=1) drives
        lp = f'rtl/dsrom_sys/s81_dv/frame_lp/{master}_l4_lp.sv'
        variant_rtl(master, lp, lp.replace('_l4_lp.sv', f'_l4_lp_{name.split("_")[-1]}.sv'), lk_stages, xk_land)
    s['name'] = name
    kt = (ROOT / out).read_text()
    roms = dict(re.findall(rf'\b{ROM}\s+(u_c\w+)\s*\(.*?\.clk\((ck_r\d)\)', kt))
    insts = [m['inst'] for m in s['macros'] if Path(m['view']).name == ROM]
    if set(roms) != set(insts):
        raise SystemExit(f'{name}: ROM instances in the kit RTL {len(roms)} != spec macros {len(insts)}')
    s['soft_root_macro_masters'] = [ROM]
    s['soft_root_macro_bindings'] = {i: dict(master=ROM, clock_pin='clk', root=roms[i]) for i in sorted(insts)}
    s['reset_landing'] = {'enable': False, 'reason': 'the RTL lands it: kit u_frl_rst = 2 plain ot_pl_pad stages on ck_r0 '
                          '(rst_n -> 1 flop) before crs4 rst (its own 2-stage rsync_q on cr, then crs4 rs gates the lp '
                          'regional reset runs) and the 4 u_xo forwarded-clock relays (rs); +2 edges reset epoch' + (
                          '; FRRST: the u_xo relay reset is re-synchronised onto each xk[k] (ot_reset_sync 2 flops, '
                          'async assert / sync release, +2 xk edges)' if xk_land else '')}
    rng = s['pin_ranges']
    if pins_near_cf:
        cf = next(c for c in s['children'] if c['inst'] == 'u_cf')
        y0 = cf['at'][1]
        # crs4 W-edge pins rst (34.56) / lk (35.04..37.70) above its origin; E-face pins just below xo (140): keep the
        # ranges between the crs4 rows and the xo band, 2 pins / um
        rng['lk'] = [round(y0 + 48.0, 1), round(y0 + 54.0, 1)]
        rng['rst_n'] = [round(y0 + 56.0, 1), round(y0 + 59.0, 1)]
        if rng['rst_n'][1] >= rng['xo'][0]:
            raise SystemExit('lk / rst_n pins collide with the xo band')
    s['pins'] = dict(E=sorted(rng, key=lambda k: rng[k][0]))
    s['pin_ranges'] = dict(sorted(rng.items(), key=lambda kv: kv[1][0]))
    s['structural_change'] = (s.get('structural_change', '') + f' | {name} (DRIVE-S81-FRH10 10-20): raw ROM CTS-root '
                              f'bindings ({len(insts)}), rst_n 2-stage kit-RTL landing, ' +
                              ('lk/rst_n E pins beside crs4' if pins_near_cf else f'lk {lk_stages}-stage relay') +
                              (', u_xo reset landed on xk (DRIVE-S81-FRRST)' if xk_land else ''))
    s['job']['owner'] = 'Claude:DRIVE-S81-FRRST' if xk_land else 'Claude:DRIVE-S81-FRH10'
    s['job']['branch'] = 'claude/s81-frame-rf3r-1020' if xk_land else 'claude/s81-frame-rf2p-1020'
    if xk_land:
        s['job'].pop('no_bench_reason', None)
        s['job']['benches'] = frame_benches(master, name, base_kit, out)
    s['job']['views_to'] = f'physical/ref_tile/{name}/views'
    s['job']['record_to'] = f'results/rtl/ref_tile/{name}'
    o = ROOT / 'tools/ref_tile/specs_s81frame' / f'{name}.json'
    o.write_text(json.dumps(s, indent=1) + '\n')
    print('wrote', o.relative_to(ROOT), out)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'variant':
        va = argparse.ArgumentParser()
        va.add_argument('cmd'); va.add_argument('--base', required=True); va.add_argument('--name', required=True)
        va.add_argument('--lk-stages', type=int, default=0); va.add_argument('--pins-near-cf', action='store_true')
        va.add_argument('--xk-land', action='store_true')
        x = va.parse_args()
        variant(x.base, x.name, x.lk_stages, x.pins_near_cf, x.xk_land)
    else:
        main()

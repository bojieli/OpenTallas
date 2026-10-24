#!/usr/bin/env python3
"""HBM d4g die plan BACK END for v2 (copy of gen_plan_v1.py; v2 changes marked V2).  Original header:

HBM d4g die plan v1 generator (PLAN-HBM, TOPDOWN-PLAN 2026-10-23).

Inputs (read-only):
  - FT-TOOL census of the r18h5 die (as-built connectivity, lane groups): census/hbm_census.json.gz
  - ODB dump of the same die (all block instances, positions): dumps/dump-hbm/blocks.tsv

Method:
  1. Instances get CANONICAL positions: the NW quadrant keeps its as-built placement; every NE/SW/SE instance takes
     the mirror image of its matched NW twin (same master family, nearest mirrored position).  The die becomes
     symmetric under MY (x), MX (y) and R180, so mirrored partitions share one type (owner plan b: quadrants aligned
     with the HBM channels).  Centre singletons (tkm, idx link/sel/ctl, host, hc_eng, ckgen) and the IO serdes get
     their own centre / IO regions.
  2. Partitions: the NW quadrant is tiled from its anchor macros (area >= 0.2 mm2), each grown over gaps
     < GROW_UM so neighbours abut; the free space is cut into equal fabric partitions <= HOP_UM per side.  Small
     leaf blocks become contents of the partition holding their centre.  The quadrant tiling is mirrored.
  3. Lanes: census groups are bundled per (src partition, dst partition, kind); bundles > SLICE_BITS are sliced.
     Each lane orbit (4 mirrored copies) is routed once over the partition adjacency graph (negotiated congestion,
     face pin cap 6/um) and mirrored, so every copy of a type sees the same ft slots.
  4. Stations: a lane crossing partition P gets max(1, ceil(len/reach)) stations (reset-less data + 1 epoch bit),
     so every hop is <= reach by construction.  Latency = stations + 1 (+ fixed), the TOPDOWN formula.
Outputs: die_plan.json (PLAN-TOOL schema opentallas.die_plan.v1), lane_members.json.gz, g0_summary.json, PNGs.
"""
import argparse, collections, gzip, heapq, json, math, os, re, sys

FT = os.environ.get('OT_HBM_FT_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inputs'))
G = 8.64                              # die lattice (PLAN-TOOL 8.64: M4-M9 symmetric tracks; 2.16 is off the M6/M7 0.064 pitch)
W0, H0 = 25988.8, 32983.12            # as-built r18h5 die
NX, NY = 3008, 3818                   # plan die = whole 8.64 grids, even counts (centre lines on grid)
W, H = NX * G, NY * G                 # 25989.12 x 32987.52
CX, CY = W / 2, H / 2
REACH = 750.0                         # COORD R3 10-23: max ft station spacing 750 um on all dies (HBM measured 1.0 mm)
REACH_WIDE = 1200.0
HOP_UM = 2000.0                       # fabric partition max side (L1 harden big partitions; L4 2-cycle hops)
ANCHOR_MM2 = 0.2
GROW_UM = 320.0                       # gaps narrower than this are absorbed into the neighbouring anchors
PIN_PER_UM = 6.0                      # face pin cap (2 layers)
WIN_PER_UM = 5.9                      # window sizing density (track snapping + 10-um face check margin under 6/um)
SLICE_BITS = 128
RING_TILE = 1002.24
SM_SPLIT = 4
VMH_H = 1607.04


def snap(v):
    return round(v / G) * G


def sdn(v):
    return math.floor(v / G + 1e-9) * G


def sup(v):
    return math.ceil(v / G - 1e-9) * G


# ------------------------------------------------------------------------------------------------ symmetry
OPS = ['I', 'MY', 'MX', 'R']          # MY: x -> W-x (NW->NE); MX: y -> H-y (NW->SW); R = both
QOP = {'NW': 'I', 'NE': 'MY', 'SW': 'MX', 'SE': 'R'}
ORIENT = {'I': 'R0', 'MY': 'MY', 'MX': 'MX', 'R': 'R180'}
OPPF = {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}


def mrect(op, r):
    x0, y0, x1, y1 = r
    if op in ('MY', 'R'):
        x0, x1 = W - x1, W - x0
    if op in ('MX', 'R'):
        y0, y1 = H - y1, H - y0
    return (x0, y0, x1, y1)


def mpt(op, p):
    x, y = p
    if op in ('MY', 'R'):
        x = W - x
    if op in ('MX', 'R'):
        y = H - y
    return (x, y)


def mface(op, f):
    if op in ('MY', 'R'):
        f = {'E': 'W', 'W': 'E'}.get(f, f)
    if op in ('MX', 'R'):
        f = {'N': 'S', 'S': 'N'}.get(f, f)
    return f


def quad_of(x, y):
    return ('N' if y >= CY else 'S') + ('W' if x < CX else 'E')


def fam(master):
    return re.sub(r'__pv\d+$', '', master)


# ------------------------------------------------------------------------------------------------ regions
# Centre cross (tkm + idx root + host + hc_eng), IO serdes boxes at the W/E edges, the two PHYs.
CTR = (sdn(10400.0), sdn(CY - 1263.0), W - sdn(10400.0), H - sdn(CY - 1263.0))      # symmetric
IOW = 3600.0
IO_T = sdn(CY + 777.6)                      # = top of the fabric row under su_NW2 (no 43-um sliver row)
IO_L = (0.0, H - IO_T, sup(IOW), IO_T)
IO_R = mrect('MY', IO_L)
PHY_W, PHY_H = 8500.0, 1177.2
PHY_N = (snap(CX - PHY_W / 2), H - sup(PHY_H + 20), snap(CX + PHY_W / 2), H)
PHY_S = mrect('MX', PHY_N)
EXCL = [CTR, IO_L, IO_R, PHY_N, PHY_S]
CENTRE_FAM = {'ot_hgi_coll_tkm_m_tp192', 'ot_hbm_idx_topk_link_static', 'ot_hbm_idx_selector_static_sel',
              'ot_hbm_idx_rootctl_static_am', 'ot_hbm_hc_root_static', 'ot_pdie_ucie_col', 'ot_hbm_host_cp_rxs',
              'hfd_ckgen_nolink', 'ot_hbm_argmax_static_sw_vm_r2'}
IO_FAM = {'ot_pdie_serdes', 'hfd_ep_static'}
PHY_FAM = {'ot_hbm3e_phy_rc_e8p5'}


def inside(r, p):
    return r[0] - 1e-6 <= p[0] <= r[2] + 1e-6 and r[1] - 1e-6 <= p[1] <= r[3] + 1e-6


def ov(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6


# ------------------------------------------------------------------------------------------------ load
def load():
    insts = {}
    for line in open(f'{FT}/dumps/dump-hbm/blocks.tsv'):
        f = line.rstrip('\n').split('\t')
        n = f[0]
        if n.startswith('hbfd_') or re.match(r'^(rf\d|rfr_|hidxr_)', n):
            continue
        x, y, w, h = map(float, f[2:6])
        if f[1].startswith('hbfd_'):
            continue
        insts[n] = dict(name=n, master=f[1], fam=fam(f[1]), x=x * W / W0, y=y * H / H0, w=w, h=h, orient=f[6])
    cen = json.load(gzip.open(f'{FT}/census/hbm_census.json.gz'))
    return insts, cen


# ------------------------------------------------------------------------------------------------ canonical positions
def canonicalise(insts):
    """NW quadrant keeps as-built; other quadrants mirror their matched NW twin.  Returns notes."""
    notes = []
    for i in insts.values():
        i['cx'], i['cy'] = i['x'] + i['w'] / 2, i['y'] + i['h'] / 2
        i['role'] = ('phy' if i['fam'] in PHY_FAM else 'io' if i['fam'] in IO_FAM else
                     'centre' if i['fam'] in CENTRE_FAM else 'quad')
        i['q'] = quad_of(i['cx'], i['cy'])
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for i in insts.values():
        if i['role'] == 'quad':
            by[i['fam']][i['q']].append(i)
    moved = 0
    for f, qs in by.items():
        nw = qs.get('NW', [])
        for q in ('NE', 'SW', 'SE'):
            op = QOP[q]
            lst = qs.get(q, [])
            if len(lst) != len(nw):
                notes.append(f'asym family {f}: NW {len(nw)} vs {q} {len(lst)} (kept as-built)')
                for i in lst:
                    i['twin'] = None
                continue
            # greedy nearest assignment in mirrored frame
            pairs = []
            for a in lst:
                ax, ay = mpt(op, (a['cx'], a['cy']))
                for b in nw:
                    pairs.append((abs(ax - b['cx']) + abs(ay - b['cy']), a['name'], b['name']))
            pairs.sort()
            ua, ub = set(), set()
            for dist, an, bn in pairs:
                if an in ua or bn in ub:
                    continue
                ua.add(an); ub.add(bn)
                a, b = insts[an], insts[bn]
                r = mrect(op, (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']))
                if abs(a['w'] - b['w']) > 1 or abs(a['h'] - b['h']) > 1:
                    notes.append(f'twin size differs {an}~{bn}')
                a['x'], a['y'] = r[0], r[1]
                a['cx'], a['cy'] = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                a['twin'] = (bn, op)
                moved += dist > 1
    # name twins for the quadrant-variant masters (vms glue NW/NE/SW/SE, coll q2/q3, ...): x_NE <-> x_NW
    for i in insts.values():
        if i['role'] != 'quad' or i['q'] == 'NW' or i.get('twin'):
            continue
        m = re.search(r'_(NE|SW|SE)(?=\d|_|$)', i['name'])
        if not m:
            continue
        tn = i['name'][:m.start()] + '_NW' + i['name'][m.end():]
        t = insts.get(tn)
        if not t or t['q'] != 'NW':
            continue
        op = QOP[i['q']]
        r = mrect(op, (t['x'], t['y'], t['x'] + t['w'], t['y'] + t['h']))
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        i['x'], i['y'] = cx - i['w'] / 2, cy - i['h'] / 2
        i['cx'], i['cy'] = cx, cy
        i['twin'] = (tn, op)
        moved += 1
        notes.append(f'name twin {i["name"]} -> mirror of {tn}')
    notes.append(f'{moved} non-NW instances moved to their mirrored NW twin site')
    # centre / io / phy re-placement inside their regions
    phy = [i for i in insts.values() if i['role'] == 'phy']
    for i in phy:
        r = PHY_N if i['cy'] > CY else PHY_S
        i['x'], i['y'] = r[0], (r[3] - i['h'] if r is PHY_N else r[1])
    return notes


# ------------------------------------------------------------------------------------------------ quadrant tiling
def quadrant_cells(insts):
    """Tile the NW quadrant (x<CX, y>CY minus exclusions) into anchors + fabric rectangles."""
    Q = (0.0, CY, CX, H)
    excl = [r for r in EXCL if ov(r, Q)]
    excl = [(max(r[0], Q[0]), max(r[1], Q[1]), min(r[2], Q[2]), min(r[3], Q[3])) for r in excl]
    anchors = []
    for i in insts.values():
        if i['role'] != 'quad' or i['q'] != 'NW':
            continue
        if i['w'] * i['h'] >= ANCHOR_MM2 * 1e6:
            anchors.append(dict(inst=i['name'], fam=i['fam'],
                                r=[sdn(i['x']), sdn(i['y']), sup(i['x'] + i['w']), sup(i['y'] + i['h'])]))
    # pin-bound hubs get an IO-sized outline (perimeter >= IO bits / 6 per um / 0.8)
    # VM hub: taller slot (G0 v1: 1.6 mm square left its faces 80% full -> face overflow), 1.6 x VMH_H
    for inst, side, ht in (('hb_vms_NW', 1607.04, VMH_H), ('hb_coll_NW', 864.0, 864.0)):
        i = insts[inst]
        x0 = min(sdn(i['cx'] - side / 2), sdn(CX - side)) if inst == 'hb_vms_NW' else sdn(i['cx'] - side / 2)
        y0 = sdn(i['cy'] - ht / 2)
        r = [x0, y0, min(x0 + side, CX), y0 + ht]
        anchors = [a for a in anchors if a['inst'] != inst]
        anchors.append(dict(inst=inst, fam=i['fam'], r=r))
    obst = [a['r'] for a in anchors] + [list(r) for r in excl]

    def free_strip(r, skip):
        for k, o in enumerate(obst):
            if k == skip:
                continue
            if ov(r, o):
                return False
        return True

    # grow anchors over small gaps (to neighbours / region edges); a gap between two anchors is split in half
    na = len(anchors)

    def nearest(k, side):
        r = anchors[k]['r']
        best, isanc = {'E': Q[2], 'W': Q[0], 'N': Q[3], 'S': Q[1]}[side], False
        for j, o in enumerate(obst):
            if j == k:
                continue
            if side in 'EW':
                if min(o[3], r[3]) - max(o[1], r[1]) <= 1e-6:
                    continue
                if side == 'E' and o[0] >= r[2] - 1e-6 and o[0] < best:
                    best, isanc = o[0], j < na
                if side == 'W' and o[2] <= r[0] + 1e-6 and o[2] > best:
                    best, isanc = o[2], j < na
            else:
                if min(o[2], r[2]) - max(o[0], r[0]) <= 1e-6:
                    continue
                if side == 'N' and o[1] >= r[3] - 1e-6 and o[1] < best:
                    best, isanc = o[1], j < na
                if side == 'S' and o[3] <= r[1] + 1e-6 and o[3] > best:
                    best, isanc = o[3], j < na
        return best, isanc

    for it in range(3):
        for k, a in enumerate(anchors):
            r = a['r']
            for side in 'EWNS':
                lim, isanc = nearest(k, side)
                cur = {'E': r[2], 'W': r[0], 'N': r[3], 'S': r[1]}[side]
                gap = abs(lim - cur)
                if not (1e-6 < gap < GROW_UM):
                    continue
                tgt = lim
                if isanc and gap > 2 * G:
                    tgt = snap((cur + lim) / 2)
                cand = {'E': [r[2], r[1], tgt, r[3]], 'W': [tgt, r[1], r[0], r[3]],
                        'N': [r[0], r[3], r[2], tgt], 'S': [r[0], tgt, r[2], r[1]]}[side]
                if cand[2] - cand[0] > 1e-6 and cand[3] - cand[1] > 1e-6 and free_strip(cand, k):
                    r[{'E': 2, 'W': 0, 'N': 3, 'S': 1}[side]] = tgt
    # the hc bank ring (8 banks + qhub, 3x3) becomes a regular abutted 3x3 grid over its bounding box
    ring = [a for a in anchors if a['fam'].startswith(('ot_hbm_hc_bankq', 'ot_hbm_hc_qhub'))]
    if len(ring) == 9:
        bx = [min(a['r'][0] for a in ring), min(a['r'][1] for a in ring), CX, max(a['r'][3] for a in ring)]
        if abs(bx[1] - CTR[3]) < 100:
            bx[1] = CTR[3]
        bx[0] = min(bx[0], sdn(CX - 3 * RING_TILE))          # ring tiles ~1 mm wide (pin-bound bank<->hub faces)
        for o in anchors:                                      # keep clear of the anchors west of the ring
            if o not in ring and ov(o['r'], bx):
                bx[0] = max(bx[0], o['r'][2])
        xs3 = [bx[0], snap(bx[0] + (bx[2] - bx[0]) / 3), snap(bx[0] + 2 * (bx[2] - bx[0]) / 3), bx[2]]
        ys3 = [bx[1], snap(bx[1] + (bx[3] - bx[1]) / 3), snap(bx[1] + 2 * (bx[3] - bx[1]) / 3), bx[3]]
        for a in ring:
            i = insts[a['inst']]
            cx, cy = i['cx'], i['cy']
            ci = min(range(3), key=lambda k: abs((xs3[k] + xs3[k + 1]) / 2 - cx))
            rj = min(range(3), key=lambda k: abs((ys3[k] + ys3[k + 1]) / 2 - cy))
            a['r'][:] = [xs3[ci], ys3[rj], xs3[ci + 1], ys3[rj + 1]]
            i['x'], i['y'] = (xs3[ci] + xs3[ci + 1] - i['w']) / 2, (ys3[rj] + ys3[rj + 1] - i['h']) / 2
            i['cx'], i['cy'] = i['x'] + i['w'] / 2, i['y'] + i['h'] / 2
    # grid lines from anchor + exclusion edges
    xs = sorted({Q[0], Q[2]} | {v for a in anchors for v in (a['r'][0], a['r'][2])} |
                {v for r in excl for v in (r[0], r[2])})
    ys = sorted({Q[1], Q[3]} | {v for a in anchors for v in (a['r'][1], a['r'][3])} |
                {v for r in excl for v in (r[1], r[3])})
    xs = [x for x in xs if Q[0] - 1e-6 <= x <= Q[2] + 1e-6]
    ys = [y for y in ys if Q[1] - 1e-6 <= y <= Q[3] + 1e-6]
    nxc, nyc = len(xs) - 1, len(ys) - 1
    occ = [[None] * nxc for _ in range(nyc)]
    for j in range(nyc):
        for i in range(nxc):
            c = ((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2)
            for k, a in enumerate(anchors):
                if inside(a['r'], c):
                    occ[j][i] = ('A', k)
            for r in excl:
                if inside(r, c):
                    occ[j][i] = ('X', 0)
    # free rectangles: row runs, then vertical merge of identical spans
    rects = []
    for j in range(nyc):
        i = 0
        while i < nxc:
            if occ[j][i] is None:
                i0 = i
                while i < nxc and occ[j][i] is None:
                    i += 1
                rects.append([xs[i0], ys[j], xs[i], ys[j + 1]])
            else:
                i += 1
    merged = True
    while merged:
        merged = False
        rects.sort(key=lambda r: (r[0], r[2], r[1]))
        out = []
        for r in rects:
            if out and abs(out[-1][0] - r[0]) < 1e-6 and abs(out[-1][2] - r[2]) < 1e-6 and abs(out[-1][3] - r[1]) < 1e-6:
                out[-1][3] = r[3]
                merged = True
            else:
                out.append(r)
        rects = out
    # absorb thin free rects into a neighbour that shares a full side (anchor first)
    MINS = 200.0

    def shares(a, b):
        if abs(a[2] - b[0]) < 1e-6 or abs(b[2] - a[0]) < 1e-6:
            return abs(a[1] - b[1]) < 1e-6 and abs(a[3] - b[3]) < 1e-6
        if abs(a[3] - b[1]) < 1e-6 or abs(b[3] - a[1]) < 1e-6:
            return abs(a[0] - b[0]) < 1e-6 and abs(a[2] - b[2]) < 1e-6
        return False

    def union(a, b):
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

    def absorb_pass():
        """Split each thin free rect at its long-side neighbours' boundaries; give every piece to the neighbour
        (free rect or anchor) whose full side it matches.  Returns True if anything changed."""
        for r in sorted(rects, key=lambda r: min(r[2] - r[0], r[3] - r[1])):
            w_, h_ = r[2] - r[0], r[3] - r[1]
            if min(w_, h_) >= MINS:
                continue
            horiz = w_ >= h_                   # long side along x
            for side in ((1, 3), (3, 1)) if horiz else ((0, 2), (2, 0)):
                # neighbours touching this long side
                nb = []
                for o in rects + [a['r'] for a in anchors]:
                    if o is r:
                        continue
                    if horiz and abs(o[side[1]] - r[side[0]]) < 1e-6 and min(o[2], r[2]) - max(o[0], r[0]) > 1e-6:
                        nb.append(o)
                    if not horiz and abs(o[side[1]] - r[side[0]]) < 1e-6 and min(o[3], r[3]) - max(o[1], r[1]) > 1e-6:
                        nb.append(o)
                lo, hi = (0, 2) if horiz else (1, 3)
                if not nb or any(o[lo] < r[lo] - 1e-6 or o[hi] > r[hi] + 1e-6 for o in nb):
                    continue
                cuts = sorted({r[lo], r[hi]} | {o[lo] for o in nb} | {o[hi] for o in nb})
                covered = sum(o[hi] - o[lo] for o in nb)
                if abs(covered - (r[hi] - r[lo])) > 1e-6:
                    continue                   # side not fully covered by neighbours
                rects.remove(r)
                for o in nb:
                    piece = list(r)
                    piece[lo], piece[hi] = o[lo], o[hi]
                    o[:] = union(o, piece)
                return True
        return False

    while absorb_pass():
        pass
    # split fabric to <= HOP_UM per side, equal pieces on the grid
    fabric = []
    for r in rects:
        nx = max(1, math.ceil((r[2] - r[0]) / HOP_UM - 1e-9))
        ny = max(1, math.ceil((r[3] - r[1]) / HOP_UM - 1e-9))
        xc = [r[0]] + [snap(r[0] + (r[2] - r[0]) * k / nx) for k in range(1, nx)] + [r[2]]
        yc = [r[1]] + [snap(r[1] + (r[3] - r[1]) * k / ny) for k in range(1, ny)] + [r[3]]
        for a in range(nx):
            for b in range(ny):
                fabric.append([xc[a], yc[b], xc[a + 1], yc[b + 1]])
    return anchors, fabric


# ------------------------------------------------------------------------------------------------ partitions
ROLE_SHORT = [('ot_hbm_accel_smh_attn', 'sm'), ('ot_hbm_su_static_pgslice_lg', 'su'), ('ot_hgi_sfu_core_split3', 'sfuc'),
              ('ot_hgi_sfu_programme_store_r10', 'sfup'), ('ot_hbm_idx_score_quarter_static', 'idxs'),
              ('ot_hbm_svc_sm_group_rel_id', 'svg'), ('ot_hbm_hc_qhub_static', 'hcq'), ('ot_hbm_hc_bankq', 'hcb'),
              ('ot_hbm_su_programme_pslice_c5', 'pgp'), ('ot_hfd_coll_q', 'coll'), ('ot_hbm_svc_wb_kport_q', 'wbk'), ('hfd_hgi_vms', 'vmh')]


def short(f):
    for k, s in ROLE_SHORT:
        if f.startswith(k):
            return s
    return 'blk'


def build_partitions(insts):
    anchors, fabric = quadrant_cells(insts)
    for i in insts.values():                   # re-mirror twins of NW instances the tiling moved
        if i.get('twin'):
            t = insts[i['twin'][0]]
            r = mrect(i['twin'][1], (t['x'], t['y'], t['x'] + t['w'], t['y'] + t['h']))
            i['x'], i['y'] = (r[0] + r[2] - i['w']) / 2, (r[1] + r[3] - i['h']) / 2
            i['cx'], i['cy'] = i['x'] + i['w'] / 2, i['y'] + i['h'] / 2
    canon = []                                 # NW canonical partitions
    cnt = collections.Counter()
    for a in sorted(anchors, key=lambda a: (-a['r'][3], a['r'][0])):
        s = short(a['fam']); nm = f'{s}{cnt[s]}'; cnt[s] += 1
        if s == 'sm':                          # L1: the SM (1.94 x 6.96 mm parent) is split into 4 stacked partitions
            r = a['r']; ys_ = [r[1]] + [snap(r[1] + (r[3] - r[1]) * k / SM_SPLIT) for k in range(1, SM_SPLIT)] + [r[3]]
            for k in range(SM_SPLIT):
                canon.append(dict(base=f'{nm}{"abcd"[k]}', r=(r[0], ys_[k], r[2], ys_[k + 1]), kind='anchor',
                                  anchor=a['inst']))
            continue
        canon.append(dict(base=nm, r=tuple(a['r']), kind='anchor', anchor=a['inst']))
    for r in sorted(fabric, key=lambda r: (-r[3], r[0])):
        nm = f'f{cnt["f"]}'; cnt['f'] += 1
        canon.append(dict(base=nm, r=tuple(r), kind='fabric', anchor=None))
    parts = []
    for c in canon:
        for q, op in QOP.items():
            parts.append(dict(name=f'{q}_{c["base"]}', base=c['base'], op=op, r=mrect(op, c['r']),
                              kind=c['kind'], cls='q_' + c['base'], anchor_nw=c['anchor']))
    # centre cross: tkm in the middle, two strips of 2 x 3 at each side; symmetric geometry
    x0, y0, x1, y1 = CTR
    tk = (snap(CX - 1000.0), y0, snap(CX + 1000.0), y1)
    parts.append(dict(name='C_tkm', base='tkm', op='I', r=tk, kind='centre', cls='c_tkm', anchor_nw=None))
    for side, (a, b) in (('W', (x0, tk[0])), ('E', (tk[2], x1))):
        xm = snap((a + b) / 2)
        ys_ = [y0, snap(y0 + (y1 - y0) / 3), snap(y0 + 2 * (y1 - y0) / 3), y1]
        for ci, (u, v) in enumerate(((a, xm), (xm, b))):
            if side == 'E' and ci == 1:      # host column: one tall partition (ucie col is 1.56 mm tall)
                parts.append(dict(name='C_E1', base='cE1', op='I', r=(u, y0, v, y1), kind='centre',
                                  cls='c_E1', anchor_nw=None))
                continue
            for ri in range(3):
                nm = f'C_{side}{ci}{ri}'
                parts.append(dict(name=nm, base=nm, op='I', r=(u, ys_[ri], v, ys_[ri + 1]), kind='centre',
                                  cls='c_' + nm, anchor_nw=None))
    # IO boxes: 3 columns each side
    for side, r in (('W', IO_L), ('E', IO_R)):
        xc = [r[0], snap(r[0] + (r[2] - r[0]) / 3), snap(r[0] + 2 * (r[2] - r[0]) / 3), r[2]]
        for k in range(3):
            nm = f'IO_{side}{k}'
            parts.append(dict(name=nm, base=nm, op='I', r=(xc[k], r[1], xc[k + 1], r[3]), kind='io',
                              cls='io_' + nm, anchor_nw=None))
    parts.append(dict(name='PHY_N', base='phy', op='I', r=PHY_N, kind='phy', cls='phy', anchor_nw=None))
    parts.append(dict(name='PHY_S', base='phy', op='MX', r=PHY_S, kind='phy', cls='phy', anchor_nw=None))
    return parts


def place_singletons(insts, parts):
    """Centre / IO / PHY instances: put each into a partition of its region (simple shelf packing)."""
    P = {p['name']: p for p in parts}
    plan = {
        'C_tkm': ['tkm_SW'],
        'C_W00': ['hb_idx__selector'], 'C_W01': ['hb_idx__link'], 'C_W02': [],
        'C_W10': ['hb_idx__xqr'], 'C_W11': [], 'C_W12': [],
        'C_E00': ['hc_eng'], 'C_E01': ['hb_idx__ctl', 'hb_ckgen'], 'C_E02': ['host_cp_rxs', 'hb_argmax'],
        'C_E1': ['host_N', 'host_ep'],
        'IO_W0': ['lk_S0', 'ep_S0'], 'IO_W1': ['lk_S1', 'ep_S1'], 'IO_W2': ['lk_N0', 'ep_N0'],
        'IO_E0': ['lk_N2', 'ep_N2'], 'IO_E1': [], 'IO_E2': ['lk_S3', 'ep_S3'],
    }
    placed = set()
    for pn, lst in plan.items():
        r = P[pn]['r']
        x, y, rowh = r[0] + 20, r[1] + 20, 0
        for n in lst:
            if n not in insts:
                continue
            i = insts[n]
            if x + i['w'] > r[2] - 10:
                x, y, rowh = r[0] + 20, y + rowh + 20, 0
            i['x'], i['y'] = x, y
            x += i['w'] + 20; rowh = max(rowh, i['h'])
            placed.add(n)
    for i in insts.values():
        i['cx'], i['cy'] = i['x'] + i['w'] / 2, i['y'] + i['h'] / 2
    return placed


def assign(insts, parts):
    """inst -> partition holding its centre (canonical positions)."""
    grid = collections.defaultdict(list)
    for p in parts:
        r = p['r']
        for gx in range(int(r[0] // 1000), int(r[2] // 1000) + 1):
            for gy in range(int(r[1] // 1000), int(r[3] // 1000) + 1):
                grid[(gx, gy)].append(p)
    where, lost = {}, []
    for i in insts.values():
        c = (i['cx'], i['cy'])
        hit = [p for p in grid[(int(c[0] // 1000), int(c[1] // 1000))] if inside(p['r'], c)]
        if not hit:
            lost.append(i['name']); continue
        where[i['name']] = hit[0]['name']
    return where, lost


# ------------------------------------------------------------------------------------------------ render
def render(parts, insts, where, path, lanes_load=None, title=''):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt, matplotlib.patches as pa
    col = {'anchor': '#9ecae1', 'fabric': '#f0f0f0', 'centre': '#fdd0a2', 'io': '#c7e9c0', 'phy': '#bdbdbd'}
    fig, ax = plt.subplots(figsize=(13, 16.5))
    for p in parts:
        r = p['r']
        ax.add_patch(pa.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col[p['kind']], ec='k', lw=.35))
    for i in insts.values():
        ax.add_patch(pa.Rectangle((i['x'], i['y']), i['w'], i['h'], fc='none', ec='#d62728', lw=.25))
    for p in parts:
        r = p['r']
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, p['name'], fontsize=3.2, ha='center', va='center')
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
    ax.set_xticks(range(0, 26001, 1000)); ax.set_yticks(range(0, 33001, 1000)); ax.tick_params(labelsize=5)
    ax.set_title(title, fontsize=8)
    plt.tight_layout(); plt.savefig(path, dpi=130); plt.close(fig)



# ------------------------------------------------------------------------------------------------ graph
OPB = {'I': 0, 'MY': 1, 'MX': 2, 'R': 3}
BOP = {v: k for k, v in OPB.items()}


def rkey(r):
    return tuple(round(v, 2) for v in r)


def build_graph(parts):
    byr = {rkey(p['r']): p['name'] for p in parts}
    for p in parts:
        p['mir'] = {}
        for g in OPS:
            p['mir'][OPB[g]] = byr.get(rkey(mrect(g, p['r'])))
        p['qb'] = OPB[p['op']]
    segs = {}                                       # (a,b) sorted -> dict
    vx = collections.defaultdict(lambda: ([], []))
    hy = collections.defaultdict(lambda: ([], []))
    for p in parts:
        r = p['r']
        vx[round(r[2], 2)][0].append(p); vx[round(r[0], 2)][1].append(p)
        hy[round(r[3], 2)][0].append(p); hy[round(r[1], 2)][1].append(p)
    for x, (L, R) in vx.items():
        for a in L:
            for b in R:
                lo, hi = max(a['r'][1], b['r'][1]), min(a['r'][3], b['r'][3])
                if hi - lo > 1e-3:
                    segs[tuple(sorted((a['name'], b['name'])))] = dict(o='V', at=x, lo=lo, hi=hi, len=hi - lo,
                        side={a['name']: 'E', b['name']: 'W'}, mid=(x, (lo + hi) / 2))
    for y, (B, T) in hy.items():
        for a in B:
            for b in T:
                lo, hi = max(a['r'][0], b['r'][0]), min(a['r'][2], b['r'][2])
                if hi - lo > 1e-3:
                    segs[tuple(sorted((a['name'], b['name'])))] = dict(o='H', at=y, lo=lo, hi=hi, len=hi - lo,
                        side={a['name']: 'N', b['name']: 'S'}, mid=((lo + hi) / 2, y))
    adj = collections.defaultdict(list)
    for (a, b), s_ in segs.items():
        s_["cap"] = WIN_PER_UM * s_["len"] * 0.80     # routing margin for slice rounding
        if fl3(a, b, s_['o']):
            s_["cap"] *= OS3_CAP                        # 3 pin layers (M7/M5 + die M9): up to 9/um; router margin
        adj[a].append((b, (a, b))); adj[b].append((a, (a, b)))
    return segs, adj


def centre(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def md(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


# ------------------------------------------------------------------------------------------------ lanes
SPLIT_OF = {}
SPLIT_LAND = {}          # P3 (COORD R6 R2-alt): every external SM lane lands on the front quarter c
SM_DIRECT = os.environ.get('OT_HBM_SM_DIRECT', '1') == '1'   # P4: abutting SM-quarter lanes = one direct hop
SM_MODE = os.environ.get('OT_HBM_SM_MODE', 'inner_c')  # inner_c (published, COORD option C+A) | off: pre-R6 | inner: COORD R6 rule, G0 FAIL on the current floorplan | strict: no route
# | inner_c: COORD option (C) 10-23 -- SM ports on c, SM-internal lanes planned, die ft may use the inner SM faces up to
#   their free capacity (the SM-internal lanes are routed first-class and share the face budget), plus (A) os M9 faces


def sm_part(v):
    return re.match(r'^(NW|NE|SW|SE)_sm\d[a-d]$', v) is not None


def sm_pair(u, v):
    """u, v = two quarters of the same SM stack (an inner SM face)."""
    a = re.match(r'^(NW|NE|SW|SE)_sm(\d)[a-d]$', u); b = re.match(r'^(NW|NE|SW|SE)_sm(\d)[a-d]$', v)
    return bool(a and b and a.groups() == b.groups())


XLAND = os.environ.get('OT_HBM_XLAND', 'xw')  # P4 study 'a': all SM lanes from the VM side land on a | 'c': R2-alt
# | P5 'xw' (default, COORD HBM PRICE RULING 14:44 (1)): only the x-write lanes (xw_*) from the VM slice land on the
#   VM-facing quarter a; the SM relays them a->b->c inside its own stack (planned SM-internal rows, 2079 b per SM)


def xland_a(other_part, bus=None):
    """XLAND=a: the peer is not a per-SM service partition (svc*), so the lane lands on the nearest quarter
    (a, facing the VM / SU row) and the SM relays it a->b->c inside (planned SM-internal rows).  XLAND=xw: the same
    for the SM x-write buses only."""
    if other_part is None or re.match(r'^(NW|NE|SW|SE)_svc\d$', other_part):
        return False
    return XLAND == 'a' or (XLAND == 'xw' and bus is not None and bus.startswith('xw_'))


STEPC_MASTER = {
    # COORD R6 (3) QUANT x4 (HBM-P4-QUANT claude/hbm-p4-quant-1023 @690e86d3d): the NW programme leaf has target 48
    # hard-wired; every quadrant's engine needs its own target (0x30+Q), so all 4 use the strapped leaf.
    'ot_hgi_qdq_nw_program_leaf': ('ot_hgi_qdq_q_program_leaf', 'new',
                                   'Step C QUANT x4: ot_hgi_qdq_q_program_leaf (TGT 0x30+Q strap, 415 pins); no view yet'),
}


def nearest_sub(inst, other_part, P, bus=None):
    if inst in SPLIT_LAND and other_part is not None and not xland_a(other_part, bus):
        return SPLIT_LAND[inst]
    subs = SPLIT_OF.get(inst)
    if not subs or other_part is None:
        return None
    oc = centre(P[other_part]['r'])
    return min(subs, key=lambda n: md(centre(P[n]['r']), oc))


def bundles(cen, where, P):
    """Bundle = one source partition driving a SET of destination partitions (a broadcast is routed as a tree,
    not as N parallel lanes).  Key (src partition, frozenset(dst partitions), kind); bits = sum of unique source
    bus widths."""
    nets = collections.OrderedDict()
    for gi, x in enumerate(cen['groups']):
        s = where.get(x['src']); t = where.get(x['dst'])
        if s is None or t is None:
            continue
        s = nearest_sub(x['src'], t, P, x['src_bus']) or s     # split SM: the lane lands on the sub-partition facing its peer
        t = nearest_sub(x['dst'], s, P, x['dst_bus']) or t
        n = nets.setdefault((x['src'], x['src_bus'], x['kind']), dict(sp=s, bits=0, dsts=set(), members=[],
                                                                       per=collections.Counter(), cap=x.get('wcap')))
        n['bits'] = max(n['bits'], x['bits'])
        if t != s:
            n['dsts'].add(t)
            n['per'][t] += x['bits']            # V2: rows into one partition add up (split buses), capped at the width
        n['members'].append(gi)
    B = collections.OrderedDict()
    for (si, sb, kind), n in nets.items():
        if not n['dsts']:
            continue
        if n['per']:
            n['bits'] = max(min(v, n['cap']) if n['cap'] else v for v in n['per'].values())
        k = (n['sp'], frozenset(n['dsts']), kind)
        b = B.setdefault(k, dict(src=n['sp'], dsts=sorted(n['dsts']), kind=kind, bits=0, members=[], nets=[]))
        b['bits'] += n['bits']
        b['members'] += n['members']
        b['nets'].append((si, sb))
        b.setdefault('nbits', []).append(n['bits'])      # P5: per-net bits (slice -> bus map for word landing)
    return B


B_ALL = {}


def orbits(B, P):
    B_ALL.clear(); B_ALL.update(B)
    done, orb = set(), []
    for k, b in B.items():
        if k in done:
            continue
        mem = {}
        for gb in range(4):
            s2 = P[k[0]]['mir'][gb]
            t2 = [P[t]['mir'][gb] for t in k[1]]
            if s2 is None or None in t2:
                continue
            k2 = (s2, frozenset(t2), k[2])
            if k2 in B and k2 not in done and k2 not in mem.values():
                mem[gb] = k2
        if 0 not in mem:
            mem[0] = k
        for v in mem.values():
            done.add(v)
            B[v]['_rep'] = mem[0]               # P5: every image slices like the orbit representative
        orb.append(mem)
    return orb


def route_all(parts, segs, adj, B, orb, iters=40, log=print):
    P = {p['name']: p for p in parts}
    C = {p['name']: centre(p['r']) for p in parts}
    notransit = {p['name'] for p in parts if p['kind'] in ('phy', 'io')}
    hist = collections.Counter()
    # slices: (orbit idx, slice idx, bits per member)
    jobs = []
    for oi, mem in enumerate(orb):
        rep = B[mem[0]]
        ns = len(slice_plan(rep))
        jobs.append((oi, ns))
    paths = {}
    load = collections.Counter()

    def dijk(srcs, t, wbits, gbs=(0,), allow=None, smint=False):
        """State = (partition, entry face): a lane never leaves a partition through the face it entered.
        P3: allow = quadrants a transit partition may belong to (quadrant containment: a lane only crosses partitions
        of its own endpoint quadrants; cross-quadrant traffic stays on the planned rings)."""
        st0 = [(u, None) for u in srcs]
        dist = {x: 0.0 for x in st0}; prev = {}
        pq = [(0.0, i, x) for i, x in enumerate(st0)]
        heapq.heapify(pq)
        cnt = len(pq); goal = None
        while pq:
            d_, _, x = heapq.heappop(pq)
            u, fin = x
            if u == t:
                goal = x
                break
            if d_ > dist[x] + 1e-9:
                continue
            for v, sk in adj[u]:
                if v in notransit and v != t:
                    continue
                if allow is not None and v != t and quadn(v) not in allow:
                    continue
                if not smint and SM_MODE in ('inner', 'inner_d', 'strict') and sm_pair(u, v):
                    continue                    # COORD R6 (2): die lanes stay off the inner SM faces
                if SM_MODE == 'strict' and v != t and sm_part(v) and not smint:
                    continue                    # strict: no die feedthrough in any SM quarter
                if v in srcs:
                    continue                    # a branch never re-enters the tree (one parent per node)
                sg = segs[sk]
                if fin is not None and sg['side'][u] == fin:
                    continue
                if any(P[v]['mir'][g_] is None for g_ in gbs):
                    continue
                base = md(C[u], sg['mid']) + md(sg['mid'], C[v])
                wm = wbits / len(gbs)
                over = 0.0
                for g_ in gbs:
                    mk = sk if g_ == 0 else tuple(sorted((P[u]['mir'][g_], P[v]['mir'][g_])))
                    over = max(over, (load[mk] + wm) / segs[mk]['cap'] - 1.0)
                if HARD and over > 0:
                    continue
                c = base * (1.0 + (0.0 if NOHIST else hist[sk])) * (1.0 + PRES * over) + 1.0
                nd = d_ + c
                y = (v, sg['side'][v])
                if nd < dist.get(y, 1e30):
                    dist[y] = nd; prev[y] = x; cnt += 1; heapq.heappush(pq, (nd, cnt, y))
        if goal is None:
            return None
        path = [goal]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        nodes = [x[0] for x in path[::-1]]
        out = []                                # loop erase: a partition is crossed at most once
        for n in nodes:
            if n in out:
                out = out[:out.index(n) + 1]
            else:
                out.append(n)
        return out

    def tree(rep, wbits, gbs):
        nodes = {rep['src']}; edges = []
        allow = {quadn(rep['src'])} | {quadn(t) for t in rep['dsts']}
        smint = all(sm_pair(rep['src'], t) for t in rep['dsts'])
        if (SM_DIRECT and smint and len(rep['dsts']) == 1
                and tuple(sorted((rep['src'], rep['dsts'][0]))) in segs):
            # P4: an SM-internal quarter lane between ABUTTING quarters is one direct registered hop, never split
            # around the stack (P3 routed 59-61 slices of smq c->b/b->a around, land_pad up to 31 cycles inside
            # the SM op).  The die ft lanes negotiate for the remaining inner-face capacity (option C).
            return [(rep['src'], rep['dsts'][0])]
        for t in sorted(rep['dsts'], key=lambda t: md(C[rep['src']], C[t])):
            p_ = dijk(nodes, t, wbits, gbs, allow, smint)
            if p_ is None:
                p_ = dijk(nodes, t, wbits, gbs, None, smint)   # no contained route: fall back (reported as a leak)
            if p_ is None:
                return None
            edges += list(zip(p_, p_[1:])); nodes |= set(p_)
        return edges

    def apply(oi, sl, ns, edges, sign):
        mem = orb[oi]
        for gb, k in mem.items():
            b = B[k]
            wb = swidth(b, sl, ns)
            for u, v in edges:
                load[tuple(sorted((P[u]['mir'][gb], P[v]['mir'][gb])))] += sign * wb

    global PRES
    best = None
    for it in range(iters):
        PRES = 0.5 * (1.3 ** it)
        order = sorted(range(len(jobs)), key=lambda j: -B[orb[jobs[j][0]][0]]['bits'])
        for j in order:
            oi, ns = jobs[j]
            rep = B[orb[oi][0]]
            for sl in range(ns):
                key = (oi, sl)
                if key in paths:
                    apply(oi, sl, ns, paths[key], -1)
                wb = swidth(rep, sl, ns) + 1
                p_ = tree(rep, wb * len(orb[oi]), tuple(orb[oi]))
                if p_ is None:
                    raise SystemExit(f'no route {rep["src"]}->{rep["dsts"]}')
                paths[key] = p_
                apply(oi, sl, ns, p_, +1)
        ovf = [(load[k] / s_['cap'], k) for k, s_ in segs.items() if load[k] > s_['cap']]
        for k, s_ in segs.items():
            if load[k] > s_['cap']:
                hist[k] += 0.5 * (load[k] / s_['cap'] - 1)
        worst = max([load[k] / s_['cap'] for k, s_ in segs.items()] + [0])
        score = sum(max(0, load[k] - s_['cap']) for k, s_ in segs.items())
        if best is None or score < best[0]:
            best = (score, dict(paths), collections.Counter(load), it)
        log(f'iter {it}: overfull segments {len(ovf)}, worst face use {worst:.2f} of {PIN_PER_UM}/um')
        if not ovf:
            break
    log(f'best iteration {best[3]}: overflow bits {best[0]}')
    paths.clear(); paths.update(best[1]); load.clear(); load.update(best[2])
    # repair: reroute slices that use an overfull face with a hard capacity limit
    global HARD
    for rnd in range(6):
        hot = {k for k, s_ in segs.items() if load[k] > s_['cap'] + 1e-6}
        if not hot:
            break
        fixed = 0
        for (oi, sl), edges in sorted(paths.items(), key=lambda kv: B[orb[kv[0][0]][0]]['bits']):
            mem = orb[oi]
            used = {tuple(sorted((P[u]['mir'][gb], P[v]['mir'][gb]))) for gb in mem for u, v in edges}
            if not used & hot:
                continue
            ns = next(n for o, n in jobs if o == oi)
            apply(oi, sl, ns, edges, -1)
            rep = B[mem[0]]
            HARD = True
            p_ = tree(rep, (swidth(rep, sl, ns) + 1) * len(mem), tuple(mem))
            HARD = False
            if p_ is None:
                apply(oi, sl, ns, edges, +1)
            else:
                paths[(oi, sl)] = p_; apply(oi, sl, ns, p_, +1); fixed += 1
            hot = {k for k, s_ in segs.items() if load[k] > s_['cap'] + 1e-6}
            if not hot:
                break
        ovb = sum(max(0, load[k] - s_['cap']) for k, s_ in segs.items())
        log(f'repair {rnd}: rerouted {fixed}, overfull {len(hot)}, overflow bits {ovb:.0f}')
    # P3 equal-depth pass: slices of one lane must land together (one landed group).  The negotiated history makes
    # some slices detour (up to 39 cycles of skew on main 5850706a3).  Reroute every slice of a multi-slice orbit,
    # longest first, on the shortest path that fits the hard face capacity with the history ignored; keep it only
    # if it is not longer.  The residual skew is padded at the landing (finalize).
    global NOHIST

    def plen(edges):
        return sum(md(C[u], C[v]) for u, v in edges)

    def ovsum():
        return sum(max(0, load[k] - s_['cap']) for k, s_ in segs.items())
    for rnd in range(3):
        better = 0
        for (oi, sl), edges in sorted(paths.items(), key=lambda kv: -plen(kv[1])):
            ns = next(n for o, n in jobs if o == oi)
            if ns < 2:
                continue
            mem = orb[oi]; rep = B[mem[0]]
            ovs0 = ovsum()
            apply(oi, sl, ns, edges, -1)
            NOHIST = True; PRES = 50.0
            p_ = tree(rep, (swidth(rep, sl, ns) + 1) * len(mem), tuple(mem))
            NOHIST = False
            if p_ is not None and plen(p_) < plen(edges) - 1e-6:
                apply(oi, sl, ns, p_, +1)
                if ovsum() <= ovs0 + 1e-6:        # shorter and the face overflow does not grow
                    paths[(oi, sl)] = p_; better += 1
                    continue
                apply(oi, sl, ns, p_, -1)
            apply(oi, sl, ns, edges, +1)
        ovb = sum(max(0, load[k] - s_['cap']) for k, s_ in segs.items())
        log(f'equalise {rnd}: shortened {better} slices, overflow bits {ovb:.0f}')
        if not better:
            break
    return paths, load


PRES = 1.0
HARD = False
NOHIST = False


OS3 = os.environ.get('OT_HBM_OS3', '1') == '1' and SM_MODE != 'off'   # COORD 10-23 option (A)
OS3_CAP = float(os.environ.get('OT_HBM_OS3_CAP', '1.2'))


def os_part(n):
    return re.match(r'^(NW|NE|SW|SE)_os\d$', n) is not None


# P6 (COORD 10-23 18:23 (1), VM|SU2 face overflow): the VM slice is the quadrant hub and its perimeter is saturated
# (52.5 kb of endpoint traffic on 10.45 mm; every VM face at 4.4-5.4/um).  Moving lanes between VM faces is zero-sum
# (P6 variants a/b: hb_idx__op off the VM -> vm|su2 5.41-5.43/um, hc0|hcq and rc3|rc4 worse).  The two 2.9-mm E/W
# faces between the VM and SU1/SU2 therefore get a second face on a third pin layer from the die budget, die M8
# (H, as the S81 svc fold faces, COORD 10-23 07:43; the os N/S faces take M9, COORD option (A)).  SM faces never do.
VM3 = os.environ.get('OT_HBM_VM3', '1') == '1'


def vm_su_pair(a, b):
    r = {re.sub(r'^(NW|NE|SW|SE)_', '', n) for n in (a, b)}
    return 'vm' in r and bool(r & {'su1', 'su2'})


def fl3(a, b, o):
    """COORD option (A): an H boundary (N/S faces) between two non-SM partitions, one of them in the os column, takes
    a third (die M9) pin layer.  SM faces never do.  P6: the VM|SU1 and VM|SU2 V boundaries take die M8."""
    if VM3 and o == 'V' and vm_su_pair(a, b):
        return True
    return OS3 and o == 'H' and not (sm_part(a) or sm_part(b)) and (os_part(a) or os_part(b))


def lay(face, k, o):
    base = {'E': ['M6', 'M4'], 'W': ['M6', 'M4'], 'N': ['M7', 'M5'], 'S': ['M7', 'M5']}[face]
    return base + (['M9'] if o == 'H' else ['M8']) if fl3(k[0], k[1], o) else base


def quadn(n):
    q = n.split('_')[0]
    return q if q in ('NW', 'NE', 'SW', 'SE') else 'X'


# ------------------------------------------------------------------------------------------------ status
REWORK = ('ot_hbm_accel_smh_attn', 'ot_hbm_su_static_pgslice_lg', 'ot_hgi_sfu_core_split3', 'ot_hbm_hc_qhub_static',
          'hfd_hgi_vms', 'ot_hgi_coll_tkm', 'ot_hbm_su_programme_pslice', 'ot_hgi_sfu_programme_store',
          'ot_hbm_idx_score_quarter', 'ot_hbm_svc_sm_group', 'ot_hfd_coll_q', 'ot_hbm_su_static_sfustore',
          'ot_hbm_idx_selector', 'ot_hbm_idx_topk_link', 'ot_hbm_hc_root',
          'ot_hbm_hc_bankq0_static', 'ot_hbm_hc_bankq_ft_static')   # COORD BAD verdicts: no reuse
IP = ('ot_hbm3e_phy', 'ot_pdie_serdes', 'ot_pdie_ucie')


def status(fam_):
    if fam_.startswith(IP):
        return 'reuse', 'hard IP'
    if fam_.startswith(REWORK):
        return 'rework', 'parent/cluster/hub: re-derived from the partition spec'
    return 'reuse', 'leaf: reuse if it meets the spec (registered ports, insertion, GEOM PASS) - check at G3'


# ------------------------------------------------------------------------------------------------ emit
def emit(parts, segs, B, orb, paths, insts, where, cen, out):
    P = {p['name']: p for p in parts}
    segcap = {k: PIN_PER_UM * s_['len'] for k, s_ in segs.items()}
    LAY = {'E': ['M6', 'M4'], 'W': ['M6', 'M4'], 'N': ['M7', 'M5'], 'S': ['M7', 'M5']}
    nsl = {}
    for (oi, sl) in paths:
        nsl[oi] = max(nsl.get(oi, 0), sl + 1)
    seg_fill = collections.Counter()                  # running window allocation per segment
    pbus = collections.defaultdict(dict)              # part -> local bus name -> spec (type frame)
    pslot = collections.defaultdict(dict)             # part -> local slot name -> spec
    ports, lanes, lat = [], [], {}
    warn = collections.Counter()
    hop_max = 0.0
    lane_cycles_by_dst = {}                           # (orbit, gb, dst part) -> max cycles over slices
    stn_total = 0
    cut_v = collections.Counter(); cut_h = collections.Counter()

    def loc(part, lid, gb):
        return f'{lid}{"abcd"[P[part]["qb"] ^ gb]}'

    def tface(part, f):
        return mface(P[part]['op'], f)

    # window allocation: one fill pointer per segment ORBIT (mirror images share it), so mirrored instances of a
    # type see mirrored windows (identical type-frame pin tables); self-symmetric segments allocate directly
    canon, alloc = {}, {}
    for k in segs:
        best = None; selfsym = False
        for g_ in range(4):
            m = tuple(sorted((P[k[0]]['mir'][g_], P[k[1]]['mir'][g_]))) if None not in (P[k[0]]['mir'][g_], P[k[1]]['mir'][g_]) else None
            if m is None or m not in segs:
                continue
            if g_ and m == k:
                selfsym = True
            if best is None or m < best[0]:
                best = (m, g_)
        canon[k] = (best[0], best[1], selfsym)
    wmax = collections.Counter()
    wset = collections.defaultdict(set)                 # V2: every member width of an orbit slice
    for (oi, sl) in paths:
        for gb, key in orb[oi].items():
            b = B[key]; ns = nsl[oi]
            wmax[(oi, sl)] = max(wmax[(oi, sl)], swidth(b, sl, ns))
            wset[(oi, sl)].add(swidth(b, sl, ns))   # V2
    own_fill = collections.Counter()
    lane_meta = {}
    lane_words = {}
    full = {}
    for oi, mem in enumerate(orb):
        rb = B[mem[0]]
        imgs = set()
        for g_ in range(4):
            sm = P[rb['src']]['mir'][g_]; dm = [P[t]['mir'][g_] for t in rb['dsts']]
            if sm is not None and None not in dm:
                imgs.add((sm, frozenset(dm)))
        full[oi] = len(mem) == len(imgs) and len(mem) > 1
    for (oi, sl), edges in sorted(paths.items(), key=lambda kv: (not full[kv[0][0]], kv[0])):
        mem = orb[oi]
        for gb, key in sorted(mem.items()):
            b = B[key]
            ns = nsl[oi]
            wb = swidth(b, sl, ns)
            if wb <= 0:
                continue
            lid = f'L{oi}s{sl}'
            dleaf = {}
            for gi in b['members']:
                x = cen['groups'][gi]
                t = where.get(x['dst'])
                if t is None:
                    continue
                t = nearest_sub(x['dst'], b['src'], P, x['dst_bus']) or t
                dleaf.setdefault(t, (x['dst'], x['dst_bus']))
            E = [(P[u]['mir'][gb], P[v]['mir'][gb]) for u, v in edges]
            root = b['src']
            dsts = set(b['dsts'])
            kids = collections.defaultdict(list); par = {}
            for u, v in E:
                kids[u].append(v); par[v] = u
            # drop nodes not reachable from the root (mirror image of an asymmetric member)
            reach_ = {root}; st_ = [root]
            while st_:
                x_ = st_.pop()
                for y_ in kids[x_]:
                    if y_ not in reach_:
                        reach_.add(y_); st_.append(y_)
            for v in [v for v in par if v not in reach_]:
                del par[v]; warn['unreachable_node'] += 1
            for x_ in list(kids):
                if x_ not in reach_:
                    kids[x_] = []
            E = [(u, v) for u, v in E if u in reach_ and v in reach_]
            # prune dangling non-destination branches (mirror image of a member whose destination set differs)
            while True:
                dead = [v for v in par if not kids[v] and v not in dsts]
                if not dead:
                    break
                for v in dead:
                    kids[par[v]].remove(v); del par[v]; warn['pruned_branch'] += 1
                E = [(u, v) for u, v in E if v in par and par[v] == u]
            miss = [t for t in dsts if t not in par and t != root]
            if miss:
                warn['unreached_dst'] += len(miss)

            def sk(u, v):
                return tuple(sorted((u, v)))

            # a crossing that leaves through its entry face (loop-erased route) becomes a registered turn
            # (functional in + re-launch), never an ft slot with in_face == out_face
            for v in list(par):
                if v not in dsts and kids[v] and segs[sk(par[v], v)]['side'][v] == segs[sk(v, kids[v][0])]['side'][v]:
                    dsts.add(v); warn['turn_stations'] += 1

            # stations per crossed (non-dst) node with children
            stations, arr = {}, {root: 0}
            order = [root]
            for u in order:
                for v in kids[u]:
                    order.append(v)
            for v in order[1:]:
                u = par[v]
                ein = segs[sk(u, v)]['mid']
                if v in dsts:
                    arr[v] = arr[u] + 1
                    # leaf to face distance inside the destination partition
                    lf = [insts[n] for n in (x['dst'] for x in []) ]
                    continue
                c0 = kids[v][0]
                eout = segs[sk(v, c0)]['mid']
                L = md(ein, eout)
                n = max(1, math.ceil(L / REACH - 1e-9))
                stations[v] = n
                hop_max = max(hop_max, L / n)
                arr[v] = arr[u] + n
            for u, v in E:
                p0, p1 = segs[sk(u, v)]['mid'], None
            # ports
            pid = {}
            for u, v in E:
                s_ = segs[sk(u, v)]
                face = s_['side'][u]
                k = sk(u, v)
                ck, h, selfsym = canon[k]
                if selfsym and not full[oi]:   # V2: full orbits allocate mirror-consistently on self-symmetric segments too
                    wlen = fit_len(s_['lo'] + seg_fill[k], wb + 1, lay(face, k, s_['o']))     # + in-band epoch bit
                    lo = s_['lo'] + seg_fill[k]; seg_fill[k] += wlen; flip = False
                    if seg_fill[k] > s_['len'] + 1e-6:
                        warn['window_overflow'] += 1
                elif not full[oi]:
                    flip = (s_['o'] == 'V' and h & 2) or (s_['o'] == 'H' and h & 1)
                    F = seg_fill[ck]
                    wlen = fit_len(s_['lo'] + F + own_fill[k], wb + 1, lay(face, k, s_['o']))
                    if flip:
                        lo = s_['hi'] - F - own_fill[k] - wlen
                    else:
                        lo = s_['lo'] + F + own_fill[k]
                    own_fill[k] += wlen
                    if F + own_fill[k] > s_['len'] + 1e-6:
                        warn['window_overflow'] += 1
                else:
                    akey = (oi, sl, ck, (P[u]['mir'][h], P[v]['mir'][h]), gb ^ h)   # V2: direction-sensitive + relative image (two images of one orbit on one segment)
                    if akey not in alloc:
                        alloc[akey] = segs[ck]['lo'] + seg_fill[ck]
                        seg_fill[ck] += max(fit_len(alloc[akey], w_ + 1, lay(face, k, s_['o'])) for w_ in wset[(oi, sl)] if w_ > 0)   # V2: window length is not monotone in the pin count (parity)
                        if seg_fill[ck] > segs[ck]['len'] + 1e-6:
                            warn['window_overflow'] += 1
                    lc = alloc[akey]
                    wlen = fit_len(lc, wb + 1, lay(face, k, s_['o']))
                    flip = (s_['o'] == 'V' and h & 2) or (s_['o'] == 'H' and h & 1)
                    if flip:
                        ext = H if s_['o'] == 'V' else W
                        lo = ext - lc - wlen
                    else:
                        lo = lc
                # source end
                if u == root:
                    j = kids[u].index(v)
                    sbus = f'{loc(u, lid, gb)}_o' if j == 0 else f'{loc(u, lid, gb)}_f{j}_o'
                    pbus[u][sbus] = dict(name=sbus, dir='out', width=wb, kind=b['kind'],
                                         leaf=('I', b['nets'][0][0], b['nets'][0][1]))
                elif u in dsts:
                    j = kids[u].index(v)
                    sbus = f'{loc(u, lid, gb)}_r{j}_o'
                    pbus[u][sbus] = dict(name=sbus, dir='out', width=wb, kind=b['kind'], leaf=('S', f'rl_{loc(u, lid, gb)}', 'q'),
                                         note='re-launch of a delivered broadcast word to a further destination')
                elif kids[u][0] == v:
                    sbus = f'{loc(u, lid, gb)}_o'
                else:
                    j = kids[u].index(v)
                    sbus = f'{loc(u, lid, gb)}_k{j}_o'
                    pbus[u][sbus] = dict(name=sbus, dir='out', width=wb, kind=b['kind'], leaf=('S', f'fk_{loc(u, lid, gb)}', 'q'),
                                         note='broadcast fork from the ft station')
                # destination end
                if v in dsts:
                    dbus = f'{loc(v, lid, gb)}_i'
                    dl = dleaf.get(v)
                    pbus[v][dbus] = dict(name=dbus, dir='in', width=wb, kind=b['kind'],
                                         leaf=('I',) + dl if dl else ('S', f'rl_{loc(v, lid, gb)}', 'd'))
                else:
                    dbus = f'{loc(v, lid, gb)}_i'
                    c0 = kids[v][0]
                    pslot[v][loc(v, lid, gb)] = dict(name=loc(v, lid, gb), in_face=tface(v, segs[sk(u, v)]['side'][v]),
                                                     out_face=tface(v, segs[sk(v, c0)]['side'][v]), width=wb,
                                                     stations=stations[v])
                portid = f'{lid}{"abcd"[gb]}_{len(pid)}'
                pid[(u, v)] = portid
                ports.append(dict(id=portid, src=dict(part=u, bus=sbus), dst=dict(part=v, bus=dbus), width=wb,
                                  kind=b['kind'], face=face, layers=lay(face, k, s_['o']),
                                  window_um=[round(lo, 3), round(lo + wlen, 3)],
                                  order='lsb_high' if flip else 'lsb_low'))
                # cut sweep (straight L between the two crossing points)
            # lanes: chains
            starts = [(root, kids[root][j], 0) for j in range(len(kids[root]))]
            for u in order:
                if u == root:
                    continue
                if u in dsts:
                    starts += [(u, v, arr[u]) for v in kids[u]]
                else:
                    starts += [(u, v, arr[u]) for v in kids[u][1:]]
            for li, (u, v, fixed) in enumerate(starts):
                u0 = u
                chain = [pid[(u, v)]]
                cyc = 1; nst = 0
                while v not in dsts:
                    nst += stations[v]
                    u, v = v, kids[v][0]
                    chain.append(pid[(u, v)])
                cyc = nst + 1 + fixed
                lname = f'{lid}{"abcd"[gb]}_{li}'
                lanes.append(dict(id=lname, ports=chain, fixed_cycles=fixed))
                lane_meta[lname] = ((oi, sl, gb), u0, 'root' if u0 == root else 'relaunch' if u0 in dsts else 'fork')
                lane_words[lname] = slice_nets(b, sl, ns)
                lat[lname] = dict(cycles=cyc, stations=nst, faces=len(chain), fixed=fixed)
                kk = (oi, gb, v)
                lane_cycles_by_dst[kk] = max(lane_cycles_by_dst.get(kk, 0), cyc)
            stn_total += sum(stations.values()) * wb
            # cut sweep along the tree edges (centre to centre)
            for u, v in E:
                a_, c_ = centre(P[u]['r']), centre(P[v]['r'])
                for xg in range(int(min(a_[0], c_[0]) // 250) + 1, int(max(a_[0], c_[0]) // 250) + 1):
                    cut_v[xg] += wb
                for yg in range(int(min(a_[1], c_[1]) // 250) + 1, int(max(a_[1], c_[1]) // 250) + 1):
                    cut_h[yg] += wb
    finalize(P, ports, lanes, lane_meta, pslot, lat, lane_words)
    return dict(ports=ports, lanes=lanes, lat=lat, pbus=pbus, pslot=pslot, warn=warn, hop_max=hop_max,
                lane_cycles_by_dst=lane_cycles_by_dst, stn_bits=stn_total, cut_v=cut_v, cut_h=cut_h,
                seg_fill=seg_fill)


TRK = {'M4': (0.048, 0.024), 'M5': (0.048, 0.024), 'M6': (0.064, 0.032), 'M7': (0.064, 0.032)}
FACE_LIM = 58                                  # pins in any 10-um face window (budget 60 = 6/um, 2 pins margin)


def pin_spread(lo, hi, pins, layers):
    """Pin coordinates exactly as PLAN-TOOL schema.pin_positions places them (centred tracks, floor step, parity)."""
    out = []
    for li, ln in enumerate(layers):
        p, off = TRK[ln]
        n = len(range(li, pins, len(layers)))
        if not n:
            continue
        k0 = math.ceil((lo - off) / p - 1e-9); k1 = math.floor((hi - off) / p + 1e-9)
        ntr = k1 - k0 + 1
        if ntr < n:
            return None
        step = max(1, ntr // n); twoc = k0 + k1
        if (twoc - (n - 1) * step) % 2 and step > 1:
            step -= 1
        first = (twoc - (n - 1) * step) // 2
        out += [off + (first + j * step) * p for j in range(n)]
    return sorted(out)


def fit_len(lo, pins, layers):
    """Shortest window from lo whose pins stay within the 10-um face budget (the floor step + parity of the
    track spreader packs pins up to ~1.2x denser than the window average, so windows are grown until they pass)."""
    w = pins / WIN_PER_UM
    while True:
        cs = pin_spread(lo, lo + w, pins, layers)
        if cs is not None:
            mx = 0; j = 0
            for i in range(len(cs)):
                while cs[i] - cs[j] > 10.0 - 1e-6:
                    j += 1
                mx = max(mx, i - j + 1)
            if mx <= FACE_LIM:
                return w
        w *= 1.03


PAD_MODE = os.environ.get('OT_HBM_PAD', 'word')   # P5 (COORD HBM PRICE RULING 14:44 (2)): word | group (P3/P4)


# Word element of a bus that is an ARRAY of independently consumed words (one word per bank / lane group); a word
# is padded only against the slices that carry the same element.  Evidence:
#   VM ring cw/ccw (ring_h/ring_v after renaming): 2224 = 8 x 278, 'lane b <-> bank b' (ot_vms_slice_clocked.sv,
#     ot_vms_rstop per-bank eg/xq 276 b + 2 VC bits): each bank's ring lane is consumed by its own bank tile.
#   lane-group fixed-return buses rq/rr/wq/dq (17 / 257 / 281 / 281 b per lane group: ot_vms_slice_clocked rq
#     [RG*8*17], rr [RG*8*257], wq [WG*8*281]; ot_hgi_sfu_lg_relay c_rq/c_wq/c_rr per bank with its own valid bit).
WORD_ELEM = [
    (re.compile(r'^hb_vms_.*\.(pr_)?(ring_[hv]|c?cw)(_out|_in)?$'), 278),
    (re.compile(r'\.(lg_|c_|l_)?rq\d*$'), 17),
    (re.compile(r'\.(lg_|c_|l_)?rr\d*$'), 257),
    (re.compile(r'\.(lg_|c_|l_)?(wq|dq)\d*$'), 281),
]


def word_elem(name, nb):
    for rx, e in WORD_ELEM:
        if rx.search(name) and nb % e == 0 and nb > e:
            return e
    return None


WORD_SLICE = int(os.environ.get('OT_HBM_WORD_SLICE', '256'))   # P5: slice size inside one word (fewer windows per face)
ALIGN = os.environ.get('OT_HBM_SLICE_ALIGN', '1') == '1' and os.environ.get('OT_HBM_PAD', 'word') == 'word'


def slice_plan(b):
    """P5: slice widths of bundle b.  Element-array buses (WORD_ELEM) are cut on element boundaries, so every slice
    carries whole words of ONE element (or whole small elements packed together) and words never chain across slices;
    the other nets are split evenly as before.  Cached on the bundle."""
    if '_sw' in b:
        return b['_sw']
    if b.get('_rep') is not None and B_ALL.get(b['_rep']) is not None and B_ALL[b['_rep']] is not b:
        R = slice_plan(B_ALL[b['_rep']])
        if sum(R) >= b['bits']:
            b['_sw'] = R
        else:                               # a wider image (e.g. SW with the 5th SerDes): rep slices + the extra bits spread
            ns, x = len(R), b['bits'] - sum(R)
            b['_sw'] = [R[i] + x // ns + (1 if i < x % ns else 0) for i in range(ns)]
        return b['_sw']
    if not ALIGN or not b.get('nbits'):
        ns = max(1, math.ceil(b['bits'] / SLICE_BITS))
        b['_sw'] = [b['bits'] // ns + (1 if i < b['bits'] % ns else 0) for i in range(ns)]
        return b['_sw']
    W, rest = [], 0
    order = canon_nets(b)

    def flush():
        nonlocal rest
        if rest:
            ns = max(1, math.ceil(rest / SLICE_BITS))
            W.extend(rest // ns + (1 if i < rest % ns else 0) for i in range(ns))
        rest = 0
    for (si, sb), nb in order:
        e = word_elem(f'{si}.{sb}', nb)
        if not e and nb < SLICE_BITS // 2:
            rest += nb                      # small fields share slices
            continue
        if not e:                           # a wide bus (one word): its own slices, never shared with another bus
            flush()
            k = math.ceil(nb / WORD_SLICE)
            W.extend(nb // k + (1 if i < nb % k else 0) for i in range(k))
            continue
        flush()
        n = nb // e
        if e > WORD_SLICE * 3 // 2:
            k = math.ceil(e / WORD_SLICE)
            for _ in range(n):
                W.extend(e // k + (1 if i < e % k else 0) for i in range(k))
        else:
            m = max(1, min(n, SLICE_BITS // e)) if e <= SLICE_BITS else 1
            while n % m:
                m -= 1
            W.extend([m * e] * (n // m))
    flush()
    W = [w for w in W if w > 0] or [b['bits']]
    x = b['bits'] - sum(W)                  # orbit width equalisation widened the bundle past its own nets: spread it
    if x > 0:
        ns = len(W)
        W = [W[i] + x // ns + (1 if i < x % ns else 0) for i in range(ns)]
    b['_sw'] = W
    return W


def canon_nets(b):
    """Nets of a bundle in a quadrant-independent order (mirror images of an orbit slice identically)."""
    pairs = list(zip(b['nets'], b.get('nbits') or [0] * len(b['nets'])))
    if not ALIGN:
        return pairs
    return sorted(pairs, key=lambda t: (re.sub(r'(NW|NE|SW|SE)', 'Q', f'{t[0][0]}.{t[0][1]}'), t[1]))


def swidth(b, sl, ns):
    W = slice_plan(b)
    if len(W) == ns:
        return W[sl]
    return b['bits'] // ns + (1 if sl < b['bits'] % ns else 0)


def slice_nets(b, sl, ns):
    rep = B_ALL.get(b.get('_rep')) if b.get('_rep') is not None else None
    if rep is not None and rep is not b:
        return slice_nets(rep, sl, ns)      # P5: words of the orbit representative (identical pads on every image)
    return _slice_nets(b, sl, ns)


def _slice_nets(b, sl, ns):
    """P5: source buses (src inst.bus) carried by slice sl of bundle b.  The bundle is the concatenation of its
    nets in b['nets'] order (b['nbits'] bits each); slice s carries bits [s*q + min(s, r), +q + (s < r))."""
    W = slice_plan(b)
    if len(W) == ns:
        lo = sum(W[:sl]); hi = lo + W[sl]
    else:
        q, r = divmod(b['bits'], ns)
        lo = sl * q + min(sl, r); hi = lo + q + (1 if sl < r else 0)
    out, at = set(), 0
    for (si, sb), nb in canon_nets(b):
        if at < hi and at + nb > lo:
            nm = f'{si}.{sb}'
            e = word_elem(nm, nb)
            if e:                                   # array of words: the slice carries elements k0..k1 of the bus
                for k in range((max(lo, at) - at) // e, (min(hi, at + nb) - 1 - at) // e + 1):
                    out.add(f'{nm}#{k}')
            else:
                out.add(nm)
        at += nb
    return frozenset(out)


def finalize(P, ports, lanes, lane_meta, pslot, lat, lane_words=None):
    """Stations and latency from the exact port windows (PLAN-TOOL formula: cycles = 2 boundary flops + stations +
    fixed; station k of n sits at L*k/n from the entry pin, so n = ceil(L / reach) keeps every hop <= reach)."""
    PT = {p['id']: p for p in ports}

    def pt(pid):
        p = PT[pid]; r = P[p['src']['part']]['r']; m = (p['window_um'][0] + p['window_um'][1]) / 2
        return {'E': (r[2], m), 'W': (r[0], m), 'N': (m, r[3]), 'S': (m, r[1])}[p['face']]

    node_cyc = {}
    lat.clear()
    for ln in lanes:
        tk, u, kind = lane_meta[ln['id']]
        if kind != 'root' and (tk, u) not in node_cyc:
            print('DEBUG', ln, tk, u, kind, [(PT[c]['src']['part'], PT[c]['dst']['part']) for c in ln['ports']]); raise SystemExit
        fixed = 0 if kind == 'root' else node_cyc[(tk, u)]
        ln['fixed_cycles'] = fixed
        ch = ln['ports']; st = 0
        for i in range(1, len(ch)):
            part = PT[ch[i - 1]]['dst']['part']; slot = PT[ch[i - 1]]['dst']['bus'][:-2]
            L = md(pt(ch[i - 1]), pt(ch[i]))
            n = max(1, math.ceil(L / (REACH * 0.99)))
            pslot[part][slot]['stations'] = n
            st += n
            node_cyc[(tk, part)] = fixed + 1 + st
        cyc = 2 + st + fixed
        node_cyc[(tk, PT[ch[-1]]['dst']['part'])] = cyc
        lat[ln['id']] = dict(cycles=cyc, stations=st, faces=len(ch), fixed=fixed)
    # P3 equal-depth landed groups (STEWARD-TOKg 10-23 10:10 defect class): all slices of one lane orbit member
    # (oi, gb) that end in the same partition land in the same cycle.  Shorter slices get land_pad delay registers
    # in the destination partition (flattened glue at the landing, after any fork point); fixed_cycles carries it
    # so the PLAN-TOOL formula (2 flops + stations + fixed) still holds.
    grp = collections.defaultdict(list)
    for ln in lanes:
        (oi, sl, gb), u, kind = lane_meta[ln['id']]
        grp[(oi, gb, PT[ln['ports'][-1]]['dst']['part'])].append(ln)
    # P5 (COORD HBM PRICE RULING 10-23 14:44 (2)): pads only where a bus is consumed as ONE WORD.  The landed group
    # is split into words: slices that carry a common source bus (one bus split over several 128-b slices) are one
    # word and land together (padded to the word's deepest slice); slices that share no bus are independent fields
    # that land when they are ready and the static compiler schedules each field at its own plan latency.
    # OT_HBM_PAD=group restores the P3/P4 rule (whole group equal depth).
    words = []
    for k, lns in grp.items():
        if PAD_MODE != 'word' or not lane_words:
            words.append((lns, 'equal-depth landed group with its sibling slices'))
            continue
        par = {l['id']: l['id'] for l in lns}

        def fnd(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        first = {}
        for l in lns:
            for nm in lane_words.get(l['id'], ()):
                if nm in first:
                    par[fnd(l['id'])] = fnd(first[nm])
                else:
                    first[nm] = l['id']
        comp = collections.defaultdict(list)
        for l in lns:
            comp[fnd(l['id'])].append(l)
        for c in comp.values():
            words.append((c, 'one-word landing: slices of one source bus land together'))
    for lns, why in words:
        top = max(lat[l['id']]['cycles'] for l in lns)
        for l in lns:
            pad = top - lat[l['id']]['cycles']
            if pad:
                l['fixed_cycles'] += pad
                e = lat[l['id']]; e['cycles'] += pad; e['fixed'] += pad
                l['note'] = f'land_pad {pad}: {why} (fixed includes it)'


def types_and_plan(parts, insts, where, em):
    P = {p['name']: p for p in parts}
    contents = collections.defaultdict(list)
    for n, pn in where.items():
        contents[pn].append(n)
    pins = collections.defaultdict(list)          # type-frame pin table per instance
    for pt in em['ports']:
        for end in ('src', 'dst'):
            pn = pt[end]['part']
            p = P[pn]; r = p['r']
            f = pt['face'] if end == 'src' else OPPF[pt['face']]
            lo, hi = pt['window_um']
            if f in 'EW':
                lo, hi = lo - r[1], hi - r[1]
                fl = p['op'] in ('MX', 'R')
                if fl:
                    lo, hi = (r[3] - r[1]) - hi, (r[3] - r[1]) - lo
            else:
                lo, hi = lo - r[0], hi - r[0]
                fl = p['op'] in ('MY', 'R')
                if fl:
                    lo, hi = (r[2] - r[0]) - hi, (r[2] - r[0]) - lo
            o = pt.get('order', 'lsb_low')
            if fl:
                o = 'lsb_high' if o == 'lsb_low' else 'lsb_low'
            pins[pn].append((pt[end]['bus'], mface(p['op'], f), round(lo, 2), round(hi, 2), o))
    sig, tdef = {}, {}
    groups = collections.defaultdict(list)
    for p in parts:
        n = p['name']
        r = p['r']; w_, h_ = r[2] - r[0], r[3] - r[1]
        cont = []
        for i in sorted(contents[n]):
            if i in SPLIT_OF:
                continue                       # split SM: every quarter gets the 'smq' content below
            I = insts[i]
            lx, ly = I['x'] - r[0], I['y'] - r[1]
            if p['op'] in ('MY', 'R'):
                lx = w_ - lx - I['w']
            if p['op'] in ('MX', 'R'):
                ly = h_ - ly - I['h']
            st, note = status(I['fam'])
            mod_ = I['fam']
            if mod_ in STEPC_MASTER:                   # P4: Step C quadrant-parameterised replacement master
                mod_, st, note = STEPC_MASTER[mod_]
            cont.append(dict(inst=i, module=mod_, status=st, origin_um=[round(lx, 3), round(ly, 3)],
                             outline_um=[I['w'], I['h']], note=note))
        # type-local content names (identical across mirrored instances): u<k> by module + type-frame origin
        cont.sort(key=lambda c: (c['module'], c['origin_um'][0], c['origin_um'][1]))
        lname = {}
        for k_, c in enumerate(cont):
            lname[c['inst']] = f'u{k_}'
            c['note'] = f'{c["inst"]}: ' + c['note']
            c['inst'] = f'u{k_}'
        syn = set()
        if p['kind'] == 'anchor' and p['base'].startswith('sm'):
            syn.add(('smq', 'ot_hbm_accel_smh_attn'))
        buses = []
        for b_ in sorted(em['pbus'][n].values(), key=lambda b: b['name']):
            b2 = dict(b_)
            lf = b_['leaf']
            if lf[0] == 'I' and lf[1] in lname:
                b2['leaf'] = f'{lname[lf[1]]}.{lf[2]}'
            elif lf[0] == 'I' and lf[1] in SPLIT_OF:
                syn.add(('smq', 'ot_hbm_accel_smh_attn')); b2['leaf'] = f'smq.{lf[2]}'
            else:
                nm_ = lf[1] if lf[0] == 'S' else f'rl_{b_["name"]}'
                syn.add((nm_, 'hbm_ft_fork_reg')); b2['leaf'] = f'{nm_}.{lf[2]}'
            buses.append(b2)
        for nm_, mod in sorted(syn):
            cont.append(dict(inst=nm_, module=mod, status='new' if mod == 'hbm_ft_fork_reg' else 'rework',
                             note='generated broadcast fork / re-launch register' if mod == 'hbm_ft_fork_reg'
                             else 'SM quarter: the SM parent is re-derived and split into 4 stacked partitions (L1)'))
        slots = sorted(em['pslot'][n].values(), key=lambda b: b['name'])
        key = (p['cls'], round(w_, 2), round(h_, 2),
               tuple((b['name'], b['dir'], b['width']) for b in buses),
               tuple((s_['name'], s_['in_face'], s_['out_face'], s_['width'], s_['stations']) for s_ in slots),
               tuple(sorted(c['module'] for c in cont)), tuple(sorted(pins[n])))
        groups[key].append(n)
        tdef[key] = dict(w=w_, h=h_, buses=buses, slots=slots, cont=cont, kind=p['kind'])
    types = {}
    tname = {}
    cnt = collections.Counter()
    for key, members in sorted(groups.items(), key=lambda kv: kv[0][0]):
        base = key[0]
        nm = base if cnt[base] == 0 else f'{base}_v{cnt[base]}'
        cnt[base] += 1
        d = tdef[key]
        t = dict(module=f'hbm_part_{nm}', outline_um=[round(d['w'], 3), round(d['h'], 3)],
                 hard=d['kind'] == 'phy',
                 buses=[{k: v for k, v in b.items()} for b in d['buses']],
                 ft_slots=d['slots'],
                 clock=dict(tap_um=[round(d['w'] / 2, 3), round(d['h'] / 2, 3)], layer='M9',
                            insertion_ps=250.0, insertion_tol_ps=40.0),
                 reset=dict(tap_um=[round(d['w'] / 2, 3), round(d['h'] / 2, 3)], sync_stages=2),
                 contents=d['cont'],
                 note=f'{len(members)} instance(s): {", ".join(members[:8])}{"..." if len(members) > 8 else ""}')
        if d['kind'] == 'phy':
            t['note'] += '; hard IP (HBM3E PHY), no wrapper'
        if d['kind'] == 'fabric':
            t['ft_track_frac'] = 0.6      # fabric partitions hold only stations + small glue: M4-M7 mostly for ft
        types[nm] = t
        for m in members:
            tname[m] = nm
    plist = [dict(name=p['name'], type=tname[p['name']], origin_um=[round(p['r'][0], 3), round(p['r'][1], 3)],
                  orient=ORIENT[p['op']]) for p in parts]
    return types, plist, groups


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument('--geom-only', action='store_true')
    a = ap.parse_args()
    insts, cen = load()
    notes = canonicalise(insts)
    parts = build_partitions(insts)
    place_singletons(insts, parts)
    where, lost = assign(insts, parts)
    print('partitions', len(parts), 'lost', len(lost), lost[:30])
    render(parts, insts, where, os.path.join(a.out, 'plan_v1_geom.png'), title='HBM d4g die plan v1 (geometry)')
    if a.geom_only:
        sys.exit(0)
    segs, adj = build_graph(parts)
    P = {p['name']: p for p in parts}
    for n, i in insts.items():
        if i['fam'] == 'ot_hbm_accel_smh_attn':
            r = (i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h'])
            SPLIT_OF[n] = [p['name'] for p in parts if p['kind'] == 'anchor' and p['base'].startswith('sm') and ov(p['r'], r)]
    B = bundles(cen, where, P)
    orb = orbits(B, P)
    print('segments', len(segs), 'bundles', len(B), 'orbits', len(orb),
          'asym orbits', sum(1 for o in orb if len(o) == 1))
    import pickle
    paths, load = route_all(parts, segs, adj, B, orb)
    pickle.dump(dict(parts=parts, segs=segs, B=B, orb=orb, paths=paths, load=load, where=where,
                     insts=insts), open(os.path.join(a.out, 'route.pkl'), 'wb'))
    em = emit(parts, segs, B, orb, paths, insts, where, cen, a.out)
    types, plist, groups = types_and_plan(parts, insts, where, em)
    print('ports', len(em['ports']), 'lanes', len(em['lanes']), 'types', len(types), 'warn', dict(em['warn']),
          'hop_max', round(em['hop_max']))
    pickle.dump(dict(em=em, types=types, plist=plist), open(os.path.join(a.out, 'emit.pkl'), 'wb'))
    # ---- die_plan.json (PLAN-TOOL schema opentallas.die_plan.v1)
    LAYERS = [dict(name='M2', dir='H', pitch_um=0.036, offset_um=0.045), dict(name='M3', dir='V', pitch_um=0.036, offset_um=0.009),
              dict(name='M4', dir='H', pitch_um=0.048, offset_um=0.012), dict(name='M5', dir='V', pitch_um=0.048, offset_um=0.012),
              dict(name='M6', dir='H', pitch_um=0.064, offset_um=0.016), dict(name='M7', dir='V', pitch_um=0.064, offset_um=0.016),
              dict(name='M8', dir='H', pitch_um=0.080, offset_um=0.116), dict(name='M9', dir='V', pitch_um=0.080, offset_um=0.116)]
    plan = {
        'schema': 'opentallas.die_plan.v1',
        'note': ('HBM d4g die plan v1 (PLAN-HBM 2026-10-23). Generated by gen_plan_v1.py from the r18h5 FT-TOOL census + '
                 'ODB dump. Quadrants NW/NE/SW/SE mirrored (MY/MX/R180) and aligned with the HBM channels (owner plan b); '
                 'broadcasts routed as trees (fork/relaunch out buses carry fixed_cycles = upstream cycles). '
                 'Bundle membership (leaf ports per lane) in lane_members.json.gz.'),
        'die': dict(name='hbm_d4g', label='HBM d4g die plan v1 (r18h5 connectivity)', tech='asap7',
                    outline_um=[round(W, 3), round(H, 3)], period_ps=833, reach_um=REACH, rep_um=450.0, grid_um=G,
                    layer_budget=dict(partition_signal_max='M7', die_layers=['M8', 'M9'],
                                      die_use=['clock_spine', 'pg', 'ft_reserved'], cut_avail={'M8': 0.6, 'M9': 0.6}),
                    pg=dict(partition_pg_max='M7', grid=[
                        dict(layer='M8', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS']),
                        dict(layer='M9', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS'])])),
        'partition_types': types,
        'partitions': plist,
        'ports': em['ports'],
        'lanes': em['lanes'],
        'clock': dict(insertion_ps=250.0, insertion_tol_ps=40.0, neighbour_skew_ps=80.0, face_xing='budgeted',
                      spine=dict(layers=['M8', 'M9'], root_um=[round(CX, 3), round(CY, 3)], topology='htree')),
        'reset': dict(sync_stages=2, data_reset=False, epoch_bit=True, release='counted'),
        'latency': dict(lanes=em['lat']),
        'budgets': dict(face_pins_per_um=6.0, face_pin_layers=2, face_window_um=10.0, pin_track_max=0.6,
                        cut_ratio_max=0.6, cut_step_um=250.0, pin_reg_p90_um=30.0),
    }
    json.dump(plan, open(os.path.join(a.out, 'die_plan.json'), 'w'), indent=None, separators=(',', ':'))
    mem = {}
    for oi, m in enumerate(orb):
        for gb, k in m.items():
            b = B[k]
            mem[f'L{oi}{"abcd"[gb]}'] = dict(src=b['src'], dsts=b['dsts'], kind=b['kind'], bits=b['bits'],
                                            nets=[f'{x}.{y}' for x, y in b['nets']])
    json.dump(mem, gzip.open(os.path.join(a.out, 'lane_members.json.gz'), 'wt'))
    print('wrote die_plan.json', os.path.getsize(os.path.join(a.out, 'die_plan.json')) // 1024, 'KB')

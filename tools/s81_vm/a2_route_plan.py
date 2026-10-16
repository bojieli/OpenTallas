#!/usr/bin/env python3
"""S81 VM A2: pin-accurate internal route plan (leaf placement + orientation + local buses + channels) and PG plan.

Successor of a2_floorplan.py (whose screen put every pin at a leaf centre: worst internal cut 2.17).  Here every
bitnet endpoint is the actual pin of the actual port on its actual face:
  * ref-tile leaves: spec.json "pins" face -> ports (ports packed along the face in list order, bits spread evenly);
  * W0 payload / header: the committed per-pin xy (physical/s81_vm_write_edge_1015/*.json);
  * A2 quarter leaves (controller / data16 / meta26 / fault join): the A2 pin-plan templates
    (results/arch/s81_vm_area_1417/a2_pin_plan.json, first-bit centre + 0.096 um step);
  * landing: the five CLOSED 1417 hardleaves (lane i_d N / o_d S, fault join), monolith bits mapped lane = bit/512.
Leaves may be mirrored (MX swaps N/S, MY swaps E/W; no rotation).  Parent ports sit on their S-DIE face (W SU, E
capture, N MIX4, S rest), spread along that face's span next to the bits' consumers.

Cut metric (tools/s81/global_fp/score.py family): each net is a Prim tree over its pins, every edge an L-route
(horizontal first); demand is counted on the edges of a G-um gcell grid (default 100 um), capacity CAP_PER_UM *
G bits per gcell edge (21.09 bits/um over-tile, M6+ routing above <= M5 leaves), share = demand / capacity, limit
0.60.  Clock / reset nets excluded (die clock tree delivery, phi - R).

PG plan: leaves carry M5 PG stripes as pins (ref-tile layer contract); the VM parent straps M6 (horizontal) and M7
(vertical) at a fixed pitch over everything; the strap tracks are removed from the over-tile signal capacity
(cap_after_pg) and every leaf's M5 PG pin columns are checked to be crossed by >= 2 M6 straps.
Screen only: no GRT / IR solve.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AREA = ROOT / 'results/arch/s81_vm_area_1417'
sys.path.insert(0, str(Path(__file__).resolve().parent))
CAP_PER_UM = 5484.375 / 260.0
CLOCKISH = ('ck_', 'rss_', 'rst_', 'A2_')
PORT_FACE = {'f_su': 'W', 't_su': 'W', 'f_capture': 'E', 'f_mx': 'N', 't_mx': 'N'}
CH = 21.6
STRIPE_SPREAD = True


def port_face(p):
    for k, f in PORT_FACE.items():
        if p.startswith(k):
            return f
    return 'S'


# ---------------------------------------------------------------------------------------------------------------- load
def load():
    inv = json.load(open(AREA / 'a2_inventory.json'))['leaves']
    leaves = []
    land = None
    for l in inv:
        if l['master'] == 'dsfd_vm_static_landing':
            land = l
            continue
        leaves.append(dict(name=l['path'], master=l['master'], w=l['outline_um'][0], h=l['outline_um'][1],
                           ports={p: v['bits'] for p, v in l['ports'].items()}, geo=l.get('geometry_source')))
    lanes = []
    for k in range(4):
        lanes.append(len(leaves))
        leaves.append(dict(name=land['path'] + f'.lane{k}', master=f'dsfd_vm_static_landing_lane{k}', w=95.04, h=95.04,
                           ports=dict(i_d=512, o_d=512, i_v=1, o_v=1, o_row=14, larm_v=1, larm_g=4, larm_base=14, fault=1),
                           geo=f'physical/ref_tile/dsfd_vm_static_landing_lane{k}_native_1417/spec.json'))
    join = len(leaves)
    leaves.append(dict(name=land['path'] + '.fault_join', master='dsfd_vm_static_landing_fault_join', w=21.6, h=21.6,
                       ports=dict(i_fault=4, o_fault=1), geo='physical/ref_tile/dsfd_vm_static_landing_fault_join_native_1417/spec.json'))
    old = [i for i, l in enumerate(inv) if l['master'] == 'dsfd_vm_static_landing'][0]
    remap = {}
    j = 0
    for i, l in enumerate(inv):
        if i == old:
            continue
        remap[i] = j
        j += 1

    def land_ep(port, bit):
        if port in ('i_d01', 'i_d23', 'o_d01', 'o_d23'):
            lane = (0 if port.endswith('01') else 2) + bit // 512
            return lanes[lane], port[:3], bit % 512
        if port in ('i_v', 'o_v'):
            return lanes[bit], port, 0
        if port == 'o_row':
            return lanes[bit // 14], 'o_row', bit % 14
        if port == 'fault':
            return join, 'o_fault', 0
        return lanes[0], port, bit
    nets = []
    for line in gzip.open(AREA / 'a2_pin_join.jsonl.gz', 'rt'):
        if not line.strip():
            continue
        r = json.loads(line)
        if r['status'] != 'ONE_DRIVER':
            continue
        ends = r['drivers'] + r['consumers']
        if any(e[0] < 0 and e[1].startswith(CLOCKISH) for e in ends):
            continue
        eps = []
        for e in ends:
            if e[0] < 0:
                eps.append((-1, re.sub(r'\[.*', '', e[1]), e[2]))
            elif e[0] == old:
                eps.append(land_ep(e[1], e[2]))
            else:
                eps.append((remap[e[0]], e[1], e[2]))
        if any(p.startswith(CLOCKISH) or p in ('ck', 'rst_n', 's_ck', 't_ck', 's_rst_n', 't_rst_n', 'ck_control', 'rn')
               for i, p, b in eps if i >= 0):
            continue
        nets.append(eps)
    return leaves, nets


# ----------------------------------------------------------------------------------------------------------- pin model
def pin_models(leaves):
    """master -> {port: [(face, x0, y0, dx, dy)] per bit position function} in R0 leaf coordinates."""
    tpl = json.load(open(AREA / 'a2_pin_plan.json'))['templates']
    tmap = {'s81_a2_stripe_data16': 'data16', 's81_a2_stripe_meta26': 'metadata26', 's81_area_id_fault_join': 'fault'}
    models = {}
    for l in leaves:
        m = l['master']
        if m in models:
            continue
        w, h = l['w'], l['h']
        model = {}
        t = tmap.get(m) or ('controller' if m.startswith('s81_a2_controller') else None)
        if m in ('s81_a2_w0_payload', 's81_a2_w0_header'):
            src = ROOT / ('physical/s81_vm_write_edge_1015/dsfd_vm_static_w0_%s.json' % m.split('_')[-1])
            pins = json.load(open(src))['pins']
            per = collections.defaultdict(dict)
            for p in pins:
                mm = re.match(r'(\w+)\[(\d+)\]', p['name'])
                port, bit = (mm.group(1), int(mm.group(2))) if mm else (p['name'], 0)
                per[port][bit] = (p['face'], p['xy_um'][0], p['xy_um'][1])
            for port, d in per.items():
                model[port] = ('table', d)
        elif t:
            for p in tpl[t]['ports']:
                c0, st = p['first_bit_center_um'], p['bit_step_um']
                if STRIPE_SPREAD and t in ('data16', 'metadata26') and p['port'] in ('i_data', 'o_data') and st[1] == 0:
                    # re-planned stripe pin plan: the wide input/output buses span the whole N / E face
                    step = (w if p['face'] in 'NS' else h) / p['bits']
                    c0 = [step / 2, c0[1]] if p['face'] in 'NS' else [c0[0], step / 2]
                    st = [step, 0] if p['face'] in 'NS' else [0, step]
                model[p['port']] = ('line', p['face'], c0, st, p['bits'])
        else:
            spec = json.load(open(ROOT / l['geo']))
            faces = spec['pins']
            for f, plist in faces.items():
                bits = [l['ports'].get(p, 1) for p in plist]
                tot = sum(bits) or 1
                length = w if f in 'NS' else h
                pos = 0.0
                for p, b in zip(plist, bits):
                    span = length * b / tot
                    model[p] = ('span', f, pos, span, b)
                    pos += span
        models[m] = model
    return models


def pin_xy(leaf, model, port, bit, x, y, fx, fy):
    """absolute pin position of (port, bit) of a leaf placed at (x, y) with mirror flags."""
    w, h = leaf['w'], leaf['h']
    mdl = model.get(port)
    fn = leaf.get('pins_fn')
    r = fn(port, bit) if fn else None
    if r is not None:
        px, py = r
    elif mdl is None:
        px, py = w / 2, h / 2
    elif mdl[0] == 'table':
        e = mdl[1].get(bit) or next(iter(mdl[1].values()))
        px, py = e[1], e[2]
    elif mdl[0] == 'line':
        _, f, c0, st, n = mdl
        px, py = c0[0] + st[0] * bit, c0[1] + st[1] * bit
    else:
        _, f, pos, span, n = mdl
        t = pos + span * (bit % max(n, 1) + 0.5) / max(n, 1)
        px, py = {'N': (t, h), 'S': (t, 0.0), 'W': (0.0, t), 'E': (w, t)}[f]
    if fx:
        px = w - px
    if fy:
        py = h - py
    return x + px, y + py


# ------------------------------------------------------------------------------------------------------------- layout
class Plan:
    def __init__(self, leaves):
        self.leaves, self.pos = leaves, {}

    def put(self, i, x, y, fx=False, fy=False):
        assert i not in self.pos, self.leaves[i]['name']
        self.pos[i] = (round(x, 4), round(y, 4), fx, fy)

    def rect(self, i):
        x, y, _, _ = self.pos[i]
        return x, y, self.leaves[i]['w'], self.leaves[i]['h']

    def check(self, W, H, ch=CH):
        bad = outside = 0
        rs = sorted(((i,) + self.rect(i) for i in self.pos), key=lambda r: r[1])
        for a in range(len(rs)):
            i, x, y, w, h = rs[a]
            if x < -1e-6 or y < -1e-6 or x + w > W + 1e-6 or y + h > H + 1e-6:
                outside += 1
            for b in range(a + 1, len(rs)):
                j, x2, y2, w2, h2 = rs[b]
                if x2 >= x + w + ch - 1e-6:
                    break
                if y2 < y + h + ch - 1e-6 and y < y2 + h2 + ch - 1e-6:
                    bad += 1
        return bad, outside


def classify(leaves, nets):
    import a2_floorplan as F
    flat = [(sorted(set(i for i, _, _ in eps if i >= 0)), []) for eps in nets]
    unit, _ = F.classify([dict(name=l['name'], master=l['master']) for l in leaves], flat)
    return unit


def skyline(P, items, x0, x1, y0, ch=CH, flip=False):
    """bottom-left skyline packing of item groups (tuples of leaves, members side by side) in [x0, x1] from y0 up;
    flip=True packs downward from y0 (mirror) and marks the leaves MX.  Returns the far edge."""
    W = x1 - x0
    sky = [(0.0, W + ch, 0.0)]
    placed = []
    for grp in items:
        grp = grp if isinstance(grp, tuple) else (grp,)
        w = sum(P.leaves[i]['w'] for i in grp) + ch * len(grp)
        h = max(P.leaves[i]['h'] for i in grp) + ch
        best = None
        for k, (a0, _, _) in enumerate(sky):
            if a0 + w > W + ch + 1e-6:
                break
            top = max(y for (a, b, y) in sky if b > a0 + 1e-9 and a < a0 + w - 1e-9)
            if best is None or top + h < best[0] - 1e-9:
                best = (top + h, a0, top)
        _, ax, ay = best
        xx = ax
        for i in grp:
            placed.append((i, x0 + xx, ay))
            xx += P.leaves[i]['w'] + ch
        nsky = [s for s in sky if s[1] <= ax or s[0] >= ax + w]
        nsky += [(s[0], ax, s[2]) for s in sky if s[0] < ax < s[1]]
        nsky += [(ax + w, s[1], s[2]) for s in sky if s[0] < ax + w < s[1]]
        nsky.append((ax, ax + w, ay + h))
        sky = sorted(nsky)
    top = max(y for _, _, y in sky) - ch
    for i, x, y in placed:
        if flip:
            P.put(i, x, y0 - y - P.leaves[i]['h'], False, True)
        else:
            P.put(i, x, y0 + y)
    return y0 - top if flip else y0 + top


def build(leaves, nets, W=3369.6, ch=CH, opts=None):
    opts = opts or {}
    P = Plan(leaves)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    unit = classify(leaves, nets)
    QW, QH = 820.8, 324.0
    SH = 4 * 75.6 + 3 * ch
    BW = 2 * QW + ch
    BH = 86.4 + 2 * QH + 2 * SH + 4 * ch
    x0 = (W - (2 * BW + ch)) / 2

    def place_slice(x, by, mirror):
        """payload at the band face (y = by side), quarter rows next, storage rows far.  mirror: block grows down."""
        bx = x0 + (x % 2) * (BW + ch)
        sgn = -1 if mirror else 1

        def Y(off, h):            # block-local offset from the band face -> absolute y of the leaf's low edge
            return by + off if not mirror else by - off - h
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])][0]
        # payload input face (N) toward the band; output face (S) toward the quarters
        P.put(pay, bx + (BW - 1166.4) / 2, Y(0, 86.4), False, not mirror)
        for q in range(4):
            row = q // 2               # quarter row 0 next to the payload, row 1 beyond
            ux = bx + (q % 2) * (QW + ch)
            qoff = 86.4 + ch + row * (QH + ch)
            soff = 86.4 + ch + 2 * (QH + ch) + row * (SH + ch)
            mem = [i for i, u in unit.items() if u == (x, q)]
            by_m = collections.defaultdict(list)
            for i in mem:
                by_m[M[i]].append(i)
            stripes = sorted(by_m['s81_a2_stripe_data16'], key=lambda i: N[i]) + by_m['s81_a2_stripe_meta26']
            ctrl = [i for i in mem if M[i].startswith('s81_a2_controller')][0]
            fj = by_m['s81_area_id_fault_join'][0]
            # quarter: 3 stripe rows (i_data N toward the payload), controller row last (ids N -> stripes' S)
            fyq = not mirror           # stripe N face toward the payload side
            sx0 = ux + (QW - (3 * 237.6 + 2 * ch)) / 2
            for k, i in enumerate(stripes):
                P.put(i, sx0 + (k % 3) * (237.6 + ch), Y(qoff + (k // 3) * (54 + ch), 54), False, fyq)
            P.put(ctrl, ux + (QW - 172.8) / 2, Y(qoff + 3 * (54 + ch), 54), False, fyq)
            P.put(fj, ux + QW - 21.6, Y(qoff + 3 * (54 + ch) + 16.2, 21.6), False, fyq)
            banks = sorted(by_m['dsfd_vm_static_bank128'], key=lambda i: N[i])
            b8, sc = by_m['dsfd_vm_static_relay128_b8'][0], by_m['dsfd_vm_static_scatter_b8_out'][0]
            b4 = sorted(by_m['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
            # storage: scatter/b8 column + b4 column in the middle, bank columns either side facing them
            cx = ux + 220.32 + ch
            P.put(sc, cx, Y(soff, 86.4), False, fyq)
            P.put(b8, cx, Y(soff + 86.4 + ch, 172.8), False, fyq)
            bx4 = cx + 172.8 + ch
            for k, i in enumerate(b4):
                P.put(i, bx4, Y(soff + k * (129.6 + ch), 129.6), False, fyq)
            for k, i in enumerate(banks):
                col = k % 2
                bxk = ux if col == 0 else bx4 + 129.6 + ch
                P.put(i, bxk, Y(soff + (k // 2) * (75.6 + ch), 75.6), col == 0, fyq)
            assert bx4 + 129.6 + ch + 220.32 <= ux + QW + 1e-6
    # bottom block row (normal, grows down from the band's lower face) and top block row (mirror, grows up)
    rest = [i for i in range(len(N)) if not (i in unit or re.search(r'w0_payload', N[i]))]
    groups = composites(N, M, rest)
    groups.sort(key=lambda g: (band_rank(M[g[0]]), -max(leaves[i]['h'] for i in g), N[g[0]]))
    yb = BH                                            # band lower face
    top = skyline(P, groups, 0.0, W, yb + ch, ch)
    for x in (0, 1):
        place_slice(x, yb, True)                       # grows down from yb: payload just under the band
    for x in (2, 3):
        place_slice(x, top + ch, False)                # grows up from the band's upper face
    H = top + ch + BH
    # shift so that y >= 0 (mirror blocks occupy [0, BH])
    return P, W, H, dict(slice_block_um=[BW, BH], band_um=[W, round(top - yb - ch, 3)])


def build_v3(leaves, nets, W=3369.6, ch=CH, opts=None):
    """v3: per-slice blocks carry their own read path.  From the central band outward each slice block holds:
    payload (input face to the band) | quarter row A (q0,q1) | quarter row B (q2,q3) | storage row A | storage row
    B | read strip (its 4 FSR, 4 return lanes, 16 read leaves).  The band holds the capture lanes (E side, MY so the
    chain flows cap -> x34_s -> x34_t toward the payloads), CDC pairs, landing, header, seq, rsched, read_v, cap_ctl."""
    opts = opts or {}
    P = Plan(leaves)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    unit = classify(leaves, nets)
    QW = 820.8
    QH = 4 * 54 + 3 * ch                  # quarter interior actually packed (3 stripe rows + controller row)
    SH = 4 * 75.6 + 3 * ch
    BW = 2 * QW + ch
    x0 = (W - (2 * BW + ch)) / 2
    slice_of = {}
    for i, n in enumerate(N):
        m = re.search(r'u_mem\.slice\[(\d)\]', n)
        if m:
            slice_of[i] = int(m.group(1))
        m = re.search(r'bounded_read\.l14\.u_read\.d(\d+)$', n)
        if m:
            slice_of[i] = (int(m.group(1)) // 2) % 4      # d_k reads slice (k/2) mod 4 (pin join)
    read_like = lambda i: any(k in M[i] for k in ('read_q', 'return', 'fsr'))

    def place_slice(x, by, sgn):
        bx = x0 + (x % 2) * (BW + ch)
        mirror = sgn < 0

        def Y(off, h):
            return by + off if not mirror else by - off - h
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])][0]
        P.put(pay, bx + (BW - 1166.4) / 2, Y(0, 86.4), False, not mirror)
        fyq = not mirror
        for q in range(4):
            row = q // 2
            ux = bx + (q % 2) * (QW + ch)
            left = q % 2 == 0
            qoff = 86.4 + ch + row * (QH + ch)
            soff = 86.4 + ch + 2 * (QH + ch) + row * (SH + ch)
            mem = [i for i, u in unit.items() if u == (x, q)]
            by_m = collections.defaultdict(list)
            for i in mem:
                by_m[M[i]].append(i)
            stripes = sorted(by_m['s81_a2_stripe_data16'], key=lambda i: N[i]) + by_m['s81_a2_stripe_meta26']
            ctrl = [i for i in mem if M[i].startswith('s81_a2_controller')][0]
            fj = by_m['s81_area_id_fault_join'][0]
            sx0 = ux + (QW - (3 * 237.6 + 2 * ch)) / 2
            for k, i in enumerate(stripes):
                P.put(i, sx0 + (k % 3) * (237.6 + ch), Y(qoff + (k // 3) * (54 + ch), 54), False, fyq)
            P.put(ctrl, ux + (QW - 172.8) / 2, Y(qoff + 3 * (54 + ch), 54), False, fyq)
            P.put(fj, sx0 + 3 * (237.6 + ch) - ch - 21.6, Y(qoff + 3 * (54 + ch) + 16.2, 21.6), False, fyq)
            banks = sorted(by_m['dsfd_vm_static_bank128'], key=lambda i: N[i])
            b8, sc = by_m['dsfd_vm_static_relay128_b8'][0], by_m['dsfd_vm_static_scatter_b8_out'][0]
            b4 = sorted(by_m['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
            # relay columns toward the slice block's centre line (left unit mirrored MY)
            if left:
                colx = dict(bankA=ux, rel=ux + 220.32 + ch, b4=ux + 220.32 + ch + 172.8 + ch,
                            bankB=ux + 220.32 + ch + 172.8 + ch + 129.6 + ch)
            else:
                colx = dict(bankB=ux + QW - 220.32, rel=ux + QW - 220.32 - ch - 172.8,
                            b4=ux + QW - 220.32 - ch - 172.8 - ch - 129.6, bankA=ux + QW - 220.32 - ch - 172.8 - ch - 129.6 - ch - 220.32)
            P.put(sc, colx['rel'], Y(soff, 86.4), False, fyq)
            P.put(b8, colx['rel'], Y(soff + SH - 172.8, 172.8), False, fyq)      # b8 toward the read strip
            for k, i in enumerate(b4):
                P.put(i, colx['b4'], Y(soff + k * (129.6 + ch) + (SH - 2 * 129.6 - ch), 129.6), False, fyq)
            for k, i in enumerate(banks):
                col = 'bankA' if k % 2 == 0 else 'bankB'
                P.put(i, colx[col], Y(soff + (k // 2) * (75.6 + ch), 75.6), col == 'bankA', fyq)
        roff = 86.4 + ch + 2 * (QH + ch) + 2 * (SH + ch)
        items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i)]
        groups = [(i,) for i in sorted(items, key=lambda i: (-leaves[i]['h'], N[i]))]
        if mirror:
            far = skyline(P, groups, bx, bx + BW, by - roff, ch, flip=True)
        else:
            far = skyline(P, groups, bx, bx + BW, by + roff, ch)
        return abs(far - by)
    rest = [i for i in range(len(N)) if not (i in unit or re.search(r'w0_payload', N[i]) or
                                             (i in slice_of and read_like(i)))]
    groups = composites(N, M, rest)
    groups.sort(key=lambda g: (0 if 'cap' in M[g[0]] else 1, -max(leaves[i]['h'] for i in g), N[g[0]]))
    # band: pack left-to-right then mirror in x (capture lanes land on the E side, chains flow toward the centre)
    tmp = Plan(leaves)
    top_rel = skyline(tmp, groups, 0.0, W, 0.0, ch)
    band_h = top_rel
    # bottom blocks first, to know the band's lower face
    probe = Plan(leaves)
    Pdepth = None
    yb = None
    # depth of a block is the same for all four (identical contents per slice up to the read strip packing)
    depths = []
    for x in range(4):
        Q = Plan(leaves)
        P0 = P
        P = Q
        depths.append(place_slice(x, 0.0, +1))
        P = P0
    D = max(depths)
    yb = D + ch
    for x in (0, 1):
        place_slice(x, yb - ch, -1)
    for i, (xx, yy, fx, fy) in tmp.pos.items():
        w = leaves[i]['w']
        P.put(i, W - xx - w, yb + yy, not fx, fy)
    yt = yb + band_h + ch
    for x in (2, 3):
        place_slice(x, yt, +1)
    H = yt + D
    return P, W, H, dict(slice_block_um=[BW, D], band_um=[W, round(band_h, 3)], quarter_interior_um=[QW, QH])


def build_v4(leaves, nets, W=3369.6, ch=CH, opts=None):
    """v4: one 820.8-um column per slice (4 columns = 3,348 um), band at the S face.
    Column, bottom-up: payload (re-outlined 820.8 x 129.6, o_data pins re-assigned to sit above their data stripe
    column) | quarters q0..q3 (each 3 x 3 stripes + controller row, stripe k in column k%3) | storage units in
    `order` | read strip (FSR, return lanes, read leaves of that slice).  Payload->stripe buses run straight up the
    three stripe columns; storage b8 relays face the read strip."""
    opts = opts or {}
    order = opts.get('order', ['q0', 'q1', 'q2', 'q3', 'st0', 'st1', 'st2', 'st3', 'read'])
    PW, PH = 820.8, 129.6
    P = Plan(leaves)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    unit = classify(leaves, nets)
    QW = 820.8
    QH = 4 * 54 + 3 * ch
    SH = 4 * 75.6 + 3 * ch
    gap = opts.get('col_gap', ch)
    x0 = (W - (4 * QW + 3 * gap)) / 2
    sx0 = (QW - (3 * 237.6 + 2 * ch)) / 2
    slot = {0: 0, 1: 1, 2: 2, 3: 0, 4: 1, 5: 2, 6: 0, 7: 1, 8: 2}       # stripe k -> column (8 = meta)
    rowk = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2}
    colw = 237.6 + ch

    def pay_pins(port, bit):
        if port == 'o_data':
            k = (bit % 128) // 16
            j = (bit // 128) * 16 + bit % 16           # stripe i_data index 0..847
            # column c carries stripes in rows 0..2; interleave them inside the column span
            c = slot[k]
            kk = [q for q in range(9) if slot[q] == c]
            pos = (kk.index(k) * 848 + j) / (len(kk) * 848 + 1)
            return sx0 + c * colw + pos * 237.6, 0.0
        if port == 'i_data':
            return (bit + 0.5) / 6784 * PW, PH
        if port in ('i_mask',):
            return 0.0, (bit + 0.5) / 212 * PH
        if port in ('o_mask', 'o_epoch'):
            return PW, (bit + 0.5) / 215 * PH
        return None
    slice_of = {}
    for i, n in enumerate(N):
        m = re.search(r'u_mem\.slice\[(\d)\]', n)
        if m:
            slice_of[i] = int(m.group(1))
        m = re.search(r'bounded_read\.l14\.u_read\.d(\d+)$', n)
        if m:
            slice_of[i] = (int(m.group(1)) // 2) % 4
    read_like = lambda i: any(k in M[i] for k in ('read_q', 'return', 'fsr'))
    rest = [i for i in range(len(N)) if not (i in unit or re.search(r'w0_payload', N[i]) or
                                             (i in slice_of and read_like(i)))]
    groups = composites(N, M, rest)
    groups.sort(key=lambda g: (0 if 'cap' in M[g[0]] else 1, -max(leaves[i]['h'] for i in g), N[g[0]]))
    tmp = Plan(leaves)
    band_h = skyline(tmp, groups, 0.0, W, 0.0, ch)
    for i, (xx, yy, fx, fy) in tmp.pos.items():
        P.put(i, W - xx - leaves[i]['w'], yy, not fx, fy)
    y0 = band_h + ch
    tops = []
    for x in range(4):
        cx = x0 + x * (QW + gap)
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])][0]
        leaves[pay]['w'], leaves[pay]['h'] = PW, PH
        leaves[pay]['pins_fn'] = pay_pins
        # payload: inputs (i_data) face the band (S), outputs face the quarters (N)
        leaves[pay]['pins_fn'] = (lambda f: (lambda port, bit: (lambda r: None if r is None else (r[0], PH - r[1]))(f(port, bit))))(pay_pins)
        y = y0
        for item in (order if 'pay' in order else ['pay'] + order):
            if item == 'pay':
                P.put(pay, cx, y)
                y += PH + ch
            elif item.startswith('q'):
                q = int(item[1])
                mem = [i for i, u in unit.items() if u == (x, q)]
                by_m = collections.defaultdict(list)
                for i in mem:
                    by_m[M[i]].append(i)
                data = sorted(by_m['s81_a2_stripe_data16'], key=lambda i: int(re.search(r'u_data(\d+)', N[i]).group(1)))
                stripes = data + by_m['s81_a2_stripe_meta26']
                for k, i in enumerate(stripes):        # stripe i_data (N in R0) faces the payload below: MX
                    P.put(i, cx + sx0 + slot[k] * colw, y + rowk[k] * (54 + ch), False, True)
                ctrl = [i for i in mem if M[i].startswith('s81_a2_controller')][0]
                fj = by_m['s81_area_id_fault_join'][0]
                P.put(ctrl, cx + (QW - 172.8) / 2, y + 3 * (54 + ch), False, True)
                P.put(fj, cx + sx0 + 3 * colw - ch - 21.6, y + 3 * (54 + ch) + 16.2, False, True)
                y += QH + ch
            elif item.startswith('st'):
                q = int(item[2])
                mem = [i for i, u in unit.items() if u == (x, q)]
                by_m = collections.defaultdict(list)
                for i in mem:
                    by_m[M[i]].append(i)
                banks = sorted(by_m['dsfd_vm_static_bank128'], key=lambda i: N[i])
                b8, sc = by_m['dsfd_vm_static_relay128_b8'][0], by_m['dsfd_vm_static_scatter_b8_out'][0]
                b4 = sorted(by_m['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
                bA = cx
                rel = cx + 220.32 + ch
                c4 = rel + 172.8 + ch
                bB = c4 + 129.6 + ch
                P.put(sc, rel, y, False, False)
                P.put(b8, rel, y + SH - 172.8, False, False)
                for k, i in enumerate(b4):
                    P.put(i, c4, y + k * (129.6 + ch) + (SH - 2 * 129.6 - ch), False, False)
                for k, i in enumerate(banks):
                    col = bA if k % 2 == 0 else bB
                    P.put(i, col, y + (k // 2) * (75.6 + ch), k % 2 == 0, False)
                y += SH + ch
            elif item == 'read':
                items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i)]
                grp = [(i,) for i in sorted(items, key=lambda i: (-leaves[i]['h'], N[i]))]
                y = skyline(P, grp, cx, cx + QW, y, ch) + ch
        tops.append(y - ch)
    H = max(tops)
    flip = set(opts.get('flip_cols', ()))
    if flip:      # staggered columns: these grow down from the top face (payload at the top, read strip at the band)
        for x in flip:
            cx = x0 + x * (QW + gap)
            for i, (xx, yy, fx, fy) in list(P.pos.items()):
                if yy >= y0 - 1e-6 and cx - 1e-6 <= xx <= cx + QW + 1e-6:
                    h = leaves[i]['h']
                    P.pos[i] = (xx, round(y0 + (H - (yy + h)), 4), fx, not fy)
    return P, W, H, dict(column_um=[QW, round(H - y0, 3)], band_um=[W, round(band_h, 3)], payload_um=[PW, PH],
                         order=order)


def build_v5(leaves, nets, W=3369.6, ch=CH, opts=None):
    """v5 'slice rows': each slice x is a full-width row (broadcast runs horizontally, where the cut capacity is the
    row height, not the 3,369.6-um width): payload row | quarter row q0..q3 | storage row (unit q under quarter q,
    b8 toward the read strip) | read strip (its FSR, return lanes, read leaves).  Two slice rows below the central
    band (mirrored), two above; band = capture lanes (E), CDC pairs, landing, header, seq, rsched, read_v."""
    opts = opts or {}
    P = Plan(leaves)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    unit = classify(leaves, nets)
    QW = 820.8
    QH = 4 * 54 + 3 * ch
    SH = 4 * 75.6 + 3 * ch
    x0 = (W - (4 * QW + 3 * ch)) / 2
    sxo = (QW - (3 * 237.6 + 2 * ch)) / 2
    colw = 237.6 + ch
    slice_of = {}
    for i, n in enumerate(N):
        m = re.search(r'u_mem\.slice\[(\d)\]', n)
        if m:
            slice_of[i] = int(m.group(1))
        m = re.search(r'bounded_read\.l14\.u_read\.d(\d+)$', n)
        if m:
            slice_of[i] = (int(m.group(1)) // 2) % 4
    read_like = lambda i: any(k in M[i] for k in ('read_q', 'return', 'fsr'))

    def slice_row(x, base, sgn):
        mirror = sgn < 0

        def Y(off, h):
            return base + off if not mirror else base - off - h
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])][0]
        P.put(pay, (W - 1166.4) / 2, Y(0, 86.4), False, not mirror)      # input face toward the band
        qoff = 86.4 + ch
        soff = qoff + QH + ch
        roff = soff + SH + ch
        for q in range(4):
            cx = x0 + q * (QW + ch)
            mem = [i for i, u in unit.items() if u == (x, q)]
            by_m = collections.defaultdict(list)
            for i in mem:
                by_m[M[i]].append(i)
            data = sorted(by_m['s81_a2_stripe_data16'], key=lambda i: int(re.search(r'u_data(\d+)', N[i]).group(1)))
            stripes = data + by_m['s81_a2_stripe_meta26']
            fyq = not mirror                           # stripe i_data (R0 N) faces the payload row
            for k, i in enumerate(stripes):
                P.put(i, cx + sxo + (k % 3) * colw, Y(qoff + (k // 3) * (54 + ch), 54), False, fyq)
            ctrl = [i for i in mem if M[i].startswith('s81_a2_controller')][0]
            fj = by_m['s81_area_id_fault_join'][0]
            P.put(ctrl, cx + (QW - 172.8) / 2, Y(qoff + 3 * (54 + ch), 54), False, fyq)
            P.put(fj, cx + sxo + 3 * colw - ch - 21.6, Y(qoff + 3 * (54 + ch) + 16.2, 21.6), False, fyq)
            banks = sorted(by_m['dsfd_vm_static_bank128'], key=lambda i: N[i])
            b8, sc = by_m['dsfd_vm_static_relay128_b8'][0], by_m['dsfd_vm_static_scatter_b8_out'][0]
            b4 = sorted(by_m['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
            rel = cx + 220.32 + ch
            c4 = rel + 172.8 + ch
            fys = mirror                               # scatter N (inputs) toward the quarter
            P.put(sc, rel, Y(soff, 86.4), False, fys)
            P.put(b8, rel, Y(soff + SH - 172.8, 172.8), False, fys)
            for k, i in enumerate(b4):
                P.put(i, c4, Y(soff + k * (129.6 + ch) + (SH - 2 * 129.6 - ch), 129.6), False, fys)
            for k, i in enumerate(banks):
                col = cx if k % 2 == 0 else c4 + 129.6 + ch
                P.put(i, col, Y(soff + (k // 2) * (75.6 + ch), 75.6), k % 2 == 0, fys)
        items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i)]
        grp = [(i,) for i in sorted(items, key=lambda i: (-leaves[i]['h'], N[i]))]
        far = skyline(P, grp, 0.0, W, Y(roff, 0) if not mirror else base - roff, ch, flip=mirror)
        return abs(far - base)
    rest = [i for i in range(len(N)) if not (i in unit or re.search(r'w0_payload', N[i]) or
                                             (i in slice_of and read_like(i)))]
    groups = composites(N, M, rest)
    groups.sort(key=lambda g: (0 if 'cap' in M[g[0]] else 1, -max(leaves[i]['h'] for i in g), N[g[0]]))
    tmp = Plan(leaves)
    band_h = skyline(tmp, groups, 0.0, W, 0.0, ch)
    # depth of a slice row (identical for all four)
    probe = Plan(leaves)
    saved = P
    P = probe
    D = slice_row(0, 0.0, +1)
    P = saved
    yb = 2 * (D + ch)                                 # two mirrored slice rows below the band
    slice_row(1, yb - ch, -1)
    slice_row(0, yb - ch - D - ch, -1)
    for i, (xx, yy, fx, fy) in tmp.pos.items():
        P.put(i, W - xx - leaves[i]['w'], yb + yy, not fx, fy)
    yt = yb + band_h + ch
    slice_row(2, yt, +1)
    slice_row(3, yt + D + ch, +1)
    H = yt + 2 * D + ch
    return P, W, H, dict(slice_row_um=[W, round(D, 3)], band_um=[W, round(band_h, 3)])


def band_rank(m):
    if 'read_' in m or 'return' in m or 'fsr' in m or 'rsched' in m:
        return 1
    return 0


def composites(N, M, rest):
    by = {N[i]: i for i in rest}
    used, out = set(), []
    for n, i in by.items():
        mm = re.match(r'(dut\.u_cap\.lane\[\d+\])\.u_l$', n)
        if mm:
            g = tuple(by[k] for k in (n, mm.group(1) + '.u_x.u_s', mm.group(1) + '.u_x.u_t') if k in by)
            out.append(g)
            used.update(g)
    for pre, order in (('dut.u_xsel', ('u_s', 'u_t')), ('dut.u_xcol', ('u_s', 'u_t')), ('dut.u_wfc.u_xi', ('u_s', 'u_t')),
                       ('dut.u_wfc.u_xo', ('u_t', 'u_s')), ('dut.u_xio.u_xq', ('u_t', 'u_s')), ('dut.u_xio.u_xg', ('u_t', 'u_s'))):
        g = tuple(by[pre + '.' + o] for o in order if pre + '.' + o in by and by[pre + '.' + o] not in used)
        if g:
            out.append(g)
            used.update(g)
    lan = tuple(i for n, i in sorted(by.items()) if re.search(r'u_land\.(lane\d|fault_join)$', n))
    if lan:
        out.append(lan)
        used.update(lan)
    out += [(i,) for i in rest if i not in used]
    return out


# ------------------------------------------------------------------------------------------------------------ evaluate
def evaluate(P, nets, W, H, G=100.0, models=None, pg=None, hot=12):
    L = P.leaves
    models = models or pin_models(L)
    nx, ny = int(math.ceil(W / G)), int(math.ceil(H / G))
    hd = collections.Counter()      # crossings of vertical gcell boundary gx at row gy (horizontal wires)
    vd = collections.Counter()
    who = collections.defaultdict(collections.Counter)
    face_bits = collections.Counter()
    port_users = collections.defaultdict(list)
    total = 0.0
    over = collections.Counter()

    def pin(e):
        i, p, b = e
        x, y, fx, fy = P.pos[i]
        return pin_xy(L[i], models[L[i]['master']], p, b, x, y, fx, fy)
    for eps in nets:
        pts = []
        tags = []
        for e in eps:
            if e[0] >= 0:
                pts.append(pin(e))
                tags.append(L[e[0]]['master'])
        if not pts:
            continue
        for e in eps:
            if e[0] < 0:
                f = port_face(e[1])
                face_bits[f] += 1
                c = pts[0]
                pts.append({'W': (0.0, c[1]), 'E': (W, c[1]), 'N': (c[0], H), 'S': (c[0], 0.0)}[f])
                tags.append('PORT_' + f)
        done = [0]
        todo = list(range(1, len(pts)))
        while todo:
            best = None
            for k in todo:
                for d in done:
                    dd = abs(pts[k][0] - pts[d][0]) + abs(pts[k][1] - pts[d][1])
                    if best is None or dd < best[0]:
                        best = (dd, k, d)
            dd, k, d = best
            todo.remove(k)
            done.append(k)
            (x1, y1), (x2, y2) = pts[d], pts[k]
            total += dd
            if not tags[k].startswith('PORT') and not tags[d].startswith('PORT') and dd > 500:
                over[(tags[d], tags[k])] += 1
            key = (tags[d][:24], tags[k][:24])
            gy = min(max(int(y1 // G), 0), ny - 1)
            for gx in range(int(min(x1, x2) // G) + 1, int(max(x1, x2) // G) + 1):
                hd[(gx, gy)] += 1
                who[('h', gx, gy)][key] += 1
            gx = min(max(int(x2 // G), 0), nx - 1)
            for g2 in range(int(min(y1, y2) // G) + 1, int(max(y1, y2) // G) + 1):
                vd[(gx, g2)] += 1
                who[('v', gx, g2)][key] += 1
    cap = CAP_PER_UM * G * (pg['signal_fraction'] if pg else 1.0)
    shares = {('h',) + k: v / cap for k, v in hd.items()}
    shares.update({('v',) + k: v / cap for k, v in vd.items()})
    worst = max(shares.values())
    n_over = sum(s > 0.60 for s in shares.values())
    top = sorted(shares.items(), key=lambda kv: -kv[1])[:hot]
    hot_list = [dict(edge=k[0], x_um=k[1] * G, y_um=k[2] * G, share=round(s, 3),
                     top_pairs=[[a, b, n] for (a, b), n in who[k].most_common(3)]) for k, s in top]
    return dict(gcell_um=G, cap_bits_per_gcell_edge=round(cap, 1), worst_share=round(worst, 3),
                edges_over_060=n_over, edges=len(shares), sum_bit_um=round(total),
                leaf_links_over_500um=sum(over.values()),
                over_reach_pairs=[[a, b, n] for (a, b), n in over.most_common(10)],
                face_pin_bits={f: face_bits[f] for f in 'NSEW'}, hotspots=hot_list)


def pg_plan(P, W, H, pitch6=21.6, pitch7=43.2, width=0.864, track=0.08):
    """VM parent PG plan (ref-tile layer contract: leaves carry full-length M5 PG stripes as pins; the parent straps
    M6 horizontally and M7 vertically over the whole body, M8 by the die).  Strap pitch 21.6 / 43.2 um on the
    placement lattice so every leaf >= 43.2 um tall is crossed by >= 2 M6 straps whatever its y; the straps' track
    share comes off the over-tile signal capacity used by the cut screen.  IR not solved."""
    f6 = (width + track) / pitch6
    f7 = (width + track) / pitch7
    signal_fraction = 1.0 - (f6 + f7) / 2
    short = collections.Counter()
    n6 = []
    for i in P.pos:
        x, y, w, h = P.rect(i)
        k = math.floor((y + h) / pitch6) - math.ceil(y / pitch6) + 1
        k7 = math.floor((x + w) / pitch7) - math.ceil(x / pitch7) + 1
        n6.append(k)
        if k < 2 or k7 < 1:
            short[P.leaves[i]['master']] += 1
    return dict(m6_pitch_um=pitch6, m7_pitch_um=pitch7, strap_width_um=width, m6_track_share=round(f6, 4),
                m7_track_share=round(f7, 4), signal_fraction=round(signal_fraction, 4),
                min_m6_straps_per_leaf=min(n6), leaves_with_fewer_than_2_m6_or_0_m7=sum(short.values()),
                by_master=dict(short),
                note='leaves under 2 M6 crossings take their PG from an aligned M6 strap at their row (21.6-um '
                     'leaves: fault joins, cap_ctl); IR/EM not solved -- the die PDN run owns that')

def connections(P, nets, W, H, models=None, port_density=8.0):
    """Prim-tree two-pin connections of every bitnet at the actual pins -> list of ((x1,y1),(x2,y2),tagA,tagB).
    Parent ports: top-down VM pin assignment per port group and face -- the group's bits are spread evenly over a
    face span centred on the median projection of the leaf pins they connect, at most port_density bits/um
    (one M4/M5 pin layer is 10.4 bits/um at 0.096 um), clipped to the face."""
    L = P.leaves
    models = models or pin_models(L)
    raw = []
    groups = collections.defaultdict(list)
    for eps in nets:
        pts, tags = [], []
        for e in eps:
            if e[0] >= 0:
                i, p, b = e
                x, y, fx, fy = P.pos[i]
                pts.append(pin_xy(L[i], models[L[i]['master']], p, b, x, y, fx, fy))
                tags.append(L[i]['master'])
        if not pts:
            continue
        ports = [e for e in eps if e[0] < 0]
        for e in ports:
            f = port_face(e[1])
            groups[(e[1], f)].append((len(raw), pts[0]))
        raw.append((pts, tags, [(e[1], port_face(e[1])) for e in ports]))
    place = {}
    face_bits = collections.Counter()
    for (pname, f), lst in groups.items():
        face_bits[f] += len(lst)
        flen = H if f in 'WE' else W
        proj = sorted((p[1] if f in 'WE' else p[0]) for _, p in lst)
        c = proj[len(proj) // 2]
        span = max(len(lst) / port_density, proj[-1] - proj[0] if len(proj) > 1 else 0.0)
        span = min(span, flen)
        lo = min(max(c - span / 2, 0.0), flen - span)
        order = sorted(range(len(lst)), key=lambda k: (lst[k][1][1] if f in 'WE' else lst[k][1][0]))
        for r, k in enumerate(order):
            t = lo + span * (r + 0.5) / len(lst)
            place[(lst[k][0], pname)] = {'W': (0.0, t), 'E': (W, t), 'N': (t, H), 'S': (t, 0.0)}[f]
    out = []
    for n, (pts, tags, ports) in enumerate(raw):
        pts = list(pts)
        tags = list(tags)
        for pname, f in ports:
            pts.append(place[(n, pname)])
            tags.append('PORT_' + f)
        done, todo = [0], list(range(1, len(pts)))
        while todo:
            best = None
            for k in todo:
                for d in done:
                    dd = abs(pts[k][0] - pts[d][0]) + abs(pts[k][1] - pts[d][1])
                    if best is None or dd < best[0]:
                        best = (dd, k, d)
            _, k, d = best
            todo.remove(k)
            done.append(k)
            out.append((pts[d], pts[k], tags[d], tags[k]))
    return out, face_bits


def route(conns, W, H, G=100.0, signal_fraction=1.0, D=4, passes=4, chunk=128, seed=1):
    """negotiated pattern global route on a G-um gcell grid: every gcell-pair bundle is split into <= chunk-bit
    pieces, each routed on the cheapest of all Z-shapes (HVH with the vertical leg at any column, VHV with the
    horizontal leg at any row, within D gcells beyond the bundle box); passes of rip-up and re-route with history
    cost.  Returns horizontal / vertical edge demand arrays, capacity and the per-edge contributors."""
    import numpy as np
    nx, ny = int(math.ceil(W / G)), int(math.ceil(H / G))
    cap = CAP_PER_UM * G * signal_fraction
    bund = collections.Counter()
    tagof = collections.defaultdict(collections.Counter)
    for (x1, y1), (x2, y2), ta, tb in conns:
        a = (min(int(x1 // G), nx - 1), min(int(y1 // G), ny - 1))
        b = (min(int(x2 // G), nx - 1), min(int(y2 // G), ny - 1))
        if a == b:
            continue
        key = (a, b) if a <= b else (b, a)
        bund[key] += 1
        tagof[key][(ta[:22], tb[:22])] += 1
    pieces = []
    for key, n in bund.items():
        k = max(1, int(math.ceil(n / chunk)))
        for j in range(k):
            pieces.append((key, n // k + (1 if j < n % k else 0)))
    rng = __import__('random').Random(seed)
    Hd = np.zeros((ny, max(nx - 1, 1)))
    Vd = np.zeros((max(ny - 1, 1), nx))
    hH = np.zeros_like(Hd)
    hV = np.zeros_like(Vd)
    choice = {}

    def segs(c, key):
        (ax, ay), (bx, by) = key
        kind, t = c
        out = []
        if kind == 'HVH':
            out += [('h', ay, ax, t), ('v', t, ay, by), ('h', by, t, bx)]
        else:
            out += [('v', ax, ay, t), ('h', t, ax, bx), ('v', bx, t, by)]
        return out

    def apply(c, key, w):
        for d, line, u, v in segs(c, key):
            lo, hi = min(u, v), max(u, v)
            if hi == lo:
                continue
            if d == 'h':
                Hd[line, lo:hi] += w
            else:
                Vd[lo:hi, line] += w

    def costs():
        uh = (Hd / cap)
        uv = (Vd / cap)
        ch = 1.0 + hH + np.where(uh > 0.55, (uh / 0.55) ** 6, 0.0)
        cv = 1.0 + hV + np.where(uv > 0.55, (uv / 0.55) ** 6, 0.0)
        ph = np.concatenate([np.zeros((ny, 1)), np.cumsum(ch, axis=1)], axis=1)
        pv = np.concatenate([np.zeros((1, nx)), np.cumsum(cv, axis=0)], axis=0)
        return ph, pv

    def segcost(ph, pv, d, line, u, v):
        lo, hi = min(u, v), max(u, v)
        if d == 'h':
            return ph[line, hi] - ph[line, lo]
        return pv[hi, line] - pv[lo, line]
    for it in range(passes):
        order = list(range(len(pieces)))
        rng.shuffle(order)
        ph, pv = costs()
        for n_done, pi in enumerate(order):
            key, w = pieces[pi]
            if pi in choice:
                apply(choice[pi], key, -w)
            if n_done % 64 == 0:
                ph, pv = costs()
            (ax, ay), (bx, by) = key
            cands = [('HVH', c) for c in range(max(0, min(ax, bx) - D), min(nx - 1, max(ax, bx) + D) + 1)]
            cands += [('VHV', r) for r in range(max(0, min(ay, by) - D), min(ny - 1, max(ay, by) + D) + 1)]
            best = min(cands, key=lambda c: sum(segcost(ph, pv, *s) for s in segs(c, key)))
            choice[pi] = best
            apply(best, key, w)
        hH += np.where(Hd / cap > 0.60, 0.5, 0.0)
        hV += np.where(Vd / cap > 0.60, 0.5, 0.0)
    who = collections.defaultdict(collections.Counter)
    for pi, (key, w) in enumerate(pieces):
        for d, line, u, v in segs(choice[pi], key):
            lo, hi = min(u, v), max(u, v)
            for z in range(lo, hi):
                e = ('h', z, line) if d == 'h' else ('v', line, z)
                if (Hd[line, z] if d == 'h' else Vd[z, line]) / cap > 0.60:
                    for t, n in tagof[key].most_common(2):
                        who[e][t] += w * n / bund[key]
    return Hd, Vd, cap, who, len(pieces), len(bund)


def route_maze(conns, W, H, G=100.0, signal_fraction=1.0, passes=6, chunk=64, target=0.58, seed=1, **_):
    """PathFinder negotiated-congestion maze routing on the gcell graph: every gcell-pair bundle split into <= chunk
    bits; each piece takes the cheapest path (Dijkstra) under cost 1 + history + present over-target penalty;
    ripped up and re-routed every pass, history grows on edges above 0.60."""
    import heapq
    import numpy as np
    nx, ny = int(math.ceil(W / G)), int(math.ceil(H / G))
    cap = CAP_PER_UM * G * signal_fraction
    bund = collections.Counter()
    tagof = collections.defaultdict(collections.Counter)
    for (x1, y1), (x2, y2), ta, tb in conns:
        a = (min(int(x1 // G), nx - 1), min(int(y1 // G), ny - 1))
        b = (min(int(x2 // G), nx - 1), min(int(y2 // G), ny - 1))
        if a == b:
            continue
        key = (a, b) if a <= b else (b, a)
        bund[key] += 1
        tagof[key][(ta[:22], tb[:22])] += 1
    pieces = []
    for key, n in bund.items():
        k = max(1, int(math.ceil(n / chunk)))
        for j in range(k):
            pieces.append((key, n // k + (1 if j < n % k else 0)))
    Hd = np.zeros((ny, max(nx - 1, 1)))
    Vd = np.zeros((max(ny - 1, 1), nx))
    hH = np.zeros_like(Hd)
    hV = np.zeros_like(Vd)
    paths = {}
    rng = __import__('random').Random(seed)

    def apply(path, w):
        for d, a, b in path:
            if d == 'h':
                Hd[a, b] += w
            else:
                Vd[a, b] += w

    def dijkstra(src, dst, w, pf):
        sx, sy = src
        tx, ty = dst
        # bounding window with margin for detours
        m = 6
        x0, x1 = max(0, min(sx, tx) - m), min(nx - 1, max(sx, tx) + m)
        y0, y1 = max(0, min(sy, ty) - m), min(ny - 1, max(sy, ty) + m)
        dist = {src: 0.0}
        prev = {}
        pq = [(0.0, src)]
        while pq:
            dcur, u = heapq.heappop(pq)
            if u == dst:
                break
            if dcur > dist.get(u, 1e18):
                continue
            ux, uy = u
            for vx, vy, d, a, b in ((ux + 1, uy, 'h', uy, ux), (ux - 1, uy, 'h', uy, ux - 1),
                                    (ux, uy + 1, 'v', uy, ux), (ux, uy - 1, 'v', uy - 1, ux)):
                if vx < x0 or vx > x1 or vy < y0 or vy > y1:
                    continue
                if d == 'h':
                    util = (Hd[a, b] + w) / cap
                    hist = hH[a, b]
                else:
                    util = (Vd[a, b] + w) / cap
                    hist = hV[a, b]
                c = 1.0 + hist + (pf * (util - target) * 10 if util > target else 0.0)
                nd = dcur + c
                v = (vx, vy)
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = (u, d, a, b)
                    heapq.heappush(pq, (nd, v))
        path = []
        v = dst
        while v != src:
            u, d, a, b = prev[v]
            path.append((d, a, b))
            v = u
        return path
    order = list(range(len(pieces)))
    for it in range(passes):
        rng.shuffle(order)
        pf = 1.0 + it * 1.5
        for pi in order:
            key, w = pieces[pi]
            if pi in paths:
                apply(paths[pi], -w)
            paths[pi] = dijkstra(key[0], key[1], w, pf)
            apply(paths[pi], w)
        hH += np.where(Hd / cap > 0.60, 1.0, 0.0)
        hV += np.where(Vd / cap > 0.60, 1.0, 0.0)
    who = collections.defaultdict(collections.Counter)
    for pi, (key, w) in enumerate(pieces):
        for d, a, b in paths[pi]:
            over = (Hd[a, b] if d == 'h' else Vd[a, b]) / cap > 0.60
            if over:
                e = ('h', b, a) if d == 'h' else ('v', b, a)
                for t, n in tagof[key].most_common(2):
                    who[e][t] += w * n / bund[key]
    return Hd, Vd, cap, who, len(pieces), len(bund)


def routed_report(P, nets, W, H, G=100.0, pg=None, router='maze', **kw):
    conns, face_bits = connections(P, nets, W, H)
    fn = route_maze if router == 'maze' else route
    Hd, Vd, cap, who, npieces, nb = fn(conns, W, H, G, pg['signal_fraction'] if pg else 1.0, **kw)
    sh = list((Hd / cap).ravel()) + list((Vd / cap).ravel())
    import numpy as np
    over = []
    for (gy, gx), v in np.ndenumerate(Hd):
        if v / cap > 0.60:
            over.append(dict(edge='h', x_um=(gx + 1) * G, y_um=gy * G, share=round(v / cap, 3),
                             top=[[a, b, round(n)] for (a, b), n in who[('h', gx, gy)].most_common(3)]))
    for (gy, gx), v in np.ndenumerate(Vd):
        if v / cap > 0.60:
            over.append(dict(edge='v', x_um=gx * G, y_um=(gy + 1) * G, share=round(v / cap, 3),
                             top=[[a, b, round(n)] for (a, b), n in who[('v', gx, gy)].most_common(3)]))
    over.sort(key=lambda r: -r['share'])
    # whole-line loads: every horizontal line (all vertical crossings) and vertical line; a line above 0.60 on
    # average cannot be fixed by any routing -- only by moving traffic or adding width/height
    hl = [(float(Vd[gy].sum() / (cap * Vd.shape[1])), (gy + 1) * G) for gy in range(Vd.shape[0])]
    vl = [(float(Hd[:, gx].sum() / (cap * Hd.shape[0])), (gx + 1) * G) for gx in range(Hd.shape[1])]
    reach = collections.Counter()
    for (a, b, ta, tb) in conns:
        if not ta.startswith('PORT') and not tb.startswith('PORT') and abs(a[0] - b[0]) + abs(a[1] - b[1]) > 500:
            reach[tuple(sorted((ta, tb)))] += 1
    return dict(model=('PathFinder maze' if router == 'maze' else 'Z-pattern') + ' global route on gcells (bundled, split <= %d bits)' % kw.get('chunk', 64),
                gcell_um=G, cap_bits_per_gcell_edge=round(cap, 1), connections=len(conns), bundles=nb, pieces=npieces,
                worst_share=round(max(sh), 3), edges_over_060=len(over), edges=len(sh),
                p99_share=round(sorted(sh)[int(0.99 * len(sh))], 3), face_pin_bits=dict(face_bits),
                worst_horizontal_line=dict(share=round(max(hl)[0], 3), y_um=max(hl)[1],
                                           lines_over_060=sum(v > 0.60 for v, _ in hl), lines=len(hl)),
                worst_vertical_line=dict(share=round(max(vl)[0], 3), x_um=max(vl)[1],
                                         lines_over_060=sum(v > 0.60 for v, _ in vl), lines=len(vl)),
                leaf_links_over_500um=sum(reach.values()),
                over_reach_pairs=[[a, b, n] for (a, b), n in reach.most_common(12)], hot=over[:15])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--width', type=float, default=3369.6)
    ap.add_argument('--gcell', type=float, default=100.0)
    ap.add_argument('--passes', type=int, default=10)
    ap.add_argument('--out', default=str(AREA / 'a2_route_plan.json'))
    ap.add_argument('--svg', default=str(AREA / 'a2_route_plan.svg'))
    a = ap.parse_args()
    leaves, nets = load()
    P, W, H, struct = build_v4(leaves, nets, a.width)
    bad, outside = P.check(W, H)
    pg = pg_plan(P, W, H)
    ev = routed_report(P, nets, W, H, a.gcell, pg=pg, passes=a.passes)
    res = dict(schema='opentallas.s81.vm-a2-route-plan.v1', status='SCREEN_PIN_ACCURATE_NOT_GRT',
               rectangle_um=[W, round(H, 3)], area_mm2=round(W * H / 1e6, 4), leaves=len(P.pos),
               legality=dict(spacing_violations=bad, outside=outside, channel_um=CH), structure=struct, pg=pg, cuts=ev,
               inputs={p: hashlib.sha256((AREA / p).read_bytes()).hexdigest()
                       for p in ('a2_inventory.json', 'a2_pin_join.jsonl.gz', 'a2_pin_plan.json')},
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               placement={P.leaves[i]['name']: [P.leaves[i]['master']] + list(P.rect(i)) + list(P.pos[i][2:])
                          for i in sorted(P.pos)})
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    import a2_floorplan as F
    F.svg(P, W, H, a.svg)
    print(json.dumps({k: res[k] for k in ('rectangle_um', 'area_mm2', 'legality', 'structure')}))
    print(json.dumps({k: v for k, v in ev.items() if k not in ('hot', 'over_reach_pairs')}))
    for r in ev['over_reach_pairs']:
        print('reach', r)
    for hrec in ev['hot']:
        print(hrec)
    print(json.dumps(pg))


if __name__ == '__main__':
    main()

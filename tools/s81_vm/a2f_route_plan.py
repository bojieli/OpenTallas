#!/usr/bin/env python3
"""S81 VM A2-F (field-major write front) pin-accurate route plan: the A2 bit graph re-grouped exactly as
tools/s81_vm/area_a2f.sv re-groups the A2 leaves, placed and global-routed with the a2_route_plan.py screen.

Net transform (pure leaf/port renaming, the parent stays wires-only; proven cycle-exact by area_a2f_equiv_gate.py):
  quarter stripe (x,q) u_data{k}  port p bit b -> field leaf (x,k) s81_a2f_field16: i_data b (SHARED by the four
                                   quarters), i_sel 168q+b, i_drain_v 8q+b, i_drain_slot 16q+b, o_data 128q+b,
                                   o_v 8q+b, fault q
  quarter (x,q) u_meta             -> s81_a2f_meta26 (x), same rule (i_data shared, o_data 208q+b)
  quarter (x,q) u_control          -> s81_a2f_control4 (x): src_v/src_bank/epochs shared, ids 168q+b, dr_v 8q+b,
                                      dr_s 16q+b, fault q
  quarter (x,q) u_fault            -> s81_a2f_fault_join4 (x): i_fault 10q+b, fault q
Leaf outlines are PLANNED (mapped-area based, see OUTLINES) until the pilot hardening of the new masters measures
them.  Pin faces follow the S-NET closed-station rule: N/S 0.12 um/pin, W/E 0.16 um/pin.
Layout ('column' family): one column per slice, the capture/CDC band at the S face (same packing as a2_route_plan
v4), per column bottom-up: payload | front rows | storage units st0..st3 | read strip.  Screen only (no GRT).
"""
import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a2_route_plan as R  # noqa: E402

ROOT = HERE.parents[1]
OUTD = ROOT / 'results/arch/s81_vm_a2f_1015'
CH = R.CH
NS_PITCH, WE_PITCH = 0.12, 0.16
# planned outlines (um).  Mapped cells (a2_current_summary.json): data16 2,691 um2 / 3,692 FF, meta26 4,180 / 5,842,
# control 2,163 / 1,323.  Merged: field16 4 x data16 - 3 shared 2,544-FF input pipelines ~ 8.5k um2; meta26 ~ 13.1k;
# control4 ~ 5.4k.  Outlines at <= 35 % cell utilisation and the pin-face rule above.
OUTLINES = {'s81_a2f_field16': (237.6, 108.0), 's81_a2f_meta26': (237.6, 162.0),
            's81_a2f_control4': (172.8, 86.4), 's81_a2f_fault_join4': (21.6, 21.6)}


# ------------------------------------------------------------------------------------------------------- transform
def transform(leaves, nets, outlines=OUTLINES):
    old = {}
    for i, l in enumerate(leaves):
        m = re.search(r'a2\.payload\[(\d)\]\.quarter\[(\d)\]\.u_(data(\d)|meta|control|fault)$', l['name'])
        if m:
            x, q, kind = int(m.group(1)), int(m.group(2)), m.group(3)
            old[i] = (x, q, 'data' if kind.startswith('data') else kind, int(m.group(4)) if m.group(4) else None)
    keep = [i for i in range(len(leaves)) if i not in old]
    new = [dict(leaves[i]) for i in keep]
    remap = {i: k for k, i in enumerate(keep)}
    idx = {}

    def add(key, name, master, ports):
        w, h = outlines[master]
        idx[key] = len(new)
        new.append(dict(name=name, master=master, w=w, h=h, ports=ports, geo=None))
    for x in range(4):
        pre = 'dut.u_core.u_ws.a2f.payload[%d].u_front' % x
        for k in range(8):
            add((x, 'data', k), pre + '.field[%d].u_data' % k, 's81_a2f_field16',
                dict(i_data=848, i_sel=672, i_drain_v=32, i_drain_slot=64, o_v=32, o_data=512, fault=4))
        add((x, 'meta', None), pre + '.u_meta', 's81_a2f_meta26',
            dict(i_data=1378, i_sel=672, i_drain_v=32, i_drain_slot=64, o_v=32, o_data=832, fault=4))
        add((x, 'control', None), pre + '.u_control', 's81_a2f_control4',
            dict(src_v=53, src_bank=424, header_epoch=3, payload_epoch=12, ids=672, dr_v=32, dr_s=64, fault=4))
        add((x, 'fault', None), pre + '.u_fault', 's81_a2f_fault_join4', dict(i_fault=40, fault=4))
    width = {'i_sel': 168, 'i_drain_v': 8, 'i_drain_slot': 16, 'o_v': 8, 'ids': 168, 'dr_v': 8, 'dr_s': 16,
             'i_fault': 10, 'fault': 1}
    shared = {'i_data', 'src_v', 'src_bank', 'header_epoch', 'payload_epoch'}

    def ep(e):
        i, p, b = e
        if i < 0:
            return e
        if i not in old:
            return (remap[i], p, b)
        x, q, kind, k = old[i]
        j = idx[(x, kind, k)]
        if p in shared:
            return (j, p, b)
        if p == 'o_data':
            return (j, p, (208 if kind == 'meta' else 128) * q + b)
        return (j, p, width[p] * q + b)
    out = []
    for eps in nets:
        seen, n2 = set(), []
        for e in eps:
            e2 = ep(e)
            if e2 not in seen:
                seen.add(e2)
                n2.append(e2)
        out.append(n2)
    return new, out


# ---------------------------------------------------------------------------------------------------------- pins
def spread(n, length, b, off=0.0):
    return off + length * (b + 0.5) / n


def new_pins(leaf):
    m, w, h = leaf['master'], leaf['w'], leaf['h']
    if m in ('s81_a2f_field16', 's81_a2f_meta26'):
        nin = leaf['ports']['i_data']
        nout = leaf['ports']['o_data'] + 32

        def f(p, b):
            if p == 'i_data':
                return spread(nin, w, b), 0.0
            if p == 'o_data':
                return spread(nout, w, b), h
            if p == 'o_v':
                return spread(nout, w, leaf['ports']['o_data'] + b), h
            if p in ('i_sel', 'i_drain_v', 'i_drain_slot'):          # 768 control bits split over W and E
                o = {'i_sel': 0, 'i_drain_v': 672, 'i_drain_slot': 704}[p] + b
                return (0.0 if o % 2 == 0 else w), spread(384, h, o // 2)
            return w, h / 2
        return f
    if m == 's81_a2f_control4':
        def f(p, b):
            o = {'src_v': 0, 'src_bank': 53, 'header_epoch': 477, 'payload_epoch': 480}.get(p)
            if o is not None:
                return spread(492, w, o + b), 0.0
            o = {'ids': 0, 'dr_v': 672, 'dr_s': 704}.get(p)
            if o is not None:
                return spread(768, w, o + b), h
            return w, h / 2
        return f
    if m == 's81_a2f_fault_join4':
        return lambda p, b: ((0.0, spread(40, h, b)) if p == 'i_fault' else (w, spread(4, h, b)))
    return None


def install_pin_models():
    base = R.pin_models

    def pm(leaves):
        old = [l for l in leaves if l['master'] not in OUTLINES and l.get('geo') is not None or
               l['master'] in ('s81_a2_w0_payload', 's81_a2_w0_header')]
        models = base(old)
        for l in leaves:
            if l['master'] in OUTLINES:
                models.setdefault(l['master'], {})
                l['pins_fn'] = new_pins(l)
        return models
    R.pin_models = pm


# -------------------------------------------------------------------------------------------------------- layout
def build(leaves, nets, W=3369.6, opts=None):
    """column family.  opts: rows = list of front rows bottom-up, each a list of tokens f0..f7 / meta / ctl / fj;
    order = storage/read order above the front; col_w = column width (default (W - 3 ch)/4)."""
    opts = opts or {}
    rows = opts.get('rows', [['f0', 'f1', 'f2'], ['f3', 'f4', 'f5'], ['f6', 'f7', 'meta'], ['ctl', 'fj']])
    order = opts.get('order', ['front', 'st0', 'st1', 'st2', 'st3', 'read'])
    ch = CH
    P = R.Plan(leaves)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    QW = opts.get('col_w', (W - 3 * ch) / 4)
    PW, PH = 820.8, 129.6
    SH = 4 * 75.6 + 3 * ch
    x0 = (W - (4 * QW + 3 * ch)) / 2
    # storage unit membership (x, q) from connectivity of the retained A2 storage leaves
    unit = {}
    for i, n in enumerate(N):
        mm = re.search(r'u_mem\.slice\[(\d)\]', n)
    pb = collections.defaultdict(collections.Counter)
    for eps in nets:
        ls = sorted(set(i for i, _, _ in eps if i >= 0))
        if len(ls) <= 6:
            for a in ls:
                for b in ls:
                    if a != b:
                        pb[a][b] += 1
    front = {}
    for i, n in enumerate(N):
        mm = re.search(r'a2f\.payload\[(\d)\]', n)
        if mm:
            front[i] = int(mm.group(1))
    # scatter (x,q): the scatter whose i_data is driven by quarter q of slice x -> read from net endpoints
    for eps in nets:
        drv = [e for e in eps if e[0] >= 0 and M[e[0]] == 's81_a2f_field16' and e[1] == 'o_data']
        if drv:
            j, _, b = drv[0]
            q = b // 128
            for e in eps:
                if e[0] >= 0 and M[e[0]] == 'dsfd_vm_static_scatter_b8_out':
                    unit[e[0]] = (front[j], q)

    def adopt(prefix, via):
        for i, m in enumerate(M):
            if m.startswith(prefix) and i not in unit:
                c = [(v, j) for j, v in pb[i].items() if j in unit and M[j].startswith(via)]
                assert c, N[i]
                unit[i] = unit[max(c)[1]]
    adopt('dsfd_vm_static_relay128_b8', 'dsfd_vm_static_scatter')
    adopt('dsfd_vm_static_relay128_b4', 'dsfd_vm_static_relay128_b8')
    adopt('dsfd_vm_static_bank128', 'dsfd_vm_static_relay128_b4')
    slice_of = {}
    for i, n in enumerate(N):
        mm = re.search(r'bounded_read\.l14\.u_read\.d(\d+)$', n)
        if mm:
            slice_of[i] = (int(mm.group(1)) // 2) % 4
        mm = re.search(r'u_mem\.slice\[(\d)\]', n)
        if mm and i not in unit:
            slice_of[i] = int(mm.group(1))
    read_like = lambda i: any(k in M[i] for k in ('read_q', 'return', 'fsr'))
    rest = [i for i in range(len(N)) if not (i in unit or i in front or re.search(r'w0_payload', N[i]) or
                                             (i in slice_of and read_like(i)))]
    groups = R.composites(N, M, rest)
    groups.sort(key=lambda g: (0 if 'cap' in M[g[0]] else 1, -max(leaves[i]['h'] for i in g), N[g[0]]))
    tmp = R.Plan(leaves)
    band_h = R.skyline(tmp, groups, 0.0, W, 0.0, ch)
    for i, (xx, yy, fx, fy) in tmp.pos.items():
        P.put(i, W - xx - leaves[i]['w'], yy, not fx, fy)
    y0 = band_h + ch
    tops = []
    fpos = {}
    for x in range(4):
        cx = x0 + x * (QW + ch)
        mem = {k: i for i, k in ((i, None) for i in ())}
        fl = {}
        for i, s in front.items():
            if s != x:
                continue
            mm = re.search(r'field\[(\d)\]', N[i])
            fl['f%d' % int(mm.group(1)) if mm else {'s81_a2f_meta26': 'meta', 's81_a2f_control4': 'ctl',
                                                     's81_a2f_fault_join4': 'fj'}[M[i]]] = i
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])][0]
        leaves[pay]['w'], leaves[pay]['h'] = PW, PH
        y = y0
        P.put(pay, cx + (QW - PW) / 2, y)
        y += PH + ch
        for item in order:
            if item == 'front':
                for row in rows:
                    ids = [fl[t] for t in row]
                    rw = sum(leaves[i]['w'] for i in ids) + ch * (len(ids) - 1)
                    assert rw <= QW + 1e-6, (row, rw, QW)
                    xx = cx + (QW - rw) / 2
                    rh = max(leaves[i]['h'] for i in ids)
                    for i in ids:
                        P.put(i, xx, y)
                        fpos[i] = (xx, y)
                        xx += leaves[i]['w'] + ch
                    y += rh + ch
            elif item.startswith('st'):
                q = int(item[2])
                mem = [i for i, u in unit.items() if u == (x, q)]
                by_m = collections.defaultdict(list)
                for i in mem:
                    by_m[M[i]].append(i)
                banks = sorted(by_m['dsfd_vm_static_bank128'], key=lambda i: N[i])
                b8, sc = by_m['dsfd_vm_static_relay128_b8'][0], by_m['dsfd_vm_static_scatter_b8_out'][0]
                b4 = sorted(by_m['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
                ux = cx + (QW - 820.8) / 2
                place_unit(P, opts.get('unit', 'v4'), ux, lambda off, h: y + off, False, sc, b8, b4, banks, N)
                y += SH + ch
            elif item == 'read':
                items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i)]
                grp = [(i,) for i in sorted(items, key=lambda i: read_key(opts, M[i], leaves[i]['h'], N[i]))]
                y = R.skyline(P, grp, cx, cx + QW, y, ch) + ch
        tops.append(y - ch)

        # payload o_data pins sit under the field leaf that consumes them; mask pins under the meta leaf
        def pay_pins(port, bit, cx=cx, fl=fl):
            if port == 'o_data':
                k, s, j = (bit % 128) // 16, bit // 128, bit % 16
                i = fl['f%d' % k]
                fx, _ = fpos[i]
                return fx - (cx + (QW - PW) / 2) + spread(848, leaves[i]['w'], 16 * s + j), PH
            if port == 'o_mask':
                i = fl['meta']
                fx, _ = fpos[i]
                return fx - (cx + (QW - PW) / 2) + spread(212, leaves[i]['w'], bit), PH
            if port == 'i_data':
                return spread(6784, PW, bit), 0.0
            if port == 'i_mask':
                return 0.0, spread(212, PH, bit)
            if port == 'o_epoch':
                return PW, PH / 2
            return None
        leaves[pay]['pins_fn'] = pay_pins
    H = max(tops)
    return P, W, H, dict(column_um=[round(QW, 3), round(H - y0, 3)], band_um=[W, round(band_h, 3)],
                         payload_um=[PW, PH], rows=rows, order=order)


def read_key(opts, m, h, n):
    """read-strip packing order: 'height' (a2_route_plan v4) or 'flow' (return lanes next to the storage, then the
    read leaves, then their valid leaves, FSR last)."""
    if opts.get('read_order', 'height') == 'flow':
        rank = 0 if 'return' in m else 1 if 'read_q' in m else 2 if 'read_v' in m else 3
        return (rank, -h, n)
    return (-h, n)


def place_unit(P, style, ux, Y, mirror, sc, b8, b4, banks, N, ch=CH):
    """one storage unit (scatter, b8, two b4, eight bank128) in an 820.8 x 367.2 box; Y(off, h) maps a unit-local
    offset from the front-facing edge to the leaf's low y.  'v4' = a2_route_plan v4 arrangement.  'tree' = pin-facing
    arrangement for the CLOSED views' faces (b8/b4: N in, S out to the next level, W responses in, E responses out;
    bank128: W in, E out): [bank col B | bank col A | b4 col | scatter+b8 col], b8 E face on the unit's E edge toward
    the return lanes, b4 E faces facing the b8 W face, bank A E faces facing the b4 W faces."""
    SH = 4 * 75.6 + 3 * ch
    f = not mirror           # R0 N face away from the front unless flipped
    if style == 'v4':
        bA, rel = ux, ux + 220.32 + ch
        c4 = rel + 172.8 + ch
        bB = c4 + 129.6 + ch
        P.put(sc, rel, Y(0, 86.4), False, mirror)
        P.put(b8, rel, Y(SH - 172.8, 172.8), False, mirror)
        for k, i in enumerate(b4):
            P.put(i, c4, Y(k * (129.6 + ch) + (SH - 2 * 129.6 - ch), 129.6), False, mirror)
        for k, i in enumerate(banks):
            P.put(i, bA if k % 2 == 0 else bB, Y((k // 2) * (75.6 + ch), 75.6), k % 2 == 0, mirror)
        return
    xB, xA = ux, ux + 220.32 + ch
    x4 = xA + 220.32 + ch
    xr = x4 + 129.6 + ch
    P.put(sc, xr, Y(0, 86.4), False, f)                       # scatter inputs face the front
    P.put(b8, xr, Y(86.4 + ch, 172.8), False, f)             # b8 N (in) faces the scatter, S (out) away
    for k, i in enumerate(sorted(b4, key=lambda i: N[i])):   # b4 N (in) away from the front, toward b8's S edge
        P.put(i, x4, Y(86.4 + ch + 172.8 - 129.6 - k * (129.6 + ch), 129.6) if False else
              Y(SH - 129.6 - k * (129.6 + ch), 129.6), False, mirror)
    for k, i in enumerate(banks):
        P.put(i, xA if k % 2 == 0 else xB, Y((k // 2) * (75.6 + ch), 75.6), False, mirror)


def classify_units(leaves, nets):
    """front slice of every A2-F leaf; storage unit (x, q) of scatter/b8/b4/bank leaves from the actual bit graph."""
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    pb = collections.defaultdict(collections.Counter)
    for eps in nets:
        ls = sorted(set(i for i, _, _ in eps if i >= 0))
        if len(ls) <= 6:
            for a in ls:
                for b in ls:
                    if a != b:
                        pb[a][b] += 1
    front = {}
    for i, n in enumerate(N):
        mm = re.search(r'a2f\.payload\[(\d)\]', n)
        if mm:
            front[i] = int(mm.group(1))
    unit = {}
    for eps in nets:
        drv = [e for e in eps if e[0] >= 0 and M[e[0]] == 's81_a2f_field16' and e[1] == 'o_data']
        if drv:
            j, _, b = drv[0]
            for e in eps:
                if e[0] >= 0 and M[e[0]] == 'dsfd_vm_static_scatter_b8_out':
                    unit[e[0]] = (front[j], b // 128)

    def adopt(prefix, via):
        for i, m in enumerate(M):
            if m.startswith(prefix) and i not in unit:
                c = [(v, j) for j, v in pb[i].items() if j in unit and M[j].startswith(via)]
                assert c, N[i]
                unit[i] = unit[max(c)[1]]
    adopt('dsfd_vm_static_relay128_b8', 'dsfd_vm_static_scatter')
    adopt('dsfd_vm_static_relay128_b4', 'dsfd_vm_static_relay128_b8')
    adopt('dsfd_vm_static_bank128', 'dsfd_vm_static_relay128_b4')
    slice_of = {}
    for i, n in enumerate(N):
        mm = re.search(r'bounded_read\.l14\.u_read\.d(\d+)$', n)
        if mm:
            slice_of[i] = (int(mm.group(1)) // 2) % 4
        mm = re.search(r'u_mem\.slice\[(\d)\]', n)
        if mm and i not in unit:
            slice_of[i] = int(mm.group(1))
    return front, unit, slice_of


def build_mid(leaves, nets, W=3369.6, opts=None):
    """mid-band family: band (capture/CDC/header/seq/rsched...) across the middle; slices 0,1 grow DOWN from it
    (mirrored), slices 2,3 grow UP; each slice owns a half-width column (W - ch)/2: payload (as wide as the field
    row) | front rows | storage rows of two units side by side | its read strip."""
    opts = opts or {}
    rows = opts.get('rows', [['f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7'], ['ctl', 'fj', 'meta']])
    st_rows = opts.get('st_rows', [['st0', 'st1'], ['st2', 'st3']])
    ch = CH
    P = R.Plan(leaves)
    M = [l['master'] for l in leaves]
    N = [l['name'] for l in leaves]
    CW = (W - ch) / 2          # W = body width; capture columns (cap_cols) are added on the E side
    SH = 4 * 75.6 + 3 * ch
    SW = 820.8
    front, unit, slice_of = classify_units(leaves, nets)
    read_like = lambda i: any(k in M[i] for k in ('read_q', 'return', 'fsr'))
    rest = [i for i in range(len(N)) if not (i in unit or i in front or re.search(r'w0_payload', N[i]) or
                                             (i in slice_of and read_like(i)))]
    groups = R.composites(N, M, rest)
    groups.sort(key=lambda g: (0 if 'cap' in M[g[0]] else 1, -max(leaves[i]['h'] for i in g), N[g[0]]))
    capcols = opts.get('cap_cols', 0)
    capg = [g for g in groups if any(M[i] == 'dsfd_vm_static_cap_leaf' for i in g)] if capcols else []
    groups = [g for g in groups if g not in capg]
    capw = 0.0
    if capg:          # capture lanes (cap_leaf -> x34_s -> x34_t) as columns along the E face, f_c toward the face
        gw = max(sum(leaves[i]['w'] for i in g) + ch * (len(g) - 1) for g in capg)
        capw = capcols * (gw + ch)
        W = W + capw
    tmp = R.Plan(leaves)
    band_h = R.skyline(tmp, groups, 0.0, W - capw, 0.0, ch)
    fpos = {}

    def block(x, base, sgn, P):
        mirror = sgn < 0
        cx = (x % 2) * (CW + ch)

        def Y(off, h):
            return base + off if not mirror else base - off - h
        fl = {}
        for i, s in front.items():
            if s == x:
                mm = re.search(r'field\[(\d)\]', N[i])
                fl['f%d' % int(mm.group(1)) if mm else {'s81_a2f_meta26': 'meta', 's81_a2f_control4': 'ctl',
                                                         's81_a2f_fault_join4': 'fj'}[M[i]]] = i
        rw0 = sum(leaves[fl[t]]['w'] for t in rows[0]) + ch * (len(rows[0]) - 1)
        PW = max(rw0, 820.8)
        PH = math.ceil(106375.68 / PW / 5.4) * 5.4
        pay = [i for i in range(len(N)) if re.search(r'w0_payload\[%d\]' % x, N[i])][0]
        leaves[pay]['w'], leaves[pay]['h'] = PW, PH
        px = cx + (CW - PW) / 2
        P.put(pay, px, Y(0, PH), False, mirror)
        off = PH + ch
        for row in rows:
            ids = [fl[t] for t in row]
            rw = sum(leaves[i]['w'] for i in ids) + ch * (len(ids) - 1)
            assert rw <= CW + 1e-6, (row, rw, CW)
            xx = cx + (CW - rw) / 2
            rh = max(leaves[i]['h'] for i in ids)
            for i in ids:
                P.put(i, xx, Y(off, leaves[i]['h']), False, mirror)
                fpos[i] = xx
                xx += leaves[i]['w'] + ch
            off += rh + ch
        for srow in st_rows:
            n = len(srow)
            tw = n * SW + (n - 1) * ch
            assert tw <= CW + 1e-6
            for j, item in enumerate(srow):
                q = int(item[2])
                ux = cx + (CW - tw) / 2 + j * (SW + ch)
                mem = [i for i, u in unit.items() if u == (x, q)]
                by_m = collections.defaultdict(list)
                for i in mem:
                    by_m[M[i]].append(i)
                banks = sorted(by_m['dsfd_vm_static_bank128'], key=lambda i: N[i])
                b8, sc = by_m['dsfd_vm_static_relay128_b8'][0], by_m['dsfd_vm_static_scatter_b8_out'][0]
                b4 = sorted(by_m['dsfd_vm_static_relay128_b4'], key=lambda i: N[i])
                place_unit(P, opts.get('unit', 'v4'), ux, lambda o, h, off=off: Y(off + o, h), mirror, sc, b8, b4,
                           banks, N)
            off += SH + ch
        items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i)]
        grp = [(i,) for i in sorted(items, key=lambda i: read_key(opts, M[i], leaves[i]['h'], N[i]))]
        if mirror:
            far = R.skyline(P, grp, cx, cx + CW, base - off, ch, flip=True)
        else:
            far = R.skyline(P, grp, cx, cx + CW, base + off, ch)

        def pay_pins(port, bit, px=px, fl=fl, PW=PW, PH=PH):
            if port == 'o_data':
                k, s, j = (bit % 128) // 16, bit // 128, bit % 16
                i = fl['f%d' % k]
                return fpos[i] - px + spread(848, leaves[i]['w'], 16 * s + j), PH
            if port == 'o_mask':
                i = fl['meta']
                return fpos[i] - px + spread(212, leaves[i]['w'], bit), PH
            if port == 'i_data':
                return spread(6784, PW, bit), 0.0
            if port == 'i_mask':
                return 0.0, spread(212, PH, bit)
            if port == 'o_epoch':
                return PW, PH / 2
            return None
        leaves[pay]['pins_fn'] = pay_pins
        return abs(far - base)
    D = max(block(x, 0.0, +1, R.Plan(leaves)) for x in range(4))
    yb = D + ch
    for x in (0, 1):
        block(x, yb - ch, -1, P)
    for i, (xx, yy, fx, fy) in tmp.pos.items():
        P.put(i, (W - capw) - xx - leaves[i]["w"], yb + yy, not fx, fy)
    yt = yb + band_h + ch
    for x in (2, 3):
        block(x, yt, +1, P)
    H = yt + D
    if capg:
        per = math.ceil(len(capg) / capcols)
        gh = max(max(leaves[i]['h'] for i in g) for g in capg)
        if opts.get('cap_dense'):        # lanes packed around the band centre (shortest capture -> payload reach)
            pitch = gh + ch
            y0c = max(0.0, min(H - per * pitch + ch, yb + band_h / 2 - (per * pitch - ch) / 2))
        else:
            pitch = (H - gh) / max(per - 1, 1)
            y0c = 0.0
        assert pitch >= gh + ch - 1e-6, ('capture column too short', pitch, gh)
        for n, g in enumerate(capg):
            c, r = n // per, n % per
            xx = W - (c + 1) * (gw + ch) + ch
            yy = y0c + r * pitch
            for i in reversed(g):          # x34_t nearest the VM body, cap_leaf on the E face (MY: f_c faces E)
                P.put(i, xx, yy, True, False)
                xx += leaves[i]['w'] + ch
    return P, W, H, dict(slice_block_um=[round(CW, 3), round(D, 3)], band_um=[W - capw, round(band_h, 3)], rows=rows,
                         st_rows=st_rows, capture_columns_um=[round(capw, 3), round(H, 3)] if capg else None)


VARIANTS = {
    # three 3-wide field rows + control row (820.8-um columns)
    'r3': dict(rows=[['ctl', 'fj'], ['f0', 'f1', 'f2'], ['f3', 'f4', 'f5'], ['f6', 'f7', 'meta']]),
    'r3top': dict(rows=[['f0', 'f1', 'f2'], ['f3', 'f4', 'f5'], ['f6', 'f7', 'meta'], ['ctl', 'fj']]),
    'r3mid': dict(rows=[['f0', 'f1', 'f2'], ['ctl', 'fj', 'meta'], ['f3', 'f4', 'f5'], ['f6', 'f7']]),
    # narrow field leaves (183.6 x 140.4: i_data 848 x 0.12 = 101.8 um of S face), four per 820.8-um row
    'r2': dict(rows=[['f0', 'f1', 'f2', 'f3'], ['ctl', 'fj', 'meta'], ['f4', 'f5', 'f6', 'f7']],
               outlines={'s81_a2f_field16': (183.6, 140.4)}),
    'r2lo': dict(rows=[['ctl', 'fj', 'meta'], ['f0', 'f1', 'f2', 'f3'], ['f4', 'f5', 'f6', 'f7']],
                 outlines={'s81_a2f_field16': (183.6, 140.4)}),
    'r3flow': dict(rows=[['f0', 'f1', 'f2'], ['f3', 'f4', 'f5'], ['f6', 'f7', 'meta'], ['ctl', 'fj']],
                   read_order='flow'),
    'r3tree': dict(rows=[['f0', 'f1', 'f2'], ['f3', 'f4', 'f5'], ['f6', 'f7', 'meta'], ['ctl', 'fj']], unit='tree'),
    'midtree': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, unit='tree'),
    'midtree_w': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, unit='tree',
                      rows=[['ctl', 'fj', 'meta'], ['f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7']]),
    'midtree_m': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, unit='tree',
                      rows=[['f0', 'f1', 'f2', 'meta', 'f3', 'f4', 'f5'], ['f6', 'ctl', 'fj', 'f7']]),
    'midcap': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, unit='tree', cap_cols=2),
    'midcap1': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, unit='tree', cap_cols=1),
    'midcapd': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, unit='tree', cap_cols=2,
                    cap_dense=True),
    'midflow': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}, read_order='flow'),
    'mid': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)}),
    'mid_w': dict(family='mid', outlines={'s81_a2f_field16': (183.6, 140.4)},
                  rows=[['ctl', 'fj', 'meta'], ['f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7']]),
    'r2hi': dict(rows=[['f0', 'f1', 'f2', 'f3'], ['f4', 'f5', 'f6', 'f7'], ['ctl', 'fj', 'meta']],
                 outlines={'s81_a2f_field16': (183.6, 140.4)}),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--width', type=float, default=3369.6)
    ap.add_argument('--gcell', type=float, default=100.0)
    ap.add_argument('--passes', type=int, default=10)
    ap.add_argument('--variant', default='r3')
    ap.add_argument('--faces', default='die', help="die = S-DIE grant (a2_route_plan.PORT_FACE); band = CDC ports "
                    "beside the band on E, rest unchanged")
    ap.add_argument('--out', default=None)
    ap.add_argument('--svg', default=None)
    a = ap.parse_args()
    install_pin_models()
    if a.faces in ('band', 'bandw'):
        base_face = R.port_face
        cdc = ('aSW', 't_wfc', 'f_wfc', 'sel', 'col', 'qSW', 't_gather')
        side = 'E' if a.faces == 'band' else 'W'
        R.port_face = lambda p: side if p.startswith(cdc) else base_face(p)
    leaves, nets = R.load()
    ol = dict(OUTLINES)
    ol.update(VARIANTS[a.variant].get('outlines', {}))
    leaves, nets = transform(leaves, nets, ol)
    vo = VARIANTS[a.variant]
    P, W, H, struct = (build_mid if vo.get('family') == 'mid' else build)(leaves, nets, a.width, vo)
    bad, outside = P.check(W, H)
    pg = R.pg_plan(P, W, H)
    ev = R.routed_report(P, nets, W, H, a.gcell, pg=pg, passes=a.passes)
    res = dict(schema='opentallas.s81.vm-a2f-route-plan.v1', status='SCREEN_PIN_ACCURATE_NOT_GRT', variant=a.variant,
               faces=a.faces,
               rectangle_um=[W, round(H, 3)], area_mm2=round(W * H / 1e6, 4), leaves=len(P.pos),
               legality=dict(spacing_violations=bad, outside=outside, channel_um=CH), structure=struct,
               planned_outlines=ol, pg=pg, cuts=ev,
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               placement={P.leaves[i]['name']: [P.leaves[i]['master']] + list(P.rect(i)) + list(P.pos[i][2:])
                          for i in sorted(P.pos)})
    out = Path(a.out or OUTD / ('a2f_route_plan_%s.json' % a.variant))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float) + '\n')
    import a2_floorplan as F
    F.svg(P, W, H, a.svg or str(out.with_suffix('.svg')))
    print(json.dumps({k: res[k] for k in ('rectangle_um', 'area_mm2', 'legality', 'structure')}))
    print(json.dumps({k: v for k, v in ev.items() if k not in ('hot', 'over_reach_pairs')}, default=float))
    for r in ev['over_reach_pairs']:
        print('reach', r)
    for hrec in ev['hot'][:6]:
        print(hrec)


if __name__ == '__main__':
    main()

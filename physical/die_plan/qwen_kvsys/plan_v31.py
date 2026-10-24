#!/usr/bin/env python3
"""KV-P2 10-23 v3.1 = v3 plus (COORD 06:33 open items):
  (a) IO row 1728 -> 1036.8 um and the SerDes MIRRORED: the x12 host SerDes becomes two x6 halves (same 0.30 mm2/lane,
      same 223-cycle latency, the 1043-b flit striped 522 W / 521 E; tx_v broadcast, tx_up/rx_v AND-joined) in MY-mirrored
      corner partitions sys_SW (cols 0-1) / sys_SE (cols 7-8): the empty N-W corner is gone;
  (b) every IO partition is one lattice column group <= 1900.8 um wide = one clock tap: sys_SW | io_W2 | io_W3 | sys_c
      (col 4: UCIe + d2d + bumps + dcal) | io_E5 | io_E6 | sys_SE (io_* = corridor / feedthrough cells of the IO row);
  (c) as-built census fix: extract_asbuilt counted the mixed-direction FDI bundles (host.fdi 2089 b, d2d_kv.fdi 1169 b)
      as 1-2 bits; the host<->SerDes and d2d<->UCIe edges carry their real widths here (+4,878 b).
PLAN-KVv3 10-23: KV/system die plan v3 = v2 lattice with (COORD 05:29 v3 items):
  (1) sys/host interface centred: the N-edge IO row keeps only PHY-side partitions -- sys_c (UCIe x64 PHY + d2d +
      fwd/clk bumps + dcal) centred over cols 3-5, sys_E (SerDes) at the N-E corner; the d2d <-> hub traffic runs in
      TWO straight corridors symmetric about the PV axis: col 3 (hgi_WN) -> hub_Wi (host, kvs_emb, embgw) and col 5
      (hgi_EN) -> hub_Ei -> hub_C (kvs_attn, kvs_ctl, pvfin, ahub, seq core); the N-W corner of the IO row (cols 0-2)
      holds no partition (IO row height is set by the SerDes macro; nothing on the die belongs at that corner);
      the centre band grows 604.8 -> 838.08 um per row (hub E/W faces carry the kvs_ctl/host band trunks);
  (2) PLL in hub_C: the clock spine root is the die centre;
  (4) L1 + reach: the 2.56-mm hg row is split into hg (outer: ectl + astk segment + heads 0,1) and hgi (inner, PV
      side: heads 2,3), each 1278.72 um; the 7-mm centre hub into 5 lattice partitions hub_Wo/Wi/C/Ei/Eo.
v2 docstring follows.

PLAN-KVv2 10-23: KV/system die plan v2 (TOPDOWN-PLAN) from the as-built rtl6 connectivity.

v2 = a regular die-row lattice with mirrored replicas (PLAN-TOOL die lattice: symmetric M4-M9 tracks, 8.64 grid):

  y ^  sys_W | sys_core            | sys_E                 (1728 um strip: UCIe/d2d | core logic + host | SerDes)
     |  N rows k=0..7 (MX of S)  .. N row 7 ..            (1520.64 um die rows, 4 HBM PCs per row)
     |  band N: hroot_WN | astkb_WN | hub | astkb_EN | hroot_EN   (432 um; MX of band S)
     |  band S: hroot_WS | astkb_WS | hub | astkb_ES | hroot_ES
     |  S rows k=7..0: phy | pc | hg | pv | hg | pc | phy   (W half R0, E half MY, N quads MX / R180)

- phy_Q_k: HBM PHY model sliced per 4 PCs (one clock region per 1.5-mm slice; was one 0.9 x 12 mm strip).
- pc_Q_k: 4 kvpc + 4 hsl + 1 slg (the slg that owns those 4 PCs) = one HBM row.
- hg_Q_k: the head group of that slg (ectl + 4 heads + hst tree) + the astk segment at chain position k (ep + 4 ex +
  owner): the thin astk column of v1 is folded into the head-group row (astk chain = vertical neighbour links).
- pv_H_k: 4 PV groups (s_k, s_k+8, s_k+16, s_k+24) per 1520-um row; vports sit in the odd PV row of their slg pair.
- band/hub: kvs_hroot + kc + fault joins (hroot), astk ctl + zn (astkb), ahub + pvfin + PV wide ctl + RH heads (hub).
- Routing is template (dimension-ordered): horizontal in the die row, vertical in one corridor column; sys traffic
  uses the pass corridor = the hg column of the N-W quadrant (sys_core sits directly above it).  Trees are broadcast
  trunks (constant width inside a column = identical replicas: each row taps its slice), gathers are mux chains.
"""
import argparse
import collections
import gzip
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_plan as v1  # noqa: E402  (connections(), nbits(), union() reused)

G = 8.64
REACH = 1200.0
XB = [0.0, 864.0, 1900.8, 3179.52, 4458.24, 6359.04, 7637.76, 8916.48, 9953.28, 10817.28]
PVC = 4                                              # PV (centre) column
ROW = 1520.64
BAND = 838.08                                        # v3: 604.8 -> 838.08 (hub E/W faces carry the band trunks)
SYS_H = 1036.8                                       # v3.1: x6 SerDes halves (1.81 mm2 in 1900.8 um) / UCIe 777.6
Y_BS = 8 * ROW
Y_BN = Y_BS + BAND
Y_N = Y_BN + BAND
Y_SYS = Y_N + 8 * ROW
DIE_W, DIE_H = XB[-1], Y_SYS + SYS_H
QUADS = dict(WS=('W', 'S', 'R0'), ES=('E', 'S', 'MY'), WN=('W', 'N', 'MX'), EN=('E', 'N', 'R180'))
PHYS = [4, 5, 0, 1, 2, 3, 6, 7]                     # slg index at physical row p (as-built order, kvpc 4p..4p+3)
PINV = {k: p for p, k in enumerate(PHYS)}
CORR = (3, 5)                                        # sys corridors: hgi_WN (col 3) and hgi_EN (col 5), symmetric about PV
OPP = dict(E='W', W='E', N='S', S='N')


def r4(v):
    return round(v, 4)


# --------------------------------------------------------------------------------------------- lattice / partitions
def row_cell(half, k):
    return k if half == 'S' else 17 - k


def cell_y(r):
    if r < 8:
        return r * ROW, ROW
    if r == 8:
        return Y_BS, BAND
    if r == 9:
        return Y_BN, BAND
    if r < 18:
        return Y_N + (r - 10) * ROW, ROW
    return Y_SYS, SYS_H


def build_partitions():
    P = {}

    def add(name, cls, cells, orient, scope, **kw):
        cs = sorted(cells)
        x0 = XB[min(c for c, _ in cs)]
        x1 = XB[max(c for c, _ in cs) + 1]
        ys = [cell_y(r) for _, r in cs]
        y0 = min(y for y, _ in ys)
        y1 = max(y + h for y, h in ys)
        P[name] = dict(name=name, cls=cls, x=r4(x0), y=r4(y0), w=r4(x1 - x0), h=r4(y1 - y0), orient=orient,
                       scope=scope, cells=cs, **kw)

    for q, (side, half, o) in QUADS.items():
        cphy, cpc, chg, chi = (0, 1, 2, 3) if side == 'W' else (8, 7, 6, 5)
        for k in range(8):
            r = row_cell(half, k)
            add(f'phy_{q}_{k}', 'phy', [(cphy, r)], o, q, idx=k)
            add(f'pc_{q}_{k}', 'pc', [(cpc, r)], o, q, idx=k)
            add(f'hg_{q}_{k}', 'hg', [(chg, r)], o, q, idx=k)
            add(f'hgi_{q}_{k}', 'hgi', [(chi, r)], o, q, idx=k)
        rb = 8 if half == 'S' else 9
        add(f'hroot_{q}', 'hroot', [(cphy, rb), (cpc, rb)], o, q)
    for half, o in (('S', 'R0'), ('N', 'MX')):
        for k in range(8):
            add(f'pv_{half}_{k}', 'pv', [(PVC, row_cell(half, k))], o, half, idx=k)
    for nm, c in (('hub_Wo', 2), ('hub_Wi', 3), ('hub_C', 4), ('hub_Ei', 5), ('hub_Eo', 6)):   # centre band
        add(nm, nm, [(c, 8), (c, 9)], 'R0', 'die')
    add('sys_SW', 'sys_SD', [(0, 18), (1, 18)], 'R0', 'die')   # SerDes x6 half W (v3.1 mirror)
    add('io_W2', 'io_ft', [(2, 18)], 'R0', 'die')
    add('io_W3', 'io_cor', [(3, 18)], 'R0', 'die')            # W corridor head (d2d/SerDes <-> hub_Wi)
    add('sys_c', 'sys_c', [(4, 18)], 'R0', 'die')             # UCIe PHY + d2d (N-edge centre, col 4)
    add('io_E5', 'io_cor', [(5, 18)], 'MY', 'die')            # E corridor head (d2d <-> hub_Ei/hub_C)
    add('io_E6', 'io_ft', [(6, 18)], 'MY', 'die')
    add('sys_SE', 'sys_SD', [(7, 18), (8, 18)], 'MY', 'die')  # SerDes x6 half E
    return P


# --------------------------------------------------------------------------------------------- as-built rewrite
HUB = {'kvs_attn': 'hub_C', 'pvfin': 'hub_C', 'ahub': 'hub_C', 'kvs_ctl': 'hub_C', 'pll': 'hub_C',
       'host': 'hub_Wi', 'kvs_emb': 'hub_Wi', 'embgw': 'hub_Wi', 'seq': 'hub_C'}
SYS_C = ('ucie_rom', 'd2d_kv', 'fwb_ep', 'fwb_rs', 'ckb_kv', 'dcal')
SYS_SD = dict(serdes_W='sys_SW', serdes_E='sys_SE')
ASTK_CHAIN = re.compile(r'^(astk_(WS|ES|WN|EN))__.*?(g_ep_(\d)|g_owner_(\d))')


def rewrite_asbuilt(asb):
    """(1) split each HBM PHY model into 8 slices of 4 PCs (port index n -> slice n // 4; clock/reset to slice 0);
    (2) astk relabel: astk chain position p serves the head group in plan row p (ectl_{PHYS[p]}): every ectl_k <->
    astk ep/owner edge is re-pointed from position k to position PINV[k] (compiler/static-schedule relabel, like v1's
    PC relabel; the astk chain order itself is unchanged)."""
    B = dict(asb['blocks'])
    fdi_fix(asb, B)
    for q in QUADS:
        b = B.pop(f'phy_{q}')
        for k in range(8):
            B[f'phy_{q}__s{k}'] = dict(b, y=b['y'] + k * b['h'] / 8, h=b['h'] / 8)
    moved = 0
    for e in asb['edges']:
        ms = re.match(r'hsl_(WS|ES)_(\d+)$', e['s'])
        md = re.match(r'hsl_(WS|ES)_(\d+)$', e['d'])
        for end in ('s', 'd'):
            if re.match(r'hsl_(WS|ES)_\d+$', e[end]):
                B[e[end]] = dict(B[e[end]], m='qkd_hslice_dn')        # the N-quad (head at 31) hslice variant
        if ms and md and ms.group(1) == md.group(1):           # chain link n -> n+-1: reverse (N-quad orientation)
            e['s'], e['d'] = f'hsl_{ms.group(1)}_{md.group(2)}', f'hsl_{md.group(1)}_{ms.group(2)}'
        elif ms and e['d'] == 'host' and ms.group(2) == '0':
            e['s'] = f'hsl_{ms.group(1)}_31'
        elif md and e['s'] == 'host' and md.group(2) == '0' and not re.search('rst|^ck', e['dp']):
            e['d'] = f'hsl_{md.group(1)}_31'
        for end, port in (('s', 'sp'), ('d', 'dp')):
            n = e[end]
            if n.startswith('phy_') and '__' not in n:
                m = re.search(r'(\d+)$', e[port])
                k = int(m.group(1)) // 4 if m and not v1.CLOCK_PORT.match(e[port]) and 'rst' not in e[port] else 0
                e[end] = f'{n}__s{k}'
        ends = [e['s'], e['d']]
        for i in (0, 1):
            m = re.match(r'ectl_(WS|ES|WN|EN)_(\d)$', ends[1 - i])
            mm = ASTK_CHAIN.match(ends[i])
            if m and mm and mm.group(2) == m.group(1):
                k = int(m.group(2))
                g = int(mm.group(4) or mm.group(5))
                assert g == k, (ends, g, k)
                new = re.sub(r'(g_ep_|g_owner_)\d', lambda z: z.group(1) + str(PINV[k]), ends[i])
                moved += new != ends[i]
                ends[i] = new
        e['s'], e['d'] = ends
    return B, moved


FDI_FIX = []


def fdi_fix(asb, B):
    """v3.1 (c) + (a): real FDI widths and the mirrored x6 SerDes halves.  die.v (rtl6): serdes_host .tx_up(fdi[0])
    .tx_v(fdi[1]) .tx_flit(fdi[1044:2]) .rx_v(fdi[1045]) .rx_flit(fdi[2088:1046]); ucie_rom same layout on d2d_kv.fdi
    (583-b flit, 1169 b).  Halves: W = flit[521:0] (522 b), E = flit[1042:522] (521 b)."""
    sd = B.pop('serdes_host')
    hw = 972.0                                              # 1.8146 mm2 / 1866.24 um
    B['serdes_W'] = dict(sd, m='ot_qfd_serdes_112g_x6_phy', w=1866.24, h=hw)
    B['serdes_E'] = dict(sd, m='ot_qfd_serdes_112g_x6_phy', w=1866.24, h=hw, o='MY')
    E = []
    for e in asb['edges']:
        if 'serdes_host' not in (e['s'], e['d']) and not ({e['s'], e['d']} == {'d2d_kv', 'ucie_rom'}):
            E.append(e)
            continue
        FDI_FIX.append(dict(e))
        if {e['s'], e['d']} == {'d2d_kv', 'ucie_rom'}:
            if e['sp'] == 'tx_up' or e['dp'] == 'rst_n':
                E.append(e)
            else:
                E.append(dict(e, bits=584 if e['dp'] == 'tx_flit' else 584, sbits=[[0, 583]]))
            continue
        for h, n in (('W', 522), ('E', 521)):
            x = dict(e)
            if x['s'] == 'serdes_host':
                x['s'] = 'serdes_' + h
            if x['d'] == 'serdes_host':
                x['d'] = 'serdes_' + h
            if (x['sp'], x['dp']) in (('fdi', 'tx_flit'), ('rx_flit', 'fdi')):
                x = dict(x, bits=n + 1, sbits=[[0, n]])          # flit half + tx_v / rx_v
            E.append(x)
    asb['edges'] = E


SPINE_RESETS = ('die_rst_n',)


def connections(asb, where):
    """v1.connections with the v3.1 census rule (COORD/GEOM-REVIEW2 G1): only the die reset (host.die_rst_n) is
    replaced by the reset spine + per-partition syncs; the host's sequenced functional resets (hbm_rst_n, host_rst_n,
    link_rst_n ...) are ordinary registered control lanes (v3 dropped 432 of them as 'reset')"""
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    tally = collections.Counter()
    for e in asb['edges']:
        s, d = e['s'], e['d']
        ps, pd = where[s][0], where[d][0]
        if v1.CLOCK_PORT.match(e['sp']):     # v3.1: by the SOURCE port (pll.locked -> host pll_locked is data)
            tally['clock_bits'] += e['bits']
            continue
        if v1.RESET_PORT.search(e['dp']) and (e['sp'] in SPINE_RESETS or e['sp'] in ('b', 'q')):
            tally['reset_bits'] += e['bits']
            continue
        if ps == pd:
            tally['internal_bits'] += e['bits']
            continue
        tally['lane_bits'] += e['bits']
        groups[(s, e['sp'])][pd].append((d, e['dp'], e['bits'], e['sbits'], e['stages']))
    return groups, tally


def v1_ranges(ix):
    out = []
    for i in sorted(ix):
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


HUBX = {h: (XB[c] + XB[c + 1]) / 2 for h, c in (('hub_Wo', 2), ('hub_Wi', 3), ('hub_C', 4), ('hub_Ei', 5),
                                                  ('hub_Eo', 6))}


def assign_blocks(B):
    out = {}
    for n, b in B.items():
        t = n.split('__')[0]
        rest = n[len(t):]
        m = re.match(r'(phy|kvpc|hsl|slg|vport|head|ectl|hst|astk|kc|kvs_hroot)_(WS|ES|WN|EN)(?:_(\d+))?(?:_(\d+))?(.*)$',
                     t)
        if m:
            cls, q, i1, i2, tail = m.groups()
            half = QUADS[q][1]
            if cls == 'phy':
                out[n] = (f'phy_{q}_{int(rest[3:])}', 'phy')
            elif cls in ('kvpc', 'hsl'):
                k = int(i1)
                out[n] = (f'pc_{q}_{k // 4}', f'{cls}{k % 4}{rest}')
            elif cls == 'slg':
                out[n] = (f'pc_{q}_{PINV[int(i1)]}', f'slg{rest}')
            elif cls == 'vport':
                j = int(i1)
                rows = sorted((PINV[2 * j], PINV[2 * j + 1]))
                assert rows[1] == rows[0] + 1 and rows[0] % 2 == 0, rows
                out[n] = (f'pv_{half}_{rows[1]}', f'vport_{QUADS[q][0]}{rest}')
            elif cls in ('ectl', 'head', 'hst'):
                r = int(i1)
                loc = {'ectl': 'ectl', 'head': f'head{i2}', 'hst': f'hst{i2}{tail}'}[cls]
                inner = cls != 'ectl' and int(i2) >= 2                 # heads 2,3 (+ their hst) on the PV side
                out[n] = (f'hg{"i" if inner else ""}_{q}_{PINV[r]}', loc + rest)
            elif cls == 'astk':
                mm = re.search(r'g_ep_(\d)|g_owner_(\d)', rest)
                if mm:
                    g = int(mm.group(1) or mm.group(2))
                    out[n] = (f'hg_{q}_{g}', 'astk' + re.sub(r'(g_ep_|g_owner_)\d', r'\1p', rest))
                else:
                    out[n] = ('hub_' + ('Wo' if q[0] == 'W' else 'Eo'), f'astk_{q}' + rest)
            elif cls in ('kc', 'kvs_hroot'):
                out[n] = (f'hroot_{q}', cls)
            continue
        m = re.match(r'pvw_([01])$', t)
        if m:
            half = 'S' if m.group(1) == '0' else 'N'
            mm = re.match(r'__u_s(\d+)_', rest)
            if mm:
                out[n] = (f'pv_{half}_{int(mm.group(1)) % 8}', 'pv' + re.sub(r'u_s(\d+)_', lambda z: f'u_g{int(z.group(1)) // 8}_', rest))
            else:
                out[n] = ('hub_C', f'pv{half}{rest}')        # wide ctl + RH heads (centre-fed)
            continue
        if t.startswith('hp_fault'):               # fault OR tree: singletons only (quad partitions stay identical)
            cx = b['x'] + b['w'] / 2                 # OR-tree node: the hub partition under its as-built x
            out[n] = (min(HUBX, key=lambda h: abs(HUBX[h] - cx)), t)
            continue
        if t == 'seq' and re.match(r'__g_(fan|xs)_(\d)', rest):       # per-quadrant seq fan/xs beside its astk ctl
            out[n] = ('hub_Wo' if int(re.match(r'__g_(fan|xs)_(\d)', rest).group(2)) < 2 else 'hub_Eo', t + rest)
        elif t in HUB:
            out[n] = (HUB[t], t + rest)
        elif t in SYS_C:
            out[n] = ('sys_c', t + rest)
        elif t in SYS_SD:
            out[n] = (SYS_SD[t], 'serdes' + rest)
        else:
            raise ValueError(f'unassigned block {n}')
    return out


# --------------------------------------------------------------------------------------------- template router
def cell_of(P, part, toward=None):
    """the partition's cell nearest `toward` (a cell)"""
    cs = P[part]['cells']
    if toward is None or len(cs) == 1:
        return cs[0]
    return min(cs, key=lambda c: (abs(c[0] - toward[0]) + abs(c[1] - toward[1]), c))


def seg(a, b):
    """straight cell segment a -> b (same row or column), excluding a"""
    (c0, r0), (c1, r1) = a, b
    assert c0 == c1 or r0 == r1, (a, b)
    out = []
    if c0 != c1:
        s = 1 if c1 > c0 else -1
        out = [(c, r0) for c in range(c0 + s, c1 + s, s)]
    elif r0 != r1:
        s = 1 if r1 > r0 else -1
        out = [(c0, r) for r in range(r0 + s, r1 + s, s)]
    return out


def is_row(r):
    return r < 8 or 10 <= r < 18


def half_of(r):
    return 'S' if r < 8 else 'N' if 10 <= r < 18 else 'B' if r in (8, 9) else 'Y'


def cell_path(P, a, b):
    """cell path from cell a to cell b (both included), dimension-ordered with corridor columns"""
    (ca, ra), (cb, rb) = a, b
    if a == b:
        return [a]
    ha, hb = half_of(ra), half_of(rb)
    if ha == 'Y' and hb == 'Y':
        return [a] + seg(a, b)
    if hb == 'Y':                                      # to sys: reverse of from-sys
        return list(reversed(cell_path(P, b, a)))
    if ha == 'Y':                                      # from sys: along the IO row to a corridor column (W of the
        pc = CORR[0] if cb <= CORR[0] else CORR[1]     # PV column -> col 3, else the PV column), straight down it;
        p1 = (pc, 18)                                  # N-half targets leave the corridor in their row, others at
        if hb == 'N':                                  # band N (then the band rule)
            p2 = (pc, rb)
            return [a] + seg(a, p1) + seg(p1, p2) + seg(p2, b)
        p2 = (pc, 9)
        return [a] + seg(a, p1) + seg(p1, p2) + cell_path(P, p2, b)[1:]
    if ha == 'B' and hb == 'B':
        return [a] + seg(a, (cb, ra)) + seg((cb, ra), b)
    if hb == 'B':
        return list(reversed(cell_path(P, b, a)))
    if ha == 'B':                                      # band -> row: switch band row in place, along the band,
        rb_band = 8 if hb == 'S' else 9                # then vertical in the target column
        p1 = (ca, rb_band)
        p2 = (cb, rb_band)
        return [a] + seg(a, p1) + seg(p1, p2) + seg(p2, b)
    # row -> row
    if ra == rb:
        return [a] + seg(a, b)
    if ha != hb:                                       # other half: through the band in the source column
        rb_band = 8 if ha == 'S' else 9
        p1 = (ca, rb_band)
        return [a] + seg(a, p1) + cell_path(P, p1, b)[1:]
    col = PVC if PVC in (ca, cb) else cb               # vertical in the PV column if PV is an end, else dst column
    p1, p2 = (col, ra), (col, rb)
    return [a] + seg(a, p1) + seg(p1, p2) + seg(p2, b)


def part_route(P, C2P, src, dst):
    """partition hop list [(u, v, face of u)] for src -> dst"""
    a = cell_of(P, src, cell_of(P, dst))
    b = cell_of(P, dst, a)
    cells = cell_path(P, a, b)
    seq = []
    for c in cells:
        p = C2P[c]
        if not seq or seq[-1][0] != p:
            seq.append((p, c))
        else:
            seq[-1] = (p, c)                            # last cell of the partition on the path
    hops = []
    prev_cell = None
    for i in range(len(seq) - 1):
        u, cu = seq[i]
        v, _ = seq[i + 1]
        # entry cell of v
        k = cells.index(cu)
        cv = cells[k + 1]
        dc, dr = cv[0] - cu[0], cv[1] - cu[1]
        face = 'E' if dc > 0 else 'W' if dc < 0 else 'N' if dr > 0 else 'S'
        hops.append((u, v, face))
    return hops, cells


def bends_of(cells):
    dirs = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(cells, cells[1:])]
    return sum(1 for d0, d1 in zip(dirs, dirs[1:]) if d0 != d1)


# --------------------------------------------------------------------------------------------- build
def span(p, fi, fo):
    if {fi, fo} == {'E', 'W'}:
        return p['w']
    if {fi, fo} == {'N', 'S'}:
        return p['h']
    return (p['w'] + p['h']) / 2


def build(asb_path):
    asb = json.load(gzip.open(asb_path))
    B, relabel = rewrite_asbuilt(asb)
    P = build_partitions()
    C2P = {c: n for n, p in P.items() for c in p['cells']}
    where = assign_blocks(B)
    for n, (p, _) in where.items():
        assert p in P, (n, p)
    groups, tally = connections(asb, where)

    by_dst = collections.defaultdict(list)
    for (s, sp), dd in groups.items():
        for pd, lst in dd.items():
            for (d, dp, bits, sb, st) in lst:
                by_dst[(d, dp)].append((s, sp, bits, st))
    gather_dst = {k: v for k, v in by_dst.items() if len({where[s][0] for s, _, _, _ in v}) > 2
                  and max(b for _, _, b, _ in v) >= 128}
    fam = collections.defaultdict(lambda: collections.defaultdict(list))
    members = collections.Counter()
    member_off = collections.defaultdict(dict)        # v3.1 binder: family key -> {member port: bit-id offset}
    for (s_, sp_), dd in groups.items():
        width = sum(len(v1.union([x[3] for x in lst])) for lst in dd.values())
        key = (s_, re.sub(r'\d+', '#', sp_)) if width <= 64 else (s_, sp_)
        # v3.1 census fix: offset by family MEMBER count (v3 used len(fam[key]) = destination partitions, so members
        # to one partition shared an offset and the union dropped bits: 512 b, e.g. phy fh0-3 16 b -> 8)
        off = 4096 * members[key] if key[1] != sp_ else 0
        members[key] += 1
        member_off[key][sp_] = off
        for pd, lst in dd.items():
            for (d, dp, bits, sb, st) in lst:
                fam[key][pd].append((d, dp, bits, [[a_ + off, b_ + off] for a_, b_ in sb], st))

    route_cache = {}

    def route(a, b):
        if (a, b) not in route_cache:
            route_cache[(a, b)] = part_route(P, C2P, a, b)
        return route_cache[(a, b)]

    def entry_of(path_parts):
        """first row partition (pc/hg/pv/phy) of a root->dst partition list"""
        for p in path_parts:
            if P[p]['cls'] in ('pc', 'hg', 'hgi', 'pv', 'phy'):
                return p
        return None

    trees = []
    for (s, sp), dd in sorted(fam.items()):
        ps = where[s][0]
        dests, asb_st = {}, {}
        for pd, lst in dd.items():
            if all((d, dp) in gather_dst for d, dp, _, _, _ in lst):
                continue
            dests[pd] = v1.union([x[3] for x in lst])
            asb_st[pd] = max(x[4] for x in lst)
        if not dests:
            continue
        parent, face_of = {}, {}
        for pd in sorted(dests, key=lambda p: (len(route(ps, p)[0]), p)):
            hops, _ = route(ps, pd)
            for (u, v, f) in hops:
                if v == ps or v in parent:
                    continue
                parent[v] = u
                face_of[v] = f
        kids = collections.defaultdict(list)
        for v, u in parent.items():
            kids[u].append(v)
        need = {}

        def below(u):
            bset = set(dests.get(u, ()))
            for v in kids[u]:
                bset |= below(v)
            need[u] = bset
            return bset
        below(ps)

        # trunk rule: inside a column (row partitions) every edge carries the full width needed at the column entry
        def chain_to_root(v):
            out = [v]
            while out[-1] != ps:
                out.append(parent[out[-1]])
            return list(reversed(out))
        width, carried = {}, {}
        for v in parent:
            ent = entry_of(chain_to_root(v)[1:])
            carried[v] = need[ent] if ent and P[v]['cls'] in ('pc', 'hg', 'hgi', 'phy') else need[v]
            width[v] = len(carried[v])
        edges = [(parent[v], v, face_of[v], width[v]) for v in parent if need[v]]
        trees.append(dict(src=s, sp=sp, root=ps, edges=edges, dests={k: len(v) for k, v in dests.items()},
                          asbuilt_stages=asb_st, kind='p2p' if len(dests) == 1 else 'tap_tree',
                          members=member_off.get((s, sp), {sp: 0}),
                          carried={v: v1_ranges(c) for v, c in carried.items() if need[v]}))

    gathers = []
    for (d, dp), srcs in sorted(gather_dst.items()):
        pd = where[d][0]
        width = max(b for _, _, b, _ in srcs)
        sparts = sorted({where[s][0] for s, _, _, _ in srcs})
        cd = (P[pd]['x'] + P[pd]['w'] / 2, P[pd]['y'] + P[pd]['h'] / 2)
        sparts.sort(key=lambda p: (-(abs(P[p]['x'] + P[p]['w'] / 2 - cd[0]) + abs(P[p]['y'] + P[p]['h'] / 2 - cd[1])), p))
        gathers.append(dict(dst=d, dp=dp, dpart=pd, width=width, srcparts=sparts,
                            asbuilt_stages=max(st for _, _, _, st in srcs), n_src=len(srcs)))

    # ---- lanes (functional node = root, destination, branch point); stations per crossed partition
    lanes, dest_lat = [], {}

    def stations(part, fi, fo):
        return max(1, math.ceil(span(P[part], fi, fo) / REACH - 1e-9))
    for t in trees:
        kids = collections.defaultdict(list)
        for (u, v, fo, bits) in t['edges']:
            kids[u].append((v, fo, bits))
        functional = {t['root']} | set(t['dests']) | {u for u in kids if len(kids[u]) > 1}
        lat_at = {t['root']: 0}
        stack = [(t['root'], v, fo, bits) for (v, fo, bits) in sorted(kids[t['root']])]
        while stack:
            start, v, fo, bits = stack.pop()
            hops = [(start, v, fo, bits)]
            cur = v
            while cur not in functional:
                (nv, nfo, nb), = kids[cur]
                hops.append((cur, nv, nfo, nb))
                cur = nv
            st = sum(stations(w, OPP[f], f2) for (u, w, f, b), (u2, w2, f2, b2) in zip(hops, hops[1:]))
            lanes.append(dict(id=f'L{len(lanes)}', src=t['src'], sp=t['sp'], root=t['root'], hops=hops, stations=st,
                              ids=t['carried'][v],
                              cycles=st + 2, width=max(b for *_, b in hops), kind=t['kind']))
            lat_at[cur] = lat_at[start] + st + 2          # out flop + stations + in flop (tap relaunch included)
            for (nv, nfo, nb) in sorted(kids[cur]):
                stack.append((cur, nv, nfo, nb))
        for d in t['dests']:
            dest_lat[(t['src'], t['sp'], d)] = (lat_at[d], t['asbuilt_stages'][d])
    for g in gathers:
        chain = g['srcparts'] + ([g['dpart']] if g['dpart'] not in g['srcparts'] else [])
        tot = 0
        # NOTE (KV-P2 binder finding): the as-built gather is the PV result T-chain of qkd_rlyi_258s MUX relays
        # (b <= s ? y : a), which extract_asbuilt collapsed as pass cells; the chain stages are logic to plan.
        for a_, b_ in zip(chain, chain[1:]):
            hops = [(u, v, fo, g['width']) for (u, v, fo) in route(a_, b_)[0]]
            st = sum(stations(w, OPP[f], f2) for (u, w, f, b), (u2, w2, f2, b2) in zip(hops, hops[1:]))
            lanes.append(dict(id=f'L{len(lanes)}', src=g['dst'], sp='gather:' + g['dp'], root=a_, hops=hops,
                              stations=st, cycles=st + 2, width=g['width'], kind='gather_chain'))
            tot += st + 2
        g['chain_cycles'] = tot
    # bends per lane on the partition-centre polyline is coarse; use the cell path of the lane's end partitions
    for l in lanes:
        fs = [f for (_, _, f, _) in l['hops']]
        l['bends'] = sum(1 for f0, f1 in zip(fs, fs[1:]) if f0 != f1)
    return dict(P=P, where=where, trees=trees, gathers=gathers, lanes=lanes, tally=tally, relabel=relabel,
                dest_lat={'|'.join(k): v for k, v in dest_lat.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    S = build(a.asbuilt)
    S['P'] = {k: {kk: vv for kk, vv in v.items()} for k, v in S['P'].items()}
    json.dump(S, gzip.open(a.out, 'wt'))
    print(f"partitions {len(S['P'])}, trees {len(S['trees'])}, gathers {len(S['gathers'])}, lanes {len(S['lanes'])}, "
          f"astk relabel edges {S['relabel']}, tally {dict(S['tally'])}", file=sys.stderr)


if __name__ == '__main__':
    main()

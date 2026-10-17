#!/usr/bin/env python3
"""q3h die-top tree v5 (Q-DIEPLAN3-HT, 2026-10-16) on the FINAL grid (array_grid.json = q3h2_grid.json, die 32,996.16 x
22,476.96; homes q3h2-homes.json).  Model only, no GEN.

Two broadcast variants (Q3H_VARIANT):
  comb      today's head chain re-placed in the head gap: xs_tap hw_d -> h_23.e_d -> h_22 ... h_0 (W), he_d -> h_24.w_d
            -> ... h_47 (E); relays in the ~393-um gaps between heads (middle row), hop <= 373.
  stations  (q3h3 candidate) one station per head in the head's centre-side gap; station -> station chain alternating
            lane L / U; station d_out1 -> its head e_d / w_d (head chain retired).
Both: n_d -> band-2 bc<lc>, s_d -> band-1 bc<lc>, bco<lc> -> far band (129.6 hop); equal age per 4-column group by pads.
Reduction (owner / CB 10-16: rs on the S face with bc): near bands (1 / 2) exit into the head-gap lanes L / U, far bands
(0 / 3) into the band gaps; 514-b relay lanes to the port slabs (W: inner channel to the slab W face; E: through the E
port column white space to the slab S / N face, or the inner channel).  native59 <-> d2d_rom in 3 parallel legs.
Writes die_top_htree.json (stations) / die_top_comb.json (comb), q3h[_comb]_sk.json, q3h[_comb]_edges.json.
"""
import json, math, os, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
RES = Path('/home/ubuntu/wt/q-dieplan2-1016/results/arch/qwen_split_compute_1014/dieplan2_1016')
VAR = os.environ.get('Q3H_VARIANT', 'stations')
TAG = '' if VAR == 'stations' else '_comb'
HOP = 373.0
G = json.load(open(os.environ.get('Q3H_GRID', str(HERE / 'array_grid.json'))))
HOMES = json.load(open(os.environ.get('Q3H_HOMES', str(RES / 'q3h2-homes.json'))))['homes']
CHN = G['channels']
HG = tuple(CHN['head_gap']); G01, G23 = (tuple(x) for x in CHN['band_gaps'])
YC = (HG[0] + HG[1]) / 2
H0 = G['heads'][0]; HW, HH = H0['w'], H0['h']
SW, SH = 330.0, HH
LANE_L, LANE_U = (HG[0] + H0['y']) / 2, (H0['y'] + HH + HG[1]) / 2
RS_LANE = {0: (G01[0] + G01[1]) / 2, 1: LANE_L, 2: LANE_U, 3: (G23[0] + G23[1]) / 2}
D_BITS, X_BITS, U_BITS = 1567, 516, 514


def rly_frame(bits):
    f = max(30.0, math.ceil(bits * 0.048) + 4.0)        # dense relay (1,567 b ~80 x 80)
    return f, f


def main():
    a0 = json.load(open(SRC / 'q2o3a0_sk.json'))
    geo = json.load(open(SRC / 'geom_q2o3a0_skip.json'))
    contract = json.load(open(HERE / 'cluster_contract.json'))
    cports = {p['port']: p for p in contract['ports']}
    arr = re.compile(r'(t|s|h)_\d+(_\d+)?$')
    BASE = json.load(open(SRC / 'q3h2_sk.json'))         # Q-DIEPLAN3's q3h2 GEN model (relay-skip) on the final grid
    keep = [dict(i) for i in BASE['insts'] if not arr.match(i['n']) and i['m'] != 'qfd_c_b16']
    I0 = {i['n']: i for i in keep}
    cl = {c['n']: dict(c, m='qfd_c_b16') for c in G['clusters']}
    xW_end = max(c['x'] + c['w'] for c in cl.values() if c['side'] == 'W')
    xE0 = min(c['x'] for c in cl.values() if c['side'] == 'E')
    P = {n: I0[n] for n in I0 if n.startswith('sp_port_tiles')}
    W_CH = (xW_end, P['sp_port_tiles_0']['x'])
    E_CH = (P['sp_port_tiles_0_f1']['x'] + P['sp_port_tiles_0_f1']['w'], xE0)
    E_PC = (P['sp_port_tiles_0_f1']['x'], E_CH[0])                         # E port column (white space between slabs)
    sc = 2090.88 / contract['outline_um']['w']

    def mirror_x(c):
        return c['o'] in ('MY', 'R180')

    def flip_y(c):
        return c['o'] in ('MX', 'R180')

    def pin(cn, port):
        c = cl[cn]; p = cports.get(port.rstrip('0123') if port.startswith('bc') else port, None)
        if port[:2] == 'bc':
            lc = int(port[-1]); xm = lc * 522.72 + 261.36; face = 'S' if port.startswith('bc') and not port.startswith('bco') else 'N'
        else:   # rs: moved to the S face (with bc), x range as the contract, scaled to 2,090.88
            a, b = cports['rs']['range_um']; xm = (a + b) / 2 * sc; face = 'S'
        x = c['x'] + (c['w'] - xm if mirror_x(c) else xm)
        if flip_y(c):
            face = {'N': 'S', 'S': 'N'}[face]
        return (x, c['y'] + c['h'] if face == 'N' else c['y'])

    rsmap = {}
    for bb in geo['buses']:
        if bb['b'].startswith('bword_'):
            t, port = bb['e'][0][0], bb['e'][1]
            c, r = (int(q) for q in t.split('_')[1:])
            side = 'W' if c < 24 else 'E'
            g = (23 - c) // 4 if side == 'W' else (c - 24) // 4
            rsmap[f'c16_{side}{g}_{r // 4}'] = dict(bword=bb['b'], node=t, port=port[0], pin=port[1])
    heads = {}
    for h in G['heads']:
        c = int(h['n'].split('_')[1]); side = 'W' if c < 24 else 'E'
        heads[c] = dict(h, m='qfd_xcol_w' if side == 'W' else 'qfd_xcol_e', side=side, g=(23 - c) // 4 if side == 'W' else (c - 24) // 4,
                        lc=c % 4 if side == 'W' else 3 - c % 4, col=c, port_in='e_d' if side == 'W' else 'w_d',
                        port_out='w_d' if side == 'W' else 'e_d')
    sgn = {'W': 1, 'E': -1}
    st, edges = {}, []

    def edge(b, c, n, src, dst, pts, pad=0):
        edges.append(dict(b=b, c=c, n=n, src=list(src), dst=list(dst), path=[[round(p[0], 3), round(p[1], 3)] for p in pts], pad=pad))

    tap = I0['xs_tap']; ty = tap['y'] + tap['h'] / 2
    gap = 522.72 - HW
    for side in 'WE':
        hs = sorted((h for h in heads.values() if h['side'] == side), key=lambda h: -sgn[side] * h['x'])
        port = 'hw_d' if side == 'W' else 'he_d'
        tx = tap['x'] if side == 'W' else tap['x'] + tap['w']
        if VAR == 'comb':
            prev = None
            for h in hs:
                fin = h['x'] + HW if side == 'W' else h['x']           # chain input face (toward the centre)
                if prev is None:            # root word: turn up in the inner channel (W) / port column (E), not over a cluster
                    vx_ = (W_CH[0] + W_CH[1]) / 2 if side == 'W' else E_PC[0] + 540.0
                    edge(f'head_{h["col"]}', 'bcast', D_BITS, ['xs_tap', port], [h['n'], h['port_in']],
                         [(tx, ty), (vx_, ty), (vx_, YC), (fin, YC)])
                else:
                    fo = prev['x'] if side == 'W' else prev['x'] + HW
                    edge(f'head_{h["col"]}', 'bcast', D_BITS, [prev['n'], prev['port_out']], [h['n'], h['port_in']], [(fo, YC), (fin, YC)])
                prev = h
        else:
            prev = None
            for k, h in enumerate(hs):
                x = h['x'] + HW + (gap - SW) / 2 if side == 'W' else h['x'] - (gap - SW) / 2 - SW
                if side == 'E' and k == 0:        # E root in the E port column (the 151-um inner channel carries rs relays)
                    x = E_PC[0] + 300.0
                o = ('MX' if k % 2 == 0 else 'R0') if side == 'W' else ('R180' if k % 2 == 0 else 'MY')
                n = f'st_{side}{k:02d}'
                st[n] = dict(n=n, m='qfd_q3h_bcast_station', x=round(x, 4), y=h['y'], w=SW, h=SH, side=side, k=k, o=o, head=h['n'])
                s_ = st[n]
                din_s = (k % 2 == 0)
                yin = s_['y'] if din_s else s_['y'] + SH
                xin = s_['x'] + SW * (0.75 if side == 'W' else 0.25)
                if prev is None:
                    edge(f'q3h_bc_{side}_root', 'bcast', D_BITS, ['xs_tap', port], [n, 'd_in'], [(tx, ty), (xin, ty), (xin, yin)])
                else:
                    p_ = st[prev]
                    lane = LANE_L if din_s else LANE_U
                    pox = p_['x'] + SW * (0.25 if side == 'W' else 0.75)
                    edge(f'q3h_bc_{side}{k:02d}_t', 'bcast', D_BITS, [prev, 'd_out0'], [n, 'd_in'],
                         [(pox, yin if din_s else yin), (pox, lane), (xin, lane), (xin, yin)])
                hf = h['x'] + HW if side == 'W' else h['x']
                fo = s_['x'] if side == 'W' else s_['x'] + SW
                edge(f'q3h_hd_{h["n"]}', 'bcast', D_BITS, [n, 'd_out1'], [h['n'], h['port_in']], [(fo, YC), (hf, YC)])
                prev = n
    for h in heads.values():
        side, g, lc = h['side'], h['g'], h['lc']
        c1, c2, c0, c3 = (f'c16_{side}{g}_{b}' for b in (1, 2, 0, 3))
        hx = h['x'] + HW / 2
        p2 = pin(c2, f'bc{lc}'); p1 = pin(c1, f'bc{lc}')
        edge(f'q3h_nd_{h["n"]}', 'xslice', X_BITS, [h['n'], 'n_d'], [c2, f'bc{lc}'], [(hx, h['y'] + HH), (p2[0], h['y'] + HH), p2])
        edge(f'q3h_sd_{h["n"]}', 'xslice', X_BITS, [h['n'], 's_d'], [c1, f'bc{lc}'], [(hx, h['y']), (p1[0], h['y']), p1])
        for near, far in ((c1, c0), (c2, c3)):
            edge(f'q3h_bco_{near}_{lc}', 'xslice', X_BITS, [near, f'bco{lc}'], [far, f'bc{lc}'], [pin(near, f'bco{lc}'), pin(far, f'bc{lc}')])

    # ---- reduction: rs on the S face -> lane -> port slab ---------------------------------------------------------------
    def cols(lo, hi, m=30.0):
        xs = []
        for k in range(int(lo // 260), int(hi // 260) + 1):
            x = min(max(k * 260 + 130.0, lo + m), hi - m)
            if lo + m <= x <= hi - m and all(abs(x - q) >= 150.0 for q in xs):
                xs.append(x)
        return xs or [(lo + hi) / 2]
    wlo = max([W_CH[0]] + [s_['x'] + s_['w'] + 5.0 for s_ in st.values() if s_['side'] == 'W' and s_['x'] + s_['w'] > W_CH[0]])
    wcol, ecol = cols(wlo, W_CH[1]), cols(*E_CH)
    # E port column: the halfband / halfres slabs leave ~78-um strips on both sides of the column; one relay column in
    # each strip plus one in the inner channel = three different 260-um windows
    hb = [I0[n] for n in I0 if re.match(r'sp_half(band|res)_[135]$', n)]
    # (the W strip carries the native59 <-> d2d legs past the constant column, so rs words use the E strip only)
    epc = [max(q['x'] + q['w'] for q in hb) + (E_PC[1] - max(q['x'] + q['w'] for q in hb)) / 2]
    if os.environ.get('Q3H_E_WSTRIP', '1') == '1':      # the W strip too (shared with the legs below y ~12.7 mm)
        epc = [E_PC[0] + 62.0] + epc
    cnt, slot = {}, {}

    def pick(lst, key):
        cnt[key] = cnt.get(key, -1) + 1
        return lst[cnt[key] % len(lst)]
    for n, r in sorted(rsmap.items(), key=lambda kv: (kv[1]['port'], kv[1]['pin'])):
        c = cl[n]; side, b = c['side'], c['band']
        p = P[r['port']]; lane = RS_LANE[b]
        sx, sy = pin(n, 'rs')
        k = slot.setdefault(r['port'], 0); slot[r['port']] += 1
        if p['y'] + 40 <= lane <= p['y'] + p['h'] - 40:
            px = p['x'] if side == 'W' else p['x'] + p['w']
            pts = [(sx, sy), (sx, lane), (px, lane)]
        elif side == 'W':
            x = pick(wcol, ('W', 'all')); py = p['y'] + 100.0 + 150.0 * k
            pts = [(sx, sy), (sx, lane), (x, lane), (x, py), (p['x'], py)]
        else:
            # E: through the port-column white space to the slab's S (above) / N (below) face, unless another slab
            # sits between: then the inner channel to the slab's E face
            above = p['y'] > lane
            between = [q for q in P.values() if q['x'] > 19000 and q is not p and
                       (lane < q['y'] < p['y'] if above else p['y'] + p['h'] < q['y'] + q['h'] < lane)]
            if not between:
                x = pick(epc + ecol, ('E', 'all'))
                if x < p['x'] + p['w']:
                    py = p['y'] if above else p['y'] + p['h']
                    pts = [(sx, sy), (sx, lane), (x, lane), (x, py)]
                else:
                    py = p['y'] + 100.0 + 150.0 * k
                    pts = [(sx, sy), (sx, lane), (x, lane), (x, py), (p['x'] + p['w'], py)]
            else:
                x = pick(ecol, ('Ec', 'all')); py = p['y'] + 100.0 + 150.0 * k
                pts = [(sx, sy), (sx, lane), (x, lane), (x, py), (p['x'] + p['w'], py)]
        edge(f'q3h_rs_{n}', 'rsum', U_BITS, [n, 'rs'], [r['port'], r['pin']], pts)
        edges[-1]['replaces'] = r['bword']
    n59, d2d = I0['native59'], I0['d2d_rom']
    legs = []
    crom_top = max(I0[f'crom_g_{k}']['y'] + I0[f'crom_g_{k}']['h'] for k in range(8))
    su = I0['sp_su64_sfu']
    for k, (b, bits, fwd) in enumerate((('lnk_native_tx_payload', 548, True), ('lnk_x3', 524, True), ('lnk_rx_payload', 548, False))):
        xu = E_PC[0] + 20.0 + 25.0 * k
        yj = crom_top + 50.0 + 45.0 * k
        xv = su['x'] + su['w'] + 90.0 + 150.0 * k
        pts = [(n59['x'] + n59['w'], n59['y'] + 120.0 + 120.0 * k), (xu, n59['y'] + 120.0 + 120.0 * k), (xu, yj), (xv, yj),
               (xv, d2d['y'] - 60.0 - 50.0 * k), (d2d['x'] + 100.0 + 120.0 * k, d2d['y'] - 60.0 - 50.0 * k), (d2d['x'] + 100.0 + 120.0 * k, d2d['y'])]
        if fwd:
            edge(b, 'spine_local', bits, ['native59', b], ['d2d_rom', b], pts)
        else:
            edge(b, 'spine_local', bits, ['d2d_rom', b], ['native59', b], pts[::-1])
        edges[-1]['replaces'] = b
        legs.append(b)

    # ---- relays ------------------------------------------------------------------------------------------------------
    blocks = keep + list(cl.values()) + list(st.values()) + list(heads.values())
    centre_ok = {'sp_su64_sfu'} | {n for n in I0 if re.match(r'(cbuf_g|crom_g)_\d$', n)}

    def ov(a, b, m=0.5):
        return a['x'] < b['x'] + b['w'] - m and b['x'] < a['x'] + a['w'] - m and a['y'] < b['y'] + b['h'] - m and b['y'] < a['y'] + a['h'] - m

    def seglen(pts):
        return sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(pts, pts[1:]))

    def at(pts, s):
        for p, q in zip(pts, pts[1:]):
            L = abs(q[0] - p[0]) + abs(q[1] - p[1])
            if s <= L or q is pts[-1]:
                f = 0 if L == 0 else min(1.0, s / L)
                return p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f
            s -= L
    relays, occupied, feed = [], [], []
    for e in edges:
        pts = e['path']; L = seglen(pts); e['relays'] = []; prev_end = 0.0; k = 0; hl = []
        fw, fh = rly_frame(e['n']); hf = fw / 2.0
        while L - prev_end > HOP:
            k += 1; placed = None; s0 = prev_end + HOP + hf
            while s0 > prev_end + hf + 1.0:
                x, y = at(pts, s0)
                r = dict(n=f"rly_{e['b']}_{k}", m=f"qfd_rly_{e['n']}", x=round(x - fw / 2, 3), y=round(y - fh / 2, 3), w=fw, h=fh, s=s0)
                hit = [b['n'] for b in blocks if ov(r, b)] + [o['n'] for o in occupied if ov(r, o, 0.0)]
                if not hit:
                    placed = r; break
                if set(hit) <= centre_ok:
                    r['feedthrough'] = sorted(set(hit)); placed = r; break
                s0 -= 3.0
            if placed is None:
                s0 = prev_end + HOP + hf; x, y = at(pts, s0)
                placed = dict(n=f"rly_{e['b']}_{k}", m=f"qfd_rly_{e['n']}", x=round(x - fw / 2, 3), y=round(y - fh / 2, 3), w=fw, h=fh, s=s0, unresolved=True)
            hl.append(placed['s'] - hf - prev_end); prev_end = placed['s'] + hf
            occupied.append(placed); e['relays'].append(placed)
        hl.append(L - prev_end)
        e['hop_max'] = round(max(hl), 1); e['route_um'] = round(L, 1); e['stages'] = len(e['relays']) + 1
        relays += e['relays']; feed += [r for r in e['relays'] if r.get('feedthrough')]

    # ---- equal age per 4-column group ------------------------------------------------------------------------------------
    by_dst = {e['dst'][0]: e for e in edges if e['c'] == 'bcast'}

    def arrive(n):
        e = by_dst[n]
        return e['stages'] + e['pad'] + (0 if e['src'][0] == 'xs_tap' else arrive(e['src'][0]))
    raw = {h['n']: arrive(h['n']) for h in heads.values()}
    pad_head = {}
    for side in 'WE':
        for g in range(6):
            hg = [h['n'] for h in heads.values() if h['side'] == side and h['g'] == g]
            tm = max(raw[x] for x in hg)
            for x in hg:
                pad_head[x] = tm - raw[x]
    # pads sit on the head's two 516-b outputs (n_d / s_d): a chain variant cannot delay a head's input without delaying
    # every head behind it; equal for both variants
    for e in edges:
        if e['c'] == 'xslice' and e['src'][1] in ('n_d', 's_d'):
            e['pad'] = pad_head[e['src'][0]]
    head_age = {x: raw[x] + pad_head[x] for x in raw}

    SPORTS = {'d_in': dict(dir='input', bits=D_BITS, face='N', note='from the inner station via lane U (MX / R180: S face, lane L)'),
              'd_out0': dict(dir='output', bits=D_BITS, face='S', note='to the outer station via lane L (MX / R180: N face, lane U)'),
              'd_out1': dict(dir='output', bits=D_BITS, face='W', note="this station's head e_d / w_d"),
              'ck': dict(dir='input', bits=1, face='E'), 'rst_n': dict(dir='input', bits=1, face='E')}
    used = {tuple(e['src']) for e in edges} | {tuple(e['dst']) for e in edges}
    out = dict(
        schema=f'q3h die-top tree v5 ({VAR}) on the FINAL grid (Q-DIEPLAN3-HT 2026-10-16)', variant=VAR, hop_um=HOP,
        geometry=dict(die=[G['die']['w'], G['die']['h']], head_gap=HG, band_gaps=[G01, G23], lane_L=LANE_L, lane_U=LANE_U,
                      rs_lanes=RS_LANE, w_inner_channel=W_CH, e_inner_channel=E_CH, e_port_column=E_PC,
                      pins='bc<lc>/bco<lc> at the local column centre; rs on the S face at the contract x range scaled to 2,090.88 (provisional until CB re-issues)'),
        hook_notes=['cluster names c16_<side><g>_<band>, heads h_<col> at the grid sites (qfd_xcol_w / _e)',
                    'rsum edges REPLACE bword_<k>; spine_local legs replace the native59<->d2d buses of the same id',
                    'pad on n_d / s_d edges: registers that put the 4 heads of a group on the same edge (CB: equal-age bc words)',
                    'relays: model sites, face to face <= 373 um, no overlap; FEEDTHROUGH sites lie on a C_CENTRE block'],
        heads=[{k: h[k] for k in ('n', 'm', 'x', 'y', 'w', 'h', 'side', 'g', 'lc', 'col')} | dict(input=h['port_in'], age=head_age[h['n']], pad=pad_head[h['n']]) for h in heads.values()],
        clusters=[{k: c[k] for k in ('n', 'm', 'x', 'y', 'w', 'h', 'o', 'side', 'g', 'band')} | dict(rs_to=rsmap[c['n']]) for c in cl.values()],
        station_master=(dict(m='qfd_q3h_bcast_station', w=SW, h=SH, ports=SPORTS, kit='shared_station_kit.json') if st else None),
        stations=[dict(n=s['n'], m=s['m'], x=s['x'], y=s['y'], w=s['w'], h=s['h'], o=s['o'], head=s['head'],
                       children=[e['dst'][0] for e in edges if e['src'][0] == s['n']],
                       unused_ports=[p for p in SPORTS if (s['n'], p) not in used and SPORTS[p]['bits'] > 1]) for s in st.values()],
        edges=[{k: e[k] for k in ('b', 'c', 'n', 'src', 'dst', 'path', 'route_um', 'stages', 'pad', 'hop_max')}
               | ({'replaces': e['replaces']} if 'replaces' in e else {})
               | dict(relays=[[r['x'], r['y'], r['w'], r['h']] + (['FEEDTHROUGH:' + '+'.join(r['feedthrough'])] if r.get('feedthrough') else []) for r in e['relays']])
               for e in edges],
        relay_count=len(relays), pad_registers=sum(e['pad'] for e in edges), centre_feedthrough_relays=len(feed),
        unresolved_relays=[r['n'] for r in relays if r.get('unresolved')])
    json.dump(out, open(HERE / ('die_top_htree.json' if VAR == 'stations' else 'die_top_comb.json'), 'w'), indent=1)

    insts = keep + [{k: c[k] for k in ('n', 'm', 'x', 'y', 'w', 'h')} for c in cl.values()] + \
        [{k: h[k] for k in ('n', 'm', 'x', 'y', 'w', 'h')} for h in heads.values()] + \
        [{k: s[k] for k in ('n', 'm', 'x', 'y', 'w', 'h')} for s in st.values()] + \
        [{k: r[k] for k in ('n', 'm', 'x', 'y', 'w', 'h')} for r in relays]
    names = {i['n'] for i in insts}
    buses, dropped = [], 0
    for b, c, bits, eps in BASE['buses']:
        if (c == 'head_chain' and bits > 1) or b.startswith('bword_'):
            continue
        if b in legs and set(eps) == {'native59', 'd2d_rom'}:
            continue
        eps2 = [x for x in eps if not arr.match(x)]
        if len(eps2) < 2:
            continue
        if not all(x in names for x in eps2):
            dropped += 1; continue
        buses.append([b, c, bits, eps2])
    for e in edges:
        ch = [e['src'][0]] + [r['n'] for r in e['relays']] + [e['dst'][0]]
        for k, (a, q) in enumerate(zip(ch, ch[1:])):
            buses.append([f"{e['b']}__r{k}" if len(ch) > 2 else e['b'], e['c'], e['n'], [a, q]])
    json.dump(dict(insts=insts, buses=buses), open(HERE / f'q3h{TAG}_sk.json', 'w'))
    json.dump(dict(variant=VAR, edges={e['b']: dict(stages=e['stages'], pad=e['pad'], route_um=e['route_um'], hop_max=e['hop_max'], src=e['src'], dst=e['dst'], c=e['c']) for e in edges},
                   heads={h['n']: dict(age=head_age[h['n']], raw=raw[h['n']], pad=pad_head[h['n']], side=h['side'], g=h['g'], lc=h['lc']) for h in heads.values()},
                   rsmap=rsmap, dropped_centre_buses=dropped), open(HERE / f'q3h{TAG}_edges.json', 'w'), indent=1)
    allb = keep + list(cl.values()) + list(st.values()) + list(heads.values())
    bad = [(a['n'], b['n']) for i, a in enumerate(allb) for b in allb[i + 1:] if ov(a, b)]
    rl = [r for r in relays if not r.get('feedthrough')]
    bad += [(r['n'], b['n']) for r in rl for b in allb if ov(r, b)]
    print(json.dumps(dict(variant=VAR, heads=len(heads), stations=len(st), relays=len(relays), pads=out['pad_registers'],
                          feedthrough=len(feed), unresolved=len(out['unresolved_relays']), overlaps=bad[:8], n_overlaps=len(bad),
                          hop_max=max(e['hop_max'] for e in edges), max_head_age=max(head_age.values()), dropped_centre_buses=dropped)))


if __name__ == '__main__':
    main()

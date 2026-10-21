#!/usr/bin/env python3
"""S81 release head die H1 unrouted plan (S81-HEAD / HD-FP, 10-21) in the die72 plan schema
(blocks name/master/kind/group/x/y/w/h/reg [+orient]; links i/c/b/d/e/n/endpoint_faces; facts.die_um/physical72; blockages),
built on the hd_floorplan.py placement.  Consumers: dv_route72.py -> dv_station_dirs72.py -> frame_bind/bind table ->
dv_diecase --bind real -> dv_rvcase (as release72/run_die72_g7.sh).

  python3 hd_plan.py build PLACEMENT OUT_PLAN          unrouted plan
  python3 hd_plan.py check ROUTED                      route verdict: failures, stations, bit-mm, longest station hop,
                                                       565-b links must have no station (else they need a relay width)
  python3 hd_plan.py cut ROUTED OUT_JSON               bits per cut vs tracks on the routed hops (limit 0.55)
  python3 hd_plan.py draw PLACEMENT [ROUTED] OUT_PNG   floorplan picture (PNG + SVG)

Link classes ('c'; only 'x_frame' has bind semantics in dv_bind, none is used here):
  chain  tile/spine-node <-> tile on the row-pair chains     spine  spine levels, top U-turn, ctl <-> spine roots
  unit   ctl <-> lane / lep core links                        coll   lane / lep <-> ot_pdie_serdes tx / rx (G7 widths)
Width 'b' = the physical lane (relay / landing master) width, as G7 (e.g. 43-b Engram chain on 276 lanes):
  bus B payload 565 b.  dsfd_dvrlyh_* / dsfd_dvland_* exist for 70/276/512/562/682 b only, so a bus-B link that carries a
  relay station or crosses a clock region rides a 682-b lane (565 payload + 117 declared spare top bits, dv_bind 'lane
  quantisation'); a same-region abutted link (no station, no landing) stays exactly 565 b.  `check` asserts that.
"""
import argparse
import collections
import json
import math
from pathlib import Path

# ------------------------------------------------------------------------------------------------ PORT / WIDTH TABLE
# Real widths from HD-CTL's port contract results/arch/s81_head_1021/ports.json (claude/s81-head-ctl-1021@b4f571642, 4 masters,
# 128 connections; HD-CHAIN 10-21 replaced the HD-FP placeholders).  Per lane key: (lane width, lanes, payload bits).  Lane width
# = a closed relay / landing master width (70/276/512/562/682); payload = the RTL bits the bundle carries (the rest are dv_bind
# lane-quantisation spare top bits).  The RTL port slices per lane are in tools/s81_dv/head72/hd_bind.py.
# LONG LANES ride 276-b lanes: the ctl <-> lane / lep core links are 4.6..12.9 mm (16..36 stations, model landing E 9..18) and
# only the 276 landing has a long (D 8, 6-bit K) closed tile (dsfd_dvland_276l); 562/682/512 landings are D 4 / K <= 7.
BUS_B = 565                     # spec s2: {x512, go, xv, rv, row17, bits32, flt}
LANE_B_RELAY = 682              # closed relay/landing width carrying bus B where a station or a landing is needed
LANES = {
    'chain':          (BUS_B, 1, BUS_B),   # tile.i/o, spo, spr, ctl sn_*/ss_* (565, fixed; 682 lane where a station/landing)
    'ctl_to_lane':    (276, 3, 554),       # ctl {m,h,d}tx_v[k] + {m,h,d}tx_d[553k +: 553] -> lane tx_v / tx_d
    'lane_to_ctl':    (276, 3, 558),       # lane rx_v / rx_d / flt -> ctl {m,h,d}rx_v[k], rx_d[553k +: 553], flt[4k +: 4]
    'ctl_to_lep':     (276, 5, 1150),      # ctl ro 1104 + mu_c 34 + mu_rc 11 + ctl_f 1 -> lep ro / mu_c / mu_rc / sl_f
    'lep_to_ctl':     (276, 5, 1148),      # lep ri 1104 + mu_rt 32 + lw 11 + fault 1 -> ctl ri / mu_rt / lw / lep_f
    'serdes_tx':      (512, 1, 512),       # lane tx -> ot_pdie_serdes.tx (lane beside its SerDes)
    'serdes_rx':      (562, 1, 514),       # ot_pdie_serdes {st, rx} -> lane rx[513:0]
    'serdes_tx_long': (276, 2, 512),       # lep tx<k> -> lk_WN<k> (lep at band height: up to 7.6 mm)
    'serdes_rx_long': (276, 2, 514),       # lk_WN<k> {st, rx} -> lep rx<k>
}
WIDTHS = {k: v[0] for k, v in LANES.items()}
# Peer-endpoint nudges (um along the face) for links whose dv_route72 station spacing (corner-avoid shift) exceeds the 405-um
# reach (station hop <= 400 um): found by a 21.6-um step search (HD-CHAIN 10-21; deterministic, the run script re-routes this plan).
NUDGE = {"c_ln_host1_t_l1": 21.6, "c_ln_draft2_r_l1": 21.6, "c_ln_draft4_t_l2": 21.6}
LEP_SERDES = {'lk_WN0': 0, 'lk_WN1': 1, 'lk_WN2': 2, 'lk_WN3': 3}     # lep lane k <-> SerDes (pair A = 0/1 TX, pair B = 2/3 RX)
RANKS = (253, 253, 252, 252)    # bundles per TP4 rank (spec s1); row base = 128 x bundles of the lower ranks
STUB = 43.2
REACH = 405.0


def seed(b, face, t):
    x, y, w, h = b['x'], b['y'], b['w'], b['h']
    t = min(0.97, max(0.03, t))
    return {'W': (x, y + t * h), 'E': (x + w, y + t * h), 'S': (x + t * w, y), 'N': (x + t * w, y + h)}[face]


def build(pk):
    B = []
    ix = {}
    for b in pk['best']['blocks']:
        ix[b['name']] = len(B)
        B.append({k: b[k] for k in ('name', 'master', 'kind', 'group', 'x', 'y', 'w', 'h', 'reg', 'orient')})
    for b in B:
        if b['name'] in LEP_SERDES:
            b['master'] = 'ot_pdie_serdes_l276'      # same module (ot_pdie_serdes_col); bind row with 2 x 276-b lanes (hd_bind.py)
    by = {b['name']: b for b in B}
    links = []
    names = set()

    def ep(name, port, face, t):
        x, y = seed(by[name], face, t)
        return [ix[name], port, round(x, 4), round(y, 4), 'box']

    def link(i, c, payload, src, dst, n, relay_ok=True, payload_b=None):
        assert i not in names, i
        names.add(i)
        (s, fs), (d, fd) = src, dst
        sb, db = B[s[0]], B[d[0]]
        est = abs(s[2] - d[2]) + abs(s[3] - d[3])
        b = payload
        if payload == BUS_B and (sb['group'] != db['group'] or est > 300.0):
            b = LANE_B_RELAY
        l = dict(i=i, c=c, b=b, d=1, e=[s, d], n=n, endpoint_faces=[fs, fd])
        if b != payload:
            l['payload_b'] = payload
        if payload_b is not None:
            l['payload_b'] = payload_b
        if i in NUDGE:
            k = 0 if B[s[0]]['name'] != 'ctl' and B[d[0]]['name'] == 'ctl' else 1
            e, f, bb = l['e'][k], l['endpoint_faces'][k], B[l['e'][k][0]]
            if f in 'WE':
                e[3] = round(min(bb['y'] + bb['h'] - 5, max(bb['y'] + 5, e[3] + NUDGE[i])), 4)
            else:
                e[2] = round(min(bb['x'] + bb['w'] - 5, max(bb['x'] + 5, e[2] + NUDGE[i])), 4)
            l['nudge_um'] = NUDGE[i]
        links.append(l)
        return l

    def E(name, port, face, t=0.5):
        return ep(name, port, face, t), face

    # ------------------------------------------------------------------ spine + chains
    lv = collections.defaultdict(int)
    for ch in pk['chains']:
        lv[ch['half']] = max(lv[ch['half']], ch['level'] + 1)
    for half in ('N', 'S'):
        up, dn = ('N', 'S') if half == 'N' else ('S', 'N')     # 'up' = away from the ctl
        top = lv[half] - 1
        for L in range(lv[half]):
            spo, spr = f'spo_{half}{L}', f'spr_{half}{L}'
            if L == 0:
                cf = 'N' if half == 'N' else 'S'
                ct = (by[spo]['x'] + by[spo]['w'] / 2 - by['ctl']['x']) / by['ctl']['w']
                cr = (by[spr]['x'] + by[spr]['w'] / 2 - by['ctl']['x']) / by['ctl']['w']
                link(f'sp_o_{half}0', 'spine', BUS_B, E('ctl', f's{half.lower()}_o', cf, ct), E(spo, 'i', dn),
                     f'ctl {"sn" if half == "N" else "ss"}_o -> spine root (x/go + null best), region crossing')
                link(f'sp_r_{half}0', 'spine', BUS_B, E(spr, 'o', dn), E('ctl', f's{half.lower()}_i', cf, cr),
                     f'spine return root -> ctl {"sn" if half == "N" else "ss"}_i, region crossing')
            else:
                link(f'sp_o_{half}{L}', 'spine', BUS_B, E(f'spo_{half}{L - 1}', 'o', up), E(spo, 'i', dn), 'spo level -> level (x/go/best)')
                link(f'sp_r_{half}{L}', 'spine', BUS_B, E(spr, 'o', dn), E(f'spr_{half}{L - 1}', 'i', up), 'spr level -> level (argmax)')
            if L == top:
                link(f'sp_u_{half}', 'spine', BUS_B, E(spo, 'o', up), E(spr, 'i', up), 'spine U-turn: top spo.o -> top spr.i')
    for ch in pk['chains']:
        half, L, side, seq = ch['half'], ch['level'], ch['side'], ch['tiles']
        spo, spr = f'spo_{half}{L}', f'spr_{half}{L}'
        stem = f'ch_{half}{L:02d}{side}'

        def tin(nm):
            return E(nm, 'i', 'W' if by[nm]['orient'] == 'R0' else 'E')

        def tout(nm):
            return E(nm, 'o', 'E' if by[nm]['orient'] == 'R0' else 'W')
        link(f'{stem}_00', 'chain', BUS_B, E(spo, 'o' + side.lower(), side), tin(seq[0]), f'{spo}.o{side.lower()} -> chain head')
        for k in range(len(seq) - 1):
            uturn = seq[k][-2] != seq[k + 1][-2]
            link(f'{stem}_{k + 1:02d}', 'chain', BUS_B, tout(seq[k]), tin(seq[k + 1]),
                 'row-pair U-turn tile -> tile' if uturn else 'tile -> tile (x/go forward, best)')
        link(f'{stem}_{len(seq):02d}', 'chain', BUS_B, tout(seq[-1]), E(spr, 'i' + side.lower(), side), f'chain tail -> {spr}.i{side.lower()}')
    # ------------------------------------------------------------------ ctl <-> lanes / lep, lanes / lep <-> SerDes
    band = pk['band']
    ctl = by['ctl']
    peers = {'W': [], 'E': []}
    for nm, ln in pk['lanes'].items():
        b = by[nm]
        side = 'W' if b['x'] < ctl['x'] else 'E'
        outer, inner = ('W', 'E') if side == 'W' else ('E', 'W')
        if b['y'] + b['h'] <= band[0]:
            cface = 'N'
        elif b['y'] >= band[1]:
            cface = 'S'
        else:
            cface = inner
        tc = (0.80 if side == 'W' else 0.20) if cface in 'NS' else 0.5
        peers[side].append((b['y'] + b['h'] / 2, nm, [(f'{nm}_t', 'ctl_to_lane', 'core_i', cface, tc - 0.08), (f'{nm}_r', 'lane_to_ctl', 'core_o', cface, tc + 0.08)]))
        sdn = ln['serdes']; s = by[sdn]
        for port, key, lt in (('tx', 'serdes_tx', 0.35), ('rx', 'serdes_rx', 0.65)):
            py = b['y'] + lt * b['h']
            st = (py - s['y']) / s['h']
            if key == 'serdes_tx':
                link(f'lt_{sdn}', 'coll', WIDTHS[key], E(nm, 'tx', outer, lt), E(sdn, 'tx', inner, st), f'{ln["role"]} lane tx -> {sdn}', payload_b=512)
            else:
                link(f'lr_{sdn}', 'coll', WIDTHS[key], E(sdn, 'rx', inner, st), E(nm, 'rx', outer, lt), f'{sdn} rx -> {ln["role"]} lane', payload_b=514)
    lep = by['lep']
    peers['W'].append((lep['y'] + lep['h'] / 2, 'lep', [('lep_t', 'ctl_to_lep', 'core_i', 'E', 0.35), ('lep_r', 'lep_to_ctl', 'core_o', 'E', 0.65)]))
    for sdn, k in LEP_SERDES.items():
        s = by[sdn]
        if s['y'] + s['h'] <= lep['y']:
            lf, lt0, sf_t = 'S', 0.15 + 0.1 * (k % 2), 0.97
        elif s['y'] >= lep['y'] + lep['h']:
            lf, lt0, sf_t = 'N', 0.15 + 0.3 * (k % 2), 0.03
        else:
            lf, lt0, sf_t = 'W', 0.45, None
        def lep_ep(port, dt):
            return E('lep', port, lf, lt0 + dt)
        def sd_ep(port, dt):
            if sf_t is None:
                py = lep['y'] + (lt0 + dt) * lep['h']
                return E(sdn, port, 'E', (py - s['y']) / s['h'])
            return E(sdn, port, 'E', sf_t + (dt if sf_t < 0.5 else -dt) * 0.1)
        for j in range(LANES['serdes_tx_long'][1]):
            link(f'lt_{sdn}_l{j}', 'coll', WIDTHS['serdes_tx_long'], lep_ep(f'tx{k}', 0.02 * j), sd_ep('tx', 0.02 * j),
                 f'lep lane {k} tx -> {sdn} (pair {"A" if k < 2 else "B"}), 276-b lane {j}', payload_b=LANES['serdes_tx_long'][2])
            link(f'lr_{sdn}_l{j}', 'coll', WIDTHS['serdes_rx_long'], sd_ep('rx', 0.1 + 0.02 * j), lep_ep(f'rx{k}', 0.1 + 0.02 * j),
                 f'{sdn} rx -> lep lane {k} (pair {"A" if k < 2 else "B"}), 276-b lane {j}', payload_b=LANES['serdes_rx_long'][2])
    for side in 'WE':
        ports = [p + (nm, j) for _, nm, ps in sorted(peers[side]) for p in ps for j in range(LANES[p[1]][1])]
        n = len(ports)
        for jj, (cport, key, pport, pface, pt, nm, j) in enumerate(ports):
            t = 0.05 + 0.9 * (jj + 0.5) / n
            nl = LANES[key][1]
            cep = E('ctl', cport, side, t)
            pep = E(nm, pport, pface, pt + 0.16 * (j - (nl - 1) / 2) / nl)
            role = pk['lanes'][nm]['role'] if nm in pk['lanes'] else 'lep'
            lid = f'c_{cport}_l{j}' if nl > 1 else f'c_{cport}'
            if key.startswith('ctl_to'):
                link(lid, 'unit', WIDTHS[key], cep, pep, f'ctl -> {nm} ({role}) core lane {j}/{nl}, region crossing (landing)', payload_b=LANES[key][2])
            else:
                link(lid, 'unit', WIDTHS[key], pep, cep, f'{nm} ({role}) core -> ctl lane {j}/{nl}, region crossing (landing)', payload_b=LANES[key][2])
    # ------------------------------------------------------------------ facts
    W, H = pk['die']
    bases, acc = [], 0
    for n in RANKS:
        bases.append(acc * 128); acc += n
    straps = {}
    for b in pk['best']['blocks']:
        if b['master'] == 'ot_s81hd_tile':
            k = b['bundle']
            straps[b['name']] = dict(bundle=k, row0_by_rank=[bases[r] + 128 * k for r in range(4)],
                                     ten_by_rank=[1 if k < RANKS[r] else 0 for r in range(4)])
    assert max(v for s in straps.values() for v in s['row0_by_rank']) < (1 << 17)
    orient = {b['name']: b['orient'] for b in B if b['orient'] != 'R0'}
    facts = dict(
        die_um=[W, H], die_mm2=round(W * H / 1e6, 3), reticle_um=pk['reticle'],
        cluster_pitch_um=W,                     # non-'cl' groups (SerDes 'edge') -> one region edge0
        bus_b=dict(payload=BUS_B, relay_lane=LANE_B_RELAY, fields='[511:0] x, [512] go, [513] xv, [514] rv, [531:515] row, [563:532] bits, [564] flt'),
        widths=WIDTHS, lanes={k: dict(lane=v[0], lanes=v[1], payload=v[2]) for k, v in LANES.items()},
        widths_source='results/arch/s81_head_1021/ports.json (HD-CTL b4f571642): real widths, no placeholders (HD-CHAIN 10-21)',
        instance_orientations=orient,
        orientation_note='bind table instance_orientations (frame_bind ORIENT_BITS): tiles R0 = i W / o E (flow east), MY = flow west; '
                         'S-half spine nodes MX (i on N, o on S); plan endpoint faces are PHYSICAL (rvcase reprojects view pins)',
        tile_straps=dict(rank_bundles=list(RANKS), rank_row_base=bases, rule='row0 = rank row base + 128 x bundle; ten = bundle < rank bundles',
                         per_instance=straps),
        regions=dict(rule='group = clock region: cl<H><L>W = spo + W chain, cl<H><L>E = spr + E chain, clctl, cllep, cl_<lane>; SerDes edge',
                     crossings='every cross-region link is a landing-plan row (fixed-latency ring, no flow control)'),
        chains=[dict(half=c['half'], level=c['level'], side=c['side'], n=len(c['tiles'])) for c in pk['chains']],
        empty_slots=pk['empty_slots'], spec_reconciliation=pk['spec_reconciliation'], floorplan_params=pk['params'],
        physical72=dict(owner_adopted=False, design='S81 HEAD H1 (HD-FP 10-21)', floorplan='tools/s81_dv/head72/hd_floorplan.py',
                        endpoint_geometry='plan face seeds; existing rvcase kit/view pin reprojection required', routing='PENDING',
                        calendar='PENDING head calendar (L5B-CAL successor)'))
    return dict(facts=facts, blocks=B, links=links, blockages=[dict(r) for r in pk.get('reserves', [])])


def stations_hops(l):
    L = l.get('L', 0.0)
    pts = [0.0]
    # station positions along the path: recover from 'sp' by walking the hops
    acc = 0.0
    for x1, y1, x2, y2, _ in l['h']:
        seg = abs(x2 - x1) + abs(y2 - y1)
        for sx, sy in l.get('sp', []):
            if min(x1, x2) - 1e-3 <= sx <= max(x1, x2) + 1e-3 and min(y1, y2) - 1e-3 <= sy <= max(y1, y2) + 1e-3:
                d = acc + abs(sx - x1) + abs(sy - y1)
                if all(abs(d - q) > 1e-3 for q in pts):
                    pts.append(d)
        acc += seg
    pts = sorted(pts) + [L]
    return [b - a for a, b in zip(pts, pts[1:])]


def check(routed):
    p = json.load(open(routed)); f = p['facts']['physical72']
    hops = []
    bad565 = []
    for l in p['links']:
        hs = stations_hops(l)
        hops.append((max(hs), l['i'], l['b'], l['s'], l['L']))
        if l['b'] == BUS_B and l['s']:
            bad565.append(l['i'])
    hops.sort(reverse=True)
    by_c = collections.defaultdict(lambda: [0, 0, 0.0])
    for l in p['links']:
        r = by_c[l['c']]; r[0] += 1; r[1] += l['s']; r[2] += l['L'] * l['b'] / 1000
    rec = dict(routing=f['routing'], failures=len(f['routing_failures']), links=len(p['links']), stations=f['relay_station_count'],
               bit_mm=round(p['facts']['bit_mm'], 1), longest_station_hop_um=round(hops[0][0], 1),
               over_reach=[h[1] for h in hops if h[0] > REACH], bus565_with_station=bad565,
               longest_hops=[dict(link=h[1], hop_um=round(h[0], 1), b=h[2], stations=h[3], L=h[4]) for h in hops[:8]],
               longest_links=[dict(link=l['i'], L=l['L'], stations=l['s'], b=l['b']) for l in sorted(p['links'], key=lambda l: -l['L'])[:8]],
               by_class={c: dict(links=v[0], stations=v[1], bit_mm=round(v[2], 1)) for c, v in sorted(by_c.items())},
               station_widths=dict(collections.Counter(f"{l['b']}" for l in p['links'] for _ in range(l['s']))))
    print(json.dumps(rec, indent=1))
    assert not f['routing_failures'] and not bad565 and not rec['over_reach'], 'ROUTE CHECK FAIL'
    return rec


def cut(routed, out, tpu=6.9, step=43.2, window=648.0):
    """Bits crossing straight cut lines (every `step`) vs routing tracks: vertical cuts are crossed by horizontal wires
    (3 H layers), horizontal cuts by vertical wires (2 V layers), 6.9 tracks/um/layer (spec s5 constants).  Full-length cuts
    and the densest `window`-long piece of every cut line (local face/channel concentration)."""
    p = json.load(open(routed)); W, H = p['facts']['die_um']
    hs, vs = [], []                       # horizontal segs (y, x0, x1, b), vertical segs (x, y0, y1, b)
    for l in p['links']:
        for x1, y1, x2, y2, b in l['h']:
            if abs(y1 - y2) < 1e-6 and abs(x2 - x1) > 1e-6:
                hs.append((y1, min(x1, x2), max(x1, x2), b))
            elif abs(x2 - x1) < 1e-6 and abs(y2 - y1) > 1e-6:
                vs.append((x1, min(y1, y2), max(y1, y2), b))
    res = {}
    for kind, segs, span, other, layers in (('vertical', hs, W, H, 3), ('horizontal', vs, H, W, 2)):
        best_full = (0, 0, 0); best_win = (0, 0, 0, 0)
        c = step
        while c < span:
            cross = [(pos, b) for pos, a0, a1, b in segs if a0 < c < a1]
            bits = sum(b for _, b in cross)
            r = bits / (other * tpu * layers)
            if r > best_full[0]:
                best_full = (r, c, bits)
            if cross:
                cross.sort()
                j = 0; s = 0
                for i in range(len(cross)):
                    s += cross[i][1]
                    while cross[i][0] - cross[j][0] > window:
                        s -= cross[j][1]; j += 1
                    rw = s / (window * tpu * layers)
                    if rw > best_win[0]:
                        best_win = (rw, c, s, cross[j][0])
            c += step
        res[kind] = dict(layers=layers, full=dict(ratio=round(best_full[0], 3), at_um=round(best_full[1], 1), bits=best_full[2], tracks=round(other * tpu * layers)),
                         window=dict(ratio=round(best_win[0], 3), at_um=round(best_win[1], 1), from_um=round(best_win[3], 1), bits=best_win[2],
                                     window_um=window, tracks=round(window * tpu * layers)))
    res['limit'] = 0.55
    res['pass'] = all(res[k][m]['ratio'] <= 0.55 for k in ('vertical', 'horizontal') for m in ('full', 'window'))
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return res


def draw(placement, routed, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    pk = json.load(open(placement)); W, H = pk['die']
    col = {'tile': '#9ecae1', 'spine': '#fd8d3c', 'ctl': '#e6550d', 'lep': '#31a354', 'lane': '#74c476', 'link': '#bcbddc'}
    fig, ax = plt.subplots(figsize=(W / 1000 * 0.9, H / 1000 * 0.9), dpi=110)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec='k'))
    for b in pk['best']['blocks']:
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fc=col[b['kind']], ec='k', lw=0.3))
        if b['kind'] != 'tile':
            ax.text(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2, b['name'].replace('lk_', '').replace('ln_', ''), ha='center', va='center',
                    fontsize=4 if b['kind'] in ('spine',) else 6, rotation=90 if b['h'] > 2 * b['w'] else 0)
        else:
            ax.text(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2, f"{b['bundle']}{'<' if b['orient'] == 'MY' else '>'}", ha='center', va='center', fontsize=4)
    for r in pk.get('reserves', []):
        ax.add_patch(Rectangle((r['x'], r['y']), r['w'], r['h'], fc='#dddddd', ec='none', hatch='////', lw=0))
    if routed:
        p = json.load(open(routed))
        cc = {'chain': '#08519c', 'spine': '#a50f15', 'unit': '#6a51a3', 'coll': '#006d2c'}
        for l in p['links']:
            for x1, y1, x2, y2, _ in l['h']:
                ax.plot([x1, x2], [y1, y2], color=cc.get(l['c'], 'k'), lw=0.35 if l['c'] == 'chain' else 0.6)
            for sx, sy in l.get('sp', []):
                ax.plot([sx], [sy], 'o', ms=1.2, color='k')
    ax.set_xlim(-200, W + 200); ax.set_ylim(-200, H + 200); ax.set_aspect('equal')
    ax.set_title(f'S81 head die H1  {W / 1000:.2f} x {H / 1000:.2f} mm  ({W * H / 1e6:.0f} mm2)  tiles: bundle index, > flow E, < flow W; dots = relay stations', fontsize=8)
    fig.tight_layout(); fig.savefig(out); fig.savefig(str(Path(out).with_suffix('.svg')))
    print('DRAWN', out)


def main():
    a = argparse.ArgumentParser(); sp = a.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('build'); s.add_argument('placement'); s.add_argument('out')
    s = sp.add_parser('check'); s.add_argument('routed')
    s = sp.add_parser('cut'); s.add_argument('routed'); s.add_argument('out')
    s = sp.add_parser('draw'); s.add_argument('placement'); s.add_argument('routed', nargs='?'); s.add_argument('out')
    v = a.parse_args()
    if v.cmd == 'build':
        p = build(json.load(open(v.placement)))
        Path(v.out).write_text(json.dumps(p, indent=1))
        print(json.dumps(dict(blocks=len(p['blocks']), links=len(p['links']), die=p['facts']['die_um'],
                              by_class=dict(collections.Counter(f"{l['c']}:{l['b']}" for l in p['links'])))))
    elif v.cmd == 'check':
        check(v.routed)
    elif v.cmd == 'cut':
        cut(v.routed, v.out)
    else:
        if v.out is None:
            v.out, v.routed = v.routed, None
        draw(v.placement, v.routed, v.out)


if __name__ == '__main__':
    main()

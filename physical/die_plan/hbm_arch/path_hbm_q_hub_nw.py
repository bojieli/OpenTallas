#!/usr/bin/env python3
"""PATH-HBM/HUBNW (2026-10-25): plan step joint_reach90 -> q_hub_nw (one complete HBM TKM path through NW_hub).

    python3 path_hbm_q_hub_nw.py BASE/die_plan.json --out OUTDIR

What it does (COORD 10-25: q_hub_nw ACCEPTED, q3 pieces at the W end of NW_hub; TKM-only L74 = 2-beat bus):
  * partition_types['q_hub_nw'] = copy of q_hub; NW_hub.type = q_hub_nw (NE_hub keeps q_hub).
  * u_hb_coll_Q_body (q2 body) -> q3 split pieces body_core / edge / vm (ot_hfd_coll_q3_*_core, main a63baaa9a0) at
    the W end; ring_ag / reduce keep the q2 masters and places.
  * TX soft site u_tkx_tx_Q = ot_hbm_tkx_2beat_tx (codex/hbm-token-1309 a64589a097; 11467 cells, Codex PLAN FIRM soft
    site [501.12,1105.92] 198.72^2).  Sources (body_core pins facing TX): the EXACT 2180-bit flit projection of
    codex/hbm-hub-1309 d59a276772 (g_qout[k] = 32-b CHUNK k; TKM dest 11..14 = bits [d*32+:32] of chunks 0..15,
    chunk16 = compacted dests {0..6,11..15} x 32, chunk17 = compacted bit per dest) + the upipe_SL cfg/start/slot
    ports; every other qout bit faces its own dest class (0-2 edge link wr_flit, 3-6 del buses, 7-10 vm writer,
    15 reduce).
  * L74 = 1171-bit beat bus (2 static beats, slot from boot_start, no beat-index pin): q_hub_nw.L74_o, ports
    L74_0/L74_1, NW_b101 ft slot (new type q_b101_nw: q_b101 with L74x1 1171; NE_b101 keeps the 2341 slot for L74m)
    and root.L74_i are 1171 wide; lane L74 beats 2 / word_bits 2341 / beat_index_bits 0.  Root seam windows unchanged.
  * root: RX soft site u_tkx_rx_SW = ot_hbm_tkx_2beat_rx (13686 cells, [112.32,1010.88] 51.84x345.6, LINK_STAGES 2)
    between the L74_i window and u_tkm_SW_root; the old name-based L74_i chains (u_col_idx / u_hb_idx__* / argmax,
    the pre-TKM placeholder) are removed with their core_conns entries.
  * return: L13_i[571:0] = {fault, done, busy, w_data512, w_mask16, w_addr40, w_v} -> vm writer_tkw_* (569 b) and
    body_core tkx_{busy,done,fault}; L13 is the direct root->NW_hub E-face port (L12 carries no TKM bits).
  * internal_stations (R3-INTERNAL, hops <= 360 um, cores_b2.RelayRouter, TX box is an obstacle).
  * HUBNW2 (COORD 10-25 ruling 3, no TKM spill onto the body W face): W end re-floorplanned edge | body with TX on the
    body N face (see PLACE); _place_prio reserves a body N-face segment under TX for all TKM source bits (asserted: one
    face, equal station count) and an edge W-face segment at the link windows.  --edge-w explores the edge strip width.
"""
import argparse, collections, copy, json, math, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, 'B2p_inputs', 'q_hub_nw')
sys.path.insert(0, HERE)
import cores_b2 as cb                                                     # noqa: E402
sys.path.insert(0, os.path.join(cb.ROOT, 'tools', 'die_plan'))
import schema as S                                                        # noqa: E402
import check as CK                                                        # noqa: E402

G = 8.64
HOP = 360.0
PIN_MAX = 5.6
OLD = 'u_hb_coll_Q_body'
BODY, EDGE, VM = 'u_hb_coll_Q_body_core', 'u_hb_coll_Q_edge', 'u_hb_coll_Q_vm'
RING, RED = 'u_hb_coll_Q_ring_ag', 'u_hb_coll_Q_reduce'
TX, RX, TKM_ROOT = 'u_tkx_tx_Q', 'u_tkx_rx_SW', 'u_tkm_SW_root'
SRC = 'q3 split main a63baaa9a0; tkx ABI codex/hbm-token-1309 a64589a097; projection codex/hbm-hub-1309 d59a276772'
CELLS = {BODY: 229064, EDGE: 82038, VM: 72841, RING: 147960, RED: 129647}
MODS = {BODY: 'ot_hfd_coll_q3_body_core', EDGE: 'ot_hfd_coll_q3_edge_core', VM: 'ot_hfd_coll_q3_vm_core'}
REGCLASS = {BODY: 'regclass_body_core.json', EDGE: 'regclass_edge_core.json', VM: 'regclass_vm_core.json'}
FACE_BAND, CHAN = 34.56, 17.28
# HUBNW2 (10-25, COORD ruling 3: no TKM spill onto the body W face): W end = edge | body, TX on the body N face.
#   edge   = tall W-band strip: W face on the hub W link windows (L51/L52/L101/L126, y 946-1202), E face face-to-face
#            with the body W face (0-station core-core cut, ~8.4k bits both ways).
#   body   = between the edge and u_hb_coll_Q_reduce (x <= 820.8), top one channel below the FIRM TX site, so the TX
#            S face sits 17.28 um above the body N face; the TKM source pins get a reserved N-face segment centred
#            under TX (every TKM bit <= HOP from TX -> the SAME station count, 0, for all L74 source bits).
#   vm     = unchanged (NE, next to its kq / rs leaves).
EDGE_W = 190.08
BODY_TOP = 1105.92 - 17.28                     # TX origin y - CHAN
BODY_X1 = 838.08 - 17.28                       # u_hb_coll_Q_reduce x - CHAN
EDGE_Y0 = 250.56                               # edge spans y 250.56..1304.64: W face covers the link windows


def _place(edge_w=EDGE_W):
    bx0 = FACE_BAND + edge_w + CHAN
    bh = round(BODY_TOP - FACE_BAND, 4)
    return {BODY: ((bx0, FACE_BAND), (round(BODY_X1 - bx0, 4), bh)),
            EDGE: ((FACE_BAND, EDGE_Y0), (edge_w, bh)),
            VM: ((1296.0, 1684.8), (648.0, 648.0))}


PLACE = _place()
# reserved face segments: (piece, group tag) -> (face, partner); the tagged groups are placed first, on a segment of
# that face centred on the partner (TX box centre / link window centroid), the rest of the face is shared as before.
PRIO = {BODY: ('tkm', 'N', f'core:{TX}'), EDGE: ('link', 'W', 'bus:links')}
TX_SITE = dict(inst=TX, module='ot_hbm_tkx_2beat_tx', cells=11467, origin_um=[501.12, 1105.92],
               outline_um=[198.72, 198.72], ff=2344, area_um2=1437.471)
RX_SITE = dict(inst=RX, module='ot_hbm_tkx_2beat_rx', cells=13686, origin_um=[112.32, 1010.88],
               outline_um=[51.84, 345.6], ff=3518, area_um2=1857.492)
TAP_BUDGET = {BODY: (550.0, 'max measured q_hub core insertion besides sfup (u_* 543-550 ps class)'),
              EDGE: (505.0, 'as u_xl_Q_ctl (89k cells, measured 505 ps)'),
              VM: (437.0, 'as u_vmb_Q3 (65k cells + macros, measured 437 ps)')}
DEL_BUSES = ['L102_o', 'L103_o', 'L104_o', 'L105_o', 'L131_i', 'L134_i', 'L135_i', 'L136_i',
             'L36_o', 'L37_o', 'L38_o', 'L39_o', 'L55_i', 'L57_i', 'L59_i', 'L61_i']
LINK_BUSES = ['L101_o', 'L126_i', 'L51_o', 'L52_i']
RAW, BEAT = 2341, 1171
L74_PORTS = ('L74_0', 'L74_1')
COMPACT = [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15]          # chunk16/17: dests 7..10 compacted away


def dest_class(d):
    if d <= 2:
        return 'link', [f'core:{EDGE}']
    if d <= 6:
        return 'del', [f'bus:{b}' for b in DEL_BUSES]
    if d <= 10:
        return 'wr', [f'core:{VM}']
    if d <= 14:
        return 'tkm', [f'core:{TX}', f'core:{EDGE}']        # TKM flit to TX; argmax in_key/meta in edge
    return 'red', [f'core:{RED}']


def _ports(piece):
    js = json.load(open(os.path.join(INP, REGCLASS[piece])))
    return [(n, v['direction'], int(v['width']), v.get('classes', {})) for n, v in js['ports'].items()]


def _is_clock(n, cls):
    return any('CLK' in k for k in cls) or re.match(r'^(clk_|.*_ck$|.*_clk$|writer_clk|vmasm_clk)', n) is not None


def _tkm_bits():
    pj = json.load(open(os.path.join(INP, 'flit_projection_d59a276772.json')))
    assert pj['bits'] == 2180 and sum(r['width'] for r in pj['ranges']) == 2180
    out = collections.defaultdict(set)
    for r in pj['ranges']:
        out[r['src_port']].update(range(r['src_lsb'], r['src_lsb'] + r['width']))
    return out


def _groups(piece, n, w, tkm):
    """[(tag, [bit idx], [targets])] for one piece port."""
    allb = list(range(w))
    if piece == BODY:
        m = re.match(r'u_body_g_qout_(\d+)_g3_\w_o_u_out_u_dst_([dv])$', n)
        if m:
            k, kind = int(m.group(1)), m.group(2)
            cls = collections.defaultdict(list)
            for b in allb:
                if kind == 'v':
                    d = b
                elif k <= 15:
                    d = b // 32
                elif k == 16:
                    d = COMPACT[b // 32]
                else:
                    d = COMPACT[b]
                tag, tg = dest_class(d)
                cls[(tag, tuple(tg))].append(b)
            if kind == 'd':     # exact projection: the TKM class is exactly the projected bits
                tb = sorted(sum((v for (tag, _), v in cls.items() if tag == 'tkm'), []))
                assert set(tb) == tkm.get(n, set()), (n, len(tb), len(tkm.get(n, ())))
            return [(tag, v, list(tg)) for (tag, tg), v in sorted(cls.items())]
        if 'upipe_SL' in n:
            return [('tkm', allb, [f'core:{TX}', f'core:{EDGE}'])]
        if 'arg_out' in n or 'link_abort' in n or 'arg_fault' in n or 'link_epoch' in n or 'sequence_pin' in n:
            return [('x', allb, [f'core:{EDGE}'])]
        m = re.match(r'u_body_g_qcap_(\d+)_', n)
        if m:
            return [('x', allb, [f'core:{EDGE}'] if int(m.group(1)) <= 4 else [f'core:{RED}'])]
        tg = []
        if 'ariter' in n or 'reduce_fault' in n:
            tg = [f'core:{RED}']
        elif 'ring_fault' in n or n == 'qid':
            tg = [f'core:{RING}']
        elif 'writer_fault' in n or 'vm_as_il' in n or 'rgx_addr_pin' in n or 'vm_select_pipe' in n:
            tg = [f'core:{VM}']
        elif n.startswith('tkx_'):
            tg = ['bus:L13_i']
        elif n in ('inj_d', 'inj_idx'):
            tg = ['core:u_cij_Q']
        elif n in ('inj_rd', 'hgi_inj_addr'):
            tg = ['leaf:u_cic_Q']
        elif n == 'hgi_del_obase':
            tg = [f'bus:{b}' for b in DEL_BUSES]
        elif n in ('vm_rq', 'vm_rq_', 'vm_rr'):
            tg = ['leaf:u_hcollrs_Q']
        elif n in ('fault_cause', 'stat_cycles', 'program_init_busy', 'done'):
            tg = ['leaf:u_obs_Q']
        elif n in ('rc_v', 'rc_tag'):
            tg = ['leaf:u_cxrc_Q_s']
        elif n.startswith(('cfg_', 'desc_')) or n in ('launch_v', 'program_configured', 'program_fault', 'hgi_busy',
                                                      'fault'):
            tg = ['leaf:u_hleaf_Q']
        return [('x', allb, tg)]
    if piece == EDGE:
        if re.search(r'link\d_(tx_pin|rx_pin|phy_up)', n):
            return [('link', allb, [f'bus:{b}' for b in LINK_BUSES])]
        if 'retry' in n:
            return [('x', allb, ['leaf:u_fr_Q', f'core:{BODY}'])]
        return [('x', allb, [f'core:{BODY}'])]
    if n == 'vmasm_rd_il':
        return [('x', allb, ['leaf:u_hcollrs_Q'])]
    if n.startswith('writer_tkw'):
        return [('x', allb, ['bus:L13_i'])]
    m = re.match(r'writer_kq(\d)', n)
    if m:
        return [('x', allb, [f'leaf:u_hcollks_Q_p{int(m.group(1)) // 2}'])]
    return [('x', allb, [f'core:{BODY}'])]


def _bits(n, w, idx=None):
    return [n] if w == 1 else [f'{n}[{i}]' for i in (range(w) if idx is None else idx)]


def _box(hc):
    (x, y), (w, h) = hc['origin_um'], hc['outline_um']
    return (x, y, w, h)


def _clamp(p, b):
    x, y, w, h = b
    return (min(max(p[0], x), x + w), min(max(p[1], y), y + h))


def _inside(p, boxes, m=4.32):
    return any(bx - m + 1e-6 < p[0] < bx + bw + m - 1e-6 and by - m + 1e-6 < p[1] < by + bh + m - 1e-6
               for bx, by, bw, bh in boxes)


def _hopmax(e):
    pts = [e['from_um']] + e['regs_um'] + [e['to_um']]
    return max([abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])] or [0.0])


def _r(p):
    return [round(p[0], 3), round(p[1], 3)]


def _sep(a, b, c):
    x, y, w, h = a
    bx, by, bw, bh = b
    return x + w + c <= bx + 1e-6 or bx + bw + c <= x + 1e-6 or y + h + c <= by + 1e-6 or by + bh + c <= y + 1e-6


def _place_prio(groups, w, h, tag, face, centre):
    """cb.place_pins with a reserved segment: the groups tagged `tag` all go on `face`, on the tracks of a segment
    centred on `centre` (face coordinate) just long enough for them; the other groups are placed by the cb.place_pins
    greedy (same order / pull / MEAN_MIN rules) with that face reduced to its tracks outside the segment."""
    vert = face in 'NS'
    L = w if vert else h
    lay2 = 'M7' if vert else 'M6'
    tr1, tr2 = cb.tracks(L, vert), cb.tracks(L, vert, lay2)
    prio = [g for g in groups if g[0].rsplit('#', 1)[-1] == tag]
    rest = [g for g in groups if g[0].rsplit('#', 1)[-1] != tag]
    npri = sum(len(g[1]) for g in prio)

    def caps(a, b, inside):
        t1 = [v for v in tr1 if (a <= v <= b) == inside]
        t2 = [v for v in tr2 if (a <= v <= b) == inside]
        ln = (b - a) if inside else max(0.0, L - 2 * cb.KEEP - (b - a))
        return t1, t2, min(len(t1), int(cb.CAP * ln)), min(len(t2), int(cb.CAP2 * ln))
    s = math.ceil(npri / PIN_MAX / G) * G
    while True:
        a = max(cb.KEEP, min(centre - s / 2, L - cb.KEEP - s))
        b = min(L - cb.KEEP, a + s)
        i1, i2, c1, c2 = caps(a, b, True)
        if c1 + c2 >= npri:
            break
        if b - a >= L - 2 * cb.KEEP - 1e-6:
            raise ValueError(f'reserved {face} segment cannot hold {npri} {tag} pins')
        s += G
    o1, o2, d1, d2 = caps(a, b, False)
    cap = {f: cb.face_cap(f, w, h) for f in 'NSEW'}
    cap[face] = d1 + d2
    if sum(len(g[1]) for g in rest) > sum(cap.values()):
        raise ValueError('perimeter full outside the reserved segment')
    load = collections.Counter()
    on = collections.defaultdict(list)
    gf = {}
    blind = lambda g: len(g[3]) == 1 and abs(list(g[3].values())[0] - 0.01) < 1e-9
    ngood = lambda g: sum(1 for v in g[3].values() if v >= 0)
    for port, names, f, pull in sorted(rest, key=lambda g: (blind(g), ngood(g), len(g[1]))):
        isb = blind((port, names, f, pull))
        if isb:
            order = [f] + sorted((x for x in 'NSEW' if x != f), key=lambda x: (x not in cb.ADJ[f], load[x] - cap[x]))
        else:
            order = sorted('NSEW', key=lambda x: -pull.get(x, -1))
        cnt, tot = collections.Counter(), 0.0
        for i, nm in enumerate(sorted(names, key=cb.bitk)):
            for x in order:
                if load[x] >= cap[x]:
                    continue
                pv = pull.get(x, -1)
                if not isb and pv < 0 and (tot + pv) / (i + 1) < cb.MEAN_MIN:
                    continue
                load[x] += 1; on[x].append(nm); cnt[x] += 1; tot += pv
                break
            else:
                raise ValueError(f'port {port}: faces {order} full')
        gf[port] = cnt.most_common(1)[0][0]
    for port, names, _, _ in prio:
        gf[port] = face

    def spread(names_, tr, f, lay):
        n = len(names_)
        idx = [int(round(i * (len(tr) - 1) / max(1, n - 1))) if n > 1 else len(tr) // 2 for i in range(n)]
        res = []
        for nm, k in zip(names_, idx):
            v = tr[k]
            lv, lh = lay or 'M5', lay or 'M4'
            res.append(dict(N=(nm, lv, v, round(h - cb.INSET, 4)), S=(nm, lv, v, cb.INSET),
                            E=(nm, lh, round(w - cb.INSET, 4), v), W=(nm, lh, cb.INSET, v))[f])
        return res
    out = []
    for f in 'NSEW':
        if f == face:
            pn = [nm for g in prio for nm in sorted(g[1], key=cb.bitk)]
            for names_, t1, t2, c in ((pn, i1, i2, c1), (on[f], o1, o2, d1)):
                for part, tr, lay in ((names_[:c], t1, None), (names_[c:], t2, lay2)):
                    if part:
                        out += spread(part, tr, f, lay)
            continue
        names = on[f]
        if not names:
            continue
        c1f, _ = cb.face_caps(f, w, h)
        for part, lay in ((names[:c1f], None), (names[c1f:], 'M7' if f in 'NS' else 'M6')):
            if part:
                out += spread(part, cb.tracks(w if f in 'NS' else h, f in 'NS', lay), f, lay)
    return out, gf, (round(a, 3), round(b, 3), npri)


def apply(plan, out, cc):
    cb.CAP2 = PIN_MAX - cb.CAP
    T = plan['partition_types']
    assert 'q_hub_nw' not in T and 'q_b101_nw' not in T
    t = copy.deepcopy(T['q_hub'])
    T['q_hub_nw'] = t
    parts = {p['name']: p for p in plan['partitions']}
    parts['NW_hub']['type'] = 'q_hub_nw'
    W, H = t['outline_um']
    rep = dict(type='q_hub_nw', source=SRC, not_done=[])
    lat0 = {k: dict(v) for k, v in plan['latency']['lanes'].items() if k in ('L74', 'L12', 'L13', 'L74m')}

    # ------------------------------------------------------------------ geometry (pieces + TX site)
    hcs = [h for h in t['hard_cores'] if h['inst'] != OLD]
    others = {h['inst']: _box(h) for h in hcs}
    hcn = {h['inst'] for h in t['hard_cores']}
    leafs = {c['inst']: (c['origin_um'][0], c['origin_um'][1], c['outline_um'][0], c['outline_um'][1])
             for c in t['contents'] if 'origin_um' in c and c['inst'] not in hcn
             and not any(h.startswith(c['inst'] + '_') for h in hcn)}
    geo = dict(others)
    for k, ((x, y), (w, h)) in PLACE.items():
        geo[k] = (x, y, w, h)
    geo[TX] = tuple(TX_SITE['origin_um'] + TX_SITE['outline_um'])
    for k in list(PLACE) + [TX]:
        x, y, w, h = geo[k]
        for v in (x, y, w, h):
            assert abs(v / G - round(v / G)) < 1e-6, (k, v)
        assert x >= FACE_BAND - 1e-6 and y >= FACE_BAND - 1e-6 and x + w <= W - FACE_BAND + 1e-6 \
            and y + h <= H - FACE_BAND + 1e-6, k
        for nm, b in list(others.items()) + list(leafs.items()) + [(k2, geo[k2]) for k2 in list(PLACE) + [TX]
                                                                    if k2 != k]:
            if nm != 'u_hb_coll_Q' and not _sep(geo[k], b, CHAN):
                raise ValueError(f'{k} overlaps / no {CHAN} channel to {nm}')
    cent = {k: (b[0] + b[2] / 2, b[1] + b[3] / 2) for k, b in geo.items()}
    for k, b in leafs.items():
        cent.setdefault(k, (b[0] + b[2] / 2, b[1] + b[3] / 2))

    # ------------------------------------------------------------------ L74 width -> 1171 (plan level)
    for b in t['buses']:
        if b['name'] == 'L74_o':
            assert b['width'] == RAW
            b['width'] = BEAT
    qb = copy.deepcopy(T['q_b101'])
    for s in qb['ft_slots']:
        if s['name'] == 'L74x1':
            assert s['width'] == RAW
            s['width'] = BEAT
    T['q_b101_nw'] = qb
    parts['NW_b101']['type'] = 'q_b101_nw'
    rt = T['root']
    for b in rt['buses']:
        if b['name'] == 'L74_i':
            assert b['width'] == RAW
            b['width'] = BEAT
    for pr in plan['ports']:
        if pr['id'] in L74_PORTS:
            assert pr['width'] == RAW
            pr['width'] = BEAT
            pr['note'] = (pr.get('note', '') + '; ' if pr.get('note') else '') + \
                'PATH-HBM/HUBNW 10-25: TKM-only 2-beat bus (ot_hbm_tkx_2beat, RAW 2341 -> 2 x 1171, window unchanged)'
    for ln in plan['lanes']:
        if ln['id'] == 'L74':
            ln.update(beats=2, word_bits=RAW, beat_index_bits=0)
            ln['note'] = ln.get('note', '') + ' | PATH-HBM/HUBNW 10-25: TKM-only tkx 2-beat (static slot from ' \
                'boot_start, pulse bits 2340:2332, no beat-index pin); TX u_tkx_tx_Q in NW_hub, RX u_tkx_rx_SW in root'
    P0 = S.Plan(plan)
    bt = CK._bus_targets(P0, 'q_hub_nw')

    # ------------------------------------------------------------------ pins of the q3 pieces
    tkm = _tkm_bits()
    os.makedirs(os.path.join(out, 'cores'), exist_ok=True)
    new_hc, pconn_all, gpins, rep_p, rep_seg = [], {}, {}, {}, {}
    for k in (BODY, EDGE, VM):
        x0, y0, cw, ch = geo[k]
        cx, cy = x0 + cw / 2, y0 + ch / 2
        groups, pconn, gtg = [], collections.defaultdict(list), {}
        nbits = 0
        for n, d, w, cls in _ports(k):
            nbits += w
            gl = [('clk', list(range(w)), [])] if _is_clock(n, cls) else _groups(k, n, w, tkm)
            assert sum(len(v) for _, v, _ in gl) == w
            for tag, idx, tg in gl:
                gname = f'{n}#{tag}'
                names = _bits(n, w, idx)
                pts = []
                for v in tg:
                    kd, _, nm = v.partition(':')
                    if kd == 'bus' and nm in bt:
                        pts.append(bt[nm][1])
                    elif nm in cent:
                        pts.append(cent[nm])
                dirs = []
                for tx, ty in pts:
                    dd = math.hypot(tx - cx, ty - cy)
                    if dd > 1e-6:
                        dirs.append(((tx - cx) / dd, (ty - cy) / dd))
                if dirs:
                    pull = {f: max(cb.NORM[f][0] * ux + cb.NORM[f][1] * uy for ux, uy in dirs) for f in 'NSEW'}
                    f = max(pull, key=pull.get)
                    for v in tg:
                        if v not in pconn[n]:
                            pconn[n].append(v)
                    gtg[gname] = (n, tg)
                else:
                    f = 'S' if k == BODY else 'E'
                    pull = {f: 0.01}
                groups.append((gname, names, f, pull))
        if k in PRIO:
            tag, face, partner = PRIO[k]
            if partner == 'bus:links':
                ys = [bt[b][1][1] for b in LINK_BUSES if b in bt and bt[b][0] == face]
                ctr = sum(ys) / len(ys) - y0
            else:
                pb = geo[partner.split(':', 1)[1]]
                ctr = (pb[0] + pb[2] / 2 - x0) if face in 'NS' else (pb[1] + pb[3] / 2 - y0)
            pins, gf, seg = _place_prio(groups, cw, ch, tag, face, ctr)
            rep_seg[k] = dict(tag=tag, face=face, centre=round(ctr, 2), segment=list(seg[:2]), pins=seg[2])
        else:
            pins, gf = cb.place_pins(groups, cw, ch)
        key = f'{MODS[k]}__{cw:g}x{ch:g}__q_hub_nw_{k}'
        pf = f'cores/{key}.json'
        json.dump([dict(name=n, layer=l, x=x, y=y) for n, l, x, y in pins], open(os.path.join(out, pf), 'w'))
        assert len(pins) == nbits
        per_face = collections.Counter(cb.face_of(x, y, cw, ch) for _, _, x, y in pins)
        dens = {f: round(c / (cw if f in 'NS' else ch), 2) for f, c in per_face.items()}
        assert max(dens.values()) <= PIN_MAX + 1e-6, (k, dens)
        pin_xy = {n: (x0 + x, y0 + y) for n, _, x, y in pins}
        gp = {}
        for gname, names, _, _ in groups:
            if gname in gtg:
                gp[gname] = (gtg[gname][0], gtg[gname][1], [pin_xy[nm] for nm in names])
        gpins[k] = gp
        capx = sum(PIN_MAX * max(0.0, (cw if f in 'NS' else ch) - 2 * cb.KEEP) for f in 'NSEW')
        rep_p[k] = dict(module=MODS[k], cells=CELLS[k], origin_um=[x0, y0], outline_um=[cw, ch], pins=len(pins),
                        port_bits=nbits, pins_per_face=dict(per_face), pins_per_um_face=dens,
                        perimeter_slack_at_pin_max=round(capx / len(pins), 3), reserved_segment=rep_seg.get(k),
                        pins_file=pf)
        new_hc.append(dict(inst=k, module=MODS[k], origin_um=[x0, y0], outline_um=[cw, ch], track_offset_um=[0.0, 0.0],
                           pins_file=pf, note=f'PATH-HBM/HUBNW 10-25: q3 split piece ({SRC}); {CELLS[k]} cells; '
                           'qout pins split per bit by dest class (exact TKM projection)'))
        pconn_all[k] = dict(pconn)
    tkm_pins = sum(len(v[2]) for v in gpins[BODY].values() if f'core:{TX}' in v[1])
    rep['tx_source_pins_on_body_core'] = tkm_pins
    # every TKM source bit: body_core pin -> TX box (Manhattan); stations = registers needed at hop <= HOP
    tb_ = geo[TX]
    st = collections.Counter()
    dmax = 0.0
    tface = collections.Counter()
    for gname, (port, tg, pp) in gpins[BODY].items():
        if f'core:{TX}' not in tg:
            continue
        for p in pp:
            q = _clamp(p, tb_)
            d = abs(p[0] - q[0]) + abs(p[1] - q[1])
            dmax = max(dmax, d)
            st[max(0, math.ceil(d / HOP) - 1)] += 1
            tface[cb.face_of(p[0] - geo[BODY][0], p[1] - geo[BODY][1], geo[BODY][2], geo[BODY][3])] += 1
    rep['tkm_source_bits'] = dict(bits=sum(st.values()), faces=dict(tface), stations_hist=dict(st),
                                  stations_min=min(st), stations_max=max(st), max_pin_to_TX_um=round(dmax, 2))
    assert rep['tkm_source_bits']['stations_min'] == rep['tkm_source_bits']['stations_max'], st
    assert set(tface) == {PRIO[BODY][1]}, tface
    i = [h['inst'] for h in t['hard_cores']].index(OLD)
    t['hard_cores'] = t['hard_cores'][:i] + new_hc + t['hard_cores'][i + 1:]
    rep['pieces'] = rep_p

    # ------------------------------------------------------------------ contents / cells
    c = [c for c in t['contents'] if c['inst'] == 'u_hb_coll_Q'][0]
    oldc = c['cells']
    bx = [geo[k] for k in (BODY, EDGE, VM, RING, RED)]
    x0 = min(b[0] for b in bx); y0 = min(b[1] for b in bx)
    x1 = max(b[0] + b[2] for b in bx); y1 = max(b[1] + b[3] for b in bx)
    c.update(module='ot_hfd_coll_q3_hard_v8x_s', cells=sum(CELLS.values()), origin_um=[x0, y0],
             outline_um=[round(x1 - x0, 4), round(y1 - y0, 4)],
             note=f'q_hub_nw (PATH-HBM/HUBNW 10-25): NW collective = q3 split ({SRC}); TKM raw 2341 -> {TX}')
    t['contents'].append(dict(inst=TX, module=TX_SITE['module'], status='new', cells=TX_SITE['cells'],
                              origin_um=TX_SITE['origin_um'], outline_um=TX_SITE['outline_um'],
                              note=f'PATH-HBM/HUBNW 10-25: FIRM soft site (Codex PLAN tkx_sites_soft_v2, not a hard '
                                   f'core): RAW {RAW} from body_core -> 2 beats of {BEAT} b on L74_o; mapped '
                                   f'{TX_SITE["cells"]} cells / {TX_SITE["ff"]} FF / {TX_SITE["area_um2"]} um2'))
    t['cells'] = int(t['cells']) - int(oldc) + sum(CELLS.values()) + TX_SITE['cells']
    t['note'] = (t.get('note', '') + '; ' if t.get('note') else '') + \
        (f'q_hub_nw (PATH-HBM/HUBNW 10-25): NW hub with the q3 collective split at the W end and the TKM TX '
         f'{TX}; L74_o = 1171-b 2-beat bus (tkx only); L13_i[571:0] = tkx return ([0] w_v, [40:1] w_addr, '
         '[56:41] w_mask, [568:57] w_data -> vm writer_tkw; [569] busy [570] done [571] fault -> body_core)')

    # ------------------------------------------------------------------ core_conns
    qn = copy.deepcopy(cc.get('q_hub', {}))
    qn.pop(OLD, None)
    for ci, ports in qn.items():
        for lp, lst in ports.items():
            if f'core:{OLD}' in lst:
                lst[:] = [v for v in lst if v != f'core:{OLD}'] + [f'core:{BODY}']
            if 'bus:L74_o' in lst:
                lst[:] = [v for v in lst if v != 'bus:L74_o']
        for lp in [lp for lp, lst in ports.items() if not lst]:
            ports.pop(lp)
    for k, pc in pconn_all.items():
        qn[k] = {n: list(v) for n, v in pc.items()}
    qn[TX] = {'raw': [f'core:{BODY}'], 'beat': ['bus:L74_o']}
    cc['q_hub_nw'] = qn
    cc['q_b101_nw'] = copy.deepcopy(cc.get('q_b101', {}))
    rcc = cc['root']
    nrm = 0
    for ci, ports in rcc.items():
        for lp, lst in ports.items():
            if 'bus:L74_i' in lst:
                lst.remove('bus:L74_i'); nrm += 1
        for lp in [lp for lp, lst in ports.items() if not lst]:
            ports.pop(lp)
    rcc[RX] = {'beat': ['bus:L74_i'], 'raw': [f'core:{TKM_ROOT}']}
    rep['root_core_conns_L74_i_removed'] = nrm

    # ------------------------------------------------------------------ q_hub_nw internal stations
    boxes = [geo[k] for k in geo]
    route = cb.RelayRouter(boxes, W, H, HOP)
    free = lambda p: cb.free_point(p, boxes, W, H)
    ist_old = t.get('internal_stations', [])
    keep, drop, rerouted = [], collections.Counter(), 0
    newb = [geo[k] for k in (BODY, EDGE, VM, TX)]
    for e in ist_old:
        lc = (str(e.get('launch', '')), str(e.get('capture', '')))
        if OLD in e['conn'] or any(x.split('.')[0] == OLD for x in lc):
            if e['conn'].startswith('bus:') or lc[0].split('.')[0] == OLD:
                drop['old body own chain (regenerated)'] += 1
                continue
            A = tuple(e['from_um'])
            B = _clamp(A, geo[BODY])
            regs = route(A, B)
            e = dict(e, conn=e['conn'].replace(OLD, BODY), capture=BODY, to_um=_r(B), regs_um=[_r(p) for p in regs],
                     note=f'PATH-HBM/HUBNW 10-25: re-targeted from {OLD} to {BODY}; {len(regs)} station(s)')
            keep.append(e); rerouted += 1
            continue
        if e['conn'] == 'bus:L74_o':
            drop['L74_o placeholder chain (L74 = tkx only, TX)'] += 1
            continue
        if any(_inside(tuple(r), newb) for r in e['regs_um']) or _inside(tuple(e['to_um']), newb, 0.0) \
                or _inside(tuple(e['from_um']), newb, 0.0):
            A, B = tuple(e['from_um']), tuple(e['to_um'])
            if e['conn'].startswith('bus:'):
                nb = free(B)
                regs = route(A, nb) + [nb]
            else:
                regs = route(A, B)
            e = dict(e, regs_um=[_r(p) for p in regs],
                     note=e.get('note', '') + f' | PATH-HBM/HUBNW 10-25: re-routed around the q3 pieces / TX '
                                              f'({len(regs)} station(s), hops <= {HOP:g} um)')
            rerouted += 1
        keep.append(e)
    added, lstat = [], []

    def chain(k, port, A, nm, kd, bits, launch_core=True):
        if kd == 'bus':
            if nm not in bt:
                return
            B = bt[nm][1]
        elif nm in geo:
            B = _clamp(A, geo[nm])
        else:
            return
        d = abs(A[0] - B[0]) + abs(A[1] - B[1])
        lstat.append((k, port, nm, bits, d))
        if d <= HOP:
            return
        if kd == 'bus':
            nc = free(A)
            regs = route(B, nc) + [nc]
            ent = dict(conn=f'bus:{nm}', from_um=_r(B), to_um=_r(A), launch=f'face bus {nm}', capture=f'{k}.{port}')
        else:
            regs = route(A, B)
            ent = dict(conn=f'core:{k}.{port}|core:{nm}', from_um=_r(A), to_um=_r(B), launch=f'{k}.{port}', capture=nm)
        ent.update(regs_um=[_r(p) for p in regs], bits=bits,
                   note=f'PATH-HBM/HUBNW 10-25 R3-INTERNAL: {d:.0f} um, {len(regs)} station(s), hops <= {HOP:g} um')
        added.append(ent)

    for k in (BODY, EDGE, VM):
        per = collections.defaultdict(list)          # (port, target) -> pins
        for gname, (port, tg, pp) in gpins[k].items():
            for v in tg:
                per[(port, v)].extend(pp)
        for (port, v), pp in per.items():
            A = (sum(p[0] for p in pp) / len(pp), sum(p[1] for p in pp) / len(pp))
            kd, _, nm = v.partition(':')
            if kd in ('bus', 'core'):
                chain(k, port, A, nm, kd, len(pp))
    # TX beat -> L74_o window (the 1171-b beat bus across the hub)
    tb = geo[TX]
    wpt = bt['L74_o'][1]
    A = _clamp(wpt, tb)
    chain(TX, 'beat', A, 'L74_o', 'bus', BEAT)
    # body_core -> TX raw (box distance; a chain only if > HOP)
    bb = geo[BODY]
    dbt = max(tb[0] - (bb[0] + bb[2]), bb[0] - (tb[0] + tb[2]), 0) + max(tb[1] - (bb[1] + bb[3]), bb[1] - (tb[1] + tb[3]), 0)
    rep['body_core_to_TX_box_um'] = round(dbt, 2)
    assert dbt <= HOP
    t['internal_stations'] = keep + added
    bad_reg = [e['conn'] for e in added if any(_inside(tuple(r), boxes, 0.0) for r in e['regs_um'])]
    worst = max((_hopmax(e), e['conn']) for e in t['internal_stations'])
    wn = max([(_hopmax(e), e['conn']) for e in t['internal_stations'] if 'HUBNW' in e.get('note', '')] or [(0, '')])
    rep['stations'] = dict(before=len(ist_old), after=len(t['internal_stations']), added=len(added),
                           dropped=dict(drop), rerouted_existing=rerouted, worst_hop_um=round(worst[0], 1),
                           worst_hop_conn=worst[1], worst_new_or_rerouted_hop_um=round(wn[0], 1),
                           worst_new_conn=wn[1], regs_inside_cores=bad_reg[:5],
                           station_regs_added=sum(len(e['regs_um']) for e in added),
                           station_bit_regs_added=sum(e['bits'] * len(e['regs_um']) for e in added))
    tk = [e for e in added if e['conn'] in ('bus:L74_o', 'bus:L13_i')]
    rep['tkx'] = {e['conn'] + ' ' + e['capture']: dict(bits=e['bits'], stations=len(e['regs_um']),
                                                        max_hop=round(_hopmax(e), 1)) for e in tk}
    cut = collections.defaultdict(lambda: [0, 0.0])
    for k, port, nm, bits, d in lstat:
        cut[f'{k}->{nm}'][0] += bits; cut[f'{k}->{nm}'][1] = max(cut[f'{k}->{nm}'][1], d)
    rep['links'] = {k: dict(bits=v[0], max_um=round(v[1])) for k, v in sorted(cut.items(), key=lambda kv: -kv[1][0])}

    # ------------------------------------------------------------------ clock taps
    ck = t['clock']
    taps = [tp for tp in ck.get('taps', []) if tp['name'].split('.')[0] != OLD]
    tp_pos = {BODY: lambda b: (b[0] + b[2] / 2, b[1] + b[3] + 4.32),
              EDGE: lambda b: (b[0] + b[2] + 4.32, b[1] + b[3] / 2),
              VM: lambda b: (b[0] + b[2] / 2, b[1] - 4.32)}
    for k in (BODY, EDGE, VM):
        x, y = tp_pos[k](geo[k])
        ins, why = TAP_BUDGET[k]
        taps.append(dict(name=k, kind='core', xy=[round(x, 3), round(y, 3)], insertion_ps=ins,
                         budget_owner=MODS[k], note=f'PATH-HBM/HUBNW BUDGET (no view yet): {why}'))
    ck['taps'] = taps

    # ------------------------------------------------------------------ root: RX site + L74_i
    rW, rH = rt['outline_um']
    rgeo = {h['inst']: _box(h) for h in rt['hard_cores']}
    rleaf = {c['inst']: (c['origin_um'][0], c['origin_um'][1], c['outline_um'][0], c['outline_um'][1])
             for c in rt['contents'] if 'origin_um' in c and c['inst'] not in rgeo}
    rxb = tuple(RX_SITE['origin_um'] + RX_SITE['outline_um'])
    for nm, b in list(rgeo.items()) + list(rleaf.items()):
        if not any(h.startswith(nm + '_') for h in rgeo) and not _sep(rxb, b, CHAN):
            raise ValueError(f'RX overlaps / no channel to root {nm}')
    rt['contents'].append(dict(inst=RX, module=RX_SITE['module'], status='new', cells=RX_SITE['cells'],
                               origin_um=RX_SITE['origin_um'], outline_um=RX_SITE['outline_um'],
                               note=f'PATH-HBM/HUBNW 10-25: FIRM soft site (Codex PLAN tkx_sites_soft_v2): L74_i 2 '
                                    f'beats x {BEAT} b -> RAW {RAW} -> {TKM_ROOT} (del_flit W face, cfg S, '
                                    f'start/slot/valid N, root_delivered_rx_pin_manifest); LINK_STAGES 2; mapped '
                                    f'{RX_SITE["cells"]} cells / {RX_SITE["ff"]} FF'))
    rt['cells'] = int(rt['cells']) + RX_SITE['cells']
    rist = rt.get('internal_stations', [])
    nd = sum(1 for e in rist if e['conn'] == 'bus:L74_i')
    rt['internal_stations'] = [e for e in rist if e['conn'] != 'bus:L74_i']
    rbt = CK._bus_targets(S.Plan(plan), 'root')
    rwin = rbt['L74_i'][1]
    rep['root'] = dict(L74_i_chains_removed=nd, L74_i_window_pt=_r(rwin),
                       window_to_RX_um=round(abs(rwin[0] - _clamp(rwin, rxb)[0]) + abs(rwin[1] - _clamp(rwin, rxb)[1]), 2),
                       RX_to_root_core_um=round(rgeo[TKM_ROOT][0] - (rxb[0] + rxb[2]), 2))
    assert rep['root']['window_to_RX_um'] <= HOP and rep['root']['RX_to_root_core_um'] <= HOP

    # ------------------------------------------------------------------ latency table (L74 word_cycles)
    P1 = S.Plan(plan)
    tab = plan['latency']['lanes']
    for lid in ('L74',):
        tab[lid] = P1.lane_latency(lid)
    rep['lane_latency'] = dict(before=lat0, after={k: tab[k] for k in lat0})
    rep['not_done'] += [
        'L13_i[571:0] bit map must match the root L13_o driver (root L13_o chains are still name-based placeholders)',
        'NE_hub keeps q_hub / 2341-b L74m (NE_b101 keeps q_b101): when NE gets its tkx TX (NE NLINK2 re-split, not in '
        'this scope) q_b101_nw folds back into q_b101',
        'pin partners of non-qout body ports remain name-based (q2 slot map) until the build_split_tops conn list',
        '64 projected flit bits are not in the 2116-b compact root del_flit (fieldmap compact_flit): they face TX '
        'but the TX discards them (selected actual core cut)']
    return rep


def corridor_cut(t, xs, horiz_bits_layers=('M4', 'M6')):
    """horizontal (E-W) bits crossing vertical cut x through the q_hub_nw internal station chains vs the free
    vertical extent (outside hard cores) x M4+M6 tracks (pitch from the plan layers)."""
    res = []
    hb = [_box(h) for h in t['hard_cores']]
    H = t['outline_um'][1]
    for x in xs:
        bits = 0
        for e in t['internal_stations']:
            pts = [e['from_um']] + e['regs_um'] + [e['to_um']]
            if any((a[0] - x) * (b[0] - x) < 0 or (a[0] == x != b[0]) for a, b in zip(pts, pts[1:])):
                bits += int(e.get('bits', 0))
        iv = sorted((b[1], b[1] + b[3]) for b in hb if b[0] <= x <= b[0] + b[2])
        blocked, cur = 0.0, None
        for a, b in iv:
            if cur is None or a > cur[1]:
                if cur:
                    blocked += cur[1] - cur[0]
                cur = [a, b]
            else:
                cur[1] = max(cur[1], b)
        if cur:
            blocked += cur[1] - cur[0]
        res.append(dict(x=x, bits=bits, free_um=round(H - blocked, 1)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--out', required=True)
    ap.add_argument('--edge-w', type=float, default=EDGE_W, help='edge strip width (um, 8.64 grid); default %(default)s')
    a = ap.parse_args()
    PLACE.clear(); PLACE.update(_place(a.edge_w))
    src = os.path.dirname(os.path.abspath(a.plan))
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(src):
        if f in ('die_plan.json', 'core_conns.json', 'cores', 'gates') or f.startswith('gates'):
            continue
        d = os.path.join(a.out, f)
        if not os.path.lexists(d):
            os.symlink(os.path.join(src, f), d)
    os.makedirs(os.path.join(a.out, 'cores'), exist_ok=True)
    for f in os.listdir(os.path.join(src, 'cores')):
        d = os.path.join(a.out, 'cores', f)
        if not os.path.lexists(d):
            os.symlink(os.path.join(src, 'cores', f), d)
    plan = json.load(open(a.plan))
    cc = json.load(open(os.path.join(src, 'core_conns.json')))
    rep = apply(plan, a.out, cc)
    json.dump(cc, open(os.path.join(a.out, 'core_conns.json'), 'w'), indent=0)
    json.dump(plan, open(os.path.join(a.out, 'die_plan.json'), 'w'), indent=0)
    json.dump(rep, open(os.path.join(a.out, 'q_hub_nw_report.json'), 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in ('stations', 'tkx', 'lane_latency', 'root', 'body_core_to_TX_box_um',
                                          'tx_source_pins_on_body_core', 'tkm_source_bits', 'pieces')}, indent=1))


if __name__ == '__main__':
    main()

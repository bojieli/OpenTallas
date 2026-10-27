#!/usr/bin/env python3
"""PATH-HBM/HUBNW (2026-10-25): plan type q_hub_nw = q_hub with the NW collective as the NLINK-3 q3 split
(ot_hfd_coll_q3_hard_v8x_s, claude/path-hbm-q3-1025@94d0f65260) and the TKM interface (tkx_*) of the HBM path.

    import q_hub_nw; rep = q_hub_nw.apply(plan, plan_dir_out, base_dir=None)

plan          loaded die_plan dict (hbm_arch B2p base = codex plan4); modified in place
plan_dir_out  the output plan directory: new core pin files go to plan_dir_out/cores/, core_conns.json is (re)written
              there with a 'q_hub_nw' entry (read from plan_dir_out, else base_dir)
returns       report dict

What it does (COORD ruling 10-25 10:04: q_hub_nw approved, PATH-HBM owns it, lands in ONE HBM plan delta):
  * partition_types['q_hub_nw'] = deep copy of q_hub; NW_hub.type = 'q_hub_nw' (NE_hub keeps q_hub).
  * hard core u_hb_coll_Q_body (q2 body, 222.6k) -> three q3 pieces (ORFS ASAP7 q3s2 synth):
      u_hb_coll_Q_body_core  ot_hfd_coll_q3_body_core  229,064 cells
      u_hb_coll_Q_edge       ot_hfd_coll_q3_edge_core   82,038 cells (3x link_e + argmax tp192; SerDes link pins)
      u_hb_coll_Q_vm         ot_hfd_coll_q3_vm_core     72,841 cells (vmasm + writer; takes tkx_w_*)
    u_hb_coll_Q_ring_ag / u_hb_coll_Q_reduce keep the q2 masters (identity-checked reuse) and their places.
  * pins: every port bit of the regclass port lists, faces by partner direction (cores_b2.place_pins), plan tracks
    (E/W M4 + M6, N/S M5 + M7, as the q_hub core pin files), <= 5.6 pins/um per face.
  * TKM interface: L74_o (2341 b = tkx_* out) is launched by body_core (qout slots 11-14 dst_d + dest_v + upipe
    tkm cfg flops); tkx return (572 b) arrives on L13_i bits [571:0] = {tkx_fault, tkx_done, tkx_busy,
    tkx_w_data[511:0], tkx_w_mask[15:0], tkx_w_addr[39:0], tkx_w_v}: 569 b -> vm_core writer_tkw_{v,d},
    3 b -> body_core tkx_{busy,done,fault}.  L12_i carries none of the TKM return (L13 is the direct root->NW_hub
    E-face port, one port hop; L12 goes root -> NW_b101 -> NW_su31 -> NW_hub).  The old L74_o relay chain to
    u_pgp_Q is removed (L74 is exactly tkx_*); the L12/L13 chains for their other payload are kept.
  * internal_stations (R3-INTERNAL, hops <= 360 um, cores_b2.RelayRouter): bus window <-> piece, piece <-> piece
    (body_core <-> edge 4021-b cut, vm <-> body), piece <-> other hub cores; every existing chain that ended at
    u_hb_coll_Q_body is re-targeted; every existing chain with a station inside a new piece is re-routed.
  * clock: one early core tap per new piece (insertion BUDGET by analogy, no view yet).
"""
import collections, copy, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

G = 8.64
HOP = 360.0
PIN_MAX = 5.6                      # pins/um per face (both layers)
OLD = 'u_hb_coll_Q_body'
BODY, EDGE, VM = 'u_hb_coll_Q_body_core', 'u_hb_coll_Q_edge', 'u_hb_coll_Q_vm'
RING, RED = 'u_hb_coll_Q_ring_ag', 'u_hb_coll_Q_reduce'
SRC = 'claude/path-hbm-q3-1025@94d0f65260'
CELLS = {BODY: 229064, EDGE: 82038, VM: 72841, RING: 147960, RED: 129647}     # q3s2 ORFS synth (README)
MODS = {BODY: 'ot_hfd_coll_q3_body_core', EDGE: 'ot_hfd_coll_q3_edge_core', VM: 'ot_hfd_coll_q3_vm_core'}
REGCLASS = {BODY: 'regclass_body_core.json', EDGE: 'regclass_edge_core.json', VM: 'regclass_vm_core.json'}
# W-end placement (see report 'placement_reason'): edge on the W face beside the SerDes link windows
# (L51/L52/L101/L126 at local y 946..1202), body_core below it in the old body slot + the free W corner,
# vm_core in the free NW corner.  origin / outline on the 8.64 lattice, >= 8.64 halo to every core and leaf.
# cores_b2 rules kept: >= FACE_BAND 34.56 from the partition faces (face flops / pin registers, GEOM-REVIEW 10-24),
# >= CHAN 17.28 channel to every other core / placed leaf (stations, repeaters, clock buffers).
FACE_BAND, CHAN = 34.56, 17.28
PLACE = {BODY: ((34.56, 34.56), (924.48, 786.24)),
         EDGE: ((34.56, 838.08), (449.28, 466.56)),
         VM: ((1296.0, 1684.8), (648.0, 648.0))}
TAP_BUDGET = {BODY: (550.0, 'max measured q_hub core insertion besides sfup (u_* 543-550 ps class)'),
              EDGE: (505.0, 'as u_xl_Q_ctl (89k cells, measured 505 ps)'),
              VM: (437.0, 'as u_vmb_Q3 (65k cells + macros, measured 437 ps)')}
DEL_BUSES = ['L102_o', 'L103_o', 'L104_o', 'L105_o', 'L131_i', 'L134_i', 'L135_i', 'L136_i',
             'L36_o', 'L37_o', 'L38_o', 'L39_o', 'L55_i', 'L57_i', 'L59_i', 'L61_i']
LINK_BUSES = ['L101_o', 'L126_i', 'L51_o', 'L52_i']
TKX_RET_BUS = 'L13_i'
TKX_OUT_BUS = 'L74_o'


def _hbm_arch_dir():
    for d in (os.environ.get('OT_HBM_ARCH'), os.path.join(HERE, 'hbm_arch'),
              os.path.join(HERE, '..', '..', '..', 'physical', 'die_plan', 'hbm_arch')):
        if d and os.path.isfile(os.path.join(d, 'cores_b2.py')):
            return os.path.abspath(d)
    raise RuntimeError('cores_b2.py not found: set OT_HBM_ARCH to physical/die_plan/hbm_arch')


def _import_cb():
    d = _hbm_arch_dir()
    sys.path.insert(0, d)
    import cores_b2 as cb          # noqa: E402  (imports tools/die_plan schema/check relative to the repo)
    return cb


def _ports(piece):
    js = json.load(open(os.path.join(HERE, 'regclass', REGCLASS[piece])))
    return [(n, v['direction'], int(v['width']), v.get('classes', {})) for n, v in js['ports'].items()]


def _is_clock(n, cls):
    return any('CLK' in k for k in cls) or re.match(r'^(clk_|.*_ck$|.*_clk$|writer_clk|vmasm_clk)', n) is not None


def _partners(piece, n, d):
    """name-based partner map of one piece port (q2_hard_v8g_s slot map, NPT=3: dest slots 0-2 link wr_flit,
    3-6 del_flit, 7-10 writer rgx_data, 11-14 tkx_del_flit + argmax in_key/meta, 15+ reduce/ring)."""
    B, E_, V = f'core:{EDGE}', f'core:{BODY}', f'core:{VM}'
    if piece == BODY:
        m = re.match(r'u_body_g_qout_(\d+)_', n)
        if m:
            k = int(m.group(1))
            if n.endswith('dst_v'):
                return [f'bus:{TKX_OUT_BUS}', B]
            if k <= 2:
                return [B]
            if k <= 6:
                return [f'bus:{b}' for b in DEL_BUSES]
            if k <= 10:
                return [V]
            if k <= 14:
                return [f'bus:{TKX_OUT_BUS}', B]
            return [f'core:{RED}']
        if 'upipe_SL' in n:
            return [f'bus:{TKX_OUT_BUS}', B]
        if 'arg_out' in n or 'link_abort' in n or 'arg_fault' in n or 'link_epoch' in n or 'sequence_pin' in n:
            return [B]
        m = re.match(r'u_body_g_qcap_(\d+)_', n)
        if m:
            return [B] if int(m.group(1)) <= 4 else [f'core:{RED}']
        if 'ariter' in n or 'reduce_fault' in n:
            return [f'core:{RED}']
        if 'ring_fault' in n or n == 'qid':
            return [f'core:{RING}']
        if 'writer_fault' in n or 'vm_as_il' in n or 'rgx_addr_pin' in n or 'vm_select_pipe' in n:
            return [V]
        if n.startswith('tkx_'):
            return [f'bus:{TKX_RET_BUS}']
        if n in ('inj_d', 'inj_idx'):
            return ['core:u_cij_Q']
        if n in ('inj_rd', 'hgi_inj_addr'):
            return ['leaf:u_cic_Q']
        if n == 'hgi_del_obase':
            return [f'bus:{b}' for b in DEL_BUSES]
        if n in ('vm_rq', 'vm_rq_', 'vm_rr'):
            return ['leaf:u_hcollrs_Q']
        if n in ('fault_cause', 'stat_cycles', 'program_init_busy', 'done'):
            return ['leaf:u_obs_Q']
        if n in ('rc_v', 'rc_tag'):
            return ['leaf:u_cxrc_Q_s']
        if n.startswith(('cfg_', 'desc_')) or n in ('launch_v', 'program_configured', 'program_fault', 'hgi_busy',
                                                    'fault'):
            return ['leaf:u_hleaf_Q']
        return []
    if piece == EDGE:
        if re.search(r'link\d_(tx_pin|rx_pin|phy_up)', n):
            return [f'bus:{b}' for b in LINK_BUSES]
        if 'retry' in n:
            return ['leaf:u_fr_Q', E_]
        return [E_]
    if piece == VM:
        if n == 'vmasm_rd_il':
            return ['leaf:u_hcollrs_Q']
        if n.startswith('writer_tkw'):
            return [f'bus:{TKX_RET_BUS}']
        m = re.match(r'writer_kq(\d)', n)
        if m:
            return [f'leaf:u_hcollks_Q_p{int(m.group(1)) // 2}']
        return [E_]
    return []


def _bits(n, w):
    return [n] if w == 1 else [f'{n}[{i}]' for i in range(w)]


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


def apply(plan, plan_dir_out, base_dir=None):
    cb = _import_cb()
    cb.CAP2 = PIN_MAX - cb.CAP                       # second pin layer: total <= 5.6 pins/um per face
    sys.path.insert(0, os.path.join(cb.ROOT, 'tools', 'die_plan'))
    import schema as S
    import check as CK
    T = plan['partition_types']
    if 'q_hub_nw' in T:
        raise ValueError('q_hub_nw already in the plan')
    t = copy.deepcopy(T['q_hub'])
    T['q_hub_nw'] = t
    parts = {p['name']: p for p in plan['partitions']}
    parts['NW_hub']['type'] = 'q_hub_nw'
    W, H = t['outline_um']
    rep = dict(type='q_hub_nw', source=SRC, moved_cores=[], not_done=[])

    # ---------------------------------------------------------------- hard cores
    hcs = [h for h in t['hard_cores'] if h['inst'] != OLD]
    old_hc = [h for h in t['hard_cores'] if h['inst'] == OLD][0]
    others = {h['inst']: _box(h) for h in hcs}
    hcn = {h['inst'] for h in t['hard_cores']}
    leafs = {c['inst']: (c['origin_um'][0], c['origin_um'][1], c['outline_um'][0], c['outline_um'][1])
             for c in t['contents'] if 'origin_um' in c and c['inst'] not in hcn
             and not any(h.startswith(c['inst'] + '_') for h in hcn)}
    for k, ((x, y), (w, h)) in PLACE.items():
        for v in (x, y, w, h):
            assert abs(v / G - round(v / G)) < 1e-6, (k, v)
        assert x >= FACE_BAND - 1e-6 and y >= FACE_BAND - 1e-6 and x + w <= W - FACE_BAND + 1e-6 \
            and y + h <= H - FACE_BAND + 1e-6, k
        for nm, (bx, by, bw, bh) in list(others.items()) + list(leafs.items()) + \
                [(k2, (p[0][0], p[0][1], p[1][0], p[1][1])) for k2, p in PLACE.items() if k2 != k]:
            if nm == 'u_hb_coll_Q':
                continue
            C = CHAN
            sep = (x + w + C <= bx + 1e-6 or bx + bw + C <= x + 1e-6 or y + h + C <= by + 1e-6 or by + bh + C <= y + 1e-6)
            if not sep:
                raise ValueError(f'{k} overlaps / no {C} channel to {nm}')
    geo = dict(others)
    for k, ((x, y), (w, h)) in PLACE.items():
        geo[k] = (x, y, w, h)
    cent = {k: (b[0] + b[2] / 2, b[1] + b[3] / 2) for k, b in geo.items()}
    for k, b in leafs.items():
        cent.setdefault(k, (b[0] + b[2] / 2, b[1] + b[3] / 2))
    P0 = S.Plan(plan)
    bt = CK._bus_targets(P0, 'q_hub_nw')

    # ---------------------------------------------------------------- pins
    os.makedirs(os.path.join(plan_dir_out, 'cores'), exist_ok=True)
    new_hc, pconn_all, pins_of, rep_p = [], {}, {}, {}
    for k in (BODY, EDGE, VM):
        x0, y0, cw, ch = geo[k]
        cx, cy = x0 + cw / 2, y0 + ch / 2
        groups, pconn = [], {}
        nbits = 0
        for n, d, w, cls in _ports(k):
            names = _bits(n, w)
            nbits += w
            tg = [] if _is_clock(n, cls) else _partners(k, n, d)
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
                pconn[n] = tg
            else:
                f = 'S' if k == BODY else 'E'
                pull = {f: 0.01}
            groups.append((n, names, f, pull))
        pins, gf = cb.place_pins(groups, cw, ch)
        key = f'{MODS[k]}__{cw:g}x{ch:g}__q_hub_nw_{k}'
        pf = f'cores/{key}.json'
        json.dump([dict(name=n, layer=l, x=x, y=y) for n, l, x, y in pins], open(os.path.join(plan_dir_out, pf), 'w'))
        per_face = collections.Counter(cb.face_of(x, y, cw, ch) for _, _, x, y in pins)
        dens = {f: round(c / (cw if f in 'NS' else ch), 2) for f, c in per_face.items()}
        rep_p[k] = dict(module=MODS[k], cells=CELLS[k], origin_um=[x0, y0], outline_um=[cw, ch], pins=len(pins),
                        port_bits=nbits, pins_per_um_face=dens, cells_per_um2=round(CELLS[k] / (cw * ch), 3),
                        pins_file=pf, spilled_ports=sum(1 for g in groups if gf[g[0]] != g[2]))
        assert len(pins) == nbits
        assert max(dens.values()) <= PIN_MAX + 1e-6, (k, dens)
        new_hc.append(dict(inst=k, module=MODS[k], origin_um=[x0, y0], outline_um=[cw, ch], track_offset_um=[0.0, 0.0],
                           pins_file=pf, note=f'PATH-HBM/HUBNW 10-25: q3 split piece of ot_hfd_coll_q3_hard_v8x_s '
                           f'({SRC}, ORFS ASAP7 q3s2); {CELLS[k]} cells'))
        pconn_all[k] = pconn
        pins_of[k] = pins
    # keep the hard-core order: the q3 pieces where the q2 body was
    i = [h['inst'] for h in t['hard_cores']].index(OLD)
    t['hard_cores'] = t['hard_cores'][:i] + new_hc + t['hard_cores'][i + 1:]
    for h in t['hard_cores']:
        if h['inst'] in (RING, RED):
            h['note'] = h['note'] + '; q_hub_nw: reused unchanged under the q3 split (identity-checked, ' + SRC + ')'
    rep['pieces'] = rep_p
    rep['ring_ag'] = dict(origin_um=geo[RING][:2], outline_um=geo[RING][2:], cells_q3s2=CELLS[RING])
    rep['reduce'] = dict(origin_um=geo[RED][:2], outline_um=geo[RED][2:], cells_q3s2=CELLS[RED])

    # ---------------------------------------------------------------- contents / cells
    c = [c for c in t['contents'] if c['inst'] == 'u_hb_coll_Q'][0]
    oldc = c['cells']
    bx = [geo[k] for k in (BODY, EDGE, VM, RING, RED)]
    x0 = min(b[0] for b in bx); y0 = min(b[1] for b in bx)
    x1 = max(b[0] + b[2] for b in bx); y1 = max(b[1] + b[3] for b in bx)
    c.update(module='ot_hfd_coll_q3_hard_v8x_s', cells=sum(CELLS.values()), origin_um=[x0, y0],
             outline_um=[round(x1 - x0, 4), round(y1 - y0, 4)],
             note=f'q_hub_nw (PATH-HBM/HUBNW 10-25): NW collective = q3 NLINK 3 TP 192 AR_ITER 1 ROWS 256 VM_RT 81 '
                  f'({SRC}); hard cores = body_core + edge + vm (new) + ring_ag + reduce (q2 masters reused); '
                  f'TKM interface tkx_* out on L74_o, tkx return on L13_i[571:0]')
    t['cells'] = int(t['cells']) - int(oldc) + sum(CELLS.values())
    t['note'] = (t.get('note', '') + '; ' if t.get('note') else '') + \
        ('q_hub_nw (PATH-HBM/HUBNW 10-25): NW hub with the q3 collective split and the TKM interface (L74_o = tkx_* '
         'out 2341 b from u_hb_coll_Q_body_core; L13_i[571:0] = tkx return: [0] w_v, [40:1] w_addr, [56:41] w_mask, '
         '[568:57] w_data -> u_hb_coll_Q_vm writer_tkw_{v,d}; [569] busy, [570] done, [571] fault -> body_core; '
         'L12_i carries no TKM bits)')
    rep['type_cells'] = dict(before=int(T['q_hub']['cells']), after=t['cells'])

    # ---------------------------------------------------------------- core_conns sidecar
    ccf = os.path.join(plan_dir_out, 'core_conns.json')
    if not os.path.isfile(ccf) and base_dir:
        ccf = os.path.join(base_dir, 'core_conns.json')
    cc = json.load(open(ccf)) if os.path.isfile(ccf) else {}
    qn = copy.deepcopy(cc.get('q_hub', {}))
    qn.pop(OLD, None)
    for ci, ports in qn.items():
        for lp, lst in ports.items():
            if f'core:{OLD}' in lst:
                lst[:] = [v for v in lst if v != f'core:{OLD}'] + [f'core:{BODY}']
            if f'bus:{TKX_OUT_BUS}' in lst:          # L74 = tkx_* only (endpoint audit 08:14): body_core alone
                lst[:] = [v for v in lst if v != f'bus:{TKX_OUT_BUS}']
        for lp in [lp for lp, lst in ports.items() if not lst]:
            ports.pop(lp)
    for k, pc in pconn_all.items():
        qn[k] = {n: list(v) for n, v in pc.items()}
    cc['q_hub_nw'] = qn
    json.dump(cc, open(os.path.join(plan_dir_out, 'core_conns.json'), 'w'), indent=0)

    # ---------------------------------------------------------------- internal stations
    boxes = [geo[k] for k in geo]
    route = cb.RelayRouter(boxes, W, H, HOP)
    free = lambda p: cb.free_point(p, boxes, W, H)
    ist_old = t.get('internal_stations', [])
    keep, drop, rerouted = [], collections.Counter(), 0
    newb = [geo[k] for k in (BODY, EDGE, VM)]
    for e in ist_old:
        lc = (str(e.get('launch', '')), str(e.get('capture', '')))
        if OLD in e['conn'] or any(x.split('.')[0] == OLD for x in lc):
            if e['conn'].startswith('bus:') or lc[0].split('.')[0] == OLD:
                drop['old body own chain (regenerated)'] += 1
                continue
            # another core's port -> old body: re-target to body_core
            A = tuple(e['from_um'])
            B = _clamp(A, geo[BODY])
            regs = route(A, B)
            e = dict(e, conn=e['conn'].replace(OLD, BODY), capture=BODY, to_um=[round(B[0], 3), round(B[1], 3)],
                     regs_um=[[round(x, 3), round(y, 3)] for x, y in regs],
                     note=f'PATH-HBM/HUBNW 10-25: re-targeted from {OLD} to {BODY}; {len(regs)} station(s), '
                          f'hops <= {HOP:g} um')
            keep.append(e)
            rerouted += 1
            continue
        if e['conn'] == f'bus:{TKX_OUT_BUS}':
            drop[f'{TKX_OUT_BUS} chain to {lc[1]} (L74 = tkx only; now body_core)'] += 1
            continue
        if any(_inside(tuple(r), newb) for r in e['regs_um']) or _inside(tuple(e['to_um']), newb, 0.0) \
                or _inside(tuple(e['from_um']), newb, 0.0):
            A, B = tuple(e['from_um']), tuple(e['to_um'])
            if e['conn'].startswith('bus:'):
                nb = free(B)
                regs = route(A, nb) + [nb]
            else:
                regs = route(A, B)
            e = dict(e, regs_um=[[round(x, 3), round(y, 3)] for x, y in regs],
                     note=e.get('note', '') + f' | PATH-HBM/HUBNW 10-25: re-routed around the q3 pieces '
                                              f'({len(regs)} station(s), hops <= {HOP:g} um)')
            rerouted += 1
        keep.append(e)
    added = []
    lstat = []
    for k in (BODY, EDGE, VM):
        byp = collections.defaultdict(list)
        for nm, ln, px, py in pins_of[k]:
            byp[cb.base(nm)].append((geo[k][0] + px, geo[k][1] + py))
        for port, tg in pconn_all[k].items():
            pp = byp[port]
            A = (sum(p[0] for p in pp) / len(pp), sum(p[1] for p in pp) / len(pp))
            bits = len(pp)
            for v in tg:
                kd, _, nm = v.partition(':')
                if kd == 'bus':
                    if nm not in bt:
                        continue
                    B = bt[nm][1]
                elif kd == 'core' and nm in geo:
                    B = _clamp(A, geo[nm])
                else:
                    continue
                d = abs(A[0] - B[0]) + abs(A[1] - B[1])
                lstat.append((k, port, nm, bits, d))
                if d <= HOP:
                    continue
                if kd == 'bus':
                    nc = free(A)
                    regs = route(B, nc) + [nc]
                    ent = dict(conn=f'bus:{nm}', from_um=[round(B[0], 3), round(B[1], 3)],
                               to_um=[round(A[0], 3), round(A[1], 3)], launch=f'face bus {nm}', capture=f'{k}.{port}')
                else:
                    regs = route(A, B)
                    ent = dict(conn=f'{k}.{port}|{nm}', from_um=[round(A[0], 3), round(A[1], 3)],
                               to_um=[round(B[0], 3), round(B[1], 3)], launch=f'{k}.{port}', capture=nm)
                ent.update(regs_um=[[round(x, 3), round(y, 3)] for x, y in regs], bits=bits,
                           note=f'PATH-HBM/HUBNW 10-25 R3-INTERNAL: {d:.0f} um core link, {len(regs)} station(s) '
                                f'(data + epoch), hops <= {HOP:g} um; +{len(regs)} cycle(s) on this link')
                ent = {kk: ent[kk] for kk in ('conn', 'from_um', 'to_um', 'regs_um', 'bits', 'launch', 'capture', 'note')}
                added.append(ent)
    t['internal_stations'] = keep + added
    worst = max([(_hopmax(e), e['conn']) for e in t['internal_stations']] or [(0, '')])
    bad_reg = [e['conn'] for e in added if any(_inside(tuple(r), boxes, 0.0) for r in e['regs_um'])]
    wn = max([(_hopmax(e), e['conn']) for e in t['internal_stations'] if 'HUBNW' in e.get('note', '')] or [(0, '')])
    dropc = collections.Counter()
    for kk, v in drop.items():
        dropc[re.sub(r' chain to (u_\w+)\.\S+', r' chains to \1', kk)] += v
    drop = dropc
    rep['stations'] = dict(worst_new_or_rerouted_hop_um=round(wn[0], 1), worst_new_conn=wn[1],
                           before=len(ist_old), after=len(t['internal_stations']), added=len(added),
                           dropped=dict(drop), rerouted_existing=rerouted, worst_hop_um=round(worst[0], 1),
                           worst_hop_conn=worst[1], regs_inside_cores=bad_reg[:5])
    tk = [e for e in added if e['conn'] in (f'bus:{TKX_OUT_BUS}', f'bus:{TKX_RET_BUS}')]
    rep['tkx'] = dict(
        out=dict(bus=TKX_OUT_BUS, bits=2341, window_pt=[round(v, 2) for v in bt[TKX_OUT_BUS][1]],
                 face=bt[TKX_OUT_BUS][0],
                 chains=[(e['capture'], e['bits'], len(e['regs_um'])) for e in tk if e['conn'] == f'bus:{TKX_OUT_BUS}']),
        ret=dict(bus=TKX_RET_BUS, bits=572, bit_map='L13_i[0]=w_v [40:1]=w_addr [56:41]=w_mask [568:57]=w_data '
                 '[569]=busy [570]=done [571]=fault; L12_i: none', window_pt=[round(v, 2) for v in bt[TKX_RET_BUS][1]],
                 face=bt[TKX_RET_BUS][0],
                 chains=[(e['capture'], e['bits'], len(e['regs_um'])) for e in tk if e['conn'] == f'bus:{TKX_RET_BUS}']))
    cut = collections.defaultdict(lambda: [0, 0.0, 0])
    for k, port, nm, bits, d in lstat:
        key = f'{k}->{nm}'
        cut[key][0] += bits; cut[key][1] = max(cut[key][1], d)
    rep['links'] = {k: dict(bits=v[0], max_um=round(v[1])) for k, v in sorted(cut.items(), key=lambda kv: -kv[1][0])}
    rep['link_bit_mm'] = round(sum(b * d for _, _, _, b, d in lstat) / 1000, 1)
    rep['station_bit_cycles'] = sum(e['bits'] * len(e['regs_um']) for e in added)

    # ---------------------------------------------------------------- clock taps
    ck = t['clock']
    taps = [tp for tp in ck.get('taps', []) if tp['name'].split('.')[0] != OLD]
    tp_pos = {BODY: lambda b: (b[0] + b[2] / 2, b[1] + b[3] + 4.32),         # N face (channel to edge)
              EDGE: lambda b: (b[0] + b[2] + 4.32, b[1] + b[3] / 2),         # E face
              VM: lambda b: (b[0] + b[2] / 2, b[1] - 4.32)}                  # S face
    for k in (BODY, EDGE, VM):
        x, y = tp_pos[k](geo[k])
        ins, why = TAP_BUDGET[k]
        taps.append(dict(name=k, kind='core', xy=[round(x, 3), round(y, 3)], insertion_ps=ins,
                         budget_owner=MODS[k], note=f'PATH-HBM/HUBNW BUDGET (no view yet): {why}'))
    ck['taps'] = taps
    rep['taps'] = [(tp['name'], tp['xy'], tp['insertion_ps']) for tp in taps if tp['name'] in (BODY, EDGE, VM)]
    rep['not_done'] += [
        'port partners are name-based (q2_hard_v8g_s slot map); exact per-bit partners come with the HBM-CORES '
        'build_split_tops conn list',
        'edge_core _pr input-register twin (+44 registered bits) not in the pin table yet (port names unchanged '
        'expected; re-run apply when the twin lands)',
        'ring_ag / reduce keep their q2 pin files and have no core clock taps (as base)',
        'root side: L74_i / L13_o chains inside root must end at u_tkm_SW_root (root type, not this module)',
        'L13_i[571:0] bit map must match the root L13_o driver (RTL bind)']
    return rep


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--out', required=True, help='output plan dir (gets die_plan.json, cores/, core_conns.json)')
    a = ap.parse_args()
    import shutil
    src = os.path.dirname(os.path.abspath(a.plan))
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(src):
        s = os.path.join(src, f)
        if f == 'die_plan.json':
            continue
        if not os.path.exists(os.path.join(a.out, f)):
            os.symlink(s, os.path.join(a.out, f)) if f != 'cores' and f != 'core_conns.json' else None
    os.makedirs(os.path.join(a.out, 'cores'), exist_ok=True)
    for f in os.listdir(os.path.join(src, 'cores')):
        d = os.path.join(a.out, 'cores', f)
        if not os.path.exists(d):
            os.symlink(os.path.join(src, 'cores', f), d)
    if not os.path.exists(os.path.join(a.out, 'core_conns.json')):
        shutil.copy(os.path.join(src, 'core_conns.json'), os.path.join(a.out, 'core_conns.json'))
    plan = json.load(open(a.plan))
    rep = apply(plan, a.out, base_dir=src)
    json.dump(plan, open(os.path.join(a.out, 'die_plan.json'), 'w'), indent=0)
    json.dump(rep, open(os.path.join(a.out, 'q_hub_nw_report.json'), 'w'), indent=1)
    print(json.dumps(rep, indent=1)[:6000])

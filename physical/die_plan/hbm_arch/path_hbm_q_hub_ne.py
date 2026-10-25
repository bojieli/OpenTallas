#!/usr/bin/env python3
"""PATH-HBM/NE2 (2026-10-25): plan step -> q_hub_ne (NE_hub collective = NLINK 2 split; COORD 10:04 ruling 1).

    HBM_ARCH_DIR=<plan worktree>/physical/die_plan/hbm_arch python3 path_hbm_q_hub_ne.py BASE/die_plan.json --out OUTDIR \
        [--body-cells N] [--vm-cells N]

What it does:
  * partition_types['q_hub_ne'] = copy of q_hub; NE_hub.type = q_hub_ne (NE_hub stops sharing q_hub; NE_b101 keeps
    q_b101 and its 2341-b L74m slot; NE has no TKM outputs, so no TX site and no L74/L13 change).
  * u_hb_coll_Q_body (as-built q2 body, NLINK 1) -> two hard pieces of ot_hfd_coll_q2_hard_v8g_s #(NLINK 2, TP 192,
    AR_ITER 1, ROWS 256, VM_RT 81) (W-EP links N2/S3):
      u_hb_coll_Q_body_n2 = ot_hfd_coll_q2n2_body_core (rest_extract: master minus ring/reduce/vmasm/writer)
      u_hb_coll_Q_vm      = ot_hfd_coll_q2n2_vm_core   (q3 vm_core members u_vmasm + u_writer; the q2 master drives
                            the writer TKM port with 0, so that constant is folded INSIDE the core: no tied pins)
    ring_ag / reduce keep the q2 masters and places.  Geometry: body_n2 = as-built body slot grown W+N, vm under it.
  * q_hub itself is renamed q_hub_ne when NE_hub was its last user (no orphan type).
  * pins: every body_n2 pin bit faces its REAL partner from the master parent view (B2p_inputs/q_hub_ne/
    body_n2_conn.json: member cell u_vmasm/u_writer -> vm, u_reduce -> reduce, u_ring -> ring, master port -> the
    q_hub leaf / bus the as-built body port went to).  vm pins: rd_il -> u_hcollrs_Q, kq<i> -> u_hcollks_Q_p<i/2>,
    rest -> body_n2.
  * internal_stations (R3-INTERNAL, hops <= 360 um, cores_b2.RelayRouter), clock taps for the 2 new cores.
"""
import argparse, collections, copy, json, math, os, re, sys

ME = os.path.dirname(os.path.abspath(__file__))
HERE = os.environ.get('HBM_ARCH_DIR') or ME
INP = os.path.join(ME, 'B2p_inputs', 'q_hub_ne')
MYROOT = os.path.abspath(os.path.join(ME, '..', '..', '..'))
sys.path.insert(0, HERE)
import cores_b2 as cb                                                     # noqa: E402
sys.path.insert(0, os.path.join(cb.ROOT, 'tools', 'die_plan'))
import schema as S                                                        # noqa: E402
import check as CK                                                        # noqa: E402

G = 8.64
HOP = 360.0
PIN_MAX = 5.6
TYPE, PART = 'q_hub_ne', 'NE_hub'
OLD = 'u_hb_coll_Q_body'
BODY, VM = 'u_hb_coll_Q_body_n2', 'u_hb_coll_Q_vm'
RING, RED = 'u_hb_coll_Q_ring_ag', 'u_hb_coll_Q_reduce'
SRC = 'q2n2 split claude/path-hbm-ne2-1025 (rest_extract of ot_hfd_coll_q2_hard_v8g_s NLINK 2 + q3 vm members)'
MODS = {BODY: 'ot_hfd_coll_q2n2_body_core', VM: 'ot_hfd_coll_q2n2_vm_core'}
VM_RTL = 'rtl/hbm_accel/cores_split/ot_hfd_coll_q2n2_hard_v8g/ot_hfd_coll_q2n2_vm_core.sv'
FACE_BAND, CHAN = 34.56, 17.28
# body_n2 on the as-built q2 body site grown W+N (reduce stays its E neighbour), vm directly S of it (25.9 um channel):
# body<->vm and body<->reduce are MASTER-INTERNAL cuts (lock-step proven with 0 extra edges), so they must close
# without relay stations (<= 360 um pin to pin).  The q_hub_nw sites (body 34.56/924x786, vm 1296/1684.8) put those
# cuts 0.8-2.1 mm apart -> stations = cycle change; not used here.
# body = the as-built body slot grown west to the face band and north to u_vmb_Q3 (12,131 pins need ~3 mm of
# perimeter at <= 5.6 pins/um); vm = the free SW corner under it, east edge one channel short of u_cxij_Q_s.
PLACE = {BODY: ((34.56, 561.6), (786.24, 743.04)),
         VM: ((34.56, 34.56), (924.48, 509.76))}
INTERNAL = (VM, RED, RING)          # master-internal partners of body_n2: a station chain there is a cycle change
TAP_BUDGET = {BODY: (550.0, 'max measured q_hub core insertion besides sfup (u_* 543-550 ps class)'),
              VM: (437.0, 'as u_vmb_Q3 (65k cells + macros, measured 437 ps)')}
DEL_BUSES = ['L102_o', 'L103_o', 'L104_o', 'L105_o', 'L131_i', 'L134_i', 'L135_i', 'L136_i',
             'L36_o', 'L37_o', 'L38_o', 'L39_o', 'L55_i', 'L57_i', 'L59_i', 'L61_i']
LINK_BUSES = ['L101_o', 'L126_i', 'L51_o', 'L52_i']
MP = {}                                   # master port -> q_hub targets (as the as-built body core_conns)
for n in ('del_flit', 'del_valid', 'hgi_del_obase'):
    MP[n] = [f'bus:{b}' for b in DEL_BUSES]
for n in ('tx_pin_flit', 'tx_pin_v', 'rx_pin_flit', 'rx_pin_v', 'phy_up'):
    MP[n] = [f'bus:{b}' for b in LINK_BUSES]
MP.update(retry_requested=['leaf:u_fr_Q'], inj_d=['core:u_cij_Q'], inj_idx=['core:u_cij_Q'], inj_rd=['leaf:u_cic_Q'],
          hgi_inj_addr=['leaf:u_cic_Q'], vm_rq=['leaf:u_hcollrs_Q'], vm_rr=['leaf:u_hcollrs_Q'],
          isa_ring=['core:u_hcollgi_Q'], qid=[f'core:{RING}'], rc_v=['leaf:u_cxrc_Q_s'], rc_tag=['leaf:u_cxrc_Q_s'],
          rst_n=[])
for n in ('cfg_v', 'cfg_target', 'cfg_addr', 'cfg_data', 'desc_v', 'desc_base', 'desc_limit', 'desc_loops', 'launch_v',
          'program_configured', 'program_fault', 'hgi_busy', 'fault', 'hgi_fault'):
    MP[n] = ['leaf:u_hleaf_Q']
for n in ('stat_cycles', 'fault_cause', 'program_init_busy', 'done', 'hgi_done'):
    MP[n] = ['leaf:u_obs_Q']
CELLT = {'u_body.u_writer': f'core:{VM}', 'u_body.u_vmasm': f'core:{VM}', 'u_body.u_reduce': f'core:{RED}',
         'u_body.u_ring': f'core:{RING}'}


def _is_clock(n):
    return re.match(r'^(clk_|clk$|.*_ck$|.*_clk$|writer_clk|vmasm_clk)', n) is not None


def _partner_targets(partners, direction='output'):
    tg = []
    if direction == 'input' and any(p.startswith('port:') for p in partners):
        # a master input net (rst_n, qid) that body_n2 shares with ring/reduce/vm: those cores are co-sinks fed from
        # the parent like body_n2, not partners of body_n2 -> no body->core conn (and no station chain) for it
        partners = [p for p in partners if not p.startswith('cell:')]
    for p in partners:
        kd, _, nm = p.partition(':')
        if kd == 'cell':
            v = [CELLT[nm]]
        elif nm.startswith('clk'):
            v = []
        else:
            assert nm in MP, ('unmapped master port', nm)
            v = MP[nm]
        tg += [x for x in v if x not in tg]
    return tg


def _body_ports():
    js = json.load(open(os.path.join(INP, 'body_n2_conn.json')))['ports']
    out = []
    for n, v in js.items():
        gl = []
        for partners, ranges in v['partners']:
            idx = [i for a, b in ranges for i in range(a, b + 1)]
            gl.append((partners, idx))
        out.append((n, v['direction'], v['width'], gl))
    return out


def _vm_ports():
    txt = open(os.path.join(MYROOT, VM_RTL)).read()
    hdr = re.search(r'(?ms)^module ot_hfd_coll_q2n2_vm_core \((.*?)\);', txt).group(1)
    return [(m.group(3), m.group(1), int(m.group(2) or 0) + 1)
            for m in re.finditer(r'(input|output) wire (?:\[(\d+):0\] )?(\w+)', hdr)]


def _vm_targets(n):
    if n == 'vmasm_rd_il':
        return ['leaf:u_hcollrs_Q']
    m = re.match(r'writer_kq(\d)', n)
    if m:
        return [f'leaf:u_hcollks_Q_p{int(m.group(1)) // 2}']
    if n == 'writer_rst_n':
        return []
    return [f'core:{BODY}']


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


def apply(plan, out, cc, cells):
    cb.CAP2 = PIN_MAX - cb.CAP
    T = plan['partition_types']
    assert TYPE not in T
    parts = {p['name']: p for p in plan['partitions']}
    assert parts[PART]['type'] == 'q_hub'
    parts[PART]['type'] = TYPE
    # NE_hub was the last q_hub user (NW_hub = q_hub_nw): q_hub moves to q_hub_ne instead of being left orphaned
    # (an orphan type has no instance face geometry -> G0C face_flop ERROR)
    orphan = not any(p['type'] == 'q_hub' for p in plan['partitions'])
    t = T.pop('q_hub') if orphan else copy.deepcopy(T['q_hub'])
    T[TYPE] = t
    W, H = t['outline_um']
    rep = dict(type=TYPE, source=SRC, not_done=[])
    lat0 = copy.deepcopy(plan['latency']['lanes'])

    # ------------------------------------------------------------------ geometry
    hcs = [h for h in t['hard_cores'] if h['inst'] != OLD]
    others = {h['inst']: _box(h) for h in hcs}
    hcn = {h['inst'] for h in t['hard_cores']}
    leafs = {c['inst']: (c['origin_um'][0], c['origin_um'][1], c['outline_um'][0], c['outline_um'][1])
             for c in t['contents'] if 'origin_um' in c and c['inst'] not in hcn
             and not any(h.startswith(c['inst'] + '_') for h in hcn)}
    geo = dict(others)
    for k, ((x, y), (w, h)) in PLACE.items():
        geo[k] = (x, y, w, h)
    for k in PLACE:
        x, y, w, h = geo[k]
        for v in (x, y, w, h):
            assert abs(v / G - round(v / G)) < 1e-6, (k, v)
        assert x >= FACE_BAND - 1e-6 and y >= FACE_BAND - 1e-6 and x + w <= W - FACE_BAND + 1e-6 \
            and y + h <= H - FACE_BAND + 1e-6, k
        for nm, b in list(others.items()) + list(leafs.items()) + [(k2, geo[k2]) for k2 in PLACE if k2 != k]:
            if nm != 'u_hb_coll_Q' and not _sep(geo[k], b, CHAN):
                raise ValueError(f'{k} overlaps / no {CHAN} channel to {nm}')
    cent = {k: (b[0] + b[2] / 2, b[1] + b[3] / 2) for k, b in geo.items()}
    for k, b in leafs.items():
        cent.setdefault(k, (b[0] + b[2] / 2, b[1] + b[3] / 2))
    P0 = S.Plan(plan)
    bt = CK._bus_targets(P0, TYPE)

    # ------------------------------------------------------------------ pins
    os.makedirs(os.path.join(out, 'cores'), exist_ok=True)
    new_hc, pconn_all, gpins, rep_p = [], {}, {}, {}
    plist = {BODY: [(n, d, w, [(_partner_targets(p, d), idx) for p, idx in gl]) for n, d, w, gl in _body_ports()],
             VM: [(n, d, w, [(_vm_targets(n), list(range(w)))]) for n, d, w in _vm_ports()]}
    for k in (BODY, VM):
        x0, y0, cw, ch = geo[k]
        cx, cy = x0 + cw / 2, y0 + ch / 2
        groups, pconn, gtg = [], collections.defaultdict(list), {}
        nbits = 0
        for n, d, w, gl in plist[k]:
            nbits += w
            if _is_clock(n):
                gl = [([], list(range(w)))]
            assert sum(len(v) for _, v in gl) == w, n
            for gi, (tg, idx) in enumerate(gl):
                gname = f'{n}#{gi}'
                names = _bits(n, w, idx)
                pts = []
                # a broadcast bit read by vm/reduce (adjacent, master-internal) AND ring (7 mm away, as-built) faces
                # the adjacent piece: its cut stays station-free; the ring chain only starts at that pin
                near = [v for v in tg if v in (f'core:{VM}', f'core:{RED}')]
                for v in (tg if k != BODY or not near else [v for v in tg if v != f'core:{RING}']):
                    kd, _, nm = v.partition(':')
                    if kd == 'bus' and nm in bt:
                        pts.append(bt[nm][1])
                    elif nm in cent:
                        pts.append(cent[nm])
                    else:
                        raise ValueError(f'{k}.{n}: target {v} not in {TYPE}')
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
                    f = 'S' if k == BODY else 'W'
                    pull = {f: 0.01}
                groups.append((gname, names, f, pull))
        pins, gf = cb.place_pins(groups, cw, ch)
        key = f'{MODS[k]}__{cw:g}x{ch:g}__{TYPE}_{k}'
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
        rep_p[k] = dict(module=MODS[k], cells=cells[k], origin_um=[x0, y0], outline_um=[cw, ch], pins=len(pins),
                        port_bits=nbits, pins_per_um_face=dens, pins_per_face=dict(per_face), pins_file=pf)
        new_hc.append(dict(inst=k, module=MODS[k], origin_um=[x0, y0], outline_um=[cw, ch], track_offset_um=[0.0, 0.0],
                           pins_file=pf, note=f'PATH-HBM/NE2 10-25: q2n2 split piece ({SRC}); {cells[k]} cells; '
                           'pins face their master-parent-view partners'))
        pconn_all[k] = dict(pconn)
    i = [h['inst'] for h in t['hard_cores']].index(OLD)
    t['hard_cores'] = t['hard_cores'][:i] + new_hc + t['hard_cores'][i + 1:]
    rep['pieces'] = rep_p

    # ------------------------------------------------------------------ contents / cells
    c = [c for c in t['contents'] if c['inst'] == 'u_hb_coll_Q'][0]
    oldc = c['cells']
    ring_red = {h['inst']: int(re.search(r'(\d+) cells', h.get('note', '')).group(1)) for h in t['hard_cores']
                if h['inst'] in (RING, RED)}
    newc = cells[BODY] + cells[VM] + sum(ring_red.values())
    bx = [geo[k] for k in (BODY, VM, RING, RED)]
    x0 = min(b[0] for b in bx); y0 = min(b[1] for b in bx)
    x1 = max(b[0] + b[2] for b in bx); y1 = max(b[1] + b[3] for b in bx)
    c.update(module='ot_hfd_coll_q2_hard_v8g_s', cells=newc, origin_um=[x0, y0],
             outline_um=[round(x1 - x0, 4), round(y1 - y0, 4)],
             note=f'q_hub_ne (PATH-HBM/NE2 10-25): NE collective = q2 NLINK 2 (W-EP links N2/S3) split ({SRC}): '
                  f'{BODY} + {VM} + q2 ring_ag/reduce masters')
    t['cells'] = int(t['cells']) - int(oldc) + newc
    rep['cells'] = dict(u_hb_coll_Q_before=oldc, after=newc, ring_reduce=ring_red)
    t['note'] = (t.get('note', '') + '; ' if t.get('note') else '') + \
        (f'q_hub_ne (PATH-HBM/NE2 10-25): NE hub, collective NLINK 2 split ({BODY} + {VM}); no TKM (L74m via NE_b101 '
         'unchanged)')

    # ------------------------------------------------------------------ core_conns
    qn = copy.deepcopy(cc.get('q_hub', {}))
    if orphan:
        cc.pop('q_hub', None)
    qn.pop(OLD, None)
    for ci, ports in qn.items():
        for lp, lst in ports.items():
            if f'core:{OLD}' in lst:
                lst[:] = [v for v in lst if v != f'core:{OLD}'] + [f'core:{BODY}']
    for k, pc in pconn_all.items():
        qn[k] = {n: list(v) for n, v in pc.items()}
    cc[TYPE] = qn

    # ------------------------------------------------------------------ internal stations
    boxes = [geo[k] for k in geo]
    route = cb.RelayRouter(boxes, W, H, HOP)
    free = lambda p: cb.free_point(p, boxes, W, H)
    ist_old = t.get('internal_stations', [])
    keep, drop, rerouted = [], collections.Counter(), 0
    newb = [geo[k] for k in (BODY, VM)]
    for e in ist_old:
        lc = (str(e.get('launch', '')), str(e.get('capture', '')))
        if OLD in e['conn'] or any(x.split('.')[0] == OLD for x in lc):
            if e['conn'].startswith('bus:') or lc[0].split('.')[0] == OLD:
                drop['old body own chain (regenerated from the new pins)'] += 1
                continue
            A = tuple(e['from_um'])
            B = _clamp(A, geo[BODY])
            regs = route(A, B)
            e = dict(e, conn=e['conn'].replace(OLD, BODY), capture=BODY, to_um=_r(B), regs_um=[_r(p) for p in regs],
                     note=f'PATH-HBM/NE2 10-25: re-targeted from {OLD} to {BODY}; {len(regs)} station(s)')
            keep.append(e); rerouted += 1
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
                     note=e.get('note', '') + f' | PATH-HBM/NE2 10-25: re-routed around the q2n2 pieces '
                                              f'({len(regs)} station(s), hops <= {HOP:g} um)')
            rerouted += 1
        keep.append(e)
    added, lstat = [], []

    def chain(k, port, A, nm, kd, bits):
        if kd == 'bus':
            if nm not in bt:
                return
            B = bt[nm][1]
        elif nm in geo:
            B = _clamp(A, geo[nm])
        elif nm in cent:
            B = cent[nm]
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
            ent = dict(conn=f'core:{k}.{port}|{kd}:{nm}', from_um=_r(A), to_um=_r(B), launch=f'{k}.{port}', capture=nm)
        ent.update(regs_um=[_r(p) for p in regs], bits=bits,
                   note=f'PATH-HBM/NE2 10-25 R3-INTERNAL: {d:.0f} um, {len(regs)} station(s), hops <= {HOP:g} um')
        added.append(ent)

    for k in (BODY, VM):
        per = collections.defaultdict(list)          # (port, target) -> pins
        for gname, (port, tg, pp) in gpins[k].items():
            for v in tg:
                per[(port, v)].extend(pp)
        for (port, v), pp in per.items():
            if k == VM and v == f'core:{BODY}':
                continue                             # body<->vm counted once (from the body side)
            A = (sum(p[0] for p in pp) / len(pp), sum(p[1] for p in pp) / len(pp))
            kd, _, nm = v.partition(':')
            if kd in ('bus', 'core', 'leaf'):
                chain(k, port, A, nm, kd, len(pp))
    t['internal_stations'] = keep + added
    bad_reg = [e['conn'] for e in added if any(_inside(tuple(r), boxes, 0.0) for r in e['regs_um'])]
    worst = max((_hopmax(e), e['conn']) for e in t['internal_stations'])
    wn = max([(_hopmax(e), e['conn']) for e in t['internal_stations'] if 'NE2' in e.get('note', '')] or [(0, '')])
    rep['stations'] = dict(before=len(ist_old), after=len(t['internal_stations']), added=len(added),
                           dropped=dict(drop), rerouted_existing=rerouted, worst_hop_um=round(worst[0], 1),
                           worst_hop_conn=worst[1], worst_new_or_rerouted_hop_um=round(wn[0], 1),
                           worst_new_conn=wn[1], regs_inside_cores=bad_reg[:5],
                           station_regs_added=sum(len(e['regs_um']) for e in added),
                           station_bit_regs_added=sum(e['bits'] * len(e['regs_um']) for e in added))
    cut = collections.defaultdict(lambda: [0, 0.0])
    for k, port, nm, bits, d in lstat:
        cut[f'{k}->{nm}'][0] += bits; cut[f'{k}->{nm}'][1] = max(cut[f'{k}->{nm}'][1], d)
    rep['links'] = {k: dict(bits=v[0], max_um=round(v[1])) for k, v in sorted(cut.items(), key=lambda kv: -kv[1][0])}
    # stations per (piece, target): uneven-station check (max - min stations among the chains of one target)
    st = collections.defaultdict(list)
    for e in added:
        key = (e['launch'].split('.')[0] if not e['conn'].startswith('bus:') else e['capture'].split('.')[0]) + \
            '->' + (e['capture'] if not e['conn'].startswith('bus:') else e['conn'])
        st[key].append(len(e['regs_um']))
    rep['stations_per_link'] = {k: dict(chains=len(v), min=min(v), max=max(v)) for k, v in sorted(st.items())}
    rep['master_internal_station_chains'] = {k: v for k, v in rep['stations_per_link'].items()
                                             if k.startswith(BODY) and any(k.endswith(x) for x in INTERNAL)}

    # ------------------------------------------------------------------ clock taps
    ck = t['clock']
    taps = [tp for tp in ck.get('taps', []) if tp['name'].split('.')[0] != OLD]
    tp_pos = {BODY: lambda b: (b[0] + b[2] / 2, b[1] + b[3] + 4.32),
              VM: lambda b: (b[0] + b[2] / 2, b[1] - 4.32)}
    for k in (BODY, VM):
        x, y = tp_pos[k](geo[k])
        ins, why = TAP_BUDGET[k]
        taps.append(dict(name=k, kind='core', xy=[round(x, 3), round(y, 3)], insertion_ps=ins,
                         budget_owner=MODS[k], note=f'PATH-HBM/NE2 BUDGET (no view yet): {why}'))
    ck['taps'] = taps

    # ------------------------------------------------------------------ latency: no die lane changes
    P1 = S.Plan(plan)
    chg = {}
    for lid, v in plan['latency']['lanes'].items():
        nv = P1.lane_latency(lid)
        if nv != lat0.get(lid):
            chg[lid] = dict(before=lat0.get(lid), after=nv)
    rep['lane_latency_changes'] = chg
    rep['not_done'] += [
        'second link (NLINK 2: W-EP N2/S3): link0+link1 tx/rx pins face the same q_hub link buses '
        '(L51_o/L52_i 612 b, L101_o/L126_i) as NW does for its 3 links; the die SerDes lanes for the 2nd link are '
        'not added in this step',
        'pin partners of master ports are the as-built q2 body core_conns (name level); ring/reduce/vm cut pins are '
        'bit-exact from the master parent view']
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--out', required=True)
    ap.add_argument('--body-cells', type=int, default=0)
    ap.add_argument('--vm-cells', type=int, default=0)
    a = ap.parse_args()
    cells = {BODY: a.body_cells, VM: a.vm_cells}
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
    rep = apply(plan, a.out, cc, cells)
    json.dump(cc, open(os.path.join(a.out, 'core_conns.json'), 'w'), indent=0)
    json.dump(plan, open(os.path.join(a.out, 'die_plan.json'), 'w'), indent=0)
    json.dump(rep, open(os.path.join(a.out, 'q_hub_ne_report.json'), 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in ('pieces', 'cells', 'stations', 'lane_latency_changes', 'master_internal_station_chains', 'links')},
                     indent=1))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""H-D4G3b GEN1 layer L2 (SU / SFU), 2026-10-18: contract post-layer on the d4g GEN0 source contract.

    l2_su_sfu.py IN.json[.gz] OUT.json --report R.json [--plan results/arch/hbm_die_d4g/plan/d4g_phy/compact.P.json]

(a) SFUS  sfus_<q> -> ot_hbm_su_static_sfustore_hw (RTL-BUILD-HBM/sfus, results/rtl/rbh_1018/sfus/d4g_binding.json): one
          clock root (clk_bank / clk_bank_macro removed), qid[1:0] identity strap SW 0 SE 1 NW 2 NE 3 (replaces QID),
          the 16-lane vi/kv buses split per lane l<NN>_*.  Latency: vi_q n+2 / write n+1 unchanged, fault n+2, reset +3.
(b) SUBR  subr_<q> -> ot_hbm_su_bridge_release_s (r2, single serial clock; closed view hbm_su_bridge_release_1018):
          clk_stream / rst_stream_n removed, bridge_rst_n / fault now serial-domain registers (fault leaf input gets its
          SYNC_MASK bit).  R1 fix: subr_SE/NW/NE.prog_busy <- pgp_<q>.busy (was pgp_SW.busy).
(c) STREE the 576 rfr_<w>_<d>_NN RF relay stages (16 routes x 36) -> SU scalar gather/broadcast tree (HBM-B-RTL1 su,
          ot_hbm_su_static_top RF_TREE=1, RF_TREE_UP = RF_TREE_DN = 14): stl_<q> ot_hbm_su_stree_leaf beside sucore_<q>,
          str_C ot_hbm_su_stree_root at the centroid of the four sucores, 14 up stations (41 b, hbfd_rly_48_<flow>, PAD
          41..47) and 14 down stations (164 b = hbfd_rly_136_<flow> bits 0..135 + hbfd_rly_48_<flow> bits 136..163, PAD
          28..47) per leg, planned homes evenly on the leg's L path.  Same structure as ot_hbm_su_stree_net (leg = N
          registered stages; hbfd_rly also clears data on reset, which the tree never reads while invalid).  Compiler: RF
          write latency 36 -> L_TREE = 14 + 14 + 4 = 32 (HBM-B-RTL1 lane note).
(d) CXPORT sucx_<q> (ot_hbm_su_static_cxport hub) -> the split leaves (HBM-SU3 / HBM-SU6, ot_hbm_su_static_cxport_split.sv):
          cxdl_<q><G> x4 (delivery lane G), cxij_<q> (inject), cxrc_<q> (red-carry + SFU operand), same params/edges as
          the hub (ot_hbm_su_static_cxport_split = hub ports, lockstep vs the hub); both leaf reset pins from
          subr_<q>.bridge_rst_n.  The six leaf faults (serial) feed a new fault leaf fcx_<q> (ot_hbm_fault_leaf N 6,
          SYNC_MASK 3f, stream) that drives the hub's old host_status.t_fault bit (+3 edges on a status-only path).
(f) SFUP  sfup_<q> stays ot_hgi_sfu_programme_store_r10 (r10n2 leaf RTL = HEAD; cluster is CRITICAL, coordinator gates
          it).  Checked, not changed: every cfg / io_cfg / io_start input of sfup_<q> comes from col_sfu_<q> with the same
          edge class, so the host contract (io_start_v >= 4 idle edges after the last IO write, 0 slack at IO2) holds iff
          the relay layer gives io_cfg_* and io_start_v EQUAL station counts (reported as constraint).
Not done here (reported): pgp_<q> -> pslice_c5 (pghead/pgcol_s r5) needs su_prog root_h SMACROS 4 x 320 RTL + pgcol_l r5;
pg_lg_tap is a child of ot_hbm_su_static_pgslice_lg (no die-level instance).
"""
import argparse, copy, gzip, json, re, sys

REGION = 'd4g_gen1_l2'
Q = ['SW', 'SE', 'NW', 'NE']
QID = {'SW': 0, 'SE': 1, 'NW': 2, 'NE': 3}
CK = 'hb_ckgen'
SER = ([CK, 'pll_serial'], [CK, 'por_serial'])
STR = ([CK, 'pll_stream'], [CK, 'por_stream'])
UP = DN = 14
SFUS_HW = 'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_sfustore_hw.sv'
SFUS_DEPS = ['rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_sfustore.sv',
             'rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_pinned_bank.sv',
             'rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_data_store.sv', 'rtl/lib/ot_rst_relay.sv']
SUBR_S = 'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_bridge_release_s.sv'
STREE = 'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_stree.sv'
CXS = 'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv'
RLY = 'rtl/hbm_accel/die_glue/hbfd_rly_masters.sv'
RLY_DEPS = ['rtl/hbm_accel/die_glue/ot_hbm_rly.sv', 'rtl/lib/ot_rst_relay.sv']
FLT = 'rtl/hbm_accel/die_glue/ot_hbm_fault_leaf.sv'


def ld(p):
    return json.load(gzip.open(p, 'rt') if p.endswith('.gz') else open(p))


def P(**kw):
    return {k: dict(direction=('output' if d == 'o' else 'input'), bits=b) for k, (d, b) in kw.items()}


def mkinst(master, source, deps, params, ports, note, slot=None, owner='H-D4G'):
    return dict(master=master, source=source, params=params, slot=slot, owner=owner, region=REGION, note=note,
                replaces_v15=None, rtl_deps=list(deps), ports=ports)


def mkedge(name, bits, src, snk, clock, basis):
    return dict(name=name, bits=bits, source=list(src), sink=list(snk), clock=clock, ready_or_credit=False,
                allowed_exception=None, basis=basis, region=REGION)


def cr(inst, port, dom, kind, src, bits=1, note=None):
    d = dict(instance=inst, port=port, bits=bits, domain=dom, kind=kind, source=list(src))
    if note:
        d['note'] = note
    return d


class Layer:
    def __init__(s, c):
        s.c = c
        s.I = c['instances']
        s.log = []

    # edge endpoints are [inst, port, lo, hi]
    def remap(s, inst, segs, basis, clock_of=None):
        """Re-target every edge end on `inst`: segs[port] = [(old_lo, old_hi, new_inst, new_port, new_lo)]."""
        out, n = [], 0
        for e in s.c['edges']:
            side = 'sink' if e['sink'][0] == inst else 'source' if e['source'][0] == inst else None
            if not side:
                out.append(e); continue
            other = 'source' if side == 'sink' else 'sink'
            _, port, lo, hi = e[side]
            ol = e[other]
            pieces = []
            for (a, b, ni, np_, nlo) in segs[port]:
                x, y = max(a, lo), min(b, hi)
                if x >= y:
                    continue
                pieces.append((x, y, ni, np_, nlo + x - a))
            if sum(y - x for x, y, *_ in pieces) != hi - lo:
                raise SystemExit(f'remap {inst}.{port}[{lo}:{hi}] not covered by segments')
            for k, (x, y, ni, np_, nl) in enumerate(pieces):
                ne = copy.deepcopy(e)
                ne[side] = [ni, np_, nl, nl + y - x]
                ne[other] = [ol[0], ol[1], ol[2] + x - lo, ol[2] + y - lo]
                ne['bits'] = y - x
                if len(pieces) > 1:
                    ne['name'] = f"{e['name']}__{ni}_{np_}"
                if clock_of:
                    ne['clock'] = clock_of(ne) or ne['clock']
                ne['basis'] = (ne.get('basis') or '') + f' | {basis}'
                out.append(ne); n += 1
        s.c['edges'] = out
        return n

    def drop(s, inst):
        s.I.pop(inst)
        s.c['clock_resets'] = [r for r in s.c['clock_resets'] if r['instance'] != inst]
        s.c['straps'] = [t for t in s.c['straps'] if t['inst'] != inst]
        s.c['open_outputs'] = [o for o in s.c['open_outputs'] if o[0] != inst]

    def edges_on(s, inst):
        return [e for e in s.c['edges'] if inst in (e['source'][0], e['sink'][0])]


def plan_centre(plan, name):
    b = plan[name]
    return b['x'] + b['w'] / 2, b['y'] + b['h'] / 2


def lpath_points(a, b, n):
    """n evenly spaced points on the L path a -> b (vertical leg first), with the flow of the segment they sit on."""
    (ax, ay), (bx, by) = a, b
    ly, lx = abs(by - ay), abs(bx - ax)
    tot = ly + lx
    pts = []
    for k in range(n):
        d = tot * (k + 1) / (n + 1)
        if d <= ly:
            x, y = ax, ay + (d if by >= ay else -d)
            flow = 'SN' if by >= ay else 'NS'
        else:
            x, y = ax + ((d - ly) if bx >= ax else -(d - ly)), by
            flow = 'WE' if bx >= ax else 'EW'
        pts.append((round(x, 3), round(y, 3), flow))
    return pts, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--plan', default='results/arch/hbm_die_d4g/plan/d4g_phy/compact.P.json')
    a = ap.parse_args()
    c = ld(a.inp)
    L = Layer(c)
    I = L.I
    plan = json.load(open(a.plan))
    rep = dict(schema='opentallas.hbm.d4g.gen1_layer.v1', layer='l2_su_sfu', input=a.inp, before=dict(
        instances=len(I), edges=len(c['edges']), edge_bits=sum(e['bits'] for e in c['edges'])), parts={})

    # ---------------------------------------------------------------- (a) sfus -> sfustore_hw
    LW = dict(vi_re=('i', 1), vi_addr=('i', 24), vi_q=('o', 32), kv_we=('i', 1), kv_waddr=('i', 24), kv_wdata=('i', 32))
    na = 0
    for q in Q:
        n = f'sfus_{q}'
        old = I[n]
        assert old['master'] == 'ot_hbm_su_static_sfustore' and old['params'].get('QID') == QID[q], (n, old['params'])
        ports = P(clk=('i', 1), rst_n=('i', 1), qid=('i', 2))
        segs = {}
        for p_, (d, w) in LW.items():
            segs[p_] = []
            for ln in range(16):
                ports[f'l{ln:02d}_{p_}'] = dict(direction='output' if d == 'o' else 'input', bits=w)
                segs[p_].append((ln * w, (ln + 1) * w, n, f'l{ln:02d}_{p_}', 0))
        ports['fault'] = dict(direction='output', bits=1)
        segs['fault'] = [(0, 1, n, 'fault', 0)]
        I[n] = mkinst('ot_hbm_su_static_sfustore_hw', SFUS_HW, SFUS_DEPS, {}, ports,
                      f'{old.get("note") or ""} | {REGION}: remastered ot_hbm_su_static_sfustore -> ot_hbm_su_static_sfustore_hw '
                      f'(RTL-BUILD-HBM/sfus d4g_binding.json; one clk root, qid strap {QID[q]}, per-lane buses; kit '
                      f'physical/ref_tile/hbm_su_sfustore_hw_1018: tile faces sfucore_{q} N with its S face)'.lstrip(' |'),
                      slot=old.get('slot'), owner=old.get('owner') or 'H-SU')
        na += L.remap(n, segs, 'd4g_gen1_l2 (a) sfus lane split')
        c['clock_resets'] = [r for r in c['clock_resets'] if not (r['instance'] == n and r['port'] in ('clk_bank', 'clk_bank_macro'))]
        c['straps'].append(dict(inst=n, port='qid', value=QID[q], lo=0, hi=2, master='ot_hbm_su_static_sfustore_hw',
                                reason=f'identity: SU quarter id of sfus_{q} (element address a[15:14] == sfucore_{q} quarter)'))
    rep['parts']['a_sfus'] = dict(instances=4, edges_rewritten=na, removed_ports=['clk_bank', 'clk_bank_macro'],
                                  latency='vi_q n+2, write n+1 unchanged; fault n+2 (was n+1); reset release +3 stream edges')

    # ---------------------------------------------------------------- (b) subr -> bridge_release_s + prog_busy R1 fix
    fixes = []
    for q in Q:
        n = f'subr_{q}'
        old = I[n]
        assert old['master'] == 'ot_hbm_su_bridge_release'
        I[n] = mkinst('ot_hbm_su_bridge_release_s', SUBR_S, [], {'MUT': 0},
                      P(clk_serial=('i', 1), rst_n=('i', 1), prog_busy=('i', 1), bridge_rst_n=('o', 1), fault=('o', 1)),
                      f'{REGION}: r2 single-serial-clock bridge release (hbm_su_bridge_release_1018 r2 CLOSED; serial->stream '
                      f'hold fix); bridge_rst_n is an async reset to su_{q}0..3 + the cxport leaves: buffered (repeaters), '
                      f'never a registered relay | was: {old.get("note", "")[:160]}', slot=old.get('slot'), owner=old.get('owner'))
        c['clock_resets'] = [r for r in c['clock_resets'] if not (r['instance'] == n and r['port'] in ('clk_stream', 'rst_stream_n'))]
        for e in c['edges']:
            if e['source'][0] == n and e['source'][1] in ('bridge_rst_n', 'fault'):
                e['clock'] = 'serial'
            if e['sink'][:2] == [n, 'prog_busy'] and e['source'][0] != f'pgp_{q}':
                was = e['source'][0]
                e['source'] = [f'pgp_{q}', 'busy', 0, 1]
                e['name'] = f"{e['name'].split('__')[0]}__pgp_{q}_busy"
                e['basis'] = (e.get('basis') or '') + f' | {REGION} (b) R1: own quadrant programme busy (was {was}.busy)'
                fixes.append([f'pgp_{q}.busy', f'{n}.prog_busy', f'was {was}.busy'])
                c['open_outputs'] = [o for o in c['open_outputs'] if o[:2] != [f'pgp_{q}', 'busy']]
        # the fault leaf input fed by subr_<q>.fault is now a serial-domain sticky level: synchronise it
        for e in c['edges']:
            if e['source'][:2] == [n, 'fault'] and I[e['sink'][0]]['master'] == 'ot_hbm_fault_leaf':
                fl = I[e['sink'][0]]
                m = int(str(fl['params']['SYNC_MASK']).split("'h")[-1], 16) | (1 << e['sink'][2])
                fl['params']['SYNC_MASK'] = f"64'h{m:x}"
    rep['parts']['b_subr'] = dict(instances=4, master='ot_hbm_su_bridge_release_s', prog_busy_rebind=fixes,
                                  fault_sync='fault-leaf SYNC_MASK bit set on the subr input (fault now serial)')

    # ---------------------------------------------------------------- (c) RF relay chains -> scalar tree
    rfr = sorted(n for n in I if re.match(r'rfr_(SW|SE|NW|NE)_(SW|SE|NW|NE)_\d+$', n))
    rfr_bits = sum(e['bits'] for e in c['edges'] if e['source'][0] in rfr or e['sink'][0] in rfr)
    keep_e = []
    gone_e = 0
    for e in c['edges']:
        if e['source'][0] in rfr or e['sink'][0] in rfr:
            gone_e += 1
        else:
            keep_e.append(e)
    c['edges'] = keep_e
    for n in rfr:
        L.drop(n)
    cen = {q: plan_centre(plan, f'sucore_{q}') for q in Q}
    root = (round(sum(x for x, _ in cen.values()) / 4, 3), round(sum(y for _, y in cen.values()) / 4, 3))
    bas = f'{REGION} (c) SU scalar tree (ot_hbm_su_stree_net, RF_TREE=1, UP=DN={UP})'
    I['str_C'] = mkinst('ot_hbm_su_stree_root', STREE, [], {'MUT': 0},
                        P(clk=('i', 1), rst_n=('i', 1), up0_i=('i', 41), up1_i=('i', 41), up2_i=('i', 41), up3_i=('i', 41),
                          dn0_o=('o', 164), dn1_o=('o', 164), dn2_o=('o', 164), dn3_o=('o', 164)),
                        f'SU scalar tree root (closed view hbm_su_stree_root_1017); centroid of the four sucores '
                        f'({root[0]:.3f}, {root[1]:.3f}) um; leg q = quadrant q (0 SW 1 SE 2 NW 3 NE)', owner='HBM-B-RTL1')
    c['clock_resets'] += [cr('str_C', 'clk', 'serial', 'clock', SER[0]), cr('str_C', 'rst_n', 'serial', 'reset', SER[1])]
    legs = {}
    nst = 0
    for qi, q in enumerate(Q):
        lf = f'stl_{q}'
        I[lf] = mkinst('ot_hbm_su_stree_leaf', STREE, [], {'MUT': 0},
                       P(clk=('i', 1), rst_n=('i', 1), head_i=('i', 41), up_o=('o', 41), dn_i=('i', 164), rf_wv=('o', 4),
                         rf_wa=('o', 32), rf_wd=('o', 128)),
                       f'SU scalar tree leaf of quadrant {q} (closed view hbm_su_stree_leaf_1017): head = sucore_{q} reducer, '
                       f'rf_w* = all four reducers\' words for sucore_{q} (as the d4f relay routes w -> {q})',
                       slot=f'sucore_{q}', owner='HBM-B-RTL1')
        c['clock_resets'] += [cr(lf, 'clk', 'serial', 'clock', SER[0]), cr(lf, 'rst_n', 'serial', 'reset', SER[1])]
        E = c['edges']
        E += [mkedge(f'stree_{q}_head_x', 32, [f'sucore_{q}', 'red_x', 0, 32], [lf, 'head_i', 0, 32], 'serial', bas),
              mkedge(f'stree_{q}_head_tag', 8, [f'sucore_{q}', 'red_tag', 0, 8], [lf, 'head_i', 32, 40], 'serial', bas),
              mkedge(f'stree_{q}_head_v', 1, [f'sucore_{q}', 'red_rf_v', 0, 1], [lf, 'head_i', 40, 41], 'serial', bas),
              mkedge(f'stree_{q}_rf_wv', 4, [lf, 'rf_wv', 0, 4], [f'sucore_{q}', 'rf_wv', 0, 4], 'serial', bas),
              mkedge(f'stree_{q}_rf_wa', 32, [lf, 'rf_wa', 0, 32], [f'sucore_{q}', 'rf_wa', 0, 32], 'serial', bas),
              mkedge(f'stree_{q}_rf_wd', 128, [lf, 'rf_wd', 0, 128], [f'sucore_{q}', 'rf_wd', 0, 128], 'serial', bas)]
        # up leg: leaf -> root, 14 stations of 41 b
        pts, length = lpath_points(cen[q], root, UP)
        prev = [lf, 'up_o', 0, 41]
        for k, (x, y, fl) in enumerate(pts):
            s_ = f'stu_{q}_{k:02d}'
            I[s_] = mkinst(f'hbfd_rly_48_{fl}', RLY, RLY_DEPS, {}, P(ck=('i', 1), rs=('i', 1), i=('i', 48), o=('o', 48)),
                           f'SU tree up leg {q} station {k}/{UP}; home ({x:.3f}, {y:.3f}) um', owner='H-D4G')
            c['clock_resets'] += [cr(s_, 'ck', 'serial', 'clock', SER[0]), cr(s_, 'rs', 'serial', 'reset', SER[1])]
            c['straps'].append(dict(inst=s_, port='i', lo=41, hi=48, value=0, master=f'hbfd_rly_48_{fl}',
                                    reason='PAD (DEDUPE standard relay hbfd_rly_48, logical width 41, spare bits 41..47 tied low; outputs 41..47 open)'))
            E.append(mkedge(f'stree_{q}_up{k:02d}', 41, prev, [s_, 'i', 0, 41], 'serial', bas))
            prev = [s_, 'o', 0, 41]; nst += 1
        E.append(mkedge(f'stree_{q}_up_root', 41, prev, ['str_C', f'up{qi}_i', 0, 41], 'serial', bas))
        # down leg: root -> leaf, 14 stations of 164 b (136 + 28 of a 48)
        pts, _ = lpath_points(root, cen[q], DN)
        pa, pb = ['str_C', f'dn{qi}_o', 0, 136], ['str_C', f'dn{qi}_o', 136, 164]
        for k, (x, y, fl) in enumerate(pts):
            sa, sb = f'std_{q}_{k:02d}a', f'std_{q}_{k:02d}b'
            I[sa] = mkinst(f'hbfd_rly_136_{fl}', RLY, RLY_DEPS, {}, P(ck=('i', 1), rs=('i', 1), i=('i', 136), o=('o', 136)),
                           f'SU tree down leg {q} station {k}/{DN} bits 0..135; home ({x:.3f}, {y:.3f}) um', owner='H-D4G')
            I[sb] = mkinst(f'hbfd_rly_48_{fl}', RLY, RLY_DEPS, {}, P(ck=('i', 1), rs=('i', 1), i=('i', 48), o=('o', 48)),
                           f'SU tree down leg {q} station {k}/{DN} bits 136..163; home ({x:.3f}, {y + 21.6:.3f}) um', owner='H-D4G')
            for s_ in (sa, sb):
                c['clock_resets'] += [cr(s_, 'ck', 'serial', 'clock', SER[0]), cr(s_, 'rs', 'serial', 'reset', SER[1])]
            c['straps'].append(dict(inst=sb, port='i', lo=28, hi=48, value=0, master=f'hbfd_rly_48_{fl}',
                                    reason='PAD (DEDUPE standard relay hbfd_rly_48, logical width 28, spare bits 28..47 tied low; outputs 28..47 open)'))
            E.append(mkedge(f'stree_{q}_dn{k:02d}a', 136, pa, [sa, 'i', 0, 136], 'serial', bas))
            E.append(mkedge(f'stree_{q}_dn{k:02d}b', 28, pb, [sb, 'i', 0, 28], 'serial', bas))
            pa, pb = [sa, 'o', 0, 136], [sb, 'o', 0, 28]; nst += 2
        E.append(mkedge(f'stree_{q}_dn_leafa', 136, pa, [lf, 'dn_i', 0, 136], 'serial', bas))
        E.append(mkedge(f'stree_{q}_dn_leafb', 28, pb, [lf, 'dn_i', 136, 164], 'serial', bas))
        legs[q] = dict(leaf_at=[round(v, 1) for v in cen[q]], leg_um=round(length, 1), um_per_hop=round(length / (UP + 1), 1))
    rep['parts']['c_stree'] = dict(removed_relays=len(rfr), removed_edges=gone_e, removed_edge_bits=rfr_bits,
                                   added=dict(leaves=4, root=1, stations=nst), root_at=list(root), legs=legs,
                                   compiler='RF write 36 -> 32 edges (L_TREE = UP + DN + 4); HBM-B-RTL1 su lane note',
                                   reach_note='leg hops > 405 um planning reach: within the measured repeated 600-750 um '
                                              '(memory reach-405-repeaters-1016); the die repeater pass must hold them')

    # ---------------------------------------------------------------- (d) cxport hub -> split leaves
    for q in Q:
        n = f'sucx_{q}'
        old = I[n]
        pr = old['params']
        dl = [f'cxdl_{q}{g}' for g in range(4)]
        ij, rc, fx = f'cxij_{q}', f'cxrc_{q}', f'fcx_{q}'
        ck4 = dict(clk_s=('i', 1), clk_q=('i', 1), rst_s_n=('i', 1), rst_q_n=('i', 1))
        for g, d in enumerate(dl):
            I[d] = mkinst('ot_hbm_su_static_cxport_dl', CXS, [], {'QID': pr['QID'], 'G': g},
                          P(**ck4, del_valid=('i', 1), del_flit=('i', 545), del_obase=('i', 40), dw_v=('o', 2),
                            dw_row=('o', 18), dw_d=('o', 1024), fault=('o', 1)),
                          f'{REGION}: SU COLL delivery leaf lane {g} of sucx_{q} (kit hbm_su_cx_dl_1017); beside su_{q}{g}',
                          slot=None, owner='HBM-SU6')
        I[ij] = mkinst('ot_hbm_su_static_cxport_ij', CXS, [],
                       {k: pr[k] for k in ('QID', 'B39_NOOP', 'INJ_RET', 'RQ', 'RQC', 'SD') if k in pr},
                       P(**ck4, inj_rd=('i', 2), inj_addr=('i', 160), inj_d=('o', 1024), inj_q0=('i', 1024), inj_q1=('i', 1024),
                         inj_q2=('i', 1024), inj_q3=('i', 1024), fault=('o', 1)),
                       f'{REGION}: SU COLL inject leaf of sucx_{q} (kit hbm_su_cx_ij_1017)', owner='HBM-SU6')
        I[rc] = mkinst('ot_hbm_su_static_cxport_rc', CXS, [], {},
                       P(**ck4, rc_v=('o', 1), rc_tag=('o', 3), rc_d=('o', 256), rr_v=('i', 1), rr_tag=('i', 3), rr_d=('i', 256),
                         red_sv=('i', 1), red_tag=('i', 32), red_x=('i', 32), rr_wv=('o', 1), rr_wa=('o', 5), rr_wd=('o', 256),
                         ro_v=('i', 16), ro_x=('i', 512), red_sel=('i', 12), sfu_x=('o', 32), fault=('o', 1)),
                       f'{REGION}: SU COLL red-carry + SFU operand leaf of sucx_{q} (kit hbm_su_cx_rc_1017); beside sucore_{q}',
                       owner='HBM-SU6')
        I[fx] = mkinst('ot_hbm_fault_leaf', FLT, [], {'N': 6, 'SYNC_MASK': "64'h3f"},
                       P(clk=('i', 1), rst_n=('i', 1), **{'in': ('i', 6)}, fault=('o', 1)),
                       f'{REGION}: fault leaf of the six cxport leaves of quadrant {q} (in 0..3 dl, 4 ij, 5 rc; serial '
                       f'sticky levels, synchronised); drives the hub\'s old host_status.t_fault bit', owner='H-D4G')
        segs = dict(
            del_valid=[(g, g + 1, dl[g], 'del_valid', 0) for g in range(4)],
            del_flit=[(545 * g, 545 * (g + 1), dl[g], 'del_flit', 0) for g in range(4)],
            del_obase=[(40 * g, 40 * (g + 1), dl[g], 'del_obase', 0) for g in range(4)],
            dw_v=[(2 * g, 2 * g + 2, dl[g], 'dw_v', 0) for g in range(4)],
            dw_row=[(18 * g, 18 * g + 18, dl[g], 'dw_row', 0) for g in range(4)],
            dw_d=[(1024 * g, 1024 * (g + 1), dl[g], 'dw_d', 0) for g in range(4)],
            inj_q=[(1024 * g, 1024 * (g + 1), ij, f'inj_q{g}', 0) for g in range(4)],
            inj_rd=[(0, 2, ij, 'inj_rd', 0)], inj_addr=[(0, 160, ij, 'inj_addr', 0)], inj_d=[(0, 1024, ij, 'inj_d', 0)],
            fault=[(0, 1, fx, 'fault', 0)])
        for p_, w in dict(rc_v=1, rc_tag=3, rc_d=256, rr_v=1, rr_tag=3, rr_d=256, red_sv=1, red_tag=32, red_x=32, rr_wv=1,
                          rr_wa=5, rr_wd=256, ro_v=16, ro_x=512, red_sel=12, sfu_x=32).items():
            segs[p_] = [(0, w, rc, p_, 0)]
        # reset: the hub's rst_n edge (subr_<q>.bridge_rst_n) fans to rst_s_n + rst_q_n of every leaf
        rst = [e for e in c['edges'] if e['sink'][:2] == [n, 'rst_n']]
        assert len(rst) == 1 and rst[0]['source'][:2] == [f'subr_{q}', 'bridge_rst_n'], rst
        c['edges'].remove(rst[0])
        nrw = L.remap(n, segs, f'{REGION} (d) cxport split')
        for lf_ in dl + [ij, rc]:
            for rp in ('rst_s_n', 'rst_q_n'):
                c['edges'].append(mkedge(f'cxsplit_{lf_}_{rp}', 1, [f'subr_{q}', 'bridge_rst_n', 0, 1], [lf_, rp, 0, 1],
                                         'serial', f'{REGION} (d) epoch reset per domain = bridge_rst_n (split RTL header)'))
        for k, lf_ in enumerate(dl + [ij, rc]):
            c['edges'].append(mkedge(f'cxsplit_{lf_}_fault', 1, [lf_, 'fault', 0, 1], [fx, 'in', k, k + 1], 'serial',
                                     f'{REGION} (d) leaf fault -> fcx_{q}'))
        ck_q = next(r for r in c['clock_resets'] if r['instance'] == n and r['port'] == 'clk_q')['source']
        ck_s = next(r for r in c['clock_resets'] if r['instance'] == n and r['port'] == 'clk_s')['source']
        L.drop(n)
        for lf_ in dl + [ij, rc]:
            c['clock_resets'] += [cr(lf_, 'clk_s', 'stream', 'clock', ck_s), cr(lf_, 'clk_q', 'serial', 'clock', ck_q)]
        c['clock_resets'] += [cr(fx, 'clk', 'stream', 'clock', STR[0]), cr(fx, 'rst_n', 'stream', 'reset', STR[1])]
        rep['parts'].setdefault('d_cxport', {})[q] = dict(leaves=dl + [ij, rc], fault_leaf=fx, edges_rewritten=nrw,
                                                          params=dict(ij=I[ij]['params']))
    rep['parts']['d_cxport']['note'] = ('hub fault -> host_status now via fcx_<q> (+3 edges, status only); leaf params = hub '
                                        'params (ij INJ_RET per quadrant as GEN0); no closed leaf views on main yet -> SYNTH')

    # ---------------------------------------------------------------- (f) sfup check (no change)
    chk = {}
    for q in Q:
        n = f'sfup_{q}'
        assert I[n]['master'] == 'ot_hgi_sfu_programme_store_r10'
        srcs = {e['sink'][1]: e['source'][0] for e in c['edges'] if e['sink'][0] == n}
        chk[q] = dict(io_cfg_we=srcs.get('io_cfg_we'), io_start_v=srcs.get('io_start_v'),
                      same_source=srcs.get('io_cfg_we') == srcs.get('io_start_v') == f'col_sfu_{q}')
    rep['parts']['f_sfup'] = dict(check=chk, constraint='relay layer: equal station count on col_sfu_<q> -> sfup_<q> '
                                  'io_cfg_* and io_start_v (host contract io_start_v >= 4 idle edges after the last IO write, '
                                  '0 slack at IO2, r10n2)', master='ot_hgi_sfu_programme_store_r10 (r10n2 leaf RTL), SYNTH; '
                                  'cluster hbm_sfu_programme_store_r10_cl CRITICAL (coordinator)')
    rep['not_done'] = dict(
        pgcol_s_pghead_r5='pgp_<q> -> ot_hbm_su_programme_pslice_c5 needs su_prog root_h SMACROS 4 x 320 (c5 cfg bank = '
                          'column*32 + local; root_h decodes 4 x 98) + compiler config lowering (--columns) + pgcol_l r5 '
                          'closure + cluster kit: pgp_<q> stays pslice_q4',
        pg_lg_tap='child of ot_hbm_su_static_pgslice_lg (su_<q><k>); no die-level instance; child view binding at the '
                  'pgslice_lg cluster (nf3-lgtap 01e4965c3 fix not merged)')

    # ---------------------------------------------------------------- bookkeeping
    c['summary']['instances'] = len(I)
    c['summary']['masters'] = len({v['master'] for v in I.values()})
    c['summary']['edges'] = len(c['edges'])
    c['summary']['edge_bits'] = sum(e['bits'] for e in c['edges'])
    c['summary']['straps'] = len(c['straps'])
    c['summary']['clock_reset_ports'] = len(c['clock_resets'])
    c['summary']['open_output_ports'] = len(c['open_outputs'])
    c['masters'] = dict(sorted(__import__('collections').Counter(v['master'] for v in I.values()).items()))
    note = (f'{REGION} (H-D4G3b fork B): sfus -> sfustore_hw x4 (qid strap, lane split); subr -> bridge_release_s r2 + '
            f'prog_busy R1 rebind x3; {len(rfr)} rfr relays -> SU scalar tree (4 leaves + root + {nst} leg stations, '
            f'UP=DN={UP}); sucx -> cxport dl x4 + ij + rc + fcx fault leaf per quadrant; sfup r10 unchanged (checked)')
    if isinstance(c.get('notes'), list):
        c['notes'].append(note)
    elif isinstance(c.get('notes'), dict):
        c['notes'][REGION] = note
    else:
        c['notes'] = [note]
    rep['after'] = dict(instances=len(I), edges=len(c['edges']), edge_bits=c['summary']['edge_bits'])
    json.dump(c, open(a.out, 'w'), indent=None)
    json.dump(rep, open(a.report, 'w'), indent=1)
    print(json.dumps(dict(before=rep['before'], after=rep['after'], stree=rep['parts']['c_stree']['added'],
                          prog_busy=len(fixes))))


if __name__ == '__main__':
    main()

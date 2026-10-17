"""DIAGNOSTIC dv2r8f2 die case (Q-DIEPLAN3 2026-10-17; Q-DV adopted geometry, Q-CLUSTER cluster 2,285.28 x 5,184).

apply_dv(v, m) runs in qwen_rom_fulldie_b3r2.selected() right after the q3h hook (OT_SPLIT_Q3H=1 + grid/contract), when
OT_SPLIT_DV=<dv model json> is set.  The q3h model carries the REAL ports of every retained master; Q-DV's model
(results/arch/qwen_dv_1016/dv2r8f2.json, instance-level, no ports) gives the geometry and the new connectivity, and its
bus map (bus_map_dv2r8f2.json, roles in Q-DV's 10-17 message) the port roles:

  * removed: every instance the dv model does not place (VM, SU, seq_su, xs_tap, cbuf/crom, column heads, port halves,
    halfbands, res trains, word status, upper leaves, forks, ...) and every bus that ends only on them;
  * retained: positions from the dv model, ports unchanged;
  * clusters: qfd_c_b16_dv = the CB contract ports scaled to the Q-CLUSTER width + rs_i (N) / rs_o (S) in corridor T;
  * slices: 12 x qfd_dv_slice2, SYNTHETIC role ports (slice RTL step 2 pending): cw_n0..3 / rs_n0..1 on N (band 2),
    cw_s0..3 / rs_s0..1 on S (band 1), st_dn_o / ch_dn_o / ch_dn_i / l9_w_* / hr_i on W, st_dn_i / ch_up_i / ch_up_o /
    l9_e_* / hr_o / st_up_o on E (dn = toward W5 = west, up = east), ck / rst_n on N, W5 re-home ports r_<bus> on W;
  * W-column re-partition (open in RTL): every q3h bus that joined a retained W-column master (collective, native59,
    tt_ctlm, embed_prov, sys_face) to a removed master is re-homed to dvs_W5 (port r_<bus>, same width), so the real
    port of the retained master is kept;
  * clocks / resets: the q3h trunks without the removed sinks + one ck / rst_n per slice (regions re-filed from the
    placement afterwards).
The strict port bind fails by construction (synthetic slice ports, qfd_c_b16_dv not on the source): chains run
OT_CHAIN_DIAGNOSTIC=1.  Relay planning, per-bit reach, GRT and die STA are real on this geometry.
"""
import json
import os
import re
from pathlib import Path

from qwen_split import q3h_cluster as Q

SLICE = 'qfd_dv_slice2'
CDV = 'qfd_c_b16_dv'
WCOL = ('io_collective', 'native59', 'tt_ctlm', 'embed_prov', 'sys_face')


def _load(env):
    p = os.environ.get(env, '').strip()
    return json.loads(Path(p).read_text()) if p else None


def _place(q, ports, w, h, fixed=None):
    """synthetic pin frame: ports with a fixed [lo, hi] range (mirrored abutting pins) spread over it; the rest per face
    packed at the 0.192 pitch (<= 6 pins/um), centred, on track"""
    fixed = fixed or {}
    for p, (bits, face) in ports.items():
        if p in fixed:
            a_, b_ = fixed[p]
            ps = [Q._trk(a_ + (b_ - a_) * k / max(1, bits - 1)) for k in range(bits)]
            q.ports[p] = ('pins', bits, face, 'M5' if face in 'NS' else 'M4', ps, 1)
            q.order.append(p)
    faces = {}
    for p, (bits, face) in ports.items():
        if p not in fixed:
            faces.setdefault(face, []).append((p, bits))
    for f, items in faces.items():
        L = w if f in 'NS' else h
        need = sum((b - 1) * Q.PITCH + 4.0 for _, b in items)
        if need > L - 8.0:
            raise ValueError(f'dv slice {f} face: {need:.0f} um of pins exceed {L:.0f}')
        cur = (L - need) / 2 if f in 'NS' else 40.0     # W / E: one fixed start, so facing slots line up
        for p, b in items:
            ps = [Q._trk(cur + k * Q.PITCH) for k in range(b)]
            q.ports[p] = ('pins', b, f, 'M5' if f in 'NS' else 'M4', ps, 1)
            q.order.append(p)
            cur = ps[-1] + 4.0


def apply_dv(v, m):
    D = _load('OT_SPLIT_DV')
    C = _load('OT_SPLIT_Q3H_CONTRACT')
    CWN = float(D.get('cluster_w', 2285.28))
    DI = {i['n']: i for i in D['insts'] if i['m'] != 'outline_marker'}
    by = {i.name: i for i in m['insts']}
    # retained instances take the dv model's places BEFORE the masters are drawn (the collective / PHY frames follow
    # their instance outline: OT_SPLIT_PHY_TALL edge variants, collective re-kitted tall; PHYs above it are MX)
    tall = os.environ.get('OT_SPLIT_PHY_TALL') == '1'
    coll = DI.get('io_collective')
    for n, i in by.items():
        if n in DI and not n.startswith('c16_'):
            i.x, i.y = DI[n]['x'], DI[n]['y']
            if tall and (n == 'io_collective' or n.startswith(('io_serdes', 'io_ucie'))):
                i.w, i.h = DI[n]['w'], DI[n]['h']
                if n != 'io_collective' and coll and DI[n]['y'] >= coll['y'] + coll['h'] - 1e-3:
                    i.orient = 'MX'
    M = v.masters(m, 1)
    if tall:
        # the frozen master set (b2 / q3h wrappers) still holds the collective / PHY frames of the old outline
        from qwen_split import native_static_io_bind as NB
        m['dv_io_placed'] = True
        NB.install_master(M, m, v.Master)
    # ---- cluster master: Q-CLUSTER's dv contract (OT_SPLIT_DV_CONTRACT, cluster_contract_dv.json: ports / faces /
    # ranges incl. rs_i / rs_o and the four quadrant clock entries); without it the CB contract scaled + rs_i / rs_o
    CD = _load('OT_SPLIT_DV_CONTRACT')
    ck_pins = ['ck']
    if CD:
        CWN, ch = CD['outline_um']['w'], CD['outline_um']['h']
        dirs = {'bco': 'output', 'rs_o': 'output', 'rs': 'output', 'tie_hi': 'output', 'tie_lo': 'output'}
        ports = {}
        for p_ in CD['ports']:
            n_ = p_['port']
            d_ = dirs.get(n_) or ('output' if n_.startswith('bco') else 'input')
            ports[n_] = dict(dir=d_, bits=p_['bits'], face=p_['face'], layer=p_['layer'], range=list(p_['range_um']))
        ck_pins = [p for p in ports if p.startswith('ck')]
    else:
        sc = CWN / C['outline_um']['w']
        ports = Q._contract_ports(C)
        for p, d in ports.items():
            d['range'] = [round(d['range'][0] * sc, 3), round(d['range'][1] * sc, 3)]
        rs = ports['rs']['range']
        ports['rs_i'] = dict(dir='input', bits=514, face='N', layer='M5', range=[rs[0], rs[0] + 513 * Q.PITCH])
        ports['rs_o'] = dict(dir='output', bits=514, face='S', layer='M5',
                             range=[round(rs[1] + 6.0, 3), round(rs[1] + 6.0 + 513 * Q.PITCH, 3)])
        ch = 5184.0
    M[CDV] = Q._master(v, CWN - Q.SHAVE, ch - Q.SHAVE, ports)
    M[CDV].name = CDV
    # ---- slice master (synthetic role ports)
    sw, sh = DI['dvs_W0']['w'], DI['dvs_W0']['h']
    # slice ports (SYNTHETIC, Q-DV roles): N / S faces MIRROR the abutting clusters' S-face pins (bc<lc> -> cw_*<lc>,
    # rs -> rs_*0, rs_o -> rs_*1 at the contract's exact x ranges: face to face, no die wire, Q-DV dv2r8f5 slice_abut);
    # W / E faces are SYMMETRIC (each side has an in and an out of every lateral kind) so one master serves the W row
    # (R0) and the E row (MY, mirroring the MY / R180 clusters): a link takes the ports on the die faces that face
    sp = {}
    fixed_rng = {}
    rng = {p_['port']: p_['range_um'] for p_ in (CD['ports'] if CD else [])}
    for f, tag in (('N', 'n'), ('S', 's')):
        for k in range(4):
            sp[f'cw_{tag}{k}'] = (516, f)
            if f'bc{k}' in rng:
                fixed_rng[f'cw_{tag}{k}'] = rng[f'bc{k}']
        for k, src in ((0, 'rs'), (1, 'rs_o')):
            sp[f'rs_{tag}{k}'] = (514, f)
            if src in rng:
                fixed_rng[f'rs_{tag}{k}'] = rng[src]
    LAT = dict(st=1136, ch=1094, l9=514, hr=453, cmd=116)
    # abutted neighbours face each other: W-face (in, out) slot k lines up with the E-face (out, in) slot k
    for kind, bits in LAT.items():
        sp[f'{kind}_wi'] = (bits, 'W')
        sp[f'{kind}_wo'] = (bits, 'W')
    for kind, bits in LAT.items():
        sp[f'{kind}_eo'] = (bits, 'E')
        sp[f'{kind}_ei'] = (bits, 'E')
    sp.update({'ck': (1, 'W'), 'rst_n': (1, 'W')})
    # W5 re-home ports (one per re-homed q3h bus, same width) go on the W face too
    removed = {n for n in by if n not in DI}
    rehome = []
    for bid, cl, bits, eps in m['buses']:
        if cl in ('clock_trunk', 'reset'):
            continue
        ins = {i for i, _ in eps}
        if ins & removed and ins & set(WCOL) and not ins - removed - set(WCOL):
            rehome.append((bid, cl, bits, eps))
    # Q-DV role table: only the W5 chain ends are re-homed, at their bit widths (W5 ch_dn_o AR 546 -> collective,
    # collective 518 -> W5; W5 D2D 548 -> native59, native59 520 -> W5; tt_ctlm hr 453 + cmd 116 = 569 -> W5); every other q3h port of a
    # retained W-column master whose peer was removed stays OPEN (the re-partition is not in RTL yet).  Budgets are
    # filled with the largest q3h buses of that master and direction (diagnostic stand-ins for the role words).
    budget = {('io_collective', 'in'): 546, ('io_collective', 'out'): 518, ('native59', 'in'): 548,
              ('native59', 'out'): 520, ('tt_ctlm', 'out'): 569}
    pick = []
    for bid, cl, bits, eps in sorted(rehome, key=lambda t: -t[2]):
        drv = eps[0][0]
        key = (drv, 'out') if drv in WCOL else (next((i for i, _ in eps if i in WCOL), None), 'in')
        if key in budget and budget[key] >= bits:
            budget[key] -= bits
            pick.append((bid, cl, bits, eps))
    rehome = pick
    # re-home ports fill the faces with room (W first: the W column is west), at the same 0.192 pitch
    room = {f: (sw if f in 'NS' else sh) - 8.0 - sum((b_ - 1) * Q.PITCH + 4.0 for b_, f_ in sp.values() if f_ == f)
            for f in 'WSNE'}
    for bid, cl, bits, eps in sorted(rehome, key=lambda t: -t[2]):
        need = (bits - 1) * Q.PITCH + 4.0
        f = next((f for f in 'WSNE' if room[f] >= need), None)
        if f is None:
            raise ValueError(f'dv slice: no face room for the re-home port of {bid} ({bits} b): {room}')
        sp[f'r_{bid}'] = (bits, f)
        room[f] -= need
    qs = v.Master(SLICE, sw - Q.SHAVE, sh - Q.SHAVE, 9, 'Q-DV slice2 (SYNTHETIC role ports, RTL step 2 pending)')
    _place(qs, sp, sw - Q.SHAVE, sh - Q.SHAVE, fixed_rng)
    M[SLICE] = qs
    # ---- instances: retained / clusters / slices at the dv model's positions
    keep = []
    for i in m['insts']:
        if i.name in removed:
            continue
        d = DI[i.name]
        i.x, i.y = d['x'], d['y']
        if i.name.startswith('c16_'):
            i.master, i.w, i.h = CDV, CWN - Q.SHAVE, ch - Q.SHAVE
        keep.append(i)
    have = {i.name for i in keep}
    for n, d in DI.items():
        if n in have:
            continue
        if d['m'] in (SLICE, 'qfd_dv_slice2'):
            keep.append(v.Inst(n, SLICE, d['x'], d['y'], sw - Q.SHAVE, sh - Q.SHAVE,
                               orient='MY' if n.startswith('dvs_E') else 'R0', kind='cluster', region='field',
                               domain='stream_1p2'))
        elif d['m'] == 'qfd_dv_lane_relay':
            continue                       # the relay planner places the lane relays itself
        else:
            raise ValueError(f'dv: instance {n} ({d["m"]}) not in the q3h model')
    m['insts'][:] = keep
    names = {i.name for i in keep}
    # final placement gate (fail closed): no two instances overlap
    srt = sorted(keep, key=lambda i: i.x)
    ovl = []
    for a_ in range(len(srt)):
        p_ = srt[a_]
        for q_ in srt[a_ + 1:]:
            if q_.x >= p_.x + p_.w - 1e-3:
                break
            if q_.y < p_.y + p_.h - 1e-3 and p_.y < q_.y + q_.h - 1e-3:
                ovl.append((p_.name, q_.name))
    if ovl:
        raise ValueError(f'dv: {len(ovl)} overlapping instances {ovl[:8]}')
    # ---- buses
    out, dropped = [], {}
    slices = sorted(n for n in names if n.startswith('dvs_'))
    for bid, cl, bits, eps in m['buses']:
        if cl in ('clock_trunk', 'reset'):
            e2 = [e for e in eps if e[0] in names]
            if cl == 'clock_trunk':           # a cluster's die clock entries (Q-CLUSTER: four quadrant pins)
                e2 = [x for e in e2 for x in ([(e[0], p) for p in ck_pins] if e[0].startswith('c16_') and e[1] == 'ck'
                                              else [e])]
            if cl == 'clock_trunk' and any(e[0].startswith('c16_') for e in e2):
                e2 += [(s, 'ck') for s in slices if not any(x == s for x, _ in e2)]
            if bid == 'rst_field':
                e2 += [(s, 'rst_n') for s in slices]
            if len(e2) > 1:
                out.append((bid, cl, bits, e2))
            continue
        if bid.startswith('bword') or bid.startswith('q3h_col_'):
            continue                       # replaced by the dv reduce / column words below
        if all(e[0] in names for e in eps):
            out.append((bid, cl, bits, eps))
            continue
        dropped[cl] = dropped.get(cl, 0) + 1
    for bid, cl, bits, eps in rehome:
        e2 = [e if e[0] not in removed else ('dvs_W5', f'r_{bid}') for e in eps]
        seen, e3 = set(), []
        for e in e2:
            if e not in seen:
                seen.add(e)
                e3.append(e)
        if len(e3) > 1:
            out.append((f'dvr_{bid}', cl, bits, e3))
    x_of = {n: DI[n]['x'] for n in DI}
    for bid, cl, bits, eps in D['buses']:
        if cl in ('clock_trunk', 'reset'):
            continue
        a = eps[0]
        if bid.startswith('q3h_col_'):
            c, band = map(int, bid.split('_')[2:4])
            lc = c % 4 if c < 24 else 3 - c % 4
            out.append((bid, 'tree_spine', 516, [(a, f'cw_{"s" if band == 1 else "n"}{lc}'), (eps[1], f'bc{lc}')]))
        elif bid.startswith('dv_rsi_'):
            out.append((bid, 'tree_spine', 514, [(eps[0], 'rs'), (eps[1], 'rs_i')]))
        elif bid.startswith('dv_rs_'):
            band = int(bid.rsplit('_', 1)[1])
            s = 's' if band == 1 else 'n'
            out.append((bid + '_a', 'tree_spine', 514, [(eps[0], 'rs'), (eps[1], f'rs_{s}0')]))
            out.append((bid + '_b', 'tree_spine', 514, [(eps[0], 'rs_o'), (eps[1], f'rs_{s}1')]))
        elif bid.startswith(('dv_l9_', 'dv_st_', 'dv_x0', 'dv_ch_')):
            wst, est = sorted(eps, key=lambda n: x_of[n])
            def lp(n, dieface, kind, d_):       # port on the die face of slice n (MY swaps the master W / E faces)
                f_ = dieface if not n.startswith('dvs_E') else {'W': 'E', 'E': 'W'}[dieface]
                return (n, f'{kind}_{f_.lower()}{d_}')
            if bid.startswith('dv_l9_'):
                src, dst = eps
                if src == wst:
                    out.append((bid, 'tree_spine', 514, [lp(src, 'E', 'l9', 'o'), lp(dst, 'W', 'l9', 'i')]))
                else:
                    out.append((bid, 'tree_spine', 514, [lp(src, 'W', 'l9', 'o'), lp(dst, 'E', 'l9', 'i')]))
            elif bid.startswith('dv_ch_'):
                out += [(bid + '_dn', 'tree_spine', 1094, [lp(est, 'W', 'ch', 'o'), lp(wst, 'E', 'ch', 'i')]),
                        (bid + '_up', 'tree_spine', 1094, [lp(wst, 'E', 'ch', 'o'), lp(est, 'W', 'ch', 'i')])]
            else:
                out += [(bid + '_dn', 'tree_spine', 1136, [lp(est, 'W', 'st', 'o'), lp(wst, 'E', 'st', 'i')]),
                        (bid + '_up', 'tree_spine', 1136, [lp(wst, 'E', 'st', 'o'), lp(est, 'W', 'st', 'i')]),
                        (bid + '_hr', 'tree_spine', 453, [lp(wst, 'E', 'hr', 'o'), lp(est, 'W', 'hr', 'i')]),
                        (bid + '_cmd', 'tree_spine', 116, [lp(wst, 'E', 'cmd', 'o'), lp(est, 'W', 'cmd', 'i')])]
        # dv_ar_W / dv_kv_* / dv_ib_W / dv_emb: the W-column re-partition is carried by the r_<bus> re-homes
    # far-band clusters: rs_i tied low (Q-CLUSTER: the far bands tie the feedthrough input)
    fed = {e[0] for b in out for e in b[3] if e[1] == 'rs_i'}
    for n in sorted(names):
        if n.startswith('c16_') and n not in fed:
            m['ties'].append((n, 'rs_i', 514, 0))
    m['ties'][:] = [t for t in m['ties'] if t[0] in names]
    m['buses'] = out
    # ---- die / relay geometry
    W = max(i.x + i.w for i in keep) + 21.6
    H = max(d['y'] + d['h'] for d in D['insts']) + 21.6
    m['die']['w'], m['die']['h'] = round(W, 3), round(H, 3)
    m['die']['mm2'] = round(W * H / 1e6, 3)
    g = m['geo']
    g['y0'], g['y_top'], g['y_io'] = 0.0, H, H
    arr = [i for i in keep if i.name.startswith(('c16_', 'dvs_'))]
    xm = (min(i.x for i in arr) + max(i.x + i.w for i in arr)) / 2
    rects = [[min(i.x for i in arr if i.cx < xm), min(i.y for i in arr), xm, max(i.y + i.h for i in arr)],
             [xm, min(i.y for i in arr), max(i.x + i.w for i in arr), max(i.y + i.h for i in arr)]]
    fields = sorted([r for r in m['regions'] if r['kind'] == 'tile_field'], key=lambda r: r['rect'][0])
    for r, rr in zip(fields, rects):
        r['rect'] = [round(z, 3) for z in rr]
    # vertical relay lanes: the W-column channel beside the array (the only vertical die channel; clusters abut)
    wcol = max(by[n].x + by[n].w for n in WCOL if n in names)
    x0 = min(i.x for i in arr)
    nl = max(1, min(2, int((x0 - wcol - 8.64) // (v.CORR + 8.64))))
    lanes = [round(wcol + 4.32 + k * (v.CORR + 8.64), 3) for k in range(nl)]
    m['corridor_lanes'] = [(lanes[c % nl], v.CORR) for c in range(v.COLS)]
    m['q3h']['dv'] = dict(model=os.environ.get('OT_SPLIT_DV'), die=m['die'], removed=len(removed), slices=len(slices),
                          rehomed=len(rehome), dropped_buses=dropped, lanes=lanes, diagnostic=True,
                          synthetic_ports=[SLICE, CDV + ' rs_i/rs_o (scaled CB contract)'])

    def fixed(model, k=1, port_bits=None):
        return dict(M)
    v.masters = fixed
    return m['q3h']['dv']

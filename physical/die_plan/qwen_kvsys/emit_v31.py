#!/usr/bin/env python3
"""PLAN-KVv3 10-23: stage 2 of the KV die plan v3 (= emit_v2 with v3 names, hub_C spine root, span-sized clock
insertion budgets, L1 cell estimates per type).  v2 docstring:

PLAN-KVv2 10-23: stage 2 of the KV die plan v2: stage1 (plan_v2.py) -> die_plan.json + plan_report_v2.json.

Mirror-aware emission (PLAN-TOOL die lattice: symmetric M4-M9 tracks, so R0/MX/MY/R180 copies of a type share one pin
table):
- every shared face is packed once, in the TYPE frame of a reference partition (the one whose type face is N or E),
  in a canonical order (lane family relative to that partition, direction, width, relative end cells in the type
  frame), then mapped to die coordinates; both abutting partitions use the same die window; bit order follows the
  reference type frame (port.order lsb_high when the reference instance is flipped along that face);
- partition types are deduplicated on their type-frame signature (class, outline, every pin window with its role,
  every ft slot as in-window -> out-window + stations, leaf contents); bus / slot names are then derived from the
  type-frame geometry, so every replica binds identical names.
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
import plan_v31 as pv2  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools' / 'die_plan'))
import schema as _schema  # noqa: E402
from cells_v3 import master_cells  # noqa: E402

G = 8.64
REACH = pv2.REACH
ST_MAX = REACH                    # ft station spacing limit (v3.4 sets budgets.ft_station_max_um, COORD R3)
OPP = pv2.OPP
PINS_PER_UM = 5.2                 # v3.1: 4.8 -> 5.2 (windows grow for PG-band exclusion + usable centre track)
GAP = 0.864
MARGIN = 2.16
LAYERS = dict(EW=['M4', 'M6'], NS=['M5', 'M7'])
FLIPX = {'MY', 'R180'}
FLIPY = {'MX', 'R180'}
QREL = {('WS', 'WS'): 'Q', ('WS', 'ES'): 'Qy', ('WS', 'WN'): 'Qx', ('WS', 'EN'): 'Qr'}


PITCH = (0.048, 0.064)        # M4/M5 and M6/M7, symmetric tracks at pitch/2 + k*pitch in every type frame


def ntracks(lo, hi, p):
    return math.floor((hi - p / 2) / p + 1e-9) - math.ceil((lo - p / 2) / p - 1e-9) + 1


def usable(lo, hi, p, ln):
    """v3.1: tracks in [lo, hi] off the partition PG stripe bands (schema.PART_PG_BANDS, plan-tool 5c83c4b9a)"""
    k0 = math.ceil((lo - p / 2) / p - 1e-9)
    k1 = math.floor((hi - p / 2) / p + 1e-9)
    return sum(1 for k in range(k0, k1 + 1) if not _schema.pg_blocked(ln, p / 2 + k * p))


def odd_window(lo, hi, nbits=0, layers=('M4', 'M6')):
    """grow hi (type frame) until each layer has enough tracks off the PG stripe bands for its bits (v3.1: plan-tool
    PG-band exclusion) and, on a layer with an odd bit count, the window centre is off the PG bands and not half-way
    between two tracks (an exact nearest-track tie) and the usable count is odd: schema.spread is then mirror-exact (R0/MX/MY/R180 replicas share one pin table)"""
    need = [len(range(i, nbits, len(layers))) for i in range(len(layers))]
    for k in range(4000):
        h = round(hi + 0.004 * k, 3)
        if all(usable(lo, h, p, ln) >= n for p, ln, n in zip(PITCH, layers, need)) and \
                not any(n % 2 and (_schema.pg_blocked(ln, (lo + h) / 2) or usable(lo, h, p, ln) % 2 == 0 or
                                   abs(((lo + h) / 2 - p / 2) / p % 1 - 0.5) < 1e-3)
                        for p, ln, n in zip(PITCH, layers, need)):
            # odd bit count on a layer: the usable-track count must be odd too and the window centre off the PG bands,
            # else schema.spread's middle pick ((m-1)//2 on even m) is not mirror-symmetric (replicas disagree)
            return h
    raise ValueError((lo, hi, nbits))


def quad_rel(own, other):
    """relation of quadrant `other` to `own` (Q, Qy = mirror in x, Qx = mirror in y, Qr = both)"""
    so, ho = own[0], own[1]
    st, ht = other[0], other[1]
    return 'Q' + ('' if so == st else 'y') + ('' if ho == ht else 'x')


def canon(name, part):
    """block/port name relative to the partition scope (quad tags relative, digits -> #)"""
    sc = part['scope']
    t = name
    if sc in pv2.QUADS:
        t = re.sub(r'_(WS|ES|WN|EN)(?=_|$|\.)', lambda m: '_' + quad_rel(sc, m.group(1)), t)
    elif sc in ('S', 'N'):
        t = re.sub(r'_(W|E)(S|N)(?=_|$|\.)', lambda m: '_' + m.group(1) + ('' if m.group(2) == sc else 'x'), t)
        t = re.sub(r'pvw_([01])', lambda m: 'pvw' + ('' if 'SN'[int(m.group(1))] == sc else 'x'), t)
    return re.sub(r'\d+', '#', t)


def type_face(orient, f):
    if f in 'EW' and orient in FLIPX:
        return OPP[f]
    if f in 'NS' and orient in FLIPY:
        return OPP[f]
    return f


def axis_flip(orient, face):
    return orient in (FLIPY if face in 'EW' else FLIPX)


def to_type_win(p, face, a, b):
    """die window [a, b] on die face `face` of partition p -> (type face, lo, hi) in the type frame"""
    base, ext = (p['y'], p['h']) if face in 'EW' else (p['x'], p['w'])
    lo, hi = a - base, b - base
    if axis_flip(p['orient'], face):
        lo, hi = ext - hi, ext - lo
    return type_face(p['orient'], face), round(lo, 3), round(hi, 3)


def rel_cell(P, ref, part):
    a, b = P[ref], P[part]
    dx = round((b['x'] + b['w'] / 2) - (a['x'] + a['w'] / 2), 1)
    dy = round((b['y'] + b['h'] / 2) - (a['y'] + a['h'] / 2), 1)
    o = P[ref]['orient']
    if o in FLIPX:
        dx = -dx
    if o in FLIPY:
        dy = -dy
    return dx, dy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage1', required=True)
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    S = json.load(gzip.open(a.stage1))
    P, where, lanes = S['P'], S['where'], S['lanes']
    asb = json.load(gzip.open(a.asbuilt))
    B, _ = pv2.rewrite_asbuilt(asb)

    # ---- ports (one per lane hop)
    ports = []
    lane_ports = []
    for l in lanes:
        hops = l['hops']
        pids = []
        for i, (u, v, f, w) in enumerate(hops):
            pids.append(len(ports))
            ports.append(dict(lane=l['id'], i=i, n=len(hops), u=u, v=v, face=f, width=w, fam=l['src'] + '.' + l['sp'],
                              root=l['root'], last=hops[-1][1]))
        lane_ports.append(pids)

    # ---- windows: per shared face, packed in the reference partition's type frame
    pair = collections.defaultdict(list)
    for ix, pr in enumerate(ports):
        pair[tuple(sorted((pr['u'], pr['v'])))].append(ix)
    over = []
    for (x, y), ixs in sorted(pair.items()):
        pxp, pyp = P[x], P[y]
        # shared face of x
        f_x = ports[ixs[0]]['face'] if ports[ixs[0]]['u'] == x else OPP[ports[ixs[0]]['face']]
        tx, ty = type_face(pxp['orient'], f_x), type_face(pyp['orient'], OPP[f_x])
        cand = [(0 if tx in 'NE' else 1, pxp['cls'], x), (0 if ty in 'NE' else 1, pyp['cls'], y)]
        ref = min(cand)[2]
        oth = y if ref == x else x
        pr_, f_ref = P[ref], (f_x if ref == x else OPP[f_x])
        if f_ref in 'EW':
            lo, hi = max(pxp['y'], pyp['y']), min(pxp['y'] + pxp['h'], pyp['y'] + pyp['h'])
            base, ext = pr_['y'], pr_['h']
        else:
            lo, hi = max(pxp['x'], pyp['x']), min(pxp['x'] + pxp['w'], pyp['x'] + pyp['w'])
            base, ext = pr_['x'], pr_['w']
        flip = axis_flip(pr_['orient'], f_ref)
        tlo, thi = (ext - (hi - base), ext - (lo - base)) if flip else (lo - base, hi - base)

        def key(ix):
            pr = ports[ix]
            fam = canon(pr['fam'], pr_)
            return (fam, pr['u'] == ref, pr['width'], rel_cell(P, ref, pr['root']), rel_cell(P, ref, pr['last']))
        cur = 0.0
        for ix in sorted(ixs, key=key):
            pr = ports[ix]
            ln = max(GAP, math.ceil((pr['width'] + 1) / PINS_PER_UM / 0.864 - 1e-9) * 0.864)
            t0 = round(tlo + MARGIN + cur, 3)
            t1 = odd_window(t0, t0 + ln, pr['width'] + 1, tuple(LAYERS['EW' if f_ref in 'EW' else 'NS']))
            ln = t1 - t0
            if t1 + MARGIN > thi + 1e-6:
                over.append(f'{x}|{y}')
            cur += ln + GAP
            d0, d1 = (base + ext - t1, base + ext - t0) if flip else (base + t0, base + t1)
            pr['window_um'] = [round(d0, 4), round(d1, 4)]
            pr['order'] = 'lsb_high' if flip else 'lsb_low'
            pr['layers'] = LAYERS['EW' if pr['face'] in 'EW' else 'NS']

    # ---- per-partition pin records (type frame)
    recs = collections.defaultdict(list)       # part -> [dict(kind, port ix, side, tface, lo, hi, width, role)]
    for ix, pr in enumerate(ports):
        for side, part, f in (('src', pr['u'], pr['face']), ('dst', pr['v'], OPP[pr['face']])):
            tf, lo, hi = to_type_win(P[part], f, *pr['window_um'])
            if side == 'src':
                role = 'o.' + canon(pr['fam'], P[part]) if pr['i'] == 0 else 'fto'
            else:
                role = 'i.' + canon(pr['fam'], P[part]) if pr['i'] == pr['n'] - 1 else 'fti'
            recs[part].append(dict(ix=ix, side=side, tf=tf, lo=lo, hi=hi, w=pr['width'], role=role))
    # slots: (part, lane) fti -> fto
    slot_pairs = collections.defaultdict(list)
    for pids in lane_ports:
        for i in range(1, len(pids)):
            pin, pout = ports[pids[i - 1]], ports[pids[i]]
            slot_pairs[pout['u']].append((pids[i - 1], pids[i]))
    sig, slotinfo = {}, {}
    for part, pp in P.items():
        rr = recs[part]
        pin_of = {(r['ix'], r['side']): r for r in rr}
        slots = []
        for (pi, po) in slot_pairs[part]:
            ri, ro = pin_of[(pi, 'dst')], pin_of[(po, 'src')]
            ci = ((ri['lo'] + ri['hi']) / 2, ri['tf'])
            co = ((ro['lo'] + ro['hi']) / 2, ro['tf'])

            def pt(c, w, h):
                t, f = c
                return {'E': (w, t), 'W': (0.0, t), 'N': (t, h), 'S': (t, 0.0)}[f]
            w_, h_ = pp['w'], pp['h']
            A, Bp = pt(ci, w_, h_), pt(co, w_, h_)
            fs = {ri['tf'], ro['tf']}
            span = w_ if fs == {'E', 'W'} else h_ if fs == {'N', 'S'} else (w_ + h_) / 2
            st = max(1, math.ceil(max(span, abs(A[0] - Bp[0]) + abs(A[1] - Bp[1])) / ST_MAX - 1e-9))
            slots.append(((ri['tf'], ri['lo'], ri['hi'], ri['w']), (ro['tf'], ro['lo'], ro['hi'], ro['w']), st, pi, po))
        slotinfo[part] = slots
        contents = sorted((loc, B[blk]['m']) for blk, (pt_, loc) in where.items() if pt_ == part)
        canon_contents = tuple(sorted(collections.Counter(re.sub(r'\d+', '#', loc) + ':' + m
                                                         for loc, m in contents).items()))
        pins = tuple(sorted((r['tf'], r['lo'], r['hi'], r['w'], r['role'] if r['role'][0] in 'io' else r['role'])
                            for r in rr))
        sl = tuple(sorted((s[0], s[1], s[2]) for s in slots))
        sig[part] = (pp['cls'], pp['w'], pp['h'], pins, sl, canon_contents)

    # ---- types
    by_sig, types, part_type = {}, {}, {}
    cls_count = collections.Counter()
    for part in sorted(P, key=lambda n: (P[n]['cls'], P[n]['orient'] != 'R0', n)):
        s_ = sig[part]
        if s_ not in by_sig:
            cls = P[part]['cls']
            tn = f'kv3_{cls}' if cls_count[cls] == 0 else f'kv3_{cls}_v{cls_count[cls]}'
            cls_count[cls] += 1
            by_sig[s_] = tn
            types[tn] = dict(rep=part)
        part_type[part] = by_sig[s_]

    # ---- names from type-frame geometry (identical in every replica)
    bus_name = {}         # (ix, side) -> bus name at that end
    type_rec = {}
    for tn, t in types.items():
        rep = t['rep']
        rr = sorted(recs[rep], key=lambda r: (r['tf'], r['lo'], r['role']))
        cnt = collections.Counter()
        names_geo = {}
        func = []
        for r in rr:
            if r['role'] in ('fti', 'fto'):
                continue
            base = r['role']
            n_ = cnt[base]
            cnt[base] += 1
            ident = re.sub(r'[^A-Za-z0-9_]', '_', base.replace('#', 'N').replace('.', '_', 1))
            nm = ident if n_ == 0 else f'{ident}_d{n_}'      # Verilog-safe bus names (gen_rtl / g2 probes)
            names_geo[(r['tf'], r['lo'], r['hi'], r['role'])] = nm
            func.append(dict(name=nm, dir='out' if r['role'][0] == 'o' else 'in', width=r['w'], kind='data'))
        slots = sorted(slotinfo[rep], key=lambda s: (s[0][0], s[0][1], s[1][0], s[1][1]))
        sl_out = []
        for j, (ki, ko, st, _, _) in enumerate(slots):
            nm = f'ft{j}'
            names_geo[('S', ki, ko)] = nm
            sl_out.append(dict(name=nm, in_face=ki[0], out_face=ko[0], width=ki[3], stations=st))
        type_rec[tn] = dict(names=names_geo, buses=func, slots=sl_out)
    for part in P:
        nm = type_rec[part_type[part]]['names']
        for r in recs[part]:
            if r['role'] in ('fti', 'fto'):
                continue
            bus_name[(r['ix'], r['side'])] = nm[(r['tf'], r['lo'], r['hi'], r['role'])]
        pin_of = {(r['ix'], r['side']): r for r in recs[part]}
        for (ki, ko, st, pi, po) in slotinfo[part]:
            s_ = nm[('S', ki, ko)]
            bus_name[(pi, 'dst')] = s_ + '_i'
            bus_name[(po, 'src')] = s_ + '_o'

    # ---- contents per type (representative)
    REUSE = __import__('emit_plan').REUSE
    ptypes, status_count, master_status = {}, collections.Counter(), {}
    cells_t, cells_dp = {}, {}
    for tn, t in types.items():
        rep = t['rep']
        pp = P[rep]
        contents = []
        for blk, (pt_, loc) in sorted(where.items(), key=lambda kv: kv[1][1]):
            if pt_ != rep:
                continue
            m = B[blk]['m']
            st, note = REUSE.get(m, ('reuse', 'leaf'))
            if pp['cls'] == 'phy':
                st, note = 'rework', 'HBM PHY model sliced per 4 PCs (one 1.5-mm clock region per slice)'
            if loc.startswith('astk') and pp['cls'] in ('hg', 'hgi'):
                st, note = 'rework', 'astk segment moved into its head-group row (chain position = plan row)'
            master_status[m] = st
            contents.append(dict(inst=loc, module=m, status=st, note=note))
            c_, how = master_cells(m, B[blk]['w'], B[blk]['h'])
            cells_t[tn] = cells_t.get(tn, 0.0) + c_
            if how != 'hard':
                cells_dp[tn] = cells_dp.get(tn, 0.0) + (c_ if re.match(r'ot_qkh_|ot_qwen_tp8_pv_', m) else 0.0)
        w, h = pp['w'], pp['h']
        ins = 250.0 if pp['cls'] == 'phy' else float(max(250, round((140 + 0.2 * (w / 2 + h / 2)) / 10) * 10))
        tr = type_rec[tn]
        ptypes[tn] = dict(
            module=f'{tn}_part', outline_um=[w, h], hard=pp['cls'] == 'phy',
            note=f'KV plan v3.1 {pp["cls"]}; representative {rep} ({pp["orient"]}); L1 est. '
                 f'{cells_t.get(tn, 0) / 1e6:.2f} M std cells flattened ({cells_dp.get(tn, 0) / 1e6:.2f} M in replicated '
                 f'datapath leaves)',
            buses=tr['buses'], ft_slots=tr['slots'],
            clock=dict(tap_um=[round(w / 2 / G) * G, round(h / 2 / G) * G], layer='M9', insertion_ps=ins,
                       insertion_tol_ps=40.0),
            reset=dict(tap_um=[round(w / 2 / G) * G, round(h / 2 / G) * G], sync_stages=2),
            contents=contents)
    for blk, (pt_, loc) in where.items():
        status_count[REUSE.get(B[blk]['m'], ('reuse',))[0]] += 1

    out_ports, out_lanes = [], []
    for l, pids in zip(lanes, lane_ports):
        ids = []
        for ix in pids:
            pr = ports[ix]
            pid = f"{l['id']}_{pr['i']}"
            ids.append(pid)
            out_ports.append(dict(id=pid, src=dict(part=pr['u'], bus=bus_name[(ix, 'src')]),
                                  dst=dict(part=pr['v'], bus=bus_name[(ix, 'dst')]), width=pr['width'], kind='data',
                                  face=pr['face'], layers=pr['layers'], window_um=pr['window_um'], order=pr['order']))
        out_lanes.append(dict(id=l['id'], ports=ids, note=f"{l['kind']} {l['src']}.{l['sp']}"))
    sp_root = P['hub_C']
    plan = {
        'schema': 'opentallas.die_plan.v1',
        'note': 'Qwen KV/system die plan v3.1 (KV-P2 10-23) = v3 (16 x 1520.64-um rows, W/E = MY, N half = MX about the '
                'centre band; hg outer/inner; 5 hub partitions, PLL + spine root in hub_C) with the IO row cut to 1036.8 um '
                'and one tap per IO partition: sys_SW (SerDes x6 half W) | io_W2 | io_W3 (W corridor head) | sys_c (UCIe + '
                'd2d) | io_E5 | io_E6 | sys_SE (SerDes x6 half E, MY): the mirrored SerDes fills the former empty N-W corner. '
                'FDI census fix (host/d2d FDI bundles at real width). Clock insertion budget per type = 140 ps + 0.2 ps/um x '
                'half-perimeter (min 250). As-built rtl6 (e33504a6f) connectivity.',
        'die': dict(name='qwen_kvsys', label='Qwen3-8B KV/system die', tech='asap7',
                    outline_um=[pv2.DIE_W, round(pv2.DIE_H, 4)], period_ps=833, reach_um=REACH, rep_um=450.0, grid_um=G,
                    layer_budget=dict(partition_signal_max='M7', die_layers=['M8', 'M9'],
                                      die_use=['clock_spine', 'pg', 'ft_reserved', 'reset'],
                                      cut_avail={'M8': 0.6, 'M9': 0.6}),
                    pg=dict(partition_pg_max='M7', grid=[
                        dict(layer='M8', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS']),
                        dict(layer='M9', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS'])])),
        'partition_types': ptypes,
        'partitions': [dict(name=p, type=part_type[p], origin_um=[P[p]['x'], P[p]['y']], orient=P[p]['orient'])
                       for p in sorted(P)],
        'ports': out_ports,
        'lanes': out_lanes,
        'clock': dict(source=dict(part='@die', bus='clk_core'), insertion_ps=250, insertion_tol_ps=40,
                      neighbour_skew_ps=80, face_xing='budgeted',
                      spine=dict(layers=['M8', 'M9'], root_um=[sp_root['x'] + sp_root['w'] / 2,
                                                               sp_root['y'] + sp_root['h'] / 2],
                                 topology='fishbone')),
        'reset': dict(source=dict(part='@die', bus='rst_n'), sync_stages=2, data_reset=False, epoch_bit=True,
                      release='counted'),
        'latency': dict(lanes={}),
        'budgets': dict(face_pins_per_um=6, face_pin_layers=2, face_window_um=10, pin_track_max=0.6, cut_ratio_max=0.6,
                        cut_step_um=250),
    }
    plan['census'] = [dict(rows='census/census_rows_v31.tsv.gz', map='census/census_map_v31.json',
                           note='as-built rtl6 e33504a6f (census_rows_v31.py); gathers as qkd_rlyi_258s T-chain hops')]
    Path(a.out).write_text(json.dumps(plan, indent=1) + '\n')
    rep = dict(partitions=len(P), types=len(ptypes),
               types_by_class=dict(collections.Counter(P[min(q for q in P if part_type[q] == tn)]['cls'] for tn in ptypes)),
               ports=len(out_ports), lanes=len(out_lanes), face_overflow=sorted(set(over)),
               leaf_instances_by_status=dict(status_count),
               masters_by_status=dict(collections.Counter(master_status.values())),
               l1_cells_per_type={tn: dict(flat_M=round(cells_t.get(tn, 0) / 1e6, 3),
                                           datapath_leaf_M=round(cells_dp.get(tn, 0) / 1e6, 3),
                                           rest_M=round((cells_t.get(tn, 0) - cells_dp.get(tn, 0)) / 1e6, 3),
                                           insertion_ps=ptypes[tn]['clock']['insertion_ps'],
                                           outline_um=ptypes[tn]['outline_um']) for tn in ptypes},
               part_type=part_type)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k != 'part_type'})[:3000], file=sys.stderr)


if __name__ == '__main__':
    main()

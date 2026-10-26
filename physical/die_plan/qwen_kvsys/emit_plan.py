#!/usr/bin/env python3
"""PLAN-KV 10-23: stage 2 of the KV die plan v1: stage1 (build_plan.py) -> die_plan.json (opentallas.die_plan.v1) +
plan_report.json.

- Partition types are deduplicated by signature (class, functional buses, ft slots in the TYPE frame, contents).
- Bus names are canonical (source block names normalised to the partition's scope, indices -> '#', ordinal suffix), so
  replicas of a regular structure share one type.
- Port windows are packed per shared face in a canonical order, in the source partition's type frame, at <= 6 pins/um
  on 2 layers (E/W faces M4+M6, N/S faces M5+M7); both partitions use the same window (schema.pin_positions).
"""
import argparse
import collections
import gzip
import json
import math
import re
import sys
from pathlib import Path

G = 8.64
REACH = 1200.0
OPP = dict(E='W', W='E', N='S', S='N')
PINS_PER_UM = 4.8
GAP = 0.864
MARGIN = 2.16
LAYERS = dict(EW=['M4', 'M6'], NS=['M5', 'M7'])
QTAG = re.compile(r'_(WS|ES|WN|EN)(?=_|$)')

REUSE = {   # leaf master -> (status, note)
    'ot_qkh_head_frontq_native': ('reuse', 'head leaf'), 'ot_qkh_head_score4_native': ('reuse', 'head leaf'),
    'ot_qkh_head_stin_native': ('reuse', 'head leaf'), 'ot_qkh_head_stk_native': ('reuse', 'head leaf'),
    'ot_qkh_ktree_lk': ('reuse', 'head leaf'), 'ot_qkh_lane8': ('reuse', 'head leaf'),
    'qkh_head_gather_stage': ('reuse', 'head leaf'), 'qkh_head_sstage': ('reuse', 'head leaf'),
    'qkd_hgs': ('reuse', 'hst tree stage (registered)'), 'qkd_hss': ('reuse', 'hst tree stage (registered)'),
    'qkd_ectlk': ('rework', 'RESPONSE_LAT / QK_ISSUE_AGE from the plan latency table (parameter)'),
    'ot_qwen_tp8_pv_slice_t': ('reuse', 'PV slice'), 'ot_qwen_tp8_pv_join_t': ('reuse', 'PV join'),
    'ot_qwen_tp8_pv_wide_ctl_tbf': ('rework', 'FIRST_INPUT_AGE = RL + 1 from the table; cmd tap-tree root'),
    'qkd_pv_rs_hd_f': ('reuse', 'PV result head'),
    'qkd_hbm3e_phy_pc': ('reuse', 'HBM PHY hard IP'), 'ot_qkvd_ucie_x64_phy': ('reuse', 'UCIe PHY hard IP'),
    'ot_qfd_serdes_112g_x12_phy': ('reuse', 'SerDes PHY hard IP'),
    'qkd_kvs_pc': ('rework', 'KVPC r4/r5 kits in gate'), 'qkd_kvs_pc_h': ('rework', 'KVPC r4/r5 kits in gate'),
    'qkd_hslice': ('reuse', 'hslice'), 'qkd_hslice_dn': ('reuse', 'hslice'),
    'qkd_kvs_grp_r2c': ('rework', 'grp r4 kit in gate'), 'qkd_kvs_grp_h_r2c': ('rework', 'grp_h r4 kit in gate'),
    'qkd_pv16_vport': ('rework', 'RT / DQ from the table (parameter)'),
    'qkd_ahub': ('rework', 'attention hub: AP_OFS / FR_OFS table-driven (r12 offsets as parameters)'),
    'qkd_pvfin': ('reuse', 'pvfin'),
    'qkd_astk_ctl_s': ('reuse', 'astk leaf'), 'qkd_astk_ep_s': ('reuse', 'astk leaf'),
    'qkd_astk_er_owner_st': ('reuse', 'astk leaf'), 'qkd_astk_ex_s': ('reuse', 'astk leaf'),
    'qkd_astk_zn': ('reuse', 'astk leaf'), 'qkd_astk_fault_join': ('reuse', 'fault join'),
    'qkd_kvs_ctl': ('reuse', 'kvs_ctl'), 'qkd_kvs_attn': ('rework', 'PV_LEAD / F_DLY from the table (parameter)'),
    'qkd_kvs_emb': ('reuse', 'kvs_emb nc32 (route pending)'), 'qkd_embgw': ('reuse', 'embgw'),
    'qkd_kvs_hroot': ('reuse', 'hroot'), 'qkd_ctrl_kc': ('reuse', 'kc'),
    'qkd_host_rt': ('rework', 'HOSTP: tie-offs / 1,203 unregistered prompt pins (GEOM FAIL 03:26)'),
    'qkd_d2ds': ('reuse', 'd2d'), 'qkd_pllm': ('reuse', 'PLL hard'), 'qkd_dcal': ('reuse', 'dcal'),
    'qkd_ckbump': ('reuse', 'bump'), 'qkd_fwdbump': ('reuse', 'bump'),
    'qkd_seq_core_static_s': ('reuse', 'seq'), 'qkd_seq_fan_s': ('reuse', 'seq'), 'qkd_seq_xs_s': ('reuse', 'seq'),
    'qkd_hp_or2': ('reuse', 'fault or'),
}


def type_face(orient, f):
    if orient == 'MY' and f in 'EW':
        return OPP[f]
    if orient == 'MX' and f in 'NS':
        return OPP[f]
    if orient == 'R180':
        return OPP[f]
    return f


def scope_norm(name, part):
    """normalise quadrant tags relative to the partition scope, then indices -> '#'"""
    sc = part['scope']
    t = name
    if sc in ('WS', 'ES', 'WN', 'EN'):
        t = t.replace(f'_{sc}', '_Q')
    if sc in ('S', 'N'):
        t = QTAG.sub(lambda m: '_' + m.group(1)[0] if m.group(1)[1] == sc else m.group(0), t)
    t = re.sub(r'pvw_[01]', 'pvw', t)
    return re.sub(r'\d+', '#', t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage1', required=True)
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    S = json.load(gzip.open(a.stage1))
    asb = json.load(gzip.open(a.asbuilt))
    P, where, lanes = S['P'], S['where'], S['lanes']
    B = asb['blocks']

    # ---- per-partition bus / slot records (instance level first)
    inst_bus = collections.defaultdict(list)     # part -> [(kind, canon, dir, width, lane id, hop index)]
    inst_slot = collections.defaultdict(list)    # part -> [(in_face_die, out_face_die, width, stations, lane, hop)]
    lane_rec = []
    for l in lanes:
        hops = l['hops']
        src_part = hops[0][0]
        canon_src = scope_norm(l['src'].split('__')[0], P[src_part]) + ('.' + l['sp'])
        recs = []
        for i, (u, v, fo, bits) in enumerate(hops):
            recs.append(dict(u=u, v=v, face=fo, width=bits))
        # source out bus
        kind_o = 'f' if l['kind'] != 'gather_chain' and not l['src'].startswith(tuple()) else 'o'
        # functional endpoints: first hop's u, last hop's v
        inst_bus[recs[0]['u']].append(('o', scope_norm(l['src'].split('__')[0], P[recs[0]['u']]) + '.' + l['sp'],
                                       'out', recs[0]['width'], l['id'], 0))
        inst_bus[recs[-1]['v']].append(('i', scope_norm(l['src'].split('__')[0], P[recs[-1]['v']]) + '.' + l['sp'],
                                        'in', recs[-1]['width'], l['id'], len(recs) - 1))
        for i in range(1, len(recs)):
            part = recs[i]['u']
            fi, fo = OPP[recs[i - 1]['face']], recs[i]['face']
            inst_slot[part].append((fi, fo, max(recs[i - 1]['width'], recs[i]['width']), 0, l['id'], i))
        lane_rec.append((l, recs))

    # ---- canonical names per partition instance
    bus_name = {}      # (part, lane, hop, 'i'/'o') -> name
    slot_name = {}     # (part, lane, hop) -> slot name
    sig = {}
    for part in P:
        pp = P[part]
        names = collections.Counter()
        bl = sorted(inst_bus[part], key=lambda r: (r[0], r[1], r[3], r[4]))
        buses = []
        for (k, canon, d, w, lid, hop) in bl:
            base = f'{k}.{canon}'
            n = names[base]
            names[base] += 1
            nm = base if n == 0 else f'{base}~{n}'
            bus_name[(part, lid, hop, k)] = nm
            buses.append((nm, d, w))
        sl = sorted(inst_slot[part], key=lambda r: (type_face(pp['orient'], r[0]), type_face(pp['orient'], r[1]),
                                                     -r[2], r[3], r[4]))
        slots = []
        for j, (fi, fo, w, st, lid, hop) in enumerate(sl):
            nm = f'ft{j}'
            slot_name[(part, lid, hop)] = nm
            slots.append([nm, type_face(pp['orient'], fi), type_face(pp['orient'], fo), w, 1, lid, hop])
        contents = sorted((loc, B[blk]['m']) for blk, (pt, loc) in where.items() if pt == part)
        canon_contents = tuple(sorted(collections.Counter(re.sub(r'\d+', '#', loc) + ':' + m
                                                         for loc, m in contents).items()))
        sig[part] = [pp['cls'], pp['w'], pp['h'], tuple(buses), slots, canon_contents]
    # ---- ports with windows
    faces = collections.defaultdict(list)     # (src part, dst part) -> [(port id, width, canon key)]
    ports = []
    plan_lanes = []
    for (l, recs) in lane_rec:
        pids = []
        for i, r in enumerate(recs):
            pid = f"{l['id']}_{i}"
            u, v = r['u'], r['v']
            sb = bus_name[(u, l['id'], 0, 'o')] if i == 0 else slot_name[(u, l['id'], i)] + '_o'
            db = bus_name[(v, l['id'], len(recs) - 1, 'i')] if i == len(recs) - 1 else \
                slot_name[(v, l['id'], i + 1)] + '_i'
            ports.append(dict(id=pid, src=dict(part=u, bus=sb), dst=dict(part=v, bus=db), width=r['width'],
                              kind='data', face=r['face'], layers=LAYERS['EW' if r['face'] in 'EW' else 'NS'],
                              window_um=None))
            faces[(u, v, r['face'])].append((len(ports) - 1, r['width'], sb + '>' + db))
            pids.append(pid)
        plan_lanes.append(dict(id=l['id'], ports=pids, note=f"{l['kind']} {l['src']}.{l['sp']}"))
    over = []
    pair_used = collections.defaultdict(float)
    for (u, v, f), lst in sorted(faces.items()):
        pu, pv = P[u], P[v]
        if f in 'EW':
            lo, hi = max(pu['y'], pv['y']), min(pu['y'] + pu['h'], pv['y'] + pv['h'])
        else:
            lo, hi = max(pu['x'], pv['x']), min(pu['x'] + pu['w'], pv['x'] + pv['w'])
        # canonical order in the source type frame
        rev = (f in 'NS' and pu['orient'] in ('MY', 'R180')) or (f in 'EW' and pu['orient'] in ('MX', 'R180'))
        key = tuple(sorted({u, v}))
        cur = pair_used[key]
        lst = sorted(lst, key=lambda r: r[2])
        for (ix, w, _) in lst:
            ln = max(GAP, math.ceil((w + 1) / PINS_PER_UM / 0.864) * 0.864)
            a0 = lo + MARGIN + cur
            b0 = a0 + ln
            if rev:
                a0, b0 = hi - MARGIN - cur - ln, hi - MARGIN - cur
            ports[ix]['window_um'] = [round(a0, 3), round(b0, 3)]
            cur += ln + GAP
            if cur + MARGIN > (hi - lo):
                over.append(f'{u}|{v} {f}')
        pair_used[key] = cur
    # ---- stations per slot instance from the port windows: ceil(Manhattan(in window, out window) / reach)
    def port_point(pr):
        sp_ = P[pr['src']['part']]
        c_ = (pr['window_um'][0] + pr['window_um'][1]) / 2
        return {'E': (sp_['x'] + sp_['w'], c_), 'W': (sp_['x'], c_), 'N': (c_, sp_['y'] + sp_['h']),
                'S': (c_, sp_['y'])}[pr['face']]
    pid_ix = {pr['id']: i for i, pr in enumerate(ports)}
    st_inst = {}
    for (l, recs) in lane_rec:
        for i in range(1, len(recs)):
            pa, pb = port_point(ports[pid_ix[f"{l['id']}_{i - 1}"]]), port_point(ports[pid_ix[f"{l['id']}_{i}"]])
            L_ = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
            st_inst[(recs[i]['u'], l['id'], i)] = max(1, math.ceil(L_ / REACH - 1e-9))
    pins = collections.defaultdict(list)       # part -> [(bus, type face, lo, hi)] in the type frame
    for pr in ports:
        for side, f_ in (('src', pr['face']), ('dst', OPP[pr['face']])):
            pt = pr[side]['part']
            pp_ = P[pt]
            base = pp_['y'] if f_ in 'EW' else pp_['x']
            pins[pt].append((pr[side]['bus'], f_, round(pr['window_um'][0] - base, 3),
                             round(pr['window_um'][1] - base, 3)))
    for part in P:
        sl = sig[part][4]
        for r_ in sl:
            r_[4] = st_inst[(part, r_[5], r_[6])]
        sig[part] = (sig[part][0], sig[part][1], sig[part][2], sig[part][3],
                     tuple((n, fi, fo, w, st) for (n, fi, fo, w, st, _, _) in sl), sig[part][5],
                     tuple(sorted(pins[part])))
    # dedupe types
    types, part_type = {}, {}
    by_sig = {}
    cls_count = collections.Counter()
    for part in sorted(P):
        s_ = sig[part]
        if s_ not in by_sig:
            cls = P[part]['cls']
            tn = f'kv_{cls}' if cls_count[cls] == 0 else f'kv_{cls}_v{cls_count[cls]}'
            cls_count[cls] += 1
            by_sig[s_] = tn
            types[tn] = dict(rep=part, sig=s_)
        part_type[part] = by_sig[s_]

    # ---- type records
    ptypes = {}
    status_count = collections.Counter()
    master_status = {}
    for tn, t in types.items():
        cls, w, h, buses, slots, _, _ = t['sig']
        rep = t['rep']
        contents = []
        for blk, (pt, loc) in sorted(where.items(), key=lambda kv: kv[1][1]):
            if pt != rep:
                continue
            m = B[blk]['m']
            st, note = REUSE.get(m, ('reuse', 'leaf'))
            master_status[m] = st
            contents.append(dict(inst=loc, module=m, status=st, note=note))
        ptypes[tn] = dict(
            module=f'{tn}_part', outline_um=[w, h], hard=cls == 'phy',
            note=f'KV plan v1 {cls}; representative instance {rep}',
            buses=[dict(name=n, dir=d, width=wd, kind='data') for (n, d, wd) in buses],
            ft_slots=[dict(name=n, in_face=fi, out_face=fo, width=wd, stations=st) for (n, fi, fo, wd, st) in slots],
            clock=dict(tap_um=[round(w / 2 / G) * G, round(h / 2 / G) * G], layer='M9', insertion_ps=250.0,
                       insertion_tol_ps=40.0),
            reset=dict(tap_um=[round(w / 2 / G) * G, round(h / 2 / G) * G], sync_stages=2),
            contents=contents)
    for part in P:
        for c in ptypes[part_type[part]]['contents']:
            pass
    for blk, (pt, loc) in where.items():
        status_count[REUSE.get(B[blk]['m'], ('reuse',))[0]] += 1

    # latency table (stations from window geometry; PLAN-TOOL gen.py latency rewrites it in the 617386333 convention)
    lat = {}
    for (l, recs) in lane_rec:
        st = sum(st_inst[(recs[i]['u'], l['id'], i)] for i in range(1, len(recs)))
        lat[l['id']] = dict(cycles=st + 1, stations=st, faces=len(recs), fixed=0)
    plan = {
        'schema': 'opentallas.die_plan.v1',
        'note': 'Qwen KV/system die plan v1 (PLAN-KV 10-23): as-built rtl6 (e33504a6f) connectivity re-planned top-down: '
                'abutted partitions, broadcasts as tap trees, gathers as mux chains, head/hst trees inside hgrp, no '
                'channels, no die relays, no delay padding (latency from this table).',
        'die': dict(name='qwen_kvsys', label='Qwen3-8B KV/system die', tech='asap7',
                    outline_um=[round(max(p['x'] + p['w'] for p in P.values()), 3),
                                round(max(p['y'] + p['h'] for p in P.values()), 3)],
                    period_ps=833, reach_um=REACH, rep_um=450.0, grid_um=G,
                    layer_budget=dict(partition_signal_max='M7', die_layers=['M8', 'M9'],
                                      die_use=['clock_spine', 'pg', 'ft_reserved', 'reset'],
                                      cut_avail={'M8': 0.6, 'M9': 0.6}),
                    pg=dict(partition_pg_max='M7', grid=[
                        dict(layer='M8', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS']),
                        dict(layer='M9', width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=['VDD', 'VSS'])])),
        'partition_types': ptypes,
        'partitions': [dict(name=p, type=part_type[p], origin_um=[P[p]['x'], P[p]['y']], orient=P[p]['orient'])
                       for p in sorted(P)],
        'ports': ports,
        'lanes': plan_lanes,
        'clock': dict(source=dict(part='@die', bus='clk_core'), insertion_ps=250, insertion_tol_ps=40,
                      neighbour_skew_ps=80, face_xing='budgeted',
                      spine=dict(layers=['M8', 'M9'], root_um=[P['sys_io']['x'] + P['sys_io']['w'] / 2,
                                                               P['sys_io']['y']], topology='fishbone')),
        'reset': dict(source=dict(part='@die', bus='rst_n'), sync_stages=2, data_reset=False, epoch_bit=True,
                      release='counted'),
        'latency': dict(lanes=lat),
        'budgets': dict(face_pins_per_um=6, face_pin_layers=2, face_window_um=10, pin_track_max=0.6, cut_ratio_max=0.6,
                        cut_step_um=250),
    }
    Path(a.out).write_text(json.dumps(plan, indent=1) + '\n')
    rep = dict(partitions=len(P), types=len(types), types_by_class=dict(collections.Counter(
        P[t['rep']]['cls'] for t in types.values())), ports=len(ports), lanes=len(plan_lanes), face_overflow=over,
        leaf_instances_by_status=dict(status_count),
        masters_by_status=dict(collections.Counter(master_status.values())), part_type=part_type)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k != 'part_type'}, indent=None)[:3000], file=sys.stderr)


if __name__ == '__main__':
    main()

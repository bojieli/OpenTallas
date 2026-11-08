#!/usr/bin/env python3
"""QC-TYPES-10/FWS 11-08: sle_fw_v3 S-export writer START with a re-rooted reset (plan event qc53v4x_fws on v4w).

Why: rst_root_n is the arst_n pin register at the W face (8,837). Every phase-1 relay lies within 380 um of it, so
a stage next to the S face (1361 um from the root) cannot have a phase-1 reset with a hop <= 405 um.

Form, in three parts. It never edits the input plan.
 (a) cws0_o and x_st_a_fe_o get W=3 and three stages, like the 14 v4u branches. The reset FOLLOWS START:
     stage i takes an existing depth-(i+1) relay of the type's reset tree. The face flop keeps depth 4
     (cland_start_raw = u_cland_rst_cmd_ei, D = depth-3 rst_rl_73). With r = rst_root_n:
         q0(t+1) = r(t-1) & s(t)
         q1(t+1) = r(t-2) & q0(t)
         q2(t+1) = r(t-3) & q1(t)
         f(t+1)  = r(t-4) & q2(t)
     so f(t+1) = r(t-4) & s(t-3). That is the v4w W=0 face, f(t+1) = r(t-4) & s(t), with START delayed exactly
     3 edges. Receiver K is +3, payload cycles +0. This is the same rule the binder prices for all W branches.
 (b) The 16 FSTART face flops get a same-depth local reset leaf (clock.landing_local_resets, DIE-HEAD-38 R1 /
     fstart_reset_leaves form). D is the depth-3 relay nearest the face, and the leaf sits half way. Today one
     relay at (311,337) feeds all 16 faces over 490-1220 um. The generator checks depth(raw)+1 == depth(old), so
     no release edge moves: 0 cycles, +1 flop per face.
 (c) Nothing else changes: other types, lanes, latency and the 14 v4u branches are byte-identical.
"""
import argparse, copy, json
from pathlib import Path

TYPE = 'sle_fw_v3'
NEW = ('cws0_o', 'x_st_a_fe_o')
LIMIT = 405.0
DESIGN_HOP = 380.0
RAW_MAX = 380.0  # design target, the hard rule is 405
PITCH = 16.2


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def construct(base, tree, rtl):
    plan = copy.deepcopy(base)
    typ = plan['partition_types'][TYPE]
    ck = typ['clock']
    pins = {p['name']: p for p in ck['landing_contract']['pins']}
    origin = pins['cland_rstart_in']['xy_um']
    ws = ck['landing_writer_start']
    if ws['depth'] != 3 or set(NEW) & set(ws['branches']):
        raise ValueError('base is not the v4u/v4w W=3 form without the S pair')
    if 'landing_local_resets' in ck:
        raise ValueError('base already has local resets')
    # Raw nets that drive an output port can never be a stage reset (face_guard 'shared').
    import re
    port_nets = set(re.findall(r'\bassign\s+\w+\s*=\s*(\w+)\s*;\s*//\s*registered reset out', rtl))
    relays = [r for r in tree['relays'] if r['q'] not in port_nets and r['q'].startswith('rst_rl_')]
    by_depth = {d: [r for r in relays if r['depth'] == d] for d in (1, 2, 3)}
    width, height = typ['outline_um']
    occupied = [s['xy_um'] for b in ws['branches'].values() for s in b['stages']]
    pts = [[round(ix * PITCH, 3), round(iy * PITCH, 3)] for ix in range(1, int(width / PITCH))
           for iy in range(1, int(height / PITCH))]
    report = []
    for bus in NEW:
        end = pins['cland_fstart_out_' + bus]['xy_um']
        layers = []
        for stage in range(3):
            layer = []
            for xy in pts:
                if l1(origin, xy) + l1(xy, end) > 1.5 * l1(origin, end) or any(l1(xy, o) <= 8.64 for o in occupied):
                    continue
                raw = min(by_depth[stage + 1], key=lambda r: (l1(xy, r['xy']), r['q']))
                if l1(xy, raw['xy']) <= RAW_MAX:
                    layer.append((xy, raw))
            layers.append(layer)
        states = [(0.0, [origin], [])]
        for layer in layers:
            nxt = []
            for xy, raw in layer:
                best = None
                for cost, path, raws in states:
                    hop = l1(path[-1], xy)
                    if hop > DESIGN_HOP:
                        continue
                    v = cost + hop * hop + 0.05 * l1(xy, raw['xy']) ** 2
                    if best is None or v < best[0]:
                        best = (v, path + [xy], raws + [raw])
                if best:
                    nxt.append(best)
            states = nxt
        states = [(c + l1(p[-1], end) ** 2, p, r) for c, p, r in states if l1(p[-1], end) <= DESIGN_HOP]
        if not states:
            raise ValueError(f'{bus}: no reset-follows-START path')
        cost, path, raws = min(states, key=lambda v: v[0])
        path = path + [end]
        occupied.extend(path[1:-1])
        ws['branches'][bus] = dict(stages=[dict(xy_um=xy, raw_reset=r['q']) for xy, r in zip(path[1:-1], raws)])
        report.append(dict(bus=bus, path_um=path, hops_um=[round(l1(a, b), 3) for a, b in zip(path, path[1:])],
                           raw_resets=[dict(q=r['q'], d=r['d'], depth=r['depth'], xy=r['xy'],
                                            flight_um=round(l1(xy, r['xy']), 3)) for xy, r in zip(path[1:-1], raws)],
                           reset_phase_per_stage=[r['depth'] for r in raws], face_reset_depth=4,
                           old_W=0, new_W=3, receiver_K_delta=3, steady_payload_cycles_delta=0,
                           equation='f(t+1) = r(t-4) & s(t-3)  (v4w: f(t+1) = r(t-4) & s(t))'))
    # ws['branches'] keeps sorted key order, like v4u
    ws['branches'] = dict(sorted(ws['branches'].items()))
    # (b) face leaves
    leaves, lrep = [], []
    for name in sorted(pins):
        if not name.startswith('cland_fstart_out_'):
            continue
        bus = name.removeprefix('cland_fstart_out_')
        face = pins[name]['xy_um']
        raw = min(by_depth[3], key=lambda r: (l1(face, r['xy']), r['q']))
        d = l1(face, raw['xy'])
        if d > 2 * RAW_MAX:
            raise ValueError(f'{bus}: no depth-3 relay within two hops of the face ({d:.1f} um)')
        xy = [round((face[0] + raw['xy'][0]) / 2, 3), round((face[1] + raw['xy'][1]) / 2, 3)]
        leaves.append(dict(name='fstart_' + bus, raw=raw['q'], xy_um=xy, consumers=['u_cland_fstart_' + bus]))
        lrep.append(dict(bus=bus, face_um=face, raw=raw['q'], raw_xy=raw['xy'], leaf_um=xy,
                         raw_to_leaf_um=round(l1(raw['xy'], xy), 3), leaf_to_face_um=round(l1(xy, face), 3),
                         old_raw='cland_reset_cmd_ei @ (311.04,336.96)',
                         old_flight_um=round(l1([311.04, 336.96], face), 3)))
    ck['landing_local_resets'] = leaves
    rep = dict(schema='qc_types_10.fws_form/1', type=TYPE, base='plan_qc53v4w e5dc7eacb745', source_um=origin,
               writer_depth=3, new_branches=report,
               max_start_hop_um=max(max(r['hops_um']) for r in report),
               max_stage_raw_flight_um=max(x['flight_um'] for r in report for x in r['raw_resets']),
               face_leaves=lrep, max_leaf_hop_um=max(max(x['raw_to_leaf_um'], x['leaf_to_face_um']) for x in lrep),
               pin_cycles='receiver strap K +3 on the crossings fed by sl_E5_fw.cws0_o and .x_st_a_fe_o; 0 payload cycles',
               rule='stage i reset depth = i+1 (reset follows START), face depth 4 unchanged')
    return plan, rep


def identical_except(a, b):
    """every key except partition_types.sle_fw_v3.clock.{landing_writer_start,landing_local_resets} byte-identical"""
    bad = [k for k in set(a) | set(b) if k != 'partition_types' and json.dumps(a.get(k)) != json.dumps(b.get(k))]
    ta, tb = a['partition_types'], b['partition_types']
    bad += [k for k in set(ta) | set(tb) if k != TYPE and json.dumps(ta.get(k)) != json.dumps(tb.get(k))]
    xa, xb = ta[TYPE], tb[TYPE]
    bad += [TYPE + '.' + k for k in set(xa) | set(xb) if k != 'clock' and json.dumps(xa.get(k)) != json.dumps(xb.get(k))]
    ca, cb = xa['clock'], xb['clock']
    changed = [k for k in set(ca) | set(cb) if json.dumps(ca.get(k)) != json.dumps(cb.get(k))]
    bad += [TYPE + '.clock.' + k for k in changed if k not in ('landing_writer_start', 'landing_local_resets')]
    wa, wb = ca['landing_writer_start'], cb['landing_writer_start']
    if wa['depth'] != wb['depth']:
        bad.append('depth')
    bad += ['branch ' + k for k in wa['branches'] if json.dumps(wa['branches'][k]) != json.dumps(wb['branches'].get(k))]
    return bad, sorted(changed), sorted(set(wb['branches']) - set(wa['branches']))


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('base', type=Path); a.add_argument('reset_tree', type=Path); a.add_argument('rtl', type=Path)
    a.add_argument('out_plan', type=Path); a.add_argument('out_report', type=Path)
    x = a.parse_args()
    if x.out_plan.exists():
        a.error('refuse to overwrite')
    base = json.loads(x.base.read_text())
    plan, rep = construct(base, json.loads(x.reset_tree.read_text())['tree'], x.rtl.read_text())
    bad, changed, added = identical_except(base, plan)
    if bad:
        raise SystemExit(f'unexpected changes {bad}')
    rep['identity'] = dict(other_keys_identical=True, changed_clock_keys=changed, added_branches=added)
    x.out_plan.write_text(json.dumps(plan, indent=1) + '\n')
    x.out_report.write_text(json.dumps(rep, indent=1) + '\n')
    print('changed', changed, 'added', added)
    for r in rep['new_branches']:
        print(r['bus'], 'hops', r['hops_um'], 'raw', [(z['q'], z['depth'], z['flight_um']) for z in r['raw_resets']])
    print('max START hop', rep['max_start_hop_um'], 'max stage raw', rep['max_stage_raw_flight_um'],
          'max leaf hop', rep['max_leaf_hop_um'])
    for f in rep['face_leaves']:
        print(' leaf', f['bus'], f['raw'], f['raw_to_leaf_um'], f['leaf_to_face_um'], 'old', f['old_flight_um'])

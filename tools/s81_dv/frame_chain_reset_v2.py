#!/usr/bin/env python3
"""Close chained-frame reset epochs in an executed bind, preserving lane gates.

This is the existing calendar-v2 correction: only the receiving frame's rst_n
gets extra stations on ck_r0. Existing return-lane resets and every ICG remain
byte-identical. Run after dv_diecase and before dv_rvcase; rerun strict port bind.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def inspect(text, sync_edges):
    relays = {}
    for m in re.finditer(r'(dsfd_rly_1_\w+) (\w+) \(\.ck\(([\w\[\]]+)\), \.rs\((\w+)\), \.i\((\w+)\), \.o\((\w+)\)\);', text):
        master, inst, ck, rs, inp, out = m.groups()
        relays[out] = dict(master=master, inst=inst, ck=ck, rs=rs, inp=inp, line=m[0])
    aliases = dict(re.findall(r'assign (\w+) = (\w+);', text))
    def depth(net, seen=()):
        assert net not in seen, ('reset cycle', net)
        if net in relays:
            return depth(relays[net]['inp'], seen + (net,)) + 1
        if net in aliases:
            return depth(aliases[net], seen + (net,))
        return 0
    gates = {m[4]: dict(inst=m[1], ck=m[2], ena=m[3], line=m[0]) for m in re.finditer(
        r'ICGx4_ASAP7_75t_R (\w+) \(\.CLK\(([\w\[\]]+)\), \.ENA\((\w+)\), \.SE\(\S+\), \.GCLK\((\w+)\[0\]\)\);', text)}
    frames = {}
    for m in re.finditer(r'(col_\w+) #\(\.INSTANCE\("(\w+)"\)\) (\w+) \((.*?)\);', text):
        master, identity, inst, body = m.groups()
        assert inst == identity
        rst = re.search(r'\.rst_n\((\w+)\)', body)[1]
        root = re.search(r'\.ck_r0\((\w+)\)', body)[1]
        lanes = []
        for expr in re.search(r'\.xk\(\{([^}]*)\}\)', body)[1].split(','):
            lane = re.fullmatch(r'\s*(\w+)\[(\d+)\]\s*', expr)
            assert lane and lane[1] in gates, ('unresolved frame lane', inst, expr)
            g = gates[lane[1]]
            lanes.append(dict(net=lane[1], stages=int(lane[2]), gate=g,
                              first_epoch=depth(g['ena']) + int(lane[2]) % 2))
        frames[inst] = dict(master=master, rst=rst, root=root, reset_depth=depth(rst),
                            read_epoch=depth(rst) + sync_edges, lanes=lanes, line=m[0])
    assert frames, 'no frame instances found'
    changes = {}
    for inst, f in frames.items():
        upstream = {re.match(r'(u_f_\w+?)_xok', l['gate']['ck'])[1]
                    for l in f['lanes'] if '_xok' in l['gate']['ck']}
        if not upstream:
            continue
        assert upstream <= frames.keys(), ('missing upstream frame', inst, upstream)
        # Current frozen lineage has one forwarded frame hop. Refuse a further
        # hierarchy rather than silently treating an already gated clock as free.
        assert all(not any('_xok' in l['gate']['ck'] for l in frames[u]['lanes']) for u in upstream)
        first = max(l['first_epoch'] for u in upstream for l in frames[u]['lanes'])
        delay = max(0, first - f['read_epoch'])
        if delay:
            changes[inst] = dict(upstream=sorted(upstream), reset=f['rst'], root=f['root'],
                old_reset_depth=f['reset_depth'], old_read_epoch=f['read_epoch'],
                upstream_first_epoch=first, delay=delay, new_read_epoch=f['read_epoch'] + delay)
    return frames, changes, relays, aliases


def correct(bind, output=None, plan_path=None, views_dir=None):
    bind = Path(bind)
    text = (bind / 'die.v').read_text()
    case = json.loads((bind / 'bind_case.json').read_text())
    hints = json.loads((bind / 'place_hints.json').read_text())
    rule = case['frame_hop0_gates']['rule']
    sync = int(re.search(r'depth \+ (\d+)', rule)[1])
    frames, changes, relays, aliases = inspect(text, sync)
    plan_path = Path(plan_path) if plan_path else bind.parents[1] / 'plan.json'
    plan = json.loads(plan_path.read_text())
    bodies = {b['name']: b for b in plan['blocks']}
    reset_positions = {r['inst']: r['xy'] for r in hints['reset_place']}
    views_dir = Path(views_dir) if views_dir else bind.parents[1] / 'case/views'
    lef_shapes = {}
    def shape(master):
        if master not in lef_shapes:
            p = views_dir / (master + '.lef')
            lef = p.read_text()
            match = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', lef)
            assert match, ('actual relay LEF SIZE missing', p)
            lef_shapes[master] = dict(width_um=float(match[1]), height_um=float(match[2]),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(), path=str(p))
        return lef_shapes[master]
    def overlaps(a, b):
        return a[0] < b[2]-1e-6 and b[0] < a[2]-1e-6 and a[1] < b[3]-1e-6 and b[1] < a[3]-1e-6
    new_boxes = []
    original = text
    additions, placement = [], []
    for inst, row in changes.items():
        f = frames[inst]
        old = f['rst']; master = relays[old]['master']
        size = shape(master); mw, mh = size['width_um'], size['height_um']
        pin = hints['block_rst_pin'][inst.removeprefix('u_')]
        body = bodies[inst.removeprefix('u_')]
        x, y, w, h = (body[k] for k in ('x', 'y', 'w', 'h'))
        face = min(('W', 'E', 'S', 'N'), key=lambda side:
            dict(W=abs(pin[0]-x), E=abs(pin[0]-x-w), S=abs(pin[1]-y), N=abs(pin[1]-y-h))[side])
        previous = reset_positions[relays[old]['inst']]
        row['placement_face'] = face
        row['placement_source_xy'] = previous
        row['placement_hops_um'] = []
        for k in range(row['delay']):
            net = f'rsfc2_{inst}_{k}'
            assert not re.search(r'\b' + net + r'\b', original), ('already patched', net)
            additions += [f'  wire {net};', f'  {master} st_{net} (.ck({f["root"]}), .rs({old}), .i({old}), .o({net}));   // chained-frame calendar v2']
            # Leave 0.01 um beyond the placer's 0.5 um clearance: exact 0.5
            # gaps can round below the threshold in double/0.001-um DBU math.
            clearance = 0.51
            xy = dict(W=[x-mw/2-clearance, pin[1]+k*(mh+clearance)], E=[x+w+mw/2+clearance, pin[1]+k*(mh+clearance)],
                      S=[pin[0]+k*(mw+clearance), y-mh/2-clearance], N=[pin[0]+k*(mw+clearance), y+h+mh/2+clearance])[face]
            xy = [round(v, 3) for v in xy]
            box = [xy[0]-mw/2, xy[1]-mh/2, xy[0]+mw/2, xy[1]+mh/2]
            assert not any(overlaps(box, [b['x']-0.5,b['y']-0.5,b['x']+b['w']+0.5,b['y']+b['h']+0.5])
                           for b in plan['blocks']), ('reset macro footprint collides with hard body', inst, xy)
            assert not any(overlaps(box, [b[0]-0.5,b[1]-0.5,b[2]+0.5,b[3]+0.5]) for b in new_boxes), ('new reset macro footprints collide', inst, xy)
            new_boxes.append(box)
            hop = abs(xy[0]-previous[0]) + abs(xy[1]-previous[1])
            assert hop <= 405, ('new reset source hop exceeds reach', inst, hop)
            row['placement_hops_um'].append(round(hop, 3)); previous = xy
            placement.append(dict(inst='st_' + net, master=master, orient='R0', xy=xy,
                kind='frame_chain_reset_v2'))
            old = net
        load_hop = abs(previous[0]-pin[0]) + abs(previous[1]-pin[1])
        assert load_hop <= 405
        row['placement_load_hop_um'] = round(load_hop, 3)
        line = f['line'].replace(f'.rst_n({f["rst"]})', f'.rst_n({old})')
        assert line != f['line'] and text.count(f['line']) == 1
        text = text.replace(f['line'], line)
        row['new_reset'] = old
    assert text.count('\nendmodule') == 1, 'expected one die module'
    text = text.replace('\nendmodule', '\n' + '\n'.join(additions) + '\nendmodule') if additions else text
    report = dict(schema='opentallas.s81.frame_chain_reset_v2.v1', source_die_sha256=digest(original),
        corrected_die_sha256=digest(text), receiver_reset_edges=sync, frames=len(frames), changes=changes,
        added_stations=len(placement), plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        reset_master_lefs=lef_shapes,
        placement_rule='actual LEF-sized rectangles: target 0.51 um clearance (>=0.5) from hard bodies and other new reset macros; every new source/load Manhattan hop <=405 um',
        ret_lane_rule='all preexisting reset stations, ICGs and lane relay connections unchanged')
    # Prove the mutation envelope by removing only the recorded new stations and
    # restoring only each receiving frame reset pin. All other bytes must match.
    restore = text
    for inst, row in changes.items():
        restore = restore.replace(f'.rst_n({row["new_reset"]})', f'.rst_n({row["reset"]})')
    if additions:
        restore = restore.replace('\n' + '\n'.join(additions) + '\nendmodule', '\nendmodule')
    assert restore == original, 'mutation escaped frame reset connections'
    assert not inspect(text, sync)[1], 'chained reset deficit remains after correction'
    if output:
        output = Path(output); output.mkdir(parents=True, exist_ok=False)
        (output / 'die.v').write_text(text)
        hints['reset_place'] += placement
        case['reset']['stations'] += len(placement)
        case['reset']['frame_chain_reset_v2'] = report
        fg = case['frame_hop0_gates']; fg['frame_epoch_stations'] += len(placement)
        fg['rule'] += '; calendar-v2 clock-limited chains retain original ICG enables and delay only receiving frame rst_n; rows record corrected read epoch'
        for inst, row in changes.items():
            name = inst.removeprefix('u_')
            fg['frame_epoch_delay'][name] = fg['frame_epoch_delay'].get(name, 0) + row['delay']
            case['reset'].setdefault('frame_actual_release_depth', {})[name] = row['old_reset_depth'] + row['delay']
        for row in fg['rows']:
            key = row['inst'] if row['inst'].startswith('u_') else 'u_' + row['inst']
            if key in changes:
                c = changes[key]
                row['frame_rst'] = c['new_reset']; row['read_epoch'] = c['new_read_epoch']
                row['calendar_G_minus_R0'] -= c['delay']
                row['frame_chain_clock_limited'] = True
        case['frame_chain_reset_v2'] = report
        (output / 'bind_case.json').write_text(json.dumps(case, indent=1) + '\n')
        (output / 'place_hints.json').write_text(json.dumps(hints, indent=1) + '\n')
        (output / 'frame_chain_reset_v2.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bind-dir', required=True)
    ap.add_argument('--out-dir', help='new output directory: corrected die and changed metadata; original remains immutable')
    ap.add_argument('--plan', help='actual GEN plan; defaults to ../../plan.json from the bind directory')
    ap.add_argument('--views-dir', help='actual consumed relay LEF directory; defaults to ../../case/views')
    a = ap.parse_args()
    print(json.dumps(correct(a.bind_dir, a.out_dir, a.plan, a.views_dir), indent=1))

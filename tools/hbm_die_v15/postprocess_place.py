#!/usr/bin/env python3
"""Audit/render a preserved --no-clock case without regenerating placement.

The exported DEF/ODB contains placed macro instances and their physical pins,
with exact source-contract clock nets and no data nets. It is a clock-placement input, never a
data-route or timing result. Every pin distance below uses consumed LEF bytes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pins(path):
    result = {}
    for match in re.finditer(r'^\s*PIN (\S+)(.*?)^\s*END \1', Path(path).read_text(), re.M | re.S):
        rects = re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', match[2])
        # All access shapes participate; widest endpoint separation is conservative.
        result[match[1]] = [((float(a) + float(c))/2, (float(b) + float(d))/2)
                            for a, b, c, d in rects]
    return result


def global_points(place, local):
    if place['o'] not in ('R0', 'MX', 'MY', 'R180'):
        raise ValueError(f"unsupported orientation {place['o']}")
    return [(place['x'] + (place['w']-x if place['o'] in ('MY', 'R180') else x),
             place['y'] + (place['h']-y if place['o'] in ('MX', 'R180') else y)) for x, y in local]


def audit(man, contract, view_dir, limit):
    placed = man['placement']
    expected = set(contract['instances'])
    excluded = set(man['excluded_instances'])
    unknown = sorted(set(placed) - expected)
    missing = sorted(expected - set(placed) - excluded)
    relay_missing = sorted(n for n in expected - set(placed)
                           if contract['instances'][n]['master'].startswith('hbfd_rly'))
    if unknown or missing or relay_missing or set(placed) & excluded:
        raise ValueError(f'coverage failure: unknown={unknown[:5]}, missing={missing[:5]}, '
                         f'relay_missing={relay_missing[:5]}, overlapping_exclusions={sorted(set(placed)&excluded)[:5]}')
    shapes = {}
    for master in {v['m'] for v in placed.values()}:
        path = view_dir / f'{master}.lef'
        if sha(path) != man['consumed_view_sha256'][path.name]:
            raise ValueError(f'consumed LEF hash mismatch: {path}')
        shapes[master] = pins(path)
    counts = Counter()
    violations = []
    worst = None
    for clock in contract.get('clock_resets', []):
        if clock['kind'] != 'clock' or clock['instance'] not in placed:
            continue
        root = clock['source']
        if root[0] not in placed:
            raise ValueError(f'clock root excluded: {root}')
        literal = [(root[0], root[1])] + [
            (clock['instance'], f'{clock["port"]}[{bit}]' if clock['bits'] > 1 else clock['port'])
            for bit in range(clock['bits'])]
        for name, port in literal:
            if not shapes[placed[name]['m']].get(port):
                raise ValueError(f'actual clock literal pin missing: {name}/{port}')
        counts['literal_clock_entries'] += clock['bits']
    for edge_index, edge in enumerate(contract['edges']):
        src, dst = edge['source'], edge['sink']
        if src[0] not in placed or dst[0] not in placed:
            counts['excluded_edge_bits'] += edge['bits']
            continue
        max_distance = -1
        max_bit = None
        for bit in range(edge['bits']):
            endpoints = []
            for endpoint in (src, dst):
                name, port, lo, _width = endpoint
                width = contract['instances'][name]['ports'][port]
                # Contract port descriptors may carry direction as well as width.
                if isinstance(width, dict):
                    width = width['bits'] if 'bits' in width else width['width']
                elif isinstance(width, (list, tuple)):
                    width = width[-1]
                pin = f'{port}[{lo+bit}]' if width > 1 else port
                local = shapes[placed[name]['m']].get(pin)
                if not local:
                    raise ValueError(f'literal pin missing: {name}/{pin}')
                endpoints.append(global_points(placed[name], local))
            distance = max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in endpoints[0] for b in endpoints[1])
            if distance > max_distance:
                max_distance, max_bit = distance, bit
        counts['audited_edges'] += 1
        counts['audited_bits'] += edge['bits']
        row = dict(edge_index=edge_index, source=src, sink=dst, bits=edge['bits'],
                   max_pin_manhattan_um=round(max_distance, 6), worst_bit=max_bit,
                   clock=edge.get('clock'), basis=edge.get('basis'))
        if worst is None or max_distance > worst['max_pin_manhattan_um']:
            worst = row
        if max_distance > limit + 1e-6:
            counts['over_limit_edges'] += 1
            counts['over_limit_bits'] += edge['bits']
            violations.append(row)
    return dict(schema='opentallas.hbm.place_pin_reach.v1', native_complete=False,
                scope='Consumed physical pin centres after placement; Manhattan lower bound, not routed length or timing.',
                contract_instances=len(expected), placed_instances=len(placed), exclusions=sorted(excluded),
                missing_instances=missing, missing_relay_instances=relay_missing,
                limit_um=limit, counts=dict(counts), worst=worst,
                over_limit_edges=sorted(violations, key=lambda e: -e['max_pin_manhattan_um']))


def export_def(man, contract, out):
    orient = dict(R0='N', MX='FS', MY='FN', R180='S')
    dbu = 1000
    number = lambda v: round(v * dbu)
    w, h = man['die_um']
    lines = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;',
             'DESIGN hbm_v16_place_only ;', 'UNITS DISTANCE MICRONS 1000 ;',
             f'DIEAREA ( 0 0 ) ( {number(w)} {number(h)} ) ;',
             f'COMPONENTS {len(man["placement"])} ;']
    for name, p in sorted(man['placement'].items()):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', name):
            raise ValueError(f'unsupported DEF instance identifier {name}')
        lines.append(f'- {name} {p["m"]} + FIXED ( {number(p["x"])} {number(p["y"])} ) {orient[p["o"]]} ;')
    clock_nets = {}
    claimed = set()
    for clock in contract['clock_resets']:
        if clock['kind'] != 'clock' or clock['instance'] not in man['placement']:
            continue
        root = tuple(clock['source'])
        if root[0] not in man['placement']:
            raise ValueError(f'actual clock root excluded: {root}')
        endpoints = clock_nets.setdefault(root, [])
        for bit in range(clock['bits']):
            endpoint = (clock['instance'], f'{clock["port"]}[{bit}]' if clock['bits'] > 1 else clock['port'])
            if endpoint in claimed:
                raise ValueError(f'clock endpoint assigned twice: {endpoint}')
            claimed.add(endpoint)
            endpoints.append(endpoint)
    # DEF bus identifiers are literal bracket names, unlike Tcl expressions.
    lines += ['END COMPONENTS', f'NETS {len(clock_nets)} ;']
    for index, (root, endpoints) in enumerate(sorted(clock_nets.items())):
        lines.append(f'- source_clock_{index}')
        for instance, port in [root] + endpoints:
            lines.append(f'  ( {instance} {port} )')
        lines.append('  + USE CLOCK ;')
    lines += ['END NETS', 'END DESIGN']
    (out / 'place_only.def').write_text('\n'.join(lines)+'\n')
    platform = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    tcl = [f'read_lef {platform}/lef/asap7_tech_1x_201209.lef',
           f'read_lef {platform}/lef/asap7sc7p5t_28_R_1x_220121a.lef']
    tcl += [f'read_lef /work/views/{master}.lef' for master in sorted({p['m'] for p in man['placement'].values()})]
    tcl += ['read_def /work/place_post/place_only.def', 'write_db /work/place_post/place_only.odb',
            'puts "OT_PLACE_ONLY_INSTANCES [llength [[ord::get_db_block] getInsts]]"',
            'puts "OT_PLACE_ONLY_CLOCK_NETS [llength [[ord::get_db_block] getNets]]"']
    (out / 'export_place.tcl').write_text('\n'.join(tcl)+'\n')
    (out / 'literal_clocks.json').write_text(json.dumps(dict(
        qualification='DIAGNOSTIC_ONLY; no data nets, no native clock qualification',
        clock_entries=len(claimed), roots=[dict(source=root, sinks=endpoints)
                                         for root, endpoints in sorted(clock_nets.items())],
        pair_source='Exact input contract edges plus all same-domain entry combinations conservatively; no inferred port ownership.'), indent=1)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--limit', type=float, default=500)
    args = parser.parse_args()
    manifest_path = args.case / 'manifest.json'
    man = json.loads(manifest_path.read_text())
    if sha(args.contract) != man['input_sha256']['contract']:
        raise ValueError('contract differs from actual generator input')
    out = args.case / 'place_post'
    out.mkdir(exist_ok=True)
    contract = json.loads(args.contract.read_text())
    report = audit(man, contract, args.case / 'views', args.limit)
    export_def(man, contract, out)
    if args.render:
        from die_case_v16 import render
        if not args.plan or sha(args.plan) != man['input_sha256']['plan']:
            raise ValueError('render plan differs from actual generator input')
        plan = json.loads(args.plan.read_text())
        strip = man.get('pc_strip')
        if strip:
            dh, south, north = strip['dh_um'], strip['s_strip_at_y'], strip['n_strip_at_y']
            for name, block in plan.items():
                if not isinstance(block, dict) or 'y' not in block:
                    continue
                y = block['y']
                block['y'] = round(y + (dh if y >= south-.01 else 0) + (dh if y >= north-.01 else 0), 3)
                if re.fullmatch(r'pc_S[WE]\d', name):
                    block['h'] = round(block['h']+dh, 3)
                elif re.fullmatch(r'pc_N[WE]\d', name):
                    block['y'] = round(block['y']-dh, 3)
                    block['h'] = round(block['h']+dh, 3)
        render(out, man, plan, *man['die_um'])
    report['input_sha256'] = dict(manifest=sha(manifest_path), contract=sha(args.contract), script=sha(__file__))
    (out / 'reach.json').write_text(json.dumps(report, indent=1)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'over_limit_edges'}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Inventory final reset endpoints from exact GEN geometry; never rewires a die.

Clock-locality alone does not establish interchangeable reset nets. Trace every
candidate through actual qkd_rlys_1 stages to its original producer and retain
the edge count. Nearest candidates are modelling evidence, never qualification.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

INST = re.compile(r'^\s+(\w+) (\S+) \((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
RESET = re.compile(r'^n_(?:rst_|hboot|rrs_)')


def bitref(net):
    return net + '[0]' if re.fullmatch(r'\w+', net) else net


def inventory(netlist, facts):
    insts = {}
    outputs = {}
    for line in netlist.splitlines():
        m = INST.match(line)
        if not m:
            continue
        master, name, body = m.groups()
        cs = {p: bitref(v.strip()) for p, v in CONN.findall(body)}
        insts[name] = master, cs
        if master in ('qkd_rlys_1', 'qkd_rst_region') and 'b' in cs:
            if cs['b'] in outputs:
                raise ValueError('multiple reset relay producers: ' + cs['b'])
            outputs[cs['b']] = name

    literals = {m[0]: int(m[1]) for m in re.findall(
        r"\bassign\s+(\w+\[\d+\])\s*=\s*1'b([01])\s*;", netlist)}

    def trace(net, stop_at_root=True):
        stages, seen = [], set()
        while net in outputs:
            name = outputs[net]
            if name in seen:
                raise ValueError('reset cycle at ' + name)
            seen.add(name)
            master, cs = insts[name]
            if master == 'qkd_rst_region':
                if not stop_at_root:
                    return dict(root=net, edges=len(stages), stages=stages,
                                root_kind='nested_region_unresolved')
                upstream = trace(cs['a'], False)
                dly_net = cs.get('dly', '').split('[')[0]
                dly = ([literals.get(f'{dly_net}[{i}]') for i in range(8)]
                       if dly_net else [])
                dly_value = sum(v << i for i, v in enumerate(dly)) if len(dly) == 8 and None not in dly else None
                return dict(root=name + '/b', root_clock=cs.get('ck'),
                            edges=len(stages), stages=stages,
                            root_kind='qkd_rst_region', root_input=cs.get('a'),
                            root_dly=dly_value, root_upstream=upstream,
                            release_formula='upstream.edges + root_dly + 2 + edges; requires exact root RTL/bind qualification')
            stages.append(dict(instance=name, clock=cs.get('ck')))
            net = cs['a']
        return dict(root=net, edges=len(stages), stages=stages,
                    root_kind='unresolved_producer')

    rows = [w for w in facts['wires'] if RESET.match(w.get('witness_net', ''))]
    # Multi-rectangle LEF pins can have different exporter witness points for
    # different loads. Retain them all and use the largest candidate distance.
    points = defaultdict(set)
    for w in rows:
        src = w['id'].split('->')[0]
        points[src].add(tuple(w['pts'][0]))
    candidates = defaultdict(list)
    for net, name in outputs.items():
        if not RESET.match(net) or name + '/b' not in points:
            continue
        t = trace(net)
        if t['root_kind'] != 'qkd_rst_region':
            continue
        ck = insts[name][1].get('ck')
        candidates[(t['root'], t['edges'], ck)].append((net, name, points[name + '/b']))
    bad, kinds = [], Counter()
    for w in rows:
        src, dst = w['id'].split('->')
        name, port = dst.rsplit('/', 1)
        master, cs = insts[name]
        clock = cs.get('ck_s') if port == 'en' and master.startswith('qkd_landsh0_') else cs.get('ck')
        t = trace(w['witness_net'])
        kinds[t['root_kind']] += 1
        if w['max_um'] <= facts['reach_um']:
            continue
        row = dict(w, master=master, reset_port=port, consumer_clock=clock,
                   provenance=t, nearest_same_root_depth_clock=None,
                   minimum_added_transport_edges=max(0, math.ceil(w['max_um'] / facts['reach_um']) - 1),
                   receiver_capture_edges=2,
                   pair_direction_status='inherited from facts; generic INOUT must be source-bound before adoption')
        opts = candidates.get((t['root'], t['edges'], clock), [])
        if opts:
            p = w['pts'][1]
            def span(v):
                return max(abs(xy[0]-p[0])+abs(xy[1]-p[1]) for xy in v[2])
            net, producer, xy = min(opts, key=lambda v: (span(v), v[0]))
            row['nearest_same_root_depth_clock'] = dict(net=net, producer=producer,
                um=span((net, producer, xy)),
                note='same logical root/edge count only; not a rewiring approval')
        bad.append(row)
    bad.sort(key=lambda r: -r['max_um'])
    return dict(schema='opentallas.kv_reset_endpoint_calendar.v1',
        status='MODEL_ONLY_UNQUALIFIED', reset_pairs=len(rows), long_reset_pairs=len(bad),
        direction_caveat='Potential exporter pairs; generic INOUT can create reverse input-as-driver pairs. Re-export from actual RTL directions before repair.',
        root_kinds=dict(kinds), long_by_port=dict(Counter(r['reset_port'] for r in bad)),
        nearest_same_root_depth_clock_within_reach=sum(
            bool(r['nearest_same_root_depth_clock'] and r['nearest_same_root_depth_clock']['um'] <= facts['reach_um'])
            for r in bad), long_pairs=bad,
        qualification_owed=['legal distribution sites and actual-pin reach',
            'receiver-local two-stage release', 'source-bound reset assertion/release calendar',
            'standard LEC and strict bind', 'causal reset/protocol bench'])


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--facts', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    raw = (a.case / 'die.v').read_bytes()
    facts = json.loads(a.facts.read_text())
    expected = facts['coverage']['source_sha256']['die.v']
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('GEN facts do not belong to exact final netlist')
    result = inventory(raw.decode(), facts)
    result['source_sha256'] = facts['coverage']['source_sha256']
    result['facts_sha256'] = hashlib.sha256(a.facts.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'long_pairs'}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Prepare source-native fault capture after the GEN has created its landings.

The generated fragment is an insertion proposal, never a bound die. It registers
actual unused output bits on their actual clock/reset pair. Domain roots remain
explicit obligations until bounded landed transport and a real STATUS sink exist.
No clock crossing, source pin coordinate, reset leaf, or sink is invented here.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

import fault_inventory as F


def prepare(die, mods, rows, early_sticky=False):
    nets, _, _, instances = F.E.P.parse_die(die)
    by = {name: (master, params, cm) for master, name, params, cm in instances}
    if len(by) != len(instances):
        raise ValueError('post-relay fault capture: duplicate instance')
    groups = collections.defaultdict(list)
    source_connections = []
    seen = set()
    for j, row in enumerate(rows):
        name, port = row['instance'], row['port']
        if name not in by or by[name][0] != row['master']:
            raise ValueError(f'{name}.{port}: stale instance/master')
        master, params, cm = by[name]
        mod = mods[master]
        if mod.ports.get(port, (None,))[0] != 'output' or mod.width(port, mod.env(params)) != row['port_width']:
            raise ValueError(f'{name}.{port}: not the actual output width')
        clock = next((cm[p] for p in ('ck', 'clk', 'ckf') if cm.get(p)), None)
        reset = next((cm[p] for p in ('rs', 'rst_n', 'rst', 'reset_n', 'rsi') if cm.get(p)), None)
        if not clock or not reset or (clock, reset) != (row['clock'], row['reset']):
            raise ValueError(f'{name}.{port}: missing/stale source clock or reset')
        if row['classification'] == 'REVIEW_UNCLASSIFIED':
            raise ValueError(f'{name}.{port}: source-native fault classification owed')
        expr = cm.get(port, '')
        if expr != (row.get('connection') or ''):
            raise ValueError(f'{name}.{port}: stale connection')
        bits = F.E.P.expr_bits(expr, nets) if expr else None
        wire = f'n_fault_capture_src_{j}'
        if not expr:
            source_connections.append(dict(instance=name, port=port, width=row['port_width'], net=wire,
                                           action='connect actual currently open output'))
        for bit in row['unused_bits']:
            key = name, port, bit
            if key in seen or type(bit) is not int or not 0 <= bit < row['port_width']:
                raise ValueError(f'{name}.{port}: duplicate/out-of-range source bit {bit}')
            seen.add(key)
            if bits is None:
                signal = wire if row['port_width'] == 1 else f'{wire}[{bit}]'
            else:
                n, b = bits[-1-bit]
                signal = n if nets[n][0] == 1 else f'{n}[{b}]'
            groups[clock, reset].append(dict(instance=name, port=port, bit=bit, signal=signal))
    nodes, fragment, roots = [], [], []
    for conn in source_connections:
        fragment.append(f'wire [{conn["width"]-1}:0] {conn["net"]};')
    for domain, ((clock, reset), sources) in enumerate(sorted(groups.items())):
        root_bits = []
        for offset in range(0, len(sources), 16):
            take = sources[offset:offset+16]
            name = f'fault_capture_d{domain}_n{offset//16}'
            output = f'n_{name}'
            master = 'qfd_fault_capture' if early_sticky else 'qfd_fault_or'
            nodes.append(dict(instance=name, master=master, N=len(take), clock=clock, reset=reset,
                              inputs=take, output=output, pin_to_output_edges=3,
                              reset_release_edges=2, first_fault_output_edge=4 if early_sticky else 5,
                              input_capture_first_edge=1 if early_sticky else 3,
                              flop_bits=len(take)+4, source_pin_geometry='OWED',
                              reset_added_direct_loads=len(take)+2 if early_sticky else 2, physical_qualification_eligible=False))
            fragment += [f'wire {output};',
                         f'{master} #(.N({len(take)})) {name} (.ck({clock}), .rs({reset}), '
                         f'.f({{{", ".join(x["signal"] for x in reversed(take))}}}), .o({output}));']
            root_bits.append(output)
        roots.append(dict(clock=clock, reset=reset, signals=root_bits,
                          transport='OWED: bounded reduction and landed crossing to actual STATUS sink'))
    sink = by.get('sys_face')
    sink_port = bool(sink and mods[sink[0]].ports.get('obs_fault', (None,))[0] == 'input')
    return dict(schema='opentallas.qwen.post-relay-fault-capture.v1',
                scope='Source insertion proposal only; not emitted GEN, not a bound or qualified die',
                physical_qualification_eligible=False, die_emission_eligible=False,
                capture_mode='early_sticky_optin' if early_sticky else 'legacy_delayed',
                actual_source_bits=len(seen), source_ports=len(rows), clock_reset_groups=len(groups),
                capture_nodes=len(nodes), capture_flop_bits=sum(n['flop_bits'] for n in nodes),
                actual_sys_face_obs_fault_input=sink_port,
                source_connections=source_connections, nodes=nodes, domain_roots=roots,
                owed=['source output hookups and native pin geometry',
                      'source pulse coverage during the two-edge local reset release; no startup event-loss claim',
                      'legal placement and <=405um source/capture/transport reach',
                      'reset-tree regeneration and actual <=32 native census',
                      'bounded OR reduction, landed cross-root transport and measured calendar',
                      'actual obs_fault sink source, closed view and full STATUS proof'],
                fragment='// SOURCE PROPOSAL ONLY: apply source_connections before insertion; do not gate this fragment.\n'
                         + '\n'.join(fragment) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('die-v', 'port-bind', 'classification', 'out'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--commit', required=True)
    p.add_argument('--early-sticky', action='store_true', help='source-only distinct first-edge capture leaf')
    p.add_argument('--src-prefix', action='append', default=[])
    p.add_argument('--local-rtl', action='append', default=[])
    a = p.parse_args()
    pb = json.loads(a.port_bind.read_text())
    classified = json.loads(a.classification.read_text())
    declared = {(r['master'], r['port']) for r in classified['owed'] if r['cls'] == 'FAULT_OBS'}
    mods, _ = F.E.load_ports(pb, a.commit, a.src_prefix, a.local_rtl)
    rows = F.collect(a.die_v, mods, declared)
    out = prepare(a.die_v, mods, rows, early_sticky=a.early_sticky)
    out['source_commit'] = a.commit
    out['sources'] = {str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                      for f in (a.die_v, a.port_bind, a.classification)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in
                      ('nodes','fragment','domain_roots','source_connections','sources','owed')}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Emit the actual five-partition W5 HEAD producer/STREAM structural source cut.

Preserves every selected instance connection, clock, count strap and real ring.
Unselected inputs remain explicit typed boundary ports. No clocks/operands are
invented, no simulation is launched and no physical view is adopted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as D

PARTS = ['sl_W5_ctl', 'sl_W5_su_c', 'sl_W5_su_l0', 'sl_W5_su_l1', 'sl_W5_stm']


def emit(rtl, provider, include_sc=False):
    top_path = rtl/'qwen_compute_bound_top.sv'; top = top_path.read_text()
    parts = PARTS + (['sl_W5_sc'] if include_sc else [])
    conn = {}; bodies = []; census = []
    source_hashes = {top_path.name: hashlib.sha256(top_path.read_bytes()).hexdigest()}
    for part in parts:
        match = re.search(r'^\s*(\w+) '+part+r' \(\n(.*?)^    \);', top, re.M|re.S)
        if not match:
            raise ValueError('selected instance missing '+part)
        master = match[1]; src = rtl/(master+'.sv')
        modules = [m for m in D.parse_modules(src.read_text(), str(src)) if m.name == master]
        if len(modules) != 1:
            raise ValueError('actual master definition missing '+master)
        ports = modules[0].ports
        pairs = re.findall(r'\.(\w+)\((.*?)\)', match[2])
        if {p for p, _ in pairs} != set(ports):
            raise ValueError('partial selected connection source '+part)
        for pin, net in pairs:
            if re.fullmatch(r'\d+\x27[bdh][0-9a-fA-F]+', net):
                continue  # preserve actual immutable count/edgefall/K straps
            if not re.fullmatch(r'\w+', net):
                raise ValueError('unsupported original connection '+net)
            direction, ranges = ports[pin]
            width = ''.join(f'[{a}:{b}]' for a,b in ranges)
            row = conn.setdefault(net, dict(width=width, drivers=[], readers=[]))
            if row['width'] != width:
                raise ValueError('different selected typed bus widths '+net)
            row['drivers' if direction == 'output' else 'readers'].append(part+'.'+pin)
        bodies.append(match[0])
        source_hashes[src.name] = hashlib.sha256(src.read_bytes()).hexdigest()
        census.append(dict(part=part, master=master, ports=len(pairs)))
    for net, row in conn.items():
        if len(row['drivers']) > 1:
            raise ValueError('multiple real drivers '+net)
    p = json.loads(provider.read_text())
    start_nets = {o['net'] for o in p['native_outputs']}
    if start_nets != {'pst_'+part for part in parts}:
        raise ValueError('START source does not cover exact selected partition cone')
    clock_ports = [s['clock_port'] for s in p['stages']]
    reset = p['root_reset_source']['net']
    if reset in conn or set(clock_ports) & set(conn):
        raise ValueError('provider/boundary name collision')
    declarations = []
    for net, row in sorted(conn.items()):
        direction = 'output' if row['drivers'] else 'input'
        if net not in start_nets:
            declarations.append(f"    {direction} wire {row['width']} {net}")
    declarations += ['    input wire '+reset] + ['    input wire '+c for c in clock_ports]
    lines = ['// Actual frozen selected structural cut. SOURCE_ONLY; clocks are explicit.',
             'module qwen_bound_head_producer_cut (', ',\n'.join(declarations), ');']
    lines += ['    wire '+n+';' for n in sorted(start_nets)]
    bindings = {'rst_raw_n':reset, **{n:n for n in clock_ports}, **{n:n for n in start_nets}}
    lines += ['    ot_die_start_stages_native_cone u_start_provider ('+', '.join(f'.{k}({v})' for k,v in bindings.items())+');']
    lines += bodies + ['endmodule']
    manifest = dict(schema='bound_head_producer_source_cut/1', source_only=True,
                    executable=False, physical_qualified=False, partitions=census,
                    boundary={n:r for n,r in conn.items() if n not in start_nets},
                    provider_clock_ports=clock_ports, provider_root_reset=reset,
                    source_sha256=source_hashes,
                    provider_source_sha256=hashlib.sha256(provider.read_bytes()).hexdigest(),
                    no_added_pipeline_edges=True,
                    holds=['actual selected clock source/polarity and phase at every native/provider clock input',
                           'transitive real native leaf source closure and measured packet review before build',
                           'explicit native CTL command/BOOT/operand stimulus at exposed unselected boundaries',
                           'actual producer write observations before global HEAD dates or pad adoption'])
    return '\n'.join(lines)+'\n',manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rtl', type=Path, required=True);p.add_argument('--provider', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True);p.add_argument('--include-sc', action='store_true');a=p.parse_args()
    sv, doc=emit(a.rtl,a.provider,a.include_sc);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'producer_cut.sv').write_text(sv)
    (a.out/'producer_cut.json').write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps(dict(parts=len(doc['partitions']),boundary_ports=len(doc['boundary']),provider_clocks=len(doc['provider_clock_ports']),source_only=True)))


if __name__=='__main__':main()

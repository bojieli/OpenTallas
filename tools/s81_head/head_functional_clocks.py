#!/usr/bin/env python3
"""Emit explicit nominal clocks for a native HEAD component.

Use measured T/F partition-input and N/M START-node readouts at the selected
corner. Internal partition latency remains a declared plan assumption. This
simulation provider does not establish physical timing or programme admission.
"""
from __future__ import annotations
import argparse
import gzip
import json
import re
from pathlib import Path

PERIOD_PS = 833.0


def read_arrivals(path: Path) -> dict[tuple[str, str], float]:
    opener = gzip.open if path.suffix == '.gz' else open
    values = {}
    with opener(path, 'rt') as stream:
        for line in stream:
            fields = line.split()
            if len(fields) >= 4 and fields[0] in {'T', 'F', 'N', 'M'}:
                key = fields[0], fields[1]
                value = float(fields[2])
                if key in values and values[key] != value:
                    raise ValueError(f'conflicting measured arrival {key}')
                values[key] = value
    if not values:
        raise ValueError('no measured T/F/N/M arrivals')
    return values


def build(plan: dict, start: dict, arrivals: dict, corner: str) -> dict:
    if corner not in {'TT', 'FF'}:
        raise ValueError('native provider requires TT or FF')
    clocks = {}
    def add(name, rise, fall, basis):
        if not re.fullmatch(r'[A-Za-z_]\w*', name):
            raise ValueError(f'illegal clock identifier {name}')
        half = PERIOD_PS / 2
        if half + fall - rise <= 0 or half + rise - fall <= 0:
            raise ValueError(f'inverted measured edge order for {name}')
        item = dict(rise_ps=rise, fall_ps=fall, basis=basis)
        if name in clocks and clocks[name] != item:
            raise ValueError(f'conflicting source clock {name}')
        clocks[name] = item
    def actual(kind, name):
        try:
            return arrivals[kind, name]
        except KeyError as error:
            raise ValueError(f'missing measured {kind} {name}; no phase fallback') from error
    for node in start['stages']:
        if node['clock_source_root']:
            rise = fall = 0.0
        else:
            cell = node['clock_source_cell']
            rise, fall = actual('N', cell), actual('M', cell)
        # clock_source_cell is already the driver selected by A/Y in the
        # manifest. Applying A/Y a second time would choose the wrong source.
        add(node['clock_port'], rise, fall,
            dict(kind='manifest_source', cell=node['clock_source_cell'],
                 from_pin=node['clock_from']))
    parts = {}
    for part in plan['partitions']:
        name = part['name']
        clock = plan['partition_types'][part['type']]['clock']
        budget_key = 'insertion_ps' if corner == 'TT' else 'insertion_ff_ps'
        if budget_key not in clock:
            raise ValueError(f'{name} has no declared {corner} internal latency')
        internal = float(clock[budget_key])
        tap = 't_' + name + '__clk'
        port = 'pc_' + name
        add(port, actual('T', tap) + internal,
            actual('F', tap) + internal,
            dict(kind='physical_part_input+declared_internal', tap=tap,
                 internal_ps=internal))
        parts[name] = dict(clock=port, type=part['type'])
    return dict(scope='Nominal functional clock provider; internal latency is declared, not measured. No physical signoff or HOST admission.',
                corner=corner, period_ps=PERIOD_PS, arrival_convention='single STA max, early=late; asymmetric measured rise/fall retained',
                phase=clocks, parts=parts)


def verilog(profile: dict) -> str:
    lines = ['// Include inside a 1ns/1fs testbench; instance bodies stay unchanged.']
    for name, item in profile['phase'].items():
        rise, fall = item['rise_ps'], item['fall_ps']
        lines += [f'reg {name}=0;',
            f'initial begin #{(416.5 + rise)/1000:.9f} {name}=1; forever begin '
            f'#{(416.5 + fall-rise)/1000:.9f} {name}=0; '
            f'#{(416.5 + rise-fall)/1000:.9f} {name}=1; end end']
    return '\n'.join(lines) + '\n'


def primary_bindings(parent: str, profile: dict) -> dict:
    """Return per-instance primary-clock substitutions, preserving forwarded clocks."""
    pattern = re.compile(r'^\s*(ot_\w+)\s+(\w+)\s*\(\n(.*?)^\s*\);', re.M | re.S)
    result = {}
    for match in pattern.finditer(parent):
        module, part, body = match.groups()
        if part == 'u_die_start_stages':
            continue
        if part not in profile['parts']:
            raise ValueError(f'unexpected physical part {part}')
        ports = re.findall(r'\.(clk(?:_t\w+)?)\([^()]*\)', body)
        if not ports:
            raise ValueError(f'{part} has no literal primary clock connection')
        result[part] = dict(module=module, ports={p: profile['parts'][part]['clock'] for p in ports})
    if result.keys() != profile['parts'].keys():
        raise ValueError('parent clock coverage differs from selected plan')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--start', type=Path, required=True)
    parser.add_argument('--arrivals', type=Path, required=True)
    parser.add_argument('--corner', choices=['TT', 'FF'], required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    profile = build(json.loads(args.plan.read_text()), json.loads(args.start.read_text()), read_arrivals(args.arrivals), args.corner)
    profile['primary_clock_bindings'] = primary_bindings(args.parent.read_text(), profile)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/'clocks.vh').write_text(verilog(profile))
    (args.out/'clock_profile.json').write_text(json.dumps(profile, indent=2)+'\n')
    print('HEAD_FUNCTIONAL_CLOCKS', len(profile['phase']), 'clocks', len(profile['parts']), 'parts', args.corner)

if __name__ == '__main__':
    main()

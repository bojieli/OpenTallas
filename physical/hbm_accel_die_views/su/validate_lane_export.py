#!/usr/bin/env python3
"""Check an OpenSTA lane ETM against its routed ODB boundary inventory.

The inventory is OT_PIN|name|io_type|signal_type|iterm_count|master_names,
emitted from the same ODB as the export. Unconnected inputs and tie outputs
need no timing arcs; every other signal pin must retain its clock relation.
This checks export completeness, not leaf or parent timing closure.
"""
import argparse
import json
import re
from pathlib import Path


def pins(text):
    """Read pin groups in the flat write_timing_model output format."""
    result = {}
    for match in re.finditer(r'\bpin\s*\(\s*"?([^"\)]+)"?\s*\)\s*\{', text):
        start = pos = match.end()
        depth = 1
        while depth and pos < len(text):
            depth += (text[pos] == '{') - (text[pos] == '}')
            pos += 1
        if depth:
            raise ValueError('Unterminated pin group')
        name = match[1].strip()
        if name in result:
            raise ValueError(f'Duplicate pin {name}')
        result[name] = text[start:pos - 1]
    return result


def validate(view, inventory, name, clock):
    boundary = {}
    for line in inventory.read_text().splitlines():
        if line.startswith('OT_PIN|'):
            _, pin, direction, signal, count, masters = line.split('|')
            boundary[pin] = (direction, signal, int(count), masters.split(','))
    if not boundary or clock not in boundary:
        raise ValueError('Missing routed boundary inventory or clock')
    expected_inputs = {p for p, (d, s, n, _) in boundary.items()
                       if d == 'INPUT' and s == 'SIGNAL' and n and p != clock}
    expected_outputs = {p for p, (d, s, n, ms) in boundary.items()
                        if d == 'OUTPUT' and s == 'SIGNAL' and n
                        and not all(m.startswith(('TIEHI', 'TIELO')) for m in ms)}
    lef = (view / f'{name}.lef').read_text()
    lef_pins = set(re.findall(r'^\s*PIN\s+(\S+)', lef, re.M))
    errors = []
    if lef_pins != set(boundary):
        errors.append('LEF/ODB pin set mismatch')
    corners = {}
    for corner in ('ss', 'ff'):
        lib = (view / f'{name}_{corner}.lib').read_text()
        groups = pins(lib)
        if set(groups) != set(boundary):
            errors.append(f'{corner}: Liberty/ODB pin set mismatch')
        missing = []
        for pin in sorted(expected_inputs | expected_outputs):
            body = groups.get(pin, '')
            types = set(re.findall(r'timing_type\s*:\s*(\w+)', body))
            required = {'setup_rising', 'hold_rising'} if pin in expected_inputs else {'rising_edge'}
            related = set(re.findall(r'related_pin\s*:\s*"([^"]+)"', body))
            if not required <= types or clock not in related:
                missing.append(pin)
        corners[corner] = dict(missing_arcs=missing, pin_count=len(groups))
        if missing:
            errors.append(f'{corner}: {len(missing)} active pins missing clock arcs')
    return dict(ok=not errors, errors=errors, corners=corners,
                connected_data_inputs=len(expected_inputs), dynamic_outputs=len(expected_outputs),
                odb_pin_count=len(boundary), lef_pin_count=len(lef_pins))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--view', type=Path, required=True)
    ap.add_argument('--inventory', type=Path, required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--clock', default='clk')
    args = ap.parse_args()
    result = validate(args.view, args.inventory, args.name, args.clock)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)

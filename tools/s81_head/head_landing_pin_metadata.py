#!/usr/bin/env python3
"""Restore omitted audit metadata from the frozen HEAD pin plan, never from an ODB."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
from gen_rtl import parse_leaf_ports
from pin_audit import INTERIOR, pin_key


def sha(data):
    return hashlib.sha256(data).hexdigest()


def declared_bits(text, module):
    ports = parse_leaf_ports(text, module)
    if not ports:
        raise ValueError('wrapper module/header missing')
    result = set()
    for bus, (_, width) in ports.items():
        if not width:
            result.add(bus)
            continue
        m = re.fullmatch(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', width)
        if not m:
            raise ValueError(f'nonliteral wrapper width {bus}: {width}')
        hi, lo = map(int, m.groups())
        result.update(f'{bus}[{i}]' for i in range(min(hi, lo), max(hi, lo) + 1))
    return result


def derive(old, plan, freeze, bind, wrapper, module, plan_bytes):
    identity = (plan.get('die'), plan.get('type'))
    if identity[0] != 's81_head' or identity != (freeze.get('die'), freeze.get('type')):
        raise ValueError('frozen HEAD plan identity mismatch')
    if plan.get('schema') != 'opentallas.die_plan.partition_plan_pins.v1':
        raise ValueError('unexpected canonical pin-plan schema')
    if freeze.get('schema') != 'opentallas.partition_freeze.v1' or freeze.get('pins_sha256') != sha(plan_bytes):
        raise ValueError('frozen pin-plan hash mismatch')
    rows = plan['pins']
    expected = {p['name'] for p in rows}
    if len(expected) != len(rows) or freeze.get('pins') != len(rows):
        raise ValueError('duplicate or incorrect frozen plan pin count')
    if expected != {pin_key(p) for p in bind} or len(bind) != len(expected):
        raise ValueError('complete port-bind declaration differs from frozen plan')
    if declared_bits(wrapper, module) != expected:
        raise ValueError('complete wrapper ABI differs from frozen plan')
    seen = {pin_key(p) for p in old}
    if len(seen) != len(old) or not seen <= expected:
        raise ValueError('old face rows contain duplicate or undeclared pins')
    w, h = freeze['outline_um']
    additions = []
    for p in rows:
        name = p['name']
        if name in seen or INTERIOR.fullmatch(name):
            continue
        if not (0 <= p['x'] <= w and 0 <= p['y'] <= h):
            raise ValueError(f'declared pin outside frozen outline: {name}')
        m = re.fullmatch(r'(.*)\[(\d+)\]', name)
        bus, bit = (m[1], int(m[2])) if m else (name, None)
        # Plan records specify actual pin centres. Exact centre + inside-outline
        # checking is stricter than inventing a face from an observed BPin.
        additions.append(dict(bus=bus, bit=bit, layer=p['layer'], x=p['x'], y=p['y'], face='island'))
    result = old + additions
    if {pin_key(p) for p in result} | {n for n in expected if INTERIOR.fullmatch(n)} != expected:
        raise ValueError('source pin coverage incomplete')
    return result, dict(die=identity[0], type=identity[1], module=module,
                        original_face_rows=len(old), frozen_plan_rows=len(rows),
                        appended_rows=len(additions), audit_rows=len(result),
                        existing_interior_exclusions=sorted(n for n in expected - seen if INTERIOR.fullmatch(n)),
                        added_pin_names=[pin_key(p) for p in additions],
                        physical_or_abi_changes=False, observed_geometry_used_as_authority=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kit', required=True, type=Path)
    ap.add_argument('--wrapper', required=True, type=Path)
    ap.add_argument('--module', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--receipt', required=True, type=Path)
    a = ap.parse_args()
    paths = {n: a.kit / n for n in ('pins.json', 'plan_pins.json', 'freeze.json', 'port_bind_pins.json')}
    for out in (a.out, a.receipt):
        if out.exists() or out.resolve() in {p.resolve() for p in paths.values()}:
            raise ValueError('fresh output paths required; original metadata must remain intact')
    raw = {n: p.read_bytes() for n, p in paths.items()}
    docs = {n: json.loads(b) for n, b in raw.items()}
    wrapper_bytes = a.wrapper.read_bytes()
    if docs['freeze.json'].get('pins_file') != 'plan_pins.json':
        raise ValueError('freeze does not identify canonical plan_pins.json')
    result, receipt = derive(docs['pins.json'], docs['plan_pins.json'], docs['freeze.json'],
                             docs['port_bind_pins.json'], wrapper_bytes.decode(), a.module, raw['plan_pins.json'])
    receipt['input_sha256'] = {n: sha(b) for n, b in raw.items()} | {'wrapper': sha(wrapper_bytes)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(result, indent=1) + '\n').encode()
    a.out.write_bytes(body)
    receipt['output_sha256'] = sha(body)
    a.receipt.write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if not isinstance(v, (list, dict))}))


if __name__ == '__main__':
    main()

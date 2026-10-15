#!/usr/bin/env python3
"""Regenerate the literal activation host port inventory; reject unsupported syntax."""
import json
import re
from pathlib import Path


def update(root):
    path = root / 'rtl/hbm_accel/generic/peers/static_activation/source_contract.json'
    contract = json.loads(path.read_text())
    source = (path.parent / 'ot_hbm_sm_activation_host_static.sv').read_text()
    header = source.split('module ot_hbm_sm_activation_host_static(', 1)[1].split(');', 1)[0]
    ports = []
    direction, bits = None, 1
    for field in header.split(','):
        match = re.fullmatch(r'(?:(input|output)\s+wire\s*(?:\[(\d+):(\d+)\]\s*)?)?([A-Za-z_][A-Za-z_0-9]*)', field.strip())
        if not match:
            raise ValueError(f'Unsupported literal port declaration: {field}')
        if match[1]:
            direction = match[1]
            bits = abs(int(match[2])-int(match[3]))+1 if match[2] else 1
        if direction is None:
            raise ValueError('Port without declared direction')
        ports.append(dict(name=match[4], direction=direction, bits=bits))
    if len({port['name'] for port in ports}) != len(ports):
        raise ValueError('Duplicate port names')
    contract['ports'] = ports
    path.write_text(json.dumps(contract, indent=2)+'\n')
    return ports


if __name__ == '__main__':
    ports = update(Path(__file__).resolve().parents[2])
    print(f'PASS {len(ports)} ports / {sum(port["bits"] for port in ports)} scalar bits')

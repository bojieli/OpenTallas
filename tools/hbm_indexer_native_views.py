#!/usr/bin/env python3
"""Full-shape R25I native pin contracts, shared by block hardening and die assembly.

Run on an admitted compute host. The contracts reserve real score/selector ports;
they do not certify service striping, exactness, timing, or analog IP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCORE_PORTS = {
    'ck': (1, 'input', 'N'), 'rst': (1, 'input', 'N'),
    'ik': (8792, 'input', 'W'), 'ikc': (8, 'output', 'W'),
    'q': (571, 'input', 'E'), 's': (610, 'output', 'E'),
    'sc': (1, 'input', 'E'), 'st': (4, 'output', 'E'),
}
SEL_PORTS = {
    'ck': (1, 'input', 'N'), 'rst': (1, 'input', 'N'),
    'fs': (90, 'input', 'W'), 'qb': (1048, 'input', 'W'),
    'qbr': (1, 'output', 'W'), 'kin': (345, 'input', 'W'),
    'qo': (2284, 'output', 'S'), 'si': (2440, 'input', 'N'),
    'sc': (4, 'output', 'S'), 'to': (612, 'output', 'E'),
    'toc': (1, 'input', 'E'), 'co': (72, 'output', 'E'),
    'coc': (1, 'input', 'E'), 'ev': (2, 'output', 'E'),
}


def pin_record(master, width, height, ports, instances, params):
    # Face payloads use two routing tracks per pin. Keep clocks off the data
    # face runs: the M7 clock area pin is near the block centre, as in r25.
    record = dict(schema='opentallas.hbm_native_indexer_ports.v1', master=master,
        kind='index', w_um=width, h_um=height, obs_top=7, instances=instances,
        orients=['R0', 'MY', 'MX', 'R180'] if instances == 4 else ['R0'],
        params=params, ports={}, generator=dict(round='r25i',
            file='tools/hbm_indexer_native_views.py',
            sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        qualification='Native pin reservation; no functional or physical closure credit')
    for face in 'WENS':
        names = [name for name, (_, _, f) in ports.items() if f == face and name not in ('ck', 'rst')]
        total = sum(ports[name][0] for name in names)
        cursor = ((height if face in 'WE' else width) - total * 0.096) / 2
        for name in names:
            bits, direction, _ = ports[name]
            layer = 'M4' if face in 'WE' else 'M5'
            pins = []
            for bit in range(bits):
                along = round(round((cursor + (bit + 0.5) * 0.096 - 0.012) / 0.048) * 0.048 + 0.012, 6)
                if not 0.5 < along < (height if face in 'WE' else width) - 0.5:
                    raise ValueError(f'{master}.{name}: pins exceed the {face} face')
                x = 0.5 if face == 'W' else width - 0.5 if face == 'E' else along
                y = 0.5 if face == 'S' else height - 0.5 if face == 'N' else along
                pins.append([f'{name}[{bit}]', layer, round(x - 0.036, 6), round(y - 0.012, 6),
                             round(x + 0.036, 6), round(y + 0.012, 6)])
            record['ports'][name] = dict(bits=bits, direction=direction, face=face,
                layer=layer, dir_segments=[[0, bits, 'in' if direction == 'input' else 'out']], pins=pins)
            cursor += bits * 0.096
    for name, dy in (('ck', 0.0), ('rst', 2.16)):
        k0 = round((width / 2 - 0.016) / 0.064)
        candidates = [0.016 + 0.064 * (k0 + delta) for delta in range(-200, 201)]
        candidates = [x for x in candidates if abs(x % 10.8 - 3.7) <= 0.4 or abs(x % 10.8 - 9.1) <= 0.4]
        x = round(min(candidates, key=lambda x: abs(x - width / 2)), 6)
        y = round(round((height / 2 + dy) / 0.048) * 0.048, 6)
        record['ports'][name] = dict(bits=1, direction='input', face='area', layer='M7',
            dir_segments=[[0, 1, 'in']], pins=[[f'{name}[0]', 'M7', x - 0.032, y - 0.144, x + 0.032, y + 0.144]])
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / 'physical/hbm_accel_die_views/index/native')
    args = ap.parse_args()
    from uarch_model import hbm_indexer_r25i_physical_model
    model = hbm_indexer_r25i_physical_model()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'model.json').write_text(json.dumps(model, indent=1) + '\n')
    candidates = [
        ('hfd_idx_score_native', 2000.16, 3000.24, SCORE_PORTS, 4, dict(L=16, FA=6, CRED=128, FWD=0)),
        ('hfd_idx_score_native_c2', 2000.16, 3402.0, SCORE_PORTS, 4, dict(L=16, FA=6, CRED=128, FWD=0)),
        ('hfd_idx_sel', 1399.656, 844.56, SEL_PORTS, 1, dict(T=1, LA=7, MEMV=1, READLAT=2)),
    ]
    for master, width, height, ports, count, params in candidates:
        record = pin_record(master, width, height, ports, count, params)
        path = args.out / master
        path.mkdir(parents=True, exist_ok=True)
        (path / 'ports.json').write_text(json.dumps(record, indent=1) + '\n')
        print(master, width, height, sum(p['bits'] for p in record['ports'].values()))


if __name__ == '__main__':
    main()

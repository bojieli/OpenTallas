#!/usr/bin/env python3
"""Source-bound preliminary bit assignment for enlarged v6b sucx/cij windows.

This proves port coverage, track alignment and per-face capacity only. PG stripe
clearance, peer pin agreement, routing and native physical timing remain open.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    a = ap.parse_args()
    d = Path(a.plan)
    r = json.loads((d / 'recovery.json').read_text())
    p = json.loads((d / 'corrected.P.json').read_text())
    report = {}
    for n in [f'sucx_{q}' for q in ('SW', 'SE', 'NW', 'NE')] + ['cij_SW']:
        ports = r['source_pins'][n]['ports']
        groups = {f: [] for f in 'NSEW'}
        if n.startswith('sucx'):
            q = n[5:]
            west, east = ('W', 'E') if q.endswith('W') else ('E', 'W')
            coll, misc = ('S', 'N') if q.startswith('S') else ('N', 'S')
            for g in range(4):
                f = west if g < 2 else east
                for port, width in [('inj_q', 1024), ('dw_d', 1024), ('dw_row', 18), ('dw_v', 2)]:
                    groups[f].append((port, g * width, width))
            stream = ['inj_rd', 'inj_addr', 'inj_d', 'del_valid', 'del_flit', 'del_obase', 'rc_v', 'rc_tag', 'rc_d', 'rr_v', 'rr_tag', 'rr_d']
            for port in stream:
                groups[coll].append((port, 0, ports[port]['bits']))
            used = {x[0] for items in groups.values() for x in items}
            for port in ports.keys() - used:
                groups[misc].append((port, 0, ports[port]['bits']))
        else:
            for f, names in dict(N=['su_inj_d'], E=['idx_tx_v', 'idx_tx'],
                                 S=['inj_rd', 'inj_idx', 'inj_addr', 'inj_d'], W=['clk', 'rst_n', 'fault']).items():
                groups[f] = [(port, 0, ports[port]['bits']) for port in names]
        seen = {k: set() for k in ports}
        faces = {}
        for f, items in groups.items():
            length = p[n]['w'] if f in 'NS' else p[n]['h']
            bits = sum(b for _, _, b in items)
            cursor = 0.012 + math.ceil(((length - bits * 0.096) / 2 - 0.012) / 0.048) * 0.048
            pins = []
            for port, low, width in sorted(items):
                centers = [round(cursor + (i + 0.5) * 0.096, 3) for i in range(width)]
                # Shift half a pin to keep every centre on 0.012 + k*0.048.
                centers = [round(c - 0.048, 3) for c in centers]
                for bit in range(low, low + width):
                    if bit in seen[port]:
                        raise ValueError(f'duplicate {n}.{port}[{bit}]')
                    seen[port].add(bit)
                pins.append(dict(port=port, low=low, bits=width, bit_centres_um=centers))
                cursor += width * 0.096
            faces[f] = dict(bits=bits, length_um=length, utilization=round(bits * 0.096 / length, 5),
                            capacity_pass=bits * 0.096 <= 0.60 * length,
                            layer='M5' if f in 'NS' else 'M4', pins=pins)
        missing = {port: len(set(range(v['bits'])) - seen[port]) for port, v in ports.items()
                   if set(range(v['bits'])) != seen[port]}
        report[n] = dict(source=r['source_pins'][n], outline=p[n], faces=faces, missing=missing,
                         assignment_pass=not missing and all(f['capacity_pass'] for f in faces.values()),
                         qualification='PRELIMINARY_NO_PHYSICAL_VIEW',
                         open=['PG stripe clearance', 'peer exact pins', 'all incident route reach and cuts',
                               'clock insertion/spread', 'TT setup / FF hold / DRC0'])
    out = dict(schema='opentallas.hbm.join_faces.v1', masters=report,
               pass_all=all(x['assignment_pass'] for x in report.values()))
    (d / 'join_faces.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({n: {f: x['bits'] for f, x in v['faces'].items()} for n, v in report.items()}))
    print('all source bits assigned, capacities pass:', out['pass_all'])


if __name__ == '__main__':
    main()

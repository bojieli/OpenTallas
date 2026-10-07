#!/usr/bin/env python3
"""Map the actual SMH element pin plan to the existing die packet contract.

This is a coverage artifact, not an abstract or a timing substitution. Unbound
real pins prevent adoption; no tie-offs or new protocol encodings are inferred.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import die_top_lint as logical
import hbm_accel_smh_physical as physical

ROOT = Path(__file__).resolve().parents[1]


def contract():
    g = physical.GEOM
    pos, die, hcore = physical.floorplan(g)
    fx, _ = pos['front']
    pins = {}
    for name, layer, _, x, y in physical.front_pins(g, hcore):
        if layer == 'M5':
            pins[name] = dict(layer=layer, xy_um=[round(fx + x, 3), die[1] if y > 0 else 0.0])
    pins['clk'] = dict(layer='M5', xy_um=[round(round((fx + 4.0 - 0.012) / 0.048) * 0.048 + 0.012, 3), die[1]])
    rtl = ROOT / 'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv'
    header = rtl.read_text().split('module ot_hbm_accel_smh #(', 1)[1].split('input  wire', 1)[1].split(');', 1)[0]
    header = 'input wire' + header
    directions = dict((name, direction) for direction, name in re.findall(
        r'\b(input|output)\s+wire\s*(?:\[[^\]]+\])?\s*(\w+)\s*[,\n]', header + '\n'))
    for name, row in pins.items():
        row['direction'] = directions[re.sub(r'\[\d+\]$', '', name)]
    bound = set()
    packets = {}
    model = logical.H.build(logical.H.R24SM3, network_probe=True)
    layout = logical.real_blocks('hbm', model)['hfd_sm']['binding']
    for packet, names in layout.items():
        rows = []
        for bit, name in enumerate(names):
            if name is None:
                rows.append(dict(bit=bit, real_pin=None, role='unassigned_logical_padding'))
                continue
            assert name in pins and name not in bound, (packet, bit, name)
            bound.add(name)
            rows.append(dict(bit=bit, real_pin=name, **pins[name]))
        packets[packet] = rows
    unbound = {name: pins[name] for name in sorted(pins.keys() - bound)}
    sources = ['tools/die_top_lint.py', 'tools/hbm_accel_die_fp.py', 'tools/hbm_accel_smh_physical.py',
               'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv', 'tools/hbm_smh_actual_pin_contract.py']
    return dict(schema='opentallas.hbm.smh.actual_pin_contract.v1',
                actual_master='ot_hbm_accel_smh', logical_master='hfd_sm',
                die_um=die, physical_pieces=27, actual_pin_count=len(pins),
                bound_pin_count=len(bound), unbound_pin_count=len(unbound),
                packets=packets, unbound_pins=unbound,
                added_cycles=0, added_register_bits=0, added_logic_gates=0,
                scope='Exact planned pin geometry and existing packet aliases only; not routed timing evidence',
                complete=not unbound, adoption=False,
                generator_variant='R24SM3',
                blockers=['Unbound op_xb and start_ready require explicit command source and acknowledgement wiring',
                          'Real top routed LEF/SS/FF abstracts and full pin agreement remain required'],
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = contract()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(f"actual={result['actual_pin_count']} mapped={result['bound_pin_count']} "
          f"unbound={result['unbound_pin_count']} complete={result['complete']}")


if __name__ == '__main__':
    main()

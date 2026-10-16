#!/usr/bin/env python3
"""Offline fixed-calendar migration native-compact-0253 -> native-retire-0600 (H-NETLIST 0600), every edge preserved.

SW NC 3->2 (client1 retired; client2 -> 1; replay code 3 -> 2); NW NC 3->0 (clients 0..2 retired; replay -> 0, CW 2->1);
NE RG 5->4 (read group3 retired, codes >=4 decrement incl. packet code), WG 3->2 (write group2 retired, codes >=3
decrement). Referencing a retired resource is an error; no runtime adapter or rescheduling is introduced.
"""
import argparse, copy, json
from pathlib import Path
from vm_abi_remap_0253 import chunks, packed


def _clients(cycle, keep, nold):
    for field, width in [('client_seq', 2), ('response_enable', 1), ('response_seq', 2)]:
        if field in cycle:
            values = chunks(cycle[field], width, nold)
            for k in range(nold):
                if k not in keep and values[k]:
                    raise ValueError(f'{field} references retired client{k}')
            cycle[field] = packed([values[k] for k in keep], width)


def _codes(cycle, field, enable, count, wold, wnew, cmap):
    if field not in cycle:
        return
    values = chunks(cycle[field], wold, count)
    out = []
    for lane, v in enumerate(values):
        active = (cycle.get(enable, 0) >> lane) & 1
        if v not in cmap:
            if active:
                raise ValueError(f'active retired {field} code {v}')
            out.append(0)
        else:
            out.append(cmap[v])
    cycle[field] = packed(out, wnew)


def migrate(schedule, quadrant):
    out = copy.deepcopy(schedule)
    for cycle in out['cycles']:
        for k, v in cycle.items():
            if isinstance(v, str):
                cycle[k] = int(v, 0)
        if quadrant == 'SW':
            _clients(cycle, [0, 2, 3], 4)
            _codes(cycle, 'bank_client', 'bank_enable', 8, 2, 2, {0: 0, 2: 1, 3: 2})
            _codes(cycle, 'hub_ring_client', 'hub_ring_enable', 2, 2, 2, {0: 0, 2: 1, 3: 2})
        if quadrant == 'NW':
            _clients(cycle, [3], 4)
            _codes(cycle, 'bank_client', 'bank_enable', 8, 2, 1, {3: 0})
            _codes(cycle, 'hub_ring_client', 'hub_ring_enable', 2, 2, 1, {3: 0})
        if quadrant == 'NE':
            _codes(cycle, 'rslot', 'rslot_v', 8, 3, 3, {0: 0, 1: 1, 2: 2, 4: 3, 5: 4})
            _codes(cycle, 'wslot', 'wslot_v', 8, 3, 3, {0: 0, 1: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6})
    out['abi_migration'] = 'native-retire-0600; offline only, cycles unchanged'
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('quadrant', choices=['SW', 'SE', 'NW', 'NE'])
    ap.add_argument('input', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    a.output.write_text(json.dumps(migrate(json.loads(a.input.read_text()), a.quadrant), indent=2) + '\n')


if __name__ == '__main__':
    main()

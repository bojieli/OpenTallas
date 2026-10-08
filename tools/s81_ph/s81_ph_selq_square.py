#!/usr/bin/env python3
"""CLAUDE s81-blocks 2026-10-07: a SQUARER selector quarter outline for die variant contract_selsq (structural
area/shape lever, same area +0.4 %): dsfd_selt_q2 at 432 x 280.8 um instead of 756 x 159.84.  The 756-um tile is
longer than one SS cycle of wire reach (~504 um a stage, memory ss-wire-reach) and its W->E data flow (lane on W,
status/output/command on E) left ~60 failing classes (-60..-434 ps) in s81ph-dsfd_selt_q-cd3337221-b.  Same faces,
same port order (lane W; t_s / t_o / f_c / f_cr E), six macros in two rows of three along the S edge
(tiles/place_macros_q2_sq.tcl).  Die adoption (selector slab re-floorplan) is the die agent's call."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_tiles_plan as T   # noqa: E402

W, H = 432.0, 280.8


def main():
    spec = {'master': 'dsfd_selt_q2', 'w_um': W, 'h_um': H, 'domain': 'stream_1p2', 'orients': ['R0', 'MY'],
            'note': 'SAFE selector quarter, square variant (contract_selsq): six 128x256 macros 2 x 3 along S',
            'ports': [['lane', 515, 'input', 'W', 'M4', 2, 0.5], ['ck', 1, 'input', 'W', 'M4', 1, 0.05],
                      ['rst', 1, 'input', 'W', 'M4', 1, 0.07],
                      ['t_s', 865, 'output', 'E', 'M4', 2, 0.30], ['t_o', 354, 'output', 'E', 'M4', 2, 0.66],
                      ['f_c', 66, 'input', 'E', 'M4', 2, 0.84], ['f_cr', 1, 'input', 'E', 'M4', 1, 0.92]]}
    ports = T.plan(spec)
    d = T.ROOT / 'physical/s81_ph_views/ports/contract_selsq/dsfd_selt_q2'
    d.mkdir(parents=True, exist_ok=True)
    rec = dict(master='dsfd_selt_q2', die='contract_selsq', w_um=W, h_um=H, obs_top=7, domain='stream_1p2', instances=None,
               orients=spec['orients'], ports=ports, generator=dict(file='tools/s81_ph/s81_ph_selq_square.py', spec=spec))
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    L = ['# dsfd_selt_q2 square (contract_selsq pin plan, tools/s81_ph/s81_ph_selq_square.py)']
    for p in sorted(ports):
        for nm, ly, x0, y0, x1, y1 in ports[p]['pins']:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')
    (d / 'ports.svh').write_text(',\n'.join(f"    {ports[p]['direction']} wire [{ports[p]['bits'] - 1}:0] {p}"
                                           for p in sorted(ports)) + '\n')
    print('ok', {p: len(v['pins']) for p, v in ports.items()})


if __name__ == '__main__':
    main()

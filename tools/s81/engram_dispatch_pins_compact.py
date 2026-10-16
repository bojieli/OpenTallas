#!/usr/bin/env python3
"""Compact candidate pins for ot_s81_engram_dispatch (VIS-ROM 10-16: v20 129.6x86.4 outline is 4.8% filled).

Same ports, faces, layers, bit order and 0.096-um pitch as tools/s81/engram_dispatch_pins.py; only the outline
shrinks to 34.56 x 34.56 um (~537 um2 of cells -> ~45% fill) and each face's pin run is centred on its face.
CANDIDATE for S-DIE re-binding (absolute die pin positions move); written to v29_engram_dispatch_compact only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v19_pins_1014 as V
R = Path(__file__).resolve().parents[2]
W = H = 34.56
def main():
    out = R / 'physical/s81_die_pins/v29_engram_dispatch_compact'
    out.mkdir(parents=True, exist_ok=True)
    pp = {}
    for face, ports in [('E', [('c_cmd', 85), ('c_done', 9), ('c_st', 2)]), ('W', [('t_mix_cmd', 85), ('f_mix_done', 9), ('f_mix_st', 2)]),
                        ('N', [('t_lk_cmd', 85), ('f_lk_done', 9), ('f_lk_st', 2)])]:
        run = sum(n for _, n in ports) * .096 + .96 * (len(ports) - 1)
        x = round(round((W - run) / 2 / .096) * .096, 3)
        for p, n in ports:
            pp[p] = [[face, 'M5' if face == 'N' else 'M4', round(x + .096 * i, 3), .084] for i in range(n)]
            x += n * .096 + .96
    pp['ck'] = [['S', 'M5', 17.244, .084]]
    pp['rst'] = [['S', 'M5', 18.204, .084]]
    fn = V.write(out, 'ot_s81_engram_dispatch', [W, H], pp, 'ck',
                 'compact candidate: same ports/faces/pitch as v20, runs centred; S-DIE must re-bind', 'v29_engram_dispatch_compact',
                 {'source': 'tools/s81/engram_dispatch_pins_compact.py', 'clock_entries': {'stream': ['ck[0]']},
                  'reset_entries': {'stream': ['rst[0]']}, 'vector_ports': ['ck', 'rst']})
    tcl = fn.with_suffix('.tcl')
    tcl.write_text(tcl.read_text().replace('-pin_name {ck}', '-pin_name {ck[0]}').replace('-pin_name {rst}', '-pin_name {rst[0]}'))
    print('ENGRAM_DISPATCH compact candidate', W, 'x', H)
if __name__ == '__main__':
    main()

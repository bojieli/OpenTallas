#!/usr/bin/env python3
"""L2H-GEN2D-RST 10-19: planning LEFs of the compact carrier tiles hbfd_rrl_chop / hbfd_rrl_csync (cpad<N> share the chop
footprint).  8.64 x 2.16 um (40 x .216 sites, two 1.08 um row pairs): inside the joint corridor's checked 10.728 x 2.844 um
home envelope.  Pins mid-face so a recorded <= 399.6 um centre-to-centre polyline stays <= 405 um pin to pin.
The die GEN re-assigns SYNTH abstract pins (top-down); die_case_v16's reset gate re-checks actual reach.
    python3 gen_lef.py OUTDIR [W H]"""
import sys
from pathlib import Path
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
W, H = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (8.64, 2.16)
PINS = {'clk': ('INPUT', W * 0.25, H), 'rst_n_in': ('INPUT', W * 0.5, 0.0), 'rst_n': ('OUTPUT', W * 0.75, H)}
for m in ('hbfd_rrl_chop', 'hbfd_rrl_csync'):
    b = [f'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\nUNITS\n    DATABASE MICRONS 1000 ;\nEND UNITS\n\nMACRO {m}\n'
         f'  FOREIGN {m} 0 0 ;\n  CLASS BLOCK ;\n  SIZE {W:g} BY {H:g} ;\n']
    for p, (d, x, y) in PINS.items():
        y0, y1 = (y - 0.024, y) if y > 0 else (0.0, 0.024)
        b.append(f'  PIN {p}\n    DIRECTION {d} ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n'
                 f'        RECT  {x - 0.012:.3f} {y0:.3f} {x + 0.012:.3f} {y1:.3f} ;\n    END\n  END {p}\n')
    b.append(f'END {m}\n\nEND LIBRARY\n')
    (out / f'{m}.lef').write_text(''.join(b))
print('LEF', W, H, sorted(p.name for p in out.glob('*.lef')))

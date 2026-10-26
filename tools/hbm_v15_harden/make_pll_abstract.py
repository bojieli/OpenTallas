#!/usr/bin/env python3
"""H-HARDEN 2026-10-15: HBM die PLL reservation abstract ot_hbm_pll_bb (analog hard IP = allowed modelled hard core,
owner rule 10-14 08:05).  Same vendor class and outline as the S81 die PLL abstract (physical/s81_ph_views/macros/
ot_s81_pll_bb: 172.8 x 172.8 um, M4 west-edge pins, M4 PG rails, M1-M4 obstruction, pins only / no timing claim);
pins renamed to the HBM interface of rtl/hbm_accel/control/ot_hbm_pll_bb.sv (refclk, reset_n -> clk_stream, clk_serial,
clk_hbm, clk_link, locked), one more output on the same 12.288 um pitch.  Liberty: pins only, no arcs (the PLL output
clocks are defined in the tile SDC at these pins)."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'physical/s81_ph_views/macros/ot_s81_pll_bb'
OUT = ROOT / 'physical/hbm_pll_views/ot_hbm_pll_bb'
OUT.mkdir(parents=True, exist_ok=True)
REN = {'pd': 'reset_n', 'ck_stream': 'clk_stream', 'ck_serial': 'clk_serial', 'ck_hbm': 'clk_hbm', 'lock': 'locked'}
lef = (SRC / 'ot_s81_pll_bb.lef').read_text()
for a, b in REN.items():
    lef = re.sub(rf'\b(PIN|END) {a}\b', rf'\1 {b}', lef)
lef = lef.replace('ot_s81_pll_bb', 'ot_hbm_pll_bb').replace('CLAUDE S81-PH: S81 die PLL', 'H-HARDEN 10-15: HBM die PLL (cloned from the S81 die PLL abstract)')
# clk_link: next free M4 west-edge site on the pin pitch (locked sits at 123.648; clk_link goes to 135.936)
link = ('  PIN clk_link\n    DIRECTION OUTPUT ;\n    USE CLOCK ;\n    SHAPE ABUTMENT ;\n    PORT\n      LAYER M4 ;\n'
        '      RECT 0.000 135.936 0.024 135.960 ;\n    END\n  END clk_link\n')
i = lef.index('  PIN VDD')
lef = lef[:i] + link + lef[i:]
for o in ('clk_stream', 'clk_serial', 'clk_hbm'):
    lef = re.sub(rf'(  PIN {o}\n    DIRECTION OUTPUT ;\n    USE )SIGNAL', r'\1CLOCK', lef)
(OUT / 'ot_hbm_pll_bb.lef').write_text(lef)
for c in ('tt', 'ff', 'ss'):
    lib = (SRC / f'ot_s81_pll_bb_{c}.lib').read_text()
    for a, b in REN.items():
        lib = re.sub(rf'pin \({a}\)', f'pin ({b})', lib)
    lib = lib.replace('ot_s81_pll_bb', 'ot_hbm_pll_bb').replace('CLAUDE S81-PH: S81 die PLL', 'H-HARDEN 10-15: HBM die PLL')
    j = lib.index('    pin (locked)')
    lib = lib[:j] + '    pin (clk_link) { direction : output; max_capacitance : 200; related_power_pin : VDD; related_ground_pin : VSS; }\n' + lib[j:]
    (OUT / f'ot_hbm_pll_bb_{c}.lib').write_text(lib)
print('wrote', OUT)

#!/usr/bin/env python3
"""DRIVE-S81-LEP 10-20: s81sl_lep r5 kits from r4m (no-region full core rows).
r5e = RX landing SRAM column moved beside the E (ri) face, mirrored MY so rd_out faces ri; outline 561.6 x 518.4; km K16.
r5k = r4m floorplan unchanged, km K16 (clock-only fallback)."""
import json, shutil, sys
from pathlib import Path
WT = Path(sys.argv[1]); RT = WT / 'physical/ref_tile'; src = RT / 's81sl_lepwd_r4m'
WHY_E = ('DRIVE-S81-LEP r5e (r4m lepnh twin gate: GRT 0 but clock spread TT 114.6 / FF 106.8 at km K8 and setup macro->reg -94.9 '
  '(RX SRAM rd_out -> ri pin flop, RX banks in two N rows at x 43..440 drive ri pins on the E face up to ~900 um away) plus reg->out -76): '
  'wide-bus repartition, 0 added cycles: the 10 RX landing SRAMs (g_rx[0] banks 0-4, g_rx[1] banks 0-4) move into ONE column beside '
  'the E face (x 475.2, y 43.2 + 43.2k, orient MY so rd_out faces the ri pins); the 1104-bit RX read bus stays inside a 35-um E strip, '
  'the long W->E RX hop is the flop->flop li pin flop (dq) -> LOCAL_WD register / SRAM write (registered both ends); TX columns unchanged '
  '(rd_out on their W edge facing lo, TX read stage qd). Outline 475.2 x 561.6 -> 561.6 x 518.4 (W/E 4.3/um, S 705 pins/561.6). '
  'Clock: km regional roots K 8 -> 16 (432 gate of this leaf: K16 spread 67.3 / 60.5). Same RTL, ports, cycles, SDC.')
WHY_K = ('DRIVE-S81-LEP r5k (fallback of r5e): r4m floorplan unchanged; km regional roots K 8 -> 16 (r4m lepnh twin: K8 spread '
  'TT 114.6 / FF 106.8 > 80; 432 gate of this leaf: K16 67.3 / 60.5). Same RTL, ports, cycles, SDC.')
for v in ('e', 'k'):
    name = f's81sl_lepwd_r5{v}'; dst = RT / name
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir()
    s = json.loads((src / 'spec.json').read_text())
    s['name'] = name
    s['job']['owner'] = 'Claude:DRIVE-S81-LEP'; s['job']['branch'] = 'claude/s81-lep-r5-1020'; s['job']['tag'] = name
    s['orfs_vars']['OT_CKKM_K'] = '16'
    if v == 'e':
        s['structural_change'] = WHY_E
        s['outline'] = {'w': 561.6, 'h': 518.4}
        for m in s['macros']:
            if '*g_rx?' in m['inst']:
                lane = int(m['inst'].split('g_rx?')[1][0]); bank = int(m['inst'].split('g_bank?')[1][0])
                m['at'] = [475.2, round(43.2 * (1 + lane * 5 + bank), 1)]; m['orient'] = 'MY'
        s['pin_ranges']['clk'] = [255.2, 263.2]; s['pin_ranges']['rst_n'] = [263.2, 271.2]
        s['fill_reason']['pin_bound'] = ('Twenty true SRAM macros (62464um2): two TX columns (x 43.2 / 259.2, 5 rows on 86.4 pitch) + one RX '
          'column beside the E face (x 475.2, 10 rows on 43.2 pitch, MY) require 561.6x518.4. W face 2234 pins/518.4um (4.3/um), '
          'E 2208/518.4 (4.3/um), host S 705/561.6 (1.3/um). No region: full core rows, logic in the W/E face strips and inter-macro '
          'channels (r5e); the tile outline is set by macro pitch and pin faces, not a squeezed util target.')
    else:
        s['structural_change'] = WHY_K
    (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    (dst / 'regen.py').write_text((src / 'regen.py').read_text())
    (dst / 'README.md').write_text(f'# {name} (DRIVE-S81-LEP 10-20)\n{s["structural_change"]}\n')
    print('made', name)

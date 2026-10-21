#!/usr/bin/env python3
"""DRIVE-S81-LEPMU 10-20: MU endpoint kits s81sl_lepmu{a,h}_r6{e,k,t} from the n32 kits (source 6cb5f3eff NATIVE32 + LOCAL_WA).
e = LEP r5e floorplan (RX SRAM column beside E/ri face, MY; 561.6x518.4) + ONE TritonCTS tree (LEP r5f / LEPNH r5a: KM-8 unequal depths)
k = same floorplan + km K16 (LEP r5e clock)
t = n32 floorplan unchanged (a: GRT 0) + ONE TritonCTS tree (clock-only fallback)."""
import json, shutil, subprocess, sys
from pathlib import Path
WT = Path(sys.argv[1]); RT = WT / 'physical/ref_tile'
FLOOR_E = ('wide-bus repartition, 0 added cycles (twin of DRIVE-S81-LEP r5e): the 10 RX landing SRAMs move into ONE column beside the E '
  'face (x 475.2, y 43.2+43.2k, orient MY so rd_out faces the ri pins); n32 gate had RX banks in two N rows across the width -> '
  'macro->reg rtq -233/-275 ps at placement (SRAM q -> E-face ri / N-face ml_wd up to ~500 um). RX read bus now stays in an E strip whose '
  'top end meets the N-face ml pins; TX columns unchanged (x 43.2 / 259.2, 86.4 pitch). Outline 475.2x561.6 -> 561.6x518.4 '
  '(W 2318/518.4 = 4.5/um, E 2362/518.4 = 4.6/um, N ml 2211/561.6 = 3.9/um, S host 705/561.6).')
CLK_ONE = ('Clock: NO km split, one TritonCTS tree (n32 gate km K8: a TT/FF spread 121.1/110.6, h 83.2/81.7; LEPNH 10-20: K8 unequal '
  'cluster depths 4..6 under a blind 8-sink top tree; pre-native one-tree lepnh 40.2/36.8).')
CLK_K16 = 'Clock: km K 8 -> 16 (432 gate of the lep leaf: K16 spread 67.3/60.5).'
KEEP_A = 'keep list: ot_s81sl_lep_status_region removed for _a (HOST_EN 0 instantiates none; n32 a keep_modules FAIL).'
for t in ('a', 'h'):
    src = RT / f's81sl_lepmu{t}_n32'
    for v in ('e', 'k', 't'):
        name = f's81sl_lepmu{t}_r6{v}'; dst = RT / name
        if dst.exists(): shutil.rmtree(dst)
        dst.mkdir()
        s = json.loads((src / 'spec.json').read_text())
        s['name'] = name
        s['job'].update(owner='Claude:DRIVE-S81-LEPMU', branch='claude/drive-s81-lepmu-1020', tag=name,
                        views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}')
        if t == 'a':
            s['route']['synth_keep_modules'] = [m for m in s['route']['synth_keep_modules'] if m != 'ot_s81sl_lep_status_region']
        why = []
        if v in ('e', 'k'):
            s['outline'] = {'w': 561.6, 'h': 518.4}
            for m in s['macros']:
                if '*g_rx?' in m['inst']:
                    lane = int(m['inst'].split('g_rx?')[1][0]); bank = int(m['inst'].split('g_bank?')[1][0])
                    m['at'] = [475.2, round(43.2 * (1 + lane * 5 + bank), 1)]; m['orient'] = 'MY'
            s['pin_ranges']['clk'] = [255.2, 263.2]; s['pin_ranges']['rst_n'] = [263.2, 271.2]
            why.append(FLOOR_E)
            s['fill_reason']['pin_bound'] = ('Twenty true SRAM macros (62464um2): two TX columns (x 43.2 / 259.2, 5 rows on 86.4 pitch) + one RX '
              'column beside the E face (x 475.2, 10 rows on 43.2 pitch, MY) require 561.6x518.4; faces W 4.5/um, E 4.6/um, N 3.9/um. '
              'No region: full core rows, logic in face strips and inter-macro channels (LEP r5e twin); outline set by macro pitch and pin '
              'faces, not a squeezed util target. RULE FREEZE 10-20: tile fill is guidance, die GRT/STA decide.')
        else:
            why.append('n32 floorplan unchanged (a gate: GRT overflow 0).')
        if v == 'k':
            s['pre_cts_extra'] = ['physical/common_flow/clock_split_km.tcl']; s['orfs_vars']['OT_CKKM_K'] = '16'; why.append(CLK_K16)
        else:
            s['pre_cts_extra'] = []; s['orfs_vars'].pop('OT_CKKM_K', None); why.append(CLK_ONE)
        if t == 'a': why.append(KEEP_A)
        s['structural_change'] = f'DRIVE-S81-LEPMU r6{v} (n32 gates FAIL: clock_rule spread, a keep_modules, h GRT ovf 2): ' + ' '.join(why) + \
            ' Same RTL (6cb5f3eff NATIVE32=1 incl LOCAL_WA, RX_SRAM=1, IN_PIPE=1), ports, cycles, SDC.'
        (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
        (dst / 'README.md').write_text(f'# {name} (DRIVE-S81-LEPMU 10-20)\n\n{s["structural_change"]}\n\n'
          'SAFE checklist: 1 pins source-registered (pin flops both faces), 2-stage reset landing PASS; 2 reach: gate measures (e/k remove the '
          '~500 um RX SRAM -> ri hop); 3 fanout: exact native census max 32 incl reset (attempt5/wc A40822/H45237 roots) PASS; 4 depth '
          '368/392 ps 12 levels PASS; 5 storage 20 SRAM PASS; 6 macros on 43.2 lattice, full rows, aspect <=1.1, faces <=4.6/um, '
          'fill pin-bound (guidance); 7 clock one tree or km16, spread <=80 TT+FF measured by gate, io_hold_margin 0.03; '
          '8 schedule: 0 added cycles.\n')
        r = subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen', str(dst / 'spec.json')], cwd=WT, capture_output=True, text=True)
        print(name, r.returncode, r.stdout[-300:], r.stderr[-600:])

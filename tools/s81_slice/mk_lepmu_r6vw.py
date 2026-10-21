#!/usr/bin/env python3
"""S81-HARV-1021 10-21: MU endpoint kits s81sl_lepmu{a,h}_r6{v,w} from r6e (same RTL / floorplan / pins / witnesses).

Why: every sink-driven TritonCTS variant of the r6e floorplan leaves the pin-flop spread on the 80 ps line (a: r6e one tree
83.2/78.0, r6k km16 93.3/95.5, r6g balance 98.5/90.1, r6u 110.4/97.3; h: r6e 82.6/76.5, r6g 61.5/55.0 = submitted).  The
18-20k flops sit in three full pin faces (N 2211, W 2326, E 2370 pins) around a 20-SRAM core, ~560 um across, fed from one
W-face port: a blind sink tree balances clusters, not the faces.  Structural change: a PLANNED balanced clock distribution
(physical/common_flow/clock_spine.tcl: binned leaves, recursive bisection, repeated L trunks around macros, leaves padded to
equal measured arrival; each SRAM clock pin its own leaf), no TritonCTS for clk.
v = spine, symmetric insertion-aware topology (SYM 1 + tree pad + safe balance), leaf 16 sinks / 30 um bins.
w = spine, plain bisection (SYM 0), leaf 24 sinks / 30 um bins (parallel fallback, different topology)."""
import json, shutil, subprocess, sys
from pathlib import Path
WT = Path(sys.argv[1]); RT = WT / 'physical/ref_tile'
KITS = sys.argv[2:] or ['a:v', 'a:w', 'h:v']
VARS = {
    'v': {'OT_SPINE_SYM': '1', 'OT_SPINE_TREE_PAD': '1', 'OT_SPINE_SAFE_BALANCE': '1', 'OT_SPINE_LEAF_N': '16',
          'OT_SPINE_BIN': '30', 'OT_SPINE_ITERS': '20', 'OT_SPINE_TOL_PS': '8', 'OT_SPINE_MACRO_LEAF': '1'},
    'w': {'OT_SPINE_LEAF_N': '24', 'OT_SPINE_BIN': '30', 'OT_SPINE_ITERS': '20', 'OT_SPINE_TOL_PS': '8',
          'OT_SPINE_SAFE_BALANCE': '1', 'OT_SPINE_MACRO_LEAF': '1'},
}
for kv in KITS:
    t, v = kv.split(':')
    src = RT / f's81sl_lepmu{t}_r6e'; name = f's81sl_lepmu{t}_r6{v}'; dst = RT / name
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir()
    s = json.loads((src / 'spec.json').read_text())
    s['name'] = name
    s['job'].update(owner='Claude:S81-HARV-1021', tag=name, views_to=f'physical/ref_tile/{name}/views',
                    record_to=f'results/rtl/ref_tile/{name}')
    s['clock'] = 'spine'
    s['pre_cts_extra'] = []
    s['orfs_vars'].pop('OT_CKKM_K', None)
    s['orfs_vars'].update(VARS[v])
    s['structural_change'] = (f'S81-HARV-1021 r6{v} (r6e/r6k/r6g/r6u clock_rule FAIL, sink-driven trees at the 80 ps line): '
        'planned balanced clock SPINE in place of TritonCTS (clock_spine.tcl; leaves padded to equal measured arrival, SRAM '
        'clock pins own leaves); ' + ('symmetric insertion-aware topology, leaf 16 / bin 30. ' if v == 'v' else
        'plain bisection, leaf 24 / bin 30 (parallel fallback). ') +
        'Floorplan, RTL (6cb5f3eff NATIVE32=1 incl LOCAL_WA, RX_SRAM=1, IN_PIPE=1), ports, cycles, SDC, witnesses = r6e.')
    (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    readme = (src / 'README.md').read_text().split('\n## ')[0].replace(src.name, name)
    (dst / 'README.md').write_text(readme + f'\n## S81-HARV-1021 10-21 (r6{v})\n{s["structural_change"]}\n\n'
        'SAFE checklist: 1-6, 8 as r6e (pins registered, 2-stage reset landing; native census max 32 incl reset; depth '
        '368/392 ps; 20 SRAM; macros on 43.2 lattice, full rows, aspect 1.08, faces <= 4.6/um; 0 added cycles). '
        '7 clock: planned spine (fixed),io_hold_margin 0.03; pin-flop spread <= 80 TT+FF measured by the --cts gate.\n')
    r = subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen', str(dst / 'spec.json')], cwd=WT,
                       capture_output=True, text=True)
    print(name, r.returncode, r.stdout[-300:], r.stderr[-600:])

#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18: equivalence bench of the VM hub-glue TILE tops (rtl/hbm_accel/generic/vm/static/
hfd_hgi_vms_glue_tiles.sv) inside the hoisted slice.  It runs the existing composition generators UNCHANGED
(vms_hoist_equiv.py for SW / NW, vms_qb_equiv.py for SE / NE: glue + 8 die-level q0_faces banks [+ NW merges] wired
from the layer, against the full-slice reference) and only re-targets the composition's glue instance to the tile top, through its bench-only wiring adapter <tile>_flat
(hfd_hgi_vms_glue_tiles_flat.sv: the glue's 4 clocks / flat bk_* buses -> the tile's clk / per-bank ports):
  hfd_hgi_vms_static_SW_glue          -> hfd_hgi_vms_glue_sw_t
  hfd_hgi_vms_static_NW_glue          -> hfd_hgi_vms_glue_nw_t
  hfd_hgi_vms_static_{SE,NE}b_glue    -> hfd_hgi_vms_glue_e_t with .sid(2'd1 / 2'd3)  (ONE master, strap pin)
The adapter drives the tile's single clk from clk_hub (the bench toggles every slice clock on the same edge).
Mutants:  --mut bank   the generators' own mutant (bank 0/1 rslot swapped in the composition) -> must FAIL
          --mut sid    (SE / NE only) the tile strap gets the OTHER E quadrant's sid -> must FAIL
    vms_glue_tile_equiv.py --quadrant SW|NW|SE|NE --out DIR [--mut bank|sid]
"""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
LAYER = 'tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json'
TILE = dict(SW='hfd_hgi_vms_glue_sw_t', NW='hfd_hgi_vms_glue_nw_t', SE='hfd_hgi_vms_glue_e_t', NE='hfd_hgi_vms_glue_e_t')
SID = dict(SE=1, NE=3)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--quadrant', required=True, choices=list(TILE))
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--mut', choices=('bank', 'sid'))
    a = ap.parse_args(); q = a.quadrant
    if a.mut == 'sid' and q not in SID:
        raise SystemExit('vms_glue_tile_equiv: --mut sid is for the strapped E master (SE / NE)')
    gen = 'vms_hoist_equiv.py' if q in ('SW', 'NW') else 'vms_qb_equiv.py'
    cmd = [sys.executable, str(ROOT / 'tools/hbm_die_v16' / gen), '--layer', str(ROOT / LAYER), '--quadrant', q, '--out', str(a.out)]
    if a.mut == 'bank':
        cmd.append('--mut')
    subprocess.run(cmd, check=True)
    comp = a.out / f'vms_hoist_comp_{q}.sv'
    t = comp.read_text()
    glue = f'hfd_hgi_vms_static_{q}_glue' if q in ('SW', 'NW') else f'hfd_hgi_vms_static_{q}b_glue'
    lines = t.split('\n')
    idx = [i for i, l in enumerate(lines) if l.startswith(f'  {glue} u_glue (')]
    if len(idx) != 1:
        raise SystemExit(f'vms_glue_tile_equiv: expected one {glue} u_glue instance, found {len(idx)}')
    l = lines[idx[0]].replace(f'  {glue} u_glue (', f'  {TILE[q]}_flat u_glue (', 1)
    if q in SID:
        s = SID[q] if a.mut != 'sid' else SID['NE' if q == 'SE' else 'SE']
        l = l.replace(' u_glue (', f" u_glue (.sid(2'd{s}), ", 1)
    lines[idx[0]] = l
    comp.write_text('\n'.join(lines))
    print('VMS_GLUE_TILE_TB', q, TILE[q], 'MUT=' + (a.mut or 'none'))


if __name__ == '__main__':
    main()

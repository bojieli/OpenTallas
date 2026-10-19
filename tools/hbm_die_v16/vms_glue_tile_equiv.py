#!/usr/bin/env python3
"""OWNERS-HBM/VM-GLUE 2026-10-18, rev 2 (VM-GLUE2): equivalence bench of the VM hub-glue TILE tops
(rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_tiles.sv) inside the hoisted slice.  It runs the existing composition
generator vms_hoist_equiv.py UNCHANGED for all four quadrants (glue + 8 die-level q0_faces banks [+ NW merges], wired
from layer vm_hoist_d4f = the GEN2 binding: SW NC 2, NW / SE / NE NC 0) and re-targets the composition's glue:
  DUT  hfd_hgi_vms_static_<Q>_glue -> <tile>_flat      (the tile master: registered faces + ot_vms_rstop_static_vr core)
  REF  hfd_hgi_vms_static_<Q>_glue -> <tile>_ref_flat  (the SAME generated face pipes / reset relay around the ORIGINAL
                                                         ot_vms_slice_static_glue with full-reset ot_vms_rstop_static)
  tiles: SW -> hfd_hgi_vms_glue_sw_t, NW -> hfd_hgi_vms_glue_nw_t, SE / NE -> hfd_hgi_vms_glue_e_t with .sid(2'd1 / 2'd3)
The rev-2 tile adds PIPE cycles on every face (a latency change), so the reference is no longer the unpipelined full
slice wrapper: both sides carry the identical face latency and slice BANK_PIN_IN, and the bench proves the tile top's
port mapping, the strap, the NW flt merge and the valid-only-reset ring stops against the original ring stops, every
output on every edge after reset (3000 random edges).
Mutants (DUT only; the reference is always the clean composition):
          --mut bank   vms_hoist_equiv's own mutant (bank 0/1 rslot swapped in the DUT composition) -> must FAIL
          --mut sid    (SE / NE only) the DUT tile strap gets the OTHER E quadrant's sid -> must FAIL
    vms_glue_tile_equiv.py --quadrant SW|NW|SE|NE --out DIR [--mut bank|sid]
"""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
LAYER = 'tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json'
TILE = dict(SW='hfd_hgi_vms_glue_sw_t', NW='hfd_hgi_vms_glue_nw_t', SE='hfd_hgi_vms_glue_e_t', NE='hfd_hgi_vms_glue_e_t')
SID = dict(SE=1, NE=3)


def retarget(comp_text, q, mod, sid):
    glue = f'hfd_hgi_vms_static_{q}_glue'
    lines = comp_text.split('\n')
    idx = [i for i, l in enumerate(lines) if l.startswith(f'  {glue} u_glue (')]
    if len(idx) != 1:
        raise SystemExit(f'vms_glue_tile_equiv: expected one {glue} u_glue instance, found {len(idx)}')
    l = lines[idx[0]].replace(f'  {glue} u_glue (', f'  {mod} u_glue (', 1)
    if sid is not None:
        l = l.replace(' u_glue (', f" u_glue (.sid(2'd{sid}), ", 1)
    lines[idx[0]] = l
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--quadrant', required=True, choices=list(TILE))
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--mut', choices=('bank', 'sid'))
    a = ap.parse_args(); q = a.quadrant
    if a.mut == 'sid' and q not in SID:
        raise SystemExit('vms_glue_tile_equiv: --mut sid is for the strapped E master (SE / NE)')
    gen = [sys.executable, str(ROOT / 'tools/hbm_die_v16/vms_hoist_equiv.py'), '--layer', str(ROOT / LAYER), '--quadrant', q]
    ref_dir = a.out / 'ref'
    subprocess.run(gen + ['--out', str(ref_dir)], check=True)
    subprocess.run(gen + ['--out', str(a.out)] + (['--mut'] if a.mut == 'bank' else []), check=True)
    comp = a.out / f'vms_hoist_comp_{q}.sv'
    sid = SID.get(q)
    dut = retarget(comp.read_text(), q, f'{TILE[q]}_flat', None if sid is None else (sid if a.mut != 'sid' else SID['NE' if q == 'SE' else 'SE']))
    ref = retarget((ref_dir / f'vms_hoist_comp_{q}.sv').read_text(), q, f'{TILE[q]}_ref_flat', sid)
    ref = ref.replace(f'module vms_hoist_comp_{q} (', f'module vms_hoist_comp_{q}_ref (', 1)
    comp.write_text(dut + '\n' + ref + '\n')
    tb = a.out / 'tb_vms_hoist.sv'
    t = tb.read_text().split('\n')
    k = [i for i, l in enumerate(t) if ' u_ref (' in l]
    if len(k) != 1:
        raise SystemExit('vms_glue_tile_equiv: expected one u_ref line in the bench')
    t[k[0]] = f'  vms_hoist_comp_{q}_ref u_ref (' + t[k[0]].split(' u_ref (', 1)[1]
    tb.write_text('\n'.join(t))
    print('VMS_GLUE_TILE_TB', q, TILE[q], 'MUT=' + (a.mut or 'none'), 'REF=' + TILE[q] + '_ref_flat')


if __name__ == '__main__':
    main()

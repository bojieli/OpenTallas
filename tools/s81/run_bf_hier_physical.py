#!/usr/bin/env python3
"""bf-arch (2026-10-09): route one hardened block of the hierarchical S81 BF pair.

  --block col   : ot_v41_bf_col (one macro column; both columns of a pair are this master, the east one mirrored MY)
  --block front : ot_s81_bf_front (pin registers + front core; replicated column interface on the west / east faces)
Same flow and IO model as run_bf_native_physical.py --margin --wc-only (route period --period, sign-off 833.333 via
signoff_ref.sdc, IO from the measured insertion --ins-ss), but each block has its own slot (--die-w x 190.08) and pin
faces: the column's interface on its east face (toward the front), its partial outputs on the south face; the front's
column interface on the west (column 0) and east (column 1) faces, the x stream on the south / north faces.
"""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81'))
import run_abi3_physical as flow
import run_bf_native_physical as nat

QP = dict(NSEG=8, NCH=16, XF=8, LV=5, BF16=1, NCHB=8, NB=2, MTP=1, EARLY=1, CG=1, DRAIN=200, FAST=1, PP=1, BP=0,
          QTIMING_FIX=1, QPIPE=1, QP_XS=1, QP_CAP=0, QP_P1=1, QP_CSAM=10, QZ=1, QZ_NS=8, QZ_NE=4, QY=1, QX=10, QBF=2,
          QZE=1, TCG=1, GRADUAL_RNE=1)


def command(a):
    top = 'ot_v41_bf_col' if a.block == 'col' else 'ot_s81_bf_front'
    cmd = ['--view', 'asap7', '--top', top]
    for s in nat.SOURCES + ['rtl/s81/ot_s81_bf_front.sv']:
        cmd += ['--source', s]
    if a.block == 'col':
        for k, v in QP.items():
            cmd += ['--param', f'{k}={v}']
        cmd += ['--param', f'BXST={a.bxst}', '--param', f'FXST={a.fxst}']
        pins = ['--pin-region', r'^(pv|pval|prow|pseg|pnseg|perr|ppos|qy_bkf).*=bottom', '--pin-region',
                r'^(clk|rst_n_pin|ze_d|issue|a_ctr|i1_|i2x_|so_).*=right']
    else:
        cmd += ['--param', 'PINREG=1', '--param', 'HITFIX=1', '--param', 'RECUT=2', '--param', 'QZE=1', '--param', 'TCG=1',
                '--param', 'HCOL=1', '--param', f'BXST={a.bxst}', '--param', f'FXST={a.fxst}']
        pins = ['--pin-region', r'^c0_.*=left', '--pin-region', r'^(c1_|c_qy_bkf_in).*=right',
                '--pin-region', r'^xb_d.*=top', '--pin-region',
                r'^(clk|rst_n|cfg_|go|go_bf|xs_|xb_v|xb_b|xb_sv|xb_u|xb_pos|busy|fault|hph).*=bottom']
    ss = a.ins_ss
    io = lambda v: str(round(v / 1000.0, 4))
    W, H = a.die_w, 190.08
    cmd += ['--clock-period-ns', a.period, '--core-input-delay-min-ns', io(ss), '--core-input-delay-max-ns', io(ss + 250),
            '--output-delay-min-ns', io(-(ss + 50)), '--output-delay-max-ns', io(100 - (ss - 150)), '--false-path-from',
            'rst_n' if a.block == 'front' else 'rst_n_pin',
            '--die-area', '0', '0', str(W), str(H), '--core-area', '2.16', '2.16', str(round(W - 2.16, 3)), str(round(H - 2.16, 3)),
            '--hold-corners', 'WC', '--slew-margin-percent', '20', '--hold-margin-ns', a.hm, '--orfs-var', 'PLACE_DENSITY_LB_ADDON=',
            '--step-tcl', 'PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
            '--step-tcl', 'PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl'] + pins
    cmd += ['--clock-uncertainty-ns', '.060', '--clock-uncertainty-hold-ns', '.025', '--orfs-corner', 'WC',
            '--stages', 'pnr', '--synth-timeout-seconds', 'unlimited', '--flow-timeout-seconds', 'unlimited',
            '--core-utilization', '45', '--place-density', '.60', '--max-transition-ns', '.25',
            '--orfs-var', 'NUM_CORES=16', '--orfs-var', 'ADDER_MAP_FILE=', '--orfs-var', 'OT_BF_HIER=1', '--orfs-var', 'OT_BF_RECUT=1',
            '--orfs-var', 'SYNTH_SCRIPT=/src/physical/s81_native_bf/synth.tcl',
            '--orfs-var', 'PDN_TCL=/src/physical/abi3/w10_wake_pdn.tcl',
            '--keep-heavy-artifacts', '--nickname-tag', a.tag, '--keep-workdir', str(a.work), '--output', str(a.output)]
    if a.block == 'col':
        cmd += ['--macro-view', nat.MACRO + '=' + nat.VIEW, '--macro-place-halo', '5.4', '5.4',
                '--step-tcl', 'POST_MACRO_PLACE=physical/s81_bf_hier/place_col.tcl']
    if a.extra:
        cmd += a.extra.split()
    return cmd


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--block', choices=('col', 'front'), required=True)
    p.add_argument('--work', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tag', required=True); p.add_argument('--period', default='.730'); p.add_argument('--ins-ss', type=float, default=841.0)
    p.add_argument('--die-w', type=float, default=0.0); p.add_argument('--hm', default='0.000')
    p.add_argument('--bxst', type=int, default=2); p.add_argument('--fxst', type=int, default=2); p.add_argument('--extra', default='')
    a = p.parse_args()
    if not a.die_w:
        a.die_w = 520.128 if a.block == 'col' else 280.152
    cmd = command(a)
    original = flow.sdc_lines
    def sdc(view, block, clock_period_ns, constraints=None):
        lines = original(view, block, clock_period_ns, constraints)
        lines += ['# Physical PP ROM read/capture: alternate banks, capture two edges after read.',
                  'set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]',
                  'set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]']
        return lines
    flow.sdc_lines = sdc
    return flow.main(cmd, synth_timeout=None, flow_timeout=None)


if __name__ == '__main__':
    raise SystemExit(main())

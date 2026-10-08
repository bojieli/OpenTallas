#!/usr/bin/env python3
"""Physical screen (SS/FF/DRC at 833.333 ps, 60/25 ps uncertainty) of the HBM contract blocks
(stream hbm-contracts, 2026-10-07).  Run through the closure loop from a pinned clean commit.

Blocks:
  pkt_ii1   hfd_coll_pkt_fifo_ii1   II=1 refill collective packet SRAM queue (3 x 256x256 macros)
  pkt_ii3   hfd_coll_pkt_fifo_ii3   the II=3 queue at the same shape (reference only)
  su_rin    hfd_su_result_ingress   SM -> SU native result edge, one SU ingress lane (64x512 macro)
  credit    hfd_coll_credit_prod    native Gray credit producer + partner credit consumer
  idle      hfd_coll_idle_tx        plesiochronous idle-insertion TX pacer

IO is a screening envelope (20 % each way; no budget sheet exists for these masters yet); the record
says so.  Die-context IO binding stays a separate gate.
"""
import argparse, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PKG = 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
CF = 'rtl/hbm_accel/collective_full_20261007/'
CT = 'rtl/hbm_accel/contracts_20261007/'
M256 = 'ot_sram_1r1w_256x256_m2_r2c2'
M64 = 'ot_sram_1r1w_64x512_m1_r2c2'
BLOCKS = dict(
    pkt_ii1=dict(top='hfd_coll_pkt_fifo_ii1', src=[PKG, CF + 'ot_hbm_collective_packet_fifo.sv',
                 CF + 'ot_hbm_collective_packet_fifo_refill.sv', CT + 'hfd_coll_pkt_fifo_ii1.sv'],
                 macros=[M256], die=(240, 240), density=.55),
    pkt_ii3=dict(top='hfd_coll_pkt_fifo_ii3', src=[PKG, CF + 'ot_hbm_collective_packet_fifo.sv',
                 CF + 'ot_hbm_collective_packet_fifo_refill.sv', CT + 'hfd_coll_pkt_fifo_ii1.sv'],
                 macros=[M256], die=(240, 240), density=.55),
    su_rin=dict(top='hfd_su_result_ingress', src=[CT + 'ot_hbm_su_result_ingress.sv', CT + 'hfd_sm_su_edge.sv'],
                macros=[M64], die=(230, 150), density=.55),
    credit=dict(top='hfd_coll_credit_prod', src=[CT + 'ot_hbm_coll_credit_producer.sv', CT + 'hfd_coll_credit.sv'],
                macros=[], die=(40, 40), density=.55),
    idle=dict(top='hfd_coll_idle_tx', src=[CT + 'ot_hbm_coll_idle_insert.sv', CT + 'hfd_coll_credit.sv'],
              macros=[], die=(30, 30), density=.55),
)


def command(block, out):
    b = BLOCKS[block]
    w, h = b['die']
    cmd = ['python3', 'tools/run_abi3_physical.py', '--view', 'asap7', '--top', b['top']]
    for s in b['src']:
        cmd += ['--source', s]
    cmd += ['--clock-port', 'clk', '--clock-period-ns', '0.833333333', '--clock-uncertainty-ns', '0.060',
            '--clock-uncertainty-hold-ns', '0.025', '--orfs-corner', 'WC', '--hold-corners', 'WC,BC',
            '--io-delay-fraction', '.2', '--sdc-append', 'physical/hbm_contracts_20261007/screening.sdc',
            '--stages', 'pnr', '--die-area', '0', '0', str(w), str(h),
            '--core-area', '1.08', '1.08', f'{w - 1.08:.3f}', f'{h - 1.08:.3f}',
            '--place-density', str(b['density']), '--routing-layers', 'M2', 'M7',
            '--max-transition-ns', 'library', '--max-fanout', '32',
            '--orfs-var', 'ADDER_MAP_FILE=', '--orfs-var', 'CTS_ARGS=-apply_ndr none',
            '--step-tcl', 'PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
            '--step-tcl', 'PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
            '--slew-margin-percent', '20', '--hold-margin-ns', '.015', '--purpose', 'characterization',
            '--nickname-tag', 'hc_' + block,
            '--synth-timeout-seconds', 'unlimited', '--flow-timeout-seconds', 'unlimited',
            '--keep-workdir', str(out / 'work'), '--output', str(out / 'physical.json')]
    for m in b['macros']:
        cmd += ['--macro-view', f'{m}=physical/asap7_memory_macros/{m}']
    if b['macros']:
        cmd += ['--macro-place-halo', '2', '2']
    return cmd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--block', choices=sorted(BLOCKS), required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--prepare-only', action='store_true')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    out = a.out.resolve()
    args = command(a.block, out)
    corner = ['python3', 'tools/w18/corner_sta.py', '--orfs-dir', str(out / 'work/orfs'),
              '--output', str(out / 'corner_sta.json')]
    for m in BLOCKS[a.block]['macros']:
        corner += ['--macro', f'physical/asap7_memory_macros/{m}']
    (out / 'screening_contract.json').write_text(json.dumps(dict(
        status='hbm-contract-block-screen (IO envelope 20 %, no budget sheet)', block=a.block,
        top=BLOCKS[a.block]['top'], command=args, corner_command=corner,
        die_context_io_binding='OPEN', acceptance='SS>=15ps,FF>=15ps,DRC0'), indent=2) + '\n')
    if a.prepare_only:
        print(json.dumps(args))
        return 0
    with (out / 'route.log').open('w') as f:
        rc = subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    (out / 'route.exit').write_text(f'{rc}\n')
    if rc:
        return rc
    with (out / 'corner.log').open('w') as f:
        rc = subprocess.run(corner, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    (out / 'corner.exit').write_text(f'{rc}\n')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Physical screen (SS/FF/DRC at 833.333 ps, 60/25 ps uncertainty) of the HBM contract blocks
(stream hbm-contracts, 2026-10-07).  Run through the closure loop from a pinned clean commit.

Blocks:
  pkt_ii1   hfd_coll_pkt_fifo_ii1   II=1 refill collective packet SRAM queue (3 x 256x256 macros)
  su_rin    hfd_su_result_ingress   SM -> SU native result edge, one SU ingress lane (64x512 macro)
  credit    hfd_coll_credit_prod    native Gray credit producer + partner credit consumer
  idle      hfd_coll_idle_tx        plesiochronous idle-insertion TX pacer

IO is a screening envelope (20 % each way; no budget sheet exists for these masters yet); the record
says so.  Die-context IO binding stays a separate gate.
"""
import argparse, json, os, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PKG = 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
CF = 'rtl/hbm_accel/collective_full_20261007/'
CT = 'rtl/hbm_accel/contracts_20261007/'
M256 = 'ot_sram_1r1w_256x256_m2_r2c2'
M64 = 'ot_sram_1r1w_64x512_m1_r2c2'
BLOCKS = dict(
    pkt_ii1=dict(top='hfd_coll_pkt_fifo_ii1', src=[PKG, CF + 'ot_hbm_collective_packet_fifo_refill.sv',
                 CT + 'hfd_coll_pkt_fifo_ii1.sv'], macros=[M256], die=(330.048, 216), density=.55,
                 macro_tcl='physical/hbm_contracts_20261007/pkt_macros_a.tcl',
                 pins=['dout.*=left', 'din.*=right', '(clk|rst_n|push|pop|ready|valid|fault|count.*)=top'], sdc=['physical/hbm_contracts_20261007/reset_rst_n.sdc']),
    # aggressive variant: wider channels and 25 um macro gaps (area is not scarce)
    pkt_ii1b=dict(top='hfd_coll_pkt_fifo_ii1', src=[PKG, CF + 'ot_hbm_collective_packet_fifo_refill.sv',
                  CT + 'hfd_coll_pkt_fifo_ii1.sv'], macros=[M256], die=(397.44, 250.56), density=.45,
                  macro_tcl='physical/hbm_contracts_20261007/pkt_macros_b.tcl',
                  pins=['dout.*=left', 'din.*=right', '(clk|rst_n|push|pop|ready|valid|fault|count.*)=top'], sdc=['physical/hbm_contracts_20261007/reset_rst_n.sdc']),
    su_rin=dict(top='hfd_su_result_ingress', src=[CT + 'ot_hbm_su_result_ingress.sv', CT + 'hfd_sm_su_edge.sv'],
                macros=[M64], die=(230, 150), density=.55, sdc=['physical/hbm_contracts_20261007/reset_rst_n.sdc']),
    su_rin_b=dict(top='hfd_su_result_ingress', src=[CT + 'ot_hbm_su_result_ingress.sv', CT + 'hfd_sm_su_edge.sv'],
                  macros=[M64], die=(299.592, 120.96), density=.5,
                  macro_tcl='physical/hbm_contracts_20261007/su_rin_macros_b.tcl',
                  pins=['^r_in=left', '^out_=top', '^(op_|fault|free_o|clk|rst_n)=bottom'], sdc=['physical/hbm_contracts_20261007/reset_rst_n.sdc']),
    credit=dict(top='hfd_coll_credit_prod', src=[CT + 'ot_hbm_coll_credit_producer.sv', CT + 'hfd_coll_credit.sv'],
                macros=[], die=(40, 40), density=.55, sdc=['physical/hbm_contracts_20261007/credit_reset.sdc']),
    idle=dict(top='hfd_coll_idle_tx', src=[CT + 'ot_hbm_coll_idle_insert.sv', CT + 'hfd_coll_idle_tx.sv'],
              macros=[], die=(30, 30), density=.55, sdc=['physical/hbm_contracts_20261007/reset_rst_n.sdc']),
)


def command(block, out, stop_after=None, label_suffix=''):
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
            '--slew-margin-percent', '20', '--hold-margin-ns', os.environ.get('HM', '.015'), '--purpose', 'characterization',
            '--nickname-tag', 'hc_' + block + label_suffix,
            '--synth-timeout-seconds', 'unlimited', '--flow-timeout-seconds', 'unlimited',
            '--keep-workdir', str(out / 'work'), '--output', str(out / 'physical.json')]
    if b.get('macro_tcl'):
        cmd += ['--orfs-var', f"MACRO_PLACEMENT_TCL=/src/{b['macro_tcl']}"]
    for pr in b.get('pins', []):
        cmd += ['--pin-region', pr]
    for extra in b.get('sdc', []):
        cmd += ['--sdc-append', extra]
    # die-clock IO budget from the closure loop's calibrate stage (CTS-only run -> measured insertion -> sdc_cmd):
    # io_vclk_<CK_SS_MEAN>.sdc times the 0.2 T IO budgets against a virtual clock at the block's own insertion
    if os.environ.get('IO_ROUTE_SDC'):
        cmd += ['--sdc-append', os.environ['IO_ROUTE_SDC']]
    if stop_after:
        cmd += ['--pnr-stop-after', stop_after]
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
    ap.add_argument('--stop-after', choices=['cts'], help='calibration run (closure-loop calibrate stage)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    out = a.out.resolve()
    args = command(a.block, out, a.stop_after, '_cal' if a.stop_after else '')
    macros = [f'physical/asap7_memory_macros/{m}' for m in BLOCKS[a.block]['macros']]
    ff_sdc = os.environ.get('IO_FF_SDC')
    (out / 'screening_contract.json').write_text(json.dumps(dict(
        status='hbm-contract-block-screen (IO envelope 20 %, no budget sheet)', block=a.block,
        top=BLOCKS[a.block]['top'], command=args, io_route_sdc=os.environ.get('IO_ROUTE_SDC'), io_ff_sdc=ff_sdc,
        die_context_io_binding='OPEN', acceptance='SS>=15ps,FF>=15ps,DRC0'), indent=2) + '\n')
    if a.prepare_only:
        print(json.dumps(args))
        return 0
    with (out / 'route.log').open('w') as f:
        rc = subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    (out / 'route.exit').write_text(f'{rc}\n')
    if rc:
        return rc
    if a.stop_after:
        return 0
    # sign-off STA: SS setup on the route SDC; FF hold with the corner-true FF IO post-SDC (io_vclk_ff_<min>_<max>)
    import importlib.util
    spec = importlib.util.spec_from_file_location('ot_corner_sta', ROOT / 'tools/w18/corner_sta.py')
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)
    o = out / 'work/orfs'
    rc = 0
    with (out / 'corner.log').open('w') as f:
        try:
            res = dict(schema='opentallas.w18.corner_sta.v1', orfs_dir=str(o),
                       policy='SS setup (route SDC) / FF hold (route SDC + FF IO post-SDC), 60/25 ps',
                       setup_ss=cs.run(o, 'ss', macros, []),
                       hold_ff=cs.run(o, 'ff', macros, [ff_sdc] if ff_sdc else []),
                       post_sdc_ff=ff_sdc)
            res['closes_signoff'] = (res['setup_ss']['worst_slack_ps'] >= 15 and res['hold_ff']['worst_slack_ps'] >= 15)
            (out / 'corner_sta.json').write_text(json.dumps(res, indent=1) + '\n')
        except Exception as e:  # noqa: BLE001
            f.write(repr(e) + '\n')
            rc = 1
    (out / 'corner.exit').write_text(f'{rc}\n')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Exact gate of the P2 variant of the collective's dedicated MTP lanes (mtp-colllane-1011, 2026-10-10).

tb_mtp_p2_lanes (rtl/dsrom_sys/s81_ph/test/tb_mtp_p2_lanes.sv): draft die A's dsfd_sp_collective (OT_S81PH_COLL_P2L,
split3cr tiles) with lane W4 to the DSpark primary (board) and lane E4 from die B (UCIe), far ends = lane tile +
dsfd_coll_p2_lane, the P2 die bus over draft-A's stations into dsfd_p2_rtt (dsfd_p2_lnk + the rb4 core), the numeric
transaction of tb_mtp_p2_fixlat (gold.hex from tools/mtp_p2_prefix_fixture.py), NTX 3 back-to-back transactions.

  case       expect  shows
  p2l_s1     pass    exact rows (numeric + metadata), every lane-1 word / start / row 2-beat segmented over lanes with bit
                     errors, done events at the primary, abort event within ABMAX while start 3 waits in die A
  p2l_s5     pass    same, another stall / gap seed
  neg_seg    FAIL    OT_P2L_MUT_SEG: second beat not shifted (segmentation)
  neg_cred   FAIL    OT_P2L_MUT_CRED: one credit over the row / start class buffer + output register (overflow fault)
  neg_hol    FAIL    OT_P2L_MUT_DIRECT: no end-to-end class credits: the abort event waits behind the pending start (HOL)
  neg_lat1   FAIL    OT_FIXLAT_MUT_LAT1: coll_p2_ep / p2_lnk receivers sized for latency 1 on the stations

    python3 tools/mtp_p2lane_gate.py --out DIR [--cases a,b] [-j N]     (repo root, fleet host)
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = 'rtl/dsrom_sys/s81_ph'
D = 'rtl/experimental/mtp_p2_ordered_20261009'
M = 'rtl/dsrom_sys/mtp'
SRC = [f'{P}/test/tb_mtp_p2_lanes.sv', f'{P}/dsfd_sp_collective.sv', f'{P}/coll/dsfd_coll_ck.sv', f'{P}/coll/dsfd_coll_core.sv',
       f'{P}/coll/dsfd_coll_split.sv', f'{P}/coll/ot_s81ph_coll_lane.sv', f'{P}/coll/ot_s81ph_skid2.sv', f'{P}/coll/ot_s81ph_ckbuf.sv',
       f'{P}/ot_s81ph_coll_core.sv', f'{P}/ot_s81ph_coll_rstc.sv', f'{P}/ot_s81_pll_bb.sv', f'{P}/ot_s81ph_link_ep.sv',
       f'{P}/ot_s81ph_link_gbx.sv', f'{P}/ot_s81ph_mem1r1w.sv', f'{P}/ot_s81ph_rfifo.sv', f'{P}/coll/dsfd_coll_p2_lane.sv',
       'rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv', 'rtl/link/ot_fifo_sram_fwft.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
       'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/link/ot_link_crc32.sv', 'rtl/common/ot_link_credit.sv', 'rtl/dsrom_sys/ot_dsrom_link_chan.sv',
       'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
       'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
       f'{M}/ot_dsrom_mtp_link_pair.sv', f'{M}/ot_dsrom_mtp_link_rtt.sv', f'{M}/rtt/ot_dsrom_mtp_rstsync.sv'] + \
      [f'{D}/{x}.sv' for x in ('ot_mtp_p2_ordered_rows', 'ot_mtp_p2_prefix', 'ot_mtp_p2_prefix_native', 'ot_mtp_p2_prefix_path',
                               'dsfd_p2_lnk', 'dsfd_p2_rtt', 'tb_mtp_p2_fixlat')] + \
      ['rtl/v41rom/ot_v41_fadd.sv', 'rtl/common/ot_prefix.sv', 'rtl/common/ot_secded.sv', 'rtl/common/ot_sc_pfifo.sv',
       'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv']
DEF = ['OT_S81PH_GBX_FMT1', 'OT_S81PH_EP_PIPE2', 'OT_S81PH_COLL_OQPIPE', 'OT_S81PH_COLL_QPIPE', 'OT_S81PH_COLL_SPLIT',
       'OT_S81PH_COLL_CR', 'OT_S81PH_LANE_CR', 'OT_S81PH_COLL_PULL', 'OT_S81PH_COLL_TREP', 'OT_S81PH_COLL_P2L', 'OT_S81PH_PLL_MODEL']
CASES = dict(p2l_s1=('pass', [], dict(SEED=1)), p2l_s5=('pass', [], dict(SEED=5)),
             neg_seg=('fail', ['OT_P2L_MUT_SEG'], dict(SEED=1)), neg_cred=('fail', ['OT_P2L_MUT_CRED'], dict(SEED=1)),
             neg_hol=('fail', ['OT_P2L_MUT_DIRECT'], dict(SEED=1)), neg_lat1=('fail', ['OT_FIXLAT_MUT_LAT1'], dict(SEED=1)))


def run(out, name):
    exp, defs, prm = CASES[name]
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(['python3', str(ROOT / 'tools/mtp_p2_prefix_fixture.py')], cwd=d, check=True, capture_output=True)
    cmd = ['verilator', '--binary', '-j', '8', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-Wno-UNUSED', '-Wno-PINCONNECTEMPTY',
           '-Wno-MULTIDRIVEN', '-Wno-UNOPTFLAT', '-Wno-PINMISSING', '-Irtl/common', '--top-module', 'tb_mtp_p2_lanes',
           '--Mdir', str(d / 'obj')] + [f'+define+{x}' for x in DEF + defs] + \
          [f'-G{k}={v}' for k, v in dict(dict(NTX=3), **prm).items()] + SRC
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return name, dict(expect=exp, got='build_error', ok=False, tail=(b.stdout + b.stderr).splitlines()[-8:])
    p = subprocess.run([str(d / 'obj/Vtb_mtp_p2_lanes')], cwd=d, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (d / 'run.log').write_text(log)
    got = 'pass' if 'P2L PASS' in log and p.returncode == 0 else 'fail'
    tail = [l for l in log.splitlines() if 'P2L' in l][-3:]
    return name, dict(expect=exp, got=got, ok=got == exp, defines=defs, params=prm, tail=tail)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cases', default=','.join(CASES))
    ap.add_argument('-j', type=int, default=6)
    ap.add_argument('--raw', action='store_true', help='exit 0 iff every case PASSED its bench (closure-loop bench stages: '
                    'a negative control is expect=fail there)')
    a = ap.parse_args()
    a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.j) as ex:
        res = dict(ex.map(lambda n: run(a.out, n), a.cases.split(',')))
    for n, r in res.items():
        print(f"{n:9s} expect {r['expect']} -> {r['got']} {'OK' if r['ok'] else 'BAD'} :: {' | '.join(r['tail'])}")
    ok = all(r['ok'] for r in res.values())
    (a.out / 'gate.json').write_text(json.dumps(dict(tool='tools/mtp_p2lane_gate.py', defines=DEF, cases=res,
                                                     verdict='PASS' if ok else 'FAIL'), indent=1) + '\n')
    print('MTP_P2LANE_GATE', 'PASS' if ok else 'FAIL')
    if a.raw:
        raw = all(r['got'] == 'pass' for r in res.values())
        print('P2LANE_RAW', 'PASS' if raw else 'FAIL'); sys.exit(0 if raw else 1)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

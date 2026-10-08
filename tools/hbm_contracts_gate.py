#!/usr/bin/env python3
"""Exactness gate of the four HBM contracts (stream hbm-contracts, 2026-10-07).

Each suite is a list of bench cases.  A positive case must print its PASS marker and exit 0; a negative
case (a baseline that lacks the contract, or a source mutant that breaks it) must FAIL with the named
assertion.  Mutants are applied to a private copy of the source; the committed RTL is never edited.

    python3 tools/hbm_contracts_gate.py --suite pkt    --out DIR [--sim verilator|iverilog]
    python3 tools/hbm_contracts_gate.py --suite credit --out DIR
    python3 tools/hbm_contracts_gate.py --suite smsu   --out DIR
    python3 tools/hbm_contracts_gate.py --suite idle   --out DIR
    python3 tools/hbm_contracts_gate.py --suite all    --out DIR

record.json: per case returncode, marker found, verdict; status PASS only if every case behaves as expected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
M256 = 'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v'
M64 = 'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v'
CF = 'rtl/hbm_accel/collective_full_20261007/'
CT = 'rtl/hbm_accel/contracts_20261007/'

PKT_SRC = [PKG, M256, CF + 'ot_hbm_collective_packet_fifo.sv', CF + 'ot_hbm_collective_packet_fifo_refill.sv']
PKT_REFILL = CF + 'ot_hbm_collective_packet_fifo_refill.sv'
CREDIT_SRC = [PKG, 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
              'rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv',
              'rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc_refill.sv',
              CT + 'ot_hbm_coll_credit_producer.sv']
SMSU_SRC = ['rtl/hbm_accel/result_relay_stage_20261007/ot_hbm_result_relay_slice.sv', M64,
            CT + 'ot_hbm_su_result_ingress.sv', CT + 'ot_hbm_sm_su_result_edge.sv']
IDLE_SRC = [PKG, 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
            'rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv',
            'rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc_refill.sv',
            CT + 'ot_hbm_coll_idle_insert.sv']


def case(name, top, src, tb, marker, expect='pass', params=None, defines=None, mutate=None, fail_regex=None):
    return dict(name=name, top=top, src=src + [tb], marker=marker, expect=expect, params=params or {},
                defines=defines or [], mutate=mutate, fail_regex=fail_regex)


SUITES = dict(
    pkt=[
        case('pkt_ii1_depth64', 'tb_packet_fifo_refill', PKT_SRC, CF + 'tb_packet_fifo_refill.sv', r'PASS_II1 ', params=dict(DEPTH=64)),
        case('pkt_ii1_depth256', 'tb_packet_fifo_refill', PKT_SRC, CF + 'tb_packet_fifo_refill.sv', r'PASS_II1 '),
        case('pkt_ii1_boundary', 'tb_packet_fifo_refill_boundary', PKT_SRC, CF + 'tb_packet_fifo_refill_boundary.sv', r'PASS_BOUNDARY '),
        case('pkt_ii3_legacy_bench', 'tb_packet_fifo', PKT_SRC, CF + 'tb_packet_fifo.sv', r'^PASS depth', params=dict(DEPTH=64)),
        case('NEG_pkt_ii3_rate', 'tb_packet_fifo_refill', PKT_SRC, CF + 'tb_packet_fifo_refill.sv', r'PASS_II1 ',
             expect='fail', params=dict(DEPTH=64), defines=['II3_BASELINE'], fail_regex=r'II1 drain took'),
        case('NEG_pkt_xfer_overwrites_head', 'tb_packet_fifo_refill', PKT_SRC, CF + 'tb_packet_fifo_refill.sv', r'PASS_II1 ',
             expect='fail', params=dict(DEPTH=64), fail_regex=r'DATA order mismatch|COUNT mismatch',
             mutate=(PKT_REFILL, 'wire xfer=c_pending&&(!c_held||take)&&!fault;', 'wire xfer=c_pending&&!fault;')),
        case('NEG_pkt_fetch_overwrites_latch', 'tb_packet_fifo_refill', PKT_SRC, CF + 'tb_packet_fifo_refill.sv', r'PASS_II1 ',
             expect='fail', params=dict(DEPTH=64), fail_regex=r'DATA order mismatch|COUNT mismatch',
             mutate=(PKT_REFILL, 'wire fetch=c_unread!=0&&(!c_pending||xfer)&&!fault;', 'wire fetch=c_unread!=0&&!fault;')),
    ],
    credit=[
        case('credit_positive', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT '),
        case('credit_positive_ratio', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             params=dict(TPH_PS=731, TCORE_PS=833)),
        case('NEG_credit_preload_partner', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', defines=['NEG_PRELOAD'], fail_regex=r'CREDIT_(OVERFLOW|LOSS)'),
        case('NEG_credit_binary_counter', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', fail_regex=r'CREDIT_K_BACKWARDS|CREDIT_OVERGRANT|CREDIT_OVERFLOW|CREDIT_ORDER',
             mutate=[(CT + 'ot_hbm_coll_credit_producer.sv', 'assign k_gray_d=k_bin_n^(k_bin_n>>1);', 'assign k_gray_d=k_bin_n;'),
                     (CT + 'ot_hbm_coll_credit_producer.sv', 'always @*begin kb[CW-1]=kg[CW-1];for(j=CW-2;j>=0;j=j-1)kb[j]=kb[j+1]^kg[j];end',
                      'always @*kb=kg;')]),
        case('NEG_credit_early_ready', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', fail_regex=r'CREDIT_READY_EARLY|CREDIT_OVERFLOW|CREDIT_LOSS',
             mutate=(CT + 'ot_hbm_coll_credit_producer.sv', 'wire both_released=phy_rel_q[0]&&core_live;',
                     'wire both_released=core_live;')),
        case('NEG_credit_width8', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', params=dict(CW=8), fail_regex=r'CREDIT_WIDTH|width'),
        case('NEG_credit_tx_gate_occupancy_only', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', fail_regex=r'TX_FLIGHT_OVERFLOW',
             mutate=(CT + 'ot_hbm_coll_credit_producer.sv', 'wire [DW-1:0] inflight=issued-popped_s;', 'wire [DW-1:0] inflight=cdc_occ;')),
        case('NEG_credit_C_below_loop', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', params=dict(C=192), fail_regex=r'CREDIT_RATE'),
        case('NEG_credit_dtx_below_bound', 'tb_coll_credit_producer', CREDIT_SRC, CT + 'tb_coll_credit_producer.sv', r'PASS_CREDIT ',
             expect='fail', params=dict(DTX_MIN=24), fail_regex=r'D_tx|DTX'),
    ],
    smsu=[
        case('smsu_edge_positive', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU '),
        case('smsu_edge_positive_long', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU ',
             params=dict(NST=49, OPS=400)),
        case('NEG_smsu_no_reservation', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU ',
             expect='fail', defines=['NEG_NO_RESERVATION'], fail_regex=r'SMSU_FAULT'),
        case('NEG_smsu_extra_row', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU ',
             expect='fail', defines=['NEG_EXTRA_ROW'], fail_regex=r'SMSU_FAULT'),
        case('NEG_smsu_sm_fault', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU ',
             expect='fail', defines=['NEG_SM_FAULT'], fail_regex=r'SMSU_FAULT'),
        case('NEG_smsu_release_before_count', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU ',
             expect='fail', fail_regex=r'SMSU_EARLY_RELEASE|SMSU_DATA',
             mutate=(CT + 'ot_hbm_su_result_ingress.sv', "releasable<=releasable+(last?hq_rows:7'd0)-{6'b0,take};", "releasable<=releasable+{6'b0,put}-{6'b0,take};")),
        case('NEG_smsu_credit_not_returned_on_pop', 'tb_sm_su_result_edge', SMSU_SRC, CT + 'tb_sm_su_result_edge.sv', r'PASS_SMSU ',
             expect='fail', fail_regex=r'SMSU_TIMEOUT|SMSU_CREDIT',
             mutate=(CT + 'ot_hbm_su_result_ingress.sv', 'if(take)free_n=free_n+1\'b1;', '')),
    ],
    idle=[
        case('idle_200ppm_M1024', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE '),
        case('idle_minus200ppm_M1024', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             params=dict(PPM=-200)),
        case('idle_200ppm_M4999_bound', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             params=dict(M=4999, NFLITS=3000000)),
        case('idle_1pct_M50', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             params=dict(PPM=10000, M=50, NFLITS=300000)),
        case('NEG_idle_none_200ppm', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             expect='fail', params=dict(M=0, CHECK_M=0), fail_regex=r'IDLE_RX_OVERFLOW'),
        case('NEG_idle_M200_at_1pct', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             expect='fail', params=dict(PPM=10000, M=200, CHECK_M=0, NFLITS=300000), fail_regex=r'IDLE_RX_OVERFLOW'),
        case('NEG_idle_M_bound_refused', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             expect='fail', params=dict(M=6000), fail_regex=r'IDLE_M_BOUND'),
        case('NEG_idle_rule_removed', 'tb_coll_idle_insert', IDLE_SRC, CT + 'tb_coll_idle_insert.sv', r'PASS_IDLE ',
             expect='fail', fail_regex=r'IDLE_SPACING|IDLE_RX_OVERFLOW',
             mutate=(CT + 'ot_hbm_coll_idle_insert.sv', 'wire due=run_q>=M_EFF;', "wire due=1'b0;")),
    ],
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_case(c, out: Path, sim: str, jobs: int):
    d = out / c['name']
    d.mkdir(parents=True)
    srcs = []
    muts = c['mutate'] if isinstance(c['mutate'], list) else ([c['mutate']] if c['mutate'] else [])
    for s in c['src']:
        p = ROOT / s
        mine = [m for m in muts if m[0] == s]
        if mine:
            text = p.read_text()
            for _, old, new in mine:
                if text.count(old) != 1:
                    return dict(name=c['name'], expect=c['expect'], verdict='ERROR', why=f'mutation anchor not unique in {s}')
                text = text.replace(old, new)
            p = d / ('mutant_' + Path(s).name)
            p.write_text(text)
        srcs.append(str(p))
    if sim == 'verilator':
        build = ['verilator', '--binary', '--timing', '-j', str(jobs), '-Wno-fatal', '-Wno-lint', '-Wno-style',
                 '--top-module', c['top'], '--Mdir', str(d / 'obj'), '-o', 'sim']
        build += [f'-G{k}={v}' for k, v in c['params'].items()] + [f'-D{x}' for x in c['defines']] + srcs
        runc = [str(d / 'obj' / 'sim')]
    else:
        build = ['iverilog', '-g2012', '-s', c['top'], '-o', str(d / 'sim.vvp')]
        build += [f'-P{c["top"]}.{k}={v}' for k, v in c['params'].items()] + [f'-D{x}' for x in c['defines']] + srcs
        runc = ['vvp', '-n', str(d / 'sim.vvp')]
    with (d / 'build.log').open('w') as f:
        b = subprocess.run(build, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    if b.returncode:
        return dict(name=c['name'], expect=c['expect'], verdict='ERROR', why='build failed', build=build,
                    log_tail=(d / 'build.log').read_text()[-2000:])
    with (d / 'run.log').open('w') as f:
        try:
            r = subprocess.run(runc, cwd=d, stdout=f, stderr=subprocess.STDOUT, timeout=7200)
            rc = r.returncode
        except subprocess.TimeoutExpired:
            rc = 'timeout'
    log = (d / 'run.log').read_text(errors='replace')
    marker = re.search(c['marker'], log, re.M) is not None
    if c['expect'] == 'pass':
        ok = rc == 0 and marker
    else:
        ok = (rc not in (0, 'timeout')) and not marker and (c['fail_regex'] is None or re.search(c['fail_regex'], log) is not None)
    shutil.rmtree(d / 'obj', ignore_errors=True)
    tail = log[-1500:]
    return dict(name=c['name'], expect=c['expect'], returncode=rc, marker=marker, verdict='OK' if ok else 'WRONG',
                params=c['params'], defines=c['defines'], mutation=c['mutate'], build=build, log_tail=tail)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--suite', choices=sorted(SUITES) + ['all'], required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sim', choices=['verilator', 'iverilog'], default='verilator')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--par', type=int, default=4)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    out = a.out.resolve()
    cases = [c for k in (sorted(SUITES) if a.suite == 'all' else [a.suite]) for c in SUITES[k]]
    files = sorted({s for c in cases for s in c['src']})
    pins = {f: sha(ROOT / f) for f in files}
    with ThreadPoolExecutor(a.par) as ex:
        res = list(ex.map(lambda c: run_case(c, out, a.sim, a.jobs), cases))
    assert pins == {f: sha(ROOT / f) for f in files}, 'sources changed during the gate'
    status = 'PASS' if all(r['verdict'] == 'OK' for r in res) else 'FAIL'
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(schema='opentallas.hbm_contracts_gate.v1', suite=a.suite, simulator=a.sim, status=status,
               commit=git, source_sha256=pins, cases=res,
               positives=sum(r['expect'] == 'pass' for r in res), negatives=sum(r['expect'] == 'fail' for r in res))
    (out / 'record.json').write_text(json.dumps(rec, indent=1) + '\n')
    for r in res:
        print(f"{r['verdict']:5s} {r['expect']:4s} {r['name']:40s} rc={r.get('returncode')} marker={r.get('marker')} {r.get('why', '')}")
    print('GATE', a.suite, status)
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

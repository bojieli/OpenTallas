#!/usr/bin/env python3
"""Stationed gates of the MTP links that still assumed a fixed latency (mtp-fixlat-1011, 2026-10-10).

(A) the head-die sequencer's partner ends dsfd_cap_mtp_ep / dsfd_vm_mtp_ep (rtl/dsrom_sys/mtp/dsfd_mtp_partner_ep.sv)
    against the sequencer's link cells at dsfd_mtp_seq_rtt's parameters, relay stations at head631's pin-to-pin counts
    (tools/s81/hub_stage_count.py: capture -> mtp 6 / back 7, vm <-> mtp 11 / 11): tb_mtp_partner_ep.
(B) the P2 draft-die links (rtl/experimental/mtp_p2_ordered_20261009/dsfd_p2_lnk.sv: dsfd_p2_lnk + the unchanged rb4
    core, dsfd_coll_p2_ep, dsfd_vm_p2_ep), relay stations at draft-A's counts (vm <-> p2 FV / RV, collective <-> p2
    FC / RC): tb_mtp_p2_fixlat, the numeric transaction of tb_mtp_p2_prefix_path checked against the fixture gold.

    python3 tools/mtp_fixlat_gate.py one CASE --out DIR      (prints FIXLAT CASE PASS|FAIL; rc 0 iff as expected)
    python3 tools/mtp_fixlat_gate.py all --out DIR
Negatives (expect FAIL): *_lat1 (OT_FIXLAT_MUT_LAT1: every new receiver sized for a latency-1 link = the legacy
3-cycle grant history), pep_stale (VM end sized for the chain-only 10 / 9 count), p2_naive (the core's plain
valid / ready pins straight onto the stations, i.e. the as-is P2, also on a single transaction), p2_nogate
(OT_FIXLAT_MUT_NOGATE: no transaction gate in dsfd_p2_lnk -> the next transaction's lane words fault the core).
"""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
M = 'rtl/dsrom_sys/mtp'
D = 'rtl/experimental/mtp_p2_ordered_20261009'
LINK = [f'{M}/ot_dsrom_mtp_link_pair.sv', f'{M}/ot_dsrom_mtp_link_rtt.sv', f'{M}/rtt/ot_dsrom_mtp_rstsync.sv']
PEP = LINK + [f'{M}/dsfd_mtp_partner_ep.sv', f'{M}/tb/tb_mtp_partner_ep.sv']
P2 = LINK + [f'{D}/{x}.sv' for x in ('ot_mtp_p2_ordered_rows', 'ot_mtp_p2_prefix', 'ot_mtp_p2_prefix_native',
                                      'ot_mtp_p2_prefix_path', 'dsfd_p2_lnk', 'dsfd_p2_rtt', 'tb_mtp_p2_fixlat')] + \
     ['rtl/v41rom/ot_v41_fadd.sv', 'rtl/common/ot_prefix.sv', 'rtl/common/ot_secded.sv', 'rtl/common/ot_sc_pfifo.sv',
      'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv']
HEAD = dict(FC=6, RC=7, FV=11, RV=11)        # head631 (lat-audit head631_stages.json; re-counted on main e707ff5b3)
DRAFTA = dict(FV=12, RV=14, FC=8, RC=9)     # draft A (s81_dies_recipe draftA on e707ff5b3, hub_stage_count): vm->p2 12, p2->vm 14, coll->p2 8, p2->coll 9
CASES = {
    'pep_s1': ('tb_mtp_partner_ep', PEP, dict(HEAD, SEED=1), [], 'pass'),
    'pep_s7': ('tb_mtp_partner_ep', PEP, dict(HEAD, SEED=7), [], 'pass'),
    'pep_lat1': ('tb_mtp_partner_ep', PEP, dict(HEAD, SEED=1), ['OT_FIXLAT_MUT_LAT1'], 'fail'),
    'pep_stale': ('tb_mtp_partner_ep', PEP, dict(HEAD, SEED=1, EP_FH=10, EP_RH=9), [], 'fail'),
    'p2_s1': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, SEED=1), [], 'pass'),
    'p2_s5': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, SEED=5), [], 'pass'),
    'p2_lat1': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, SEED=1), ['OT_FIXLAT_MUT_LAT1'], 'fail'),
    'p2_naive': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, SEED=1), ['OT_P2_NAIVE'], 'fail'),
    'p2_naive_1tx': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, SEED=1, NTX=1, START_DELAY=0), ['OT_P2_NAIVE'], 'fail'),
    # latency of the link ends (no stations, saturated): lnk vs the core driven directly (OT_P2_NAIVE at 0 stations)
    'p2_lat_direct0': ('tb_mtp_p2_fixlat', P2, dict(FV=0, RV=0, FC=0, RC=0, NTX=1, START_DELAY=0, NOSTALL=1), ['OT_P2_NAIVE'], 'pass'),
    'p2_lat_lnk0': ('tb_mtp_p2_fixlat', P2, dict(FV=0, RV=0, FC=0, RC=0, NTX=1, START_DELAY=0, NOSTALL=1), [], 'pass'),
    'p2_lat_lnk': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, NTX=1, START_DELAY=0, NOSTALL=1), [], 'pass'),
    'p2_nogate': ('tb_mtp_p2_fixlat', P2, dict(DRAFTA, SEED=1), ['OT_FIXLAT_MUT_NOGATE'], 'fail'),
}
TAG = {'tb_mtp_partner_ep': 'PEP PASS', 'tb_mtp_p2_fixlat': 'P2FL PASS'}


def one(name, out):
    top, src, params, defs, expect = CASES[name]
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    if top == 'tb_mtp_p2_fixlat':
        subprocess.run(['python3', str(ROOT / 'tools/mtp_p2_prefix_fixture.py')], cwd=d, check=True, capture_output=True)
    cmd = ['iverilog', '-g2012', '-Irtl/common', '-s', top, '-o', str(d / 'sim.vvp')] + [f'-D{x}' for x in defs] + \
          [f'-P{top}.{k}={v}' for k, v in params.items()] + src
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        print(f'FIXLAT {name} BUILD_ERROR'); return 2
    p = subprocess.run(['vvp', '-n', str(d / 'sim.vvp')], cwd=d, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (d / 'run.log').write_text(log)
    got = 'pass' if (p.returncode == 0 and TAG[top] in log and 'FATAL' not in log) else 'fail'
    last = [l for l in log.splitlines() if l.strip()][-3:]
    print(f'FIXLAT {name} {got.upper()} (expect {expect}) :: ' + ' | '.join(last))
    return 0 if got == expect else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['one', 'all']); ap.add_argument('case', nargs='?')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.mode == 'one':
        sys.exit(one(a.case, a.out.resolve()))
    rc = {n: one(n, a.out.resolve()) for n in CASES}
    bad = [n for n, v in rc.items() if v]
    print('FIXLAT GATE', 'PASS' if not bad else f'FAIL {bad}'); sys.exit(1 if bad else 0)

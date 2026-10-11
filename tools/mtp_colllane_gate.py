#!/usr/bin/env python3
"""Exact gate of the collective's DEDICATED MTP lane (mtp-colllane-1011, 2026-10-10).

tb_s81ph_coll_sys (4-die TP4 collective group, split3cr tiles, against the C8 reference engines) with
+define+OT_S81PH_COLL_MTPL +define+TB_MTP: every die's dsfd_sp_collective carries lane W4 (closed lane tile +
dsfd_coll_mtp_lane), dies d <-> d^1 over a board channel with bit errors (link-layer replay), the head-die sequencer's
transmitters at the real 8 / 8 hub stations, consumers over 5 / 5 stations (rtl/dsrom_sys/s81_ph/test/tb_mtp_lane_io.sv).

  case        expect  what it shows
  base        pass    collective exact with MTPL built and no MTP traffic (reference for coll_done)
  pos_rand    pass    token / seed / accept exact in order under random consumer stalls, collective exact
  pos_hol     pass    seed consumer stalled FOREVER: every token still arrives (no HOL between the MTP classes)
  pos_block   pass    both MTP consumers stalled forever: collective exact AND coll_done == base (no blocking of
                      collective traffic: the lane shares no queue with lanes 0..7)
  pos_win     pass    long stall windows: class credits, receiver grants and class buffers run full, exact
  pos_rate    pass    no stalls, the sequencer's fastest emission (1 token / 6 cycles): rate + first-token latency
  neg_shared  FAIL    OT_MTPL_MUT_SHARED (classes share the landing FIFO = HOL design) under pos_hol's stalls
  neg_cred    FAIL    OT_MTPL_MUT_CRED (TCRED + 3 token credits, one over the SRAM FIFO's TCRED + 2) under pos_win's stalls: class buffer overflow
  neg_stale   FAIL    OT_MTPL_MUT_STALE (receivers sized for the chain-record 6 / 7 on the real 8 / 8): overflow

    python3 tools/mtp_colllane_gate.py --out DIR [--cases a,b] [-j N]     (run from the repo root on a fleet host)
"""
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF = ('+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 +define+OT_S81PH_COLL_OQPIPE +define+OT_S81PH_COLL_QPIPE '
       '+define+OT_S81PH_COLL_SPLIT +define+OT_S81PH_COLL_CR +define+OT_S81PH_LANE_CR +define+OT_S81PH_COLL_PULL '
       '+define+OT_S81PH_COLL_TREP +define+OT_S81PH_COLL_MTPL +define+TB_MTP').split()
CASES = dict(
    base=('pass', ['-GNTOK=0', '-GNSEED=0', '-GNACC=0']),
    pos_rand=('pass', ['-GMSTALL=0']),
    pos_hol=('pass', ['-GMSTALL=1']),
    pos_block=('pass', ['-GMSTALL=2', '-GMTP_HOLD=9000']),
    pos_win=('pass', ['-GMSTALL=4']),
    pos_rate=('pass', ['-GMSTALL=3', '-GTGAP=6', '-GNTOK=1000']),
    rate_t64=('pass', ['-GMSTALL=3', '-GTGAP=6', '-GNTOK=1000', '+define+OT_MTPL_TCRED=64']),
    rate_t32=('pass', ['-GMSTALL=3', '-GTGAP=6', '-GNTOK=1000', '+define+OT_MTPL_TCRED=32']),
    neg_shared=('fail', ['-GMSTALL=1', '-GMTP_HOLD=20000', '+define+OT_MTPL_MUT_SHARED']),
    neg_cred=('fail', ['-GMSTALL=4', '+define+OT_MTPL_MUT_CRED']),
    neg_stale=('fail', ['-GMSTALL=4', '+define+OT_MTPL_MUT_STALE']),
)


def run(out, name):
    exp, extra = CASES[name]
    p = subprocess.run(['bash', 'rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh', str(out), name] + DEF + extra, cwd=ROOT,
                       capture_output=True, text=True)
    log = (out / f'{name}.log').read_text(errors='replace') if (out / f'{name}.log').exists() else p.stdout + p.stderr
    passed = 'TB_S81PH_COLL_SYS PASS' in log
    built = 'BUILD_FAIL' not in log
    cyc = re.search(r'CYCLES dut_last (\d+) ref_last (\d+) first_send (\d+) .* coll_done (-?\d+)', log)
    mtp = [l for l in log.splitlines() if l.startswith('MTP DIE')]
    rate = re.search(r'second_half_tokens (\d+) in (\d+) cycles', log)
    ok = built and (passed if exp == 'pass' else not passed)
    return name, dict(expect=exp, passed=passed, built=built, ok=ok, extra=extra,
                      coll_done=int(cyc.group(4)) if cyc else None, dut_last=int(cyc.group(1)) if cyc else None,
                      ref_last=int(cyc.group(2)) if cyc else None, mtp=mtp[:12],
                      cycles_per_token=round(int(rate.group(2)) / int(rate.group(1)), 3) if rate and int(rate.group(1)) else None,
                      tail=[l for l in log.splitlines() if 'FAIL' in l or 'fatal' in l.lower() or 'LINK_REG' in l][:6])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cases', default=','.join(CASES))
    ap.add_argument('-j', type=int, default=9)
    a = ap.parse_args()
    a.out = a.out.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    names = a.cases.split(',')
    with ThreadPoolExecutor(a.j) as ex:
        res = dict(ex.map(lambda n: run(a.out, n), names))
    for n, r in res.items():
        print(f"{n:11s} expect {r['expect']:4s} -> {'PASS' if r['passed'] else 'FAIL'} {'OK' if r['ok'] else 'BAD'} "
              f"coll_done {r['coll_done']} cyc/tok {r['cycles_per_token']} {' | '.join(r['tail'][:2])}")
    noblock = None
    if 'base' in res and 'pos_block' in res:
        noblock = res['base']['coll_done'] is not None and res['base']['coll_done'] == res['pos_block']['coll_done'] \
            and res['base']['dut_last'] == res['pos_block']['dut_last']
        print('NO_BLOCK (pos_block coll_done == base)', noblock, res['base']['coll_done'], res['pos_block']['coll_done'])
    verdict = all(r['ok'] for r in res.values()) and noblock is not False
    rec = dict(tool='tools/mtp_colllane_gate.py', defines=DEF, cases=res, no_block_of_collective=noblock,
               verdict='PASS' if verdict else 'FAIL')
    (a.out / 'gate.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('MTP_COLLLANE_GATE', rec['verdict'])
    sys.exit(0 if verdict else 1)


if __name__ == '__main__':
    main()

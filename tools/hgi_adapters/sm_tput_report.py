#!/usr/bin/env python3
"""hgi-1010/g: tb_hgi_sm_tput run.log + vec/meta.json -> an hgi-e2e-schema report.json (hgi_sim.e2e_calibration.ratios /
service(): per record disp / ret / cost, unit SM op 0) plus the throughput bench's provenance.

    python3 tools/hgi_adapters/sm_tput_report.py RUNDIR --out results/rtl/hgi_unit_tput_20261010/sm/<veh>_L0_tput/report.json
            [--extra NAME=RUNLOG ...]  (sensitivity runs: same vectors, other +LAT / +BWX10)
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

PAT = re.compile(r"TPUT (\d+) disp (\d+) ret (\d+) service (\d+) lines (\d+) (\d+)")


def parse(log):
    t = Path(log).read_text()
    rows = [tuple(map(int, m.groups())) for m in PAT.finditer(t)]
    return rows, ("HGI_SM_TPUT PASS" in t), [ln for ln in t.splitlines() if ln.startswith(("x loaded", "summary", "HGI_SM"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--log', default='run.log')
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutants', nargs='*', default=[], help='MUT=run_log pairs (must FAIL)')
    ap.add_argument('--extra', nargs='*', default=[], help='NAME=run_log sensitivity runs')
    ap.add_argument('--commit', default='')
    a = ap.parse_args()
    run = Path(a.run)
    meta = json.loads((run / 'vec/meta.json').read_text())
    rows, ok, lines = parse(run / a.log)
    recs = []
    for (k, d, r, sv, l0, l1), m in zip(rows, meta['records']):
        recs.append(dict(k=k, unit='SM', op=0, tag=m['tag'], real=1, disp=d, ret=r, service=sv, cost=m['cost'],
                         ratio=round(sv / m['cost'], 3), fmt=m['fmt'], M=m['M'], K=m['K'], Q=m['Q'], LPR=m['LPR'],
                         lines_real_sm0_sm1_cum=[l0, l1], x_load=m['x_load'], mismatch=0 if ok else None))
    busy = sum(x['service'] for x in recs)
    cost = sum(x['cost'] for x in recs)
    muts = {}
    for s in a.mutants:
        n, p = s.split('=', 1)
        t = Path(p).read_text()
        muts[n] = 'FAIL (as required)' if 'HGI_SM_TPUT FAIL' in t else ('PASS (MUTANT NOT CAUGHT)' if 'PASS' in t else 'no verdict')
    extra = {}
    for s in a.extra:
        n, p = s.split('=', 1)
        rr, okx, lx = parse(p)
        extra[n] = dict(pass_=okx, service=[x[3] for x in rr], service_sum=sum(x[3] for x in rr), lines=lx)
    rep = dict(
        schema='opentallas.hgi_unit_tput.v1 (hgi-e2e report schema subset)', pass_=ok and len(recs) == len(meta['records']),
        summary=dict(cycles=rows[-1][2] - rows[0][1] if rows else 0, records=len(recs), service_sum=busy, sim_cost_sum=cost,
                     ratio=round(busy / cost, 3) if cost else None),
        per_unit=dict(SM=dict(records=len(recs), real=len(recs), exact=len(recs) if ok else 0, rtl_busy=busy, sim_cost=cost)),
        records=recs, mutants=muts, sensitivity=extra, rtl_lines=lines, vehicle=meta['vehicle'], price_source=meta['source'],
        source_commit=a.commit,
        bench='rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_tput.sv (run_sm_tput.sh; vectors tools/hgi_adapters/sm_tput_bench.py)',
        scaling=('NSM 32 adapter + publication at full width; SMs 0, 1 REAL ot_hbm_accel_smh at the production slice '
                 'Q = ceil(M / 32) rows x full K; SMs 2..31 replay real SM (s mod 2) port for port (identical op fields, '
                 'broadcast x, equal per-SM HBM share => identical timing); the publication serialises all 32 SMs\' rows '
                 'through NPC 4 VM clients, so its tail is measured, not scaled'),
        hbm_model='per real SM: in-order, first access +LAT (default 104 = hgi_sim MEAS hbm.first_access), one line every '
                  'LB x 32 / 3,166.7 cycles (the SM\'s share of the die\'s 3.80 TB/s)',
        limits=['B uses the D2 SM line image (B.stride = LPR x LB); the compiler exports carry raw-row strides, which '
                'ot_hgi_sm_record refuses (stride check E3) -- compiler gap, not measured here',
                'FP8 / FP4 records: ot_hgi_sm_xload refuses fmt 1 / 2 (no activation quantiser in RTL); timing = the real '
                'x-load in BF16 mode on the same A + tb-written quantised fragments'])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep['summary']), muts)


if __name__ == '__main__':
    main()

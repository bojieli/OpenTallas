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
# track-B engine bench (tb_hgi_smmv_tput, run_smmv_tput.sh): no per-SM line counters in its TPUT line
PAT_SMMV = re.compile(r"TPUT (\d+) disp (\d+) ret (\d+) service (\d+) xi ")
SMMV = False


def parse(log):
    t = Path(log).read_text()
    if SMMV:
        rows = [tuple(map(int, m.groups())) + (None, None) for m in PAT_SMMV.finditer(t)]
        return rows, ("HGI_SMMV_TPUT PASS" in t), [ln for ln in t.splitlines() if ln.startswith(("x loaded", "summary", "HGI_SM"))]
    rows = [tuple(map(int, m.groups())) for m in PAT.finditer(t)]
    return rows, ("HGI_SM_TPUT PASS" in t), [ln for ln in t.splitlines() if ln.startswith(("x loaded", "summary", "HGI_SM"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run', nargs='?')
    ap.add_argument('--log', default='run.log')
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutants', nargs='*', default=[], help='MUT=run_log pairs (must FAIL)')
    ap.add_argument('--extra', nargs='*', default=[], help='NAME=run_log sensitivity runs')
    ap.add_argument('--commit', default='')
    ap.add_argument('--xbd', action='store_true', help='run built with +define+XBD (native block-dot x, xload BD 1)')
    ap.add_argument('--smmv', action='store_true', help='log of tb_hgi_smmv_tput (ot_hgi_smmv engine, run_smmv_tput.sh)')
    ap.add_argument('--bench', default='', help='override the bench provenance string')
    ap.add_argument('--token', nargs='*', help='combine: report.json files -> per-token extrapolation over the priced program')
    a = ap.parse_args()
    global SMMV
    SMMV = a.smmv
    if a.token is not None:
        return token(a)
    run = Path(a.run)
    meta = json.loads((run / 'vec/meta.json').read_text())
    rows, ok, lines = parse(run / a.log)
    recs = []
    for (k, d, r, sv, l0, l1), m in zip(rows, meta['records']):
        recs.append(dict(k=k, unit='SM', op=0, tag=m['tag'], real=1, disp=d, ret=r, service=sv, cost=m['cost'],
                         ratio=round(sv / m['cost'], 3), fmt=m['fmt'], M=m['M'], K=m['K'], Q=m['Q'], LPR=m['LPR'],
                         lines_real_sm0_sm1_cum=[l0, l1], layer=m.get('layer'), o_bf16=m.get('o_bf16'), indexed=m.get('indexed'),
                         x_load=('native block-dot x (ot_hgi_sm_xload BD 1)' if a.xbd and m['fmt'] in ('FP8E4M3', 'FP4E2M1') else m['x_load']), mismatch=0 if ok else None))
    busy = sum(x['service'] for x in recs)
    cost = sum(x['cost'] for x in recs)
    muts = {}
    for s in a.mutants:
        n, p = s.split('=', 1)
        t = Path(p).read_text()
        muts[n] = 'FAIL (as required)' if re.search(r'HGI_SMM?V?_TPUT FAIL|DEADLOCK', t) else ('PASS (MUTANT NOT CAUGHT)' if 'PASS' in t else 'no verdict')
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
        bench=a.bench or 'rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_tput.sv (run_sm_tput.sh; vectors tools/hgi_adapters/sm_tput_bench.py)',
        scaling=('NSM 32 adapter + publication at full width; SMs 0, 1 REAL ot_hbm_accel_smh at the production slice '
                 'Q = ceil(M / 32) rows x full K; SMs 2..31 replay real SM (s mod 2) port for port (identical op fields, '
                 'broadcast x, equal per-SM HBM share => identical timing); the publication serialises all 32 SMs\' rows '
                 'through NPC 4 VM clients, so its tail is measured, not scaled'),
        hbm_model='per real SM: in-order, first access +LAT (default 104 = hgi_sim MEAS hbm.first_access), one line every '
                  'LB x 32 / 3,166.7 cycles (the SM\'s share of the die\'s 3.80 TB/s)',
        limits=['B uses the D2 SM line image (B.stride = LPR x LB); the compiler exports carry raw-row strides, which '
                'ot_hgi_sm_record refuses (stride check E3) -- compiler gap, not measured here',
                ('FP8 / FP4 records: native block-dot x path (ot_hgi_sm_xload BD 1, ot_hdc_actquant; opt-in on main 291e1f95f)'
                 if a.xbd else
                 'FP8 / FP4 records: ot_hgi_sm_xload refuses fmt 1 / 2 (no activation quantiser in RTL); timing = the real '
                 'x-load in BF16 mode on the same A + tb-written quantised fragments'),
                'indexed expert records (operand I, FP4 slots 0-5) run as plain records: the I read is not modelled',
                'the LM head publishes to VM here (production: STREAM)',
                'records are issued one after another; the adapter does not overlap records (MUT_EARLY shows why)'])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep['summary']), muts)


def token(a):
    """per-token SM.MATVEC: every SM record of the priced DS program gets the measured service of the benched record
    with the same shape key (fmt, K, M, O BF16, price); exact when identical shapes measure identically (checked:
    the spread of each key's measured services is reported)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sm_tput_bench as SB
    meas = {}
    for p in a.token:
        for r in json.loads(Path(p).read_text())['records']:
            k = (r['fmt'], r['K'], r['M'], bool(r.get('o_bf16')), r['cost'])
            meas.setdefault(k, []).append(r['service'])
    lays = [str(i) for i in range(40)] + ['head']
    prog, src = SB.program_records(lays)
    rows, miss, tot_m, tot_p, tot_pm = {}, [], 0.0, 0.0, 0.0
    for r in prog:
        k = (r['fmt'], r['K'], r['M'], bool(r['o_bf16']), r['cost'])
        tot_p += r['cost']
        if k not in meas:
            miss.append(r['tag']); continue
        v = meas[k]
        sv = sum(v) / len(v)
        tot_pm += r['cost']
        tot_m += sv
        e = rows.setdefault(str(k), dict(tag=r['tag'], fmt=k[0], K=k[1], M=k[2], o_bf16=k[3], price=k[4], measured=v,
                                         spread=max(v) - min(v), count=0))
        e['count'] += 1
    byfmt = {}
    for e in rows.values():
        f = byfmt.setdefault(e['fmt'], dict(records=0, price=0.0, measured=0.0))
        f['records'] += e['count']; f['price'] += e['count'] * e['price']; f['measured'] += e['count'] * sum(e['measured']) / len(e['measured'])
    for f in byfmt.values():
        f['ratio'] = round(f['measured'] / f['price'], 3); f['price'] = round(f['price'], 1); f['measured'] = round(f['measured'], 1)
    rep = dict(schema='opentallas.hgi_unit_tput.v1 (op record, per-token extrapolation)', op='SM.MATVEC',
               records_per_token=len(prog), unmatched=len(miss), price_cycles_per_token=round(tot_p, 1),
               measured_cycles_per_token=round(tot_m, 1), ratio=round(tot_m / tot_p, 3) if not miss else None,
               unmatched_price=round(tot_p - tot_pm, 1), matched_price=round(tot_pm, 1),
               ratio_matched=round(tot_m / tot_pm, 3) if tot_pm else None,
               by_fmt=byfmt, shapes=sorted(rows.values(), key=lambda e: -e['count'] * e['price']), program=src, from_reports=a.token,
               unmatched_kinds=sorted(set(miss)),
               max_spread=max((e['spread'] for e in rows.values()), default=None))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(rep['records_per_token'], rep['price_cycles_per_token'], rep['measured_cycles_per_token'], rep['ratio'], rep['ratio_matched'], 'unmatched', len(miss), 'max_spread', rep['max_spread'])


if __name__ == '__main__':
    main()

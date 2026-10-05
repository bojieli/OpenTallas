"""Measure the default-OFF P2 expert-fetch component at full32PC/8SM/96SRAM.

--points 1 is the minimal changed-capture gate: REFpb notice/non-notice, REFab,
three backpressure levels, correction and fail-stop controls. --points 64 is
an 88-case headline sweep, required only when the changed mechanism warrants it.
The 140ns first-access gate and composed40-fetch token gain remain independent.
Uses retained matching C++ objects; never accepts a binary for different RTL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
SOURCES = ['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_r5a_ecc_pkg.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_expert_stream_pc_p2.sv',
           'rtl/hbm_accel/service/ot_hbm_accel_expert_fetch_p2.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
           'rtl/test/hbm_accel/tb_hbm_accel_r5a_p2.sv']
TOP='tb_hbm_accel_r5a_p2'
VARIANTS={'p2':(SOURCES,TOP)}
STALL_PCT = (10, 40, 75)
GATE_NS = 140.0
PRICE = dict(central_refresh_live_ns=469.5, postponed_ns=133.2, cdc_ns=6.4, stall_ns=0.1, routed_fetches=40,
             r5a_modelled_us=13.46, r0c_modelled_us=-14.86,
             source='results/rtl/w19_expert_fetch.json; study a3ed9c36d ladder_model.py')
NOTICE_LEAD_PS = 300_000          # >= LEAD 32 + tRFCpb 196 + tRCD 19 cycles = 252 ns; static-schedule notice


def build(work, ref_mode, sources=SOURCES, top=TOP):
    d = work / f'build_ref{ref_mode}'
    exe = d / 'obj' / f'V{top}'
    fingerprint=hashlib.sha256((' '.join(sources)+str(ref_mode)+''.join(hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources)).encode()).hexdigest()
    stamp=d/'source.sha256'
    if exe.exists() and stamp.exists() and stamp.read_text().strip()==fingerprint:
        return exe
    # Verilator keeps unchanged generated C++ files; make reuses only matching
    # objects. A binary without a matching source stamp is never accepted.
    d.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '4', '-O2', '--top-module', top,
           '--Mdir', str(d / 'obj'), f'-GREF_MODE={ref_mode}'] + [str(ROOT / s) for s in sources]
    with open(d / 'build.log', 'w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    stamp.write_text(fingerprint+'\n')
    return exe


def run(exe, t_route_ps, lead_ps, mut=0, stall=0):
    out = subprocess.run([str(exe), f'+t_route_ps={t_route_ps}', f'+notice_lead_ps={lead_ps}', f'+mut={mut}']
                         + ([f'+stall={stall}'] if stall else []),
                         capture_output=True, text=True, check=False).stdout
    first = [l for l in out.splitlines() if l.startswith('FIRST ')]
    if len(first) < 2:
        return dict(t_route_ps=t_route_ps, notice_lead_ps=lead_ps, mut=mut, verdict='FAIL', raw=out[-2000:])
    kv = dict(re.findall(r'(\w+)=(-?\w+)', first[0]))
    rec = {k: int(v) for k, v in kv.items() if re.fullmatch(r'-?\d+', v)}
    rec.update(mut=mut, stall_pct=stall, verdict=first[1].split('=')[1], violations_text=[l for l in out.splitlines() if l.startswith('VIOL')][:5])
    rec['w13_first_all_ns'] = rec['w13_first_all_ps'] / 1000
    return rec


def stats(rows):
    v = [r['w13_first_all_ns'] for r in rows if r['verdict'] == 'PASS']
    return dict(cases=len(rows), passed=len(v), max_ns=max(v), mean_ns=round(statistics.mean(v), 2),
                min_ns=min(v), over_gate=sum(x > GATE_NS for x in v)) if v else dict(cases=len(rows), passed=0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=16)
    ap.add_argument('--points', type=int, default=64)
    ap.add_argument('--variant', choices=sorted(VARIANTS), default='p2')
    a = ap.parse_args(argv)
    sources, top = VARIANTS[a.variant]
    if a.out.exists():
        raise SystemExit('fresh record path required')
    a.work.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        exe_pb, exe_ab = ex.map(lambda m: build(a.work, m, sources, top), (1, 0))
    t0 = 8_000_000                                    # after the first full REFpb round and first REFab stagger
    pb_span, ab_span = 3_866_624, 3_899_392           # one 32-command REFpb round; one REFab tREFI (3,808 cycles)
    jobs = []
    for i in range(a.points):
        jobs.append(('refpb_notice', exe_pb, t0 + i * pb_span // a.points + 7_013 * i % 1024, NOTICE_LEAD_PS))
        jobs.append(('refpb_no_notice', exe_pb, t0 + i * pb_span // a.points + 7_013 * i % 1024, 0))
        jobs.append(('refab', exe_ab, t0 + i * ab_span // a.points + 7_013 * i % 1024, 0))
    if a.variant == 'p2':
        for st_pct in STALL_PCT:
            for i in range(0, a.points, 8):
                jobs.append((f'refpb_notice_stall{st_pct}', exe_pb, t0 + i * pb_span // a.points + 7_013 * i % 1024,
                             NOTICE_LEAD_PS, st_pct))
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: dict(case=j[0], **run(j[1], j[2], j[3], 0, j[4] if len(j) > 4 else 0)), jobs))
    neg = [dict(case='neg_corrupt_sector', **run(exe_pb, t0, NOTICE_LEAD_PS, 1)),
           dict(case='neg_trcd_check_plus_1ns', **run(exe_pb, t0, NOTICE_LEAD_PS, 2))]
    protection=[dict(case='single_bit_correction',**run(exe_pb,t0,NOTICE_LEAD_PS,3)),
                dict(case='double_bit_refusal',**run(exe_pb,t0,NOTICE_LEAD_PS,4)),
                dict(case='wrong_sector_identity',**run(exe_pb,t0,NOTICE_LEAD_PS,5)),
                dict(case='mutable_state_refusal',**run(exe_pb,t0,NOTICE_LEAD_PS,6)),
                dict(case='captured_syndrome_refusal',**run(exe_pb,t0,NOTICE_LEAD_PS,7)),
                dict(case='post_syndrome_packet_refusal',**run(exe_pb,t0,NOTICE_LEAD_PS,8))]
    by = {c: [r for r in res if r['case'] == c] for c in ('refpb_notice', 'refpb_no_notice', 'refab')}
    st = {c: stats(v) for c, v in by.items()}
    sel = st['refpb_notice']
    stall_rows = [r for r in res if r['case'].startswith('refpb_notice_stall')]
    exact = all(r['verdict'] == 'PASS' and r.get('bad', 1) == 0 and r.get('viol', 1) == 0
                for r in by['refpb_notice'] + stall_rows)
    measured = sel.get('max_ns')
    base = PRICE['central_refresh_live_ns'] + PRICE['cdc_ns'] + PRICE['stall_ns']
    gain_us = None if measured is None else round(PRICE['routed_fetches'] * (base - measured) * 1e-3, 3)
    rec = dict(schema='opentallas.hbm_accel.ha4.expert_first_access.v1', variant=a.variant, top=top,
               source_commit=os.environ.get('OT_SOURCE_COMMIT') or subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
               source_dirty=False if os.environ.get('OT_SOURCE_COMMIT') else bool(subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT,
                                                capture_output=True, text=True).stdout.strip()),
               input_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in sources},
               simulator=subprocess.run([VERILATOR, '--version'], capture_output=True, text=True).stdout.strip(),
               host=os.uname().nodename, controller_clock_ps=1024, sm_clock_ps=833.333333333,
               metric='router top-6 out -> every SM of the stack has released the first expert\'s w1/w3 lines '
                      '(the c52 w19_expert_fetch exposed_ns metric)',
               assumed_path_ns=dict(noc_each_way=5.0, phy_command=5.0, phy_response=10.0,
                                    note='same terms the c52 bench charged as REQ_PS/RSP_PS = 15 ns each way'),
               notice_lead_ps=NOTICE_LEAD_PS, gate_ns=GATE_NS, stats=st,
               exact=dict(verdict='PASS' if exact else 'FAIL', cases=len(by['refpb_notice']) + len(stall_rows),
                          backpressure_cases=len(stall_rows),
                          sectors_checked_per_case=6 * 392 * 4),
               negative_controls=[dict(case=n['case'], verdict=n['verdict'], bad=n.get('bad'), viol=n.get('viol')) for n in neg],
               performance=dict(verdict='PASS' if measured is not None and measured<=GATE_NS else 'FAIL',
                    first_access_gate_ns=GATE_NS, criterion='all SMs first-expert w1/w3 access, independent of composed token gain'),
               adoption=False, physical_context='NOT_RUN',
               price=PRICE, measured_first_access_worst_ns=measured,
               measured_r5a_gain_us_vs_central=gain_us,
               cases=res + neg, protection=protection,
               protection_pass=protection[0]['verdict']=='PASS' and protection[0].get('bad',1)==0 and all(p['verdict']=='FAIL' and 'DUT FAULT' in p.get('raw','') for p in protection[1:]) and all('sm0_delivered=0' in p.get('raw','') for p in protection[-2:]))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(dict(stats=st, exact=rec['exact'], negative=rec['negative_controls'], gain_us=gain_us,protection_pass=rec['protection_pass']), indent=2))


if __name__ == '__main__':
    main()

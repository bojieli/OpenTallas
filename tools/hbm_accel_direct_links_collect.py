#!/usr/bin/env python3
"""Collect existing HA2 terminals, never build or rerun them. Exclusive evidence output."""
import argparse
import hashlib
import json
import re
from pathlib import Path

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def collect(run, faults, price_file):
    required=['supervisor.exit','gather_build.exit','reduce_build.exit',
              'pins_after.exit','input_sha256.txt','source_commit.txt']
    missing=[x for x in required if not (run/x).exists()]
    if missing: raise RuntimeError('nonterminal run: '+', '.join(missing))
    exits={x:int((run/x).read_text()) for x in required if x.endswith('.exit') and x!='supervisor.exit'}
    gather=(run/'gather.log').read_text() if (run/'gather.log').exists() else ''
    reduce=(run/'reduce.log').read_text() if (run/'reduce.log').exists() else ''
    for name in ['gather.exit','reduce.exit']:
        if (run/name).exists(): exits[name]=int((run/name).read_text())
    gt=re.search(r'HA2_TERMINAL checks=(\d+) mismatches=(\d+)',gather)
    rt=re.search(r'HA2_REDUCE_TERMINAL checks=(\d+) mismatches=(\d+)',reduce)
    markers_present=bool(gt and rt)
    rows=[dict(round=int(r),first_cycles=int(f),last_cycles=int(l),
               first_ns=int(f)*0.834,last_ns=int(l)*0.834)
          for r,f,l in re.findall(r'HA2_GATHER round=(\d+) first_cycles=(\d+) last_cycles=(\d+)',gather)]
    rc=[int(x) for x in re.findall(r'HA2_REDUCE case=\d+ cycles=(\d+)',reduce)]
    ft=re.search(r'HA2_FAULT_TERMINAL checks=(\d+) mismatches=(\d+)',(faults/'faults.log').read_text())
    model=json.loads(price_file.read_text())['price']
    longest=max((x['last_ns'] for x in rows),default=None)
    exact=markers_present and not any(exits.values()) and int(gt[2])==0 and int(rt[2])==0 and ft and int(ft[2])==0
    return dict(schema='opentallas.rtl.hbm_accel_ha2.v1',
        source_commit=(run/'source_commit.txt').read_text().strip(),
        fault_source_commit='a4d53ea7a', host='ot-agidock128', run_pid=419075,
        input_sha256=(run/'input_sha256.txt').read_text().splitlines(),
        raw_sha256={p.name:sha(p) for p in run.iterdir() if p.is_file()},
        exits=exits, exact=dict(directed_verdict='PASS' if exact else 'INCOMPLETE_REDUCER_ELAB_FAILED',
            gather_verdict='PASS' if gt and int(gt[2])==0 and exits.get('gather.exit')==0 else 'FAIL',
            reducer_verdict='ELABORATION_FAILED_MISSING_ot_hdc_lzc32' if exits.get('reduce_build.exit')==95 else ('PASS' if rt and int(rt[2])==0 else 'PENDING'),
            gather_packet_checks=int(gt[1]) if gt else None, gather_fp32_lane_checks=int(gt[1])*16 if gt else None,
            gather_mismatches=int(gt[2]) if gt else None, reduction_cases=int(rt[1]) if rt else None,
            reduction_mismatches=int(rt[2]) if rt else None,
            fault_checks=int(ft[1]) if ft else None, fault_mismatches=int(ft[2]) if ft else None,
            real_w19_executor_verdict='PENDING',head_token_verdict='PENDING'),
        measurements=dict(gather=rows, standalone_fp32_tree_cycles=rc,
            standalone_fp32_tree_ns=[x*0.834 for x in rc], arithmetic_bench_lanes=1,
            simulated_period_ns=0.834, clock_target_hz=1.2e9,
            clock_note='1 ps precision rounds each 416.667 ps half-cycle to 417 ps; no physical frequency qualification',
            whole_allreduce_ns=None,gather_slope_ns_per_word=None,topk_96x512_cycles=None,
            gather_measurement_valid=bool(gt and int(gt[2])==0),
            bounds='96 ranks, one 512-bit word/rank/snapshot; explicit wire registers, single-flight credits, output stalls',
            phy='130 ns ESTIMATE simulated service, not measured PHY',
            cdc='not exercised',refresh='not exercised',system_serial_critical_path='PENDING'),
        price=dict(record=str(price_file),fixed_gather_ns_estimate=model['latency']['gather_fixed_ns_estimate'],
            measured_snapshot_minus_estimate_ns=(longest-model['latency']['gather_fixed_ns_estimate']) if longest is not None else None,
            delta_cause='price assumed two hops without contention; five global records serialize onto each local port behind returning single-flight credits',
            w15_fixed_gather_reference_ns=777,w15_fixed_ar_reference_ns=824,
            comparison='reference fixed terms are not a matched payload slope comparison'),
        physical=dict(serdes_mm2_estimate=model['area']['serdes_mm2'],
            serdes_w_estimate=model['power']['serdes_w'],
            composed_area_mm2=None,routed_corridor_verdict='NOT_RUN',
            ss_wns_ns=None,ff_wns_ns=None,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        measured_composition=dict(adopted_rungs=[],ha2_per_user_gain_pct=None,
            status='HA2 excluded: no real-program/system/physical qualification'),
        verdict=('REJECT_SNAPSHOT_CANDIDATE' if longest is not None and longest>550 else
                 'FAIL_BUILD_OR_EXACT_GATE' if not exact else 'PENDING_SYSTEM_GATES'),
        adopt=False, reasons=['snapshot measured against <=550 ns first gate',
            'no full-context all-reduce/CDC/refresh/top-k/slope qualification',
            'area, route, SS/FF and composed gain gates not passed'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--faults',type=Path,required=True);ap.add_argument('--price',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    rec=collect(a.run,a.faults,a.price)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f: json.dump(rec,f,indent=2);f.write('\n')

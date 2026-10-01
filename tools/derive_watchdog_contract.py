#!/usr/bin/env python3
"""Source/read-only metadata audit; no simulator, payload reads or live changes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from watchdog_contract_model import Budget, Event, Sample, Watchdog, legacy_pc_timeout

ROOT=Path(__file__).resolve().parents[1]
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
DRIVER='rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp'
PORTS='rtl/test/v41_runtime/ot_v41_rt_die.sv'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def small(path):
    if path.stat().st_size>4*1024**2: raise ValueError('metadata size cap')
    return path.read_bytes()


def connected_case(record_raw,log_raw):
    record=json.loads(record_raw)
    if record['source_commit']!=SOURCE or record['status']!='PASS_BOUNDED_CONNECTED_BASELINE':
        raise ValueError('connected source/verdict mismatch')
    if sha(log_raw)!=record['simulation']['log_sha256']: raise ValueError('runtime log hash mismatch')
    log=log_raw.decode()
    fields=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',re.search(r'CONNECTED_WINDOW_PASS .*',log)[0]))
    if fields!=record['metrics']: raise ValueError('terminal metrics mismatch')
    if fields['reads']!=2176 or fields['replies']!=2176 or fields['max_inflight']!=1:
        raise ValueError('connected geometry mismatch')
    points=[]
    for line in log.splitlines():
        if line.startswith('PROGRESS '):
            f=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(-?\d+)\b',line))
            points.append({k:f[k] for k in ('cycle','reads','replies','rows','refill','staged')})
    if not points or not all(b['replies']>a['replies'] for a,b in zip(points,points[1:])):
        raise ValueError('no observed advancing reply trace')
    # Lift only the bounded service trace into a constant-PC abstraction. The
    # connected bench has no actual core PC, so never call it a live PC replay.
    trigger=fields['start']+100001
    return {'metrics':fields,'progress':points,'assumed_constant_core_pc':24,
       'constant_pc_is_counterfactual':True,'watchdog':100000,
       'legacy_first_failing_cycle':legacy_pc_timeout([(fields['start'],(24,)*4),(trigger,(24,)*4)],100000),
       'healthy_reply_checkpoint_after_trigger':next(p for p in points if p['cycle']>trigger),
       'stage_dwell_cycles':fields['staged']-fields['start'],
       'conclusion':'Constant-PC interpretation falsely times out this completed cold service; no actual core-PC or current-live deadlock conclusion',
       'universal_bound_admitted':False}


def negatives():
    b=Budget(1,3,10,1,2,2,'synthetic trace formula only',('one credit','no competitor'))
    scenarios={}
    m=Watchdog([b]*4,diagnostic_pc_dwell=5)
    trace=[(c,(24,c,24,24)) for c in range(32)]
    outcomes=[]
    for c,pc in trace: outcomes.append({'cycle':c,'pcs':pc,'verdict':m.advance(c,[Sample(p) for p in pc])})
    scenarios['one_rank_starvation']={'authority':'synthetic','budget':b.__dict__,
       'legacy_timeout':legacy_pc_timeout(trace,5),'samples':outcomes}
    m=Watchdog([None]*4,diagnostic_pc_dwell=5)
    outcomes=[]
    for c in range(8):outcomes.append({'cycle':c,'busy':c%2,'verdict':m.advance(c,[Sample(24,c%2)]*4)})
    scenarios['spurious_busy']={'authority':'synthetic','samples':outcomes}
    m=Watchdog([b]*4)
    m.advance(0,[Sample(24)]*4,[Event(0,'offer','op0/sector0'),Event(0,'accept','op0/sector0')])
    scenarios['absent_response']={'authority':'synthetic','accepted_cycle':0,'identity':'op0/sector0',
       'response_bound':10,'checked_cycle':11,'verdict':m.advance(11,[Sample(25)]*4),
       'classification':'response deadline violation under supplied synthetic bound, not proof of causal deadlock'}
    b=Budget(30,3,4,1,2,2,'synthetic serial composition',('one credit','no competitor'))
    m=Watchdog([b]*4,diagnostic_pc_dwell=5);outcomes=[]
    for i in range(30):
        for c,kind in ((i*5,'offer'),(i*5+1,'accept'),(i*5+4,'response')):
            es=[Event(r,kind,f'op0/sector{i}') for r in range(4)]
            outcomes.append({'cycle':c,'kind':kind,'identity':f'op0/sector{i}',
                'verdict':m.advance(c,[Sample(24)]*4,es)})
    outcomes.append({'cycle':150,'kind':'complete','verdict':m.advance(150,[Sample(24)]*4,[Event(r,'complete') for r in range(4)])})
    scenarios['long_healthy_refill']={'authority':'synthetic','budget':b.__dict__,
       'legacy_timeout':legacy_pc_timeout([(c,(24,)*4) for c in range(151)],5),'samples':outcomes}
    assert scenarios['one_rank_starvation']['legacy_timeout'] is None
    assert [0,'RESPONSE_DEADLINE'] in json.loads(json.dumps(scenarios['absent_response']['verdict']))
    assert all(not s['verdict'] for s in outcomes)
    return scenarios


def audit(out,case,bench_repo):
    if out.exists(): raise FileExistsError('additive fresh evidence directory required')
    record_raw=small(case/'record.json');log_raw=small(case/'runtime.log');record=json.loads(record_raw)
    pins={}
    for p,expected in {**record['source_sha256'],DRIVER:None,PORTS:None}.items():
        raw=subprocess.check_output(['git','show',SOURCE+':'+p],cwd=ROOT)
        if expected and sha(raw)!=expected: raise ValueError('source pin mismatch: '+p)
        pins[p]=sha(raw)
    bench=small(bench_repo/'rtl/test/w17_window_connected_baseline/tb.sv')
    tool=small(bench_repo/'tools/w17_window_connected_baseline.py')
    if sha(bench)!=record['bench_sha256'] or sha(tool)!=record['tool_sha256']:
        raise ValueError('connected producer pin mismatch')
    result={'status':'PASS_CONTRACT_MODEL_TESTS_ONLY','source_commit':SOURCE,'source_sha256':pins,
      'authority':{'connected_case_path':str(case),'record_sha256':sha(record_raw),'runtime_sha256':sha(log_raw),
          'bench_sha256':sha(bench),'tool_sha256':sha(tool)},'connected_counterexample':connected_case(record_raw,log_raw),
      'observable_existing_Die_interface':{
          'pc':'per-rank program-counter changes; same PC may span healthy service, PC toggles need not retire an operation',
          'done':'per-rank terminal indication; check fault and service drain before accepting success',
          'fault':'per-rank DUT fault, independent of progress; sample before done/timeout classification',
          'dstate':'core state/unit/idles/wait flags and packed sticky fault sources; diagnostic, transitions not guaranteed useful progress',
          'dwords':'16-bit CDMA in/out words; modular deltas require bounded sampling and epoch/owner binding; not WINDOW sector counts',
          'busy/issue/cycles':'activity/selection/elapsed count, not proof of retirement',
          'links':'driver enqueue/dequeue and destination queues are visible in link_step; aggregate traffic is insufficient per-rank operation progress'},
      'existing_wrapper_ports_not_in_Die_virtual_interface':{'dbg_fs':'can add getter in future driver using existing wrapper port; no RTL instrumentation needed'},
      'needs_new_causal_observability':[
          'WINDOW descriptor acceptance/owner/epoch, state, row publication and schedule completion',
          'offered and accepted service identity, source/rank/tag/epoch plus accepted timestamp',
          'matching response handshake and actual row/operation retirement, not response valid alone',
          'request/response per-owner queue occupancy/oldest age and backend refresh/arbitration state',
          'per-engine operation start/retire and wait dependency reason (ports or separate source-pinned simulation probe)'],
      'deadline_contract':{'operation_formula':'stage + N*(admission + response + issue_gap) + drain, conservative serialized one-credit scenario',
          'admission_origin':'first stable owned offer; bound must include ready/backpressure and arbitration',
          'inflight_origin':'accepted unique operation-qualified identity; matched response retires; duplicate/spent reject before mutation',
          'operation_origin':'operation start; never slides with PC, traffic or useful progress; late completion cannot erase failure',
          'missing_bound':'UNKNOWN/BOUND_MISSING; diagnostic silence is not proved deadlock',
          'universal_timeout_admitted':False},
      'finite_bounds_still_missing':[
          'reachable starting bank/open-row/refresh state and lazy refresh catch-up bound, not one cold start',
          'competitor arrival/backlog limits and owner mux/PC arbiter fairness in cycles; MAXSKIP16 limits bypass count, not elapsed time alone',
          'queue admission/service bounds including backend request/RSP queues and consumer-ready stalls',
          'producer row handoff, descriptor stage/publication, packed-row drain and engine-ready/SU retirement bounds',
          'operation sizes/canonical owner identities for each PC and epoch, error/abort/reset completion rules',
          'clock-domain/cycle conversion for each service bound; do not transfer physical 1.2GHz qualification from runtime CLK_PS1000'],
      'near_term_future_driver_fix':[
          'strict positive bounded parsing for RT_WATCHDOG/maxc/link latencies; original uses atol/atoi unchecked',
          'sample each rank fault/done/PC/state/words before aggregate all-done and timeout decisions',
          'per-rank diagnostics exclude completed ranks; keep hard external wall/cycle ceilings as failed/incomplete run caps, not service proofs',
          'snapshot per-rank existing diagnostics and link due-queue ages; no busy/state/credit heartbeat resets',
          'add accepted identity/response/retirement instrumentation separately and review bounds before enforceable per-service deadlines',
          'no proposal to relax RT_WATCHDOG based on this single observation'],
      'limits':['standalone model and test-harness correctness only','no actual current-live PC24 deadlock or liveness verdict','no full-token, universal deadline, payload or hardware admission','no driver/source/live job edits or restarts']}
    out.mkdir(parents=True)
    (out/'attempt9_record.json').write_bytes(record_raw);(out/'attempt9_runtime.log').write_bytes(log_raw)
    (out/'contract.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (out/'negative_controls.json').write_text(json.dumps(negatives(),indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out',type=Path,required=True);a.add_argument('--case',type=Path,required=True)
    a.add_argument('--bench-repo',type=Path,required=True);args=a.parse_args()
    audit(args.out,args.case,args.bench_repo)

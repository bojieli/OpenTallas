#!/usr/bin/env python3
"""Read-only baseline intake and epoch-candidate comparison; never builds."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = '4e38326d6f361bc85e660f48c59c355e2bb95274'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-dir', required=True)
    ap.add_argument('--out', required=True, help='new evidence directory')
    args = ap.parse_args()
    baseline = Path(args.baseline_dir)
    raw = (baseline/'record.json').read_bytes()
    log = (baseline/'runtime.log').read_bytes()
    b = json.loads(raw)
    assert b['source_commit'] == PIN and b['status'] == 'PASS_BOUNDED_CONNECTED_BASELINE'
    assert sha(log) == b['simulation']['log_sha256']
    for path, expected in b['source_sha256'].items():
        assert sha(subprocess.check_output(['git','show',PIN+':'+path], cwd=ROOT)) == expected
    g, m = b['geometry'], b['metrics']
    for key, value in dict(rows=128,sectors_per_row=17,base_sector=262144,
                           source_credits=1,backend_TAGW=17,NPC=32,REFPB=3,
                           CLK_PS=1000,MEM_MODE=0,MEM_WORDS=264320).items():
        assert g[key] == value
    drains = re.findall(r'PC_DRAIN pc=(\d+) reads=(\d+) q=(\d+) r=(\d+) refreshes=(\d+) activations=(\d+)',log.decode())
    assert len(drains) == 32 and {int(d[0]) for d in drains} == set(range(32))
    assert all(tuple(map(int,d[1:4])) == (68,0,0) for d in drains)
    assert m == dict(start=12300,staged=136669,done=136800,refill=124368,
                     reads=2176,replies=2176,beats=32,max_inflight=1)
    candidate_path = ROOT/'results/rtl/w17_window_epoch9_candidate_20261001_attempt1/record.json'
    candidate = json.loads(candidate_path.read_bytes())
    assert candidate['verdict'] == 'PASS_BOUNDED_CORRECTNESS_ONLY'
    # Schedule edge identity, from the unchanged source model. B=last scale response.
    predicted_last_response = m['start']+m['refill']-1
    predicted_staged = predicted_last_response+1
    row_span_sum = m['refill']-128*3
    latency_sum = row_span_sum-128*16
    r = dict(schema='opentallas.window_epoch9.baseline_comparison.v1',
        source_commit=PIN,baseline_record_sha256=sha(raw),baseline_log_sha256=sha(log),
        candidate_record_sha256=sha(candidate_path.read_bytes()),
        verdict='MEASURED_CREDIT1_ANCHOR_CANDIDATE_CORRECTNESS_ONLY',
        baseline_metrics=m,backend_drained_PCs=32,
        backend_refreshes=sum(int(d[4]) for d in drains),
        backend_activations=sum(int(d[5]) for d in drains),
        source_edge_accounting=dict(prior_model_predicted_last_response_cycle=predicted_last_response,
            prior_model_predicted_staged_cycle=predicted_staged,
            observed_minus_predicted_staged_cycles=m['staged']-predicted_staged,
            verdict='ONE_CYCLE_EDGE_CONVENTION_MISMATCH_PRESERVED',
            stage_minus_start_cycles=m['staged']-m['start'],
            done_minus_start_cycles=m['done']-m['start'],
            schedule_refill_cycles=m['refill'],sum_row_firstgrant_to_scale_reply_spans=row_span_sum,
            sum_handshake_latencies_if_no_request_refusal=latency_sum,
            identity='refill=sum(row_span)+384; credit1 row_span=sum(17 handshake latencies)+16 when requests are not refused',
            inference_limit='Prior model edge identity differs by1 from fixture labels. Aggregate counter alone does not prove every request-ready edge. Inferred latency sum is conditional, not an event-by-event transcript; no edge alignment tuning applied.'),
        candidate_comparison=dict(credits=8,epoch_bits=9,correctness='PASS through actual owner muxes and KARB with synthetic service',
            actual_backend_refill_cycles=None,gain=None,
            constant_service_model='credit1=128*(17L+19); credit8=128*(3L+12) for constant handshake L>=7 and no refusal',
            model_limit='Do not fit constant L to measured credit1 or divide baseline by8. Actual DRAM refresh, row state, PC queues and return arbitration depend on changed admission times.'),
        conditional_layer_cost=dict(one_identical_cold_refill_schedule_cycles=124368,
            start_to_staged_cycles=124369,
            scope='One bounded cold WINDOW refill contribution only. Subsequent QK/PV, other layer work, retention and competitors need their own composed conditions; no whole40/warmtoken transfer.'),
        watchdog_observation=dict(threshold_cycles=100000,refill_exceeds_threshold_by=24368,
            scope='Refill counter exceeds threshold; whether ANY-rank-PC watchdog actually fires depends on its own progress/reset contract. Parent owns that analysis. No live driver/watchdog edit.'),
        next_gate='Model source-controlled eight-credit admission and actual backend/return timing event by event at the same start/reset origin. Preserve edge identities and predict before reusing parent connected fixture. Verify per-PC counts/drain and reject mismatches rather than fitting timings.',
        limits=['CLK_PS1000 internal behavioral timing; no physical clock qualification',
            'No competitors; source API historical prime provenance, generated nonpoison data, no actual producer writes/checkpoint/fulltoken qualification',
            'No builds, parent baseline reruns, live/main edits or watchdog changes in this intake',
            'Healthy wrap conservation qualified; external fault recovery and512-epoch same-tag ghosts remain subject to explicit drain/nonreplay contract'])
    out = (ROOT/args.out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    (out/'baseline_record.json').write_bytes(raw)
    (out/'baseline_runtime.log').write_bytes(log)
    (out/'comparison.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('verdict','baseline_metrics','backend_refreshes','backend_activations')},indent=2))

if __name__ == '__main__':
    main()

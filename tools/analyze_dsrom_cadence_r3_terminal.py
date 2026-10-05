#!/usr/bin/env python3
"""Read-only reconstruction of the retained r3 trace; never launches HDL."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/rtl/dsrom_upstream_pair_cadence_execution_r3_20261002'


def loader_trace(cfg_cycle=13, last_cycle=119, nseg=8):
    """Simultaneous NBA transcription of pair loader; values after each edge."""
    run = k = valid = address = 0
    trace = []
    for cycle in range(last_cycle + 1):
        old_run, old_k = run, k
        valid, address = old_run, old_k
        if cycle == cfg_cycle:
            run, k = 1, 0
        elif old_run:
            k = (old_k + 1) & 31
            if old_k == 3 * nseg:
                run = 0
        trace.append(dict(cycle=cycle, ld_run=run, ld_k=k, c_v=valid, c_a=address))
    return trace


def inspect(text):
    edges = [dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', line))
             for line in text.splitlines() if line.startswith('EDGE ')]
    emitted = [int(re.search(r'cycle=(\d+)', line)[1]) for line in text.splitlines()
               if line.startswith('EMITTED ')]
    occupancy = 0
    pops = []
    first_overflow = None
    for e in edges:
        if e['cnt'] != occupancy:
            raise ValueError('occupancy discontinuity')
        if e['gate']:
            if e['pop']:
                pops.append(e['cycle'])
            occupancy += e['npush'] - e['pop']
            if occupancy > 4 and first_overflow is None:
                first_overflow = e['cycle']
    return dict(emitted_cycles=emitted, pop_cycles=pops, first_overflow=first_overflow,
                final_occupancy=occupancy, last_edge=edges[-1])


def analyze():
    manifest = json.loads((EVIDENCE / 'artifact_sha256.json').read_text())
    for name, digest in manifest.items():
        if hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() != digest:
            raise ValueError('retained evidence changed: ' + name)
    record = json.loads((EVIDENCE / 'record.json').read_text())
    text = (EVIDENCE / 'production5_simulate.log').read_text()
    observed = inspect(text)
    trace = loader_trace()
    writes = [e for e in trace if e['c_v']]
    assert [e['c_a'] for e in writes] == list(range(25))
    assert trace[119]['c_v'] == 0 and trace[119]['c_a'] == 25
    assert observed['first_overflow'] == 119
    assert observed['emitted_cycles'] == list(range(62, 118, 5))
    assert observed['pop_cycles'] == list(range(65, 114, 8))
    return dict(
        status='FAIL_UNQUALIFIED_UNCHANGED', evidence_commit='97b880aba6085f565ab553b092c7cc8c853a5c83',
        GO_commit=record['GO_commit'], observed=observed,
        config_contract=dict(nseg=8, cw=25, legal_valid_write_addresses=[0,24],
            cfg_go_cycle=13, last_valid_registered_port=writes[-1],
            first_inactive_registered_port=trace[39], fault_cycle_port=trace[119],
            element_last_write_edge=39, go_edge=40,
            conclusion='ca25 is an inactive held port address, not a legal valid write; c_v0 is source-derived, not logged independently'),
        fault_ownership=dict(overflow='4+1>4+0 on enabled edge119',
            hazard=1, issue=0, pairfault=1, spinefault=0, walker_position=0,
            incoming_position=1, slot=0, emitted=12, pushes=12, pops=7,
            confidence='high: actual trace plus existing source inequality; selected composition only'),
        terminal_defects=dict(parser='unconditionally requires ca<25 despite inactive c_v',
            bench='sequential OTHER_FAULT check after $finish; generated C++ calls VL_FINISH_MT then checks sticky ffault and calls VL_STOP_MT',
            actual_fatal='OTHER_FAULT at line200; no STATIC_WITNESS_NOT_REPRODUCED in actual log',
            policy='retain fatal rejection and all old receipts; no retroactive PASS'),
        model=dict(scope='one selected full-row FP4/MTP2 pair, not fullfield throughput or physical qualification',
            producer_interval_cycles=5, consumer_same_slot_interval_cycles=8,
            arrival_slices_per_cycle='1/5', maximum_same_slot_service_per_cycle='1/8',
            excess_slices_per_cycle='3/40', finite_fifo_cannot_cover_unbounded_stream=True,
            position_schedule_words_before=40, proposed_latency_bound_schedule_words=64,
            mtp_positions=2, added_schedule_cycles=48,
            fixture_period_ps=833, analytical_added_schedule_ns=39.984,
            schedule_duration_increase_percent=60, schedule_rate_decrease_percent=37.5,
            extra_state_for_image_only_admission=0,
            note='This is schedule cost, not end-to-end token latency or SS/FF credit; VM readiness and final drain remain composed separately.'),
        proposal=dict(execution_authorized=False, hardware_or_expectations_changed=False,
            diagnostic='New additive bench captures pre/post c_v and ld_run/ld_k; validate address bounds only on valid write, exact inactive25 derivation otherwise. Make recognized first-fault and unrelated-fault paths mutually exclusive; retain all unrelated fatal checks.',
            admission='Bind image generator recurrence floor to actual LAT8 and reject production5/FAST1 composition before launch. Use source-existing FAST8 schedule as control; model all round demands before any broader adoption.',
            alternative='Actual upstream credits/throttle requires separate source/model/gating proof; larger FIFO alone does not repair sustained excess.',
            qualification='Production overflow is a mandatory composition/admission failure, even if a future negative diagnostic recognizes it cleanly.'),
        used_seconds=record['used_seconds'], peak_memory_bytes=int(record['final_metrics']['memory.peak']),
        claims=dict(fullfield=False, physical=False, fulltoken=False, adoption=False))


if __name__ == '__main__':
    print(json.dumps(analyze(), indent=2, sort_keys=True))

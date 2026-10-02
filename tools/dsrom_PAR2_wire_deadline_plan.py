"""Finite physical delivery requirements from a sealed, unmeasured source prediction."""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_PAR2_wire_deadline_plan_20261002'


def shared_link(events, bits_per_edge, latency, capacity):
    """One shared domain, registered delivery, positive service; no free concurrency.

    Each event supplies ready-edge and consumer preedge deadline. Delivery is
    post-edge; its consumer can sample on the following edge. Queue capacity
    includes in-flight packets until that sample. Overflow is fail-closed.
    """
    if any(type(x) is not int or x <= 0 for x in (bits_per_edge, latency, capacity)):
        raise ValueError('positive bandwidth, latency and owned capacity required')
    finish = 0
    leases = []
    results = []
    for e in sorted(events, key=lambda x: (x['ready'], x['identity'])):
        if e['bits'] <= 0 or e['deadline'] < e['ready']:
            raise ValueError('invalid packet or deadline')
        # No same-edge credit reuse: a seat sampled at n is reusable at n+1.
        leases = [n for n in leases if n >= e['ready']]
        if len(leases) >= capacity:
            raise ValueError('finite shared-domain queue overflow')
        start = max(finish, e['ready'])
        finish = start + math.ceil(e['bits'] / bits_per_edge)
        sample = finish + latency + 1
        leases.append(sample)
        results.append(dict(identity=e['identity'], sample=sample,
                            exposed_edges=max(0, sample-e['deadline'])))
    return results


def build():
    inp = BASE / 'inputs'
    origins = json.loads((inp/'origins.json').read_text())
    for n, receipt in origins.items():
        if hashlib.sha256((inp/n).read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('sealed source input changed')
    p = json.loads((inp/'prediction.json').read_text())
    roots = [json.loads(x) for x in (inp/'root_prediction.jsonl').read_text().splitlines()]
    writes = [json.loads(x) for x in (inp/'VM_write_prediction.jsonl').read_text().splitlines()]
    byrow = {r['row']: r for r in roots}
    if len(byrow) != 576 or len(writes) != 576:
        raise ValueError('whole row conservation')
    for w in writes:
        r = byrow[w['address']-32768]
        if w['edge'] != r['edge']+1 or w['port'] != r['root']:
            raise ValueError('native registered root writer relation changed')
    bursts = Counter(r['edge'] for r in roots if r['root'] >= 64)
    return dict(
        schema='opentallas.dsrom.PAR2.wire-deadline-plan.v1',
        candidate='DS4096-TP4-S58-PAR2-NP2048',
        origins=origins, generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_prediction_not_measured=True, source_edges=p['absolute_edges'],
        cfg=dict(command_accept_edge=13, read_edges=[14,38], capture_edges=[15,39],
                 go_edge=40, words_per_pair=25, payload_bits_per_word=48,
                 independent_ports_per_shard=2048, aggregate_payload_bits_per_shard=2457600,
                 local_parallel_ports_not_shared_link_bandwidth=True,
                 remote_command_identity_bits=37,
                 hard_ROM_clkq_capture_and_fanout_cost=None,
                 requirement='All local configuration visible before GO; command crossing must shift or precede cfg origin; no invented prefetch lead.'),
        activation=dict(VM_read_edges=[40,119], AQ_capture_edges=[54,133],
                        accepted_broadcast_edges=[62,292], first_CE=65,
                        conservative_full_packet_bits=1681,
                        packet_basis='1632 full source bus plus49 identity bits; interface proposal, not accepted network ABI',
                        native_pair_accept_to_first_CE_edges=3,
                        those_three_edges_are_not_free_wire_slack=True,
                        upstream_packet_ready_edges=None,
                        requirement='Bind each producer-ready receipt to pair acceptance and preserve native have/s_ok; any later pair receipt propagates through actual source schedule.'),
        root=dict(total_rows=576, shard1_crossing_rows=sum(bursts.values()),
                  shard1_burst_rows_by_edge=dict(sorted(bursts.items())),
                  proposed_packet_bits=108, peak_proposed_payload_bits_per_edge=max(bursts.values())*108,
                  native_local_root_to_VM_write_edges=1,
                  physical_shared_domain_bandwidth=None, physical_CDC_edges=None,
                  registered_delivery_requires_next_edge_sample=True,
                  requirement='Hold exact ordered identity/data until destination visibility. Original source has no new ACK; crossing receiver storage/credits require separately priced implementation.'),
        provider_contract=dict(required_fields=['source_receipt','resource_domain','bits_per_edge','latency_edges',
                                               'owned_queue_capacity','registered_delivery','owner_visibility_edge'],
                               shared_resource_across_event_classes=True,
                               mutable_control_SRAM_HBM_link_protection_retained=True),
        no_ROM_ECC=True, new_global_seat_pool=False, new_ACK_wire=False,
        measured_physical_provider_values_available=False,
        wholephase_exposed_delta=None, whole_iteration_delta=None,
        iteration_requirement='Six verification positions plus drafter and commit/rollback; cannot multiply this synthetic phase into a token rate.',
        RTL_build_admitted=False, physical_fit=False, fulltoken_rate=False, new_jobs=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('preserve immutable records')
    args.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')

#!/usr/bin/env python3
"""One rejected S81 split assessment, reusing the frozen selected phase ledger.

No allocator, inference, RTL execution, topology sweep or source-map replay.
The ledger selects worst alternatives under the OLD metric; it is a screening
schedule, not the actual expert trajectory or a proven critical path.
"""
import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

SPLIT = 'results/uarch/dsrom_s81_service_capacity_split_20261004/r1/'
GROUP = 'results/uarch/dsrom_s81_minimum_protected_group_20261004/model.json'
LINK = 'results/rtl/dsrom_1m_allmeasured_20261004/links.json'
COMPOSITION = 'results/rtl/dsrom_1m_allmeasured_20261004/composition.json'
PINS = ['tools/dsrom_s81_split_latency.py', SPLIT+'model.json', SPLIT+'transport_movements.jsonl.gz', GROUP,
        LINK, COMPOSITION, 'tools/dsrom_s81_service_capacity_split.py',
        'tools/runtime/dsrom/s81_minimum_su256.cpp',
        'tools/runtime/dsrom/s81_source_caller.cpp',
        'tools/dsrom_stage_program_join.py',
        'results/uarch/dsrom_baseline_link_clock_20261004/context_r1/model.json']


def message_cycles(size, fixed):
    if size < 0 or size % 4:
        raise ValueError('selected source extent must be nonnegative raw32')
    return fixed + (size + 63)//64 - 1 if size else 0


def assess(root):
    load = lambda p: json.loads((root/p).read_text())
    split, group, link, comp = [load(p) for p in
                              (SPLIT+'model.json', GROUP, LINK, COMPOSITION)]
    hop = link['hop']
    fixed = hop['total_cycles'] - (hop['payload_flits'] - 1)
    assert fixed == hop['first_flit_cycles'] + hop['wire_stage_cycles'] == 269
    assert message_cycles(hop['payload_B'], fixed) == hop['total_cycles']
    ns_per_edge = 1e9/link['clock_hz']
    read_ns = group['read_service']['latency_ns_candidate']
    publish_ns = group['service']['accepted_head_to_captured_retirement_ns_bound']
    layers = defaultdict(lambda: defaultdict(float))
    aggregate = defaultdict(int)
    nodes = []
    with gzip.open(root/(SPLIT+'transport_movements.jsonl.gz'), 'rt') as f:
        for line in f:
            row = json.loads(line)
            layer = int(row['node'].split('.')[0][1:])
            ranks = [defaultdict(float) for _ in range(4)]
            for t in row['transfers']:
                r = ranks[t['rank']]
                h = t['hops_each_way']
                old_h = abs(2*layer-t['source_stage'])
                ib, ob = t['input_bytes'], t['output_bytes']
                cycles = message_cycles(ib, fixed)+message_cycles(ob, fixed)
                serial = max((ib+63)//64-1, 0)+max((ob+63)//64-1, 0)
                starts = int(ib > 0)+int(ob > 0)
                r['split_packet_ns'] += h*cycles*ns_per_edge
                r['same_alias_original_packet_ns'] += old_h*cycles*ns_per_edge
                r['split_first_arrival_ns'] += h*starts*fixed*ns_per_edge
                r['split_serialization_ns'] += h*serial*ns_per_edge
                r['hop_payload_bytes'] += h*(ib+ob)
                # Extent demand for one input copy and one result copy per
                # frozen fragment. NOT claimed emitted PCs or runtime captures.
                # Four operands alias: unique words, not 4x prefetch demand.
                words = (ib+ob)//4
                aggregate['all_TP4_copy_unique_prefetch_reads'] += words
                aggregate['all_TP4_copy_scalar_writes_and_matching_ACKs'] += words
                aggregate['all_TP4_fragment_input_and_output_bytes_once'] += ib+ob
                r['copy_unique_read_words'] += words
                r['copy_scalar_publications'] += words
                r['copy_prefetch_service_ns'] += words*read_ns
                r['copy_publication_retirement_ns'] += words*publish_ns
                if old_h:
                    r['same_alias_original_copy_ports_ns'] += words*(read_ns+publish_ns)
                if old_h == 0:
                    r['new_crosshome_copy_words'] += words
            # TP4 ranks concurrent, fragments on each rank serial. Max AFTER
            # summing serial demands, never sum four ranks or max each resource.
            split_rank = max(ranks, key=lambda r:r['split_packet_ns'])
            demand_rank = max(ranks, key=lambda r:
                r['split_packet_ns']+r['copy_prefetch_service_ns']+
                r['copy_publication_retirement_ns'])
            n = {'node': row['node'], 'frozen_alias': row['worst_alias'],
                 'old_reported_split_ns': row['transport_ns'],
                 'old_reported_baseline_ns': row['prior_transport_ns'],
                 'split_packet_ns': split_rank['split_packet_ns'],
                 'same_alias_original_packet_ns': max(
                     r['same_alias_original_packet_ns'] for r in ranks),
                 'split_first_arrival_ns': split_rank['split_first_arrival_ns'],
                 'split_serialization_ns': split_rank['split_serialization_ns'],
                 'conditional_same_alias_original_packet_plus_copy_ports_ns': max(
                     r['same_alias_original_packet_ns']+
                     r['same_alias_original_copy_ports_ns'] for r in ranks),
                 'copy_extent_port_demand': dict(demand_rank),
                 'conditional_serial_packet_plus_copy_ports_ns':
                     demand_rank['split_packet_ns']+
                     demand_rank['copy_prefetch_service_ns']+
                     demand_rank['copy_publication_retirement_ns']}
            nodes.append(n)
            for k in ('split_packet_ns', 'same_alias_original_packet_ns',
                      'split_first_arrival_ns', 'split_serialization_ns',
                      'conditional_same_alias_original_packet_plus_copy_ports_ns',
                      'conditional_serial_packet_plus_copy_ports_ns'):
                layers[layer][k] += n[k]
            for k in ('copy_unique_read_words', 'copy_scalar_publications',
                      'copy_prefetch_service_ns', 'copy_publication_retirement_ns',
                      'new_crosshome_copy_words'):
                layers[layer][k] += demand_rank[k]
    totals = {k: sum(l[k] for l in layers.values()) for k in next(iter(layers.values()))}
    old_split = sum(n['old_reported_split_ns'] for n in nodes)
    old_original = sum(n['old_reported_baseline_ns'] for n in nodes)
    totals['old_reported_split_ns'] = old_split
    totals['old_reported_original_ns'] = old_original
    totals['corrected_same_alias_split_delta_ns'] = (
        totals['split_packet_ns']-totals['same_alias_original_packet_ns'])
    totals['conditional_same_alias_packet_plus_copy_ports_delta_ns'] = (
        totals['conditional_serial_packet_plus_copy_ports_ns']-
        totals['conditional_same_alias_original_packet_plus_copy_ports_ns'])
    assert abs(totals['split_packet_ns']-totals['split_first_arrival_ns']-
               totals['split_serialization_ns']) < 1e-6
    return {
        'schema': 'opentallas.S81.single_split_latency_assessment.v1',
        'verdict': 'REJECT_SPLIT_AS_SUBMITTED', 'adopted': False,
        'executable_homes': False, 'headline_token_ns': None,
        'measured_full_token_rate': None, 'default_enabled': False,
        'scope': '40 layer field-phase frozen screening ledger; excludes HEAD, embedding, nonfield arithmetic and actual dynamic expert selection',
        'source_pins': {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in PINS},
        'link': {'bytes_per_edge': 64, 'clock_hz_target': link['clock_hz'],
                 'endpoint_GBps_target': 76.8, 'measured_message_bytes': hop['payload_B'],
                 'measured_message_cycles': hop['total_cycles'],
                 'first_arrival_cycles': fixed,
                 'formula': 'h * (269 + ceil(bytes/64) - 1) per nonempty direction; store-and-forward, no cut-through credit',
                 'extrapolated_size_and_multihop_not_measured': True,
                 'clock_context_SS_FF_qualified': False,
                 'credit_ports': 'one 64B forward flit/edge, positive reverse credit; 512 credits, measured no stalls for original641-flit message only',
                 'global_ACK_reverse_extra_ns': None},
        'calendar': 'sequential source groups/fragments; before-field copy must publish before field GO; after-field copy must publish before next consumer; TP4 max not sum; no overlap credited',
        'totals': totals, 'layers': {str(k):dict(v) for k,v in sorted(layers.items())},
        'aggregate_port_demand_NOT_summed_as_latency': dict(aggregate),
        'native_copy': {
            'operator': 'existing SU256 M1_BYP, no arithmetic reorder',
            'compiler_API': 'Popper emit_native_transfer(source_offer,source_node,destination_offer,program_words,srcScalar,dstScalar,N); packed native SU + END, writer=9+actual entry, source producer/output extent checked',
            'extent_scope': 'one input/output copy per frozen remote fragment; demand projection only until Popper emitted program PCs/extents are supplied; input reuse cannot be credited without actual leases/calendar',
            'A_B_C_D': 'same source span, set-deduplicated ONE prefetch per unique word',
            'source_port': 'one held raw32 read_word, span lease through captured response and GO',
            'destination_port': 'one held scalar offer until SAME visible ACK, then next word; no 128-group wide-port credit',
            'selected_capture_owner': 'native SU publication path plus Nash native_copy_visible; NO second OutputBatch.capture and NO extra source reread charged',
            'conditional_prefetch_ns_per_word': read_ns,
            'conditional_empty_head_publication_to_retirement_ns_per_word': publish_ns,
            'bank_service_II_ns_NOT_added_again': group['service']['bank_service_II_ns'],
            'includes': 'publication charge includes modeled all6copy RMW/postverify, counted return and reverse-release; these edges are not re-added as a separate ACK',
            'excludes': 'native bypass cycles, GO/END/CDC, reader exclusion/contention, occupied-head delay, actual remote wholephase reverse/drain; none assigned zero',
            'native_bypass_measured_ns': None, 'actual_emitted_copy_extent_manifest': None,
            'model_clock_qualified': False,
            'physical_field_side_copy_source_or_VM_owner_bound': False,
            'packet_bytes_charged_once': True,
            'port_time_is_not_extra_packet_bytes': True,
            'conditional_sum_is_neither_measured_token_nor_proven_bound': True},
        'headline_comparison': {
            'existing_fused_component_calendar_us': comp['AR_us'],
            'existing_fused_component_rate_tok_s': comp['AR_tok_s'],
            'same_scope_addition_permitted': False,
            'reason': '725.057us composes fused measured primitive graph, stage hops/VM/gather already present; literal field-dispatch ledger and SU restore copies are not the same bound source/calendar. Adding either entire transport envelope double-counts existing work.',
            'conclusion': 'old7.798912ms does not establish measured headline failure: it double-counted serialization and is a conservative sequential frozen phase schedule. The sub-ms composition is not complete-source/signed-off evidence either. Current scalar-copy caller cannot inherit its fused parallelism without a real dependency/port join.'},
        'existing_component_service_evidence_NOT_readded': {
            'critical_path_us_by_class': comp['critical_path_us_by_class'],
            'head_lm_us': comp['info']['head']['lm_head_us'],
            'head_argmax_drain_us': comp['info']['head']['argmax_drain_us'],
            'embed_us': comp['info']['embed']['us'],
            'fused_window_selected_us_per_layer': comp['info']['window']['per_layer_us'],
            'asbuilt_window_us_per_layer': comp['info']['window']['asbuilt_c1_us'],
            'slow_fast_CDC_us_on_fused_path': comp['cdc_on_path_us'],
            'actual_complete_source_native_service_calendar': None,
            'note': 'measured component durations at target clocks plus vendor budgets; not measured full source token or clock signoff; require actual scope/operand/port join before reuse'},
        'capacity': split['capacity_screen'],
        'missing_service_durations': ['native M1_BYP exact extents and measured complete GO-to-idle service',
            'actual destination placement/banking and all-copy/remote reader retirement',
            'nonfield ordered source program native services and selected expert phases',
            'full HEAD/embedding/context and bootstrap source costs'],
        'decision': 'No adoption: corrected same-alias packet screening still increases exposed serial work; native copy port demand is substantial and unhidden. Field screen misses2percent budget by0.840104mm2 before changed overlays, actual field-side VM/publication ownership and SS/FF clocks remain unqualified. Do not generate executable homes or claim a new headline. No rescue sweep.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = assess(a.root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'verdict': result['verdict'], 'totals': result['totals']}))

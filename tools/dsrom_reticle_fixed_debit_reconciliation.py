#!/usr/bin/env python3
"""Disjoint accounting audit; no floorplan, allocator, rate or hardware admission."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002'


def union_area(rectangles):
    """Exact integer-DBU union, including nested/overlapping rectangles."""
    if any(len(r) != 4 or r[0] >= r[2] or r[1] >= r[3] for r in rectangles):
        raise ValueError('invalid rectangle')
    xs = sorted({x for r in rectangles for x in (r[0], r[2])})
    total = 0
    for a, b in zip(xs, xs[1:]):
        intervals = sorted((r[1], r[3]) for r in rectangles if r[0] < b and r[2] > a)
        end = None
        length = 0
        for lo, hi in intervals:
            if end is None or lo > end:
                length += hi - lo
            elif hi > end:
                length += hi - end
            end = max(hi, end) if end is not None else hi
        total += (b - a) * length
    return total


def budget_branch(field, residual, service_union, extra_exclusions, extra_hardware):
    """Positive-cost accounting branch; PASS is necessary area only, never fit."""
    if any(v < 0 for v in (field, residual, service_union, extra_exclusions, extra_hardware)):
        raise ValueError('negative charge or implicit credit')
    total = field + residual + service_union + extra_exclusions + extra_hardware
    return dict(total_mm2=total, margin_mm2=858 - total,
                area_condition_pass=total <= 858, physical_fit_proven=False,
                build_admitted=False)


def parallel_successor(ledger, compiled):
    """ONE bijective physical sharding proposal, no allocator or depth sweep."""
    mapping = [dict(source_site=g, shard=g // 2048, local_site=g % 2048,
                    source_return_region=g // 32,
                    local_return_region=(g % 2048) // 32) for g in range(4096)]
    bf = {i * 4096 // 724 for i in range(724)}
    if bf != set(compiled['BF_DUAL_site_IDs']):
        raise ValueError('actual corrected622 BF mask mismatch')
    active = set(compiled['weight_active_site_IDs'])
    padding = set(compiled['padding_site_IDs'])
    if active & padding or active | padding != set(range(4096)):
        raise ValueError('actual compiled padding partition mismatch')
    local_bf = {i * 2048 // 362 for i in range(362)}
    for shard in (0, 1):
        if {g % 2048 for g in bf if g // 2048 == shard} != local_bf:
            raise ValueError('BF dual compatibility mask changed')
    for region in range(128):
        if len({mapping[g]['shard'] for g in range(32*region, 32*(region+1))}) != 1:
            raise ValueError('source ordered return region cut')
    half = ledger['composed_priced_field_terms'] / 2
    fixed = ledger['inherited_service_routes_clockPG_debit']
    residual = ledger['earlier_unidentified_native_residual_proxy_47_208']['mm2']
    total = half + fixed + residual
    return dict(candidate_id='DS4096-TP4-S58-PAR2-NP2048',
        status='ONE_PROPOSED_PARALLEL_OWNERSHIP_SUCCESSOR_NOT_ADOPTED',
        parent_candidate='DS4096-TP4-S58-PAIR1',
        serial_stage_owners=58, logical_TP_ranks=4, physical_shards_per_rank_owner=2,
        layer_dies_before=232, layer_dies_after=464,
        total_with_unchanged44_other_dies_before=276,
        total_with_unchanged44_other_dies_after=508,
        other44_die_fit_and_native_head_not_qualified=True,
        source_site_mapping=mapping,
        ordered_return_regions_per_shard=64, logical_return_leaves_per_shard=4096,
        source_reduction_region_cut_count=0, reduction_tree_depth_unchanged=6,
        local_compiled_NP=2048, local_NBF=362, local_q_sites=1686,
        weight_macro_rows=4096, weight_macros_per_complete_pair=4,
        weight_macros_per_shard=8192, aggregate_weight_macros_per_old_owner=16384,
        aggregate_weight_bits_per_old_owner=16384*4096*274,
        aggregate_weight_bits_unchanged=True, aggregate_adjacent_compute_unchanged=True,
        arithmetic_intensity_unchanged=True,
        actual_622_shard_site_census=[dict(shard=s,
            active_pairs=sum(g//2048 == s for g in active),
            padding_q_pairs=sum(g//2048 == s for g in padding),
            compiled_q_sites=1686, compiled_BF_dual_sites=362) for s in (0,1)],
        padding='All721 actual622 padding IDs retained through the bijection, not rounded or dropped; no repacking.',
        PHW=10, cfg72_macros_per_shard=7*2048,
        cfg_bits_per_shard=7*2048*4096*72,
        uniform_cfg_physical_storage_bits_per_rank_owner=2*7*2048*4096*72,
        uniform_cfg_logical_payload_bits_per_rank_owner=4096*1024*25*48,
        field_terms_per_shard_mm2=half,
        return_bits_per_shard=69771008//2,
        return_FF50_per_shard_mm2=ledger['declared_return_FF50_proxy']/2,
        return_topology='Same32pair/root regions and source-root order; R64 per shard, RD64/ROOTD128 retained. Source R128 wrapper adaptation unimplemented.',
        cfg_and_return_half_scaling_is_structural_model_not_characterized_macro=True,
        full_inherited_fixed_debit_retained_per_shard_mm2=fixed,
        full47p208_residual_retained_per_shard_mm2=residual,
        conservative_priced_per_shard_mm2=total,
        per_shard_margin_for_extra_IO_link_adapter_hardware_mm2=858-total,
        added_two_shard_fixed_and_residual_per_old_owner_mm2=fixed+residual,
        fixed_services_replicated_not_silently_shared=True,
        physically_packable_or_routable=False,
        unchanged_source_issue_work_cycles=True,
        added_serial_stage_hops=0, added_TP_collective_tree_levels=0,
        added_intraowner_boundary=True,
        boundary=dict(remote_roots=64, bits_per_source_root_result=69,
            unbackpressured_remote_result_port_width_bits_per_stream_cycle=64*69,
            throughput_not_assumed_equal_port_width=True,
            activation_source_cut_widths_bits=[549,1616],
            activation_widths_are_source_interface_screens_not_chosen_link_lanes=True,
            local_cfg72_arrays_generate_distinct48bit_words=True,
            mirrored_key_tables_and_delivery_fence_adapter_unpriced=True,
            no_full_cfg_words_free_broadcast=True,
            remote_root_tag_order_generation_lease_and_fault_drain_required=True),
        critical_path=dict(
            original='max(all original source-region completions) -> source-root consumer visibility',
            successor='max(local-region ready, remote activation accept + remote native issue/return + remote transport/visibility) -> same ordered consumer',
            additional_exposed_cost='max(0, remote_visibility_deadline - original_consumer_deadline) + extra acceptance/fence stalls; per actual source call and shared resource',
            no_single_token_loss_proven=False,
            no_added_serial_stage_hops_does_not_imply_zero_latency=True,
            nonoverlapped_boundary_sensitivity_ns=[100,200,500],
            sensitivity_us_if_all1149_layer_weight_calls_exposed=[1149*n/1000 for n in (100,200,500)],
            sensitivity_is_conditional_envelope_not_measured_rate=True,
            actual_remote_needed_call_count_and_positive_link_costs_unbound=True,
            current_source_issue_work_preserved_not_full_token_elapsed=True),
        exact_remaining_adapters=['Old R128 consumer ordered gather from twoR64 halves; backpressure or capture for nonbackpressured bursts',
            'Actual site/run membership and stage packets per d660 call including selected6EIDs; no new tensor packing',
            'Finite dual-die activation/config accept leases, generation/fault fence, remote root visible ACK',
            'HE/CROM/ECC physical sidecars routed to original homes; no duplicated weight/provider storage credit',
            'Per-shard fixed service/PHY/clockPG rectangles and extra link endpoint area with <=163.12mm2 margin',
            'Current accepted-return workload and polynomial kernel workspace/traffic; no32MiB cacheless free recompute'],
        build_admitted=False, performance_adopted=False)


def build():
    pins = []
    def load(path):
        b = path.read_bytes()
        pins.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(b).hexdigest()))
        return json.loads(b)
    manifest = load(OUT / 'inputs/manifest.json')
    for row in manifest:
        b = (OUT / 'inputs' / row['snapshot']).read_bytes()
        if hashlib.sha256(b).hexdigest() != row['sha256']:
            raise ValueError('frozen source identity mismatch')
    retained = load(OUT / 'inputs/hierarchical.json')
    reticle = load(OUT / 'inputs/reticle.json')
    src = (OUT / 'inputs/source_equations.py').read_text()
    # Bind the literal historical equation; do not execute its compiler/model.
    for term in ('footprint=416.76/7102',
                 'product_usable=.9*(9931*footprint-hub_loss-max(0,.125*814.982-(118.426-64.902)))'):
        if term not in src:
            raise ValueError('historical equation changed')
    p = OUT / 'inputs'
    service = load(p / 'service.json')['service']
    candidate = load(p / 'candidate.json')
    ledger = load(p / 'compiled_budget.json')['exact_once_area_ledger_mm2']
    current = load(p / 'current_address_verdict.json')
    load(p / 'owner_manifest.json')
    load(p / 'address_manifest.json')
    compiled = load(p / 'owner_readback.json')['compiled_field']

    field = 9931 * (416.76 / 7102)
    hub = retained['current_product_capacity_sensitivity']['rows'][0]['baseline_usable_mm2']
    charge = .125 * 814.982 - (118.426 - 64.902)
    hub_loss = field - charge - hub / .9
    residual_displacement = reticle['constrained_alternative']['residual_field_debit_mm2']
    corrected_corridors = reticle['constrained_alternative']['usable_field_mm2'] - (858 - ledger['inherited_service_routes_clockPG_debit'])
    unfactored = field - hub_loss - charge - residual_displacement
    decomposition = dict(
        complement_of_legacy_9931_slot_field=858 - field,
        inherited_C_rotate_hub_replacement=hub_loss,
        old_12p5_overhead_net_of_ring_credit=charge,
        net_new_hub_corridor_displacement_after_outline_growth=residual_displacement,
        historical_10pct_slot_fill_loss=.1 * unfactored,
        corrected_bidirectional_corridor=corrected_corridors)
    fixed = sum(decomposition.values())
    if abs(fixed - ledger['inherited_service_routes_clockPG_debit']) > 1e-9:
        raise ValueError('inherited complement failed exact reproduction')

    rects = service['rectangles']
    bounds = [r['bbox_DBU'] for r in rects]
    width, height = service['die_DBU']
    if any(not (0 <= x <= xx <= width and 0 <= y <= yy <= height) for x, y, xx, yy in bounds):
        raise ValueError('source rectangle outside envelope')
    scale = service['DBU_per_um'] ** 2 * 1e6
    raw = sum((r[2] - r[0]) * (r[3] - r[1]) for r in bounds) / scale
    union = union_area(bounds) / scale
    if abs(raw - sum(r['area_mm2'] for r in rects)) > 1e-9:
        raise ValueError('source rectangle area mismatch')
    by_class = {'clear_route_only': [], 'provider_or_combined': []}
    for r in rects:
        by_class['clear_route_only' if 'CLEAR_ROUTE_BAND' in r['name'] else 'provider_or_combined'].append(r)
    field_cost = ledger['composed_priced_field_terms']
    unknown_residual = ledger['earlier_unidentified_native_residual_proxy_47_208']['mm2']
    remaining_fixed = fixed - union
    extra_limit = 858 - field_cost - unknown_residual - union
    conservative = budget_branch(field_cost, unknown_residual, union, remaining_fixed, 0)
    if abs(conservative['total_mm2'] - ledger['conservative_no_containment_credit_die_total']) > 1e-9:
        raise ValueError('old failure changed')
    source_work = current['partial_source_work']
    return dict(
        schema='opentallas.dsrom.reticle-fixed-debit-disjoint-audit.v1',
        candidate_id='DS4096-TP4-S58-PAIR1', compiled_NP=4096, NBF=724,
        stages=58, TP=4, weight_active_pairs=3375, charged_padding_q_pairs=721,
        source_pins=pins, historical_source_manifest=manifest,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fixed_debit_algebra_mm2=decomposition,
        decomposition_is_accounting_not_disjoint_physical_regions=True,
        source_service_rectangles=rects,
        rectangle_union=dict(sum_mm2=raw, union_mm2=union, duplicate_overlap_mm2=raw-union,
            groups={k:dict(names=[r['name'] for r in rs], area_mm2=sum(r['area_mm2'] for r in rs)) for k, rs in by_class.items()},
            geometrically_contained=True, geometry_source_is_reservation_not_routed_provider=True,
            unknown_outside_rectangle_area_mm2=858-union,
            outside_rectangle_area_is_free_packable=False),
        containment=dict(proven_removable_double_count_mm2=raw-union,
            named_service_90p446_already_inside_fixed_debit=True,
            named_service_proxy_mm2=candidate['area_and_service_reserve']['source_named_service_proxy_mm2'],
            rectangles_replacing_named_service_proxy_not_an_additional_debit=True,
            unmapped_inherited_complement_after_rectangle_union_mm2=remaining_fixed,
            unmapped_is_not_verified_required_exclusion_area=True,
            all_current_charges_retained=True,
            native_47p208_residual_mm2=unknown_residual,
            native_residual_status='Difference of analytical payload-density plus old element-strip reservation and catalog active frames; no provider/instance containment proof. Retained, not an identified new block.'),
        composed_conservative_branch=conservative,
        corrected_4096_branch_contract=dict(
            priced_field_mm2=field_cost, full_return_FF50_mm2=ledger['declared_return_FF50_proxy'],
            cfg_body_and_mux_mm2=ledger['config_prospective_body_plus_local_mux'],
            max_extra_exclusions_plus_unpriced_hardware_mm2=extra_limit,
            required_reconciliation_vs_inherited_mm2=remaining_fixed-extra_limit,
            conditional_if_native_residual_fully_source_contained_limit_mm2=extra_limit+unknown_residual,
            explicit_equation='458.81144120512 + 47.208013178655904 + 131.24731428864 + E + H <= 858',
            E='Unique outside-service exclusions: IO/PHY, halos, unfillable strips, clock/PG/decap/hold/DFT. No double charge for bands within rectangles.',
            H='Additional unpriced native cfg/ECC/HE/CROM/head/guard hardware, strictly nonnegative.',
            rectangle_provider_union_and_E_field_placement_must_be_disjoint=True,
            actual_E_and_H_received=False, current_branch_selected=False),
        route_policy=dict(actual_PDN_vias_clock_shapes_bound=False,
            reserve_50pct_is_policy_not_measured_occupancy=True,
            corridor_margin_tracks={r['name']:r['margin_tracks'] for r in service['corridors']},
            no_discount_from_margin_or_free_whitespace=True),
        coordinated_decision=dict(
            next_action='Bind unique outside-service exclusion regions and contained instance IDs to the E+H threshold for the same compiled4096/S58 candidate before any successor.',
            providers={'geometry_owner':'Exact rectangle/halo/IO/clockPG exclusion union and remaining legal complete-pair row packing; clock/via occupied shapes or retained policy masks.',
                       'allocator_owner_Nash':'Keep corrected622/d660 full-map immutable; only after geometry fails its bound, recompile ONE power-of-two smaller NP with complete source row-region ownership, BF dual sites, HE/CROM/ECC reservations and all model capacity.',
                       'calendar_owner':'Bind d660 source steps to positive finite cfg/root/service/shared-resource costs; price only actual accepted ownership crossings plus serialization/replicated hubs.'},
            successor_selected=False, successor_count_or_depth_sweep=False,
            successor_trigger='Verified exclusion+unpriced hardware exceeds220.7332313275841mm2 or same-candidate legal packing fails. A conservative complement alone does not trigger a die-count decision.',
            topology='FixedTP4, source ordered reductions, fixed4096 depth/2macros per logical slot; aggregate model weights/compute retained.',
            split_alternative='Existing stage ownership first. Added spatial dies are not automatically serial hops; TP change needs separate exact reduction proof.'),
        single_parallel_successor=parallel_successor(ledger, compiled),
        calendar=dict(source_work=source_work, current_missing_terms=current['missing_terms'],
            native_failures=current['native_failures'], full_token_calendar_complete=False,
            geometry_reconciliation_only_added_stage_hops=0,
            geometry_reconciliation_is_no_latency_credit=True,
            successor_latency_requires_actual_owner_crossing_graph=True),
        verdict='RETAIN_CONSERVATIVE_FAIL_RECONCILE_FIXED_COMPLEMENT_BEFORE_SUCCESSOR',
        physical_admitted=False, build_admitted=False, rate_adopted=False,
        original_failures_unchanged=True, RTL_PR_or_remote_jobs=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT / 'model-r4.json')
    args = parser.parse_args()
    data = (json.dumps(build(), indent=2, sort_keys=True) + '\n').encode()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists() and args.out.read_bytes() != data:
        raise ValueError('immutable verdict exists; use a new path')
    args.out.write_bytes(data)
    print(json.dumps(dict(out=str(args.out), sha256=hashlib.sha256(data).hexdigest())))


if __name__ == '__main__':
    main()

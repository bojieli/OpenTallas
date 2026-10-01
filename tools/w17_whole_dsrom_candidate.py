#!/usr/bin/env python3
"""Incremental whole DSROM sizing authority; never a hardware admission."""
import argparse
import hashlib
import json
import subprocess
from decimal import Decimal as D
from pathlib import Path

PINS = {
    'geometry_search': ('e61a5a1ee', 'results/quality/w16_w17_geometry_search_20261001/search.json'),
    'dispatch': ('c8468d3f7', 'results/quality/w16_w17_dispatch_alternatives_20261001/comparison.json'),
    'crom_intake': ('075b72af6', 'results/quality/w16_dsrom_crom_writer_intake_20261001/receipt.json'),
    'engram_actual_beats': ('9b5ca5767', 'results/quality/w16_engram_eight_scale_binding_20261001/spec.json'),
    'power_all_arcs': ('e79394b1c', 'results/uarch/w10_q_power_envelope_r1/power.json'),
    'embedding_head': ('57dd0bedd', 'results/quality/w16_dsrom_embedding_head_home_20261001/contract.json'),
    'codec': ('93431e3c5', 'results/quality/w16_dsrom_nonexpert_codec_views_20261001/contract.json'),
}

def build():
    pins, records = {}, {}
    for name, (commit, path) in PINS.items():
        full = subprocess.check_output(['git', 'rev-parse', commit], text=True).strip()
        raw = subprocess.check_output(['git', 'show', full + ':' + path])
        records[name] = json.loads(raw)
        pins[name] = dict(commit=full, path=path, sha256=hashlib.sha256(raw).hexdigest())
    search = records['geometry_search']
    q = next(r for r in search['candidates'] if r['q_pairs'] == 1024)
    dispatch = records['dispatch']
    words = 32320 * 5120 // 16
    assert words == 2525 * 4096
    # Coordination-only compatible-arc estimates: not silently promoted to
    # immutable source evidence. Full static includes Q root/leak, BF root/
    # leak, hub and CROM; Q root must NOT be added a second time.
    static = D('131.624205916')
    phases = []
    for family, active in [('w1', 832), ('w3', 832), ('w2', 1024)]:
        leaf = D('.40664966772') * active
        clock_static = static + leaf
        root_data = D('3.03343') * 1024
        leaf_data = D('4.94096') * active
        wire = D('37.1537') * 1024
        phases.append(dict(family=family, awake_q_pairs=active,
            q_root_clock_W=str(D('.01671097834') * 1024),
            q_leaf_clock_W=str(leaf), q_leak_W=str(D('.008407424728304') * 1024),
            BF_root_clock_W='31.7540', BF_leak_W='9.03146',
            hub_clock_leak_IO_W='59.84105', CROM_always_clock_W='5.23457',
            combined_static_reservation_W=str(static),
            clock_plus_static_W=str(clock_static),
            clock_plus_static_margin_W=str(D('474.56') - clock_static),
            root_data_conservative_W=str(root_data), leaf_data_conservative_W=str(leaf_data),
            unresolved_wire_ceiling_W=str(wire),
            provisional_Q_data_plus_clock_static_W=str(clock_static + root_data + leaf_data + wire),
            BF_hub_nonexpert_data_W=None,
            qualification='UNQUALIFIED_COORDINATION_VALUES_PENDING_IMMUTABLE_PHASE_RECEIPT',
            interpretation='Instantaneous allocation, not measured power or steady thermal refutation. No inactive frontend isolation or duty averaging credit.'))
    alternatives = [r for r in dispatch['candidates'] if r['policy'] == 'compact_stage_activation_reuse']
    return dict(schema='opentallas.w17.whole-dsrom-incremental-candidate.v1',
        source_pins=pins, scope='Concrete partial whole-design point; unbound homes/costs prohibit admission.',
        candidate=dict(q_pairs_per_expert_die=1024, BF_pairs_reserved_per_expert_die=1024,
            expert_integer=q, q_mask=q['q_mask'], BF_mask=q['BF_mask'],
            expert_dies=724, head_dies=4, embedding_dies=4,
            allocated_subproblem_die_count=732, complete_product_die_count=None,
            count_interpretation='724 expert dies plus eight separate proposed vocabulary homes; nonexpert/Engram/HC/state homes not included. No historical208-die transfer.'),
        vocabulary_homes=dict(
            combined_one_BF_field_excess_words=2 * words - 1024 * 2 * 8192,
            head=dict(homes=4, vocabulary_rows_per_home=32320, K=5120,
                physical_274bit_words_per_home=words, BF_pairs_per_home=1024,
                physical_4096_macros_per_pair=4, logical_8192_mates_per_pair=2,
                capacity_words_per_home=1024 * 2 * 8192, proposed_output_tiles=[16384, 15936],
                output='FP32 logits, full K per vocabulary quarter; global lowest-ID argmax',
                image_layout_exactness_and_spatial_fit=False, field_latency_cycles=None),
            embedding=dict(homes=4, complete_table_copies=1, physical_banks_per_home=2525,
                bank_depth=4096, bank_width_bits=274, physical_words_per_home=words,
                owner='token // 32320', local_row='token % 32320',
                word_address='local_row * 320 + wordslot', bank='word_address // 4096',
                bank_row='word_address % 4096', address_bits=24,
                proposed_row_read_issue_cycles=320, delivered_row_bytes=10240,
                proposed_ports='One registered 274-bit bank word per streaming cycle; local capture and registered selection required.',
                owner_broadcast_CDC_consumer_latency_cycles=None, mapped_fit=False),
            qualification='INTEGER_STORAGE_PROPOSAL_ONLY; logical8192 mate equals two4096 parity banks, not doubled capacity.'),
        constants=dict(actual_writer_words_per_rank=508800, logical_capacity_words=524288,
            actual_writer_intake_pass=True, mandatory_generated_Engram_product_words=40960,
            resulting_required_words=549760, aperture_excess_words=25472,
            generated_product_provenance='Owner report: G.mul(q_weight,k_weight), 20480 FP32 coefficients at each of L1/L14; source pair completeness pending. No new checkpoint read authorized.',
            proposed_three_64bit_words_per_274bit_container=183254,
            selected_minimal_home=dict(homes=4, rank_local_complete_image=True,
                logical_word_address_bits=20, previous_logical_address_bits=19,
                containers_needed=183254, physical_4096x274_banks=45,
                physical_container_capacity=184320, logical_64bit_word_capacity=552960,
                spare_logical_words=3200, logical_to_container='address // 3',
                lane_select='address % 3', bank='container // 4096', bank_row='container % 4096',
                useful_bits_per_container=192, zero_padding_bits=82,
                scalar_read_ports=1, read_issue_words_per_fast_cycle=1,
                simultaneous_unrelated_reads=False,
                arbitration='Serialize all rank-local constant consumers in instruction order; hold response lease until consumer acceptance.',
                read_capture_and_registered_select_cycles=None,
                capacity_address_proof=True, producer_change_authorized=False,
                contextual_SS_FF_ports_area_power=False),
            physical_home_ports_arbitration_and_unpack='Selected one-port rank-local packed home above; latency/physical implementation remains unqualified.',
            qualification='Current actual images verified; complete operands and physical service NOT qualified.'),
        engram=dict(actual_eight_scale_spec_pin=pins['engram_actual_beats'],
            immutable_table_stored_bytes=202758032400, auxiliary_projection_constant_bytes=315043840,
            row_codes_bytes=256, row_scale_bytes=8, lookups_per_token=48,
            stored_lookup_bytes=12672, decoded_BF16_lookup_bytes=24576,
            four_projection_view_delivery_bytes=98304,
            immutable_ROM_or_HBM_home=None, TP_table_replication=None,
            lookup_route_ports_and_latency=None,
            decoder='Matching exponent on every beat; unchanged beat0 scale latch is a retained exactness failure.',
            qualification='Actual retained row software binding is not physical decoder/lookup admission.'),
        power=dict(per_die_budget_W='474.56', committed_all_arc_Q_only_W=q['conditional_q_construction_power_W'],
            all_arc_verdict='REJECTED_CONSERVATIVE_ALLOCATION_NOT_PHYSICAL_IMPOSSIBILITY',
            phase_rows=phases, compatible_arc_values_source_pinned=False,
            no_stop_credit_reason='Current inactive frontend captures xs inputs; go/act gates leaf, not root sampling.',
            next_minimum_correction='Source-pinned phase envelope with BF/hub/nonexpert data and source-proven isolation or reduced active-pair schedule, priced with atomic segment/config/refill/wake costs. No free 7-pair batching.'),
        dispatch=dict(route=dispatch['route_model'], CDC=dispatch['CDC_model'],
            baseline_serialization_only_us=440, alternatives=alternatives,
            width_units='Bits per rank per source cycle; four separate TP4 replicas. Both directions and control tracks charged.',
            credits='Retain packet/activation until actual final consumer and reverse CDC; last serializer byte is not release.',
            full_token_latency_cycles=None, performance_qualified=False),
        unresolved_owner_contracts=dict(Confucius='Immutable compatible-clock/data phase ledger, BF/hub/nonexpert activity and physical power/IR.',
            Fermat='CROM physical banks/read ports, full nonexpert field placement and constant consumer conflicts.',
            Avicenna='Engram physical home demand and source-complete generated constant operands; no new checkpoint reads.',
            Godel='q1024 stride96 template replay, epoch/peer credits and strong CKV/drain/backend visibility completion.'),
        mandatory_correctness='CKV writes require connected WE, actual CWL+BURST backend visibility and final consumer acknowledgement; fixes are mandatory baseline, not optional1percent optimization.',
        verdict='REJECTED_FOR_ADMISSION_UNDER_AVAILABLE_BOUNDS',
        complete_architecture_admission=False, engine_RTL_build_ready=False,
        physical_admission=False, headline_rate=None, jobs_launched=0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    Path(args.out).write_text(json.dumps(build(), indent=2, sort_keys=True) + '\n')

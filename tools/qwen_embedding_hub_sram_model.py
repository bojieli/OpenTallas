#!/usr/bin/env python3
"""Pre-RTL ingress sizing; arithmetic only, no synthesis/STA/geometry probe."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/arch/emb_hbm_20261008/takeover/hub_sram_model.json'
BASE = ROOT / 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2'
NAME = BASE.name

def main():
    macro = json.loads((BASE / f'{NAME}.json').read_text())
    scope_path = ROOT / 'results/arch/emb_hbm_20261008/takeover/terminal_routes_20261009/hub_util/scope.json'
    scope = json.loads(scope_path.read_text())
    area = macro['area']['macro_area_um2'] * 12
    halo = 2.16
    seat_area = 12 * (94.824 + 2 * halo) * (41.04 + 2 * halo)
    seats = []
    for link in range(4):
        for bank in range(3):
            x = 70.2 + bank * 127.224
            y = 100.44 + link * 73.44
            seats.append({'link': link, 'bank': bank, 'origin_um': [x, y],
                          'size_um': [94.824, 41.04], 'halo_um': halo,
                          'used_bits_per_word': [256, 256, 136][bank],
                          'orientation': 'R0'})
    paths = [scope_path, ROOT / 'rtl/physical/ot_qwen_die_cdc_ch.sv',
             ROOT / 'rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb.sv',
             ROOT / 'physical/qwen_die_masters/cfg/qfd_hub_emb.env',
             ROOT / 'physical/qwen_die_masters/mc/qfd_hub_emb/plain.sdc']
    paths += sorted(BASE.glob('*'))
    model = {
      'schema': 'opentallas.embedding_hub_sram_proposal.v1',
      'status': 'PRE_RTL_REVIEW_ONLY', 'parent_source': '8bfbb0bb0',
      'model_before_RTL': True, 'MAC_per_cycle': 0,
      'scope': 'Replace only four synchronous ingress ib[128][523] arrays; preserve AD8 async FIFO, OD8 output FIFO, XS8 skid and all other native logic.',
      'fault_evidence': scope,
      'inventory': {'links': 4, 'depth_per_link': 128, 'payload_bits': 523,
                    'original_payload_flop_bits': 4 * 128 * 523,
                    'secded_64_72_words_per_payload': 9,
                    'padded_data_bits': 576, 'encoded_bits': 648,
                    'useful_payload_bits_per_die': 267776,
                    'encoded_bits_per_die': 331776,
                    'physical_capacity_bits': 393216,
                    'unused_bits_per_macro_triplet': 120,
                    'macro_name': NAME, 'macros_per_link': 3, 'macros_per_die': 12},
      'bandwidth': {'per_link_useful_bits_per_edge': 523,
                    'per_link_SRAM_write_bits_per_edge': 648,
                    'per_link_SRAM_read_bits_per_edge': 648,
                    'per_link_physical_port_bytes_per_edge': 96,
                    'per_link_used_port_bytes_per_edge': 81,
                    'aggregate_useful_bits_per_edge': 2092,
                    'aggregate_physical_write_bytes_per_edge': 384,
                    'aggregate_physical_read_bytes_per_edge': 384,
                    'II_target_edges': 1,
                    'port_type': 'three concurrent 1R1W SRAMs/link, same wclk, no read/write port arbitration'},
      'latency': {'domain': 'fck0..3, actual833.333ps; source route770ps; uncertainties60/25ps unchanged',
        'baseline_edges': {'E0': 'capture ingress', 'E1': 'write ib', 'E2': 'pop ib into async FIFO and return credit'},
        'proposed_edges': {'E0': 'capture ingress and reserve one of128 logical capacity slots',
          'E1': 'capture nine parallel SECDED encodings', 'E2': 'write all three SRAM banks',
          'E3': 'earliest SRAM read issue, avoiding same-address read/write ambiguity',
          'E4': 'capture macro data and syndrome, reserving finite corrected-output capacity',
          'E5': 'correct/UE classify and actually accept into async FIFO; only then return upstream credit'},
        'added_wclk_edges': 3, 'added_first_word_ns': 2.499999,
        'added_credit_return_edges': 3,
        'existing_RTT_window_restart_edges': [117, 119],
        'proposed_no_extra_stall_window_restart_edges': [120, 122],
        'minimum_remaining_128_window_margin_edges': 6,
        'system_composition': 'Add3 fck edges to each traversed ingress. A response/fence traversing one ingress costs+2.5ns; do not multiply by four parallel links. Async phase/backpressure changes require measured gate.',
        'BOOT_END': 'Ordered behind all earlier ingress words; do not report drain/credit at SRAM read issue. Fence completes only after real downstream retirement and pre-existing gateway semantics.'},
      'finite_flow_control': {'capacity': 128,
        'rule': 'One logical occupancy reservation per accepted ingress word, including encoder pending, resident SRAM and read/decode pending; reservation released only at real async acceptance. No early credit and no 128+pipeline overbooking.',
        'encode_pending_slots': 1, 'read_decode_pending_minimum_slots': 2,
        'read_issue_rule': 'Reserve pending decode slot before read; stop when reserved pending slots unavailable. Maintain in-order issue and acceptance; no SRAM row reused while a read is pending.',
        'implementation_question': 'Two pending slots are minimum; actual registered async-ready stop latency must be measured and may require one additional plain holding slot. Any such slot is priced before RTL approval.',
        'controls': 'single plain pointers, counts, credits, valid flags; no control ECC/TMR/mirrors/authentication',
        'ECC_scope': 'actual SRAM payload including11 tagbits, only; nine independent SECDED64/72 lanes. CE corrected before async; UE sticky fault and no silent publication, with explicit credit/reset behavior to be gated.',
        'same_address': 'Issue read only for committed older row; no reliance on ambiguous macro same-address simultaneous read/write behavior.'},
      'placement_arithmetic': {'outline_um': [567.216, 567.216], 'core_area_um2': 316730,
        'macro_area_um2': area, 'halo_seat_area_um2': seat_area,
        'seats': seats, 'between_macro_gap_um': 32.4,
        'between_halos_channel_um': 28.08,
        'macro_region_extent_um': [70.2, 100.44, 419.472, 361.8],
        'geometric_nonoverlap_by_construction': True,
        'actual_placement_or_route_proof': False,
        'stdcell_budget_at55pct_after_macro_exclusion_um2': .55 * (316730 - area),
        'stdcell_budget_at55pct_after_halo_exclusion_um2': .55 * (316730 - seat_area),
        'minimum_net_stdcell_saving_without_halo_um2': 221043 - .55 * (316730 - area),
        'minimum_net_stdcell_saving_with_halo_um2': 221043 - .55 * (316730 - seat_area),
        'break_even_removed_area_per_original_payload_bit_um2': (221043 - .55 * (316730 - seat_area)) / 267776,
        'flop_proxy_only_um2_per_bit': .32,
        'removed_payload_flop_proxy_um2': 267776 * .32,
        'net_new_logic_allowance_at_proxy_with_halo_um2': 267776 * .32 - (221043 - .55 * (316730 - seat_area)),
        'new_register_proxy': {'per_link_encode_bits': 648, 'per_link_read_capture_bits': 1296,
          'per_link_syndrome_flags_bits': 144, 'per_link_plain_pending_hold_bits': 0,
          'total_bits': 8352, 'proxy_um2': 8352 * .32,
          'remaining_codec_control_buffer_allowance_um2_at_proxy': 267776*.32 - (221043-.55*(316730-seat_area)) - 8352*.32,
          'claim': 'Sizing allowance only; actual registered-ready latency and pending-slot implementation may change this inventory. No measured area saving.'},
        'claim': 'Seat arithmetic fits existing outline. Standard-cell saving, codec/control cost, pins, PDN, detailed route and timing are unmeasured; no adoption or die growth/removal credit.'},
      'pin_channels': {'macro_total_signal_pins': 819,
        'dynamic_pins_full_bank': 529, 'dynamic_pins_136bit_bank': 289,
        'dynamic_pins_per_link_triplet': 1347,
        'constants': 'write masks all ones for648 meaningful bits, spare repair configuration tied inactive, unused120 physical bits static; not runtime protected controls',
        'pin_view': 'M4 edge pins at96nm pitch; macro interior OBS M1-M4, route above on M5-M7 as allowed by hub',
        'cross_macro_edge_demand_upper_bound': 410,
        'edge_nominal_two_track_48nm_capacity': 427,
        'margin_tracks': 17,
        'edge_conservative_M4_only_capacity': 320,
        'edge_conservative_M4_plus_M6_capacity': 641,
        'escape_requirement': '410-pin edge does not meet75%-usable two-track singleM4 capacity320. Require actual M4→M6 escape vias for spare routing capacity; do not treat nominal427 as conservative pass.',
        'claim': 'Only local edge escape arithmetic, not a proved global channel. Align codec/capture cells next to each bank; avoid gathering all twelve819-pin interfaces into one channel. Preserve existing top-level hub pins.'},
      'macro_timing': {'claim_boundary': macro['claim_boundary'],
        'SS_clk_to_q_ps': macro['timing']['ss']['clk_to_q_ps'],
        'SS_min_period_ps': macro['timing']['ss']['min_period_ps'],
        'SS_setup_ps': macro['timing']['ss']['setup_ps'],
        'FF_hold_ps': macro['timing']['ff']['hold_ps'],
        'SS_nominal_remaining_capture_budget_ps_excluding_sink_setup_wire_skew': 833.333-60-macro['timing']['ss']['clk_to_q_ps'],
        'source770_remaining_capture_budget_ps_excluding_sink_setup_wire_skew': 770-60-macro['timing']['ss']['clk_to_q_ps'],
        'qualification': 'Macro minperiod alone does not close codec/hold or actual macro→capture path; all actuallib corners and own clk→q retained.'},
      'energy': {'TT_three_macro_read_fj_per_link_word': 3*macro['timing']['tt']['read_energy_fj'],
        'TT_three_macro_write_fj_per_link_word': 3*macro['timing']['tt']['write_energy_fj'],
        'TT_full_four_link_II1_macro_dynamic_w': 12*(macro['timing']['tt']['read_energy_fj']+macro['timing']['tt']['write_energy_fj'])*1.2e9*1e-15,
        'claim': 'Analytical macro-only access energy at all ports active each edge; excludes codec/control/clock tree/wires. No measured system power or energy gain.'},
      'review_gates': ['Claude approval before additive default-off RTL',
        'minimum one-link523bit exact gate: capacity128 burst, II1, credits, stalls, wrap/reset, tags and BOOT_END ordering',
        'actual SRAM CE correction/UE rejection and data/tag/order/early-credit mutants',
        'remote admitted postmap memory inventory and netstdarea saving versus threshold',
        'existing outline actual macro seats/pin escape/PDN/hub routing-layer check',
        'TT/FF closure with SS sensitivity and actual833.333ps/60ps/25ps budgets'],
      'inputs': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(model, indent=2) + '\n')
    print(OUT.relative_to(ROOT))

if __name__ == '__main__':
    main()

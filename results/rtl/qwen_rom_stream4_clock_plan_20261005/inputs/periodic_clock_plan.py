#!/usr/bin/env python3
"""Price one periodic-clock STREAM4 controller boundary before implementation.

This is a physical clock-plan successor, not a controller logic revision or
an enrollment of the simulation backend's shared arrays as hardware CDC.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import qwen_rom_runtime_pc_context as C
import uarch_model as U

ROOT = C.ROOT
BASE = ROOT / 'results/rtl/qwen_rom_stream4_clock_plan_20261005'


def fifo(name, replicas, width, depth, source, destination, pins, semantics):
    ptr = depth.bit_length()
    # Actual ot_async_fifo: four local pointer vectors, four synchronized
    # vectors, six online bits, two flags, four reset-conditioner bits.
    state = 8 * ptr + 12
    return {
        'name': name, 'replicas': replicas, 'payload_bits': width,
        'depth': depth, 'pointer_bits': ptr, 'source_domain': source,
        'destination_domain': destination, 'frontend_pins': pins,
        'semantics': semantics, 'storage_bits': replicas * width * depth,
        'control_state_bits': replicas * state,
        'storage_role': 'realization of existing logical ring; no duplicate backing ring',
        'primitive': 'rtl/lib/ot_async_fifo.sv',
        'implemented_at_selected_frontend': False,
        'payload_write_bytes_per_source_edge': width / 8,
        'payload_read_bytes_per_destination_edge': width / 8,
        'aggregate_payload_bits_per_destination_edge': replicas * width,
        'visibility_destination_edges': [2, 3],
        'first_consumption_destination_edges': [3, 4],
        'credit_return_source_edges': [2, 3],
        'latency_basis': 'two pointer synchronizer FFs plus registered empty/full; phase-dependent, no metastability tail bound',
        'reset_online': 'both resets flush; two-stage local release plus online rendezvous before valid/ready',
        'mutable_storage_protection': 'required and not supplied by bare FIFO; source-compatible SRAM/protection hook pending',
    }


def compose():
    selected = C.compose()
    pc = (C.BASE / 'inputs/ot_hbm_r14_stream_pc.sv').read_text()
    backend = (C.BASE / 'inputs/ot_qwen_hbm_stream4_tagged.sv').read_text()
    period = 1024
    requirements = {
        'T_RCD': 19375, 'T_RCDW': 9375, 'T_RP': 16250, 'T_RAS': 28125,
        'T_RTP': 5625, 'T_CCDL': 2560, 'T_RRDS': 2500, 'T_RRDL': 3125,
        'T_FAW': 15000, 'T_RFC': 350000, 'T_RFCPB': 200000,
        'T_RREFD': 8000, 'T_RTW': 9948,
        'T_WTR': 6250 + 1024 + 6250,
        'T_WRR': 6250 + 1024 + 20625,
    }
    timing = {}
    for name, minimum in requirements.items():
        match = re.search(r'\b' + name + r'\s*=\s*(\d+)', pc)
        if not match:
            raise ValueError('selected PC timer missing: ' + name)
        edges = int(match.group(1))
        timing[name] = {'selected_edges': edges, 'periodic_budget_ps': edges * period,
                        'source_checker_minimum_ps': minimum,
                        'budget_margin_ps': edges * period - minimum}
    if any(t['budget_margin_ps'] < 0 for t in timing.values()):
        raise ValueError('periodic clock violates selected absolute timer budget')
    families = [
        fifo('stream_landing', 128, 256 + 17 + 8, 64, 'HCLK', 'CORE',
             ['l_v', 'l_sec', 'l_row', 'l_data', 'l_pop'],
             'publish only actual completed RD; pop only l_v&&l_pop; reserve against CRED32 before RD'),
        fifo('token_write', 128, 256 + 24 + 9, 16, 'CORE', 'HCLK',
             ['w_v', 'w_sec', 'w_data', 'w_tag', 'w_room'],
             'w_room preserves >=3 slots; held payload until AQ handoff; one owner tag until real WR completion'),
        fifo('write_done', 128, 9, 64, 'HCLK', 'CORE', ['wd_v', 'wd_tag'],
             'tag publication only after actual WR latency; implicit consume wd_v each core edge, never first unrelated ACK'),
        fifo('tagged_request', 4, 24 + 5 + 13, 4, 'TCLK', 'HCLK',
             ['t_req_v', 't_req_ready', 't_req_addr', 't_req_len', 't_req_tag', 't_req_we', 't_req_wdata'],
             'read-only: t_req_we faults/drops; wdata not stored; len1..16, same splitter/map/AQ order'),
        fifo('tagged_response', 128, 256 + 13 + 4, 32, 'HCLK', 'TCLK',
             ['t_rsp_v', 't_rsp_ready', 't_rsp_tag', 't_rsp_beat', 't_rsp_data', 't_rsp_wr', 't_pc_room'],
             'reserve before AQ push; publish due CL+BURST+RSP in port order; preserve advisory >=8 slots, never credit it as exact reservation'),
    ]
    storage = sum(f['storage_bits'] for f in families)
    control = sum(f['control_state_bits'] for f in families)
    # Actual mailbox data hold + capture + response hold + source response,
    # and seven local state / eight synchronized control FFs per mailbox.
    mailbox_bits = (2 * 30 + 2 * 1 + 15) + (2 * 1 + 2 * 1 + 15)
    # h_fault/h_code are shared unsafely by the simulation backend. Physical
    # sticky code delivery needs its own mailbox; t_bad->CORE and CORE fault
    # ->TCLK each need two FFs, with no independent multi-bit code crossing.
    fault_bits = (2 * 16 + 2 * 1 + 15) + 4
    paths = {
        'descriptor_to_accept': {'charge': '4 HCLK edges + 3 CORE edges, no queue/receiver stall',
                                 'max_phase_only_ps': 4 * period + 3 * 833.333,
                                 'hold': 'row19/n11 held until acceptance ACK; one pending descriptor'},
        'GO_to_stack_sample': {'charge': '4 HCLK mailbox edges + 1 HCLK registered go_q edge, plus busy wait',
                               'max_phase_only_ps': 5 * period,
                               'hold': 'one pending GO captured from source pulse; destination waits busy_all, ACK after consumption'},
        'stream_RD_to_core_consume': {'charge': 'ceil((CL+BURST+RSP)/1024) HCLK edges + 4 CORE edges; reservation before RD',
                                     'hclk_read_return_edges': (12500 + 1024 + 10000 + 1023) // 1024,
                                     'max_phase_only_ps': 23 * period + 4 * 833.333},
        'tagged_request_to_response': {'charge': '4 HCLK ingress edges + actual splitter/AQ/refresh wait + 23 HCLK read-return edges + 4 TCLK edges',
                                        'known_HCLK_charge_ps': 27 * period,
                                        'TCLK_charge_edges': 4,
                                        'source_TCLK_period_ps': None},
        'write_to_done': {'charge': '4 HCLK ingress edges + AQ/refresh wait + ceil((CWL+BURST+RSP)/1024) HCLK edges + 4 CORE edges',
                          'hclk_write_return_edges': (6250 + 1024 + 10000 + 1023) // 1024,
                          'max_phase_only_ps_excluding_AQ_wait': 21 * period + 4 * 833.333},
    }
    pins = []
    for path in ['tools/runtime/qwen_combined/stream4_memory_binding.hpp',
                 'tools/runtime/qwen_combined/stream4_tagged_rows_hook.cpp',
                 'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_cdc_mailbox.sv', 'rtl/lib/ot_reset_sync.sv']:
        pins.append({'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()})
    return {
        'schema': 'qwen_rom_stream4_periodic_clock_plan_r1',
        'selected_clock': 'external periodic HCLK,1024ps; new explicit physical input',
        'selected_controller_sha256': C.PINS['ot_hbm_r14_stream_pc.sv'],
        'selected_stack_sha256': C.PINS['ot_hbm_r14_stream_stack.sv'],
        'controller_logic_changed': False, 'runtime_backend_changed': False,
        'model_owner': 'Maxwell; additive price submitted before new context source',
        'clock_ports': {'controller_hclk': {'period_ps': period, 'duty_cycle': .5,
                                          'provider': 'Goodall/Laplace external clock root/PHY contract',
                                          'loaded_insertion_skew_slew_ps': None},
                        'core_clk': {'period_ps': 833.333},
                        'tagged_clk': {'source': 'die.hclk via tagged_rows_hook t_clk', 'period_ps': None},
                        'resets': 'CORE/HCLK/TCLK independently synchronized release after source clock stable; shared abort/epoch flush, no live-reset replay outside common controller reset'},
        'constraints': {'SS_setup_uncertainty_ps': 60, 'FF_hold_uncertainty_ps': 25,
                        'HCLK_min_pulse_high_low_ps': [512, 512],
                        'blanket_async_clock_groups_allowed': False,
                        'binary_counter_or_payload_false_paths_allowed': False,
                        'Gray_bus_max_delay': 'source period to first synchronizer pins; source-period bus skew bound, exact instance scoped',
                        'sync_exceptions': 'only actual metastability stage1 D; stage1->stage2 timed in receiving domain; no payload exception',
                        'payload_constraints': 'stable owner slot through synchronized pointer; actual read mux/output capture timed; macro loaded SS/FF arcs and reset recovery/removal required'},
        'absolute_HBM_timer_budgets': timing,
        'timer_budget_is_NOT_state_machine_or_PHY_timing_proof': True,
        'refresh': {'REFI_edges': 3808, 'REFI_periodic_ps': 3899392, 'maximum_REFI_ps': 3900000,
                    'REFIPB_edges': 118, 'REFIPB_periodic_ps': 120832,
                    'PULLIN': 16, 'refresh_AQ_stall_bound_edges': 64,
                    'same_bank_ref_round_and_phase': 'unchanged source logic; no inferred refresh-free bandwidth'},
        'frontend_fifos': families,
        'descriptor_GO_mailboxes': {'descriptor_width': 30, 'descriptor_ACK_width': 1,
                                     'GO_width': 1, 'GO_ACK_width': 1,
                                     'primitive': 'rtl/lib/ot_cdc_mailbox.sv',
                                     'state_bits': mailbox_bits,
                                     'GO_no_new_frontend_ready_alias': 'retain pulse port; capture one outstanding, overflow is source protocol fault',
                                     'descriptor_READY': 'both CDC owner slot and all128 controller desc_r; acceptance ACK remains causal'},
        'fault_CDC': {'HCLK_code_mailbox_width': 16, 'HCLK_code_ACK_width': 1,
                      'TCLK_bad_to_CORE_sync_FF': 2, 'CORE_fault_to_TCLK_sync_FF': 2,
                      'state_bits': fault_bits,
                      'raw_h_fault_h_code_or_CORE_fault_to_TCLK_connections_allowed': False,
                      'delivery': 'held sticky source fault/code through mailbox, same common reset epoch; no unsynchronized code bus'},
        'source_latency_paths': paths,
        'area': {'payload_storage_bits': storage, 'FIFO_pointer_online_reset_bits': control,
                 'mailbox_bits': mailbox_bits, 'global_HCLK_reset_FF_bits': 2,
                 'fault_CDC_bits': fault_bits,
                 'storage_FF_realization_area_um2': storage * U.DFF_UM2,
                 'CDC_control_FF_floor_area_um2': (control + mailbox_bits + fault_bits + 2) * U.DFF_UM2,
                 'mapped_area_mux_decode_clock_wire_protection': None,
                 'existing_rings_replaced_once_not_added_again': True,
                 'parent_accumulator_33bits_removed_only_in_selected_external_clock_cut': True,
                 'physical_slot_fit': None},
        'fanout': {'HCLK_PC_replicas': 128, 'HCLK_FIFO_domains': sum(f['replicas'] for f in families),
                   'HCLK_descriptor_GO_fault_mailboxes': 3,
                   'CORE_FIFO_domains': 384, 'TCLK_FIFO_domains': 132,
                   'descriptor_row19_n11_and_GO_leaf_fanout': 128,
                   'descriptor_ready_reduction': '4x32PC plus global4-way AND; retain loaded cuts',
                   'actual_pin_cap_and_wire_distributed_buffers': None},
        'transport': {'shared_memory_controller_owner': 'same4stack128PC, same source sector map and AQ write-before-read order',
                      'stream_binding': 'stream_* frontend pins map to unprefixed backend fields using stream4_memory_binding.hpp',
                      'tagged_binding': 'die.h_* <-> backend.t_* through source tagged_rows_hook; separate TCLK, no implicit tie to controller_hclk',
                      'actual_PHY_request_return_completion_provider': None,
                      'no_simulation_shared_arrays_as_hardware_credit': True},
        'token_composition': {'per_event_service_costs': paths,
                               'critical_event_counts_or_overlap_from_retained_source_schedule': None,
                               'additional_token_latency_ps': None,
                               'old_baseline_crossings_are_not_zero_or_automatically_additive': True,
                               'no_new_P8191_run': True},
        'source_pins': pins,
        'physical_controller_cut_source_ready': True,
        'full_frontend_CDC_implementation_ready': False,
        'whole_context_build_admitted': False,
        'preserved_gate_failure': selected['clock'],
        'remaining_implementation': ['bind clock provider and reset/RDC with Goodall/Laplace',
                                     'install protected finite ring CDC using actual SRAM/load/slot models',
                                     'bind PHY returns/reservations to same controller and source clocks',
                                     'Maxwell compose per-event causal costs without repeat token run'],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        p.error('preserve old evidence; choose a new output path')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(compose(), sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    main()

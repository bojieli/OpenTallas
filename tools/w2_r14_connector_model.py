#!/usr/bin/env python3
"""Additive W2/R14 ABI and source-cost composition, not a caller allocator.

All bindings below are obligations checked at a proposed accepted endpoint.
They do not constitute installed source callbacks, a CDC or a visibility oracle.
"""
import argparse
import ast
import hashlib
import json
import inspect
from pathlib import Path
from w2_pc_exact_completion_model import owner46, decode_owner46, uint, size

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/w2_r14_connector_model_20261003'


def verify_inputs():
    manifest = json.loads((OUT / 'input_manifest.json').read_text())
    for row in manifest['inputs']:
        if hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('source pin: ' + row['path'])
    return manifest


def physical(byte):
    # Execute ONLY the archived authoritative pure function: no payload/imports.
    path = OUT / 'inputs/inputs/main/tools/qwen_hbm_provider_bindings_r17.py'
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'physical')
    scope = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), scope)
    result = scope['physical'](byte)
    result['physical_PC7'] = result['stack'] * 32 + result['PC']
    result['inverse_byte'] = ((result['local_sector31'] * 32 + result['byte_in_sector']) // 128 * 512
                              + result['stack'] * 128
                              + (result['local_sector31'] * 32 + result['byte_in_sector']) % 128)
    return result


def meta92(child, sm, rf_slot, parent_ref):
    return (uint(child, 46) << 46 | uint(sm, 5) << 41 |
            uint(rf_slot, 9) << 32 | uint(parent_ref, 32))


def decode_meta92(value):
    uint(value, 92)
    return dict(child=value >> 46, sm=(value >> 41) & 31,
                rf_slot=(value >> 32) & 511, parent_ref=value & 0xffffffff)


def backend16(generation, physical_tag):
    return uint(generation, 4) << 12 | uint(physical_tag, 12)


def explicit_client(provider_class, directory):
    # Never truncate provider-class6 to client3; KV5 is already occupied.
    uint(provider_class, 6)
    if provider_class not in directory:
        raise ValueError('unbound provider class')
    value = uint(directory[provider_class], 3)
    if value >= 6:
        raise ValueError('unmapped seventh client')
    return value


def validate_sector_binding(*, byte, child, source_meta, die, legacy_die,
                            legacy_stack, length, beat, parent_ref, parent55, sm):
    """Check supplied live directory binding; do not manufacture/allocate it."""
    uint(die, 1); uint(legacy_die, 1); uint(parent55, 55)
    addr = physical(byte)
    c = decode_owner46(child)
    m = decode_meta92(source_meta)
    if byte % 32 or length != 1 or beat != 0:
        raise ValueError('one-sector LEN1 BEAT0 contract')
    if c['client'] >= 6 or c['physical_pc'] != addr['physical_PC7']:
        raise ValueError('actual NC6 translated PC')
    if die != legacy_die or legacy_stack != addr['stack']:
        raise ValueError('DIE/STACK scope')
    if m != dict(child=child, sm=uint(sm, 5), rf_slot=parent55 & 511,
                 parent_ref=uint(parent_ref, 32)):
        raise ValueError('pre-bound child/parent metadata')
    # Parent owner is intentionally not compared with the last child owner.
    return dict(address=addr, child=child, parent55=parent55)


def validate_return(saved, observed):
    """No state/credit release on failed validation; ledger owner must latch fault.

    Legacy192 is retained whole. Direction and accepted backing-visible receipt
    remain separate. This check is not a physical write-visibility proof.
    """
    widths = dict(die=1, stack=2, legacy192=192, source_meta92=92,
                  backend16=16, direction=1, beat=5)
    if set(saved) != set(widths) or set(observed) != set(widths):
        raise ValueError('incomplete saved/returned identity')
    for key, width in widths.items():
        uint(saved[key], width); uint(observed[key], width)
        if saved[key] != observed[key]:
            raise ValueError('wrong/stale return ' + key)
    if observed['beat'] != 0:
        raise ValueError('sector terminal beat')
    return True


def release_predicate(*, w2_local_accepted, rf_common_ack, visible,
                      reader_ack, child_reverse_validated, parent_released,
                      forward_cdc_drained, reverse_cdc_drained):
    """Symbolic causal receipts, NOT counters or newly installed state bits.

    Actual provider must generate these predicates. Mere time/empty/reset is
    never a substitute. Source and backend generation wrap use the same full
    old-copy exclusion, independently; no numerical generation run cap.
    """
    return all(type(v) is bool and v for v in locals().values())


def generation_rearm(*, debts_retired, admission_frozen, provider_old_copies_absent,
                     reset_endpoints_fenced):
    """Separate wrap/reset gate, not a freeze imposed on each normal completion."""
    return all(type(v) is bool and v for v in locals().values())


def rf_publish(parent55, mask, format_verified=False):
    uint(parent55, 55); uint(mask, 16)
    if mask != 0xffff or format_verified is not True:
        raise ValueError('partial frame or missing exact source codec')
    return parent55


def model():
    pins = verify_inputs()
    composition = json.loads((OUT / 'inputs/r2/composition.json').read_text())
    costs = json.loads((OUT / 'inputs/cost-inputs.json').read_text())
    if not composition['p_wr_done_ready_required']:
        raise ValueError('superseded pulse-only endpoint')
    w2 = composition['W2_model_costs']['full_wrapper_variant']
    if (w2['NC'], w2['raw_state_bits_per_PC'], w2['protected_state_bits_per_PC']) != (6, 4779, 9144):
        raise ValueError('wrong W2 parameter selection')
    widths = dict(meta=46+5+9+32, sidecar=46+5+9+32+4,
                  request=455+92, owned=465+92+4, command=339+4,
                  W10_request=339+50, W10_return=303+50)
    expected = dict(meta=costs['sidecar_source_metadata_bits'], sidecar=costs['sidecar_plus_backend_generation_bits'],
                    request=costs['proposed_provider_request_bits'], owned=costs['proposed_owned_bits'],
                    command=costs['proposed_command_full_backend_token_bits'],
                    W10_request=costs['proposed_raw_request'], W10_return=costs['proposed_raw_return'])
    if widths != expected:
        raise ValueError('connector width mismatch')
    state = dict(sidecar_logical_bits=4*32*128*96,
                 sidecar_macro_capacity_bits=4*32*128*256,
                 sidecar_macros=4*32,
                 W10_protected_pipeline_increment_bits=144*38*2*2*72,
                 RF_assembly_data_candidate_bits=32*16*256,
                 RF_assembly_mask_candidate_bits=32*16)
    if state['W10_protected_pipeline_increment_bits'] != costs['pipeline_two_seats_38stages_144lanes_increment_bits']:
        raise ValueError('W10 omitted sideband')
    owner_source = (OUT / 'inputs/inputs/main/rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv').read_text()
    if 'if(held&&ore)' not in owner_source or 'live[tag_saved]<=0' not in owner_source:
        raise ValueError('R14 early-retirement source changed')
    nc6 = size(nc=6)
    if (nc6['state_bits_per_PC'] != w2['raw_state_bits_per_PC'] or
        nc6['protected_storage']['bits_per_PC'] != w2['protected_state_bits_per_PC']):
        raise ValueError('owner cost vs composition mismatch')
    g0 = dict(component_can_proceed_independently_of_native_caller=True,
        selected_geometry=dict(NC=6, MAX_OUT=16, CTAG=32, GEN=4, PTAG=39, AW=34),
        full_wrapper_port_address_default=32,
        AW34_is_lossless_R14_sector_carrier_not_change_to_original=True,
        proposed_defaultoff_namespace='New same-interface completion successor; originals byteidentical',
        service_clock_period_ps=None, source_clock_reset_domain_bound=False,
        loaded_setup_hold_budget_ps=None,
        selected_lookup_stages=None, priced_stage_variant='L1 only; prospective minima, not SS proof',
        compare_ports=nc6['lookup_ports'], update_ports=nc6['logical_table_updates_per_edge'],
        lookup_storage=nc6['table_storage'],
        source_input_signal_bits=nc6['port_signal_bits'],
        compare_fanout_per_client_bank=nc6['comparator_broadcast_sinks_per_bit_per_client_bank'],
        compare_load_SS_fF_per_bit_per_bank=nc6['compare_sink_SS_fF_per_bit_per_bank'],
        global_match_rows=96, per_client_tag_gen_mux_depth=4,
        requester_hold_capacity=1, requester_hold_bits=335,
        request_arbiter_sequential_reference_prepared=False,
        reset_rearm_control_ports_selected=False, reset_rearm_extra_state_price=None,
        mutable_protection_latency_mapped=False,
        proposed_validation=['NC6/MAX16 actual full-width request/read/ready-held write ports',
            'old-state lookups and validation-before-any-release, no same-edge returned-credit reuse',
            'frozen request under backend stall; held read/write under independent client refusal',
            'live duplicate/wrong direction/wrong gen/wrong original32/reset-stale refusal',
            'valid-code identity mutation not merely protection syndrome mutation',
            'no reset-erasure of accepted debt; positive allcopy rearm',
            'boundary request/return/multi-release collision and stickyfault no grants or releases'],
        remaining_component_decisions=['Source clock/reset and loaded SS/FF timing budget',
            'Stage enrollment including protection lookup/hold path; reprice if L1 insufficient',
            'Concrete reset/rearm debt-fence interface, state/control debit and oldstate request arbiter'])
    return dict(scope='Additive connector-bound W2 model; no RTL/runtime/physical admission',
                pins=pins, verdict='FAIL_CONNECTED_SOURCE_MODEL_ADMISSION', build_allowed=False,
                widths=widths, state_cost_inputs=state, actual_W2_NC6=w2,
                boundary_signal_bits=composition['boundary_signal_bits'],
                latency=composition['latency'], component_G0=g0,
                write_contract=dict(p_wr_done_ready_required=True,
                    supersedes_pulse_only_1bfbb=True, backend_visible_receipt_required=True,
                    legacy_adapter_selected=False, legacy_adapter_bits_latency=None),
                allocation=dict(source_generation_bits=4, backend_generation_bits=4,
                    independent_generations=True, source_owner46_die_scoped=True,
                    source_legacy192_preserved=True, meta92_same_context_index=True,
                    second_CAM=False, new_directory_client=False,
                    one_W2_sector_bytes=32, R14_LEN=1, R14_BEAT=0,
                    RF_frame_children=16, simultaneous_children_proven=False,
                    producer_client_parent_allocator_bound=False),
                retirement=dict(current_R14_ore_early_retirement_compatible=False,
                    w2_local_release_not_physical_tag_release=True,
                    required_release_receipts=list(inspect.signature(release_predicate).parameters),
                    required_wrap_reset_receipts=list(inspect.signature(generation_rearm).parameters),
                    implementation='Replace early ore tag/context free with validated reverse all-copy retirement; exact provider ports/control update pending',
                    new_control_bits=None, maximum_quarantine_occupancy=None,
                    wrap_wait_edges=None),
                once_only=dict(rule=composition['once_only_composition']['rule'],
                    matched_old_W2_debit=None, net_area=None,
                    sidecar_assembly_transport_overlap_credit=0,
                    macro_area=None, routes_clock_SShold=None),
                next_gate=['Popper accepted native caller/client/parent-child directory binding and receipt on actual R14 route',
                    'Full16 command/backing/return echo, NC6 translated-PC and held WRready ports',
                    'Replace R14 early ore retirement with saved-identity reverse quarantine; actual all-copy wrap/reset predicates',
                    'Exact16-sector RF frame or source-valid partial join/codec and stable pre-bound parent55',
                    'Joined port/update schedule, source clocks/CDC, named physical costs, once-only debit and finite continuous calendar'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = model()
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output: args.output.write_text(text)
    else: print(text, end='')

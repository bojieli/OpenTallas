"""S81 receipt composition and finite component timing, without whole-core simulation.

Known mapped area and source counts are not physical fit. Unknown measured service
terms propagate to the token sink. Superseded VM floors are never added together.
"""
from pathlib import Path
import hashlib
import ast
import json
import math

NS = 'results/uarch/dsrom_s81_unified_components_20261004'
CANDIDATE = 'DSROM-S81-TP4-NP2417-BF519-RD64-CAP1-VM9SF2ROUTE'


def positive(x, name):
    if type(x) not in (int, float) or not math.isfinite(x) or x <= 0:
        raise ValueError('Positive finite service required: ' + name)
    return x


def vm_service(binding):
    """Selected-service analytical bound; no default clock, II or stage count.

    A full WQD4 row queue has three predecessors, each occupying the real bank
    service II. Old-stripe read/decode/merge/check must own the same finite bank
    ports as publication. Route issue throughput is independently required.
    """
    names = ('write_clock_GHz', 'field_clock_GHz', 'gear_bound_ns',
             'bank_service_II_edges', 'route_service_II_edges',
             'packet_route_edges', 'checked_old_stripe_read_edges',
             'decode_old_edges', 'merge_encode_edges', 'data_check_commit_edges',
             'checked_publication_edges', 'registered_receipt_edges',
             'reverse_CDC_edges', 'forward_CDC_edges', 'reverse_capture_clock_GHz',
             'bank_pipeline_capacity_rows', 'bank_service_rows_ahead_bound')
    missing = [n for n in names if binding.get(n) is None]
    if missing:
        return {'bound_ns': None, 'missing': missing}
    for n in names:
        if n == 'bank_service_rows_ahead_bound':
            if type(binding[n]) is not int or binding[n] < 0:
                raise ValueError('Nonnegative actual occupancy bound required')
        else:
            positive(binding[n], n)
    for n in (k for k in names if k.endswith('_edges') or k.endswith('_rows') or k.endswith('_bound') and k != 'gear_bound_ns'):
        if type(binding[n]) is not int:
            raise ValueError('Integer edge count required: ' + n)
    obligations = ('RMW_ports_reserved', 'all_six_copy_visible_receipt',
                   'old_head_identity_match', 'reverse_count_identity_match')
    if any(binding.get(n) is not True for n in obligations):
        raise ValueError('RMW/publication ownership not bound')
    w = binding['write_clock_GHz']
    if binding['gear_bound_ns'] < binding['forward_CDC_edges'] / w:
        raise ValueError('Gear bound omits forward CDC')
    stages = names[5:12]
    occupied = sum(binding[n] for n in stages if n != 'packet_route_edges')
    # Any proposed pipelined II must retain every occupied row until its
    # matched completion. The bank port schedule still needs measurement.
    if binding['bank_pipeline_capacity_rows'] * binding['bank_service_II_edges'] < occupied:
        raise ValueError('Bank II omits retained RMW pipeline capacity')
    pred = binding['bank_service_rows_ahead_bound'] * binding['bank_service_II_edges']
    service = sum(binding[n] for n in stages)
    bound = binding['gear_bound_ns'] + (pred + service) / w + binding['reverse_CDC_edges'] / binding['reverse_capture_clock_GHz']
    return {'bound_ns': bound, 'queued_and_inflight_predecessor_wait_edges': pred,
            'bank_port_occupation_edges': occupied,
            'route_service_II_edges': binding['route_service_II_edges'],
            'forward_CDC_already_in_gear_bound': True,
            'physical_qualified': False}


def solve_events(events):
    """Max-plus critical path over actual executed events, not inventory counts.

    Caller supplies source-owned accepted program events with provider durations.
    Parallel TP ranks join at max. Unknown duration or predecessor stays unknown;
    shared resources serialize via explicit predecessor IDs in the event list.
    """
    done, unresolved = {}, {}
    for e in events:
        name = e['id']
        if name in done:
            raise ValueError('Duplicate event identity')
        deps = e['deps']
        if any(d not in done for d in deps):
            raise ValueError('Events must be topologically ordered')
        duration = e['duration_ns']
        if duration is not None:
            positive(duration, name)
        gaps = sorted(set(([name] if duration is None else []) +
                          [u for d in deps for u in unresolved[d]]))
        done[name] = None if gaps else max([done[d] for d in deps] or [0]) + duration
        unresolved[name] = gaps
    return {'finish_ns': done, 'unbound_events': unresolved,
            'resource_rule': 'shared bank/link/codec occupations must appear as dependency edges'}


def build(root, ctx=1048576, executed_events=None, vm_binding=None):
    root = Path(root)
    if type(ctx) is not int or ctx <= 0:
        raise ValueError('Positive context length required')
    kit = root / NS
    manifest = json.loads((kit / 'input_manifest.json').read_text())
    data = {}
    for name, pin in manifest.items():
        p = kit / 'inputs' / name
        if hashlib.sha256(p.read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('Receipt changed: ' + name)
        if name.endswith('.json'):
            data[name] = json.loads(p.read_text())
    timing_ast = ast.parse((kit / 'inputs/vm_selected_timing.py').read_text())
    required = next(ast.literal_eval(n.value) for n in timing_ast.body
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REQUIRED' for t in n.targets))
    inv, ret = data['inventory.json'], data['return.json']
    cap, parent = data['capture_native.json'], data['capture_parent.json']
    r3, r4 = data['vm_r3.json'], data['vm_r4.json']
    expected = (81, 4, 2417, 519, 9668)
    if tuple(inv[k] for k in ('stages', 'TP', 'pairs_per_rank_die', 'BF_dual_pairs', 'physical_ROM4096_per_layer_die')) != expected:
        raise ValueError('Selected S81 inventory changed')
    if ret['retained_nodes'] != 5090 or ret['retained_unilateral_nodes'] != 384:
        raise ValueError('Strict unary/root storage omitted')
    areas = r4['prospective_area']
    vm_floor = sum(areas[k] for k in ('joint_r3_placement_floor_mm2',
                                    'retained_suffix_added_placement_mm2',
                                    'codec_construction_added_placement_mm2'))
    if not math.isclose(vm_floor, areas['combined_placement_floor_mm2'], abs_tol=1e-12):
        raise ValueError('r4 floor does not replace healthy floor')
    cap_floor = cap['actual_capture']['cell_only_50pct_reservation_mm2']
    old_tail = 7 / .9
    provisional = [r3['latency']['empty_queue_tail_upper_excluding_codec_ns'],
                   r3['latency']['depth4_tail_upper_excluding_codec_ns']]
    # One fixed graph skeleton per stage. Not a synthesized accepted-program
    # calendar: its source issue events and costs remain explicitly unbound.
    events = []
    previous = []
    for stage in range(81):
        ranks = []
        for rank in range(4):
            prefix = f's{stage}.r{rank}'
            chain = [('dispatch_cfg_activation', None), ('matrix_last_root', None),
                     ('qualified_VM_visible_reverse_packet', None), ('source_release', None)]
            deps = previous
            for suffix, duration in chain:
                name = prefix + '.' + suffix
                events.append(dict(id=name, deps=deps, duration_ns=duration,
                                   stage=stage, rank=rank, source='selected component enrollment pending'))
                deps = [name]
            ranks += deps
        previous = ranks
    events.append(dict(id='head_and_token_return', deps=previous, duration_ns=None))
    if executed_events is not None:
        events = executed_events
        if not events or events[-1]['id'] != 'head_and_token_return':
            raise ValueError('Complete executed graph needs head/token sink')
        for e in events:
            if not e.get('provider_sha256') or not e.get('source_program_sha256'):
                raise ValueError('Executed events need provider and program source identity')
    solved = solve_events(events)
    return {
        'schema': 'opentallas.uarch.DSROM.S81.component_composition.v1',
        'candidate': CANDIDATE, 'context_tokens': ctx,
        'inventory': {'stages': 81, 'TP': 4, 'layer_rank_dies': 324,
                      'head_dies': inv['head_dies'], 'table_dies': inv['table_dies'],
                      'total_dies': inv['layer_dies'] + inv['head_dies'] + inv['table_dies'],
                      'pairs_per_rank_die': 2417, 'BF_dual_pairs': 519,
                      'Q_only_pairs': inv['q_only_pairs'], 'padding_pairs': inv['padding_pairs'],
                      'rows_per_macro': inv['rows'], 'macros_per_pair': inv['macros_per_pair'],
                      'macros_per_rank_die': 9668, 'total_layer_macros': inv['physical_ROM4096_layer_total'],
                      'ROM_ECC': False, 'matrix_stage_map_sha256': manifest['stage_map.json']['sha256']},
        'return': {'nodes': 5090, 'binary': 4706, 'unary': 384, 'roots': 128,
                   'retained_storage_bits': ret['retained_storage_bits'],
                   'storage_FF50_mm2': ret['retained_FF50_reservation_mm2'],
                   'added_dead_prune_latency_cycles': ret['latency_change_dead_prune_cycles'],
                   'physical_qualified': False},
        'area': {'VM_per_provider_floor_mm2': vm_floor,
                 'VM_floor_terms_mm2': {k: areas[k] for k in areas if k.endswith('_mm2')},
                 'r4_replaces_r3_and_r2_not_summed': True,
                 'actual_capture_body_um2': cap['actual_capture']['actual_cell_area_um2'],
                 'capture_cell50_mm2': cap_floor,
                 'one_capture_plus_one_VM_component_floor_mm2': cap_floor + vm_floor,
                 'physical_provider_replicas_per_rank_die': None,
                 'selected_disjoint_physical_slot': None, 'whole_die_mm2': None,
                 'reticle_width_mm': 26, 'reticle_height_mm': 33, 'reticle_mm2': 858,
                 'whole_die_fit': None, 'containment_credit_mm2': 0,
                 'exclusions': areas['excludes'] + ['capture ties/clock/reset/hold/PG',
                    'disjoint inherited-service union', 'PHY/clock-region placement and wire stages']},
        'service': {'new_MACs_per_cycle': 0, 'new_arithmetic_intensity': 'unchanged; capture/publication only',
                    'capture_no_READY': True, 'roots': 128, 'capture_capacity_per_root': 1,
                    'source_VM_data_bytes_per_native_edge': parent['VM_bytes_per_cycle'],
                    'root_bits_per_native_edge': parent['root_bits_per_cycle'],
                    'VM_address_data_bits_per_native_edge': parent['VM_address_data_bits_per_cycle'],
                    'packet_bits_per_root': 136, 'coded_state_bits_per_packet': 216,
                    'route_instances': 2, 'existing_route_reuse_already_credited': 1,
                    'aggregate_slow_packet_bits_per_edge': r3['ports']['aggregate_slow_packet_bits'],
                    'macro_write_rows_per_bank_edge': 1, 'macro_write_copies': 6,
                    'bank_K': 4, 'bank_WQD': 4, 'bank_service_II_edges': None,
                    'RMW_port_schedule': None, 'routing_track_capacity': None,
                    'whole_phase_slots': r4['source_suffix']['required_four_frame_slots'],
                    'accepted_phase_rows_bound': r4['source_suffix']['max_actual_fragment_rows'],
                    'no_next_GO_while_faulted': True, 'mutable_protection_retained': True},
        'clock_load': {'native_capture_CLK_sinks': cap['actual_capture']['source_clock']['native_CLK_sinks'],
                       'native_capture_async_sinks': cap['actual_capture']['source_cold_reset']['native_async_sinks'],
                       'additional_VM_FF_floor': r3['coded_state']['total_added_FF_floor'] + r4['source_suffix']['additional_FF_vs_joint_r3'],
                       'selected_VM_GHz': None, 'native_functional_clock': 'one parent clk; no physical domain credit',
                       'stream_target_GHz': 1.2, 'serial_target_GHz': .9,
                       'SS_setup_uncertainty_ps': 60, 'FF_hold_uncertainty_ps': 25,
                       'Clock_C_max_region_mm': 5.25, 'clock_mesh': False,
                       'loaded_CTS_reset_PG_fit': None},
        'element_evidence': {'q_pipeline_exact_verdict': data['qpipe_exact.json']['verdict'],
                             'q_pipeline_option_added_edges': data['qpipe_exact.json']['added_latency_cycles'],
                             'selected_q_pipeline_option': None,
                             'retained_D_r2_SS_setup_ns': data['qframe_D_FAIL.json']['corners']['SS']['timing']['setup_wns_ns'],
                             'D_r2_failure_preserved_not_transferred': True,
                             'S81_element_context_SSFF': None},
        'latency': {'capture_source_enclosing_idle_edges': parent['added_idle_edges_per_actual_executed_phase'],
                    'mapping_added_edges': 0, 'actual_executed_phase_count': None,
                    'release_rule': 'max(native idle, same-owner all-copy VM visible + captured reverse credits + packet drain); enclosing source edges are not summed twice',
                    'provisional_W11_only': {'fast_GHz': 1.2, 'slow_GHz': .9,
                        'route_stages': 16, 'tail_before_codec_ns': provisional,
                        'old_scatter_only_ns': old_tail,
                        'conditional_extra_tail_ns': [x - old_tail for x in provisional],
                        'physical_clock_or_latency_qualified': False},
                    'selected_service': vm_service(vm_binding or {}),
                    'selected_timing_required_binding_template': {k: None for k in required}, 'events': events,
                    'stage_graph_scope': 'TP4 ranks join by max; stage edges are enrollment skeleton, not 81 measured serial hops or all matrix declarations as executed phases',
                    'analytical_event_solution': {
                        'token_return_ns': solved['finish_ns']['head_and_token_return'],
                        'unbound_on_token_path': solved['unbound_events']['head_and_token_return'],
                        'stage_rank_release_ns': {k: v for k, v in solved['finish_ns'].items() if k.endswith('.source_release')},
                        'resource_rule': solved['resource_rule']},
                    'AR_token_ns': solved['finish_ns']['head_and_token_return'], 'MTP_iteration_ns': None, 'accepted_tokens_per_iteration': None,
                    'MTP_requires': ['six-position verify accepted schedule', 'drafter', 'commit/rollback'],
                    'single_user_tokens_s': None, 'absolute_consumer_deadline_ns': None},
        'admission': {'RTL': False, 'physical': False, 'fit': None, 'rate': None,
                      'whole_core_simulation_required': False,
                      'next_minimum_measurement': 'one NB2/RC6/K4/WQD4/RDREG1 group only after provider/clock/ports agreed; not selected',
                      'missing': ['provider SHA and selected VM clock', 'loaded RMW/read/decode/merge/check service II and stages',
                                  'all-six-copy commit/count receipt/CDC', 'source spine/adapter/core domains',
                                  'selected physical slot and clock/PG/channel union', 'accepted program origin/consumer first VM read']},
        'input_sha256': {n: p['sha256'] for n, p in manifest.items()}}

"""Default-off full-width Qwen station contract; analytical sizing before RTL.

The fixed-schedule producer has no tile-ready handshake. Instructions, launch,
and the VM-aligned x stream cross together; tile faults return separately.
The narrowed r21 interfaces are not silently reinterpreted as this contract.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pin_slices():
    """Exact orientation-specific proposed509-bit interface, no bit-zero proxy."""
    roles = {'qfd_cst_s': {'a': 'a', 'b': 'b', 'tap': 't'},
             'qfd_cst_n': {'b': 'a', 'a': 'b', 'tap': 't'},
             'qfd_chead_e': {'w': 'a', 'e': 'b', 'n': 't', 's': 'c'},
             'qfd_chead_w': {'e': 'a', 'w': 'b', 'n': 't', 's': 'c'}}
    return {master: dict(parameters={'ENABLE_FULLWIDTH': 1, 'TAP': 1,
                                    'SPLIT': int('chead' in master)},
        ports={port: [dict(die_lo=0, width=508, rtl_port=role+'_d', rtl_lo=0),
                      dict(die_lo=508, width=1, rtl_port=role+'_fault', rtl_lo=0)]
               for port, role in mapping.items()},
        scalars={'ck': 'clk', 'rst_n': 'rst_n'},
        unconnected_output_branch_fault_tie=0)
        for master, mapping in roles.items()}


def model(stations=1536, heads=64, path_hops=None, die_height_um=None):
    if stations < 1 or heads < 0 or (path_hops is not None and path_hops < 1):
        raise ValueError('positive station/path counts required')
    ff_source = 'results/rtl/qwen_rom_fulldie_20261003/k16_demand_r1/inputs/SS_cell_prices.json'
    ff = json.loads((ROOT / ff_source).read_text())['facts']['DFFASRHQNx1_ASAP7_75t_R']['SS']
    # Only the register element. Clock/reset trees are not payload registers.
    payload = 379 + 1 + 128
    cst_ff, head_ff = 2 * payload + 3, 3 * payload + 4
    total_ff = stations * cst_ff + heads * head_ff
    # Preserve historical F2/FIFO room; do not reclaim unimplemented logic credit.
    old_frame = [52.704, 103.68]
    # r18 already removes64clock+1reset from corridor andclock+reset fromtap.
    # All509 actual signalpins fit the existing52.704um face at2-track pitch.
    extra_w = max(0, math.ceil((509 * .096 + 2 - old_frame[0]) / .432 - 1e-9)) * .432
    frame = [round(old_frame[0] + extra_w, 6), old_frame[1]]
    sources = ['rtl/hdc/ot_qwen_me_array_w12.sv', 'rtl/hdc/ot_qwen_rom_tile_w12.sv',
               'rtl/hdc/ot_hdc_delay.sv', 'rtl/physical/ot_qwen_die_station.sv',
               'tools/qwen_rom_fulldie_b3r2.py', 'tools/die_top_lint.py', ff_source]
    return dict(schema='opentallas.qwen_station_fullwidth_r22.v2', default_off=True,
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
        selected_tile=dict(commit='e721e27b561104aac303e4cdd1187b59cd163e20',
            path='rtl/physical/ot_qwen_rom_tile_die.sv', command_ports={'ib':379, 'ib_go':1, 'xl':128},
            reverse_port='fault', ready_port=None, tile_id='16-bit static strap, not transported'),
        protocol=dict(kind='fixed_schedule', input_cut='post-VM x alignment; spine tgo/tb/xl_d',
            instruction_assembly=False, fifo=False, credits=False, tile_backpressure=False,
            reason='The actual tile has no ready port; independent stalling destroys BD/XD alignment',
            retirement='Existing spine result/tag owner. Fault OR output is not a retirement acknowledgement',
            reset='Cold POR only; source launch remains zero through pipeline fill; warm reset requires prior global drain'),
        payload_map=[dict(field='ib', lo=0, width=379), dict(field='ib_go', lo=379, width=1),
                     dict(field='xl', lo=380, width=128)],
        exact_proposed_pin_slices=pin_slices(),
        proposed_bundle_map={leg:[dict(field='payload', lo=0, width=508, direction='forward'),
            dict(field='fault', lo=508, width=1, direction='reverse')] for leg in ['corridor','tap']},
        external_clock_reset=dict(clk_pins_per_instance=1, rst_n_pins_per_instance=1,
            clk_implemented='r18 explicit per-region clock nets; do not retain legacy64clock payloadbits',
            rst_n_implemented=False,
            rst_n_gap='r18 removed bundledreset but only builds HBM/CDC resettrees; add explicit tile/station/head reset'),
        boundaries=dict(corridor_bits=509, tap_bits=509, r21_corridor_bits=323, r21_tap_bits=323,
            pre_r18_recipe=dict(fullwidth_corridor=574, fullwidth_tap=511, r21_corridor=388, r21_tap=325),
            extra_bits_per_boundary=186, instruction_bits_per_cycle=379, activation_bits_per_cycle=128,
            register_payload_bits_per_cycle=508, MACs_per_cycle=0, compute_intensity_MAC_per_byte=0,
            communication='One508-bit input,2 independent kept output copies at a station;3 at a head',
            memory_ports_bytes_per_cycle={}, clock_reset_payload_FF=0),
        state=dict(corridor_FF=cst_ff, head_FF=head_ff, relay_FF=510,
            fault_input_capture_then_OR=True, two_forward_copies_per_station=True,
            three_forward_copies_per_head=True, FIFO_storage_bits=0, assembly_storage_bits=0,
            instruction_muxes=0, demuxes=0, control_fanout_target_max=32,
            fault_fanin_max=3, data_pin_fanout=1,
            mutable_protection='Preserve existing policy; new fault registers/control protection requires its own qualification; no ROM ECC introduced'),
        replicas=dict(stations=stations, heads=heads, total_FF=total_ff),
        geometry=dict(old_station_frame_um=old_frame, proposed_station_frame_um=frame,
            extra_width_um=round(extra_w,6), pin_pitch_um=.096,
            corridor_pin_span_um=509*.096, tap_pin_span_um=509*.096,
            available_corridor_pin_span_um=frame[0]-2, available_tap_pin_span_um=frame[1]-2,
            geometric_pin_fit=(509*.096 <= frame[0]-2 and 509*.096 <= frame[1]-2),
            candidate_frame_is_routed=False, routing_tracks_needed_per_corridor=509,
            signal_routing_capacity_after_PDN=None, full_die_routing_fit=False,
            additional_station_frames_mm2=(stations+heads)*extra_w*frame[1]/1e6,
            additional_die_width_um=round(heads*extra_w,6),
            additional_die_area_mm2=None if die_height_um is None else heads*extra_w*die_height_um/1e6,
            die_area_formula='64 * extra_width_um * actual_r22_die_height_um / 1e6; full floorplan must be regenerated'),
        area=dict(FF_cell_um2=ff['area_um2'], FF_total_mm2=total_ff*ff['area_um2']/1e6,
            total_clock_pin_fF=total_ff*ff['pins']['CLK']['cap_fF'],
            FF_and_logic_slot_proxy_mm2=3*total_ff*ff['area_um2']/1e6,
            slot_proxy_basis='FF cell area x1.5 logic allowance /0.5 utilization; not a measured route',
            new_payload_FF_over_same_shape508bit_copy_station=0,
            new_fault_FF_over_same_shape_ready_AND_station=0),
        latency=dict(forward_cycles_per_station=1, fault_cycles_per_station=2,
            delta_forward_cycles_over_original508copy=0, two_beat_serialization_cycles=0,
            path_hops=path_hops, forward_path_cycles=path_hops,
            fault_path_cycles=None if path_hops is None else 2*path_hops,
            publication_guard_cycles_min=None if path_hops is None else 2*path_hops,
            publication_guard='Root must retain token results until all tile faults can arrive; use actual max fault-hop count and tile fault-production latency.2*H alone excludes tile fault latency',
            tag_rule='BD, VM x path, tile IREG and spine XD must be composed from the same concrete path; unequal-depth branches require equalization',
            token_delta=None, headline_adoption=False),
        gates=dict(component_RTL_authoring=True, physical_route=False, exact_transaction=False,
            final_master_interface=False, SSFF=False, full_token_adoption=False),
        blockers=['Install concrete509-bit bundle maps and missing explicit field reset tree in r22 generator',
            'Bind producer BD/XVM/IREG/XD to actual station and relay path lengths',
            'Implement and price global fault publication guard from real tile fault latency and result commit owner',
            'Confirm mutable fault/control protection and selected link fault contract',
            'Measure exact transaction/fault negatives and actual508bit station at SS/FF; then full die context'])


def dual_fault_model(path_hops=None, tile_fault_latency=None):
    m = model(path_hops=path_hops)
    m['schema'] = 'opentallas.qwen_station_fullwidth_r22.dual_fault.v1'
    for role, spec in m['exact_proposed_pin_slices'].items():
        for port, slices in spec['ports'].items():
            slices.append(dict(die_lo=509,width=1,rtl_port=slices[-1]['rtl_port']+'_n',rtl_lo=0))
    for leg in m['proposed_bundle_map'].values():
        leg.append(dict(field='fault_n',lo=509,width=1,direction='reverse'))
    m['boundaries'].update(corridor_bits=510,tap_bits=510,extra_bits_per_boundary=187)
    m['state'].update(corridor_FF=1022,head_FF=1532,relay_FF=512,
        fault_complementary_rails=True,retention_gate='Each positive/complement rail must have a distinct mapped sequential driver',
        coverage='Fault state only; original380-bit instruction/go storage has no installed integrity code')
    delta=m['replicas']['stations']*3+m['replicas']['heads']*4
    m['replicas']['total_FF']+=delta
    area=delta*m['area']['FF_cell_um2']/1e6
    prices=json.loads((ROOT/'results/rtl/qwen_rom_fulldie_20261003/k16_demand_r1/inputs/SS_cell_prices.json').read_text())
    cap=prices['facts']['DFFASRHQNx1_ASAP7_75t_R']['SS']['pins']['CLK']['cap_fF']
    m['area']['total_clock_pin_fF']+=delta*cap
    m['area']['FF_total_mm2']+=area
    m['area']['FF_and_logic_slot_proxy_mm2']+=3*area
    m['area']['new_fault_FF_over_same_shape_ready_AND_station']=delta
    m['geometry'].update(corridor_pin_span_um=510*.096,tap_pin_span_um=510*.096,routing_tracks_needed_per_corridor=510)
    m['forward_control_protection']=dict(installed=False,raw_control_bits=380,
        SECDED64_blocks=6,coded_bits=432,sidecar_bits=48,
        prospective_signal_bus_bits=558,prospective_pin_span_um=558*.096,
        decode_before_launch_required=True,tile_checker_installed=False,
        note='No protection credit for forward control. Root token publication guard alone cannot undo corrupted operand addresses/mutable writes.')
    depth=None if path_hops is None or tile_fault_latency is None else 2*path_hops+tile_fault_latency+1
    m['root_publication_guard']=dict(installed=False,root_decode_cycles=1,
        tile_fault_latency=tile_fault_latency,min_hold_cycles=depth,
        result_ports=96,raw_word_bits=1+24+16+512,protected_word_bits=9*72,
        payload_storage_bits_lower_bound=None if depth is None else 96*depth*648,
        formula='96 ports * (2H + actual_tile_fault_latency +1 rootdecode) cycles *648 protectedbits per valid/address/mask/data word',
        limitations='No buffering/ready contract at current result port. Maximum fault-lateness and all mutable write commit points must be bound before authoring guard.')
    m['field_reset_contract']=dict(instances=3136,leaf_port='rst_n',cold_reset_only=True,
        max_fanout=32,minimum_buffer_leaves=98,minimum_tree_levels=3,
        asynchronous_assert_synchronous_release=True,release_sync_FF_per_clock_region=2,
        release_and_launch_guard='Keep source go0 until every region reports reset-release and all forward pipeline stages are clean; no warm reset with accepted work',
        installed=False,reset_root='Explicit external power-on/reset controller; source ABI not yet installed')
    m['gates'].update(physical_route='diagnostic only; parallel exact/upset and mapped-retention gates',
        full_token_adoption=False)
    return m


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))

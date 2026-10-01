#!/usr/bin/env python3
"""Source-bound ordinary GPU packet-fabric/whole-element screening, never admission.

No RTL, clocks, physical jobs or prior verdicts are changed. Every proposed
latency is a compiler modeling contract, not a measured instruction latency.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '4535be1001d69bc43669e0fdf0401896be4034a6'
DFF = .2916
GATE = .2
UTIL = .5
PACK = 1.31
FAST = 1.2e9
SIMD = .9e9


def pinned(rev, path, pins):
    data = subprocess.check_output(['git', 'show', rev + ':' + path], cwd=ROOT)
    full = subprocess.check_output(['git', 'rev-parse', rev], cwd=ROOT, text=True).strip()
    pins.append(dict(source_git=full, path=path, sha256=hashlib.sha256(data).hexdigest()))
    return json.loads(data)


def footprint(bits=0, gates=0):
    return (bits * DFF + gates * GATE) / UTIL / 1e6


def channel(lanes, tracks_per_um):
    # Both directions, complete 320-bit sector packets and four handshake bits.
    tracks = 2 * lanes * (320 + 4)
    return dict(tracks=tracks, routing_utilization=.70,
                width_um=math.ceil(tracks / (tracks_per_um*.70) / 5) * 5,
                payload_Bpc_one_direction=lanes * 32)


def credit_floor(distance_um):
    hops = math.ceil(distance_um / 504)
    # Roundtrip wires, switch/head/write/credit registers, pointer CDC and phase.
    return dict(wire_hops_one_way=hops, route_cycles_one_way=hops + 3,
                no_stall_credit_roundtrip_fast_cycles=2*hops + 5 + 8 + 2,
                required_credits_for_II1=2*hops + 5 + 8 + 2)


def link_calendar(credits, delay, n=1000, stall=0):
    """Finite link credits include queued AND in-flight packets; no hidden slots."""
    free = credits
    flights = []
    sent = received = max_live = 0
    for t in range(100000):
        if flights and flights[0] <= t and t >= stall:
            flights.pop(0)
            received += 1
            free += 1
        if sent < n and free:
            flights.append(t + delay)
            free -= 1
            sent += 1
        assert free + len(flights) == credits
        max_live = max(max_live, len(flights))
        if received == n:
            return dict(done=True, elapsed_fast_cycles=t+1, packets=received,
                        max_live=max_live, credits=credits, speed_credit=0)
    return dict(done=False, packets=received, max_live=max_live, credits=credits)


def compose(lanes=24, credits=128, sm_w=2200, sm_h=3500):
    pins = []
    r3 = pinned('14c57fd85', 'results/rtl/w19_checkpoint_production_20261001/gpu-simd-lowering-candidate-r3.json', pins)
    old = pinned('577d195ba', 'results/uarch/common_gpu_sector_crossbar_20261001/model_before_RTL_r4.json', pins)
    units = pinned(BASE, 'results/arch/arch_budget_v41.json', pins)['unit_areas_um2']
    screens = pinned('f83ba3f6e', 'results/physical_abi3/asap7/gpu/w13_composed_screen_20261001/whole32_model_screen.json', pins)
    small = pinned('14c57fd85', 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json', pins)
    large = pinned('14c57fd85', 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.json', pins)
    sm_macro = small['area']['macro_area_um2'] * PACK / 1e6
    ledger = pinned('7a40179be', 'results/physical_abi3/asap7/gpu/w13_composed_screen_20261001/whole32_once_only_resource_ledger_r1.json', pins)
    service = next(x for x in ledger['once_only_resource_ledger'] if x['resource']=='commonservice corrected400 candidate')
    l2 = next(x for x in ledger['once_only_resource_ledger'] if x['resource']=='L2 publication storage')
    lg_macro = large['area']['macro_area_um2'] * PACK / 1e6
    # Existing SIMT unit charges add+mul only. RF is a separate storage resource.
    assert math.isclose(units['fp32_mac_um2'], units['fp32_add_um2'] + units['fp32_mul_um2'])
    rf = 64 * sm_macro
    # 32 independent banks, each 512 logical F32 words in a padded 128x256 view.
    # bank row=word[8:2], subword=word[1:0]; upper four F32 subwords unused.
    shared = 32 * sm_macro
    shared_mux = footprint(gates=32*32*3 + 32*256, bits=32*(7+2+1+16))
    rf_mux = footprint(gates=8192)
    # Explicit conservative control reservation, not a measured implementation.
    scoreboard = footprint(bits=65536)
    transpose = footprint(bits=3072*8)
    # INT add/compare, shift, F32 compare and warp32 shuffle, separately charged.
    int_cmp_gates = 128 * (32*5 + 32*5 + 32*5 + 24)
    shift_shuffle_mux = 128 * 32 * 5 * 2
    instruction = footprint(bits=128*32*(7+7+5), gates=int_cmp_gates + shift_shuffle_mux)
    divider = footprint(bits=19*64, gates=19*33*5 + 19*32*2)
    extras = dict(RF_storage=rf, RF_depth_mux=rf_mux, scoreboard_control=scoreboard,
                  shared_replacement_increment=shared-2*lg_macro,
                  shared_subword_mux_mask_control=shared_mux,
                  transpose_buffer=transpose, INT_FCMP_shift_shuffle=instruction,
                  one_scalar_divider=divider)
    rows = []
    for model in ('qwen', 'v41'):
        fp = pinned(BASE, f'results/floorplan/hbm_gpu/{model}_hbm_die.json', pins)
        baseline = next(x for x in screens['rows'] if x['model']==model)['analytical_sm_area']['total_mm2']
        cv = channel(lanes, fp['channels_um']['tracks_per_um_v'])
        ch = channel(lanes, fp['channels_um']['tracks_per_um_h'])
        # Whole 8x4 array, central strip carries four quadrant link bundles.
        # 1.5mm north/south bands each reserve L2/service and local fanout.
        root_strip = max(4000, 4*cv['width_um'])
        w = 8*(sm_w+9.008) + 7*cv['width_um'] + root_strip
        h = 4*(sm_h+5.68) + 3*ch['width_um'] + 3000
        core = fp['core_um']
        slot = sm_w*sm_h/1e6
        priced = baseline + sum(extras.values())
        distance = w/2 + h/2
        cf = credit_floor(distance)
        geometry_fit = w <= core['x1']-core['x0'] and h <= core['y1']-core['y0']
        placements = []
        for y in range(4):
            for x in range(8):
                px = core['x0']+x*(sm_w+9.008+cv['width_um'])+(root_strip if x>=4 else 0)
                py = core['y0']+1500+y*(sm_h+5.68+ch['width_um'])
                placements.append(dict(SM=y*8+x, quadrant=(y//2)*2+x//4,
                                       bbox_um=[px,py,px+sm_w,py+sm_h]))
        rows.append(dict(model=model, sm_count=32, whole_slot_um=[sm_w,sm_h],
                         whole_slot_capacity_mm2=slot, array_including_reserved_channels_um=[w,h],
                         baseline_sm_mm2=baseline, explicit_added_costs_mm2=extras,
                         priced_sm_mm2=priced, unallocated_whole_element_margin_mm2=slot-priced,
                         aggregate_slots_mm2=32*slot, vertical=cv, horizontal=ch,
                         geometry_fit=geometry_fit, known_element_area_fit=priced<=slot,
                         root_strip_um=root_strip,
                         reserved_service_bands_mm2=3000*w/1e6,
                         reserved_router_strip_mm2=root_strip*(h-3000)/1e6,
                         analytical_SM_placements=placements,
                         quadrant_service_macro_map=dict(quadrants=4,
                             each=dict(common_data_macros=100, L2_payload_macros=64,
                                       grid=[14,12], unused_grid_positions=4,
                                       pitch_um=[200,90], footprint_um=[2800,1080]),
                             placement='One macro grid per quadrant in its north/south1500um band; remaining band reserves metadata/control/CDC and fanout.',
                             actual_macro_outline_um=[large['area']['macro_width_um'],large['area']['macro_height_um']],
                             status='Analytical actual macro outline packing, not routed floorplan'),
                         credit=cf, credits_fit=credits>=cf['required_credits_for_II1'],
                         sustained_quadrant_budget_Bpc=750,
                         width_fit=lanes*32>=750,
                         map_scope='Full32SM capacity envelope, not an actual LEF or undersized physical proxy.',
                         legacy_dedicated_hub='Not retained as GPU compute; HC/SU/SFU/attention/indexer must lower to explicitly charged ordinary GPU units. No free kernel execution or rate credit.',
                         remaining=['compiler full-program edge/issue/port calendar',
                                    'exact scatter/mask and same-bank collision/forwarding',
                                    'SFU lowering or explicit additional standard-GPU units',
                                    'full router/fanout/clock-cell placement and pin access',
                                    'complete SM actual LEF and contextual SS/FF']))
    # Distributed PC->lane + lane->bank switches, four ordinary quadrants.
    local_mux_bits = 4*(lanes*31*320 + 36*(lanes-1)*320)
    # A conventional inter-quadrant sector switch charges every input candidate.
    root_mux_bits = (4*lanes)*(4*lanes-1)*320
    # Independent bidirectional input buffers: quadrant links and root links.
    fifo_bits = 2*4*lanes*credits*320*2
    state_bits = 2*4*lanes*(math.ceil(math.log2(credits+1))*3+16)*2
    route_hops = max(x['credit']['wire_hops_one_way'] for x in rows)
    pipeline_bits = 2*4*lanes*320*route_hops
    # Explicit request/grant and round-robin control reservation for every
    # local/root input-output pair. Charge registers plus 64 gate equivalents.
    arb_pairs = 4*(32*lanes + lanes*36) + (4*lanes)**2
    arb_bits = arb_pairs*16
    base_network = footprint(bits=fifo_bits+state_bits+pipeline_bits+arb_bits,
                             gates=local_mux_bits+root_mux_bits+arb_pairs*64)
    network_area = base_network*1.25  # clock/fanout/control physical allowance
    network = dict(local_mux_bit_equivalents=local_mux_bits, root_mux_bit_equivalents=root_mux_bits,
                   link_FIFO_payload_bits=fifo_bits, explicit_state_bits=state_bits,
                   charged_wire_pipeline_bits=pipeline_bits,
                   arbitration_pairs=arb_pairs, arbitration_state_bits=arb_bits,
                   clock_fanout_allowance_fraction=.25, footprint_mm2=network_area,
                   topology='Four32PC/9client local addressed fabrics, ordinary four-quadrant packet switch; no all-PC broadcast to144banks.',
                   buffer_scope=f'{credits} credited slots per directed lane include network-flight reservations. Stalls retain all state; no free credits.',
                   scheduling='Addressed virtual-output queues and ordinary matching; 768B/cycle is an aggregate upper capacity, not a guarantee for hotspot traffic. Full-program matching calendar mandatory.',
                   not_priced_or_proven=['actual arbitration/clock/fanout synthesis and placement',
                                        'full-program interquadrant contention and route locality',
                                        'routing-layer pin assignment and extracted timing'],
                   replaces='r4 global crossbar topology only after exact resource replacement proof; never add a composed-die total as a component')
    calendar = link_calendar(credits, max(x['credit']['no_stall_credit_roundtrip_fast_cycles'] for x in rows))
    contract = dict(status='CANDIDATE_COMPILER_CAPS_NOT_MEASURED_HARDWARE',
                    actual_general_SIMT_lanes=0, actual_full_GPU_instruction_latency=None,
                    SMs=32, partitions_SM=4, warp_threads=32, resident_warps_SM=32,
                    logical_RF_KiB_SM=128, physical_RF_KiB_SM=256,
                    RF_read_bits_serial_cycle=8192, RF_write_bits_serial_cycle=4096,
                    RF_read_latency_candidate=2, one_write_slot_per_partition_cycle=True,
                    ADD_MUL_core_latency_candidate=7, ADD_MUL_RF_to_scoreboard_candidate=9,
                    INT_FCMP_core_latency_candidate=7, shuffle_core_latency_candidate=5,
                    divider_count_SM=1, divider_II_candidate=1, divider_core_latency_candidate=19,
                    FMA=False, arithmetic_reordering=False,
                    shared_logical_KiB_SM=64, shared_physical_KiB_SM=128,
                    shared_banks=32, shared_ports_bank='1R1W', shared_B_serial_cycle=128,
                    shared_B_fast_cycle_equivalent=128*SIMD/FAST,
                    shared_read_latency_candidate=2, shared_write_latency_candidate=1,
                    SIMD_hz=SIMD, fabric_hz=FAST,
                    dependent_ADD_MUL_fast_cycles_candidate=12,
                    macro_SS_clk_to_q_ps=dict(RF_shared=small['timing']['ss']['clk_to_q_ps'],
                                            gather_queue=large['timing']['ss']['clk_to_q_ps']),
                    all_instruction_and_macro_timing_requires_contextual_SS_FF=True,
                    mask_read_write_collision='stall or forward required committed value; pre-write macro read is not completion',
                    measured_negative='TC16 source000ba0898 SSsetup-31.06ps; no transfer, retry or clock qualification')
    for row in rows:
        row['network_reservation_fit'] = network_area <= row['reserved_router_strip_mm2']
        row['common_service_and_L2_packed_mm2'] = service['incremental_commonservice_mm2_die'] + l2['packed_SRAM_mm2_die'] + l2['controller_mm2_die']
        row['service_reservation_fit'] = row['common_service_and_L2_packed_mm2'] <= row['reserved_service_bands_mm2']
    feasible = all(x['geometry_fit'] and x['known_element_area_fit'] and x['width_fit'] and x['credits_fit'] and x['network_reservation_fit'] and x['service_reservation_fit'] for x in rows)
    return dict(schema='opentallas.w13.ordinary_gpu_distributed_fit.v1', source_pins=pins,
                candidate_only=True, default_enabled=False, adopt=False,
                coarse_resource_candidate=feasible, physical_build_ready=False,
                full_program_ready=False, physical_admission='FAIL_CLOSED_PENDING_FULL_COMPOSITION',
                clock_targets_unchanged=True, rows=rows, network=network,
                analytical_assumptions=dict(DFF_um2_per_bit=DFF, gate_um2=GATE,
                    cell_placement_utilization=UTIL, macro_packing_factor=PACK,
                    assumed_wire_stage_span_um=504,
                    wire_stage_span_status='Sizing hypothesis, not measured wire delay or timing-qualified pipeline. Shorter span requires more credits, buffers and latency; full-program calendar must price it.',
                    port_matching_status='Candidate addressed queues and ordinary arbitration; aggregate capacity does not guarantee adversarial or full-program throughput.'),
                link_credit_calendar=calendar, compiler_contract=contract,
                historical_57_corridor_failure_preserved=True,
                largest_open_gate='Full-program ordinary GPU edge/port calendar and actual complete element pin/fanout/contextual timing',
                no_new_hardware=True, speed_credit=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--lanes',type=int,default=24)
    p.add_argument('--credits',type=int,default=128)
    a=p.parse_args()
    result=compose(a.lanes,a.credits)
    result['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'coarse_candidate':result['coarse_resource_candidate'],
                      'physical_admission':result['physical_admission']}))


if __name__=='__main__':
    main()

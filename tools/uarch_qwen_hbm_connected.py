#!/usr/bin/env python3
"""Compose baseline Qwen GPU token integration before adding controller RTL.

Uses the unified model and its existing macro/floorplan inputs. This is an
integration sizing record, never a token, clock or adoption verdict. New
controllers must implement these ports and the activation/KV causality rules.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import uarch_model as U
from hdc_qwen_fullshape_placement_w12 import placement, TP

ROOT = Path(__file__).resolve().parents[1]


def compose():
    if TP != 2:
        raise ValueError('The GPU comparator is the shipped TP2 arithmetic contract')
    design = U.hbm_gpu_design('qwen')
    fp = json.loads((ROOT/'results/floorplan/hbm_gpu/qwen_hbm_die.json').read_text())
    mats = [m for m in placement()['matrices_per_die']
            if m['name'].startswith('L00.') or m['name'] == 'lm_head']
    clock, serial, sm, line = 1.2e9, .9e9, 32, 128
    leaf, trunk = fp['barrier_network']['leaf_cycles'], fp['barrier_network']['trunk_cycles']
    wire = next(x['cycles_one_way'] for x in fp['crossings'] if x['name']=='weight_phy_to_sm')
    latency = math.ceil(U.HBM_LOADED_LAT_NS*1e-9*clock) + 2*wire + 2
    # Retain 512 credits. Price worst jitter rather than silently increasing
    # credits or claiming the assumed bandwidth closes in a real controller.
    worst = latency + 55
    credit_Bpc = sm * 512 * line / worst
    requested_Bpc = 3.6e12 / clock
    served_Bpc = min(requested_Bpc, credit_Bpc)
    boundary = 2*(leaf+trunk)+3
    ops = U.qwen_hbm_ops(design['element'], boundary+16, design['drain_cycles'])
    base_cycles, _ = U.stream_overlap(ops, served_Bpc, sm*line,
                                     design['staging_kb_per_sm']*1024*sm)
    import arch_budget_qwen3 as Q
    exchange = Q.tp_exchanges(Q.clock_hz())['per_exchange_cycles']
    vector_cycles = sum(t for _,t in ops) - 181*(boundary+16+design['drain_cycles']) \
                    - 36*design['drain_cycles'] - 72*exchange
    assert vector_cycles >= 0
    serial_extra = math.ceil(vector_cycles*(clock/serial-1))
    # Explicit initial baseline costs. They may be replaced only by matched
    # connected measurements; they cannot vanish into a host callback.
    vector_hop = next(x['cycles_one_way'] for x in fp['crossings']
                      if x['name']=='x_broadcast_root_to_sm')
    vector_CDC = 8                 # request and completion: four fast cycles each
    vector_network = 252*(2*vector_hop+vector_CDC)
    result_commit = 181*(leaf+2)  # local result route plus two-cycle L2 commit
    format_selector = 181*2       # decode/subtree selector pipeline, no changed K order
    rows = []
    for m in mats:
        maxrows = math.ceil(m['rows']/sm)
        active = min(128, m['split'])
        groups = m['split']//active
        assert m['split'] % active == 0 and m['columns'] % m['split'] == 0
        tiles = math.ceil(maxrows/256)
        rows.append(dict(name=m['name'], rows_die=m['rows'], rows_max_sm=maxrows,
                         K=m['columns'], golden_split=m['split'], active_leaves=active,
                         independent_rows_per_weight_line=2 if active==64 else 1,
                         K_groups=groups, products_per_chunk=m['columns']//m['split'],
                         row_tiles_256=tiles, tail_rows=maxrows-(tiles-1)*256,
                         descriptor_count_per_sm=tiles, bulk_copy_descriptors_per_sm=1,
                         scale_bytes_die=2*m['rows'], scale_preload_cycles=maxrows,
                         scale_storage_bytes_sm=8192,
                         tile_transition_cycles=4*(tiles-1),
                         global_barriers_per_matrix=1,
                         needs_exact_subtree_bypass=active==64))
    transition = 36*sum(r['tile_transition_cycles'] for r in rows[:4])+rows[-1]['tile_transition_cycles']
    scale_excess = 36*sum(max(0,r['scale_preload_cycles']-latency) for r in rows[:4]) \
                   + max(0,rows[-1]['scale_preload_cycles']-latency)
    # Two 128B elastic packets per client (one request, one response), 36
    # clients: 32 SM weight ports and one L2/vector/KV injector per quadrant.
    clients, packet_bits = 36, 1024+32+16+4
    fifo_bits = clients * 2 * packet_bits
    ctl_bits = clients*(10+4+1) + 4*(10+4)
    hub_area = (fifo_bits+ctl_bits)*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6
    physical = dict(physical_SM_count=32, tensor_lanes_per_SM=128, columns_per_SM=16,
                    active_AR_columns=1, SIMT_lanes_per_SM=128,
                    physical_MACs_per_fast_cycle=32*128*16,
                    active_QKV_MACs_per_fast_cycle=32*128,
                    active_GU_MACs_per_fast_cycle=32*2*64,
                    lane_local_register_bytes_per_SM=64*1024)
    blocks = dict(
        shared_HBM_NoC=dict(replicas=4, clients_per_quadrant=9,
            memory_line_bytes=128, data_Bpc_per_quadrant=served_Bpc/4,
            requested_Bpc_per_quadrant=750, credits_per_client=512,
            request_metadata_bits=52, response_packet_bits=1044,
            physical_request_and_return_lanes_per_quadrant=9,
            arbitration='Read requests consume credits; read data and write data share one byte budget. Write acknowledgements consume no data budget.',
            multiplexer_cost='9-way grant/route per quadrant; per-SM weight routes stay quadrant-local',
            fanout='No weight broadcast across dies or quadrants; L2 injector shares controller capacity',
            elastic_packet_bits=fifo_bits, control_bits=ctl_bits,
            footprint_mm2_estimate=hub_area, setup_cycles=2,
            loaded_round_trip_cycles=latency, worst_jitter_cycles=55),
        L2_vector=dict(replicas=4, bytes_per_slice=2*1024*1024,
            gather_bits_per_SM=256, broadcast_bits=2048,
            read_Bpc_per_slice=256, write_Bpc_per_SM=32,
            reduction_order='Golden chunk8/tree order, carried by explicit row/leaf indices; arrival order never defines the arithmetic tree',
            mux_demux='32 addressed producers, four banked slices, 32 addressed consumers',
            barrier='Release only after every actual result is committed; no host gather or fixture insertion'),
        SIMT_SFU=dict(replicas=32, lanes_per_SM=128, clock_hz=serial,
            local_read_Bpc_per_SM=3*128*4, local_write_Bpc_per_SM=128*4,
            tree_levels_4096=12, tree_levels_128=7,
            rounding='Preserve norm scalar, row scale, ordered TP reduction, post-TP scale and FP8 KV conversion as separate golden points',
            CDC='Producer/results FIFO between fast1.2GHz and serial0.9GHz, four fast cycles each way',
            CDC_fast_cycles_per_operation=vector_CDC,
            network_fast_cycles_per_operation=2*vector_hop,
            serial_clock_extra_fast_cycles_per_token=serial_extra),
        row_descriptor=dict(replicas=32, rows_per_tile=256, global_row_bits=18,
            logical_scale_rows_per_SM=4096, physical_scale_bytes_per_SM=8192,
            local_tile_transition_cycles=4, whole_operation_barriers=1,
            transport='One uninterrupted bulk-copy descriptor covers all row tiles; ring is not reset or refetched at tile boundaries',
            addressing='RTL global row offset addresses L2 and scale SRAM; RTL argmax uses global row for ties',
            alternatives=dict(resize_RMAX4096=dict(tile_transitions=0,
                coverage='Template default is4096, but existing RMAX256 gate is not head coverage; new in-context gates required'),
                selected='256-row RTL tiling with global offsets, continuous weight stream and one final barrier')),
        GU_exact64=dict(replicas=32,physical_lanes=128,independent_rows_per_issue=2,
            active_leaves_per_row=64,weight_Bpc=128,
            arithmetic='Two disjoint64-leaf trees, each preserving its row golden; bypass128-leaf combine, never add padding or combine rows',
            x_fragment_bits_per_column=128*16,
            row_scale='16-entry addressed result FIFO serializes the two-row bursts through the existing row-scale multiplier; original rounding preserved',
            result_FIFO_bits_per_SM=16*(16*32+18+16),
            result_FIFO_footprint_mm2_per_SM=16*(16*32+18+16)*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6,
            exposed_last_pair_cycles_per_token=72,
            gate='New format/subtree/row metadata path needs exactness and in-context SS/FF; current W13 does not qualify it'),
        KV_attention=dict(replicas=32,weight_line_B=128,
            formats=dict(BF16=dict(active_lanes=64,weight_B_per_lane=2),
                         FP8_E4M3=dict(active_lanes=128,weight_B_per_lane=1)),
            arithmetic='Interleaved attention chunks and empty+0 leaves in the golden order, not contiguous dense K grouping',
            writer='RTL-produced K/V rounded toFP8, coalesced as actual128B head rows and committed through shared HBM',
            gate='No host-produced current-token KV; format and interleaved-tree gates required'))
    routes = dict(weight_vertical=dict(bits=1088, capacity=fp['channels_um']['v_wires']),
                  vector_horizontal=dict(bits=2048+256+64, capacity=fp['channels_um']['h_wires']),
                  assignment='Separate shoreline/quadrant weight corridors and central vector corridors; a shared vertical corridor would overflow and is forbidden',
                  gate='Analytical corridor allocation only; composed hub routing-layer gate and SS/FF remain mandatory')
    assert routes['weight_vertical']['bits']<=routes['weight_vertical']['capacity']
    assert routes['vector_horizontal']['bits']<=routes['vector_horizontal']['capacity']
    sources = ['tools/uarch_model.py', 'tools/uarch_qwen_hbm_connected.py',
               'tools/hdc_qwen_fullshape_placement_w12.py', 'tools/hdc_golden.py',
               'results/floorplan/hbm_gpu/qwen_hbm_die.json', 'results/arch/qwen3_budget.json',
               'results/physical_abi3/asap7/gpu/ot_gpu_tc_col_l16_092/physical.json',
               'results/physical_abi3/asap7/gpu/ot_gpu_bd_col_lb2_092/physical.json']
    return dict(schema='opentallas.qwen-hbm-connected-sizing.v1',status='model_before_controller_RTL',
        base_design=design, physical=physical, blocks=blocks, matrix_contracts=rows,
        ports_and_routes=routes,
        floorplan_fit=dict(existing_mm2=design['die_fit']['used_mm2'],
            new_controller_mm2=hub_area,
            GU_result_FIFO_mm2=32*blocks['GU_exact64']['result_FIFO_footprint_mm2_per_SM'],
            available_mm2=design['die_fit']['core_avail_mm2'],
            fits=design['die_fit']['used_mm2']+hub_area+32*blocks['GU_exact64']['result_FIFO_footprint_mm2_per_SM']<=design['die_fit']['core_avail_mm2']),
        latency=dict(fast_clock_target_hz=clock,serial_clock_target_hz=serial,
            assumed_HBM_bytes_s=3.6e12,credit_limited_worst_case_bytes_s=served_Bpc*clock,
            composed_stream_cycles_estimate=math.ceil(base_cycles),
            row_tile_transition_cycles_per_token=transition,scale_preload_excess_cycles=scale_excess,
            serial_clock_extra_cycles=serial_extra,
            vector_network_and_CDC_cycles=vector_network,
            result_commit_cycles=result_commit,format_selector_cycles=format_selector,
            GU_last_pair_cycles=72,
            token_cycles_estimate=math.ceil(base_cycles)+transition+scale_excess+serial_extra+vector_network+result_commit+format_selector+72,
            row_tiling_vs_RMAX4096_extra_cycles=transition,
            note='Conservative sizing estimate, not a headline. Explicit serial-clock, vector-network, CDC, result-commit and format-selector costs are added without claiming overlap. Replace only with matched connected measurements.'),
        causality=dict(activation='RTL result -> L2 commit -> RTL norm/vector/attention/residual -> next layer -> head',
            KV='RTL-produced current-token K/V -> FP8 RTL writer -> same shared HBM service -> later attention read',
            fixtures='Host may initialize checkpoint weights/constants and starting token state; no host activation, norm, gather, K/V or inter-layer replacement',
            acceptance='All36layers+head, actual32SMs perTP2die, golden checkpoints and token, realistic shared-memory traffic, contextual routing and SS/FF'),
        prerequisite_gates=['Active64 GU subtree bypass (no K rechunking/padding)',
            'INT8/BF16/FP8 KV format-compatible SM and interleaved attention tree order',
            'RTL row tiling/global scale/result offsets and head argmax ties',
            'Connected shared HBM/L2/NoC/barrier and actual vector/KV/TP producer-consumer execution'],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        full_token=False,adoption=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    rec=compose()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x') as f:json.dump(rec,f,indent=2,sort_keys=True);f.write('\n')


if __name__=='__main__':main()

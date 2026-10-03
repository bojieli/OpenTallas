#!/usr/bin/env python3
"""HA2 sizing extension of the unified analytical model; no adopted rows."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import ast
ROOT = Path(__file__).resolve().parents[1]
# Read the pinned unified-model constant without importing its unrelated physical inventories.
_UARCH_AST = ast.parse((ROOT / 'tools/uarch_model.py').read_text())
DFF_UM2 = next(ast.literal_eval(n.value) for n in _UARCH_AST.body
               if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DFF_UM2' for t in n.targets))

def tree(leaves):
    """Adjacent-pair tree, odd tail bypassed, without inserting zero leaves."""
    levels = []
    nodes = list(leaves)
    while len(nodes) > 1:
        nxt = []
        level = []
        for i in range(0, len(nodes), 2):
            pair = nodes[i:i+2]
            level.append(pair)
            nxt.append(pair)
        levels.append(level)
        nodes = nxt
    return levels

def peer(rank, port):
    group, lane = divmod(rank, 16)
    if port < 15:
        return group * 16 + port + (port >= lane)
    other = port - 15
    return (other + (other >= group)) * 16 + lane

def price():
    # Transferred unit rates from the 42-lane/die ablation budgets, NOT PHY characterization.
    lanes = 40
    period = 1e9 / 1.2e9
    wire = math.ceil(14000 / 430)  # ESTIMATE 14 mm endpoint-to-PHY; addendum's <=430 um stages
    record_bits = 512 + 32 + 7
    bits_cycle = 2 * 112e9 * 257 / 272 / 1.2e9
    serialization = math.ceil(record_bits / bits_cycle)
    hop = 2 * wire + math.ceil(130 / period) + serialization
    snapshot_bits = 96*512 + 6*record_bits + 6*15 + 20 + 96
    mux_bits = 15*record_bits*5   # six-source mux per local TX, five 2:1 mux equivalents/bit
    wire_bits = 20*2*wire*record_bits
    reg_mm2 = (snapshot_bits + wire_bits) * DFF_UM2 / 1e6
    fixed_gather = 2*hop + 3 + 96
    fixed_ar = fixed_gather - 96 + 7*7 + 1  # ESTIMATE LAT7, seven levels; exact program gate pending
    baseline = 1e6 / 2261.7
    saved_us = (225*(777-fixed_gather*period) + 40*(824-fixed_ar*period))/1000
    pins = ['tools/uarch_model.py', 'tools/w19_hbm_tp96_isa.py',
            'rtl/chip/ot_coll_topk_merge.sv', 'tools/w15_collectives.py']
    return dict(schema='opentallas.ha2.price.v1', status='ESTIMATE', adopt=False,
        provenance={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
        model_scope={'v41_hbm':'96 ranks', 'qwen_hbm':'not sized by HA2',
                     'v41_rom':'unchanged', 'qwen_rom':'unchanged'},
        topology=dict(ranks=96, groups=6, group_size=16, local_ports=15, global_ports=5,
                      full_duplex_links=960, ports_per_die=20, lanes_per_port=2, lanes_per_die=lanes),
        ports=dict(record_bits=record_bits, payload_bytes=64, lane_gbps=112,
                   fec_efficiency=257/272, payload_bits_per_cycle=bits_cycle,
                   serialization_cycles=serialization, snapshot_read_bytes_per_cycle=64,
                   local_write_bytes_per_cycle=15*64, global_write_bytes_per_cycle=5*64,
                   total_receive_bytes_per_cycle=20*64, wire_boundary_bits_per_cycle=20*record_bits),
        timing=dict(clock_hz=1.2e9, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                    endpoint_to_phy_um=14000, max_stage_um=430, wire_stages_each_side=wire,
                    phy_fec_ns=130, phy_fec_grade='ESTIMATE: tools/w15_collectives.py board_112g.adopted_hop_ns',
                    modeled_link_cycles=hop, serialization_cycles=serialization,
                    credit_return_cycles=hop, cdc_cycles=None,
                    cdc_status='PENDING: same-clock transport bench; system CDC excluded from measured claim'),
        compute=dict(macs_per_cycle=0, fp32_adders_per_lane_per_die=95,
                     reduction_levels=7, adder_latency_cycles=7, arithmetic_area_mm2=None,
                     exact_tree='adjacent pairs, odd tail pass; W19 uses separate 8-leaf trees, no extra zero leaves'),
        area=dict(serdes_mm2=lanes*18/42, serdes_budget_mm2=18,
                  serdes_grade='ESTIMATE transferred budget divided by 42 lanes (arch_budget_v41)',
                  snapshot_register_bits=snapshot_bits, wire_register_bits=wire_bits,
                  dff_cell_mm2=reg_mm2, register_floorplan_mm2_at_70pct=reg_mm2/.7,
                  mux_2to1_bit_equivalents=mux_bits, mux_area_mm2=None,
                  tx_fanout=20, relay_fanout=15, port_replica_count=20,
                  routing_tracks_required=20*record_bits, corridor_capacity_tracks=None,
                  fit='PENDING: excludes mux, adders, clock/PG, repeaters and PHY overhead'),
        power=dict(serdes_w=lanes*33/42, budget_w=33,
                   grade='ESTIMATE transferred budget; excludes endpoint/wires/clock', endpoint_w=None),
        latency=dict(gather_fixed_cycles_estimate=fixed_gather,
                     gather_fixed_ns_estimate=fixed_gather*period,
                     ar_fixed_ns_estimate=fixed_ar*period,
                     gather_payload_slope_cycles_per_rank_word=None,
                     per_token_saved_us_estimate=saved_us,
                     per_user_gain_pct_estimate=100*(baseline/(baseline-saved_us)-1),
                     status='UNVALIDATED; no system latency/adoption credit'))

def compile_plan(kind):
    if kind == 'w19_oreduce':
        return dict(kind=kind, rounding='FP32 RNE per edge, BF16 once after each 8-leaf tree',
                    trees=[tree(range(g*8,g*8+8)) for g in range(8)],
                    dest=list(range(96)), zeros_inserted=False)
    if kind == 'ar96':
        return dict(kind=kind, tree=tree(range(96)), rounding='FP32 RNE per edge',
                    dest=list(range(96)), golden_program_gate='PENDING')
    return dict(kind=kind, sources=list(range(96)), dest=list(range(96)),
                order='rank-major, score/ID words kept separate', candidates_per_rank=512,
                candidate_buffer_bytes=96*512*8, topk='reuse ot_coll_topk_merge N=96,NMAX=512')

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists(): raise SystemExit('refuse to overwrite evidence')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(dict(price=price(), compiler={k:compile_plan(k) for k in
        ['gather','ar96','w19_oreduce','topk']}, peers=[[peer(r,p) for p in range(20)] for r in range(96)]),indent=2)+'\n')

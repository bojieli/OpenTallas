#!/usr/bin/env python3
"""Source-bound HA2 replacement price; no inference or adoption credit."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def model():
    record = json.loads((ROOT / 'results/rtl/ha2_owner_reducer_takeover_20261005/takeover.json').read_text())
    price = record['parent_adapter_prebuild_price']
    price['prebuild_quiet_ff_reservation'] = price['quiet_monitor_counter_ff']
    price['quiet_monitor_counter_ff'] = 6 + 16 + 2
    price['total_added_ff'] = 4113 + 122 + price['quiet_monitor_counter_ff']
    price['ff_cell_area_floor_um2'] = price['total_added_ff'] * .2916
    price['new_cdc'] = 1
    price['new_payload_cdc'] = 0
    price['new_control_cdc'] = 'one PHY-quiet bit through two core-domain synchronizer FF; drain latency phase-dependent, unmeasured'
    price['quiet_price_detail'] = '6 pending FF +16 delivered-word FF +2 PHY-quiet sync FF; expected count combinational; conservative prebuild reserve93 retained separately'
    price['selection'] = dict(NC=8, NOG=8, BF16=1, PFMAX=384, NPT=8,
        INJ=2, DEL=4, LANES=16, LAT=7, SLOTREG=1, HUBW=35, WSTG=14,
        QAW=6, TXAW=6, RXAW=8, SWCRED=256)
    price['historical_matched_hub'] = price.pop('configurations')[-1]
    price['context_lifetime'] = ('Bound tuple drives all queues/reduction until real positive local quiet; '
        'shared8 alone grants next go after matching fabric release and publication. '
        'go rearms pres/rptr/transaction counters; never resets FIFO/CDC pointers or credits.')
    price['quiet_observation'] = ('Explicit delay-valid OR and AFIFO write-empty outputs; '
        'no private hierarchy taps, added payload registers, or change to pointer advancement.')
    price['memory_bytes_per_cycle'] = dict(own_payload_write_max=128, peer_payload_write_max=512, operand_read=512, result_payload=64)
    price['logical_write_sources'] = 10
    price['operand_presence_shape'] = [8,48]
    price['operand_registers_bits'] = 196608
    price['replicated_adder_nodes'] = 112
    price['area_estimate_um2'] = 183000 + (196608-32768)*.2916
    price['area_estimate_label'] = 'ESTIMATE: old PF64 synth plus incremental operand DFF floor; runtime mux/decoder/buffering and enclosing queues excluded'
    price['parent_area_scope'] = 'replaces embedded array/tree, not a second reducer'
    price['rank_contract'] = 'shared8 rank<96; AR rank64..95 receive only, never inject/reduce'
    price['macs_per_cycle'] = 0
    price['fp32_adds_per_issue'] = 7 * 16
    price['golden_tree'] = 'three levels adjacent rank pairs, FP32 rounding at every node, final BF16 RNE'
    price['steady_issue_interval_cycles'] = 1
    price['slotreg_added_cycles_per_flit'] = 1
    price['route_variants'] = [dict(utilization=u, PFMAX=384, NC=8, NPT=8, INJ=2)
        for u in (25, 30, 35)]
    price['routing_tracks_needed'] = None
    price['channel_capacity'] = None
    price['floorplan_slot_fit'] = None
    price['serial_critical_path_including_wire_CDC_credit_refresh_ns'] = None
    price['composed_token_gain_fraction'] = None
    price['qualification'] = 'UNVALIDATED; component exactness and parent physical/context gates pending'
    paths = ['rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv',
        'rtl/hbm_accel/integration/ot_hbm_tu_shared8.sv',
        'tools/hbm_accel_shared_join_model.py', 'tools/dshbm_1m_coll.py']
    price['current_authority_sha256'] = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    return price

if __name__ == '__main__':
    print(json.dumps(model(), indent=2, sort_keys=True))

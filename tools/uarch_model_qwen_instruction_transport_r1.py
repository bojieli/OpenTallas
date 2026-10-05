"""Selected, default-off extension of the unified Qwen microarchitecture model.

Prices the literal NW18/AW24 W12 instruction transport before RTL authoring.
No arithmetic, baseline source or headline latency is changed by import.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def price(stations=1536):
    facts=json.loads((ROOT/'results/rtl/qwen_rom_fulldie_20261003/k16_demand_r1/inputs/SS_cell_prices.json').read_text())
    ff=facts['facts']['DFFASRHQNx1_ASAP7_75t_R']['SS']
    bits=2*216+432+72  # two protected 190-bit beats, protected 379-bit assembly, control64
    body=bits*stations*ff['area_um2']
    head_bits=64*(432+3*432+4*72)
    return dict(schema='QWEN_W12_TWO_BEAT_MODEL_R1',default_off=True,
        unified_model_sha256=hashlib.sha256((ROOT/'tools/uarch_model.py').read_bytes()).hexdigest(),
        source_width=dict(NW=18,AW=24,packed_instruction_bits=3*18+13*24+13),
        stations=stations,MACs_per_cycle=0,memory_ports=dict(sender_write_bits_per_accept=432,
          sender_read_bits_per_beat=216,receiver_write_bits_per_beat=216,receiver_read_bits_per_cycle=432,
          control_read_write_bits_per_cycle=72),
        boundary=dict(data_bits_per_cycle=190,beat_valid=1,beat_last=1,beat_ready=1,
          reset_bits=64,clock_bits=64,go_bits=1,x_bits=128,x_ready_bits=1,
          corridor_bits_before=637,corridor_bits_after=451,tap_bits_before=511,tap_bits_after=325,
          k16_corridor_nets_before=40,k16_corridor_nets_after=29,
          link_spine_bits_before=2112,link_spine_bits_after=2112,
          link_spine_hotspot_relief_credited=0),
        state=dict(raw_payload_bits=759,protected_bits_per_station=bits,protected_bits_total=bits*stations,
          control_bits_physically_stored=72,one_instruction_outstanding_per_station=True,
          column_heads=64,head_branch_acceptance_source='UNKNOWN: three-way north/south/head-chain fanout acceptance ledger required',
          conservative_added_head_state_bits=head_bits),
        cost=dict(FF_body_mm2=body/1e6,logic_proxy_mm2=.5*body/1e6,
          slot_mm2_at_50pct=3*body/1e6,slot_capacity_mm2=stations*52.704*69.12/1e6,
          conservative_head_FF_body_mm2=head_bits*ff['area_um2']/1e6,
          conservative_head_slot_mm2_at_50pct=3*head_bits*ff['area_um2']/1e6,
          conservative_total_slot_mm2_at_50pct=3*(body+head_bits*ff['area_um2'])/1e6,
          head_clock_pin_load_SS_fF=head_bits*ff['pins']['CLK']['cap_fF'],
          clock_pin_load_SS_fF=bits*stations*ff['pins']['CLK']['cap_fF'],
          muxes='sender 2:1 x216; receiver SECDED decode 6x72 and encode 6x64; control decode/encode 1x72',
          fanout='each ready/valid point-to-point; real tree branch/clock/reset buffer census required',
          old_state_debit=0,logic_proxy_measured=False,codec_timing_qualified=False),
        latency=dict(accept_to_first_beat_cycles=1,accept_to_second_beat_cycles=2,
          accept_to_consumer_earliest_cycles=3,per_hop_extra_instruction_cycles_over_1beat=1,
          data_return_and_x_network_cycles_changed=0,
          token_delta='sum selected instruction path hop counts + finite stall/consumer retirement; exact source program/map required',
          warm_fence='wait accepted beats, actual consumer retirement and all_copy_drained; no timer or debt discard',
          retirement_source='must be identity-qualified by the actual caller; bare retirement level cannot distinguish a stale ACK during a new issued instruction',
          cold_reset='destructive power-on only; warm request never asserts cold reset'),
        clocks=dict(stream_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        physical=dict(hard_reticle_mm2=858,full_die_IR_required=True,
          reserve_M9_from_actual_PDN_geometry=True,core_fixture_IR_is_not_die_PASS=True,
          after_route_demand_capacity=None,unchanged_link_spine_hotspot_remains=True),
        admission='component RTL authoring/static exact transport gate only; full system caller and changed route not yet admitted')

if __name__=='__main__':print(json.dumps(price(),indent=2))

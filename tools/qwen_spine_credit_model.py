#!/usr/bin/env python3
"""Finite Qwen spatial tree shell, sized before RTL; no adopted rate credit."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    src='results/uarch/qwen_body_wire_latency_20261003/study.json'
    prior=json.loads((ROOT/src).read_text())
    ops=prior['decomposition']['me_ops']
    body=[r for r in ops if r['op'] in ('QKV_ME','O_ME','GU_ME','down_ME')]
    burst=max(r['rounds']*8 for r in body)
    slots=1<<(burst-1).bit_length()
    # Worst wire RTT is conservatively the retained whole-body112, not a new guessed short lane wire.
    local_latency=46
    return dict(schema='opentallas.qwen-spine-credit-model.v1',adopted=False,
        sources_sha256={src:hashlib.sha256((ROOT/src).read_bytes()).hexdigest()},
        lanes=16,words_per_lane=48,bits_per_packet_per_lane=1536,tag_bits=32,
        MACs_per_cycle=0,FP32_adds_per_cycle_per_lane=46,
        storage=dict(result_slots=slots,basis=f'max body operation emits{burst} lane packets: max rounds3 times IL8; next power of two{slots}',
            input_credits=slots,downstream_initial_credits=2,
            reservation='One input credit reserves one result slot across capture, all arithmetic stages and output staging; return only when registered output launches',
            payload_FF_bits=slots*1536,metadata_FF_bits=slots*32,
            registered_mux_bits=(8+2+1)*1536,SRAM_macros=0),
        ports=dict(input_bits_per_cycle=1536+32+4+1,output_bits_per_cycle=1536+32+1,
            credit_bits_each_direction=1,memory_bytes_per_cycle=0),
        routing=dict(frame_um=[600.048,600.048],max_side_um=1000,
            per_data_side_pins=1536,signal_tracks_available_at_pitch064=int(570/.064),
            passes_local_pin_capacity=True,hub_layer_check='pending actual die lane transpose'),
        area=dict(additional_FF_um2=(slots*(1536+32)+(8+2+1)*1536)*.2916,
            tree_historical_area_proxy_um2=30358.243,die_16_replica_reserved_mm2=16*.600048**2),
        latency=dict(arithmetic_cycles=41,external_capture_and_output_stages=5,
            local_packet_cycles_bound=local_latency,
            retained_whole_body_wire_roundtrip_bound=112,
            input_credit_roundtrip_upper_bound=local_latency+112,
            credits_needed_for_full_one_packet_per_cycle=local_latency+112,
            full_rate_credit_window=False,
            body_complete_operation_burst_fits=True,
            serial_packet_extra_cycles_upper_bound=local_latency+112,
            body_packets_per_token=36*sum(r['rounds']*8 for r in body),
            conservative_body_extra_cycles_bound=36*sum(r['rounds']*8 for r in body)*(local_latency+112),
            head_bound='head packets *158; exact head packet count remains required for adopted token rate',
            adoption_gate='Recompose actual body/head packet schedule and measured shell latency. Bound deliberately assumes every packet serialized with full112 wire RTT.'),
        exactness='Same adjacent-pair FP32 tree; level valid and select are generated from each captured split and transaction tag. All48 held positions retire. FIFO drains in arrival order. Remote stalls only consume reserved credits.',
        finite_flow='32 outstanding input reservations; two prepaid downstream credits. Arbitrarily delayed credit return stalls without dropping or overwriting packets. Reset flush requires simultaneous peer credit reset.')
if __name__=='__main__':
 print(json.dumps(model(),indent=2))

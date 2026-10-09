#!/usr/bin/env python3
"""Size the Qwen HBM embedding path before physical implementation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def model(strip_side_um=600.0, pin_pitch_um=0.096, pin_layers=2, usable_edge_fraction=0.75):
    if strip_side_um <= 0 or pin_pitch_um <= 0 or pin_layers < 1 or not 0 < usable_edge_fraction <= 1:
        raise ValueError('positive dimensions/layers and usable edge fraction in (0,1] required')
    measured = json.loads((ROOT/'results/arch/emb_hbm_20261008/takeover/summary.json').read_text())
    die = json.loads((ROOT/'results/arch/emb_hbm_20261008/r21c_die.json').read_text())
    replicas = dict(gateway=1, strip=4, controller=128, pcport=128)
    frames = dict(gateway_hub=[567.216,567.216], strip=[strip_side_um,strip_side_um],
                  controller=[247.536,370.44], pcport=[116.64,116.64])
    demand = 32*(258+1)
    capacity = int(strip_side_um/pin_pitch_um*pin_layers*usable_edge_fraction)
    paths = ['results/arch/emb_hbm_20261008/takeover/summary.json',
             'results/arch/emb_hbm_20261008/r21c_die.json']
    paths += ['rtl/qwen_sys/emb_hbm_20261008/'+p.name
              for p in sorted((ROOT/'rtl/qwen_sys/emb_hbm_20261008').glob('*.sv'))]
    paths += ['physical/qwen_die_masters/cfg/'+p+'.env' for p in
              ('qfd_hub_emb','qfd_ctrl_emb_00','qfd_emb_pcport','qfd_emb_strip','qfd_emb_strip_w600')]
    return dict(schema='opentallas.qwen.embedding_hbm_closure.v1', adopted=False, physical_closed=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        MACs_per_cycle=0, compute_intensity_MAC_per_byte=0,
        communication_intensity='One 4098-byte exact released row per generated token per compute die; no layer multiplier',
        storage=dict(rows=151936,hidden=4096,code_bytes=151936*4096,scale_bytes=151936*2,
                     payload_bytes=151936*4098,allocated_HBM_bytes_per_copy=149*128*32*1024,
                     copies_per_die=1,twin_default=False,ECC='mutable HBM SECDED72, 32 check bits per 256 payload bits'),
        memory_port_bytes_per_cycle=dict(each_PC_read_payload_peak=32,each_PC_write_payload_peak=32,
                                         each_PC_ECC_sideband_peak=4,SU_read_payload_peak=64),
        boundary_bits_per_cycle=dict(SU_request=26,SU_response=513,SU_credit=1,
                                     each_link_word_each_direction=528,each_PC_return=259,
                                     strip_return_face=32*259,strip_PC_command_fanout=32),
        replica_count=replicas,
        replica_mux_demux_cost=dict(request_broadcast_replicas=4,PC_command_fanout=32,
                                   strip_code_gather_pairs=16,strip_scale_select_inputs=32,
                                   hub_stack_select_inputs=4,selected_response_width_bits=512),
        routing=dict(pin_pitch_um=pin_pitch_um,pin_layers=pin_layers,usable_edge_fraction=usable_edge_fraction,
                     strip_left_demand_tracks=demand,strip_left_capacity_tracks=capacity,
                     strip_left_planned_fit=demand<=capacity,
                     legacy_strip_side_um=414.72,
                     legacy_strip_capacity_tracks=int(414.72/pin_pitch_um*pin_layers*usable_edge_fraction),
                     legacy_strip_planned_fit=False,
                     assumptions='Conservative pin-side planning only; verify actual layer access and pin placement in route. Die corridors and 100um final boundary wires remain OPEN.'),
        area=dict(frames_um=frames,strip_total_frame_mm2=4*strip_side_um**2/1e6,
                  strip_frame_delta_vs_414p72_mm2=4*(strip_side_um**2-414.72**2)/1e6,
                  existing_r21c_die_mm2=die['die_mm2'],existing_reticle_margin_mm2=die['margin_mm2'],
                  freed_embedding_reservation_mm2=11.046,utilisation_target=0.55,
                  slot_fit='OPEN: r21c uses historical qfd_kvc slots; strip/controller/pcport successors need real abstract placement. Freed north IO-band area does not establish east/west shoreline slot fit.'),
        finite_flow=dict(link_credits=128,SU_request_queue=32,SU_consumer_credits=32,hub_x3_skid=8,
                         static_PC_queue=4,pcport_read_class_FIFO=32,pcport_write_FIFO=4,
                         strip_return_FIFO_each_PC=4,
                         sizing='65 SU response words; credit stalls are measured at SU13/EQ22 and link72 each direction. No same-cycle die ready response is assumed. Queue capacities and credit conservation still require physical boundary qualification.'),
        latency=dict(stream_clock_hz=1.2e9,HBM_clock_hz=1e9/1.024,serial_embedding_fetches_per_token=1,
                     measured_cycles={n:{k:v['stats'][k] for k in ('lat_min','lat_mean','lat_max')}
                                      for n,v in measured['variants'].items() if not n.startswith('mut_')},
                     measured_scope=measured['scope'],hidden_cycles=0,
                     baseline_replaced_cycles_estimate=65,
                     pending_mean_extra_cycles=473-65,pending_max_observed_extra_cycles=887-65,
                     baseline_estimate_status='Historical behavioural baseline share not isolated; no new headline until qualified path and reprice.'),
        exactness=dict(positive_variants=5,negative_variants=4,all_expected=measured['all_expected'],
                       golden='Released checkpoint W8 INT8 codes and BF16 scales; every delivered decoded FP32 element checked; CE corrected and UE fail closed'),
        energy='OPEN: requires measured activity and qualified cell/clock inventory; no assumed energy saving',
        headline_credit=0)

if __name__ == '__main__':
    print(json.dumps(model(),indent=2))

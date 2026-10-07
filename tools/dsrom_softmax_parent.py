#!/usr/bin/env python3
"""Full-shape SAFE softmax arithmetic placement and conditional parent cost.

Only measured leaves occupy the placement. Remaining softmax operators and CDC
are explicitly unbound: this arithmetic region is not a complete SU hard macro.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / 'results/rtl/dsrom_softmax_recovery_20261007/pin_maps'


def build(utilization=0.55, pin_hops=2, parent_width_um=1728.):
    if not 0.55 <= utilization <= 0.60:
        raise ValueError('owner target utilization must be 0.55..0.60')
    if pin_hops != 2:
        raise ValueError('one input and one output near-pin stage required')
    maps = {k: json.loads((PINS / f'{k}.json').read_text()) for k in ('exprcf', 'div2b')}
    ew, dw = (maps[k]['die_um'][2] for k in ('exprcf', 'div2b'))
    head_area = 17 * ew**2 + 16 * dw**2
    pitch = math.ceil(head_area / utilization / parent_width_um / 0.001) * 0.001
    margin, gap = 10., 8.
    tech = json.loads((ROOT / 'physical/dsrom_su_softmax_safe/routing_technology.json').read_text())
    local_tracks = math.floor(gap * utilization * sum(1 / tech['layers'][k]['pitch_um'][0] for k in ('M4', 'M6')))
    head_tracks = math.floor(100 * utilization * sum(1 / tech['layers'][k]['pitch_um'][0] for k in ('M4', 'M6')))
    instances, hops = [], []
    for h in range(16):
        ox, oy = 0., (h % 8) * pitch
        partition = 'su_s' if h < 8 else 'su_n'
        for kind, count, width, cols, xoff in [('exp', 17, ew, 6, margin),
                                              ('div', 16, dw, 4, margin + 6 * (ew + gap) + 20)]:
            for lane in range(count):
                x, y = ox + xoff + lane % cols * (width + gap), oy + margin + lane // cols * (width + gap)
                if x + width > ox + parent_width_um or y + width > oy + pitch:
                    raise ValueError('head arithmetic packing exceeds priced slot')
                name = f'h{h}_{kind}{lane}'
                rtl = (f'g_sk[{h}].g_xt.u_e' if kind == 'exp' and lane == 16 else
                       f'g_b[{h*16+lane}].g_xt.u_e' if kind == 'exp' else f'g_dv[{h*16+lane}].g_ft.u_d')
                instances.append(dict(name=name, partition=partition, master='ot_dsrom_su_softmax_exp_tile' if kind == 'exp' else 'ot_dsrom_su_fdiv_tile',
                                      master_variant='LM11_LA11_NSPLIT2_ADDX0' if kind == 'exp' else 'NR2',
                                      x=round(x,3), y=round(y,3), w=width, h=width, orient='R0',
                                      clock_domain='stream_1p2', rtl_instance=rtl, pin_map=f'{kind}_pin_map'))
                for direction, bits in [('input', 33 if kind == 'exp' else 65), ('output', 34)]:
                    hops.append(dict(instance=name, partition=partition, direction=direction, bits_per_cycle=bits,
                                     register_stages=1, max_last_segment_um=100,
                                     protocol='fixed_rate_valid', initiation_interval=1,
                                     station_master=None, clock_budget_sheet=None,
                                     status='REQUIRES_MEASURED_STATION_AND_PARENT_CLOCK_BINDING'))
    raw = 16 * head_area
    boundary = {'exp_input':272*33, 'exp_output':272*34, 'div_input':256*65, 'div_output':256*34}
    model = dict(schema='opentallas.dsrom_softmax_parent.v1', applicable_design='DeepSeek-V4.1 ROM S81',
        source=dict(pin_maps={k:dict(path=str((PINS/f'{k}.json').relative_to(ROOT)), sha256=hashlib.sha256((PINS/f'{k}.json').read_bytes()).hexdigest()) for k in maps}),
        full_shape=dict(heads=16, lanes_per_head=16, exp_replicas=272, div_replicas=256),
        outline=dict(width_um=parent_width_um,height_um=round(8*pitch,3),partitions=['su_s','su_n'], target_utilization=utilization, coordinates='local to each of two separate parent reservations'),
        physical=dict(raw_leaf_area_mm2=raw/1e6, arithmetic_region_area_mm2=16*parent_width_um*pitch/1e6,
                      old_SU_slot_mm2=12.80594, fits_old_SU_slot=False, complete_SU_area_mm2=None,
                      unplaced=['max/scale/sub/add/reduce/BF16/RoPE operators','row buffer and delay storage','pin stations','clock/reset tree','serial-to-stream CDC']),
        compute=dict(peak_divides_per_cycle=256, peak_exponentials_per_cycle=272,
                     standalone_MACs_per_cycle=0, exp_internal_multiply_ops_per_cycle=272*7, exp_internal_add_ops_per_cycle=272*8, explanation='FP exp micro-operations remain within measured exp leaves; this parent adds no MAC'),
        communication=dict(boundary_bits_per_cycle=boundary, boundary_bytes_per_cycle={k:v/8 for k,v in boundary.items()},
                           memory_port_bytes_per_cycle={'leaf_external':0, 'parent_score_row_buffer_read':1024, 'parent_score_row_buffer_write':1024},
                           parent_score_row_buffer_capacity_bytes=40*1024,
                           parent_stream_port_bytes_per_cycle={'scores':1024,'pv':1024,'exponentials':1024,'bf16_rope_result':512},
                           operations_per_boundary_byte=528/(sum(boundary.values())/8),
                           replica_mux_demux_cost='one-to-one lane wiring, no shared operand multiplexer; denominator broadcast remains parent logic',
                           parent_fanout='16 lane copies per head; retained local register/buffer tree required',
                           routing_tracks_needed={'worst_leaf_all_signal_pins':99, 'per_head_input_scores_and_pv':1024, 'per_head_output_exp_and_bf16':768},
                           channel_capacity_tracks={'local_8um_M4_M6_at_utilization':local_tracks,'head_100um_M4_M6_at_utilization':head_tracks},
                           tracks_fit=local_tracks>=99 and head_tracks>=1024,
                           routing_qualification='analytical tracks only, no obstruction/pin-access/DRC credit', technology=tech),
        latency=dict(stream_period_ps=833.333, pin_hops_per_tile=pin_hops,
                     candidate_extra_cycles_vs_measured_recut_SAFE2={'attn.exp':2,'attn.normalize':2},
                     T640_candidate_nodes={'attn.max':104,'attn.exp':257,'attn.den':120,'attn.sink':20,'attn.normalize':173},
                     T128_candidate_nodes={'attn.max':72,'attn.exp':225,'attn.den':90,'attn.sink':20,'attn.normalize':173},
                     status='analytical conditional; RTL measurement and parent clock/CDC path still required'),
        clock_contract=dict(domain='stream_1p2', old_SU_slab_domain='serial_0p9',
                            crossing='explicit 3:4 ratio CDC at serial/stream boundary; no inherited common-clock timing credit',
                            CDC_latency_cycles=None, parent_SS_FF_budget=None),
        adoption=False, hardware_build_admitted=False,
        missing=['source-pinned parent clock budget and actual station views','channel capacity/route validation','unplaced parent operators and CDC','exp leaf final FF ECO','post-hop exactness and measured cycles'],
        instances=instances, hops=hops,
        pin_interfaces={'exp_pin_map':maps['exprcf'],'div_pin_map':maps['div2b']})
    # Geometric non-overlap is necessary, never a physical sign-off claim.
    for i,a in enumerate(instances):
        for b in instances[i+1:]:
            if a['partition'] != b['partition']: continue
            if min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x']) and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y']):
                raise ValueError(f"overlap {a['name']} {b['name']}")
    return model

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path); ap.add_argument('--utilization',type=float,default=.55)
    args=ap.parse_args(); result=build(args.utilization); text=json.dumps(result,indent=2)+'\n'
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
    else: print(text,end='')

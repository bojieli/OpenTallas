#!/usr/bin/env python3
"""Source-pinned Qwen TP4 physical lower bounds; no architectural/build adoption."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def size(context=8192, groups=6144, layers=36, tp=4, layer_cycle_reference=4668):
 if context<=0 or context & (context-1) or groups<128 or groups%128 or tp not in (2,4):
  raise ValueError('Require power-of-two context, 128-group subtree multiples and TP2/4')
 heads=8//tp;tiles=groups//4;beat_bytes=64;head_dim=128
 window_bytes=2*heads*context*head_dim
 rounds=math.ceil(math.ceil(context/16)/(groups>>7))
 local_words=2*rounds*heads
 capacity=tiles*128*beat_bytes
 # Lower bound assumes a byte-packed window, ideal balance, no conflicts,
 # immediate responses, no tags/leases or draining and free codec work.
 beats=math.ceil(window_bytes/beat_bytes)
 lanes=math.ceil(beats/layer_cycle_reference)
 port_bits=512+512+7+1  # actual kvw data/mask/address and valid
 payload_bits=port_bits+16  # conditional addressed transport reuses 16-bit tile identity
 return dict(context=context,tp=tp,groups=groups,layers=layers,tiles_per_die=tiles,kv_heads_per_die=heads,
  local_words_per_tile=local_words,local_capacity_words=128,one_window_fits=local_words<=128,
  local_macro_capacity_bytes_per_die=capacity,useful_window_bytes_per_layer_die=window_bytes,
  useful_all_layer_bytes_per_die=layers*window_bytes,all_layer_capacity_lower_bound_fits=layers*window_bytes<=capacity,
  padded_current_window_bytes=tiles*local_words*beat_bytes,
  new_position_bytes_per_layer_die=2*heads*head_dim,
  warm_update_bytes_per_token_die=layers*2*heads*head_dim,
  conditional_one_window_reload_bytes_per_token_die=layers*window_bytes,
  ideal_64B_fill_beats_per_layer=beats,ideal_one_lane_fill_cycles_per_layer=beats,
  observed_layer_cycle_reference=layer_cycle_reference,
  ideal_fill_lanes_to_match_observed_layer_reference=lanes,
  ideal_data_bytes_per_cycle_at_that_lane_count=lanes*beat_bytes,
  actual_tile_fill_port_bits_per_lane=port_bits,
  candidate_destination_bits=16, candidate_addressed_fill_payload_bits_per_lane=payload_bits,
  candidate_addressed_payload_bits_per_cycle_at_that_lane_count=lanes*payload_bits,
  fill_transport_selected=False,
  latency_scope='Conditional refill lower bound if the selected design retains one local layer window and reloads it each layer hop. It is not observed runtime latency, not a priced G0 calendar, and not assumed absent from existing model terms.',
  cycle_reference_scope='Original TP4 SU64 context-zero host-serviced layer cycles only. Using 4668 sizes a demanding service target; it does not predict an 8K-context layer or grant overlap.',
  physical_build_ready=False,adoption=False)


def generate():
 paths=['physical/asap7_memory_macros/index.json','rtl/hdc/ot_qwen_rom_tile_w12.sv',
        'tools/qwen_rom_floorplan_candidate_w12.py','tools/qwen_rom_wire_budget_w12.py','tools/uarch_model.py']
 pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
 cat=json.loads((ROOT/paths[0]).read_text())['macros']
 macros={n:{k:cat[n][k] for k in ('width_um','height_um','clk_to_q_ps','min_period_ps')} for n in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')}
 rom=macros['ot_rom_4096x266_m8'];kv=macros['ot_sram_1r1w_128x256_m1_r2c2']
 area_tile=10*rom['width_um']*rom['height_um']+2*kv['width_um']*kv['height_um']
 rows=[size(context=c) for c in (1,8192,16384,32768)]
 if pins!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}:raise ValueError('Inputs changed')
 return dict(schema='opentallas.qwen-rom-physical-dimensions.v1',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='blocked',source_sha256=pins,
  macros=macros,selected_runtime_point={'TP':4,'G':6144,'CODE_BANKS':5,'SMIN':7,'SU':64,'MEM_EXTRA':1},
  macro_count_per_tile={'ROM':10,'KV_SRAM':2},macro_count_per_die={'ROM':15360,'KV_SRAM':3072},
  macro_area_lower_bound_mm2_per_tile=area_tile/1e6,macro_area_lower_bound_mm2_per_die=1536*area_tile/1e6,
  area_exclusions=['Arithmetic logic, register stages, pin access, halos, routing, clock/PG, hub/service, spine and PHY regions'],
  rows=rows,mandatory_model_inputs=['Select persistent KV storage home/lifetimes across 36 layers and prove layer-switch publication/read visibility.',
   'Bind actual finite fill lanes/ports/bandwidth, masks, destinations, arbitration, buffers, codec and acknowledgement/CDC semantics.',
   'Reconcile whether existing model HBM/KV terms already charge the transfer before composing any refill latency.',
   'Bind track capacity, mux/demux/fanout, real slot dimensions and SS macro capture budget; complete SS/FF context before build.'],
  clock_policy={'target_ns':0.833333,'setup_uncertainty_ns':0.060,'hold_uncertainty_ns':0.025},
  track_demand=None,channel_capacity=None,slot_fit=None,measured_service_latency=None,
  physical_build_ready=False,adoption=False,heavy_jobs_launched=0,
  claim_boundary='Concrete macro inventory, capacity and conditional ideal fill lower bounds only. Not a unified-model price, selected storage policy, route/fit, connected local-KV proof or measured token rate.')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args()
 if a.result.exists():ap.error('Refusing to overwrite evidence')
 r=generate();a.result.parent.mkdir(parents=True,exist_ok=True)
 with a.result.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({'status':r['status'],'8k':r['rows'][1],'macro_area_lower_bound_mm2_per_die':r['macro_area_lower_bound_mm2_per_die']},indent=2))
 return 1


if __name__=='__main__':raise SystemExit(main())

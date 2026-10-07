#!/usr/bin/env python3
"""Price existing gather-shift register against the retained full64 failure."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def model():
 p=R/'results/uarch/hbm_su_divider_halfpair_20261007/route_attempt1_recovered/summary.json'
 receipt=json.loads(p.read_text());aw=24;ff=6*aw+11
 return dict(schema='opentallas.hbm_su.div64_closure_successor.v1',selected=False,build_ready=False,
  baseline=receipt,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()},
  setup=dict(candidate='Enable existing GSH=1 in unique full64 successor wrapper',
   source='rtl/hbm_accel/su/div64_candidate/ot_hdc_v41x_vec_lane_c12.sv:g_gq.g_gs',
   mechanism='Register barrel-shift output before G2 address adder and read-address mux',
   state_FF_per_lane=ff,state_raw_area_um2=ff*.37908,incremental_slot_area_at55pct_um2=ff*.37908/.55,
   aligned_fields='s_v,s_par,s_cpair,s_a,s_b,s_c,s_d,s_o,s_qs,s_src; reset clears s_v',
   extra_gather_cycles=1,extra_nongather_cycles=0,extra_memory_return_cycles=0,
   controller_fetch_cycles_before=8,controller_fetch_cycles_after=9,
   required_schedule='Controller GSH must match lane; gather read and all dependent output metadata move one edge together; rd_q latency remains unchanged.',
   boundary_bits_unchanged=True,MACs_per_cycle_unchanged=True,memory_bytes_per_cycle_unchanged=True,
   token_latency_formula='number of serial exposed gather operations / serial_domain_hz; compiler schedule must provide exact count',
   token_latency_measured=None,replica_count_requires_selected_full_inventory=True,
   fanout='Local155FF/lane; no new global control broadcast; physical buffering and placement need measurement',
   qualification='Analytical local cost only; no claim that GSH alone closes full setup'),
  hold=dict(actual_clock_pair='div64_3 rising -> core_clk rising',
   required_incremental_min_path_ps=15-receipt['hold_ff_ps'],
   repair='Preserve four generated clocks and60/25 uncertainty. Characterize explicit hold-buffer insertion on actual failing return data cones atFF and recheckSS; no RTL delay chain or false-path waiver.',
   buffer_count=None,buffer_area=None,
   reason_open='Required49.8ps minimum-path increase cannot be converted to a cell count without actual corner slew/load and remaining SS budget.',
   input_margin_deficit_ps=15-receipt['input_hold_ff_ps'],output_margin_deficit_ps=15-receipt['output_hold_ff_ps']),
  required_before_build=['Unified model composition of exact exposed gather count and replicated slot fit','FF buffer-cell characterization and all hold endpoints inventory','Exact random plus vehicle gates with GSH1/DDIV64 and gather collision coverage'],
  active_attempt_policy='Keep original automatic attempt2 progressing; successor does not replace its source or failed receipt')
if __name__=='__main__':print(json.dumps(model(),indent=2))

#!/usr/bin/env python3
"""Prepare one source-sized loaded W4->W6 SS/FF plan; never launch physical tools."""
import argparse,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/hbm_W6_W4_loaded_SSFF_plan_20261003/r1'
RF='ot_sram_1r1w_128x256_m1_r2c2';SCR='ot_sram_1r1w_1024x256_m2_r2c2'
def need(v,m):
 if not v:raise ValueError(m)
def source_inputs():
 rows=json.loads((BASE/'source_pins.json').read_text());out={}
 for r in rows:
  raw=(BASE/r['archive']).read_bytes();need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'physical source drift '+r['path']);out[r['path']]=raw
 return out

def plan():
 raw=source_inputs();geom={}
 for master,count in [(RF,4096),(SCR,64)]:
  text=raw[f'physical/asap7_memory_macros/{master}/{master}.lef'].decode();m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text);need(m is not None,'macro outline');w,h=map(float,m.groups());meta=json.loads(raw[f'physical/asap7_memory_macros/{master}/{master}.json']);timing=meta['timing'];geom[master]=dict(count=count,width_um=w,height_um=h,bare_area_mm2=count*w*h/1e6,source_model_SS_clktoq_ps=timing['ss']['clk_to_q_ps'],source_model_FF_clktoq_ps=timing['ff']['clk_to_q_ps'],source_model_SS_clock_cap_ff=timing['ss']['clk_cap_ff'],SS_intrinsic_read_budget_before_dest_setup_wire_skew_ps=1000/1.2-60-timing['ss']['clk_to_q_ps'],claim_boundary=meta['claim_boundary'],loaded_or_extracted_measurement=False)
 return dict(schema='W4_W6_LOADED_SSFF_PLAN_R1',selected_route='W4_W6_FULL32_ORIGINAL_V1_ASAP7_RVT_M2_M5_R1',SMs=32,models_qualified=['Qwen only if actual Qwen source context supplied'],DS_transfer_credit=False,executor='Goodall',model_and_adapter_signer='Popper',wholeHBM_CDC_debt_owner='Claude',launch_admitted=False,
  clock=dict(period_ns=1/1.2,SS_setup_uncertainty_ns=.060,FF_hold_uncertainty_ns=.025,stream_GHz=1.2,bench_clock_is_not_closure=True,clock_sensitivity_ns=[1/1.2,1,1/.9],sensitivity_not_adoption=True),
  geometry=dict(macros=geom,bare_macro_total_mm2=sum(v['bare_area_mm2'] for v in geom.values()),original_v1=True,halo_PG_OBS_clock_and_logic_area_not_in_bare_sum=True,W4_W6_logic_slot_fit=None,actual_fullSM_neighbor_inventory_required=True),
  cuts=dict(request_bits=58,host_ACK_bits=57,internal_done_bits=57,ACK_tuple_width=55,consumer_bits=57,return_identity_width=55,drain_response_bits=68,perSM_and_full32_dedup_required=True,actual_tracks_per_cut=None,capacity_per_cut=None),
  critical_arcs=[
   dict(id='W4_CAPTURE_TO_ACK_ENCODE',start='RF.g_identity.accepted_identity[54:0]',end='RF.g_identity.protected_ACK[71:0]',cone='W4 w4_encode; publisher write_pending/ACKvalid controls'),
   dict(id='W4_HOST_ACK_TO_W6_STATE',start='RF.g_identity.protected_ACK[71:0]',end='W6.enabled.protected_state[143:0]',cone='W4 SECDED decode/padding-error+host valid mux -> Popper adapter -> W6 full55 comparator/phase -> encode_row'),
   dict(id='W6_READY_TO_W4_ACK_CLEAR',start='W6.enabled.protected_state[143:0]',end='RF.ack_valid',cone='W6 SECDED decode/age/phase/expected identity -> ready -> W4 decoded-error and identity_fault gates'),
   dict(id='W4_INTERNAL_DONE_TO_W6',start='FULL_SM.g_identity.g_enabled.simd_identity_q[71:0]',end='W6.enabled.protected_state[143:0]',cone='Map this exact source register to final netlist; W4 SIMD saved tuple decode/DONE mux -> adapter -> W6 compare/encode'),
   dict(id='RF_READ_CAPTURE_CONTEXT',start='RF macro rd_out[255:0] repeated 128',end='RF.rsp_a/rsp_b',cone='Actual SS macro clktoq, page select, load and receiving setup; both operand copies retained'),
   dict(id='RF_MIRRORED_WRITE_CONTEXT',start='write_go,wr_addr,wr_data source FFs',end='both RF copies w_ce_in,w_addr_in,wd_in',cone='Real SS setup and FF hold for all pages/banks, with postCTS skew and insertion'),
   dict(id='RESET_RECOVERY_REMOVAL',start='actual por_n/rst_n synchronizer/distribution',end='W4 async reset FFs/W6 protected_state',cone='Clocked W6 runtime quarantine vs W4 ACK abort; recovery/removal, release synchronization and fault/admission stop, no broad false-path waiver')],
  exception_policy='No blanket false/multicycle paths on ACK/ready/visibility/state or macro data. CDC exceptions only for actual synchronizer pins with a source-bound reviewed CDC graph.',
  required_positive_inputs=['Popper signed exact composed adapter model incl perport bits/bytes, staged latency, mux/fanout/protectedstate, onceonly area and finite service/wait assumptions','Clean final source/tool/PDK manifest for W4,W6,adapter,full128 SIMD/scratch and actual fullSM neighbor context','32 physical SM IDs and W4/W6 slot coordinates, row/site/orientation/bbox, macro4096RF64scratch census and liveOBS/halo/PG exclusions','Actual loads/launch driver slew/min/max delays and capture arcs for every scoped control/data port; no synthetic idealzero loading','Legal M2-M5 cut widths/tracks/capacity and selected route/no tuning sweep','Clock/reset CTS sources/skew/insertion and sameclock or actual adapterCDC seats; mutable protection costs included','SS/FF macro and standard-cell Liberty/LEF/RC scale coherence, actual corners/voltages and final placed instance census','Fresh measured fleet CPU/RAM/disk reservation and source-bound GO using guarded aligned launcher'],
  launcher='tools/run_abi3_physical_aligned_guarded.py --macro-track-gate',hooks=['ot_mts::place exact macro instance placements','ot_mts::assert_on_track -label POST_TAPCELL'],
  measurement=['Both setup SS60ps and hold FF25ps on named loaded arcs, including postCTS parasitics and macro clock paths','Report added capture/adapter/codec/retirement cycles and actual area/pin/mux/clock/reset/hold-repair delta to Popper once','Source exact32 instances and all RF/scratch/neighbor macros; padding optimization debit only after actual mapped census','PASS/FAIL immutable raw logs/netlist/ODB/SDC/STA/source/tool/corner hashes; reject failed route, no speculative tuning'],new_PNR_jobs=0,fullsystem_or_MTP_runs=0)

def check_admission(enrollment):
 p=plan();need(enrollment.get('route')==p['selected_route'],'selected route')
 clock=enrollment.get('clock',{});need(clock=={k:p['clock'][k] for k in ['period_ns','SS_setup_uncertainty_ns','FF_hold_uncertainty_ns']},'SSFF clock policy')
 for key in ['positive_composed_model','clean_exact_source','slot_and_macro_census','loaded_pin_bounds','positive_track_capacities','clock_reset_CDC_bound','SSFF_PDK_coherent','fresh_capacity_GO']:
  need(enrollment.get(key) is True,'missing admission '+key)
 need(enrollment.get('SM_ids')==list(range(32)),'full32 SM census')
 need(enrollment.get('RF_macros')==4096 and enrollment.get('scratch_macros')==64,'full RF scratch geometry')
 need(enrollment.get('slot_fit_mm2') is not None and type(enrollment['slot_fit_mm2']) in (int,float) and math.isfinite(enrollment['slot_fit_mm2']) and enrollment['slot_fit_mm2']>0,'positive slot area')
 return dict(verdict='PASS_ENROLLMENT_FIELDS_ONLY',launch_authorized=False,reviewed_sourcebound_GO_still_required=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--admission',type=Path);x=a.parse_args();print(json.dumps(check_admission(json.loads(x.admission.read_text())) if x.admission else plan(),indent=2,sort_keys=True))

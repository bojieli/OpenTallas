#!/usr/bin/env python3
"""Router recurrence repair sizing using the current unified model, before RTL."""
import argparse,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import uarch_model as U
ROOT=Path(__file__).resolve().parents[1]
def model():
 c=U.A.shape();assert (c['num_routed_experts'],c['experts_per_token'])==(384,6)
 n,p,k,iw=384,16,6,9;w=42;streams=2*p;nodes=streams-1
 # Each internal merge retains six entries. Constant invalid entries 6/7
 # eliminate four first-stage comparisons and the unused last output pair.
 ff=dict(lane_payload=streams*k*(w-1),lane_valid=streams*k,
         incoming_keys=streams*w,compare_predicates=streams*k,
         lane_control_pipes=streams*6,merge_pipeline=nodes*(3*8+k)*w,
         id_sort=6*8*(iw+1),output_valid_pipeline=29,beat_address=iw)
 total=sum(ff.values())
 old=json.loads((ROOT/'results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/topk_f3/physical.json').read_text())
 oldff=old['place_and_route']['metrics']['sequential_cell_count']
 old_area=old['design']['area_um2']; old_comb=old_area-oldff*U.DFF_UM2
 oldcomp=16*8+15*20;newcomp=streams*k+nodes*15
 # Conservative linear comparison/mux allowance; 10% explicitly prices CTS,
 # reset distribution and routing repair rather than assuming free protection.
 area=(total*U.DFF_UM2+old_comb*newcomp/oldcomp)*1.10
 core=old['design']['core_area_um2'];outline=old['place_and_route']['metrics']['die_area_um2']
 return dict(schema='opentallas.hbm.router.pipeline.before_rtl.v1',
  canonical_shape=dict(N=n,P=p,K=k,IW=iw,input_bits=512,output_bits=54),
  mechanism='two alternating lane banks; registered compare predicates then payload insert; exact per-bank top6; five merge levels',
  baseline_source='topk_f3 181dedac8d9c; SS FAIL is history, not adoption',
  unified_model=dict(source='tools/uarch_model.py',sha256=hashlib.sha256((ROOT/'tools/uarch_model.py').read_bytes()).hexdigest(),DFF_um2=U.DFF_UM2,model_layers=c['num_layers']),
  MACs_per_cycle=0,comparisons=dict(old_parallel_inventory=oldcomp,new_parallel_inventory=newcomp),
  memory_ports=dict(SRAM=0,HBM=0,ROM=0),bytes_per_input_cycle=64,bits_per_input_cycle=514,
  output_bits_per_vector=55,vector_beats=24,vector_II_cycles=24,
  comparator_bank_recurrence_cycles=2,bank_replicas=32,die_leaf_replicas=1,
  FF_inventory=ff,total_FF=total,baseline_mapped_FF=oldff,FF_delta=total-oldff,
  reset_scope='mutable lane-valid/control resets retained; payload eligibility gated by valid; no new protection credit',
  baseline_lastbeat_latency_cycles=23,candidate_lastbeat_latency_cycles=28,latency_delta_cycles=5,
  latency_is_analytical_pending_exact_gate=True,period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
  added_ns_per_layer_at_1p2GHz=5/1.2,nonoverlapped_token_delta_ns=c['num_layers']*5/1.2,
  current_die_outline_um2=outline,current_core_um2=core,comparison_mux_area_allowance_um2=old_comb*newcomp/oldcomp,
  FF_area_um2=total*U.DFF_UM2,CTS_reset_repair_allowance_fraction=.10,total_cell_allowance_um2=area,
  variants=[dict(utilization_percent=u,allowed_cell_um2=core*u/100,analytical_slot_fit=area<=core*u/100) for u in (55,57.5,60)],
  external_context='Turing/source owner must supply actual launch/capture clock, min/max ports and load; no scalar zero-IO or parent qualification',
  routing_tracks=dict(input_signals=514,output_signals=55,capacity='existing real die corridor/pin allocation, owner binding pending'),
  adopted=False,physical_qualified=False)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);q=a.parse_args();x=model();q.out.parent.mkdir(parents=True,exist_ok=True);q.out.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ('total_FF','FF_delta','total_cell_allowance_um2','variants','nonoverlapped_token_delta_ns')},indent=2))

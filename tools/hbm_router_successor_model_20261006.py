#!/usr/bin/env python3
"""Price the concrete router control-retention/merge-cut successor before RTL."""
import argparse,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import uarch_model as U
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1'
def model():
 shape=U.A.shape();assert (shape['num_routed_experts'],shape['experts_per_token'])==(384,6)
 old=json.loads((R/'before_rtl.json').read_text());meas=json.loads((R/'flowrepair_r2_GRT_actual/record.json').read_text())
 # First merge: four bypasses need one extra42bit register; four live
 # comparisons need both42bit candidates plus three GT/EQ chunk pairs.
 # Each other stage retains8 real candidates plus4*3 GT/EQ pairs.
 first_extra=4*42+4*(2*42+6)
 cs_extra=8*42+4*6
 delta_merge=31*(first_extra+3*cs_extra)
 total=old['total_FF']+delta_merge+20
 # Source-level lane-control inventory was already32*6 in the old model.
 # The mapped vehicle folded it; charge every source FF again in this bound.
 extra_vs_map=total-45270
 area=(meas['cell_area_um2']+extra_vs_map*U.DFF_UM2)*1.10
 core=area/.575
 # Existing actual boundary margins are retained; size one finite new frame.
 side=math.ceil((math.sqrt(core)+4.32)*1000)/1000
 return dict(schema='opentallas.router.successor.before_rtl.v1',canonical_shape=old['canonical_shape'],
 unified_model=dict(path='tools/uarch_model.py',sha256=hashlib.sha256((ROOT/'tools/uarch_model.py').read_bytes()).hexdigest(),DFF_um2=U.DFF_UM2),
 measured_baseline_record='router_pipeline_r1/flowrepair_r2_GRT_actual/record.json',baseline_mapped_FF=45270,baseline_cell_um2=meas['cell_area_um2'],
 mechanism='preserved lane hierarchy/local controls; each42bit merge comparison registers three14bit GT/EQ chunks and real candidates before selection',
 FF_inventory=dict(previous_source_upper=old['total_FF'],first_merge_extra_per_node=first_extra,other_merge_extra_per_node=cs_extra,merge_nodes=31,extra_merge_FF=delta_merge,extra_output_valid_FF=20),
 source_FF_upper=total,FF_delta_vs_previous_source=delta_merge+20,FF_delta_vs_measured_mapping=extra_vs_map,
 control_inventory_required=dict(x_first=32,c_first=32,x_v=32,c_v=32,x_last=32,c_last=32,finished=32,ge_q=192,valid_q=192),
 control_retention='keep_hierarchy only intent; actual mapped32 instances/registers and loaded delivery must be verified, no freeclock/reset/protection credit',
 clock_sink_inventory=dict(total_source_FF_upper=total,new_clock_pin_cap_fF_SS_upper=extra_vs_map*.446638,basis='existing unifiedmodel DFFHQNx1 CLK0.446638fF; upper includes control FF, actual SSFF cellmix/caps measured at mapgate',root_input_cap='not inferred from sinksum',new_CTS_reset_state_reserved=True),
 internal_pipeline_boundaries=dict(first_merge_cut_bits_per_node=first_extra,other_merge_cut_bits_per_node=cs_extra,tree_nodes_per_level=[16,8,4,2,1],added_local_track_upper_per_level=[n*(first_extra+3*cs_extra) for n in [16,8,4,2,1]],capacity_proven=False,capacity_binding='actual Turing leaf frame/corridor allocation and native congestion must verify these distributed local bundles'),
 bytes_per_input_cycle=64,bits_per_input_cycle=514,output_bits_per_vector=55,vector_beats=24,vector_II_cycles=24,MACs_per_cycle=0,memory_ports=dict(SRAM=0,HBM=0,ROM=0),
 boundary_tracks=dict(input=514,output=55,capacity='Turing actual receiver/frame allocation remains required'),
 baseline_tail_cycles=23,previous_tail_cycles=28,successor_tail_cycles=48,extra_cycles_vs_previous=20,extra_cycles_vs_baseline=25,
 added_ns_per_layer_vs_previous=20/1.2,nonoverlapped_token_delta_ns_vs_previous=shape['num_layers']*20/1.2,
 preserved_publication='previous lane final commit24 remains until merge first candidate capture26; first next-vector commit26 happens after capture; no earlyvalid clear',
 period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,input_min_max_ps=166.6,output_min_max_ps=166.6,output_load_fF=3.898,
 current_core_um2=meas['core_area_um2'],cell_area_allowance_um2=area,CTS_reset_predicate_repair_allowance_fraction=.10,
 old_slot_fit_at_55_to_60_percent=area<=meas['core_area_um2']*.60,
 finite_candidate_frame=dict(die_side_um=side,core_lower_um=[2.052,2.160],core_upper_um=[round(side-2.047,3),round(side-2.101,3)],priced_target_utilization=.575),
 parent_allocation='OPEN: no existing leaf slot fit or parent closure inferred; Turing must consume priced finite frame',
 functional_gate='ONE changed full384/K6 independent FP32 golden including II24 back-to-back, bank-phase and heldreset negatives',
 map_gate='verify real local control DFFs after mapping before placement; detailed loadedclock/IO/receiver checks remain mandatory',
 adopted=False,physical_qualified=False)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);q=a.parse_args();r=model();q.out.parent.mkdir(parents=True,exist_ok=True);q.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

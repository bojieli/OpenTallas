#!/usr/bin/env python3
"""Price the real circular-delay split and common-clock local relay/TX experiment."""
import json
from pathlib import Path

def model():
    inj,w,d=2,544,35
    ff_area=.2916
    mux_area=3*.08748+.04374
    tx_per=7+7+16+16+1+1+w+16
    local_bits=inj*(w+1)
    width,height=840.024,40.176
    islands=[dict(x0=150.012,x1=250.020,y0=1.080,y1=38.880),
             dict(x0=570.024,x1=670.032,y0=1.080,y1=38.880)]
    return dict(schema='opentallas.ha2.circular_split_local_tx.v1',adopted=False,default_off=True,
      source_truth=dict(module='ot_ha2_delay_quiet',path='rtl/hbm_accel/ha2_ar/ot_ha2_parent_quiet_prims.sv',
        implementation='mem[D] plus rotating integer pointer, selected-slot combinational output; not a spatial shift chain',
        parent='rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner_truecredit.sv:g_hub[i].u_h',original_depth=d,
        replacement='D34 circular store followed by a real D1 local register, then unconditional-payload truecredit TX',
        equivalence_required='Original D35 versus D34+D1 on valid data, bubbles, quiet, common reset; exact TX tags and credits retained'),
      inventory=dict(injectors=inj,payload_bits=w,original_data_valid_bits=inj*d*(w+1),
        split_ring_data_valid_bits=inj*(d-1)*(w+1),new_local_stage_data_valid_bits=local_bits,
        total_data_valid_bit_delta=0,conservative_original_pointer_bits=inj*32,
        conservative_split_pointer_bits=inj*32,local_D1_pointer_bits_after_constant_elimination=0,
        original_read_mux2_eq=inj*w*(d-1),split_read_mux2_eq=inj*w*(d-2),read_mux2_eq_delta=-inj*w,
        local_payload_enable_mux2_eq=0,local_payload_enable_note='Physical candidate CAPTURE_ALWAYS=1 exact gate removes enabled payload muxes; default0 retained in source',
        tx_register_bits=inj*tx_per,combined_local_register_bits=local_bits+inj*tx_per,
        tx_payload_enable_mux2_eq_delta=-inj*w,tx_tag_enable_mux2_eq=inj*16,
        local_valid_payload_enable_fanout=0,local_payload_enable_mux2_eq_delta=-inj*w,tx_payload_valid_enable_fanout_removed=inj*w),
      area=dict(ff_proxy_um2=ff_area,mux2_proxy_um2=mux_area,
        combined_local_storage_um2=(local_bits+inj*tx_per)*ff_area,
        combined_local_mux_proxy_um2=(inj*16)*mux_area,
        slot_um=[width,height],slot_area_um2=width*height,target_utilisation=.55,
        reserved_lane_islands=islands,per_lane_island_area_um2=(100.008*37.800),
        per_lane_storage_and_mux_proxy_um2=((w+1+tx_per)*ff_area+16*mux_area),
        mapping_control_CTS_repair_unmeasured=True,die_area_delta_unqualified=True,
        accounting='D1 storage transferred out of D35 inventory, not newly added parent storage. Actual hard partition footprint/clock cost must be measured.'),
      ports=dict(MACs_per_cycle=0,compute_intensity=0,forward_data_bits_per_cycle=inj*w,
        forward_bytes_per_cycle=inj*w/8,local_launch_capture_boundary_bits=inj*(w+1),
        replicas=inj,independent_lanes=True,per_lane_signal_pin_pitch_um=.144,
        native_M5_pitch_um=.048,per_lane_input_545_pin_span_um=544*.144,per_lane_output_561_pin_span_um=560*.144,
        forward_tag_bits_per_cycle=32,forward_valid_bits_per_cycle=2,
        input_pin_windows_x_um=[[160.044,238.380],[580.044,658.380]],
        output_pin_windows_x_um=[[160.044,240.684],[580.044,660.684]],
        lane_island_width_um=100.008,wire_length_requires_extracted_route=True),
      clock=dict(period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,minimum_margin_ps=15,
        experiment='One real root and common CTS containing local D1 launch and TX capture registers',
        internal_source_clock='Measured actual D1 clock branch, never an assigned virtual source arrival',
        upstream_D34_selected_slot_clock_unqualified=True,return_credit_boundary_clock_unqualified=True,
        report='INTERNAL-ONLY experiment: D1-to-TX and all reg2reg SS/FF, full coverage counts, all unconstrained upstream/reset/credit/output endpoints listed; no virtual input arrival assigned'),
      cycles=dict(nominal_hub_depth_before=35,nominal_hub_depth_after=34+1,
        physical_experiment_hub_stages=1,hub_stages_outside_experiment=34,
        nominal_token_delta=0,adopt_delta_only_after_exact_gate=True),
      power=dict(invalid_payload_switching_may_increase=True,energy_gain_claimed=False),
      physical_build_ready=False,remaining=['W2 source-pinned split-delay and unconditional-TX exact gate',
        'Actual wrapper elaboration and source inventory', 'Modeled structural candidate guarded full-shape P&R',
        'Extracted local launch/capture CTS and complete path-class reports',
        'Unqualified external D34/credit boundary joined in actual parent before adoption'])

if __name__=='__main__':
    print(json.dumps(model(),indent=2))

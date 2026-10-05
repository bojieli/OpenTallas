#!/usr/bin/env python3
"""Finite CMD1 parent prebuild price. Existing source clocks, no headline adoption."""
import ast, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def model():
    u=ROOT/'tools/uarch_model.py'
    constants={n.targets[0].id:n.value for n in ast.parse(u.read_text()).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    dff=ast.literal_eval(constants['DFF_UM2'])
    np=32; channels=16; rd=64; wr=8; phy=rd+wr
    # Direct PCWB address, not the hashed canonical-provider address function.
    command_fields=dict(write=1,write_slot=3,bank=5,row=19,column=5,data=256)
    command_bits=sum(command_fields.values())
    # Real caller context retained by one selected stack phase, not an invented native identity.
    context_fields=dict(operation=64,phase=32,physical_rank=7,stack=2)
    receipt_fields=dict(operation=64,phase=32,sector=34,generation=32,slot=3,pc=5,bank=5,row=19,column=5)
    receipt_bits=sum(receipt_fields.values())
    pending_fields=dict(receipt=receipt_bits,data=256,state=3)
    pending_bits=sum(pending_fields.values())
    pending_coded=72*((pending_bits+63)//64)
    fifo_control_per_pc=7+7+7
    ff=dict(ca_phase_and_sticky=2,stack_context=sum(context_fields.values()),
        phy_column_payload=np*phy*command_bits,phy_column_control=np*fifo_control_per_pc,
        retained_write_raw=np*wr*pending_bits,retained_write_coded_shadow=np*wr*pending_coded,
        write_order_controls=np*(3+3+4),parent_sticky=1)
    bits=sum(ff.values())
    # Positive conservative logic reservations, explicitly estimates, not measurements.
    mux_1bit=np*((phy-1)*command_bits+(wr-1)*receipt_bits)+channels*28
    cmp_1bit=np*wr*receipt_bits
    gate_eq=4*mux_1bit+6*cmp_1bit+8*np*21+128
    nand2_um2=.08748
    body=bits*dff+gate_eq*nand2_um2
    payload_landing_bits=np*rd*256
    inputs=['rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_command_match.sv',
      'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb.sv','rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv',
      'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv','tools/uarch_model.py']
    # Actual fixture command->visibility path, never a synthesized timer-created ACK.
    wr_visibility_ns=5+6.250+1.024+10+5
    return dict(schema='opentallas.pcwb.actual_parent_prebuild.v1',sources={x:sha(x) for x in inputs},
      selected_top='ot_hbm_accel_pcwb_service_stack',ENABLE_default=0,CMD_MATCH_CUT_default=0,
      owners=dict(parent='Euclid',controller_leaf='Bacon',model_and_CA='Sagan',prepaid_column_visibility_adapter='Euclid',source_list_helper='Rawls'),
      clocks=dict(service_input='service_clk',service_period_ps=1024,core_input='core_clk',core_period_ps=833.333,
        service_source='Explicit uniform clock input; donor DS functional master uses hclk #512. Physical PLL/distribution is not installed/qualified.',
        prohibited='Do not use Qwen fractional ~clk & tick or average1024. No live P0 edit.',
        source_model='tools/hbm_accel_service_context_model.py already prices 1024/833 domains',
        logic_route_target_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        whole_service_1p2GHz_closed=False),
      CA=dict(channels=channels,PCs=np,requests_per_channel_per_service_edge=1,
        arbitration='Existing paired-PC parity schedule, actual ca_ready[channel] and request; suppress/fault simultaneous or wrong-parity requests.',
        command_bits_per_channel=28,total_command_bits_per_edge=channels*28,
        queue_bits=0,extra_pipeline_edges=0,stall_cost='Each rejected slot costs at least2 service edges until that PC next owns slot; refresh refusal is a real fault, not hidden/retried PASS.'),
      column=dict(record_fields=command_fields,record_bits=command_bits,queue_depth_per_PC=phy,
        reserved_read_slots_per_PC=rd,reserved_write_slots_per_PC=wr,issued_per_PC_per_edge_max=1,
        bytes_per_service_edge_peak=np*32,peak_Bps=np*32/(1.024e-9),
        PHY_output='col_valid/ready FIFO; data pop only actualPHYacceptance; controller col_valid cannot be gated after internal issue.',
        read_prepaid='CRED64 credits cover queued+PHYinflight+landing64+consumer. Return only CDC rd_freed after actual core consumption.',
        write_prepaid='8 total write leases/PC cover controller WQ8+column queued+PHYinflight+visible-not-returned. Forward wq only after free lease reservation.',
        bytes_per_command_boundary=command_bits/8,queue_area_included=True,installed_FIFO_macros=None,
        partial_target_only='No full rank/source-native read identity qualification from this raw stream parent.'),
      write=dict(context_fields=context_fields,receipt_fields=receipt_fields,receipt_bits=receipt_bits,
        pending_fields=pending_fields,pending_bits=pending_bits,coded_shadow_bits=pending_coded,
        controller_WQ8_order='Bind oldest not-issued retained write at actual WRissue; validate PC/bank/row/col/data before marking issued.',
        visibility='Real PHY/CWL/burst/backing-store commit returns entire held tuple. Validate statePHYaccepted and complete tuple; state3 encodes FREE/QUEUED/CONTROLLERissued/PHYaccepted/VISIBLE. No age timer/WRissue ACK.',
        retirement='Release lease only matched visible receipt actually accepted by writer. Keep posted debt during output stalls.',
        fences='writer row emission idle AND all posted writes visible/accepted AND allPC WQempty AND no queued/inflight output; real readback descriptor held until fence.',
        reset='Cold POR only; no local reset that clears externally accepted PHY debt.',generation='Actual provider/frame irs_serial32; no synthetic/local/default generation. Missing owner/generation refuses admission; no slot reuse until matched return.',
        reserved_lease_capacity=np*wr,metadata_comparison_bits_per_stack=cmp_1bit),
      costs=dict(added_FF_inventory=ff,added_FF_bits=bits,FF_cell_um2=bits*dff,
        mux_onebit_2to1_equivalents=mux_1bit,compare_bits=cmp_1bit,
        logic_NAND2_equivalents_estimate=gate_eq,logic_area_estimate_um2=gate_eq*nand2_um2,
        cell_area_estimate_um2=body,placement_reservation_um2_50pct=2*body,
        reused_read_landing_payload_bits=payload_landing_bits,reused_read_landing_control_bits=np*(9*7),
        clock_tree_power_grid_protection_decode_route_extra_um2=None,
        tracks_CA=channels*28,tracks_column=np*command_bits,tracks_matched_visibility=np*receipt_bits,
        actual_channel_capacity=None,slot_fit=None,
        no_physical_FIFO_or_fullarray_instantiation_authorized=True),
      calendar=dict(no_new_CMD1_leaf_edges=True,CA_added_edges=0,prepaid_PHY_FIFO_min_edges=1,
        command_queue_wait_upper_if_PHY_blackout_ns=None,read_added_parent_lower_ns=1.024,
        return_CDC_lower_ns=3*.833333+2*1.024,
        donor_WRITE_issue_to_real_visibility_ns=wr_visibility_ns,
        fence_lower_after_last_WRissue_ns=wr_visibility_ns+1.024,
        readback_ready_edge='Only after visibility accepted and fence registered; no inter-op free overlap.',
        DS_writer_actual_source_bound=dict(window_rows40_sectors_each17=680,compressed_rows8_sectors_each9=72,
          index_keys8_max_sectors_each3=24,total_die_sectors_upper=776,
          writer_rows_upper=56,serialized_row_mapper_minimum_service_edges=112,
          write_emit_only_lower_ns=776*1.024,
          die_serial_writer_envelope_ns=(776+112)*1.024+wr_visibility_ns+1.024,
          scope='Conservative die sum; stack filter/rank ownership excludes some sectors. Not composed token latency.'),
        Qwen_full_token_count=None,DS_full_token_stall_exposure=None,
        full_token_native_calendar='MANDATORY_OPEN; no transfer from per-stack lower bounds to measured headline.'),
      MACs_per_cycle=0,replicas=dict(per_stack=np,per_DS_rank_stacks=4,full_target_binding_not_adopted=True),
      build_selection='Bounded C/A and finite per-PC adapter source are sized. Full stack hardware growth requires installed physical queue/slot and actual clock-source context.',
      current_memory_composition='MANDATORY_OPEN',adopted=False,exactness=False,SS_FF_in_context=False)
if __name__=='__main__':print(json.dumps(model(),indent=2)+'\n',end='')

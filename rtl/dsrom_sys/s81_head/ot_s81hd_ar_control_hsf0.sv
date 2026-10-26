`timescale 1ns/1ps
// Actual rank -> RESULT -> fault composition, not a whole head controller.
// Own/peer framing and issue/START remain caller responsibilities. External
// faults are original bits0..5 (bit3 local NaN) then11..16, with live LP separate.
module ot_s81hd_ar_control_hsf0 #(parameter integer MUT_MODE=0)(
 input wire ck,rst_rank_pin_n,rst_rank_hold_n,rst_result_n,rst_fault_n,rst_fault_output_n,
 input wire own_valid,input wire[80:0]own_record,
 input wire[5:0]peer_valid,input wire[3317:0]peer_frames,
 input wire[15:0]destination_header,input wire sequencer_grant,
 input wire lep_fault_i,input wire[11:0]external_fault_events,
 output wire result_pending,result_ready,result_overwrite,
 output wire flit_valid,output wire[511:0]flit_data,
 output wire merged_valid,output wire[48:0]merged_row_bits,output wire[30:0]merged_identity,
 output wire[16:0]fault_vector,output wire ctl_fault
);
 wire tf,cf,nf,cv;wire[6:0]ov;
 ot_s81hd_rank_merge_hsf0 #(.MUT_ROW(MUT_MODE==3))u_rank(
 .ck(ck),.rst_pin_n(rst_rank_pin_n),.rst_hold_n(rst_rank_hold_n),
 .ov_p(own_valid),.orec_d(own_record),.mrx_v(peer_valid),.mrx_d(peer_frames),
 .valid(merged_valid),.row_bits(merged_row_bits),.identity(merged_identity),
 .tag_fault(tf),.copy_fault(cf),.nan_fault(nf),.check_valid(cv),.overwrite(ov));
 ot_s81hd_result_landing_hsf0 #(.MUT_USER_HI(MUT_MODE==1))u_result(
 .ck(ck),.rst_result_n(rst_result_n),.merged_valid(merged_valid),
 .merged_row_bits(merged_row_bits),.merged_identity(merged_identity),
 .destination_header(destination_header),.sequencer_grant(sequencer_grant),
 .result_pending(result_pending),.result_ready(result_ready),.overwrite(result_overwrite),
 .flit_valid(flit_valid),.flit_data(flit_data));
 wire[5:0]local_events=external_fault_events[5:0]|{2'b00,(cv&&nf),3'b000};
 wire[15:0]events={external_fault_events[11:6],result_overwrite,(|ov),(cv&&cf),(cv&&tf),local_events};
 ot_s81hd_fault_state_hsf0 #(.MUT_LEP_DROP(MUT_MODE==2))u_fault(
 .ck(ck),.rst_vector_n(rst_fault_n),.rst_output_n(rst_fault_output_n),
 .lep_fault_i(lep_fault_i),.other_events_i(events),.fault_vector(fault_vector),.ctl_fault(ctl_fault));
endmodule

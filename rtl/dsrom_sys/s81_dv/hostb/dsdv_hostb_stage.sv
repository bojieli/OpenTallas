`timescale 1ns/1ps
`default_nettype none
// Separately named opt-in actual s0N source wrapper boundary. Default preserves
// original endpoint ring wiring. New consumer outputs are real515/53 contracts,
// not synthetic token generators. Physical landing/KS6 selection is explicit.
module dsdv_hostb_stage #(parameter integer ENABLE=0)(
 input wire ck,rst_n,configured,
 input wire [7:0] local_stage,input wire [1:0] local_rank,
 input wire [31:0] epoch_id,input wire [63:0] programme_id,input wire [47:0] receiver_edge,transit_body_edge,
 input wire [15:0] expected_tid,input wire [7:0] expected_header_stage,
 input wire [9:0] expected_user,input wire [20:0] expected_position,expected_token,
 input wire header_slot,job_active,starter_armed,
 input wire [1103:0] from_prev,local_ro,return_ro,
 input wire forward_slot,return_slot,
 output wire [1103:0] to_local,next_ro,
 output wire [514:0] f_host,output wire [52:0] ks_descriptor,
 output wire [2:0] ks_slot,output wire [5:0] arm_mask,
 output wire arm_commit,output wire [11:0] fault);
 generate if(ENABLE==0)begin:g_original
   assign to_local=from_prev;assign next_ro=local_ro;
   assign f_host=0;assign ks_descriptor=0;assign ks_slot=0;assign arm_mask=0;assign arm_commit=0;assign fault=0;
 end else begin:g_hbe
   wire [1103:0] forward_ro;
   dsdv_hostb_rx u_rx(.ck(ck),.rst_n(rst_n),.configured(configured),.local_stage(local_stage),.local_rank(local_rank),
    .epoch_id(epoch_id),.programme_id(programme_id),.receiver_edge(receiver_edge),.transit_body_edge(transit_body_edge),.expected_tid(expected_tid),
    .expected_header_stage(expected_header_stage),.expected_user(expected_user),.expected_position(expected_position),.expected_token(expected_token),.header_slot(header_slot),.job_active(job_active),.starter_armed(starter_armed),
    .ring_i(from_prev),.local_ring(to_local),.forward_ring(forward_ro),.f_host(f_host),.ks_descriptor(ks_descriptor),
    .ks_slot(ks_slot),.arm_mask(arm_mask),.arm_commit(arm_commit),.fault(fault[7:0]));
   dsdv_hostb_tx u_tx(.ck(ck),.rst_n(rst_n),.local_ro(local_ro),.forward_ro(forward_ro),.return_ro(return_ro),
    .forward_slot(forward_slot),.return_slot(return_slot),.next_ro(next_ro),.fault(fault[11:8]));
 end endgenerate
endmodule
`default_nettype wire

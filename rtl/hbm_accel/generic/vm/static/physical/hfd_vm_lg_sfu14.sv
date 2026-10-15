`timescale 1ns/1ps
`default_nettype none
// Concrete physical master: actual same two-edge transport, fixed return calendar.
module hfd_vm_lg_sfu14 #(parameter integer MUT=0)(
    input wire clk,rst_n,
    input wire [16:0] local_rq,far_rq,
    input wire [280:0] local_wq,far_wq,
    input wire [0:0] local_read,local_write,
    output wire [16:0] near_rq,
    output wire [280:0] near_wq,
    input wire [256:0] near_rr,
    input wire [0:0] near_w_done,
    output wire [256:0] local_rr,far_rr,
    output wire [0:0] local_w_done,far_w_done,
    output wire fault
);
 ot_hbm_vm_lg_static_bank #(.READ_RETURN(14),.WRITE_RETURN(11),.MUT(MUT)) u_core(
 .clk(clk),
 .rst_n(rst_n),
 .local_rq(local_rq),
 .far_rq(far_rq),
 .local_wq(local_wq),
 .far_wq(far_wq),
 .local_read(local_read),
 .local_write(local_write),
 .near_rq(near_rq),
 .near_wq(near_wq),
 .near_rr(near_rr),
 .near_w_done(near_w_done),
 .local_rr(local_rr),
 .far_rr(far_rr),
 .local_w_done(local_w_done),
 .far_w_done(far_w_done),
 .fault(fault));
endmodule
`default_nettype wire

// Native central FUSED hub: exactly two external level-four trees.
// N4EXT=1 source generate ignores uq1/uq3,pk4a/b,pb4a/b and drives dq1/dq3 zero.
module ot_hnx_fused_hub_n4ext #(parameter integer DELIVERED_RESET = 0) (
 input wire clk, rst_n, job_v,
 input wire [216:0] job,
 output wire done, fault, busy,
 input wire [7:0] wsc,
 input wire [5:0] pk5,
 input wire pb5,
 input wire [270:0] up_nw, up_ne,
 output wire [172:0] down_nw, down_ne
);
 ot_hnx_fused_hub #(.D(5120),.RR(10),.NMAX(8),.MUT(0),.N4EXT(1),.DELIVERED_RESET(DELIVERED_RESET)) u_native (
 .clk(clk),.rst_n(rst_n),.job_v(job_v),.job(job),.done(done),.fault(fault),.busy(busy),
 .wsc(wsc),.pk4a(6'd0),.pk4b(6'd0),.pk5(pk5),.pb4a(1'b0),.pb4b(1'b0),.pb5(pb5),
 .uq0(up_nw),.uq1(271'd0),.uq2(up_ne),.uq3(271'd0),
 .dq0(down_nw),.dq1(),.dq2(down_ne),.dq3());
endmodule

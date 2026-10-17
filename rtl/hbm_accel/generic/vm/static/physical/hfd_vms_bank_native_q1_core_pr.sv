`timescale 1ns/1ps
`default_nettype none
// H-SM 2026-10-17 (H-NETLIST source-binding request): hfd_vms_bank_native_q1_core with LITERAL input pin registers,
// the q0C convention (faces_q0/hfd_vms_bank_native_q0_faces.sv = ot_pin_regs-generated wrapper, inputs only).  Every data
// input gets one flop at its pin on clk (+1 edge, in the RTL the die binds); clk / rst_n pass straight through; every output
// is already a register of the bank body (ot_vms_bank_static_strap rr/eg/pr/status/*_done), so no output stage is added.
// The physical view equals this RTL (kit pin_regs disabled with that reason; recipe 4, hold_budget die).
module hfd_vms_bank_native_q1_core_pr(
    input wire [16:0] rq0,
    output wire [256:0] rr0,
    input wire [16:0] rq3,
    output wire [256:0] rr3,
    input wire [280:0] wq0,
    output wire wq_done0,
    input wire [2:0] bid,
    input wire [1:0] sid,
    input wire clk,
    input wire rst_n,
    input wire rslot_v,
    input wire [2:0] rslot,
    input wire wslot_v,
    input wire [2:0] wslot,
    input wire [280:0] kq,
    output wire kq_done,
    input wire [275:0] xq,
    output wire xq_done,
    input wire [275:0] xq2,
    output wire xq2_done,
    output wire [275:0] eg,
    input wire [284:0] pq,
    output wire [265:0] pr,
    output wire [17:0] status
);
    (* keep *) reg [16:0] rq0__ot_q;
    always @(posedge clk) rq0__ot_q <= rq0;
    (* keep *) reg [16:0] rq3__ot_q;
    always @(posedge clk) rq3__ot_q <= rq3;
    (* keep *) reg [280:0] wq0__ot_q;
    always @(posedge clk) wq0__ot_q <= wq0;
    (* keep *) reg [2:0] bid__ot_q;
    always @(posedge clk) bid__ot_q <= bid;
    (* keep *) reg [1:0] sid__ot_q;
    always @(posedge clk) sid__ot_q <= sid;
    (* keep *) reg rslot_v__ot_q;
    always @(posedge clk) rslot_v__ot_q <= rslot_v;
    (* keep *) reg [2:0] rslot__ot_q;
    always @(posedge clk) rslot__ot_q <= rslot;
    (* keep *) reg wslot_v__ot_q;
    always @(posedge clk) wslot_v__ot_q <= wslot_v;
    (* keep *) reg [2:0] wslot__ot_q;
    always @(posedge clk) wslot__ot_q <= wslot;
    (* keep *) reg [280:0] kq__ot_q;
    always @(posedge clk) kq__ot_q <= kq;
    (* keep *) reg [275:0] xq__ot_q;
    always @(posedge clk) xq__ot_q <= xq;
    (* keep *) reg [275:0] xq2__ot_q;
    always @(posedge clk) xq2__ot_q <= xq2;
    (* keep *) reg [284:0] pq__ot_q;
    always @(posedge clk) pq__ot_q <= pq;
    hfd_vms_bank_native_q1_core u_ot_pr_core(.rq0(rq0__ot_q), .rr0(rr0), .rq3(rq3__ot_q), .rr3(rr3), .wq0(wq0__ot_q), .wq_done0(wq_done0), .bid(bid__ot_q), .sid(sid__ot_q), .clk(clk), .rst_n(rst_n), .rslot_v(rslot_v__ot_q), .rslot(rslot__ot_q), .wslot_v(wslot_v__ot_q), .wslot(wslot__ot_q), .kq(kq__ot_q), .kq_done(kq_done), .xq(xq__ot_q), .xq_done(xq_done), .xq2(xq2__ot_q), .xq2_done(xq2_done), .eg(eg), .pq(pq__ot_q), .pr(pr), .status(status));
endmodule
`default_nettype wire

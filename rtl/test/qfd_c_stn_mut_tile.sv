`timescale 1ns/1ps
// BENCH-ONLY MUTANTS of rtl/physical/qcluster/qfd_c_stn.sv for the per-master bench tools/qwen_cluster/bench_stn.sh
// (S-QSTN 2026-10-18).  Each master carries one fault; tb_qfd_c_stn.sv must FAIL on every one of them:
//   qfd_c_stn516 : q[515] inverted (top bit; the cluster lockstep mutant S covers bit 0)
//   qfd_c_stn514 : q[300] stuck at 0
//   qfd_c_xstn   : x hold deadline one edge late  (XOFF 4 instead of 3)
//   qfd_c_xstnw  : x hold deadline one edge early (XOFF 2 instead of 3)
module qfd_c_stn516 (
    input  wire         ck,
    input  wire [515:0] d,
    output wire [515:0] q
);
    (* keep *) reg [515:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = {~q_r[515], q_r[514:0]};
endmodule

module qfd_c_stn514 (
    input  wire         ck,
    input  wire [513:0] d,
    output wire [513:0] q
);
    (* keep *) reg [513:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = {q_r[513:301], 1'b0, q_r[299:0]};
endmodule

module qfd_c_xstn (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   sidx,
    input  wire [515:0] b_d,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
    ot_qfd_xcst #(.AW(24), .NW(18), .XOFF(4)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d), .a_r(),
        .b_d(a_d), .b_r(1'b1), .tap_d(tap_d));
endmodule

module qfd_c_xstnw (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   sidx,
    input  wire [515:0] b_d,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
    ot_qfd_xcst #(.AW(24), .NW(18), .XOFF(2)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d), .a_r(),
        .b_d(a_d), .b_r(1'b1), .tap_d(tap_d));
endmodule

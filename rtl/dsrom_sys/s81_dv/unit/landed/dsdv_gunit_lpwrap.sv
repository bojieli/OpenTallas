`timescale 1ns/1ps
// PL-GUNIT (10-18): behavioural-bench wrapper -- presents the LANDED parent dsdv_gunit_lp (lp.py, reschedule mode) under
// the flat parent's name and ports, both region clocks on one clock (as on the die: related, neighbour-relative), so
// test/tb_dsdv_gunit.sv (GUNIT_GATE vs tools/hdc_golden_v41) runs unchanged on the landed parent.  Bench only.
// The landing at the stop boundary (L0|L2) re-schedules the N-side rung by +3 edges each way (record "rescheduled_nets"),
// so N- and S-side beats reach the stop 3 edges apart and the tb's per-case latency check sees 0..3-edge jitter between
// cases.  GUNIT_LP_SCOMP=k adds the die-side compensation the compiler would schedule: k edges on vi_s and on vo_s (k = 3
// makes the unit exactly 'flat + 3' on every rung port, so router / HC latency must again be one constant).
`ifndef GUNIT_LP_SCOMP
`define GUNIT_LP_SCOMP 0
`endif
module dsdv_gunit #(
    parameter integer V    = 276,
    parameter integer MUT  = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d,
    output wire          fault
);
    localparam integer SC = `GUNIT_LP_SCOMP;
    wire [V-1:0] vi_s_c, vo_s_c;
    ot_pl_pad #(.W(V), .N(SC)) u_ci (.ck(clk), .d(vi_s), .q(vi_s_c));
    ot_pl_pad #(.W(V), .N(SC)) u_co (.ck(clk), .d(vo_s_c), .q(vo_s));
    dsdv_gunit_lp #(.V(V)) u_lp (.ck_hc(clk), .ck_rt(clk), .rst_n(rst_n), .sid(sid), .vi_s(vi_s_c), .vo_s(vo_s_c),
        .vi_n(vi_n), .vo_n(vo_n), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .fault(fault));
endmodule

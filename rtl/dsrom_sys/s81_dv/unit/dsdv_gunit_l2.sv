`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l2 -- G-unit leaf L2 (4th of 6 from the top): the column-3 V-rung stop.
//
// Stack (N -> S, each 680 um wide): L5 tail | L4 finish | L0 HP roots | L2 stop | L1 select | L3 weights.
//   rung     ot_dsdv_vstop (unchanged): rn_* = the N side (toward L0 .. L5, s_3N), rs_* = the S side (L1, L3, s_3S);
//            taps + sinks SC (kind 5) and HP (kind 7); injects the unit's CTL rows both ways on one edge.
//   SC       the vstop's own deliver flops (dl_*) leave on the S face to L1 unfiltered (L1 filters kind 5 behind its
//            input flop: no extra edge on the router's critical path).
//   HP       kind 7 filtered into a registered copy, N face to L0 (off the critical path).
//   CTL      rct (L1: router rows) and hct (L0: HC rows relayed from L5) are zero when idle; their OR enters the vstop
//            inject flops; both on one edge is a sticky fault (the compiler never schedules it; no arbitration).
//   cw / sid E-face input flops, then one output flop per face (S: L1, N: L0).
//   fault    output flop: vstop | L1 | L0 | collision.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 9 = the CTL rows injected northbound only.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l2 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // N face (L0)
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    output reg           hp_av, output reg [275:0] hp_a, output reg hp_bv, output reg [275:0] hp_b,
    output wire          cwn_v, output wire [9:0] cwn_a, output wire [255:0] cwn_d, output wire [3:0] sidn,
    input  wire          hct_v, input wire [275:0] hct_b, input wire hf,
    // S face (L1)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    output wire          dl_av, output wire [275:0] dl_a, output wire dl_bv, output wire [275:0] dl_b,
    output wire          cws_v, output wire [9:0] cws_a, output wire [255:0] cws_d, output wire [3:0] sids,
    input  wire          rct_v, input wire [275:0] rct_b, input wire rf,
    // E face (unit pins)
    input  wire [3:0]    sid,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d,
    output reg           fault
);
    localparam [7:0] KSC = 8'h20, KHP = 8'h80;
    wire f_vs, in_v = rct_v | hct_v; wire [275:0] in_b = rct_b | hct_b;
    // rung: vi_s = northbound arrivals (from L1), vo_n = toward L0; vi_n = southbound arrivals (from L0), vo_s = toward L1
    ot_dsdv_vstop #(.V(276)) u_vs (.clk(clk), .rst_n(rst_n), .tap_k(KSC | KHP), .sink_k(KSC | KHP),
        .vi_s(rs_i), .vo_n(rn_o), .vi_n(rn_i), .vo_s(rs_o), .dl_nv(dl_av), .dl_n(dl_a), .dl_sv(dl_bv), .dl_s(dl_b),
        .in_nv(in_v), .in_n(in_b), .in_sv(MUT == 9 ? 1'b0 : in_v), .in_s(MUT == 9 ? 276'd0 : in_b), .fault(f_vs));
    // HP copy for L0 (kind 7)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hp_av <= 1'b0; hp_bv <= 1'b0; end
        else begin hp_av <= dl_av && dl_a[3:1] == 3'd7; hp_bv <= dl_bv && dl_b[3:1] == 3'd7; end
    always @(posedge clk) begin hp_a <= dl_a; hp_b <= dl_b; end
    // cw / sid: E input flop, then one output flop per face
    wire [270:0] cw_q;
    dsdv_gunit_pass #(.W(271), .N(1)) u_cwi (.clk(clk), .rst_n(rst_n), .d({cw_d, cw_a, cw_v}), .q(cw_q));
    dsdv_gunit_pass #(.W(271), .N(1)) u_cwn (.clk(clk), .rst_n(rst_n), .d(cw_q), .q({cwn_d, cwn_a, cwn_v}));
    dsdv_gunit_pass #(.W(271), .N(1)) u_cws (.clk(clk), .rst_n(rst_n), .d(cw_q), .q({cws_d, cws_a, cws_v}));
    reg [3:0] sid_q, sn_q, ss_q;
    always @(posedge clk) begin sid_q <= sid; sn_q <= sid_q; ss_q <= sid_q; end
    assign sidn = sn_q; assign sids = ss_q;
    // collision + fault
    reg col, rf_q, hf_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin col <= 1'b0; rf_q <= 1'b0; hf_q <= 1'b0; fault <= 1'b0; end
        else begin
            col <= col | (rct_v & hct_v); rf_q <= rf; hf_q <= hf;
            fault <= f_vs | rf_q | hf_q | col;
        end
endmodule

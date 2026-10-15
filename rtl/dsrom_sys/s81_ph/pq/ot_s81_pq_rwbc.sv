`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_pq_rwbc: the COUNT-ONLY return leaf of the S81 PQ core under PQ return topology G (s81-die lead r6 2026-10-14
// 16:35: the gather root leaves are THE roots, VM writes stay the capture's; the PQ core still needs its per-group,
// per-tag row counts ga_i and group faults q2f_i).  s81-die-rtl-bind r3 2026-10-14.
// = the count half of ot_s81_pq_rwb_core (the reference spine's T_RET group, ot_v41_pqc_ret) with the SAME stages, so
//   ga / q2f are cycle-identical to an RWB fed the same root words: pin register (PIN 1) -> RPT 1 repeater -> one-hot
//   tag registers -> registered popcount ga; q2f = OR over the group of (v && (e || !live[tag])) one stage later, ORed with
//   the registered faults.
// Inputs per region r (a die TAP of the gather's t_capture root word r = {e, pos3, row16, fp32 32, v}):
//   r_v[r] = t_capture[53r], r_tag[2r +: 2] = row[15:14] = t_capture[53r+48 : 53r+47] (PQ rows carry the op tag in the
//   top two row bits), r_e[r] = t_capture[53r+52];  g_flt = the gather's sticky fault t_capture[6944] (the gather root
//   faults; the native roots' r_flt), live = the PQ core's mdr_o[4*CFW +: 4] = mdr_o[455:452] (the four live bits; s81-die r6b: the die carries 4 b, not 458).
// Outputs: ga[4t +: 4] = number of the group's regions with a valid row of tag t this cycle (NR <= 15), q2f.
// Masters (die slots physical/s81_die_pins/v19/pq_count_slots.json, x-tiling 15 / 2 / 15 repeating):
//   ot_s81_pq_rwbc15, ot_s81_pq_rwbc2.  Clock: the PQ stream clock.
// Mutant OT_S81_PQ_RWBC_MUT_GA: the group's last region is not counted (the RWB's GA mutant).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_pq_rwbc_core #(
    parameter integer NR = 15,
    parameter integer VAW = 19,
    parameter integer RPT = 1,
    parameter integer CFW = 5 * VAW + 18,
    parameter integer GRW = 4 * CFW + 4 + 2
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [NR-1:0]   r_v,
    input  wire [2*NR-1:0] r_tag,
    input  wire [NR-1:0]   r_e,
    input  wire            g_flt,
    input  wire [3:0]      live_i,      // = the PQ core's mdr_o[4*CFW +: 4] (the live bits; the die slices them, s81-die r6b)
    output reg             q2f,
    output reg  [15:0]     ga
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    // pin registers (PIN 1)
    reg [NR-1:0]   a_v, a_e;
    reg [2*NR-1:0] a_tag;
    always @(posedge clk) begin a_v <= r_v; a_e <= r_e; a_tag <= r_tag; end
    // stage 0: the repeater (RPT) and the registered root inputs
    wire [NR-1:0]   p_v, p_e;
    wire [2*NR-1:0] p_tag;
    ot_hdc_delay #(.W(NR), .D(RPT), .RESET(1)) u_prv (.clk(clk), .rst_n(rst_l[0]), .d(a_v), .q(p_v));
    ot_hdc_delay #(.W(NR + 2*NR), .D(RPT)) u_prd (.clk(clk), .rst_n(rst_l[0]), .d({a_e, a_tag}), .q({p_e, p_tag}));
    reg [NR-1:0] q0_v, q0_e;
    always @(posedge clk or negedge rst_l[0]) if (!rst_l[0]) q0_v <= {NR{1'b0}}; else q0_v <= p_v;
    always @(posedge clk) q0_e <= p_e;
    // the group's configuration replica: only the live bits {live[3:0]} = rep[4*CFW +: 4] are read
    wire [3:0] live;
    ot_v41_kreg #(.W(4)) u_rep (.clk(clk), .arst_n(rst_l[0]), .d(live_i), .q(live));
    wire [4*NR-1:0] oh_cnt;
    reg  [NR-1:0]   q1_f;
    genvar gk;
    generate for (gk = 0; gk < NR; gk = gk + 1) begin : g_reg
        wire [3:0] ohd = 4'b0001 << p_tag[2*gk +: 2];
        wire [3:0] oh_l, oh_c;   // the valid tag one-hot: live select / count copies (the RWB's u_oh3 / u_oh4)
        ot_v41_kreg #(.W(4), .AR(1)) u_ohl (.clk(clk), .arst_n(rst_l[0]), .d(ohd & {4{p_v[gk]}}), .q(oh_l));
        ot_v41_kreg #(.W(4), .AR(1)) u_ohc (.clk(clk), .arst_n(rst_l[0]), .d(ohd & {4{p_v[gk]}}), .q(oh_c));
        assign oh_cnt[4*gk +: 4] = oh_c;
        wire live_m = |(live & oh_l);
        always @(posedge clk or negedge rst_l[0])
            if (!rst_l[0]) q1_f[gk] <= 1'b0;
            else q1_f[gk] <= q0_v[gk] && (q0_e[gk] || !live_m);
    end endgenerate
    reg       flt_q;
    reg [NR-1:0] gm;
    integer kt, kr;
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) begin q2f <= 1'b0; ga <= 16'd0; flt_q <= 1'b0; end
        else begin
            flt_q <= g_flt;                       // pin flop (the RWB's r_flt register)
            q2f <= |q1_f || flt_q;
            for (kt = 0; kt < 4; kt = kt + 1) begin
                gm = {NR{1'b0}};
                for (kr = 0; kr < NR; kr = kr + 1) gm[kr] = oh_cnt[4 * kr + kt];
`ifdef OT_S81_PQ_RWBC_MUT_GA
                gm[NR-1] = 1'b0;
`endif
                ga[4*kt +: 4] <= 4'($countones(gm));
            end
        end
endmodule

module ot_s81_pq_rwbc15 (
    input  wire clk, rst_n,
    input  wire [14:0] r_v, input wire [29:0] r_tag, input wire [14:0] r_e, input wire g_flt,
    input  wire [3:0] live,
    output wire q2f, output wire [15:0] ga
);
    ot_s81_pq_rwbc_core #(.NR(15)) u_g (.clk(clk), .rst_n(rst_n), .r_v(r_v), .r_tag(r_tag), .r_e(r_e), .g_flt(g_flt),
        .live_i(live), .q2f(q2f), .ga(ga));
endmodule

module ot_s81_pq_rwbc2 (
    input  wire clk, rst_n,
    input  wire [1:0] r_v, input wire [3:0] r_tag, input wire [1:0] r_e, input wire g_flt,
    input  wire [3:0] live,
    output wire q2f, output wire [15:0] ga
);
    ot_s81_pq_rwbc_core #(.NR(2)) u_g (.clk(clk), .rst_n(rst_n), .r_v(r_v), .r_tag(r_tag), .r_e(r_e), .g_flt(g_flt),
        .live_i(live), .q2f(q2f), .ga(ga));
endmodule

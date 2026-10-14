`timescale 1ns/1ps
// ot_s81_pq_rwb: the S81 PQ row write-back block (RWB), one per tier-half return group (s81-romB3 2026-10-14; the die's
// f_pq / t_pq interface, el1013-s81-gather.log 11:21 settlement, PQ full-shape design option C:
// results/uarch/dsrom_s81_pq_fullshape_design_20261007 "12 RWB, one per tier-half (10 or 11 regions)").
// Function = the reference spine's T_RET group (ot_v41_pqc_ret, physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv)
// for NR regions, bit- and cycle-exact: root return stages 0-3, the per-tag configuration replica (458 b from the PQ
// core's mdr_o), the regions' VM writes (w_we / w_addr / w_data) and the per-tag row popcount ga (4 b a tag, <= 15).
// Changes vs the reference, none functional on the reference's ports:
//   * NR up to 15 (the reference's popcount vector was 8 b: NR <= 8); the native core groups 128 regions as 12 RWBs
//     (8 x 11 + 4 x 10, ga_i 12 x 16 b, q2f_i 12 b).
//   * registered faces: PIN 1 (input pin flops on every r_*, output pin flops on every w_*) with RPT 1, the same two
//     stages each way as the reference's PIN 0 / RPT 2 repeaters (the end block abuts the RWB: repeaters replaced, not added).
//   * r_flt[NR]: the regions' root faults (ot_s81_pq_ret_root_cam_p.fault), registered and ORed into the group fault
//     q2f (the design's "the RWB ORs the root fault into the spine fault"); r_flt = 0 leaves q2f identical.
// Two hardened masters (they differ in width only, 11 vs 10 regions; no strap, no tied port): ot_s81_pq_rwb11 x8,
// ot_s81_pq_rwb10 x4.  Clock: the PQ stream clock (stream_1p2), as the PQ core.
module ot_s81_pq_rwb_core #(
    parameter integer NR = 11,
    parameter integer VAW = 19,
    parameter integer PQ = 1,
    parameter integer RPT = 1,
    parameter integer PIN = 1,
    parameter integer CFW = 5 * VAW + 18,
    parameter integer GRW = 4 * CFW + 4 + 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NR-1:0]     r_v,
    input  wire [16*NR-1:0]  r_row,
    input  wire [3*NR-1:0]   r_pos,
    input  wire [32*NR-1:0]  r_fp32,
    input  wire [16*NR-1:0]  r_bf16,
    input  wire [NR-1:0]     r_e,
    input  wire [GRW-1:0]    mdr,
    input  wire [NR-1:0]     r_flt,      // the regions' root faults (sticky at the root), ORed into the group fault
    output wire [NR-1:0]     w_we,
    output wire [NR*VAW-1:0] w_addr,
    output wire [NR*32-1:0]  w_data,
    output reg               q2f,
    output reg  [15:0]       ga
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    // screen pin registers (PIN = 1)
    wire [NR-1:0]    i_v, i_e;
    wire [16*NR-1:0] i_row, i_bf;
    wire [3*NR-1:0]  i_pos;
    wire [32*NR-1:0] i_f32;
    wire [NR-1:0]     o_we;
    wire [NR*VAW-1:0] o_addr;
    wire [NR*32-1:0]  o_data;
    generate if (PIN != 0) begin : g_pin
        reg [NR-1:0] a_v, a_e; reg [16*NR-1:0] a_row, a_bf; reg [3*NR-1:0] a_pos; reg [32*NR-1:0] a_f32;
        reg [NR-1:0] b_we; reg [NR*VAW-1:0] b_addr; reg [NR*32-1:0] b_data;
        always @(posedge clk) begin
            a_v <= r_v; a_e <= r_e; a_row <= r_row; a_bf <= r_bf16; a_pos <= r_pos; a_f32 <= r_fp32;
            b_we <= o_we; b_addr <= o_addr; b_data <= o_data;
        end
        assign {i_v, i_e, i_row, i_bf, i_pos, i_f32} = {a_v, a_e, a_row, a_bf, a_pos, a_f32};
        assign {w_we, w_addr, w_data} = {b_we, b_addr, b_data};
    end else begin : g_nopin
        assign {i_v, i_e, i_row, i_bf, i_pos, i_f32} = {r_v, r_e, r_row, r_bf16, r_pos, r_fp32};
        assign {w_we, w_addr, w_data} = {o_we, o_addr, o_data};
    end endgenerate
    // stage 0: repeaters and the registered root inputs
    reg [NR-1:0]    q0_v, q0_e;
    reg [14*NR-1:0] q0_row;
    reg [16*NR-1:0] q0_bf;
    reg [3*NR-1:0]  q0_pos;
    reg [32*NR-1:0] q0_f32;
    wire [NR-1:0]    p_v, p_e;
    wire [16*NR-1:0] p_row, p_bf;
    wire [3*NR-1:0]  p_pos;
    wire [32*NR-1:0] p_f32;
    ot_hdc_delay #(.W(NR), .D(RPT), .RESET(1)) u_prv (.clk(clk), .rst_n(rst_l[0]), .d(i_v), .q(p_v));
    ot_hdc_delay #(.W(NR + 16*NR + 16*NR + 3*NR + 32*NR), .D(RPT)) u_prd (.clk(clk), .rst_n(rst_l[0]),
        .d({i_e, i_row, i_bf, i_pos, i_f32}), .q({p_e, p_row, p_bf, p_pos, p_f32}));
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) q0_v <= {NR{1'b0}};
        else q0_v <= p_v;
    integer kr0;
    always @(posedge clk) begin
        q0_e <= p_e; q0_bf <= p_bf; q0_pos <= p_pos; q0_f32 <= p_f32;
        for (kr0 = 0; kr0 < NR; kr0 = kr0 + 1) q0_row[14*kr0 +: 14] <= p_row[16*kr0 +: 14];
    end
    // the group's configuration replica (kept)
    wire [GRW-1:0] rep;
    ot_v41_kreg #(.W(GRW)) u_rep (.clk(clk), .arst_n(rst_l[0]), .d(mdr), .q(rep));
    reg [NR-1:0]     w_we_r;
    reg [NR*VAW-1:0] w_addr_r;
    reg [NR*32-1:0]  w_data_r;
    reg [NR-1:0]     q1_v, q1_f;
    reg [NR*VAW-1:0] q1_a, q1_p;
    reg [NR*32-1:0]  q1_f32;
    reg [NR*16-1:0]  q1_bf;
    wire [4*NR-1:0]  oh_cnt;
    genvar gk;
    generate for (gk = 0; gk < NR; gk = gk + 1) begin : g_reg
        wire [1:0] rtag = (PQ != 0) ? p_row[16*gk + 14 +: 2] : rep[4*CFW + 4 +: 2];
        wire [3:0] ohd = 4'b0001 << rtag;
        wire [19:0] oh;
        ot_v41_kreg #(.W(4)) u_oh0 (.clk(clk), .arst_n(rst_l[0]), .d(ohd), .q(oh[3:0]));
        ot_v41_kreg #(.W(4)) u_oh1 (.clk(clk), .arst_n(rst_l[0]), .d(ohd), .q(oh[7:4]));
        ot_v41_kreg #(.W(4)) u_oh2 (.clk(clk), .arst_n(rst_l[0]), .d(ohd), .q(oh[11:8]));
        ot_v41_kreg #(.W(4), .AR(1)) u_oh3 (.clk(clk), .arst_n(rst_l[0]), .d(ohd & {4{p_v[gk]}}), .q(oh[15:12]));
        ot_v41_kreg #(.W(4), .AR(1)) u_oh4 (.clk(clk), .arst_n(rst_l[0]), .d(ohd & {4{p_v[gk]}}), .q(oh[19:16]));
        assign oh_cnt[4*gk +: 4] = oh[19:16];
        reg  [17:0]   rsfm_d;
        wire [13:0]   rs_m;
        wire [3:0]    fm_m;
        integer t0, t2;
        always @* begin
            rsfm_d = '0;
            for (t0 = 0; t0 < 4; t0 = t0 + 1) rsfm_d = rsfm_d | (rep[CFW*t0 +: 18] & {18{ohd[t0]}});
        end
        ot_v41_kreg #(.W(18)) u_rsfm (.clk(clk), .arst_n(rst_l[0]), .d(rsfm_d), .q({rs_m, fm_m}));
        reg [VAW-1:0] ob_m, o1_m, o3_m, o5_m, o7_m;
        reg           live_m;
        integer t;
        always @* begin
            ob_m = '0; o1_m = '0; o3_m = '0; o5_m = '0; o7_m = '0; live_m = 1'b0;
            for (t = 0; t < 4; t = t + 1) begin
                ob_m = ob_m | (rep[CFW*t + 4*VAW + 18 +: VAW] & {VAW{oh[t]}});
                o7_m = o7_m | (rep[CFW*t + 3*VAW + 18 +: VAW] & {VAW{oh[8 + t]}});
                o5_m = o5_m | (rep[CFW*t + 2*VAW + 18 +: VAW] & {VAW{oh[8 + t]}});
                o3_m = o3_m | (rep[CFW*t + VAW + 18 +: VAW] & {VAW{oh[4 + t]}});
                o1_m = o1_m | (rep[CFW*t + 18 +: VAW] & {VAW{oh[4 + t]}});
                live_m = live_m | (rep[4*CFW + t] & oh[12 + t]);
            end
        end
        wire [VAW-1:0] a_s;
        wire           row_ge;
        ot_v41_ksadd #(.W(VAW)) u_a (.a(ob_m), .b(VAW'(q0_row[14*gk +: 14])), .cin(1'b0), .s(a_s), .cout());
        ot_v41_ksadd #(.W(14)) u_rs (.a(q0_row[14*gk +: 14]), .b(~rs_m), .cin(1'b1), .s(), .cout(row_ge));
        always @(posedge clk) begin
            q1_a[VAW*gk +: VAW] <= a_s;
            case (q0_pos[3*gk +: 3])
                3'd0: q1_p[VAW*gk +: VAW] <= '0;
                3'd1: q1_p[VAW*gk +: VAW] <= o1_m;
                3'd2: q1_p[VAW*gk +: VAW] <= {o1_m[VAW-2:0], 1'b0};
                3'd3: q1_p[VAW*gk +: VAW] <= o3_m;
                3'd4: q1_p[VAW*gk +: VAW] <= {o1_m[VAW-3:0], 2'b0};
                3'd5: q1_p[VAW*gk +: VAW] <= o5_m;
                3'd6: q1_p[VAW*gk +: VAW] <= {o3_m[VAW-2:0], 1'b0};
                default: q1_p[VAW*gk +: VAW] <= o7_m;
            endcase
            q1_f32[32*gk +: 32] <= q0_f32[32*gk +: 32];
            q1_bf[16*gk +: 16] <= q0_bf[16*gk +: 16];
        end
        always @(posedge clk or negedge rst_l[0])
            if (!rst_l[0]) begin q1_v[gk] <= 1'b0; q1_f[gk] <= 1'b0; end
            else begin
                q1_v[gk] <= q0_v[gk];
                q1_f[gk] <= q0_v[gk] && (q0_e[gk] || !live_m);
            end
        wire       s_hi = fm_m[0] || (fm_m[1] && fm_m[3]);
        wire       s_lo = fm_m[0] || (fm_m[1] && fm_m[2]);
        reg [2:0]  q1_gs;
        always @(posedge clk) q1_gs <= {row_ge, s_hi, s_lo};
        wire [VAW-1:0] w_s;
        ot_v41_ksadd #(.W(VAW)) u_w (.a(q1_a[VAW*gk +: VAW]), .b(q1_p[VAW*gk +: VAW]), .cin(1'b0), .s(w_s), .cout());
        reg [VAW-1:0] q1b_w;
        reg [31:0]    q1b_f32;
        reg [15:0]    q1b_bf;
        always @(posedge clk) begin
            q1b_w <= w_s; q1b_f32 <= q1_f32[32*gk +: 32]; q1b_bf <= q1_bf[16*gk +: 16];
        end
        wire [3:0] q2_sel;
        genvar gsl;
        for (gsl = 0; gsl < 4; gsl = gsl + 1) begin : g_sel
            wire [2:0] q1_g;
            ot_v41_kreg #(.W(3)) u_g (.clk(clk), .arst_n(rst_l[0]), .d(q1_gs), .q(q1_g));
            ot_v41_kreg #(.W(1)) u_s (.clk(clk), .arst_n(rst_l[0]), .d(q1_g[2] ? q1_g[1] : q1_g[0]), .q(q2_sel[gsl]));
        end
        reg [VAW-1:0] q2_a;
        reg [31:0]    q2_f32;
        reg [15:0]    q2_bf;
        always @(posedge clk) begin
            q2_a <= q1b_w; q2_f32 <= q1b_f32; q2_bf <= q1b_bf;
        end
        always @(posedge clk) begin
            w_addr_r[VAW*gk +: VAW] <= q2_a;
            for (t2 = 0; t2 < 4; t2 = t2 + 1)
`ifdef OT_S81_PQ_RWB_MUT_DATA
                w_data_r[32*gk + 8*t2 +: 8] <= q2_sel[t2] ? q2_f32[8*(3-t2) +: 8] : ((t2 < 2) ? 8'd0 : q2_bf[8*(t2-2) +: 8]);
`else
                w_data_r[32*gk + 8*t2 +: 8] <= q2_sel[t2] ? q2_f32[8*t2 +: 8] : ((t2 < 2) ? 8'd0 : q2_bf[8*(t2-2) +: 8]);
`endif
        end
    end endgenerate
    ot_hdc_delay #(.W(NR), .D(RPT), .RESET(1)) u_pwv (.clk(clk), .rst_n(rst_l[0]), .d(w_we_r), .q(o_we));
    ot_hdc_delay #(.W(NR*VAW + NR*32), .D(RPT)) u_pwd (.clk(clk), .rst_n(rst_l[0]), .d({w_addr_r, w_data_r}),
                                                       .q({o_addr, o_data}));
    reg [NR-1:0] q2_v, q1b_v;
    integer kt, kr;
    reg [NR-1:0] gm;
    reg [NR-1:0] flt_q;
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) begin w_we_r <= {NR{1'b0}}; q2_v <= {NR{1'b0}}; q1b_v <= {NR{1'b0}}; q2f <= 1'b0; ga <= 16'd0; flt_q <= {NR{1'b0}}; end
        else begin
            q1b_v <= q1_v; q2_v <= q1b_v; w_we_r <= q2_v;
            flt_q <= r_flt;
            q2f <= |q1_f || |flt_q;
            for (kt = 0; kt < 4; kt = kt + 1) begin
                gm = {NR{1'b0}};
                for (kr = 0; kr < NR; kr = kr + 1) gm[kr] = oh_cnt[4 * kr + kt];
`ifdef OT_S81_PQ_RWB_MUT_GA
                gm[NR-1] = 1'b0;                 // mutant: the group's last region is not counted
`endif
                ga[4*kt +: 4] <= 4'($countones(gm));
            end
        end
endmodule

module ot_s81_pq_rwb11 (
    input  wire          clk, rst_n,
    input  wire [10:0]   r_v, input wire [175:0] r_row, input wire [32:0] r_pos, input wire [351:0] r_fp32,
    input  wire [175:0]  r_bf16, input wire [10:0] r_e, input wire [10:0] r_flt,
    input  wire [457:0]  mdr,
    output wire [10:0]   w_we, output wire [208:0] w_addr, output wire [351:0] w_data,
    output wire          q2f, output wire [15:0] ga
);
    ot_s81_pq_rwb_core #(.NR(11)) u_g (.clk(clk), .rst_n(rst_n), .r_v(r_v), .r_row(r_row), .r_pos(r_pos),
        .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .mdr(mdr), .r_flt(r_flt), .w_we(w_we), .w_addr(w_addr),
        .w_data(w_data), .q2f(q2f), .ga(ga));
endmodule
module ot_s81_pq_rwb10 (
    input  wire          clk, rst_n,
    input  wire [9:0]    r_v, input wire [159:0] r_row, input wire [29:0] r_pos, input wire [319:0] r_fp32,
    input  wire [159:0]  r_bf16, input wire [9:0] r_e, input wire [9:0] r_flt,
    input  wire [457:0]  mdr,
    output wire [9:0]    w_we, output wire [189:0] w_addr, output wire [319:0] w_data,
    output wire          q2f, output wire [15:0] ga
);
    ot_s81_pq_rwb_core #(.NR(10)) u_g (.clk(clk), .rst_n(rst_n), .r_v(r_v), .r_row(r_row), .r_pos(r_pos),
        .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .mdr(mdr), .r_flt(r_flt), .w_we(w_we), .w_addr(w_addr),
        .w_data(w_data), .q2f(q2f), .ga(ga));
endmodule

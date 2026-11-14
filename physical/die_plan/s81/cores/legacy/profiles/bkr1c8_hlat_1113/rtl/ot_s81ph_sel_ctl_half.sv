`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_sel_ctl_half -- CLAUDE S81-PH selector control, HALF-RATE search (SAFE backstop, CLAUDE DIRECTIVE
// 2026-10-07 05:00).  Generated from ot_hdc_v41x_sel_ctl (rtl/hdc/v41x/ot_hdc_v41x_sel.sv) by
// tools/s81_ph/make_sel_ctl_half.py: the two threshold-search units (selt_c cd3337221-b SS -541 on their sum trees)
// run UNCHANGED on a clock-gated half-rate edge (latch + AND); the control FSM stays on ck with its waits / holds
// doubled.  The searches are consistent for growing counts (native comment), so a result sampled on a slow edge is
// as valid as a fast one; the final results are taken after the doubled waits, when counts are static: exact.
// SDC: u_ctl.u_cs.* / u_ctl.u_fs.* internal paths multicycle setup 2 / hold 1 (physical/s81_ph_views/selector/
// selt_c_half.sdc).  Cost: search latency 2x (+~16 cycles per wait), running-bound refresh at half rate.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_sel_ctl_half #(
    parameter integer Q  = 4,
    parameter integer K  = 512,
    parameter integer KW = $clog2(K + 1),
    parameter integer CB = KW + 1,
    // CLAUDE S81-PH tiles (defaults = the native unit): XD extra edges each way between the control and the slices
    // (the waits and holdoffs grow by the round trip), PERM 1: slice i serves quarter qs[2i +: 2] (tie quotas in
    // quarter order)
    parameter integer XD   = 0,
    parameter integer PERM = 0
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire [KW-1:0]           k_in,
    input  wire                    k_ld,
    input  wire [2*Q-1:0]          qs,
    input  wire [Q*16*(CB+4)-1:0]  s_gc,
    input  wire [Q*16*(CB+4)-1:0]  s_gf,
    input  wire [Q*16*CB-1:0]      s_bc,
    input  wire [Q*16*CB-1:0]      s_bf,
    input  wire [Q-1:0]            s_last,
    input  wire [Q-1:0]            s_hfin,
    input  wire [Q-1:0]            s_stopped,
    input  wire [Q-1:0]            s_done2,
    input  wire [Q-1:0]            s_emitted,
    input  wire [Q-1:0]            s_ovf,
    output reg  [15:0]             c_T,
    output reg  [7:0]              c_Bt,
    output reg                     c_fclr,
    output wire [3:0]              c_cg,
    output wire [3:0]              c_fg,
    output reg                     c_ing,
    output reg                     c_stop,
    output reg                     c_p2,
    output reg                     c_p3,
    output reg                     c_rep,
    output reg  [15:0]             c_st,
    output reg  [Q*(KW+1)-1:0]     c_rem,
    output reg                     c_hclr,
    output reg                     rep_req,
    output reg                     ovf,
    output wire                    busy
);
    localparam integer XW   = CB + 10;              // search sums
    localparam integer QC   = KW + 1;               // coarse quota width
    localparam integer XR   = 2 * XD;               // round trip added by the tile hops
    // HALF RATE (SAFE backstop): the two search units run on ck gated every other cycle (latch + AND); the slice round
    // trip of 3 + XR fast edges + 1 is 2 x (3 + XRH + 1) slow-edge aligned (XR even): XRH = XR / 2 - 1 (bench-checked); every wait /
    // hold in fast edges is twice the slow-edge latency plus the gate phase
    localparam integer XRH  = (XR >= 2) ? XR / 2 - 1 : 0;   // bench: XR/2-2 fails (res aligned one slow edge early), -1 and 0 pass
    localparam integer WAIT = 2 * (14 + XRH) + 2;
    localparam integer HOLD = 2 * (26 + 2 * XRH) + 4;
    localparam integer HC0  = 2 * (20 + 2 * XRH) + 4, HF0 = 2 * (36 + 2 * XRH) + 4, CLRW = 2 * (20 + 2 * XRH) + 4;
    localparam integer TW   = 8;
    localparam integer KI   = K;
    localparam [QC-1:0] KQ  = KI[QC-1:0];
    localparam [XW-1:0] QINV = {XW{1'b1}};          // a quota no count reaches
    localparam [2:0] C_ING = 3'd0, C_FL = 3'd1, C_P2 = 3'd2, C_W2 = 3'd3, C_R = 3'd4, C_P3 = 3'd5, C_CLR = 3'd6;

    // status inputs, registered
    reg [Q-1:0] st_last, st_hfin, st_stopped, st_done2, st_emitted, st_ovf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin st_last <= 0; st_hfin <= 0; st_stopped <= 0; st_done2 <= 0; st_emitted <= 0; st_ovf <= 0; end
        else begin
            st_last <= s_last; st_hfin <= s_hfin; st_stopped <= s_stopped; st_done2 <= s_done2;
            st_emitted <= s_emitted; st_ovf <= s_ovf;
        end
    end

    // the two searches
    reg  [QC-1:0] kq;
    reg  [XW-1:0] qf;
    wire [7:0]    cres_b, fres_b;
    wire [XW-1:0] cres_above, fres_above;
    wire          cres_ok, fres_ok;
    wire [Q*CB-1:0] cres_eq, fres_eq;
    // clock gate: en toggles every fast edge; latched while clk is low; ck_h = the fast edges that end an en cycle
    reg hen_q, hen_l;
    always @(posedge clk or negedge rst_n) if (!rst_n) hen_q <= 1'b0; else hen_q <= ~hen_q;
    always @(*) if (!clk) hen_l = hen_q;
    wire ck_h = clk & hen_l;
    ot_s81ph_native_sel_su #(.Q(Q), .CB(CB), .QW(QC), .XR(XRH)) u_cs (
        .clk(ck_h), .gs(s_gc), .bs(s_bc), .q(kq), .g_out(c_cg),
        .res_b(cres_b), .res_above(cres_above), .res_ok(cres_ok), .res_eq(cres_eq));
    ot_s81ph_native_sel_su #(.Q(Q), .CB(CB), .QW(XW), .XR(XRH)) u_fs (
        .clk(ck_h), .gs(s_gf), .bs(s_bf), .q(qf), .g_out(c_fg),
        .res_b(fres_b), .res_above(fres_above), .res_ok(fres_ok), .res_eq(fres_eq));

    reg  [2:0]    st;
    reg  [TW-1:0] wcnt, hold_c, hold_f;
    reg           kseen, hf_seen, bs_done;
    reg  [7:0]    bs, ls;
    reg  [QC-1:0] m, t;
    reg  [Q*CB-1:0] eq;
    wire [15:0]   tc = {cres_b, 8'h00};
    wire [15:0]   tf = {c_Bt, fres_b};
    wire          use_c = (st == C_ING) && kseen && (hold_c == 0) && cres_ok;
    wire          use_f = (st == C_ING) && kseen && (hold_c == 0) && (hold_f == 0) && fres_ok;
    wire [QC-1:0] kin_c = ({1'b0, k_in} > KQ) ? KQ : {1'b0, k_in};
    wire [XW-1:0] cab = cres_above;

    // tie quotas: t_q = max(0, t - ties in quarters below q)
    reg  [Q*QC-1:0] rem_d;
    reg  [CB+2:0]   pre;
    integer i;
    integer j;
    generate if (PERM == 0) begin : g_rq
        always @(*) begin
            pre = 0;
            for (i = 0; i < Q; i = i + 1) begin
                rem_d[QC*i +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre) ? t - pre[QC-1:0] : {QC{1'b0}};
                pre = pre + {3'b000, eq[CB*i +: CB]};
            end
        end
    end else begin : g_rqp
        // ties of the slices serving lower quarters
        always @(*) begin
            for (i = 0; i < Q; i = i + 1) begin
                pre = 0;
                for (j = 0; j < Q; j = j + 1)
                    if (qs[2*j +: 2] < qs[2*i +: 2]) pre = pre + {3'b000, eq[CB*j +: CB]};
                rem_d[QC*i +: QC] = ({{(CB+3-QC){1'b0}}, t} > pre) ? t - pre[QC-1:0] : {QC{1'b0}};
            end
        end
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= C_CLR; wcnt <= CLRW[TW-1:0]; c_T <= 0; c_Bt <= 0; c_fclr <= 1'b0; c_ing <= 1'b0; c_stop <= 1'b0;
            c_p2 <= 1'b0; c_p3 <= 1'b0; c_rep <= 1'b0; c_st <= 0; c_rem <= 0; c_hclr <= 1'b0; rep_req <= 1'b0;
            ovf <= 1'b0; kq <= 0; qf <= QINV; hold_c <= 0; hold_f <= 0; kseen <= 1'b0; hf_seen <= 1'b0;
            bs_done <= 1'b0; bs <= 0; ls <= 0; m <= 0; t <= 0; eq <= 0;
        end else begin
            c_fclr <= 1'b0; c_p2 <= 1'b0; c_p3 <= 1'b0; c_hclr <= 1'b0; rep_req <= 1'b0;
            if (hold_c != 0) hold_c <= hold_c - 1'b1;
            if (hold_f != 0) hold_f <= hold_f - 1'b1;
            if (wcnt != 0) wcnt <= wcnt - 1'b1;
            case (st)
                C_ING: begin
                    if (k_ld && !kseen) begin
                        kseen <= 1'b1; kq <= kin_c; hold_c <= HC0[TW-1:0]; hold_f <= HF0[TW-1:0];
                    end
                    // the running bound
                    if (use_c) begin
                        if (cres_b > c_Bt) begin
                            c_Bt <= cres_b; c_fclr <= 1'b1; hold_f <= HOLD[TW-1:0]; qf <= QINV;
                        end else if (cres_b == c_Bt)
                            qf <= {{(XW-QC){1'b0}}, kq} - cab;
                    end
                    if (use_c && use_f)          c_T <= (tc > c_T) ? ((tc > tf) ? tc : tf) : ((tf > c_T) ? tf : c_T);
                    else if (use_c && tc > c_T)  c_T <= tc;
                    else if (use_f && tf > c_T)  c_T <= tf;
                    if (&st_last) begin st <= C_FL; c_ing <= 1'b0; c_stop <= 1'b1; hf_seen <= 1'b0; bs_done <= 1'b0; end
                end
                C_FL: begin
                    if ((&st_hfin) && !hf_seen) begin hf_seen <= 1'b1; wcnt <= WAIT[TW-1:0]; end
                    if (hf_seen && wcnt == 0 && !bs_done) begin
                        bs_done <= 1'b1; bs <= cres_b; m <= kq - cab[QC-1:0];
                    end
                    if (bs_done && (&st_stopped)) begin
                        st <= C_P2; c_rep <= |st_ovf; ovf <= |st_ovf; rep_req <= |st_ovf;
                        c_st <= {bs, 8'h00}; c_p2 <= 1'b1; qf <= {{(XW-QC){1'b0}}, m};
                    end
                end
                C_P2: begin
                    if (&st_done2) begin st <= C_W2; wcnt <= WAIT[TW-1:0] + 2'd2; end   // + res_eq's (slow) edge
                end
                C_W2: begin
                    if (wcnt == 0) begin
                        st <= C_R; ls <= fres_b; t <= m - fres_above[QC-1:0]; eq <= fres_eq;
                    end
                end
                C_R: begin
                    st <= C_P3; c_rem <= rem_d; c_st <= {bs, ls}; c_p3 <= 1'b1; rep_req <= c_rep;
                end
                C_P3: begin
                    if (&st_emitted) begin st <= C_CLR; c_hclr <= 1'b1; wcnt <= CLRW[TW-1:0]; end
                end
                default: begin                     // C_CLR: the slices clear; stale search results drain
                    c_T <= 0; c_Bt <= 0; qf <= QINV; kseen <= 1'b0; c_rep <= 1'b0; c_stop <= 1'b0; ovf <= 1'b0;
                    if (wcnt == 0) begin st <= C_ING; c_ing <= 1'b1; end
                end
            endcase
        end
    end
    assign busy = (st != C_ING) || kseen;
endmodule

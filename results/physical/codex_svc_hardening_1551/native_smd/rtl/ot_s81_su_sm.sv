`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 SU softmax SE / SO, split into small hardened masters (el1011-s81su-sm, 2026-10-12; PHYSICAL SPEC SM v3).
// Replaces the SM lane tiles of ot_s81_su_tile (TK 4: ot_dsrom_su_softmax H 2 x LPH 16, 570,772 flops on one root) by,
// at each SM spine stop (2 heads; the stop's slots, write window and status are those of the old tile):
//   TAP/OUT ot_s81_su_smt x 1    : pin flops on the stop's own slots (aligned at the source: data rows 2 TI, 2 TI + 1;
//                                   parameter slots 0 .. NPS-1), registered row numbering (a misaligned row -> o_fo),
//                                   job state, the parameters, the s / pv rows out, the per-job config out, cos / sin
//                                   streamed to the divide engines, e / o rows in -> result staging -> write slots.
//   LANE    ot_s81_su_sml x 16 a head (one lane, position-independent; cfg sk_en on lane 0): s * scale, the score
//                                   buffer, the lane's running max, s + (-mb), exp -> e; lane 0 also runs the sink's
//                                   exp(sink + (-mb)) one slot ahead of the row (the same add + exp unit).
//   SUM     ot_s81_su_smc x 1 a head: the two chunk chains (8 lanes, 7 sequential adds) and the in-vector tree.
//   ROOT    ot_s81_su_smr x 1 a head: the 16 lane maxima -> max tree -> -mb; the streaming time levels of the row sum,
//                                   the tap at lt, den = es + exp(sink - mb).
//   DIVIDE  ot_s81_su_smd x 8 a head (one RoPE pair = lanes 2 p, 2 p + 1; cfg p): pv / den, BF16, the inverse RoPE of
//                                   the 64-element tail with the pair's cos / sin.
// Values: ot_dsrom_su_softmax (MARGIN 0, ADD6 0, EXP6 0, DIVF12 1) step for step, in the same order: the max is order
// free (ordered keys), every sum (chunk chain, in-vector tree, time levels, den) is inside one master exactly as in the
// unit; only latency moves (registered master boundaries + the slab's equal-depth relays; lanes run in lockstep).
// ---------------------------------------------------------------------------------------------------------------------

// ======================================================================================================== TAP / OUT
module ot_s81_su_smt #(
    parameter integer SM_H = 16, SM_LPH = 16, S_RD = 16, WS = 2, MUT = 0,
    parameter integer NPS = (S_RD < 5) ? S_RD : 5          // parameter slots wired (SO has 5 parameter rows)
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [3:0]             cfg_ti,                 // this stop's index among the SM stops (TI)
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [NPS*512-1:0]     dn_p_i,                 // spine slots 0 .. NPS-1 (parameter rows)
    // to the lanes / divide engines (registered).  The operand rows themselves (spine slots 2 TI, 2 TI + 1) do not
    // pass through this master: the slab relays them straight to the lanes / divide engines, 2 stations deeper than
    // these valids (this master's pin + valid registers), so they meet at the engines' pin flops.
    output reg                    s_v,                    // a score vector (SE)
    output reg                    p_v,                    // a PV vector (SO)
    output reg                    c_v,                    // SE configuration (a pulse, before the first score)
    output reg  [6:0]             c_nv,
    output reg  [2:0]             c_lt,
    output reg  [31:0]            c_scale,
    output reg  [63:0]            c_sink,                 // head 0, head 1
    output reg                    cs_v,                   // cos / sin pair cs_i (SO, after its parameters)
    output reg  [4:0]             cs_i,
    output reg  [63:0]            cs_d,                   // {cos, sin}
    // from the heads
    input  wire                   e_v_i,                  // e vector (both heads, lockstep)
    input  wire [1023:0]          e_d_i,
    input  wire                   o_v_i,                  // o vector (both heads, lockstep)
    input  wire [511:0]           o_d_i,                  // head 0 lanes 0..15, head 1 lanes 0..15 (BF16)
    input  wire                   den_v_i,                // den reached the divide engines
    input  wire                   f_i,                    // a divide engine's sticky fault
    // this stop's write slots (registered) and status
    output reg  [WS-1:0]          o_v,
    output reg  [WS*14-1:0]       o_a,
    output reg  [WS*16-1:0]       o_m,
    output reg  [WS*512-1:0]      o_d,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam [3:0] K_SE = 4, K_SO = 5;
    localparam integer SMW = SM_H * SM_LPH, RSM = SMW / 16;      // rows a beat (one score vector of every head)
    localparam integer R_SE = 2, R_SO = 1, R = 2;                // rows an event (2 heads x 16 lanes)
    localparam integer RW = 14 + 16 + 512;
`ifndef SYNTHESIS
    initial begin
        if (SM_LPH != 16) $fatal(1, "ot_s81_su_smt: 16 lanes a head");
        if (RSM != S_RD) $fatal(1, "ot_s81_su_smt: aligned tap needs rows a beat == S_RD");
        if (WS < 1) $fatal(1, "ot_s81_su_smt: write slots");
    end
`endif
    // regional reset relay
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;

    // ------------------------------------------------------------------ pin flops
    reg              dq_st;
    reg  [3:0]       dq_kind;
    reg  [7:0]       dq_jid;
    reg  [S_RD-1:0]  dq_v;
    reg  [NPS*512-1:0] dq_p;
    reg  [3:0]       ti;
    reg              ev_q, ov_q, dv_q, f_q;
    reg  [1023:0]    ed_q;
    reg  [511:0]     od_q;
    always @(posedge clk) begin
        dq_kind <= dn_kind_i; dq_jid <= dn_jid_i; dq_p <= dn_p_i; ti <= cfg_ti;
        ed_q <= e_d_i; od_q <= o_d_i;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; ev_q <= 1'b0; ov_q <= 1'b0; dv_q <= 1'b0; f_q <= 1'b0; end
        else begin dq_st <= dn_st_i; dq_v <= dn_v_i; ev_q <= e_v_i; ov_q <= o_v_i; dv_q <= den_v_i; f_q <= f_i; end

    // ------------------------------------------------------------------ job, row numbering (registered terms only)
    reg  [3:0]   jkind;
    reg          mine;
    reg  [7:0]   jid;
    reg  [3:0]   np;                                   // parameter rows of the job
    reg  [15:0]  rcnt;                                 // rows of the job before this cycle
    reg          pdone;                                // a pulse: the job's parameter rows are all in
    reg          ofault;
    wire [4:0]   pc_n;                                 // valid rows this cycle (a prefix of the slots)
    function automatic [4:0] popc(input [S_RD-1:0] v);
        integer i;
        begin popc = 0; for (i = 0; i < S_RD; i = i + 1) popc = popc + v[i]; end
    endfunction
    assign pc_n = popc(dq_v);
    wire         pcyc = mine && dq_v[0] && (rcnt < {12'd0, np});           // a parameter cycle
    wire         ocyc = mine && dq_v[0] && (rcnt >= {12'd0, np});          // an operand cycle (one beat)
    wire         misal = ocyc && (!(&dq_v) || ((rcnt - {12'd0, np}) & (RSM - 1)) != 0);
    reg  [511:0] prow0;                                // only its fields are used
    reg  [511:0] prow1, prow2, prow3, prow4;           // SE: prow1 the sinks; SO: cos lo / hi, sin lo / hi
    reg  [5:0]   cs_n;                                 // cos / sin pairs still to stream
    reg          shr;                                  // streaming this cycle (cs_n != 0)
    wire         shn = (pdone && jkind == K_SO) || (shr && cs_n != 6'd1);
    wire [15:0]  shk;                                  // kept copies of shr, one a 64-b slice of cos and of sin
    genvar gk;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_shk
        ot_s81_su_sm_keep_ff u_k (.clk(clk), .rst_n(rst_n), .d(shn), .q(shk[gk]));
    end endgenerate
    always @(posedge clk) begin : pcap
        integer s;
        reg [15:0] j;
        for (s = 0; s < NPS; s = s + 1) begin
            j = rcnt + s;
            if (pcyc && dq_v[s] && j < {12'd0, np}) begin
                if (j == 0) prow0 <= dq_p[512 * s +: 512];
                if (j == 1) prow1 <= dq_p[512 * s +: 512];
                if (j == 2) prow2 <= dq_p[512 * s +: 512];
                if (j == 3) prow3 <= dq_p[512 * s +: 512];
                if (j == 4) prow4 <= dq_p[512 * s +: 512];
            end
        end
        // stream: {prow2, prow1} (cos) and {prow4, prow3} (sin) shift one pair a cycle; slice k (64 b of each) on its own
        // kept copy of the shift enable (<= 128 loads a copy, not one 2,048-load net)
        for (s = 0; s < 16; s = s + 1)
            if (shk[s]) begin
                if (s < 7) begin
                    prow1[64 * s +: 64] <= prow1[64 * s + 32 +: 64]; prow3[64 * s +: 64] <= prow3[64 * s + 32 +: 64];
                end else if (s == 7) begin
                    prow1[448 +: 64] <= {prow2[31:0], prow1[480 +: 32]}; prow3[448 +: 64] <= {prow4[31:0], prow3[480 +: 32]};
                end else if (s < 15) begin
                    prow2[64 * (s - 8) +: 64] <= prow2[64 * (s - 8) + 32 +: 64];
                    prow4[64 * (s - 8) +: 64] <= prow4[64 * (s - 8) + 32 +: 64];
                end else begin
                    prow2[448 +: 64] <= {32'd0, prow2[480 +: 32]}; prow4[448 +: 64] <= {32'd0, prow4[480 +: 32]};
                end
            end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin jkind <= 0; mine <= 0; jid <= 0; np <= 0; rcnt <= 0; pdone <= 0; ofault <= 0; end
        else begin
            pdone <= 1'b0;
            if (dq_st) begin
                jkind <= dq_kind; jid <= dq_jid; mine <= (dq_kind == K_SE || dq_kind == K_SO);
                np <= (dq_kind == K_SO) ? 4'd5 : 4'd1 + (SM_H + 15) / 16; rcnt <= 0;
            end else begin
                rcnt <= rcnt + {11'd0, pc_n};
                if (pcyc && rcnt + {11'd0, pc_n} >= {12'd0, np}) pdone <= 1'b1;
            end
            if (misal) ofault <= 1'b1;
        end
    end

    // ------------------------------------------------------------------ rows / configuration / cos-sin out
    always @(posedge clk) begin
        if (pdone && jkind == K_SE) begin
            c_nv <= prow0[64 +: 7]; c_lt <= prow0[128 +: 3]; c_scale <= prow0[96 +: 32];
            c_sink <= prow1[64 * ti[2:0] +: 64];
        end
        cs_i <= 5'd31 - (cs_n[4:0] - 5'd1);
        cs_d <= {prow1[31:0], prow3[31:0]};
    end
    reg [13:0] obase;
    always @(posedge clk) if (pdone) obase <= prow0[13:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s_v <= 0; p_v <= 0; c_v <= 0; cs_v <= 0; cs_n <= 0; shr <= 0; end
        else begin
            s_v <= ocyc && jkind == K_SE;
            p_v <= ocyc && jkind == K_SO;
            c_v <= pdone && jkind == K_SE;
            cs_v <= shr;
            shr <= shn;
            if (pdone && jkind == K_SO) cs_n <= 6'd32;
            else if (cs_n != 0) cs_n <= cs_n - 6'd1;
        end
    end

    // ------------------------------------------------------------------ result events (e: SE, o: SO), staging
    reg  [15:0]      oc;
    reg              ev;
    reg  [7:0]       ev_n;
    reg  [RW*R-1:0]  ev_r;
    function automatic [RW-1:0] mkrow(input [13:0] a, input [511:0] d);
        mkrow = {a, 16'hFFFF, d};
    endfunction
    always @(*) begin : evb
        integer q;
        ev = 1'b0; ev_n = 0; ev_r = 0;
        if (ev_q && jkind == K_SE) begin
            ev = 1'b1; ev_n = R_SE;
            for (q = 0; q < R_SE; q = q + 1)
                ev_r[RW * q +: RW] = mkrow(obase + oc * RSM + ti * R_SE + q, ed_q[512 * q +: 512]);
        end
        if (ov_q) begin
            ev = 1'b1; ev_n = R_SO;
            ev_r[0 +: RW] = mkrow(obase + oc * (SMW / 32) + ti * R_SO, od_q);
        end
    end
    reg [RW-1:0] hb [0:R-1];
    reg [RW-1:0] tb [0:R-1];
    reg [7:0]    hn, tn;
    reg          ovf, ufs, dn;
    wire [7:0]   k = (hn < WS) ? hn : 8'd0 + WS;
    wire [7:0]   hrem = hn - k;
    always @(posedge clk) begin : stg                  // staged rows: no reset
        integer q;
        for (q = 0; q < R; q = q + 1) begin
            if (hrem == 0) begin
                if (tn != 0) hb[q] <= tb[q];
                else if (ev) hb[q] <= ev_r[RW * q +: RW];
            end else if (q + WS < R) hb[q] <= hb[q + WS];
            if ((hrem == 0 && tn != 0 && ev) || (hrem != 0 && ev && tn == 0)) tb[q] <= ev_r[RW * q +: RW];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hn <= 0; tn <= 0; ovf <= 0; ufs <= 0; oc <= 0; dn <= 0; end
        else begin
            if (f_q) ufs <= 1'b1;
            if (hrem == 0) begin
                if (tn != 0) begin hn <= tn; tn <= ev ? ev_n : 8'd0; end
                else hn <= ev ? ev_n : 8'd0;
            end else begin
                hn <= hrem;
                if (ev) begin if (tn != 0) ovf <= 1'b1; else tn <= ev_n; end
            end
            if (dq_st) oc <= 0; else if (ev) oc <= oc + 1;
            if (dq_st) dn <= 1'b0; else if (dv_q) dn <= 1'b1;
        end
    end
    always @(posedge clk) begin : outs
        integer s;
        for (s = 0; s < WS; s = s + 1) begin
            o_a[14 * s +: 14] <= (s < R) ? hb[s][RW - 1 -: 14] : 14'd0;
            o_m[16 * s +: 16] <= (s < R) ? hb[s][512 +: 16] : 16'd0;
            o_d[512 * s +: 512] <= (s < R) ? hb[s][0 +: 512] : 512'd0;
        end
    end
    always @(posedge clk or negedge rst_n) begin : outv
        integer s;
        if (!rst_n) begin o_v <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
        else begin
            for (s = 0; s < WS; s = s + 1) o_v[s] <= (s < k);
            o_fu <= ufs; o_fo <= ovf || ofault; o_alive <= 1'b1; o_den <= dn; o_rdy <= 1'b0; o_rjid <= jid;
        end
    end
endmodule

// a kept flop (its own module, listed in SYNTH_KEEP_MODULES): replicated enables survive synthesis as separate drivers
module ot_s81_su_sm_keep_ff (input wire clk, input wire rst_n, input wire d, output wire q);
    (* keep = "true" *) reg q_k;
    always @(posedge clk or negedge rst_n) if (!rst_n) q_k <= 1'b0; else q_k <= d;
    assign q = q_k;
endmodule

// ======================================================================================================== LANE
module ot_s81_su_sml #(
    parameter integer NVMAX = 40, LM = 5, LA = 4
) (
    input  wire        clk,
    input  wire        rst_in,
    input  wire        sk_en,                          // cfg: this lane also runs the head's sink exp (lane 0)
    input  wire        i_cv,                           // SE configuration
    input  wire [6:0]  i_nv,
    input  wire [31:0] i_scale,
    input  wire [31:0] i_sink,
    input  wire        i_sv,                           // score
    input  wire [31:0] i_s,
    input  wire        i_mv,                           // -mb of the head
    input  wire [31:0] i_nmb,
    output reg         o_mxv,                          // the lane's row max (final)
    output reg  [31:0] o_mx,
    output reg         o_ev,                           // e (o_es: the sink's exp, o_el: the row's last vector)
    output reg         o_es,
    output reg         o_el,
    output reg  [31:0] o_e
);
    localparam integer D_EXP = 7 * LM + 8 * LA + 4;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction

    // pin flops
    reg        cv, sv, mv, ske;
    reg [6:0]  nv_p; reg [31:0] scale_p, sink_p, s_p, nmb_p;
    always @(posedge clk) begin nv_p <= i_nv; scale_p <= i_scale; sink_p <= i_sink; s_p <= i_s; nmb_p <= i_nmb; ske <= sk_en; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 1'b0; sv <= 1'b0; mv <= 1'b0; end else begin cv <= i_cv; sv <= i_sv; mv <= i_mv; end
    reg [6:0]  nv; reg [31:0] scale, sink;
    always @(posedge clk) if (cv) begin nv <= nv_p; scale <= scale_p; sink <= sink_p; end

    // A. s = s_raw * scale -> buffer; running max
    wire [LM:0] smv;
    ot_hdc_vline #(.D(LM)) u_smv (.clk(clk), .rst_n(rst_n), .v(sv), .vd(smv));
    wire [31:0] s_m, s_m_raw;
    wire fm;
    wire [LM:0] s_inactive;
    ot_hdc_vline #(.D(LM)) u_s_inactive (.clk(clk), .rst_n(rst_n),
        .v(sv && s_p == 32'hff800000), .vd(s_inactive));
    // The finite-domain multiplier does not implement IEEE infinity. Carry the
    // compiler's mask around it and retain the sentinel in the score store/max.
    ot_dsrom_su_softmax_mul #(LM) u_m (clk, rst_n, sv,
        s_p == 32'hff800000 ? 32'd0 : s_p, scale, s_m_raw, fm);
    assign s_m = s_inactive[LM] ? 32'hff800000 : s_m_raw;
    reg [31:0] sbuf [0:NVMAX-1];
    reg [6:0]  wcnt;
    reg        s_mlast, a_done, fv, ff;
    reg [31:0] s_q, rmax;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wcnt <= 7'd0; a_done <= 1'b0; s_mlast <= 1'b0; fv <= 1'b0; ff <= 1'b0; end
        else begin
            a_done <= s_mlast;
            s_mlast <= smv[LM] && (wcnt + 7'd1 == nv);
            fv <= smv[LM]; ff <= (wcnt == 7'd0);
            if (smv[LM]) wcnt <= (wcnt + 7'd1 == nv) ? 7'd0 : wcnt + 7'd1;
        end
    end
    always @(posedge clk) if (smv[LM]) sbuf[wcnt] <= s_m;
    always @(posedge clk) s_q <= s_m;
    wire ge;
    ot_hdc_kge #(.W(32), .K(1)) u_ge (.a(okey(rmax)), .b(okey(s_q)), .ge(ge));
    always @(posedge clk) if (fv) rmax <= (ff || !ge) ? s_q : rmax;
    always @(posedge clk or negedge rst_n) if (!rst_n) o_mxv <= 1'b0; else o_mxv <= a_done;
    always @(posedge clk) if (a_done) o_mx <= rmax;

    // B. (sink one slot ahead on sk_en) re-read s, e = exp(s + (-mb))
    reg [31:0] mbn, s_rd;
    reg [6:0]  rcnt;
    reg        rd_on, rv, rlast, skg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rd_on <= 1'b0; rcnt <= 7'd0; rv <= 1'b0; rlast <= 1'b0; skg <= 1'b0; end
        else begin
            rv <= rd_on;
            rlast <= rd_on && (rcnt + 7'd1 == nv);
            skg <= mv && ske;
            if (mv) begin rd_on <= 1'b1; rcnt <= 7'd0; end
            else if (rd_on) begin
                rcnt <= rcnt + 7'd1;
                if (rcnt + 7'd1 == nv) rd_on <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (mv) mbn <= nmb_p;
        if (rd_on) s_rd <= sbuf[rcnt];
        else if (mv) s_rd <= sink;
    end
    wire av = rv || skg;
    wire [LA+D_EXP:0] bv, bl, bs;
    ot_hdc_vline #(.D(LA + D_EXP)) u_bv (.clk(clk), .rst_n(rst_n), .v(av), .vd(bv));
    ot_hdc_vline #(.D(LA + D_EXP)) u_bl (.clk(clk), .rst_n(rst_n), .v(rlast), .vd(bl));
    ot_hdc_vline #(.D(LA + D_EXP)) u_bs (.clk(clk), .rst_n(rst_n), .v(skg), .vd(bs));
    wire [31:0] bd, be;
    wire fa, fe;
    ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a (clk, rst_n, av, s_rd, mbn, bd, fa);
    ot_hdc_v41x_exp #(.LM(LM), .LA(LA)) u_e (.clk(clk), .rst_n(rst_n), .v(bv[LA]), .x(bd), .y(be), .vo(), .fault(fe));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_ev <= 1'b0; o_es <= 1'b0; o_el <= 1'b0; end
        else begin o_ev <= bv[LA + D_EXP]; o_es <= bs[LA + D_EXP]; o_el <= bl[LA + D_EXP]; end
    // -Inf is the compiler's inactive score-lane sentinel.  The polynomial exp
    // clamps its input to -87, so it MUST NOT supply the inactive lane's value.
    // Delay the mask on the same fixed add/exp timeline; no execution gating.
    wire [LA+D_EXP:0] inactive;
    ot_hdc_vline #(.D(LA + D_EXP)) u_inactive (.clk(clk), .rst_n(rst_n),
        .v(rv && s_rd == 32'hff800000), .vd(inactive));
    always @(posedge clk) o_e <= inactive[LA + D_EXP] ? 32'd0 : be;
endmodule

// ======================================================================================================== SUM
module ot_s81_su_smc #(
    parameter integer LPH = 16, LA = 4
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire               i_v,                     // an e vector of the head (not the sink)
    input  wire               i_l,                     // the row's last
    input  wire [LPH*32-1:0]  i_e,
    output reg                o_v,                     // the vector's sum (in-vector tree root)
    output reg                o_l,
    output reg  [31:0]        o_s
);
    localparam integer CPV = LPH / 8, LVI = $clog2(CPV);
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg               e_at, e_last;
    reg [LPH*32-1:0]  be;
    always @(posedge clk) be <= i_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin e_at <= 1'b0; e_last <= 1'b0; end
                                           else begin e_at <= i_v; e_last <= i_v && i_l; end
    // chunk chain: acc0 = x0 (-0 -> +0), acc_j = acc_{j-1} + x_j
    wire [7*LA:0] cv, cl;
    ot_hdc_vline #(.D(7 * LA)) u_cv (.clk(clk), .rst_n(rst_n), .v(e_at), .vd(cv));
    ot_hdc_vline #(.D(7 * LA)) u_cl (.clk(clk), .rst_n(rst_n), .v(e_last), .vd(cl));
    wire [CPV*32-1:0] csum_o;
    genvar k, j, l;
    generate for (k = 0; k < CPV; k = k + 1) begin : g_ch
        wire [32*8-1:0] acc;
        wire [31:0] x0 = be[32*(8*k) +: 32];
        assign acc[31:0] = (x0 == 32'h80000000) ? 32'd0 : x0;
        for (j = 1; j < 8; j = j + 1) begin : g_j
            wire [31:0] xj;
            wire fa;
            ot_hdc_delay #(.W(32), .D(LA * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n), .d(be[32*(8*k+j) +: 32]), .q(xj));
            ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a
                (clk, rst_n, cv[LA*(j-1)], acc[32*(j-1) +: 32], xj, acc[32*j +: 32], fa);
        end
        assign csum_o[32*k +: 32] = acc[32*7 +: 32];
    end endgenerate
    // in-vector tree over the chunk sums
    wire [LA*LVI:0] vtv, vtl;
    ot_hdc_vline #(.D(LA * LVI)) u_vtv (.clk(clk), .rst_n(rst_n), .v(cv[7*LA]), .vd(vtv));
    ot_hdc_vline #(.D(LA * LVI)) u_vtl (.clk(clk), .rst_n(rst_n), .v(cl[7*LA]), .vd(vtl));
    generate for (k = 0; k <= LVI; k = k + 1) begin : g_vt
        wire [(CPV >> k)*32-1:0] x;
        if (k == 0) begin : g_0
            assign x = csum_o;
        end else begin : g_n
            for (l = 0; l < (CPV >> k); l = l + 1) begin : g_l
                wire fa;
                ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a
                    (clk, rst_n, vtv[LA*(k-1)], g_vt[k-1].x[64*l +: 32], g_vt[k-1].x[64*l + 32 +: 32], x[32*l +: 32], fa);
            end
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) begin o_v <= 1'b0; o_l <= 1'b0; end
                                           else begin o_v <= vtv[LA*LVI]; o_l <= vtl[LA*LVI]; end
    always @(posedge clk) o_s <= g_vt[LVI].x;
endmodule

// ======================================================================================================== ROOT
module ot_s81_su_smr #(
    parameter integer LPH = 16, LA = 4, LTMAX = 6
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire               i_cv,                    // SE configuration: lt
    input  wire [2:0]         i_lt,
    input  wire               i_mxv,                   // the lanes' row maxima (lockstep)
    input  wire [LPH*32-1:0]  i_mx,
    input  wire               i_skv,                   // exp(sink - mb) from the sink lane
    input  wire [31:0]        i_sk,
    input  wire               i_vv,                    // the vector sums (from the sum master)
    input  wire               i_vl,
    input  wire [31:0]        i_vs,
    output reg                o_mv,                    // -mb to the lanes
    output reg  [31:0]        o_nmb,
    output reg                o_dv,                    // den to the divide engines
    output reg  [31:0]        o_den
);
    localparam integer LH = $clog2(LPH);
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    // pin flops
    reg              cv, mxv, skv, vv, vl;
    reg [2:0]        lt_p, lt;
    reg [LPH*32-1:0] mx;
    reg [31:0]       sk, vs, sk_hold;
    always @(posedge clk) begin lt_p <= i_lt; mx <= i_mx; sk <= i_sk; vs <= i_vs; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 0; mxv <= 0; skv <= 0; vv <= 0; vl <= 0; end
        else begin cv <= i_cv; mxv <= i_mxv; skv <= i_skv; vv <= i_vv; vl <= i_vv && i_vl; end
    always @(posedge clk) if (cv) lt <= lt_p;
    always @(posedge clk) if (skv) sk_hold <= sk;
    // max tree (order free: max on ordered keys)
    genvar k, l;
    generate for (k = 0; k <= LH; k = k + 1) begin : g_mt
        wire [(LPH >> k)*32-1:0] x;
        wire                     v;
        if (k == 0) begin : g_0
            assign x = mx;
            assign v = mxv;
        end else begin : g_n
            reg [(LPH >> k)*32-1:0] xr;
            reg                     vr;
            for (l = 0; l < (LPH >> k); l = l + 1) begin : g_l
                wire [31:0] xa = g_mt[k-1].x[64*l +: 32], xb = g_mt[k-1].x[64*l + 32 +: 32];
                wire ge;
                ot_hdc_kge #(.W(32), .K(1)) u_ge (.a(okey(xa)), .b(okey(xb)), .ge(ge));
                always @(posedge clk) xr[32*l +: 32] <= ge ? xa : xb;
            end
            always @(posedge clk or negedge rst_n) if (!rst_n) vr <= 1'b0; else vr <= g_mt[k-1].v;
            assign x = xr;
            assign v = vr;
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) o_mv <= 1'b0; else o_mv <= g_mt[LH].v;
    always @(posedge clk) if (g_mt[LH].v) o_nmb <= {~g_mt[LH].x[31], g_mt[LH].x[30:0]};
    // time levels of the row sum: level t holds a left operand until its right sibling arrives (add or pass)
    wire [(LTMAX+1)*32-1:0] tl_x;
    wire [LTMAX:0]          tl_v, tl_l;
    assign tl_x[31:0] = vs;
    assign tl_v[0] = vv;
    assign tl_l[0] = vl;
    generate for (k = 0; k < LTMAX; k = k + 1) begin : g_tl
        wire [31:0] xi = tl_x[k*32 +: 32];
        wire vi = tl_v[k], li = tl_l[k];
        reg  [31:0] held;
        reg         par;
        wire comb = vi && par;
        wire pass = vi && !par && li;
        wire [LA:0] ov, ol, op;
        ot_hdc_vline #(.D(LA)) u_ov (.clk(clk), .rst_n(rst_n), .v(comb || pass), .vd(ov));
        ot_hdc_vline #(.D(LA)) u_ol (.clk(clk), .rst_n(rst_n), .v((comb || pass) && li), .vd(ol));
        ot_hdc_vline #(.D(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(pass), .vd(op));
        wire [31:0] sum, pd;
        wire fa;
        ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a (clk, rst_n, comb, held, xi, sum, fa);
        ot_hdc_delay #(.W(32), .D(LA)) u_pd (.clk(clk), .rst_n(rst_n), .d(xi), .q(pd));
        reg  [31:0] xo;
        reg         vo_r, lo_r;
        always @(posedge clk) xo <= op[LA] ? pd : sum;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin vo_r <= 1'b0; lo_r <= 1'b0; end
            else begin vo_r <= ov[LA]; lo_r <= ol[LA]; end
        end
        assign tl_x[(k+1)*32 +: 32] = xo;
        assign tl_v[k+1] = vo_r;
        assign tl_l[k+1] = lo_r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) par <= 1'b0;
            else if (vi) par <= li ? 1'b0 : ~par;
        end
        always @(posedge clk) if (vi && !par) held <= xi;
    end endgenerate
    // tap at level lt: the item carrying the last flag; den = es + exp(sink - mb)
    reg  [31:0] rs_x;
    reg         rs_v;
    wire        tap = tl_v[lt] && tl_l[lt];
    always @(posedge clk or negedge rst_n) if (!rst_n) rs_v <= 1'b0; else rs_v <= tap;
    always @(posedge clk) if (tap) rs_x <= tl_x[lt*32 +: 32];
    wire [LA:0] dnv;
    ot_hdc_vline #(.D(LA)) u_dnv (.clk(clk), .rst_n(rst_n), .v(rs_v), .vd(dnv));
    wire [31:0] den_r;
    wire fd;
    ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_d (clk, rst_n, rs_v, rs_x, sk_hold, den_r, fd);
    always @(posedge clk or negedge rst_n) if (!rst_n) o_dv <= 1'b0; else o_dv <= dnv[LA];
    always @(posedge clk) if (dnv[LA]) o_den <= den_r;
endmodule

// ======================================================================================================== DIVIDE
module ot_s81_su_smd #(
    parameter integer LPH = 16, TAIL = 64, LM = 5, LA = 4, STALEDEN = 0
) (
    input  wire        clk,
    input  wire        rst_in,
    input  wire [2:0]  cfg_p,                          // the pair: lanes 2 p, 2 p + 1 of the head
    input  wire        i_pv,                           // a PV vector's two lanes
    input  wire [63:0] i_pa,
    input  wire        i_dv,                           // den
    input  wire [31:0] i_den,
    input  wire        i_csv,                          // cos / sin pair i_csi
    input  wire [4:0]  i_csi,
    input  wire [63:0] i_csd,
    output reg         o_ov,
    output reg  [31:0] o_o,                            // {lane 2 p + 1, lane 2 p} BF16
    output reg         o_f                             // sticky: a tail vector before its cos / sin
);
    localparam integer NPV = 512 / LPH;
    localparam integer D_DIV = 33;
    localparam integer DR = D_DIV + 1 + LM + LA + 1;
    localparam integer UT = (512 - TAIL) / LPH;        // first tail vector (28)
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg        piv, dvq, csv;
    reg [63:0] pa, csd;
    reg [31:0] dnq;
    reg [4:0]  csi;
    reg [2:0]  p;
    always @(posedge clk) begin pa <= i_pa; dnq <= i_den; csd <= i_csd; csi <= i_csi; p <= cfg_p; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin piv <= 1'b0; dvq <= 1'b0; csv <= 1'b0; end
                                           else begin piv <= i_pv; dvq <= i_dv; csv <= i_csv; end
    // the pair's cos / sin for the TAIL / LPH tail vectors (slot = vector - UT)
    reg [31:0] ccos [0:3];
    reg [31:0] csin [0:3];
    reg [2:0]  csn;                                    // pairs of the current set received
    always @(posedge clk) if (csv && csi[2:0] == p) begin ccos[csi[4:3]] <= csd[63:32]; csin[csi[4:3]] <= csd[31:0]; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) csn <= 3'd0;
        else if (csv && csi == 5'd0) csn <= (p == 3'd0) ? 3'd1 : 3'd0;
        else if (csv && csi[2:0] == p) csn <= csn + 3'd1;
    // den (STALEDEN: the bench's negative control loads it on the first den after reset only)
    reg [31:0] denl;
    reg        den_seen;
    always @(posedge clk or negedge rst_n) if (!rst_n) den_seen <= 1'b0; else if (dvq) den_seen <= 1'b1;
    always @(posedge clk) if (dvq && !(STALEDEN != 0 && den_seen)) denl <= dnq;
    // pv / den -> BF16
    reg [6:0] ucnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ucnt <= 7'd0;
        else if (piv) ucnt <= (ucnt + 7'd1 == NPV) ? 7'd0 : ucnt + 7'd1;
    end
    wire [DR:0] dv;
    ot_hdc_vline #(.D(DR)) u_dv (.clk(clk), .rst_n(rst_n), .v(piv), .vd(dv));
    wire [6:0] u_q, u_r, u_rd;
    ot_hdc_delay #(.W(7), .D(D_DIV)) u_ul (.clk(clk), .rst_n(rst_n), .d(ucnt), .q(u_q));
    ot_hdc_delay #(.W(7), .D(1)) u_ul1 (.clk(clk), .rst_n(rst_n), .d(u_q), .q(u_r));
    ot_hdc_delay #(.W(7), .D(LM + LA)) u_urd (.clk(clk), .rst_n(rst_n), .d(u_r), .q(u_rd));
    wire [63:0] qd;
    reg  [31:0] o0;
    genvar l;
    generate for (l = 0; l < 2; l = l + 1) begin : g_dv
        wire fd;
        ot_dsrom_su_fdiv_f12 #(.NR(0)) u_d (.clk(clk), .rst_n(rst_n), .v(piv), .a(pa[32*l +: 32]), .b(denl),
                                            .y(qd[32*l +: 32]), .vo(), .fault(fd));
        wire [15:0] qb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(qd[32*l + 16 +: 16]),
                                           .inc(qd[32*l + 15] & (qd[32*l + 16] | (|qd[32*l +: 15]))), .y(qb));
        always @(posedge clk) o0[16*l +: 16] <= qb;
    end endgenerate
    // inverse RoPE of the pair on the tail: even lane a*c + b*s, odd lane b*c + -(a*s)
    wire [31:0] o0_d;
    ot_hdc_delay #(.W(32), .D(LM + LA)) u_o0d (.clk(clk), .rst_n(rst_n), .d(o0), .q(o0_d));
    reg  [31:0] c, s;
    always @(posedge clk) begin c <= ccos[u_q[1:0]]; s <= csin[u_q[1:0]]; end
    wire tail = (u_rd >= UT);
    reg  [31:0] ob;
    wire [31:0] a = {o0[15:0], 16'd0}, b = {o0[31:16], 16'd0};
    generate for (l = 0; l < 2; l = l + 1) begin : g_rp
        wire [31:0] m1, m2, ad;
        wire f1, f2, f3;
        ot_dsrom_su_softmax_mul #(LM) u_m1 (clk, rst_n, dv[D_DIV + 1], (l == 0) ? a : b, c, m1, f1);
        ot_dsrom_su_softmax_mul #(LM) u_m2 (clk, rst_n, dv[D_DIV + 1], (l == 0) ? b : a, s, m2, f2);
        wire [31:0] m2s = (l == 0) ? m2 : {~m2[31], m2[30:0]};
        ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a (clk, rst_n, dv[D_DIV + 1 + LM], m1, m2s, ad, f3);
        wire [15:0] adb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(ad[31:16]), .inc(ad[15] & (ad[16] | (|ad[14:0]))), .y(adb));
        always @(posedge clk) ob[16*l +: 16] <= tail ? adb : o0_d[16*l +: 16];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_ov <= 1'b0; o_f <= 1'b0; end
        else begin
            o_ov <= dv[DR];
            if (dv[D_DIV] && u_q >= UT && csn < 3'd4) o_f <= 1'b1;
        end
    end
    always @(posedge clk) o_o <= ob;
endmodule

`timescale 1ns/1ps
// =====================================================================================================================
// KVE-2/SEQ 2026-10-17 (coordinator decision 0cx (3) / 0db): the attention programme qkd_native_attention_programme is the
// SOLE owner of the static D2D end's attention RX port.  qkd_seq_static_p is the successor of qkd_seq_static (kept as
// history in qkd_seq_static.sv): it no longer sees att_rx_v/kind/beat nor reads the CMD record or the Q beats off the KVN
// receiver's data wires.  It takes them from the programme's existing, registered decode outputs:
//   request_valid / request_position[17:0]   (CMD kind 1, one edge after the RX event; position = native authority position)
//   q_valid / q_beat[4:0] / q_data[511:0]    (Q kind 2, two edges after the RX event; already checked by the record codec
//                                             against kind / epoch / layer / beat and the compiled RX slot)
// No new programme port is needed.  The KVN receiver word (kvn_word_*) is NOT attention RX and is unchanged.
// Static schedule: no credit, no ready.  Off-slot arrivals are sticky FAULTS, never waited for (as qkd_seq_static).
//
// Cluster (wires-only parent qkd_seq_static_p over hardened leaves):
//   qkd_seq_core_static_p x 1  control leaf (successor of qkd_seq_core_static)
//   qkd_seq_xd_sel_r      x 4  128-b store-data select (one per store slice), KV-NATIVE 10-17 successor of qkd_seq_xd_sel
//                              (history): pin flops on q_v (8 select copies) / q_d / k_d, then x_d <= q_v ? q_d : kvn_d;
//                              +1 edge on Q and KVN store data, and the core's x_v / x_cls pass through it (+1) to stay aligned
//   qkd_seq_xs_tp8        x 4  UNCHANGED store slices (closed view)
//   qkd_seq_fan           x 4  UNCHANGED quadrant pin registers (closed views)
// Timeline, E = the edge of the CMD RX event at the D2D end (programme rx_event and the old att_rx_v are the same edge):
//   programme request_valid E+1 -> core pin E+2 = a 0 at E+3; Q beat n: programme q_* E+3+n, xd_sel out / store push E+4+n
//   (old: E+2+n, +2: programme Q register + select register).  KVN word: kvn_word_* E+35..38 (unchanged), xd_sel out /
//   store push E+36..39 (old E+35..38, +1).  KP0 = 36 (old 37) keeps every pop / aq start / Q beat / posted row / hs at
//   the SAME absolute edge as qkd_seq_static: aq and kvn faces are cycle-identical.  KV-NATIVE 10-17 (qkd_seq_xd_sel_r): store
//   push +1 more (Q E+5+n, KVN E+37..40); every pop / face edge is unchanged (absorbed: first K pop E+39, first Q pop later).  The stream descriptor (kc face) is
//   launched by the CMD event and leaves +1 edge later than qkd_seq_static (priced in the KVE-2-SEQ lane record).
// MUT (bench only): 1 Q beats 0/1 swapped; 2 posted rows' t = T; 3 aq start one edge late; 4 KVN push one edge early;
//   5 (xd_sel) the select ignores q_v (Q data replaced by the KVN wires).
// =====================================================================================================================
module qkd_seq_core_static_p #(
    parameter integer KVN_A0 = 32,
    parameter integer KP0    = 36,
    parameter integer LP_WIN = 64,
    parameter integer KWC    = 4,
    parameter integer MUT    = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          prg_req_v,               // attention programme request_valid (CMD decoded)
    input  wire [17:0]   prg_req_pos,             // attention programme request_position
    input  wire          prg_q_v,                 // attention programme q_valid
    input  wire [4:0]    prg_q_beat,              // attention programme q_beat
    input  wire          kvn_word_valid,
    input  wire [10:0]   kvn_word_tag,
    input  wire          lp_run,
    input  wire [5:0]    lp_layer,
    input  wire [13:0]   lp_ctx_t,
    input  wire [87:0]   svc_h,
    output reg           x_v,
    output reg  [2:0]    x_cls,
    output reg           s_qpop,
    output reg           s_kpop,
    output reg  [2:0]    s_kidx,
    output reg           s_kwgo,
    output reg  [1:0]    s_kwn,
    output reg  [27:0]   f_aqm_w, f_aqm_e,
    output reg  [22:0]   f_kwm_w, f_kwm_e,
    output reg  [32:0]   f_kc_w, f_kc_e,
    input  wire [1:0]    f_cr_w, f_cr_e,
    input  wire [1:0]    f_af_w, f_af_e,
    input  wire [1:0]    f_mf_w, f_mf_e,
    output reg           hs,
    input  wire [7:0]    ar_h,
    input  wire          hf,
    output wire [92:0]   tk,
    output wire [9:0]    kst
);
    wire [2:0] rrv;
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rrv));
    wire rr = rrv[0], rq = rrv[1], rd = rrv[2];
    // ---- pin capture (every functional input lands in a pin flop) ----
    reg          rv, qv, kvv, lpr, ov, og, hfq;
    reg  [3:0]   crq, afq, mfq;
    reg  [4:0]   qb;
    reg  [17:0]  rpos;
    reg  [10:0]  ktg;
    reg  [5:0]   lpl, ob;
    reg  [13:0]  lpt;
    reg  [87:0]  sv;
    always @(posedge ck) begin
        rpos <= prg_req_pos; qb <= prg_q_beat; ktg <= kvn_word_tag; lpl <= lp_layer; lpt <= lp_ctx_t;
        ob <= ar_h[5:0]; og <= ar_h[6]; sv <= svc_h;
    end
    always @(posedge ck or negedge rr)
        if (!rr) begin rv <= 0; qv <= 0; kvv <= 0; lpr <= 0; ov <= 0; hfq <= 0; crq <= 0; afq <= 0; mfq <= 0; end
        else begin
            rv <= prg_req_v; qv <= prg_q_v; kvv <= kvn_word_valid; lpr <= lp_run; ov <= ar_h[7]; hfq <= hf;
            crq <= {f_cr_e, f_cr_w}; afq <= {f_af_e, f_af_w}; mfq <= {f_mf_e, f_mf_w};
        end
    // ---- the layer's fixed timeline (a = 0 two edges after the programme's request) ----
    localparam integer A_END = KP0 + 41;
    reg          act;
    reg  [7:0]   a;
    reg  [5:0]   layer, lp_hold_l;
    reg  [13:0]  a_T, lp_hold_t;
    reg  [6:0]   lp_age;
    reg          lp_seen;
    wire         cmd    = rv;
    wire         q_slot = act && a < 8'd32;                       // store push of Q beat a (data from xd_sel)
    wire         q_exp  = act && a >= 8'd1 && a <= 8'd32;         // programme q_valid (registered) expected
    wire         k_exp  = act && a >= 8'(KVN_A0 - ((MUT == 4) ? 1 : 0)) && a < 8'(KVN_A0 + 4 - ((MUT == 4) ? 1 : 0));
    wire [1:0]   kp_j   = 2'(a - 8'(KP0 - 1));
    wire         k_pop  = act && a >= 8'(KP0 - 1) && a < 8'(KP0 + 3);
    wire [7:0]   a_st   = 8'(KP0 + 3 + ((MUT == 3) ? 1 : 0));
    wire         a_sta  = act && a == a_st;
    wire [5:0]   qn     = 6'(a - (a_st + 8'd1));
    wire         q_pop  = act && a > a_st && a <= a_st + 8'd32;
    wire         kw_go  = act && (a == a_st + 8'd1 || a == a_st + 8'd3);
    wire         kw_row = (a == a_st + 8'd3);
    function [2:0] ktag(input [1:0] j);
        ktag = {j[1], 1'b0, j[0]};
    endfunction
    reg  [1:0]   kn_arr;
    reg          xk;
    reg          a_start, a_q_valid, kvw_v;
    reg  [5:0]   a_q_beat;
    reg  [1:0]   kvw_vg;
    reg  [13:0]  kvw_t;
    reg  [5:0]   kvw_layer;
    reg  [6:0]   r_n, q_seen;
    reg  [7:0]   kwc;
    reg  [2:0]   jc [0:3];
    wire [3:0]   jnz = {jc[3] != 0, jc[2] != 0, jc[1] != 0, jc[0] != 0};
    wire         jn  = &jnz;
    reg          kwq;
    reg          f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_cr, f_join, f_pend, f_row, f_ovl;
    wire         kd_fault, kd_v;
    wire [31:0]  kd_d;
    ot_qkvd_kv_desc #(.NL(36)) u_kd (.clk(ck), .rst_n(rd), .p_mid_init(20'd0), .p_tok_init(20'd0),
        .attn_v(cmd && !act), .attn_layer(lp_hold_l), .attn_T(lp_hold_t),
        .done_v(ov && r_n == 7'd31), .k_v(kd_v), .k_d(kd_d), .k_ready(1'b1), .fault(kd_fault));
    integer i;
    always @(posedge ck or negedge rr) begin
        if (!rr) begin
            act <= 0; a <= 0; lp_seen <= 0; lp_age <= 0;
            x_v <= 0; xk <= 0; kn_arr <= 0; s_qpop <= 0; s_kpop <= 0; s_kwgo <= 0;
            a_start <= 0; a_q_valid <= 0; kvw_v <= 0; r_n <= 0; q_seen <= 0;
            kwc <= 8'(KWC); kwq <= 0; for (i = 0; i < 4; i = i + 1) jc[i] <= 0;
            {f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_cr, f_join, f_pend, f_row, f_ovl} <= 0;
        end else begin
            if (lpr) begin lp_seen <= 1; lp_age <= 0; lp_hold_l <= lpl; lp_hold_t <= lpt; end
            else if (lp_seen && lp_age != 7'h7f) lp_age <= lp_age + 1'b1;
            if (cmd) begin
                if (act) f_ovl <= 1;
                if (!lp_seen || lp_age > 7'(LP_WIN)) f_lp <= 1;
                // the programme's authority position must be the layer programme's T - 1
                if (rpos != 18'(lp_hold_t - 14'd1)) f_pos <= 1;
                act <= 1; a <= 0; layer <= lp_hold_l; a_T <= lp_hold_t; lp_seen <= 0; q_seen <= 0; kn_arr <= 0;
            end else if (act) begin
                a <= a + 1'b1;
                if (a == 8'(A_END)) act <= 0;
            end
            // store pushes at compiled edges: Q beats from xd_sel (programme q_data), KVN words from xd_sel (KVN wires)
            xk <= k_exp;
            x_v <= q_slot || k_exp;
            x_cls <= q_slot ? 3'b001 : 3'b010;
            if (qv != q_exp) f_q <= 1;                               // programme Q beat off its compiled edge
            if (qv) begin
                if (qb != 5'(q_seen)) f_q <= 1;
                q_seen <= q_seen + 1'b1;
            end
            if (kvv != xk) f_arr <= 1;                               // KVN word not on its compiled edge
            if (kvv) begin
                if (ktg[10:8] != 3'b010 || ktg[2:0] != ktag(kn_arr)) f_tag <= 1;
                kn_arr <= kn_arr + 1'b1;
            end
            s_kpop <= k_pop; s_kidx <= ktag(kp_j);
            s_qpop <= q_pop; a_q_valid <= q_pop;
            if (q_pop) a_q_beat <= (MUT == 1 && qn < 6'd2) ? (qn ^ 6'd1) : qn;
            if (act && a == a_st + 8'd1 && q_seen != 7'd32) f_q <= 1;
            a_start <= a_sta;
            kvw_v <= kw_go;
            if (kw_go) begin kvw_vg <= {kw_row, 1'b0}; kvw_t <= (MUT == 2) ? a_T : a_T - 14'd1; kvw_layer <= layer; end
            s_kwgo <= kw_go; s_kwn <= {kw_row, 1'b0};
            if (kw_go && kwc == 0) f_cr <= 1;
            kwc <= kwc - (kw_go ? 8'd1 : 8'd0) + (kwq ? 8'd1 : 8'd0);
            kwq <= jn;
            if (kwq && kwc == 8'(KWC)) f_cr <= 1;
            for (i = 0; i < 4; i = i + 1) begin
                jc[i] <= jc[i] + (crq[i] ? 3'd1 : 3'd0) - ((jn && jc[i] != 0) ? 3'd1 : 3'd0);
                if (crq[i] && jc[i] == 3'd7) f_join <= 1;
            end
            if (a_start) r_n <= 0;
            else if (ov) begin
                r_n <= r_n + 1'b1;
                if (og || ob != r_n[5:0]) f_res <= 1;
            end
            f_pend <= f_pend | hfq | (|afq);
            f_row <= f_row | (|mfq);
        end
    end
    reg [27:0] aq1;
    reg [22:0] kw1;
    reg [2:0]  hsd;
    always @(posedge ck) begin
        aq1[26:7] <= {a_T, layer}; aq1[5:0] <= a_q_beat;
        f_aqm_w[26:7] <= aq1[26:7]; f_aqm_w[5:0] <= aq1[5:0]; f_aqm_e[26:7] <= aq1[26:7]; f_aqm_e[5:0] <= aq1[5:0];
        kw1[21:0] <= {kvw_vg, kvw_t, kvw_layer};
        f_kwm_w[21:0] <= kw1[21:0]; f_kwm_e[21:0] <= kw1[21:0];
        f_kc_w[31:0] <= kd_d; f_kc_e[31:0] <= kd_d;
    end
    always @(posedge ck or negedge rq)
        if (!rq) begin
            aq1[27] <= 0; aq1[6] <= 0; f_aqm_w[27] <= 0; f_aqm_w[6] <= 0; f_aqm_e[27] <= 0; f_aqm_e[6] <= 0;
            kw1[22] <= 0; f_kwm_w[22] <= 0; f_kwm_e[22] <= 0; f_kc_w[32] <= 0; f_kc_e[32] <= 0; hsd <= 0; hs <= 0;
        end else begin
            aq1[27] <= a_start; aq1[6] <= a_q_valid;
            f_aqm_w[27] <= aq1[27]; f_aqm_w[6] <= aq1[6]; f_aqm_e[27] <= aq1[27]; f_aqm_e[6] <= aq1[6];
            kw1[22] <= kvw_v; f_kwm_w[22] <= kw1[22]; f_kwm_e[22] <= kw1[22];
            f_kc_w[32] <= kd_v; f_kc_e[32] <= kd_v;
            hsd <= {hsd[1:0], a_start}; hs <= hsd[2];
        end
    reg        d_done, drn, fault;
    reg [1:0]  d_gen;
    reg [17:0] d_tok;
    reg [31:0] d_val, d_cyc;
    reg [8:0]  cause;
    always @(posedge ck) if (sv[2]) begin d_gen <= sv[5:4]; d_tok <= sv[23:6]; d_val <= sv[55:24]; d_cyc <= sv[87:56]; end
    always @(posedge ck or negedge rq)
        if (!rq) begin d_done <= 0; drn <= 0; fault <= 0; cause <= 0; end
        else begin
            if (sv[2]) d_done <= sv[3];
            drn <= !act && kwc == 8'(KWC) && !kwq && (jc[0] == 0) && (jc[1] == 0) && (jc[2] == 0) && (jc[3] == 0);
            cause <= {f_arr | f_tag, f_lp, f_pos, f_join | f_cr, kd_fault, f_pend | f_row, f_q | f_ovl, f_res, 1'b0};
            fault <= |{f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_cr, f_join, f_pend, f_row, f_ovl, kd_fault};
        end
    assign tk  = {d_done, d_gen, drn, fault, {3'd0, fault}, sv[0], sv[1], d_tok, d_val, d_cyc};
    assign kst = {fault, cause};
endmodule

// store-data select, one per store slice (hardened once, x4): the programme's Q beat data or the KVN receiver word,
// selected by the programme's own q_valid (data-aligned, no control from the core), into one output register.
module qkd_seq_xd_sel #(parameter integer W = 128, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          q_v,
    input  wire [W-1:0]  q_d,
    input  wire [W-1:0]  k_d,
    output reg  [W-1:0]  x_d
);
    always @(posedge ck) x_d <= (q_v && MUT != 5) ? q_d : k_d;
endmodule

// KV-NATIVE 10-17 successor of qkd_seq_xd_sel (routed native audit, claude/native-batch-1017 029f539c5: q_v capture 230.8 >
// 190 ps -- the bare q_v pin fanned out to all 128 mux selects ahead of the x_d flops).  Every input is now a pin flop:
//   stage 1 (at the N pins): NS replicated q_v select copies (each a kept flop of the q_v pin, one per W/NS-bit group),
//                            q_d / k_d pin flops, x_vi / x_ci pin flops (the core's store-push control, passed through);
//   stage 2 (at the S pins):  x_d <= qv_p[g] ? qd_p : kd_p per group; x_vo / x_co = the stage-1 control flops.
// Data latency 2 edges (was 1); the store-push control (x_v / x_cls from qkd_seq_core_static_p) now goes through this tile
// with +1 edge so it stays aligned with x_d at every qkd_seq_xs_tp8.  No reset (pure pipeline; the core's x_v is reset).
// MUT (bench only): 5 the select ignores q_v (as qkd_seq_xd_sel); 6 the last select copy ignores q_v (one group of W/NS bits).
module qkd_seq_xd_sel_r #(parameter integer W = 128, parameter integer NS = 8, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          q_v,
    input  wire [W-1:0]  q_d,
    input  wire [W-1:0]  k_d,
    input  wire          x_vi,
    input  wire [2:0]    x_ci,
    output reg  [W-1:0]  x_d,
    output reg           x_vo,
    output reg  [2:0]    x_co
);
    localparam integer G = W / NS;
    (* keep = "true", dont_touch = "true" *) reg [NS-1:0] qv_p;
    reg [W-1:0] qd_p, kd_p;
    always @(posedge ck) begin
        qv_p <= {NS{q_v}}; qd_p <= q_d; kd_p <= k_d;
        x_vo <= x_vi; x_co <= x_ci;
    end
    genvar g;
    generate for (g = 0; g < NS; g = g + 1) begin : g_sel
        wire sel = qv_p[g] && MUT != 5 && !(MUT == 6 && g == NS - 1);
        always @(posedge ck) x_d[G*g +: G] <= sel ? qd_p[G*g +: G] : kd_p[G*g +: G];
    end endgenerate
endmodule

// wires-only parent on the contract slot `seq` (successor of qkd_seq_static): no cell, no flop of its own
module qkd_seq_static_p #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          prg_req_v,
    input  wire [17:0]   prg_req_pos,
    input  wire          prg_q_v,
    input  wire [4:0]    prg_q_beat,
    input  wire [511:0]  prg_q_data,
    input  wire          kvn_word_valid,
    input  wire [10:0]   kvn_word_tag,
    input  wire [511:0]  kvn_word_data,
    input  wire          lp_run,
    input  wire [5:0]    lp_layer,
    input  wire [13:0]   lp_ctx_t,
    input  wire [173:0]  svc,
    output wire [539:0]  aq_WS, aq_WN, aq_ES, aq_EN,
    output wire [1046:0] kvn_WS_d, kvn_WN_d, kvn_ES_d, kvn_EN_d,
    input  wire          kvn_WS_cr, kvn_WN_cr, kvn_ES_cr, kvn_EN_cr,
    output wire [32:0]   kc_WS, kc_WN, kc_ES, kc_EN,
    input  wire          af_WS, af_WN, af_ES, af_EN,
    input  wire          mf_WS, mf_WN, mf_ES, mf_EN,
    input  wire [519:0]  ar,
    input  wire          hf,
    output wire          hs,
    output wire [92:0]   tk,
    output wire [9:0]    kst
);
    wire          x_v, s_qpop, s_kpop, s_kwgo;
    wire [2:0]    x_cls, s_kidx;
    wire [1:0]    s_kwn;
    wire [27:0]   f_aqm [0:1];
    wire [22:0]   f_kwm [0:1];
    wire [32:0]   f_kc  [0:1];
    wire [3:0]    f_cr, f_af, f_mf;
    wire [255:0]  sq  [0:3];
    wire [511:0]  skw [0:3];
    wire [127:0]  xd  [0:3];
    wire [3:0]    xv;                              // store-push control per slice, +1 edge through qkd_seq_xd_sel_r
    wire [2:0]    xc  [0:3];
    // hard children carry no #() under the hard define (closed views are the MUT 0 build)
`ifdef OT_QKD_SEQ_STATIC_P_HARD
    qkd_seq_core_static_p u_core (
`else
    qkd_seq_core_static_p #(.MUT(MUT)) u_core (
`endif
       .ck(ck), .rst_n(rst_n), .prg_req_v(prg_req_v), .prg_req_pos(prg_req_pos),
        .prg_q_v(prg_q_v), .prg_q_beat(prg_q_beat), .kvn_word_valid(kvn_word_valid), .kvn_word_tag(kvn_word_tag),
        .lp_run(lp_run), .lp_layer(lp_layer), .lp_ctx_t(lp_ctx_t),
        .svc_h({svc[173:90], svc[25], svc[24], svc[20], svc[19]}),
        .x_v(x_v), .x_cls(x_cls), .s_qpop(s_qpop), .s_kpop(s_kpop), .s_kidx(s_kidx), .s_kwgo(s_kwgo), .s_kwn(s_kwn),
        .f_aqm_w(f_aqm[0]), .f_aqm_e(f_aqm[1]), .f_kwm_w(f_kwm[0]), .f_kwm_e(f_kwm[1]), .f_kc_w(f_kc[0]), .f_kc_e(f_kc[1]),
        .f_cr_w(f_cr[1:0]), .f_cr_e(f_cr[3:2]), .f_af_w(f_af[1:0]), .f_af_e(f_af[3:2]), .f_mf_w(f_mf[1:0]), .f_mf_e(f_mf[3:2]),
        .hs(hs), .ar_h(ar[519:512]), .hf(hf), .tk(tk), .kst(kst));
    genvar s, k;
    generate for (s = 0; s < 4; s = s + 1) begin : g_xs
`ifdef OT_QKD_SEQ_STATIC_P_HARD
        qkd_seq_xd_sel_r u_xd (.ck(ck), .q_v(prg_q_v), .q_d(prg_q_data[128*s +: 128]),
            .k_d(kvn_word_data[128*s +: 128]), .x_vi(x_v), .x_ci(x_cls), .x_d(xd[s]), .x_vo(xv[s]), .x_co(xc[s]));
`else
        qkd_seq_xd_sel_r #(.MUT(MUT)) u_xd (.ck(ck), .q_v(prg_q_v), .q_d(prg_q_data[128*s +: 128]),
            .k_d(kvn_word_data[128*s +: 128]), .x_vi(x_v), .x_ci(x_cls), .x_d(xd[s]), .x_vo(xv[s]), .x_co(xc[s]));
`endif
        qkd_seq_xs_tp8 u_xs (.ck(ck), .rst_n(rst_n), .x_v(xv[s]), .x_cls(xc[s]), .x_d(xd[s]),
            .qpop(s_qpop), .kpop(s_kpop), .kidx(s_kidx), .kwgo(s_kwgo), .kwn(s_kwn), .q_w(sq[s][127:0]), .q_e(sq[s][255:128]),
            .kw_w(skw[s][255:0]), .kw_e(skw[s][511:256]));
    end endgenerate
    wire [511:0]  fq  [0:1];
    wire [1023:0] fkw [0:1];
    generate for (k = 0; k < 2; k = k + 1) begin : g_cp
        for (s = 0; s < 4; s = s + 1) begin : g_s
            assign fq[k][128*s +: 128]        = sq[s][128*k +: 128];
            assign fkw[k][128*s +: 128]       = skw[s][256*k +: 128];
            assign fkw[k][512 + 128*s +: 128] = skw[s][256*k + 128 +: 128];
        end
    end endgenerate
    wire [539:0]  aq  [0:3];
    wire [1046:0] kvn [0:3];
    wire [32:0]   kc  [0:3];
    wire [3:0]    cr = {kvn_EN_cr, kvn_ES_cr, kvn_WN_cr, kvn_WS_cr};
    wire [3:0]    af = {af_EN, af_ES, af_WN, af_WS};
    wire [3:0]    mf = {mf_EN, mf_ES, mf_WN, mf_WS};
    generate for (k = 0; k < 4; k = k + 1) begin : g_fan
        qkd_seq_fan u_fan (.ck(ck), .rst_n(rst_n), .aqm(f_aqm[k/2]), .q(fq[k/2]), .kwm(f_kwm[k/2]),
            .kw(fkw[k/2]), .kc_i(f_kc[k/2]), .aq(aq[k]), .kvn(kvn[k]), .kc(kc[k]), .kvn_cr(cr[k]), .af(af[k]),
            .mf(mf[k]), .cr_o(f_cr[k]), .af_o(f_af[k]), .mf_o(f_mf[k]));
    end endgenerate
    assign aq_WS = aq[0];   assign aq_WN = aq[1];   assign aq_ES = aq[2];   assign aq_EN = aq[3];
    assign kvn_WS_d = kvn[0]; assign kvn_WN_d = kvn[1]; assign kvn_ES_d = kvn[2]; assign kvn_EN_d = kvn[3];
    assign kc_WS = kc[0];   assign kc_WN = kc[1];   assign kc_ES = kc[2];   assign kc_EN = kc[3];
endmodule

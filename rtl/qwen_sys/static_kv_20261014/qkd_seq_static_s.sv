`timescale 1ns/1ps
// =====================================================================================================================
// RTL-BUILD-KV/SEQ 2026-10-18 (P3 of lanes/RTL-BUILD-KV.md): qkd_seq_static_s = qkd_seq_static_p WITHOUT the legacy
// landing faces.  On the static KV die the landing strips are gone: the sequencer's KV-row face kvn_<q>_d[1046:0] has no
// consumer (new K/V rows are written by the D2D end's KVN receiver -> writer programme path), and its inputs
// kvn_<q>_cr (landing row credit) and mf_<q> (merge fault) have no producer.  On-die credits are banned (static
// schedule), so the faces AND the logic behind them are deleted, not tied:
//   core   : posted-row timeline (s_kwgo / s_kwn / kvw_* / f_kwm), KVN pops (s_kpop / s_kidx), the row-credit account
//            (kwc / kwq / jc[4] / f_cr / f_join) and the merge-fault latch (f_row) are gone; x_cls is gone (Q only).
//   store  : qkd_seq_xs_s holds only the Q FIFO (40 x 128) and its two registered copies; the KVN FIFO, the eight KVN
//            word registers and the 2 x 256-b row copies are gone.
//   fan    : qkd_seq_fan_s carries aq / kc out and af back only (no kvn / kw / kwm / kvn_cr / mf / cr_o / mf_o).
//   xd_sel : gone.  With the KVN words no longer stored, the store's data input is the programme's q_data directly (the
//            store's own input register is the pin flop); the core issues the Q store push one edge earlier
//            (q_slot = cmd || act && a < 31) so the push stays data-aligned.
//   kvn_word_data[511:0] is no longer an input.  kvn_word_valid / kvn_word_tag stay: the static D2D end's KVN receiver
//   timeline is still CHECKED against its compiled slot (f_arr / f_tag sticky faults, never a gate).
// What kvn_cr / mf did in qkd_seq_static(_p) (read of the RTL, 10-18):
//   kvn_<q>_cr -> fan c1 -> cr_o -> core crq -> jc[q] -> jn -> kwq -> kwc.  kwc is read ONLY by the fault check f_cr
//   (kw_go && kwc == 0, or a return with kwc full) and by tk's drained bit drn.  No pop, push, start, Q beat, row, hs or
//   descriptor depends on it: credits never stalled issue.  LIVE BUG on the die (cr has no producer): kwc starts at
//   KWC = 4 and loses 2 a layer, so the first posted row of layer 2 (the third layer) sees kwc == 0 -> f_cr sticky ->
//   tk.fault / kst[9] / cause[5] from layer 2 of the first token on, and drn stays 0 after layer 0 (kwc also wraps).
//   mf_<q> -> fan m1 -> mf_o -> core mfq -> f_row -> fault / cause[3] only (harmless when tied 0, X when floating).
// Output faces against qkd_seq_static_p (bench tools/qwen_static_kv/seq_static_s_bench.sh, lockstep every edge):
//   aq_<q>, kc_<q>, hs, tk, kst bit- and edge-identical when the reference's kvn_<q>_cr is an always-available credit (a
//   landing that returns every row) and mf = 0.  tk.drained = !act (was !act && credits home; equal under that
//   reference).  kst cause[5] (f_join | f_cr) is a reserved 0 bit of the host status word (layout kept for the host).
// K-17 ties kept: ot_qkvd_kv_desc p_mid_init / p_tok_init = 0 are FUNCTIONAL static-schedule CSRs (the DESC pre-hint
//   spacing seed), not mode straps; 0 = "unknown" is a legal value: the issuer measures p_mid after layer 1 and p_tok
//   after the first token, so only the first layer(s) after reset take the exact hint-0 path (DESC + GO at the ATTN).
//   kc words are exact either way; the cold-start latency is the only cost.
// MUT (bench only): 1 Q beats 0/1 swapped; 3 aq start one edge late; 4 KVN-arrival check expects one edge early
//   (fault); 6 Q store push one edge late (data misaligned); 7 tk drained bit inverted; 8 (xs_s) FIFO push from the
//   unregistered x_v (data misaligned); 9 (fan_s) kc data one pin stage short (word / valid split).
// =====================================================================================================================
module qkd_seq_core_static_s #(
    parameter integer KVN_A0 = 32,
    parameter integer KP0    = 36,
    parameter integer LP_WIN = 64,
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
    output reg           x_v,                     // Q store push (data = programme q_data at the store's input register)
    output reg           s_qpop,
    output reg  [27:0]   f_aqm_w, f_aqm_e,
    output reg  [32:0]   f_kc_w, f_kc_e,
    input  wire [1:0]    f_af_w, f_af_e,
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
    reg  [3:0]   afq;
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
        if (!rr) begin rv <= 0; qv <= 0; kvv <= 0; lpr <= 0; ov <= 0; hfq <= 0; afq <= 0; end
        else begin
            rv <= prg_req_v; qv <= prg_q_v; kvv <= kvn_word_valid; lpr <= lp_run; ov <= ar_h[7]; hfq <= hf;
            afq <= {f_af_e, f_af_w};
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
    // Q store push of beat n one edge before qkd_seq_static_p's (no xd_sel register in front of the store)
    wire         q_slot = (MUT == 6) ? (act && a < 8'd32) : (cmd || (act && a < 8'd31));
    wire         q_exp  = act && a >= 8'd1 && a <= 8'd32;         // programme q_valid (registered) expected
    wire         k_exp  = act && a >= 8'(KVN_A0 - ((MUT == 4) ? 1 : 0)) && a < 8'(KVN_A0 + 4 - ((MUT == 4) ? 1 : 0));
    wire [7:0]   a_st   = 8'(KP0 + 3 + ((MUT == 3) ? 1 : 0));
    wire         a_sta  = act && a == a_st;
    wire [5:0]   qn     = 6'(a - (a_st + 8'd1));
    wire         q_pop  = act && a > a_st && a <= a_st + 8'd32;
    function [2:0] ktag(input [1:0] j);
        ktag = {j[1], 1'b0, j[0]};                // HEADS 1: KVN tags 0, 1, 4, 5 in arrival order
    endfunction
    reg  [1:0]   kn_arr;
    reg          xk;
    reg          a_start, a_q_valid;
    reg  [5:0]   a_q_beat;
    reg  [6:0]   r_n, q_seen;
    reg          f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_pend, f_ovl;
    wire         kd_fault, kd_v;
    wire [31:0]  kd_d;
    ot_qkvd_kv_desc #(.NL(36)) u_kd (.clk(ck), .rst_n(rd), .p_mid_init(20'd0), .p_tok_init(20'd0),
        .attn_v(cmd && !act), .attn_layer(lp_hold_l), .attn_T(lp_hold_t),
        .done_v(ov && r_n == 7'd31), .k_v(kd_v), .k_d(kd_d), .k_ready(1'b1), .fault(kd_fault));
    always @(posedge ck or negedge rr) begin
        if (!rr) begin
            act <= 0; a <= 0; lp_seen <= 0; lp_age <= 0;
            x_v <= 0; xk <= 0; kn_arr <= 0; s_qpop <= 0;
            a_start <= 0; a_q_valid <= 0; r_n <= 0; q_seen <= 0;
            {f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_pend, f_ovl} <= 0;
        end else begin
            if (lpr) begin lp_seen <= 1; lp_age <= 0; lp_hold_l <= lpl; lp_hold_t <= lpt; end
            else if (lp_seen && lp_age != 7'h7f) lp_age <= lp_age + 1'b1;
            if (cmd) begin
                if (act) f_ovl <= 1;
                if (!lp_seen || lp_age > 7'(LP_WIN)) f_lp <= 1;
                if (rpos != 18'(lp_hold_t - 14'd1)) f_pos <= 1;      // authority position = the layer programme's T - 1
                act <= 1; a <= 0; layer <= lp_hold_l; a_T <= lp_hold_t; lp_seen <= 0; q_seen <= 0; kn_arr <= 0;
            end else if (act) begin
                a <= a + 1'b1;
                if (a == 8'(A_END)) act <= 0;
            end
            x_v <= q_slot;
            if (qv != q_exp) f_q <= 1;                               // programme Q beat off its compiled edge
            if (qv) begin
                if (qb != 5'(q_seen)) f_q <= 1;
                q_seen <= q_seen + 1'b1;
            end
            xk <= k_exp;
            if (kvv != xk) f_arr <= 1;                               // KVN word not on its compiled edge (check only)
            if (kvv) begin
                if (ktg[10:8] != 3'b010 || ktg[2:0] != ktag(kn_arr)) f_tag <= 1;
                kn_arr <= kn_arr + 1'b1;
            end
            s_qpop <= q_pop; a_q_valid <= q_pop;
            if (q_pop) a_q_beat <= (MUT == 1 && qn < 6'd2) ? (qn ^ 6'd1) : qn;
            if (act && a == a_st + 8'd1 && q_seen != 7'd32) f_q <= 1;
            a_start <= a_sta;
            if (a_start) r_n <= 0;
            else if (ov) begin
                r_n <= r_n + 1'b1;
                if (og || ob != r_n[5:0]) f_res <= 1;
            end
            f_pend <= f_pend | hfq | (|afq);
        end
    end
    reg [27:0] aq1;
    reg [2:0]  hsd;
    always @(posedge ck) begin
        aq1[26:7] <= {a_T, layer}; aq1[5:0] <= a_q_beat;
        f_aqm_w[26:7] <= aq1[26:7]; f_aqm_w[5:0] <= aq1[5:0]; f_aqm_e[26:7] <= aq1[26:7]; f_aqm_e[5:0] <= aq1[5:0];
        f_kc_w[31:0] <= kd_d; f_kc_e[31:0] <= kd_d;
    end
    always @(posedge ck or negedge rq)
        if (!rq) begin
            aq1[27] <= 0; aq1[6] <= 0; f_aqm_w[27] <= 0; f_aqm_w[6] <= 0; f_aqm_e[27] <= 0; f_aqm_e[6] <= 0;
            f_kc_w[32] <= 0; f_kc_e[32] <= 0; hsd <= 0; hs <= 0;
        end else begin
            aq1[27] <= a_start; aq1[6] <= a_q_valid;
            f_aqm_w[27] <= aq1[27]; f_aqm_w[6] <= aq1[6]; f_aqm_e[27] <= aq1[27]; f_aqm_e[6] <= aq1[6];
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
            drn <= (MUT == 7) ? act : !act;
            // cause[5] (was f_join | f_cr) and cause[0] are reserved 0 bits of the host status layout
            cause <= {f_arr | f_tag, f_lp, f_pos, 1'b0, kd_fault, f_pend, f_q | f_ovl, f_res, 1'b0};
            fault <= |{f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_pend, f_ovl, kd_fault};
        end
    assign tk  = {d_done, d_gen, drn, fault, {3'd0, fault}, sv[0], sv[1], d_tok, d_val, d_cyc};
    assign kst = {fault, cause};
endmodule

// Q store slice (hardened once, x4): the 128-b slice of the programme's Q beat, its Q FIFO and two registered copies (W /
// E fans).  Successor of qkd_seq_xs_tp8 without the KVN FIFO / KVN words / row copies (no consumer on the static die).
module qkd_seq_xs_s #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          x_v,
    input  wire [127:0]  x_d,
    input  wire          qpop,
    output wire [127:0]  q_w,
    output wire [127:0]  q_e
);
    wire rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    reg          xv, qp;
    reg [127:0]  xd;
    (* keep = "true", dont_touch = "true" *) reg [255:0] q;
    always @(posedge ck) xd <= x_d;
    always @(posedge ck or negedge rr)
        if (!rr) begin xv <= 1'b0; qp <= 1'b0; end
        else begin xv <= x_v; qp <= qpop; end
    wire [127:0] qh;
    ot_qkvd_seq_m_sfifo #(.W(128), .D(40)) u_q (.clk(ck), .rst_n(rr), .push((MUT == 8) ? x_v : xv), .din(xd), .pop(qp),
        .dout(qh));
    always @(posedge ck) if (qp) q <= {2{qh}};
    assign q_w = q[127:0];
    assign q_e = q[255:128];
endmodule

// One quadrant's pin registers (hardened once, x4): aq / kc out (capture, then launch at the face), the attention
// stack's fault bit back.  Successor of qkd_seq_fan without kvn / kvn_cr / mf.
module qkd_seq_fan_s #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [27:0]   aqm,
    input  wire [511:0]  q,
    input  wire [32:0]   kc_i,
    output wire [539:0]  aq,                      // {start, T 14, layer 6, q valid, beat 6, data 512}
    output wire [32:0]   kc,                      // {v, d 32}
    input  wire          af,
    output reg           af_o
);
    wire rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    reg [27:0]  am, am2;
    reg [511:0] qd, qd2;
    reg [32:0]  kq, kq2;
    reg         a1;
    always @(posedge ck) begin
        am[26:7] <= aqm[26:7]; am[5:0] <= aqm[5:0]; am2[26:7] <= am[26:7]; am2[5:0] <= am[5:0];
        qd <= q; qd2 <= qd; kq[31:0] <= kc_i[31:0]; kq2[31:0] <= (MUT == 9) ? kc_i[31:0] : kq[31:0];
    end
    always @(posedge ck or negedge rr)
        if (!rr) begin
            am[27] <= 1'b0; am[6] <= 1'b0; am2[27] <= 1'b0; am2[6] <= 1'b0; kq[32] <= 1'b0; kq2[32] <= 1'b0;
            a1 <= 1'b0; af_o <= 1'b0;
        end else begin
            am[27] <= aqm[27]; am[6] <= aqm[6]; am2[27] <= am[27]; am2[6] <= am[6];
            kq[32] <= kc_i[32]; kq2[32] <= kq[32]; a1 <= af; af_o <= a1;
        end
    assign aq = {am2[27:6], am2[5:0], qd2};
    assign kc = kq2;
endmodule

// wires-only parent on the contract slot `seq` (successor of qkd_seq_static_p): no cell, no flop of its own
module qkd_seq_static_s #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          prg_req_v,
    input  wire [17:0]   prg_req_pos,
    input  wire          prg_q_v,
    input  wire [4:0]    prg_q_beat,
    input  wire [511:0]  prg_q_data,
    input  wire          kvn_word_valid,
    input  wire [10:0]   kvn_word_tag,
    input  wire          lp_run,
    input  wire [5:0]    lp_layer,
    input  wire [13:0]   lp_ctx_t,
    input  wire [173:0]  svc,
    output wire [539:0]  aq_WS, aq_WN, aq_ES, aq_EN,
    output wire [32:0]   kc_WS, kc_WN, kc_ES, kc_EN,
    input  wire          af_WS, af_WN, af_ES, af_EN,
    input  wire [7:0]    ar_h,                    // the hub result word's {valid, g, beat 6} (data bypasses the sequencer)
    input  wire          hf,
    output wire          hs,
    output wire [92:0]   tk,
    output wire [9:0]    kst
);
    wire          x_v, s_qpop;
    wire [27:0]   f_aqm [0:1];
    wire [32:0]   f_kc  [0:1];
    wire [3:0]    f_af;
    wire [255:0]  sq  [0:3];
`ifdef OT_QKD_SEQ_STATIC_S_HARD
    qkd_seq_core_static_s u_core (
`else
    qkd_seq_core_static_s #(.MUT(MUT)) u_core (
`endif
        .ck(ck), .rst_n(rst_n), .prg_req_v(prg_req_v), .prg_req_pos(prg_req_pos),
        .prg_q_v(prg_q_v), .prg_q_beat(prg_q_beat), .kvn_word_valid(kvn_word_valid), .kvn_word_tag(kvn_word_tag),
        .lp_run(lp_run), .lp_layer(lp_layer), .lp_ctx_t(lp_ctx_t),
        .svc_h({svc[173:90], svc[25], svc[24], svc[20], svc[19]}),
        .x_v(x_v), .s_qpop(s_qpop), .f_aqm_w(f_aqm[0]), .f_aqm_e(f_aqm[1]), .f_kc_w(f_kc[0]), .f_kc_e(f_kc[1]),
        .f_af_w(f_af[1:0]), .f_af_e(f_af[3:2]), .hs(hs), .ar_h(ar_h), .hf(hf), .tk(tk), .kst(kst));
    genvar s, k;
    generate for (s = 0; s < 4; s = s + 1) begin : g_xs
`ifdef OT_QKD_SEQ_STATIC_S_HARD
        qkd_seq_xs_s u_xs (.ck(ck),
`else
        qkd_seq_xs_s #(.MUT(MUT)) u_xs (.ck(ck),
`endif
            .rst_n(rst_n), .x_v(x_v), .x_d(prg_q_data[128*s +: 128]), .qpop(s_qpop),
            .q_w(sq[s][127:0]), .q_e(sq[s][255:128]));
    end endgenerate
    wire [511:0]  fq  [0:1];
    generate for (k = 0; k < 2; k = k + 1) begin : g_cp
        for (s = 0; s < 4; s = s + 1) begin : g_s
            assign fq[k][128*s +: 128] = sq[s][128*k +: 128];
        end
    end endgenerate
    wire [539:0]  aq  [0:3];
    wire [32:0]   kc  [0:3];
    wire [3:0]    af = {af_EN, af_ES, af_WN, af_WS};
    generate for (k = 0; k < 4; k = k + 1) begin : g_fan
`ifdef OT_QKD_SEQ_STATIC_S_HARD
        qkd_seq_fan_s u_fan (.ck(ck),
`else
        qkd_seq_fan_s #(.MUT(MUT)) u_fan (.ck(ck),
`endif
            .rst_n(rst_n), .aqm(f_aqm[k/2]), .q(fq[k/2]), .kc_i(f_kc[k/2]), .aq(aq[k]),
            .kc(kc[k]), .af(af[k]), .af_o(f_af[k]));
    end endgenerate
    assign aq_WS = aq[0];   assign aq_WN = aq[1];   assign aq_ES = aq[2];   assign aq_EN = aq[3];
    assign kc_WS = kc[0];   assign kc_WN = kc[1];   assign kc_ES = kc[2];   assign kc_EN = kc[3];
endmodule

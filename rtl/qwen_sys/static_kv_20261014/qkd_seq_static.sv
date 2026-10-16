`timescale 1ns/1ps
// =====================================================================================================================
// Q-KVSYS PVJOIN 2026-10-16 (lead-approved retirement of the credit/event sequencer qkd_seq on the static KV path):
// qkd_seq_static = the KV die sequencer as a STATIC FORMATTER on qkd_seq's legacy die faces.  No credit, no ready, no
// event-driven state: every store pop, attention start, Q beat, posted KV row and stream descriptor leaves at a fixed edge
// after the layer's compiled CMD record slot of the static D2D end; arrivals that are not exactly where the link compiler
// put them are FAULTS (sticky), never waited for.
//
// Cluster (wires-only parent qkd_seq_static over hardened leaves, as qkd_seq):
//   qkd_seq_core_static x 1  NEW control leaf (this file)
//   qkd_seq_xs_tp8      x 4  UNCHANGED store slices (HEADS 1, closed view qkd_seq_xs_tp8): Q FIFO + KVN FIFO + rows
//   qkd_seq_fan         x 4  UNCHANGED quadrant pin registers (ot_qkvd_seq_m_fan, closed views): aq / kvn / kc out
// Die faces OUT (bit-identical layout to qkd_seq): aq_<q>[539:0], kvn_<q>_d[1046:0], kc_<q>[32:0], hs, tk[92:0], kst[9:0].
// Die faces IN (replace qkd_seq's lx credit-bridge words r_x3_d / r_sd / r_kvd / t_ar_cr and the host hc):
//   arx {att_rx_v, att_rx_kind 4, att_rx_beat 5}     the static D2D end's attention RX port (CMD kind 1, Q kind 2)
//   kvw {kvn_word_valid, kvn_word_tag 11, kvn_word_data 512}  the end's KVN receiver (data = every RX payload, one edge
//        after its event: the Q beat data rides the same 512 wires, so the store's x3 word needs no mux)
//   lp  {attention_run, layer 6, ctx_t 14}           the layer programme (qkd_static_kv_layer_programme_img): the
//        layer's T = ctx_t and layer; its attention_run must precede the CMD record within LP_WIN edges
//   svc[173:0]                                        the end's HOST service word (same bits as the root's svc bus):
//        engine result / collective busy / KV flush for tk (the host's legacy token word; the native host path ignores it)
//   ar, hf, af_<q>, mf_<q>, kvn_<q>_cr               as qkd_seq (hub results, faults, landing row credits as CHECKS)
// Gone with qkd_seq: x3/kvd/RES credits (r_x3_cr, t_ar_cr), the ROM-die stage stepper copy (r_sd, ds, pw, hc), t_ar_d.
//
// Fixed timeline (a = core edges after the CMD record is captured at the core pin; HEADS 1, Q FP32: 32 Q words,
// 4 KVN words tags 0,1,4,5, 2 posted rows vg 00 / 10, 32 RES words), from the link compiler's slot offsets
// (tools/qwen_split/d2d_link_calendar.py: Q rx_out CMD+1..+32, KVN rx_out CMD+34..+37):
//   store x_v  Q: the beat's own event pin, registered (data-aligned);  KVN: compiled at a = KVN_A0+1+k (checked against
//              kvn_word_valid, tags checked against 0,1,4,5)
//   kpop a = KP0..KP0+3, aq start a = KP0+4, Q pops a = KP0+5..KP0+36 (beat n at KP0+5+n), rows posted a = KP0+5, KP0+7
//   stream descriptor (ot_qkvd_kv_desc, unchanged) launched at a = 0; hs = aq start + 3 (as qkd_seq)
// The fans add the same two pin stages as on qkd_seq.  Latency against qkd_seq: see tools/qwen_static_kv/seq_static_bench.sh
// (measured per face and recorded in the cost ledger).
// MUT (bench only): 1 Q beats 0/1 swapped; 2 the posted rows' t = T (not T-1); 3 aq start one edge late;
// 4 KVN store push one edge early (data misaligned).
// =====================================================================================================================
module qkd_seq_core_static #(
    parameter integer KVN_A0 = 32,
    parameter integer KP0    = 37,
    parameter integer LP_WIN = 64,
    parameter integer KWC    = 4,
    parameter integer MUT    = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          att_rx_v,
    input  wire [3:0]    att_rx_kind,
    input  wire [4:0]    att_rx_beat,
    input  wire          kvn_word_valid,
    input  wire [10:0]   kvn_word_tag,
    input  wire [18:0]   cmd_d,                   // kvn_word_data[18:0]: the CMD record's {position 18, 1}
    input  wire          lp_run,
    input  wire [5:0]    lp_layer,
    input  wire [13:0]   lp_ctx_t,
    input  wire [87:0]   svc_h,                   // {cycles 32, value 32, token 18, gen 2, done, result_v, kv_flush, coll_busy}
    // store control
    output reg           x_v,
    output reg  [2:0]    x_cls,
    output reg           s_qpop,
    output reg           s_kpop,
    output reg  [2:0]    s_kidx,
    output reg           s_kwgo,
    output reg  [1:0]    s_kwn,
    // fan control (W copy, E copy)
    output reg  [27:0]   f_aqm_w, f_aqm_e,
    output reg  [22:0]   f_kwm_w, f_kwm_e,
    output reg  [32:0]   f_kc_w, f_kc_e,
    input  wire [1:0]    f_cr_w, f_cr_e,
    input  wire [1:0]    f_af_w, f_af_e,
    input  wire [1:0]    f_mf_w, f_mf_e,
    // hub
    output reg           hs,
    input  wire [7:0]    ar_h,                    // the hub result word's {valid, g, beat 6} (data bypasses the sequencer)
    input  wire          hf,
    // host
    output wire [92:0]   tk,
    output wire [9:0]    kst
);
    // reset: one pin flop, then a relay (as qkd_seq_core)
    wire rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    // ---- pin capture ----
    reg          rv, kvv, lpr, ov, og, hfq;
    reg  [3:0]   rk, crq, afq, mfq;
    reg  [4:0]   rb;
    reg  [10:0]  ktg;
    reg  [18:0]  cd;
    reg  [5:0]   lpl, ob;
    reg  [13:0]  lpt;
    reg  [87:0]  sv;
    always @(posedge ck) begin
        rk <= att_rx_kind; rb <= att_rx_beat; ktg <= kvn_word_tag; cd <= cmd_d; lpl <= lp_layer; lpt <= lp_ctx_t;
        ob <= ar_h[5:0]; og <= ar_h[6]; sv <= svc_h;
    end
    always @(posedge ck or negedge rr)
        if (!rr) begin rv <= 0; kvv <= 0; lpr <= 0; ov <= 0; hfq <= 0; crq <= 0; afq <= 0; mfq <= 0; end
        else begin
            rv <= att_rx_v; kvv <= kvn_word_valid; lpr <= lp_run; ov <= ar_h[7]; hfq <= hf;
            crq <= {f_cr_e, f_cr_w}; afq <= {f_af_e, f_af_w}; mfq <= {f_mf_e, f_mf_w};
        end
    // ---- the layer's fixed timeline ----
    localparam integer A_END = KP0 + 40;
    reg          act;
    reg  [7:0]   a;
    reg  [5:0]   layer, lp_hold_l;
    reg  [13:0]  a_T, lp_hold_t;
    reg  [6:0]   lp_age;
    reg          lp_seen;
    wire         cmd  = rv && rk == 4'd1;
    wire         qev  = rv && rk == 4'd2;
    // compiled store / fan events (decoded one edge ahead, registered)
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
        ktag = {j[1], 1'b0, j[0]};                // HEADS 1: KVN tags 0, 1, 4, 5 in arrival order
    endfunction
    reg  [1:0]   kn_arr;
    reg          xk, xk2;
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
    ot_qkvd_kv_desc #(.NL(36)) u_kd (.clk(ck), .rst_n(rr), .p_mid_init(20'd0), .p_tok_init(20'd0),
        .attn_v(cmd && !act), .attn_layer(lp_hold_l), .attn_T(lp_hold_t),
        .done_v(ov && r_n == 7'd31), .k_v(kd_v), .k_d(kd_d), .k_ready(1'b1), .fault(kd_fault));
    integer i;
    always @(posedge ck or negedge rr) begin
        if (!rr) begin
            act <= 0; a <= 0; layer <= 0; a_T <= 0; lp_seen <= 0; lp_age <= 0; lp_hold_l <= 0; lp_hold_t <= 0;
            x_v <= 0; x_cls <= 0; xk <= 0; xk2 <= 0; kn_arr <= 0; s_qpop <= 0; s_kpop <= 0; s_kidx <= 0; s_kwgo <= 0; s_kwn <= 0;
            a_start <= 0; a_q_valid <= 0; a_q_beat <= 0; kvw_v <= 0; r_n <= 0; q_seen <= 0;
            kwc <= 8'(KWC); kwq <= 0; for (i = 0; i < 4; i = i + 1) jc[i] <= 0;
            {f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_cr, f_join, f_pend, f_row, f_ovl} <= 0;
        end else begin
            // layer programme expectation: its attention_run opens a window the CMD record must land in
            if (lpr) begin lp_seen <= 1; lp_age <= 0; lp_hold_l <= lpl; lp_hold_t <= lpt; end
            else if (lp_seen && lp_age != 7'h7f) lp_age <= lp_age + 1'b1;
            if (cmd) begin
                if (act) f_ovl <= 1;
                if (!lp_seen || lp_age > 7'(LP_WIN)) f_lp <= 1;
                act <= 1; a <= 0; layer <= lp_hold_l; a_T <= lp_hold_t; lp_seen <= 0; q_seen <= 0; kn_arr <= 0;
            end else if (act) begin
                a <= a + 1'b1;
                if (a == 8'(A_END)) act <= 0;
            end
            // the CMD record's data arrives on the KVN data wires one edge after its event: position = T - 1
            if (act && a == 8'd0 && cd != {5'd0, 13'(a_T - 14'd1), 1'b1}) f_pos <= 1;
            // store pushes: Q at its own (registered) event, KVN at its compiled edge
            // Q: the beat's data is on the KVN data wires one edge after its event -> push from the event pin
            xk <= k_exp; xk2 <= xk;
            x_v <= (att_rx_v && att_rx_kind == 4'd2) || k_exp;
            x_cls <= (att_rx_v && att_rx_kind == 4'd2) ? 3'b001 : 3'b010;
            if (qev) begin
                if (!act || rb != 5'(q_seen)) f_q <= 1;
                q_seen <= q_seen + 1'b1;
            end
            if (kvv != xk2) f_arr <= 1;                              // KVN word not on its compiled edge
            if (kvv) begin
                if (ktg[10:8] != 3'b010 || ktg[2:0] != ktag(kn_arr)) f_tag <= 1;
                kn_arr <= kn_arr + 1'b1;
            end
            if (rv && !cmd && !qev) f_q <= 1;                       // another record kind on the attention port
            // pops, start, Q beats, rows
            s_kpop <= k_pop; s_kidx <= ktag(kp_j);
            s_qpop <= q_pop; a_q_valid <= q_pop;
            if (q_pop) a_q_beat <= (MUT == 1 && qn < 6'd2) ? (qn ^ 6'd1) : qn;
            if (act && a == a_st + 8'd1 && q_seen != 7'd32) f_q <= 1; // every Q beat stored before the first pop
            a_start <= a_sta;
            kvw_v <= kw_go;
            if (kw_go) begin kvw_vg <= {kw_row, 1'b0}; kvw_t <= (MUT == 2) ? a_T : a_T - 14'd1; kvw_layer <= layer; end
            s_kwgo <= kw_go; s_kwn <= {kw_row, 1'b0};
            // landing row credits: a CHECK of the compiled occupancy (2 rows a layer against KWC), never a gate
            if (kw_go && kwc == 0) f_cr <= 1;
            kwc <= kwc - (kw_go ? 8'd1 : 8'd0) + (kwq ? 8'd1 : 8'd0);
            kwq <= jn;
            if (kwq && kwc == 8'(KWC)) f_cr <= 1;
            for (i = 0; i < 4; i = i + 1) begin
                jc[i] <= jc[i] + (crq[i] ? 3'd1 : 3'd0) - ((jn && jc[i] != 0) ? 3'd1 : 3'd0);
                if (crq[i] && jc[i] == 3'd7) f_join <= 1;
            end
            // hub results: 32 in beat order after the start
            if (a_start) r_n <= 0;
            else if (ov) begin
                r_n <= r_n + 1'b1;
                if (og || ob != r_n[5:0]) f_res <= 1;
            end
            f_pend <= f_pend | hfq | (|afq);
            f_row <= f_row | (|mfq);
        end
    end
    // ---- outputs to the fans (as qkd_seq: own registers + one stage, then the pin copies) ----
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
    always @(posedge ck or negedge rr)
        if (!rr) begin
            aq1[27] <= 0; aq1[6] <= 0; f_aqm_w[27] <= 0; f_aqm_w[6] <= 0; f_aqm_e[27] <= 0; f_aqm_e[6] <= 0;
            kw1[22] <= 0; f_kwm_w[22] <= 0; f_kwm_e[22] <= 0; f_kc_w[32] <= 0; f_kc_e[32] <= 0; hsd <= 0; hs <= 0;
        end else begin
            aq1[27] <= a_start; aq1[6] <= a_q_valid;
            f_aqm_w[27] <= aq1[27]; f_aqm_w[6] <= aq1[6]; f_aqm_e[27] <= aq1[27]; f_aqm_e[6] <= aq1[6];
            kw1[22] <= kvw_v; f_kwm_w[22] <= kw1[22]; f_kwm_e[22] <= kw1[22];
            f_kc_w[32] <= kd_v; f_kc_e[32] <= kd_v;
            hsd <= {hsd[1:0], a_start}; hs <= hsd[2];
        end
    // ---- host token word (legacy face; the native host path does not read it) and fault word ----
    reg        d_done, drn, fault;
    reg [1:0]  d_gen;
    reg [17:0] d_tok;
    reg [31:0] d_val, d_cyc;
    reg [8:0]  cause;
    always @(posedge ck or negedge rr)
        if (!rr) begin d_done <= 0; d_gen <= 0; d_tok <= 0; d_val <= 0; d_cyc <= 0; drn <= 0; fault <= 0; cause <= 0; end
        else begin
            if (sv[2]) begin                                        // engine_result_v (kind-15 record of the compute die)
                d_done <= sv[3]; d_gen <= sv[5:4]; d_tok <= sv[23:6]; d_val <= sv[55:24]; d_cyc <= sv[87:56];
            end
            drn <= !act && kwc == 8'(KWC) && !kwq && (jc[0] == 0) && (jc[1] == 0) && (jc[2] == 0) && (jc[3] == 0);
            cause <= {f_arr | f_tag, f_lp, f_pos, f_join | f_cr, kd_fault, f_pend | f_row, f_q | f_ovl, f_res, 1'b0};
            fault <= |{f_arr, f_tag, f_q, f_lp, f_pos, f_res, f_cr, f_join, f_pend, f_row, f_ovl, kd_fault};
        end
    // {d_done, gen 2, drained, fault, code 4, coll_busy, kv_write_flush, next_token 18, next_val 32, cycles 32}
    assign tk  = {d_done, d_gen, drn, fault, {3'd0, fault}, sv[0], sv[1], d_tok, d_val, d_cyc};
    assign kst = {fault, cause};
endmodule

// wires-only parent on the contract slot `seq` (static successor of qkd_seq): no cell, no flop of its own
module qkd_seq_static #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          att_rx_v,
    input  wire [3:0]    att_rx_kind,
    input  wire [4:0]    att_rx_beat,
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
    qkd_seq_core_static #(.MUT(MUT)) u_core (.ck(ck), .rst_n(rst_n), .att_rx_v(att_rx_v), .att_rx_kind(att_rx_kind),
        .att_rx_beat(att_rx_beat), .kvn_word_valid(kvn_word_valid), .kvn_word_tag(kvn_word_tag), .cmd_d(kvn_word_data[18:0]),
        .lp_run(lp_run), .lp_layer(lp_layer), .lp_ctx_t(lp_ctx_t),
        .svc_h({svc[173:90], svc[25], svc[24], svc[20], svc[19]}),
        .x_v(x_v), .x_cls(x_cls), .s_qpop(s_qpop), .s_kpop(s_kpop), .s_kidx(s_kidx), .s_kwgo(s_kwgo), .s_kwn(s_kwn),
        .f_aqm_w(f_aqm[0]), .f_aqm_e(f_aqm[1]), .f_kwm_w(f_kwm[0]), .f_kwm_e(f_kwm[1]), .f_kc_w(f_kc[0]), .f_kc_e(f_kc[1]),
        .f_cr_w(f_cr[1:0]), .f_cr_e(f_cr[3:2]), .f_af_w(f_af[1:0]), .f_af_e(f_af[3:2]), .f_mf_w(f_mf[1:0]), .f_mf_e(f_mf[3:2]),
        .hs(hs), .ar_h(ar[519:512]), .hf(hf), .tk(tk), .kst(kst));
    genvar s, k;
    generate for (s = 0; s < 4; s = s + 1) begin : g_xs
        qkd_seq_xs_tp8 u_xs (.ck(ck), .rst_n(rst_n), .x_v(x_v), .x_cls(x_cls), .x_d(kvn_word_data[128*s +: 128]),
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

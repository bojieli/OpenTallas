`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KVJ-C 2026-10-17 (coordinator decision D2, kv_static_join_plan.md): the embedding gateway, BOOT-ONLY.
//
// Successor of qkd_embgw_splitboot (rtl/qwen_sys/split_20261014/qkd_embgw_splitboot.sv).  On the static KV die the token's
// embedding row is read through the 128 pseudo-channels by qkd_embedding_static_pc (compiled issue edges), returned on
// the four per-stack return-hop trains, joined by qkd_embedding_static_join and sent on the d2d link by
// qkd_embedding_row_tx.  The legacy credit SU request face (r_ea / t_ecr / t_eq: the r21f embedding ROM face with RQD
// credits, the FETCH broadcast and the in-order row answer) therefore has no consumer and is REMOVED, not given a
// producer.  The gateway keeps only its boot role, bit-for-bit and cycle-for-cycle as in qkd_embgw_splitboot:
//   hb {v, end, E 25, data 256} boot words from the host (BD-word skid, hb_cr credit)  ->  emf_<q> BOOT_WR to the stack
//   that holds the sector, BOOT_END to all four (snooped: expected count / checksum);  emr_<q> STATUS words
//   {count, checksum} from the four strips  ->  emb_ready (sums match, sticky) else fault.  est = {cause 11, fault,
//   emb_ready} with the SAME cause layout ([7:0] the gateway fault_code, [8] strip overrun, [9] boot skid overrun,
//   [10] strip credit overflow).  Boot is the exceptional initialisation phase (owner rule 10-14: credits stay at the
//   boot / off-die boundaries); the token path through this cell no longer exists.
// Removed state: the 32-entry request FIFO, the row FSM, the FETCH command and its sequence, the 512-b eq register.
// Behavioural change outside the legal envelope only: a CODE / SCALE word from a strip (only a FETCH can cause one, and
// no FETCH is ever sent) is now consumed and latched as fault_code[3] instead of parking in its slot forever.
// Proof of unchanged behaviour: rtl/test/qwen_static_kv/tb_qkd_embgw_boot_equiv.sv (lock-step against
// qkd_embgw_splitboot with r_ea idle, under random legal stimulus and under the 4-strip boot bench).
// MUT (bench only): 5 = BOOT_WR sent to stack + 1 (as the splitboot body); 6 = a new BOOT_END does not clear emb_ready.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_embgw_boot #(
    parameter integer OD  = 4,
    parameter integer TXC = 4,
    parameter integer BD  = 4,
    parameter integer MUT = 0
) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire [3:0]        lr_v,
    input  wire [4*2-1:0]    lr_k,
    input  wire [3:0]        lr_p,
    input  wire [4*4-1:0]    lr_s,
    input  wire [4*512-1:0]  lr_d,
    input  wire [3:0]        lr_cr,
    output reg  [3:0]        lt_v,
    output reg  [4*2-1:0]    lt_k,
    output reg  [4*4-1:0]    lt_s,
    output reg  [4*281-1:0]  lt_d,
    output reg  [3:0]        lt_cr,
    input  wire              hb_v,
    input  wire              hb_end,
    input  wire [24:0]       hb_e,
    input  wire [255:0]      hb_d,
    output reg               hb_cr,
    output wire [12:0]       st
);
    localparam [24:0] E_SCALE = 25'd19447808;
    localparam [1:0] K_BOOT_WR = 2'd1, K_BOOT_END = 2'd2;   // gateway -> strip
    localparam [1:0] K_STATUS = 2'd2;                        // strip -> gateway
    localparam integer OA = $clog2(OD);
    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    localparam integer CW = $clog2(TXC + 1) + 1;
    localparam integer RW = 2 + 1 + 4 + 512;
    integer i;
    // ---- reset: asynchronous assert, synchronous release ----
    reg rs0, rs;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    // ---- input capture ----
    reg          hbv_p, hbe_p;
    reg [24:0]   hbs_p;
    reg [255:0]  hbd_p;
    reg [3:0]    lrv_p, lrc_p;
    reg [RW-1:0] lrw_p [0:3];
    always @(posedge ck or negedge rs)
        if (!rs) begin hbv_p <= 1'b0; lrv_p <= 4'd0; lrc_p <= 4'd0; end
        else begin hbv_p <= hb_v; lrv_p <= lr_v; lrc_p <= lr_cr; end
    always @(posedge ck) begin
        hbe_p <= hb_end; hbs_p <= hb_e; hbd_p <= hb_d;
        for (i = 0; i < 4; i = i + 1) lrw_p[i] <= {lr_k[2*i +: 2], lr_p[i], lr_s[4*i +: 4], lr_d[512*i +: 512]};
    end
    // ---- per-link receive buffers (OD words: the strip's transmit credits) ----
    reg  [RW-1:0] rf  [0:4*OD-1];
    reg  [OA:0]   rfw [0:3];
    reg  [OA:0]   rfr [0:3];
    reg  [3:0]    rne, rfull;
    always @(*)
        for (i = 0; i < 4; i = i + 1) begin
            rne[i]   = (rfw[i] != rfr[i]);
            rfull[i] = (rfw[i][OA-1:0] == rfr[i][OA-1:0]) && (rfw[i][OA] != rfr[i][OA]);
        end
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (lrv_p[i]) rf[i*OD + rfw[i][OA-1:0]] <= lrw_p[i];
    // ---- one-word slot a link (the splitboot gateway's e_take slots) ----
    reg  [3:0]    sv;
    reg  [RW-1:0] sd [0:3];
    wire [3:0]    e_take = rne & ~sv;
    reg  [3:0]    stv, xtv;                  // slots holding a STATUS word / any other word (fault)
    always @(*) for (i = 0; i < 4; i = i + 1) begin
        stv[i] = sv[i] && sd[i][RW-1 -: 2] == K_STATUS;
        xtv[i] = sv[i] && sd[i][RW-1 -: 2] != K_STATUS;
    end
    wire [1:0]    sp = stv[0] ? 2'd0 : stv[1] ? 2'd1 : stv[2] ? 2'd2 : 2'd3;
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (e_take[i]) sd[i] <= rf[i*OD + rfr[i][OA-1:0]];
    // ---- boot skid (BD words: the host router's credits) ----
    reg  [281:0]  bq   [0:BD-1];
    reg  [1:0]    bdst [0:BD-1];
    reg  [BA:0]   bw, br;
    wire          bne   = (bw != br);
    wire          bfull = (bw[BA-1:0] == br[BA-1:0]) && (bw[BA] != br[BA]);
    wire [281:0]  bh    = bq[br[BA-1:0]];
    wire          bh_end = bh[281];
    wire [1:0]    bh_dst = bdst[br[BA-1:0]];
    wire [24:0]   hbs_sc = hbs_p - E_SCALE;
    wire [1:0]    hb_stk = (hbs_p < E_SCALE) ? hbs_p[6:5] : hbs_sc[6:5];
    always @(posedge ck) if (hbv_p && !bfull) begin
        bq[bw[BA-1:0]]   <= {hbe_p, hbs_p, hbd_p};
        bdst[bw[BA-1:0]] <= (MUT == 5) ? (hb_stk + 2'd1) : hb_stk;
    end
    // ---- transmit: link credits, the boot skid head ----
    reg  [CW-1:0] lc [0:3];
    reg  [3:0]    lcnz;
    always @(*) for (i = 0; i < 4; i = i + 1) lcnz[i] = (lc[i] != 0);
    wire          bsend  = bne && (bh_end ? (&lcnz) : lcnz[bh_dst]);
    wire          bend_v = bsend && bh_end;
    reg  [3:0]    tgt;
    always @(*) for (i = 0; i < 4; i = i + 1) tgt[i] = bsend && (bh_end || bh_dst == i);
    wire [1:0]    t_k = bh_end ? K_BOOT_END : K_BOOT_WR;
    wire [280:0]  t_d = bh_end ? {217'd0, bh[63:0]} : {bh[255:0], bh[280:256]};
    reg           f_rx, f_bq, f_lc;
    always @(posedge ck) for (i = 0; i < 4; i = i + 1) if (tgt[i]) begin
        lt_k[2*i +: 2] <= t_k; lt_s[4*i +: 4] <= 4'd0; lt_d[281*i +: 281] <= t_d;
    end
    // ---- boot check ----
    reg        bend, emb_ready, f_q;
    reg [31:0] x_cnt, x_csum, a_cnt, a_csum;
    reg [2:0]  nst;
    reg [7:0]  fc;
    always @(posedge ck or negedge rs)
        if (!rs) begin
            bw <= 0; br <= 0; lt_v <= 4'd0; lt_cr <= 4'd0; hb_cr <= 1'b0; f_rx <= 1'b0; f_bq <= 1'b0; f_lc <= 1'b0;
            for (i = 0; i < 4; i = i + 1) begin rfw[i] <= 0; rfr[i] <= 0; lc[i] <= TXC[CW-1:0]; end
            sv <= 4'd0; bend <= 1'b0; x_cnt <= 0; x_csum <= 0; a_cnt <= 0; a_csum <= 0; nst <= 0; emb_ready <= 1'b0;
            f_q <= 1'b0; fc <= 8'd0;
        end else begin
            for (i = 0; i < 4; i = i + 1) begin
                if (lrv_p[i]) begin if (rfull[i]) f_rx <= 1'b1; else rfw[i] <= rfw[i] + 1'b1; end
                if (e_take[i]) begin rfr[i] <= rfr[i] + 1'b1; sv[i] <= 1'b1; end
                lc[i] <= lc[i] - {{(CW-1){1'b0}}, tgt[i]} + {{(CW-1){1'b0}}, lrc_p[i]};
                if (lrc_p[i] && !tgt[i] && lc[i] == TXC[CW-1:0]) f_lc <= 1'b1;
                if (xtv[i]) begin sv[i] <= 1'b0; f_q <= 1'b1; fc[3] <= 1'b1; end   // no FETCH is ever sent
            end
            lt_cr <= e_take;
            lt_v  <= tgt;
            if (hbv_p) begin if (bfull) f_bq <= 1'b1; else bw <= bw + 1'b1; end
            if (bsend) br <= br + 1'b1;
            hb_cr <= bsend;
            if (|stv) begin
                sv[sp] <= 1'b0;
                if (!bend) begin f_q <= 1'b1; fc[6] <= 1'b1; end
                a_cnt <= a_cnt + sd[sp][31:0]; a_csum <= a_csum + sd[sp][63:32]; nst <= nst + 1'b1;
            end
            if (bend_v) begin
                if (MUT != 6) emb_ready <= 1'b0;
                bend <= 1'b1; x_cnt <= bh[31:0]; x_csum <= bh[63:32]; a_cnt <= 0; a_csum <= 0; nst <= 0;
            end
            if (bend && nst == 3'd4) begin
                bend <= 1'b0;
                if (a_cnt == x_cnt && a_csum == x_csum) emb_ready <= 1'b1;
                else begin f_q <= 1'b1; fc[5] <= 1'b1; end
            end
        end
    // ---- status (flops at the pins) ----
    reg [12:0] st_q;
    always @(posedge ck or negedge rs)
        if (!rs) st_q <= 13'd0;
        else st_q <= {f_lc, f_bq, f_rx, fc, f_q | f_rx | f_bq | f_lc, emb_ready};
    assign st = st_q;
endmodule

// The die cell (slot): the splitboot cell's ports minus r_ea / t_ecr / t_eq, packing unchanged (emr {kind 2, poison,
// sequence 4, data 512, v}, emf {kind 2, sequence 4, data 281, v}, hb {data 256, E 25, end, v}, est {cause 11, fault,
// emb_ready}).  <q> = WS, WN, ES, EN = stack 0..3.
module qkd_embgw_boot #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [519:0]  emr_WS,
    input  wire          emr_WS_cr,
    output wire [287:0]  emf_WS,
    output wire          emf_WS_cr,
    input  wire [519:0]  emr_WN,
    input  wire          emr_WN_cr,
    output wire [287:0]  emf_WN,
    output wire          emf_WN_cr,
    input  wire [519:0]  emr_ES,
    input  wire          emr_ES_cr,
    output wire [287:0]  emf_ES,
    output wire          emf_ES_cr,
    input  wire [519:0]  emr_EN,
    input  wire          emr_EN_cr,
    output wire [287:0]  emf_EN,
    output wire          emf_EN_cr,
    input  wire [282:0]  hb,
    output wire          hb_cr,
    output wire [12:0]   est
);
    wire [519:0] emr [0:3];
    wire [287:0] emf [0:3];
    assign emr[0] = emr_WS; assign emr[1] = emr_WN; assign emr[2] = emr_ES; assign emr[3] = emr_EN;
    assign emf_WS = emf[0]; assign emf_WN = emf[1]; assign emf_ES = emf[2]; assign emf_EN = emf[3];
    wire [3:0]       lr_v, lr_p, lt_v, lt_cr;
    wire [7:0]       lr_k, lt_k;
    wire [15:0]      lr_s, lt_s;
    wire [4*512-1:0] lr_d;
    wire [4*281-1:0] lt_d;
    wire [12:0]      st;
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_lk
        assign lr_v[q]             = emr[q][0];
        assign lr_d[512*q +: 512]  = emr[q][512:1];
        assign lr_s[4*q +: 4]      = emr[q][516:513];
        assign lr_p[q]             = emr[q][517];
        assign lr_k[2*q +: 2]      = emr[q][519:518];
        assign emf[q]              = {lt_k[2*q +: 2], lt_s[4*q +: 4], lt_d[281*q +: 281], lt_v[q]};
    end endgenerate
    ot_qkvd_embgw_boot #(.OD(4), .TXC(4), .BD(4), .MUT(MUT)) u_body (
        .ck(ck), .rst_n(rst_n),
        .lr_v(lr_v), .lr_k(lr_k), .lr_p(lr_p), .lr_s(lr_s), .lr_d(lr_d),
        .lr_cr({emr_EN_cr, emr_ES_cr, emr_WN_cr, emr_WS_cr}),
        .lt_v(lt_v), .lt_k(lt_k), .lt_s(lt_s), .lt_d(lt_d),
        .lt_cr({emf_EN_cr, emf_ES_cr, emf_WN_cr, emf_WS_cr}),
        .hb_v(hb[0]), .hb_end(hb[1]), .hb_e(hb[26:2]), .hb_d(hb[282:27]), .hb_cr(hb_cr),
        .st(st));
    assign est = st;
endmodule

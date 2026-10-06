`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION MODEL (default-off successor of ot_qwen_hbm_stream4_ack, which is left byte-identical;
// selected only by the CDC bench rtl/test/qwen_rom_runtime/realmem/tb_qwen_rt_kv_stream4_cdc.sv and
// tb_qwen_rt_kv_stream4.cpp built with -DCDC).  Same 4 x ot_hbm_r14_stream_stack controllers, same
// KV map, same picosecond DRAM checker and backing store as ot_qwen_hbm_stream4_ack.  What differs is
// the memory clock interface (results/rtl/qwen_rom_stream4_clock_plan_20261005, P0 boundary r5):
//   * the controllers run on an EXTERNAL periodic HCLK input `hclk` (1,024 ps), not on the derived
//     gated clock ~clk & tick_q (which the plan rejected: 833/1,667 ps intervals);
//   * every per-PC crossing (landing, write queue, write-done, landing credits) is the synthesizable
//     hardened element ot_qwen_stream4_cdc_pc (gray-pointer async FIFOs, registered on both sides),
//     instead of the behavioural shared rings with modelled visibility;
//   * the descriptor / GO crossing is the existing closed-loop toggle mailbox (payload held until the
//     accept toggle returns through two flops); the controller fault crosses through two flops.
// The DRAM itself (row/column timing checker, return due times = CL/CWL + BURST + RSP) stays the
// behavioural HBM3E model on the HCLK side: a returned beat is pushed into the landing FIFO on the
// HCLK edge at which it is due (the PHY's registered return), a write-done on its due edge.
// ---------------------------------------------------------------------------
module ot_qwen_hbm_stream4_cdc #(
    parameter integer NSTK      = 4,
    parameter integer NPC       = 32 * NSTK,
    parameter integer MEM_WORDS = 3 * 131072,
    parameter integer TAGW      = 9,
    parameter integer CRED      = 32,
    parameter integer PHASE     = 0,
    parameter integer PULLIN    = 0,
    parameter integer WQ        = 4,
    parameter integer WBUF      = 16,
    parameter integer PROTECTED = 0,
    parameter integer SYNC      = 2,
    parameter integer RSEL      = 0,       // ot_qwen_stream4_cdc_pc landing read select: 1 = r9 (closed route r9a)
    parameter integer RNG       = 10,
    parameter integer KV_MAP    = 0,       // 1: option-M quadrant-local stripe (ot_qwen_kv_map_m.svh)
    parameter integer CDC_MARGIN = 0,      // 1: ot_qwen_stream4_cdc_pc MARGIN (pin registers, credit landing) + the
                                           //    receiver's per-PC landing queue (LCRED words, registered credit return)
    parameter integer LCRED     = 6,
    parameter integer CDC_NEG   = 0        // negative control only: MARGIN element without the receiver queue
) (
    input  wire                 clk,
    input  wire                 rst_n, // cold POR only
    input  wire                 warm_rst_n, // protected path: admission pause, never erase debt
    input  wire                 hclk,          // external periodic controller clock (1,024 ps)
    input  wire                 d_v,
    output wire                 d_rdy,
    input  wire [18:0]          d_row,
    input  wire [10:0]          d_n,
    input  wire                 go,
    output wire [NPC-1:0]       l_v,
    output wire [NPC*17-1:0]    l_sec,
    output wire [NPC*8-1:0]     l_row,
    output wire [NPC*256-1:0]   l_data,
    input  wire [NPC-1:0]       l_pop,
    input  wire [NPC-1:0]       w_v,
    input  wire [NPC*24-1:0]    w_sec,
    input  wire [NPC*256-1:0]   w_data,
    input  wire [NPC*TAGW-1:0]  w_tag,
    output wire [NPC-1:0]       w_room,
    output wire [NPC-1:0]       wd_v,
    output wire [NPC*TAGW-1:0]  wd_tag,
    output wire                 fault,
    output reg  [15:0]          fault_code
);
    reg fault_raw;
    assign fault = fault_raw | (PROTECTED && protected_cf);
    localparam integer LR = 64;
    localparam integer CYC = 1024;
    localparam longint BURST=1024, TCCDL=2560, CL=12500, CWL=6250, RCD=19375, RCDW=9375, RP=16250, RAS=28125,
                       RTP=5625, WR=20625, WTRS=4375, WTRL=6250, RTW=9948, RRDS=2500, RRDL=3125, FAW=15000,
                       RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;

    reg [255:0] mem [0:MEM_WORDS-1] /*verilator public_flat_rw*/;

`include "ot_qwen_kv_map_m.svh"
    function automatic [16:0] p2l(input integer port, input [4:0] bk, input [4:0] cl);
        reg [9:0] j; reg [4:0] q; reg [1:0] k;
        begin
            j = {bk[4:2], cl, bk[1:0]}; q = 5'(port % 32); k = 2'(port / 32);
            p2l = (KV_MAP != 0) ? m_p2l(port, j) : {j[0], q[4], j[9:1], q[3:0], k};
        end
    endfunction
    function automatic integer l2port(input [16:0] l);
        l2port = (KV_MAP != 0) ? m_l2port(l) : integer'(l[1:0]) * 32 + integer'({l[15], l[5:2]});
    endfunction
    function automatic [9:0] l2j(input [16:0] l);
        l2j = (KV_MAP != 0) ? m_l2j(l) : {l[14:6], l[16]};
    endfunction
    function automatic [4:0] l2bank(input [16:0] l);
        reg [9:0] j; begin j = l2j(l); l2bank = {j[9:7], j[1:0]}; end
    endfunction
    function automatic [4:0] l2col(input [16:0] l);
        reg [9:0] j; begin j = l2j(l); l2col = j[6:2]; end
    endfunction
    // per-stack descriptor n (option M: the stacks' windows differ for P < 8191)
    function automatic [10:0] nstk(input integer sk, input [10:0] n);
        nstk = (KV_MAP != 0) ? m_n(sk, n) : n;
    endfunction

    // ---- per-domain reset release of the common reset epoch ----
    wire c_rst_n, h_rst_n;
    ot_reset_sync u_crst (.clk(clk),  .async_rst_n(rst_n), .sync_rst_n(c_rst_n));
    ot_reset_sync u_hrst (.clk(hclk), .async_rst_n(rst_n), .sync_rst_n(h_rst_n));

    // ---- the streaming controllers, on HCLK ----
    reg  desc_v_q, go_q; reg [18:0] dq_row; reg [10:0] dq_n;
    wire [NSTK-1:0] desc_rk, sfault_k, busy_k;
    wire desc_r = &desc_rk, sfault = |sfault_k, busy_all = &busy_k;
    wire protected_dv,protected_go,protected_cf,protected_hf,protected_ready;
    wire [18:0] protected_row;wire [10:0] protected_n;
    if(PROTECTED)begin:protected_front
        ot_qwen_s4_protected_control #(.MEM_ROWS(MEM_WORDS/131072)) u_control(.clk(clk),.hclk(hclk),.por_n(rst_n),.warm_rst_n(warm_rst_n),
            .d_v(d_v),.d_rdy(protected_ready),.d_row(d_row),.d_n(d_n),.go(go),
            .desc_v(protected_dv),.desc_r(desc_r),.desc_row(protected_row),.desc_n(protected_n),
            .busy_all(busy_all),.h_go(protected_go),
            .c_external_fault(|c_fault_p),.h_external_fault(h_fault|sfault|(|h_fault_p)),.c_fault(protected_cf),.h_fault(protected_hf));
    end else begin:raw_front
        assign {protected_dv,protected_go,protected_cf,protected_hf,protected_ready}=5'b0;
        assign protected_row=0;assign protected_n=0;
    end
    wire [NPC-1:0] row_v, col_v, col_we, busy, wr_r;
    wire [NPC*3-1:0] row_op; wire [NPC*5-1:0] row_bank, col_bank, col_col; wire [NPC*19-1:0] row_row;
    wire [NPC*3-1:0] cred_ret;
    wire [NPC-1:0] wr_v; wire [NPC*5-1:0] wr_bank, wr_col; wire [NPC*24-1:0] wr_sec;
    for (genvar sk = 0; sk < NSTK; sk = sk + 1) begin : stk
        ot_hbm_r14_stream_stack #(.ENABLE(1), .REF_MODE(1), .CRED(CRED), .PHASE(PHASE), .WR_EN(1), .WQ(WQ), .PULLIN(PULLIN)) u_ctl (
            .clk(hclk), .rst_n(h_rst_n), .desc_v((PROTECTED?protected_dv:desc_v_q) && desc_r), .desc_r(desc_rk[sk]), .desc_row(PROTECTED?protected_row:dq_row), .desc_n(nstk(sk, PROTECTED?protected_n:dq_n)),
            .go(PROTECTED?protected_go:go_q), .next_posted(1'b0), .row_v(row_v[sk*32 +: 32]), .row_op(row_op[sk*96 +: 96]),
            .row_bank(row_bank[sk*160 +: 160]), .row_row(row_row[sk*608 +: 608]),
            .col_v(col_v[sk*32 +: 32]), .col_bank(col_bank[sk*160 +: 160]), .col_col(col_col[sk*160 +: 160]),
            .cred_ret(cred_ret[sk*96 +: 96]), .busy(busy[sk*32 +: 32]), .fault(sfault_k[sk]),
            .wr_v(wr_v[sk*32 +: 32]), .wr_bank(wr_bank[sk*160 +: 160]), .wr_col(wr_col[sk*160 +: 160]),
            .wr_r(wr_r[sk*32 +: 32]), .col_we(col_we[sk*32 +: 32]));
        assign busy_k[sk] = busy[sk*32];
    end

    // ---- the per-PC clock interface (hardened element x NPC) ----
    reg  [NPC-1:0] lp_v, ap_v;                       // HCLK: landing / write-done pushes (registered)
    reg  [16:0] lp_sec [0:NPC-1]; reg [7:0] lp_row [0:NPC-1]; reg [255:0] lp_dat [0:NPC-1]; reg [TAGW-1:0] ap_tag [0:NPC-1];
    wire [NPC-1:0] c_fault_p, h_fault_p, h_cv;
    wire [NPC*24-1:0] h_csec; wire [NPC*256-1:0] h_cdata; wire [NPC*TAGW-1:0] h_ctag;
    wire [NPC-1:0] h_wcon = col_v & col_we;
    for (genvar q = 0; q < NPC; q = q + 1) begin : pc
        if(PROTECTED)begin:protected_path
        ot_qwen_s4_protected_pc #(.MEM_WORDS(MEM_WORDS), .PC_ID(q), .TAGW(TAGW), .LD(LR), .WB(WBUF), .AD(LR), .SYNC(SYNC)) u_cdc (
            .clk(clk), .por_n(rst_n), .warm_rst_n(warm_rst_n),
            .l_v(l_v[q]), .l_sec(l_sec[q*17 +: 17]), .l_row(l_row[q*8 +: 8]), .l_data(l_data[q*256 +: 256]), .l_pop(l_pop[q]),
            .w_v(w_v[q]), .w_sec(w_sec[q*24 +: 24]), .w_data(w_data[q*256 +: 256]), .w_tag(w_tag[q*TAGW +: TAGW]),
            .w_room(w_room[q]), .wd_v(wd_v[q]), .wd_tag(wd_tag[q*TAGW +: TAGW]), .c_fault(c_fault_p[q]),
            .hclk(hclk),
            .h_lv(lp_v[q]), .h_lsec(lp_sec[q]), .h_lrow(lp_row[q]), .h_ldata(lp_dat[q]), .h_cred(cred_ret[q*3 +: 3]),
            .h_wv(wr_v[q]), .h_wsec(wr_sec[q*24 +: 24]), .h_hand(wr_v[q] && wr_r[q]), .h_wcon(h_wcon[q]),
            .h_cv(h_cv[q]), .h_csec(h_csec[q*24 +: 24]), .h_cdata(h_cdata[q*256 +: 256]), .h_ctag(h_ctag[q*TAGW +: TAGW]),
            .h_av(ap_v[q]), .h_atag(ap_tag[q]), .h_fault(h_fault_p[q]));
        end else begin:raw_path
        // landing as the element presents it (MARGIN: one-cycle pushes) and the credit it gets back
        wire e_lv, e_cr; wire [16:0] e_sec; wire [7:0] e_row; wire [255:0] e_dat;
        if (CDC_MARGIN != 0 && CDC_NEG == 0) begin : g_rx
            // the receiver's landing queue (physically the landing crossbar's per-PC port, die qfd_kvc): LCRED words,
            // the service's l_v / l_pop interface on its head, one registered credit per consumed word
            reg [280:0] rq [0:LCRED-1];
            reg [$clog2(LCRED):0] rn; reg [$clog2(LCRED)-1:0] rh, rt; reg cr;
            wire take = rn != 0 && l_pop[q];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin rn <= 0; rh <= 0; rt <= 0; cr <= 1'b0; end
                else begin
                    if (e_lv) begin rq[rt] <= {e_sec, e_row, e_dat}; rt <= (rt == LCRED-1) ? 0 : rt + 1'b1; end
                    if (take) rh <= (rh == LCRED-1) ? 0 : rh + 1'b1;
                    rn <= rn + e_lv - take;
                    cr <= take;
                    if (e_lv && rn == LCRED && !take) $error("CDC_MARGIN landing queue overflow PC %0d", q);
                end
            assign l_v[q] = rn != 0;
            assign {l_sec[q*17 +: 17], l_row[q*8 +: 8], l_data[q*256 +: 256]} = rq[rh];
            assign e_cr = cr;
        end else begin : g_direct
            assign l_v[q] = e_lv;
            assign {l_sec[q*17 +: 17], l_row[q*8 +: 8], l_data[q*256 +: 256]} = {e_sec, e_row, e_dat};
            assign e_cr = l_pop[q];
        end
        ot_qwen_stream4_cdc_pc #(.TAGW(TAGW), .LD(LR), .WB(WBUF), .AD(LR), .SYNC(SYNC), .RSEL(RSEL), .RNG(RNG),
                                 .MARGIN(CDC_MARGIN), .LCRED(LCRED)) u_cdc (
            .clk(clk), .c_arst_n(rst_n),
            .l_v(e_lv), .l_sec(e_sec), .l_row(e_row), .l_data(e_dat), .l_pop(e_cr),
            .w_v(w_v[q]), .w_sec(w_sec[q*24 +: 24]), .w_data(w_data[q*256 +: 256]), .w_tag(w_tag[q*TAGW +: TAGW]),
            .w_room(w_room[q]), .wd_v(wd_v[q]), .wd_tag(wd_tag[q*TAGW +: TAGW]), .c_fault(c_fault_p[q]),
            .hclk(hclk), .h_arst_n(rst_n),
            .h_lv(lp_v[q]), .h_lsec(lp_sec[q]), .h_lrow(lp_row[q]), .h_ldata(lp_dat[q]), .h_cred(cred_ret[q*3 +: 3]),
            .h_wv(wr_v[q]), .h_wsec(wr_sec[q*24 +: 24]), .h_hand(wr_v[q] && wr_r[q]), .h_wcon(h_wcon[q]),
            .h_cv(h_cv[q]), .h_csec(h_csec[q*24 +: 24]), .h_cdata(h_cdata[q*256 +: 256]), .h_ctag(h_ctag[q*TAGW +: TAGW]),
            .h_av(ap_v[q]), .h_atag(ap_tag[q]), .h_fault(h_fault_p[q]));
        end
        assign wr_bank[q*5 +: 5] = l2bank(wr_sec[q*24 +: 17]);
        assign wr_col[q*5 +: 5]  = l2col(wr_sec[q*24 +: 17]);
    end

    // ---- core domain: descriptor / GO toggles, faults ----
    longint ccyc;
    longint hcyc;
    reg d_tog, g_tog, a_tog;
    reg [18:0] d_row_c; reg [10:0] d_n_c;
    reg h_fault; reg [15:0] h_code;
    reg a1, a2, a_seen, d_pend, dr1, dr2, hf1, hf2;
    integer p;
    always @(posedge clk or negedge c_rst_n) begin
        if (!c_rst_n) begin
            ccyc <= 0; d_tog <= 0; g_tog <= 0; a1 <= 0; a2 <= 0; a_seen <= 0; d_pend <= 0; dr1 <= 0; dr2 <= 0;
            hf1 <= 0; hf2 <= 0; fault_raw <= 0; fault_code <= 0;
        end else begin
            ccyc <= ccyc + 1;
            a1 <= a_tog; a2 <= a1; dr1 <= desc_r; dr2 <= dr1; hf1 <= h_fault; hf2 <= hf1;
            if (a2 != a_seen) begin a_seen <= a2; d_pend <= 1'b0; end
            if (!PROTECTED && d_v) begin
                if (!d_rdy) begin fault_raw <= 1'b1; fault_code[0] <= 1'b1; end
                d_row_c <= d_row; d_n_c <= d_n; d_tog <= ~d_tog; d_pend <= 1'b1;
            end
            if (!PROTECTED && go) g_tog <= ~g_tog;
            if(PROTECTED && protected_cf) begin fault_raw<=1;fault_code[4]<=1;end
            for (p = 0; p < NPC; p = p + 1) begin
                if (l_pop[p] && !l_v[p]) begin fault_raw <= 1'b1; fault_code[1] <= 1'b1; end
                if (w_v[p] && l2port(w_sec[p*24 +: 17]) != p) begin fault_raw <= 1'b1; fault_code[3] <= 1'b1; end
            end
            if (|c_fault_p) begin fault_raw <= 1'b1; fault_code[3] <= 1'b1; end
            if (hf2) begin fault_raw <= 1'b1; fault_code <= fault_code | h_code; end
        end
    end
    assign d_rdy = PROTECTED ? protected_ready : (!d_pend && dr2);

    // ---- controller domain: mailbox, DRAM checker, returns ----
    reg d1, d2, d_seen, g1, g2, g_seen, go_req;
    longint now;
    bit     b_open [0:NPC-1][0:31]; int b_row [0:NPC-1][0:31];
    longint b_act [0:NPC-1][0:31], b_pre [0:NPC-1][0:31], b_rd [0:NPC-1][0:31], b_wr [0:NPC-1][0:31], b_ref_end [0:NPC-1][0:31];
    longint p_ref0 [0:NPC-1], p_nref [0:NPC-1];
    longint p_last_act [0:NPC-1], p_last_rd [0:NPC-1], p_last_wr [0:NPC-1], p_last_col [0:NPC-1], p_last_ref [0:NPC-1], p_last_refpb_any [0:NPC-1];
    int     p_wr_bg [0:NPC-1];
    longint p_act_bg [0:NPC-1][0:3], p_col_bg [0:NPC-1][0:3], p_faw [0:NPC-1][0:3];
    bit [31:0] p_round [0:NPC-1];
    longint viol /*verilator public_flat_rw*/, n_act /*verilator public_flat_rw*/, n_rd /*verilator public_flat_rw*/,
            n_wr /*verilator public_flat_rw*/, n_ref /*verilator public_flat_rw*/, n_pre, max_land /*verilator public_flat_rw*/;
    longint rq_due [0:NPC-1][0:LR-1]; reg [255:0] rq_dat [0:NPC-1][0:LR-1]; reg [16:0] rq_sec [0:NPC-1][0:LR-1];
    reg [7:0] rq_row [0:NPC-1][0:LR-1];
    integer rq_w [0:NPC-1], rq_r [0:NPC-1];
    longint aq_due [0:NPC-1][0:LR-1]; reg [TAGW-1:0] aq_tag [0:NPC-1][0:LR-1];
    integer aq_w [0:NPC-1], aq_r [0:NPC-1];
    longint lpend [0:NPC-1];                         // landing entries pushed and not yet credited back
    // a WR column command of the previous edge: its captured queue entry arrives now (h_cv)
    reg [NPC-1:0] wc_pend; longint wc_addr [0:NPC-1], wc_now [0:NPC-1]; int wc_bank [0:NPC-1];
    task automatic v(input string what, input integer pc, input integer bk);
        if (viol < 20) $display("HBM_STREAM VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
        viol++;
        h_fault <= 1'b1; h_code[8] <= 1'b1;
    endtask

    integer q, b, gg, k;
    bit trace = 1'b0;
    initial trace = $test$plusargs("hbm_trace");
    always @(posedge hclk or negedge h_rst_n) begin
        if (!h_rst_n) begin
            hcyc = 0; d1 <= 0; d2 <= 0; d_seen <= 0; g1 <= 0; g2 <= 0; g_seen <= 0; go_req <= 0; a_tog <= 0;
            desc_v_q <= 0; go_q <= 0; h_fault <= 0; h_code <= 0; lp_v <= 0; ap_v <= 0; wc_pend = 0;
            viol = 0; n_act = 0; n_rd = 0; n_wr = 0; n_ref = 0; n_pre = 0; max_land = 0;
            for (q = 0; q < NPC; q = q + 1) begin
                rq_w[q] = 0; rq_r[q] = 0; aq_w[q] = 0; aq_r[q] = 0; lpend[q] = 0;
                p_last_act[q] = -1000000; p_last_rd[q] = -1000000; p_last_wr[q] = -1000000; p_last_col[q] = -1000000;
                p_last_refpb_any[q] = -1000000; p_round[q] = 0; p_wr_bg[q] = 0;
                begin : ph
                    automatic int P = 118;
                    automatic int base = (PHASE + ((q % 32) * P) / 32) % P;
                    p_last_ref[q] = longint'(base + ((base + P + (q % 32)) % 2)) * CYC;
                    p_ref0[q] = p_last_ref[q]; p_nref[q] = 0;
                end
                for (gg = 0; gg < 4; gg = gg + 1) begin p_act_bg[q][gg] = -1000000; p_col_bg[q][gg] = -1000000; p_faw[q][gg] = -1000000; end
                for (b = 0; b < 32; b = b + 1) begin
                    b_open[q][b] = 0; b_act[q][b] = -1000000; b_pre[q][b] = -1000000; b_rd[q][b] = -1000000;
                    b_wr[q][b] = -1000000; b_ref_end[q][b] = 0; b_row[q][b] = 0;
                end
            end
        end else begin
            now = hcyc * CYC;
            d1 <= d_tog; d2 <= d1; g1 <= g_tog; g2 <= g1;
            if (desc_v_q && desc_r) begin desc_v_q <= 1'b0; a_tog <= ~a_tog; end
            else if (!desc_v_q && d2 != d_seen) begin desc_v_q <= 1'b1; d_seen <= d2; dq_row <= d_row_c; dq_n <= d_n_c; end
            if (g2 != g_seen) begin g_seen <= g2; go_req <= 1'b1; end
            go_q <= 1'b0;
            if ((go_req || g2 != g_seen) && busy_all && !go_q) begin go_q <= 1'b1; go_req <= 1'b0; end
            if (sfault) begin h_fault <= 1'b1; h_code[9] <= 1'b1; end
            if (PROTECTED && protected_hf) begin h_fault<=1;h_code[4]<=1;end
            if (|h_fault_p) begin h_fault <= 1'b1; h_code[2] <= 1'b1; end
            // the WR commands of the previous edge: write the captured entry to the array
            for (q = 0; q < NPC; q = q + 1) if (wc_pend[q]) begin
                if (!h_cv[q] || h_csec[q*24 +: 24] != 24'(wc_addr[q])) begin
                    now = wc_now[q]; v("WR does not match the oldest queued write", q, wc_bank[q]); now = hcyc * CYC;
                end else begin
                    mem[wc_addr[q]] = h_cdata[q*256 +: 256];
                    gg = aq_w[q] % LR;
                    aq_due[q][gg] = (wc_now[q] + CWL + BURST + RSP + CYC - 1) / CYC;
                    aq_tag[q][gg] = h_ctag[q*TAGW +: TAGW];
                    aq_w[q] = aq_w[q] + 1;
                end
            end
            wc_pend = 0;
            for (q = 0; q < NPC; q = q + 1) begin
                if (row_v[q]) begin
                    automatic int op = row_op[q*3 +: 3], bk = row_bank[q*5 +: 5], rw = row_row[q*19 +: 19], g = bk & 3;
                    case (op)
                        1: begin // ACT
                            n_act++;
                            if (trace) $display("HBMTRACE ACT h=%0d pc=%0d bank=%0d", hcyc, q, bk);
                            if (b_open[q][bk]) v("ACT to open bank", q, bk);
                            if (now < b_pre[q][bk] + RP) v("tRP", q, bk);
                            if (now < b_act[q][bk] + RAS + RP) v("tRC", q, bk);
                            if (now < p_last_act[q] + RRDS) v("tRRD_S", q, bk);
                            if (now < p_act_bg[q][g] + RRDL) v("tRRD_L", q, bk);
                            if (now < p_faw[q][0] + FAW) v("tFAW", q, bk);
                            if (now < b_ref_end[q][bk]) v("ACT during refresh", q, bk);
                            if (now < p_last_refpb_any[q] + RREFD) v("tRREFD", q, bk);
                            b_open[q][bk] = 1; b_row[q][bk] = rw; b_act[q][bk] = now;
                            p_last_act[q] = now; p_act_bg[q][g] = now;
                            p_faw[q][0] = p_faw[q][1]; p_faw[q][1] = p_faw[q][2]; p_faw[q][2] = p_faw[q][3]; p_faw[q][3] = now;
                        end
                        0: begin // PRE
                            n_pre++;
                            if (!b_open[q][bk]) v("PRE closed bank", q, bk);
                            if (now < b_act[q][bk] + RAS) v("tRAS", q, bk);
                            if (now < b_rd[q][bk] + RTP) v("tRTP", q, bk);
                            if (now < b_wr[q][bk] + CWL + BURST + WR) v("tWR", q, bk);
                            b_open[q][bk] = 0; b_pre[q][bk] = now;
                        end
                        6: begin // REFpb
                            n_ref++;
                            if (trace) $display("HBMTRACE REF h=%0d pc=%0d bank=%0d", hcyc, q, bk);
                            if (b_open[q][bk]) v("REFpb to open bank", q, bk);
                            if (now < b_pre[q][bk] + RP) v("tRP (REFpb)", q, bk);
                            if (now < b_act[q][bk] + RAS + RP) v("tRC (REFpb)", q, bk);
                            if (now < b_ref_end[q][bk]) v("REFpb during refresh", q, bk);
                            if (now < p_last_act[q] + RREFD) v("tRREFD (REFpb after ACT)", q, bk);
                            if (now < p_last_refpb_any[q] + RREFD) v("tRREFD (REFpb after REFpb)", q, bk);
                            if (p_round[q][bk]) v("REFpb bank twice in one round", q, bk);
                            p_round[q][bk] = 1; if (&p_round[q]) p_round[q] = 0;
                            if (PULLIN == 0) begin
                                if (now - p_last_ref[q] > REFI / 32) v("REFpb late", q, bk);
                                p_last_ref[q] = now;
                            end else begin
                                //: pull-in: the k-th REFpb is due by origin + k * tREFI/32 and may come at most PULLIN
                                //: controller periods (118 cycles) before the controller's own schedule
                                p_nref[q]++;
                                if (now > p_ref0[q] + p_nref[q] * (REFI / 32)) v("REFpb late", q, bk);
                                if (now < p_ref0[q] + (p_nref[q] - PULLIN) * 118 * CYC - 2 * CYC) v("REFpb pulled in too far", q, bk);
                            end
                            p_last_refpb_any[q] = now;
                            b_ref_end[q][bk] = now + RFCPB;
                        end
                        default: v("row op not used by this controller", q, bk);
                    endcase
                end
                if (PULLIN == 0 && now - p_last_ref[q] > REFI / 32) begin v("refresh overdue", q, 0); p_last_ref[q] = now; end
                if (PULLIN != 0 && now > p_ref0[q] + (p_nref[q] + 1) * (REFI / 32)) begin v("refresh overdue", q, 0); p_nref[q]++; end
                if (col_v[q]) begin
                    automatic int bk = col_bank[q*5 +: 5], cl = col_col[q*5 +: 5], g = bk & 3;
                    automatic logic [16:0] ls = p2l(q, 5'(bk), 5'(cl));
                    automatic longint a = longint'(b_row[q][bk]) * 131072 + ls;
                    if (!b_open[q][bk]) v(col_we[q] ? "WR closed bank" : "RD closed bank", q, bk);
                    if (now < b_act[q][bk] + (col_we[q] ? RCDW : RCD)) v("tRCD", q, bk);
                    if (now < p_last_col[q] + BURST) v("tCCD_S", q, bk);
                    if (now < p_col_bg[q][g] + TCCDL) v("tCCD_L", q, bk);
                    if (now < b_ref_end[q][bk]) v("column command during refresh", q, bk);
                    if (b_row[q][bk] * 131072 >= MEM_WORDS) v("row beyond the backing store", q, bk);
                    p_last_col[q] = now; p_col_bg[q][g] = now;
                    if (!col_we[q]) begin
                        if (now < p_last_wr[q] + CWL + BURST + ((p_wr_bg[q] == g) ? WTRL : WTRS)) v("tWTR", q, bk);
                        n_rd++;
                        p_last_rd[q] = now; b_rd[q][bk] = now;
                        k = rq_w[q] % LR;
                        rq_due[q][k] = (now + CL + BURST + RSP + CYC - 1) / CYC;
                        rq_dat[q][k] = (a < MEM_WORDS) ? mem[a] : 256'd0;
                        rq_sec[q][k] = ls; rq_row[q][k] = 8'(b_row[q][bk]);
                        rq_w[q] = rq_w[q] + 1;
                    end else begin
                        if (now < p_last_rd[q] + RTW) v("tRTW", q, bk);
                        n_wr++;
                        p_last_wr[q] = now; p_wr_bg[q] = g; b_wr[q][bk] = now;
                        if (trace) $display("HBMTRACE WR h=%0d pc=%0d bank=%0d sec=%0d", hcyc, q, bk, a);
                        wc_pend[q] = 1'b1; wc_addr[q] = a; wc_now[q] = now; wc_bank[q] = bk;
                    end
                end
            end
            for (gg = 0; gg < NPC / 2; gg = gg + 1) if (row_v[2*gg] && row_v[2*gg+1]) v("two row commands on one channel slot", 2*gg, 0);
            // returns: the beat due at the NEXT edge is presented now and pushed into the landing FIFO at that edge
            for (q = 0; q < NPC; q = q + 1) begin
                lpend[q] = lpend[q] - longint'(cred_ret[q*3 +: 3]);
                if (rq_r[q] != rq_w[q] && rq_due[q][rq_r[q] % LR] <= hcyc + 1) begin
                    k = rq_r[q] % LR;
                    lp_v[q] <= 1'b1; lp_dat[q] <= rq_dat[q][k]; lp_sec[q] <= rq_sec[q][k]; lp_row[q] <= rq_row[q][k];
                    rq_r[q] = rq_r[q] + 1; lpend[q] = lpend[q] + 1;
                    if (lpend[q] > max_land) max_land = lpend[q];
                end else lp_v[q] <= 1'b0;
                if (aq_r[q] != aq_w[q] && aq_due[q][aq_r[q] % LR] <= hcyc + 1) begin
                    k = aq_r[q] % LR;
                    ap_v[q] <= 1'b1; ap_tag[q] <= aq_tag[q][k];
                    aq_r[q] = aq_r[q] + 1;
                end else ap_v[q] <= 1'b0;
            end
            hcyc = hcyc + 1;
        end
    end
endmodule

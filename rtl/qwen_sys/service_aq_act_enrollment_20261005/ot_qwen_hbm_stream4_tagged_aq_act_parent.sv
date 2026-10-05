`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION MODEL (default-off, additive): ot_qwen_hbm_stream4_ack (left byte-identical) plus a
// TAGGED NEAR-ROW READ PORT served by the SAME 128 pseudo-channel controllers and the SAME
// backing array `mem` as the descriptor stream.  Selected by the combined STREAM4 die runtime
// through qwen_stream4_wire_native_tagged_rows(Vdie&, Vhbm&) (tools/runtime/qwen_combined/
// stream4_tagged_rows_hook.cpp), which wires the die's protected hclk row boundary to the t_*
// pins below, the clock and reset included (combinational pin wiring only).
//
// Tagged port (clock t_clk / reset t_rst_n: the die's hclk / hrst_n; the contract of
// ot_qwen_hbm_model_ack PC_RDY = 1, as the row clients ot_qwen_nearhbm_row_sectors use it):
//   requests, 4 clients s (the die's per-stack row engines): t_req_v/t_req_ready/t_req_we [4],
//     t_req_addr 4 x 24 (ABSOLUTE logical sector: layer * 2^17 + layer-relative), t_req_len 4 x 5
//     (1 .. 16 sectors, consecutive), t_req_tag 4 x 13 (opaque, returned on every beat),
//     t_req_wdata 4 x 256.  READ-ONLY: t_req_we = 1 faults (code bit 11) and is dropped.
//   responses, 128 ports = client s * 32 + pc(a), pc(a) = ((a>>2)^(a>>7)^(a>>12)) & 31 (the clients'
//     own pseudo-channel hash, so their advisory room check names the port that returns):
//     t_rsp_v/t_rsp_ready/t_rsp_wr [128], t_rsp_tag 128 x 13, t_rsp_beat 128 x 4 (sector index in the
//     burst), t_rsp_data 128 x 256; t_pc_room [128] = the port can take 4 more beats (advisory, one
//     synchroniser stale); beats of one port return in issue order.
// Path: t_clk request FIFO (4 deep a client) -> two-flop pointer crossing -> controller domain
// SPLITTER (one client a controller cycle, rotating; each beat a sector of the client's burst, its
// stream-map pseudo-channel l2port, bank, column; one beat per pseudo-channel a cycle, in order; the
// response slot is reserved first) -> the pseudo-channel's ACCESS QUEUE in ot_hbm_r14_stream_pc
// (AQ_RD = 1, the write-back queue: token write-backs and tagged reads issue in arrival order, write
// hand-off first) -> the RD column command (col_aq) reads `mem` at issue, the DRAM checker applies
// every timing rule -> response ring of the port, visible CL + burst + RSP later -> two-flop pointer
// crossing -> t_clk response presentation.  Visibility contract: tagged reads wait while no
// descriptor is current (before the first, or while the next is being posted); a read of layer L
// is served while L is the controllers' current descriptor row (fault code bit 12 otherwise);
// write-backs handed off earlier are visible to it (queue order).  Arbitration
// (ot_hbm_r14_stream_pc AQ_RD): tagged reads are background to the stream, with a starvation bound.
// (Header of ot_qwen_hbm_stream4_ack follows.)
// ---------------------------------------------------------------------------
// SIMULATION MODEL (default-off; selected only by the 4-stack HBM_STREAM REAL_MEM die
// rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv).  NSTK HBM3E stacks (32 pseudo-
// channels each, NPC = 32 * NSTK landing/write ports) behind NSTK near-HBM STREAMING controllers
// ot_hbm_r14_stream_stack (RTL, WR_EN = 1), for ot_qwen_rt_kv_stream4_service.  Successor of
// ot_qwen_hbm_stream_ack (one stack; left byte-identical): the clock, crossings, DRAM checker,
// landing FIFOs, write buffers and write-done are that module's, per pseudo-channel, for all
// NSTK * 32 pseudo-channels.  What differs is the KV MAP, striped across the stacks so that every
// stack, pseudo-channel and bank streams an equal share of every 16-position tile, in the order
// attention consumes it:
//   window of layer n = DRAM row n of every bank of every PC of every stack (positions < 8192:
//   4 MiB = 4 x 1 MiB);  layer-relative logical sector (ot_qwen_rt_kv_fill_service LAYOUT)
//     lsec = {r[7], r[6], g[8:0], r[5:0]}   g = 16-position tile, r < 128: K of head r[6], dim
//     pair r[5:0]; r >= 128: V of head r[6], position g*16 + r[5:2], dim pair r[1:0];
//   stack k = r[1:0], pseudo-channel q = r[6:2], PC-local stream index j = {g[8:0], r[7]}
//   (BG = j[1:0], column = j[6:2], bank set = j[9:7], bank = {set, BG}: the controller's walk).
// So the window of position P is the stream prefix of 2 * (P/16 + 1) sectors per PC in EVERY
// stack: one descriptor (row, n) broadcast to the NSTK controllers, all PCs equal.
// The backing store `mem` keeps the LOGICAL layout (layer n at sector n * 2^17, public), as
// ot_qwen_hbm_model_ack / ot_qwen_hbm_stream_ack, so the host preload and token check are unchanged.
// The descriptor is accepted when every stack is ready; go goes to every stack.  All stacks
// share the controller clock and REFpb phase (independent stacks; the checker is per PC).
// ---------------------------------------------------------------------------
module ot_qwen_hbm_stream4_tagged_aq_act_parent #(
    parameter integer AQ_ACT_CUT = 0,
    parameter integer NSTK      = 4,
    parameter integer NPC       = 32 * NSTK,
    parameter integer MEM_WORDS = 3 * 131072,
    parameter integer TAGW      = 9,
    parameter integer CRED      = 32,
    parameter integer PHASE     = 0,
    parameter integer PULLIN    = 16,          // controller refresh pull-in (ot_hbm_r14_stream_pc PULLIN)
    parameter integer TTAGW     = 13,          // tagged port: tag bits
    parameter integer TRQ       = 4,           // tagged port: request FIFO a client
    parameter integer TRR       = 32,          // tagged port: response ring a port (power of two)
    parameter integer WQ        = 4,
    parameter integer WBUF      = 16,          // power of two
    parameter integer CORE_FS   = 833333,      // core clock period (fs): 1.2 GHz
    parameter integer CTL_FS    = 1024000      // controller clock period (fs): HBM CK/2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // descriptor (notice) and go, core domain
    input  wire                 d_v,
    output wire                 d_rdy,
    input  wire [18:0]          d_row,
    input  wire [10:0]          d_n,
    input  wire                 go,
    // landing, core domain
    output reg  [NPC-1:0]       l_v,
    output reg  [NPC*17-1:0]    l_sec,
    output reg  [NPC*8-1:0]     l_row,
    output reg  [NPC*256-1:0]   l_data,
    input  wire [NPC-1:0]       l_pop,
    // writes, core domain
    input  wire [NPC-1:0]       w_v,
    input  wire [NPC*24-1:0]    w_sec,
    input  wire [NPC*256-1:0]   w_data,
    input  wire [NPC*TAGW-1:0]  w_tag,
    output reg  [NPC-1:0]       w_room,
    output reg  [NPC-1:0]       wd_v,
    output reg  [NPC*TAGW-1:0]  wd_tag,
    output reg                  fault,
    output reg  [15:0]          fault_code,
    // tagged near-row read port (t_clk domain)
    input  wire                 t_clk,
    input  wire                 t_rst_n,
    input  wire [3:0]           t_req_v,
    output reg  [3:0]           t_req_ready,
    input  wire [3:0]           t_req_we,
    input  wire [95:0]          t_req_addr,
    input  wire [19:0]          t_req_len,
    input  wire [4*TTAGW-1:0]   t_req_tag,
    input  wire [1023:0]        t_req_wdata,
    output reg  [NPC-1:0]       t_pc_room,
    output reg  [NPC-1:0]       t_rsp_v,
    input  wire [NPC-1:0]       t_rsp_ready,
    output reg  [NPC-1:0]       t_rsp_wr,
    output reg  [NPC*TTAGW-1:0] t_rsp_tag,
    output reg  [NPC*4-1:0]     t_rsp_beat,
    output reg  [NPC*256-1:0]   t_rsp_data,
    output reg  [31:0]          t_rd_sectors      // tagged sectors returned (t_clk domain)
);
    localparam integer LR = 64;                  // return / landing ring depth (> CRED)
    localparam integer CYC = 1024;               // ps per controller cycle
    localparam longint BURST=1024, TCCDL=2560, CL=12500, CWL=6250, RCD=19375, RCDW=9375, RP=16250, RAS=28125,
                       RTP=5625, WR=20625, WTRS=4375, WTRL=6250, RTW=9948, RRDS=2500, RRDL=3125, FAW=15000,
                       RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;

    // backing store, LOGICAL sector layout (as ot_qwen_hbm_model_ack); public for the host preload
    reg [255:0] mem [0:MEM_WORDS-1] /*verilator public_flat_rw*/;

    // (stack k, PC q, bank, column) -> layer-relative logical sector
    function automatic [16:0] p2l(input integer port, input [4:0] bk, input [4:0] cl);
        reg [9:0] j; reg [4:0] q; reg [1:0] k;
        begin
            j = {bk[4:2], cl, bk[1:0]}; q = 5'(port % 32); k = 2'(port / 32);
            p2l = {j[0], q[4], j[9:1], q[3:0], k};
        end
    endfunction
    // logical sector -> port (k * 32 + q), bank, column
    function automatic integer l2port(input [16:0] l);
        l2port = integer'(l[1:0]) * 32 + integer'({l[15], l[5:2]});
    endfunction
    function automatic [4:0] l2bank(input [16:0] l);
        reg [9:0] j; begin j = {l[14:6], l[16]}; l2bank = {j[9:7], j[1:0]}; end
    endfunction
    function automatic [4:0] l2col(input [16:0] l);
        reg [9:0] j; begin j = {l[14:6], l[16]}; l2col = j[6:2]; end
    endfunction

    // ---- controller clock ---------------------------------------------------------------
    // free-running (also through reset, so the controller domain sees its reset on a clock edge)
    reg [31:0] acc = 0; reg tick_q = 1'b0;
    always @(posedge clk)
        if (acc + CORE_FS >= CTL_FS) begin acc <= acc + CORE_FS - CTL_FS; tick_q <= 1'b1; end
        else begin acc <= acc + CORE_FS; tick_q <= 1'b0; end
    wire hclk = ~clk & tick_q;

    // ---- the streaming controller -------------------------------------------------------
    reg  desc_v_q, go_q; reg [18:0] dq_row; reg [10:0] dq_n;
    wire [NSTK-1:0] desc_rk, sfault_k, busy_k;
    wire desc_r = &desc_rk, sfault = |sfault_k, busy_all = &busy_k;
    wire [NPC-1:0] row_v, col_v, col_we, busy, wr_r;
    wire [NPC*3-1:0] row_op; wire [NPC*5-1:0] row_bank, col_bank, col_col; wire [NPC*19-1:0] row_row;
    reg  [NPC*3-1:0] cred_ret;
    reg  [NPC-1:0] wr_v_q, wr_rd_q; reg [NPC*5-1:0] wr_bank_q, wr_col_q;
    wire [NPC-1:0] col_aq;
    for (genvar sk = 0; sk < NSTK; sk = sk + 1) begin : stk
        ot_qwen_service_stack_aq_act_select #(.AQ_ACT_CUT(AQ_ACT_CUT), .ENABLE(1), .REF_MODE(1), .CRED(CRED), .PHASE(PHASE), .WR_EN(1), .WQ(WQ), .PULLIN(PULLIN),
                                  .AQ_RD(1)) u_ctl (
            .clk(hclk), .rst_n(rst_n), .desc_v(desc_v_q && desc_r), .desc_r(desc_rk[sk]), .desc_row(dq_row), .desc_n(dq_n),
            .go(go_q), .next_posted(1'b0), .row_v(row_v[sk*32 +: 32]), .row_op(row_op[sk*96 +: 96]),
            .row_bank(row_bank[sk*160 +: 160]), .row_row(row_row[sk*608 +: 608]),
            .col_v(col_v[sk*32 +: 32]), .col_bank(col_bank[sk*160 +: 160]), .col_col(col_col[sk*160 +: 160]),
            .cred_ret(cred_ret[sk*96 +: 96]), .busy(busy[sk*32 +: 32]), .fault(sfault_k[sk]),
            .wr_v(wr_v_q[sk*32 +: 32]), .wr_bank(wr_bank_q[sk*160 +: 160]), .wr_col(wr_col_q[sk*160 +: 160]),
            .wr_r(wr_r[sk*32 +: 32]), .col_we(col_we[sk*32 +: 32]),
            .wr_rd(wr_rd_q[sk*32 +: 32]), .col_aq(col_aq[sk*32 +: 32]));
        assign busy_k[sk] = busy[sk*32];
    end

    // ---- shared state (each variable written by ONE clock domain) ---------------------------
    longint ccyc;                       // core cycles (core domain)
    longint hcyc;                       // controller cycles (controller domain)
    // landing ring (written: controller domain; read pointer: core domain)
    reg [255:0] ld_data [0:NPC-1][0:LR-1];
    reg [16:0]  ld_sec  [0:NPC-1][0:LR-1];
    reg [7:0]   ld_row  [0:NPC-1][0:LR-1];
    longint     ld_vis  [0:NPC-1][0:LR-1];
    integer     ld_w [0:NPC-1], ld_r [0:NPC-1];
    // write buffer (written: core; hand-off and completion pointers: controller)
    reg [23:0]      wb_sec  [0:NPC-1][0:WBUF-1];
    reg [255:0]     wb_data [0:NPC-1][0:WBUF-1];
    reg [TAGW-1:0]  wb_tag  [0:NPC-1][0:WBUF-1];
    longint         wb_vis  [0:NPC-1][0:WBUF-1];  // controller cycle from which it is visible there
    integer         wb_w [0:NPC-1], wb_h [0:NPC-1], wb_c [0:NPC-1];
    // write-done ring (written: controller; read pointer: core)
    reg [TAGW-1:0]  ak_tag [0:NPC-1][0:LR-1];
    longint         ak_vis [0:NPC-1][0:LR-1];
    integer         ak_w [0:NPC-1], ak_r [0:NPC-1];
    longint         pops [0:NPC-1];               // landing pops (core); its count crosses as credits
    reg d_tog, g_tog, a_tog;                       // core: descriptor / go toggles; controller: accept toggle
    reg [18:0] d_row_c; reg [10:0] d_n_c;
    reg h_fault; reg [15:0] h_code;                // controller-domain faults

    // ---- core domain ------------------------------------------------------------------------
    reg a1, a2, a_seen, d_pend, dr1, dr2;
    integer p, k;
    bit trace_c = 1'b0;
    initial trace_c = $test$plusargs("hbm_trace");
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ccyc <= 0; d_tog <= 0; g_tog <= 0; a1 <= 0; a2 <= 0; a_seen <= 0; d_pend <= 0; dr1 <= 0; dr2 <= 0;
            l_v <= 0; wd_v <= 0; w_room <= 0; fault <= 0; fault_code <= 0;
            for (p = 0; p < NPC; p = p + 1) begin ld_r[p] = 0; wb_w[p] = 0; ak_r[p] = 0; pops[p] = 0; end
        end else begin
            ccyc <= ccyc + 1;
            a1 <= a_tog; a2 <= a1; dr1 <= desc_r; dr2 <= dr1;
            if (a2 != a_seen) begin a_seen <= a2; d_pend <= 1'b0; end
            if (d_v) begin
                if (!d_rdy) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                d_row_c <= d_row; d_n_c <= d_n; d_tog <= ~d_tog; d_pend <= 1'b1;
            end
            if (go) g_tog <= ~g_tog;
            for (p = 0; p < NPC; p = p + 1) begin
                // landing: the presented head was taken?
                if (l_v[p] && l_pop[p]) begin ld_r[p] = ld_r[p] + 1; pops[p] = pops[p] + 1; end
                else if (l_pop[p]) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
                if (ld_w[p] - ld_r[p] > CRED) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
                k = ld_r[p] % LR;
                l_v[p] <= (ld_w[p] != ld_r[p]) && ld_vis[p][k] <= ccyc + 1;
                l_data[p*256 +: 256] <= ld_data[p][k]; l_sec[p*17 +: 17] <= ld_sec[p][k]; l_row[p*8 +: 8] <= ld_row[p][k];
                // write-done: presented heads are always taken
                if (wd_v[p]) ak_r[p] = ak_r[p] + 1;
                k = ak_r[p] % LR;
                wd_v[p] <= (ak_w[p] != ak_r[p]) && ak_vis[p][k] <= ccyc + 1;
                wd_tag[p*TAGW +: TAGW] <= ak_tag[p][k];
                // writes in
                if (w_v[p]) begin
                    if (trace_c) $display("HBMTRACE PUSH c=%0d pc=%0d sec=%0d", ccyc, p, w_sec[p*24 +: 24]);
                    if (wb_w[p] - wb_c[p] >= WBUF || l2port(w_sec[p*24 +: 17]) != p) begin
                        fault <= 1'b1; fault_code[3] <= 1'b1;
                    end
                    k = wb_w[p] % WBUF;
                    wb_sec[p][k] = w_sec[p*24 +: 24]; wb_data[p][k] = w_data[p*256 +: 256]; wb_tag[p][k] = w_tag[p*TAGW +: TAGW];
                    wb_vis[p][k] = hcyc + 2;
                    wb_w[p] = wb_w[p] + 1;
                end
                w_room[p] <= (WBUF - (wb_w[p] - wb_c[p])) >= 3;
            end
            if (h_fault) begin fault <= 1'b1; fault_code <= fault_code | h_code; end
            if (tb2) begin fault <= 1'b1; fault_code[11] <= 1'b1; end
        end
    end
    assign d_rdy = !d_pend && dr2;

    // ---- controller domain: synchronisers, checker, returns -------------------------------
    reg d1, d2, d_seen, g1, g2, g_seen, go_req;
    longint pc1 [0:NPC-1], pc2 [0:NPC-1], pprev [0:NPC-1];
    // DRAM state / checker (ps)
    longint now;
    bit     b_open [0:NPC-1][0:31]; int b_row [0:NPC-1][0:31];
    longint b_act [0:NPC-1][0:31], b_pre [0:NPC-1][0:31], b_rd [0:NPC-1][0:31], b_wr [0:NPC-1][0:31], b_ref_end [0:NPC-1][0:31];
    longint p_ref0 [0:NPC-1], p_nref [0:NPC-1];   // PULLIN: schedule origin, REFpb count
    longint p_last_act [0:NPC-1], p_last_rd [0:NPC-1], p_last_wr [0:NPC-1], p_last_col [0:NPC-1], p_last_ref [0:NPC-1], p_last_refpb_any [0:NPC-1];
    int     p_wr_bg [0:NPC-1];
    longint p_act_bg [0:NPC-1][0:3], p_col_bg [0:NPC-1][0:3], p_faw [0:NPC-1][0:3];
    bit [31:0] p_round [0:NPC-1];
    longint viol /*verilator public_flat_rw*/, n_act /*verilator public_flat_rw*/, n_rd /*verilator public_flat_rw*/,
            n_wr /*verilator public_flat_rw*/, n_ref /*verilator public_flat_rw*/, n_pre, max_land /*verilator public_flat_rw*/;
    // return queues (controller cycle due)
    longint rq_due [0:NPC-1][0:LR-1]; reg [255:0] rq_dat [0:NPC-1][0:LR-1]; reg [16:0] rq_sec [0:NPC-1][0:LR-1];
    reg [7:0] rq_row [0:NPC-1][0:LR-1];
    integer rq_w [0:NPC-1], rq_r [0:NPC-1];
    longint aq_due [0:NPC-1][0:LR-1]; reg [TAGW-1:0] aq_tag [0:NPC-1][0:LR-1];
    integer aq_w [0:NPC-1], aq_r [0:NPC-1];
    // ---- tagged port state ----------------------------------------------------------------
    // request FIFO (written: t domain; read pointer: controller domain)
    reg [23:0] tq_addr [0:3][0:TRQ-1]; reg [4:0] tq_len [0:3][0:TRQ-1]; reg [TTAGW-1:0] tq_tag [0:3][0:TRQ-1];
    integer tq_w [0:3], tq_r [0:3];            // t-domain write count, controller-domain read count
    integer tq_ws1 [0:3], tq_ws2 [0:3];         // tq_w through two controller flops
    integer tq_rs1 [0:3], tq_rs2 [0:3];         // tq_r through two t flops
    integer t_cur [0:3];                        // controller: next beat of the client's head request
    integer t_rr;
    // per pseudo-channel tagged reads waiting for hand-off, then issued in queue order (controller domain)
    reg [16:0] ta_sec [0:NPC-1][0:LR-1]; reg [6:0] ta_port [0:NPC-1][0:LR-1]; reg [TTAGW-1:0] ta_tag [0:NPC-1][0:LR-1];
    reg [3:0] ta_beat [0:NPC-1][0:LR-1]; reg [7:0] ta_row [0:NPC-1][0:LR-1];
    integer ta_w [0:NPC-1], ta_h [0:NPC-1], ta_c [0:NPC-1];   // pushed / handed off / issued
    reg [NPC-1:0] pres_rd;                      // the presented hand-off entry is a tagged read
    // response rings (written + published: controller; read: t)
    reg [255:0] tr_data [0:NPC-1][0:TRR-1]; reg [TTAGW-1:0] tr_tag [0:NPC-1][0:TRR-1]; reg [3:0] tr_beat [0:NPC-1][0:TRR-1];
    longint tr_due [0:NPC-1][0:TRR-1];
    integer tr_res [0:NPC-1], tr_w [0:NPC-1], tr_pub [0:NPC-1];   // reserved / written / published (controller)
    integer tr_ps1 [0:NPC-1], tr_ps2 [0:NPC-1];                    // published through two t flops
    integer tr_rd [0:NPC-1];                                       // t-domain pops
    integer tr_rs1 [0:NPC-1], tr_rs2 [0:NPC-1];                    // pops through two controller flops
    reg t_bad, tb1, tb2;
    reg d_any;                                                     // a descriptor has been accepted (controller)                                           // t-domain fault (write request) to the core
    function automatic integer tpc(input [23:0] a);
        tpc = integer'(((a >> 2) ^ (a >> 7) ^ (a >> 12)) & 24'd31);
    endfunction
    task automatic v(input string what, input integer pc, input integer bk);
        if (viol < 20) $display("HBM_STREAM VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
        viol++;
        h_fault <= 1'b1; h_code[8] <= 1'b1;
    endtask

    integer q, b, gg;
    bit trace = 1'b0;
    initial trace = $test$plusargs("hbm_trace");
    always @(posedge hclk or negedge rst_n) begin
        if (!rst_n) begin
            hcyc = 0; d1 <= 0; d2 <= 0; d_seen <= 0; g1 <= 0; g2 <= 0; g_seen <= 0; go_req <= 0; a_tog <= 0;
            desc_v_q <= 0; go_q <= 0; cred_ret <= 0; wr_v_q <= 0; wr_rd_q <= 0; pres_rd = 0; h_fault <= 0; h_code <= 0;
            for (gg = 0; gg < 4; gg = gg + 1) begin tq_r[gg] = 0; tq_ws1[gg] = 0; tq_ws2[gg] = 0; t_cur[gg] = 0; end
            t_rr = 0; d_any <= 1'b0;
            viol = 0; n_act = 0; n_rd = 0; n_wr = 0; n_ref = 0; n_pre = 0; max_land = 0;
            for (q = 0; q < NPC; q = q + 1) begin
                pc1[q] = 0; pc2[q] = 0; pprev[q] = 0; rq_w[q] = 0; rq_r[q] = 0; aq_w[q] = 0; aq_r[q] = 0;
                ta_w[q] = 0; ta_h[q] = 0; ta_c[q] = 0; tr_res[q] = 0; tr_w[q] = 0; tr_pub[q] = 0; tr_rs1[q] = 0; tr_rs2[q] = 0;
                ld_w[q] = 0; ak_w[q] = 0; wb_h[q] = 0; wb_c[q] = 0;
                p_last_act[q] = -1000000; p_last_rd[q] = -1000000; p_last_wr[q] = -1000000; p_last_col[q] = -1000000;
                p_last_refpb_any[q] = -1000000; p_round[q] = 0; p_wr_bg[q] = 0;
                begin : ph
                    automatic int P = 118;                                       // REFpb period (cycles), as the RTL
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
            // -- descriptor / go crossings
            d1 <= d_tog; d2 <= d1; g1 <= g_tog; g2 <= g1;
            if (desc_v_q && desc_r) begin desc_v_q <= 1'b0; a_tog <= ~a_tog; d_any <= 1'b1; end
            else if (!desc_v_q && d2 != d_seen) begin desc_v_q <= 1'b1; d_seen <= d2; dq_row <= d_row_c; dq_n <= d_n_c; end
            if (g2 != g_seen) begin g_seen <= g2; go_req <= 1'b1; end
            go_q <= 1'b0;
            if ((go_req || g2 != g_seen) && busy_all && !go_q) begin go_q <= 1'b1; go_req <= 1'b0; end
            if (sfault) begin h_fault <= 1'b1; h_code[9] <= 1'b1; end
            // -- commands issued this cycle (sampled at the edge, as the bench)
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
                    if (col_aq[q]) begin
                        //: a tagged read: the oldest issued-not-yet tagged entry of this PC, same sector
                        if (now < p_last_wr[q] + CWL + BURST + ((p_wr_bg[q] == g) ? WTRL : WTRS)) v("tWTR", q, bk);
                        n_rd++;
                        p_last_rd[q] = now; b_rd[q][bk] = now;
                        k = ta_c[q] % LR;
                        if (ta_c[q] == ta_h[q] || ta_sec[q][k] != ls || ta_row[q][k] != 8'(b_row[q][bk])) begin
                            v("tagged RD does not match the oldest queued tagged read", q, bk);
                        end else begin
                            automatic int rp = ta_port[q][k];
                            gg = tr_w[rp] % TRR;
                            tr_data[rp][gg] = (a < MEM_WORDS) ? mem[a] : 256'd0;
                            tr_tag[rp][gg] = ta_tag[q][k]; tr_beat[rp][gg] = ta_beat[q][k];
                            tr_due[rp][gg] = (now + CL + BURST + RSP + CYC - 1) / CYC;
                            tr_w[rp] = tr_w[rp] + 1;
                        end
                        ta_c[q] = ta_c[q] + 1;
                    end else if (!col_we[q]) begin
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
                        // the write is the buffer's oldest handed-off sector of this PC
                        k = wb_c[q] % WBUF;
                        if (trace) $display("HBMTRACE WR h=%0d c=%0d pc=%0d bank=%0d sec=%0d", hcyc, ccyc, q, bk, a);
                        if (wb_c[q] == wb_h[q] || wb_sec[q][k] != 24'(a)) begin
                            v("WR does not match the oldest queued write", q, bk);
                        end else begin
                            mem[a] = wb_data[q][k];
                            gg = aq_w[q] % LR;
                            aq_due[q][gg] = (now + CWL + BURST + RSP + CYC - 1) / CYC;
                            aq_tag[q][gg] = wb_tag[q][k];
                            aq_w[q] = aq_w[q] + 1;
                        end
                        wb_c[q] = wb_c[q] + 1;
                    end
                end
            end
            for (gg = 0; gg < NPC / 2; gg = gg + 1) if (row_v[2*gg] && row_v[2*gg+1]) v("two row commands on one channel slot", 2*gg, 0);
            // -- returns land / write-done leaves (crosses to the core: visible two core edges later)
            for (q = 0; q < NPC; q = q + 1) begin
                while (rq_r[q] != rq_w[q] && rq_due[q][rq_r[q] % LR] <= hcyc) begin
                    k = rq_r[q] % LR; gg = ld_w[q] % LR;
                    ld_data[q][gg] = rq_dat[q][k]; ld_sec[q][gg] = rq_sec[q][k]; ld_row[q][gg] = rq_row[q][k];
                    ld_vis[q][gg] = ccyc + 2;
                    ld_w[q] = ld_w[q] + 1; rq_r[q] = rq_r[q] + 1;
                    if (ld_w[q] - ld_r[q] > max_land) max_land = ld_w[q] - ld_r[q];
                end
                while (aq_r[q] != aq_w[q] && aq_due[q][aq_r[q] % LR] <= hcyc) begin
                    k = aq_r[q] % LR; gg = ak_w[q] % LR;
                    ak_tag[q][gg] = aq_tag[q][k]; ak_vis[q][gg] = ccyc + 2;
                    ak_w[q] = ak_w[q] + 1; aq_r[q] = aq_r[q] + 1;
                end
                // credits: the core's pop count through two controller flops
                pc2[q] = pc1[q]; pc1[q] = pops[q];
                cred_ret[q*3 +: 3] <= 3'(pc2[q] - pprev[q]);
                if (pc2[q] - pprev[q] > 7) begin h_fault <= 1'b1; h_code[10] <= 1'b1; end
                pprev[q] = pc2[q];
                // write hand-off to the controller queue (visible two controller edges after the push)
                if (wr_v_q[q] && wr_r[q]) begin
                    if (trace) $display("HBMTRACE HAND h=%0d c=%0d pc=%0d rd=%0d", hcyc, ccyc, q, pres_rd[q]);
                    if (pres_rd[q]) ta_h[q] = ta_h[q] + 1; else wb_h[q] = wb_h[q] + 1;
                end
                k = wb_h[q] % WBUF;
                //: hand-off order: a visible write-back first, else the oldest tagged read
                if ((wb_h[q] != wb_w[q]) && wb_vis[q][k] <= hcyc + 1) begin
                    wr_v_q[q] <= 1'b1; wr_rd_q[q] <= 1'b0; pres_rd[q] = 1'b0;
                    wr_bank_q[q*5 +: 5] <= l2bank(wb_sec[q][k][16:0]);
                    wr_col_q[q*5 +: 5] <= l2col(wb_sec[q][k][16:0]);
                end else if (ta_h[q] != ta_w[q]) begin
                    gg = ta_h[q] % LR;
                    wr_v_q[q] <= 1'b1; wr_rd_q[q] <= 1'b1; pres_rd[q] = 1'b1;
                    wr_bank_q[q*5 +: 5] <= l2bank(ta_sec[q][gg]);
                    wr_col_q[q*5 +: 5] <= l2col(ta_sec[q][gg]);
                end else begin
                    wr_v_q[q] <= 1'b0; wr_rd_q[q] <= 1'b0; pres_rd[q] = 1'b0;
                    k = wb_h[q] % WBUF;
                    wr_bank_q[q*5 +: 5] <= l2bank(wb_sec[q][k][16:0]);
                    wr_col_q[q*5 +: 5] <= l2col(wb_sec[q][k][16:0]);
                end
                // tagged responses: publish the due ones (in order); pops come back through two flops
                while (tr_pub[q] != tr_w[q] && tr_due[q][tr_pub[q] % TRR] <= hcyc) tr_pub[q] = tr_pub[q] + 1;
                tr_rs2[q] = tr_rs1[q]; tr_rs1[q] = tr_rd[q];
            end
            // -- tagged splitter: one client a controller cycle (rotating), its head burst's beats in order,
            //    at most one beat a pseudo-channel a cycle; the response slot is reserved before the push
            begin : split
                automatic bit [NPC-1:0] used = 0;
                automatic int s, c, rp, port, sp;
                automatic logic [23:0] a;
                for (c = 0; c < 4; c = c + 1) begin tq_ws2[c] = tq_ws1[c]; tq_ws1[c] = tq_w[c]; end
                //: served only while a descriptor is current (none pending): its row is the reads' layer
                for (c = 0; c < 4 && d_any && !desc_v_q; c = c + 1) begin
                    s = (t_rr + c) % 4;
                    if (tq_r[s] != tq_ws2[s]) begin
                        sp = tq_r[s] % TRQ;
                        if (tq_len[s][sp] == 0 || tq_len[s][sp] > 16) begin h_fault <= 1'b1; h_code[13] <= 1'b1; end
                        while (t_cur[s] < tq_len[s][sp]) begin
                            a = tq_addr[s][sp] + 24'(t_cur[s]);
                            port = l2port(a[16:0]); rp = s * 32 + tpc(a);
                            if (used[port] || ta_w[port] - ta_c[port] >= LR || tr_res[rp] - tr_rs2[rp] >= TRR) break;
                            if (integer'(a >> 17) != integer'(dq_row)) begin h_fault <= 1'b1; h_code[12] <= 1'b1; end
                            gg = ta_w[port] % LR;
                            ta_sec[port][gg] = a[16:0]; ta_row[port][gg] = 8'(a >> 17); ta_port[port][gg] = 7'(rp);
                            ta_tag[port][gg] = tq_tag[s][sp]; ta_beat[port][gg] = 4'(t_cur[s]);
                            ta_w[port] = ta_w[port] + 1; tr_res[rp] = tr_res[rp] + 1; used[port] = 1'b1;
                            t_cur[s] = t_cur[s] + 1;
                        end
                        if (t_cur[s] >= tq_len[s][sp] || tq_len[s][sp] == 0 || tq_len[s][sp] > 16) begin
                            tq_r[s] = tq_r[s] + 1; t_cur[s] = 0;
                        end
                        t_rr = (s + 1) % 4;
                        break;
                    end
                end
            end
            hcyc = hcyc + 1;
        end
    end

    // ---- tagged port, t_clk domain -------------------------------------------------------------
    integer tp, tc;
    always @(posedge t_clk or negedge t_rst_n) begin
        if (!t_rst_n) begin
            t_req_ready <= 0; t_rsp_v <= 0; t_rsp_wr <= 0; t_pc_room <= 0; t_rd_sectors <= 0; t_bad <= 1'b0;
            for (tc = 0; tc < 4; tc = tc + 1) begin tq_w[tc] = 0; tq_rs1[tc] = 0; tq_rs2[tc] = 0; end
            for (tp = 0; tp < NPC; tp = tp + 1) begin tr_rd[tp] = 0; tr_ps1[tp] = 0; tr_ps2[tp] = 0; end
        end else begin
            for (tc = 0; tc < 4; tc = tc + 1) begin
                tq_rs2[tc] = tq_rs1[tc]; tq_rs1[tc] = tq_r[tc];
                if (t_req_v[tc] && t_req_ready[tc]) begin
                    if (t_req_we[tc]) t_bad <= 1'b1;                       // read-only port
                    else begin
                        tq_addr[tc][tq_w[tc] % TRQ] = t_req_addr[tc*24 +: 24]; tq_len[tc][tq_w[tc] % TRQ] = t_req_len[tc*5 +: 5];
                        tq_tag[tc][tq_w[tc] % TRQ] = t_req_tag[tc*TTAGW +: TTAGW];
                        tq_w[tc] = tq_w[tc] + 1;
                    end
                end
                t_req_ready[tc] <= (tq_w[tc] - tq_rs2[tc] < TRQ) && !t_bad && !fault;
            end
            for (tp = 0; tp < NPC; tp = tp + 1) begin
                tr_ps2[tp] = tr_ps1[tp]; tr_ps1[tp] = tr_pub[tp];
                if (t_rsp_v[tp] && t_rsp_ready[tp]) begin tr_rd[tp] = tr_rd[tp] + 1; t_rd_sectors <= t_rd_sectors + 1; end
                t_rsp_v[tp] <= (tr_ps2[tp] != tr_rd[tp]);
                t_rsp_data[tp*256 +: 256] <= tr_data[tp][tr_rd[tp] % TRR];
                t_rsp_tag[tp*TTAGW +: TTAGW] <= tr_tag[tp][tr_rd[tp] % TRR];
                t_rsp_beat[tp*4 +: 4] <= tr_beat[tp][tr_rd[tp] % TRR];
                t_pc_room[tp] <= (TRR - (tr_ps2[tp] - tr_rd[tp])) >= 8;
            end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin tb1 <= 0; tb2 <= 0; end else begin tb1 <= t_bad; tb2 <= tb1; end
endmodule

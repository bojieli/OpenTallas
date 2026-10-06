`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// S81 minimum vehicle for the WINDOW KV load (claude/dsrom-s81-window-bind-20261004): ONE layer die's window
// HBM service, exactly the S81 die's chain, at the target position 1,048,575 on the 1M token's golden rows.
//
//   ot_dsrom_window_attn_source_la (LA=1)  or  the as-built ot_chip_v41x_window_attn_source_owner_safe through the
//   same wrapper with STREAM_LA=0 (LA=0; REFILL_CREDITS = CREDITS, REFILL_OWNER_SAFE = 1: the S81 selection)
//     -> K port: ot_chip_v41x_kv_rope_reqmux_c8 (window client; CKV / RoPE idle) -> ot_chip_v41x_hbm_karb
//     -> ot_dsrom_hbm_wmux (ENABLE = LA || KG; client 0 = the source's wide port, client 1 = kgather)
//     -> ot_hdc_v41x_idx_hbm_c8, the S81 stack model (32 PCs, QD 64, RQD 32, RW 16, MAXSKIP 16, REFPB 3),
//        here at the 1.2 GHz streaming clock (CLK_PS 833).  Four stacks; the window ring is on stack 0.
//   BG = 1: every stack's karb B side (the pooled indexer's bridge port) carries a saturating sequential
//     4-sector read stream on all 32 pseudo-channels from cycle T0 - 600 (a bench generator standing in for the
//     L20 full index scan's pressure on the stacks: the scan runs at 91.9% of peak, results/rtl/
//     dsrom_reindex_candidates_20261004 reader csa1_full_L20_clk833).
//   KG = 1: ot_hdc_v41x_idx_kgather on every stack's wmux client 1 reads the re-index layer's REAL 1M candidate
//     blocks (+PFX lists, the W11 ring placement BASE / BSTEP / OSTEP), started with the window job; every key
//     of every beat checked against the stack contents (bench-preloaded with the model's sector pattern).
// The 128 window rows (+WMEM, @-addressed sector image at W_BASE of stack 0) are primed (as a host image),
// then one job (user 0, first = 1,048,448, count 128) is started at T0 (the refresh phase) and streamed into an
// always-ready consumer.  Every streamed row (16 x {scale, codes} blocks a lane) is compared with +ROWS, the
// golden packed rows (slot order).  Prints WLOAD (start -> staged: cycles, ns, TB/s, fraction of the stack
// peak), WSTREAM (start -> merge done), KGSTACK per stack, and VERDICT.
// ---------------------------------------------------------------------------
module tb_dsrom_s81_window_la #(
    parameter integer WINDOW_PIPELINE = 0,
    parameter integer CTL_LEAF = 0,   // WINDOW_PIPELINE only: 1/2 = source control leaf, MARGIN 0/1
    parameter integer LA = 1, CREDITS = 8, BG = 0, KG = 0, CLK_PS = 833, LA_IW = 8, LA_ISSUE_PC = 0,
    parameter integer OWN_WRITE = 1,  // 0: all 128 rows are host image (+WMEM must hold the own row): cold-row reference
    parameter integer KG_FIRST = 0,   // 1: the gather runs first (with the own-row write), the window job starts after it
    parameter integer PULLIN = 0,     // HBM controller idle REFpb pull-in (ot_hdc_v41x_idx_hbm PULLIN)
    parameter integer PULLIN_LRU = 0,
    parameter integer PULLIN_BATCH = 0,
    parameter integer REF_LEGACY = 0,     // diagnostic only: the pre-2026-10-04 REFpb placement
    parameter longint REFI_PS = 3900000,  // diagnostic only (the no-refresh floor); 3.9 us is JESD238
    parameter integer BG_STOP = 0,    // 1: the background scan stops when the window job starts (the scan precedes the select)
    parameter integer BASE = 0, BSTEP = 1000, OSTEP = 136,
    parameter integer MAX_CYCLES = 400000
) (input wire clk);
    localparam integer NPC = 32, AW = 30, TAGW = 16, STAGW = 17, LENW = 4, BEATW = 4, DW = 256;
    localparam integer MEMW = 1 << 22;
    localparam integer W_BASE = 32'h0030_0000;               // window ring (user 0), 32-sector aligned
    localparam integer FIRST = 1048448, POS = 1048575;
    localparam integer HW = 20, LBW = 14, LMW = 11, WB = 128, DF = 8;
    reg rst_n = 0;
    longint cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    integer T0 = 3000;
    // ---------------- the window source (DUT) ----------------
    reg prime_v = 0, start_v = 0, blk_v = 0;
    reg [20:0] prime_row = 0;
    reg [3:0] blk_idx = 0;
    reg [255:0] blk_codes = 0;
    reg [7:0] blk_scale = 0;
    wire blk_ready;
    wire prime_ready, start_ready, staged_v, busy, done, src_fault, kv_v;
    wire [4:0] src_code; wire [3:0] kv_m; wire [4*16*265-1:0] kv_w;
    wire [31:0] refill_cycles, sectors_read, rows_fetched, blocks_written, sectors_written, la_cycles;
    wire [7:0] rows_refilled;
    wire [3:0] w_v, w_rdy, w_we, w_wdone, w_sv, w_srdy; wire [4*AW-1:0] w_addr; wire [15:0] w_len, w_sbeat;
    wire [4*TAGW-1:0] w_tag, w_stag; wire [1023:0] w_wdata, w_sdata; wire [127:0] w_wstrb;
    wire [NPC-1:0] wl_req_v, wl_req_rdy, wl_rsp_v, wl_rsp_rdy;
    wire [NPC*AW-1:0] wl_req_addr; wire [NPC*LENW-1:0] wl_req_len; wire [NPC*13-1:0] wl_req_tag, wl_rsp_tag;
    wire [NPC*BEATW-1:0] wl_rsp_beat; wire [NPC*DW-1:0] wl_rsp_data;
    ot_dsrom_window_attn_source_la #(.STREAM_LA(LA != 0), .WINDOW_PIPELINE(WINDOW_PIPELINE != 0), .CTL_LEAF(CTL_LEAF), .LA_IW(LA_IW), .LA_ISSUE_PC(LA_ISSUE_PC), .REFILL_OWNER_SAFE(1), .POS_W(21), .USER_W(10),
        .SEC_W(AW), .HAW(AW), .TAGW(TAGW), .WIN_STACK(0), .STREAM_II1(0), .REFILL_CREDITS(CREDITS)) u_src (
        .clk(clk), .rst_n(rst_n),
        .retain_qk(1'b0), .retain_pv(1'b0), .retain_complete(1'b0), .retain_invalidate(1'b0),
        .retain_generation(16'd0),
        .region_base_sector(AW'(W_BASE)), .region_sector_count(AW'(128 * 17)),
        .prime_v(prime_v), .prime_ready(prime_ready), .prime_user(10'd0), .prime_row(prime_row),
        .blk_v(blk_v), .blk_ready(blk_ready), .blk_user(10'd0), .blk_row(21'(POS)), .blk_idx(blk_idx),
        .blk_codes(blk_codes), .blk_scale(blk_scale),
        .start_v(start_v), .start_ready(start_ready), .start_user(10'd0), .start_first(21'(FIRST)),
        .start_count(8'd128), .staged_v(staged_v), .stream_go(1'b1),
        .busy(busy), .done(done), .fault(src_fault), .fault_code(src_code),
        .refill_cycles(refill_cycles), .sectors_read(sectors_read), .rows_fetched(rows_fetched),
        .blocks_written(blocks_written), .sectors_written(sectors_written), .rows_refilled(rows_refilled),
        .kv_v(kv_v), .kv_ready(1'b1), .kv_m(kv_m), .kv_w(kv_w),
        .m_v(w_v), .m_rdy(w_rdy), .m_addr(w_addr), .m_len(w_len), .m_tag(w_tag), .m_we(w_we),
        .m_wdata(w_wdata), .m_wstrb(w_wstrb), .m_wr_done(w_wdone),
        .s_v(w_sv), .s_rdy(w_srdy), .s_tag(w_stag), .s_beat(w_sbeat), .s_data(w_sdata),
        .wl_req_v(wl_req_v), .wl_req_rdy(wl_req_rdy), .wl_req_addr(wl_req_addr), .wl_req_len(wl_req_len),
        .wl_req_tag(wl_req_tag), .wl_rsp_v(wl_rsp_v), .wl_rsp_rdy(wl_rsp_rdy), .wl_rsp_tag(wl_rsp_tag),
        .wl_rsp_beat(wl_rsp_beat), .wl_rsp_data(wl_rsp_data), .la_load_cycles(la_cycles));
    // ---------------- K-side mux (window client only) ----------------
    wire [3:0] pm_v, pm_rdy, pm_we, pk_wd, ps_v, ps_rdy; wire [4*AW-1:0] pm_addr; wire [15:0] pm_len, ps_beat;
    wire [4*TAGW-1:0] pm_tag, ps_tag; wire [1023:0] pm_wdata, ps_data; wire [127:0] pm_wstrb; wire mux_fault;
    ot_chip_v41x_kv_rope_reqmux_c8 #(.C8_PUBLICATION(0), .HAW(AW), .TAGW(TAGW)) u_kv_mux (
        .clk(clk), .rst_n(rst_n),
        .w_v(w_v), .w_rdy(w_rdy), .w_addr(w_addr), .w_len(w_len), .w_tag(w_tag), .w_we(w_we), .w_wdata(w_wdata),
        .w_wstrb(w_wstrb), .w_wr_done(w_wdone), .w_sv(w_sv), .w_srdy(w_srdy), .w_stag(w_stag), .w_sbeat(w_sbeat),
        .w_sdata(w_sdata),
        .c_v(4'd0), .c_rdy(), .c_addr('0), .c_len(16'd0), .c_tag('0), .c_we(4'd0), .c_wdata('0), .c_wstrb('0),
        .c_wr_done(), .c_sv(), .c_srdy(4'hf), .c_stag(), .c_sbeat(), .c_sdata(),
        .p_v(4'd0), .p_rdy(), .p_addr('0), .p_len(16'd0), .p_tag('0), .p_we(4'd0), .p_wdata('0), .p_wstrb('0),
        .p_wr_done(), .p_sv(), .p_srdy(4'hf), .p_stag(), .p_sbeat(), .p_sdata(),
        .m_v(pm_v), .m_rdy(pm_rdy), .m_addr(pm_addr), .m_len(pm_len), .m_tag(pm_tag), .m_we(pm_we),
        .m_wdata(pm_wdata), .m_wstrb(pm_wstrb), .m_wr_done(pk_wd), .s_v(ps_v), .s_rdy(ps_rdy), .s_tag(ps_tag),
        .s_beat(ps_beat), .s_data(ps_data), .fault(mux_fault), .rope_grants(), .rope_wait_cycles());
    // ---------------- kgather (KG) lists ----------------
    integer nlist [0:3];
    reg [LBW-1:0] list [0:4*2048-1];
    reg kg_lw = 0, kg_cmd = 0;
    integer nblk = 0;
    longint t_wstart = -1, t_wdone = -1, t_kg0 = -1;
    reg [LMW-1:0] kg_lwa = 0;
    reg [LBW-1:0] kg_lwb [0:3];
    function automatic integer ooff(input integer q);  ooff = (q * OSTEP) % 1024; endfunction
    function automatic integer obase(input integer q); obase = BASE + q * BSTEP; endfunction
    function automatic [255:0] pat(input [AW-1:0] sec);
        for (integer w = 0; w < 8; w = w + 1) pat[32*w +: 32] = (32'(sec) * 32'd8 + w) * 32'h9E3779B1 ^ 32'h5bd1e995;
    endfunction
    function automatic [543:0] expkey(input integer a, input integer lb, input integer k);
        integer lk, sb, pos; reg [AW-1:0] sc, cs; reg [255:0] sw;
        begin
            lk = ooff(a) + 8 * lb + k; sb = lk / 1024; pos = lk % 1024;
            sc = AW'((obase(a) + 17 * sb) * 128 + pos / 8);
            cs = AW'((obase(a) + 17 * sb + 1) * 128 + 2 * pos);
            sw = pat(sc);
            expkey = {sw[32*(pos % 8) +: 32], pat(cs + 1), pat(cs)};
        end
    endfunction
    // ---------------- four stacks ----------------
    wire [4*NPC-1:0] kg_v, kg_rdy, kg_rv, kg_rrdy; wire [4*NPC*AW-1:0] kg_addr; wire [4*NPC*LENW-1:0] kg_len;
    wire [4*NPC*16-1:0] kg_tag16; wire [4*NPC*16-1:0] kg_rtag16; wire [4*NPC*BEATW-1:0] kg_rbeat;
    wire [4*NPC*DW-1:0] kg_rdata;
    wire [3:0] kg_busy, kg_valid, kg_fault; wire [4*16-1:0] kg_kv; wire [4*16*544-1:0] kg_key;
    wire [4*2*LBW-1:0] kg_blk; wire [4*48-1:0] kg_keys, kg_beats;
    wire [3:0] wm_fault;
    reg bg_on = 0;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_stack
        // B side: background generator
        reg  [31:0] bg_n [0:NPC-1];
        wire [NPC-1:0] b_v, b_rdy, b_rsp_v;
        wire [NPC*AW-1:0] b_addr; wire [NPC*LENW-1:0] b_len; wire [NPC*TAGW-1:0] b_tag;
        for (genvar p = 0; p < NPC; p = p + 1) begin : g_bg
            wire [31:0] ghi = (bg_n[p] + 32'(s * 7919)) * 32;
            wire [31:0] g = ghi + ((32'(p) ^ (ghi >> 5) ^ (ghi >> 10)) & 31);
            assign b_v[p] = BG != 0 && bg_on;
            assign b_addr[p*AW +: AW] = AW'(32'h0010_0000 + g * 4);
            assign b_len[p*LENW +: LENW] = LENW'(4);
            assign b_tag[p*TAGW +: TAGW] = 16'(bg_n[p]);
            always @(posedge clk) if (!rst_n) bg_n[p] <= 0; else if (b_v[p] && b_rdy[p]) bg_n[p] <= bg_n[p] + 1;
        end
        // the karb (K = the window client of the reqmux on stack 0; idle elsewhere)
        wire [NPC-1:0] a_v, a_rdy, a_we, a_wd, a_rv, a_rrdy;
        wire [NPC*AW-1:0] a_addr; wire [NPC*LENW-1:0] a_len; wire [NPC*STAGW-1:0] a_tag, a_rtag;
        wire [NPC*DW-1:0] a_wdata, a_rdata; wire [NPC*DW/8-1:0] a_wstrb; wire [NPC*BEATW-1:0] a_rbeat;
        ot_chip_v41x_hbm_karb #(.NPC(NPC), .AW(AW), .TAGW(TAGW)) u_arb (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag), .b_we({NPC{1'b0}}),
            .b_wdata({NPC*DW{1'b0}}), .b_wstrb({NPC*DW/8{1'b0}}), .b_wr_done(),
            .b_rsp_v(b_rsp_v), .b_rsp_rdy({NPC{1'b1}}), .b_rsp_tag(), .b_rsp_beat(), .b_rsp_data(),
            .k_v(pm_v[s]), .k_rdy(pm_rdy[s]), .k_addr(pm_addr[s*AW +: AW]), .k_len(pm_len[s*4 +: 4]),
            .k_tag(pm_tag[s*16 +: 16]), .k_we(pm_we[s]), .k_wdata(pm_wdata[s*256 +: 256]),
            .k_wstrb(pm_wstrb[s*32 +: 32]), .k_wr_done(pk_wd[s]),
            .k_rsp_v(ps_v[s]), .k_rsp_rdy(ps_rdy[s]), .k_rsp_tag(ps_tag[s*16 +: 16]),
            .k_rsp_beat(ps_beat[s*4 +: 4]), .k_rsp_data(ps_data[s*256 +: 256]),
            .h_v(a_v), .h_rdy(a_rdy), .h_addr(a_addr), .h_len(a_len), .h_tag(a_tag), .h_we(a_we),
            .h_wdata(a_wdata), .h_wstrb(a_wstrb), .h_wr_done(a_wd),
            .r_v(a_rv), .r_rdy(a_rrdy), .r_tag(a_rtag), .r_beat(a_rbeat), .r_data(a_rdata),
            .k_grants(), .b_grants(), .contended());
        // the wide mux: client 0 = window (stack 0 only), client 1 = kgather
        wire [2*NPC-1:0] c_v, c_rdy, c_rv, c_rrdy; wire [2*NPC*AW-1:0] c_addr; wire [2*NPC*LENW-1:0] c_len;
        wire [2*NPC*13-1:0] c_tag, c_rtag; wire [2*NPC*BEATW-1:0] c_rbeat; wire [2*NPC*DW-1:0] c_rdata;
        if (s == 0) begin : g_win
            assign c_v[0 +: NPC] = wl_req_v; assign c_addr[0 +: NPC*AW] = wl_req_addr;
            assign c_len[0 +: NPC*LENW] = wl_req_len; assign c_tag[0 +: NPC*13] = wl_req_tag;
            assign wl_req_rdy = c_rdy[0 +: NPC];
            assign wl_rsp_v = c_rv[0 +: NPC]; assign wl_rsp_tag = c_rtag[0 +: NPC*13];
            assign wl_rsp_beat = c_rbeat[0 +: NPC*BEATW]; assign wl_rsp_data = c_rdata[0 +: NPC*DW];
            assign c_rrdy[0 +: NPC] = wl_rsp_rdy;
        end else begin : g_nowin
            assign c_v[0 +: NPC] = '0; assign c_addr[0 +: NPC*AW] = '0; assign c_len[0 +: NPC*LENW] = '0;
            assign c_tag[0 +: NPC*13] = '0; assign c_rrdy[0 +: NPC] = {NPC{1'b1}};
        end
        assign c_v[NPC +: NPC] = kg_v[s*NPC +: NPC];
        assign c_addr[NPC*AW +: NPC*AW] = kg_addr[s*NPC*AW +: NPC*AW];
        assign c_len[NPC*LENW +: NPC*LENW] = kg_len[s*NPC*LENW +: NPC*LENW];
        for (genvar p = 0; p < NPC; p = p + 1) begin : g_kt
            assign c_tag[(NPC + p)*13 +: 13] = kg_tag16[(s*NPC + p)*16 +: 13];
            assign kg_rtag16[(s*NPC + p)*16 +: 16] = {3'b0, c_rtag[(NPC + p)*13 +: 13]};
        end
        assign kg_rdy[s*NPC +: NPC] = c_rdy[NPC +: NPC];
        assign kg_rv[s*NPC +: NPC] = c_rv[NPC +: NPC];
        assign kg_rbeat[s*NPC*BEATW +: NPC*BEATW] = c_rbeat[NPC*BEATW +: NPC*BEATW];
        assign kg_rdata[s*NPC*DW +: NPC*DW] = c_rdata[NPC*DW +: NPC*DW];
        assign c_rrdy[NPC +: NPC] = kg_rrdy[s*NPC +: NPC];
        wire [NPC-1:0] h_v, h_rdy, h_we, h_wd, r_v, r_rdy;
        wire [NPC*AW-1:0] h_addr; wire [NPC*LENW-1:0] h_len; wire [NPC*STAGW-1:0] h_tag, r_tag;
        wire [NPC*DW-1:0] h_wdata, r_data; wire [NPC*DW/8-1:0] h_wstrb; wire [NPC*BEATW-1:0] r_beat;
        ot_dsrom_hbm_wmux #(.ENABLE(LA != 0 || KG != 0), .NPC(NPC), .AW(AW), .TAGW(STAGW), .LENW(LENW),
            .BEATW(BEATW), .DW(DW), .NW(2), .CW(1), .WTAGW(13)) u_wmux (
            .clk(clk), .rst_n(rst_n),
            .a_v(a_v), .a_rdy(a_rdy), .a_addr(a_addr), .a_len(a_len), .a_tag(a_tag), .a_we(a_we),
            .a_wdata(a_wdata), .a_wstrb(a_wstrb), .a_wr_done(a_wd), .a_rsp_v(a_rv), .a_rsp_rdy(a_rrdy),
            .a_rsp_tag(a_rtag), .a_rsp_beat(a_rbeat), .a_rsp_data(a_rdata),
            .w_v(c_v), .w_rdy(c_rdy), .w_addr(c_addr), .w_len(c_len), .w_tag(c_tag),
            .w_rsp_v(c_rv), .w_rsp_rdy(c_rrdy), .w_rsp_tag(c_rtag), .w_rsp_beat(c_rbeat), .w_rsp_data(c_rdata),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wd),
            .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),
            .fault(wm_fault[s]), .w_grants(), .a_held());
`ifdef DRAMCHK
        // the traced copy of the same controller (rtl/test/ot_hdc_v41x_idx_hbm_trace.sv: the model byte for byte
        // plus a JESD238 command log and checker), checked at the end of the run
        ot_hdc_v41x_idx_hbm_trace #(.NPC(NPC), .AW(AW), .DW(DW), .MEM_WORDS(MEMW), .TAGW(STAGW), .LENW(LENW),
            .BEATW(BEATW), .QD(64), .RQD(32), .RW(16), .MAXSKIP(16), .CLK_PS(CLK_PS), .REFPB(3), .MEM_MODE(0),
            .PULLIN(PULLIN), .PULLIN_LRU(PULLIN_LRU), .PULLIN_BATCH(PULLIN_BATCH), .REF_LEGACY(REF_LEGACY), .REFI_PS(REFI_PS)) hm (
            .clk(clk), .rst_n(rst_n), .req_v(h_v), .req_rdy(h_rdy), .req_addr(h_addr), .req_len(h_len),
            .req_tag(h_tag), .req_we(h_we), .req_wdata(h_wdata), .req_wstrb(h_wstrb), .wr_done(h_wd),
            .rsp_v(r_v), .rsp_rdy(r_rdy), .rsp_tag(r_tag), .rsp_beat(r_beat), .rsp_data(r_data));
        final hm.dram_check(s);
`else
        ot_hdc_v41x_idx_hbm_c8 #(.NPC(NPC), .AW(AW), .DW(DW), .MEM_WORDS(MEMW), .TAGW(STAGW), .LENW(LENW),
            .BEATW(BEATW), .QD(64), .RQD(32), .RW(16), .MAXSKIP(16), .CLK_PS(CLK_PS), .REFPB(3), .MEM_MODE(0),
            .PULLIN(PULLIN), .PULLIN_LRU(PULLIN_LRU), .PULLIN_BATCH(PULLIN_BATCH), .REF_LEGACY(REF_LEGACY), .REFI_PS(REFI_PS)) hm (
            .clk(clk), .rst_n(rst_n), .req_v(h_v), .req_rdy(h_rdy), .req_addr(h_addr), .req_len(h_len),
            .req_tag(h_tag), .req_we(h_we), .req_wdata(h_wdata), .req_wstrb(h_wstrb), .wr_done(h_wd),
            .wr_done_addr(), .wr_done_tag(),
            .rsp_v(r_v), .rsp_rdy(r_rdy), .rsp_tag(r_tag), .rsp_beat(r_beat), .rsp_data(r_data));
`endif
        if (KG != 0) begin : g_kg
            ot_hdc_v41x_idx_kgather #(.NPC(NPC), .WB(WB), .AW(AW), .HW(HW), .TAGW(16), .LENW(LENW), .BEATW(BEATW),
                .DW(DW), .LBW(LBW), .LMW(LMW), .DF(DF)) kg (
                .clk(clk), .rst_n(rst_n), .lw_v(kg_lw && kg_lwa < LMW'(nlist[s])), .lw_addr(kg_lwa), .lw_blk(kg_lwb[s]),
                .cmd_v(kg_cmd), .cmd_base(HW'(obase(s))), .cmd_skip(10'(ooff(s))), .cmd_n(12'(nlist[s])),
                .busy(kg_busy[s]), .fault(kg_fault[s]),
                .req_v(kg_v[s*NPC +: NPC]), .req_rdy(kg_rdy[s*NPC +: NPC]), .req_addr(kg_addr[s*NPC*AW +: NPC*AW]),
                .req_len(kg_len[s*NPC*LENW +: NPC*LENW]), .req_tag(kg_tag16[s*NPC*16 +: NPC*16]),
                .rsp_v(kg_rv[s*NPC +: NPC]), .rsp_rdy(kg_rrdy[s*NPC +: NPC]), .rsp_tag(kg_rtag16[s*NPC*16 +: NPC*16]),
                .rsp_beat(kg_rbeat[s*NPC*BEATW +: NPC*BEATW]), .rsp_data(kg_rdata[s*NPC*DW +: NPC*DW]),
                .o_valid(kg_valid[s]), .o_ready(1'b1), .o_kv(kg_kv[s*16 +: 16]), .o_key(kg_key[s*16*544 +: 16*544]),
                .o_blk(kg_blk[s*2*LBW +: 2*LBW]), .cnt_keys_streamed(kg_keys[s*48 +: 48]),
                .cnt_hbm_beats(kg_beats[s*48 +: 48]));
        end else begin : g_nokg
            assign kg_v[s*NPC +: NPC] = '0; assign kg_addr[s*NPC*AW +: NPC*AW] = '0;
            assign kg_len[s*NPC*LENW +: NPC*LENW] = '0; assign kg_tag16[s*NPC*16 +: NPC*16] = '0;
            assign kg_rrdy[s*NPC +: NPC] = {NPC{1'b1}}; assign kg_busy[s] = 1'b0; assign kg_valid[s] = 1'b0;
            assign kg_fault[s] = 1'b0; assign kg_kv[s*16 +: 16] = '0; assign kg_key[s*16*544 +: 16*544] = '0;
            assign kg_blk[s*2*LBW +: 2*LBW] = '0; assign kg_keys[s*48 +: 48] = '0; assign kg_beats[s*48 +: 48] = '0;
        end
    end endgenerate
    // ---------------- vectors ----------------
    reg [4223:0] exp_row [0:127];
    string wmem, rows_f, pfx;
    initial begin : load
        integer fd, r, v, i, q;
        void'($value$plusargs("t0=%d", T0));
        if (!$value$plusargs("WMEM=%s", wmem)) $fatal(1, "+WMEM required");
        if (!$value$plusargs("ROWS=%s", rows_f)) $fatal(1, "+ROWS required");
        $readmemh(wmem, g_stack[0].hm.mem);
        $readmemh(rows_f, exp_row);
        for (q = 0; q < 4; q = q + 1) nlist[q] = 0;
        if (KG != 0) begin
            if (!$value$plusargs("PFX=%s", pfx)) $fatal(1, "+PFX required with KG");
            for (q = 0; q < 4; q = q + 1) begin
                fd = $fopen($sformatf("%s.s%0d", pfx, q), "r");
                if (fd == 0) $fatal(1, "cannot open list %0d", q);
                r = $fscanf(fd, "%d", nlist[q]);
                for (i = 0; i < nlist[q]; i = i + 1) begin r = $fscanf(fd, "%h", v); list[q*2048 + i] = LBW'(v); end
                $fclose(fd);
            end
        end
    end
    // key-region contents for the gather: the model's sector pattern at every sector a list touches
    task automatic preload_keys(input integer q);
        for (integer i = 0; i < nlist[q]; i = i + 1)
            for (integer k = 0; k < 8; k = k + 1) begin : one
                integer lk, sb, pos; reg [AW-1:0] sc, cs;
                lk = ooff(q) + 8 * int'(list[q*2048 + i]) + k; sb = lk / 1024; pos = lk % 1024;
                sc = AW'((obase(q) + 17 * sb) * 128 + pos / 8);
                cs = AW'((obase(q) + 17 * sb + 1) * 128 + 2 * pos);
                case (q)
                    0: begin g_stack[0].hm.mem[sc % MEMW] = pat(sc); g_stack[0].hm.mem[cs % MEMW] = pat(cs);
                             g_stack[0].hm.mem[(cs + 1) % MEMW] = pat(cs + 1); end
                    1: begin g_stack[1].hm.mem[sc % MEMW] = pat(sc); g_stack[1].hm.mem[cs % MEMW] = pat(cs);
                             g_stack[1].hm.mem[(cs + 1) % MEMW] = pat(cs + 1); end
                    2: begin g_stack[2].hm.mem[sc % MEMW] = pat(sc); g_stack[2].hm.mem[cs % MEMW] = pat(cs);
                             g_stack[2].hm.mem[(cs + 1) % MEMW] = pat(cs + 1); end
                    default: begin g_stack[3].hm.mem[sc % MEMW] = pat(sc); g_stack[3].hm.mem[cs % MEMW] = pat(cs);
                             g_stack[3].hm.mem[(cs + 1) % MEMW] = pat(cs + 1); end
                endcase
            end
    endtask
    // ---------------- sequence ----------------
    longint t_start = -1, t_staged = -1, t_done = -1, t_first_w = -1, t_last_w = -1, kg_last = -1;
    integer phase = 0, nprime = 0, beats = 0, bad = 0, wsect = 0, kg_bad = 0;
    longint w_rsp_stall = 0, w_req_notrdy = 0, w_issue_idle = 0;
    integer kptr [0:3]; longint kfirst [0:3], klast [0:3];
    initial for (integer q = 0; q < 4; q = q + 1) begin kptr[q] = 0; kfirst[q] = -1; klast[q] = -1; end
    integer li = 0;
    always @(posedge clk) begin
        if (cyc == 2 && KG != 0) for (integer q = 0; q < 4; q = q + 1) preload_keys(q);
        if (cyc == 5) rst_n <= 1;
        prime_v <= 0; start_v <= 0; kg_lw <= 0; kg_cmd <= 0; blk_v <= 0;
        if (rst_n) case (phase)
            0: begin                                    // prime the 127 older rows (host image already in HBM)
                if (prime_v && prime_ready) nprime = nprime + 1;
                if (nprime < (OWN_WRITE != 0 ? 127 : 128)) begin prime_v <= 1; prime_row <= 21'(FIRST + nprime); end
                else phase <= 1;
            end
            1: begin                                    // kgather lists, then wait for T0
                if (KG != 0 && li < 2048) begin
                    kg_lw <= 1; kg_lwa <= LMW'(li);
                    for (integer q = 0; q < 4; q = q + 1) kg_lwb[q] <= list[q*2048 + li];
                    li = li + 1;
                end
                if (BG != 0 && cyc >= T0 - 600) bg_on <= 1;
                if (cyc >= T0 - 1 && (KG == 0 || li >= 2048)) begin
                    t_wstart = cyc + 1; phase <= 6; if (OWN_WRITE == 0) nblk = 16;
                    if (KG != 0 && KG_FIRST != 0) begin kg_cmd <= 1; t_kg0 = cyc + 1; end
                end
            end
            6: begin                                    // the token's own row: 16 blocks through the as-built writer
                if (blk_v && blk_ready) nblk = nblk + 1;
                if (nblk < 16) begin
                    blk_v <= 1; blk_idx <= 4'(nblk);
                    blk_codes <= exp_row[POS % 128][256*nblk +: 256]; blk_scale <= exp_row[POS % 128][4096 + 8*nblk +: 8];
                end else if (blk_ready && !busy) begin
                    if (t_wdone < 0) t_wdone = cyc;
                    if (KG_FIRST == 0 || (kptr[0] == nlist[0] && kptr[1] == nlist[1] && kptr[2] == nlist[2] &&
                                          kptr[3] == nlist[3] && kg_busy == 0 && t_kg0 >= 0)) begin
                        start_v <= 1; phase <= 2; if (BG_STOP != 0) bg_on <= 0;
                    end
                end
            end
            2: if (start_v && start_ready) begin
                   t_start = cyc; start_v <= 0; phase <= 3; if (KG != 0 && KG_FIRST == 0) begin kg_cmd <= 1; t_kg0 = cyc; end
               end else start_v <= 1;
            3: begin
                if (staged_v && t_staged < 0) t_staged = cyc;
                if (done) begin t_done = cyc; phase <= 4; end
                if (src_fault || mux_fault || |wm_fault || |kg_fault) begin
                    $display("FAULT src=%0d code=%b mux=%0d wmux=%b kg=%b", src_fault, src_code, mux_fault, wm_fault, kg_fault);
                    phase <= 9;
                end
                if (cyc > T0 + MAX_CYCLES) begin $display("TIMEOUT"); phase <= 9; end
            end
            4: if (KG == 0 || (kptr[0] == nlist[0] && kptr[1] == nlist[1] && kptr[2] == nlist[2] &&
                               kptr[3] == nlist[3] && kg_busy == 0)) phase <= 5;
               else if (cyc > T0 + MAX_CYCLES) begin $display("TIMEOUT"); phase <= 9; end
            5: begin report(); $finish; end
            default: begin bad = bad + 1; report(); $finish; end
        endcase
    end
    // window responses landed (wide port or K port)
    always @(posedge clk) if (rst_n && phase == 3) begin
        automatic integer c = 0;
        for (integer p = 0; p < NPC; p = p + 1) if (g_stack[0].r_v[p] && g_stack[0].r_rdy[p] &&
            (g_stack[0].r_tag[p*STAGW + 14 +: 3] == 3'b111 && g_stack[0].r_tag[p*STAGW + 13] == 1'b0 ||
             g_stack[0].r_tag[p*STAGW + 16] && g_stack[0].r_tag[p*STAGW + 14 +: 2] == 2'b00)) c = c + 1;
        if (c != 0) begin if (t_first_w < 0) t_first_w = cyc; t_last_w = cyc; wsect = wsect + c; end
        for (integer p = 0; p < NPC; p = p + 1) begin
            if (g_stack[0].r_v[p] && !g_stack[0].r_rdy[p]) w_rsp_stall = w_rsp_stall + 1;
            if (wl_req_v != 0 || u_src.busy) begin if (!wl_req_rdy[p]) w_req_notrdy = w_req_notrdy + 1; end
        end
        if (u_src.busy && wl_req_v == 0 && t_first_w >= 0 && wsect < 2176) w_issue_idle = w_issue_idle + 1;
    end
    // streamed rows
    integer srow = 0;
    always @(posedge clk) if (rst_n && kv_v) begin
        for (integer l = 0; l < 4; l = l + 1) if (kv_m[l]) begin
            automatic reg [4223:0] got = '0;
            automatic integer slot = (FIRST + srow) % 128;
            for (integer g = 0; g < 16; g = g + 1) begin
                automatic reg [264:0] blk = kv_w[(l*16 + g)*265 +: 265];
                got[256*g +: 256] = blk[255:0];
                got[4096 + 8*g +: 8] = blk[263:256];
                if (blk[264]) bad = bad + 1;
            end
            if (got !== exp_row[slot]) begin
                bad = bad + 1; if (bad < 4) $display("ROW MISMATCH row=%0d slot=%0d", FIRST + srow, slot);
            end
            srow = srow + 1;
        end
        beats = beats + 1;
    end
    // gather output check
    always @(posedge clk) if (rst_n && KG != 0) for (integer q = 0; q < 4; q = q + 1) if (kg_valid[q]) begin
        automatic integer nk = kg_kv[q*16 + 8] ? 2 : 1;
        if (kfirst[q] < 0) kfirst[q] = cyc - t_kg0;
        klast[q] = cyc - t_kg0;
        for (integer b = 0; b < nk; b = b + 1) begin
            if (kptr[q] + b >= nlist[q] || kg_blk[q*2*LBW + b*LBW +: LBW] !== list[q*2048 + kptr[q] + b]) kg_bad = kg_bad + 1;
            else for (integer k = 0; k < 8; k = k + 1)
                if (kg_key[(q*16 + 8*b + k)*544 +: 544] !== expkey(q, int'(list[q*2048 + kptr[q] + b]), k)) kg_bad = kg_bad + 1;
        end
        kptr[q] = kptr[q] + nk;
    end
    task automatic report();
        real lns, sns, tbps, peak;
        longint lc;
        lc = t_staged - t_start;
        lns = real'(lc) * CLK_PS / 1000.0;
        sns = real'(t_done - t_start) * CLK_PS / 1000.0;
        tbps = 69632.0 / lns / 1000.0;
        peak = 32.0 * 32.0 / 1.024 / 1000.0;
        $display("WLOAD la=%0d credits=%0d bg=%0d kg=%0d clk_ps=%0d t0=%0d cycles=%0d ns=%0.1f bytes=69632 tbps=%0.4f peak_tbps=%0.4f frac=%0.4f first_rsp_cycles=%0d last_rsp_cycles=%0d sectors=%0d la_cycles=%0d refill_cycles=%0d",
                 LA, CREDITS, BG, KG, CLK_PS, T0, lc, lns, tbps, peak, tbps / peak, t_first_w - t_start,
                 t_last_w - t_start, wsect, la_cycles, refill_cycles);
        $display("WDIAG rsp_stall_pc_cycles=%0d req_notrdy_pc_cycles=%0d issue_idle_cycles=%0d", w_rsp_stall, w_req_notrdy, w_issue_idle);
        $display("WSTREAM cycles=%0d ns=%0.1f rows=%0d beats=%0d", t_done - t_start, sns, srow, beats);
        $display("WWRITE cycles=%0d ns=%0.1f blocks=16 sectors_written=%0d", t_wdone - t_wstart,
                 real'(t_wdone - t_wstart) * CLK_PS / 1000.0, sectors_written);
        if (KG != 0) begin
            longint mx = -1;
            for (integer q = 0; q < 4; q = q + 1) begin
                $display("KGSTACK s=%0d blocks=%0d sectors=%0d hbm_beats=%0d keys=%0d first=%0d last=%0d", q, nlist[q],
                         17 * nlist[q], kg_beats[q*48 +: 48], kg_keys[q*48 +: 48], kfirst[q], klast[q]);
                if (kg_beats[q*48 +: 48] != 48'(17 * nlist[q]) || kg_keys[q*48 +: 48] != 48'(8 * nlist[q])) kg_bad = kg_bad + 1;
                if (klast[q] > mx) mx = klast[q];
            end
            $display("KGATHER last=%0d bad=%0d first_cycle_rel_window_start=%0d", mx, kg_bad, t_kg0 - t_start);
        end
        $display("VERDICT %s bad=%0d kg_bad=%0d rows=%0d fault=%0d",
                 (bad == 0 && kg_bad == 0 && srow == 128 && !src_fault && !mux_fault && wm_fault == 0 && phase == 5)
                 ? "PASS" : "FAIL", bad, kg_bad, srow, src_fault);
    endtask
endmodule

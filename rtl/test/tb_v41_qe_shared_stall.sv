`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Actual QE (ot_hdc_v41_qe, full shape BL16/IL8/NBMAX192, CHUNK8) fed by the
// actual QE weight streamer (ot_hdc_qstream, FULL_SHAPE, NPC32) through the
// shared one-stack HBM timing owner (ot_chip_v41x_shared_hbm_model) while 32
// K/KV requesters read the same stack.  One LINQ descriptor (the production
// L0 wq_a shape: nb 160, tiles 3, nout 320 = 3,840 weight words, 65,280 sectors).
// Driven by tools/v41_qe_shared_stall_gate.py.  Files in the cwd:
//   w.mem   weight sectors (word a at sector WBASE + 17a, sector s = word bits 256s..)
//   x.mem   activation blocks (32 FP32 words of BF16 values per line)
//   y.mem   expected BF16 outputs (as FP32 bits), one per row, NOUT rows
// Plusargs: KPER (0 = no K traffic; else each PC offers a one-sector read every
// KPER cycles), KCRED (outstanding K reads per PC), LEAD, RATE (the no-stall
// admission), STALL (bench build parameter).
// ---------------------------------------------------------------------------
module tb_v41_qe_shared_stall #(parameter integer STALL = 1, LWIN = 10);
    localparam integer NB = 160, TILES = 3, NOUT = 320, IL = 8, BL = 16;
    localparam integer WORDS = TILES * NB * IL, SPW = 17, WBASE = 65536, WIN = 1 << LWIN;
    localparam integer MEMW = 131072;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0, start = 0, go = 0, launched = 0;
    integer cycles = 0, kper = 0, kcred = 8, lead = 1, rate = 0;
    // QE <-> streamer
    wire qr_re, qr_ready, qok, qe_idle, qe_ready, qe_fault, qs_fault, h_fault;
    wire [29:0] qr_addr; wire [4351:0] qr_q;
    wire [29:0] xr_addr; wire xr_re; reg [1023:0] xr_q = 0;
    wire [29:0] outaddr; wire [31:0] mask; wire [1023:0] outdata; wire outwe;
    wire lr; wire [11:0] la; reg [159:0] lq = 0;
    wire [16:0] winwe; wire [17*LWIN-1:0] winwa; wire [4351:0] winwd; wire winre; wire [LWIN-1:0] winra;
    reg [4351:0] winq = 0;
    reg [255:0] window [0:16][0:WIN-1];
    wire hv, hr; wire [29:0] ha; wire [5:0] hl; wire [LWIN-1:0] ht; wire [31:0] room, rv, rr;
    wire [32*LWIN-1:0] rt; wire [159:0] rb; wire [8191:0] rd;
    wire [3:0] qs_why; wire [31:0] qs_fetched, qs_consumed;
    // K requesters
    reg [31:0] kv = 0; wire [31:0] krdy, krv, kdone;
    reg [959:0] ka = 0; reg [127:0] kl = 0;
    wire [8191:0] krdata; wire [32*17-1:0] krtag; wire [127:0] krbeat;
    reg [1023:0] xmem [0:NB-1];
    reg [31:0] ymem [0:NOUT-1];
    integer i, seen = 0, errors = 0, masked = 0;
    integer qe_go_cyc = -1, qe_end = -1, qok_cyc = -1, first_issue = -1, last_issue = -1;
    integer starve = 0, align = 0, rows_cycles = 0;
    integer k_acc = 0, k_stall = 0, k_rsp = 0, k_offer = 0;
    integer kout [0:31];
    integer w_sectors = 0;
    integer ky;

    initial begin
        $readmemh("x.mem", xmem);
        $readmemh("y.mem", ymem);
        for (i = 0; i < MEMW; i = i + 1) hbm.u_mem.mem[i] = 256'(i);
        $readmemh("w.mem", hbm.u_mem.mem, WBASE);
        for (i = 0; i < 32; i = i + 1) kout[i] = 0;
        if (!$value$plusargs("KPER=%d", kper)) kper = 0;
        if (!$value$plusargs("KCRED=%d", kcred)) kcred = 8;
        if (!$value$plusargs("LEAD=%d", lead)) lead = 1;
        if (!$value$plusargs("RATE=%d", rate)) rate = 0;
        repeat (4) @(negedge clk); rst_n = 1; start = 1;
        @(negedge clk); start = 0;
    end

    always @(negedge clk) if (rst_n) begin
        cycles = cycles + 1; go = 0;
        if (qok && !launched) begin go = 1; launched = 1; qe_go_cyc = cycles; end
        if (qok && qok_cyc < 0) qok_cyc = cycles;
        // K traffic from the token start until the QE drains: one-sector reads, KCRED outstanding per PC
        kv = 0; kl = 0;
        if (kper > 0 && qe_end < 0)
            for (integer p = 0; p < 32; p = p + 1)
                if ((cycles % kper) == (p % kper) && kout[p] < kcred) begin
                    kv[p] = 1; kl[p*4 +: 4] = 4'd1;
                    // sector 4x on pseudo-channel p (the model's pc_of hash), rows walk the K region
                    ky = ((cycles / kper) * 7 + p * 13) % 512;
                    ka[p*30 +: 30] = 30'(4 * ((ky << 5) | ((p ^ ky ^ (ky >> 5)) & 31)));
                end
        if (qe_fault || qs_fault || h_fault) begin
            $display("FAULT qe=%0d qs=%0d why=%b hbm=%0d cycles=%0d seen=%0d", qe_fault, qs_fault, qs_why, h_fault,
                     cycles, seen);
            $display("V41QESHARED status=fault");
            $finish;
        end
        if (launched && qe_idle && seen == TILES * IL && qe_end < 0) qe_end = cycles;
        if (qe_end > 0 && cycles > qe_end + 4) begin
            $display("V41QESHARED status=%0s rows=%0d errors=%0d masked=%0d kper=%0d kcred=%0d stall=%0d lwin=%0d qok=%0d go=%0d first_issue=%0d last_issue=%0d end=%0d starve=%0d align=%0d rows_cycles=%0d k_offer=%0d k_acc=%0d k_stall=%0d k_rsp=%0d w_sectors=%0d fetched=%0d consumed=%0d",
                     (errors == 0 && masked == 4) ? "pass" : "mismatch", seen * BL, errors, masked, kper, kcred,
                     STALL, LWIN, qok_cyc, qe_go_cyc, first_issue, last_issue, qe_end, starve, align, rows_cycles,
                     k_offer, k_acc, k_stall, k_rsp, w_sectors, qs_fetched, qs_consumed);
            begin : hbmstats
                longint rd, act, hit, conf;
                rd = 0; act = 0; hit = 0; conf = 0;
                for (integer p = 0; p < 32; p = p + 1) begin
                    rd += hbm.u_mem.st_rd[p]; act += hbm.u_mem.st_act[p]; hit += hbm.u_mem.st_hit[p];
                    conf += hbm.u_mem.st_conf[p];
                end
                $display("V41QEHBM reads=%0d acts=%0d row_hits=%0d row_conflicts=%0d lat_sum_ps=%0d lat_max_ps=%0d bp_cycles=%0d",
                         rd, act, hit, conf, hbm.u_mem.st_rd_lat_sum, hbm.u_mem.st_rd_lat_max, hbm.u_mem.st_bp_cycles);
            end
            $finish;
        end
        if (cycles > 400000) begin $display("V41QESHARED status=timeout seen=%0d", seen); $finish; end
    end

    always @(posedge clk) begin
        if (lr) lq <= (la == 0) ? ((160'(WORDS) << 60)) : 160'd0;       // hbm offset 0, rom base 0, n words, FP8
        if (xr_re) xr_q <= xmem[xr_addr >> 5];
        for (integer j = 0; j < 17; j = j + 1) begin
            if (winre) winq[j*256 +: 256] <= window[j][winra];
            if (winwe[j]) window[j][winwa[j*LWIN +: LWIN]] <= winwd[j*256 +: 256];
        end
        if (rst_n) begin
            if (qe.st == 5) begin
                rows_cycles <= rows_cycles + 1;
                if (!qr_ready) starve <= starve + 1;
                else if (!qe.issue_fire) align <= align + 1;
            end
            if (qr_re) begin if (first_issue < 0) first_issue <= cycles; last_issue <= cycles; end
            for (integer p = 0; p < 32; p = p + 1) begin
                if (kv[p]) k_offer = k_offer + 1;
                if (kv[p] && krdy[p]) begin k_acc = k_acc + 1; kout[p] = kout[p] + 1; end
                if (kv[p] && !krdy[p]) k_stall = k_stall + 1;
                if (krv[p]) begin k_rsp = k_rsp + 1; kout[p] = kout[p] - 1; end
                if (rv[p] && rr[p]) w_sectors = w_sectors + 1;
            end
            if (outwe) begin
                if (outaddr !== 30'(seen * BL)) begin
                    errors = errors + 1; $display("ORDER addr=%0d seen=%0d", outaddr, seen);
                end
                if (mask == 32'h0) masked = masked + 1;
                for (integer j = 0; j < BL; j = j + 1) if (seen * BL + j < NOUT) begin
                    if (!mask[j] || outdata[j*32 +: 32] !== ymem[seen * BL + j]) begin
                        if (errors < 8) $display("MISMATCH row=%0d got=%h exp=%h mask=%0d", seen * BL + j,
                                                 outdata[j*32 +: 32], ymem[seen * BL + j], mask[j]);
                        errors = errors + 1;
                    end
                end else if (mask[j]) errors = errors + 1;
                seen = seen + 1;
            end
        end
    end

    ot_hdc_v41_qe #(.AW(30), .NW(21), .BL(16), .IL(8), .NBMAX(192), .CHUNK8(1), .WEIGHT_STALL(STALL)) qe (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(qe_ready), .idle(qe_idle), .i_mode(2'b0), .i_fp4(1'b0),
        .i_unrounded(1'b0), .i_xbase(30'b0), .i_nb(8'(NB)), .i_nout(21'(NOUT)), .i_tiles(21'(TILES)),
        .i_wbase(30'b0), .i_ind(1'b0), .i_ibase(30'b0), .i_istride(30'b0), .i_obase(30'b0), .i_m(3'b0),
        .i_xps(30'b0), .i_ops(30'b0), .vi_re(), .vi_addr(), .vi_q(32'b0), .xr_re(xr_re), .xr_addr(xr_addr), .xr_q(xr_q),
        .w_we(outwe), .w_addr(outaddr), .w_mask(mask), .w_data(outdata),
        .kvb_v(), .kvb_src_addr(), .kvb_codes(), .kvb_scale(), .kvb_fault(),
        .qr_re(qr_re), .qr_addr(qr_addr), .qr_q(qr_q), .qr_issue_ready(STALL ? qr_ready : 1'b1), .fault(qe_fault));
    ot_hdc_qstream #(.FULL_SHAPE(1), .ALLOW_QE_STALL(STALL), .NPC(32), .LWIN(LWIN)) stream (
        .clk(clk), .rst_n(rst_n), .cfg_base(30'(WBASE)), .cfg_lbase(12'b0), .cfg_lead(21'(lead)),
        .cfg_rate(16'(rate)), .tok_start(start), .pos(21'd1),
        .l_re(lr), .l_addr(la), .l_q(lq), .vi_re(), .vi_addr(), .vi_q(32'b0), .wrel_v(1'b0),
        .qd_v(start), .qd_nb(8'(NB)), .qd_tiles(21'(TILES)), .q_ok(qok),
        .qr_re(qr_re), .qr_issue_ready(qr_ready), .qr_addr(qr_addr), .qr_q(qr_q),
        .win_we(winwe), .win_waddr(winwa), .win_wdata(winwd), .win_re(winre), .win_raddr(winra), .win_q(winq),
        .hq_v(hv), .hq_rdy(hr), .hq_addr(ha), .hq_len(hl), .hq_tag(ht), .hq_room(room),
        .hr_v(rv), .hr_rdy(rr), .hr_tag(rt), .hr_beat(rb), .hr_data(rd),
        .fault(qs_fault), .fault_why(qs_why), .st_fetched(qs_fetched), .st_consumed(qs_consumed));
    ot_chip_v41x_shared_hbm_model #(.MEM_WORDS(MEMW), .WTAGW(LWIN)) hbm (
        .clk(clk), .rst_n(rst_n), .kbase(30'b0), .kcount(30'd65536), .wbase(30'(WBASE)), .wcount(30'd65536),
        .k_v(kv), .k_rdy(krdy), .k_addr(ka), .k_len(kl), .k_tag(544'b0), .k_we(32'b0), .k_data(8192'b0),
        .k_strb(1024'b0), .k_done(kdone), .kr_v(krv), .kr_rdy(32'hffffffff), .kr_tag(krtag), .kr_beat(krbeat),
        .kr_data(krdata),
        .w_v(hv), .w_rdy(hr), .w_addr(ha), .w_len(hl), .w_tag(ht), .w_room(room),
        .wr_v(rv), .wr_rdy(rr), .wr_tag(rt), .wr_beat(rb), .wr_data(rd), .fault(h_fault));
endmodule

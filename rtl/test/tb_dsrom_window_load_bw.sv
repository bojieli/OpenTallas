`timescale 1ns/1ps
// DS ROM WINDOW KV load bandwidth at the 1M target position (HBM path audit 2026-10-04).
// One die's per-layer WINDOW load: 128 packed rows (absolute positions 1,048,448..1,048,575, slot =
// row mod 128) x 17 sectors at the 544-B pitch from ONE HBM3E stack (WIN_STACK), on the timing-faithful
// refresh-live stack model ot_hdc_v41x_idx_hbm (32 PCs, W11 gate values QD 64 / RQD 32 / RW 16 /
// MAXSKIP 16 / REFPB 3, 10 ns controller+PHY each way) at the 1.2 GHz streaming clock (CLK_PS 833).
//   MODE 0: as built -- ot_chip_v41x_window_kv_prefetch, rows primed then prefetched one prefetch command
//           per row (the refill schedule's order), REFILL_CREDITS = CREDITS; its single tagged port is
//           steered to the PC the address maps to; responses return one a cycle (its one landing port).
//   MODE 1: ot_dsrom_window_stream_la (128-B granules on every PC of the stack, whole window in flight).
// Every staged row is compared with the backing array (codes 16 x 256 b + 16 scale bytes).
// Prints one BW line: cycles, first response, sectors, bytes, achieved TB/s and fraction of the stack peak.
module tb_dsrom_window_load_bw;
    parameter integer MODE = 1, CREDITS = 1, CLK_PS = 833;
    integer T0 = 3000; initial if ($value$plusargs("t0=%d", T0)) ;   // start cycle (refresh phase)
    localparam integer NPC = 32, AW = 24, TAGW = 16, LENW = 5, BEATW = 4, SLOTS = 128, PITCH = 17;
    localparam integer NSECT = SLOTS * PITCH;
    localparam longint POS = 1048575;
    reg clk = 0, rst_n = 0;
    always #(CLK_PS / 2000.0) clk = ~clk;
    longint cyc = 0; always @(posedge clk) cyc <= cyc + 1;

    function automatic [255:0] sector_data(input integer s);
        integer k; reg [255:0] d;
        k = s % PITCH;
        for (integer z = 0; z < 32; z = z + 1) begin
            if (k < 16) d[8*z +: 8] = 8'(((s * 31 + z * 7) % 127) | ((z & 1) << 7));
            else d[8*z +: 8] = (z < 16) ? 8'((s + z) & 8'h7f) : 8'((s * 13 + z) & 8'hff);
        end
        sector_data = d;
    endfunction
    function automatic [4223:0] row_exp(input integer slot);
        reg [4223:0] r;
        for (integer k = 0; k < 16; k = k + 1) r[256*k +: 256] = sector_data(slot * PITCH + k);
        r[4096 +: 128] = sector_data(slot * PITCH + 16);
        row_exp = r;
    endfunction
    function automatic integer pc_of(input [AW-1:0] s);
        pc_of = (((s >> 2) ^ (s >> 7) ^ (s >> 12)) & (NPC - 1));
    endfunction

    // ---------------- HBM stack ----------------
    wire [NPC-1:0] h_req_v, h_req_rdy, h_req_we, h_wr_done, h_rsp_v, h_rsp_rdy;
    wire [NPC*AW-1:0] h_req_addr; wire [NPC*LENW-1:0] h_req_len; wire [NPC*TAGW-1:0] h_req_tag, h_rsp_tag;
    wire [NPC*256-1:0] h_req_wdata, h_rsp_data; wire [NPC*32-1:0] h_req_wstrb; wire [NPC*BEATW-1:0] h_rsp_beat;
    ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .MEM_WORDS(4096), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
        .QD(64), .RQD(32), .RW(16), .MAXSKIP(16), .REFPB(3), .CLK_PS(CLK_PS), .MEM_MODE(0)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(h_req_v), .req_rdy(h_req_rdy), .req_addr(h_req_addr),
        .req_len(h_req_len), .req_tag(h_req_tag), .req_we(h_req_we), .req_wdata(h_req_wdata),
        .req_wstrb(h_req_wstrb), .wr_done(h_wr_done), .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy),
        .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat), .rsp_data(h_rsp_data));
    initial for (integer s = 0; s < 4096; s = s + 1) u_hbm.mem[s] = (s < NSECT) ? sector_data(s) : '0;

    longint t_start = -1, t_first = -1, t_done = -1;
    integer bad = 0, faulted = 0;
    integer beats_cnt = 0;
    always @(posedge clk) if (rst_n) begin
        automatic integer c = 0;
        for (integer p = 0; p < NPC; p = p + 1) if (h_rsp_v[p] && h_rsp_rdy[p]) c = c + 1;
        if (c != 0 && t_first < 0 && t_start >= 0) t_first = cyc;
        beats_cnt = beats_cnt + c;
    end

    generate if (MODE == 0) begin : g_asbuilt
        reg prime_v = 0, prefetch_v = 0, packed_re = 0;
        reg [20:0] prime_row = 0, prefetch_row = 0, packed_rrow = 0;
        wire prime_ready, prefetch_ready, packed_valid; wire [4223:0] packed_row;
        wire [3:0] m_v, m_we, m_wr_done, s_rdy; reg [3:0] s_v; wire [4*30-1:0] m_addr; wire [15:0] m_len;
        wire [4*TAGW-1:0] m_tag; reg [4*TAGW-1:0] s_tag; reg [15:0] s_beat; reg [4*256-1:0] s_data;
        wire [4*256-1:0] m_wdata; wire [127:0] m_wstrb; wire [3:0] m_rdy; wire fault; wire [4:0] fault_code;
        wire [31:0] st_rows; wire [31:0] st_rd, st_bw, st_sr, st_sw;
        ot_chip_v41x_window_kv_prefetch #(.REFILL_CREDITS(CREDITS), .WIN_STACK(0), .TAGW(TAGW)) u_dut (
            .clk(clk), .rst_n(rst_n), .region_base_sector(30'd0), .region_sector_count(30'(NSECT)),
            .prime_v(prime_v), .prime_ready(prime_ready), .prime_user(10'd0), .prime_row(prime_row),
            .blk_v(1'b0), .blk_ready(), .blk_user(10'd0), .blk_row(21'd0), .blk_idx(4'd0), .blk_codes(256'd0),
            .blk_scale(8'd0), .prefetch_v(prefetch_v), .prefetch_ready(prefetch_ready), .prefetch_user(10'd0),
            .prefetch_row(prefetch_row), .kv_ok(), .re(1'b0), .ruser(10'd0), .rrow(21'd0), .relem(9'd0), .q(),
            .packed_re(packed_re), .packed_ruser(10'd0), .packed_rrow(packed_rrow), .packed_ridx(4'd0),
            .packed_valid(packed_valid), .packed_row(packed_row), .packed_codes(), .packed_scale(),
            .bank_req_v(1'b0), .bank_req_ready(), .bank_req_user(10'd0), .bank_req_first(21'd0),
            .bank_req_mask(4'd0), .bank_rsp_v(), .bank_rsp_user(), .bank_rsp_first(), .bank_rsp_mask(),
            .bank_rsp_valid_mask(), .bank_rsp_rows(), .bank_rsp_fault(), .fault(fault), .fault_code(fault_code),
            .st_rows_fetched(st_rows), .st_blocks_written(st_bw), .st_sectors_read(st_sr),
            .st_sectors_written(st_sw), .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag),
            .m_we(m_we), .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wr_done(m_wr_done), .s_v(s_v), .s_rdy(s_rdy),
            .s_tag(s_tag), .s_beat(s_beat), .s_data(s_data));
        // request steering: the one tagged port -> the PC its sector maps to
        wire [AW-1:0] a0 = m_addr[AW-1:0];
        wire integer pc0 = pc_of(a0);
        for (genvar p = 0; p < NPC; p = p + 1) begin : g_req
            assign h_req_v[p] = m_v[0] && !m_we[0] && pc0 == p;
            assign h_req_addr[p*AW +: AW] = a0;
            assign h_req_len[p*LENW +: LENW] = LENW'(m_len[3:0]);
            assign h_req_tag[p*TAGW +: TAGW] = m_tag[TAGW-1:0];
        end
        assign h_req_we = 0; assign h_req_wdata = 0; assign h_req_wstrb = 0;
        assign m_rdy = {3'b0, h_req_rdy[pc0]}; assign m_wr_done = 0;
        // responses: one landing port, round robin over the PCs
        reg [4:0] rr = 0; reg [NPC-1:0] pick;
        always @* begin
            pick = 0;
            for (integer i = 0; i < NPC; i = i + 1) begin
                automatic integer p = (rr + i) % NPC;
                if (pick == 0 && h_rsp_v[p]) pick[p] = 1'b1;
            end
            s_v = 0; s_tag = 0; s_beat = 0; s_data = 0;
            for (integer p = 0; p < NPC; p = p + 1) if (pick[p]) begin
                s_v[0] = 1; s_tag[TAGW-1:0] = h_rsp_tag[p*TAGW +: TAGW]; s_beat[3:0] = h_rsp_beat[p*BEATW +: BEATW];
                s_data[255:0] = h_rsp_data[p*256 +: 256];
            end
        end
        assign h_rsp_rdy = pick;
        always @(posedge clk) if (|pick) rr <= rr + 1;
        initial begin
            repeat (10) @(posedge clk); rst_n = 1;
            for (integer r = 0; r < SLOTS; r = r + 1) begin
                @(negedge clk); prime_v = 1; prime_row = 21'(POS - 127 + r);
                @(posedge clk); while (!prime_ready) @(posedge clk);
            end
            @(negedge clk); prime_v = 0;
            while (cyc < T0) @(posedge clk);
            t_start = cyc;
            for (integer r = 0; r < SLOTS; r = r + 1) begin
                @(negedge clk); prefetch_v = 1; prefetch_row = 21'(POS - 127 + r);
                @(posedge clk); while (!prefetch_ready) @(posedge clk);
                @(negedge clk); prefetch_v = 0;
                @(posedge clk); while (!prefetch_ready && !fault) @(posedge clk);
                if (fault) begin $display("DUT FAULT code=%b row=%0d", fault_code, r); faulted = 1; r = SLOTS; end
            end
            t_done = cyc;
            for (integer r = 0; r < SLOTS; r = r + 1) begin
                @(negedge clk); packed_re = 1; packed_rrow = 21'(POS - 127 + r);
                #0.001;
                if (!packed_valid || packed_row !== row_exp(int'((POS - 127 + r) % 128))) begin
                    bad = bad + 1; if (bad < 4) $display("ROW MISMATCH row=%0d valid=%0d", r, packed_valid);
                end
            end
            @(negedge clk); packed_re = 0;
            report(st_sr);
        end
    end else begin : g_stream
        reg start = 0; wire busy, done, fault; wire [SLOTS-1:0] rv; reg [6:0] rd_slot = 0; wire [4223:0] rd_row;
        ot_dsrom_window_stream_la #(.ENABLE(1), .NPC(NPC), .AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW))
        u_dut (.clk(clk), .rst_n(rst_n), .start(start), .base(24'd0), .busy(busy), .done(done), .row_valid(rv),
            .fault(fault), .req_v(h_req_v), .req_rdy(h_req_rdy), .req_addr(h_req_addr), .req_len(h_req_len),
            .req_tag(h_req_tag), .req_we(h_req_we), .req_wdata(h_req_wdata), .req_wstrb(h_req_wstrb),
            .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy), .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat),
            .rsp_data(h_rsp_data), .rd_slot(rd_slot), .rd_row(rd_row));
        initial begin
            repeat (10) @(posedge clk); rst_n = 1;
            while (cyc < T0) @(posedge clk);
            @(negedge clk); start = 1; t_start = cyc + 1;
            @(negedge clk); start = 0;
            @(posedge clk); while (!done && !fault && cyc < T0 + 200000) @(posedge clk);
            t_done = cyc; if (fault) begin faulted = 1; $display("DUT FAULT"); end
            for (integer r = 0; r < SLOTS; r = r + 1) begin
                @(negedge clk); rd_slot = 7'(r); #0.001;
                if (!rv[r] || rd_row !== row_exp(r)) begin
                    bad = bad + 1; if (bad < 4) $display("ROW MISMATCH slot=%0d valid=%0d", r, rv[r]);
                end
            end
            report(32'(beats_cnt));
        end
    end endgenerate

    task automatic report(input [31:0] sectors_read);
        real ns, tbps, peak;
        ns = real'(t_done - t_start) * CLK_PS / 1000.0;
        tbps = real'(NSECT) * 32.0 / ns / 1000.0;          // bytes/ns = GB/s; /1000 = TB/s
        peak = 32.0 * 32.0 / 1.024 / 1000.0;               // 32 PCs x 32 B / 1,024 ps = 1.0 TB/s
        $display("BW mode=%0d credits=%0d clk_ps=%0d t0=%0d cycles=%0d first_rsp_cycles=%0d sectors=%0d sectors_read=%0d bytes=%0d ns=%0.1f tbps=%0.4f peak_tbps=%0.4f frac=%0.4f rd_lat_mean_ns=%0.1f rd_lat_max_ns=%0.1f bad=%0d fault=%0d",
            MODE, CREDITS, CLK_PS, T0, t_done - t_start, t_first - t_start, NSECT, sectors_read, NSECT * 32, ns,
            tbps, peak, tbps / peak,
            (beats_cnt > 0) ? real'(u_hbm.st_rd_lat_sum) / beats_cnt / 1000.0 : 0.0, real'(u_hbm.st_rd_lat_max) / 1000.0,
            bad, faulted);
        $display("VERDICT %s", (bad == 0 && faulted == 0 && sectors_read == NSECT) ? "PASS" : "FAIL");
        $finish;
    endtask
endmodule

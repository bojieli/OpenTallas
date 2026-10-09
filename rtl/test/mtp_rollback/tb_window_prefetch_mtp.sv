`timescale 1ns/1ps
// DS ROM window KV prefetch under DSpark MTP rollback (stream mtp-rollback, review MR-1, 2026-10-09).
// DUT: ot_chip_v41x_window_kv_prefetch_r256 (WINDOW_SLOTS = 256 HBM ring, 128-row on-die stage) behind a
// one-stack HBM sector model with back-pressure.  Prefill PRE positions, then STEPS speculative steps: each step
// writes the verify pass's rows q+1 .. q+1+g (16 blocks each, content a function of (position, step): a rejected
// row differs from the committed row the same position gets later), commits n = q+2+a (a in 0..g, mixed), and
// then reads the WHOLE window of the next query (positions n-127 .. n-1) through prefetch -> packed_row, each
// compared with the committed row.  Rollback is nothing but the anchor: the DUT is never told about a rejection.
// WINDOW_SLOTS = 128 (as built) is the mutant: a rejected row clobbers committed row p-128 -> fault / mismatch.
module tb_window_prefetch_mtp;
    parameter integer WINDOW_SLOTS = 256;
    parameter integer PRE = 140;
    parameter integer STEPS = 120;
    parameter integer CREDITS = 1;
    localparam integer SEC_W = 30, HAW = 30, TAGW = 16, G = 5;
    localparam integer BASE = 64, COUNT = 256 * 17;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg blk_v = 0, prefetch_v = 0;
    reg [20:0] blk_row = 0, prefetch_row = 0;
    reg [3:0] blk_idx = 0;
    reg [255:0] blk_codes = 0;
    reg [7:0] blk_scale = 0;
    wire blk_ready, prime_ready, prefetch_ready, kv_ok, fault;
    wire [31:0] q, st_rows, st_blocks, st_reads, st_writes;
    wire packed_valid; wire [4223:0] packed_row;
    wire [255:0] packed_codes; wire [7:0] packed_scale;
    wire [4:0] fault_code;
    wire [3:0] m_v, m_we, s_rdy;
    wire [4*HAW-1:0] m_addr;
    wire [15:0] m_len, s_beat;
    wire [4*TAGW-1:0] m_tag, s_tag;
    wire [1023:0] m_wdata, s_data;
    wire [127:0] m_wstrb;
    wire bank_req_ready, bank_rsp_v, bank_rsp_fault;
    reg [3:0] m_wr_done = 0, s_v = 0, m_rdy = 4'hf;
    reg [4*TAGW-1:0] rsp_tag = 0;
    reg [1023:0] rsp_data = 0;
    reg [255:0] mem [0:BASE+COUNT-1];
    integer errors = 0, faults = 0, cycles = 0, rows_checked = 0, steps_done = 0;
    integer addr, b;
    ot_chip_v41x_window_kv_prefetch_r256 #(.WIN_STACK(1), .WINDOW_SLOTS(WINDOW_SLOTS), .REFILL_CREDITS(CREDITS),
        .TAGW(TAGW)) dut (
        .clk(clk), .rst_n(rst_n), .region_base_sector(SEC_W'(BASE)), .region_sector_count(SEC_W'(COUNT)),
        .prime_v(1'b0), .prime_ready(prime_ready), .prime_user(10'd0), .prime_row(21'd0),
        .blk_v(blk_v), .blk_ready(blk_ready), .blk_user(10'd0), .blk_row(blk_row),
        .blk_idx(blk_idx), .blk_codes(blk_codes), .blk_scale(blk_scale),
        .prefetch_v(prefetch_v), .prefetch_ready(prefetch_ready),
        .prefetch_user(10'd0), .prefetch_row(prefetch_row), .kv_ok(kv_ok),
        .re(1'b0), .ruser(10'd0), .rrow(21'd0), .relem(9'd0), .q(q),
        .packed_re(1'b0), .packed_ruser(10'd0), .packed_rrow(prefetch_row), .packed_ridx(4'd0),
        .packed_valid(packed_valid), .packed_row(packed_row),
        .packed_codes(packed_codes), .packed_scale(packed_scale),
        .bank_req_v(1'b0), .bank_req_ready(bank_req_ready), .bank_req_user(10'd0), .bank_req_first(21'd0),
        .bank_req_mask(4'd0), .bank_rsp_v(bank_rsp_v), .bank_rsp_user(), .bank_rsp_first(), .bank_rsp_mask(),
        .bank_rsp_valid_mask(), .bank_rsp_rows(), .bank_rsp_fault(bank_rsp_fault),
        .fault(fault), .fault_code(fault_code),
        .st_rows_fetched(st_rows), .st_blocks_written(st_blocks),
        .st_sectors_read(st_reads), .st_sectors_written(st_writes),
        .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len),
        .m_tag(m_tag), .m_we(m_we), .m_wdata(m_wdata), .m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done), .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag),
        .s_beat(s_beat), .s_data(s_data));
    assign s_tag = rsp_tag;
    assign s_data = rsp_data;
    assign s_beat = 0;
    always @(posedge clk) begin
        cycles <= cycles + 1;
        m_rdy[1] <= (cycles % 3) != 0;
        m_wr_done <= 0; s_v <= 0;
        if (rst_n && m_v[1] && m_rdy[1]) begin
            addr = m_addr[1*HAW +: HAW];
            if (addr < BASE || addr >= BASE+COUNT || m_len[1*4 +: 4] != 1) begin
                $display("BADADDR %0d", addr); errors = errors + 1;
            end else if (m_we[1]) begin
                for (b = 0; b < 32; b = b + 1)
                    if (m_wstrb[1*32+b]) mem[addr][8*b +: 8] <= m_wdata[1*256+8*b +: 8];
                m_wr_done[1] <= 1;
            end else begin
                rsp_tag[1*TAGW +: TAGW] <= m_tag[1*TAGW +: TAGW];
                rsp_data[1*256 +: 256] <= mem[addr];
                s_v[1] <= 1;
            end
        end
    end
    // row content of position p written by step s: FP8 codes < 0x7f (no poison), scale < 0xff
    function automatic [7:0] code(input integer p, input integer s, input integer blk, input integer byt);
        code = 8'((p * 7 + s * 29 + blk * 13 + byt * 3) % 120);
    endfunction
    function automatic [7:0] scl(input integer p, input integer s, input integer blk);
        scl = 8'((p * 5 + s * 11 + blk) % 200 + 1);
    endfunction
    function automatic [4223:0] image(input integer p, input integer s);
        integer k, y;
        begin
            image = '0;
            for (k = 0; k < 16; k = k + 1) begin
                for (y = 0; y < 32; y = y + 1) image[256*k + 8*y +: 8] = code(p, s, k, y);
                image[4096 + 8*k +: 8] = scl(p, s, k);
            end
        end
    endfunction
    integer committed_step [0:8191];         // the step whose write of position p was committed
    task automatic write_row(input integer p, input integer s);
        integer k, y;
        begin
            for (k = 0; k < 16; k = k + 1) begin
                while (!blk_ready) @(negedge clk);
                @(negedge clk);
                blk_row = 21'(p); blk_idx = 4'(k);
                for (y = 0; y < 32; y = y + 1) blk_codes[8*y +: 8] = code(p, s, k, y);
                blk_scale = scl(p, s, k);
                blk_v = 1;
                @(negedge clk); blk_v = 0;
                while (!blk_ready) @(negedge clk);
            end
        end
    endtask
    integer fault_seen = 0;
    task automatic check_row(input integer p);
        integer guard;
        begin
            while (!prefetch_ready) @(negedge clk);
            @(negedge clk); prefetch_row = 21'(p); prefetch_v = 1;
            @(negedge clk); prefetch_v = 0;
            guard = 0;
            while (!kv_ok && guard < 2000 && !(fault && !fault_seen)) begin @(negedge clk); guard = guard + 1; end
            if (fault && !fault_seen) begin
                fault_seen = 1; faults = faults + 1; errors = errors + 1;
                $display("FAULT step=%0d row=%0d code=%b", steps_done, p, fault_code);
            end else if (!packed_valid || packed_row !== image(p, committed_step[p])) begin
                errors = errors + 1;
                if (errors < 10) $display("MISMATCH step=%0d row=%0d valid=%0d", steps_done, p, packed_valid);
            end
            rows_checked = rows_checked + 1;
        end
    endtask
    integer p, s, j, g, a, qq, n, seed, k;
    integer hist [0:G];
    initial begin
        for (k = 0; k < BASE+COUNT; k = k + 1) mem[k] = 0;
        for (k = 0; k <= G; k = k + 1) hist[k] = 0;
        seed = 7;
        repeat (5) @(negedge clk); rst_n = 1;
        for (p = 0; p < PRE; p = p + 1) begin write_row(p, 0); committed_step[p] = 0; end
        qq = PRE - 1;
        for (s = 1; s <= STEPS; s = s + 1) begin
            g = (s % 7 == 3) ? 1 + (s % G) : G;
            a = (s <= 12) ? ((s - 1) % (G + 1)) : ($urandom(seed) % (g + 1));
            seed = seed + 1;
            if (a > g) a = g;
            hist[a] = hist[a] + 1;
            for (j = 0; j <= g; j = j + 1) write_row(qq + 1 + j, s);      // the verify pass's rows
            for (j = 0; j <= a; j = j + 1) committed_step[qq + 1 + j] = s; // commit q+1 .. q+1+a
            qq = qq + 1 + a;
            n = qq + 1;
            steps_done = s;
            for (p = n - 127; p <= n - 1; p = p + 1) check_row(p);        // the next query's window
            if (errors > 50) s = STEPS + 1;
        end
        $display("RESULT %s slots=%0d steps=%0d positions=%0d rows_checked=%0d errors=%0d faults=%0d acc=%0d/%0d/%0d/%0d/%0d/%0d refills=%0d cycles=%0d",
                 (errors == 0 && !fault && steps_done == STEPS) ? "PASS" : "FAIL", WINDOW_SLOTS, steps_done, qq + 1,
                 rows_checked, errors, faults, hist[0], hist[1], hist[2], hist[3], hist[4], hist[5], st_rows, cycles);
        $finish;
    end
endmodule

`timescale 1ns/1ps
module tb_chip_v41x_window_kv_prefetch;
    localparam integer SEC_W = 30, HAW = 30, TAGW = 16;
    localparam integer BASE = 64, COUNT = 2*2176;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg blk_v = 0, prime_v = 0, prefetch_v = 0, re = 0;
    reg [20:0] blk_row = 0, prefetch_row = 0, rrow = 0;
    reg [20:0] prime_row = 0;
    reg [9:0] user_id = 0;
    reg [3:0] blk_idx = 0;
    reg [255:0] blk_codes = 0;
    reg [7:0] blk_scale = 0;
    reg [8:0] relem = 0;
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
    reg [3:0] m_wr_done = 0, s_v = 0;
    reg [4*TAGW-1:0] rsp_tag = 0;
    reg [1023:0] rsp_data = 0;
    reg [255:0] mem [0:BASE+COUNT-1];
    integer errors = 0;
    integer addr, b;
    ot_chip_v41x_window_kv_prefetch #(.WIN_STACK(2)) dut (
        .clk(clk), .rst_n(rst_n), .region_base_sector(SEC_W'(BASE)),
        .region_sector_count(SEC_W'(COUNT)),
        .prime_v(prime_v), .prime_ready(prime_ready), .prime_user(user_id), .prime_row(prime_row),
        .blk_v(blk_v), .blk_ready(blk_ready), .blk_user(user_id), .blk_row(blk_row),
        .blk_idx(blk_idx), .blk_codes(blk_codes), .blk_scale(blk_scale),
        .prefetch_v(prefetch_v), .prefetch_ready(prefetch_ready),
        .prefetch_user(user_id), .prefetch_row(prefetch_row), .kv_ok(kv_ok),
        .re(re), .ruser(user_id), .rrow(rrow), .relem(relem), .q(q),
        .packed_re(1'b0), .packed_ruser(user_id), .packed_rrow(prefetch_row), .packed_ridx(4'd1),
        .packed_valid(packed_valid), .packed_row(packed_row),
        .packed_codes(packed_codes), .packed_scale(packed_scale),
        .fault(fault), .fault_code(fault_code),
        .st_rows_fetched(st_rows), .st_blocks_written(st_blocks),
        .st_sectors_read(st_reads), .st_sectors_written(st_writes),
        .m_v(m_v), .m_rdy(4'hf), .m_addr(m_addr), .m_len(m_len),
        .m_tag(m_tag), .m_we(m_we), .m_wdata(m_wdata), .m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done), .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag),
        .s_beat(s_beat), .s_data(s_data));
    assign s_tag = rsp_tag;
    assign s_data = rsp_data;
    assign s_beat = 0;
    always @(posedge clk) begin
        m_wr_done <= 0; s_v <= 0;
        if (rst_n && m_v[2]) begin
            addr = m_addr[2*HAW +: HAW];
            if (addr < BASE || addr >= BASE+COUNT || m_len[2*4 +: 4] != 1) begin
                $display("BADADDR %0d", addr); errors = errors + 1;
            end else if (m_we[2]) begin
                for (b = 0; b < 32; b = b + 1)
                    if (m_wstrb[2*32+b]) mem[addr][8*b +: 8] <= m_wdata[2*256+8*b +: 8];
                m_wr_done[2] <= 1;
            end else begin
                rsp_tag[2*TAGW +: TAGW] <= m_tag[2*TAGW +: TAGW];
                rsp_data[2*256 +: 256] <= mem[addr];
                s_v[2] <= 1;
            end
        end
    end
    task automatic push_block(input integer row, input integer idx);
        begin
            while (!blk_ready) @(negedge clk);
            @(negedge clk);
            blk_row = 21'(row); blk_idx = 4'(idx);
            blk_codes = {32{8'h38}}; blk_scale = (idx == 1) ? 8'h80 : 8'h7f;
            blk_v = 1;
            @(negedge clk); blk_v = 0;
            while (!blk_ready) @(negedge clk);
        end
    endtask
    task automatic fetch_row(input integer row);
        begin
            while (!prefetch_ready) @(negedge clk);
            @(negedge clk); prefetch_row = 21'(row); prefetch_v = 1;
            @(negedge clk); prefetch_v = 0;
            while (!kv_ok && !fault) @(negedge clk);
        end
    endtask
    task automatic check_elem(input integer row, input integer elem, input [31:0] expected);
        begin
            @(negedge clk); rrow = 21'(row); relem = 9'(elem); re = 1;
            @(negedge clk); re = 0;
            if (q !== expected) begin
                $display("BADQ row=%0d elem=%0d got=%h expected=%h", row, elem, q, expected);
                errors = errors + 1;
            end
        end
    endtask
    integer idx;
    integer context_fault_seen = 0;
    reg [4223:0] expected_row;
    initial begin
        for (idx = 0; idx < BASE+COUNT; idx = idx + 1) mem[idx] = 0;
        repeat (5) @(negedge clk); rst_n = 1;
        for (idx = 0; idx < 16; idx = idx + 1) push_block(0, idx);
        if (fault || st_blocks != 16 || st_writes != 32) errors = errors + 1;
        if (mem[BASE] !== {32{8'h38}} ||
            mem[BASE+16][7:0] !== 8'h7f ||
            mem[BASE+16][15:8] !== 8'h80 ||
            mem[BASE+16][255:128] !== 0) begin
            $display("BAD HBM image"); errors = errors + 1;
        end
        fetch_row(0);
        check_elem(0, 0, 32'h3f800000);
        check_elem(0, 31, 32'h3f800000);
        check_elem(0, 32, 32'h40000000);
        check_elem(0, 63, 32'h40000000);
        check_elem(0, 511, 32'h3f800000);
        if (!packed_valid || packed_codes !== {32{8'h38}} || packed_scale !== 8'h80)
            errors = errors + 1;
        for (idx = 0; idx < 16; idx = idx + 1)
            expected_row[256*idx +: 256] = mem[BASE+idx];
        expected_row[4096 +: 128] = mem[BASE+16][127:0];
        if (packed_row !== expected_row) begin
            $display("PACKED STAGE DIFFERS FROM HBM IMAGE"); errors = errors + 1;
        end
        if (fault || st_rows != 1 || st_reads != 17) errors = errors + 1;
        // The host may preload a historical packed row and then publish its
        // absolute position tag. No core-side block rewrite is required.
        for (idx = 0; idx < 17; idx = idx + 1) mem[BASE+17+idx] = mem[BASE+idx];
        @(negedge clk); prime_row = 1; prime_v = 1;
        @(negedge clk); prime_v = 0;
        fetch_row(1);
        check_elem(1, 32, 32'h40000000);
        // Row 128 replaces ring slot zero. The old absolute-position tag must
        // be rejected even though the HBM sector addresses are the same.
        for (idx = 0; idx < 16; idx = idx + 1) push_block(128, idx);
        fetch_row(128);
        check_elem(128, 32, 32'h40000000);
        // A second user's ring starts 2,176 sectors later and shares no HBM
        // bytes with the first user's slot zero.
        user_id = 1;
        for (idx = 0; idx < 16; idx = idx + 1) push_block(0, idx);
        fetch_row(0);
        check_elem(0, 32, 32'h40000000);
        if (mem[BASE+2176] !== {32{8'h38}}) errors = errors + 1;
        user_id = 0;
        for (idx = 0; idx < 16; idx = idx + 1) push_block(1048575, idx);
        fetch_row(1048575);
        check_elem(1048575, 511, 32'h3f800000);
        @(negedge clk); blk_row = 21'(1048576); blk_idx = 0;
        blk_codes = {32{8'h38}}; blk_scale = 8'h7f; blk_v = 1;
        @(negedge clk); blk_v = 0;
        @(negedge clk);
        context_fault_seen = fault_code[1] && st_writes == 128;
        if (!context_fault_seen) begin
            $display("1M BOUNDARY NOT REJECTED"); errors = errors + 1;
        end
        @(negedge clk); prefetch_row = 0; prefetch_v = 1;
        @(negedge clk); prefetch_v = 0;
        @(negedge clk);
        if (!fault || !fault_code[0]) begin
            $display("STALE ROW NOT REJECTED"); errors = errors + 1;
        end
        // A third user has no reserved sector slice; reject before issuing.
        user_id = 2;
        @(negedge clk); blk_row = 0; blk_idx = 0; blk_codes = {32{8'h38}};
        blk_scale = 8'h7f; blk_v = 1;
        @(negedge clk); blk_v = 0;
        @(negedge clk);
        if (!fault_code[1] || st_writes != 128) begin
            $display("UNRESERVED USER NOT REJECTED"); errors = errors + 1;
        end
        $display("WINDOW_KV rows=%0d blocks=%0d reads=%0d writes=%0d stale_fault=%0d region_fault=%0d context_fault=%0d errors=%0d",
                 st_rows, st_blocks, st_reads, st_writes, fault_code[0], fault_code[1], context_fault_seen, errors);
        if (errors == 0 && st_rows == 5 && st_blocks == 64 && st_reads == 85 && st_writes == 128)
            $display("PASS");
        else $display("FAIL");
        $finish;
    end
    initial begin #100000; $display("TIMEOUT"); $display("FAIL"); $finish; end
endmodule

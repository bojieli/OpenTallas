`timescale 1ns/1ps
// Supply bench of the bulk-copy engine (rtl/gpu/ot_gpu_bulk_copy.sv) against a behavioural HBM share:
// reads return after LAT + uniform[0, JIT] cycles in any order, at most one line per cycle, and no faster
// than RATE_PPM/1e6 lines per cycle (the SM's share of the die's sustained HBM bandwidth).  The tensor core
// takes one line per cycle whenever the staging has it.  Prints delivered lines over the measurement window
// and checks that the stream arrives in order and intact.
module tb_gpu_bulk_copy;
    parameter integer DEPTH = 1024, MAX_OUT = 512, LAT = 550, JIT = 100, RATE_PPM = 808594, NLINES = 40000;
    localparam integer TW = $clog2(DEPTH);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base; reg [23:0] d_lines;
    wire req_v; wire [31:0] req_addr; wire [TW-1:0] req_tag;
    reg rsp_v; reg [TW-1:0] rsp_tag; reg [1023:0] rsp_data;
    wire s_valid; wire [1023:0] s_data; wire [$clog2(MAX_OUT+1)-1:0] outstanding; wire idle;
    ot_gpu_bulk_copy #(.DEPTH(DEPTH), .MAX_OUT(MAX_OUT)) dut (
        .clk(clk), .rst_n(rst_n), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines),
        .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
        .s_valid(s_valid), .s_ready(1'b1), .s_data(s_data), .outstanding(outstanding), .idle(idle));
    // pending reads
    reg [31:0] p_addr [0:MAX_OUT-1];
    reg [TW-1:0] p_tag [0:MAX_OUT-1];
    integer p_rdy [0:MAX_OUT-1];
    reg p_use [0:MAX_OUT-1];
    integer cyc = 0, i, pick, credit_ppm = 0, got = 0, bad = 0, max_out = 0, seed = 11;
    integer t_first = -1, t_win0 = -1, n_win0 = 0, t_win1 = -1, n_win1 = 0;
    initial for (i = 0; i < MAX_OUT; i = i + 1) p_use[i] = 0;
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) begin
        rsp_v <= 1'b0;
        if (rst_n) begin
            // accept a request into a free pending entry
            if (req_v) begin
                pick = -1;
                for (i = 0; i < MAX_OUT; i = i + 1) if (!p_use[i] && pick < 0) pick = i;
                p_use[pick] = 1; p_addr[pick] = req_addr; p_tag[pick] = req_tag;
                p_rdy[pick] = cyc + LAT + (JIT > 0 ? ($urandom(seed) % (JIT + 1)) : 0);
            end
            // return at most one ready line a cycle, within the bandwidth share
            credit_ppm = credit_ppm + RATE_PPM;
            if (credit_ppm > 2000000) credit_ppm = 2000000;
            if (credit_ppm >= 1000000) begin
                pick = -1;
                for (i = 0; i < MAX_OUT; i = i + 1)
                    if (p_use[i] && p_rdy[i] <= cyc && (pick < 0 || p_rdy[i] < p_rdy[pick])) pick = i;
                if (pick >= 0) begin
                    rsp_v <= 1'b1; rsp_tag <= p_tag[pick];
                    rsp_data <= {32{p_addr[pick] ^ 32'h5a5a0000}};
                    p_use[pick] = 0;
                    credit_ppm = credit_ppm - 1000000;
                end
            end
        end
    end
    // consumer: in-order, intact
    always @(posedge clk) if (rst_n && s_valid) begin
        if (s_data !== {32{got[31:0] ^ 32'h5a5a0000}}) bad = bad + 1;
        if (got == 0) t_first = cyc;
        if (got == NLINES / 4) begin t_win0 = cyc; end
        if (got == 3 * NLINES / 4) begin t_win1 = cyc; end
        got = got + 1;
    end
    always @(posedge clk) if (outstanding > max_out) max_out = outstanding;
    initial begin
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(negedge clk); d_valid = 1; d_base = 0; d_lines = NLINES;
        @(negedge clk); d_valid = 0;
        wait (got == NLINES);
        repeat (2) @(posedge clk);
        $display("BULK depth=%0d max_out=%0d lat=%0d jit=%0d rate_ppm=%0d lines=%0d first_line=%0d window_lines=%0d window_cycles=%0d peak_outstanding=%0d bad=%0d",
                 DEPTH, MAX_OUT, LAT, JIT, RATE_PPM, got, t_first, NLINES / 2, t_win1 - t_win0, max_out, bad);
        $finish;
    end
    initial begin #50000000; $display("BULK TIMEOUT got=%0d", got); $finish; end
endmodule

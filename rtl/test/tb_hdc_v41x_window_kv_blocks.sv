`timescale 1ns/1ps
module tb_hdc_v41x_window_kv_blocks #(parameter integer SEPARATE_ROWS = 0);
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, cap_v = 0, issue = 0, blk_ready = 0;
    reg [29:0] cap_src_addr = 0, issue_src_base = 0, issue_kvt_base = 0;
    reg [255:0] cap_codes = 0;
    reg [7:0] cap_scale = 0;
    reg [20:0] issue_row = 0, issue_abs_row = 0;
    wire cap_ready, issue_ready, blk_v, fault;
    wire [29:0] blk_kvt_base, blk_first_elem;
    wire [20:0] blk_row, blk_kvt_row;
    wire [3:0] blk_idx;
    wire [255:0] blk_codes;
    wire [7:0] blk_scale;
    integer b, abs_case = 12345, local_case;
    ot_hdc_v41x_window_kv_blocks #(.SEPARATE_ROWS(SEPARATE_ROWS)) dut (
        .clk(clk), .rst_n(rst_n), .cap_v(cap_v), .cap_src_addr(cap_src_addr),
        .cap_codes(cap_codes), .cap_scale(cap_scale), .cap_ready(cap_ready),
        .issue(issue), .issue_src_base(issue_src_base),
        .issue_kvt_base(issue_kvt_base), .issue_row(issue_row), .issue_abs_row(issue_abs_row),
        .issue_ready(issue_ready), .blk_v(blk_v), .blk_ready(blk_ready),
        .blk_kvt_base(blk_kvt_base), .blk_row(blk_row), .blk_kvt_row(blk_kvt_row), .blk_idx(blk_idx),
        .blk_first_elem(blk_first_elem), .blk_codes(blk_codes),
        .blk_scale(blk_scale), .fault(fault));
    initial begin
        if (!$value$plusargs("ROW=%d", abs_case)) abs_case = 12345;
        local_case = SEPARATE_ROWS ? ((abs_case < 127) ? abs_case : 127) : abs_case;
        repeat (2) @(negedge clk);
        rst_n = 1;
        for (b = 0; b < 16; b = b + 1) begin
            if (!cap_ready) $fatal(1, "capture not ready at %0d", b);
            cap_v = 1; cap_src_addr = 30'd4096 + b*32;
            cap_codes = {32{8'(b)}}; cap_scale = 8'(127+b);
            @(negedge clk);
        end
        cap_v = 0;
        if (!issue_ready) $fatal(1, "row incomplete");
        issue = 1; issue_src_base = 4096; issue_kvt_base = 30'd32768;
        issue_row = 21'(local_case);
        issue_abs_row = 21'(abs_case);
        @(negedge clk);
        issue = 0;
        for (b = 0; b < 16; b = b + 1) begin
            if (!blk_v || blk_idx !== 4'(b) || blk_row !== 21'(abs_case) ||
                blk_kvt_row !== 21'(local_case) ||
                blk_kvt_base !== 30'd32768 || blk_codes !== {32{8'(b)}} ||
                blk_scale !== 8'(127+b) ||
                blk_first_elem !== 30'(32768 + ((local_case >> 4) << 13) + (b << 9) + (local_case & 15)))
                $fatal(1, "block mismatch %0d", b);
            // Hold both data and index for two cycles before accepting.
            repeat (2) @(negedge clk);
            if (blk_idx !== 4'(b) || blk_codes !== {32{8'(b)}})
                $fatal(1, "backpressure instability %0d", b);
            blk_ready = 1;
            @(negedge clk);
            blk_ready = 0;
        end
        if (blk_v || !cap_ready || fault) $fatal(1, "writer did not return cleanly");
        $display("PASS window KV exact block handoff abs=%0d local=%0d", abs_case, local_case);
        $finish;
    end
endmodule

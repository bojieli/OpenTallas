`timescale 1ns/1ps
// Numeric proof for ot_a3_vector_rms_norm at an arbitrary power-of-two width.
//
// The G1f geometry probe (rtl/test/tb_a3_g1f_reduced_geometry.sv) asks only
// whether the engine ADMITS a geometry -- it feeds BF16 1.0 for every operand
// and compares no value.  When the engine's mean reciprocal stopped being one
// of two hardcoded constants and became derived from the width, "err = 0" was
// no longer enough: a derived reciprocal could admit a width and compute it
// wrongly.  This drives real operands from a hex image and dumps the results
// so the caller can compare them, word for word, against
// runtime/reference/tensor_accelerator_rmsnorm.py.
//
// Driven by tests/test_a3_rms_norm_width.py, which supplies the operands and
// makes the comparison.  Both shipped Qwen widths are positive controls, so a
// regression at 4,096 or 128 fails here too.
module tb_a3_rms_norm_width;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    reg [31:0] cnt = 0, rows = 0, cols = 0;

    reg [31:0] inmem [0:8191];
    reg [31:0] wmem  [0:8191];
    reg [31:0] omem  [0:8191];

    wire in_en, w_en, out_we;
    wire [31:0] in_addr, w_addr, out_addr, out_data;
    reg  [31:0] in_data = 0, w_data = 0;
    wire busy, done;
    wire [7:0] err;
    wire [31:0] results, sats, work;

    always @(posedge clk) begin
        in_data <= in_en ? inmem[in_addr[12:0]] : 32'd0;
        w_data  <= w_en  ? wmem[w_addr[12:0]]   : 32'd0;
        if (out_we) omem[out_addr[12:0]] <= out_data;
    end

    ot_a3_vector_rms_norm rms (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_count(cnt), .cfg_rows(rows), .cfg_cols(cols),
        .cfg_epsilon_bits(32'h3586_37bd),
        .cfg_input_base(32'd0), .cfg_weight_base(32'd0), .cfg_output_base(32'd0),
        .input_rd_en(in_en), .input_rd_addr(in_addr), .input_rd_data(in_data),
        .weight_rd_en(w_en), .weight_rd_addr(w_addr), .weight_rd_data(w_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(err),
        .result_count(results), .saturation_count(sats), .work_count(work)
    );

    integer guard;
    initial begin
        if (!$value$plusargs("rows=%d", rows)) rows = 8;
        if (!$value$plusargs("cols=%d", cols)) cols = 16;
        cnt = rows * cols;
        for (guard = 0; guard < 8192; guard = guard + 1) omem[guard] = 32'hdeadbeef;
        $readmemh("in.hex", inmem);
        $readmemh("w.hex", wmem);
        repeat (4) @(negedge clk); rst_n = 1'b1; repeat (4) @(negedge clk);
        start = 1'b1; @(negedge clk); start = 1'b0;
        guard = 0;
        while (!done && guard < 40000000) begin @(posedge clk); guard = guard + 1; end
        $display("RMS rows=%0d cols=%0d count=%0d err=%0d results=%0d sats=%0d",
                 rows, cols, cnt, err, results, sats);
        $writememh("out.hex", omem, 0, cnt - 1);
        $finish;
    end
endmodule

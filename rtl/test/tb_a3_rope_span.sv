`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Numeric and cycle proof for ot_a3_vector_rope over a span of positions.
//
// A decode VECTOR.ROPE launch rotates one position.  A prefill launch rotates a
// span of them -- the same 83 launches the golden device reports for decode,
// each covering 16 positions -- against ITS OWN coefficient row per position.
// This bench drives real operands from hex images and dumps every written word
// so the caller can compare them, position by position, against
// runtime/reference/tensor_accelerator_rope.py.
//
// It also reports the cycles from start to done, which is what makes the
// pipelining claim measurable rather than structural: at span 1 the legacy
// qualified core is entered and the count is the shipped one, and with
// LANE_AT_SPAN1 the identical operand stream must produce the identical output
// image in about a quarter of the cycles.
//
// Driven by tests/test_a3_rope_span.py.  The shipped Qwen geometry is a positive
// control at span 1, so a regression on the decode path fails here too.
// ---------------------------------------------------------------------------
module tb_a3_rope_span #(
    parameter integer QUERY_HEADS = 32,
    parameter integer KEY_HEADS = 8,
    parameter integer HEAD_WIDTH = 128,
    parameter integer MAX_POSITION_SPAN = 65536,
    parameter integer LANE_AT_SPAN1 = 0,
    parameter integer ROW_BUFFERS = 4,
    parameter integer COEF_BUFFERS = 2,
    parameter integer OUT_BUFFERS = 2,
    //: Word capacity of the behavioural banks.  Sized for the largest case the
    //: caller runs (32 heads x 128 columns x 16 positions), not for a model.
    parameter integer BANK_WORDS = 131072
) ();
    localparam integer AW = $clog2(BANK_WORDS);

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    reg [31:0] rows = 0, cols = 0, span = 0, count = 0;

    reg [31:0] inmem [0:BANK_WORDS-1];
    reg [31:0] cmem  [0:BANK_WORDS-1];
    reg [31:0] omem  [0:BANK_WORDS-1];

    wire in_en, c_en, out_we;
    wire [31:0] in_addr, c_addr, out_addr, out_data;
    reg  [31:0] in_data = 0, c_data = 0;
    wire busy, done;
    wire [7:0] err;
    wire [31:0] results, sats, work;
    reg  [31:0] writes = 0;

    //: One-cycle synchronous read, which is what the engine bank port is: the
    //: shipped adapter consumes a response exactly one cycle after it asserts
    //: the enable.
    always @(posedge clk) begin
        in_data <= in_en ? inmem[in_addr[AW-1:0]] : 32'd0;
        c_data  <= c_en  ? cmem[c_addr[AW-1:0]]   : 32'd0;
        if (out_we) begin
            omem[out_addr[AW-1:0]] <= out_data;
            writes <= writes + 32'd1;
        end
    end

    ot_a3_vector_rope #(
        .QUERY_HEADS(QUERY_HEADS[31:0]),
        .KEY_HEADS(KEY_HEADS[31:0]),
        .HEAD_WIDTH(HEAD_WIDTH[31:0]),
        .MAX_POSITION_SPAN(MAX_POSITION_SPAN[31:0]),
        .LANE_AT_SPAN1(LANE_AT_SPAN1),
        .ROW_BUFFERS(ROW_BUFFERS),
        .COEF_BUFFERS(COEF_BUFFERS),
        .OUT_BUFFERS(OUT_BUFFERS)
    ) rope (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_count(count), .cfg_rows(rows), .cfg_cols(cols),
        .cfg_input_base(32'd0), .cfg_coefficient_base(32'd0),
        .cfg_output_base(32'd0),
        .input_rd_en(in_en), .input_rd_addr(in_addr), .input_rd_data(in_data),
        .coefficient_rd_en(c_en), .coefficient_rd_addr(c_addr),
        .coefficient_rd_data(c_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(err),
        .result_count(results), .saturation_count(sats), .work_count(work)
    );

    integer guard;
    integer cycles;
    reg [31:0] override_count;
    initial begin
        if (!$value$plusargs("rows=%d", rows)) rows = QUERY_HEADS;
        if (!$value$plusargs("span=%d", span)) span = 1;
        cols = HEAD_WIDTH;
        count = rows * cols * span;
        //: A deliberately malformed count, for the negative controls.
        if ($value$plusargs("count=%d", override_count)) count = override_count;
        for (guard = 0; guard < BANK_WORDS; guard = guard + 1)
            omem[guard] = 32'hdeadbeef;
        $readmemh("rope_in.hex", inmem);
        $readmemh("rope_coef.hex", cmem);
        repeat (4) @(negedge clk); rst_n = 1'b1; repeat (4) @(negedge clk);
        start = 1'b1; @(negedge clk); start = 1'b0;
        cycles = 0;
        guard = 0;
        while (!done && guard < 400000000) begin
            @(posedge clk);
            guard = guard + 1;
            cycles = cycles + 1;
        end
        $display("ROPE rows=%0d cols=%0d span=%0d count=%0d err=%0d results=%0d work=%0d sats=%0d writes=%0d cycles=%0d canary=%08x",
                 rows, cols, span, count, err, results, work, sats, writes,
                 cycles, omem[count[AW-1:0]]);
        if (err == 8'd0)
            $writememh("rope_out.hex", omem, 0, count - 1);
        $finish;
    end
endmodule

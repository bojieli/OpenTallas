`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Block campaign for the qualified 128-point transform,
// rtl/abi3/ot_a3_vector_hadamard.sv.
//
// The expected words come from the independent scalar reference
// ``runtime.reference.hadamard.hadamard_rotate_128_bf16``: seven
// ascending-stride binary32 butterfly stages, one multiplication by the exact
// binary32 encoding of 1/sqrt(128), and one BF16 round-to-nearest-even
// conversion, in that order.  The comparison is per word, so a datapath that
// reaches the same answer with a different number of roundings is wrong here.
//
// This testbench exists because the block had no RTL campaign at all, and
// because its working buffer was restructured from MAX_ROWS*WIDTH entries to
// WIDTH entries -- processing one row at a time.  That restructure is only
// legitimate because no butterfly pair crosses a row boundary, and this
// campaign is what demonstrates the rows still come out bit-identical.
// ---------------------------------------------------------------------------
module tb_a3_vector_hadamard;
    localparam integer WIDTH = 128;
    localparam integer ROWS = 3;
    localparam integer ELEMENTS = ROWS * WIDTH;
    localparam [31:0] SENTINEL = 32'hdead_beef;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] input_mem    [0:ELEMENTS-1];
    reg [31:0] expected_mem [0:ELEMENTS-1];
    reg [31:0] observed_mem [0:ELEMENTS-1];

    // 4096 bits, not 128: a short register silently keeps only the TAIL of a
    // long path, so $readmemh then fails on a truncated name and the run
    // reports a mismatch or a timeout instead of a load failure.
    reg [4095:0] input_path;
    reg [4095:0] expected_path;

    wire        a_rd_en;
    wire [31:0] a_rd_addr;
    reg  [31:0] a_rd_data;
    wire        out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    wire        busy;
    wire        done;
    wire [7:0]  error_code;
    wire [31:0] out_count;

    integer i;
    integer mismatches;
    integer cycles;

    ot_a3_vector_hadamard dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_rows(16'(ROWS)), .cfg_cols(16'(WIDTH)),
        .cfg_count(32'(ELEMENTS)), .cfg_dtype_a(8'h10),
        .cfg_a_base(32'b0), .cfg_out_base(32'b0),
        .a_rd_en(a_rd_en), .a_rd_addr(a_rd_addr), .a_rd_data(a_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count)
    );

    // One-cycle read latency, matching the block's S_LOAD_WAIT.
    always @(posedge clk)
        if (a_rd_en && a_rd_addr < ELEMENTS)
            a_rd_data <= input_mem[a_rd_addr];

    always @(posedge clk)
        if (out_we && out_addr < ELEMENTS)
            observed_mem[out_addr] <= out_data;

    initial begin
        if (!$value$plusargs("input=%s", input_path)) begin
            $display("FAIL: missing +input=");
            $finish;
        end
        if (!$value$plusargs("expected=%s", expected_path)) begin
            $display("FAIL: missing +expected=");
            $finish;
        end
        $readmemh(input_path, input_mem);
        $readmemh(expected_path, expected_mem);
        for (i = 0; i < ELEMENTS; i = i + 1) observed_mem[i] = SENTINEL;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);
        start = 1'b1;
        @(posedge clk);
        start = 1'b0;

        cycles = 0;
        while (!done && cycles < 2000000) begin
            @(posedge clk);
            cycles = cycles + 1;
        end

        if (!done) begin
            $display("FAIL: timeout after %0d cycles", cycles);
            $finish;
        end
        if (error_code != 8'd0) begin
            $display("FAIL: error_code=%0d", error_code);
            $finish;
        end
        if (out_count != ELEMENTS) begin
            $display("FAIL: out_count=%0d expected %0d", out_count, ELEMENTS);
            $finish;
        end

        mismatches = 0;
        for (i = 0; i < ELEMENTS; i = i + 1) begin
            if (observed_mem[i] !== expected_mem[i]) begin
                if (mismatches < 8)
                    $display("MISMATCH at %0d: observed %08x expected %08x",
                             i, observed_mem[i], expected_mem[i]);
                mismatches = mismatches + 1;
            end
        end

        if (mismatches == 0)
            $display("PASS: %0d words bit-identical to the scalar reference in %0d cycles",
                     ELEMENTS, cycles);
        else
            $display("FAIL: %0d of %0d words differ", mismatches, ELEMENTS);
        $finish;
    end
endmodule

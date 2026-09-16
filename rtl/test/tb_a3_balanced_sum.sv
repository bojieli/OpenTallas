`timescale 1ns/1ps
// The NUM-6.1 balanced tree against the reference's own association.
//
// Expectations come from tools/build_a3_balanced_sum_vectors.py, which CALLS
// runtime.tensor_accelerator.sparse_attention._balanced_sum. The association is
// the contract, so the generator also records, per case, whether a LEFT FOLD of
// the same 64 lanes gives a different number -- 5 of the 9 cases say yes, and
// those are the ones that make this bench about the tree rather than about
// addition.
module tb_a3_balanced_sum;
    localparam integer LANES = 64;

    reg clk = 0, rst_n = 0, start = 0;
    reg [LANES*32-1:0] lanes;
    wire busy, done;
    wire [31:0] total;
    wire [1:0] error_code;
    wire [31:0] add_count;

    reg [31:0] lmem [0:LANES-1];
    integer j, errors = 0;
    integer ncases, c;
    integer fh, code;
    reg [1023:0] name, path;
    reg [31:0] expected;

    ot_a3_reduction_balanced_sum #(.LANES(LANES)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .lanes(lanes),
        .busy(busy), .done(done), .total(total),
        .error_code(error_code), .add_count(add_count)
    );

    always #1 clk = ~clk;

    task go; begin
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %h\n", name, expected);
            for (j = 0; j < LANES; j = j + 1) lmem[j] = 32'd0;
            $sformat(path, "lanes_%0d.hex", c); $readmemh(path, lmem);
            for (j = 0; j < LANES; j = j + 1) lanes[j*32 +: 32] = lmem[j];
            go;

            if (total !== expected) begin
                $display("FAIL %0s got %08h expected %08h", name, total, expected);
                errors = errors + 1;
            end
            if (error_code !== 2'd0) begin
                $display("FAIL %0s error_code=%0d", name, error_code);
                errors = errors + 1;
            end
            //: A power-of-two tree performs exactly LANES-1 additions. One more
            //: or one fewer is a different association even if the number came
            //: out right on this data.
            if (add_count !== LANES - 1) begin
                $display("FAIL %0s performed %0d adds, a %0d-lane tree is %0d",
                         name, add_count, LANES, LANES - 1);
                errors = errors + 1;
            end
            $display("  %0s: total=%08h adds=%0d", name, total, add_count);
        end
        $fclose(fh);

        if (errors == 0)
            $display("PASS a3_balanced_sum: %0d cases match the reference association at %0d adds each", ncases, LANES - 1);
        else
            $display("FAIL a3_balanced_sum: %0d errors", errors);
        $finish;
    end
endmodule

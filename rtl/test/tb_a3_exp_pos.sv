`timescale 1ns/1ps
// The positive-argument exponential against exp_cr32 itself.
//
// ot_a3_fp32_exp_pos_cr_rne claims to be CORRECTLY ROUNDED, so the authority is
// runtime.tensor_accelerator.sparse_attention.exp_cr32 -- the same function that
// supplies ATTENTION.SPARSE's probabilities -- and nothing weaker would test the
// claim. tools/build_a3_exp_pos_vectors.py also recomputes the module's ln2 and
// log2(e) literals and refuses to build if either digit is wrong, so a mistyped
// constant is a build failure rather than a wrong last bit somewhere in range.
//
// The corpus targets the RANGE REDUCTION, which is what is new: arguments
// exactly on a multiple of ln2 (where the floor can fall either way), one ulp
// either side of those, the subnormal input edge, and the largest argument whose
// exponential is still finite.
module tb_a3_exp_pos;
    reg clk = 0, rst_n = 0;
    reg in_valid = 0;
    reg [31:0] argument_code;
    wire in_ready, out_valid;
    reg out_ready = 1;
    wire [31:0] result_code;
    wire [1:0] result_error;

    integer errors = 0, checked = 0;
    integer ncases, c, over_i;
    integer fh, code;
    reg [1023:0] name;
    reg [31:0] arg, want;

    ot_a3_fp32_exp_pos_cr_rne dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_ready(in_ready),
        .argument_code(argument_code),
        .out_valid(out_valid), .out_ready(out_ready),
        .result_code(result_code), .result_error(result_error)
    );

    always #1 clk = ~clk;

    task issue(input [31:0] a); begin
        wait (in_ready);
        @(negedge clk); argument_code = a; in_valid = 1;
        @(negedge clk); in_valid = 0;
        wait (out_valid); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %h %h %d\n", name, arg, want, over_i);
            issue(arg);
            checked = checked + 1;
            if (over_i) begin
                if (result_error !== 2'd3) begin
                    $display("FAIL %0s should overflow, error=%0d", name, result_error);
                    errors = errors + 1;
                end
            end else begin
                if (result_error !== 2'd0) begin
                    $display("FAIL %0s error=%0d (0=none,1=arg,2=uncertified,3=overflow)",
                             name, result_error);
                    errors = errors + 1;
                end else if (result_code !== want) begin
                    $display("FAIL %0s x=%08h got %08h expected %08h",
                             name, arg, result_code, want);
                    errors = errors + 1;
                end
            end
        end
        $fclose(fh);

        // -- refusals: this unit owns x > 0 only --------------------------
        issue(32'h00000000);                       //: +0
        if (result_error !== 2'd1) begin
            $display("FAIL +0 gave error %0d, expected ERR_ARGUMENT", result_error);
            errors = errors + 1;
        end
        issue(32'hbf800000);                       //: -1.0
        if (result_error !== 2'd1) begin
            $display("FAIL -1.0 gave error %0d, expected ERR_ARGUMENT", result_error);
            errors = errors + 1;
        end
        issue(32'h7f800000);                       //: +inf
        if (result_error !== 2'd1) begin
            $display("FAIL +inf gave error %0d, expected ERR_ARGUMENT", result_error);
            errors = errors + 1;
        end
        issue(32'h43000000);                       //: 128, past the finite range
        if (result_error !== 2'd3) begin
            $display("FAIL 128 gave error %0d, expected ERR_OVERFLOW", result_error);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_exp_pos: %0d arguments bit-identical to exp_cr32, and 4 refusals fail closed", checked);
        else
            $display("FAIL a3_exp_pos: %0d errors over %0d arguments", errors, checked);
        $finish;
    end
endmodule

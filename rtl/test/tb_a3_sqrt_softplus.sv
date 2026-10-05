`timescale 1ns/1ps
// VECTOR.SQRT_SOFTPLUS against the reference's own diagnostics.
//
// tools/build_a3_sqrt_softplus_vectors.py calls
// ``binary32_sqrt_softplus_rne_with_diagnostics``, which evaluates
// log(1+exp(x)) with exact rational interval enclosures, refines until both
// outward endpoints land in one binary32 rounding cell, and correctly rounds
// the square root of that already-rounded softplus.
//
// THREE THINGS ARE CHECKED, not one. The value, the intermediate softplus, and
// the BRANCH. The linear-threshold and proved-underflow branches return exactly
// right answers by construction -- softplus(x) = x, and softplus(x) = 0 -- so a
// device that reached one of them by accident would still agree on the value.
// Checking which branch ran is what separates a correct answer from a correct
// answer for the wrong reason.
module tb_a3_sqrt_softplus #(
    //: Overridden from the command line so one suite can measure the refusal
    //: rate at several fixed-point widths, which is how the width was chosen.
    parameter integer FRAC_BITS = 224,
    //: Also overridable, so the suite can be run at a term count where the
    //: series' tail is LARGE -- which is the only configuration in which the
    //: upper endpoint's tail bound is observable at all.
    parameter integer ATANH_TERMS = 56
);
    reg clk = 0, rst_n = 0, iv = 0;
    reg [31:0] a = 0;
    wire in_ready;
    wire [31:0] y, softplus_out;
    wire [1:0] error_code, branch_taken;
    wire ov, busy;

    ot_a3_vector_sqrt_softplus #(
        .FRAC_BITS(FRAC_BITS), .ATANH_TERMS(ATANH_TERMS)
    ) dut (
        .clk(clk), .rst_n(rst_n), .valid_in(iv), .in_ready(in_ready),
        .a(a), .y(y), .error_code(error_code), .valid_out(ov),
        .busy(busy), .branch_taken(branch_taken), .softplus_out(softplus_out)
    );
    always #1 clk = ~clk;

    reg [31:0] vin  [0:8191];
    reg [31:0] vout [0:8191];
    reg [31:0] vbr  [0:8191];
    reg [31:0] vsp  [0:8191];
    integer i, n, errors = 0, shown = 0, fh, code;
    integer uncertified = 0;
    integer br_seen [0:2];

    initial begin
        fh = $fopen("sp_count.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open sp_count.txt"); $finish; end
        code = $fscanf(fh, "%d\n", n);
        $fclose(fh);
        $readmemh("sp_in.hex", vin);
        $readmemh("sp_out.hex", vout);
        $readmemh("sp_branch.hex", vbr);
        $readmemh("sp_softplus.hex", vsp);
        for (i = 0; i < 3; i = i + 1) br_seen[i] = 0;

        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;
        for (i = 0; i < n; i = i + 1) begin
            @(negedge clk); a = vin[i]; iv = 1;
            @(negedge clk); iv = 0;
            wait (ov); @(negedge clk);
            br_seen[branch_taken] = br_seen[branch_taken] + 1;
            if (error_code == 2'd2) begin
                //: A refusal is not a wrong answer, but it is not a right one
                //: either: counted and reported, and the suite fails if any
                //: case the reference could certify this one could not.
                uncertified = uncertified + 1;
                if (shown < 12) begin
                    $display("FAIL %08h refused as uncertified, reference gave %08h",
                             vin[i], vout[i]);
                    shown = shown + 1;
                end
                errors = errors + 1;
            end else if (error_code != 2'd0) begin
                if (shown < 12) begin
                    $display("FAIL %08h error_code=%0d", vin[i], error_code);
                    shown = shown + 1;
                end
                errors = errors + 1;
            end else begin
                if (branch_taken !== vbr[i][1:0]) begin
                    if (shown < 12) begin
                        $display("FAIL %08h took branch %0d, reference took %0d",
                                 vin[i], branch_taken, vbr[i][1:0]);
                        shown = shown + 1;
                    end
                    errors = errors + 1;
                end
                if (softplus_out !== vsp[i]) begin
                    if (shown < 12) begin
                        $display("FAIL %08h softplus %08h expected %08h",
                                 vin[i], softplus_out, vsp[i]);
                        shown = shown + 1;
                    end
                    errors = errors + 1;
                end
                if (y !== vout[i]) begin
                    if (shown < 12) begin
                        $display("FAIL %08h got %08h expected %08h",
                                 vin[i], y, vout[i]);
                        shown = shown + 1;
                    end
                    errors = errors + 1;
                end
            end
        end

        //: A nonfinite operand must fail closed: the reference raises.
        @(negedge clk); a = 32'h7f80_0000; iv = 1; @(negedge clk); iv = 0;
        wait (ov); @(negedge clk);
        if (error_code !== 2'd1) begin
            $display("FAIL +inf gave error_code=%0d", error_code);
            errors = errors + 1;
        end
        @(negedge clk); a = 32'h7fc0_0000; iv = 1; @(negedge clk); iv = 0;
        wait (ov); @(negedge clk);
        if (error_code !== 2'd1) begin
            $display("FAIL NaN gave error_code=%0d", error_code);
            errors = errors + 1;
        end

        //: Every branch has to have run, or the suite silently covers one path.
        for (i = 0; i < 3; i = i + 1)
            if (br_seen[i] == 0) begin
                $display("FAIL branch %0d never ran", i);
                errors = errors + 1;
            end

        $display("  branches exercised: linear=%0d underflow=%0d transcendental=%0d",
                 br_seen[0], br_seen[1], br_seen[2]);
        if (errors == 0)
            $display("PASS a3_sqrt_softplus: %0d cases match the reference on value, intermediate softplus and branch, with no refusals, and a nonfinite operand fails closed", n);
        else
            $display("FAIL a3_sqrt_softplus: %0d errors of %0d (%0d uncertified)",
                     errors, n, uncertified);
        $finish;
    end
endmodule

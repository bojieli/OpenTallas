`timescale 1ns/1ps
// The tile scheduler's logical-work product, at the width it needs against the
// width it was written at.
//
// ot_a3_vector_mhc_pre_tile_scheduler computes
//
//     logical_work = {32'd0, tokens} * {32'd0, fields} * {32'd0, k}
//
// which asks synthesis for two 64x64 multipliers and put 38 FAx1 full adders in
// one ripple chain to tile_logical_work[63] -- 237.4 MHz routed, below the design
// limiter.  Two of the three operands are bounded by CONSTANTS in that module for
// every tile kind: fields_total is 24, 8 or 16 and k_total is 16,384 or 1, and the
// state machine advances each base only while base + active < total, so no base
// ever exceeds its total and
//
//     active_field_count <= 24    (5 bits)
//     active_k_count     <= 16384 (15 bits)
//
// This bench is the equivalence that licences narrowing them.  It drives the two
// forms over the whole bounded space it can enumerate and a wide random sample of
// token counts, and it also drives values OUTSIDE the bound -- not to pass, but to
// record exactly where the two forms part, so the bound is documented by
// measurement rather than assumed.
module tb_a3_tile_work_product_equiv;
    integer errors = 0, checks = 0, outside = 0, t;
    reg [31:0] tokens, fields, k;
    reg [63:0] wide, narrow;

    // the form as written: three zero-extended 64-bit operands
    task compute_wide; begin
        wide = ({32'd0, tokens} * {32'd0, fields}) * {32'd0, k};
    end endtask

    // the form at the width the bound licences: 32 x 5 then 37 x 15
    reg [4:0]  n_fields;
    reg [14:0] n_k;
    reg [36:0] n_tf;
    reg [51:0] n_tfk;
    task compute_narrow; begin
        n_fields = fields[4:0];
        n_k      = k[14:0];
        n_tf     = {5'd0, tokens} * {32'd0, n_fields};
        n_tfk    = {15'd0, n_tf} * {37'd0, n_k};
        narrow   = {12'd0, n_tfk};
    end endtask

    task one(input [31:0] a, input [31:0] b, input [31:0] c); begin
        tokens = a; fields = b; k = c;
        compute_wide; compute_narrow;
        checks = checks + 1;
        if (b <= 32'd24 && c <= 32'd16384) begin
            if (wide !== narrow) begin
                errors = errors + 1;
                if (errors <= 8)
                    $display("FAIL in-bound tokens=%0d fields=%0d k=%0d wide=%0d narrow=%0d",
                             a, b, c, wide, narrow);
            end
        end else if (wide !== narrow) begin
            outside = outside + 1;
        end
    end endtask

    initial begin
        //: the whole bounded field range against the bounded k boundary values and
        //: a spread of token counts, including the 32-bit extremes
        for (fields = 0; fields <= 24; fields = fields + 1) begin
            one(32'd0,          fields, 32'd0);
            one(32'd1,          fields, 32'd1);
            one(32'd128,        fields, 32'd16384);
            one(32'd512,        fields, 32'd16383);
            one(32'd8192,       fields, 32'd4096);
            one(32'd262144,     fields, 32'd16384);
            one(32'hFFFF_FFFF,  fields, 32'd16384);
            one(32'h7FFF_FFFF,  fields, 32'd1);
        end
        //: every k boundary at the widest field
        for (k = 16380; k <= 16384; k = k + 1) one(32'd65535, 32'd24, k);
        //: a random sample inside the bound
        for (t = 0; t < 20000; t = t + 1)
            one($random, {$random} % 25, {$random} % 16385);
        //: and OUTSIDE it, to record where the forms part
        for (t = 0; t < 4000; t = t + 1)
            one($random, 32'd25 + ({$random} % 1000), 32'd16385 + ({$random} % 100000));

        if (errors == 0)
            $display("PASS a3_tile_work_product: %0d vectors, the narrowed product equals the 64-bit one for every fields<=24 and k<=16384 (%0d out-of-bound vectors differ, which is the bound)",
                     checks, outside);
        else
            $display("FAIL a3_tile_work_product: %0d of %0d in-bound vectors differ", errors, checks);
        $finish;
    end
endmodule

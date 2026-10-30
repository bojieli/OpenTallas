// ---------------------------------------------------------------------------
// Low-latency binary32 add and multiply (ot_hdc_qadd / ot_hdc_qmul) for the
// decode core's stream unit and special-function pipelines.
//
// Same arithmetic, bit for bit, as the qualified five-stage pipes they stand in
// for -- rtl/proto/ot_fp32_add_rne_pipe.sv and rtl/hdc/ot_hdc_fp32_mul_pipe.sv:
// IEEE RNE with gradual underflow, every zero result canonical +0, a zero
// multiplier operand giving +0, (+-0)+(+-0) = +0, and a nonfinite operand or an
// overflowing result failing closed through `err` with y = 0.  Equivalence is
// checked cycle by cycle against those pipes (rtl/test/tb_hdc_fastfp_equiv.sv).
//
// What is different is depth.  The five-stage pipes are cut around carry
// chains that the synthesis flow maps to ripple logic (a 31-bit magnitude
// compare, 28-bit adds, a 48-bit product sum, the rounding increment); here
// every carry chain is an explicit Kogge-Stone prefix network, the product is a
// carry-save tree, and the leading-zero count is a tree whose exponent-floor
// clamp is a sentinel bit, so each operation is three register stages.
// ---------------------------------------------------------------------------

// W-bit adder with carry-in, Kogge-Stone prefix carries.
module ot_hdc_ksa #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    reg [W:0] g, p, gn, pn;
    integer l, i;
    always @* begin
        g = {a & b, cin};
        p = {a ^ b, 1'b0};
        for (l = 1; l <= W; l = l * 2) begin
            gn = g;
            pn = p;
            for (i = l; i <= W; i = i + 1) begin
                gn[i] = g[i] | (p[i] & g[i - l]);
                pn[i] = p[i] & p[i - l];
            end
            g = gn;
            p = pn;
        end
    end
    assign s = (a ^ b) ^ g[W-1:0];
    assign cout = g[W];
endmodule

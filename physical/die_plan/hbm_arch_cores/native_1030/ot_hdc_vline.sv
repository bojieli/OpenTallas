// ---------------------------------------------------------------------------
// Special-function pipelines of the hardwired decode core: exp, reciprocal and
// reciprocal square root.  Each is an unrolled chain of the qualified binary32
// multiply/add pipes (LATENCY 5, II 1) plus single-cycle integer steps, so each
// accepts one operand per cycle and returns it a fixed DEPTH later.  No divider,
// no iteration, no combinational IEEE operation.
//
// The algorithms and their operation order are the specification in
// tools/hdc_golden.py (exp, reciprocal, rsqrt); the RTL matches it bit for bit.
// ---------------------------------------------------------------------------

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_vline #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule

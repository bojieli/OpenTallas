// S81-LEPFLF-HOLD sequential LEC of the f_lf status register (OT_S81SL_LEP_LFNEG).
// REF = the as-built rising-edge register; NEW = falling-edge pre-stage lf_n + rising-edge lf (lf_n exposed for the
// induction invariant only).  Launch = rising-edge flops q (as the lnland k_st / k_flt landing registers).
module lf_ref(input wire clk, input wire [1:0] l0_st, l1_st, input wire [2:0] l0_f, l1_f, output reg [3:0] lf);
    always @(posedge clk) lf <= {l1_st[0] | (|l1_f), l1_st[1], l0_st[0] | (|l0_f), l0_st[1]};
endmodule
module lf_new(input wire clk, input wire [1:0] l0_st, l1_st, input wire [2:0] l0_f, l1_f, output reg [3:0] lf,
              output reg [3:0] lf_n);
    always @(negedge clk) lf_n <= {l1_st[0] | (|l1_f), l1_st[1], l0_st[0] | (|l0_f), l0_st[1]};
`ifdef LEC_MUT
    always @(negedge clk) lf <= {l1_st[0] | (|l1_f), l1_st[1], l0_st[0] | (|l0_f), l0_st[1]};  // mutant: no rising stage
`else
    always @(posedge clk) lf <= lf_n;
`endif
endmodule
module lf_miter(input wire clk, input wire [9:0] din, output wire ok);
    reg [9:0] q;
    always @(posedge clk) q <= din;
    wire [3:0] a, b, bn;
    lf_ref r(.clk(clk), .l0_st(q[1:0]), .l1_st(q[3:2]), .l0_f(q[6:4]), .l1_f(q[9:7]), .lf(a));
    lf_new n(.clk(clk), .l0_st(q[1:0]), .l1_st(q[3:2]), .l0_f(q[6:4]), .l1_f(q[9:7]), .lf(b), .lf_n(bn));
    wire [3:0] fq = {q[2] | (|q[9:7]), q[3], q[0] | (|q[6:4]), q[1]};
    wire low = ~clk;                   // clock level = phase: low = after a falling edge (or start), high = after a rising edge
    // main property a == b, plus the induction invariant: low phase lf_n == f(q); high phase lf_n == lf
    assign ok = (a == b) && (low ? (bn == fq) : (bn == b));
endmodule

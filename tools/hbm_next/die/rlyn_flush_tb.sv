// HNX-DIE 10-20: reset-flush bench for the RESET-FREE relay hbfd_rlyn_<W>_<dir> (rtl/hbm_accel/die_glue/ot_hbm_rlyn.sv).
// A reset producer (async-clear register, value 0 in reset) feeds a chain of D reset-free stages; flops start RANDOM
// (Verilator --x-initial unique + +verilator+rand+reset+2).  The clock runs during reset for RCYC edges.  From the first
// edge after release, every cycle checks chain output == the same pipe built from reset flops (zero at power-up).
//   PASS iff RCYC >= D (the documented precondition).  Mutants: -DMUT_SHORT_RESET (RCYC = D/2) and +define+OT_HBM_RLYN_MUT
//   (bit 0 inverted in every stage) must FAIL.
`timescale 1ns/1ps
module tb_rlyn_flush;
    localparam int D = 13, W = 48;   // odd D: the per-stage bit-0 mutant does not cancel
`ifdef MUT_SHORT_RESET
    localparam int RCYC = D / 2;
`else
    localparam int RCYC = D + 2;
`endif
    reg clk = 0; always #1 clk = ~clk;
    reg rs_n = 0;
    integer cyc = 0, errs = 0, chk = 0;
    reg [W-1:0] p;                                   // producer: reset value 0, random data after release
    always @(posedge clk or negedge rs_n) if (!rs_n) p <= '0; else p <= {$random, $random};
    reg [W-1:0] h [0:D];                             // reference = the same pipe WITH reset (all zero at power-up)
    integer k;
    initial for (k = 0; k <= D; k = k + 1) h[k] = '0;
    always @(posedge clk) begin h[0] <= p; for (k = 1; k <= D; k = k + 1) h[k] <= h[k-1]; end
    wire [W-1:0] c [0:D];
    assign c[0] = p;
    genvar g;
    generate for (g = 0; g < D; g = g + 1) begin : st
        hbfd_rlyn_48_WE u (.ck(clk), .i(c[g]), .o(c[g+1]));
    end endgenerate
    // the consumer may read from its release on: chain output must equal the reset reference (h[D-1]) on every
    // post-release edge; an unflushed random stage visible after release is an error
    always @(negedge clk) begin
        cyc <= cyc + 1;
        if (rs_n) begin
            chk = chk + 1;
            if (c[D] !== h[D-1]) begin errs = errs + 1; if (errs < 5) $display("RLYN_FLUSH_MISMATCH cyc %0d got %h exp %h", cyc, c[D], h[D-1]); end
        end
    end
    initial begin
        repeat (RCYC) @(posedge clk); #0.5 rs_n = 1;
        repeat (400) @(posedge clk);
        $display("RLYN_FLUSH %s checks=%0d errors=%0d D=%0d RCYC=%0d", (errs == 0 && chk > 0) ? "PASS" : "FAIL", chk, errs, D, RCYC);
        $finish;
    end
endmodule

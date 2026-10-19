`timescale 1ns/1ps
// S81-SAFE-FIX/GUNIT (10-19): ot_hdc_sinkhorn_p (pipelined, core clock) == ot_hdc_sinkhorn (one normalisation per edge)
// bit for bit: y and fault of every case, and out_valid exactly LAT = 602 edges after the accepting edge.
// Inputs (xorshift, +SEED / +N): exp-like rows (2^-30 .. 1), wide-range rows (tiny .. 1, step-0 subnormal quotients),
// subnormal / zero rows (subnormal sums, 0/0), and fault words (negative, Inf, NaN, raw random).
// Cycle-driven (Verilator, main tb_sinkhorn_p_eq.cpp).  -DMUT=1 builds the one-stage-early mutant (must FAIL).
// Prints SKP PASS cases=<n> ... / SKP FAIL <errors>.
`ifndef MUT
`define MUT 0
`endif
module tb_sinkhorn_p_eq (input wire clk);
    localparam integer LAT = 602;
    reg rst_n, iv; reg [511:0] e;
    wire rr, rv, rf, rb, pr, pv, pf, pb; wire [511:0] ry, py;
    ot_hdc_sinkhorn #(.ITERS(20)) u_r (.clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(rr), .in_e(e),
        .out_valid(rv), .y(ry), .fault(rf), .busy(rb));
    ot_hdc_sinkhorn_p #(.ITERS(20), .MUT(`MUT)) u_p (.clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(pr), .in_e(e),
        .out_valid(pv), .y(py), .fault(pf), .busy(pb));
    integer N, c, k, cyc, ph, t0, errs, gotr, gotp, nf, ns, cls; reg [31:0] lf;
    reg [511:0] yr, yp; reg fr, fp;
    function [31:0] nx(input [31:0] x); reg [31:0] v; begin v = x ^ (x << 13); v = v ^ (v >> 17); nx = v ^ (v << 5); end endfunction
    task automatic word(input integer cl, input integer row, output [31:0] w);
        reg [31:0] a;
        begin
            lf = nx(lf); a = lf;
            case (cl)
                0: w = {1'b0, 8'(97 + a[28:24] % 30), a[22:0]};                 // exp-like
                1: w = {1'b0, 8'(1 + a[30:24] % 127), a[22:0]};                 // wide range
                2: w = (row == 1) ? {9'd0, a[22:0] >> a[27:23]} : {1'b0, 8'(100 + a[28:24] % 27), a[22:0]};  // subnormal row
                3: w = (row == 2) ? 32'd0 : {1'b0, 8'(110 + a[28:24] % 17), a[22:0]};  // zero row (0/0)
                4: w = (a[31:29] == 3'd0) ? {1'b1, a[30:0]} : (a[31:29] == 3'd1) ? 32'h7f800000 :
                       (a[31:29] == 3'd2) ? 32'h7fc00001 : {1'b0, 8'(115 + a[28:24] % 12), a[22:0]};  // fault words
                5: w = a;                                                         // raw
                6: w = (a[3:0] == 0) ? {9'd0, a[22:0]} : {1'b0, 8'(90 + a[28:24] % 37), a[22:0]};  // stray subnormals
                default: w = {1'b0, 8'd127, 23'd0} >> (a[1:0]);                  // 1.0 and exact-tie-prone words
            endcase
        end
    endtask
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 64;
        if (!$value$plusargs("SEED=%d", lf)) lf = 1;
        lf = lf ^ 32'h2545f491; if (lf == 0) lf = 1;
        cyc = 0; ph = 0; c = 0; errs = 0; nf = 0; ns = 0; rst_n = 0; iv = 0; e = 0;
    end
    reg [31:0] w;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1;
        // monitors (outputs of the previous edge)
        if (rv) begin gotr = 1; yr = ry; fr = rf; end
        if (pv) begin
            gotp = 1; yp = py; fp = pf;
            if (cyc - t0 != LAT + 1) begin errs = errs + 1; $display("ERR case %0d out_valid %0d edges after accept (want %0d)", c, cyc - t0 - 1, LAT); end   // seen one edge later
        end
        case (ph)
            0: if (cyc > 5 && rr && pr) begin
                lf = nx(lf); cls = lf % 8;
                for (k = 0; k < 16; k = k + 1) begin word(cls, k / 4, w); e[32*k +: 32] <= w; end
                iv <= 1; gotr = 0; gotp = 0; ph = 1;
            end
            1: begin iv <= 0; t0 = cyc; ph = 2; end   // the accepting edge is the one that ended the iv cycle
            2: if (gotr && gotp) begin
                if (yr !== yp || fr !== fp) begin
                    errs = errs + 1;
                    if (errs < 6) $display("ERR case %0d class %0d fault ref %0d pipe %0d y0 ref %h pipe %h", c, cls, fr, fp, yr[31:0], yp[31:0]);
                end
                if (fr) nf = nf + 1; else ns = ns + 1;
                c = c + 1; ph = (c == N) ? 3 : 0;
            end
            default: begin
                if (errs == 0) $display("SKP PASS cases=%0d (%0d normal, %0d fault) out_valid at accept + %0d", N, ns, nf, LAT);
                else $display("SKP FAIL %0d errors in %0d cases", errs, N);
                $finish;
            end
        endcase
    end
endmodule

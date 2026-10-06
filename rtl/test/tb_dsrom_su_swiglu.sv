`timescale 1ns/1ps
// DS-ROM recovery su_swiglu: ot_dsrom_su_swiglu (fused SwiGLU x route weight -> BF16 -> FP8 act-quant) on one
// node's golden operands, vectors back to back, timed at the unit's 1.2 GHz clock (tools/dsrom_su_swiglu.py).
//   g.mem / u.mem / w.mem   one binary32 word an element (N elements, N a multiple of W; padding lanes are +0)
//   a.mem                   the golden BF16 activation (as binary32) of the first NA elements
//   exp.mem                 per 32-element block {fault[3:0], e[11:0], q[255:0], y[511:0]} (aq_expect), NBLK blocks
// +N +NA +NBLK +LIM=<hex>.  Prints first input cycle, last output cycle, the checks.
module tb_dsrom_su_swiglu #(
    parameter integer W = 64,
    parameter integer ROUTED = 1,
    parameter integer NIN = 33,
    parameter integer NOUT = 23,
    parameter integer LM = 5,
    parameter integer LA = 4,
    parameter integer QLAT = 5,
    parameter integer IREG = 0
);
    localparam integer NB = W / 32;
    localparam integer MAXE = 8192;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0]  gm [0:MAXE-1];
    reg [31:0]  um [0:MAXE-1];
    reg [31:0]  wm [0:MAXE-1];
    reg [31:0]  am [0:MAXE-1];
    reg [783:0] ex [0:MAXE/32-1];
    integer n = 0, na = 0, nblk = 0;
    reg [31:0] lim = 32'h41200000;
    initial begin
        if (!$value$plusargs("N=%d", n)) n = 0;
        if (!$value$plusargs("NA=%d", na)) na = 0;
        if (!$value$plusargs("NBLK=%d", nblk)) nblk = 0;
        if (!$value$plusargs("LIM=%h", lim)) lim = 32'h41200000;
        $readmemh("g.mem", gm, 0, n - 1);
        $readmemh("u.mem", um, 0, n - 1);
        if (ROUTED != 0) $readmemh("w.mem", wm, 0, n - 1);
        $readmemh("a.mem", am, 0, na - 1);
        $readmemh("exp.mem", ex, 0, nblk - 1);
    end
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [32*W-1:0] g = 0, u = 0, w = 0;
    wire vo, fault;
    wire [8*W-1:0] q;
    wire [10*NB-1:0] e;
    wire [16*W-1:0] y;
    ot_dsrom_su_swiglu #(.W(W), .NIN(NIN), .NOUT(NOUT), .ROUTED(ROUTED), .LM(LM), .LA(LA), .QLAT(QLAT), .IREG(IREG)) dut (.clk(clk), .rst_n(rst_n), .v(v), .g(g),
        .u(u), .w(w), .lim(lim), .vo(vo), .q(q), .e(e), .y(y), .fault(fault));
    integer cyc = 0, iv = 0, oa = 0, ov = 0, ea = 0, eq = 0, idle = 0, l, b, k, blk, nchk = 0;
    integer first_in = -1, last_out = -1, a_first = -1, a_last = -1, sat = 0;
    reg [783:0] x;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        v <= 1'b0;
        if (cyc > 5 && iv < n / W) begin
            v <= 1'b1;
            for (l = 0; l < W; l = l + 1) begin
                g[32*l +: 32] <= gm[iv*W + l];
                u[32*l +: 32] <= um[iv*W + l];
                w[32*l +: 32] <= (ROUTED != 0) ? wm[iv*W + l] : 32'd0;
            end
            iv = iv + 1;
            if (first_in < 0) first_in = cyc + 1;
        end
        // the lanes' BF16 activation (the quantisers' input), against the golden
        if (rst_n && dut.av[0]) begin
            for (l = 0; l < W; l = l + 1) begin
                k = oa * W + l;
                if (k < na && dut.ab[32*l +: 32] !== am[k]) ea = ea + 1;
            end
            if (a_first < 0) a_first = cyc;
            a_last = cyc; oa = oa + 1;
        end
        if (rst_n && vo) begin
            for (b = 0; b < NB; b = b + 1) begin
                blk = ov * NB + b;
                if (blk < nblk) begin
                    x = ex[blk];
                    nchk = nchk + 1;
                    if (x[780] || fault || {e[10*b +: 10], q[256*b +: 256], y[512*b +: 512]} !== {x[777:768], x[767:0]})
                        eq = eq + 1;
                end
            end
            ov = ov + 1; last_out = cyc;
        end
        if (iv == n / W) idle = idle + 1;
        if (idle == 400) begin
            $display("SWG W=%0d n=%0d vectors=%0d a_errors=%0d blocks_checked=%0d q_errors=%0d first_in=%0d a_first=%0d a_last=%0d last_out=%0d",
                     W, n, n / W, ea, nchk, eq, first_in, a_first, a_last, last_out);
            if (ea == 0 && eq == 0 && nchk == nblk && oa == n / W && ov == n / W) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule

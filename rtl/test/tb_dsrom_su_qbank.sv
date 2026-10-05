`timescale 1ns/1ps
// DS-ROM recovery su_swiglu: ot_dsrom_su_qbank (NB quantiser instances, optional index-q RoPE front) on one node's
// golden blocks, NB blocks a beat back to back, timed at 1.2 GHz (tools/dsrom_su_swiglu.py).
//   x.mem    one binary32 word an element (NBLK*32 elements; padding to whole beats is +0)
//   cs.mem   ROPE: 32 cos words then 32 sin words
//   r.mem    ROPE: the golden BF16 rotated row values (the quantisers' input) of every element
//   exp.mem  per block {fault[3:0], e[11:0], q[255:0], y[511:0]} (aq_expect)
// +NBLK +FP4.
module tb_dsrom_su_qbank #(
    parameter integer NB = 32,
    parameter integer ROPE = 0,
    parameter integer NIN = 33,
    parameter integer NOUT = 23,
    parameter integer LM = 5,
    parameter integer LA = 4,
    parameter integer QLAT = 5
);
    localparam integer MAXB = 512;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg [31:0]  xm [0:MAXB*32-1];
    reg [31:0]  rm [0:MAXB*32-1];
    reg [31:0]  csm [0:63];
    reg [783:0] ex [0:MAXB-1];
    integer nblk = 0, fp4 = 0, nbeat = 0;
    reg [2047:0] cs = 0;
    integer i;
    initial begin
        if (!$value$plusargs("NBLK=%d", nblk)) nblk = 0;
        if (!$value$plusargs("FP4=%d", fp4)) fp4 = 0;
        nbeat = (nblk + NB - 1) / NB;
        for (i = 0; i < MAXB*32; i = i + 1) xm[i] = 32'd0;
        $readmemh("x.mem", xm, 0, nblk * 32 - 1);
        $readmemh("exp.mem", ex, 0, nblk - 1);
        if (ROPE != 0) begin
            $readmemh("cs.mem", csm, 0, 63);
            $readmemh("r.mem", rm, 0, nblk * 32 - 1);
            for (i = 0; i < 64; i = i + 1) cs[32*i +: 32] = csm[i];
        end
    end
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [1024*NB-1:0] x = 0;
    wire vo, fault;
    wire [256*NB-1:0] q;
    wire [10*NB-1:0] e;
    wire [512*NB-1:0] y;
    ot_dsrom_su_qbank #(.NB(NB), .NIN(NIN), .NOUT(NOUT), .ROPE(ROPE), .LM(LM), .LA(LA), .QLAT(QLAT)) dut (.clk(clk), .rst_n(rst_n), .v(v),
        .fp4(fp4 != 0), .x(x), .cs(cs), .vo(vo), .q(q), .e(e), .y(y), .fault(fault));
    integer cyc = 0, ib = 0, ob = 0, eq = 0, er = 0, idle = 0, b, k, blk, nchk = 0, orr = 0;
    integer first_in = -1, last_out = -1;
    reg [783:0] xx;
    reg [31:0] wv;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        v <= 1'b0;
        if (cyc > 5 && ib < nbeat) begin
            v <= 1'b1;
            for (k = 0; k < 32 * NB; k = k + 1) x[32*k +: 32] <= xm[ib*32*NB + k];
            ib = ib + 1;
            if (first_in < 0) first_in = cyc + 1;
        end
        if (ROPE != 0 && rst_n && dut.vq) begin           // the quantisers' input: bf16 of the rotated words
            for (k = 0; k < 32 * NB; k = k + 1) begin
                wv = dut.xr[32*k +: 32];
                wv = (wv + 32'h7FFF + {31'd0, wv[16]}) & 32'hFFFF0000;
                if (orr*32*NB + k < nblk*32 && wv !== rm[orr*32*NB + k]) er = er + 1;
            end
            orr = orr + 1;
        end
        if (rst_n && vo) begin
            for (b = 0; b < NB; b = b + 1) begin
                blk = ob * NB + b;
                if (blk < nblk) begin
                    xx = ex[blk];
                    nchk = nchk + 1;
                    if (xx[780] || fault || {e[10*b +: 10], q[256*b +: 256], y[512*b +: 512]} !== {xx[777:768], xx[767:0]})
                        eq = eq + 1;
                end
            end
            ob = ob + 1; last_out = cyc;
        end
        if (ib == nbeat) idle = idle + 1;
        if (idle == 200) begin
            $display("QBK NB=%0d ROPE=%0d nblk=%0d beats=%0d rope_errors=%0d blocks_checked=%0d q_errors=%0d first_in=%0d last_out=%0d",
                     NB, ROPE, nblk, nbeat, er, nchk, eq, first_in, last_out);
            if (eq == 0 && er == 0 && nchk == nblk && ob == nbeat) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule

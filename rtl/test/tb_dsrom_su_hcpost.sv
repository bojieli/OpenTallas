`timescale 1ns/1ps
// Bench of ot_dsrom_su_hcpost (DS-ROM recovery lever su_hcpost): golden beats from tools/dsrom_su_hcpost.py
// (+DIR=<case dir>: op.mem = comb[16] post[4] as one 640-bit word; in.mem = a beat a line {y[NG], r[NG*4]};
// exp.mem = a beat a line, out[NG*4]).  go and the first beat issue together at cycle 0, the beats back to back;
// prints the cycle the last output beat lands at the vector memory (end of the WOUT stages), counted from go as
// cycle 0, and the bit-exact compare of every output word.
module tb_dsrom_su_hcpost;
    parameter integer NG = 256;
    parameter integer WIN = 33;
    parameter integer WOUT = 23;
    parameter integer MAXB = 512;
    parameter integer ML = 5;
    parameter integer AL = 4;
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg go = 0, in_v = 0;
    reg [16*32-1:0] comb;
    reg [4*32-1:0]  post;
    reg [NG*4*32-1:0] in_r;
    reg [NG*32-1:0]   in_y;
    wire out_v, fault;
    wire [NG*4*32-1:0] out_d;
    ot_dsrom_su_hcpost #(.NG(NG), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL)) dut (.clk(clk), .rst_n(rst_n), .go(go), .comb(comb), .post(post),
        .in_v(in_v), .in_r(in_r), .in_y(in_y), .out_v(out_v), .out_d(out_d), .fault(fault));
    reg [20*32-1:0]    opm [0:0];
    reg [NG*5*32-1:0]  inm [0:MAXB-1];
    reg [NG*4*32-1:0]  exm [0:MAXB-1];
    integer nb, cyc, ob, errs, words, first_out, last_out, w;
    string dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NB=%d", nb)) nb = 20;
        $readmemh({dir, "/op.mem"}, opm);
        $readmemh({dir, "/in.mem"}, inm);
        $readmemh({dir, "/exp.mem"}, exm);
        comb = opm[0][16*32-1:0];
        post = opm[0][20*32-1:16*32];
        cyc = -4; ob = 0; errs = 0; words = 0; first_out = -1; last_out = -1;
        repeat (3) @(posedge clk);
        rst_n = 1;
    end
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        // drive (sampled by the DUT at the next edge = cycle cyc+1)
        if (cyc + 1 >= 0 && cyc + 1 < nb) begin
            go <= (cyc + 1 == 0);
            in_v <= 1'b1;
            {in_y, in_r} <= inm[cyc + 1];
        end else begin
            go <= 1'b0;
            in_v <= 1'b0;
        end
        if (out_v) begin
            if (first_out < 0) first_out = cyc;
            last_out = cyc;
            for (w = 0; w < NG * 4; w = w + 1) begin
                words = words + 1;
                if (out_d[32*w +: 32] !== exm[ob][32*w +: 32]) begin
                    if (errs < 8) $display("MISMATCH beat %0d word %0d got %08h want %08h", ob, w, out_d[32*w +: 32],
                                           exm[ob][32*w +: 32]);
                    errs = errs + 1;
                end
            end
            ob = ob + 1;
        end
        if (cyc > nb + WIN + WOUT + 64) begin
            // cycle numbering: go is sampled at cycle 0; an output seen at cycle c landed in the cycle-c register,
            // so go -> last landed write is last_out + 1 cycles (the SU records' last_write convention)
            $display("HCP nb=%0d beats_out=%0d words=%0d errors=%0d fault=%0d first_out=%0d last_out=%0d cycles=%0d %s",
                     nb, ob, words, errs, fault, first_out, last_out, last_out + 1,
                     (errs == 0 && ob == nb && !fault) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule

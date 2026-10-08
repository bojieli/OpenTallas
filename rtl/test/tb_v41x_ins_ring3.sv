`timescale 1ns/1ps
// RING 3 (generate-wired timing wheel) against RING 2 and the RING 0 shift line at the HBM SFU lane's u_l4 shape
// (KIND 1, MLAT 6, ALAT 6, DDIV 21, DENR 1: W 120, DEPTHS {D_SIG 122, D_EXP 94, 0}, DMAX 122) plus a K 7 shape.
// vo / coll / busy every cycle, q whenever vo.  +MUT: none (the negative is a source mutation of RING 3).
module tb_v41x_ins_ring3;
    parameter integer W = 120, K = 3, DMAX = 122;
    parameter [16*K-1:0] DEPTHS = {16'd122, 16'd94, 16'd0};
    parameter integer CYC = 200000;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg v; reg [K-1:0] sel; reg [W-1:0] d;
    wire vo0, vo2, vo3, c0, c2, c3, b0, b2, b3; wire [W-1:0] q0, q2, q3;
    ot_hdc_v41x_ins #(.W(W), .K(K), .DEPTHS(DEPTHS), .DMAX(DMAX), .RING(0)) u0 (clk, rst_n, v, sel, d, vo0, q0, c0, b0);
    ot_hdc_v41x_ins #(.W(W), .K(K), .DEPTHS(DEPTHS), .DMAX(DMAX), .RING(2)) u2 (clk, rst_n, v, sel, d, vo2, q2, c2, b2);
    ot_hdc_v41x_ins #(.W(W), .K(K), .DEPTHS(DEPTHS), .DMAX(DMAX), .RING(3)) u3 (clk, rst_n, v, sel, d, vo3, q3, c3, b3);
    integer i, err = 0, nvo = 0, ncoll = 0, k;
    integer seed = 12345;
    task rnd; begin
        v = ($random(seed) % 4) != 0;
        k = ($unsigned($random(seed)) % K);
        sel = {{(K-1){1'b0}}, 1'b1} << k;
        for (i = 0; i < W; i = i + 32) d[i +: 32] = $random(seed);
    end endtask
    initial begin
        v = 0; sel = 1; d = 0;
        repeat (3) @(negedge clk);
        rst_n = 1;
        repeat (CYC) begin
            @(negedge clk); rnd; #0.1;
            if (vo2 !== vo3 || c2 !== c3 || b2 !== b3 || vo0 !== vo3 || b0 !== b3 || c0 !== c3) begin
                err = err + 1; if (err < 10) $display("MISMATCH ctl t=%0t vo %b%b%b coll %b%b%b busy %b%b%b", $time, vo0, vo2, vo3, c0, c2, c3, b0, b2, b3);
            end
            if (vo3 && (q3 !== q2 || (!c0 && q3 !== q0))) begin
                err = err + 1; if (err < 10) $display("MISMATCH q t=%0t", $time);
            end
            nvo = nvo + vo3; ncoll = ncoll + c3;
        end
        if (err == 0) $display("PASS RING3==RING2==RING0 W=%0d K=%0d DMAX=%0d cycles=%0d vo=%0d coll=%0d", W, K, DMAX, CYC, nvo, ncoll);
        else $display("FAIL %0d mismatches", err);
        $finish;
    end
endmodule

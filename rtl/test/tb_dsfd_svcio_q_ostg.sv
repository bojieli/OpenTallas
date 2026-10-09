`timescale 1ns/1ps
// gaps-design 2026-10-08: dsfd_svcio_q OSTG bench: q_q = 4 x q delayed 3 + OSTG cycles, bit-exact on random words.
// MUT = 1 checks against the r3 latency (3) with OSTG = 1 and must FAIL.
module tb_dsfd_svcio_q_ostg; parameter OSTG=0, MUT=0;
reg ck=0; always #1 ck=~ck; reg [514:0] q; wire [2059:0] qq; integer i, bad=0, lat;
dsfd_svcio_q #(.OSTG(OSTG)) u(.ck(ck),.rst(1'b1),.q(q),.q_q(qq));
reg [514:0] h[0:63];
initial begin lat = 3+OSTG-MUT; for(i=0;i<60;i=i+1) begin @(negedge ck); q={17{$random}}; h[i]=q; if(i>=lat) if(qq!=={4{h[i-lat]}}) bad=bad+1; end
 $display("%s dsfd_svcio_q OSTG=%0d MUT=%0d bad=%0d", bad?"FAIL":"PASS", OSTG, MUT, bad); $finish; end endmodule

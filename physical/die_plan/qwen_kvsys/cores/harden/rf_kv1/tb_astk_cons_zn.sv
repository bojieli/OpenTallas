`timescale 1ns/1ps
module tb;
  reg ck=0; always #1 ck=~ck;
  reg rst_n=0; reg [3:0] zc; reg [14:0] tc; reg [137:0] zi; reg fi;
  wire [137:0] zo0, zo1, ho0, ho1; wire fo0, fo1, hf0, hf1;
  qkd_astk_zn    g (.ck(ck),.rst_n(rst_n),.zc(zc),.tc(tc),.zi(zi),.zo(zo0),.fi(fi),.fo(fo0));
  qkd_astk_zn_c  n (.ck(ck),.rst_n(rst_n),.zc(zc),.tc(tc),.zi(zi),.zo(zo1),.fi(fi),.fo(fo1));
  qkd_astk_zn_head_p   #(.ZC(4'b0110)) gh (.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zi),.zo(ho0),.fo(hf0));
  qkd_astk_zn_head_p_c #(.ZC(4'b0110)) nh (.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zi),.zo(ho1),.fo(hf1));
  integer i, k, bad=0, act=0, puts=0, seed, cycles; reg [13:0] T;
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    if (!$value$plusargs("cycles=%d", cycles)) cycles = 200000;
    zc = $random(seed); T = $random(seed); fi = 0;
    tc = {T, 1'b0}; zi = 0;
    repeat (4) @(negedge ck); rst_n = 1;
    for (i=0;i<cycles;i=i+1) begin
      @(negedge ck);
      if (({$random(seed)} % 3000) == 0) T = $random(seed);
      tc = {T, ({$random(seed)} % 997) == 0};
      for (k=0;k<5;k=k+1) zi[32*k +: 32] = $random(seed);
      zi[0] = ({$random(seed)} % 4) != 0;
      fi = ({$random(seed)} % 5000) == 0;
      if (i % 70000 == 35000) rst_n = 0; else rst_n = 1;
      if (g.put) puts = puts + 1;
      if (g.ov && g.ot[0]==0 && (|g.oa)) act = act + 1;
      if (i > 12 && (zo0 !== zo1 || fo0 !== fo1 || g.oa !== n.oa || g.ob !== n.ob || ho0 !== ho1 || hf0 !== hf1 || gh.oa !== nh.oa)) begin
        bad = bad + 1; if (bad < 5) $display("MISMATCH i=%0d oa %h / %h ho %h / %h", i, g.oa, n.oa, gh.oa, nh.oa); end
    end
    $display("SIM seed=%0d cycles=%0d puts=%0d oa_nonzero=%0d mismatches=%0d", seed, i, puts, act, bad); $finish;
  end
endmodule

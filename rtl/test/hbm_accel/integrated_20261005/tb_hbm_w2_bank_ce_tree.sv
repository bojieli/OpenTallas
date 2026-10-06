`timescale 1ns/1ps
// Minimum changed-source mechanism at the actual station37-word packet bank.
// Golden is the immutable original bank, compared every edge including repair.
// No owner/warm wrapper is invented; integration retains their existing hooks.
module tb_hbm_w2_bank_ce_tree;
 localparam WORDS=37;
 reg clk=0,por_n=0,load=0,load_encoded=0,fatal=0;
 reg [WORDS*64-1:0] d=0;
 reg [WORDS*72-1:0] encoded_d=0;
 wire [WORDS*64-1:0] qg,qt,qo;
 wire [WORDS*72-1:0] cg,ct,co;
 wire ng,nt,no,fg,ft,fo,rg,rt,ro;
 integer comparisons=0,repair_edges=0;
 always #0.416666667 clk=~clk;
 ot_hbm_w2_protected_bank #(.WORDS(WORDS)) gold(
  .clk(clk),.por_n(por_n),.load(load),.load_encoded(load_encoded),.fatal(fatal),
  .d(d),.encoded_d(encoded_d),.q(qg),.encoded_q(cg),.normal(ng),.fault(fg),.repairing(rg));
 ot_hbm_w2_protected_bank_ce_tree #(.WORDS(WORDS),.BALANCED_CE_SELECT(1)) tree(
  .clk(clk),.por_n(por_n),.load(load),.load_encoded(load_encoded),.fatal(fatal),
  .d(d),.encoded_d(encoded_d),.q(qt),.encoded_q(ct),.normal(nt),.fault(ft),.repairing(rt));
 ot_hbm_w2_protected_bank_ce_tree #(.WORDS(WORDS)) off(
  .clk(clk),.por_n(por_n),.load(load),.load_encoded(load_encoded),.fatal(fatal),
  .d(d),.encoded_d(encoded_d),.q(qo),.encoded_q(co),.normal(no),.fault(fo),.repairing(ro));
 task compare;begin
  if({qg,cg,ng,fg,rg}!=={qt,ct,nt,ft,rt})$fatal(1,"tree changed source behavior edge=%0d",comparisons);
  if({qg,cg,ng,fg,rg}!=={qo,co,no,fo,ro})$fatal(1,"defaultOFF changed source behavior");
  comparisons++;
 end endtask
 always @(negedge clk)begin #0.001;compare();end
 task mutate(input integer index,input [71:0] mask);begin
  gold.code[index]=gold.code[index]^mask;
  tree.g_tree.u_tree.code[index]=tree.g_tree.u_tree.code[index]^mask;
  off.g_legacy.u_legacy.code[index]=off.g_legacy.u_legacy.code[index]^mask;
 end endtask
 initial begin
  repeat(2)@(negedge clk);#0.01;por_n=1;
  for(integer w=0;w<WORDS;w++)d[w*64+:64]=64'h0123456789abcdef^(64'(w)<<32);
  load=1;@(negedge clk);#0.01;load=0;
  if(qt!==d||!nt)$fatal(1,"actual37word source capture mismatch");
  // Actual held payload; second load during correction must be refused.
  mutate(36,72'b1<<20);mutate(0,72'b1<<20);mutate(18,72'b1<<20);
  #0.01;if(nt||ft||!rt)$fatal(1,"CE did not withhold current permission");
  d=~d;load=1;
  while(rt)begin @(negedge clk);#0.01;repair_edges++;if(repair_edges>15)$fatal(1,"repair phase count changed");end
  load=0;
  if(repair_edges!=15||ft)$fatal(1,"three held stripes must take unchanged15edges");
  $display("PASS_CE_TREE_HELD_CORRECTION selected=0,18,36 repair_edges=%0d",repair_edges);
  // Mutable repair-controller corruption must refuse all normal permission.
  mutate(WORDS,(72'b1<<0)|(72'b1<<20));#0.01;
  if(!ft||nt)$fatal(1,"repair-controller DUE permission escaped");
  repeat(3)@(negedge clk);#0.01;
  if(!ft||nt)$fatal(1,"sticky refused control state changed");
  $display("PASS_CE_TREE_CURRENT_CONTROL_DUE_REFUSAL");
  $display("PASS_CE_TREE_FULL37_GOLDEN_DEFAULT_OFF comparisons=%0d",comparisons);$finish;
 end
endmodule

`timescale 1ns/1ps
`default_nettype none
// HBM-CORES-KITS-26 10-30: per-quarter reset release copies (selector GEOM-72 (a)) vs the main master before the change.
// Old (main ea152b24736) and new ot_hbm_idx_selector_static_sel run in lockstep on one random legal op stream (ops 0..7,
// production-like op2 ingest bursts, random k/pass/addr/in_line) with ASYNC rst_n pulses at random sub-cycle times
// (assert and release off the clock edge, pulses of 1..6 cycles, ops keep flowing through reset and release).
// Compared on EVERY clk edge: selected_v / selected_line / fault and every quarter's state (rv, rop, buf_q, fill, wp,
// tie_rem, comp_started, last_id, selected, qfault) plus all 4x64 hist words and ties. PASS needs 0 mismatches and
// >= NRST reset pulses and selected beats > 0. MUT=4 on the new master releases quarter 3 one edge early: must FAIL.
module tb_sel_rstq #(parameter integer NMUT=0, parameter integer SEED=11, parameter integer NCYC=60000, parameter integer NRST=40);
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg [3:0] op=0; reg [1:0] pass=0; reg [7:0] addr=0; reg [9:0] k=0; reg [2367:0] in_line=0;
 wire [3:0] osv, nsv; wire [2367:0] osl, nsl; wire of_, nf;
 ot_hbm_idx_selector_static_sel_old #(.STRUCT(1)) old_u(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),
  .op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(osv),.selected_line(osl),.fault(of_));
 ot_hbm_idx_selector_static_sel #(.MUT(NMUT),.STRUCT(1)) new_u(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),
  .op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(nsv),.selected_line(nsl),.fault(nf));
 integer cyc=0, mism=0, selbeats=0, seed=SEED, nrst=0, b;
 reg started=0;
 `define Q(q) \
   if (old_u.core.gq[q].rv!==new_u.core.gq[q].rv || old_u.core.gq[q].rop!==new_u.core.gq[q].rop || \
       old_u.core.gq[q].buf_q!==new_u.core.gq[q].buf_q || old_u.core.gq[q].fill!==new_u.core.gq[q].fill || \
       old_u.core.gq[q].wp!==new_u.core.gq[q].wp || old_u.core.gq[q].tie_rem!==new_u.core.gq[q].tie_rem || \
       old_u.core.gq[q].comp_started!==new_u.core.gq[q].comp_started || old_u.core.gq[q].last_id!==new_u.core.gq[q].last_id || \
       old_u.core.selected[q]!==new_u.core.selected[q] || old_u.core.ties[q]!==new_u.core.ties[q]) bad=1; \
   for (b=0;b<64;b=b+1) if (old_u.core.hist[q][b]!==new_u.core.hist[q][b]) bad=1;
 reg bad;
 always @(posedge clk) if (started) begin
  #0.2;
  cyc=cyc+1; bad=0;
  if (osv!==nsv || osl!==nsl || of_!==nf || old_u.core.qfault!==new_u.core.qfault) bad=1;
  `Q(0) `Q(1) `Q(2) `Q(3)
  if (bad) begin mism=mism+1; if (mism<6) $display("MISMATCH cyc %0d t=%0t rst_n %b sv %h/%h fault %b/%b qfault %b/%b", cyc, $time, rst_n, osv, nsv, of_, nf, old_u.core.qfault, new_u.core.qfault); end
  if (|osv) selbeats=selbeats+1;
 end
 task automatic rline; begin
  for (integer q=0;q<4;q=q+1) for (integer l=0;l<16;l=l+1)
   in_line[q*592+l*37 +: 37] = {20'($random(seed)), 16'($random(seed)), 1'($random(seed)%5!=0)};
 end endtask
 // async reset pulses, independent of the op stream
 initial begin
  #3.3 rst_n=1;
  forever begin
   #(200 + ($unsigned($random(seed)) % 3000) + 0.37);
   rst_n=0; nrst=nrst+1;
   #(1 + ($unsigned($random(seed)) % 11) + 0.61);
   rst_n=1;
  end
 end
 initial begin
  @(posedge clk); started=1;
  for (integer i=0;i<NCYC;i=i+1) begin
   if (($unsigned($random(seed)) % 50)==0) begin  // production-like burst: op1, op3, op2 ingest, op5 sweep, op4/op6
    k<=10'(1+($unsigned($random(seed))%512)); op<=1; @(posedge clk); op<=3; @(posedge clk);
    for (integer a=0;a<24;a=a+1) begin rline; op<=2; addr<=8'(a); @(posedge clk); end
    for (integer bb=31;bb>=0;bb=bb-1) begin op<=5; pass<=0; addr<=8'(bb); @(posedge clk); end
    for (integer a=0;a<24;a=a+1) begin op<=4; pass<=1; addr<=8'(a); @(posedge clk); end
    for (integer a=0;a<24;a=a+1) begin op<=6; pass<=2; addr<=8'(a); @(posedge clk); end
    i=i+130;
   end else begin
    rline; k<=10'($unsigned($random(seed))%600);
    op<=4'($unsigned($random(seed))%8); pass<=2'($unsigned($random(seed))%3); addr<=8'($random(seed));
    @(posedge clk);
   end
  end
  $display("TB_SEL_RSTQ cycles %0d resets %0d selected_beats %0d mismatches %0d", cyc, nrst, selbeats, mism);
  if (mism==0 && nrst>=NRST && selbeats>0) $display("TB_SEL_RSTQ PASS");
  else begin $display("TB_SEL_RSTQ FAIL"); $fatal(1, "per-quarter reset equivalence failed"); end
  $finish;
 end
endmodule

`timescale 1ns/1ps
`default_nettype none
// LH-UNREAD F-S: ot_hbm_idx_selector_static_sel (selected-only) vs canonical ot_hbm_idx_selector_static.
// Phase A: the production IDX compiler op stream (tools/hbm_idx_static_calendar.py compile_program: op1, op3, 171x op2
// ingest, op5 31..0, passes 1/2 op3 + 171x op4 + 2 drain + op5, 171x op6 compact) for NRUN key sets, plus a random
// legal-op phase (ops 0..7, never 8). selected_v / selected_line / fault must be identical EVERY cycle.
// Phase B: op 8 (emit) must raise the new master's sticky fault; the canonical keeps fault 0.
// SMUT: parameter of the NEW master only (1 = threshold mutant -> selected mismatch, 3 = drops the op8 fault).
module tb_hbm_idx_selector_sel_eq #(parameter integer SMUT=0, parameter integer NRUN=3, parameter integer SEED=7);
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg [3:0] op=0; reg [1:0] pass=0; reg [7:0] addr=0; reg [9:0] k=0; reg [2367:0] in_line=0;
 wire [3:0] rv_o, rsv, nsv; wire [2367:0] rl_o, rsl, nsl; wire [15:0] rthr; wire [55:0] robs; wire rf, nf;
 ot_hbm_idx_selector_static ref_u(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),
  .addr(addr),.k(k),.in_line(in_line),.out_v(rv_o),.out_line(rl_o),.threshold_observe(rthr),.selected_v(rsv),
  .selected_line(rsl),.selected_observe(robs),.fault(rf));
 ot_hbm_idx_selector_static_sel #(.MUT(SMUT)) new_u(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),
  .op(op),.pass(pass),.addr(addr),.k(k),.in_line(in_line),.selected_v(nsv),.selected_line(nsl),.fault(nf));
 integer cyc=0, mism=0, selbeats=0, seed=SEED; reg cmp=1, pre_ok=0;
 reg qf0_d=0; always @(posedge clk) begin qf0_d<=ref_u.core.qfault[0]; if (ref_u.core.qfault[0] && !qf0_d) $display("Q0 t=%0t rop=%0d raddr=%0d sel=%0d wp=%0d fill=%0d last_id=%0d", $time, ref_u.core.gq[0].rop, ref_u.core.gq[0].raddr, ref_u.core.selected[0], ref_u.core.gq[0].wp, ref_u.core.gq[0].fill, ref_u.core.gq[0].last_id); end
 always @(negedge clk) if (ref_u.core.gq[0].compact && (ref_u.core.gq[0].raddr>=169 || ref_u.core.gq[0].raddr<=1)) $display("PRE t=%0t raddr=%0d last_id=%0d id0=%0d v0=%b id15=%0d pw=%b wa=%0d sel=%0d ch=%0d", $time, ref_u.core.gq[0].raddr, ref_u.core.gq[0].last_id, ref_u.core.gq[0].raw[36:17], ref_u.core.gq[0].raw[0], ref_u.core.gq[0].raw[15*37+17+:20], ref_u.core.gq[0].pack_write, ref_u.core.gq[0].wa, ref_u.core.selected[0], ref_u.core.gq[0].chosen_next);
 reg rf_d=0; always @(posedge clk) begin rf_d<=rf; if (rf && !rf_d) $display("REF_FAULT_RISE t=%0t op=%0d pass=%0d addr=%0d k=%0d qfault=%b", $time, op, pass, addr, k, ref_u.core.qfault); end
 always @(posedge clk) if (rst_n && cmp) begin
  cyc<=cyc+1;
  if (rsv!==nsv || rsl!==nsl || rf!==nf) begin
   mism=mism+1; if (mism<5) $display("MISMATCH cyc %0d sv %h/%h fault %b/%b", cyc, rsv, nsv, rf, nf);
  end
  if (|rsv) selbeats=selbeats+1;
 end
 task automatic tick(input [3:0] o, input [1:0] p, input [7:0] a); begin op<=o; pass<=p; addr<=a; @(posedge clk); end endtask
 task automatic idle(input integer n, input [1:0] p); for (integer i=0;i<n;i=i+1) tick(0,p,0); endtask
 task automatic line(input integer a); begin
  for (integer q=0;q<4;q=q+1) for (integer l=0;l<16;l=l+1) begin
   in_line[q*592+l*37 +: 37] = {20'(a*16+l), 16'($random(seed)), 1'($random(seed)%5!=0)};
  end end endtask
 task automatic production(input [9:0] kk); begin
  k<=kk; tick(1,0,0); idle(16,0); idle(128+28+100,0);
  tick(3,0,0);
  for (integer i=0;i<294;i=i+1) begin
   if (i>=123) begin line(i-123); tick(2,0,8'(i-123)); end else tick(0,0,0);
  end
  idle(2,0); for (integer b=31;b>=0;b=b-1) tick(5,0,8'(b)); idle(1,0);
  for (integer ps=1;ps<=2;ps=ps+1) begin
   tick(3,2'(ps),0); for (integer a=0;a<171;a=a+1) tick(4,2'(ps),8'(a)); idle(2,2'(ps));
   for (integer b=(ps==2?63:31);b>=0;b=b-1) tick(5,2'(ps),8'(b)); idle(1,0);
  end
  for (integer a=0;a<171;a=a+1) tick(6,2,8'(a)); idle(3,0); idle(1+16*8+4,0);
 end endtask
 initial begin
  idle(4,0); rst_n=1; idle(4,0);
  for (integer r=0;r<NRUN;r=r+1) production(10'(1+($unsigned($random(seed))%512)));
  // random legal ops (never 8)
  for (integer i=0;i<4000;i=i+1) begin line($unsigned($random(seed))%256); k<=10'($unsigned($random(seed))%600);
   tick(4'($unsigned($random(seed))%8), 2'($unsigned($random(seed))%3), 8'($random(seed))); end
  idle(8,0);
  $display("PHASE_A cycles %0d selected_beats %0d mismatches %0d", cyc, selbeats, mism);
  // phase B (L2H-GEN2E fix): fresh reset, then ONE op 8 with no prior fault source (the earlier phase B ran production(64)
  // first, whose hand-built stream raised the canonical's own fault, so the precondition could never hold).
  cmp=0; rst_n=0; idle(4,0); rst_n=1; idle(8,0);
  pre_ok = (rf===0 && nf===0); $display("PHASE_B precondition fault ref %b new %b", rf, nf);
  tick(8,0,0); idle(6,0);
  $display("PHASE_B op8: ref fault %b new fault %b", rf, nf);
  if (mism==0 && selbeats>0 && pre_ok && nf===1 && rf===0) $display("TB_SEL_EQ PASS");
  else begin $display("TB_SEL_EQ FAIL"); $fatal(1, "selector sel equivalence failed"); end
  $finish;
 end
endmodule
`default_nettype wire

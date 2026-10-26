`timescale 1ns/1ps
`default_nettype none
// HBM-TIE 2026-10-17 (stub audit 0da, H-2): the top-k K of the IDX selector is a per-launch IDX operand issued by the
// IDX F20 collar col_idx (ot_hbm_static_cfg_collar, P_IDX params), operand row 5 bits [179:170] = prm[1459:1450],
// replacing the die strap .k(10'd512). The IDX calendar programme issues selector op 1 (clear frame) on a compiler-
// fixed edge after start_v; the selector core latches k on that op. The collar refuses any configuration frame while
// its launch runs, so K is stable for the whole launch (static, no handshake).
// Bench: two die selector masters (ot_hbm_idx_selector_static, pin-registered shell) run the same radix-select op
// calendar on the same score lines; REF gets K from the bench's launch record, DUT gets it from the collar's prm bits.
// Every output must agree on every edge, and each launch must select exactly K entries (sum of selected_observe).
// Two launches with different K (512, then 37), 4 quarters x 16 lanes x NL lines of valid scores.
// MUT: 1 DUT reads prm[1460:1451] (field off by one), 2 DUT K captured at the first launch only (no re-issue),
//      3 DUT K taken from row 4 (wrong operand row).
module tb;
 parameter integer MUT=0;
 localparam integer NL=24, EW=37, LW=592;
 reg clk=0; always #0.4165 clk=~clk;
 reg rst_n=0;
 integer cyc=0; always @(posedge clk) cyc<=cyc+1;
 // ---------------- host F20 broadcast
 reg cfg_v=0, desc_v=0, launch_v=0; reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0; reg [255:0] cfg_data=0;
 task automatic frame(input [11:0] a, input [255:0] d); begin
  @(negedge clk); cfg_v=1; cfg_target=8'd120; cfg_addr=a; cfg_data=d; @(negedge clk); cfg_v=0; repeat(3) @(negedge clk);
 end endtask
 task automatic desc_launch; begin
  @(negedge clk); desc_v=1; cfg_target=8'd120; @(negedge clk); desc_v=0; repeat(3) @(negedge clk);
  launch_v=1; @(negedge clk); launch_v=0;
 end endtask
 wire [0:0] pw_we; wire [11:0] pw_addr; wire [255:0] pw_data; wire [6*256-1:0] prm; wire start_v; wire [1:0] go;
 wire [220:0] rec; wire c_ready, c_active, c_fault;
 reg c_done=0;
 ot_hbm_static_cfg_collar #(.PAGE_W(1),.NS(1),.NPR(6),.NREC(8),.NGO(2),.NB(2),.NF(4),.XSER(0)) col_idx(
  .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),
  .cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.c_busy(2'b00),.c_done(c_done),.c_fault(4'b0),
  .pw_we(pw_we),.pw_addr(pw_addr),.pw_data(pw_data),.prm(prm),.start_v(start_v),.go(go),.rec(rec),
  .ready(c_ready),.active(c_active),.fault(c_fault));
 // ---------------- K as wired on the die (contract edge col_idx.prm[1450:1460] -> hb_idx__selector.k)
 reg [9:0] k_first; reg k_first_v=0;
 always @(posedge clk) if(start_v && !k_first_v) begin k_first<=prm[1459:1450]; k_first_v<=1; end
 wire [9:0] k_die = (MUT==1) ? prm[1460:1451] : (MUT==2 && k_first_v) ? k_first : (MUT==3) ? prm[1203:1194] : prm[1459:1450];
 reg [9:0] k_ref=0;
 // ---------------- selector op calendar (what the IDX calendar programme issues)
 reg [3:0] op=0; reg [1:0] pass=0; reg [7:0] addr=0; reg [2367:0] line=0;
 wire [3:0] ov_r,ov_d,sv_r,sv_d; wire [2367:0] ol_r,ol_d,sl_r,sl_d; wire [15:0] th_r,th_d; wire [55:0] so_r,so_d; wire f_r,f_d;
 ot_hbm_idx_selector_static ref_sel(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),
  .addr(addr),.k(k_ref),.in_line(line),.out_v(ov_r),.out_line(ol_r),.threshold_observe(th_r),.selected_v(sv_r),
  .selected_line(sl_r),.selected_observe(so_r),.fault(f_r));
 ot_hbm_idx_selector_static dut_sel(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(op),.pass(pass),
  .addr(addr),.k(k_die),.in_line(line),.out_v(ov_d),.out_line(ol_d),.threshold_observe(th_d),.selected_v(sv_d),
  .selected_line(sl_d),.selected_observe(so_d),.fault(f_d));
 integer checks=0;
 always @(negedge clk) if(rst_n) begin
  checks=checks+1;
  if({ov_r,sv_r,th_r,so_r,f_r}!=={ov_d,sv_d,th_d,so_d,f_d} || ol_r!==ol_d || sl_r!==sl_d)
   $fatal(1,"IDX_K_MISMATCH cycle=%0d k_ref=%0d k_die=%0d mut=%0d",cyc,k_ref,k_die,MUT);
 end
 function automatic [EW-1:0] entry(input integer q, input integer a, input integer l, input integer seed);
  reg [15:0] sc; reg [31:0] h;
  begin
   h = (q*7919 + a*104729 + l*1299709 + seed*15485863) ^ 32'h9e3779b9; h = h ^ (h>>13); h = h*32'h5bd1e995; h = h ^ (h>>15);
   sc = h[15:0];
   entry = {20'(a*16+l), sc, 1'b1};
  end
 endfunction
 task automatic issue(input [3:0] o, input [1:0] p, input [7:0] a); begin
  @(negedge clk); op=o; pass=p; addr=a;
 end endtask
 task automatic idle(input integer n); integer i; begin for(i=0;i<n;i=i+1) issue(0,0,0); end endtask
 task automatic run_frame(input integer seed); integer a,q,l,b; begin
  issue(1,0,0); issue(3,0,0); idle(2);
  for(a=0;a<NL;a=a+1) begin
   for(q=0;q<4;q=q+1) for(l=0;l<16;l=l+1) line[q*LW+l*EW+:EW]=entry(q,a,l,seed);
   issue(2,0,8'(a));
  end
  line=0; idle(3);
  for(b=31;b>=0;b=b-1) issue(5,0,8'(b));
  for(integer ps=1;ps<3;ps=ps+1) begin
   issue(3,2'(ps),0); idle(2);
   for(a=0;a<NL;a=a+1) issue(4,2'(ps),8'(a));
   idle(4);
   for(b=(ps==2)?63:31;b>=0;b=b-1) issue(5,2'(ps),8'(b));
  end
  idle(2);
  for(a=0;a<NL;a=a+1) issue(6,0,8'(a));
  idle(4); issue(7,0,0); idle(4);
  for(a=0;a<NL;a=a+1) issue(8,0,8'(a));
  idle(6);
 end endtask
 function automatic integer total(input [55:0] so); begin
  total=int'(so[13:0])+int'(so[27:14])+int'(so[41:28])+int'(so[55:42]);
 end endfunction
 reg [255:0] row; integer launches=0;
 task automatic launch_with(input [9:0] kv, input integer seed); begin
  row = 0; row[179:170] = kv; frame(12'h805, row);
  desc_launch;
  wait(start_v); k_ref = kv;           // the launch record the compiler issued
  idle(3);                              // compiler-fixed offset start_v -> op 1
  run_frame(seed);
  @(negedge clk); c_done=1; @(negedge clk); c_done=0;   // IDX calendar done -> collar run ends
  if(total(so_r)!=int'(kv) || f_r) $fatal(1,"IDX_K_SELECT_COUNT ref=%0d k=%0d fault=%0d",total(so_r),kv,f_r);
  launches=launches+1;
 end endtask
 initial begin
  repeat(4) @(negedge clk); rst_n=1; repeat(4) @(negedge clk);
  frame(12'h800, 256'd0); frame(12'h801, 256'd0); frame(12'h802, 256'd0); frame(12'h803, 256'd0); frame(12'h804, 256'h3ff);
  frame(12'hE01, 256'd1<<128);   // need: no programme rows in this bench; wait for c_done (calendar done)
  launch_with(10'd512, 1);
  wait(!c_active); repeat(4) @(negedge clk);
  launch_with(10'd37, 2);
  wait(!c_active); repeat(4) @(negedge clk);
  if(c_fault) $fatal(1,"IDX_K_COLLAR_FAULT");
  $display("IDX_K_ISSUER PASS launches=%0d k=512,37 checks=%0d lines=%0d", launches, checks, NL*64);
  $finish;
 end
endmodule
`default_nettype wire

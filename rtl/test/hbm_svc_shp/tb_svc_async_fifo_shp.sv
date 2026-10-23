`timescale 1ps/1ps
// kshare r5a: lockstep reviewed ot_hbm_svc_async_fifo vs ot_hbm_svc_async_fifo_shp (shared-pointer sliced storage):
// same stimulus, independent wr (1024 ps) / rd (833 ps) clocks with a seed-chosen phase, random valid/ready, two
// mid-run resets of both sides; every output compared on every edge of either clock.  MUT 1 (bench, must FAIL):
// slice 0's one-hot read slot is not advanced (stale data in the first slice).
module tb_svc_async_fifo_shp;
 parameter integer WIDTH=279, DEPTH=8, SW=7, GS=7, MUT=0, SEED=1, N=200000;
 reg wr_clk=0, rd_clk=0, wr_rst_n=0, rd_rst_n=0, wr_valid=0, rd_ready=0; reg [WIDTH-1:0] wr_data=0;
 integer ph; initial begin ph = 37 + (SEED*131)%700; #(ph); forever #417 rd_clk=~rd_clk; end
 always #512 wr_clk=~wr_clk;
 wire r_wrdy,r_rv,r_ov,r_un,s_wrdy,s_rv,s_ov,s_un; wire [WIDTH-1:0] r_rd,s_rd;
 ot_hbm_svc_async_fifo #(.WIDTH(WIDTH),.DEPTH(DEPTH)) u_ref(.wr_clk(wr_clk),.wr_rst_n(wr_rst_n),.wr_valid(wr_valid),
  .wr_ready(r_wrdy),.wr_data(wr_data),.wr_overflow(r_ov),.rd_clk(rd_clk),.rd_rst_n(rd_rst_n),.rd_valid(r_rv),
  .rd_ready(rd_ready),.rd_data(r_rd),.rd_underflow(r_un));
 ot_hbm_svc_async_fifo_shp #(.WIDTH(WIDTH),.DEPTH(DEPTH),.SW(SW),.GS(GS)) u_dut(.wr_clk(wr_clk),.wr_rst_n(wr_rst_n),
  .wr_valid(wr_valid),.wr_ready(s_wrdy),.wr_data(wr_data),.wr_overflow(s_ov),.rd_clk(rd_clk),.rd_rst_n(rd_rst_n),
  .rd_valid(s_rv),.rd_ready(rd_ready),.rd_data(s_rd),.rd_underflow(s_un));
 generate if(MUT==1) begin:g_mut always @(posedge rd_clk) force u_dut.g_s[0].rs = 1; end endgenerate
 integer i, errs=0, checks=0, pops=0, k; reg [31:0] r;
 // stimulus: only drive valid/ready the way a protocol-correct user would (valid held until accepted is not needed for
 // equivalence; both DUTs see identical inputs), changed away from clock edges.  Data compared BIT BY BIT: Verilator
 // 5.050 word-level === and |(a^b) see unmasked padding above bit 35 when the last slice is 1 bit wide (WIDTH 36 SW 5)
 // v4: random words go through a WIDTH+32-bit temporary (writing 32 bits past a 1-bit wr_data put garbage into
 // the simulator padding, which the v1-v3 binary mux copied through on both sides and the v4 AND-OR masks)
 reg [WIDTH+31:0] wtmp;
 always @(negedge wr_clk) begin r=$urandom; wr_valid <= r[1:0]!=0; for(k=0;k<WIDTH;k=k+32) wtmp[k+:32]=$urandom; wr_data <= wtmp[WIDTH-1:0]; end
 always @(negedge rd_clk) begin r=$urandom; rd_ready <= r[2:0]!=0; if(r_rv&&rd_ready) pops=pops+1; end
 integer b; reg dmis;
 task chk; begin checks=checks+1; dmis=0; for(b=0;b<WIDTH;b=b+1) if(r_rd[b]!=s_rd[b]) dmis=1;
  if({r_wrdy,r_rv,r_ov,r_un}!=={s_wrdy,s_rv,s_ov,s_un} || (r_rv && dmis)) begin errs=errs+1;
   if(errs<6) $display("SHP_MISMATCH t=%0t ctl ref=%b dut=%b data_eq=%0d xor=%h", $time, {r_wrdy,r_rv,r_ov,r_un},{s_wrdy,s_rv,s_ov,s_un}, r_rd===s_rd, r_rd^s_rd); if(errs<3) $display(" ref=%h dut=%h", r_rd, s_rd); end
 end endtask
 // review 10:45 (a): the slot-index invariant itself, every edge: each slice wa == wr_bin[AW-1:0], rs == 1 << rd_bin[AW-1:0] (v4 one-hot read slot)
 localparam integer AW=$clog2(DEPTH), NS=(WIDTH+SW-1)/SW;
 integer inv_err=0, inv_chk=0;
 genvar gs;
 generate for(gs=0;gs<NS;gs=gs+1) begin:g_inv
  always @(posedge wr_clk) #1 begin inv_chk=inv_chk+1;
   if(u_dut.g_s[gs].wa!==u_dut.wr_bin[AW-1:0]) begin inv_err=inv_err+1; if(inv_err<4) $display("SHP_INV wa slice %0d t=%0t", gs, $time); end end
  always @(posedge rd_clk) #1 begin inv_chk=inv_chk+1;
   if(u_dut.g_s[gs].rs!==(1<<u_dut.rd_bin[AW-1:0])) begin inv_err=inv_err+1; if(inv_err<4) $display("SHP_INV rs slice %0d t=%0t", gs, $time); end end
 end endgenerate
 // reset-release margin: wr_clk edges from group-0 write reset release to the first write fire (min over reset epochs)
 integer mg_cnt=-1, mg_min=1<<30;
 always @(posedge wr_clk) begin
  if(!u_dut.gw_reset[0]) mg_cnt=0; else if(mg_cnt>=0) begin
   if(u_dut.wr_fire) begin if(mg_cnt<mg_min) mg_min=mg_cnt; mg_cnt=-1; end else mg_cnt=mg_cnt+1; end
 end
 always @(posedge wr_clk) #1 chk; always @(posedge rd_clk) #1 chk;
 initial begin
  void'($urandom(SEED));
  #5000 wr_rst_n=1; #300 rd_rst_n=1;
  for(i=0;i<N/2;i=i+1) @(posedge wr_clk);
  #200 wr_rst_n=0; #3000 wr_rst_n=1;                    // writer-side reset (both_reset) mid-run
  for(i=0;i<N/4;i=i+1) @(posedge wr_clk);
  #100 rd_rst_n=0; #2500 rd_rst_n=1;                    // reader-side reset mid-run
  for(i=0;i<N/4;i=i+1) @(posedge wr_clk);
  $display("SHP_INVARIANT checks=%0d errors=%0d release_to_first_fire_min_wr_edges=%0d", inv_chk, inv_err, mg_min);
  errs = errs + inv_err;
  if(errs==0 && pops>1000) $display("SHP_LOCKSTEP PASS WIDTH=%0d DEPTH=%0d SW=%0d checks=%0d pops=%0d", WIDTH, DEPTH, SW, checks, pops);
  else $display("SHP_LOCKSTEP FAIL MUT=%0d errors=%0d checks=%0d pops=%0d", MUT, errs, checks, pops);
  $finish;
 end
endmodule

// HBM-HARD-6-TOPK lock-step bench: ot_hbm_idx_topk_ingest NQ=0 (gold, vD form) vs NQ=1 (MUT=`MUTN), FILL_GROUPS=8, WPIPE=1.
// Random stimulus incl. clear / flush / emit / mid-run resets; every output compared every cycle after the first reset.
`timescale 1ns/1ps
module tb;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0, clear=0, ingest_v=0, flush=0, emit_v=0; reg[2367:0] line=0; reg[7:0] rank=0,gbase=0;
 wire fa,fb; wire[9:0] ca,cb; wire[7:0] wea,web; wire[47:0] waa,wab; wire[4095:0] wda,wdb;
 ot_hbm_idx_topk_ingest #(.MUT(0),.FILL_GROUPS(8),.WPIPE(1),.NQ(0)) g(.clk(clk),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(line),
  .flush(flush),.emit_v(emit_v),.rank(rank),.gbase(gbase),.fault(fa),.selected_count(ca),.wo_we(wea),.wo_wa(waa),.wo_wd(wda));
 ot_hbm_idx_topk_ingest #(.MUT(`MUTN),.FILL_GROUPS(8),.WPIPE(1),.NQ(1)) r(.clk(clk),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(line),
  .flush(flush),.emit_v(emit_v),.rank(rank),.gbase(gbase),.fault(fb),.selected_count(cb),.wo_we(web),.wo_wa(wab),.wo_wd(wdb));
 function integer rnd(input integer d); begin rnd = $random(seed) & 32'h7fffffff; end endfunction
 integer cyc=0, errs=0, seed, dens, i, ncyc, armed=0, nwe=0, nclr=0, nrst=0;
 initial begin
  if(!$value$plusargs("seed=%d",seed)) seed=1;
  if(!$value$plusargs("ncyc=%d",ncyc)) ncyc=4000;
  dens=50;
  repeat(ncyc) begin
   @(negedge clk); cyc=cyc+1;
   if(cyc%500==0) dens=rnd(0)%101;      // vary valid-bit density 0..100 %
   rst_n <= !((cyc<12) || (rnd(0)%997==0) && cyc>100);
   clear <= (rnd(0)%100)<3; flush <= (rnd(0)%100)<2; emit_v <= (rnd(0)%100)<3;
   ingest_v <= (rnd(0)%100)<75; rank <= rnd(0); gbase <= rnd(0);
   for(i=0;i<74;i=i+1) line[i*32+:32] = $random(seed);
   for(i=0;i<64;i=i+1) line[i*37] = ((rnd(0)%100)<dens);
   if(!rst_n) nrst=nrst+1; if(clear) nclr=nclr+1;
   if(cyc==20) armed=1;
  end
  $display("BENCH MUT=%0d seed=%0d cycles=%0d errs=%0d we_cycles=%0d clears=%0d reset_cycles=%0d", `MUTN, seed, cyc, errs, nwe, nclr, nrst);
  $finish;
 end
 always @(posedge clk) if(armed) begin
  #0.5;
  if(wea!=0) nwe=nwe+1;
  if({fa,ca,wea,waa,wda} !== {fb,cb,web,wab,wdb}) begin
   errs=errs+1;
   if(errs<4) $display("DIFF cyc=%0d fault %b/%b cnt %0d/%0d we %h/%h wa %h/%h wd_eq %0d", cyc, fa,fb,ca,cb,wea,web,waa,wab, wda===wdb);
  end
 end
endmodule

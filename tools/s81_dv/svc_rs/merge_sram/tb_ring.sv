`timescale 1ns/1ps
module tb_ring;
 parameter integer DPT=8, MUT=0;
 localparam integer W=528;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,v=0,store=0; reg[W-1:0]data=0;
 wire[W-1:0]head;
 reg[W-1:0]ref_ring[0:DPT-1];
 integer filled=0,checks=0,errors=0; reg qualified=0;
 ot_hdc_v41x_merge_ring_sram #(.W(W),.DPT(DPT),.MUT(MUT)) dut(.*);
 always @(posedge clk) begin
  if(rst_n) begin
   if(qualified)begin
    checks=checks+1;
    if(head!==ref_ring[0])begin errors=errors+1;if(errors<4)$display("MISMATCH dpt=%0d mut=%0d check=%0d",DPT,MUT,checks);end
   end
   if(v)begin
    for(integer j=0;j<DPT-1;j=j+1)ref_ring[j]=ref_ring[j+1];
    // Hold/rotate must use old head, so final word is captured separately below.
   end
  end
 end
 // Reference operation in one block with old head saved, before all shifts.
 // Separate checker above only reads reference; the block below updates on negedge after check.
 reg[W-1:0]saved; reg prior_v=0,prior_store=0; reg[W-1:0]prior_data;
 initial begin
  for(integer epoch=0;epoch<3;epoch=epoch+1)begin
   @(negedge clk);rst_n=0;v=0;store=0;qualified=0;filled=0;
   repeat(3)@(negedge clk);
   rst_n=1;
   for(integer cycle=0;cycle<1200;cycle=cycle+1)begin
    v=(cycle<DPT)||((cycle%7)!=2 && (cycle%11)!=3);
    store=(cycle<DPT)||((cycle%5)!=1 && (cycle%9)!=4);
    for(integer b=0;b<17;b=b+1)data[W-1:0]=(data<<32) ^ (32'(epoch*100000+cycle*101+b*37));
    if(cycle%13==0)data={W{1'b1}}; // identical repeated payloads are legal, do not deduplicate.
    saved=ref_ring[0];prior_v=v;prior_store=store;prior_data=data;
    @(posedge clk); #1;
    if(prior_v)ref_ring[DPT-1]=prior_store?prior_data:saved;
    if(cycle==DPT-1)qualified=1;
    @(negedge clk);
   end
  end
  $display("RING_RESULT DPT=%0d MUT=%0d checks=%0d errors=%0d",DPT,MUT,checks,errors);
  if(checks<3000)$fatal(1,"coverage");
  if(MUT==0 && errors!=0)$fatal(1,"positive mismatch");
  if(MUT!=0 && errors==0)$fatal(1,"mutation escaped");
  $finish;
 end
endmodule

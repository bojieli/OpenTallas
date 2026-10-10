`timescale 1ns/1ps
module tb_hbm_svc_dma_pc_cache_wide;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,alloc_v=0,ret_v=0,fetch_v=0,out_rdy=1;
 reg [5:0] alloc_slot=0;reg [7:0] alloc_idx=0,alloc_group=0,ret_group=0,fetch_group=0;
 reg [3:0] alloc_len=1,fetch_mask=15;reg [1:0] alloc_bank=0,ret_bank=0;
 reg alloc_epoch=0,ret_epoch=0,fetch_epoch=0,ret_fault=0;reg [255:0] ret_data=0;
 wire alloc_rdy,ret_rdy,fetch_rdy,out_v,ret_reject,metadata_fault;
 wire [1023:0] out_data;wire [3:0] out_fault;
 ot_hbm_svc_dma_pc_cache_wide #(.ENABLE(1),.MUT_EPOCH(MUT)) dut(.*);
 reg [1027:0] expect_q[0:511];integer sent=0,seen=0,rejected=0,cycle=0;
 integer first_fetch=-1,first_publish=-1,previous_publish=-1,max_gap=0;
 reg measure=0,held=0;reg [1027:0] held_word;
 function automatic [255:0] pat(input integer g,input integer b,input bit e);
   pat={64'h123456789abcdef0^g,64'hfedcba9876543210^b,64'h55aa00ff3333aaaa^g,64'h0f0f1f1f2f2f3f3f^e};
 endfunction
 function automatic [1023:0] bundle(input integer g,input bit e,input [3:0] mask);
   begin for(integer b=0;b<4;b=b+1)bundle[b*256 +: 256]=mask[b]?pat(g,b,e):256'b0;end
 endfunction
 always @(posedge clk) begin
   cycle=cycle+1;
   if(rst_n) begin
     if(ret_reject)rejected=rejected+1;
     if(measure && fetch_v && fetch_rdy && first_fetch<0)first_fetch=cycle;
     if(held && (!out_v || {out_fault,out_data}!==held_word))$fatal(1,"held bundle changed");
     held=out_v && !out_rdy;if(held)held_word={out_fault,out_data};
     if(out_v && out_rdy)begin
       if(seen>=sent || {out_fault,out_data}!==expect_q[seen])$fatal(1,"bundle %0d mismatch",seen);
       if(measure)begin
         if(first_publish<0)first_publish=cycle;
         if(previous_publish>=0 && cycle-previous_publish>max_gap)max_gap=cycle-previous_publish;
         previous_publish=cycle;
       end
       seen=seen+1;
     end
   end else held=0;
 end
 task automatic allocate(input [7:0]g,input [1:0]b,input bit e);
  begin @(negedge clk);alloc_v=1;alloc_group=g;alloc_slot=g[7:2];alloc_bank=b;alloc_epoch=e;alloc_idx=g;
    @(posedge clk);while(!alloc_rdy)@(posedge clk);@(negedge clk);alloc_v=0;end
 endtask
 task automatic respond(input [7:0]g,input [1:0]b,input bit e,input bit f);
  begin @(negedge clk);ret_v=1;ret_group=g;ret_bank=b;ret_epoch=e;ret_data=pat(g,b,e);ret_fault=f;
    @(posedge clk);while(!ret_rdy)@(posedge clk);@(negedge clk);ret_v=0;end
 endtask
 task automatic fetch(input [7:0]g,input bit e,input [3:0]mask,input [3:0]fault);
  reg[1023:0]d;
  begin @(negedge clk);fetch_v=1;fetch_group=g;fetch_epoch=e;fetch_mask=mask;
    d=bundle(g,e,mask);for(integer b=0;b<4;b=b+1)if(fault[b])d[b*256+:256]=0;
    expect_q[sent]={fault,d};sent=sent+1;
    @(posedge clk);while(!fetch_rdy)@(posedge clk);@(negedge clk);fetch_v=0;end
 endtask
 task automatic drain;begin wait(seen==sent);repeat(2)@(negedge clk);end endtask
 integer g,b;
 initial begin
   repeat(3)@(negedge clk);rst_n=1;
   // Fetch before allocation must wait; allocation itself must make progress.
   fetch(200,1,15,0);
   repeat(8)@(negedge clk);if(out_v)$fatal(1,"early fetch leaked");
   for(b=0;b<4;b=b+1)allocate(200,b,1);
   // Attempt reuse with native debt: backpressure prevents epoch wrap.
   @(negedge clk);alloc_v=1;alloc_group=200;alloc_slot=50;alloc_bank=0;alloc_epoch=0;
   repeat(3)begin @(negedge clk);if(alloc_rdy)$fatal(1,"recycle with debt accepted");end
   alloc_v=0;
   // Wrong epoch return is rejected without changing readiness.
   respond(200,0,0,0);
   for(b=3;b>=0;b=b-1)respond(200,b,1,0);
   drain();if(rejected!=1)$fatal(1,"stale return gate");
   // All banks and every logical group, arbitrary reverse bank return order.
   for(g=0;g<256;g=g+1)for(b=0;b<4;b=b+1)allocate(g,b,0);
   for(g=255;g>=0;g=g-1)for(b=3;b>=0;b=b-1)respond(g,b,0,0);
   repeat(5)@(negedge clk);
   measure=1;
   for(g=0;g<256;g=g+1)fetch(g,0,15,0);
   drain();measure=0;
   if(first_publish-first_fetch!=8)$fatal(1,"cache firsttransfer %0d",first_publish-first_fetch);
   if(max_gap>4)$fatal(1,"cache output throughput gap %0d",max_gap);
   $display("MEASURE cache_visible_cycles=7 cache_transfer_cycles=8 max_group_transfer_gap=%0d sectors_per_cycle_min=%f",max_gap,4.0/max_gap);
   // Finite contexts and bundle backpressure; mixed bank masks.
   out_rdy=0;for(g=0;g<4;g=g+1)fetch(g,0,1<<g,0);
   repeat(20)@(negedge clk);if(fetch_rdy)$fatal(1,"missing context backpressure");
   out_rdy=1;drain();
   // New epoch waits for matching allocation and does not expose old payload.
   fetch(4,1,15,0);repeat(8)@(negedge clk);if(out_v)$fatal(1,"old epoch publish");
   for(b=0;b<4;b=b+1)allocate(4,b,1);
   for(b=0;b<4;b=b+1)respond(4,b,0,0);
   for(b=0;b<4;b=b+1)respond(4,b,1,0);
   drain();if(rejected!=5)$fatal(1,"epoch rejection count");
   respond(4,0,1,0);if(rejected!=6)$fatal(1,"duplicate response accepted");
   // Stored SRAM fault record is a poisoned sector in an otherwise exact bundle.
   for(b=0;b<4;b=b+1)allocate(70,b,1);
   for(b=0;b<4;b=b+1)respond(70,b,1,b==2);
   fetch(70,1,15,4);drain();
   if(metadata_fault)$fatal(1,"false control fault");
   // Flip one mutable metadata bit: complement detects, fail closed.
   @(negedge clk);dut.meta[70][0]=~dut.meta[70][0];
   ret_group=70;ret_bank=0;ret_epoch=0;ret_v=1;
   repeat(2)@(negedge clk);ret_v=0;
   if(!metadata_fault || out_v || alloc_rdy || fetch_rdy)$fatal(1,"metadata detection failure");
   $display("PASS bundles=%0d rejected=%0d fetch_before_alloc epoch debt backpressure protected_metadata",seen,rejected);
   $finish;
 end
 initial begin repeat(30000)@(posedge clk);$display("DEBUG seen=%0d sent=%0d g=%0d b=%0d af=%b rf=%b ff=%b mf=%b head=%d tail=%d st0=%h req0=%h meta200=%h brv=%h bov=%h",seen,sent,g,b,alloc_rdy,ret_rdy,fetch_rdy,metadata_fault,dut.head,dut.tail,dut.st[0],dut.req[0],dut.meta[200],dut.brv,dut.bov);$fatal(1,"deadlock");end
endmodule

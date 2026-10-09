`timescale 1ps/1fs
module tb_emb_far_bus;
 parameter integer NEG=0;
 reg ck=0,lclk=0,rst_n=0;
 always #416.666667 lclk=~lclk;
 initial begin #100; forever #416.666667 ck=~ck; end
 reg [527:0] hub_i=0;
 reg [524:0] emb_i=0,kv_i=0;
 wire [527:0] hub_o,ghub,ohub;
 wire [524:0] emb_o,kv_o,gemb,gkv,oemb,okv;
 wire fault,gfault,ofault;
 wire [524:0] mutated_emb=emb_i ^ (NEG ? 525'b10 : 525'b0);
 ot_qfd_link_far_bus #(.ENABLE(1)) dut(.ck(ck),.lclk(lclk),.rst_n(rst_n),.hub_i(hub_i),.hub_o(hub_o),.emb_i(mutated_emb),.emb_o(emb_o),.kv_i(kv_i),.kv_o(kv_o),.fault(fault));
 ot_qfd_link_far_bus disabled(.ck(ck),.lclk(lclk),.rst_n(rst_n),.hub_i(hub_i),.hub_o(ohub),.emb_i(emb_i),.emb_o(oemb),.kv_i(kv_i),.kv_o(okv),.fault(ofault));
 ot_qfd_link_far golden(.ck(ck),.lclk(lclk),.rst_n(rst_n),.l_i(hub_i),.l_o(ghub),.e_v(gemb[524]),.e_d(gemb[523:1]),.t_cr(gemb[0]),.t_v(emb_i[524]),.t_d(emb_i[523:1]),.e_cr(emb_i[0]),.k_v(gkv[524]),.k_d(gkv[523:1]),.kt_cr(gkv[0]),.kt_v(kv_i[524]),.kt_d(kv_i[523:1]),.k_cr(kv_i[0]),.fault(gfault));
 function automatic [522:0] packet(input bit emb,input integer idx,input bit incoming);
  reg [511:0] d; reg [10:0] tag;
  begin d={16{32'(idx*379 + emb*71 + incoming*125)}};tag={emb,2'b01,8'(idx)};packet={tag,d};end
 endfunction
 integer txe=0,txk=0,rxe=0,rxk=0,tecr=0,tkcr=0,simultaneous=0;
 always @(negedge lclk) if(rst_n) begin
  if({hub_o,emb_o,kv_o,fault} !== {ghub,gemb,gkv,gfault}) $fatal(1,"FAIL far native-output equivalence");
  if({ohub,oemb,okv,ofault} !== 0) $fatal(1,"FAIL far default-off");
  if(fault) $fatal(1,"FAIL far credit/overflow fault");
  if(emb_o[0]) tecr=tecr+1;
  if(kv_o[0]) tkcr=tkcr+1;
  if(emb_i[524] && kv_i[524]) simultaneous=simultaneous+1;
  if(hub_o[0]) begin
   if(hub_o[15]) begin
    if({hub_o[15:5],hub_o[527:16]} !== packet(1,txe,0)) $fatal(1,"FAIL engine transmit class/order/data");
    txe=txe+1;
   end else begin
    if({hub_o[15:5],hub_o[527:16]} !== packet(0,txk,0)) $fatal(1,"FAIL KV transmit class/order/data");
    txk=txk+1;
   end
  end
  if(emb_o[524]) begin
   if(emb_o[523:1] !== packet(1,rxe,1)) $fatal(1,"FAIL engine receive class/order/data");
   rxe=rxe+1;
  end
  if(kv_o[524]) begin
   if(kv_o[523:1] !== packet(0,rxk,1)) $fatal(1,"FAIL KV receive class/order/data");
   rxk=rxk+1;
  end
 end
 integer i,j; reg [522:0] p;
 initial begin repeat(6) @(negedge lclk); rst_n=1; end
 initial begin
  wait(rst_n); repeat(16) @(negedge ck);
  for(i=0;i<128;i=i+1) begin
   p=packet(i%2==0,i/2,1); hub_i={p[511:0],p[522:512],4'b0,1'b1};
   @(negedge ck);hub_i=0;repeat(3) @(negedge ck);
  end
 end
 // Transmit both classes together; four source credits bound each queue.
 // Input class credits are returned one local cycle after delivery.
 initial begin
  wait(rst_n);repeat(16) @(negedge lclk);
  for(j=0;j<512;j=j+1) begin
   #1;
   emb_i={(j%8==0),packet(1,j/8,0),emb_o[524]};
   kv_i={(j%8==0),packet(0,j/8,0),kv_o[524]};
   @(negedge lclk);
  end
  #1;emb_i={1'b0,523'b0,emb_o[524]};kv_i={1'b0,523'b0,kv_o[524]};
  repeat(40) begin @(negedge lclk);#1;emb_i={1'b0,523'b0,emb_o[524]};kv_i={1'b0,523'b0,kv_o[524]};end
  if(txe!=64 || txk!=64 || rxe!=64 || rxk!=64 || tecr!=64 || tkcr!=64 || simultaneous!=64)
   $fatal(1,"FAIL far counts tx=%0d/%0d rx=%0d/%0d credit=%0d/%0d simultaneous=%0d",txe,txk,rxe,rxk,tecr,tkcr,simultaneous);
  $display("PASS far_bus native equivalence default-off TXengine64 TXkv64 RXengine64 RXkv64 simultaneous64 credits64each fault0 CR128 OD8 AD8 TQ4 ECR4 KCR4 ck/lclk833.333334ps phase100ps");$finish;
 end
endmodule

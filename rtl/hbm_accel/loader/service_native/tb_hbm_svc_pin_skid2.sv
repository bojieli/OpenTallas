`timescale 1ns/1ps
module tb_hbm_svc_pin_skid2;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,in_v=0,out_r=0;reg[339:0]in_data=0;
 wire in_r,out_v;wire[339:0]out_data;
 ot_hbm_svc_pin_skid2 #(.WIDTH(340),.MUT(MUT)) dut(.*);
 reg[339:0]ref_data[0:1];integer nr=0,nw=0,count=0,checks=0,full=0,stalled=0;
 reg push,pop;reg[31:0]rng=32'h7b19c40d;
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(integer t=0;t<8192;t=t+1)begin
   @(negedge clk);rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   rst_n=t%257!=0;in_v=rng[0]||rng[4];out_r=rng[1]||rng[6];
   for(integer k=0;k<10;k=k+1)in_data[k*32+:32]=32'(t*139+k)^rng;
   in_data[339:320]=20'(t);
   if(!rst_n)begin count=0;nr=0;nw=0;end
   #1;
   if(in_r!==(count<2)||out_v!==(count!=0))$fatal(1,"skid occupancy timing t=%0d",t);
   if(count!=0 && out_data!==ref_data[nr])$fatal(1,"skid exact head mismatch t=%0d",t);
   push=in_v&&in_r;pop=out_v&&out_r;
   @(posedge clk);
   if(rst_n)begin
    if(push)begin ref_data[nw]=in_data;nw=nw^1;end
    if(pop)nr=nr^1;
    count=count+int'(push)-int'(pop);checks=checks+1;
    if(count==2)full=full+1;if(count!=0&&!out_r)stalled=stalled+1;
   end
  end
  if(checks<8000||full<500||stalled<500)$fatal(1,"skid coverage insufficient");
  $display("PIN_SKID2 PASS checks=%0d full=%0d stalled=%0d exact_count2_contract=1 added_edges=0",checks,full,stalled);$finish;
 end
endmodule

`timescale 1ns/1ps
module tb_hbm_kr_ready_bridge;
 parameter integer MUT=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0;integer epoch=0,cyc=0,sent=0,received=0,last_rx=-1,max_occ=0,first_push=-1;
 reg grant_prev=0;wire ir,ov,fault;wire[2:0]occupancy;wire[276:0]od;
 wire iv=sent<256;wire ready=(epoch==0)?(cyc<100):((cyc<100)||(cyc%19>=7));
 function automatic[276:0]payload(input integer n);payload={21'(n),256'(n*32'h01020305)};endfunction
 ot_hbm_svc_kr_ready_bridge #(.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.in_v(iv),.in_rdy(ir),
  .in_data(payload(epoch*10000+sent)),.out_v(ov),.out_rdy(ready),.out_data(od),.fault(fault),.occupancy(occupancy));
 always @(posedge clk)begin
  if(!rst_n)begin cyc<=0;sent<=0;received<=0;grant_prev<=0;last_rx<=-1;first_push<=-1;end
  else begin
   cyc<=cyc+1;grant_prev<=ir;
   if(iv&&grant_prev)begin sent<=sent+1;if(sent==0)first_push<=cyc;end
   if(occupancy>max_occ)max_occ<=occupancy;
   if(fault||occupancy>3)$fatal(1,"KR_BRIDGE_OCCUPANCY_FAULT");
   if(ov&&ready)begin
    if(od!==payload(epoch*10000+received))$fatal(1,"KR_BRIDGE_DATA_MISMATCH epoch=%0d rx=%0d got=%h",epoch,received,od);
    if(received==0&&cyc!=first_push+1)$fatal(1,"KR_BRIDGE_LATENCY_FAIL firstpush=%0d firstrx=%0d",first_push,cyc);
    if(received>0&&cyc<90&&cyc!=last_rx+1)$fatal(1,"KR_BRIDGE_II1_FAIL");
    received<=received+1;last_rx<=cyc;
   end
   if(cyc>2000)$fatal(1,"KR_BRIDGE_TIMEOUT");
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  wait(cyc==130);@(negedge clk);
  if(occupancy!=3)$fatal(1,"KR_BRIDGE_NO_OCCUPIED_RESET");
  rst_n=0;repeat(3)@(negedge clk);
  if(ov||occupancy!=0||dut.ready_prev||ir)$fatal(1,"KR_BRIDGE_RESET_FAIL");
  epoch=1;rst_n=1;wait(received==256);repeat(4)@(negedge clk);
  if(sent!=256||received!=256||occupancy!=0||max_occ!=3)$fatal(1,"KR_BRIDGE_TOTAL_FAIL");
  $display("KR_BRIDGE_PASS exact=256 II=1 max_occupancy=%0d occupied_reset=1 latency_hbm=1",max_occ);$finish;
 end
endmodule

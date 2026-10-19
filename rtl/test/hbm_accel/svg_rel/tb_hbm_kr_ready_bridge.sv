`timescale 1ns/1ps
module tb_hbm_kr_ready_bridge;
 parameter integer MUT=0,PRODUCER=0,VALID_MUT=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0;integer epoch=0,cyc=0,sent=0,received=0,last_rx=-1,max_occ=0,first_push=-1;
 reg grant_prev=0;wire ir,ov,fault;wire[2:0]occupancy;wire[276:0]od;
 wire fixture_iv=sent<256;
 wire ready=(epoch==0)?((cyc<100)||(PRODUCER!=0&&cyc>=150&&cyc<180)):((cyc<100)||(cyc%19>=7));
 wire iv,source_ready;wire[276:0]bridge_data;wire[17:0]native_valid;
 integer bridge_sent=0;
 integer pop_truth[0:17][0:3];
 initial for(integer r=0;r<18;r=r+1)for(integer t=0;t<4;t=t+1)pop_truth[r][t]=0;
 always @(posedge clk)if(rst_n)for(integer r=0;r<18;r=r+1)begin
  pop_truth[r][{dut.valid_regions[r],ready}]=pop_truth[r][{dut.valid_regions[r],ready}]+1;
  if(dut.pop_regions[r] !== (dut.valid_regions[r]&&ready))
   $fatal(1,"KR_POP_EQUATION_MISMATCH region=%0d",r);
 end

 function automatic[276:0]payload(input integer n);payload={21'(n),{8{32'(n*32'h01020305)}}};endfunction
 generate if(PRODUCER!=0)begin:g_producer
  reg ready_q;
  wire[17:0]vregions;
  always @(posedge clk)if(!rst_n)ready_q<=0;else ready_q<=ir;
  ot_hbm_svc_pin_skid2_bw_safe #(.WIDTH(277),.REGIONAL(1))producer(
   .clk(clk),.rst_n(rst_n),.in_v(fixture_iv),.in_r(source_ready),
   .in_data(payload(epoch*10000+sent)),.out_v(iv),.out_r_regions({18{ready_q}}),
   .out_data(bridge_data),.in_v_regions({18{fixture_iv}}),.out_v_regions(vregions));
  assign native_valid=(VALID_MUT!=0)?(vregions&~18'd128):vregions;
 end else begin:g_fixture
  assign iv=fixture_iv;assign source_ready=grant_prev;
  assign bridge_data=payload(epoch*10000+sent);assign native_valid={18{iv}};
 end endgenerate
 ot_hbm_svc_kr_ready_bridge #(.MUT(MUT),.REGIONAL_VALID(PRODUCER))dut(.clk(clk),.rst_n(rst_n),.in_v(iv),.in_rdy(ir),
  .in_data(bridge_data),.out_v(ov),.out_rdy(ready),.out_data(od),.fault(fault),.occupancy(occupancy),.in_v_regions(native_valid));
 always @(posedge clk)begin
  if(!rst_n)begin cyc<=0;sent<=0;received<=0;grant_prev<=0;last_rx<=-1;first_push<=-1;bridge_sent<=0;end
  else begin
   cyc<=cyc+1;grant_prev<=ir;
   if(fixture_iv&&source_ready)sent<=sent+1;
   if(iv&&grant_prev)begin bridge_sent<=bridge_sent+1;if(bridge_sent==0)first_push<=cyc;end
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
  wait(cyc==((PRODUCER!=0)?210:130));@(negedge clk);
  if(occupancy!=3)$fatal(1,"KR_BRIDGE_NO_OCCUPIED_RESET");
  rst_n=0;repeat(3)@(negedge clk);
  if(ov||occupancy!=0||dut.ready_prev||ir)$fatal(1,"KR_BRIDGE_RESET_FAIL");
  epoch=1;rst_n=1;wait(received==256);repeat(4)@(negedge clk);
  if(sent!=256||received!=256||occupancy!=0||max_occ!=3)$fatal(1,"KR_BRIDGE_TOTAL_FAIL");
  for(integer r=0;r<18;r=r+1)begin
   for(integer t=0;t<4;t=t+1)if(pop_truth[r][t]==0)$fatal(1,"KR_POP_TRUTH_MISSING region=%0d state=%0d",r,t);
   $display("KR_POP_TRUTH region=%0d 00=%0d 01=%0d 10=%0d 11=%0d",r,pop_truth[r][0],pop_truth[r][1],pop_truth[r][2],pop_truth[r][3]);
  end
  $display("KR_BRIDGE_PASS exact=256 II=1 max_occupancy=%0d occupied_reset=1 latency_hbm=1",max_occ);$finish;
 end
endmodule

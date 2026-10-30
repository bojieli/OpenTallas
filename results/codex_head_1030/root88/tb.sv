`timescale 1ns/1ps
module boot_path #(parameter integer SETTLE=88)(input wire clk,raw,input wire[15:0]d,
 output wire start,start_d,latest,ready,fault,output wire[15:0]q,refq,output wire mission,input wire host_done);
 reg[83:0]rstpipe;
 always@(posedge clk)if(!raw)rstpipe<=0;else rstpipe<={rstpipe[82:0],1'b1};
 assign latest=rstpipe[83];
 ot_dp_landing_root #(.SETTLE(SETTLE)) root(.clk(clk),.rst_raw_n(raw),.start(start),.start_d(start_d));
 wire[7:0]wr;wire[6:0]rd;assign wr[0]=start_d;assign rd[0]=start;
 for(genvar i=0;i<7;i=i+1)begin:w
  ot_dp_landing_relay s(.clk(clk),.rst_raw_n(latest),.d(wr[i]),.q(wr[i+1]));
 end
 wire fw;
 ot_dp_landing_relay face(.clk(clk),.rst_raw_n(latest),.d(wr[7]),.q(fw));
 for(genvar j=0;j<6;j=j+1)begin:r
  ot_dp_landing_relay s(.clk(clk),.rst_raw_n(latest),.d(rd[j]),.q(rd[j+1]));
 end
 wire rr,ff,rref,fref;
 // K'=K+W-R=3+7-6=4; no added steady data cycles.
 ot_dp_clk_landing_ca #(.W(16),.DEPTH(8),.K(4)) ring(.fclk(clk),.t_rst_n(fw),.clk(clk),.rst_n(rd[6]),.d(d),.q(q),.ready(rr),.fault(ff));
 ot_dp_clk_landing_ca #(.W(16),.DEPTH(8),.K(3)) reference_ring(.fclk(clk),.t_rst_n(start),.clk(clk),.rst_n(start),.d(d),.q(refq),.ready(rref),.fault(fref));
 wire[17:0]sr,sf;assign sr[0]=rr;assign sf[0]=ff;
 for(genvar k=0;k<17;k=k+1)begin:status
  ot_dp_landing_collect #(.N(1)) s(.clk(clk),.rst_n(latest),.ready_i(sr[k]),.fault_i(sf[k]),.ready_o(sr[k+1]),.fault_o(sf[k+1]));
 end
 assign ready=sr[17]&&rref;assign fault=sf[17]||fref;
 assign mission=host_done&&ready&&!fault;
endmodule
module tb;
 reg clk=0;always #5 clk=~clk;
 reg raw=0;reg[15:0]d=0;reg host_done=0;
 wire gs,gd,gl,gr,gf,gm,bs,bd,bl,br,bf,bm;wire[15:0]gq,gref,bq,bref;
 boot_path #(.SETTLE(88)) good(clk,raw,d,gs,gd,gl,gr,gf,gq,gref,gm,host_done);
 boot_path #(.SETTLE(74)) old_short(clk,raw,d,bs,bd,bl,br,bf,bq,bref,bm,host_done);
 integer trial,age,checks=0,old_guard_fail=0,old_data_fail=0,first_d,first_s,mission_edge,first_ready;
 initial begin
 for(trial=0;trial<4;trial=trial+1)begin
  @(negedge clk);raw=0;host_done=0;
  repeat(5)@(posedge clk);
  @(negedge clk);raw=1;first_d=0;first_s=0;mission_edge=0;first_ready=0;
  for(age=1;age<=420;age=age+1)begin
   d=16'((trial+1)*1001+age*177);
   host_done=age>((trial%2==0)?80:220);
   @(posedge clk);#1;
   if(gd&&first_d==0)first_d=age;
   if(gs&&first_s==0)first_s=age;
   if(gr&&first_ready==0)first_ready=age;
   if(gm&&mission_edge==0)mission_edge=age;
   if(gd&&(age<88||!gl))$fatal(1,"ROOT_GUARD_FAIL trial%0d age%0d",trial,age);
   if(bd&&(age<88||!bl))old_guard_fail=old_guard_fail+1;
   if(gf)$fatal(1,"GOOD_RING_FAULT trial%0d age%0d",trial,age);
   if(gr)begin checks=checks+1;if(gq!==gref)$fatal(1,"GOOD_DATA_MISMATCH trial%0d age%0d q%h ref%h",trial,age,gq,gref);end
   if(br&&bq!==bref)old_data_fail=old_data_fail+1;
   if(gm&&(!host_done||!gr||age<88))$fatal(1,"MISSION_EARLY");
   @(negedge clk);
  end
  if(first_d!=88||first_s!=89||mission_edge==0)$fatal(1,"BAD_START_DATES %0d/%0d/%0d",first_d,first_s,mission_edge);
  $display("BOOT trial%0d rootD%0d root%0d statusReady%0d mission%0d",trial,first_d,first_s,first_ready,mission_edge);
 end
 if(checks<900||old_guard_fail==0||old_data_fail==0)$fatal(1,"CONTROL_SURVIVED checks%0d guard%0d data%0d",checks,old_guard_fail,old_data_fail);
 $display("ROOT88_PASS checks%0d old74_guard_violations%0d old74_payload_mismatches%0d cold1_warm3",checks,old_guard_fail,old_data_fail);$finish;
 end
endmodule

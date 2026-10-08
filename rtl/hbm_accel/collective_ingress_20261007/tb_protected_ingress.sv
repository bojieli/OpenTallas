`timescale 1ns/1fs
module tb_protected_ingress;
 localparam TOTAL=384;
 reg clk=0,pclk=0;
 always #0.416666667 clk=~clk;
 initial begin #0.137;forever #0.416666667 pclk=~pclk;end
 reg rst_n=0,prst_n=0,cold_link_start=0,source_start=0;
 wire[23:0] link_epoch=24'h721;
 reg reserve_valid=0,out_r=0;
 wire reserve_ready,source_fault;
 wire grant_valid,grant_ready,ack_valid,ack_ready;
 wire[71:0] grant_word,ack_word;
 wire source_grant_v,source_grant_r,source_ack_v,source_ack_r;
 wire[71:0] source_grant_word,source_ack_word;
 wire grant_fault,ack_fault;
 wire out_v,final_retire,quiet_core,quiet_phy,fault;
 wire[544:0] out_d;
 wire[8:0] landing_count,receive_count;
 reg[2:0] fixture_v=0;
 reg[544:0] fixture_d0=0,fixture_d1=0,fixture_d2=0;
 wire ph_rx_v=fixture_v[2];wire[544:0] ph_rx_flit=fixture_d2;
 // Three pclk fixture edges after reservation; this is NOT a PHY timing claim.
 ot_hbm_collective_protected_ingress #(.ENABLE(1)) dut(.*);
 ot_hbm_credit_source #(.ENABLE(1)) source(
  .clk(pclk),.rst_n(prst_n),.cold_link_start(source_start),.link_epoch(link_epoch),
  .reserve_valid(reserve_valid),.reserve_ready(reserve_ready),
  .grant_valid(source_grant_v),.grant_ready(source_grant_r),.grant_word(source_grant_word),
  .ack_valid(source_ack_v),.ack_ready(source_ack_r),.ack_word(source_ack_word),.fault(source_fault));
 ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(72),.AW(3)) grant_transport(
  .wclk(clk),.wrst_n(rst_n),.in_v(grant_valid),.in_r(grant_ready),.in_d(grant_word),
  .rclk(pclk),.rrst_n(prst_n),.out_v(source_grant_v),.out_r(source_grant_r),.out_d(source_grant_word),
  .wempty(),.rempty(),.fault(grant_fault));
 ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(72),.AW(3)) ack_transport(
  .wclk(pclk),.wrst_n(prst_n),.in_v(source_ack_v),.in_r(source_ack_r),.in_d(source_ack_word),
  .rclk(clk),.rrst_n(rst_n),.out_v(ack_valid),.out_r(ack_ready),.out_d(ack_word),
  .wempty(),.rempty(),.fault(ack_fault));
 function automatic[544:0] datum(input integer n);
  reg[544:0] v;begin for(integer k=0;k<545;k=k+1)v[k]=((n*17+k*31)>>(k%19))&1;datum=v;end
 endfunction
 integer launched=0,arrived=0,retired=0,phy_cycles=0,core_cycles=0;
 integer max_outstanding=0,intermediate_moves=0;reg allow_fault=0;
 always @(posedge pclk)begin
  phy_cycles=phy_cycles+1;
  if(!prst_n)begin fixture_v<=0;fixture_d0<=0;fixture_d1<=0;fixture_d2<=0;end
  else begin
   fixture_v<={fixture_v[1:0],reserve_valid&&reserve_ready};
   fixture_d2<=fixture_d1;fixture_d1<=fixture_d0;fixture_d0<=datum(launched);
   if(reserve_valid&&reserve_ready)launched=launched+1;
   if(ph_rx_v)begin
    if(ph_rx_flit!==datum(arrived))$fatal(1,"fixture PHY data mismatch arrival=%0d data=%h",arrived,ph_rx_flit[63:0]);
    arrived=arrived+1;
   end
   if(launched-retired>64||launched<retired)$fatal(1,"credit conservation");
   if(launched-retired>max_outstanding)max_outstanding=launched-retired;
   if(!allow_fault&&(fault!==1'b0||source_fault!==1'b0||grant_fault!==1'b0||ack_fault!==1'b0))$fatal(1,"unexpected fault");
  end
 end
 always @(posedge clk)begin
  core_cycles=core_cycles+1;
  if(rst_n)begin
   if(final_retire!==(out_v&&out_r))$fatal(1,"retirement mismatch");
   if(final_retire)begin
    if(retired>=launched||out_d!==datum(retired))$fatal(1,"DATA order mismatch retired=%0d",retired);
    retired=retired+1;
   end
   if(dut.g_on.landing_valid&&(^dut.g_on.landing_data===1'bx))$fatal(1,"unknown landing payload");
   if(dut.g_on.cdc_valid&&dut.g_on.flight_ready)intermediate_moves=intermediate_moves+1;
   if(!allow_fault&&(fault!==1'b0||source_fault!==1'b0||grant_fault!==1'b0||ack_fault!==1'b0))$fatal(1,"unexpected core fault");
  end
 end
 task phy_tick;begin @(posedge pclk);#0.02;@(negedge pclk);end endtask
 initial begin
  force dut.g_on.cdc_in_ready=1'b0;
  force dut.g_on.u_cdc.in_v=1'b0;
  repeat(5)phy_tick;prst_n=1;
  @(negedge clk);rst_n=1;
  repeat(4)phy_tick;
  if(reserve_ready||launched!=0)$fatal(1,"source did not start at zero");
  @(negedge pclk);source_start=1;phy_tick;source_start=0;
  @(negedge clk);cold_link_start=1;@(negedge clk);cold_link_start=0;
  reserve_valid=1;
  repeat(180)phy_tick;
  if(launched!=64||arrived!=64||landing_count!=64||retired!=0||reserve_ready||fixture_v!=0)
   $fatal(1,"initial64 exhaustion launch=%0d arrive=%0d landing=%0d",launched,arrived,landing_count);
  repeat(50)phy_tick;
  if(launched!=64||landing_count!=64||retired!=0||quiet_phy)$fatal(1,"65th launch or false quiet");
  release dut.g_on.cdc_in_ready;release dut.g_on.u_cdc.in_v;
  // Intermediate transport can drain fully into RX, but no final retirement.
  repeat(300)phy_tick;
  if(launched!=64||retired!=0||receive_count!=64||landing_count!=0||reserve_ready||quiet_core||intermediate_moves!=64)
   $fatal(1,"intermediate credit return launch=%0d rx=%0d moves=%0d",launched,receive_count,intermediate_moves);
  // Finite fixture calendar: 384 packets, II3 queues, return handshakes and
  // deterministic stalls. This is not a wall-time job cutoff.
  for(integer c=0;c<3500;c=c+1)begin
   reserve_valid=launched<TOTAL;out_r=(c%31>=9);phy_tick;
  end
  reserve_valid=0;out_r=1;repeat(100)phy_tick;
  if(launched!=TOTAL||arrived!=TOTAL||retired!=TOTAL||!quiet_core||!quiet_phy||fixture_v!=0)
   $fatal(1,"drain launch=%0d arrive=%0d retire=%0d quiet=%b%b",launched,arrived,retired,quiet_core,quiet_phy);
  // Refill the landing under a test-only downstream block, then corrupt its
  // sealed mutable control before any of these flits can be consumed.
  force dut.g_on.cdc_in_ready=1'b0;force dut.g_on.u_cdc.in_v=1'b0;
  out_r=0;reserve_valid=1;repeat(30)phy_tick;reserve_valid=0;repeat(5)phy_tick;
  if(landing_count==0)$fatal(1,"fault test empty landing");
  allow_fault=1;
  dut.g_on.u_landing.g_on.seal=dut.g_on.u_landing.g_on.seal^72'b1;
  #0.01;if(!fault||out_v||final_retire||quiet_core||quiet_phy)$fatal(1,"landing quarantine");
  repeat(10)phy_tick;
  if(!fault||retired!=TOTAL||out_v||final_retire)$fatal(1,"fault quarantine lost");
  $display("PASS ingress W545 payload=%0d max_outstanding=%0d fixture_phy_edges=3 core_cycles=%0d phy_cycles=%0d fault_landing=%0d",retired,max_outstanding,core_cycles,phy_cycles,landing_count);
  $finish;
 end
endmodule

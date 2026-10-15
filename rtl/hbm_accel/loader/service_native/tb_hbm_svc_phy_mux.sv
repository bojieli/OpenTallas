`timescale 1ns/1ps
module tb_hbm_svc_phy_mux;
 reg hbm_clk=0;always #0.512 hbm_clk=~hbm_clk;
 reg hbm_rst_n=0;
 reg [31:0] rd_v=0,wb_v=0,k_rdy=0;
 wire [31:0] rd_rdy,wb_rdy,k_v,k_we;
 reg [959:0] rd_addr=0,wb_addr=0;wire [959:0] k_addr;
 reg [127:0] rd_len=0,wb_len=0;wire [127:0] k_len;
 reg [543:0] rd_tag=0,wb_tag=0;wire [543:0] k_tag;
 reg [8191:0] wb_data=0;wire [8191:0] k_wdata;
 reg [1023:0] wb_strb='1;wire [1023:0] k_wstrb;
 ot_hbm_svc_phy_mux dut(.*);
 integer p,rounds,accepts=0;
 reg [31:0] expected_wb=0;
 task tick;begin @(posedge hbm_clk);#0.01;end endtask
 task check(input bit wb);begin
  #0.01;
  for(integer i=0;i<32;i=i+1)begin
   if(k_v[i]!==1||k_we[i]!==wb||k_addr[i*30+:30]!== (wb?wb_addr[i*30+:30]:rd_addr[i*30+:30])||
      k_tag[i*17+:17]!== (wb?wb_tag[i*17+:17]:rd_tag[i*17+:17]))$fatal(1,"mux ownership pc=%0d",i);
   if(wb&&(k_wdata[i*256+:256]!==wb_data[i*256+:256]||k_wstrb[i*32+:32]!==32'hffffffff))$fatal(1,"write payload");
  end
 end endtask
 initial begin
  for(p=0;p<32;p=p+1)begin
   rd_addr[p*30+:30]=p+100;wb_addr[p*30+:30]=p+1000;
   rd_len[p*4+:4]=1;wb_len[p*4+:4]=1;
   rd_tag[p*17+:17]=p;wb_tag[p*17+:17]=p+64;
   wb_data[p*256+:256]={8{32'hfb310000+p}};
  end
  tick();@(negedge hbm_clk);hbm_rst_n=1;rd_v='1;wb_v='1;
  check(0);tick();check(0); // lock read while PHY stalls.
  // Newly competing WB valid cannot replace the held read request.
  repeat(3)begin tick();check(0);end
  @(negedge hbm_clk);k_rdy='1;
  #0.01;if(rd_rdy!=='1||wb_rdy!==0)$fatal(1,"grant");
  tick();check(1); // after accepting read, round-robin chooses WB.
  @(negedge hbm_clk);k_rdy=0;
  tick();check(1);repeat(3)begin tick();check(1);end
  @(negedge hbm_clk);k_rdy='1;tick();check(0);
  for(rounds=0;rounds<16;rounds=rounds+1)begin
   @(negedge hbm_clk);check(rounds[0]);tick();
  end
  @(negedge hbm_clk);hbm_rst_n=0;k_rdy=0;rd_v=0;wb_v=0;tick();
  @(negedge hbm_clk);hbm_rst_n=1;wb_v='1;tick();check(1);
  @(negedge hbm_clk);rd_v='1;repeat(3)begin tick();check(1);end
  $display("PHY_MUX PASS pcs=32 initial_accepts=64 alternating_accepts=512 held_stall_cases=3");$finish;
 end
endmodule

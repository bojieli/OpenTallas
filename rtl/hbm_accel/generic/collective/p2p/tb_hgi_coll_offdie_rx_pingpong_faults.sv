`timescale 1ns/1ps
module tb_hgi_coll_offdie_rx_pingpong_faults;
 reg clk=0,rst_n=0,arm=0,ab=0,pv=0,rel=0,rb=0,sv=0,sb=0;
 reg [6:0] words=1;reg [5:0] si=0;
 wire ready,pinv,fault;wire [1:0] br;wire [6:0] cause;wire [611:0] pinf;
 ot_hgi_coll_offdie_rx_pingpong dut(.clk(clk),.rst_n(rst_n),.arm_v(arm),.arm_bank(ab),.block_words(words),
 .phy_v(pv),.phy_flit(612'h123),.phy_ready(ready),.block_ready(br),.release_v(rel),.release_bank(rb),
 .slot_v(sv),.slot_bank(sb),.slot_index(si),.pin_v(pinv),.pin_flit(pinf),.fault(fault),.fault_cause(cause));
 task tick;begin #5;clk=1;#1;#4;clk=0;end endtask
 task reset;begin rst_n=0;arm=0;pv=0;rel=0;sv=0;ab=0;rb=0;sb=0;si=0;words=1;tick;tick;rst_n=1;tick;end endtask
 task fill0;begin arm=1;tick;arm=0;pv=1;tick;pv=0;tick;tick;if(br!==2'b01)$fatal(1,"fault setup block");end endtask
 initial begin
  reset;rel=1;rb=1;tick;if(!fault||!cause[6])$fatal(1,"unavailable selected bank release");
  reset;arm=1;tick;ab=1;tick;if(!fault||!cause[5])$fatal(1,"switch fill bank while accepting current block");
  reset;fill0;rel=1;tick;rel=0;sv=1;sb=1;tick;
  if(!fault||!cause[6]||pinv)$fatal(1,"wrong commanded slot bank");
  reset;fill0;rel=1;tick;rel=0;sv=1;si=1;tick;
  if(!fault||!cause[2]||pinv)$fatal(1,"out of order bank index");
  reset;fill0;arm=1;tick;
  if(!fault||!cause[0])$fatal(1,"overwrite complete unread block");
  reset;fill0;rel=1;tick;rel=0;sv=1;tick;sv=0;rel=1;tick;
  if(!fault||!cause[6])$fatal(1,"overlapping drain ownership");
  $display("HCOLL_OFFDIE_RX_PINGPONG_FAULTS_PASS six_bank_ownership_cases");
  $finish;
 end
endmodule

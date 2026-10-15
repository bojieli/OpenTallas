`timescale 1ns/1ps
module tb_hbm_su_port_census;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[15:0]vi=0,vw=0;reg[63:0]rd=0;reg[1:0]rw=0;
 reg[383:0]va=0,wa=0;reg[1535:0]ra=0;reg[47:0]rwa=0;
 ot_hbm_su_port_census #(.N(16))d(.clk(clk),.rst_n(rst_n),.vi_re(vi),.vi_addr(va),
 .rd_re(rd),.rd_addr(ra),.vm_we(vw),.vm_waddr(wa),.res_we(rw),.res_addr(rwa),
 .lsw_v(32'd0),.ldr_v(32'd0),.lsw_sec(480'd0),.ldr_sec(480'd0));
 initial begin
  repeat(2)@(negedge clk);rst_n=1;
  rd[0]=1;rd[4]=1;ra[4*24+:24]=16;
  @(negedge clk);rd=0;ra=0;rd[0]=1;rd[5]=1;ra[5*24+:24]=16;
  @(negedge clk);rd=0;ra=0;rd[0]=1;rd[4]=1;
  @(negedge clk);rd=0;vw=3;wa[24+:24]=16;
  @(negedge clk);vw=0;vi=1;va[0+:24]=1<<18;rw=1;rwa[0+:24]=1<<18;
  @(negedge clk);rst_n=0;
  if(d.active_cycles!=5||d.read_row_conflict_cycles!=1||d.write_conflict_cycles!=1||d.rf_reads!=1||d.rf_writes!=1||d.off_column_reads!=3)$fatal(1,"PORT_CENSUS FAIL");
  $display("PORT_CENSUS PASS same_class_conflict cross_class_allowed broadcast_allowed write_conflict rf_ports");$finish;
 end
endmodule

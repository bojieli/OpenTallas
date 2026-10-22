`timescale 1ns/1ps
module tb_pr0_reset;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg [3:0] c_in=0;reg [63:0] row_in=0;reg [15:0] e_in=0;reg [11:0] lt_in=0;
 reg [1:0] hid=0,bsel=0;reg q_valid_in=0;reg [5:0] q_beat_in=0;reg [127:0] q_data_in=0;
 wire [31:0] kp;wire kpv,gf;wire [63:0] nb;
 ot_qkh_lane8_nc32c dut(.*);
 integer epoch,k,checked=0;
 initial begin
  repeat(8)@(negedge clk);
  for(epoch=0;epoch<4;epoch=epoch+1)begin
   // The first active input capture is edge6: 2 landing +3 relay +1 control FF.
   rst_n=1;c_in=4'b1110;q_valid_in=1;lt_in=12'hfff;
   for(k=1;k<=8;k=k+1)begin
    @(posedge clk);#0.1;
    if(dut.rst_n__ot_rl1 !== (k>=2))$fatal(1,"LANDING_RELEASE epoch%0d edge%0d",epoch,k);
    if(dut.u_ot_pr_core.r32 !== {211{(k>=5)}})$fatal(1,"REGIONAL_RELEASE epoch%0d edge%0d",epoch,k);
    if(dut.u_ot_pr_core.c3 !== (k>=6?3'b111:3'b000))$fatal(1,"FIRST_CAPTURE epoch%0d edge%0d",epoch,k);
    checked=checked+1;@(negedge clk);
   end
   // Reset while inputs and arithmetic are active. Assertions land on edge2.
   rst_n=0;
   for(k=1;k<=8;k=k+1)begin
    @(posedge clk);#0.1;
    if(dut.rst_n__ot_rl1 !== (k<2))$fatal(1,"LANDING_ASSERT epoch%0d edge%0d",epoch,k);
    if(dut.u_ot_pr_core.r32 !== {211{(k<2)}})$fatal(1,"REGIONAL_ASSERT epoch%0d edge%0d",epoch,k);
    if(k>=2 && (dut.u_ot_pr_core.c3!==0 || kpv!==0 || gf!==0))$fatal(1,"RESET_CONTROL_NOT_CLEAR");
    checked=checked+1;@(negedge clk);
   end
  end
  $display("PR0_RESET_PASS epochs=%0d checks=%0d regions=211 landing=2 relay_release=5 first_capture=6",epoch,checked);$finish;
 end
endmodule

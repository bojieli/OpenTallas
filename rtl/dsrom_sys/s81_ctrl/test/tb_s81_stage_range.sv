`timescale 1ns/1ps
module tb_s81_stage_range;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg[11:0] cfg_users=64;reg in_valid=0,in_last=0,out_ready=0;
 reg[511:0] in_data=0;wire in_ready,out_valid,out_last,fault;
 wire[511:0] out_data;wire[3:0] fault_code;wire[127:0] fault_hdr;
 wire[31:0] st_msgs,st_flits;
 ot_s81_stage_guard #(.MAXU(64),.MY_ID(10),.SRC_LO(20),.SRC_HI(23)) dut(.*);
 integer bad=0,i;
 initial begin
  if($value$plusargs("bad=%d",bad))begin end
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  for(i=0;i<4;i=i+1)begin
   in_valid=1;out_ready=i%2==0;in_last=i==3;
   in_data={16{32'h55aa1122}};
   if(i==0)begin in_data[51:40]=bad==1?12'd64:12'd63;
    in_data[72:52]=bad==2?21'd1048576:21'd1048575;
    in_data[23:12]=12'd3999; // staticsourcefield isnotauthenticationhardware
   end
   #1;if(out_valid!==in_valid||out_data!==in_data||out_last!==in_last||in_ready!==out_ready)
    $fatal(1,"stageobserverchangedpayloadorflow");
   @(negedge clk);out_ready=1;@(negedge clk);
  end
  in_valid=0;@(negedge clk);
  if(bad==0&&fault)$fatal(1,"unexpectedrangeflag");
  if(bad==1&&(!fault||fault_code!=6))$fatal(1,"userboundmissing");
  if(bad==2&&(!fault||fault_code!=7))$fatal(1,"positionboundmissing");
  $display("STAGE_RANGE PASS bad%0d transparent0cycles",bad);$finish;
 end
endmodule

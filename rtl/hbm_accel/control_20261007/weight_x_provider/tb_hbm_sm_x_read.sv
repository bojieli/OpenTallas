`timescale 1ns/1ps
module tb_hbm_sm_x_read;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg installed_valid=1;reg[36:0] installed_base=37'h10000;reg[37:0] installed_limit=38'h78000;
 reg[15:0] installed_record=16'hbc;reg[7:0] installed_extent=128;reg[6:0] installed_ring=117;
 reg x_req_valid=0;wire x_req_ready;reg[15:0] x_req_record=16'hbc;reg[6:0] x_req_base=117;reg[7:0] x_req_extent=128;
 wire x_valid,x_error;reg x_ready=0;wire[15:0] x_record;wire[6:0] x_ordinal;wire[3:0] x_group;wire[2047:0] x_data;
 reg[15:0] issuer_tag=16'hf124;
 wire service_req_valid,service_rsp_ready;reg service_req_ready=0,service_rsp_valid=0,service_rsp_we=0,service_fault=0;
 wire[36:0] service_req_addr;wire[15:0] service_req_tag;reg[15:0] service_rsp_tag=0;reg[255:0] service_rsp_data=0;
 wire fault;integer received=0,cycle=0,pending=0,which=0,j,sectorcount=0;
 reg[36:0] saved_address;reg[15:0] saved_tag;
 ot_hbm_sm_x_read #(.ENABLE(1)) dut(.*);
 function[31:0] word_value(input integer ordinal,input integer fragment_word);
  begin word_value=fragment_word<788?32'h12340000^32'(ordinal*1024+fragment_word):0;end
 endfunction
 function[255:0] sector(input[36:0] address);
  integer offset,ordinal,word_start,k;reg[255:0] data;
  begin offset=int'(address-installed_base);ordinal=offset/3328;word_start=(offset%3328)/4;data=0;
   for(k=0;k<8;k=k+1)data[k*32+:32]=word_value(ordinal,word_start+k);
   sector=data;
  end
 endfunction
 always @(negedge clk)if(rst_n)begin
  cycle=cycle+1;x_ready=cycle%7!=0;service_req_ready=cycle%3!=0&&pending==0&&!service_rsp_valid;
  if(pending>0)begin pending=pending-1;if(pending==0)begin service_rsp_valid=1;service_rsp_tag=saved_tag;service_rsp_data=sector(saved_address);
   if(which==2)service_rsp_tag=saved_tag^1;
   if(which==3&&(saved_address-installed_base)%3328==3296)service_rsp_data[255]=1;
  end end
 end
 always @(posedge clk)if(rst_n)begin
  if(x_req_valid&&x_req_ready)x_req_valid<=0;
  if(service_req_valid&&service_req_ready)begin saved_address<=service_req_addr;saved_tag<=service_req_tag;pending<=2;sectorcount<=sectorcount+1;end
  if(service_rsp_valid&&service_rsp_ready)service_rsp_valid<=0;
  if(x_valid&&x_ready)begin
   if(x_error||x_record!=installed_record||x_ordinal!=7'(received/13)||x_group!=4'(received%13))$fatal(1,"X identity");
   for(j=0;j<64;j=j+1)if(x_data[j*32+:32]!==word_value(received/13,(received%13)*64+j))$fatal(1,"X reconstruction");
   received<=received+1;
  end
  if(which!=0&&fault)begin if(x_valid||service_req_valid)$fatal(1,"fault side effect");$display("PASS X negative %0d",which);$finish;end
  if(which==0&&fault)$fatal(1,"unexpected X fault");
  if(received==1664)begin if(sectorcount!=13312)$fatal(1,"X sector count");$display("PASS X extent128 groups1664 sectors13312");$finish;end
 end
 initial begin if($value$plusargs("CASE=%d",which))begin end repeat(3)@(negedge clk);rst_n=1;x_req_valid=1;if(which==1)x_req_record=0;end
 initial begin #3000000;$fatal(1,"bounded X component did not complete");end

 reg[2104:0] corrupted;
 initial begin
  wait(rst_n);
  if(which==4)begin wait(service_req_valid);@(negedge clk);corrupted=dut.sectors.q^2105'd1;force dut.sectors.q=corrupted;end
 end
endmodule

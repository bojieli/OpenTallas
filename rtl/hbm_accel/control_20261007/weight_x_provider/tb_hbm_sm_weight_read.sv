`timescale 1ns/1ps
module tb_hbm_sm_weight_read;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg installed_valid=1;reg[31:0] installed_line_base=32'd100;reg[32:0] installed_line_limit=33'd116;
 wire req_v,req_ready;wire[31:0] req_addr;wire[9:0] req_tag;
 wire rsp_v;wire[9:0] rsp_tag;wire[1087:0] rsp_data;
 reg[15:0] issuer_tag=16'hf123;
 wire service_req_valid,service_rsp_ready;reg service_req_ready=0,service_rsp_valid=0,service_rsp_we=0,service_fault=0;
 wire[36:0] service_req_addr;wire[15:0] service_req_tag;
 reg[15:0] service_rsp_tag=0;reg[255:0] service_rsp_data=0;
 wire fault;integer sent=0,received=0,cycle=0,pending=0,which=0,j,sectorcount=0;
 reg[36:0] saved_address;reg[15:0] saved_tag;
 reg source_valid=0;wire source_ready;
 wire[41:0] source_data={32'(100+sent),10'(sent)};
 ot_hbm_accel_smh_reqrl #(.W(42)) actual_request_port(.clk(clk),.rst_n(rst_n),.s_valid(source_valid),.s_ready(source_ready),.s_data(source_data),.m_valid(req_v),.m_ready(req_ready),.m_data({req_addr,req_tag}));
 ot_hbm_sm_weight_read #(.ENABLE(1)) dut(.*);
 function[255:0] sector(input[36:0] address);
  integer line,part,k;reg[255:0] data;
  begin line=int'(address/160);part=int'((address%160)/32);data=0;
   for(k=0;k<8;k=k+1)if(part<4||k<2)data[k*32+:32]=32'(line^(part*8+k));
   sector=data;
  end
 endfunction
 always @(negedge clk)begin
  if(rst_n)begin
   cycle=cycle+1;source_valid=sent<16;service_req_ready=cycle%3!=0&&pending==0&&!service_rsp_valid;
   if(pending>0)begin pending=pending-1;if(pending==0)begin service_rsp_valid=1;service_rsp_tag=saved_tag;service_rsp_data=sector(saved_address);
    if(which==2)service_rsp_tag=saved_tag^1;
    if(which==3&&saved_address%160==128)service_rsp_data[1279-1024]=1;
   end end
   if(which==1&&sent==0)installed_line_limit=100;
  end
 end
 always @(posedge clk)if(rst_n)begin
  if(source_valid&&source_ready)sent<=sent+1;
  if(service_req_valid&&service_req_ready)begin saved_address<=service_req_addr;saved_tag<=service_req_tag;pending<=3;sectorcount<=sectorcount+1;end
  if(service_rsp_valid&&service_rsp_ready)service_rsp_valid<=0;
  if(rsp_v)begin
   if(rsp_tag!=10'(received))$fatal(1,"tag ordering");
   for(j=0;j<34;j=j+1)if(rsp_data[j*32+:32]!==32'((100+received)^j))$fatal(1,"line reconstruction");
   received<=received+1;
  end
  if(which!=0&&fault)begin
   if(rsp_v||req_ready||service_req_valid)$fatal(1,"fault side effect");
   $display("PASS weight negative %0d",which);$finish;
  end
  if(which==0&&fault)$fatal(1,"unexpected fault");
  if(received==16)begin if(sectorcount!=80)$fatal(1,"sector count");$display("PASS weight16 sectors80 actual_REQCR2");$finish;end
 end
 initial begin if($value$plusargs("CASE=%d",which))begin end repeat(3)@(negedge clk);rst_n=1;end
 initial begin #1000000;$fatal(1,"bounded component did not complete");end

 reg[1336:0] corrupted;
 initial begin
  wait(rst_n);
  if(which==4)begin wait(service_req_valid);@(negedge clk);corrupted=dut.sectors.q^1337'd1;force dut.sectors.q=corrupted;end
 end
endmodule

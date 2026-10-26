`timescale 1ns/1ps
module tb_qkd_host_ingest_station;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[4:0]lpc=5'd17;reg[290:0]fi=0;wire[290:0]fo;wire[287:0]host_es;
 reg host_cr=0,host_ack=0,host_fault=0;reg[31:0]ci=0,ai=0;wire[31:0]co,ao;reg fault_i=0;wire fault_o;
 qkd_host_ingest_station #(.MUT(MUT))dut(.*);
 integer nlocal=0,nforward=0,checks=0;reg[255:0]data=256'h123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef;
 task tick;begin @(posedge ck);#1;end endtask
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 always @(posedge ck)if(rst_n)begin
  if(host_es[0])begin
   nlocal++;check(host_es[287:286]==3&&host_es[285:276]=={5'd7,5'd9}&&host_es[275:257]==19'd24430&&host_es[256:1]==(data^256'd17),"exact static ABI");
  end
  if(fo[0])nforward++;
 end
 initial begin
  repeat(4)tick();rst_n=1;repeat(4)tick();
  for(integer d=0;d<32;d++)begin @(negedge ck);fi={data^256'(d),19'd24430,5'd9,5'd7,5'(d),1'b1};end
  @(negedge ck);fi[0]=0;repeat(8)tick();check(nlocal==1&&nforward==32&&!fault_o,"exactly one logical PC consumes");
  @(negedge ck);ci=32'h80000001;ai=32'h00400008;host_cr=1;host_ack=1;
  @(negedge ck);ci=0;ai=0;host_cr=0;host_ack=0;tick();
  check(co==32'h80020001&&ao==32'h00420008,"independent credit and commit vectors");
  @(negedge ck);host_fault=1;@(negedge ck);host_fault=0;repeat(5)tick();check(fault_o,"fault chain sticky");
  $display("PASS HOST_INGEST_STATION checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule

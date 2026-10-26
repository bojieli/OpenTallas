`timescale 1ns/1ps
module tb_qkd_host_ingest_map;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[289:0]ing=0;wire ing_cr;wire[1163:0]out;reg[127:0]out_cr=0;reg[7:0]ack_n=0;
 wire marker_v;wire[65:0]marker;reg marker_cr=0;wire fault;wire[31:0]issued,landed;
 qkd_host_ingest_map #(.MUT(MUT))dut(.ord_cr(1'b0),.issue_v(),.issue_pc(),.*);
 integer checks=0,nout=0,cycles=0,first=-1,last=0;reg[31:0]addrq[0:255];reg[255:0]dq[0:255];
 reg[65:0]marker_expected=66'h0123456789abcdef0;
 function[255:0]pat(input integer k);begin for(integer j=0;j<8;j++)pat[j*32+:32]=32'(k)*32'h9e3779b9+32'(j);end endfunction
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task tick;begin @(posedge ck);#1;end endtask
 task push(input[31:0]a,input[255:0]d);begin @(negedge ck);ing={d,a,1'b1,1'b1};@(negedge ck);ing[0]=0;end endtask
 always @(posedge ck)begin
  cycles++;out_cr<=0;
  for(integer s=0;s<4;s++)if(out[s*291])begin
   integer j,b,c,r,pc,stack,t,e,scale;
   reg[31:0]a;reg[290:0]w;
   a=addrq[nout];w=out[s*291+:291];
   if(!a[31])begin j=((a>>7)&127)|(((a>>15)&7)<<7);b=((j>>7)<<2)|(j&3);c=(j>>2)&31;r=64+((a>>18)&63);pc=a&31;stack=(a>>5)&3;end
   else begin
    e=a&32'h7fffffff;
    if(e<19447808)begin t=e/128;pc=e%32;stack=(e/32)%4;j=t%1024;r=24427+t/1024;end
    else begin scale=e-19447808;pc=scale%32;stack=(scale/32)%4;j=384+scale/128;r=24575;end
    b=((j/128)<<2)|(j%4);c=(j/4)%32;
   end
   check(s==stack&&w[5:1]==pc&&w[10:6]==b&&w[15:11]==c&&w[34:16]==r,"production sector physical map");
   check(w[290:35]==dq[nout],"sector data exact");
   if(first<0)first=cycles;last=cycles;nout++;out_cr[s*32+pc]<=1;
  end
  if(marker_v)check(marker==marker_expected&&landed==issued,"marker visibility exact");
 end
 initial begin
  for(integer k=0;k<64;k++)begin
   // Full logical PC sweep; valid layer35 and dummy-bit=0 at CTX8192.
   addrq[k]=32'((35<<18)|((k&7)<<15)|((k*13&127)<<7)|k);dq[k]=pat(k);
  end
  for(integer k=64;k<128;k++)begin addrq[k]=32'h80000000|32'((151000+(k&15))*128+(k&127));dq[k]=pat(k);end
  for(integer k=128;k<192;k++)begin addrq[k]=32'h80000000|32'(19447808+(k-128)*137);dq[k]=pat(k);end
  repeat(4)tick();rst_n=1;repeat(3)tick();
  // Saturated, one-sector/cycle input: no artificial command serialization.
  @(negedge ck);
  for(integer k=0;k<192;k++)begin ing={dq[k],addrq[k],1'b1,1'b1};@(negedge ck);end
  ing=0;repeat(15)tick();check(nout==192&&!fault&&issued==192,"all three real map regions");
  check(last-first==191,"one sector each cycle measured");
  push(32'hffffffff,{190'd0,marker_expected});repeat(15)tick();check(!marker_v&&landed==0,"marker waits on commits");
  @(negedge ck);ack_n=8'd128;@(negedge ck);ack_n=8'd64;@(negedge ck);ack_n=0;
  repeat(15)tick();check(landed==192&&!fault,"commit count exact");
  // QPIPE forbids RMW and an out-of-range layer is rejected.
  push(32'h01000000,0);repeat(8)tick();check(fault,"out of range address rejected");
  $display("PASS HOST_INGEST_MAP checks=%0d sectors=%0d interval=%0d",checks,nout,last-first);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule

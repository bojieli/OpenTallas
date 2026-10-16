`timescale 1ns/1ps
module ot_hgi_quant_decode(input clk,rst_n,v,generic_enable,legacy_fp4,input[127:0]header,input[1023:0]x,output vo,output[511:0]y,output fault,decode_fault);
 assign vo=0;assign y=0;assign fault=0;assign decode_fault=0;
endmodule
module tb;
 reg clk=0;always #1 clk=~clk;reg rst_n=0;reg[1408:0]cmd=0;
 wire ready,done,fault,drained,req_v,rsp_r;wire[336:0]req;reg req_r=0,rsp_v=0,provider_fault=0;reg[272:0]rsp=0;
 ot_hgi_quant_vm_transport #(.ENABLE(1),.SERIAL_SHAPE(1))dut(.*);
 reg[255:0]a,o;reg[127:0]h;reg[63:0]ar,ac,orr,oc;integer cases=0,waited;
 task check(input[19:0]nr,nc,input[31:0]rowstride,input[15:0]inner,input bcast);
 begin
  rst_n=0;cmd=0;repeat(3)@(negedge clk);rst_n=1;while(!ready)@(negedge clk);
  a=0;o=0;h=0;h[127:124]=4;h[123:118]=4;h[99:93]=7'b0010001;
  a[1:0]=1;o[1:0]=1;a[5]=bcast;a[87:68]=nr;a[67:48]=nc;a[119:88]=rowstride;a[135:120]=inner;
  o=a;o[5]=0;o[47:8]=40'd131072;
  cmd[0]=1;cmd[1+:128]=h;cmd[385+:256]=a;cmd[1153+:256]=o;@(negedge clk);cmd=0;
  waited=0;while(!dut.val2&&waited<30)begin @(negedge clk);waited=waited+1;end
  if(!dut.val2)$fatal(1,"span did not finish");
  ar=nr-64'd1;ac=nc-64'd1;orr=nr-64'd1;oc=nc-64'd1;
  ar=ar*rowstride;ac=ac*(bcast?64'd0:(inner==0?64'd1:inner));
  orr=orr*rowstride;oc=oc*(inner==0?64'd1:inner);
  if(dut.aspan_q!==ar+ac||dut.ospan_q!==orr+oc||dut.orow_q!==oc)
   $fatal(1,"product mismatch nrow=%d ncol=%d rowstride=%h inner=%h bcast=%b",nr,nc,rowstride,inner,bcast);
  cases=cases+1;
 end endtask
 initial begin
  for(integer b=0;b<2;b=b+1)for(integer n=0;n<4;n=n+1)for(integer st=0;st<4;st=st+1)
   check(n==0?20'd1:n==1?20'd17:n==2?20'd65537:20'hfffff,n==0?20'd32:n==1?20'd512:n==2?20'd65536:20'hfffe0,st==0?32'd0:st==1?32'd1:st==2?32'h80000000:32'hffffffff,st==0?16'd0:st==1?16'd1:st==2?16'h8000:16'hffff,b);
  $display("PASS QUANT_SERIAL_SPAN_CORNER cases=%0d independent64bitmultiply",cases);$finish;
 end
endmodule

`timescale 1ns/1ps
module tb_actual;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,start=0;reg[15:0]epoch=0,ie=0;reg[5:0]layer=0;
 reg pv0=0,pv1=0,rv=0;reg[16383:0]p0=0,p1=0;wire ov,fault;wire[547:0]record_out;
 qkd_result_finalize_collected #(.CONFIGURED(1),.CAPTURE_AGES({32{32'd63}}),.STACK_FIRST({32'd104,32'd96,32'd88,32'd80}))dut(
 .clk_join({32{ck}}),.clk_merge({3{ck}}),.clk_control(ck),.rst_n(rst_n),.start(start),.epoch(epoch),.layer(layer),
 .reciprocal({4{32'h3f000000}}),.reciprocal_valid(rv),.reciprocal_epoch(ie),
 .p0_valid(pv0),.p1_valid(pv1),.p0_epoch(ie),.p1_epoch(ie),.p0_partial(p0),.p1_partial(p1),
 .result_v(ov),.result_record(record_out),.fault(fault));
 function[511:0] data(input integer b,input integer context_id);
 integer j;begin for(j=0;j<16;j=j+1)data[32*j+:32]={1'b0,8'(120+b%8),23'(j*1024+context_id*256+b)};end endfunction
 task tick;begin @(posedge ck);#1;@(negedge ck);end endtask
 integer c,k,b,count;reg[15:0]old_ep;reg[5:0]old_layer;reg[511:0]wanted;
 initial begin
  tick;rst_n=1;tick;
  for(c=0;c<2;c=c+1)begin
   epoch=16'hfffe+c;ie=epoch;layer=20+c;old_ep=epoch;old_layer=layer;
   for(b=0;b<32;b=b+1)begin p0[b*512+:512]=data(b,c);p1[b*512+:512]=data(b,c);end
   start=1;tick;start=0;epoch=16'h17;layer=1;count=0;
   for(k=0;k<120;k=k+1)begin
    pv0=k==7;pv1=k==19;rv=k==47;tick;
    if(fault)$fatal(1,"actual source fault c=%0d age=%0d",c,k);
    if(ov!==(k>=82&&k<114))$fatal(1,"actual output age=%0d v=%b",k,ov);
    if(ov)begin
     wanted=data(count,c);
     if(record_out!=={5'd0,4'd3,old_layer,old_ep,5'(count),wanted})$fatal(1,"actual result mismatch c=%0d beat=%0d",c,count);
     count=count+1;
    end
   end
   if(count!=32)$fatal(1,"actual result count");
  end
  $display("PASS actual 32x16 ADD7/MUL6 to distributed548: two contexts 1024 exact FP32 words, held epoch/layer");$finish;
 end
endmodule

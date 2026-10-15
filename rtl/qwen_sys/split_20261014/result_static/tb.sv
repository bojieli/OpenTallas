`timescale 1ns/1ps
module tb;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[31:0]cv=0,pv=0;reg[511:0]ce=0,pe=0;reg[191:0]cl=0;reg[16383:0]pd=0;reg mc=0;
 wire ov,fault;wire[547:0]rec;
 qkd_result_static #(.DATA_MUT(MUT))dut(.clk_node({32{ck}}),.clk_merge({3{ck}}),.rst_n(rst_n),.cmd_v(cv),.cmd_epoch(ce),.cmd_layer(cl),.merge_cmd_v(mc),
 .producer_v(pv),.producer_epoch(pe),.producer_data(pd),.result_v(ov),.result_record(rec),.fault(fault));
 integer t,b,w,c,mode,count,passed=0;reg[511:0]expected;
 task tick;begin @(posedge ck);#1;@(negedge ck);end endtask
 function[511:0] data(input integer context_id,input integer beat);
 integer j;begin for(j=0;j<16;j=j+1)data[j*32+:32]=32'h51800000^(context_id*65536)^(beat*256)^j;end endfunction
 task reset;begin rst_n=0;cv=0;mc=0;pv=0;tick;rst_n=1;tick;end endtask
 task frame(input integer context_id,input integer badmode);
 integer k,i;reg[15:0]e;reg[5:0]l;
 begin
  e=16'h100+context_id;l=context_id%36;
  cv='1;mc=1;pv=0;
  for(i=0;i<32;i=i+1)begin ce[i*16+:16]=e;cl[i*6+:6]=l;pe[i*16+:16]=e;pd[i*512+:512]=data(context_id,i);end
  tick;cv=0;mc=0;count=0;
  // Command wires change immediately after capture: results must retain OLD context.
  ce='1;cl='1;
  for(k=0;k<70;k=k+1)begin
   pv=(k==8)?32'hffffffff:0;
   if(badmode==1&&k==8)pv[3]=0; // missing
   if(badmode==2&&k==9)pv[3]=1; // duplicate
   if(badmode==3&&k==7)pv[3]=1; // early
   if(badmode==4&&k==8)pe[3*16+:16]=e-1; // stale
   tick;
   if(badmode==0)begin
    if(fault)$fatal(1,"unexpected fault context=%0d age=%0d",context_id,k);
    if(ov!==(k>=34&&k<66))$fatal(1,"output age %0d v=%b",k,ov);
    if(ov)begin
     expected=data(context_id,count);
     if(rec!=={5'd0,4'd3,l,e,5'(count),expected})$fatal(1,"record mismatch context=%0d beat=%0d",context_id,count);
     count=count+1;
    end
   end
  end
  if(badmode==0&&count!=32)$fatal(1,"count");
  if(badmode!=0&&!fault)$fatal(1,"missing expected fault mode=%0d",badmode);
  passed=passed+1;
 end endtask
 initial begin
  reset;
  for(c=0;c<4;c=c+1)frame(c,0); // consecutive contexts, no reset
  for(mode=1;mode<=4;mode=mode+1)begin reset;frame(10+mode,mode);end
  $display("PASS distributed548 %0d frames 128 exact records; missing duplicate early stale faults",passed);$finish;
 end
endmodule

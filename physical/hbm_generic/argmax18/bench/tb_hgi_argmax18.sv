`timescale 1ns/1ps
module tb_hgi_argmax18;
 reg clk=0; always #0.4166665 clk=~clk;
 reg rst_n=0,in_v=0,in_last=0,in_bias_en=0;
 reg [7:0] in_mask=0;
 reg [255:0] in_vals=0,in_bias=0;
 reg [6:0] cfg_rank=0;reg[17:0]cfg_imm_a=0;
 wire [31:0] value_o,ds_value;wire v,nan_o,fault,range_o;wire[17:0]idx;
 wire dv,dnan,dfault,drange;wire[17:0]didx;
 wire rv,rnan,rfault;wire[16:0]ridx;
 ot_hgi_argmax18_m #(.GENERIC18(1)) dut(clk,rst_n,in_v,in_last,in_bias_en,in_mask,in_vals,in_bias,cfg_rank,cfg_imm_a,v,idx,nan_o,fault,range_o,value_o);
 ot_hgi_argmax18_m ds(clk,rst_n,in_v,in_last,in_bias_en,in_mask,in_vals,in_bias,cfg_rank,cfg_imm_a,dv,didx,dnan,dfault,drange,ds_value);
 ot_dshbm_argmax_m #(.LP(8),.IW(17),.FLAT(7),.FAST(1)) reference(clk,rst_n,in_v,in_last,in_bias_en,in_mask,in_vals,in_bias,rv,ridx,rnan,rfault);
 reg [31:0] eval[0:15];integer expected[0:15];integer enan[0:15],erange[0:15];integer sent=0,seen=0,cycles=0;
 always @(posedge clk) begin
  #0.01;
  if(rst_n) begin
   cycles=cycles+1;
   if({dv,dnan,dfault,drange}!={rv,rnan,rfault,1'b0} || (rv && didx!={1'b0,ridx})) $fatal(1,"DS_LOCKSTEP");
   if(v) begin
    if(seen>=sent || idx!==expected[seen][17:0] || nan_o!==enan[seen][0] || range_o!==erange[seen][0] || fault || value_o!==eval[seen]) $fatal(1,"ARGMAX row=%0d idx=%0d exp=%0d nan=%b range=%b",seen,idx,expected[seen],nan_o,range_o);
    seen=seen+1;
   end
  end
 end
 task row(input integer count,winner,rank,step,kind);
 integer b,j,id;reg[31:0]value;
 begin
  eval[sent]=(kind==4)?32'h40400000:(kind==2)?32'h7fc00001:(kind==1)?32'h40a00000:(kind==3)?32'h00000000:32'h40800000; expected[sent]=winner+rank*step; enan[sent]=(kind==2);erange[sent]=(expected[sent]>=262144);sent=sent+1;
  for(b=0;b<(count+7)/8;b=b+1)begin
   @(negedge clk);in_v=1;in_bias_en=(kind==4);in_last=(b==(count+7)/8-1);in_mask=0;
   // Deliberately perturb config after entry: wrapper must retain the row binding.
   cfg_rank=(b==0)?rank:7'd1;cfg_imm_a=(b==0)?step:18'd13;
   for(j=0;j<8;j=j+1)begin
    id=b*8+j;in_mask[j]=(id<count);value=32'hbf800000;
    if(kind==0 && id==winner)value=32'h40800000;
    if(kind==4 && id==winner)value=32'h40000000;
    in_bias[32*j+:32]=(kind==4)?32'h3f800000:32'h00000000;
    if(kind==1 && (id==winner || id==winner+8))value=32'h40a00000;
    if(kind==2 && (id==winner || id==winner+1))value=32'h7fc00001;
    if(kind==3)value=(id%2)?32'h80000000:32'h00000000;
    in_vals[32*j+:32]=value;
   end
  end
 end
 endtask
 initial begin
 repeat(4)@(negedge clk);rst_n=1;
 row(151936,151935,0,0,0); // full Qwen row, high bit exercises IW18
 row(128,11,3,37984,1); // equal maxima in same lane across beats
 row(17,4,2,37984,2); // first NaN and partial mask
 row(9,0,0,0,3); // signed zeros tie
 row(8,7,95,2048,0); // DS TP96 offset
 row(33,24,0,0,4); // exact2+1 biased winner; DS native lockstep
 row(8,7,127,262143,0); // range must not silently truncate
 @(negedge clk);in_v=0;in_last=0;
 repeat(40)@(negedge clk);
 if(seen!=sent)$fatal(1,"MISSING %0d/%0d",seen,sent);
 $display("HGI_ARGMAX18 PASS rows=%0d cycles=%0d DS_LOCKSTEP=1",seen,cycles);$finish;
 end
endmodule

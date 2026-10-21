`timescale 1ns/1ps
module tb_tr;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,w_en_i=0,w_half_i=0,r_half_i=0,sel_i=0;
 reg[7:0]w_cnt_i=0,r_c_i=0;reg[3:0]w_pad_i=0;
 reg[1059:0]w_g=0;reg[575:0]qk_ib=0;
 wire[575:0]col[0:3],eib[0:3],rcol[0:3],reib[0:3];
 integer collisions=0;reg prev_en=0,prev_half=0;
 integer checks=0,errors=0;reg qualified=0;
 for(genvar x=0;x<4;x=x+1)begin:g
  ot_hdc_v41x_attn_tr_x #(.TD(32),.DPT(8),.NL(4),.XOFF(8*x))dut(.clk(clk),.rst_n(rst_n),.w_en_i(w_en_i),.w_half_i(w_half_i),.w_cnt_i(w_cnt_i),.w_pad_i(w_pad_i),.w_g(w_g),.r_half_i(r_half_i),.r_c_i(r_c_i),.sel_i(sel_i),.qk_ib(qk_ib),.col(col[x]),.eib(eib[x]));
  ot_hdc_v41x_attn_tr_x_ref #(.TD(32),.DPT(8),.NL(4),.XOFF(8*x))refdut(.clk(clk),.rst_n(rst_n),.w_en_i(w_en_i),.w_half_i(w_half_i),.w_cnt_i(w_cnt_i),.w_pad_i(w_pad_i),.w_g(w_g),.r_half_i(r_half_i),.r_c_i(r_c_i),.sel_i(sel_i),.qk_ib(qk_ib),.col(rcol[x]),.eib(reib[x]));
 end
 always@(posedge clk)begin #1;if(qualified)begin
  checks=checks+1;for(integer x=0;x<4;x=x+1)if({col[x],eib[x]}!=={rcol[x],reib[x]})begin errors=errors+1;if(errors<5)$display("TR_MISMATCH check=%0d xoff=%0d",checks,x*8);end
 end end
 initial begin
  for(integer epoch=0;epoch<3;epoch=epoch+1)begin
   @(negedge clk);qualified=0;prev_en=0;prev_half=0;rst_n=0;w_en_i=0;repeat(4)@(negedge clk);rst_n=1;
   for(integer c=0;c<1600;c=c+1)begin
    w_en_i=(c<20)||(c%7!=2);w_half_i=(c<20)?((c/8)%2):((c/3)%2);w_cnt_i=8'(c%8);
    r_half_i=c%2;r_c_i=8'((c/2)%8);sel_i=c%4!=1;w_pad_i=4'(c%16);
    for(integer lane=0;lane<4;lane=lane+1)begin
     for(integer b=0;b<9;b=b+1)w_g[lane*265+:265]=(w_g[lane*265+:265]<<32)^32'(epoch*123451+c*9871+lane*113+b*73);
     w_g[lane*265+264]=(lane+c)%2;
    end
    for(integer b=0;b<18;b=b+1)qk_ib=(qk_ib<<32)^32'(epoch*1123+c*997+b*67);
    qualified=c>=24;
    if(qualified&&prev_en&&(r_half_i==prev_half))collisions=collisions+1;
    prev_en=w_en_i;prev_half=w_half_i;
    @(negedge clk);
   end
  end
  $display("TR_COLLISION_EDGES %0d",collisions);if(collisions<1500)$fatal(1,"collision coverage");
  $display("TR_RESULT checks=%0d vectors=%0d errors=%0d",checks,checks*4,errors);
  if(checks<4500||errors!=0)$fatal(1,"transpose equivalence");$finish;
 end
endmodule

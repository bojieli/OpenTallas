`timescale 1ns/1ps
module ot_hdc_v41x_hcp_lanes(input wire clk,rst_n,fst,gov_i,input wire[7:0]lv_i,ss_i,input wire[255:0]w_i,s_i,input wire[127:0]x_i,output wire[255:0]y,output wire lf);
 assign y=0;assign lf=0;
endmodule
module tb_hgi_hc_bank_shell_control_static;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,d_v=0,d_ss=0,f_in=0;reg[5:0]nv=0;reg[15:0]wa=0,xa=0;
 wire ov,oss,fo,rov,ross,rfo;wire[5:0]onv,ronv;wire[15:0]owa,oxa,rowa,roxa;
 wire[31:0]lv,ss;wire go;wire mf;
 ot_hgi_hc_bank_shell_static dut(.clk(clk),.rst_n(rst_n),.weight_ap(278'd0),.x_write_v(1'b0),.x_write_word(10'd0),.x_write_data(512'd0),
 .d_v(d_v),.d_ss(d_ss),.d_nv(nv),.d_wa(wa),.d_xa(xa),.f_in(f_in),.lane_fault(4'd0),
 .o_v(ov),.o_ss(oss),.o_nv(onv),.o_wa(owa),.o_xa(oxa),.f_out(fo),.lane_valid(lv),.lane_ss(ss),.lane_go(go),
 .weight_data(),.residual_data(),.write_done(),.read_valid(),.memory_fault(mf));
 ot_hdc_v41x_hcp_stage #(.W(32),.AW(16),.ML(3),.LM(8),.LA(7),.SOR(1),.LRST(1),.ADRST(0),.LG(8)) ref_(
 .clk(clk),.rst_n(rst_n),.first(1'b0),.d_v(d_v),.d_ss(d_ss),.d_nv(nv),.d_wa(wa),.d_xa(xa),.o_v(rov),.o_ss(ross),.o_nv(ronv),.o_wa(rowa),.o_xa(roxa),
 .sum_in(1024'd0),.sum_out(),.f_in(f_in),.f_out(rfo),.w_re(),.w_addr(),.w_data(1024'd0),.x_re(),.x_addr(),.x_data(512'd0));
 integer n,checks=0;
 always @(posedge clk)begin #0.01;
  if(rst_n&&checks>12)begin
   if({ov,oss,onv,owa,oxa,fo,lv,ss,go}!=={rov,ross,ronv,rowa,roxa,rfo,ref_.g_lg.lvs,ref_.g_lg.sss,ref_.g_lg.ov_r})$fatal(1,"BANK_SHELL_CONTROL mismatch n=%0d",checks);
   if(dut.w_re!==ref_.w_re||dut.x_re!==ref_.x_re||dut.w_addr!==ref_.w_addr||dut.x_addr!==ref_.x_addr||mf)$fatal(1,"BANK_SHELL_CONTROL address mismatch");
  end
  checks=checks+1;
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(n=0;n<1024;n=n+1)begin
   d_v=(n%7!=2);d_ss=(n%3==0);nv=6'(n%33);wa=16'((n%2)*128+(n%80));xa=16'(n%640);f_in=(n%67==9);@(negedge clk);
  end
  $display("BANK_SHELL_CONTROL PASS cycles=%0d exact_source_reference=1 arithmetic_stubbed=1",checks);$finish;
 end
endmodule

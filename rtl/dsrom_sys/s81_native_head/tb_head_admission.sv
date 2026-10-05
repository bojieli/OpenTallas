`timescale 1ns/1ps
module tb_head_admission;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,m_go=0;
 reg [20:0] m_k=5120;reg [1:0] m_split=0;
 reg [29:0] m_wbase=1,m_xbase=0,m_xks=1,m_xcs=5120,m_xjs=0,m_obase=10,m_ots=8,m_ojs=1;
 reg m_round=0,m_amax=1,m_mmode=0;
 reg s_idle=0;
 wire ready,idle,s_go,fault;wire [1:0] s_fmt;
 ot_v41_rom_adapt #(.OPT_NATIVE_HEAD(1),.S81_CAPTURE(1),.PHW(10),.VAW(30)) dut(
  .clk(clk),.rst_n(rst_n),.capture_command_ready(1'b1),
  .q_go(1'b0),.q_xbase(30'd0),.q_nb(8'd0),.q_wbase(30'd0),.q_ind(1'b0),.q_ibase(30'd0),.q_istride(30'd0),.q_obase(30'd0),.q_unrounded(1'b0),
  .m_go(m_go),.m_k(m_k),.m_split(m_split),.m_wbase(m_wbase),.m_xbase(m_xbase),.m_xks(m_xks),.m_xcs(m_xcs),.m_xjs(m_xjs),.m_obase(m_obase),.m_ots(m_ots),.m_ojs(m_ojs),
  .m_round(m_round),.m_amax(m_amax),.m_mmode(m_mmode),.i_m(3'd1),.i_xps(30'd0),.i_ops(30'd0),
  .ready(ready),.idle(idle),.vi_q(32'd0),.s_go(s_go),.s_fmt(s_fmt),.s_ready(1'b1),.s_idle(s_idle),.fault(fault));
 integer edges=0;
 always @(posedge clk)begin edges=edges+1;if(edges>80)$fatal(1,"finite adapter progress");end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;dut.keyrom[3]=32'hc0000001;
  @(negedge clk);m_go=1;@(negedge clk);m_go=0;
  wait(s_go);if(fault || s_fmt!=1)$fatal(1,"native head admission FP32");
  @(negedge clk);s_idle=1;wait(ready);
  @(negedge clk);m_amax=0;m_go=1;@(negedge clk);m_go=0;
  repeat(8)begin @(negedge clk);if(s_go)$fatal(1,"invalid round0 descriptor issued");end
  if(!fault)$fatal(1,"invalid round0 accepted");
  $display("PASS_SOURCE_HEAD_ROUND0_AMAX_FP32_AND_INVALID_ADMISSION");$finish;
 end
endmodule

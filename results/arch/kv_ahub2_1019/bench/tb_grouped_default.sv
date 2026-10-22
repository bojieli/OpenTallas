`timescale 1ns/1ps
module tb_grouped_default;
 reg clk=0,core_rst_n=0,child_rst_n=0,command_valid=0,return_valid=0;
 reg [267:0] command_word;
 reg [67:0] return_word;
 wire [267:0] a_command,b_command;
 wire [67:0] a_return,b_return;
 wire [3:0] a_flags,b_flags;
 qkd_ahub_grouped_zh_transport_private a(
 .clk(clk),.core_rst_n(core_rst_n),.child_rst_n(child_rst_n),
 .command_valid(command_valid),.return_valid(return_valid),
 .command_word(command_word),.return_word(return_word),
 .child_command(a_command),.core_return(a_return),
 .command_out_valid(a_flags[0]),.return_out_valid(a_flags[1]),
 .command_accept(a_flags[2]),.return_accept(a_flags[3]));
 qkd_ahub_zh_transport_private b(
 .clk(clk),.core_rst_n(core_rst_n),.child_rst_n(child_rst_n),
 .command_valid(command_valid),.return_valid(return_valid),
 .command_word(command_word),.return_word(return_word),
 .child_command(b_command),.core_return(b_return),
 .command_out_valid(b_flags[0]),.return_out_valid(b_flags[1]),
 .command_accept(b_flags[2]),.return_accept(b_flags[3]));
 integer n,k;
 initial begin
  for(n=0;n<256;n=n+1)begin
   core_rst_n=n[0];child_rst_n=n[1];command_valid=n[2];return_valid=n[3];
   for(k=0;k<268;k=k+1)command_word[k]=((k*13+n*17)>>(k%7))&1;
   for(k=0;k<68;k=k+1)return_word[k]=((k*17+n*13)>>(k%5))&1;
   #1;
   if({a_command,a_return,a_flags}!=={b_command,b_return,b_flags})$fatal(1,"DEFAULT_FAIL sample=%0d",n);
   if({a_command,a_return,a_flags}!=={command_word,return_word,return_valid,command_valid,return_valid,command_valid})
    $fatal(1,"DEFAULT_FAIL direct_bypass sample=%0d",n);
   clk=~clk;#1;
  end
  $display("DEFAULT_PASS 256 arbitrary inputs/reset samples, 340 bits each");$finish;
 end
endmodule

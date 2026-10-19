`timescale 1ns/1ps
`default_nettype none
// Opt-in mixed descriptor semantics checker. Caller supplies its landed reset
// and the descriptor class/valid from the SAME command token, after relocation.
// Does not modify the SM command, packet checks, or any cycle of the data path.
module ot_hbm_svc_command_class_guard #(parameter integer ENABLE=0)(
 input wire clk,app_reset_n,
 input wire[191:0]assembled_command,
 input wire descriptor_class_at_command,context_valid_at_command,
 output reg fault
);
 wire magic_word=assembled_command[191:184]==8'ha2;
 wire[2:0]mode=assembled_command[183:181];
 always @(posedge clk or negedge app_reset_n)
  if(!app_reset_n)fault<=1'b0;
  else if(ENABLE!=0&&magic_word&&
          (!context_valid_at_command||mode==3'd3||mode[2]!=descriptor_class_at_command))fault<=1'b1;
endmodule
`default_nettype wire

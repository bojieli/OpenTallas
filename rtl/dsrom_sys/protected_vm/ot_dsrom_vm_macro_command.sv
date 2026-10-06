`timescale 1ns/1ps
// Independent local held address/permission seat. No delayed fault forgiveness.
module ot_dsrom_vm_macro_command #(parameter integer WIDTH=18)(
 input wire clk,cold_n,capture,input wire [WIDTH-1:0] d,
 output wire [WIDTH-1:0] command,output wire fault
);
 (* keep=1,dont_touch=1 *) reg [WIDTH-1:0] q,q_check;
 assign command=q;
 assign fault=q!=~q_check;
 // Address capture enable is a pipeline phase, never a full-packet compare.
 // Checked read/write permission is carried inside d, independently protected.
 always @(posedge clk)begin
  if(!cold_n)begin q<=0;q_check<={WIDTH{1'b1}};end
  else if(capture)begin q<=d;q_check<=~d;end
 end
endmodule

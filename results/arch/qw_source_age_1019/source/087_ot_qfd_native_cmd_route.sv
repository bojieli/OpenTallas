`timescale 1ns/1ps
// Source ABI cmd380 WSRC55/GO0 and ret95 fault94. No descriptor remap,
// completion generation, issue delay or status-derived clock/control gate.
module ot_qfd_native_cmd_route(
 input wire clk,input wire rst_n,
 input wire[379:0]cmd,
 input wire[94:0]rom_ret,input wire[94:0]native_ret,
 output wire[379:0]rom_cmd,output wire[379:0]native_cmd,
 output wire[94:0]ret
);
 reg native_selected,native_fault;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin native_selected<=0;native_fault<=0;end
  else begin
   if(cmd[0])native_selected<=cmd[55];
   if(native_ret[94])native_fault<=1;
  end
 assign rom_cmd={cmd[379:1],cmd[0]&&!cmd[55]};
 assign native_cmd={cmd[379:1],cmd[0]&&cmd[55]};
 wire[94:0]selected_ret=native_selected?native_ret:rom_ret;
 assign ret={selected_ret[94]|native_fault,selected_ret[93:0]};
endmodule

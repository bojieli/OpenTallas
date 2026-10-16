`timescale 1ns/1ps
// Fixed-name physical views of the existing E3 control FFs. No added register or cycle.
module qvm_write_control_w27_native (
 input wire clk,rst_n,we,
 input wire [26:0] d,
 output wire qwe,
 output wire [26:0] q
);
 ot_qfd_vm_write_control_t #(.W(27)) u_core(.clk(clk),.rst_n(rst_n),.we(we),.d(d),.qwe(qwe),.q(q));
endmodule
module qvm_write_control_w26_native (
 input wire clk,rst_n,we,
 input wire [25:0] d,
 output wire qwe,
 output wire [25:0] q
);
 ot_qfd_vm_write_control_t #(.W(26)) u_core(.clk(clk),.rst_n(rst_n),.we(we),.d(d),.qwe(qwe),.q(q));
endmodule

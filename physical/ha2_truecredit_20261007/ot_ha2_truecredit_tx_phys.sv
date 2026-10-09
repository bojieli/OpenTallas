// Fixed full-shape wrapper only; exact protocol source unchanged.
module ot_ha2_truecredit_tx_phys(
 input wire clk,rst_n,
 input wire[1:0] issue_v,arrival_v,return_v,
 input wire[1087:0] arrival_data,input wire[31:0] return_tag,
 output wire[1:0] issue_ready,send_v,
 output wire[1087:0] send_data,output wire[31:0] send_tag,
 output wire quiet,fault
);
 ot_ha2_truecredit_sender #(.W(544),.INJ(2),.AW(6),.TAGW(16),.REG(1)) u_core
 (.clk(clk), .rst_n(rst_n), .issue_v(issue_v), .arrival_v(arrival_v), .return_v(return_v), .arrival_data(arrival_data), .return_tag(return_tag), .issue_ready(issue_ready), .send_v(send_v), .send_data(send_data), .send_tag(send_tag), .quiet(quiet), .fault(fault));
endmodule

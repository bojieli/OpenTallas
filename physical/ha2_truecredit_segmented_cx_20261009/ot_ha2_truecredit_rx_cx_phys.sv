// credit-ready (2026-10-08): pipelined true-credit rx with CREDIT ready (ot_ha2_truecredit_receiver_p CREDIT=1, CRD=8):
// receiver_ready[i] carries the consumer's credit-return pulse (pin flop, registered credit counter); same ports/pins as rx_p.
module ot_ha2_truecredit_rx_cx_phys(
 input wire clk,rst_n,
 input wire[1:0] arrival_v,receiver_ready,
 input wire[1087:0] arrival_data,input wire[31:0] arrival_tag,
 output wire[1:0] send_v,return_v,
 output wire[1087:0] send_data,output wire[31:0] return_tag,
 output wire quiet,fault
);
 ot_ha2_truecredit_receiver_segmented_cx #(.SEGMENTED(1),.W(544),.INJ(2),.AW(6),.TAGW(16),.CREDIT(1),.CRD(8)) u_core
 (.clk(clk), .rst_n(rst_n), .arrival_v(arrival_v), .receiver_ready(receiver_ready), .arrival_data(arrival_data), .arrival_tag(arrival_tag), .send_v(send_v), .return_v(return_v), .send_data(send_data), .return_tag(return_tag), .quiet(quiet), .fault(fault));
endmodule

// safe-hbm (2026-10-08, REVIEW_20261008 C4 / S-C4): true-credit rx with the 64-deep queue in 1R1W SRAM
// (ot_ha2_truecredit_receiver_s: pin flops, WREG macro inputs, registered macro output, credit ready, CRD=8);
// same ports/pins/SDC as rx_c (2 x 64x512 macros per lane).
module ot_ha2_truecredit_rx_s_phys(
 input wire clk,rst_n,
 input wire[1:0] arrival_v,receiver_ready,
 input wire[1087:0] arrival_data,input wire[31:0] arrival_tag,
 output wire[1:0] send_v,return_v,
 output wire[1087:0] send_data,output wire[31:0] return_tag,
 output wire quiet,fault
);
 ot_ha2_truecredit_receiver_s #(.W(544),.INJ(2),.AW(6),.TAGW(16),.CREDIT(1),.CRD(8)) u_core
 (.clk(clk), .rst_n(rst_n), .arrival_v(arrival_v), .receiver_ready(receiver_ready), .arrival_data(arrival_data), .arrival_tag(arrival_tag), .send_v(send_v), .return_v(return_v), .send_data(send_data), .return_tag(return_tag), .quiet(quiet), .fault(fault));
endmodule

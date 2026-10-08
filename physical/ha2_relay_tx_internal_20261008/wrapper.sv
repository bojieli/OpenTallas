// INTERNAL-ONLY experiment: actual local D1 launch and TX share one clock tree.
// Upstream D34 selected-slot source and credit/reset/output parents are outside
// this vehicle and cannot be qualified from its timing result.
module ot_ha2_relay_tx_internal(
 input wire clk,rst_n,
 input wire [1:0] issue_v,arrival_v,return_v,
 input wire [1087:0] arrival_data,
 input wire [31:0] return_tag,
 output wire [1:0] issue_ready,send_v,
 output wire [1087:0] send_data,
 output wire [31:0] send_tag,
 output wire quiet,fault
);
 wire [1:0] local_v;
 wire [1087:0] local_data;
 wire launch_quiet,tx_quiet;
 ot_ha2_hub_launch_single #(.W(544),.INJ(2),.CAPTURE_ALWAYS(1)) u_launch(
 .clk(clk),.rst_n(rst_n),.v_in(arrival_v),.d_in(arrival_data),
 .v_out(local_v),.d_out(local_data),.quiet(launch_quiet));
 ot_ha2_truecredit_sender_capture #(.W(544),.INJ(2),.AW(6),.TAGW(16),.CAPTURE_ALWAYS(1)) u_tx(
 .clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(local_v),
 .arrival_data(local_data),.return_v(return_v),.return_tag(return_tag),
 .issue_ready(issue_ready),.send_v(send_v),.send_data(send_data),.send_tag(send_tag),
 .quiet(tx_quiet),.fault(fault));
 assign quiet=launch_quiet&&tx_quiet;
endmodule

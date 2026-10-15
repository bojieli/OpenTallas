`default_nettype none
// Distinct physical identity for the current scorer metadata delay. No logic,
// reset, latency or arithmetic change relative to W25/D123/RESET0 ot_hdc_delay.
module hidx_meta_w25_d123_r0 (
 input wire clk, rst_n,
 input wire [24:0] d,
 output wire [24:0] q
);
 ot_hdc_delay #(.W(25),.D(123),.RESET(0)) delay(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
`default_nettype wire

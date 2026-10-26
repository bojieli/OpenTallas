`default_nettype none
// Distinct physical identity for the current scorer metadata delay: W25, exactly D123 edges, data unreset.
// Register-file form (ot_hdc_delay_rf): cycle-exact vs ot_hdc_delay W25/D123/RESET0 without 3,075 zero-logic hold hops.
module hidx_meta_w25_d123_r0 (
 input wire clk, rst_n,
 input wire [24:0] d,
 output wire [24:0] q
);
 ot_hdc_delay_rf #(.W(25),.D(123)) delay(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
`default_nettype wire

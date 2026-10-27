module rf_base(input clk, rst_n, output [1:0] q);
// Exact low-two-bit cone: real W=68 data lanes cannot influence pointer or low bits.
ot_hdc_delay_rf #(.W(2),.D(6)) u(.clk(clk),.rst_n(rst_n),.d(2'b01),.q(q));
endmodule

// Route top of ot_hdc_vreduce_f12 at the Qwen SU shape (SW 64, LV 7, LA 5, LM 6): a fixed-parameter wrapper, because
// yosys 0.68 asserts (rtlil.cc:1231) when the parameterised reducer is the top of a hierarchy pass.
module ot_hdc_vreduce_f12_w (input wire clk, input wire rst_n, input wire v_in, mx_in, sq_in, last_in, input wire [23:0] addr_in,
  input wire [64*32-1:0] x_in, output wire o_we, output wire [23:0] o_addr, output wire [31:0] o_data, output wire busy, output wire fault);
  ot_hdc_vreduce_f12 #(.LA(5), .LM(6), .SW(64), .LV(7), .AW(24)) u (.*);
endmodule

module gu_s4(input t3_ss, input [22:0] t3_sq, input t3_rinc, output [31:0] y);
 assign y = {t3_ss, 31'({8'd0, t3_sq}) + 31'(t3_rinc)};
endmodule

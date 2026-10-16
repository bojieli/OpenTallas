// Scoped physical probe of actual distributed-source mul status capture.
// MUT1 is a stopped real root, used only in the negative functional bench.
module ot_s81_engram_capture2_probe #(parameter integer MUT=0)(
 input wire clk,arst_n,input wire [1:0] d,output wire [1:0] q);
 wire actual_clk=(MUT==1)?1'b0:clk;
 ot_s81_engram_capture_slice #(.W(2)) capture(actual_clk,arst_n,d,q);
endmodule

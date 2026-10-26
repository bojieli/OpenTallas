module top(input clk, ce, input [5:0] a, output [31:0] q); ot_rom_64x32_m2 #(.INSTANCE("native_sysc"), .VIAMAP("profile.hex")) u_rom(.clk(clk),.ce_in(ce),.addr_in(a),.rd_out(q)); endmodule

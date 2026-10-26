module top(input clk,input ce,input [5:0]addr,output[31:0]q);
ot_rom_64x32_m2 #(.VIAMAP("profile.viamap.hex"), .INSTANCE("kv_dcal")) u(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(q));
endmodule

module top(input wclk,rclk,ce,input [4:0] addr,input[63:0] data,output[63:0] q);
ot_sram_1r1w2c_32x64_m1 u_m(.wclk(wclk),.rclk(rclk),.r_ce_in(ce),.r_addr_in(addr),.rd_out(q),.w_ce_in(ce),.w_addr_in(addr),.wd_in(data),.w_mask_in(64'hffffffffffffffff));
endmodule

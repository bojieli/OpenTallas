module macro_capture(input clk,ce,input [6:0] addr,output raw,captured);
wire [255:0] q;
ot_sram_1r1w_128x256_m1_r2c2 memory(.clk(clk),.r_ce_in(ce),.r_addr_in(addr),.rd_out(q),.w_ce_in(1'b0),.w_addr_in(7'b0),.wd_in(256'b0),.w_mask_in(256'b0),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
assign raw=q[0];
DFFHQNx1_ASAP7_75t_R capture(.CLK(clk),.D(q[0]),.QN(captured));
endmodule

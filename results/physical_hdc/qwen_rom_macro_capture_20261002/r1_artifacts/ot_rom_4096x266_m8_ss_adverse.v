module macro_capture(input clk,ce,input [11:0] addr,output raw,captured);
wire [265:0] q;
ot_rom_4096x266_m8 memory(.clk(clk),.ce_in(ce),.addr_in(addr),.rd_out(q));
assign raw=q[0];
DFFHQNx1_ASAP7_75t_R capture(.CLK(clk),.D(q[0]),.QN(captured));
endmodule

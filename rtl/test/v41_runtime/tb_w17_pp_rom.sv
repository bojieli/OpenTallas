`timescale 1ns/1ps
module tb_w17_pp_rom (
    input wire clk,
    input wire [7:0] ce,
    input wire [11:0] addr,
    output wire [273:0] q [8]
);
    genvar g;
    generate for (g=0; g<8; g=g+1) begin : g_rom
        // Both field names and empty runtime INSTANCE names, including logical b.
        ot_rom_4096x274_m8 #(.INSTANCE(g<4 ?
            (g==0 ? "e7_0" : g==1 ? "e7_1" : g==2 ? "e7b_0" : "e7b_1") :
            (g==4 ? "_0" : g==5 ? "_1" : g==6 ? "b_0" : "b_1"))) u_rom
            (.clk(clk), .ce_in(ce[g]), .addr_in(addr), .rd_out(q[g]));
    end endgenerate
endmodule

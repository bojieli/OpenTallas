`timescale 1ns/1ps
// Released normalization map; four17-bit IDs per72-bit word, eight real macros.
// Fault-free ROM contract, no ECC sidecar. Raw-token bounds checked before read.
module ot_dsrom_engram_token_map (
    input wire clk, rst_n, in_v,
    input wire [20:0] in_tok,
    output reg out_v,
    output reg [16:0] out_cid,
    output reg fault
);
    wire legal = in_tok < 21'd129280;
    wire [71:0] q [0:7];
    reg pending;
    reg [2:0] bank;
    reg [1:0] lane;
    genvar g;
    generate for(g=0;g<8;g=g+1) begin: m
`ifndef SYNTHESIS
        ot_rom_4096x72_m8 #(.INSTANCE($sformatf("tmap%0d",g))) rom (
`else
        ot_rom_4096x72_m8 rom (
`endif
            .clk(clk), .ce_in(in_v && legal && in_tok[16:14]==g),
            .addr_in(in_tok[13:2]), .rd_out(q[g]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin pending<=0;out_v<=0;out_cid<=0;fault<=0;bank<=0;lane<=0;end
        else begin
            pending<=in_v && legal;
            bank<=in_tok[16:14];lane<=in_tok[1:0];
            out_v<=pending;
            if(in_v && !legal) fault<=1;
            if(pending) begin
                out_cid<=q[bank][17*lane +:17];
                if(q[bank][17*lane +:17]>=17'd99092) begin fault<=1;out_v<=0;end
            end
        end
    end
endmodule

`timescale 1ns/1ps
// Eight full Engram slots (24 columns x8beats x512bits), protected by eight
// SECDED72 words per beat. Compact1536 addresses into6groups of3real256x256
// SRAMs; the top192bits of each third macro row are spare. Writer identity
// bounds are checked before capture. Slotready must await wr_pending drain.
module ot_dsrom_engram_prefetch #(
    parameter [71:0] READ_INJECT = 72'd0 // simulation exactness only, default off
) (
    input wire ck,rst_n,
    input wire wr_v,
    input wire [10:0] wr_addr, // {slot3,column5,beat3}; column<24
    input wire [511:0] wr_data,
    output wire wr_pending,
    input wire rd_v,
    input wire [10:0] rd_addr,
    output reg out_v,
    output reg [511:0] out_data,
    output reg out_ce,out_ue,
    output reg fault
);
    wire wr_ok=wr_addr[7:3]<24;
    wire rd_ok=rd_addr[7:3]<24;
    wire [10:0] wr_compact=({8'd0,wr_addr[10:8]}<<7)+({8'd0,wr_addr[10:8]}<<6)+{3'd0,wr_addr[7:0]};
    wire [10:0] rd_compact=({8'd0,rd_addr[10:8]}<<7)+({8'd0,rd_addr[10:8]}<<6)+{3'd0,rd_addr[7:0]};
    wire [575:0] encoded;
    genvar lane,group,bank;
    generate for(lane=0;lane<8;lane=lane+1) begin:g_encode
        ot_s81_secded_enc72 u_enc(.d(wr_data[64*lane+:64]),.c(encoded[72*lane+:72]));
    end endgenerate
    reg wr_q;
    reg [10:0] wa_q;
    reg [575:0] wd_q;
    reg rv_q;
    reg [2:0] rg_q;
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin wr_q<=0;rv_q<=0;fault<=0;end
        else begin
            wr_q<=wr_v&&wr_ok;
            rv_q<=rd_v&&rd_ok;
            if((wr_v&&!wr_ok)||(rd_v&&!rd_ok)||out_ue) fault<=1;
        end
    end
    always @(posedge ck) begin wa_q<=wr_compact;wd_q<=encoded;rg_q<=rd_compact[10:8];end
    assign wr_pending=wr_q;
    wire [767:0] bank_wdata={192'd0,wd_q};
    wire [767:0] group_data [0:5];
    generate for(group=0;group<6;group=group+1) begin:g_group
        for(bank=0;bank<3;bank=bank+1) begin:g_bank
            ot_sram_1r1w_256x256_m2_r2c2 u_sram(
                .clk(ck),.r_ce_in(rd_v&&rd_ok&&rd_compact[10:8]==group),.r_addr_in(rd_compact[7:0]),
                .rd_out(group_data[group][256*bank+:256]),
                .w_ce_in(wr_q&&wa_q[10:8]==group),.w_addr_in(wa_q[7:0]),
                .wd_in(bank_wdata[256*bank+:256]),.w_mask_in({256{1'b1}}),
                .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
        end
    end endgenerate
    wire [575:0] read_code=group_data[rg_q][575:0];
    wire [511:0] decoded;
    wire [7:0] ce,ue;
    generate for(lane=0;lane<8;lane=lane+1) begin:g_decode
        ot_s81_secded_dec72 u_dec(.c(read_code[72*lane+:72]^(lane==0?READ_INJECT:72'd0)),
            .d(decoded[64*lane+:64]),.ce(ce[lane]),.ue(ue[lane]));
    end endgenerate
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin out_v<=0;out_ce<=0;out_ue<=0;end
        else begin out_v<=rv_q;out_ce<=rv_q&&(|ce);out_ue<=rv_q&&(|ue);end
    end
    always @(posedge ck) out_data<=decoded;
endmodule

`timescale 1ns/1ps
// 24 complete 288-byte HBM rows in two actual128x256 SRAM macros.
// Read calendar: reserve scale-sector8 first, followed by code sectors0..7;
// input/read face and macro output each have real registers. No ready/credits.
module ot_hbm_engram_row_store_decode #(
    parameter integer MUT_SCALE = 0,
    parameter integer DECODE_ENABLE = 1
)(
    input wire clk,rst_n,epoch_begin,
    input wire write_v,input wire[4:0]write_row,input wire[3:0]write_sector,input wire[255:0]write_data,
    input wire read_v,input wire[4:0]read_row,input wire[3:0]read_sector,
    output reg out_v,output reg[4:0]out_row,output reg[2:0]out_block,output reg[511:0]out_data,
    output reg raw_v,output reg[4:0]raw_row,output reg[3:0]raw_sector,output reg[255:0]raw_data,
    output reg fault
);
    reg wv;reg[7:0]wa;reg[255:0]wd;
    reg[215:0]written;
    reg rv;reg[7:0]ra;
    wire[511:0]raw;reg[511:0]captured;
    reg[2:0]valid_pipe,bank_pipe;
    reg[4:0]row_pipe[0:2];reg[3:0]sector_pipe[0:2];
    reg[63:0]scales;reg[4:0]scale_row;reg scale_valid;
    wire[255:0]codes=captured[bank_pipe[2]*256+:256];
    wire[2:0]block=sector_pipe[2][2:0];
    wire[7:0]scale=MUT_SCALE?scales[7:0]:scales[block*8+:8];
    wire[511:0]decoded;
    ot_sram_1r1w_128x256_m1_r2c2 m0(.clk(clk),
        .r_ce_in(rv && ra[7]==1'b0),.r_addr_in(ra[6:0]),.rd_out(raw[0+:256]),
        .w_ce_in(wv && wa[7]==1'b0),.w_addr_in(wa[6:0]),.wd_in(wd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_sram_1r1w_128x256_m1_r2c2 m1(.clk(clk),
        .r_ce_in(rv && ra[7]==1'b1),.r_addr_in(ra[6:0]),.rd_out(raw[256+:256]),
        .w_ce_in(wv && wa[7]==1'b1),.w_addr_in(wa[6:0]),.wd_in(wd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    always @(posedge clk)captured<=raw;
    for(genvar l=0;l<32;l=l+1)begin:g_lane
        ot_hdc_engram_e4m3_bf16 dec(.code(codes[l*8+:8]),.scale(scale),.bf16(decoded[l*16+:16]));
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            written<=0;wv<=0;wa<=0;wd<=0;rv<=0;ra<=0;valid_pipe<=0;bank_pipe<=0;
            scales<=0;scale_row<=0;scale_valid<=0;out_v<=0;out_row<=0;out_block<=0;out_data<=0;raw_v<=0;raw_row<=0;raw_sector<=0;raw_data<=0;fault<=0;
            for(integer s=0;s<3;s=s+1)begin row_pipe[s]<=0;sector_pipe[s]<=0;end
        end else if(epoch_begin)begin
            written<=0;wv<=0;rv<=0;valid_pipe<=0;bank_pipe<=0;scale_valid<=0;
            out_v<=0;raw_v<=0;fault<=0;
        end else begin
            wv<=write_v;wa<=8'(write_row*9+write_sector);wd<=write_data;
            rv<=read_v;ra<=8'(read_row*9+read_sector);
            valid_pipe<={valid_pipe[1:0],read_v};
            bank_pipe<={bank_pipe[1:0],(8'(read_row*9+read_sector)>>7)!=0};
            row_pipe[0]<=read_row;sector_pipe[0]<=read_sector;
            for(integer s=1;s<3;s=s+1)begin row_pipe[s]<=row_pipe[s-1];sector_pipe[s]<=sector_pipe[s-1];end
            if(write_v && (write_row>=24 || write_sector>=9))fault<=1;
            if(wv && wa<216)begin
                if(written[wa])fault<=1;
                written[wa]<=1;
            end
            if(read_v && (read_row>=24 || read_sector>=9 || !written[8'(read_row*9+read_sector)]))fault<=1;
            raw_v<=valid_pipe[2];
            if(valid_pipe[2])begin raw_row<=row_pipe[2];raw_sector<=sector_pipe[2];raw_data<=codes;end
            out_v<=DECODE_ENABLE && valid_pipe[2] && sector_pipe[2]!=8;
            if(valid_pipe[2])begin
                if(sector_pipe[2]==8)begin
                    scales<=codes[63:0];scale_row<=row_pipe[2];scale_valid<=1;
                end else begin
                    if(DECODE_ENABLE && (!scale_valid || scale_row!=row_pipe[2]))fault<=1;
                    out_row<=row_pipe[2];out_block<=block;out_data<=decoded;
                end
            end
        end
    end
endmodule

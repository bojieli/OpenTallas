`timescale 1ns/1ps
`default_nettype none
// Compact probability image for the revisioned static parent. Reserved load
// group127 writes8 BF16 scalars in the low128bits of the existing2048bit port.
// Each scalar belongs to one physical result column (DS replicas or Qwen pairs).
// Real128x256 SRAM, registered macro inputs and a separate output capture.
// Read results have a fixed2edge latency; faults never gate or delay reads.
module ot_hbm_sm_attn_pstore #(parameter integer MUT=0)(
    input wire clk,rst_n,clear_v,
    input wire xw_en,
    input wire [6:0] xw_addr,xw_grp,
    input wire [2047:0] xw_data,
    input wire read_v,
    input wire [6:0] read_addr,
    output reg p_v,
    output reg [127:0] p_data,
    output reg fault
);
    reg wce,rce,v1;
    reg [6:0] wa,ra;
    reg [255:0] wd;
    reg [127:0] written;
    wire [255:0] rd;
    always @(posedge clk)begin
        wa<=xw_addr;wd<={128'd0,xw_data[127:0]};ra<=read_addr ^ ((MUT==1)?7'd1:7'd0);
        p_data<=rd[127:0];
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin wce<=0;rce<=0;v1<=0;p_v<=0;fault<=0;written<=0;end
        else begin
            wce<=xw_en && xw_grp==7'd127;
            rce<=read_v;v1<=rce;p_v<=v1;
            if(clear_v)begin
                written<=0;
                if(read_v || rce || wce || (xw_en && xw_grp==7'd127))fault<=1;
            end else if(wce)written[wa]<=1;
            if(read_v && (!written[read_addr] ||
               (xw_en && xw_grp==7'd127 && xw_addr==read_addr) || (wce && wa==read_addr)))fault<=1;
            if(xw_en && xw_grp==7'd127 && |xw_data[2047:128])fault<=1;
        end
    ot_sram_1r1w_128x256_m1_r2c2 u_p(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(rd),
        .w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
endmodule
`default_nettype wire

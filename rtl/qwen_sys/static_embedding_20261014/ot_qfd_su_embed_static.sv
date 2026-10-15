`timescale 1ns/1ps
// Static preloaded successor of ot_qfd_su_embed_pf: same exact INT8 decode,
// one physically mapped 64x512 row SRAM, no credit requester or held GO.
// Compiler completes all 65 preload slots before SU GO. A missing row faults
// on that exact GO edge and cannot cause an implicit retry or delayed launch.
module ot_qfd_su_embed_static #(
    parameter integer SW=64,AW=24,NW=18,HID=4096,EMB_CODE_LANES=64,EMB_ADDR_BASE=0,FI=1
)(input wire clk,rst_n,go_in,a_src,input wire [NW-1:0] tok,
  input wire [FI-1:0] f_in,output wire go_out,output wire [FI-1:0] f_out,output wire pend,
  input wire fill_begin,input wire [NW-1:0] fill_token,
  input wire preload_slot,preload_v,preload_scale,input wire [5:0] preload_word,
  input wire [NW-1:0] preload_token,input wire [511:0] preload_data,
  input wire [SW-1:0] su_va_re,input wire [SW*AW-1:0] su_va_addr,
  output wire [SW*32-1:0] su_va_q,output wire [SW-1:0] va_re,
  output wire [SW*AW-1:0] va_addr,input wire [SW*32-1:0] va_q,output reg fault);
    localparam integer ELI=6;
    reg [63:0] filled;
    reg scale_filled;
    reg [NW-1:0] buffer_token;
    reg [15:0] rscale;
    assign go_out=go_in;
    assign f_out=f_in;
    assign pend=1'b0;
    initial if(SW!=64||HID!=4096||EMB_CODE_LANES!=64||NW!=18)
        $fatal(1,"static embedding consumer requires full 4096-element/64-lane shape");
    integer lane;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin filled<=0;scale_filled<=0;buffer_token<=0;fault<=0;end
        else begin
            if(fill_begin) begin
                filled<=0;scale_filled<=0;buffer_token<=fill_token;
                if(fill_token>=151936||preload_slot||go_in) fault<=1;
            end
            if(preload_slot!=preload_v) fault<=1;
            if(preload_slot) begin
                if(preload_token!=buffer_token||fill_begin) fault<=1;
                if(preload_scale) begin
                    if(scale_filled) fault<=1;
                    scale_filled<=1;
                end else begin
                    if(filled[preload_word]) fault<=1;
                    filled[preload_word]<=1;
                end
            end
            if(go_in&&a_src&&(!(&filled)||!scale_filled||tok!=buffer_token||preload_slot||fill_begin)) fault<=1;
            if(|(bad&embed_sel)) fault<=1;
            for(lane=0;lane<SW;lane=lane+1)
                if(su_va_re[lane]&&embed_active&&
                   ((((su_va_addr[lane*AW+:AW]-EMB_ADDR_BASE)&(HID-1))/EMB_CODE_LANES)!=word)) fault<=1;
        end
    always @(posedge clk) if(preload_slot&&preload_v&&preload_scale) rscale<=preload_data[15:0];
    // ---- the decode (ot_qfd_su_embed term for term, the code ROM replaced by the row buffer) ----
    reg embed_active;
    reg [SW-1:0] embed_sel;
    reg [SW*ELI-1:0] embed_lanes;
    wire [511:0] code_q;
    wire code_re = |(su_va_re & {SW{embed_active}});
    wire [AW-1:0] word = ((su_va_addr[0 +: AW] - EMB_ADDR_BASE) & (HID - 1)) / EMB_CODE_LANES;
    ot_sram_1r1w_64x512_m1_r2c2 u_rb(
        .clk(clk),.r_ce_in(code_re),.r_addr_in(word[5:0]),.rd_out(code_q),
        .w_ce_in(preload_slot&&preload_v&&!preload_scale),.w_addr_in(preload_word),
        .wd_in(preload_data),.w_mask_in({512{1'b1}}),
        .rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(18'd0));
    assign va_re = su_va_re & ~({SW{embed_active}});
    assign va_addr = su_va_addr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            embed_active <= 1'b0;
            embed_sel <= 0;
        end else begin
            if (go_in) embed_active <= a_src;
            embed_sel <= su_va_re & {SW{embed_active}};
        end
    end
    wire [SW-1:0] bad;
    genvar el;
    generate for (el = 0; el < SW; el = el + 1) begin : g_dec
        always @(posedge clk) embed_lanes[el*ELI +: ELI] <= su_va_addr[el*AW +: ELI];
        wire [31:0] decoded;
        ot_hdc_qwen_int8_embed_decode u_decode (
            .code(code_q[8*embed_lanes[el*ELI +: ELI] +: 8]), .scale(rscale), .value(decoded), .fault(bad[el]));
        assign su_va_q[el*32 +: 32] = embed_sel[el] ? decoded : va_q[el*32 +: 32];
    end endgenerate
endmodule

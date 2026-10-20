`timescale 1ns/1ps
// Registered producer -> actual SU row SRAM face. Compiler reservations are
// checked against ACTUAL producer identity/data, never used to synthesize data
// or to reschedule a late/missing word. One additional boundary-register edge.
module qkd_embedding_static_preload_face(
    input wire ck,rst_n,
    input wire word_v,input wire [511:0] word_data,
    input wire [17:0] word_token,input wire [5:0] word_index,
    input wire word_scale,input wire [15:0] word_epoch,
    input wire expected_slot,input wire [17:0] expected_token,
    input wire [5:0] expected_word,input wire expected_scale,input wire [15:0] expected_epoch,
    input wire i_fill_begin,input wire [17:0] i_fill_token,input wire [15:0] i_fill_epoch,
    output reg fill_begin,output reg [17:0] fill_token,output reg [15:0] fill_epoch,
    output reg preload_slot,preload_v,preload_scale,
    output reg [5:0] preload_word,output reg [17:0] preload_token,
    output reg [511:0] preload_data,output reg [15:0] preload_epoch,output reg fault
);
    always @(posedge ck) begin
        fill_token<=i_fill_token;fill_epoch<=i_fill_epoch;
        preload_data<=word_data;preload_token<=word_token;
        preload_word<=word_index;preload_scale<=word_scale;preload_epoch<=word_epoch;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin fill_begin<=0;preload_slot<=0;preload_v<=0;fault<=0;end
        else begin
            fill_begin<=i_fill_begin;preload_slot<=expected_slot;preload_v<=word_v;
            if(expected_slot!=word_v) fault<=1;
            if(expected_slot&&(word_token!=expected_token||word_index!=expected_word||word_scale!=expected_scale||word_epoch!=expected_epoch)) fault<=1;
            if(i_fill_begin&&(word_v||expected_slot||i_fill_token>=151936)) fault<=1;
        end
endmodule

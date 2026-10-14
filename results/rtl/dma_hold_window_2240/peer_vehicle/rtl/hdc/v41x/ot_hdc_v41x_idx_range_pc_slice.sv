`timescale 1ns/1ps
// Physical boundary for one index-key HBM pseudo-channel. Four virtual range
// requesters share the channel. The response data bus is shared and its
// context is encoded in the reserved tag bits [TAGW-3:TAGW-4]; only the
// selected requester's valid is asserted. This avoids four copies of the
// 256-bit data bus at the local physical boundary.
module ot_hdc_v41x_idx_range_pc_slice #(
    parameter integer AW=28,LENW=4,TAGW=16,BEATW=4,DW=256,
    parameter integer QUANTUM=128
) (
    input wire clk,rst_n,
    input wire [3:0] i_req_v,
    output reg [3:0] i_req_rdy,
    input wire [4*AW-1:0] i_req_addr,
    input wire [4*LENW-1:0] i_req_len,
    input wire [4*TAGW-1:0] i_req_tag,
    output reg h_req_v,
    input wire h_req_rdy,
    output reg [AW-1:0] h_req_addr,
    output reg [LENW-1:0] h_req_len,
    output reg [TAGW-1:0] h_req_tag,
    input wire h_rsp_v,
    output wire h_rsp_rdy,
    input wire [TAGW-1:0] h_rsp_tag,
    input wire [BEATW-1:0] h_rsp_beat,
    input wire [DW-1:0] h_rsp_data,
    output wire [3:0] o_rsp_v,
    input wire [3:0] o_rsp_rdy,
    output wire [TAGW-1:0] o_rsp_tag,
    output wire [BEATW-1:0] o_rsp_beat,
    output wire [DW-1:0] o_rsp_data
);
    localparam integer BW=TAGW-4;
    reg [1:0] rr;
    reg [15:0] served;
    reg [1:0] selected;
    integer d,c;
    always @* begin
        selected=0;h_req_v=0;h_req_addr=0;h_req_len=0;h_req_tag=0;
        i_req_rdy=0;
        for(d=0;d<4;d=d+1) begin
            c=(int'(rr)+d)&3;
            if(!h_req_v && i_req_v[c]) begin
                h_req_v=1;
                selected=2'(c);
            end
        end
        if(h_req_v) begin
            h_req_addr=i_req_addr[selected*AW +: AW];
            h_req_len=i_req_len[selected*LENW +: LENW];
            h_req_tag=i_req_tag[selected*TAGW +: TAGW] |
                      (TAGW'(selected)<<BW);
            i_req_rdy[selected]=h_req_rdy;
        end
    end
    wire [1:0] rsp_ctx=h_rsp_tag[BW +: 2];
    assign o_rsp_v=h_rsp_v ? (4'b0001<<rsp_ctx) : 4'b0000;
    assign h_rsp_rdy=o_rsp_rdy[rsp_ctx];
    assign o_rsp_tag=h_rsp_tag & ~(TAGW'(3)<<BW);
    assign o_rsp_beat=h_rsp_beat;
    assign o_rsp_data=h_rsp_data;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            rr<=0;served<=0;
        end else if(h_req_v && h_req_rdy) begin
            if(QUANTUM==1 || (selected==rr && served==16'(QUANTUM-1))) begin
                rr<=selected+2'd1;
                served<=0;
            end else if(selected!=rr) begin
                rr<=selected;
                served<=16'd1;
            end else served<=served+16'd1;
        end
    end
endmodule

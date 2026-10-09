`timescale 1ns/1ps
// Reviewedstaticstage0cycle bounds observer. No SRC/DEST authentication,
// typeauthorization, expectedpositionhistory, or failclosedpacketdrop. Actual
// compiler/link staticrouting and nativeproducercredits own thosecontracts.
module ot_s81_stage_guard #(
    parameter integer FLIT = 512, NW = 21, MAXU = 16, MY_ID = 0,
    parameter integer SRC_LO = 0, SRC_HI = 0, SRC2_LO = 4095, SRC2_HI = 0,
    parameter integer GRP_LO = 4095, GRP_HI = 0,
    parameter [15:0]  TYPE_MASK = 16'h0002,
    parameter integer LEN_HID = 640, LEN_SIDE_MAX = 64, CHECK_POS = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [11:0]     cfg_users,
    input  wire            in_valid,
    output wire            in_ready,
    input  wire [FLIT-1:0] in_data,
    input  wire            in_last,
    output wire            out_valid,
    input  wire            out_ready,
    output wire [FLIT-1:0] out_data,
    output wire            out_last,
    output reg             fault,
    output reg  [3:0]      fault_code,
    output wire [127:0]    fault_hdr,
    output wire [31:0]     st_msgs,
    output wire [31:0]     st_flits
);
    reg in_msg;
    assign out_valid=in_valid;assign in_ready=out_ready;
    assign out_data=in_data;assign out_last=in_last;
    // Keep legacystatuspins but omitunusedwideheader/history storage.
    assign fault_hdr=0;assign st_msgs=0;assign st_flits=0;
    wire[11:0] user_id=in_data[51:40];wire[20:0] position=in_data[72:52];
    always @(posedge clk or negedge rst_n)begin
      if(!rst_n)begin in_msg<=0;fault<=0;fault_code<=0;end
      else if(in_valid&&in_ready)begin
        in_msg<=!in_last;
        if(!in_msg&&!fault)begin
          if(user_id>=MAXU||user_id>=cfg_users)begin fault<=1;fault_code<=6;end
          else if(position>=21'd1048576)begin fault<=1;fault_code<=7;end
        end
      end
    end
endmodule

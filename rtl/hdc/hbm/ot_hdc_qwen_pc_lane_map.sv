`timescale 1ns/1ps
// A source's lane number is a bank index within its own code/scale window;
// the physical PC is selected by the low sector-address bits. Independent
// scale bases and embedding scale rows therefore rotate source lanes across
// the 128 physical PCs. Carry the original lane in the service tag so an
// out-of-order response returns to the exact window bank that issued it.
module ot_hdc_qwen_pc_lane_map #(
    parameter integer PCS=128,
    parameter integer AW=32,
    parameter integer TAGW=17,
    parameter integer LW=$clog2(PCS),
    parameter integer MTAGW=TAGW+LW
) (
    input wire clk, rst_n,
    input wire [PCS-1:0] s_req_v,
    output reg [PCS-1:0] s_req_rdy,
    input wire [PCS-1:0] s_req_we,
    input wire [PCS*AW-1:0] s_req_addr,
    input wire [PCS*TAGW-1:0] s_req_tag,
    input wire [PCS*256-1:0] s_req_data,
    output reg [PCS-1:0] p_req_v,
    input wire [PCS-1:0] p_req_rdy,
    output reg [PCS-1:0] p_req_we,
    output reg [PCS*AW-1:0] p_req_addr,
    output reg [PCS*MTAGW-1:0] p_req_tag,
    output reg [PCS*256-1:0] p_req_data,
    input wire [PCS-1:0] p_rsp_v,
    output reg [PCS-1:0] p_rsp_rdy,
    input wire [PCS*MTAGW-1:0] p_rsp_tag,
    input wire [PCS*256-1:0] p_rsp_data,
    output reg [PCS-1:0] s_rsp_v,
    input wire [PCS-1:0] s_rsp_rdy,
    output reg [PCS*TAGW-1:0] s_rsp_tag,
    output reg [PCS*256-1:0] s_rsp_data,
    input wire [PCS-1:0] p_wr_done_v,
    input wire [PCS*MTAGW-1:0] p_wr_done_tag,
    output reg [PCS-1:0] s_wr_done_v,
    output reg [PCS*TAGW-1:0] s_wr_done_tag,
    output reg fault
);
    initial if (PCS!=128 || AW<32 || LW!=7) $fatal(1,"Qwen PC lane map geometry");
    integer phys, lane;
    reg req_collision, rsp_collision, wr_collision;
    always @(*) begin
        phys=0; lane=0;
        s_req_rdy=0;
        p_req_v=0; p_req_we=0; p_req_addr=0; p_req_tag=0; p_req_data=0;
        req_collision=0;
        for (integer s=0;s<PCS;s=s+1) if (s_req_v[s]) begin
            phys=s_req_addr[s*AW +: LW];
            if (p_req_v[phys]) req_collision=1;
            else begin
                p_req_v[phys]=1;
                p_req_we[phys]=s_req_we[s];
                p_req_addr[phys*AW +: AW]=s_req_addr[s*AW +: AW];
                p_req_tag[phys*MTAGW +: MTAGW]={LW'(s),s_req_tag[s*TAGW +: TAGW]};
                p_req_data[phys*256 +: 256]=s_req_data[s*256 +: 256];
                s_req_rdy[s]=p_req_rdy[phys];
            end
        end
        p_rsp_rdy=0; s_rsp_v=0; s_rsp_tag=0; s_rsp_data=0;
        rsp_collision=0;
        for (integer p=0;p<PCS;p=p+1) if (p_rsp_v[p]) begin
            lane=p_rsp_tag[p*MTAGW+TAGW +: LW];
            if (s_rsp_v[lane]) rsp_collision=1;
            else begin
                s_rsp_v[lane]=1;
                s_rsp_tag[lane*TAGW +: TAGW]=p_rsp_tag[p*MTAGW +: TAGW];
                s_rsp_data[lane*256 +: 256]=p_rsp_data[p*256 +: 256];
                p_rsp_rdy[p]=s_rsp_rdy[lane];
            end
        end
        s_wr_done_v=0; s_wr_done_tag=0; wr_collision=0;
        for (integer p=0;p<PCS;p=p+1) if (p_wr_done_v[p]) begin
            lane=p_wr_done_tag[p*MTAGW+TAGW +: LW];
            if (s_wr_done_v[lane]) wr_collision=1;
            else begin
                s_wr_done_v[lane]=1;
                s_wr_done_tag[lane*TAGW +: TAGW]=p_wr_done_tag[p*MTAGW +: TAGW];
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault<=0;
        else if (req_collision || rsp_collision || wr_collision) fault<=1;
    end
endmodule

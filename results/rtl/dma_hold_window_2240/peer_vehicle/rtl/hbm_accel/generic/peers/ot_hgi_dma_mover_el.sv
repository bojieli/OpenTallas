`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_dma_mover_el (hbm-fq/dma 2026-10-11, textbook audit): the mover's ROUTED ELEMENT = ot_hgi_dma_mover as the die
// runs it with the KV write-back engine split out (KVW 1, SVR2 0): the sector engine reads VM sources through the packet
// client, the VM DMA wide read group (vr2q / vr2r, 8,770 b) and its 32-lane capture belong to the hardened KV engine
// element ot_hgi_dma_kvw.  This wrapper is ot_hgi_dma_mover VR2 0 / KVW 0 without the read-group ports, so the element's
// outline is sized by its real interface (~4.7k IO pins, not 13.0k).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_mover_el #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          mv_v,
    output wire          mv_rdy,
    input  wire [226:0]  mv,
    output wire          mv_done,
    output wire          mv_fault,
    output wire          mv_src,
    input  wire          fence_v,
    output wire          fence_rdy,
    output wire          fence_done,
    output wire          k_req_v,
    input  wire          k_req_rdy,
    output wire          k_req_we,
    output wire [36:0]   k_req_addr,
    output wire [255:0]  k_req_wdata,
    output wire [31:0]   k_req_wstrb,
    output wire [15:0]   k_req_tag,
    input  wire          k_rsp_v,
    output wire          k_rsp_rdy,
    input  wire          k_rsp_we,
    input  wire [255:0]  k_rsp_data,
    input  wire          k_fault,
    output wire [3:0]    r_req_v,
    input  wire [3:0]    r_req_rdy,
    output wire [4*37-1:0] r_req_addr,
    output wire [4*4-1:0] r_req_len,
    output wire [4*16-1:0] r_req_tag,
    output wire [3:0]    r_req_we,
    output wire [4*256-1:0] r_req_wdata,
    output wire [4*32-1:0] r_req_wstrb,
    input  wire [3:0]    r_rsp_v,
    input  wire [3:0]    r_rsp_we,
    output wire [3:0]    r_rsp_rdy,
    input  wire [4*16-1:0] r_rsp_tag,
    input  wire [3:0]    r_rsp_last,
    input  wire [4*256-1:0] r_rsp_data,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    output wire [279:0]  wl,
    input  wire          wl_done
);
    wire [512:0] vr2q_nc;
    ot_hgi_dma_mover #(.MUT(MUT), .VR2(0), .KVW(0)) u_mv (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv),
        .mv_done(mv_done), .mv_fault(mv_fault), .mv_src(mv_src), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_req_addr), .k_req_wdata(k_req_wdata),
        .k_req_wstrb(k_req_wstrb), .k_req_tag(k_req_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data), .k_fault(k_fault),
        .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag),
        .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we),
        .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data),
        .vr2q(vr2q_nc), .vr2r(8257'd0), .vmq(vmq), .vmr(vmr), .wl(wl), .wl_done(wl_done));
    wire unused_ok = &{1'b0, vr2q_nc};
endmodule
`default_nettype wire

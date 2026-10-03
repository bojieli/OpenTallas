`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Composition glue of the GPU-organised HBM comparator system top:
//   ot_gpu_memsys_adapter  one die's memory system (ot_gpu_memsys) with its
//                          load-time HBM image named after the die
//                          ("die<d>_p<slice>.hex", tools/gpu_sys/mem_image.py)
//   ot_gpu_coll_system     R per-die collective endpoints (ot_gpu_coll_endpoint)
//                          and the NVLS-style switch fabric (ot_gpu_coll_fabric)
// ENABLE = 0: inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_memsys_adapter #(
    parameter integer ENABLE    = 0,
    parameter integer NC        = 4,
    parameter integer NS        = 2,
    parameter integer NPC       = 2,
    parameter integer MEM_WORDS = 65536,
    parameter integer DIE       = 0,
    parameter integer USE_W2    = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC-1:0]     c_req_v,
    output wire [NC-1:0]     c_req_rdy,
    input  wire [NC-1:0]     c_req_we,
    input  wire [NC*32-1:0]  c_req_addr,
    input  wire [NC*256-1:0] c_req_wdata,
    input  wire [NC*32-1:0]  c_req_wstrb,
    input  wire [NC*16-1:0]  c_req_tag,
    output wire [NC-1:0]     c_rsp_v,
    input  wire [NC-1:0]     c_rsp_rdy,
    output wire [NC*16-1:0]  c_rsp_tag,
    output wire [NC-1:0]     c_rsp_we,
    output wire [NC*256-1:0] c_rsp_data,
    output wire              fault
);
    localparam string PFX = (DIE == 0) ? "die0" : (DIE == 1) ? "die1" : (DIE == 2) ? "die2" : "die3";
    ot_gpu_memsys #(.ENABLE(ENABLE), .NC(NC), .NS(NS), .NPC(NPC), .MEM_WORDS(MEM_WORDS), .CLK_PS(1000),
                    .USE_W2(USE_W2), .IMAGE_PREFIX(PFX)) u_ms (
        .clk(clk), .rst_n(rst_n), .req_v(c_req_v), .req_rdy(c_req_rdy), .req_we(c_req_we), .req_addr(c_req_addr),
        .req_wdata(c_req_wdata), .req_wstrb(c_req_wstrb), .req_tag(c_req_tag), .rsp_v(c_rsp_v), .rsp_rdy(c_rsp_rdy),
        .rsp_tag(c_rsp_tag), .rsp_we(c_rsp_we), .rsp_data(c_rsp_data), .fault(fault));
endmodule

module ot_gpu_coll_system #(
    parameter integer ENABLE  = 0,
    parameter integer R       = 2,
    parameter integer NL      = 128,
    parameter integer SW_PIPE = 8
) (
    input  wire              clk_sm,
    input  wire              rst_sm_n,
    input  wire              clk_link,
    input  wire              rst_link_n,
    input  wire [R-1:0]      req_v,
    output wire [R-1:0]      req_rdy,
    input  wire [R-1:0]      mode,
    input  wire [R*8-1:0]    count,
    input  wire [R*NL*32-1:0] data,
    output wire [R-1:0]      rsp_v,
    input  wire [R-1:0]      rsp_rdy,
    output wire [R*NL*32-1:0] rsp_data,
    output wire              fault
);
    localparam integer PW = 32 * 16 + 2 + 32;
    wire [R-1:0] up_v, dn_v, ep_f;
    wire [R*PW-1:0] up_rec, dn_rec;
    wire fab_f;
    genvar r;
    for (r = 0; r < R; r = r + 1) begin : g_r
        ot_gpu_coll_endpoint #(.ENABLE(ENABLE), .NL(NL), .R(R), .RANK(r)) u_ep (
            .clk_sm(clk_sm), .rst_sm_n(rst_sm_n), .coll_req_v(req_v[r]), .coll_req_rdy(req_rdy[r]),
            .coll_mode(mode[r]), .coll_count(count[r*8 +: 8]), .coll_data(data[r*NL*32 +: NL*32]),
            .coll_rsp_v(rsp_v[r]), .coll_rsp_rdy(rsp_rdy[r]), .coll_rsp_data(rsp_data[r*NL*32 +: NL*32]),
            .coll_fault(ep_f[r]), .clk_link(clk_link), .rst_link_n(rst_link_n),
            .lk_tx_v(up_v[r]), .lk_tx_rec(up_rec[r*PW +: PW]), .lk_rx_v(dn_v[r]), .lk_rx_rec(dn_rec[r*PW +: PW]));
    end
    ot_gpu_coll_fabric #(.ENABLE(ENABLE), .R(R), .NL(NL), .SW_PIPE(SW_PIPE)) u_fab (
        .clk_link(clk_link), .rst_link_n(rst_link_n), .up_v(up_v), .up_rec(up_rec), .dn_v(dn_v), .dn_rec(dn_rec),
        .fault(fab_f));
    assign fault = (|ep_f) | fab_f;
endmodule

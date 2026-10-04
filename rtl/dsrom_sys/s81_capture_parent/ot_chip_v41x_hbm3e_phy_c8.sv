`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM3E stack interface of the adopted V4.1 layer die: PHY + controller + stack,
// BEHAVIOURAL STAND-IN (simulation models, not physical RTL; the physical
// block is the ot_hbm3e_phy abstract of physical/asap7_memory_macros).
//
// One stack, two host ports, each with the request / response protocol of the
// timing model the adopted gates were measured on:
//
//   K port  32 pseudo-channels, one valid/ready request port per pseudo-
//           channel (reads of req_len sectors, one-sector masked writes with a
//           wr_done), per-channel response ports -- ot_hdc_v41x_idx_hbm
//           (REFPB = 3 refresh-aware per-bank refresh, 64-beat queues).  Carries
//           the pooled indexer's key reads and timed key-image writes (and is
//           the port a KV streamer would use).
//   W port  (W_PORT = 1) the QE weight region: one request channel, NPC_W
//           per-channel response ports and per-channel room -- ot_hdc_hbm_model
//           (PC_RDY = 1, PC_ROOM = 16), the model of the W_HBM gates.
//
// The two ports are separate channel groups of the stack model: their DRAM
// timing is modelled per group, the bandwidth interference between them is NOT
// modelled (the adopted gates put them on separate model instances too).
// Capacity: K_MEM sectors on the K port; a request past it raises k_oor (the
// model itself would wrap the address).
// Contents: MEM_WORDS 32-byte sectors per group; the bench loads them through
// the hierarchy (u_k.mem, g_w.u_w.mem), as the gates do.
// ---------------------------------------------------------------------------
module ot_chip_v41x_hbm3e_phy_c8 #(
    parameter integer NPC       = 32,
    parameter integer K_AW      = 28,          // full-shape packed regions need 30
    parameter integer K_MEM     = 1 << 18,     // K port sectors
    parameter integer W_PORT    = 0,
    parameter integer W_AW      = 24,          // full-shape weight-sector address is 30 bits
    parameter integer NPC_W     = 8,
    parameter integer W_MEM     = 1 << 20,     // W port sectors
    parameter integer LWIN      = 10,          // W port tag bits
    parameter integer KTAGW     = 16,          // K port tag bits
    parameter integer CLK_PS    = 1000
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // K port
    input  wire [NPC-1:0]       k_v,
    output wire [NPC-1:0]       k_rdy,
    input  wire [NPC*K_AW-1:0]  k_addr,
    input  wire [NPC*4-1:0]     k_len,
    input  wire [NPC*KTAGW-1:0] k_tag,
    input  wire [NPC-1:0]       k_we,
    input  wire [NPC*256-1:0]   k_wdata,
    input  wire [NPC*32-1:0]    k_wstrb,
    output wire [NPC-1:0]       k_wr_done,
    output wire [NPC-1:0]       kr_v,
    input  wire [NPC-1:0]       kr_rdy,
    output wire [NPC*KTAGW-1:0] kr_tag,
    output wire [NPC*4-1:0]     kr_beat,
    output wire [NPC*256-1:0]   kr_data,
    // W port
    input  wire                 w_v,
    output wire                 w_rdy,
    input  wire [W_AW-1:0]      w_addr,
    input  wire [5:0]           w_len,
    input  wire [LWIN-1:0]      w_tag,
    output wire [NPC_W-1:0]     w_room,
    output wire [NPC_W-1:0]     wr_v,
    input  wire [NPC_W-1:0]     wr_rdy,
    output wire [NPC_W*LWIN-1:0] wr_tag,
    output wire [NPC_W*5-1:0]   wr_beat,
    output wire [NPC_W*256-1:0] wr_data,
    // status
    output reg                  k_oor,         // sticky: a K request reached past K_MEM (the model would wrap)
    output wire                 w_oor,         // sticky: invalid W request blocked before model modulo
    output wire [63:0]          refreshes,     // K port refresh events
    output wire [31:0]          w_reads,       // W port sector reads
    output wire [NPC*K_AW-1:0] k_wr_done_addr,
    output wire [NPC*KTAGW-1:0] k_wr_done_tag
);
    ot_hdc_v41x_idx_hbm_c8 #(.NPC(NPC), .AW(K_AW), .DW(256), .MEM_WORDS(K_MEM), .TAGW(KTAGW), .LENW(4), .BEATW(4),
                          .QD(64), .REFPB(3), .MEM_MODE(0)) u_k (
        .clk(clk), .rst_n(rst_n), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_addr), .req_len(k_len),
        .req_tag(k_tag), .req_we(k_we), .req_wdata(k_wdata), .req_wstrb(k_wstrb), .wr_done(k_wr_done),.wr_done_addr(k_wr_done_addr),.wr_done_tag(k_wr_done_tag),
        .rsp_v(kr_v), .rsp_rdy(kr_rdy), .rsp_tag(kr_tag), .rsp_beat(kr_beat), .rsp_data(kr_data));
    // capacity check: the model addresses its array modulo K_MEM; a request past it must fault, never wrap
    integer c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) k_oor <= 1'b0;
        else for (c = 0; c < NPC; c = c + 1)
            if (k_v[c] && k_rdy[c] && (64'(k_addr[c*K_AW +: K_AW]) + 64'(k_len[c*4 +: 4]) > 64'(K_MEM))) begin
                k_oor <= 1'b1;
`ifndef SYNTHESIS
                $error("ot_chip_v41x_hbm3e_phy: K request sector %0d + %0d past the stack's %0d sectors",
                       k_addr[c*K_AW +: K_AW], k_len[c*4 +: 4], K_MEM);
`endif
            end
    reg [63:0] ref_n;
    integer p;
    always @(*) begin
        ref_n = 64'd0;
        for (p = 0; p < NPC; p = p + 1) ref_n = ref_n + 64'(u_k.st_ref[p]);
    end
    assign refreshes = ref_n;

    generate if (W_PORT) begin : g_w
        wire model_ready;
        wire range_ok = (w_len != 0) &&
            ((64'(w_addr) + 64'(w_len)) <= 64'(W_MEM));
        assign w_rdy = model_ready && range_ok;
        reg w_oor_r;
        assign w_oor = w_oor_r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) w_oor_r <= 1'b0;
            else if (w_v && !range_ok) w_oor_r <= 1'b1;
        ot_hdc_hbm_model #(.NPC(NPC_W), .AW(W_AW), .DW(256), .MEM_WORDS(W_MEM), .TAGW(LWIN), .LENW(6), .BEATW(5),
                           .CLK_PS(CLK_PS), .PC_RDY(1), .PC_ROOM(16)) u_w (
            .clk(clk), .rst_n(rst_n), .req_v(w_v && range_ok), .req_rdy(model_ready), .pc_room(w_room), .req_we(1'b0),
            .req_addr(w_addr), .req_len(w_len), .req_tag(w_tag), .req_wdata(256'd0),
            .rsp_v(wr_v), .rsp_rdy(wr_rdy), .rsp_tag(wr_tag), .rsp_beat(wr_beat), .rsp_data(wr_data));
        reg [31:0] rd_n;
        integer r;
        always @(*) begin
            rd_n = 32'd0;
            for (r = 0; r < NPC_W; r = r + 1) rd_n = rd_n + 32'(u_w.st_rd[r]);
        end
        assign w_reads = rd_n;
    end else begin : g_nw
        assign w_oor = 1'b0;
        assign w_rdy = 1'b0; assign w_room = {NPC_W{1'b0}}; assign wr_v = {NPC_W{1'b0}};
        assign wr_tag = {NPC_W*LWIN{1'b0}}; assign wr_beat = {NPC_W*5{1'b0}}; assign wr_data = {NPC_W*256{1'b0}};
        assign w_reads = 32'd0;
    end endgenerate
endmodule

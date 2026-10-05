`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_memsys: the per-die memory system of the GPU-organised HBM
// comparator (clk_mem): NC MREQ clients -> ot_gpu_xbar -> NS address-
// interleaved L2 slices (ot_gpu_l2_slice, 128-byte interleave on byte-address
// bits [7 +: log2(NS)]) -> one shoreline HBM partition per slice
// (ot_gpu_hbm_partition around ot_hdc_hbm_model, NPC pseudo-channels and
// MEM_WORDS 32-byte words each).
//
// Client ports are packed: client c's field occupies [c*W +: W].
// Die-global byte address X -> slice X[7 +: LNS]; partition-local byte
// address {X[31:7+LNS], X[6:0]}; sector = local >> 5; model word =
// sector % MEM_WORDS of g_on.g_s[slice].u_part.g_on.u_model.mem; byte lane
// X[4:0] = bits [8*lane +: 8] (tools/gpu_sys/mem_image.py).
// Image loading: "<prefix>_p<slice>.hex" per partition (DIE_IDX < 0) or
// "<prefix>_d<DIE_IDX>_p<slice>.hex" (DIE_IDX >= 0, several dies under one
// plusarg), <prefix> from the plusarg +gpu_sys_mem_prefix=<prefix> or else
// IMAGE_PREFIX (empty and no plusarg: zero-filled).
// ENABLE = 0 (default): inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_memsys #(
    parameter integer ENABLE    = 0,
    parameter integer NC        = 4,
    parameter integer NS        = 2,
    parameter integer NPC       = 2,
    parameter integer MEM_WORDS = 16384,
    parameter integer CLK_PS    = 1000,
    parameter integer L2_BYTES  = 32768,
    parameter integer OSD       = 64,
    parameter integer USE_W2    = 0,
    parameter integer DIE_IDX   = -1,
    parameter         IMAGE_PREFIX = ""
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC-1:0]     req_v,
    output wire [NC-1:0]     req_rdy,
    input  wire [NC-1:0]     req_we,
    input  wire [NC*32-1:0]  req_addr,
    input  wire [NC*256-1:0] req_wdata,
    input  wire [NC*32-1:0]  req_wstrb,
    input  wire [NC*16-1:0]  req_tag,
    output wire [NC-1:0]     rsp_v,
    input  wire [NC-1:0]     rsp_rdy,
    output wire [NC*16-1:0]  rsp_tag,
    output wire [NC-1:0]     rsp_we,
    output wire [NC*256-1:0] rsp_data,
    output wire              fault
);
    generate if (ENABLE != 0) begin : g_on
        localparam integer LNC  = (NC > 1) ? $clog2(NC) : 1;
        localparam integer STW  = 16 + LNC;
        localparam integer LOSD = (OSD > 1) ? $clog2(OSD) : 1;

        wire [NS-1:0]     s_req_v, s_req_rdy, s_req_we, s_rsp_v, s_rsp_rdy, s_rsp_we;
        wire [NS*32-1:0]  s_req_addr, s_req_wstrb;
        wire [NS*256-1:0] s_req_wdata, s_rsp_data;
        wire [NS*STW-1:0] s_req_tag, s_rsp_tag;
        wire [NS-1:0]     s_fault, p_fault;

        ot_gpu_xbar #(.ENABLE(1), .NC(NC), .NS(NS), .TW(16)) u_xbar (
            .clk(clk), .rst_n(rst_n),
            .c_req_v(req_v), .c_req_rdy(req_rdy), .c_req_we(req_we), .c_req_addr(req_addr),
            .c_req_wdata(req_wdata), .c_req_wstrb(req_wstrb), .c_req_tag(req_tag),
            .c_rsp_v(rsp_v), .c_rsp_rdy(rsp_rdy), .c_rsp_tag(rsp_tag), .c_rsp_we(rsp_we), .c_rsp_data(rsp_data),
            .s_req_v(s_req_v), .s_req_rdy(s_req_rdy), .s_req_we(s_req_we), .s_req_addr(s_req_addr),
            .s_req_wdata(s_req_wdata), .s_req_wstrb(s_req_wstrb), .s_req_tag(s_req_tag),
            .s_rsp_v(s_rsp_v), .s_rsp_rdy(s_rsp_rdy), .s_rsp_tag(s_rsp_tag), .s_rsp_we(s_rsp_we),
            .s_rsp_data(s_rsp_data));

        genvar s;
        for (s = 0; s < NS; s = s + 1) begin : g_s
            wire            d_req_v, d_req_rdy, d_req_we, d_rsp_v, d_rsp_rdy, d_rsp_we;
            wire [31:0]     d_req_addr, d_req_wstrb;
            wire [255:0]    d_req_wdata, d_rsp_data;
            wire [LOSD-1:0] d_req_tag, d_rsp_tag;
            /* verilator lint_off UNUSEDSIGNAL */   // statistics, read hierarchically by benches
            wire [31:0]     st_rd_hit, st_rd_miss, st_wr_hit, st_wr_miss;
            /* verilator lint_on UNUSEDSIGNAL */
            ot_gpu_l2_slice #(.ENABLE(1), .NS(NS), .TW(STW), .L2_BYTES(L2_BYTES), .OSD(OSD)) u_l2 (
                .clk(clk), .rst_n(rst_n),
                .req_v(s_req_v[s]), .req_rdy(s_req_rdy[s]), .req_we(s_req_we[s]), .req_addr(s_req_addr[s*32 +: 32]),
                .req_wdata(s_req_wdata[s*256 +: 256]), .req_wstrb(s_req_wstrb[s*32 +: 32]),
                .req_tag(s_req_tag[s*STW +: STW]),
                .rsp_v(s_rsp_v[s]), .rsp_rdy(s_rsp_rdy[s]), .rsp_tag(s_rsp_tag[s*STW +: STW]), .rsp_we(s_rsp_we[s]),
                .rsp_data(s_rsp_data[s*256 +: 256]),
                .d_req_v(d_req_v), .d_req_rdy(d_req_rdy), .d_req_we(d_req_we), .d_req_addr(d_req_addr),
                .d_req_wdata(d_req_wdata), .d_req_wstrb(d_req_wstrb), .d_req_tag(d_req_tag),
                .d_rsp_v(d_rsp_v), .d_rsp_rdy(d_rsp_rdy), .d_rsp_tag(d_rsp_tag), .d_rsp_we(d_rsp_we),
                .d_rsp_data(d_rsp_data),
                .stat_rd_hit(st_rd_hit), .stat_rd_miss(st_rd_miss), .stat_wr_hit(st_wr_hit), .stat_wr_miss(st_wr_miss),
                .fault(s_fault[s]));
            ot_gpu_hbm_partition #(.ENABLE(1), .NS(NS), .TW(LOSD), .NPC(NPC), .MEM_WORDS(MEM_WORDS),
                                   .CLK_PS(CLK_PS), .USE_W2(USE_W2), .PART_IDX(s), .DIE_IDX(DIE_IDX),
                                   .IMAGE_PREFIX(IMAGE_PREFIX)) u_part (
                .clk(clk), .rst_n(rst_n),
                .req_v(d_req_v), .req_rdy(d_req_rdy), .req_we(d_req_we), .req_addr(d_req_addr),
                .req_wdata(d_req_wdata), .req_wstrb(d_req_wstrb), .req_tag(d_req_tag),
                .rsp_v(d_rsp_v), .rsp_rdy(d_rsp_rdy), .rsp_tag(d_rsp_tag), .rsp_we(d_rsp_we), .rsp_data(d_rsp_data),
                .fault(p_fault[s]));
        end
        assign fault = |{s_fault, p_fault};
    end else begin : g_off
        assign req_rdy = '0;
        assign rsp_v = '0;
        assign rsp_tag = '0;
        assign rsp_we = '0;
        assign rsp_data = '0;
        assign fault = 1'b0;
    end endgenerate
endmodule

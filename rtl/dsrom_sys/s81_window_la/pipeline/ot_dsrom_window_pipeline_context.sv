`timescale 1ns/1ps
// Full-shape source/WMUX interface projection from the actual retained S81
// WINDOW binding. No scan-folded ports, behavioral SRAM credit or IO exceptions.
// clk is the actual shared streaming root; parent CTS/arrival/load qualification
// is a separate required source-bound input, never inferred from this top.
module ot_dsrom_window_pipeline_context #(
    parameter integer NPC=32, AW=30, TAGW=16, STAGW=17, LENW=4, BEATW=4, DW=256, WTAGW=13,
    parameter integer SEC_W=30, HAW=30, POS_W=21, USER_W=10, SPLIT_COLUMNS=0, STAGE_MARGIN=0
) (
    input wire clk, rst_n,
    input wire retain_qk, retain_pv, retain_complete, retain_invalidate,
    input wire [15:0] retain_generation,
    input wire [SEC_W-1:0] region_base_sector, region_sector_count,
    input wire prime_v,
    output wire prime_ready,
    input wire [USER_W-1:0] prime_user,
    input wire [POS_W-1:0] prime_row,
    input wire blk_v,
    output wire blk_ready,
    input wire [USER_W-1:0] blk_user,
    input wire [POS_W-1:0] blk_row,
    input wire [3:0] blk_idx,
    input wire [255:0] blk_codes,
    input wire [7:0] blk_scale,
    input wire start_v,
    output wire start_ready,
    input wire [USER_W-1:0] start_user,
    input wire [POS_W-1:0] start_first,
    input wire [7:0] start_count,
    output wire staged_v,
    input wire stream_go,
    output wire busy, done, fault,
    output wire [4:0] fault_code,
    output wire [31:0] refill_cycles, sectors_read,
    output wire [31:0] rows_fetched, blocks_written, sectors_written,
    output wire [7:0] rows_refilled,
    output wire kv_v,
    input wire kv_ready,
    output wire [3:0] kv_m,
    output wire [4*16*265-1:0] kv_w,
    output wire [3:0] m_v,
    input wire [3:0] m_rdy,
    output wire [4*HAW-1:0] m_addr,
    output wire [15:0] m_len,
    output wire [4*TAGW-1:0] m_tag,
    output wire [3:0] m_we,
    output wire [1023:0] m_wdata,
    output wire [127:0] m_wstrb,
    input wire [3:0] m_wr_done,
    input wire [3:0] s_v,
    output wire [3:0] s_rdy,
    input wire [4*TAGW-1:0] s_tag,
    input wire [15:0] s_beat,
    input wire [1023:0] s_data,
    input wire [NPC-1:0] a_v, a_rsp_rdy, g_v, g_rsp_rdy, h_rdy, h_wr_done, r_v,
    input wire [NPC*AW-1:0] a_addr, g_addr,
    input wire [NPC*LENW-1:0] a_len, g_len,
    input wire [NPC*STAGW-1:0] a_tag, r_tag,
    input wire [NPC*WTAGW-1:0] g_tag,
    input wire [NPC-1:0] a_we,
    input wire [NPC*DW-1:0] a_wdata, r_data,
    input wire [NPC*DW/8-1:0] a_wstrb,
    input wire [NPC*BEATW-1:0] r_beat,
    output wire [NPC-1:0] a_rdy, a_wr_done, a_rsp_v, g_rdy, g_rsp_v, h_v, h_we, r_rdy,
    output wire [NPC*STAGW-1:0] a_rsp_tag, h_tag,
    output wire [NPC*BEATW-1:0] a_rsp_beat, g_rsp_beat,
    output wire [NPC*DW-1:0] a_rsp_data, g_rsp_data, h_wdata,
    output wire [NPC*WTAGW-1:0] g_rsp_tag,
    output wire [NPC*AW-1:0] h_addr,
    output wire [NPC*LENW-1:0] h_len,
    output wire [NPC*DW/8-1:0] h_wstrb,
    output wire [31:0] la_load_cycles, wg, ah,
    output wire wm_fault
);
    // source <-> wmux client 0
    wire [NPC-1:0] wl_req_v, wl_req_rdy, wl_rsp_v, wl_rsp_rdy;
    wire [NPC*AW-1:0] wl_req_addr; wire [NPC*LENW-1:0] wl_req_len; wire [NPC*WTAGW-1:0] wl_req_tag, wl_rsp_tag;
    wire [NPC*BEATW-1:0] wl_rsp_beat; wire [NPC*DW-1:0] wl_rsp_data;
    ot_dsrom_window_attn_source_la #(.SPLIT_COLUMNS(SPLIT_COLUMNS), .STAGE_MARGIN(STAGE_MARGIN), .STREAM_LA(1), .WINDOW_PIPELINE(1), .LA_ISSUE_PC(1), .REFILL_OWNER_SAFE(1), .POS_W(21), .USER_W(10), .SEC_W(AW),
        .HAW(AW), .TAGW(TAGW), .WIN_STACK(0), .STREAM_II1(0), .REFILL_CREDITS(8)) u_src (
        .clk(clk), .rst_n(rst_n),
        .retain_qk(1'b0), .retain_pv(1'b0), .retain_complete(1'b0), .retain_invalidate(1'b0),
        .retain_generation(16'd0),
        .region_base_sector(region_base_sector), .region_sector_count(region_sector_count),
        .prime_v(prime_v), .prime_ready(prime_ready), .prime_user(prime_user),
        .prime_row(prime_row),
        .blk_v(blk_v), .blk_ready(blk_ready), .blk_user(blk_user), .blk_row(blk_row),
        .blk_idx(blk_idx), .blk_codes(blk_codes), .blk_scale(blk_scale),
        .start_v(start_v), .start_ready(start_ready), .start_user(start_user),
        .start_first(start_first), .start_count(start_count), .staged_v(staged_v),
        .stream_go(stream_go), .busy(busy), .done(done), .fault(fault), .fault_code(fault_code),
        .refill_cycles(refill_cycles), .sectors_read(sectors_read), .rows_fetched(rows_fetched),
        .blocks_written(blocks_written), .sectors_written(sectors_written), .rows_refilled(rows_refilled),
        .kv_v(kv_v), .kv_ready(kv_ready), .kv_m(kv_m), .kv_w(kv_w),
        .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag), .m_we(m_we),
        .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wr_done(m_wr_done),
        .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag), .s_beat(s_beat),
        .s_data(s_data),
        .wl_req_v(wl_req_v), .wl_req_rdy(wl_req_rdy), .wl_req_addr(wl_req_addr), .wl_req_len(wl_req_len),
        .wl_req_tag(wl_req_tag), .wl_rsp_v(wl_rsp_v), .wl_rsp_rdy(wl_rsp_rdy), .wl_rsp_tag(wl_rsp_tag),
        .wl_rsp_beat(wl_rsp_beat), .wl_rsp_data(wl_rsp_data), .la_load_cycles(la_load_cycles));
    wire [2*NPC-1:0] c_rdy, c_rv; wire [2*NPC*WTAGW-1:0] c_rtag; wire [2*NPC*BEATW-1:0] c_rbeat;
    wire [2*NPC*DW-1:0] c_rdata;
    wire [NPC-1:0] a_wd, a_rv;
    wire [NPC*STAGW-1:0] a_rtag;
    wire [NPC*BEATW-1:0] a_rbeat;
    wire [NPC*DW-1:0] a_rdata;
    ot_dsrom_hbm_wmux #(.ENABLE(1), .NPC(NPC), .AW(AW), .TAGW(STAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
        .NW(2), .CW(1), .WTAGW(WTAGW)) u_wmux (
        .clk(clk), .rst_n(rst_n),
        .a_v(a_v), .a_rdy(a_rdy), .a_addr(a_addr), .a_len(a_len),
        .a_tag(a_tag), .a_we(a_we), .a_wdata(a_wdata),
        .a_wstrb(a_wstrb), .a_wr_done(a_wd), .a_rsp_v(a_rv), .a_rsp_rdy(a_rsp_rdy),
        .a_rsp_tag(a_rtag), .a_rsp_beat(a_rbeat), .a_rsp_data(a_rdata),
        .w_v({g_v, wl_req_v}), .w_rdy(c_rdy), .w_addr({g_addr, wl_req_addr}),
        .w_len({g_len, wl_req_len}), .w_tag({g_tag, wl_req_tag}),
        .w_rsp_v(c_rv), .w_rsp_rdy({g_rsp_rdy, wl_rsp_rdy}), .w_rsp_tag(c_rtag), .w_rsp_beat(c_rbeat),
        .w_rsp_data(c_rdata),
        .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
        .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),
        .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat),
        .r_data(r_data), .fault(wm_fault), .w_grants(wg), .a_held(ah));
    assign wl_req_rdy = c_rdy[0 +: NPC];
    assign wl_rsp_v = c_rv[0 +: NPC]; assign wl_rsp_tag = c_rtag[0 +: NPC*WTAGW];
    assign wl_rsp_beat = c_rbeat[0 +: NPC*BEATW]; assign wl_rsp_data = c_rdata[0 +: NPC*DW];
    assign a_wr_done=a_wd; assign a_rsp_v=a_rv; assign a_rsp_tag=a_rtag;
    assign a_rsp_beat=a_rbeat; assign a_rsp_data=a_rdata;
    assign g_rdy=c_rdy[NPC +: NPC]; assign g_rsp_v=c_rv[NPC +: NPC];
    assign g_rsp_tag=c_rtag[NPC*WTAGW +: NPC*WTAGW];
    assign g_rsp_beat=c_rbeat[NPC*BEATW +: NPC*BEATW];
    assign g_rsp_data=c_rdata[NPC*DW +: NPC*DW];
endmodule

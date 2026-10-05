`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Pre-layout SS/FF screen context of the S81 window-load binding (claude/dsrom-s81-window-bind-20261004):
// ot_dsrom_window_attn_source_la (STREAM_LA = 1: the as-built packed-row writer and attention row merge, plus
// the bound ot_dsrom_window_stream_la, ot_dsrom_window_la_stage, tag mirror and job control) and the WIN_STACK
// stack's ot_dsrom_hbm_wmux (ENABLE = 1, two clients: the window, the candidate gather), joined exactly as the
// patched S81 die joins them.  Every port of the pair is registered at this boundary (one flop per bit: the
// karb stack side, the stack, the gather client, the source's control and attention ports), so the screen
// times flop -> logic -> flop through the stack's ready and response wires as well as inside the units; the
// screen tool false-paths the top's own I/O.  Area/power are not claimed from this context.
// ---------------------------------------------------------------------------
module ot_dsrom_s81_wl_screen #(
    parameter integer NPC = 32, AW = 30, TAGW = 16, STAGW = 17, LENW = 4, BEATW = 4, DW = 256, WTAGW = 13
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [255:0] din,          // control + data sources, folded into the registered inputs
    output reg  [255:0] dout
);
    // ---------- registered inputs (a shift chain from din feeds every input flop) ----------
    localparam integer NIN = 2 + 30 + 30 + 1 + 10 + 21 + 1 + 10 + 21 + 4 + 256 + 8 + 1 + 10 + 21 + 8 + 1 + 1
                           + 4 + 4 + 4 + 64 + 16 + 1024                               // K port (4 stacks)
                           + NPC + NPC*AW + NPC*LENW + NPC*STAGW + NPC + NPC*DW + NPC*DW/8   // karb stack side
                           + NPC                                                      // karb rsp_rdy
                           + NPC + NPC*AW + NPC*LENW + NPC*WTAGW + NPC                 // gather client
                           + NPC + NPC + NPC + NPC + NPC*STAGW + NPC*BEATW + NPC*DW;   // stack
    reg [NIN-1:0] ir;
    always @(posedge clk) ir <= {ir[NIN-257:0], din};
    localparam integer o_rv = 0, o_rbase = 2, o_rcount = 32, o_prime_v = 62, o_prime_user = 63, o_prime_row = 73,
        o_blk_v = 94, o_blk_user = 95, o_blk_row = 105, o_blk_idx = 126, o_blk_codes = 130, o_blk_scale = 386,
        o_start_v = 394, o_start_user = 395, o_start_first = 405, o_start_count = 426, o_stream_go = 434,
        o_kv_ready = 435, o_m_rdy = 436, o_m_wd = 440, o_s_v = 444, o_s_tag = 448, o_s_beat = 512, o_s_data = 528,
        o_a_v = 1552, o_a_addr = o_a_v + NPC, o_a_len = o_a_addr + NPC*AW, o_a_tag = o_a_len + NPC*LENW,
        o_a_we = o_a_tag + NPC*STAGW, o_a_wdata = o_a_we + NPC, o_a_wstrb = o_a_wdata + NPC*DW,
        o_a_rrdy = o_a_wstrb + NPC*DW/8,
        o_g_v = o_a_rrdy + NPC, o_g_addr = o_g_v + NPC, o_g_len = o_g_addr + NPC*AW, o_g_tag = o_g_len + NPC*LENW,
        o_g_rrdy = o_g_tag + NPC*WTAGW,
        o_h_rdy = o_g_rrdy + NPC, o_h_wd = o_h_rdy + NPC, o_r_v = o_h_wd + NPC, o_r_tag = o_r_v + NPC,
        o_r_beat = o_r_tag + NPC*STAGW, o_r_data = o_r_beat + NPC*BEATW;
    // source <-> wmux client 0
    wire [NPC-1:0] wl_req_v, wl_req_rdy, wl_rsp_v, wl_rsp_rdy;
    wire [NPC*AW-1:0] wl_req_addr; wire [NPC*LENW-1:0] wl_req_len; wire [NPC*WTAGW-1:0] wl_req_tag, wl_rsp_tag;
    wire [NPC*BEATW-1:0] wl_rsp_beat; wire [NPC*DW-1:0] wl_rsp_data;
    wire prime_ready, blk_ready, start_ready, staged_v, busy, done, fault, kv_v;
    wire [4:0] fault_code; wire [3:0] kv_m; wire [4*16*265-1:0] kv_w;
    wire [31:0] refill_cycles, sectors_read, rows_fetched, blocks_written, sectors_written, la_cycles;
    wire [7:0] rows_refilled;
    wire [3:0] m_v, m_we, s_rdy; wire [4*AW-1:0] m_addr; wire [15:0] m_len; wire [4*TAGW-1:0] m_tag;
    wire [1023:0] m_wdata; wire [127:0] m_wstrb;
    ot_dsrom_window_attn_source_la #(.STREAM_LA(1), .LA_ISSUE_PC(1), .REFILL_OWNER_SAFE(1), .POS_W(21), .USER_W(10), .SEC_W(AW),
        .HAW(AW), .TAGW(TAGW), .WIN_STACK(0), .STREAM_II1(0), .REFILL_CREDITS(8)) u_src (
        .clk(clk), .rst_n(rst_n),
        .retain_qk(1'b0), .retain_pv(1'b0), .retain_complete(1'b0), .retain_invalidate(1'b0),
        .retain_generation(16'd0),
        .region_base_sector(ir[o_rbase +: 30]), .region_sector_count(ir[o_rcount +: 30]),
        .prime_v(ir[o_prime_v]), .prime_ready(prime_ready), .prime_user(ir[o_prime_user +: 10]),
        .prime_row(ir[o_prime_row +: 21]),
        .blk_v(ir[o_blk_v]), .blk_ready(blk_ready), .blk_user(ir[o_blk_user +: 10]), .blk_row(ir[o_blk_row +: 21]),
        .blk_idx(ir[o_blk_idx +: 4]), .blk_codes(ir[o_blk_codes +: 256]), .blk_scale(ir[o_blk_scale +: 8]),
        .start_v(ir[o_start_v]), .start_ready(start_ready), .start_user(ir[o_start_user +: 10]),
        .start_first(ir[o_start_first +: 21]), .start_count(ir[o_start_count +: 8]), .staged_v(staged_v),
        .stream_go(ir[o_stream_go]), .busy(busy), .done(done), .fault(fault), .fault_code(fault_code),
        .refill_cycles(refill_cycles), .sectors_read(sectors_read), .rows_fetched(rows_fetched),
        .blocks_written(blocks_written), .sectors_written(sectors_written), .rows_refilled(rows_refilled),
        .kv_v(kv_v), .kv_ready(ir[o_kv_ready]), .kv_m(kv_m), .kv_w(kv_w),
        .m_v(m_v), .m_rdy(ir[o_m_rdy +: 4]), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag), .m_we(m_we),
        .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wr_done(ir[o_m_wd +: 4]),
        .s_v(ir[o_s_v +: 4]), .s_rdy(s_rdy), .s_tag(ir[o_s_tag +: 64]), .s_beat(ir[o_s_beat +: 16]),
        .s_data(ir[o_s_data +: 1024]),
        .wl_req_v(wl_req_v), .wl_req_rdy(wl_req_rdy), .wl_req_addr(wl_req_addr), .wl_req_len(wl_req_len),
        .wl_req_tag(wl_req_tag), .wl_rsp_v(wl_rsp_v), .wl_rsp_rdy(wl_rsp_rdy), .wl_rsp_tag(wl_rsp_tag),
        .wl_rsp_beat(wl_rsp_beat), .wl_rsp_data(wl_rsp_data), .la_load_cycles(la_cycles));
    wire [2*NPC-1:0] c_rdy, c_rv; wire [2*NPC*WTAGW-1:0] c_rtag; wire [2*NPC*BEATW-1:0] c_rbeat;
    wire [2*NPC*DW-1:0] c_rdata;
    wire [NPC-1:0] a_rdy, a_wd, a_rv, h_v, h_we, r_rdy; wire [NPC*STAGW-1:0] a_rtag, h_tag;
    wire [NPC*BEATW-1:0] a_rbeat; wire [NPC*DW-1:0] a_rdata, h_wdata; wire [NPC*AW-1:0] h_addr;
    wire [NPC*LENW-1:0] h_len; wire [NPC*DW/8-1:0] h_wstrb; wire wm_fault; wire [31:0] wg, ah;
    ot_dsrom_hbm_wmux #(.ENABLE(1), .NPC(NPC), .AW(AW), .TAGW(STAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
        .NW(2), .CW(1), .WTAGW(WTAGW)) u_wmux (
        .clk(clk), .rst_n(rst_n),
        .a_v(ir[o_a_v +: NPC]), .a_rdy(a_rdy), .a_addr(ir[o_a_addr +: NPC*AW]), .a_len(ir[o_a_len +: NPC*LENW]),
        .a_tag(ir[o_a_tag +: NPC*STAGW]), .a_we(ir[o_a_we +: NPC]), .a_wdata(ir[o_a_wdata +: NPC*DW]),
        .a_wstrb(ir[o_a_wstrb +: NPC*DW/8]), .a_wr_done(a_wd), .a_rsp_v(a_rv), .a_rsp_rdy(ir[o_a_rrdy +: NPC]),
        .a_rsp_tag(a_rtag), .a_rsp_beat(a_rbeat), .a_rsp_data(a_rdata),
        .w_v({ir[o_g_v +: NPC], wl_req_v}), .w_rdy(c_rdy), .w_addr({ir[o_g_addr +: NPC*AW], wl_req_addr}),
        .w_len({ir[o_g_len +: NPC*LENW], wl_req_len}), .w_tag({ir[o_g_tag +: NPC*WTAGW], wl_req_tag}),
        .w_rsp_v(c_rv), .w_rsp_rdy({ir[o_g_rrdy +: NPC], wl_rsp_rdy}), .w_rsp_tag(c_rtag), .w_rsp_beat(c_rbeat),
        .w_rsp_data(c_rdata),
        .h_v(h_v), .h_rdy(ir[o_h_rdy +: NPC]), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
        .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(ir[o_h_wd +: NPC]),
        .r_v(ir[o_r_v +: NPC]), .r_rdy(r_rdy), .r_tag(ir[o_r_tag +: NPC*STAGW]), .r_beat(ir[o_r_beat +: NPC*BEATW]),
        .r_data(ir[o_r_data +: NPC*DW]), .fault(wm_fault), .w_grants(wg), .a_held(ah));
    assign wl_req_rdy = c_rdy[0 +: NPC];
    assign wl_rsp_v = c_rv[0 +: NPC]; assign wl_rsp_tag = c_rtag[0 +: NPC*WTAGW];
    assign wl_rsp_beat = c_rbeat[0 +: NPC*BEATW]; assign wl_rsp_data = c_rdata[0 +: NPC*DW];
    // ---------- registered outputs, folded into dout ----------
    wire [NPC*(1+AW+LENW+STAGW+1+DW+DW/8) + NPC + NPC + NPC + NPC*(STAGW+BEATW+DW) + 2*NPC + 2*NPC*(WTAGW+BEATW+DW)
          + 4*(1+AW+4+TAGW+1+256+32) + 4 + 1 + 4 + 16960 + 8 + 5 + 6 + 6*32 + 2 + 32 + 32 - 1:0] ov = {
        h_v, h_addr, h_len, h_tag, h_we, h_wdata, h_wstrb, r_rdy, a_rdy, a_wd, a_rtag, a_rbeat, a_rdata, a_rv,
        c_rdy, c_rv, c_rtag, c_rbeat, c_rdata, m_v, m_addr, m_len, m_tag, m_we, m_wdata, m_wstrb, s_rdy,
        kv_v, kv_m, kv_w, rows_refilled, fault_code, prime_ready, blk_ready, start_ready, staged_v, busy, done,
        refill_cycles, sectors_read, rows_fetched, blocks_written, sectors_written, la_cycles, fault, wm_fault, wg, ah};
    localparam integer NOUT = $bits(ov);
    // parallel load every 64th cycle, else shift out 256 bits a cycle: every output flop is observable
    reg [NOUT-1:0] orr;
    reg [5:0] ph;
    always @(posedge clk) begin
        ph <= ph + 1'b1;
        orr <= (ph == 6'd0) ? ov : (orr >> 256);
        dout <= orr[255:0];
    end
endmodule

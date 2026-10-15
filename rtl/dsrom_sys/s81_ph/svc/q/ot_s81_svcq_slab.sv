`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE s81-svcq-1011: the COMPUTE of one S81 scan-service slab (stack ST of die DIE_ID): everything between the
// svc IO hub's quadrant-side ports (dsfd_svc_io / ot_s81ph_svc_io: q_q copy, a0 / od valid-ready, x) and the 32
// per-PC tiles dsfd_svc_pc (rq / rk / rd / wd).  Composition of unchanged exact engines:
//   ot_s81_svcq_attn    attention: owned-row fetch, held / owned-dim row assembler, ckv merge, ot_hdc_v41x_attn_s
//   ot_dsrom_window_attn_source_la (STREAM_LA 1)  own-row block writer (K port) + 128-row WINDOW
//                       load over the 32 PCs; its engine-format window rows are re-packed (wiring only) into the
//                       merger's 4,224-b window port
//   ot_s81_svcq_idx     index key stream (ring, this stack's quarter) + score quarter -> selector-native x words
//   ot_s81_svcq_pcarb   per-PC arbiter: A = index stream, B = window stream, G = window K ports (4) + fetch ports (P)
// q frames (svc protocol v1) consumed here besides the attention / index types:
//   3 OWN_ROW  header pos = the row's position, user; len 16: word j = block j {[263:256] UE8M0 scale, [255:0] codes}
//   12 CFG     len 0, persists: spec [29:0] window ring region base sector, [59:30] its sector count
// The window job starts with the attention job (WIN_LOAD: user, first position, count).
// ---------------------------------------------------------------------------
module ot_s81_svcq_slab #(
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer P = 8,
    parameter integer DR = 64,
    parameter bit SRAM_MACRO = 0,
    parameter integer ENGINE = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [514:0]         q,            // {fault, live, data[512:1], v[0]} (the IO hub's registered quadrant copy)
    output wire                 a0_v,
    output wire [511:0]         a0_d,
    input  wire                 a0_r,
    output wire                 od_v,
    output wire [511:0]         od_d,
    input  wire                 od_r,
    output wire                 x_v,
    output wire [511:0]         x_d,
    input  wire                 x_r,
    output wire [32*341-1:0]    rq,
    input  wire [31:0]          rk,
    input  wire [31:0]          rv,
    input  wire [32*17-1:0]     r_tag,
    input  wire [32*4-1:0]      r_beat,
    input  wire [32*256-1:0]    r_data,
    input  wire [31:0]          wd,
    output wire                 fault,
    output wire [63:0]          fault_code,
    output wire                 job_active,
    output wire                 kv_beat
);
    localparam integer HAW = 30, NG = 4 + P, FTAGW = 8;
    wire q_v = q[0];
    wire [511:0] q_d = q[512:1];
    reg in_fault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) in_fault <= 0; else if (q[514] || (q_v && !q[513])) in_fault <= 1'b1;

    // ---------------- frame parser (slab-local types: OWN_ROW, CFG) ----------------
    reg in_frame; reg [11:0] left; reg [3:0] f_type; reg f_mine; reg [11:0] f_idx;
    reg [20:0] f_pos; reg [9:0] f_user;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin in_frame <= 0; left <= 0; f_type <= 0; f_mine <= 0; f_idx <= 0; end
        else if (q_v && !in_frame) begin
            f_type <= q_d[511:508]; f_mine <= q_d[503]; f_idx <= 0; left <= q_d[491:480]; in_frame <= q_d[491:480] != 0;
            f_pos <= q_d[479:459]; f_user <= q_d[458:449];
        end else if (q_v) begin
            f_idx <= f_idx + 1'b1; left <= left - 1'b1; if (left == 12'd1) in_frame <= 1'b0;
        end
    end
    reg [29:0] w_rbase, w_rcount;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin w_rbase <= 0; w_rcount <= 0; end
        else if (q_v && !in_frame && q_d[503] && q_d[511:508] == 4'd12) begin w_rbase <= q_d[29:0]; w_rcount <= q_d[59:30]; end
    // OWN_ROW block FIFO (valid-only input: absorbed, overflow is a fault)
    localparam integer BQ = 32;
    reg [21+10+4+264-1:0] bq [0:BQ-1];
    reg [5:0] bqw, bqr;
    wire bq_push = q_v && in_frame && f_mine && f_type == 4'd3;
    // Gate mutants (tb_s81_svcq_slab must FAIL each): SVCQS_MUT_BIDX block index lost, SVCQS_MUT_POS row position +1.
`ifdef SVCQS_MUT_BIDX
    always @(posedge clk) if (bq_push) bq[bqw[4:0]] <= {f_pos, f_user, 4'd0, q_d[263:0]};
`elsif SVCQS_MUT_POS
    always @(posedge clk) if (bq_push) bq[bqw[4:0]] <= {f_pos + 21'd1, f_user, f_idx[3:0], q_d[263:0]};
`else
    always @(posedge clk) if (bq_push) bq[bqw[4:0]] <= {f_pos, f_user, f_idx[3:0], q_d[263:0]};
`endif
    wire blk_v = bqw != bqr;
    wire blk_ready;
    wire [298:0] bh = bq[bqr[4:0]];
    reg bq_ovf;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin bqw <= 0; bqr <= 0; bq_ovf <= 0; end
        else begin
            if (bq_push) begin bqw <= bqw + 1'b1; if (bqw - bqr >= 6'(BQ)) bq_ovf <= 1'b1; end
            if (blk_v && blk_ready) bqr <= bqr + 1'b1;
        end

    // ---------------- attention ----------------
    wire wj_v; wire [9:0] wj_user; wire [20:0] wj_first; wire [7:0] wj_count;
    wire w_v, w_ready; wire [3:0] w_m; wire [4*4224-1:0] w_rows;
    wire [P-1:0] f_mv, f_mrdy, f_sv; wire [P*HAW-1:0] f_maddr; wire [P*FTAGW-1:0] f_mtag, f_stag;
    wire [P*4-1:0] f_sbeat; wire [P*256-1:0] f_sdata;
    wire at_fault; wire [15:0] at_fc; wire qk_iss, pv_iss;
    ot_s81_svcq_attn #(.DIE_ID(DIE_ID), .ST(ST), .P(P), .SRAM_MACRO(SRAM_MACRO), .ENGINE(ENGINE)) u_attn (
        .clk(clk), .rst_n(rst_n), .q_v(q_v), .q_d(q_d),
        .wj_v(wj_v), .wj_user(wj_user), .wj_first(wj_first), .wj_count(wj_count),
        .w_v(w_v), .w_ready(w_ready), .w_m(w_m), .w_rows(w_rows),
        .m_v(f_mv), .m_rdy(f_mrdy), .m_addr(f_maddr), .m_tag(f_mtag),
        .s_v(f_sv), .s_tag(f_stag), .s_beat(f_sbeat), .s_data(f_sdata),
        .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .od_v(od_v), .od_d(od_d), .od_r(od_r),
        .kv_beat(kv_beat), .qk_iss(qk_iss), .pv_iss(pv_iss), .job_active(job_active),
        .fault(at_fault), .fault_code(at_fc));

    // ---------------- window source ----------------
    reg ws_pend; reg [9:0] ws_user; reg [20:0] ws_first; reg [7:0] ws_count;
    wire ws_ready;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ws_pend <= 0;
        else if (wj_v) begin ws_pend <= wj_count != 0; ws_user <= wj_user; ws_first <= wj_first; ws_count <= wj_count; end
        else if (ws_ready) ws_pend <= 1'b0;
    wire wsrc_v; wire [3:0] wsrc_m; wire [4*16*265-1:0] wsrc_w;
    wire [3:0] wm_v, wm_rdy, wm_we, wm_wr_done, ws_v, ws_rdy;
    wire [4*HAW-1:0] wm_addr; wire [15:0] wm_len, ws_beat; wire [4*12-1:0] wm_tag, ws_tag;
    wire [1023:0] wm_wdata, ws_data; wire [127:0] wm_wstrb;
    wire [31:0] wl_v, wl_rdy, wl_rsp_v, wl_rsp_rdy; wire [32*HAW-1:0] wl_addr; wire [32*4-1:0] wl_len, wl_rsp_beat;
    wire [32*12-1:0] wl_tag, wl_rsp_tag; wire [32*256-1:0] wl_rsp_data;
    wire w_busy, w_done, w_fault; wire [4:0] w_fc;
    ot_dsrom_window_attn_source_la #(.STREAM_LA(1), .WINDOW_PIPELINE(0), .POS_W(21), .USER_W(10), .SEC_W(30), .HAW(HAW),
        .TAGW(12), .NPC(32), .WTAGW(12), .WLENW(4), .BEATW(4)) u_win (
        .clk(clk), .rst_n(rst_n),
        .retain_qk(1'b0), .retain_pv(1'b0), .retain_complete(1'b0), .retain_invalidate(1'b0), .retain_generation(16'd0),
        .region_base_sector(w_rbase), .region_sector_count(w_rcount),
        .prime_v(1'b0), .prime_ready(), .prime_user(10'd0), .prime_row(21'd0),
        .blk_v(blk_v), .blk_ready(blk_ready), .blk_user(bh[268 +: 10]), .blk_row(bh[278 +: 21]), .blk_idx(bh[264 +: 4]),
        .blk_codes(bh[255:0]), .blk_scale(bh[263:256]),
        .start_v(ws_pend), .start_ready(ws_ready), .start_user(ws_user), .start_first(ws_first), .start_count(ws_count),
        .staged_v(), .stream_go(1'b1),
        .busy(w_busy), .done(w_done), .fault(w_fault), .fault_code(w_fc),
        .refill_cycles(), .sectors_read(), .rows_fetched(), .blocks_written(), .sectors_written(), .rows_refilled(),
        .kv_v(wsrc_v), .kv_ready(w_ready), .kv_m(wsrc_m), .kv_w(wsrc_w),
        .m_v(wm_v), .m_rdy(wm_rdy), .m_addr(wm_addr), .m_len(wm_len), .m_tag(wm_tag), .m_we(wm_we),
        .m_wdata(wm_wdata), .m_wstrb(wm_wstrb), .m_wr_done(wm_wr_done),
        .s_v(ws_v), .s_rdy(ws_rdy), .s_tag(ws_tag), .s_beat(ws_beat), .s_data(ws_data),
        .wl_req_v(wl_v), .wl_req_rdy(wl_rdy), .wl_req_addr(wl_addr), .wl_req_len(wl_len), .wl_req_tag(wl_tag),
        .wl_rsp_v(wl_rsp_v), .wl_rsp_rdy(wl_rsp_rdy), .wl_rsp_tag(wl_rsp_tag), .wl_rsp_beat(wl_rsp_beat),
        .wl_rsp_data(wl_rsp_data), .la_load_cycles());
    // engine-format window rows -> the merger's packed 4,224-b rows (wiring: group g = {fmt 0, scale, 32 codes})
    assign w_v = wsrc_v; assign w_m = wsrc_m;
    genvar gl, gg;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_wl
        for (gg = 0; gg < 16; gg = gg + 1) begin : g_wg
            assign w_rows[gl*4224 + 256*gg +: 256] = wsrc_w[(gl*16 + gg)*265 +: 256];
            assign w_rows[gl*4224 + 4096 + 8*gg +: 8] = wsrc_w[(gl*16 + gg)*265 + 256 +: 8];
        end
    end endgenerate
    reg w_fmt_bad;                      // a window lane with the CKV format bit is a contract violation
    integer wi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w_fmt_bad <= 0;
        else if (wsrc_v) for (wi = 0; wi < 64; wi = wi + 1) if (wsrc_m[wi/16] && wsrc_w[wi*265 + 264]) w_fmt_bad <= 1'b1;

    // ---------------- index ----------------
    wire [31:0] ix_v, ix_rdy, ix_rsp_v, ix_rsp_rdy; wire [32*HAW-1:0] ix_addr; wire [32*4-1:0] ix_len, ix_rsp_beat;
    wire [32*16-1:0] ix_tag, ix_rsp_tag; wire [32*256-1:0] ix_rsp_data;
    wire ix_fault; wire [7:0] ix_fc;
    ot_s81_svcq_idx #(.ST(ST), .TAGW(16)) u_idx (
        .clk(clk), .rst_n(rst_n), .q_v(q_v), .q_d(q_d),
        .req_v(ix_v), .req_rdy(ix_rdy), .req_addr(ix_addr), .req_len(ix_len), .req_tag(ix_tag),
        .rsp_v(ix_rsp_v), .rsp_rdy(ix_rsp_rdy), .rsp_tag(ix_rsp_tag), .rsp_beat(ix_rsp_beat), .rsp_data(ix_rsp_data),
        .x_v(x_v), .x_d(x_d), .x_r(x_r), .fault(ix_fault), .fault_code(ix_fc));

    // ---------------- per-PC arbiter ----------------
    wire [NG-1:0] g_v, g_rdy, g_we, g_wr_done, g_rsp_v, g_rsp_rdy;
    wire [NG*HAW-1:0] g_addr; wire [NG*4-1:0] g_len, g_rsp_beat; wire [NG*12-1:0] g_tag, g_rsp_tag;
    wire [NG*256-1:0] g_wdata, g_rsp_data; wire [NG*32-1:0] g_wstrb;
    assign g_v = {f_mv, wm_v};
    assign g_addr = {f_maddr, wm_addr};
    assign g_len = {{P{4'd1}}, wm_len};
    assign g_we = {{P{1'b0}}, wm_we};
    assign g_wdata = {{P{256'd0}}, wm_wdata};
    assign g_wstrb = {{P{32'd0}}, wm_wstrb};
    genvar gf;
    generate for (gf = 0; gf < P; gf = gf + 1) begin : g_ft
        assign g_tag[(4 + gf)*12 +: 12] = 12'(f_mtag[gf*FTAGW +: FTAGW]);
        assign f_stag[gf*FTAGW +: FTAGW] = g_rsp_tag[(4 + gf)*12 +: FTAGW];
    end endgenerate
    assign g_tag[4*12-1:0] = wm_tag;
    assign f_mrdy = g_rdy[NG-1:4]; assign wm_rdy = g_rdy[3:0];
    assign wm_wr_done = g_wr_done[3:0];
    assign ws_v = g_rsp_v[3:0]; assign ws_tag = g_rsp_tag[4*12-1:0]; assign ws_beat = g_rsp_beat[15:0];
    assign ws_data = g_rsp_data[1023:0];
    assign f_sv = g_rsp_v[NG-1:4]; assign f_sbeat = g_rsp_beat[NG*4-1:16]; assign f_sdata = g_rsp_data[NG*256-1:1024];
    assign g_rsp_rdy = {{P{1'b1}}, ws_rdy};
    wire pa_fault; wire [4:0] pa_fc;
    ot_s81_svcq_pcarb #(.NPC(32), .NG(NG), .DQ(8), .DR(DR), .AW(HAW)) u_arb (
        .clk(clk), .rst_n(rst_n),
        .a_v(ix_v), .a_rdy(ix_rdy), .a_addr(ix_addr), .a_len(ix_len), .a_tag(ix_tag),
        .a_rsp_v(ix_rsp_v), .a_rsp_rdy(ix_rsp_rdy), .a_rsp_tag(ix_rsp_tag), .a_rsp_beat(ix_rsp_beat), .a_rsp_data(ix_rsp_data),
        .b_v(wl_v), .b_rdy(wl_rdy), .b_addr(wl_addr), .b_len(wl_len), .b_tag(wl_tag),
        .b_rsp_v(wl_rsp_v), .b_rsp_rdy(wl_rsp_rdy), .b_rsp_tag(wl_rsp_tag), .b_rsp_beat(wl_rsp_beat), .b_rsp_data(wl_rsp_data),
        .g_v(g_v), .g_rdy(g_rdy), .g_addr(g_addr), .g_len(g_len), .g_tag(g_tag), .g_we(g_we), .g_wdata(g_wdata),
        .g_wstrb(g_wstrb), .g_wr_done(g_wr_done), .g_rsp_v(g_rsp_v), .g_rsp_rdy(g_rsp_rdy), .g_rsp_tag(g_rsp_tag),
        .g_rsp_beat(g_rsp_beat), .g_rsp_data(g_rsp_data),
        .rq(rq), .rk(rk), .rv(rv), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data), .wd(wd),
        .fault(pa_fault), .fault_code(pa_fc));

    assign fault_code = {16'd0, 3'd0, in_fault, bq_ovf, w_fmt_bad, w_fault, w_fc, pa_fault, pa_fc, ix_fault, ix_fc, at_fc};
    assign fault = in_fault || bq_ovf || w_fmt_bad || w_fault || pa_fault || ix_fault || at_fault;
endmodule

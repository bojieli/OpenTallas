`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE s81die-1011/ctrl svch: the slab-singleton functions of the hierarchical scan service, hosted in quadrant 2
// (dsfd_svc_quad QID 2: the middle of the 4-quadrant row -- one quadrant hop to Q1 / Q3, two to Q0 -- with the
// shortest station chain of the three western quadrants to the IO hub).  All of it is the flat ot_s81_svcq_slab /
// ot_s81_svcq_attn function, unchanged in value, re-plumbed onto registered seams:
//   OWN_ROW block FIFO + CFG       (as ot_s81_svcq_slab; gate mutants SVCQS_MUT_BIDX / SVCQS_MUT_POS kept here)
//   window source                  ot_dsrom_window_attn_source_la STREAM_LA 1 (unchanged); its 32 per-PC wide ports
//                                  are B LANES to the owning quadrant's PC service (credit request lane, landing FIFO
//                                  DRB beats here with pop credits back to that service's reservation); its rows are
//                                  BROADCAST as 4 dim slices on credit lanes (sent when every quadrant holds a credit)
//   owned-row fetch                ot_s81_svcq_selfetch (unchanged), fed from quadrant 2's assembler copy; its rows go
//                                  to the od export FIFO and, as dim slices, valid-only to every quadrant's assembler
//   G router                       window K ports (4) + fetch ports (8): per-port registered slot (pc = the PHY map
//                                  ((s >> 2) ^ (s >> 7) ^ (s >> 12)) mod 32 decoded once), per-destination-quadrant
//                                  round robin over the registered slots into that quadrant's G credit lane; G
//                                  responses from the 4 lanes steered to their port by a registered per-port pick;
//                                  write completions summed per port (one g_wr_done pulse a cycle per port)
//   result emitter                a0 (scores of the held rows from the ROOT combine, then p.v of the owned dims from
//                                  quadrant ST's PV lane) and od (ROWX of every fetched row): ot_s81_svcq_attn's frame
//                                  format, order rules and END (source id 0, on the job's last PV frame, after every
//                                  ROWX frame and score beat); fail closed on any quadrant / home fault.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svch_home #(
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer P = 8,
    parameter integer NG = 13,
    parameter integer DRB = 64,
    parameter integer DW0 = 22, DW1 = 14, DW2 = 4, DW3 = 14,     // per-destination credit-lane depths (2 NR + 4)
    parameter bit SRAM_MACRO = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 q_v,
    input  wire [511:0]         q_d,
    // quadrant 2's attention-quarter job state
    input  wire                 go,
    input  wire [7:0]           tagj,
    input  wire [20:0]          posj,
    input  wire [9:0]           userj,
    input  wire [7:0]           wcount,
    input  wire [29:0]          rbase,
    input  wire [29:0]          rcount,
    input  wire [20:0]          npub,
    input  wire                 wj_v,
    input  wire [9:0]           wj_user,
    input  wire [20:0]          wj_first,
    input  wire [7:0]           wj_count,
    input  wire [511:0]         held,
    input  wire [9:0]           own_count,
    input  wire                 own_done,
    output wire [9:0]           own_idx,
    input  wire [9:0]           own_rank,
    input  wire [20:0]          own_gid,
    // window broadcast lanes (per quadrant d: {mask 4, slice 4,224}) + credits
    output wire [3:0]           wb_v,
    output wire [4*4228-1:0]    wb_d,
    input  wire [3:0]           wb_c,
    // fetched-row broadcast (valid-only) {rank 10, gid 21, slice 576}
    output reg  [3:0]           fb_v,
    output reg  [4*607-1:0]     fb_d,
    // B lanes, all 32 PCs: requests {len, addr, tag 12} + credits, responses {tag 12, beat, data} + landing credits
    output wire [31:0]          bq_v,
    output wire [32*46-1:0]     bq_d,
    input  wire [31:0]          bq_c,
    input  wire [31:0]          br_v,
    input  wire [32*272-1:0]    br_d,
    output wire [31:0]          br_c,
    // G lanes per quadrant: requests (344) + credits, responses (276) + credits, write completions
    output wire [3:0]           gq_v,
    output wire [4*344-1:0]     gq_d,
    input  wire [3:0]           gq_c,
    input  wire [3:0]           gr_v,
    input  wire [4*276-1:0]     gr_d,
    output wire [3:0]           gr_c,
    input  wire [4*NG-1:0]      gwd,
    // scores (root combine) and p.v words (quadrant ST's lane, after its receiver)
    input  wire                 sc_v,
    output wire                 sc_r,
    input  wire [2131:0]        sc_d,
    input  wire                 pv_v,
    output wire                 pv_r,
    input  wire [512:0]         pv_d,
    input  wire                 qfault,        // any quadrant / combine / lane fault (registered, relayed)
    // per-stack host writes (dsfd_host_sd hw<s> without v: {cls 2, we, addr 32, d 256}) and their completions
    input  wire                 hw_v,
    input  wire [290:0]         hw_d,
    output reg                  hc_cr,
    output reg  [7:0]           hc_ack,
    // results
    output reg                  a0_v,
    output reg  [511:0]         a0_d,
    input  wire                 a0_r,
    output reg                  od_v,
    output reg  [511:0]         od_d,
    input  wire                 od_r,
    output wire                 fault,
    output wire [31:0]          fault_code
);
    localparam integer HAW = 30, NL = 4, H = 16, KW = 10, POS_W = 21, FTAGW = 8;
    function automatic integer dw(input integer d);
        dw = (d == 0) ? DW0 : (d == 1) ? DW1 : (d == 2) ? DW2 : DW3;
    endfunction
    function automatic [4:0] pc_of(input [HAW-1:0] s);
        pc_of = 5'((s >> 2) ^ (s >> 7) ^ (s >> 12));
    endfunction
    genvar gd, gp, gk;

    // ---------------- OWN_ROW / CFG parser (ot_s81_svcq_slab) ----------------
    reg in_frame; reg [11:0] left; reg [3:0] f_type; reg f_mine; reg [11:0] f_idx; reg [20:0] f_pos; reg [9:0] f_user;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin in_frame <= 0; left <= 0; f_type <= 0; f_mine <= 0; f_idx <= 0; f_pos <= 0; f_user <= 0; end
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
    localparam integer BQ = 32;
    reg [21+10+4+264-1:0] bq [0:BQ-1];
    reg [5:0] bqw, bqr;
    wire bq_push = q_v && in_frame && f_mine && f_type == 4'd3;
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

    // ---------------- window source (unchanged) ----------------
    reg ws_pend; reg [9:0] ws_user; reg [20:0] ws_first; reg [7:0] ws_count;
    wire ws_ready;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ws_pend <= 0; ws_user <= 0; ws_first <= 0; ws_count <= 0; end
        else if (wj_v) begin ws_pend <= wj_count != 0; ws_user <= wj_user; ws_first <= wj_first; ws_count <= wj_count; end
        else if (ws_ready) ws_pend <= 1'b0;
    wire wsrc_v, wsrc_ready; wire [3:0] wsrc_m; wire [4*16*265-1:0] wsrc_w;
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
        .kv_v(wsrc_v), .kv_ready(wsrc_ready), .kv_m(wsrc_m), .kv_w(wsrc_w),
        .m_v(wm_v), .m_rdy(wm_rdy), .m_addr(wm_addr), .m_len(wm_len), .m_tag(wm_tag), .m_we(wm_we),
        .m_wdata(wm_wdata), .m_wstrb(wm_wstrb), .m_wr_done(wm_wr_done),
        .s_v(ws_v), .s_rdy(ws_rdy), .s_tag(ws_tag), .s_beat(ws_beat), .s_data(ws_data),
        .wl_req_v(wl_v), .wl_req_rdy(wl_rdy), .wl_req_addr(wl_addr), .wl_req_len(wl_len), .wl_req_tag(wl_tag),
        .wl_rsp_v(wl_rsp_v), .wl_rsp_rdy(wl_rsp_rdy), .wl_rsp_tag(wl_rsp_tag), .wl_rsp_beat(wl_rsp_beat),
        .wl_rsp_data(wl_rsp_data), .la_load_cycles());
    reg w_fmt_bad;
    integer wi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w_fmt_bad <= 0;
        else if (wsrc_v) for (wi = 0; wi < 64; wi = wi + 1) if (wsrc_m[wi/16] && wsrc_w[wi*265 + 264]) w_fmt_bad <= 1'b1;
    // broadcast: quarter d of each row = groups 4 d .. 4 d + 3 -> {scales 32, codes 1024}
    wire [3:0] wb_ir;
    assign wsrc_ready = &wb_ir;
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_wb
        wire [4227:0] sl;
        for (gp = 0; gp < 4; gp = gp + 1) begin : g_l
            for (gk = 0; gk < 4; gk = gk + 1) begin : g_g
                assign sl[gp*1056 + 256*gk +: 256] = wsrc_w[(gp*16 + 4*gd + gk)*265 +: 256];
                assign sl[gp*1056 + 1024 + 8*gk +: 8] = wsrc_w[(gp*16 + 4*gd + gk)*265 + 256 +: 8];
            end
        end
        assign sl[4227:4224] = wsrc_m;
        ot_s81_svch_ctx #(.W(4228), .DEPTH(dw(gd))) u_tx (.clk(clk), .rst_n(rst_n), .i_v(wsrc_v && wsrc_ready),
            .i_r(wb_ir[gd]), .i_d(sl), .o_v(wb_v[gd]), .o_d(wb_d[gd*4228 +: 4228]), .c_in(wb_c[gd]));
    end endgenerate

    // ---------------- owned-row fetch (unchanged) + od export FIFO + broadcast ----------------
    wire [P-1:0] f_mv, f_mrdy, f_sv; wire [P*HAW-1:0] f_maddr; wire [P*FTAGW-1:0] f_mtag, f_stag;
    wire [P*4-1:0] f_sbeat; wire [P*256-1:0] f_sdata;
    wire f_ov, f_or; wire [KW-1:0] f_rank; wire [POS_W-1:0] f_gid; wire [2303:0] f_row;
    wire f_run, f_done, f_fault; wire [3:0] f_fc;
    ot_s81_svcq_selfetch #(.DIE_ID(DIE_ID), .ST(ST), .P(P), .S(16), .HAW(HAW), .SRAM_MACRO(SRAM_MACRO)) u_fetch (
        .clk(clk), .rst_n(rst_n), .job_v(go), .published_source_count(npub),
        .region_base_sector(rbase), .region_sector_count(rcount),
        .id_count(own_count), .id_done(own_done), .id_idx(own_idx), .id_rank_in(own_rank), .id_gid(own_gid),
        .o_v(f_ov), .o_ready(f_or), .o_rank(f_rank), .o_gid(f_gid), .o_row(f_row),
        .run(f_run), .done(f_done), .fault(f_fault), .fault_code(f_fc),
        .m_v(f_mv), .m_rdy(f_mrdy), .m_addr(f_maddr), .m_tag(f_mtag),
        .s_v(f_sv), .s_tag(f_stag), .s_beat(f_sbeat), .s_data(f_sdata));
    localparam integer XQ = 8;
    reg [KW+POS_W+2304-1:0] xq [0:XQ-1];
    reg [3:0] xw, xr;
    assign f_or = (xw - xr) < 4'(XQ);
    always @(posedge clk) if (f_ov && f_or) xq[xw[2:0]] <= {f_rank, f_gid, f_row};
    integer fd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fb_v <= 0;
        else fb_v <= {4{f_ov && f_or}};
    always @(posedge clk)
        for (fd = 0; fd < 4; fd = fd + 1)
            fb_d[fd*607 +: 607] <= {f_rank, f_gid, f_row[2048 + 64*fd +: 64], f_row[512*fd +: 512]};

    // ---------------- B lanes (window wide port, 32 PCs) ----------------
    wire [31:0] b_ovfv;
    generate for (gp = 0; gp < 32; gp = gp + 1) begin : g_b
        ot_s81_svch_ctx #(.W(46), .DEPTH(dw(gp / 8))) u_tx (.clk(clk), .rst_n(rst_n), .i_v(wl_v[gp]), .i_r(wl_rdy[gp]),
            .i_d({wl_len[gp*4 +: 4], wl_addr[gp*HAW +: HAW], wl_tag[gp*12 +: 12]}),
            .o_v(bq_v[gp]), .o_d(bq_d[gp*46 +: 46]), .c_in(bq_c[gp]));
        ot_s81_svch_crx #(.W(272), .DEPTH(DRB)) u_rx (.clk(clk), .rst_n(rst_n), .i_v(br_v[gp]), .i_d(br_d[gp*272 +: 272]),
            .o_v(wl_rsp_v[gp]), .o_r(wl_rsp_rdy[gp]),
            .o_d({wl_rsp_tag[gp*12 +: 12], wl_rsp_beat[gp*4 +: 4], wl_rsp_data[gp*256 +: 256]}), .c_out(br_c[gp]), .ovf(b_ovfv[gp]));
    end endgenerate
    reg b_ovf;
    always @(posedge clk or negedge rst_n) if (!rst_n) b_ovf <= 0; else if (|b_ovfv) b_ovf <= 1'b1;

    // ---------------- host writes (dsfd_host_sd contract: SCRED 8 credits, one cr pulse per word taken) ----------------
    // KV (cls 0) / RoPE (cls 1) sector writes -> HBM sector addr[29:0] of this stack through G port 12 (the PHY map picks
    // the PC); markers (addr ffffffff) are consumed without a write and without an ack; Engram (cls 2) / reserved class /
    // a read (we 0) is a sticky fault, dropped.  ack = this cycle's completed host sector writes (wd of port 12).
    localparam integer HQD = 16;
    reg [290:0] hq [0:HQD-1]; reg [4:0] hqw, hqr; reg h_ovf, h_bad;
    wire hq_v = hqw != hqr;
    wire [290:0] hq_d = hq[hqr[3:0]];
    wire hq_mark = hq_d[287:256] == 32'hffffffff;
    wire hq_sec = hq_d[288] && hq_d[290:289] < 2'd2 && !hq_mark;
    wire hq_pop = hq_v && (hq_sec ? (p_v[12] && p_rdy[12]) : 1'b1);
    always @(posedge clk) if (hw_v) hq[hqw[3:0]] <= hw_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hqw <= 0; hqr <= 0; h_ovf <= 0; h_bad <= 0; hc_cr <= 0; end
        else begin
            if (hw_v) begin hqw <= hqw + 1'b1; if (hqw - hqr >= 5'(HQD)) h_ovf <= 1'b1; end
            if (hq_pop) hqr <= hqr + 1'b1;
            if (hq_pop && !hq_sec && !(hq_mark && hq_d[288] && hq_d[290:289] < 2'd2)) h_bad <= 1'b1;
            hc_cr <= hq_pop;
        end
    reg [2:0] hk_add; integer hk_n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hc_ack <= 0; hk_n = 0; end
        else begin
            hk_add = 3'(gwd[12]) + 3'(gwd[NG + 12]) + 3'(gwd[2*NG + 12]) + 3'(gwd[3*NG + 12]);
`ifdef SVCH_MUT_HACK
            hk_n = hk_n + 32'(hk_add);
            hc_ack <= (hk_add != 0 && hk_n % 7 == 0) ? 8'(hk_add) - 8'd1 : 8'(hk_add);   // MUTANT: every 7th ack lost
`else
            hc_ack <= 8'(hk_add);
`endif
        end

    // ---------------- G router: per-port registered slots -> per-quadrant round robin ----------------
    reg [NG-1:0] sl_v;
    reg [343:0] sl_d [0:NG-1];
    reg [NG-1:0] taken;
    wire [3:0] gq_ir;
    wire [NG-1:0] p_v;
    wire [NG*344-1:0] p_d;
    wire [NG-1:0] p_bad;
    generate for (gk = 0; gk < NG; gk = gk + 1) begin : g_pt
        wire [HAW-1:0] a0; wire [3:0] ln; wire we; wire [11:0] tg; wire [31:0] stb; wire [255:0] wdat;
        if (gk < 4) begin : g_w
            assign a0 = wm_addr[gk*HAW +: HAW]; assign ln = wm_len[gk*4 +: 4]; assign we = wm_we[gk];
            assign tg = wm_tag[gk*12 +: 12]; assign stb = wm_wstrb[gk*32 +: 32]; assign wdat = wm_wdata[gk*256 +: 256];
            assign p_v[gk] = wm_v[gk];
        end else if (gk < 12) begin : g_f
            assign a0 = f_maddr[(gk-4)*HAW +: HAW]; assign ln = 4'd1; assign we = 1'b0;
            assign tg = 12'(f_mtag[(gk-4)*FTAGW +: FTAGW]); assign stb = 32'd0; assign wdat = 256'd0;
            assign p_v[gk] = f_mv[gk-4];
        end else begin : g_h
            // port 12: host sector writes (one 32-B sector, all bytes)
            assign a0 = hq_d[285:256]; assign ln = 4'd1; assign we = 1'b1;
            assign tg = 12'd0; assign stb = 32'hffffffff; assign wdat = hq_d[255:0];
            assign p_v[gk] = hq_v && hq_sec;
        end
        wire [HAW-1:0] al = a0 + HAW'(ln) - 1'b1;
        assign p_bad[gk] = !we && (ln == 0 || pc_of(al) != pc_of(a0) || (a0 >> 2) != (al >> 2));
        assign p_d[gk*344 +: 344] = {pc_of(a0), 4'(gk), we, we ? 4'd1 : ln, a0, tg, stb, wdat};
    end endgenerate
    wire [NG-1:0] p_rdy = ~sl_v | taken;
    assign wm_rdy = p_rdy[3:0];
    assign f_mrdy = p_rdy[11:4];
    reg [3:0] grr [0:3];
    reg [3:0] gsel_v; reg [3:0] gsel [0:3];
    integer d, s;
    always @(*) begin
        taken = 0;
        for (d = 0; d < 4; d = d + 1) begin
            gsel_v[d] = 1'b0; gsel[d] = 0;
            if (gq_ir[d])
                for (s = 0; s < NG; s = s + 1)
                    if (!gsel_v[d] && sl_v[(32'(grr[d]) + s) % NG] && sl_d[(32'(grr[d]) + s) % NG][343:342] == 2'(d)) begin
                        gsel_v[d] = 1'b1; gsel[d] = 4'((32'(grr[d]) + s) % NG);
                    end
            if (gsel_v[d]) taken[gsel[d]] = 1'b1;
        end
    end
    reg g_bad;
    integer k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sl_v <= 0; g_bad <= 0; for (d = 0; d < 4; d = d + 1) grr[d] <= 0; end
        else begin
            for (k = 0; k < NG; k = k + 1)
                if (p_v[k] && p_rdy[k]) begin
                    if (p_bad[k]) begin g_bad <= 1'b1; sl_v[k] <= 1'b0; end      // dropped (fail closed)
                    else sl_v[k] <= 1'b1;
                end else if (taken[k]) sl_v[k] <= 1'b0;
            for (d = 0; d < 4; d = d + 1) if (gsel_v[d]) grr[d] <= (gsel[d] == 4'(NG - 1)) ? 4'd0 : gsel[d] + 1'b1;
        end
    always @(posedge clk) for (k = 0; k < NG; k = k + 1) if (p_v[k] && p_rdy[k] && !p_bad[k]) sl_d[k] <= p_d[k*344 +: 344];
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_gq
        ot_s81_svch_ctx #(.W(344), .DEPTH(dw(gd))) u_tx (.clk(clk), .rst_n(rst_n), .i_v(gsel_v[gd]), .i_r(gq_ir[gd]),
            .i_d(sl_d[gsel[gd]]), .o_v(gq_v[gd]), .o_d(gq_d[gd*344 +: 344]), .c_in(gq_c[gd]));
    end endgenerate
    // G responses: 4 lane receivers -> per-port registered pick
    wire [3:0] grx_v; wire [275:0] grx_d [0:3]; reg [3:0] grx_r; wire [3:0] grx_ovf;
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_gr
        ot_s81_svch_crx #(.W(276), .DEPTH(dw(gd))) u_rx (.clk(clk), .rst_n(rst_n), .i_v(gr_v[gd]), .i_d(gr_d[gd*276 +: 276]),
            .o_v(grx_v[gd]), .o_r(grx_r[gd]), .o_d(grx_d[gd]), .c_out(gr_c[gd]), .ovf(grx_ovf[gd]));
    end endgenerate
    reg [NG-1:0] po_v; reg [271:0] po_d [0:NG-1]; reg [1:0] prr [0:NG-1];
    wire [NG-1:0] po_rdy = {{(NG-4){1'b1}}, ws_rdy};
    reg [1:0] psel [0:NG-1]; reg [NG-1:0] psel_v;
    always @(*) begin
        grx_r = 0;
        for (k = 0; k < NG; k = k + 1) begin
            psel_v[k] = 1'b0; psel[k] = 0;
            if (!po_v[k] || po_rdy[k])
                for (s = 0; s < 4; s = s + 1)
                    if (!psel_v[k] && grx_v[(32'(prr[k]) + s) % 4] && 32'(grx_d[(32'(prr[k]) + s) % 4][275:272]) == k) begin
                        psel_v[k] = 1'b1; psel[k] = 2'((32'(prr[k]) + s) % 4);
                    end
            if (psel_v[k]) grx_r[psel[k]] = 1'b1;
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin po_v <= 0; for (k = 0; k < NG; k = k + 1) prr[k] <= 0; end
        else for (k = 0; k < NG; k = k + 1) begin
            if (po_v[k] && po_rdy[k]) po_v[k] <= 1'b0;
            if (psel_v[k]) begin po_v[k] <= 1'b1; prr[k] <= psel[k] + 1'b1; end
        end
    always @(posedge clk) for (k = 0; k < NG; k = k + 1) if (psel_v[k]) po_d[k] <= grx_d[psel[k]][271:0];
    generate for (gk = 0; gk < NG; gk = gk + 1) begin : g_po
        if (gk < 4) begin : g_w
            assign ws_v[gk] = po_v[gk]; assign ws_tag[gk*12 +: 12] = po_d[gk][271:260];
            assign ws_beat[gk*4 +: 4] = po_d[gk][259:256]; assign ws_data[gk*256 +: 256] = po_d[gk][255:0];
        end else if (gk < 12) begin : g_f
            assign f_sv[gk-4] = po_v[gk]; assign f_stag[(gk-4)*FTAGW +: FTAGW] = po_d[gk][260 +: FTAGW];
            assign f_sbeat[(gk-4)*4 +: 4] = po_d[gk][259:256]; assign f_sdata[(gk-4)*256 +: 256] = po_d[gk][255:0];
        end
    end endgenerate
    // write completions: per port, the 4 quadrants' pulses summed into a counter, one pulse a cycle
    reg [5:0] wdc [0:3];
    reg [3:0] wdone;
    reg [2:0] wadd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wdone <= 0; for (k = 0; k < 4; k = k + 1) wdc[k] <= 0; end
        else for (k = 0; k < 4; k = k + 1) begin
            wadd = 3'(gwd[k]) + 3'(gwd[NG + k]) + 3'(gwd[2*NG + k]) + 3'(gwd[3*NG + k]);
            wdone[k] <= (wdc[k] != 0) || (wadd != 0);
            wdc[k] <= wdc[k] + 6'(wadd) - 6'((wdc[k] != 0) || (wadd != 0));
        end
    assign wm_wr_done = wdone;
    reg gwd_bad;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) gwd_bad <= 0;
        else for (k = 4; k < 12; k = k + 1) if (gwd[k] | gwd[NG + k] | gwd[2*NG + k] | gwd[3*NG + k]) gwd_bad <= 1'b1;

    // ---------------- result emitter (ot_s81_svcq_attn's, re-plumbed) ----------------
    localparam integer SCB = 2132;
    wire [15:0] s_row = sc_d[SCB-1 -: 16];
    wire [3:0]  s_m   = sc_d[SCB-17 -: 4];
    reg [3:0] hm;
    integer l;
    always @(*) begin
        hm = 0;
        for (l = 0; l < NL; l = l + 1) begin
            if (32'(s_row) + l < 32'(wcount)) hm[l] = s_m[l] && ((32'(s_row) + l) % 4 == ST);
            else hm[l] = s_m[l] && held[KW'(32'(s_row) + l - 32'(wcount))];
        end
    end
    reg [2:0] a_state; reg [4:0] a_i; reg [3:0] a_mask; reg [3:0] pv_frames;
    reg x_busy; reg [3:0] x_i; reg [KW+POS_W+2304-1:0] xb;
    reg emit_flt;
    wire live = !(qfault || fault);
    reg sc_pop, pv_pop;
    assign sc_r = sc_pop; assign pv_r = pv_pop;
    function automatic [511:0] hdr(input [3:0] typ, input endb, input [11:0] len, input [448:0] spec);
        hdr = {typ, endb, 4'd0, tagj, 3'd0, len, posj, userj, spec};
    endfunction
    function automatic integer pop4(input [3:0] m);
        pop4 = m[0] + m[1] + m[2] + m[3];
    endfunction
    integer b, nh;
    reg [448:0] sp;
    always @(*) begin
        sc_pop = 1'b0; pv_pop = 1'b0;
        if (!a0_v || a0_r) begin
            case (a_state)
                0: if (live && sc_v && hm == 0) sc_pop = 1'b1;
                   else if (live && !sc_v && pv_v && pv_d[512] &&
                            (pv_frames != 4'd7 || (x_busy == 0 && xw == xr && f_done))) pv_pop = 1'b1;
                1: sc_pop = pop4(a_mask) == 1;
                2: pv_pop = pv_v;
                default: ;
            endcase
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a0_v <= 0; od_v <= 0; a_state <= 0; a_i <= 0; xw <= 0; xr <= 0; x_busy <= 0; x_i <= 0; pv_frames <= 0;
            emit_flt <= 0; a_mask <= 0; a0_d <= 0; od_d <= 0;   // result registers: emitter state, reset
        end else begin
            if (f_ov && f_or) xw <= xw + 1'b1;
            if (go) pv_frames <= 0;
            if (a0_v && a0_r) a0_v <= 1'b0;
            if (!a0_v || a0_r) begin
                case (a_state)
                    0: if (live && sc_v) begin
                           a_mask <= hm;
                           if (hm != 0) begin
                               sp = 0; sp[448:447] = 2'd0; sp[446:431] = s_row; sp[430:427] = hm; sp[63:0] = sc_d[NL*H-1:0];
                               a0_v <= 1'b1; a0_d <= hdr(4'd8, 1'b0, 12'(pop4(hm)), sp); a_state <= 1;
                           end
                       end else if (pv_pop) begin
                           sp = 0; sp[448:447] = 2'd1; sp[446:431] = 16'(pv_d[263:256]); sp[255:0] = pv_d[255:0];
                           a0_v <= 1'b1; a0_d <= hdr(4'd8, pv_frames == 4'd7, 12'd16, sp); a_state <= 2; a_i <= 0;
                       end else if (live && !sc_v && pv_v && !pv_d[512]) emit_flt <= 1'b1;   // lane out of frame
                    1: begin
                           nh = -1;
                           for (b = NL - 1; b >= 0; b = b - 1) if (a_mask[b]) nh = b;
                           a0_v <= 1'b1; a0_d <= sc_d[NL*H + nh*H*32 +: H*32];
                           a_mask[nh] <= 1'b0;
                           if (pop4(a_mask) == 1) a_state <= 0;
                       end
                    2: if (pv_v) begin
                           if (pv_d[512]) emit_flt <= 1'b1;
                           a0_v <= 1'b1; a0_d <= pv_d[511:0];
                           a_i <= a_i + 1'b1;
                           if (a_i == 5'd15) begin a_state <= 0; pv_frames <= pv_frames + 1'b1; end
                       end
                    default: a_state <= 0;
                endcase
            end
            if (od_v && od_r) od_v <= 1'b0;
            if (!od_v || od_r) begin
                if (!x_busy) begin
                    if (live && xw != xr) begin
                        xb = xq[xr[2:0]];
                        sp = 0; sp[9:0] = xb[KW+POS_W+2304-1 -: KW]; sp[30:10] = xb[POS_W+2304-1 -: POS_W];
                        od_v <= 1'b1; od_d <= hdr(4'd11, 1'b0, 12'd8, sp); x_busy <= 1'b1; x_i <= 0;
                    end
                end else begin
                    xb = xq[xr[2:0]];
                    od_v <= 1'b1;
                    od_d <= {190'd0, xb[2048 + 32*x_i +: 32], xb[256*x_i +: 256], x_i[2:0],
                             xb[POS_W+2304-1 -: POS_W], xb[KW+POS_W+2304-1 -: KW]};
                    x_i <= x_i + 1'b1;
                    if (x_i == 4'd7) begin x_busy <= 1'b0; xr <= xr + 1'b1; end
                end
            end
        end
    end
    wire [3:0] fflt = {f_fault, w_fault, bq_ovf, w_fmt_bad};
    assign fault_code = {4'd0, h_ovf, h_bad, emit_flt, gwd_bad, |grx_ovf, b_ovf, g_bad, f_fc, w_fc, fflt, 8'd0};
    assign fault = |fault_code;
endmodule

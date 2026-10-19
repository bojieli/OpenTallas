// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_eng_seq_static.sv
`timescale 1ns/1ps
`default_nettype none
// HC engine event programme (H-NETLIST/hceng 2026-10-16): a programme SRAM (ot_sram_1r1w_1024x256) of EVENT words,
// each {magic c7a1 [255:240] (the F20 row header the folded ot_static_program_target__d4g_hc checks), pc [233:224], payload [W-1:20], time [19:0]}. A launch runs [start_base, start_limit)
// once (start_loops must be 1). The edge counter t starts at 0 on the edge after start_v is captured; the word at the
// queue head fires (payload on `event`, event_v) on the edge where t == time, so its fields are visible to the engine
// in the cycle after that edge. Times must strictly increase; a word reaching the head after its time (late), a bad
// magic/pc, a write while running, or an illegal start faults. Words are prefetched (read -> macro -> capture -> 4-entry
// queue) so one event per edge is sustained; nothing waits on any datapath response.
module ot_hbm_hc_eng_seq_static__d4g_hc #(
    parameter integer W = 124
)(
    input  wire          clk, rst_n,
    input  wire          cfg_we,
    input  wire [9:0]    cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          start_v,
    input  wire [9:0]    start_base,
    input  wire [10:0]   start_limit,
    input  wire [15:0]   start_loops,
    output reg  [W-1:0]  event_word,
    output reg           event_v,
    output reg  [19:0]   t,
    output reg           active, done, fault
);
    initial if (W < 21 || W > 224) $fatal(1, "event payload must fit");
    // ---- pin flops
    reg cfg_we_q, start_v_q; reg [9:0] cfg_addr_q, start_base_q; reg [255:0] cfg_data_q;
    reg [10:0] start_limit_q; reg [15:0] start_loops_q;
    always @(posedge clk) begin cfg_addr_q <= cfg_addr; cfg_data_q <= cfg_data; start_base_q <= start_base;
        start_limit_q <= start_limit; start_loops_q <= start_loops; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin cfg_we_q <= 0; start_v_q <= 0; end
        else begin cfg_we_q <= cfg_we; start_v_q <= start_v; end
    // ---- fetch
    reg running;                                // words remain to be read
    reg [9:0] rpc; reg [10:0] limit;
    reg rv0, rv1; reg [9:0] rpc0, rpc1;
    wire [255:0] macro_data; reg [255:0] captured;
    reg [2:0] qn;                               // queued words
    wire [2:0] inflight = {2'b0, rv0} + {2'b0, rv1};
    wire issue = running && (qn + inflight) < 3'd4;
    reg [W+9:0] q [0:3];                        // {pc, payload}
    reg [1:0] qh, qt;
    reg busy;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk), .r_ce_in(issue), .r_addr_in(rpc), .rd_out(macro_data),
        .w_ce_in(cfg_we_q && !busy && !start_v_q), .w_addr_in(cfg_addr_q), .wd_in(cfg_data_q), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk) captured <= macro_data;
    wire word_ok = captured[255:240] == 16'hc7a1 && captured[233:224] == rpc1 && captured[239:234] == 0 &&
                   captured[223:W] == 0;
    wire [W-1:0] head = q[qh][W-1:0];
    wire head_v = qn != 0;
    wire fire = head_v && head[19:0] == t;
    wire legal_start = start_limit_q > {1'b0, start_base_q} && start_limit_q <= 11'd1024 && start_loops_q == 16'd1;
    reg [19:0] last_time; reg have_last;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 0; rpc <= 0; limit <= 0; rv0 <= 0; rv1 <= 0; qn <= 0; qh <= 0; qt <= 0; busy <= 0; t <= 0;
            event_v <= 0; active <= 0; done <= 0; fault <= 0; have_last <= 0; last_time <= 0;
        end else begin
            event_v <= 1'b0; done <= 1'b0;
            if (busy) t <= t + 1'b1;
            rv0 <= issue; rv1 <= rv0; rpc0 <= rpc; rpc1 <= rpc0;
            if (issue) begin
                rpc <= rpc + 1'b1;
                if ({1'b0, rpc} + 11'd1 == limit) running <= 1'b0;
            end
            if (rv1) begin
                if (!word_ok) fault <= 1'b1;
                q[qt] <= {rpc1, captured[W-1:0]}; qt <= qt + 1'b1;
            end
            if (fire) begin
                event_word <= head; event_v <= 1'b1; qh <= qh + 1'b1;
                if (have_last && head[19:0] <= last_time) fault <= 1'b1;
                last_time <= head[19:0]; have_last <= 1'b1;
            end
            if (head_v && head[19:0] < t) fault <= 1'b1;             // late word
            qn <= qn + (rv1 ? 3'd1 : 3'd0) - (fire ? 3'd1 : 3'd0);
            // end of programme: nothing left to read, in flight or queued
            if (busy && !running && !rv0 && !rv1 && (qn == 0 || (qn == 1 && fire)) && !issue) begin
                busy <= 1'b0; done <= 1'b1;
            end
            active <= busy;
            if (cfg_we_q && (busy || start_v_q)) fault <= 1'b1;
            if (start_v_q) begin
                if (busy || cfg_we_q || !legal_start) fault <= 1'b1;
                else begin running <= 1'b1; busy <= 1'b1; rpc <= start_base_q; limit <= start_limit_q; t <= 0;
                           have_last <= 1'b0; end
            end
        end
    end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_root_static.sv
`timescale 1ns/1ps
`default_nettype none
// Static HC ROOT engine (HBM-B-RTL2, plan (b) d4g, 2026-10-17), die master hc_eng (centre).  Successor of the
// single-block ot_hbm_hc_eng_static for the per-quadrant die: the projection datapath (8 bank tiles x 256 lanes) moves
// into 4 quarter engines ot_hbm_hc_qeng_static (hc_eng_<q>, 64 lanes x 8 banks each, beside the quadrant's hc_<q>),
// and this root keeps everything else of the full engine unchanged:
//   PROGRAMME  the folded F20 programme + table targets and ot_hbm_hc_eng_seq_static__d4g_hc (same event word layout; the
//              ingest event is forwarded to quarter e_ingq with its wave index now QUARTER-LOCAL, 0 .. K/1024 - 1).
//   CORE       ot_hdc_v41x_hcp_sys1_static__d4g_hc W = 256 SYS = 1 with TPRE = 6: issue, descriptor (tap 0 -> the 4 quarters,
//              lane count clamped per quarter), the last 2 levels of the chunk tree over the 4 quarter subtree sums
//              ((q0 + q1) + (q2 + q3): the PARTIAL-SUM TREE ROOT), the run tail, raw FIFO, scalar r unit, raw * r.
//   MIX STORE, TABLE, 2 TAIL UNITS, RESULT PINS, GATHERED-MIX ports: as in ot_hbm_hc_eng_static.
// Cross-quadrant traffic per quarter: 29-b descriptor + 39-b ingest event out, 34-b subtree sum in (was 8,192-b chunk
// sums + 8,192-b waves into one block).
// LATENCY vs ot_hbm_hc_eng_static (compiler constants, lanes/HBM-B-RTL2.md):
//   raw accumulation arrival (RAW0) +DRAW = 4 + XRD + XRU + 6 TLA - 18 edges (+28 at XRD = XRU = 0, TLA = 7);
//   pops / tail launches / emits move by the same DRAW; the ingest event must fire 2 + XRD edges before the wave
//   cadence of the full engine (event -> root out flop -> [XRD relays] -> quarter pin flop); the 4 quarters land in
//   parallel (no one-wave-an-edge stagger).
// STATIC: no ready, credit or backpressure.  New fault: a quarter subtree sum not on its due edge (ps_v != expected).
// Pin registers: every input lands in a pin flop, every output is a flop; rst_n through ot_rst_relay__d4g_hc.
// MUT (bench): 2 = tail pre-sigmoid eps dropped (unit 0).
module ot_hbm_hc_root_static #(
    parameter integer K    = 20480,
    parameter [31:0]  NF   = 32'h46a00000,       // binary32(K)
    parameter integer XRD  = 0,                  // die relay stages root -> quarter (descriptor + ingest event)
    parameter integer XRU  = 0,                  // die relay stages quarter -> root (subtree sums)
    parameter integer QDRLY = 1,                 // quarter's centre <-> bank relays (ot_hbm_hc_qeng_static DRLY)
    parameter integer QCHX = 0,                  // HH-9 10-19: quarter bank-chain pin-register edges (qeng CPR 1 -> 11)
    parameter integer TLA  = 7,                  // quarter tree adder stages
    parameter integer MUT  = 0
)(
    input  wire           clk, rst_n,
    // F20 programme bus (folded targets: programme id tgt, table id tgt + 1)
    input  wire [7:0]     tgt,
    input  wire           cfg_v,
    input  wire [7:0]     cfg_target,
    input  wire [11:0]    cfg_addr,
    input  wire [255:0]   cfg_data,
    input  wire           desc_v,
    input  wire [11:0]    desc_base,
    input  wire [12:0]    desc_limit,
    input  wire [15:0]    desc_loops,
    input  wire           launch_v,
    output wire           configured,
    // quarter engines hc_eng_<q> (q = 0..3 = SW, SE, NW, NE)
    output reg  [3:0]     qd_v, qd_ss,
    output reg  [27:0]    qd_nv,
    output reg  [39:0]    qd_wa, qd_xa,
    output reg  [3:0]     qi_v, qi_kind,
    output reg  [7:0]     qi_slot,
    output reg  [19:0]    qi_lo, qi_w,
    output reg  [47:0]    qi_cnt,
    output reg  [39:0]    qi_word,
    input  wire [3:0]     qps_v,
    input  wire [127:0]   qps,
    input  wire [3:0]     qps_f,
    input  wire [3:0]     q_fault,
    // quadrant clients hc_<q>
    input  wire [3:0]     gathered_mix_v,
    input  wire [19:0]    gathered_mix_row,
    input  wire [11:0]    gathered_mix_pos,
    input  wire [127:0]   gathered_mix_data,
    output reg  [3:0]     result_v,
    output reg  [11:0]    result_position,
    output reg  [3071:0]  result,
    output reg            program_active, program_done, fault
);
    localparam integer W = 256, AW = 10, R = K / (8 * W);
    localparam integer LM = 8, LA = 7, SOR = 1, ML = 2;
    localparam integer SYS_LAT0 = 1 + 7 * (LA + 1 + SOR) + 3 + 2 + (ML - 2) + LM + LA + SOR + 2 * QDRLY + QCHX;
    // d0 -> root out flop -> XRD -> quarter pin flop -> chain (SYS_LAT0) -> 6 tree levels -> quarter out flop -> XRU
    // -> root pin flop
    localparam integer SYS_LAT = SYS_LAT0 + 1 + XRD + 1 + 6 * TLA + 1 + XRU + 1;
    localparam integer NVW = $clog2(W) + 1;
    initial if (K % (8 * W) != 0 || R > 16) $fatal(1, "K must be a multiple of 2,048, <= 32,768");

    // ------------------------------------------------------------------ synced reset
    wire [1:0] rn;
    ot_rst_relay__d4g_hc #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    wire rst_c = rn[0];

    // ------------------------------------------------------------------ pin registers
    reg [3:0] gv_q; reg [19:0] gr_q; reg [11:0] gp_q; reg [127:0] gd_q;
    reg [3:0] psv_q, psf_q, qf_q; reg [127:0] ps_q;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin gv_q <= 0; psv_q <= 0; psf_q <= 0; qf_q <= 0; end
        else begin gv_q <= gathered_mix_v; psv_q <= qps_v; psf_q <= qps_f; qf_q <= q_fault; end
    always @(posedge clk) begin
        gr_q <= gathered_mix_row; gp_q <= gathered_mix_pos; gd_q <= gathered_mix_data; ps_q <= qps;
    end
    // ------------------------------------------------------------------ folded F20 targets (pin flops inside)
    wire cfg_we, start_v, tbl_we_q, ptgt_fault, ttgt_fault, seq_active;
    wire [9:0] p_addr, start_base, tbl_addr_q; wire [255:0] p_data, tbl_data_q;
    wire [10:0] start_limit; wire [15:0] start_loops;
    ot_static_program_target__d4g_hc #(.PCW(10), .TGT_PIN(1)) u_ptgt (.clk(clk), .rst_n(rst_c), .tgt(tgt), .cfg_v(cfg_v),
        .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
        .program_cfg_we(cfg_we), .program_cfg_addr(p_addr), .program_cfg_data(p_data), .program_start_v(start_v),
        .program_start_base(start_base), .program_start_limit(start_limit), .program_start_loops(start_loops),
        .configured(configured), .fault(ptgt_fault));
    // table target: only its row-write port has a consumer (a table is data; a launch on id tgt + 1 is never issued)
    ot_static_program_target__d4g_hc #(.PCW(10), .TGT_PIN(1)) u_ttgt (.clk(clk), .rst_n(rst_c), .tgt(tgt + 8'd1), .cfg_v(cfg_v),
        .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
        .program_cfg_we(tbl_we_q), .program_cfg_addr(tbl_addr_q), .program_cfg_data(tbl_data_q), .program_start_v(),
        .program_start_base(), .program_start_limit(), .program_start_loops(), .configured(), .fault(ttgt_fault));

    // ------------------------------------------------------------------ programme
    localparam integer EW = 124;
    wire [EW-1:0] ev; wire ev_v; wire [19:0] ev_t; wire seq_done, seq_fault;
    ot_hbm_hc_eng_seq_static__d4g_hc #(.W(EW)) u_seq (.clk(clk), .rst_n(rst_c), .cfg_we(cfg_we), .cfg_addr(p_addr),
        .cfg_data(p_data), .start_v(start_v), .start_base(start_base), .start_limit(start_limit),
        .start_loops(start_loops), .event_word(ev), .event_v(ev_v), .t(ev_t), .active(seq_active), .done(seq_done),
        .fault(seq_fault));
    wire        e_ing   = ev_v && ev[20];
    wire [1:0]  e_ingq  = ev[22:21];
    wire        e_kind  = ev[23];
    wire [1:0]  e_slot  = ev[25:24];
    wire [4:0]  e_lo    = ev[30:26];
    wire [6:0]  e_w     = ev[37:31];
    wire [11:0] e_cnt   = ev[49:38];
    wire [9:0]  e_word  = ev[59:50];
    wire        e_gm    = ev_v && ev[60];
    wire [1:0]  e_gmq   = ev[62:61];
    wire        e_gmo   = ev[63];
    wire        e_launch= ev_v && ev[64];
    wire [3:0]  e_npos  = ev[68:65];
    wire [1:0]  e_wslot = ev[70:69];
    wire [31:0] e_eps   = ev[102:71];
    wire        e_pop   = ev_v && ev[103];
    wire        e_clear = ev_v && ev[104];
    wire        e_tf    = ev_v && ev[105];
    wire [6:0]  e_tset  = ev[112:106];
    wire        e_tl    = ev_v && ev[113];
    wire        e_tunit = ev[114];
    wire [2:0]  e_tpos  = ev[117:115];
    wire        e_emit  = ev_v && ev[118];
    wire [3:0]  e_qmask = ev[122:119];
    wire        e_eunit = ev[123];

    // ------------------------------------------------------------------ ingest event -> quarter e_ingq (out flops)
    always @(posedge clk or negedge rst_c)
        if (!rst_c) qi_v <= 4'd0; else qi_v <= e_ing ? (4'd1 << e_ingq) : 4'd0;
    always @(posedge clk) if (e_ing) begin
        qi_kind[e_ingq] <= e_kind; qi_slot[e_ingq*2 +: 2] <= e_slot; qi_lo[e_ingq*5 +: 5] <= e_lo;
        qi_w[e_ingq*5 +: 5] <= e_w[4:0]; qi_cnt[e_ingq*12 +: 12] <= e_cnt; qi_word[e_ingq*10 +: 10] <= e_word;
    end
    reg ev_fault;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) ev_fault <= 1'b0; else if (e_ing && e_w[6:5] != 2'd0) ev_fault <= 1'b1;   // quarter wave index < 32

    // ------------------------------------------------------------------ HCP core (TPRE = 6: partial-sum tree root)
    wire sd_v, sd_ss; wire [NVW-1:0] sd_nv; wire [AW-1:0] sd_wa, sd_xa;
    wire o_valid, o_last, core_fault, core_idle; wire [2:0] o_pos; wire [4:0] o_idx; wire [31:0] o_data;
    ot_hdc_v41x_hcp_sys1_static__d4g_hc #(.W(W), .TL(4), .PMAX(8), .OMAX(32), .AW(AW), .CW(16), .ML(ML), .DF(32),
        .STATIC_CALENDAR(1), .SYS(1), .SYS_LAT(SYS_LAT), .TPRE(6)) u_core (
        .clk(clk), .reduction_clk(clk), .scalar_clk(clk), .rst_n(rst_c), .calendar_pop(e_pop),
        .cmd_valid(e_launch), .cmd_ready(), .cmd_npos(e_npos), .cmd_nout(6'd24), .cmd_nchunk(16'(K / 8)),
        .cmd_scale(1'b1), .cmd_nf(NF), .cmd_eps(e_eps), .cmd_wbase(AW'({e_wslot, 8'd0})), .cmd_xbase({AW{1'b0}}),
        .w_re(), .x_re(), .w_addr(), .x_addr(), .w_data({(8*W*32){1'b0}}), .x_data({(8*W*16){1'b0}}),
        .o_valid(o_valid), .o_ready(1'b1), .o_pos(o_pos), .o_idx(o_idx), .o_data(o_data), .o_last(o_last),
        .fault(core_fault), .idle(core_idle),
        .sd_v(sd_v), .sd_ss(sd_ss), .sd_nv(sd_nv), .sd_wa(sd_wa), .sd_xa(sd_xa), .sys_sum(ps_q), .sys_fault(|psf_q));
    // descriptor -> the 4 quarters (out flops); quarter q's lanes are 64q .. 64q + 63 of the run
    always @(posedge clk or negedge rst_c) if (!rst_c) qd_v <= 4'd0; else qd_v <= {4{sd_v}};
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) begin
        qd_ss[q] <= sd_ss; qd_wa[q*10 +: 10] <= sd_wa; qd_xa[q*10 +: 10] <= sd_xa;
        qd_nv[q*7 +: 7] <= (sd_nv <= NVW'(64 * q)) ? 7'd0 : (sd_nv >= NVW'(64 * q + 64)) ? 7'd64 : 7'(sd_nv - NVW'(64 * q));
    end
    // the subtree sums of the task issued SYS_LAT edges ago must be in the pin flops now (all 4 quarters)
    reg [SYS_LAT-1:0] xv; reg ps_fault;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin xv <= 0; ps_fault <= 1'b0; end
        else begin
            xv <= {xv[SYS_LAT-2:0], sd_v};
            if (psv_q != {4{xv[SYS_LAT-1]}}) ps_fault <= 1'b1;
        end

    // ------------------------------------------------------------------ mix store
    reg [8*24*32-1:0] mixes; reg [191:0] have; reg mix_fault; reg [3:0] gm_open;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin have <= 0; mix_fault <= 0; gm_open <= 0; end
        else begin
            if (e_clear) have <= 0;
            if (e_gm) gm_open[e_gmq] <= e_gmo;
            if (o_valid) begin
                if (o_idx >= 5'd24) mix_fault <= 1'b1;
                else begin mixes[(o_pos*24 + o_idx)*32 +: 32] <= o_data; have[o_pos*24 + o_idx] <= 1'b1; end
            end
            for (integer q = 0; q < 4; q = q + 1) if (gv_q[q]) begin
                if (!gm_open[q] || gr_q[q*5 +: 5] >= 5'd24) mix_fault <= 1'b1;
                else begin
                    mixes[(gp_q[q*3 +: 3]*24 + gr_q[q*5 +: 5])*32 +: 32] <= gd_q[q*32 +: 32];
                    have[gp_q[q*3 +: 3]*24 + gr_q[q*5 +: 5]] <= 1'b1;
                end
            end
        end
    end

    // ------------------------------------------------------------------ bases/scales table
    reg [2:0] tf_cnt; reg [6:0] tf_set; reg [1:0] tf_row_q; reg tf_rd_q; reg [895:0] hold; reg tbl_fault;
    wire [255:0] tbl_rd;
    wire tf_rd = tf_cnt != 3'd0;
    wire [1:0] tf_row = 2'(4 - tf_cnt);
    ot_sram_1r1w_1024x256_m2_r2c2 u_tbl (.clk(clk), .r_ce_in(tf_rd), .r_addr_in({1'b0, tf_set, tf_row}),
        .rd_out(tbl_rd), .w_ce_in(tbl_we_q && !seq_active), .w_addr_in(tbl_addr_q), .wd_in(tbl_data_q),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin tf_cnt <= 0; tf_rd_q <= 0; tbl_fault <= 0; end
        else begin
            tf_rd_q <= tf_rd; tf_row_q <= tf_row;
            if (tf_rd) tf_cnt <= tf_cnt - 1'b1;
            if (e_tf) begin if (tf_rd) tbl_fault <= 1'b1; tf_cnt <= 3'd4; tf_set <= e_tset; end
            if (tbl_we_q && seq_active) tbl_fault <= 1'b1;
        end
    end
    always @(posedge clk) if (tf_rd_q) hold[tf_row_q*224 +: 224] <= tbl_rd[223:0];   // row payload (F20 header off)
    // set layout: base i = row i/7 word i%7 = hold word i (i < 24); scale j = row 3 word 3 + j = hold word 24 + j
    wire [767:0] t_bases = hold[767:0]; wire [95:0] t_scales = hold[863:768];

    // ------------------------------------------------------------------ tail units
    wire [1:0] tv, tfl; wire [1535:0] tres; reg [2:0] tpos [0:1]; reg [1:0] tready; reg tail_fault;
    genvar gu;
    for (gu = 0; gu < 2; gu = gu + 1) begin : g_tail
        wire go = e_tl && e_tunit == gu;
        ot_hbm_hc_tail_unit_static__d4g_hc #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0)) u_t (.clk(clk), .rst_n(rst_c),
            .launch(go), .mixes(mixes[e_tpos*768 +: 768]), .bases(t_bases), .scales(t_scales),
            .result_v(tv[gu]), .result(tres[gu*768 +: 768]), .fault(tfl[gu]));
    end
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin tready <= 0; tail_fault <= 0; end
        else begin
            for (integer u = 0; u < 2; u = u + 1) begin
                if (tv[u]) tready[u] <= 1'b1;
                if (e_tl && e_tunit == u) begin tready[u] <= 1'b0; tpos[u] <= e_tpos; end
            end
            if (e_tl && have[e_tpos*24 +: 24] != 24'hffffff) tail_fault <= 1'b1;
            if (e_emit && !tready[e_eunit]) tail_fault <= 1'b1;
        end
    end

    // ------------------------------------------------------------------ result pins (all flops)
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) result_v <= 4'd0;
        else result_v <= e_emit ? e_qmask : 4'd0;
    end
    always @(posedge clk) if (e_emit) for (integer q = 0; q < 4; q = q + 1) if (e_qmask[q]) begin
        result_position[q*3 +: 3] <= tpos[e_eunit]; result[q*768 +: 768] <= tres[e_eunit*768 +: 768];
    end

    // ------------------------------------------------------------------ status
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin fault <= 0; program_active <= 0; program_done <= 0; end
        else begin
            program_active <= seq_active; program_done <= seq_done;
            if (seq_fault || ev_fault || ps_fault || (|qf_q) || core_fault || mix_fault || tbl_fault || tail_fault ||
                (|tfl) || ptgt_fault || ttgt_fault) fault <= 1'b1;
        end
    end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_tail_unit_static.sv
`timescale 1ns/1ps
`default_nettype none
// HC tail unit (H-NETLIST/hceng 2026-10-16): the exact codex tail ot_hgi_hc_tail_static__d4g_hc (sigmoid pre/post + exp +
// Sinkhorn ITERS 20, a35449ada, unchanged) with its Sinkhorn clock derived here and a FIXED launch->result latency.
//   sink clock: one rising edge every SDIV core edges (free-running divider from reset; ot_hdc_sinkhorn_mc pattern,
//               the derived clock is synchronous to clk: a generated clock /SDIV for sign-off).
//   schedule  : launch at core edge t0 (mixes/bases/scales captured by the tail); the tail's e_ready is age 197;
//               sink_launch is held for exactly one sink period starting at the first divider wrap edge with
//               age >= 198 (one sink edge samples it); sink_capture CAP edges after that wrap edge;
//               result_v / result are presented at t0 + L (L = 198 + SDIV + CAP + 2), independent of the divider
//               phase: the earlier capture is held in the tail's own result register. No ready, busy or response
//               signal moves any event; a capture without the Sinkhorn's out_valid faults (tail contract).
module ot_hbm_hc_tail_unit_static__d4g_hc #(
    parameter integer SDIV = 7,
    parameter integer CAP  = 289,
    parameter integer MUT_PRE = 0,
    parameter integer L = 198 + SDIV + CAP + 2
)(
    input  wire          clk, rst_n,
    input  wire          launch,
    input  wire [767:0]  mixes, bases,
    input  wire [95:0]   scales,
    output reg           result_v,
    output wire [767:0]  result,
    output wire          fault
);
    localparam integer CW = $clog2(SDIV);
    reg [CW-1:0] cnt; reg sclk;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cnt <= 0; sclk <= 1'b0; end
        else begin cnt <= (cnt == SDIV - 1) ? {CW{1'b0}} : cnt + 1'b1; sclk <= (cnt == SDIV - 1); end
    wire wrap = (cnt == SDIV - 1);                 // the edge on which sclk rises
    reg active, sl, armed; reg [9:0] age, sage;
    wire tv; wire tf;
    reg capture_q;
    ot_hgi_hc_tail_static__d4g_hc #(.MUT_PRE(MUT_PRE)) u_tail (.clk(clk), .sink_clk(sclk), .rst_n(rst_n), .launch(launch),
        .mixes(mixes), .bases(bases), .scales(scales), .sink_launch(sl), .sink_capture(capture_q),
        .e_ready(), .result_v(tv), .result(result), .fault(tf));
    reg own_fault, captured;
    assign fault = own_fault | tf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin active <= 0; sl <= 0; armed <= 0; age <= 0; sage <= 0; capture_q <= 0; result_v <= 0;
                          own_fault <= 0; captured <= 0; end
        else begin
            capture_q <= 1'b0; result_v <= 1'b0;
            if (active) age <= age + 1'b1;
            if (launch) begin
                if (active) own_fault <= 1'b1;
                active <= 1'b1; age <= 10'd1; armed <= 1'b0; captured <= 1'b0;
            end
            // sink launch window: set on the first wrap edge at age >= 198, cleared on the next wrap edge
            if (active && !armed && age >= 10'd198 && wrap) begin sl <= 1'b1; armed <= 1'b1; sage <= 10'd1; end
            else if (sl && wrap) sl <= 1'b0;
            if (armed && !captured) begin
                sage <= sage + 1'b1;
                if (sage == 10'(CAP)) begin capture_q <= 1'b1; captured <= 1'b1; end
            end
            if (active && age == 10'(L - 1)) begin
                result_v <= 1'b1; active <= 1'b0;
                if (!captured) own_fault <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hdc_v41x_hcp_sys1_static.sv
// SYS1 source partition successor. All roots are frequency-locked; phase/reach
// remain physical obligations. No asynchronous FIFO or timing waiver is implied.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection projection engine (HCP) of the re-specified DeepSeek-V4.1
// decode die: docs/ARCH_SPEC_V41.md section 6 item 7, gap-table row
// "hyper-connection projection" (2,048 FP32 MAC lanes).
//
// FUNCTION (tools/hdc_golden_v41.py Model.hc_mixes under R-ARITH "chunk8").
// Per position p, with flat = the BF16 4-copy residual (K = 4 x dim elements)
// and fn the [nout, K] binary32 projection:
//   ss      = csum(mul(flat, flat))                        (the norm's sum of squares)
//   r       = rsqrt(add(div(ss, nf), eps))                  (hdc_golden rsqrt: magic + 3 Newton steps)
//   mix[o]  = mul(csum(mul(fn[o, :], flat)), r)             (o = 0 .. nout-1)
// csum = chunks of 8 contiguous terms summed sequentially from +0, the chunk
// sums added by a pairwise tree padded with +0.  Every operation is one
// binary32 op of rtl/hdc/ot_hdc_fastfp.sv (3-stage add / multiply, RNE,
// gradual underflow, canonical +0) or the IEEE divider ot_hdc_fdiv__d4g_hc.  With
// cmd_scale = 0 the engine returns the raw csum dot products (mix[o] =
// csum(...) exactly; the ss task and the scale are skipped).
//
// LANES.  8 groups x W lanes = 8W FP32 MAC lanes (W = 256: 2,048).  A lane is
// one multiplier feeding one adder whose sum re-enters exactly 3 cycles later
// (the add latency), so a lane interleaves 3 chunk accumulations ("slots") and
// retires one multiply-add per cycle.  A TASK is one aligned run of W chunks
// (8W terms) of one accumulation (position p, row o, run r): the W lanes of a
// group each own one chunk of the run.  One task issues per cycle.  Task n
// (issued in cycle n) belongs to group (n div 3) mod 8, slot n mod 3, and its
// term k (k = 0 .. 7) is multiplied in cycle n + 3k (plus a fixed offset): so
// every lane is busy every cycle, the 8 groups are always at 8 DIFFERENT terms
// k, and the chunk sums of exactly one task complete per cycle.
//
// MEMORIES (outside the engine; fixed read latency ML cycles from the
// registered address to the data at the input port, no handshake).  Both are
// banked by term k, so the 8 groups never conflict:
//   weight bank k, word wbase + o*R + r, lane l:  fn[o][8*(r*W + l) + k]      (binary32)
//   x      bank k, word xbase + p*R + r, lane l:  flat_p[8*(r*W + l) + k]     (BF16)
// with R = ceil(nchunk / W) runs, nchunk = K/8, words past the vector ignored
// (lanes l >= nchunk - r*W of the last run are masked to +0 operands).  Bank k
// in cycle c serves the task issued in cycle c - 3k; its data is rotated to
// that task's group (a one-hot AND-OR by the group field the task carries).
//
// REDUCTION, exactly the csum tree.  The W chunk sums of a task enter a
// pipelined pairwise tree of log2(W) adder levels: that is the csum subtree of
// an aligned run of W chunks.  The run sums of one accumulation (r = 0 .. R-1)
// enter the TAIL: TL levels, level l holding one pending left sibling.  At
// level l an event with bit l of r set adds the stored sibling and moves up;
// with bit l clear it is stored and stops -- unless it is the accumulation's
// last run, whose right sibling is all padding, so it moves up unchanged
// (added to +0).  Every addition is the tree's own pair, so the result is
// csum's padded tree bit for bit (padding past pow2(nchunk) only adds +0).
// Requires R <= 2^TL (fault otherwise) and K a multiple of 8.
//
// ORDER.  Positions p = 0 .. npos-1; per position the ss task run (if
// cmd_scale) then rows o = 0 .. nout-1, each its R runs.  Raw sums enter a
// DF-entry FIFO; issue reserves an entry per accumulation (credit), so the
// engine never drops a result.  The scalar unit turns ss into r (one fdiv,
// one add, one multiply, sequenced: ~90 cycles per position, while the rows
// of that position accumulate), and each raw row sum leaves through one
// multiplier as mix = raw * r (raw * 1.0 = raw when cmd_scale = 0).
//
// PROTOCOL.  cmd_valid/cmd_ready: one command at a time (cmd_ready rises again
// after the command's last result is accepted).  o_valid/o_ready: results in
// (p, o) order, o_last on the command's final result.  Every output is a flop;
// every input is registered before use.  fault (sticky per command): a
// nonfinite operand or overflow anywhere, a divide fault, or R > 2^TL.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_hcp_sys1_static__d4g_hc #(
    parameter integer W    = 8,         // lanes per group (power of two >= 2); lanes = 8W (spec: W = 256)
    parameter integer TL   = 9,         // tail levels: runs per accumulation R <= 2^TL (spec: 4)
    parameter integer PMAX = 8,         // positions per command (power of two)
    parameter integer OMAX = 32,        // rows per position (power of two)
    parameter integer AW   = 16,        // bank word address width
    parameter integer CW   = 16,        // chunk-count width (nchunk = K/8)
    parameter integer ML   = 2,         // memory read latency
    parameter integer DF   = 32,        // raw-result FIFO depth (power of two)
    // el1011-hcvm-hc SYSTOLIC lanes (opt-in, default off; cycles change): SYS = 1 builds no lane groups and no bank
    // rotation.  The 8W lanes live outside in 8 bank stages (ot_hdc_v41x_hcp_stage__d4g_hc, one per bank, chained): the task
    // descriptor leaves on sd_* (tap 0), stage k multiplies term k from its OWN bank and adds it to the partial chunk
    // sum of stage k - 1 (stage 0 adds to +0), so csum's chunk order ((0 + t0) + t1) .. + t7 is kept op for op; stage
    // 7's W chunk sums come back on sys_sum SYS_LAT cycles after tap 0 (the tree leaves at tap SYS_LAT + 1).
    parameter integer STATIC_CALENDAR = 0, // compiler schedules all raw reads; no credit/ready gating
    parameter integer SYS  = 0,
    parameter integer SYS_LAT = 0,
    // HBM-B-RTL2 (plan (b) d4g, 2026-10-17; default 0 = unchanged): SYS = 1 with TPRE > 0 takes sys_sum already reduced
    // by the first TPRE levels of the pairwise chunk tree (outside, in the 4 quarter engines ot_hbm_hc_qeng_static):
    // sys_sum carries W >> TPRE aligned subtree sums (leaf i = lanes i*2^TPRE .. +2^TPRE-1), the internal tree only
    // builds the remaining LW - TPRE levels, and SYS_LAT counts to the arrival of those subtree sums.  Same pairs, same
    // order, so the run sums are bit-identical to TPRE = 0.
    parameter integer TPRE = 0,
    parameter integer PW   = (PMAX > 1) ? $clog2(PMAX) : 1,
    parameter integer OXW  = (OMAX > 1) ? $clog2(OMAX) : 1
) (
    input  wire              clk, // command / descriptor root
    input wire reduction_clk, scalar_clk,
    input  wire              rst_n,
    input  wire              calendar_pop, // STATIC_CALENDAR: reserved raw-accumulator read slot
    // command
    input  wire              cmd_valid,
    output reg               cmd_ready,
    input  wire [PW:0]       cmd_npos,          // 1 .. PMAX
    input  wire [OXW:0]      cmd_nout,          // 1 .. OMAX
    input  wire [CW-1:0]     cmd_nchunk,        // K / 8, >= 1
    input  wire              cmd_scale,
    input  wire [31:0]       cmd_nf,            // binary32 of K (the mean's divisor)
    input  wire [31:0]       cmd_eps,
    input  wire [AW-1:0]     cmd_wbase,
    input  wire [AW-1:0]     cmd_xbase,
    // weight banks (binary32) and x banks (BF16), bank k at [k*...]
    output reg  [7:0]        w_re,
    output reg  [8*AW-1:0]   w_addr,
    input  wire [8*W*32-1:0] w_data,
    output reg  [7:0]        x_re,
    output reg  [8*AW-1:0]   x_addr,
    input  wire [8*W*16-1:0] x_data,
    // results
    output reg               o_valid,
    input  wire              o_ready,
    output reg  [PW-1:0]     o_pos,
    output reg  [OXW-1:0]    o_idx,
    output reg  [31:0]       o_data,
    output reg               o_last,
    output reg               fault,
    output reg               idle,
    // SYS = 1: the descriptor to stage 0, the chunk sums and lane faults back from stage 7
    output wire              sd_v,
    output wire              sd_ss,
    output wire [$clog2(W):0] sd_nv,
    output wire [AW-1:0]     sd_wa,
    output wire [AW-1:0]     sd_xa,
    input  wire [(W>>TPRE)*32-1:0] sys_sum,
    input  wire              sys_fault
);
    localparam integer LW  = $clog2(W);
    localparam integer NVW = LW + 1;
    localparam integer LWT = LW - TPRE;               // tree levels built here
    localparam integer NL  = W >> TPRE;               // tree leaves
    localparam integer DFW = $clog2(DF);
    // descriptor fields
    localparam integer F_V   = 0;
    localparam integer F_SS  = 1;
    localparam integer F_LR  = 2;                 // last run
    localparam integer F_GRP = 3;                 // 3 bits
    localparam integer F_NV  = 6;                 // NVW bits
    localparam integer F_WA  = F_NV + NVW;
    localparam integer F_XA  = F_WA + AW;
    localparam integer F_POS = F_XA + AW;
    localparam integer F_IDX = F_POS + PW;
    localparam integer F_R   = F_IDX + OXW;       // TL low bits of the run index
    localparam integer F_LO  = F_R + TL;          // last output of the command
    localparam integer DW    = F_LO + 1;
    // pipeline taps (descriptor delay-line index of the task a stage holds)
    localparam integer T_OP   = 21 + ML + 3;                 // group operands of term 7
    localparam integer T_LEAF = SYS ? SYS_LAT + 1 : 31 + ML; // tree leaves
    localparam integer T_TAIL = T_LEAF + 3 * LWT;             // tree output = tail level 0 input
    localparam integer NDL    = T_TAIL + 3 * TL + 1;

    genvar gk, gg, gl, gv;
    integer i;

    // ------------------------------------------------------------------ command / issue
    reg              busy, active;
    reg [PW:0]       npos_r;
    reg [OXW:0]      nout_r;
    reg [CW-1:0]     nrun_r, nlast_r;              // runs per accumulation; lanes of the last run
    reg              scale_r;
    reg [31:0]       nf_r, eps_r;
    reg [PW-1:0]     p;
    reg [OXW-1:0]    o;
    reg              ssph;
    reg [CW-1:0]     r;
    reg [AW-1:0]     wbase_r, wcur, xpos;
    reg [4:0]        ph24;                          // free-running cycle mod 24
    reg [DFW:0]      acc_cnt;                       // accumulations reserved, not yet popped
    wire             pop_raw;
    wire [CW-1:0]    nrun_c = (cmd_nchunk + W - 1) >> LW;
    wire             first_r = (r == 0);
    wire             last_r = (r == nrun_r - 1'b1);
    wire             credit = (acc_cnt < DF);
    wire             iss = active && (STATIC_CALENDAR || !first_r || credit);
    wire             accept_cmd = STATIC_CALENDAR ? cmd_valid : (cmd_valid && cmd_ready);
    wire             last_o = ssph ? 1'b0 : ({1'b0, o} == nout_r - 1'b1);
    wire             last_p = ({1'b0, p} == npos_r - 1'b1);
    reg  [DW-1:0]    d0;
    wire             tl_over_c = (nrun_c > (1 << TL));
    localparam [NVW-1:0] WNV = W;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; active <= 1'b0; cmd_ready <= 1'b0; ph24 <= 5'd0; acc_cnt <= 0;
        end else begin
            ph24 <= (ph24 == 5'd23) ? 5'd0 : ph24 + 5'd1;
            cmd_ready <= !busy && !(accept_cmd);
            if (!STATIC_CALENDAR) acc_cnt <= acc_cnt + (iss && first_r) - pop_raw;
            if (accept_cmd) begin
                busy <= 1'b1; active <= 1'b1;
            end else if (iss && last_r && last_o && last_p) begin
                active <= 1'b0;
            end
            if (o_valid && (STATIC_CALENDAR || o_ready) && o_last) busy <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (accept_cmd) begin
            npos_r <= cmd_npos; nout_r <= cmd_nout; scale_r <= cmd_scale;
            nrun_r <= nrun_c; nlast_r <= ((cmd_nchunk - 1'b1) & (W - 1)) + 1'b1;
            nf_r <= cmd_nf; eps_r <= cmd_eps; wbase_r <= cmd_wbase;
            p <= 0; o <= 0; r <= 0; ssph <= cmd_scale; wcur <= cmd_wbase; xpos <= cmd_xbase;
        end else if (iss) begin
            if (!last_r) r <= r + 1'b1;
            else begin
                r <= 0;
                if (ssph) ssph <= 1'b0;
                else if (!last_o) o <= o + 1'b1;
                else begin
                    o <= 0; p <= p + 1'b1; ssph <= scale_r; wcur <= wbase_r; xpos <= xpos + nrun_r;
                end
            end
            if (!ssph && !(last_r && last_o)) wcur <= wcur + 1'b1;
        end
        // the task descriptor entering the delay line (a bubble still carries its group)
        d0 <= {DW{1'b0}};
        d0[F_V] <= iss;
        d0[F_SS] <= ssph;
        d0[F_LR] <= last_r;
        d0[F_GRP +: 3] <= ph24 / 3;
        d0[F_NV +: NVW] <= last_r ? nlast_r[NVW-1:0] : WNV;
        d0[F_WA +: AW] <= wcur;
        d0[F_XA +: AW] <= xpos + r;
        d0[F_POS +: PW] <= p;
        d0[F_IDX +: OXW] <= o;
        d0[F_R +: TL] <= r[TL-1:0];
        d0[F_LO] <= !ssph && last_o && last_p;
    end
    // delay line: dl[i] = d0 delayed i cycles (dl[0] = d0); the valid bit is reset
    reg  [NDL-1:0]        dlv;                      // valid bits (reset)
    reg  [(DW-1)*NDL-1:0] dld;                      // the other fields (no reset)
    wire [DW*(NDL+1)-1:0] dl;
    assign dl[DW-1:0] = d0;
    generate for (gv = 0; gv < NDL; gv = gv + 1) begin : g_dl
        assign dl[DW*(gv+1) +: DW] = {dld[(DW-1)*gv +: DW-1], dlv[gv]};
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) dlv <= {NDL{1'b0}};
        else for (i = 0; i < NDL; i = i + 1) dlv[i] <= dl[DW*i + F_V];
    end
    always @(posedge clk)
        for (i = 0; i < NDL; i = i + 1) dld[(DW-1)*i +: DW-1] <= dl[DW*i + 1 +: DW-1];

    // ------------------------------------------------------------------ bank addresses (term k at tap 3k)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w_re <= 8'd0; x_re <= 8'd0; end
        else for (i = 0; i < 8; i = i + 1) begin
            w_re[i] <= dl[DW*(3*i) + F_V] && !dl[DW*(3*i) + F_SS];
            x_re[i] <= dl[DW*(3*i) + F_V];
        end
    end
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1) begin
            w_addr[AW*i +: AW] <= dl[DW*(3*i) + F_WA +: AW];
            x_addr[AW*i +: AW] <= dl[DW*(3*i) + F_XA +: AW];
        end

    reg [NL*32-1:0] leaf;
    reg            leaf_v;
    wire           lane_fault_any;
    assign sd_v = d0[F_V]; assign sd_ss = d0[F_SS]; assign sd_nv = d0[F_NV +: NVW]; assign sd_wa = d0[F_WA +: AW];
    assign sd_xa = d0[F_XA +: AW];
    initial if (TPRE != 0 && (SYS == 0 || TPRE >= LW)) $fatal(1, "TPRE needs SYS = 1 and TPRE < log2(W)");
    generate if (SYS == 0) begin : g_flat
    // ------------------------------------------------------------------ input registers
    reg [8*W*32-1:0] w_in;
    reg [8*W*16-1:0] x_in;
    always @(posedge clk) begin
        w_in <= w_data;
        x_in <= x_data;
    end

    // ------------------------------------------------------------------ rotation to groups, masking
    // bank k's input register holds the task at tap 3k + 2 + ML
    wire [63:0] sel;                                  // sel[8g + k]
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_sel
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_k
            //: qualified by the task's valid bit: a bubble's group field may be stale (the delay line's data
            //: bits carry no reset), and only valid tasks are guaranteed one per group
            assign sel[8*gg + gk] = dl[DW*(3*gk + 2 + ML) + F_V] && (dl[DW*(3*gk + 2 + ML) + F_GRP +: 3] == gg);
        end
    end

    reg  [7:0]        gfirst, glast;                // first: a = +0 (term 0, or no task)
    reg  [7:0]        gov;                          // the group holds a task's operands
    wire [8*W-1:0]    lane_fault;
    wire [8*W*32-1:0] gsum;
    reg  [7:0]        lastv [0:6];                  // group's last-term flag, delayed 0..6 from gw
    reg  [7:0]        fst   [0:3];                  // group's first flag, delayed 0..3
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_grp
        reg          ov, oss;
        reg [NVW-1:0] onv;
        reg [W*32-1:0] ow;
        reg [W*16-1:0] ox;
        integer k2;
        always @(*) begin
            ov = 1'b0; oss = 1'b0; onv = {NVW{1'b0}}; ow = {(W*32){1'b0}}; ox = {(W*16){1'b0}};
            for (k2 = 0; k2 < 8; k2 = k2 + 1) begin
                ov  = ov  | sel[8*gg + k2];
                oss = oss | (sel[8*gg + k2] & dl[DW*(3*k2 + 2 + ML) + F_SS]);
                onv = onv | ({NVW{sel[8*gg + k2]}} & dl[DW*(3*k2 + 2 + ML) + F_NV +: NVW]);
                ow  = ow  | ({(W*32){sel[8*gg + k2]}} & w_in[W*32*k2 +: W*32]);
                ox  = ox  | ({(W*16){sel[8*gg + k2]}} & x_in[W*16*k2 +: W*16]);
            end
        end
        for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
            wire        lv = ov && (gl < onv);
            wire [31:0] xw = {ox[16*gl +: 16], 16'h0000};
            reg  [31:0] gx, gw;                    // the lane's operands (lane-local registers)
            always @(posedge clk) begin
                gx <= lv ? xw : 32'd0;
                gw <= lv ? (oss ? xw : ow[32*gl +: 32]) : 32'd0;
            end
            // the lane: product, then the 3-slot interleaved accumulation
            wire [31:0] prod, sum;
            wire [1:0]  e0, e1;
            wire        v0, v1;
            ot_hdc_fp32_mul_fast__d4g_hc u_mul (.clk(clk), .rst_n(rst_n), .valid_in(gov[gg]),
                                        .a(gw), .b(gx),
                                        .y(prod), .err(e0), .valid_out(v0));
            ot_hdc_fp32_add_fast__d4g_hc u_add (.clk(clk), .rst_n(rst_n), .valid_in(v0),
                                        .a(fst[2][gg] ? 32'd0 : sum), .b(prod),
                                        .y(sum), .err(e1), .valid_out(v1));
            assign gsum[32*(W*gg + gl) +: 32] = sum;
            //: errors count only on a task's terms (the valid chains ride the units' own pipes)
            assign lane_fault[W*gg + gl] = (v0 && (|e0)) || (v1 && (|e1));
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) gov[gg] <= 1'b0; else gov[gg] <= ov;
        always @(posedge clk) begin
            gfirst[gg] <= sel[8*gg + 0] || !ov;
            glast[gg]  <= sel[8*gg + 7];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 7; i = i + 1) lastv[i] <= 8'd0;
        end else begin
            lastv[0] <= glast;
            for (i = 1; i < 7; i = i + 1) lastv[i] <= lastv[i-1];
        end
    end
    always @(posedge clk) begin
        fst[0] <= gfirst;
        for (i = 1; i < 4; i = i + 1) fst[i] <= fst[i-1];
    end
    //: fst[2] is the first flag of the term whose product the adder takes now;
    //: lastv[5] marks the group whose adder output is a finished chunk sum.
    wire [7:0] done_g = lastv[5];

    // ------------------------------------------------------------------ tree over the W chunk sums
    integer g3;
    always @(posedge clk) begin
        leaf <= {(W*32){1'b0}};
        for (g3 = 0; g3 < 8; g3 = g3 + 1)
            if (done_g[g3]) leaf <= gsum[W*32*g3 +: W*32];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= |done_g;
    end
    assign lane_fault_any = |lane_fault;
    end else begin : g_sys
    // the stage chain is outside: stage 7's chunk sums of the task at tap T_LEAF - 1 arrive on sys_sum now
    always @(posedge reduction_clk) leaf <= dl[DW*(T_LEAF-1) + F_V] ? sys_sum : {(NL*32){1'b0}};
    always @(posedge reduction_clk or negedge rst_n)
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= dl[DW*(T_LEAF-1) + F_V];
    assign lane_fault_any = sys_fault;
    end endgenerate
    wire [31:0] root;
    wire        tree_fault;
    wire        tree_vo;
    ot_hdc_v41x_addtree__d4g_hc #(.N(NL)) u_tree (.clk(reduction_clk), .rst_n(rst_n), .v(leaf_v), .x(leaf), .y(root), .vo(tree_vo),
                                         .fault(tree_fault));
    wire [LWT*3:0] tvv;
    ot_hdc_v41x_vline__d4g_hc #(.D(3*LWT)) u_tvv (.clk(reduction_clk), .rst_n(rst_n), .v(leaf_v), .vd(tvv));

    // ------------------------------------------------------------------ tail: pairwise tree over runs
    wire [32*(TL+1)-1:0] ev_val;
    wire [TL:0]          ev_v;
    wire [TL-1:0]        tail_fault;
    assign ev_val[31:0] = root;
    assign ev_v[0] = tvv[3*LWT];
    generate for (gv = 0; gv < TL; gv = gv + 1) begin : g_tail
        localparam integer TAP = T_TAIL + 3 * gv;
        wire bitl  = dl[DW*TAP + F_R + gv];
        wire lastr = dl[DW*TAP + F_LR];
        wire go    = ev_v[gv] && (bitl || lastr);
        reg [31:0] slot;
        always @(posedge reduction_clk) if (ev_v[gv] && !bitl && !lastr) slot <= ev_val[32*gv +: 32];
        wire [1:0] e;
        ot_hdc_fp32_add_fast__d4g_hc u_a (.clk(reduction_clk), .rst_n(rst_n), .valid_in(go),
                                  .a(bitl ? slot : 32'd0), .b(ev_val[32*gv +: 32]),
                                  .y(ev_val[32*(gv+1) +: 32]), .err(e), .valid_out(ev_v[gv+1]));
        assign tail_fault[gv] = ev_v[gv+1] && (|e);
    end endgenerate
    localparam integer T_RAW = T_TAIL + 3 * TL;
    wire raw_v   = ev_v[TL] && dl[DW*T_RAW + F_LR];
    wire raw_bad = ev_v[TL] && !dl[DW*T_RAW + F_LR];      // R > 2^TL

    // ------------------------------------------------------------------ raw-result FIFO
    localparam integer RQW = 1 + 1 + PW + OXW + 32;       // {last out, ss, pos, idx, value}
    reg  [RQW-1:0] rq [0:DF-1];
    reg  [DFW:0]   rq_wp, rq_rp;
    wire           rq_ne = (rq_wp != rq_rp);
    wire [RQW-1:0] rq_h = rq[rq_rp[DFW-1:0]];
    reg  [RQW-1:0] raw_w;
    reg            raw_wv;
    always @(posedge reduction_clk) begin
        raw_w <= {dl[DW*(T_RAW) + F_LO], dl[DW*(T_RAW) + F_SS], dl[DW*(T_RAW) + F_POS +: PW],
                  dl[DW*(T_RAW) + F_IDX +: OXW], ev_val[32*TL +: 32]};
        if (raw_wv) rq[rq_wp[DFW-1:0]] <= raw_w;
    end
    always @(posedge reduction_clk or negedge rst_n) begin
        if (!rst_n) begin rq_wp <= 0; raw_wv <= 1'b0; end
        else begin
            raw_wv <= raw_v;
            if (raw_wv) rq_wp <= rq_wp + 1'b1;
        end
    end
    wire          h_lo  = rq_h[RQW-1];
    wire          h_ss  = rq_h[RQW-2];
    wire [PW-1:0] h_pos = rq_h[32 + OXW +: PW];
    wire [OXW-1:0] h_idx = rq_h[32 +: OXW];
    wire [31:0]   h_val = rq_h[31:0];

    always @(posedge scalar_clk or negedge rst_n) begin
        if (!rst_n) rq_rp <= 0; else if (pop_raw) rq_rp <= rq_rp + 1'b1;
    end
    // ------------------------------------------------------------------ scalar r unit
    reg  [31:0]     rv [0:PMAX-1];
    reg  [PMAX-1:0] r_ok;
    reg  [3:0]      st;
    reg             pend;
    reg  [1:0]      it;
    reg  [PW-1:0]   rs_pos;
    reg  [31:0]     rs_q, rs_h, rs_y, rs_a;
    localparam [3:0] S_IDLE = 4'd0, S_DIV = 4'd1, S_EPS = 4'd2, S_HALF = 4'd3, S_YY = 4'd4, S_HY = 4'd5,
                     S_SUB = 4'd6, S_MY = 4'd7;
    wire rs_take = STATIC_CALENDAR ? (calendar_pop && h_ss) : (rq_ne && h_ss && (st == S_IDLE));
    // units
    reg         dv, av, mv;
    reg  [31:0] da, db, aa, ab, ma, mb;
    wire [31:0] dy, ay, my;
    wire        dvo, avo, mvo, dfl;
    wire [1:0]  aerr, merr;
    ot_hdc_fdiv__d4g_hc u_div (.clk(scalar_clk), .rst_n(rst_n), .v(dv), .a(da), .b(db), .y(dy), .vo(dvo), .fault(dfl));
    ot_hdc_fp32_add_fast__d4g_hc u_sa (.clk(scalar_clk), .rst_n(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay), .err(aerr),
                               .valid_out(avo));
    ot_hdc_fp32_mul_fast__d4g_hc u_sm (.clk(scalar_clk), .rst_n(rst_n), .valid_in(mv), .a(ma), .b(mb), .y(my), .err(merr),
                               .valid_out(mvo));
    wire rs_fault = (dvo && dfl) || (avo && (|aerr)) || (mvo && (|merr));
    always @(posedge scalar_clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pend <= 1'b0; dv <= 1'b0; av <= 1'b0; mv <= 1'b0; r_ok <= {PMAX{1'b0}};
        end else begin
            dv <= 1'b0; av <= 1'b0; mv <= 1'b0;
            if (accept_cmd) r_ok <= {PMAX{1'b0}};
            case (st)
                S_IDLE: if (rs_take) begin st <= S_DIV; pend <= 1'b0; end
                S_DIV:  if (!pend) begin dv <= 1'b1; pend <= 1'b1; end
                        else if (dvo) begin pend <= 1'b0; st <= S_EPS; end
                S_EPS:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_HALF; end
                S_HALF: if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_YY; end
                S_YY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_HY; end
                S_HY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_SUB; end
                S_SUB:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_MY; end
                S_MY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin
                            pend <= 1'b0;
                            if (it == 2'd2) begin st <= S_IDLE; r_ok[rs_pos] <= 1'b1; end
                            else st <= S_YY;
                        end
                default: st <= S_IDLE;
            endcase
        end
    end
    always @(posedge scalar_clk) begin
        if (st == S_IDLE && rs_take) begin
            rs_pos <= h_pos; da <= h_val; db <= nf_r; it <= 2'd0;
        end
        if (st == S_DIV && pend && dvo) begin aa <= dy; ab <= eps_r; end
        if (st == S_EPS && pend && avo) begin
            ma <= ay; mb <= 32'h3F000000;                         // half = v * 0.5
            rs_y <= 32'h5F3759DF - {1'b0, ay[31:1]};              // y0 from v's bits
        end
        if (st == S_HALF && pend && mvo) begin rs_h <= my; ma <= rs_y; mb <= rs_y; end
        if (st == S_YY && pend && mvo) begin ma <= rs_h; mb <= my; end
        if (st == S_HY && pend && mvo) begin aa <= 32'h3FC00000; ab <= {~my[31], my[30:0]}; end
        if (st == S_SUB && pend && avo) begin ma <= rs_y; mb <= ay; end
        if (st == S_MY && pend && mvo) begin
            rs_y <= my; ma <= my; mb <= my; it <= it + 1'b1;
            if (it == 2'd2) rv[rs_pos] <= my;
        end
    end

    // ------------------------------------------------------------------ output: raw * r
    localparam integer OQ = 8;
    localparam integer OTW = 1 + PW + OXW;
    reg  [3:0]  oinf;                                 // products in flight
    reg  [3:0]  ocnt;
    wire        o_room = ({1'b0, oinf} + {1'b0, ocnt} + {4'd0, o_valid}) < OQ;
    wire        h_ok = !scale_r || r_ok[h_pos];
    wire        take_out = STATIC_CALENDAR ? (calendar_pop && !h_ss) : (rq_ne && !h_ss && h_ok && o_room);
    assign pop_raw = rs_take || take_out;
    reg         ov_in;
    reg  [31:0] oa, ob;
    reg  [OTW-1:0] otag_in;
    wire [31:0] oy;
    wire [1:0]  oerr;
    wire        ovo;
    wire [OTW-1:0] otag;
    ot_hdc_fp32_mul_fast__d4g_hc u_om (.clk(scalar_clk), .rst_n(rst_n), .valid_in(ov_in), .a(oa), .b(ob), .y(oy), .err(oerr),
                               .valid_out(ovo));
    ot_hdc_delay__d4g_hc #(.W(OTW), .D(3)) u_otag (.clk(scalar_clk), .rst_n(rst_n), .d(otag_in), .q(otag));
    reg  [OTW+31:0] oq [0:OQ-1];
    reg  [3:0]      oq_wp, oq_rp;
    wire            oq_ne = (oq_wp != oq_rp);
    wire            o_load = oq_ne && (!o_valid || o_ready);
    generate if (!STATIC_CALENDAR) begin : g_legacy_output
    always @(posedge scalar_clk or negedge rst_n) begin
        if (!rst_n) begin
            ov_in <= 1'b0; oinf <= 4'd0; ocnt <= 4'd0; oq_wp <= 4'd0; oq_rp <= 4'd0; o_valid <= 1'b0;
        end else begin
            ov_in <= take_out;
            oinf <= oinf + {3'd0, take_out} - {3'd0, ovo};
            ocnt <= ocnt + {3'd0, ovo} - {3'd0, o_load};
            if (ovo) oq_wp <= (oq_wp == OQ - 1) ? 4'd0 : oq_wp + 4'd1;
            if (o_load) oq_rp <= (oq_rp == OQ - 1) ? 4'd0 : oq_rp + 4'd1;
            if (o_load) o_valid <= 1'b1;
            else if (o_ready) o_valid <= 1'b0;
        end
    end
    always @(posedge scalar_clk) begin
        if (ovo) oq[oq_wp] <= {otag, oy};
        if (o_load) {o_last, o_pos, o_idx, o_data} <= oq[oq_rp];
    end
    end else begin : g_static_output
        // A reserved read launches one result. No output queue or ready signal
        // can move this event; the compiler reserves its multiplier+flop delay.
        always @(posedge scalar_clk or negedge rst_n) begin
            if (!rst_n) begin ov_in <= 0; o_valid <= 0; end
            else begin ov_in <= take_out; o_valid <= ovo; end
        end
        always @(posedge scalar_clk) if (ovo) {o_last,o_pos,o_idx,o_data} <= {otag,oy};
    end endgenerate
    always @(posedge scalar_clk) if (take_out) begin
        oa <= h_val; ob <= scale_r ? rv[h_pos] : 32'h3F800000; otag_in <= {h_lo,h_pos,h_idx};
    end
    wire calendar_fault = STATIC_CALENDAR && (
        (calendar_pop && (!rq_ne || (h_ss ? (st != S_IDLE) : !h_ok))) ||
        (raw_wv && ((rq_wp - rq_rp) == DF) && !calendar_pop) ||
        (accept_cmd && busy));

    // ------------------------------------------------------------------ fault, idle
    reg lf_r, tf_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; idle <= 1'b1; lf_r <= 1'b0; tf_r <= 1'b0; end
        else begin
            lf_r <= lane_fault_any;
            tf_r <= tree_fault || (|tail_fault) || raw_bad || rs_fault || (ovo && (|oerr));
            if (accept_cmd) fault <= tl_over_c || (STATIC_CALENDAR && busy);
            else if (lf_r || tf_r || calendar_fault) fault <= 1'b1;
            idle <= !busy;
        end
    end
endmodule


// Scoped source: rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_tail_static.sv
`timescale 1ns/1ps
`default_nettype none
// Exact HC sigmoid/Sinkhorn tail on a compiler-fixed calendar. No response,
// ready, occupancy, or busy signal chooses a normal execution cycle.
// launch captures 24 mixes,3 scales,24 bases. Arithmetic issue slots relative
// to launch are fixed below. e_ready marks cycle197 (data already stable).
// Compiler reserves sink_launch on the separate measured slow clock AFTER
// e_ready, then sink_capture in the core domain when the 41st Sinkhorn edge
// has completed (ITERS20). Input/output arrays stay stable across this interval.
// Any missed arithmetic tag/capture contract faults without delaying work.
module ot_hgi_hc_tail_static__d4g_hc #(
    parameter integer ITERS=20,
    parameter [31:0] HC_EPS=32'h358637bd,
    parameter integer MUT_PRE=0
)(
    input wire clk,sink_clk,rst_n,
    input wire launch,
    input wire [767:0] mixes,bases,
    input wire [95:0] scales,
    input wire sink_launch,sink_capture,
    output wire e_ready,
    output reg result_v,
    output wire [767:0] result,
    output reg fault
);
    localparam integer P1=1,P2=28,MAX=55,P3=56,P4=75,P5=148,P6=159,P7=186,EREADY=197;
    reg active;
    reg [8:0] age;
    reg [31:0] t[0:23],b[0:23],s[0:2],mx[0:3];
    reg [767:0] final_result;
    assign result=final_result;
    assign e_ready=active&&(age==EREADY);
    wire p1=active&&age>=P1&&age<P1+24;
    wire p2=active&&age>=P2&&age<P2+24;
    wire p3=active&&age>=P3&&age<P3+16;
    wire p4=active&&age>=P4&&age<P4+24;
    wire p5=active&&age>=P5&&age<P5+8;
    wire p6=active&&age>=P6&&age<P6+8;
    wire p7=active&&age>=P7&&age<P7+8;
    wire [4:0] i=p1?5'(age-P1):p2?5'(age-P2):p3?5'(age-P3+8):
        p4?5'(age-P4):p5?5'(age-P5):p6?5'(age-P6):5'(age-P7);
    wire mv=p1||(p7&&i>=4), av=p2||p3||p5||(p7&&i<4);
    wire [31:0] ma=t[i],mb=p1?s[(i<4)?0:(i<8)?1:2]:32'h40000000;
    wire [31:0] aa=t[i],ab=p2?b[i]:p3?(mx[(i-8)>>2]^32'h80000000):
        p5?32'h3f800000:(MUT_PRE?32'd0:HC_EPS);
    wire [31:0] ey,dy,my,ay;
    wire mo,ao,eo,do_,ef,df;
    wire [1:0] me,ae;
    wire [4:0] mi,ai,ei,di;
    ot_hdc_fp32_mul_fast__d4g_hc mul(.clk(clk),.rst_n(rst_n),.valid_in(mv),.a(ma),.b(mb),.y(my),.err(me),.valid_out(mo));
    ot_hdc_fp32_add_fast__d4g_hc add(.clk(clk),.rst_n(rst_n),.valid_in(av),.a(aa),.b(ab),.y(ay),.err(ae),.valid_out(ao));
    ot_hdc_v41x_exp__d4g_hc #(.LM(3),.LA(3)) exp_(.clk(clk),.rst_n(rst_n),.v(p4),
        .x((i<8)?(t[i]^32'h80000000):t[i]),.y(ey),.vo(eo),.fault(ef));
    ot_hdc_v41x_fdiv__d4g_hc div_(.clk(clk),.rst_n(rst_n),.v(p6),.a(32'h3f800000),.b(t[i]),.y(dy),.vo(do_),.fault(df));
    ot_hdc_delay__d4g_hc #(.W(5),.D(3)) mt(clk,rst_n,i,mi);
    ot_hdc_delay__d4g_hc #(.W(5),.D(3)) at(clk,rst_n,i,ai);
    ot_hdc_delay__d4g_hc #(.W(5),.D(49)) et(clk,rst_n,i,ei);
    ot_hdc_delay__d4g_hc #(.W(5),.D(19)) dt(clk,rst_n,i,di);
    function automatic greater(input [31:0] a,c);
        if(a[30:0]==0&&c[30:0]==0)greater=0;
        else if(a[31]!=c[31])greater=!a[31];
        else greater=a[31]?(a[30:0]<c[30:0]):(a[30:0]>c[30:0]);
    endfunction
    wire [511:0] se,sy;
    for(genvar j=0;j<16;j=j+1)assign se[j*32+:32]=t[j+8];
    wire sr,sv,sf,sbusy;
    ot_hdc_sinkhorn__d4g_hc #(.ITERS(ITERS),.EPS(HC_EPS)) sink(
        .clk(sink_clk),.rst_n(rst_n),.in_valid(sink_launch),.in_ready(sr),
        .in_e(se),.out_valid(sv),.y(sy),.fault(sf),.busy(sbusy));
    reg sink_fault;
    always @(posedge sink_clk or negedge rst_n)begin
        if(!rst_n)sink_fault<=0;
        else if((sink_launch&&!sr)||sf)sink_fault<=1;
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;age<=0;fault<=0;result_v<=0;end
        else begin
            result_v<=sink_capture;
            if(active&&age<EREADY+1)age<=age+1'b1;
            if(launch)begin
                age<=1;active<=1;
                if(active)fault<=1;
            end
            if((mo&&(|me))||(ao&&(|ae))||(eo&&ef)||(do_&&df)||sink_fault)fault<=1;
            if(sink_capture)begin
                // sv remains high for a complete sink-clock period. Compiler
                // picks the reserved core edge within that proven interval.
                if(!active||age<EREADY||!sv||sf)fault<=1;
                active<=0;
            end
        end
    end
    always @(posedge clk)begin
        if(launch)begin
            for(integer j=0;j<24;j=j+1)begin t[j]<=mixes[j*32+:32];b[j]<=bases[j*32+:32];end
            for(integer j=0;j<3;j=j+1)s[j]<=scales[j*32+:32];
        end
        if(mo)t[mi]<=my;
        if(ao)t[ai]<=ay;
        if(eo)t[ei]<=ey;
        if(do_)t[di]<=dy;
        if(active&&age==MAX)for(integer r=0;r<4;r=r+1)begin:maximum
            reg [31:0] v;
            v=t[8+4*r];
            for(integer c=1;c<4;c=c+1)if(greater(t[8+4*r+c],v))v=t[8+4*r+c];
            mx[r]<=v;
        end
        if(sink_capture)begin
            for(integer j=0;j<8;j=j+1)final_result[j*32+:32]<=t[j];
            final_result[256+:512]<=sy;
        end
    end
endmodule
`default_nettype wire

// Scoped source: rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
`timescale 1ns/1ps
`default_nettype none
// F20 programme target. Two registered transport rungs; execution never waits.
// A descriptor arms exactly one launch. Actual programme-pin writes maintain a
// finite installed-row bitmap, not a shadow payload. The first write after a
// descriptor starts a fresh image generation; unwritten old SRAM rows are invalid.
// A descriptor-only rearm may reuse an installed image. Descriptor verification
// scans the exact [base,limit) range before configured can rise; descriptor-only
// reuse of the same resident range reuses its proof. All scanning and
// write-commit latency is initialization; an early launch faults without replay.
// TGT_PIN=1 (H-NETLIST 0600): the target id comes from the identity strap pin tgt (die constant), so one hardened master
// serves every target id; TGT_PIN=0 keeps the TARGET parameter (tgt unused).
// CAP_CLK=1 (H-NETLIST 0600): the F20 input-capture rung (cv/dv/lv, target/address/data/base/limit/loops, tgt) runs on
// clk_cap, a related same-frequency phase-0 root kept short at the face; the body (bitmap, scan, outputs) stays on clk.
module ot_static_program_target__d4g_hc #(parameter [7:0] TARGET=8'd48,parameter integer PCW=10,parameter integer TGT_PIN=0,
                                  parameter integer CAP_CLK=0)(
    input wire clk,rst_n,
    input wire clk_cap,   // used only when CAP_CLK=1
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire program_active,
    output reg program_cfg_we,
    output reg [PCW-1:0] program_cfg_addr,
    output reg [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault
);
    localparam integer ROWS=1<<PCW;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    // External reset reaches two synchronizer pins, not the entire valid bitmap.
    (* async_reg = "true" *) reg reset_meta,reset_live;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_live<=0;end
        else begin reset_meta<=1;reset_live<=reset_meta;end
    reg cv,dv,lv;
    reg [7:0] target;
    wire clk_in=(CAP_CLK!=0)?clk_cap:clk;
    reg [7:0] tgt_q; always @(posedge clk_in) tgt_q<=tgt;
    wire [7:0] tid=(TGT_PIN!=0)?tgt_q:TARGET;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg [ROWS-1:0] installed;
    reg install_open,armed,scanning,validated,missing;
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk_in)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk_in or negedge reset_live)
        if(!reset_live)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            installed<=0;install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;
            scan_row<=0;scan_limit<=0;commit<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            // Observe the real registered programme-write pins. The neighbour's
            // capture and SRAM write consume two further edges; commit masks both.
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin
                if(!install_open)installed<=({{(ROWS-1){1'b0}},1'b1}<<program_cfg_addr);
                else installed[program_cfg_addr]<=1'b1;
                install_open<=1;
            end
            if(cv && target==tid)begin
                armed<=0;validated<=0;configured<=0;
                if(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address})fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end
            end
            if(dv && target==tid)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        // Same range in the unchanged resident generation: reuse
                        // the completed row proof, not a stale descriptor arm.
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!installed[scan_row])missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !installed[scan_row])fault<=1;
                    else validated<=1;
                end else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base;
                    program_start_limit<=stored_limit;program_start_loops<=stored_loops;
                end
            end
        end
endmodule
`default_nettype wire

// Scoped source: rtl/hdc/ot_hdc_delay.sv
`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay__d4g_hc #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_fastfp.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Low-latency binary32 add and multiply (ot_hdc_qadd__d4g_hc / ot_hdc_qmul__d4g_hc) for the
// decode core's stream unit and special-function pipelines.
//
// Same arithmetic, bit for bit, as the qualified five-stage pipes they stand in
// for -- rtl/proto/ot_fp32_add_rne_pipe.sv and rtl/hdc/ot_hdc_fp32_mul_pipe.sv:
// IEEE RNE with gradual underflow, every zero result canonical +0, a zero
// multiplier operand giving +0, (+-0)+(+-0) = +0, and a nonfinite operand or an
// overflowing result failing closed through `err` with y = 0.  Equivalence is
// checked cycle by cycle against those pipes (rtl/test/tb_hdc_fastfp_equiv.sv).
//
// What is different is depth.  The five-stage pipes are cut around carry
// chains that the synthesis flow maps to ripple logic (a 31-bit magnitude
// compare, 28-bit adds, a 48-bit product sum, the rounding increment); here
// every carry chain is an explicit Kogge-Stone prefix network, the product is a
// carry-save tree, and the leading-zero count is a tree whose exponent-floor
// clamp is a sentinel bit, so each operation is three register stages.
// ---------------------------------------------------------------------------

// W-bit adder with carry-in, Kogge-Stone prefix carries.
module ot_hdc_ksa__d4g_hc #(parameter integer W = 8) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    // Index 0 of the prefix network is the carry-in; index i+1 is bit i.
    reg [W:0] g, p, gn, pn;
    integer l, i;
    always @* begin
        g = {a & b, cin};
        p = {a ^ b, 1'b0};
        for (l = 1; l <= W; l = l * 2) begin
            gn = g;
            pn = p;
            for (i = l; i <= W; i = i + 1) begin
                gn[i] = g[i] | (p[i] & g[i - l]);
                pn[i] = p[i] & p[i - l];
            end
            g = gn;
            p = pn;
        end
    end
    assign s = (a ^ b) ^ g[W-1:0];
    assign cout = g[W];
endmodule

// Leading-zero count of a 32-bit word as a tree (n = 32 for zero).
module ot_hdc_lzc32__d4g_hc (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule

// 24 x 24 unsigned product in two halves, so a pipeline register can sit in
// the middle of the tree: 24 AND rows, Wallace reduction by vector 3:2
// compressors 24 -> 16 -> 11 -> 8 (ot_hdc_mul24_rows__d4g_hc), then 8 -> 6 -> 4 -> 3
// -> 2 and a Kogge-Stone final add (ot_hdc_mul24_sum__d4g_hc).  Rows are flat vectors,
// row k in bits [48k +: 48]; a compressor writes its sum to row 2i and its
// carry to row 2i+1.
module ot_hdc_mul24_rows__d4g_hc (
    input  wire [23:0]     a,
    input  wire [23:0]     b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;        // {carry, sum} of three rows
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a & {24{b[i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

module ot_hdc_mul24_sum__d4g_hc (
    input  wire [48*8-1:0] rows,
    output wire [47:0]     p
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(rows[144*i +: 48], rows[144*i + 48 +: 48], rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire unused_cout;
    ot_hdc_ksa__d4g_hc #(.W(48)) u_cpa (.a(l7[47:0]), .b(l7[95:48]), .cin(1'b0), .s(p), .cout(unused_cout));
endmodule

// ---------------------------------------------------------------------------
// Binary32 add, LATENCY 3, II 1.  Stage for stage:
//   1  decode; |b| > |a| as one 31-bit prefix compare of the encodings; both
//      exponent differences; the smaller significand aligned with a jam
//   2  the add and the subtract (both prefix adders); the add's one-bit
//      renormalize; the cancellation normalize, its shift the leading-zero
//      count of the difference OR a sentinel at the exponent floor
//   3  round to nearest even (prefix increment), encode, the refusals
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_fast__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    //: Magnitude order is the integer order of the encodings (a subnormal's
    //: exponent 1 and a normal's hidden bit agree with it), so the swap is one
    //: compare: b[30:0] > a[30:0] exactly when a - b borrows.
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksa__d4g_hc #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire swap = !cmp_c;
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksa__d4g_hc #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksa__d4g_hc #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    //: Three guard bits, everything shifted past them OR-ed into the lowest.
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    //: Both alignments, then the pick: when b is the larger b's exponent is
    //: not below a's, so dba is the distance; otherwise dab.
    wire [27:0] small_a = jam28(a_man, dba);
    wire [27:0] small_b = jam28(b_man, dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= bypass;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_code <= bypass_code;
        s1_sub <= a[31] ^ b[31];
        s1_sign <= swap ? b[31] : a[31];
        s1_exp <= swap ? b_exp : a_exp;
        s1_big <= swap ? b_man : a_man;
        s1_small <= swap ? small_a : small_b;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum, dif;
    wire sum_c, dif_c;
    ot_hdc_ksa__d4g_hc #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum), .cout(sum_c));
    ot_hdc_ksa__d4g_hc #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif), .cout(dif_c));
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    //: The authority normalizes one bit at a time while bit 26 is clear and the
    //: exponent is above 1: the shift is min(lzc, exp - 1).  A one at bit
    //: 26 - (exp - 1) makes the count stop there.
    wire [7:0]  room = s1_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz;
    ot_hdc_lzc32__d4g_hc u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz));
    wire [26:0] sub_val = dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksa__d4g_hc #(.W(8)) u_esub (.a(s1_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksa__d4g_hc #(.W(8)) u_eadd (.a(s1_exp), .b(8'd0), .cin(carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_code <= s1_code; s2_sign <= s1_sign;
        s2_zero <= s1_sub && (dif == 28'd0);
        s2_exp <= s1_sub ? exp_sub : exp_add;
        s2_val <= s1_sub ? sub_val : add_val;
    end

    // -- stage 3 ------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_hc #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd), .cout(rnd_c));
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, s2_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {s2_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (s2_exp == 8'hff) || (e >= 9'd255);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= s2_code; err <= s2_err; end
            else if (s2_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Binary32 multiply, LATENCY 3, II 1.
//   1  decode; subnormal operands normalized (tree LZC); the exponent sum;
//      the partial products and three carry-save levels (24 -> 8 rows)
//   2  the rest of the tree and the prefix final add; both exponent
//      decisions (leading bit 47 or 46) and the subnormal-result alignment
//      masks, all from the exponent sum alone
//   3  the product's top bit picks the decision; align, round, encode, refuse
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_fast__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam [1:0] E_NONE = 2'd0;
    localparam [1:0] E_NONFINITE = 2'd1;
    localparam [1:0] E_OVERFLOW = 2'd2;

    // -- stage 1 ------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [23:0] a_raw = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_raw = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire zero = (a[30:0] == 31'd0) || (b[30:0] == 31'd0);
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_hc u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_hc u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    //: The authority's powers: field - 150 for a normal, -149 - shift for a
    //: subnormal (a normal has no leading zero, so the shift is 0 there).
    wire signed [11:0] a_power = (a_field == 8'd0) ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = (b_field == 8'd0) ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksa__d4g_hc #(.W(12)) u_pw (.a(a_power), .b(b_power), .cin(1'b0), .s(power), .cout(power_c));

    //: The first three compressor levels ride in stage 1, after the normalize.
    wire [48*8-1:0] rows;
    ot_hdc_mul24_rows__d4g_hc u_rows (.a(a_raw << a_lz[4:0]), .b(b_raw << b_lz[4:0]), .rows(rows));

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= valid_in;
    end
    always @(posedge clk) begin
        s1_byp <= nonfinite || zero;
        s1_err <= nonfinite ? E_NONFINITE : E_NONE;
        s1_sign <= a[31] ^ b[31];
        s1_rows <= rows;
        s1_power <= power;
    end

    // -- stage 2 ------------------------------------------------------------
    wire [47:0] prod;
    ot_hdc_mul24_sum__d4g_hc u_sum (.rows(s1_rows), .p(prod));
    //: floor = power + msb; a subnormal result when floor < -126, and then the
    //: alignment is -(power + 149) whatever the msb, so only the normal path's
    //: fixed alignment (23 or 24) depends on the product.
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    //: sh_sub >= 24 whenever it is used; clamp at 63 (everything below).
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_byp <= s1_byp; s2_err <= s1_err; s2_sign <= s1_sign;
        s2_prod <= prod;
        s2_sub47 <= fl47 < -12'sd126;
        s2_sub46 <= fl46 < -12'sd126;
        s2_fl47 <= fl47; s2_fl46 <= fl46;
        s2_sh <= shc; s2_mr <= m_round; s2_ms <= m_sticky;
    end

    // -- stage 3 ------------------------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    wire [23:0] rnd;
    wire rnd_c;
    ot_hdc_ksa__d4g_hc #(.W(24)) u_rnd (.a(main), .b(24'd0), .cin(rb && (st || main[0])), .s(rnd), .cout(rnd_c));
    wire carry = !is_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = fl + {11'd0, carry};
    wire over = !is_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = is_sub && rnd[23];
    wire [31:0] code = is_sub ? (sub_carry ? {s2_sign, 8'h01, 23'd0} : {s2_sign, 8'h00, rnd[22:0]})
                              : {s2_sign, field, man[22:0]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= s2_v;
            if (s2_byp) begin y <= 32'd0; err <= s2_err; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end
endmodule

// Fault-reporting wrappers, as ot_hdc_fadd / ot_hdc_fmul but LATENCY 3.
module ot_hdc_qadd__d4g_hc #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_add_fast__d4g_hc (unchanged); L > 3 is ot_hdc_fp32_add_lat__d4g_hc #(L), bit for bit
    // the same values, with the extra cuts (rtl/hdc/ot_hdc_fp32_add_lat__d4g_hc.sv) so no stage carries two prefix adders.
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_add_fast__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_add_lat__d4g_hc #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

module ot_hdc_qmul__d4g_hc #(
    // el1011-q-sp 2026-10-11: L = 3 is ot_hdc_fp32_mul_fast__d4g_hc (unchanged); L > 3 is ot_hdc_fp32_mul_lat__d4g_hc #(L), bit for bit
    // the same values; L >= 5 cuts the four carry-save levels from the 48-bit prefix add (fast stage 2, the lane
    // tile's -180 ps TT path s1_rows -> s2_prod).
    parameter integer L = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (L == 3) begin : g_f
        ot_hdc_fp32_mul_fast__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_l
        ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fastfp_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 serial-domain wrappers over the fast binary32 units (rtl/hdc/ot_hdc_fastfp.sv), kept out of that file so
// the records that pin it stay current.  Needs rtl/hdc/ot_hdc_fastfp.sv (or its DPI stand-ins); the non-default
// branches also need rtl/hdc/ot_hdc_fp32_mul_lat__d4g_hc.sv, rtl/hdc/ot_hdc_fp32_add_lat__d4g_hc.sv and rtl/hdc/ot_hdc_prefix.sv.
//   ot_hdc_qmul_lat__d4g_hc #(LAT)       ot_hdc_qmul__d4g_hc at LAT 3 (default), ot_hdc_fp32_mul_lat4__d4g_hc / _lat5i / _lat #(LAT)
//   ot_hdc_qadd_lat__d4g_hc #(KEEP, LAT) ot_hdc_qadd__d4g_hc (default), ot_hdc_fp32_add_lat3__d4g_hc / _lat4i (keep-prefix adders)
//   ot_hdc_kadd__d4g_hc / _kge / _kinc   integer add / compare / increment: behavioural (K = 0) or keep-prefix (K = 1)
// ---------------------------------------------------------------------------
// ot_hdc_qmul_lat__d4g_hc #(LAT): ot_hdc_qmul__d4g_hc with the multiplier's latency as a parameter.  LAT = 3 is ot_hdc_qmul__d4g_hc
// itself (ot_hdc_fp32_mul_fast__d4g_hc); LAT = 4..7 is ot_hdc_fp32_mul_lat__d4g_hc #(LAT) (rtl/hdc/ot_hdc_fp32_mul_lat__d4g_hc.sv, which
// needs rtl/hdc/ot_hdc_fp32_add_lat__d4g_hc.sv), bit-identical to it (21d9aab2: 5,000,000 biased pairs).  W11 serial
// domain: the 3-stage multiply misses 1.111 ns at SS; LAT 4 reaches 987 MHz.
module ot_hdc_qmul_lat__d4g_hc #(
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (LAT == 3) begin : g_l3
        ot_hdc_fp32_mul_fast__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_l4
        // the fixed LAT-4 top: a plain module name, so synthesis can keep it as its own hierarchy
        // (ORFS SYNTH_KEEP_MODULES) and ABC maps it as the standalone unit
        ot_hdc_fp32_mul_lat4__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 5) begin : g_l5
        // LAT 5 is the input-cut variant (C1 + C3; rtl/hdc/ot_hdc_fp32_mul_lat__d4g_hc.sv): the operand multiplexer ahead of
        // the unit shares a stage with the decode / normalise, not with the partial products (W11 serial domain)
        ot_hdc_fp32_mul_lat5i__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_ln
        ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// ot_hdc_qadd_lat__d4g_hc #(KEEP, LAT): ot_hdc_qadd__d4g_hc, or (KEEP = 1) the plain ot_hdc_fp32_add_lat3__d4g_hc top of
// rtl/hdc/ot_hdc_fp32_add_lat__d4g_hc.sv (needs rtl/hdc/ot_hdc_prefix.sv): the same binary32 add, bit for bit, with
// (* keep *) Kogge-Stone prefix adders that ABC cannot re-ripple inside a parent block; LAT = 4 (KEEP = 1) is
// the input-cut ot_hdc_fp32_add_lat4i__d4g_hc (W11 serial domain, 0.9 GHz at SS).
module ot_hdc_qadd_lat__d4g_hc #(
    parameter integer KEEP = 0,
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (KEEP == 0) begin : g_fast
        ot_hdc_fp32_add_fast__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_keep4
        ot_hdc_fp32_add_lat4i__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_keep
        ot_hdc_fp32_add_lat3__d4g_hc u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Keep-prefix integer arithmetic for the W11 serial-domain build (K = 1: rtl/hdc/ot_hdc_prefix.sv, whose
// (* keep *) Kogge-Stone levels ABC cannot re-ripple; K = 0: the behavioural operator, the unit as it was).
module ot_hdc_kadd__d4g_hc #(parameter integer W = 24, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire cin, output wire [W-1:0] s, output wire cout
);
    generate if (K == 0) begin : g_b
        assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
    end else begin : g_k
        ot_hdc_ksadd_k__d4g_hc #(.W(W)) u (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
    end endgenerate
endmodule

// ge = (a >= b), unsigned
module ot_hdc_kge__d4g_hc #(parameter integer W = 32, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, output wire ge
);
    generate if (K == 0) begin : g_b
        assign ge = (a >= b);
    end else begin : g_k
        wire [W-1:0] unused_s;
        ot_hdc_ksadd_k__d4g_hc #(.W(W)) u (.a(a), .b(~b), .cin(1'b1), .s(unused_s), .cout(ge));
    end endgenerate
endmodule

// y = a + inc (mod 2^W)
module ot_hdc_kinc__d4g_hc #(parameter integer W = 16, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire inc, output wire [W-1:0] y
);
    generate if (K == 0) begin : g_b
        assign y = a + {{(W-1){1'b0}}, inc};
    end else begin : g_k
        wire unused_co;
        ot_hdc_inc_k__d4g_hc #(.W(W)) u (.a(a), .inc(inc), .y(y), .co(unused_co));
    end endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_add_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_add_lat__d4g_hc #(LAT): the binary32 adder of ot_hdc_fp32_add_fast__d4g_hc (rtl/hdc/ot_hdc_fastfp.sv), bit for bit,
// with LAT = 3..6 register stages.  A MEASUREMENT vehicle for the 1.2 GHz @ SS decision (W11, 2026-09-30): the
// same logic is cut at up to three extra boundaries, so the SS fmax against LAT shows the flop overhead.
//   A1  decode, magnitude compare, exponent differences        | cut C_A  (LAT >= 5)
//   A2  both jammed alignments, the swap pick
//   B1  28-bit sum and difference (prefix adders)               | cut C_B  (LAT >= 4)
//   B2  normalise: sentinel LZC, shift, exponent adjust
//   C1  round increment (prefix adder)                          | cut C_C  (LAT >= 6)
//   C2  encode, subnormal, overflow, canonical zero -> y
//   (B2 is cut after the sentinel LZC when LAT >= 7)
// Every prefix adder is ot_hdc_ksadd_k__d4g_hc (rtl/hdc/ot_hdc_prefix.sv): (* keep *) Kogge-Stone levels, so ABC cannot
// re-ripple the carries inside a parent block (W13: the plain form closed standalone and failed in context).
// LAT 3 has the cuts of ot_hdc_fp32_add_fast__d4g_hc (after A, after B, after C).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_add_lat__d4g_hc #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bits {D, C, B, A} (LAT must be 3 + their count); -1: by LAT.
    // W11 serial domain: CUTS = 4'b0001 (C_A, LAT 4) cuts the INPUT side, so an operand multiplexer in front of
    // the unit shares stage 1 with the decode / compare instead of the alignment
    parameter integer CUTS = -1,
    // DRST 0 (fe-push-hphys-1010, opt-in via OT_FP_DATA_NORST): only the valid bits are reset (cuts VB, valid_out);
    // y / err / data cuts are plain flops (consumers qualify them with valid_out).  1: legacy, every stage bit reset.
    parameter integer DRST = `ifdef OT_FP_DATA_NORST 0 `else 1 `endif
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;     // inside B2: after the sentinel LZC
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k__d4g_hc #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k__d4g_hc #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k__d4g_hc #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 boundary bundle
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    ot_hdc_w11_cut__d4g_hc #(.W(WA + 1), .CUT(CUT_A), .VB(DRST ? -1 : WA - 1)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    // ---- A2 ----------------------------------------------------------------------------------------
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k__d4g_hc #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k__d4g_hc #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    ot_hdc_w11_cut__d4g_hc #(.W(WB), .CUT(CUT_B), .VB(DRST ? -1 : WB - 1)) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    // ---- B2 ----------------------------------------------------------------------------------------
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32__d4g_hc u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // B2a -> B2b boundary (LAT >= 7)
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    ot_hdc_w11_cut__d4g_hc #(.W(WD), .CUT(CUT_D), .VB(DRST ? -1 : WD - 1)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k__d4g_hc #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k__d4g_hc #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_hc #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [WC-1:0] c2_in;
    ot_hdc_w11_cut__d4g_hc #(.W(WC), .CUT(CUT_C), .VB(DRST ? -1 : WC - 1)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    // ---- C2 ----------------------------------------------------------------------------------------
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate if (DRST != 0) begin : g_yr
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
            else begin
                valid_out <= u_v;
                if (u_byp) begin y <= u_code; err <= u_err; end
                else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
                else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
                else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
            end
        end
    end else begin : g_yn
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= u_v;
        end
        always @(posedge clk) begin
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end endgenerate
endmodule

// a W-bit bundle, registered when CUT = 1 (bit 0... the bundle's MSB is the valid, reset to 0), else passed through
// VB >= 0 (fe-push-hphys-1010, opt-in): only bit VB (the bundle's valid) is reset; the data bits are plain flops (a wide
// datapath costs no reset fan-out; validity travels on the reset bit).  VB < 0 (default): every bit reset, as before.
module ot_hdc_w11_cut__d4g_hc #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule

// fixed tops for the hardening sweep
// the W11 serial-domain LAT-4 adder: the LAT-3 cuts plus C_A (after the decode / compare), bit-identical
module ot_hdc_fp32_add_lat4i__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hc #(.LAT(4), .CUTS(1)) u (.*);
endmodule
module ot_hdc_fp32_add_lat3__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hc #(.LAT(3)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hc #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat5__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hc #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat6__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hc #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_add_lat7__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat__d4g_hc #(.LAT(7)) u (.*);
endmodule

// Scoped source: rtl/hdc/ot_hdc_fp32_mul_lat.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fp32_mul_lat__d4g_hc #(LAT): the binary32 multiplier of ot_hdc_fp32_mul_fast__d4g_hc (rtl/hdc/ot_hdc_fastfp.sv), bit for
// bit, with LAT = 3..9 register stages (W11 measurement vehicle for 1.2 GHz @ SS; see ot_hdc_fp32_add_lat__d4g_hc).
//   S1  decode, subnormal LZC                             | C5 (LAT >= 8; margin rule 2026-10-06)
//       normalise shift                                   | C1 (LAT >= 6)
//       partial products + three carry-save levels, the exponent sum
//   S2  four carry-save levels                            | C2 (LAT >= 5)
//       the 48-bit prefix add; the subnormal masks
//   S3  select, subnormal shift, sticky/round bits        | C3 (LAT >= 4)
//       round increment (prefix add)                      | C4 (LAT >= 7)
//       encode                                            | C6 (LAT >= 9; margin rule 2026-10-06)
//   C7 (LAT >= 10; margin m3 2026-10-06) sits in front of S1: field / zero / non-finite decode | LZC, power
//       refusals -> y
// Every prefix adder is ot_hdc_ksadd_k__d4g_hc (rtl/hdc/ot_hdc_prefix.sv, (* keep *) levels).
// Uses ot_hdc_w11_cut__d4g_hc (rtl/hdc/ot_hdc_fp32_add_lat__d4g_hc.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fp32_mul_lat__d4g_hc #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bit k-1 = C<k> (LAT must be 3 + their count); -1: by LAT as above.
    // W11 serial domain: CUTS = 4'b0101 (C1 + C3, LAT 5) cuts the INPUT side, so an operand multiplexer in front
    // of the unit shares stage 1 with the decode / normalise instead of the partial-product rows
    parameter integer CUTS = -1,
    // KCP > 1 (margin m3, 2026-10-06): the C1 operand register is KCP kept copies (ot_hdc_mul_kcp48__d4g_hc), each driving
    // 24/KCP partial products, so the 24-load operand broadcast to the partial-product rows is a local net.  Values
    // identical (every copy captures the same a_n / b_n); no added cycle.  Needs CUT1.
    parameter integer KCP = 1,
    // Opt-in: reset only valid bits at extra cuts; payload is ignored until valid.
    parameter integer DRST = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT1 = (CUTS >= 0) ? CUTS % 2       : (LAT >= 6) ? 1 : 0;
    localparam integer CUT2 = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 5) ? 1 : 0;
    localparam integer CUT3 = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT4 = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;
    localparam integer CUT5 = (CUTS >= 0) ? (CUTS / 16) % 2 : (LAT >= 8) ? 1 : 0;
    localparam integer CUT6 = (CUTS >= 0) ? (CUTS / 32) % 2 : (LAT >= 9) ? 1 : 0;
    localparam integer CUT7 = (CUTS >= 0) ? (CUTS / 64) % 2 : (LAT >= 10) ? 1 : 0;
    generate if (CUTS >= 0 && CUT1 + CUT2 + CUT3 + CUT4 + CUT5 + CUT6 + CUT7 + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_mul_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction

    // ---- S1a: decode, normalise --------------------------------------------------------------------
    // C7: field / zero / non-finite decode | LZC, power
    wire [68:0] c7;
    ot_hdc_w11_cut__d4g_hc #(.W(69), .CUT(CUT7), .VB(DRST ? -1 : 69-1)) u_c7 (.clk(clk), .rst_n(rst_n),
        .d({valid_in, a, b, (a[30:23] == 8'd0), (b[30:23] == 8'd0),
            (a[30:23] == 8'hff) || (b[30:23] == 8'hff), (a[30:0] == 31'd0) || (b[30:0] == 31'd0)}), .q(c7));
    wire        x_v, x_afz, x_bfz, nonfinite, zero;
    wire [31:0] x_a, x_b;
    assign {x_v, x_a, x_b, x_afz, x_bfz, nonfinite, zero} = c7;
    wire [7:0]  a_field = x_a[30:23];
    wire [7:0]  b_field = x_b[30:23];
    wire [23:0] a_raw = {!x_afz, x_a[22:0]};
    wire [23:0] b_raw = {!x_bfz, x_b[22:0]};
    wire [5:0] a_lz, b_lz;
    ot_hdc_lzc32__d4g_hc u_la (.x({a_raw, 8'hff}), .n(a_lz));
    ot_hdc_lzc32__d4g_hc u_lb (.x({b_raw, 8'hff}), .n(b_lz));
    wire signed [11:0] a_power = x_afz ? (-12'sd149 - {7'd0, a_lz[4:0]})
                                                   : ($signed({4'd0, a_field}) - 12'sd150);
    wire signed [11:0] b_power = x_bfz ? (-12'sd149 - {7'd0, b_lz[4:0]})
                                                   : ($signed({4'd0, b_field}) - 12'sd150);
    // C5: decode / LZC | normalise shift
    localparam integer W5 = 1 + 1 + 2 + 1 + 24 + 24 + 5 + 5 + 12 + 12;
    wire [W5-1:0] c5;
    ot_hdc_w11_cut__d4g_hc #(.W(W5), .CUT(CUT5), .VB(DRST ? -1 : W5-1)) u_c5 (.clk(clk), .rst_n(rst_n),
        .d({x_v, nonfinite || zero, (nonfinite ? E_NONFINITE : E_NONE), x_a[31] ^ x_b[31], a_raw, b_raw, a_lz[4:0],
            b_lz[4:0], a_power, b_power}), .q(c5));
    wire        n_v, n_bz, n_sign;
    wire [1:0]  n_err;
    wire [23:0] n_ar, n_br;
    wire [4:0]  n_al, n_bl;
    wire [11:0] n_ap, n_bp;
    assign {n_v, n_bz, n_err, n_sign, n_ar, n_br, n_al, n_bl, n_ap, n_bp} = c5;
    wire [23:0] a_n = n_ar << n_al;
    wire [23:0] b_n = n_br << n_bl;
    localparam integer W1 = 1 + 1 + 2 + 1 + 24 + 24 + 12 + 12;
    wire [W1-1:0] c1;
    ot_hdc_w11_cut__d4g_hc #(.W(W1), .CUT(CUT1), .VB(DRST ? -1 : W1-1)) u_c1 (.clk(clk), .rst_n(rst_n),
        .d({n_v, n_bz, n_err, n_sign, a_n, b_n, n_ap, n_bp}),
        .q(c1));
    wire        p_v, p_byp, p_sign;
    wire [1:0]  p_err;
    wire [23:0] p_a, p_b;
    wire [11:0] p_ap, p_bp;
    assign {p_v, p_byp, p_err, p_sign, p_a, p_b, p_ap, p_bp} = c1;
    // ---- S1b: rows, exponent sum ------------------------------------------------------------------
    wire [11:0] power;
    wire power_c;
    ot_hdc_ksadd_k__d4g_hc #(.W(12)) u_pw (.a(p_ap), .b(p_bp), .cin(1'b0), .s(power), .cout(power_c));
    wire [48*8-1:0] rows;
    generate if (KCP > 1 && CUT1 != 0) begin : g_kcp
        wire [KCP*24-1:0] ka, kb;
        genvar k;
        for (k = 0; k < KCP; k = k + 1) begin : g_c
            ot_hdc_mul_kcp48__d4g_hc u_k (.clk(clk), .rst_n(rst_n),
`ifdef NEGK
                .d({a_n ^ ((k == 1) ? 24'd1 : 24'd0), b_n}),   // bench negative control only
`else
                .d({a_n, b_n}),
`endif .q({ka[24*k +: 24], kb[24*k +: 24]}));
        end
        ot_hdc_mul24_rows_k__d4g_hc #(.K(KCP)) u_rows (.a(ka), .b(kb), .rows(rows));
    end else begin : g_nokcp
        ot_hdc_mul24_rows__d4g_hc u_rows (.a(p_a), .b(p_b), .rows(rows));
    end endgenerate

    reg        s1_v, s1_byp, s1_sign;
    reg [1:0]  s1_err;
    reg [48*8-1:0] s1_rows;
    reg signed [11:0] s1_power;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= p_v;
    end
    always @(posedge clk) begin
        s1_byp <= p_byp; s1_err <= p_err; s1_sign <= p_sign; s1_rows <= rows; s1_power <= power;
    end

    // ---- S2a: compress to two rows; masks ----------------------------------------------------------
    wire [48*6-1:0] l4;
    wire [48*4-1:0] l5;
    wire [48*3-1:0] l6;
    wire [48*2-1:0] l7;
    genvar i;
    generate
        for (i = 0; i < 2; i = i + 1) begin : g_l4
            assign l4[96*i +: 96] = csa(s1_rows[144*i +: 48], s1_rows[144*i + 48 +: 48], s1_rows[144*i + 96 +: 48]);
        end
        assign l4[192 +: 96] = s1_rows[288 +: 96];
        for (i = 0; i < 2; i = i + 1) begin : g_l5
            assign l5[96*i +: 96] = csa(l4[144*i +: 48], l4[144*i + 48 +: 48], l4[144*i + 96 +: 48]);
        end
    endgenerate
    assign l6[0 +: 96] = csa(l5[0 +: 48], l5[48 +: 48], l5[96 +: 48]);
    assign l6[96 +: 48] = l5[144 +: 48];
    assign l7 = csa(l6[0 +: 48], l6[48 +: 48], l6[96 +: 48]);
    wire signed [11:0] fl47 = s1_power + 12'sd47;
    wire signed [11:0] fl46 = s1_power + 12'sd46;
    wire signed [11:0] sh_sub = -(s1_power + 12'sd149);
    wire [5:0] shc = (sh_sub > 12'sd63) ? 6'd63 : sh_sub[5:0];
    reg [47:0] m_round, m_sticky;
    integer k;
    always @* begin
        for (k = 0; k < 48; k = k + 1) begin
            m_round[k] = ({6'd0, k[5:0]} == {6'd0, shc} - 12'd1);
            m_sticky[k] = ({6'd0, k[5:0]} < {6'd0, shc} - 12'd1);
        end
    end
    localparam integer W2 = 1 + 1 + 2 + 1 + 96 + 1 + 1 + 12 + 12 + 6 + 48 + 48;
    wire [W2-1:0] c2;
    ot_hdc_w11_cut__d4g_hc #(.W(W2), .CUT(CUT2), .VB(DRST ? -1 : W2-1)) u_c2 (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_err, s1_sign, l7, fl47 < -12'sd126, fl46 < -12'sd126, fl47, fl46, shc, m_round, m_sticky}),
        .q(c2));
    wire        q_v, q_byp, q_sign, q_s47, q_s46;
    wire [1:0]  q_err;
    wire [95:0] q_l7;
    wire [11:0] q_fl47, q_fl46;
    wire [5:0]  q_sh;
    wire [47:0] q_mr, q_ms;
    assign {q_v, q_byp, q_err, q_sign, q_l7, q_s47, q_s46, q_fl47, q_fl46, q_sh, q_mr, q_ms} = c2;
    // ---- S2b: the prefix add -----------------------------------------------------------------------
    wire [47:0] prod;
    wire unused_cout;
    ot_hdc_ksadd_k__d4g_hc #(.W(48)) u_cpa (.a(q_l7[47:0]), .b(q_l7[95:48]), .cin(1'b0), .s(prod), .cout(unused_cout));

    reg        s2_v, s2_byp, s2_sign, s2_sub47, s2_sub46;
    reg [1:0]  s2_err;
    reg [47:0] s2_prod, s2_mr, s2_ms;
    reg [5:0]  s2_sh;
    reg signed [11:0] s2_fl47, s2_fl46;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= q_v;
    end
    always @(posedge clk) begin
        s2_byp <= q_byp; s2_err <= q_err; s2_sign <= q_sign;
        s2_prod <= prod;
        s2_sub47 <= q_s47; s2_sub46 <= q_s46;
        s2_fl47 <= q_fl47; s2_fl46 <= q_fl46;
        s2_sh <= q_sh; s2_mr <= q_mr; s2_ms <= q_ms;
    end

    // ---- S3a: select, subnormal shift, round/sticky bits ------------------------------------------
    wire top = s2_prod[47];
    wire is_sub = top ? s2_sub47 : s2_sub46;
    wire signed [11:0] fl = top ? s2_fl47 : s2_fl46;
    wire [23:0] n_main = top ? s2_prod[47:24] : s2_prod[46:23];
    wire n_rb = top ? s2_prod[23] : s2_prod[22];
    wire n_st = top ? (|s2_prod[22:0]) : (|s2_prod[21:0]);
    wire [47:0] sub_shifted = s2_prod >> s2_sh;
    wire [23:0] s_main = sub_shifted[23:0];
    wire s_rb = |(s2_prod & s2_mr);
    wire s_st = |(s2_prod & s2_ms);
    wire [23:0] main = is_sub ? s_main : n_main;
    wire rb = is_sub ? s_rb : n_rb;
    wire st = is_sub ? s_st : n_st;
    localparam integer W3 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W3-1:0] c3;
    ot_hdc_w11_cut__d4g_hc #(.W(W3), .CUT(CUT3), .VB(DRST ? -1 : W3-1)) u_c3 (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_err, s2_sign, is_sub, fl, main, rb && (st || main[0])}), .q(c3));
    wire        r_v, r_byp, r_sign, r_sub, r_inc;
    wire [1:0]  r_err;
    wire [11:0] r_fl;
    wire [23:0] r_main;
    assign {r_v, r_byp, r_err, r_sign, r_sub, r_fl, r_main, r_inc} = c3;
    // ---- S3b: round ---------------------------------------------------------------------------------
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__d4g_hc #(.W(24)) u_rnd (.a(r_main), .b(24'd0), .cin(r_inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer W4 = 1 + 1 + 2 + 1 + 1 + 12 + 24 + 1;
    wire [W4-1:0] c4;
    ot_hdc_w11_cut__d4g_hc #(.W(W4), .CUT(CUT4), .VB(DRST ? -1 : W4-1)) u_c4 (.clk(clk), .rst_n(rst_n),
        .d({r_v, r_byp, r_err, r_sign, r_sub, r_fl, rnd_w, rnd_cw}), .q(c4));
    wire        o_v, o_byp, o_sign, o_sub, rnd_c;
    wire [1:0]  o_err;
    wire signed [11:0] o_fl;
    wire [23:0] rnd;
    assign {o_v, o_byp, o_err, o_sign, o_sub, o_fl, rnd, rnd_c} = c4;
    // ---- S3c: encode --------------------------------------------------------------------------------
    wire carry = !o_sub && rnd_c;
    wire [23:0] man = carry ? {1'b1, rnd[23:1]} : rnd;
    wire signed [11:0] floor_ = o_fl + {11'd0, carry};
    wire over = !o_sub && (floor_ > 12'sd127);
    wire [7:0] field = floor_[7:0] + 8'd127;
    wire sub_carry = o_sub && rnd[23];
    wire [31:0] code = o_sub ? (sub_carry ? {o_sign, 8'h01, 23'd0} : {o_sign, 8'h00, rnd[22:0]})
                             : {o_sign, field, man[22:0]};
    // C6: encode | refusals -> y
    localparam integer W6 = 1 + 1 + 2 + 1 + 32;
    wire [W6-1:0] c6;
    ot_hdc_w11_cut__d4g_hc #(.W(W6), .CUT(CUT6), .VB(DRST ? -1 : W6-1)) u_c6 (.clk(clk), .rst_n(rst_n), .d({o_v, o_byp, o_err, over, code}), .q(c6));
    wire        e_v, e_byp, e_over;
    wire [1:0]  e_err;
    wire [31:0] e_code;
    assign {e_v, e_byp, e_err, e_over, e_code} = c6;
    generate if (DRST != 0) begin : g_output_reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= e_v;
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end
    end else begin : g_output_valid_reset
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= e_v;
        end
        always @(posedge clk) begin
            if (e_byp) begin y <= 32'd0; err <= e_err; end
            else if (e_over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (e_code[30:0] == 31'd0) ? 32'd0 : e_code; err <= E_NONE; end
        end
    end endgenerate
endmodule

module ot_hdc_fp32_mul_lat4__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat6__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat7__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(7)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat9__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(9)) u (.*);
endmodule

// the W11 serial-domain LAT-5 multiplier: the LAT-4 cuts plus C1 (after the decode / normalise), bit-identical
module ot_hdc_fp32_mul_lat5i__d4g_hc (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(5), .CUTS(5)) u (.*);
endmodule

// KCP copy of the C1 operand register: kept (SYNTH_KEEP_MODULES) so equal-D copies are never merged into one driver
module ot_hdc_mul_kcp48__d4g_hc (input wire clk, input wire rst_n, input wire [47:0] d, output reg [47:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 48'd0; else q <= d;
endmodule

// ot_hdc_mul24_rows__d4g_hc with the operands supplied as K copies: partial product i reads copy i*K/24 (identical values)
module ot_hdc_mul24_rows_k__d4g_hc #(parameter integer K = 2) (
    input  wire [K*24-1:0] a,
    input  wire [K*24-1:0] b,
    output wire [48*8-1:0] rows
);
    function automatic [95:0] csa;
        input [47:0] r0, r1, r2;
        begin
            csa[47:0] = r0 ^ r1 ^ r2;
            csa[95:48] = ((r0 & r1) | (r0 & r2) | (r1 & r2)) << 1;
        end
    endfunction
    wire [48*24-1:0] l0;
    wire [48*16-1:0] l1;
    wire [48*11-1:0] l2;
    genvar i;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_pp
            assign l0[48*i +: 48] = {24'd0, a[24*(i*K/24) +: 24] & {24{b[24*(i*K/24) + i]}}} << i;
        end
        for (i = 0; i < 8; i = i + 1) begin : g_l1
            assign l1[96*i +: 96] = csa(l0[144*i +: 48], l0[144*i + 48 +: 48], l0[144*i + 96 +: 48]);
        end
        for (i = 0; i < 5; i = i + 1) begin : g_l2
            assign l2[96*i +: 96] = csa(l1[144*i +: 48], l1[144*i + 48 +: 48], l1[144*i + 96 +: 48]);
        end
        assign l2[480 +: 48] = l1[720 +: 48];
        for (i = 0; i < 3; i = i + 1) begin : g_l3
            assign rows[96*i +: 96] = csa(l2[144*i +: 48], l2[144*i + 48 +: 48], l2[144*i + 96 +: 48]);
        end
        assign rows[288 +: 96] = l2[432 +: 96];
    endgenerate
endmodule

// Scoped source: rtl/hdc/ot_hdc_prefix.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Explicit log-depth adders (W10, 72f00b86; shared FP primitive copy owned by W11, rtl/hdc/ot_hdc_prefix.sv).
//
// Written as behavioural `a + b` or `a + inc`, yosys/ABC maps these adders as carry ripples (chains of MAJ or
// OR cells) even with ADDER_MAP_FILE cleared: measured at ORFS WC, 0.833 ns, a 28-bit add inside the element
// took 920 ps and a 24-bit rounding increment a chain of ten OR4/OR5 cells (W10 and W13, 2026-09-30).  Here each
// Kogge-Stone prefix level is a (* keep *) net, so synthesis must keep log2(W) levels.
//
// ot_v41_ksadd: s = a + b + cin (W bits), cout.
// ot_v41_inc:   y = a + inc (W bits), co (the carry out of the top bit).
// ---------------------------------------------------------------------------
module ot_hdc_ksadd_k__d4g_hc #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule


module ot_hdc_inc_k__d4g_hc #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    // t[i]: all of positions [0, i] are one, position 0 being the increment
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign t[l + 1][i] = t[l][i] & t[l][i - (1 << l)];
                end else begin : g_p
                    assign t[l + 1][i] = t[l][i];
                end
            end
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule

// Scoped source: rtl/hdc/ot_hdc_sfu.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Special-function pipelines of the hardwired decode core: exp, reciprocal and
// reciprocal square root.  Each is an unrolled chain of the qualified binary32
// multiply/add pipes (LATENCY 5, II 1) plus single-cycle integer steps, so each
// accepts one operand per cycle and returns it a fixed DEPTH later.  No divider,
// no iteration, no combinational IEEE operation.
//
// The algorithms and their operation order are the specification in
// tools/hdc_golden.py (exp, reciprocal, rsqrt); the RTL matches it bit for bit.
// ---------------------------------------------------------------------------

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_vline__d4g_hc #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule

// exp(x): clamp to [-87, 88]; n = rint(x*log2e) by the 1.5*2^23 trick; two-
// constant Cody-Waite reduction; degree-6 Horner; 2^n added to the exponent.
module ot_hdc_exp__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 92;
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [31:0] K_MAGIC = 32'h4B400000;   //  1.5 * 2^23
    localparam [31:0] K_NMAGIC = 32'hCB400000;
    localparam [31:0] K_HI    = 32'h3F317200;   //  ln2 high part
    localparam [31:0] K_LO    = 32'h35BFBE8E;   //  ln2 low part
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t, u, n, a_hi, a_lo, r1, r, xc_d20, lo_d5;
    wire [6:0] f;
    ot_hdc_fmul m_t  (clk, rst_n, vd[1],  xc, K_LOG2E, t,   f[0]);   // 6
    ot_hdc_fadd a_u  (clk, rst_n, vd[6],  t,  K_MAGIC, u,   f[1]);   // 11
    ot_hdc_fadd a_n  (clk, rst_n, vd[11], u,  K_NMAGIC, n,  f[2]);   // 16
    ot_hdc_fmul m_hi (clk, rst_n, vd[16], n,  K_HI,    a_hi, f[3]);  // 21
    ot_hdc_fmul m_lo (clk, rst_n, vd[16], n,  K_LO,    a_lo, f[4]);  // 21
    ot_hdc_delay__d4g_hc #(.W(32), .D(20)) d_x (clk, rst_n, xc, xc_d20);
    ot_hdc_fadd a_r1 (clk, rst_n, vd[21], xc_d20, {~a_hi[31], a_hi[30:0]}, r1, f[5]);  // 26
    ot_hdc_delay__d4g_hc #(.W(32), .D(5)) d_lo (clk, rst_n, a_lo, lo_d5);
    ot_hdc_fadd a_r  (clk, rst_n, vd[26], r1, {~lo_d5[31], lo_d5[30:0]}, r, f[6]);     // 31

    // Horner: p = C0; six times p = p*r + C[k]; r travels in 10-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay__d4g_hc #(.W(32), .D(10)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_fmul u_m (clk, rst_n, vd[31 + 10*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_fadd u_a (clk, rst_n, vd[36 + 10*(k-1)], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    // n as an integer: u = 1.5*2^23 + n exactly, so n sits in u's fraction.
    reg  [8:0] nint;
    wire [8:0] nint_d;
    always @(posedge clk) nint <= u[8:0];   // low 9 bits of 0x400000 + n are n
    ot_hdc_delay__d4g_hc #(.W(9), .D(79)) d_n (clk, rst_n, nint, nint_d);   // 12 -> 91
    always @(posedge clk) y <= pa[6] + {{14{nint_d[8]}}, nint_d, 23'd0};   // 92

    assign fault = |{f, hf};
endmodule

// 1/d: seed 0x7ef311c7 - bits(d), three Newton-Raphson steps y*(2 - d*y).
module ot_hdc_recip__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 46;
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0, d1;
    always @(posedge clk) begin
        // The bit seed wraps above this finite positive denominator.
        // Saturate that unsupported range to +0 before Newton iteration.
        y0 <= (!x[31] && x[30:23] != 8'hff && x > 32'h7EF311C7)
            ? 32'h00000000 : 32'h7EF311C7 - x;
        d1 <= x;
    end
    wire [31:0] yi [0:3];
    wire [31:0] dd [0:2];
    wire [31:0] m [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [8:0] f;
    assign yi[0] = y0;
    assign dd[0] = d1;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_d
                ot_hdc_delay__d4g_hc #(.W(32), .D(15)) d_d (clk, rst_n, dd[k], dd[k+1]);
            end
            ot_hdc_fmul m_m (clk, rst_n, vd[1 + 15*k], dd[k], yi[k], m[k], f[3*k]);
            ot_hdc_fadd a_s (clk, rst_n, vd[6 + 15*k], 32'h40000000, {~m[k][31], m[k][30:0]}, s[k], f[3*k+1]);
            ot_hdc_delay__d4g_hc #(.W(32), .D(10)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y (clk, rst_n, vd[11 + 15*k], yd[k], s[k], yi[k+1], f[3*k+2]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_rsqrt__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer DEPTH = 61;
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    always @(posedge clk) y0 <= 32'h5F3759DF - {1'b0, x[31:1]};
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_fmul m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // 5
    ot_hdc_delay__d4g_hc #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 6
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay__d4g_hc #(.W(32), .D(20)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_fmul m_yy (clk, rst_n, vd[1 + 20*k],  yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_fmul m_hm (clk, rst_n, vd[6 + 20*k],  hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_fadd a_s  (clk, rst_n, vd[11 + 20*k], 32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay__d4g_hc #(.W(32), .D(15)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_fmul m_y  (clk, rst_n, vd[16 + 20*k], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fdiv.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION, fully pipelined: II 1, fixed DEPTH 31.
//
// WHY A NEW DIVIDER.  The repository's qualified correctly rounded divider,
// rtl/abi3/ot_a3_fp32_div_rne_pipe.sv, is a bisection FSM: one operand in
// flight, an in_ready handshake and ~50 cycles per quotient.  The decode core
// streams one operand per cycle, so it needs the same function as a systolic
// pipe.  This is the digit recurrence that rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv
// uses for the square root, applied to division: one quotient bit per stage,
// a 25-bit compare-and-subtract per stage, no multiplier anywhere.
//
// FUNCTION.  y = RN_even(a / b) in binary32 with gradual underflow, and every
// zero result canonical +0 -- the arithmetic of tools/hdc_golden_v41.div and of
// the qualified add/mul pipes.  Operands may be subnormal.  A nonfinite
// operand, a zero divisor or an overflowing quotient FAILS CLOSED: `fault` on
// that result and y = +0 (the pipes' convention; never an infinity).
//
// EXACTNESS.  Both significands are normalised to [2^23, 2^24).  The recurrence
// forms Q = floor(ma * 2^26 / mb), 26 or 27 significant bits, and the final
// remainder; the remainder is nonzero exactly when the quotient is inexact, so
// {Q, remainder != 0} carries the guard and a true sticky bit.  A subnormal
// result shifts {significand, guard} right with the shifted-out bits ORed into
// the sticky, then rounds once.  So the result is rounded exactly once, from
// the exact quotient.
//
// Stages: 1 decode/normalise, 27 recurrence (quotient bits 2^0 .. 2^-26),
// 3 finish (select and exponent, subnormal shift, round and encode).
// ---------------------------------------------------------------------------
module ot_hdc_fdiv__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer DEPTH = 31;
    localparam integer QB = 27;

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- decode: normalise both significands (priority encoder + shift) ------
    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    wire [33:0] na = norm(a[30:23], a[22:0]);
    wire [33:0] nb = norm(b[30:23], b[22:0]);

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_zero <= (a[30:0] == 31'd0);
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // ---- recurrence: stage j forms quotient bit 2^-j -----------------------------
    reg [24:0]        r_rem  [0:QB-1];
    reg [QB-1:0]      r_q    [0:QB-1];
    reg [23:0]        r_mb   [0:QB-1];
    reg               r_sign [0:QB-1];
    reg               r_zero [0:QB-1];
    reg               r_bad  [0:QB-1];
    reg signed [10:0] r_e    [0:QB-1];

    genvar j;
    generate
        for (j = 0; j < QB; j = j + 1) begin : g_rec
            wire [24:0] src_rem = (j == 0) ? {1'b0, d_ma} : {r_rem[j-1][23:0], 1'b0};
            wire [23:0] src_mb  = (j == 0) ? d_mb : r_mb[j-1];
            wire [QB-1:0] src_q = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [25:0] diff = {1'b0, src_rem} - {2'b0, src_mb};
            wire take = !diff[25];
            always @(posedge clk) begin
                r_rem[j]  <= take ? diff[24:0] : src_rem;
                r_q[j]    <= {src_q[QB-2:0], take};
                r_mb[j]   <= src_mb;
                r_sign[j] <= (j == 0) ? d_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? d_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? d_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? d_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[QB-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[QB-1];
        f1_zero <= r_zero[QB-1];
        f1_bad  <= r_bad[QB-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[QB-1]);
            f1_be  <= r_e[QB-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[QB-1]);
            f1_be  <= r_e[QB-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = (25'd1 << sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3: round to nearest even, encode ----------------------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    wire [30:0] code = {f2_field, f2_sig[22:0]} + {30'd0, rup};
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_sinkhorn.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection Sinkhorn unit of the DeepSeek-V4.1 decode core,
// LATENCY-OPTIMISED: one whole normalisation step per clock.
//
// FUNCTION.  tools/hdc_golden_v41.py Model.hc_mixes after the exponential:
// given e = exp(comb - rowmax) (4 x 4, row-major, binary32), return
//     comb = e / seqsum_row(e) + eps               (step 0: rows)
//     comb = comb / (seqsum_col(comb) + eps)        (step 1: columns)
//     (ITERS - 1) x { rows, then columns }          (steps 2 .. 2 ITERS - 1)
// where every sum is SEQUENTIAL in index order, ((a + b) + c) + d, each
// addition and each division one IEEE binary32 operation (RNE, gradual
// underflow, every zero result +0).  2 ITERS = 40 normalisations for V4.1.
// The row max and the exponential stay in the stream unit's SFU (the golden's
// exp is its own polynomial); this unit starts where they end.
//
// WHY.  tools/decode_critical_path.py found V4.1's per-user decode bounded by
// this chain: 80 Sinkhorns per token, each 40 DEPENDENT normalisations, and a
// normalisation on the pipelined units costs 3 chained adds + the eps add +
// the 31-deep divider ot_hdc_fdiv__d4g_hc = 51 cycles.  Area is nearly free here (one
// unit per sublayer engine), so this unit spends it on latency:
//
// * no pipeline registers inside a step: the state (16 words) is the only
//   register, and one clock is one normalisation.  A step is a single
//   combinational path  state -> 3 chained adds -> eps add -> seed ->
//   quotient -> state,  so it pays ONE register overhead, not ~51;
// * positive-only adders (ot_hdc_sk_add__d4g_hc): every operand here is >= 0, so the
//   cancellation path of a general adder does not exist; S and S + 1 come
//   from one compound prefix adder and rounding only selects;
// * division by multiply-and-check (ot_hdc_sk_seed__d4g_hc + ot_hdc_sk_quot__d4g_hc): a
//   512-entry quadratic seed R with 1/T - 2^-26 < R <= 1/T (proved for all
//   2^23 significands), M' = floor(X' R) is M or M - 1, and two EXACT
//   remainder signs select M', M'+1 or M'+2: the correctly rounded quotient,
//   bit-identical to IEEE division by construction.  The seed depends only on
//   the denominator, so each row's four quotients share one;
// * all four rows (16 quotients) in parallel; the matrix is written back
//   TRANSPOSED each step, so the next step (columns) again sums storage rows:
//   no row/column select mux anywhere on the path.  40 steps is an even
//   number of transposes, so the result leaves in the input orientation.
//
// Steady-state operand ranges (why the step path needs no subnormal logic):
// after step 0 every element is q + eps >= eps (normal), every step's
// denominator is a positive sum + eps >= eps (normal), and a quotient
// x / (x + ... + eps) lies in [2^-23, 1] (normal).  Step 0 is the only one
// that can see subnormal e, a subnormal row sum or a subnormal quotient, so it
// runs as two cycles on a separate general datapath:
//   A: row sums -> normalise (leading-zero count) -> registers
//   B: seed -> quotient WITH gradual underflow -> + eps -> state
// and the step path is the lean one.  An out-of-range steady quotient cannot
// occur; if it did, `fault` would say so (fail closed).
//
// SCHEDULE.  Accept (in_valid & in_ready) -> A -> B -> 2 ITERS - 1 steps;
// out_valid pulses 2 ITERS + 1 clock edges after the accepting edge (41 for
// ITERS = 20) and `y` holds until the next accept.
//
// FAIL-CLOSED.  A nonfinite or negative (nonzero) input element, an overflow
// of a sum, a zero row sum (0/0) or a quotient out of range raises `fault`
// with out_valid, and y is then all +0 -- the hdc units' convention.  -0 is
// read as +0.
//
// CLOCK.  One step per clock makes this clock the STEP time.  In the ~1 GHz
// decode core the unit runs as a multicycle path (or on a divided clock):
// ceil(step_ns * f_core) core cycles per step.  Routed figures:
// results/physical_abi3/asap7/hdc/v41/ot_hdc_sinkhorn__d4g_hc/.
// ---------------------------------------------------------------------------
module ot_hdc_sinkhorn__d4g_hc #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD       // hc_eps = 1e-6 in binary32
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [511:0] in_e,                  // element (r, c) at [32 (4r + c) +: 32]
    output reg          out_valid,
    output wire [511:0] y,
    output reg          fault,
    output wire         busy
);
    localparam integer STEPS = 2 * ITERS - 1;  // steady steps after step 0
    localparam [1:0] P_IDLE = 2'd0, P_A = 2'd1, P_B = 2'd2, P_RUN = 2'd3;
    localparam [7:0]  EPS_E = (EPS[30:23] == 8'd0) ? 8'd1 : EPS[30:23];
    localparam [23:0] EPS_M = {EPS[30:23] != 8'd0, EPS[22:0]};

    reg [1:0]  ph;
    reg [7:0]  cnt;
    reg        flt;
    reg [31:0] er [0:15];                      // step-0 inputs
    reg [31:0] st [0:15];                      // the matrix, transposed every step
    // step-0 registers between A and B
    reg [23:0]       a_xm [0:15];
    reg signed [9:0] a_xe [0:15];
    reg              a_xz [0:15];
    reg [23:0]       a_tm [0:3];
    reg signed [9:0] a_te [0:3];

    assign in_ready = (ph == P_IDLE);
    assign busy = (ph != P_IDLE);

    genvar r, c;

    // ======================= step 0, cycle A: row sums, normalise =======================
    wire [15:0] a_bad_in;
    wire [3:0]  a_bad_sum;
    wire [23:0]       nx_m [0:15];
    wire signed [9:0] nx_e [0:15];
    wire              nx_z [0:15];
    wire [23:0]       nt_m [0:3];
    wire signed [9:0] nt_e [0:3];
    generate
        for (r = 0; r < 16; r = r + 1) begin : g_ain
            wire [31:0] w = er[r];
            assign a_bad_in[r] = (w[31] && (w[30:0] != 31'd0)) || (w[30:23] == 8'hFF);
            ot_hdc_sk_norm__d4g_hc u_nx (.x(w[30:0]), .m(nx_m[r]), .e(nx_e[r]), .z(nx_z[r]));
        end
        for (r = 0; r < 4; r = r + 1) begin : g_arow
            wire [7:0]  ee [0:3];
            wire [23:0] mm [0:3];
            for (c = 0; c < 4; c = c + 1) begin : g_dec
                wire [31:0] w = er[4*r + c];
                assign ee[c] = (w[30:23] == 8'd0) ? 8'd1 : w[30:23];
                assign mm[c] = {w[30:23] != 8'd0, w[22:0]};
            end
            wire [7:0] e1, e2, e3, g1, g2, g3;
            wire [23:0] m1, m2, m3;
            wire o1, o2, o3, u1, u2, u3, tz;
            ot_hdc_sk_add__d4g_hc u_a1 (.ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                                .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
            ot_hdc_sk_add__d4g_hc u_a2 (.ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),
                                .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
            ot_hdc_sk_add__d4g_hc u_a3 (.ea(g2), .ua(u2), .ma(m2), .eb(ee[3]), .mb(mm[3]),
                                .eg(g3), .up(u3), .e(e3), .m(m3), .ovf(o3));
            wire [30:0] sum = {m3[23] ? e3 : 8'd0, m3[22:0]};
            ot_hdc_sk_norm__d4g_hc u_nt (.x(sum), .m(nt_m[r]), .e(nt_e[r]), .z(tz));
            assign a_bad_sum[r] = o1 | o2 | o3 | tz;
        end
    endgenerate

    // ======================= step 0, cycle B: divide with underflow, + eps ==============
    wire [31:0] b_out [0:15];
    wire [15:0] b_bad;
    generate
        for (r = 0; r < 4; r = r + 1) begin : g_brow
            wire [28:0] rs;
            ot_hdc_sk_seed__d4g_hc u_seed (.tm(a_tm[r]), .r(rs));
            for (c = 0; c < 4; c = c + 1) begin : g_bel
                wire [30:0] q;
                wire rng, ov;
                ot_hdc_sk_quot__d4g_hc #(.SUBN(1)) u_q (.xm(a_xm[4*r + c]), .xe(a_xe[4*r + c]), .xz(a_xz[4*r + c]),
                                                .tm(a_tm[r]), .te(a_te[r]), .r(rs), .y(q), .range(rng));
                wire [7:0]  qe = (q[30:23] == 8'd0) ? 8'd1 : q[30:23];
                wire [23:0] qm = {q[30:23] != 8'd0, q[22:0]};
                wire [7:0]  oe, og;
                wire [23:0] om;
                wire        ou;
                ot_hdc_sk_add__d4g_hc u_eps (.ea(qe), .ua(1'b0), .ma(qm), .eb(EPS_E), .mb(EPS_M),
                                     .eg(og), .up(ou), .e(oe), .m(om), .ovf(ov));
                // transposed write: storage row c holds logical column c
                assign b_out[4*c + r] = {1'b0, om[23] ? oe : 8'd0, om[22:0]};
                assign b_bad[4*r + c] = rng | ov;
            end
        end
    endgenerate

    // ======================= steady step: sum, + eps, divide ============================
    wire [31:0] s_out [0:15];
    wire [15:0] s_bad;
    generate
        for (r = 0; r < 4; r = r + 1) begin : g_srow
            wire [7:0]  ee [0:3];
            wire [23:0] mm [0:3];
            wire [3:0]  sub;
            for (c = 0; c < 4; c = c + 1) begin : g_dec
                wire [31:0] w = st[4*r + c];
                assign ee[c]  = (w[30:23] == 8'd0) ? 8'd1 : w[30:23];
                assign mm[c]  = {w[30:23] != 8'd0, w[22:0]};
                assign sub[c] = (w[30:23] == 8'd0);
            end
            wire [7:0] e1, e2, e3, et, g1, g2, g3, gt;
            wire [23:0] m1, m2, m3, mt;
            wire o1, o2, o3, ot, u1, u2, u3, ut;
            // the chain: each add takes the previous one's exponent as eg + up (up resolves last)
            ot_hdc_sk_add__d4g_hc u_s1 (.ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                                .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
            ot_hdc_sk_add__d4g_hc u_s2 (.ea(g1), .ua(u1), .ma(m1), .eb(ee[2]), .mb(mm[2]),
                                .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
            ot_hdc_sk_add__d4g_hc u_s3 (.ea(g2), .ua(u2), .ma(m2), .eb(ee[3]), .mb(mm[3]),
                                .eg(g3), .up(u3), .e(e3), .m(m3), .ovf(o3));
            ot_hdc_sk_add__d4g_hc u_ae (.ea(g3), .ua(u3), .ma(m3), .eb(EPS_E), .mb(EPS_M),
                                .eg(gt), .up(ut), .e(et), .m(mt), .ovf(ot));
            // t >= eps is normal: its significand is already normalised
            wire signed [9:0] te = $signed({2'b00, et}) - 10'sd127;
            wire [28:0] rs;
            ot_hdc_sk_seed__d4g_hc u_seed (.tm(mt), .r(rs));
            for (c = 0; c < 4; c = c + 1) begin : g_sel
                wire [30:0] q;
                wire rng;
                ot_hdc_sk_quot__d4g_hc #(.SUBN(0)) u_q (.xm(mm[c]), .xe($signed({2'b00, ee[c]}) - 10'sd127), .xz(1'b0),
                                                .tm(mt), .te(te), .r(rs), .y(q), .range(rng));
                assign s_out[4*c + r] = {1'b0, q};
                assign s_bad[4*r + c] = rng | sub[c] | o1 | o2 | o3 | ot | !mt[23];
            end
        end
    endgenerate

    // ======================= control ===================================================
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= P_IDLE;
            cnt <= 8'd0;
            flt <= 1'b0;
            out_valid <= 1'b0;
            fault <= 1'b0;
        end else begin
            out_valid <= 1'b0;
            case (ph)
                P_IDLE: if (in_valid) begin
                    ph <= P_A;
                    flt <= 1'b0;
                end
                P_A: begin
                    ph <= P_B;
                    flt <= flt | (|a_bad_in) | (|a_bad_sum);
                end
                P_B: begin
                    flt <= flt | (|b_bad);
                    cnt <= STEPS[7:0];
                    if (STEPS == 0) begin
                        ph <= P_IDLE;
                        out_valid <= 1'b1;
                        fault <= flt | (|b_bad);
                    end else ph <= P_RUN;
                end
                default: begin
                    flt <= flt | (|s_bad);
                    cnt <= cnt - 8'd1;
                    if (cnt == 8'd1) begin
                        ph <= P_IDLE;
                        out_valid <= 1'b1;
                        fault <= flt | (|s_bad);
                    end
                end
            endcase
        end
    end

    always @(posedge clk) begin
        for (k = 0; k < 16; k = k + 1) begin
            if (in_ready && in_valid) er[k] <= in_e[32*k +: 32];
            if (ph == P_A) begin
                a_xm[k] <= nx_m[k];
                a_xe[k] <= nx_e[k];
                a_xz[k] <= nx_z[k];
            end
            if (ph == P_B) st[k] <= b_out[k];
            else if (ph == P_RUN) st[k] <= s_out[k];
        end
        for (k = 0; k < 4; k = k + 1) if (ph == P_A) begin
            a_tm[k] <= nt_m[k];
            a_te[k] <= nt_e[k];
        end
    end

    generate
        for (r = 0; r < 16; r = r + 1) begin : g_y
            assign y[32*r +: 32] = fault ? 32'd0 : st[r];
        end
    endgenerate
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_sk_arith.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Latency-optimised combinational arithmetic for the hyper-connection
// Sinkhorn unit (ot_hdc_sinkhorn__d4g_hc.sv).  Every module here is COMBINATIONAL and
// written structurally -- Kogge-Stone prefix carries, carry-save (3:2) trees,
// logarithmic shifters -- because the flow's generic `+` and `*` lower to
// ripple structures that dominate a chained datapath.  The integer
// specification of every operation is tools/gen_hdc_sinkhorn_recip_rom.py
// (add_pos, seed, xr_product, div), which that tool checks against IEEE
// binary32 and which the campaign checks this RTL against bit for bit.
//
//   ot_hdc_sk_cadd__d4g_hc   compound adder: a+b and a+b+1 from one prefix tree
//   ot_hdc_sk_csa__d4g_hc    carry-save reduction of N rows to two (row-level Wallace)
//   ot_hdc_sk_mul__d4g_hc    unsigned multiplier: AND array (optionally truncated
//                    below a column) -> carry-save tree -> prefix adder
//   ot_hdc_sk_add__d4g_hc    POSITIVE binary32 add, RNE, gradual underflow
//   ot_hdc_sk_seed__d4g_hc   R ~ 1/T, one-sided (1/T - 2^-26 < R <= 1/T)
//   ot_hdc_sk_quot__d4g_hc   correctly rounded X / T from the seed: candidate
//                    M' = floor(X' R) and two exact remainder signs
//   ot_hdc_sk_norm__d4g_hc   normalise a (possibly subnormal) binary32 significand
// ---------------------------------------------------------------------------

// ---- compound Kogge-Stone adder ---------------------------------------------
module ot_hdc_sk_cadd__d4g_hc #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W:0]   s0,     // a + b
    output wire [W:0]   s1      // a + b + 1
);
    localparam integer L = (W <= 1) ? 1 : $clog2(W);
    // level l holds generate/propagate of the span [i : i-2^l+1] (clipped at 0)
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_lv
            // KEEP: every prefix level is a netlist boundary.  The flow extracts half/full adders
            // into library cells, which cuts ABC's view of the path into short cones; each cone
            // then looks far faster than the clock and ABC's area recovery re-maps the prefix
            // network as a RIPPLE chain (seen routed: 22 OA21 in a row per 24-bit add).  Kept
            // level wires pin the log-depth structure.
            (* keep *) wire [W-1:0] g, p;
            if (l == 0) begin : g_init
                assign g = a & b;
                assign p = a ^ b;
            end else begin : g_step
                for (i = 0; i < W; i = i + 1) begin : g_bit
                    if (i >= (1 << (l - 1))) begin : g_op
                        assign g[i] = g_lv[l-1].g[i] | (g_lv[l-1].p[i] & g_lv[l-1].g[i-(1<<(l-1))]);
                        assign p[i] = g_lv[l-1].p[i] & g_lv[l-1].p[i-(1<<(l-1))];
                    end else begin : g_pass
                        assign g[i] = g_lv[l-1].g[i];
                        assign p[i] = g_lv[l-1].p[i];
                    end
                end
            end
        end
    endgenerate
    wire [W-1:0] gg = g_lv[L].g;       // generate of bits [i:0]
    wire [W-1:0] pp = g_lv[L].p;       // propagate of bits [i:0]
    wire [W-1:0] hp = a ^ b;
    wire [W-1:0] c0 = {gg[W-2:0], 1'b0};
    wire [W-1:0] c1 = {gg[W-2:0] | pp[W-2:0], 1'b1};
    assign s0 = {gg[W-1], hp ^ c0};
    assign s1 = {gg[W-1] | pp[W-1], hp ^ c1};
endmodule

// ---- carry-save reduction: N rows of W bits to two, s + c == sum (mod 2^W) ----
module ot_hdc_sk_csa__d4g_hc #(
    parameter integer N = 3,
    parameter integer W = 8
) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s,
    output wire [W-1:0]   c
);
    function automatic integer nxt(input integer n);
        nxt = (n <= 2) ? n : 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer cnt(input integer l);
        integer k, n;
        begin
            n = N;
            for (k = 0; k < 64; k = k + 1) if (k < l) n = nxt(n);
            cnt = n;
        end
    endfunction
    function automatic integer levels(input integer dummy);
        integer k, n, lv;
        begin
            n = N; lv = 0;
            for (k = 0; k < 64; k = k + 1) if (n > 2) begin n = nxt(n); lv = lv + 1; end
            levels = lv;
        end
    endfunction
    localparam integer LV = levels(0);
    genvar l, t, r;
    generate
        for (l = 0; l <= LV; l = l + 1) begin : g_lv
            wire [N*W-1:0] v;          // level l: cnt(l) rows, the rest zero
            if (l == 0) begin : g_init
                assign v = rows;
            end else begin : g_step
                localparam integer NT = cnt(l - 1);
                localparam integer NG = NT / 3;
                for (t = 0; t < NG; t = t + 1) begin : g_fa
                    wire [W-1:0] x = g_lv[l-1].v[(3*t)*W +: W];
                    wire [W-1:0] y = g_lv[l-1].v[(3*t + 1)*W +: W];
                    wire [W-1:0] z = g_lv[l-1].v[(3*t + 2)*W +: W];
                    wire [W-1:0] maj = (x & y) | (x & z) | (y & z);
                    assign v[(2*t)*W +: W] = x ^ y ^ z;
                    assign v[(2*t + 1)*W +: W] = {maj[W-2:0], 1'b0};
                end
                for (r = 3 * NG; r < NT; r = r + 1) begin : g_pass
                    assign v[(2*NG + (r - 3*NG))*W +: W] = g_lv[l-1].v[r*W +: W];
                end
                if (N > cnt(l)) begin : g_fill
                    assign v[cnt(l)*W +: (N - cnt(l))*W] = {((N - cnt(l))*W){1'b0}};
                end
            end
        end
    endgenerate
    assign s = g_lv[LV].v[0 +: W];
    generate
        if (cnt(LV) >= 2) begin : g_two
            assign c = g_lv[LV].v[W +: W];
        end else begin : g_one
            assign c = {W{1'b0}};
        end
    endgenerate
endmodule

// ---- unsigned multiplier; partial-product bits in columns below DROP are not built ----
module ot_hdc_sk_mul__d4g_hc #(
    parameter integer WA = 24,
    parameter integer WB = 24,
    parameter integer DROP = 0
) (
    input  wire [WA-1:0]    a,
    input  wire [WB-1:0]    b,
    output wire [WA+WB-1:0] p
);
    localparam integer W = WA + WB;
    wire [WB*W-1:0] rows;
    genvar j;
    generate
        for (j = 0; j < WB; j = j + 1) begin : g_pp
            wire [W-1:0] full = b[j] ? ({{WB{1'b0}}, a} << j) : {W{1'b0}};
            if (DROP > 0) begin : g_tr
                assign rows[j*W +: W] = {full[W-1:DROP], {DROP{1'b0}}};
            end else begin : g_full
                assign rows[j*W +: W] = full;
            end
        end
    endgenerate
    wire [W-1:0] s, c;
    wire [W:0]   s0, s1;
    ot_hdc_sk_csa__d4g_hc #(.N(WB), .W(W)) u_tree (.rows(rows), .s(s), .c(c));
    ot_hdc_sk_cadd__d4g_hc #(.W(W)) u_cpa (.a(s), .b(c), .s0(s0), .s1(s1));
    assign p = s0[W-1:0];
endmodule

// ---- POSITIVE binary32 addition, RNE, gradual underflow -------------------------
// Operands in the unit's unpacked form: an EFFECTIVE exponent (a zero field
// reads as 1) and the 24-bit significand with its hidden bit explicit (0 for a
// subnormal or zero).  Positive operands cannot cancel, so there is no
// leading-zero path: the exact sum S = big + small * 2^-d needs at most one
// right shift, and because the big significand has no fraction bits the
// fraction of S is exactly the shifted-out part of the small one:
//   no carry: result S (+1 if guard & (sticky | lsb));  guard = small bit d-1
//   carry:    result S >> 1 (+1 if S[0] & (any shifted-out | S[1]))
// S and S + 1 come from ONE compound prefix adder and the round only selects.
// `ovf`: the exponent reached 255 (the caller fails closed).
//
// CHAINING.  Operand a is the running sum of a chain; its exponent arrives as
// ea + ua, where ea is known early and the increment ua (the previous add's
// carry/round-up) is the LAST bit that previous add resolves.  Everything that
// depends only on exponents and on the early operand b -- both exponent
// differences, the order, b's alignment shift and its sticky bits -- is formed
// for BOTH values of ua and selected when ua arrives, so a chained add waits
// only for a's significand, not for an exponent subtraction.  The outputs are
// in the same form: eg + up (eg early, up late).  ua = 0 for a first add.
module ot_hdc_sk_add__d4g_hc (
    input  wire [7:0]  ea,
    input  wire        ua,
    input  wire [23:0] ma,
    input  wire [7:0]  eb,
    input  wire [23:0] mb,
    output wire [7:0]  eg,
    output wire        up,
    output wire [7:0]  e,
    output wire [23:0] m,
    output wire        ovf
);
    wire [8:0] ea1 = {1'b0, ea} + 9'd1;
    wire [7:0] ea_c [0:1];
    assign ea_c[0] = ea;
    assign ea_c[1] = ea1[7:0];
    wire [1:0]  age_c;
    wire [7:0]  dba_c [0:1];
    wire [24:0] shb_c [0:1];
    wire [1:0]  bany_c, bst_c;
    genvar u, i;
    generate
        for (u = 0; u < 2; u = u + 1) begin : g_u
            wire [8:0] ab0, ab1, ba0, ba1;
            ot_hdc_sk_cadd__d4g_hc #(.W(8)) u_dab (.a(ea_c[u]), .b(~eb), .s0(ab0), .s1(ab1));   // ea - eb
            ot_hdc_sk_cadd__d4g_hc #(.W(8)) u_dba (.a(eb), .b(~ea_c[u]), .s0(ba0), .s1(ba1));   // eb - ea
            assign age_c[u] = ab1[8];
            assign dba_c[u] = ba1[7:0];                  // valid when b > a
            // b aligned under a, and its shifted-out bits (all early); dab valid when a >= b
            assign shb_c[u] = (ab1[7:0] >= 8'd25) ? 25'd0 : ({mb, 1'b0} >> ab1[4:0]);
            wire [23:0] mk_any, mk_st;
            for (i = 0; i < 24; i = i + 1) begin : g_mk
                assign mk_any[i] = (ab1[7:0] > i);
                assign mk_st[i]  = (ab1[7:0] > i + 1);
            end
            assign bany_c[u] = |(mb & mk_any);
            assign bst_c[u]  = |(mb & mk_st);
        end
    endgenerate
    wire        a_ge  = ua ? age_c[1] : age_c[0];
    wire        swap  = !a_ge;                   // b strictly larger exponent
    wire [7:0]  dba   = ua ? dba_c[1] : dba_c[0];
    wire [24:0] shb   = ua ? shb_c[1] : shb_c[0];
    wire        b_any = ua ? bany_c[1] : bany_c[0];
    wire        b_st  = ua ? bst_c[1] : bst_c[0];

    // a aligned under b (a is the late operand)
    wire [24:0] sha = (dba >= 8'd25) ? 25'd0 : ({ma, 1'b0} >> dba[4:0]);
    wire [23:0] mk_a_any, mk_a_st;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_mka
            assign mk_a_any[i] = (dba > i);
            assign mk_a_st[i]  = (dba > i + 1);
        end
    endgenerate
    wire a_any = |(ma & mk_a_any), a_st = |(ma & mk_a_st);

    wire [7:0]  eA   = ua ? ea1[7:0] : ea;
    assign eg        = swap ? eb : eA;
    wire [23:0] mg   = swap ? mb : ma;
    wire [23:0] ahi  = swap ? sha[24:1] : shb[24:1];
    wire        g    = swap ? sha[0] : shb[0];
    wire        any  = swap ? a_any : b_any;
    wire        st   = swap ? a_st : b_st;

    wire [24:0] s0, s1;
    ot_hdc_sk_cadd__d4g_hc #(.W(24)) u_sum (.a(mg), .b(ahi), .s0(s0), .s1(s1));
    wire carry = s0[24];
    wire rnc = g & (st | s0[0]);
    wire rc  = s0[0] & (any | s0[1]);
    wire [23:0] mp = carry ? (rc ? s1[24:1] : s0[24:1]) : (rnc ? s1[23:0] : s0[23:0]);
    wire ovm = !carry & rnc & s1[24];          // S = 2^24 - 1 rounded up to 2^24
    wire [8:0] eg1 = {1'b0, eg} + 9'd1;
    assign up  = carry | ovm;
    assign e   = up ? eg1[7:0] : eg;
    assign m   = {mp[23] | ovm, mp[22:0]};
    assign ovf = up & (eg1[7:0] == 8'hFF);
endmodule

// ---- reciprocal seed: 1/T - 2^-26 < R <= 1/T, R in units of 2^-28 ---------------
// T = tm * 2^-23 in [1, 2).  One carry-save tree forms, exactly, at 2^-46:
//   S = c0 2^14 - c1 (h - 2^13) 2 + c2 sq(dm >> 4) - 2^18
// (h = tm[13:0], dm its one's-complement distance from the segment centre,
// sq the square of dm's 16-wide bucket centre / 2^12, from a ROM), and
// R = S[46:18].  The generator proves the bound for all 2^23 significands.
module ot_hdc_sk_seed__d4g_hc (
    input  wire [23:0] tm,
    output wire [28:0] r
);
    wire [32:0] c0;
    wire [22:0] c1;
    wire [12:0] c2;
    ot_hdc_sk_recip_rom__d4g_hc u_rom (.i(tm[22:14]), .c0(c0), .c1(c1), .c2(c2));
    wire [13:0] h  = tm[13:0];
    wire [12:0] dm = h[13] ? h[12:0] : ~h[12:0];
    // the C2 term's square is read, not computed: a 512-entry ROM on dm's top 9 bits,
    // looked up in parallel with the coefficients (bucket-centre square; proved in the bound)
    wire [13:0] sq;
    ot_hdc_sk_sq_rom__d4g_hc u_sq (.dmh(dm[12:4]), .sq(sq));

    localparam integer W = 48;
    localparam integer NR = 2 + 14 + 14 + 1;
    wire [NR*W-1:0] rows;
    assign rows[0*W +: W] = {{(W-47){1'b0}}, c0, 14'd0};
    assign rows[1*W +: W] = {{(W-37){1'b0}}, c1, 14'd0};
    genvar j;
    generate
        for (j = 0; j < 14; j = j + 1) begin : g_c1
            // - c1 * h_j * 2^(j+1), negated as ~x (+1 folded into the constant row)
            wire [W-1:0] v = h[j] ? ({{(W-23){1'b0}}, c1} << (j + 1)) : {W{1'b0}};
            assign rows[(2 + j)*W +: W] = ~v;
        end
        for (j = 0; j < 14; j = j + 1) begin : g_c2
            assign rows[(16 + j)*W +: W] = sq[j] ? ({{(W-13){1'b0}}, c2} << j) : {W{1'b0}};
        end
    endgenerate
    // 14 negation carries minus the bias 2^18, modulo 2^48
    assign rows[30*W +: W] = 48'd14 - 48'd262144;
    wire [W-1:0] s, c;
    wire [W:0]   s0, s1;
    ot_hdc_sk_csa__d4g_hc #(.N(NR), .W(W)) u_tree (.rows(rows), .s(s), .c(c));
    ot_hdc_sk_cadd__d4g_hc #(.W(W)) u_cpa (.a(s), .b(c), .s0(s0), .s1(s1));
    assign r = s0[46:18];
endmodule

// ---- correctly rounded quotient X / T from the seed ------------------------------
// xm, tm: normalised significands (bit 23 set); xe, te: unbiased exponents;
// xz: X is zero.  X' = X or 2X so that q' = X'/T is in [1, 2); E is q's
// unbiased exponent.  M' = floor(q'_approx 2^23) is M or M - 1 (M = floor of the
// exact q' 2^23), so with the two exact remainders
//   r1 = X' 2^24 - (2M'+1) T   (the sign of q' - (M' + 1/2) 2^-23)
//   r2 = r1 - 2T               (the sign of q' - (M' + 3/2) 2^-23)
// the correctly rounded significand is M' + [r1 > 0] + [r2 > 0] (a zero
// remainder is an exact tie: to even).  r1 lies in [-T, 3T), so the remainders
// are formed modulo 2^27 from the LOW columns of M' T only.
// SUBN = 1 adds gradual underflow: a result below 2^-126 is the same
// construction on the coarser grid 2^(-149): M'_s = M' >> s, X' 2^(24-s).
// SUBN = 0 is for operands whose quotient is known normal; an exponent outside
// [1, 254] raises `range` instead.
module ot_hdc_sk_quot__d4g_hc #(
    parameter integer SUBN = 0
) (
    input  wire [23:0]       xm,
    input  wire signed [9:0] xe,
    input  wire              xz,
    input  wire [23:0]       tm,
    input  wire signed [9:0] te,
    input  wire [28:0]       r,
    output wire [30:0]       y,
    output wire              range
);
    // X < T (both normalised): the quotient's leading bit
    wire [24:0] cmp_s0, cmp_s1;
    ot_hdc_sk_cadd__d4g_hc #(.W(24)) u_cmp (.a(xm), .b(~tm), .s0(cmp_s0), .s1(cmp_s1));
    wire lt = !cmp_s1[24];
    wire signed [10:0] e0 = $signed({xe[9], xe}) - $signed({te[9], te});
    wire signed [10:0] e1 = e0 - 11'sd1;
    wire signed [10:0] E  = lt ? e1 : e0;

    // M' = floor(X R 2^(lt-28) ... ) : the truncated product, taken one bit lower when X < T
    wire [52:0] pr;
    ot_hdc_sk_mul__d4g_hc #(.WA(24), .WB(29), .DROP(20)) u_xr (.a(xm), .b(r), .p(pr));
    wire [23:0] mp = lt ? pr[50:27] : pr[51:28];
    wire [24:0] xp = lt ? {xm, 1'b0} : {1'b0, xm};

    // grid shift for a subnormal result
    wire [4:0]  s;
    wire        zero_s;
    generate
        if (SUBN != 0) begin : g_sub
            wire signed [10:0] sfull = -11'sd126 - E;
            assign zero_s = (sfull > 11'sd24);
            assign s = (sfull <= 11'sd0) ? 5'd0 : (zero_s ? 5'd0 : sfull[4:0]);
        end else begin : g_nosub
            assign zero_s = 1'b0;
            assign s = 5'd0;
        end
    endgenerate
    wire [23:0] ms = mp >> s;
    wire [26:0] xs = {2'b00, xp} << (5'd24 - s);          // X' 2^(24-s) mod 2^27

    // r1 = xs - T - sum_j T_j (ms << (j+1))  (mod 2^27), subtrahends negated as ~v (+1 each)
    localparam integer W = 27;
    localparam integer NR = 24 + 3;
    wire [NR*W-1:0] rows;
    genvar j;
    generate
        for (j = 0; j < 24; j = j + 1) begin : g_pp
            wire [W-1:0] v = tm[j] ? ({3'b000, ms} << (j + 1)) : {W{1'b0}};
            assign rows[j*W +: W] = ~v;
        end
    endgenerate
    assign rows[24*W +: W] = xs;
    assign rows[25*W +: W] = ~{3'b000, tm};
    assign rows[26*W +: W] = 27'd25;                         // 24 + 1 negation carries
    wire [W-1:0] ts, tc;
    ot_hdc_sk_csa__d4g_hc #(.N(NR), .W(W)) u_tree (.rows(rows), .s(ts), .c(tc));
    // r2 = r1 - 2T = ts + tc + ~(2T) + 1
    wire [W-1:0] t2 = ~{2'b00, tm, 1'b0};
    wire [W-1:0] u_s = ts ^ tc ^ t2;
    wire [W-1:0] u_maj = (ts & tc) | (ts & t2) | (tc & t2);
    wire [W-1:0] u_cs = {u_maj[W-2:0], 1'b0};
    wire [W:0] a1, a1p, a2, a2p;
    ot_hdc_sk_cadd__d4g_hc #(.W(W)) u_r1 (.a(ts), .b(tc), .s0(a1), .s1(a1p));
    ot_hdc_sk_cadd__d4g_hc #(.W(W)) u_r2 (.a(u_s), .b(u_cs), .s0(a2), .s1(a2p));
    wire neg1 = a1[W-1];
    wire neg2 = a2p[W-1];
    // zero tests without the carry chain: A + B + cin == 0 (mod 2^W) iff A ^ B == {(A | B) << 1, cin}
    wire z1 = ((ts ^ tc) == {(ts[W-2:0] | tc[W-2:0]), 1'b0});
    wire z2 = ((u_s ^ u_cs) == {(u_s[W-2:0] | u_cs[W-2:0]), 1'b1});
    wire inc1 = (!neg1 & !z1) | (z1 & ms[0]);
    wire inc2 = (!neg2 & !z2) | (z2 & !ms[0]);

    // M' + {0, 1, 2}
    wire [24:0] m1_s0, m1_s1;
    ot_hdc_sk_cadd__d4g_hc #(.W(24)) u_inc (.a(ms), .b(24'd0), .s0(m1_s0), .s1(m1_s1));
    wire [23:0] m2_s0, m2_s1;
    ot_hdc_sk_cadd__d4g_hc #(.W(23)) u_inc2 (.a(ms[23:1]), .b(23'd0), .s0(m2_s0), .s1(m2_s1));
    wire [24:0] mplus1 = m1_s1;
    wire [24:0] mplus2 = {m2_s1, ms[0]};
    wire [24:0] mf = inc2 ? mplus2 : (inc1 ? mplus1 : {1'b0, ms});

    wire ovm = mf[24];                                       // rounded up to 2^24
    wire signed [10:0] eb = E + 11'sd127;
    wire signed [10:0] eb1 = E + 11'sd128;
    wire sub = (SUBN != 0) && (s != 5'd0);
    wire [7:0] field = sub ? {7'd0, mf[23]} : (ovm ? eb1[7:0] : eb[7:0]);
    wire bad_hi = !sub && (ovm ? (eb1 > 11'sd254) : (eb > 11'sd254));
    wire bad_lo = (SUBN == 0) && (eb < 11'sd1);
    wire zero = xz | zero_s;
    assign y = zero ? 31'd0 : {field, ovm ? 23'd0 : mf[22:0]};
    assign range = !zero & (bad_hi | bad_lo);
endmodule

// ---- normalise a binary32 magnitude: significand to [2^23, 2^24), unbiased exponent ----
module ot_hdc_sk_norm__d4g_hc (
    input  wire [30:0]       x,
    output reg  [23:0]       m,
    output reg signed [9:0]  e,
    output wire              z
);
    wire [7:0]  f  = x[30:23];
    wire [23:0] mm = {f != 8'd0, x[22:0]};
    assign z = (mm == 24'd0);
    integer k;
    reg [4:0] lz;
    always @* begin
        lz = 5'd0;
        for (k = 0; k < 24; k = k + 1) if (mm[k]) lz = 5'd23 - k[4:0];
        m = mm << lz;
        e = $signed({2'b00, (f == 8'd0) ? 8'd1 : f}) - 10'sd127 - $signed({5'd0, lz});
    end
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
`timescale 1ns/1ps
// GENERATED by tools/gen_hdc_sinkhorn_recip_rom.py -- do not edit.
//
// Quadratic reciprocal seed coefficients for T = 1.f: index i = f[22:14], centre
// Tc = 1 + (i + 1/2) 2^-9; c0 = round(2^32/Tc), c1 = round(2^22/Tc^2), c2 = round(2^12/Tc^3).
// The generator proves 1/T - 2^-26 < R <= 1/T for all 2^23 significands (see ot_hdc_sk_div).
module ot_hdc_sk_recip_rom__d4g_hc (
    input  wire [8:0] i,
    output reg  [32:0] c0,
    output reg  [22:0] c1,
    output reg  [12:0] c2
);
    always @* begin
        case (i)
            9'd0: begin c0 = 33'hffc00ffc; c1 = 23'h3fe00c; c2 = 13'hff4; end
            9'd1: begin c0 = 33'hff408f94; c1 = 23'h3fa06c; c2 = 13'hfdc; end
            9'd2: begin c0 = 33'hfec18e0e; c1 = 23'h3f612a; c2 = 13'hfc5; end
            9'd3: begin c0 = 33'hfe430aad; c1 = 23'h3f2247; c2 = 13'hfad; end
            9'd4: begin c0 = 33'hfdc504b5; c1 = 23'h3ee3c1; c2 = 13'hf96; end
            9'd5: begin c0 = 33'hfd477b6d; c1 = 23'h3ea597; c2 = 13'hf7f; end
            9'd6: begin c0 = 33'hfcca6e1a; c1 = 23'h3e67ca; c2 = 13'hf68; end
            9'd7: begin c0 = 33'hfc4ddc07; c1 = 23'h3e2a58; c2 = 13'hf51; end
            9'd8: begin c0 = 33'hfbd1c47d; c1 = 23'h3ded41; c2 = 13'hf3b; end
            9'd9: begin c0 = 33'hfb5626c8; c1 = 23'h3db083; c2 = 13'hf24; end
            9'd10: begin c0 = 33'hfadb0234; c1 = 23'h3d741f; c2 = 13'hf0e; end
            9'd11: begin c0 = 33'hfa605611; c1 = 23'h3d3813; c2 = 13'hef8; end
            9'd12: begin c0 = 33'hf9e621ae; c1 = 23'h3cfc5f; c2 = 13'hee2; end
            9'd13: begin c0 = 33'hf96c645b; c1 = 23'h3cc102; c2 = 13'hecc; end
            9'd14: begin c0 = 33'hf8f31d6b; c1 = 23'h3c85fc; c2 = 13'heb7; end
            9'd15: begin c0 = 33'hf87a4c32; c1 = 23'h3c4b4c; c2 = 13'hea1; end
            9'd16: begin c0 = 33'hf801f004; c1 = 23'h3c10f0; c2 = 13'he8c; end
            9'd17: begin c0 = 33'hf78a0838; c1 = 23'h3bd6ea; c2 = 13'he77; end
            9'd18: begin c0 = 33'hf7129426; c1 = 23'h3b9d37; c2 = 13'he62; end
            9'd19: begin c0 = 33'hf69b9325; c1 = 23'h3b63d7; c2 = 13'he4e; end
            9'd20: begin c0 = 33'hf6250491; c1 = 23'h3b2acb; c2 = 13'he39; end
            9'd21: begin c0 = 33'hf5aee7c4; c1 = 23'h3af210; c2 = 13'he24; end
            9'd22: begin c0 = 33'hf5393c1c; c1 = 23'h3ab9a6; c2 = 13'he10; end
            9'd23: begin c0 = 33'hf4c400f5; c1 = 23'h3a818e; c2 = 13'hdfc; end
            9'd24: begin c0 = 33'hf44f35ae; c1 = 23'h3a49c6; c2 = 13'hde8; end
            9'd25: begin c0 = 33'hf3dad9a9; c1 = 23'h3a124d; c2 = 13'hdd4; end
            9'd26: begin c0 = 33'hf366ec45; c1 = 23'h39db23; c2 = 13'hdc1; end
            9'd27: begin c0 = 33'hf2f36ce7; c1 = 23'h39a448; c2 = 13'hdad; end
            9'd28: begin c0 = 33'hf2805af0; c1 = 23'h396dbb; c2 = 13'hd9a; end
            9'd29: begin c0 = 33'hf20db5c7; c1 = 23'h39377b; c2 = 13'hd86; end
            9'd30: begin c0 = 33'hf19b7cd1; c1 = 23'h390188; c2 = 13'hd73; end
            9'd31: begin c0 = 33'hf129af75; c1 = 23'h38cbe1; c2 = 13'hd60; end
            9'd32: begin c0 = 33'hf0b84d1b; c1 = 23'h389685; c2 = 13'hd4d; end
            9'd33: begin c0 = 33'hf047552d; c1 = 23'h386175; c2 = 13'hd3b; end
            9'd34: begin c0 = 33'hefd6c716; c1 = 23'h382caf; c2 = 13'hd28; end
            9'd35: begin c0 = 33'hef66a240; c1 = 23'h37f833; c2 = 13'hd16; end
            9'd36: begin c0 = 33'heef6e619; c1 = 23'h37c400; c2 = 13'hd04; end
            9'd37: begin c0 = 33'hee87920e; c1 = 23'h379017; c2 = 13'hcf1; end
            9'd38: begin c0 = 33'hee18a58d; c1 = 23'h375c76; c2 = 13'hcdf; end
            9'd39: begin c0 = 33'hedaa2007; c1 = 23'h37291c; c2 = 13'hccd; end
            9'd40: begin c0 = 33'hed3c00ed; c1 = 23'h36f60a; c2 = 13'hcbc; end
            9'd41: begin c0 = 33'hecce47b0; c1 = 23'h36c33f; c2 = 13'hcaa; end
            9'd42: begin c0 = 33'hec60f3c4; c1 = 23'h3690ba; c2 = 13'hc99; end
            9'd43: begin c0 = 33'hebf4049c; c1 = 23'h365e7a; c2 = 13'hc87; end
            9'd44: begin c0 = 33'heb8779ad; c1 = 23'h362c80; c2 = 13'hc76; end
            9'd45: begin c0 = 33'heb1b526d; c1 = 23'h35facb; c2 = 13'hc65; end
            9'd46: begin c0 = 33'heaaf8e53; c1 = 23'h35c95a; c2 = 13'hc54; end
            9'd47: begin c0 = 33'hea442cd7; c1 = 23'h35982d; c2 = 13'hc43; end
            9'd48: begin c0 = 33'he9d92d72; c1 = 23'h356743; c2 = 13'hc32; end
            9'd49: begin c0 = 33'he96e8f9e; c1 = 23'h35369c; c2 = 13'hc21; end
            9'd50: begin c0 = 33'he90452d5; c1 = 23'h350638; c2 = 13'hc11; end
            9'd51: begin c0 = 33'he89a7693; c1 = 23'h34d615; c2 = 13'hc00; end
            9'd52: begin c0 = 33'he830fa55; c1 = 23'h34a634; c2 = 13'hbf0; end
            9'd53: begin c0 = 33'he7c7dd98; c1 = 23'h347693; c2 = 13'hbe0; end
            9'd54: begin c0 = 33'he75f1fdc; c1 = 23'h344734; c2 = 13'hbd0; end
            9'd55: begin c0 = 33'he6f6c09f; c1 = 23'h341814; c2 = 13'hbc0; end
            9'd56: begin c0 = 33'he68ebf61; c1 = 23'h33e934; c2 = 13'hbb0; end
            9'd57: begin c0 = 33'he6271ba5; c1 = 23'h33ba93; c2 = 13'hba0; end
            9'd58: begin c0 = 33'he5bfd4ec; c1 = 23'h338c31; c2 = 13'hb91; end
            9'd59: begin c0 = 33'he558eab9; c1 = 23'h335e0d; c2 = 13'hb81; end
            9'd60: begin c0 = 33'he4f25c90; c1 = 23'h333027; c2 = 13'hb72; end
            9'd61: begin c0 = 33'he48c29f6; c1 = 23'h33027e; c2 = 13'hb63; end
            9'd62: begin c0 = 33'he4265270; c1 = 23'h32d512; c2 = 13'hb53; end
            9'd63: begin c0 = 33'he3c0d585; c1 = 23'h32a7e3; c2 = 13'hb44; end
            9'd64: begin c0 = 33'he35bb2bc; c1 = 23'h327af0; c2 = 13'hb35; end
            9'd65: begin c0 = 33'he2f6e99d; c1 = 23'h324e39; c2 = 13'hb26; end
            9'd66: begin c0 = 33'he29279b2; c1 = 23'h3221bd; c2 = 13'hb18; end
            9'd67: begin c0 = 33'he22e6283; c1 = 23'h31f57c; c2 = 13'hb09; end
            9'd68: begin c0 = 33'he1caa39c; c1 = 23'h31c975; c2 = 13'hafa; end
            9'd69: begin c0 = 33'he1673c88; c1 = 23'h319da9; c2 = 13'haec; end
            9'd70: begin c0 = 33'he1042cd4; c1 = 23'h317216; c2 = 13'hade; end
            9'd71: begin c0 = 33'he0a1740b; c1 = 23'h3146bc; c2 = 13'hacf; end
            9'd72: begin c0 = 33'he03f11bd; c1 = 23'h311b9c; c2 = 13'hac1; end
            9'd73: begin c0 = 33'hdfdd0577; c1 = 23'h30f0b4; c2 = 13'hab3; end
            9'd74: begin c0 = 33'hdf7b4ec9; c1 = 23'h30c604; c2 = 13'haa5; end
            9'd75: begin c0 = 33'hdf19ed43; c1 = 23'h309b8b; c2 = 13'ha97; end
            9'd76: begin c0 = 33'hdeb8e076; c1 = 23'h30714b; c2 = 13'ha89; end
            9'd77: begin c0 = 33'hde5827f4; c1 = 23'h304741; c2 = 13'ha7c; end
            9'd78: begin c0 = 33'hddf7c34e; c1 = 23'h301d6e; c2 = 13'ha6e; end
            9'd79: begin c0 = 33'hdd97b219; c1 = 23'h2ff3d1; c2 = 13'ha60; end
            9'd80: begin c0 = 33'hdd37f3e7; c1 = 23'h2fca6a; c2 = 13'ha53; end
            9'd81: begin c0 = 33'hdcd8884e; c1 = 23'h2fa138; c2 = 13'ha46; end
            9'd82: begin c0 = 33'hdc796ee2; c1 = 23'h2f783c; c2 = 13'ha38; end
            9'd83: begin c0 = 33'hdc1aa73a; c1 = 23'h2f4f75; c2 = 13'ha2b; end
            9'd84: begin c0 = 33'hdbbc30ed; c1 = 23'h2f26e2; c2 = 13'ha1e; end
            9'd85: begin c0 = 33'hdb5e0b91; c1 = 23'h2efe83; c2 = 13'ha11; end
            9'd86: begin c0 = 33'hdb0036c0; c1 = 23'h2ed657; c2 = 13'ha04; end
            9'd87: begin c0 = 33'hdaa2b212; c1 = 23'h2eae60; c2 = 13'h9f8; end
            9'd88: begin c0 = 33'hda457d1f; c1 = 23'h2e869b; c2 = 13'h9eb; end
            9'd89: begin c0 = 33'hd9e89784; c1 = 23'h2e5f09; c2 = 13'h9de; end
            9'd90: begin c0 = 33'hd98c00da; c1 = 23'h2e37aa; c2 = 13'h9d2; end
            9'd91: begin c0 = 33'hd92fb8bc; c1 = 23'h2e107c; c2 = 13'h9c5; end
            9'd92: begin c0 = 33'hd8d3bec8; c1 = 23'h2de980; c2 = 13'h9b9; end
            9'd93: begin c0 = 33'hd878129a; c1 = 23'h2dc2b6; c2 = 13'h9ac; end
            9'd94: begin c0 = 33'hd81cb3d0; c1 = 23'h2d9c1d; c2 = 13'h9a0; end
            9'd95: begin c0 = 33'hd7c1a207; c1 = 23'h2d75b4; c2 = 13'h994; end
            9'd96: begin c0 = 33'hd766dcdf; c1 = 23'h2d4f7c; c2 = 13'h988; end
            9'd97: begin c0 = 33'hd70c63f7; c1 = 23'h2d2974; c2 = 13'h97c; end
            9'd98: begin c0 = 33'hd6b236ef; c1 = 23'h2d039c; c2 = 13'h970; end
            9'd99: begin c0 = 33'hd6585567; c1 = 23'h2cddf3; c2 = 13'h964; end
            9'd100: begin c0 = 33'hd5febf02; c1 = 23'h2cb87a; c2 = 13'h958; end
            9'd101: begin c0 = 33'hd5a57361; c1 = 23'h2c932f; c2 = 13'h94d; end
            9'd102: begin c0 = 33'hd54c7226; c1 = 23'h2c6e13; c2 = 13'h941; end
            9'd103: begin c0 = 33'hd4f3baf5; c1 = 23'h2c4925; c2 = 13'h936; end
            9'd104: begin c0 = 33'hd49b4d72; c1 = 23'h2c2466; c2 = 13'h92a; end
            9'd105: begin c0 = 33'hd4432940; c1 = 23'h2bffd3; c2 = 13'h91f; end
            9'd106: begin c0 = 33'hd3eb4e05; c1 = 23'h2bdb6f; c2 = 13'h914; end
            9'd107: begin c0 = 33'hd393bb67; c1 = 23'h2bb737; c2 = 13'h908; end
            9'd108: begin c0 = 33'hd33c710b; c1 = 23'h2b932c; c2 = 13'h8fd; end
            9'd109: begin c0 = 33'hd2e56e99; c1 = 23'h2b6f4e; c2 = 13'h8f2; end
            9'd110: begin c0 = 33'hd28eb3b7; c1 = 23'h2b4b9c; c2 = 13'h8e7; end
            9'd111: begin c0 = 33'hd238400d; c1 = 23'h2b2815; c2 = 13'h8dc; end
            9'd112: begin c0 = 33'hd1e21344; c1 = 23'h2b04bb; c2 = 13'h8d1; end
            9'd113: begin c0 = 33'hd18c2d05; c1 = 23'h2ae18c; c2 = 13'h8c6; end
            9'd114: begin c0 = 33'hd1368cf9; c1 = 23'h2abe87; c2 = 13'h8bc; end
            9'd115: begin c0 = 33'hd0e132cb; c1 = 23'h2a9bae; c2 = 13'h8b1; end
            9'd116: begin c0 = 33'hd08c1e24; c1 = 23'h2a78ff; c2 = 13'h8a6; end
            9'd117: begin c0 = 33'hd0374eb1; c1 = 23'h2a567b; c2 = 13'h89c; end
            9'd118: begin c0 = 33'hcfe2c41c; c1 = 23'h2a3421; c2 = 13'h891; end
            9'd119: begin c0 = 33'hcf8e7e13; c1 = 23'h2a11f0; c2 = 13'h887; end
            9'd120: begin c0 = 33'hcf3a7c42; c1 = 23'h29efe9; c2 = 13'h87d; end
            9'd121: begin c0 = 33'hcee6be55; c1 = 23'h29ce0b; c2 = 13'h872; end
            9'd122: begin c0 = 33'hce9343fc; c1 = 23'h29ac56; c2 = 13'h868; end
            9'd123: begin c0 = 33'hce400ce4; c1 = 23'h298ac9; c2 = 13'h85e; end
            9'd124: begin c0 = 33'hcded18bc; c1 = 23'h296965; c2 = 13'h854; end
            9'd125: begin c0 = 33'hcd9a6734; c1 = 23'h29482a; c2 = 13'h84a; end
            9'd126: begin c0 = 33'hcd47f7fb; c1 = 23'h292716; c2 = 13'h840; end
            9'd127: begin c0 = 33'hccf5cac2; c1 = 23'h29062a; c2 = 13'h836; end
            9'd128: begin c0 = 33'hcca3df3a; c1 = 23'h28e565; c2 = 13'h82c; end
            9'd129: begin c0 = 33'hcc523513; c1 = 23'h28c4c8; c2 = 13'h822; end
            9'd130: begin c0 = 33'hcc00cc01; c1 = 23'h28a451; c2 = 13'h819; end
            9'd131: begin c0 = 33'hcbafa3b4; c1 = 23'h288402; c2 = 13'h80f; end
            9'd132: begin c0 = 33'hcb5ebbe1; c1 = 23'h2863d8; c2 = 13'h806; end
            9'd133: begin c0 = 33'hcb0e143a; c1 = 23'h2843d5; c2 = 13'h7fc; end
            9'd134: begin c0 = 33'hcabdac73; c1 = 23'h2823f8; c2 = 13'h7f3; end
            9'd135: begin c0 = 33'hca6d8440; c1 = 23'h280441; c2 = 13'h7e9; end
            9'd136: begin c0 = 33'hca1d9b56; c1 = 23'h27e4af; c2 = 13'h7e0; end
            9'd137: begin c0 = 33'hc9cdf16b; c1 = 23'h27c543; c2 = 13'h7d6; end
            9'd138: begin c0 = 33'hc97e8633; c1 = 23'h27a5fb; c2 = 13'h7cd; end
            9'd139: begin c0 = 33'hc92f5965; c1 = 23'h2786d9; c2 = 13'h7c4; end
            9'd140: begin c0 = 33'hc8e06ab7; c1 = 23'h2767db; c2 = 13'h7bb; end
            9'd141: begin c0 = 33'hc891b9e1; c1 = 23'h274901; c2 = 13'h7b2; end
            9'd142: begin c0 = 33'hc843469a; c1 = 23'h272a4c; c2 = 13'h7a9; end
            9'd143: begin c0 = 33'hc7f51099; c1 = 23'h270bbb; c2 = 13'h7a0; end
            9'd144: begin c0 = 33'hc7a71797; c1 = 23'h26ed4d; c2 = 13'h797; end
            9'd145: begin c0 = 33'hc7595b4e; c1 = 23'h26cf03; c2 = 13'h78e; end
            9'd146: begin c0 = 33'hc70bdb75; c1 = 23'h26b0dc; c2 = 13'h785; end
            9'd147: begin c0 = 33'hc6be97c7; c1 = 23'h2692d8; c2 = 13'h77d; end
            9'd148: begin c0 = 33'hc6718ffd; c1 = 23'h2674f7; c2 = 13'h774; end
            9'd149: begin c0 = 33'hc624c3d2; c1 = 23'h265739; c2 = 13'h76b; end
            9'd150: begin c0 = 33'hc5d83302; c1 = 23'h26399d; c2 = 13'h763; end
            9'd151: begin c0 = 33'hc58bdd46; c1 = 23'h261c24; c2 = 13'h75a; end
            9'd152: begin c0 = 33'hc53fc25c; c1 = 23'h25fecc; c2 = 13'h752; end
            9'd153: begin c0 = 33'hc4f3e1ff; c1 = 23'h25e197; c2 = 13'h749; end
            9'd154: begin c0 = 33'hc4a83beb; c1 = 23'h25c483; c2 = 13'h741; end
            9'd155: begin c0 = 33'hc45ccfde; c1 = 23'h25a790; c2 = 13'h738; end
            9'd156: begin c0 = 33'hc4119d95; c1 = 23'h258abf; c2 = 13'h730; end
            9'd157: begin c0 = 33'hc3c6a4ce; c1 = 23'h256e0e; c2 = 13'h728; end
            9'd158: begin c0 = 33'hc37be546; c1 = 23'h25517f; c2 = 13'h720; end
            9'd159: begin c0 = 33'hc3315ebd; c1 = 23'h253510; c2 = 13'h718; end
            9'd160: begin c0 = 33'hc2e710f1; c1 = 23'h2518c2; c2 = 13'h710; end
            9'd161: begin c0 = 33'hc29cfba1; c1 = 23'h24fc93; c2 = 13'h708; end
            9'd162: begin c0 = 33'hc2531e8e; c1 = 23'h24e085; c2 = 13'h700; end
            9'd163: begin c0 = 33'hc2097976; c1 = 23'h24c497; c2 = 13'h6f8; end
            9'd164: begin c0 = 33'hc1c00c1c; c1 = 23'h24a8c9; c2 = 13'h6f0; end
            9'd165: begin c0 = 33'hc176d63f; c1 = 23'h248d1a; c2 = 13'h6e8; end
            9'd166: begin c0 = 33'hc12dd7a1; c1 = 23'h24718a; c2 = 13'h6e0; end
            9'd167: begin c0 = 33'hc0e51003; c1 = 23'h245619; c2 = 13'h6d8; end
            9'd168: begin c0 = 33'hc09c7f27; c1 = 23'h243ac8; c2 = 13'h6d1; end
            9'd169: begin c0 = 33'hc05424d0; c1 = 23'h241f95; c2 = 13'h6c9; end
            9'd170: begin c0 = 33'hc00c00c0; c1 = 23'h240480; c2 = 13'h6c1; end
            9'd171: begin c0 = 33'hbfc412ba; c1 = 23'h23e98b; c2 = 13'h6ba; end
            9'd172: begin c0 = 33'hbf7c5a82; c1 = 23'h23ceb3; c2 = 13'h6b2; end
            9'd173: begin c0 = 33'hbf34d7db; c1 = 23'h23b3f9; c2 = 13'h6ab; end
            9'd174: begin c0 = 33'hbeed8a89; c1 = 23'h23995e; c2 = 13'h6a3; end
            9'd175: begin c0 = 33'hbea67251; c1 = 23'h237edf; c2 = 13'h69c; end
            9'd176: begin c0 = 33'hbe5f8ef7; c1 = 23'h23647f; c2 = 13'h694; end
            9'd177: begin c0 = 33'hbe18e041; c1 = 23'h234a3c; c2 = 13'h68d; end
            9'd178: begin c0 = 33'hbdd265f5; c1 = 23'h233016; c2 = 13'h686; end
            9'd179: begin c0 = 33'hbd8c1fd7; c1 = 23'h23160d; c2 = 13'h67f; end
            9'd180: begin c0 = 33'hbd460dae; c1 = 23'h22fc21; c2 = 13'h677; end
            9'd181: begin c0 = 33'hbd002f40; c1 = 23'h22e251; c2 = 13'h670; end
            9'd182: begin c0 = 33'hbcba8455; c1 = 23'h22c89f; c2 = 13'h669; end
            9'd183: begin c0 = 33'hbc750cb3; c1 = 23'h22af08; c2 = 13'h662; end
            9'd184: begin c0 = 33'hbc2fc822; c1 = 23'h22958e; c2 = 13'h65b; end
            9'd185: begin c0 = 33'hbbeab669; c1 = 23'h227c2f; c2 = 13'h654; end
            9'd186: begin c0 = 33'hbba5d752; c1 = 23'h2262ed; c2 = 13'h64d; end
            9'd187: begin c0 = 33'hbb612aa3; c1 = 23'h2249c6; c2 = 13'h646; end
            9'd188: begin c0 = 33'hbb1cb026; c1 = 23'h2230bb; c2 = 13'h63f; end
            9'd189: begin c0 = 33'hbad867a4; c1 = 23'h2217cb; c2 = 13'h639; end
            9'd190: begin c0 = 33'hba9450e6; c1 = 23'h21fef7; c2 = 13'h632; end
            9'd191: begin c0 = 33'hba506bb6; c1 = 23'h21e63d; c2 = 13'h62b; end
            9'd192: begin c0 = 33'hba0cb7df; c1 = 23'h21cd9f; c2 = 13'h624; end
            9'd193: begin c0 = 33'hb9c93529; c1 = 23'h21b51b; c2 = 13'h61e; end
            9'd194: begin c0 = 33'hb985e360; c1 = 23'h219cb2; c2 = 13'h617; end
            9'd195: begin c0 = 33'hb942c24f; c1 = 23'h218464; c2 = 13'h610; end
            9'd196: begin c0 = 33'hb8ffd1c0; c1 = 23'h216c2f; c2 = 13'h60a; end
            9'd197: begin c0 = 33'hb8bd1180; c1 = 23'h215415; c2 = 13'h603; end
            9'd198: begin c0 = 33'hb87a815a; c1 = 23'h213c15; c2 = 13'h5fd; end
            9'd199: begin c0 = 33'hb838211a; c1 = 23'h21242f; c2 = 13'h5f6; end
            9'd200: begin c0 = 33'hb7f5f08d; c1 = 23'h210c63; c2 = 13'h5f0; end
            9'd201: begin c0 = 33'hb7b3ef7f; c1 = 23'h20f4b0; c2 = 13'h5ea; end
            9'd202: begin c0 = 33'hb7721dbd; c1 = 23'h20dd16; c2 = 13'h5e3; end
            9'd203: begin c0 = 33'hb7307b15; c1 = 23'h20c596; c2 = 13'h5dd; end
            9'd204: begin c0 = 33'hb6ef0753; c1 = 23'h20ae2f; c2 = 13'h5d7; end
            9'd205: begin c0 = 33'hb6adc246; c1 = 23'h2096e2; c2 = 13'h5d0; end
            9'd206: begin c0 = 33'hb66cabbc; c1 = 23'h207fad; c2 = 13'h5ca; end
            9'd207: begin c0 = 33'hb62bc383; c1 = 23'h206890; c2 = 13'h5c4; end
            9'd208: begin c0 = 33'hb5eb096a; c1 = 23'h20518d; c2 = 13'h5be; end
            9'd209: begin c0 = 33'hb5aa7d40; c1 = 23'h203aa2; c2 = 13'h5b8; end
            9'd210: begin c0 = 33'hb56a1ed4; c1 = 23'h2023cf; c2 = 13'h5b2; end
            9'd211: begin c0 = 33'hb529edf4; c1 = 23'h200d14; c2 = 13'h5ac; end
            9'd212: begin c0 = 33'hb4e9ea72; c1 = 23'h1ff672; c2 = 13'h5a6; end
            9'd213: begin c0 = 33'hb4aa141d; c1 = 23'h1fdfe7; c2 = 13'h5a0; end
            9'd214: begin c0 = 33'hb46a6ac5; c1 = 23'h1fc975; c2 = 13'h59a; end
            9'd215: begin c0 = 33'hb42aee3b; c1 = 23'h1fb31a; c2 = 13'h594; end
            9'd216: begin c0 = 33'hb3eb9e4f; c1 = 23'h1f9cd6; c2 = 13'h58e; end
            9'd217: begin c0 = 33'hb3ac7ad3; c1 = 23'h1f86aa; c2 = 13'h588; end
            9'd218: begin c0 = 33'hb36d8398; c1 = 23'h1f7095; c2 = 13'h582; end
            9'd219: begin c0 = 33'hb32eb86f; c1 = 23'h1f5a98; c2 = 13'h57d; end
            9'd220: begin c0 = 33'hb2f0192a; c1 = 23'h1f44b1; c2 = 13'h577; end
            9'd221: begin c0 = 33'hb2b1a59b; c1 = 23'h1f2ee1; c2 = 13'h571; end
            9'd222: begin c0 = 33'hb2735d95; c1 = 23'h1f1929; c2 = 13'h56b; end
            9'd223: begin c0 = 33'hb23540ea; c1 = 23'h1f0386; c2 = 13'h566; end
            9'd224: begin c0 = 33'hb1f74f6d; c1 = 23'h1eedfb; c2 = 13'h560; end
            9'd225: begin c0 = 33'hb1b988f0; c1 = 23'h1ed885; c2 = 13'h55b; end
            9'd226: begin c0 = 33'hb17bed48; c1 = 23'h1ec327; c2 = 13'h555; end
            9'd227: begin c0 = 33'hb13e7c47; c1 = 23'h1eadde; c2 = 13'h54f; end
            9'd228: begin c0 = 33'hb10135c2; c1 = 23'h1e98ab; c2 = 13'h54a; end
            9'd229: begin c0 = 33'hb0c4198c; c1 = 23'h1e838e; c2 = 13'h544; end
            9'd230: begin c0 = 33'hb087277a; c1 = 23'h1e6e87; c2 = 13'h53f; end
            9'd231: begin c0 = 33'hb04a5f60; c1 = 23'h1e5996; c2 = 13'h53a; end
            9'd232: begin c0 = 33'hb00dc113; c1 = 23'h1e44bb; c2 = 13'h534; end
            9'd233: begin c0 = 33'hafd14c68; c1 = 23'h1e2ff4; c2 = 13'h52f; end
            9'd234: begin c0 = 33'haf950133; c1 = 23'h1e1b44; c2 = 13'h52a; end
            9'd235: begin c0 = 33'haf58df4b; c1 = 23'h1e06a8; c2 = 13'h524; end
            9'd236: begin c0 = 33'haf1ce685; c1 = 23'h1df222; c2 = 13'h51f; end
            9'd237: begin c0 = 33'haee116b7; c1 = 23'h1dddb0; c2 = 13'h51a; end
            9'd238: begin c0 = 33'haea56fb6; c1 = 23'h1dc954; c2 = 13'h515; end
            9'd239: begin c0 = 33'hae69f15a; c1 = 23'h1db50c; c2 = 13'h50f; end
            9'd240: begin c0 = 33'hae2e9b79; c1 = 23'h1da0d9; c2 = 13'h50a; end
            9'd241: begin c0 = 33'hadf36de9; c1 = 23'h1d8cbb; c2 = 13'h505; end
            9'd242: begin c0 = 33'hadb86881; c1 = 23'h1d78b1; c2 = 13'h500; end
            9'd243: begin c0 = 33'had7d8b19; c1 = 23'h1d64bb; c2 = 13'h4fb; end
            9'd244: begin c0 = 33'had42d588; c1 = 23'h1d50da; c2 = 13'h4f6; end
            9'd245: begin c0 = 33'had0847a5; c1 = 23'h1d3d0c; c2 = 13'h4f1; end
            9'd246: begin c0 = 33'haccde149; c1 = 23'h1d2953; c2 = 13'h4ec; end
            9'd247: begin c0 = 33'hac93a24c; c1 = 23'h1d15ae; c2 = 13'h4e7; end
            9'd248: begin c0 = 33'hac598a85; c1 = 23'h1d021c; c2 = 13'h4e2; end
            9'd249: begin c0 = 33'hac1f99cd; c1 = 23'h1cee9f; c2 = 13'h4dd; end
            9'd250: begin c0 = 33'habe5cffd; c1 = 23'h1cdb35; c2 = 13'h4d8; end
            9'd251: begin c0 = 33'habac2cee; c1 = 23'h1cc7de; c2 = 13'h4d3; end
            9'd252: begin c0 = 33'hab72b079; c1 = 23'h1cb49b; c2 = 13'h4ce; end
            9'd253: begin c0 = 33'hab395a76; c1 = 23'h1ca16b; c2 = 13'h4ca; end
            9'd254: begin c0 = 33'hab002ac0; c1 = 23'h1c8e4e; c2 = 13'h4c5; end
            9'd255: begin c0 = 33'haac72130; c1 = 23'h1c7b45; c2 = 13'h4c0; end
            9'd256: begin c0 = 33'haa8e3da0; c1 = 23'h1c684e; c2 = 13'h4bb; end
            9'd257: begin c0 = 33'haa557feb; c1 = 23'h1c556b; c2 = 13'h4b7; end
            9'd258: begin c0 = 33'haa1ce7e9; c1 = 23'h1c429a; c2 = 13'h4b2; end
            9'd259: begin c0 = 33'ha9e47577; c1 = 23'h1c2fdc; c2 = 13'h4ad; end
            9'd260: begin c0 = 33'ha9ac286e; c1 = 23'h1c1d30; c2 = 13'h4a9; end
            9'd261: begin c0 = 33'ha97400a9; c1 = 23'h1c0a97; c2 = 13'h4a4; end
            9'd262: begin c0 = 33'ha93bfe04; c1 = 23'h1bf811; c2 = 13'h49f; end
            9'd263: begin c0 = 33'ha904205a; c1 = 23'h1be59d; c2 = 13'h49b; end
            9'd264: begin c0 = 33'ha8cc6785; c1 = 23'h1bd33b; c2 = 13'h496; end
            9'd265: begin c0 = 33'ha894d363; c1 = 23'h1bc0eb; c2 = 13'h492; end
            9'd266: begin c0 = 33'ha85d63cd; c1 = 23'h1baead; c2 = 13'h48d; end
            9'd267: begin c0 = 33'ha82618a2; c1 = 23'h1b9c81; c2 = 13'h489; end
            9'd268: begin c0 = 33'ha7eef1bb; c1 = 23'h1b8a68; c2 = 13'h484; end
            9'd269: begin c0 = 33'ha7b7eef7; c1 = 23'h1b785f; c2 = 13'h480; end
            9'd270: begin c0 = 33'ha7811032; c1 = 23'h1b6669; c2 = 13'h47b; end
            9'd271: begin c0 = 33'ha74a5547; c1 = 23'h1b5484; c2 = 13'h477; end
            9'd272: begin c0 = 33'ha713be15; c1 = 23'h1b42b1; c2 = 13'h473; end
            9'd273: begin c0 = 33'ha6dd4a78; c1 = 23'h1b30ef; c2 = 13'h46e; end
            9'd274: begin c0 = 33'ha6a6fa4e; c1 = 23'h1b1f3e; c2 = 13'h46a; end
            9'd275: begin c0 = 33'ha670cd73; c1 = 23'h1b0d9f; c2 = 13'h466; end
            9'd276: begin c0 = 33'ha63ac3c6; c1 = 23'h1afc11; c2 = 13'h461; end
            9'd277: begin c0 = 33'ha604dd24; c1 = 23'h1aea94; c2 = 13'h45d; end
            9'd278: begin c0 = 33'ha5cf196c; c1 = 23'h1ad928; c2 = 13'h459; end
            9'd279: begin c0 = 33'ha599787b; c1 = 23'h1ac7cc; c2 = 13'h455; end
            9'd280: begin c0 = 33'ha563fa2f; c1 = 23'h1ab682; c2 = 13'h451; end
            9'd281: begin c0 = 33'ha52e9e68; c1 = 23'h1aa548; c2 = 13'h44c; end
            9'd282: begin c0 = 33'ha4f96504; c1 = 23'h1a941f; c2 = 13'h448; end
            9'd283: begin c0 = 33'ha4c44de1; c1 = 23'h1a8307; c2 = 13'h444; end
            9'd284: begin c0 = 33'ha48f58de; c1 = 23'h1a71ff; c2 = 13'h440; end
            9'd285: begin c0 = 33'ha45a85dc; c1 = 23'h1a6107; c2 = 13'h43c; end
            9'd286: begin c0 = 33'ha425d4b8; c1 = 23'h1a5020; c2 = 13'h438; end
            9'd287: begin c0 = 33'ha3f14553; c1 = 23'h1a3f48; c2 = 13'h434; end
            9'd288: begin c0 = 33'ha3bcd78c; c1 = 23'h1a2e81; c2 = 13'h430; end
            9'd289: begin c0 = 33'ha3888b42; c1 = 23'h1a1dcb; c2 = 13'h42c; end
            9'd290: begin c0 = 33'ha3546057; c1 = 23'h1a0d24; c2 = 13'h428; end
            9'd291: begin c0 = 33'ha32056a9; c1 = 23'h19fc8d; c2 = 13'h424; end
            9'd292: begin c0 = 33'ha2ec6e1a; c1 = 23'h19ec05; c2 = 13'h420; end
            9'd293: begin c0 = 33'ha2b8a689; c1 = 23'h19db8e; c2 = 13'h41c; end
            9'd294: begin c0 = 33'ha284ffd7; c1 = 23'h19cb26; c2 = 13'h418; end
            9'd295: begin c0 = 33'ha25179e6; c1 = 23'h19bace; c2 = 13'h414; end
            9'd296: begin c0 = 33'ha21e1495; c1 = 23'h19aa85; c2 = 13'h410; end
            9'd297: begin c0 = 33'ha1eacfc6; c1 = 23'h199a4c; c2 = 13'h40c; end
            9'd298: begin c0 = 33'ha1b7ab5a; c1 = 23'h198a22; c2 = 13'h409; end
            9'd299: begin c0 = 33'ha184a732; c1 = 23'h197a08; c2 = 13'h405; end
            9'd300: begin c0 = 33'ha151c331; c1 = 23'h1969fc; c2 = 13'h401; end
            9'd301: begin c0 = 33'ha11eff37; c1 = 23'h195a00; c2 = 13'h3fd; end
            9'd302: begin c0 = 33'ha0ec5b26; c1 = 23'h194a13; c2 = 13'h3f9; end
            9'd303: begin c0 = 33'ha0b9d6e0; c1 = 23'h193a35; c2 = 13'h3f6; end
            9'd304: begin c0 = 33'ha0877248; c1 = 23'h192a66; c2 = 13'h3f2; end
            9'd305: begin c0 = 33'ha0552d40; c1 = 23'h191aa5; c2 = 13'h3ee; end
            9'd306: begin c0 = 33'ha02307aa; c1 = 23'h190af4; c2 = 13'h3eb; end
            9'd307: begin c0 = 33'h9ff10168; c1 = 23'h18fb51; c2 = 13'h3e7; end
            9'd308: begin c0 = 33'h9fbf1a5d; c1 = 23'h18ebbc; c2 = 13'h3e3; end
            9'd309: begin c0 = 33'h9f8d526d; c1 = 23'h18dc37; c2 = 13'h3e0; end
            9'd310: begin c0 = 33'h9f5ba979; c1 = 23'h18ccbf; c2 = 13'h3dc; end
            9'd311: begin c0 = 33'h9f2a1f66; c1 = 23'h18bd56; c2 = 13'h3d8; end
            9'd312: begin c0 = 33'h9ef8b416; c1 = 23'h18adfc; c2 = 13'h3d5; end
            9'd313: begin c0 = 33'h9ec7676c; c1 = 23'h189eb0; c2 = 13'h3d1; end
            9'd314: begin c0 = 33'h9e96394d; c1 = 23'h188f72; c2 = 13'h3ce; end
            9'd315: begin c0 = 33'h9e65299c; c1 = 23'h188042; c2 = 13'h3ca; end
            9'd316: begin c0 = 33'h9e34383d; c1 = 23'h187120; c2 = 13'h3c7; end
            9'd317: begin c0 = 33'h9e036513; c1 = 23'h18620c; c2 = 13'h3c3; end
            9'd318: begin c0 = 33'h9dd2b002; c1 = 23'h185306; c2 = 13'h3c0; end
            9'd319: begin c0 = 33'h9da218f0; c1 = 23'h18440e; c2 = 13'h3bc; end
            9'd320: begin c0 = 33'h9d719fc0; c1 = 23'h183524; c2 = 13'h3b9; end
            9'd321: begin c0 = 33'h9d414457; c1 = 23'h182648; c2 = 13'h3b5; end
            9'd322: begin c0 = 33'h9d110698; c1 = 23'h181779; c2 = 13'h3b2; end
            9'd323: begin c0 = 33'h9ce0e66a; c1 = 23'h1808b8; c2 = 13'h3af; end
            9'd324: begin c0 = 33'h9cb0e3b1; c1 = 23'h17fa04; c2 = 13'h3ab; end
            9'd325: begin c0 = 33'h9c80fe52; c1 = 23'h17eb5e; c2 = 13'h3a8; end
            9'd326: begin c0 = 33'h9c513631; c1 = 23'h17dcc5; c2 = 13'h3a5; end
            9'd327: begin c0 = 33'h9c218b35; c1 = 23'h17ce3a; c2 = 13'h3a1; end
            9'd328: begin c0 = 33'h9bf1fd42; c1 = 23'h17bfbb; c2 = 13'h39e; end
            9'd329: begin c0 = 33'h9bc28c3f; c1 = 23'h17b14a; c2 = 13'h39b; end
            9'd330: begin c0 = 33'h9b933810; c1 = 23'h17a2e7; c2 = 13'h397; end
            9'd331: begin c0 = 33'h9b64009b; c1 = 23'h179490; c2 = 13'h394; end
            9'd332: begin c0 = 33'h9b34e5c7; c1 = 23'h178646; c2 = 13'h391; end
            9'd333: begin c0 = 33'h9b05e77a; c1 = 23'h17780a; c2 = 13'h38e; end
            9'd334: begin c0 = 33'h9ad70598; c1 = 23'h1769da; c2 = 13'h38a; end
            9'd335: begin c0 = 33'h9aa8400a; c1 = 23'h175bb7; c2 = 13'h387; end
            9'd336: begin c0 = 33'h9a7996b4; c1 = 23'h174da1; c2 = 13'h384; end
            9'd337: begin c0 = 33'h9a4b097e; c1 = 23'h173f97; c2 = 13'h381; end
            9'd338: begin c0 = 33'h9a1c984e; c1 = 23'h17319b; c2 = 13'h37e; end
            9'd339: begin c0 = 33'h99ee430b; c1 = 23'h1723aa; c2 = 13'h37a; end
            9'd340: begin c0 = 33'h99c0099c; c1 = 23'h1715c7; c2 = 13'h377; end
            9'd341: begin c0 = 33'h9991ebe7; c1 = 23'h1707f0; c2 = 13'h374; end
            9'd342: begin c0 = 33'h9963e9d5; c1 = 23'h16fa25; c2 = 13'h371; end
            9'd343: begin c0 = 33'h9936034b; c1 = 23'h16ec67; c2 = 13'h36e; end
            9'd344: begin c0 = 33'h99083831; c1 = 23'h16deb5; c2 = 13'h36b; end
            9'd345: begin c0 = 33'h98da886f; c1 = 23'h16d10f; c2 = 13'h368; end
            9'd346: begin c0 = 33'h98acf3ec; c1 = 23'h16c376; c2 = 13'h365; end
            9'd347: begin c0 = 33'h987f7a90; c1 = 23'h16b5e8; c2 = 13'h362; end
            9'd348: begin c0 = 33'h98521c43; c1 = 23'h16a867; c2 = 13'h35f; end
            9'd349: begin c0 = 33'h9824d8ed; c1 = 23'h169af2; c2 = 13'h35c; end
            9'd350: begin c0 = 33'h97f7b074; c1 = 23'h168d88; c2 = 13'h359; end
            9'd351: begin c0 = 33'h97caa2c3; c1 = 23'h16802b; c2 = 13'h356; end
            9'd352: begin c0 = 33'h979dafc0; c1 = 23'h1672da; c2 = 13'h353; end
            9'd353: begin c0 = 33'h9770d754; c1 = 23'h166594; c2 = 13'h350; end
            9'd354: begin c0 = 33'h97441968; c1 = 23'h16585a; c2 = 13'h34d; end
            9'd355: begin c0 = 33'h971775e5; c1 = 23'h164b2c; c2 = 13'h34a; end
            9'd356: begin c0 = 33'h96eaecb1; c1 = 23'h163e09; c2 = 13'h347; end
            9'd357: begin c0 = 33'h96be7db8; c1 = 23'h1630f2; c2 = 13'h344; end
            9'd358: begin c0 = 33'h969228e1; c1 = 23'h1623e7; c2 = 13'h341; end
            9'd359: begin c0 = 33'h9665ee15; c1 = 23'h1616e7; c2 = 13'h33f; end
            9'd360: begin c0 = 33'h9639cd3d; c1 = 23'h1609f2; c2 = 13'h33c; end
            9'd361: begin c0 = 33'h960dc644; c1 = 23'h15fd09; c2 = 13'h339; end
            9'd362: begin c0 = 33'h95e1d911; c1 = 23'h15f02b; c2 = 13'h336; end
            9'd363: begin c0 = 33'h95b6058e; c1 = 23'h15e359; c2 = 13'h333; end
            9'd364: begin c0 = 33'h958a4ba5; c1 = 23'h15d692; c2 = 13'h330; end
            9'd365: begin c0 = 33'h955eab40; c1 = 23'h15c9d6; c2 = 13'h32e; end
            9'd366: begin c0 = 33'h95332448; c1 = 23'h15bd25; c2 = 13'h32b; end
            9'd367: begin c0 = 33'h9507b6a6; c1 = 23'h15b07f; c2 = 13'h328; end
            9'd368: begin c0 = 33'h94dc6245; c1 = 23'h15a3e4; c2 = 13'h325; end
            9'd369: begin c0 = 33'h94b12710; c1 = 23'h159754; c2 = 13'h323; end
            9'd370: begin c0 = 33'h948604ee; c1 = 23'h158acf; c2 = 13'h320; end
            9'd371: begin c0 = 33'h945afbcc; c1 = 23'h157e55; c2 = 13'h31d; end
            9'd372: begin c0 = 33'h94300b94; c1 = 23'h1571e6; c2 = 13'h31a; end
            9'd373: begin c0 = 33'h9405342f; c1 = 23'h156581; c2 = 13'h318; end
            9'd374: begin c0 = 33'h93da7588; c1 = 23'h155927; c2 = 13'h315; end
            9'd375: begin c0 = 33'h93afcf8a; c1 = 23'h154cd8; c2 = 13'h312; end
            9'd376: begin c0 = 33'h93854220; c1 = 23'h154094; c2 = 13'h310; end
            9'd377: begin c0 = 33'h935acd34; c1 = 23'h15345a; c2 = 13'h30d; end
            9'd378: begin c0 = 33'h933070b1; c1 = 23'h15282b; c2 = 13'h30b; end
            9'd379: begin c0 = 33'h93062c82; c1 = 23'h151c06; c2 = 13'h308; end
            9'd380: begin c0 = 33'h92dc0093; c1 = 23'h150feb; c2 = 13'h305; end
            9'd381: begin c0 = 33'h92b1ecce; c1 = 23'h1503db; c2 = 13'h303; end
            9'd382: begin c0 = 33'h9287f11e; c1 = 23'h14f7d6; c2 = 13'h300; end
            9'd383: begin c0 = 33'h925e0d70; c1 = 23'h14ebda; c2 = 13'h2fe; end
            9'd384: begin c0 = 33'h923441ad; c1 = 23'h14dfe9; c2 = 13'h2fb; end
            9'd385: begin c0 = 33'h920a8dc3; c1 = 23'h14d403; c2 = 13'h2f8; end
            9'd386: begin c0 = 33'h91e0f19d; c1 = 23'h14c826; c2 = 13'h2f6; end
            9'd387: begin c0 = 33'h91b76d25; c1 = 23'h14bc53; c2 = 13'h2f3; end
            9'd388: begin c0 = 33'h918e0049; c1 = 23'h14b08b; c2 = 13'h2f1; end
            9'd389: begin c0 = 33'h9164aaf3; c1 = 23'h14a4cc; c2 = 13'h2ee; end
            9'd390: begin c0 = 33'h913b6d11; c1 = 23'h149918; c2 = 13'h2ec; end
            9'd391: begin c0 = 33'h9112468d; c1 = 23'h148d6d; c2 = 13'h2e9; end
            9'd392: begin c0 = 33'h90e93755; c1 = 23'h1481cd; c2 = 13'h2e7; end
            9'd393: begin c0 = 33'h90c03f54; c1 = 23'h147636; c2 = 13'h2e4; end
            9'd394: begin c0 = 33'h90975e77; c1 = 23'h146aa9; c2 = 13'h2e2; end
            9'd395: begin c0 = 33'h906e94aa; c1 = 23'h145f26; c2 = 13'h2e0; end
            9'd396: begin c0 = 33'h9045e1d9; c1 = 23'h1453ac; c2 = 13'h2dd; end
            9'd397: begin c0 = 33'h901d45f2; c1 = 23'h14483d; c2 = 13'h2db; end
            9'd398: begin c0 = 33'h8ff4c0e1; c1 = 23'h143cd6; c2 = 13'h2d8; end
            9'd399: begin c0 = 33'h8fcc5292; c1 = 23'h14317a; c2 = 13'h2d6; end
            9'd400: begin c0 = 33'h8fa3faf3; c1 = 23'h142627; c2 = 13'h2d4; end
            9'd401: begin c0 = 33'h8f7bb9f1; c1 = 23'h141add; c2 = 13'h2d1; end
            9'd402: begin c0 = 33'h8f538f77; c1 = 23'h140f9d; c2 = 13'h2cf; end
            9'd403: begin c0 = 33'h8f2b7b75; c1 = 23'h140467; c2 = 13'h2cc; end
            9'd404: begin c0 = 33'h8f037dd6; c1 = 23'h13f93a; c2 = 13'h2ca; end
            9'd405: begin c0 = 33'h8edb9688; c1 = 23'h13ee16; c2 = 13'h2c8; end
            9'd406: begin c0 = 33'h8eb3c578; c1 = 23'h13e2fb; c2 = 13'h2c5; end
            9'd407: begin c0 = 33'h8e8c0a94; c1 = 23'h13d7ea; c2 = 13'h2c3; end
            9'd408: begin c0 = 33'h8e6465ca; c1 = 23'h13cce2; c2 = 13'h2c1; end
            9'd409: begin c0 = 33'h8e3cd706; c1 = 23'h13c1e3; c2 = 13'h2bf; end
            9'd410: begin c0 = 33'h8e155e37; c1 = 23'h13b6ee; c2 = 13'h2bc; end
            9'd411: begin c0 = 33'h8dedfb4a; c1 = 23'h13ac01; c2 = 13'h2ba; end
            9'd412: begin c0 = 33'h8dc6ae2d; c1 = 23'h13a11e; c2 = 13'h2b8; end
            9'd413: begin c0 = 33'h8d9f76ce; c1 = 23'h139643; c2 = 13'h2b5; end
            9'd414: begin c0 = 33'h8d78551a; c1 = 23'h138b72; c2 = 13'h2b3; end
            9'd415: begin c0 = 33'h8d514901; c1 = 23'h1380a9; c2 = 13'h2b1; end
            9'd416: begin c0 = 33'h8d2a5270; c1 = 23'h1375e9; c2 = 13'h2af; end
            9'd417: begin c0 = 33'h8d037156; c1 = 23'h136b33; c2 = 13'h2ad; end
            9'd418: begin c0 = 33'h8cdca59f; c1 = 23'h136085; c2 = 13'h2aa; end
            9'd419: begin c0 = 33'h8cb5ef3c; c1 = 23'h1355e0; c2 = 13'h2a8; end
            9'd420: begin c0 = 33'h8c8f4e1b; c1 = 23'h134b43; c2 = 13'h2a6; end
            9'd421: begin c0 = 33'h8c68c229; c1 = 23'h1340b0; c2 = 13'h2a4; end
            9'd422: begin c0 = 33'h8c424b56; c1 = 23'h133625; c2 = 13'h2a2; end
            9'd423: begin c0 = 33'h8c1be990; c1 = 23'h132ba3; c2 = 13'h29f; end
            9'd424: begin c0 = 33'h8bf59cc5; c1 = 23'h132129; c2 = 13'h29d; end
            9'd425: begin c0 = 33'h8bcf64e6; c1 = 23'h1316b8; c2 = 13'h29b; end
            9'd426: begin c0 = 33'h8ba941e0; c1 = 23'h130c4f; c2 = 13'h299; end
            9'd427: begin c0 = 33'h8b8333a3; c1 = 23'h1301ef; c2 = 13'h297; end
            9'd428: begin c0 = 33'h8b5d3a1d; c1 = 23'h12f798; c2 = 13'h295; end
            9'd429: begin c0 = 33'h8b37553e; c1 = 23'h12ed49; c2 = 13'h293; end
            9'd430: begin c0 = 33'h8b1184f5; c1 = 23'h12e302; c2 = 13'h291; end
            9'd431: begin c0 = 33'h8aebc931; c1 = 23'h12d8c4; c2 = 13'h28f; end
            9'd432: begin c0 = 33'h8ac621e1; c1 = 23'h12ce8d; c2 = 13'h28c; end
            9'd433: begin c0 = 33'h8aa08ef6; c1 = 23'h12c460; c2 = 13'h28a; end
            9'd434: begin c0 = 33'h8a7b105d; c1 = 23'h12ba3a; c2 = 13'h288; end
            9'd435: begin c0 = 33'h8a55a607; c1 = 23'h12b01d; c2 = 13'h286; end
            9'd436: begin c0 = 33'h8a304fe4; c1 = 23'h12a608; c2 = 13'h284; end
            9'd437: begin c0 = 33'h8a0b0de3; c1 = 23'h129bfb; c2 = 13'h282; end
            9'd438: begin c0 = 33'h89e5dff3; c1 = 23'h1291f6; c2 = 13'h280; end
            9'd439: begin c0 = 33'h89c0c605; c1 = 23'h1287f9; c2 = 13'h27e; end
            9'd440: begin c0 = 33'h899bc009; c1 = 23'h127e05; c2 = 13'h27c; end
            9'd441: begin c0 = 33'h8976cded; c1 = 23'h127418; c2 = 13'h27a; end
            9'd442: begin c0 = 33'h8951efa4; c1 = 23'h126a33; c2 = 13'h278; end
            9'd443: begin c0 = 33'h892d251b; c1 = 23'h126056; c2 = 13'h276; end
            9'd444: begin c0 = 33'h89086e45; c1 = 23'h125682; c2 = 13'h274; end
            9'd445: begin c0 = 33'h88e3cb10; c1 = 23'h124cb5; c2 = 13'h272; end
            9'd446: begin c0 = 33'h88bf3b6d; c1 = 23'h1242ef; c2 = 13'h270; end
            9'd447: begin c0 = 33'h889abf4d; c1 = 23'h123932; c2 = 13'h26e; end
            9'd448: begin c0 = 33'h8876569f; c1 = 23'h122f7d; c2 = 13'h26c; end
            9'd449: begin c0 = 33'h88520155; c1 = 23'h1225cf; c2 = 13'h26a; end
            9'd450: begin c0 = 33'h882dbf5e; c1 = 23'h121c29; c2 = 13'h269; end
            9'd451: begin c0 = 33'h880990ac; c1 = 23'h12128b; c2 = 13'h267; end
            9'd452: begin c0 = 33'h87e5752f; c1 = 23'h1208f4; c2 = 13'h265; end
            9'd453: begin c0 = 33'h87c16cd8; c1 = 23'h11ff65; c2 = 13'h263; end
            9'd454: begin c0 = 33'h879d7797; c1 = 23'h11f5dd; c2 = 13'h261; end
            9'd455: begin c0 = 33'h8779955e; c1 = 23'h11ec5d; c2 = 13'h25f; end
            9'd456: begin c0 = 33'h8755c61d; c1 = 23'h11e2e5; c2 = 13'h25d; end
            9'd457: begin c0 = 33'h873209c5; c1 = 23'h11d974; c2 = 13'h25b; end
            9'd458: begin c0 = 33'h870e6048; c1 = 23'h11d00b; c2 = 13'h259; end
            9'd459: begin c0 = 33'h86eac996; c1 = 23'h11c6a9; c2 = 13'h258; end
            9'd460: begin c0 = 33'h86c745a0; c1 = 23'h11bd4e; c2 = 13'h256; end
            9'd461: begin c0 = 33'h86a3d459; c1 = 23'h11b3fb; c2 = 13'h254; end
            9'd462: begin c0 = 33'h868075b0; c1 = 23'h11aaaf; c2 = 13'h252; end
            9'd463: begin c0 = 33'h865d2998; c1 = 23'h11a16a; c2 = 13'h250; end
            9'd464: begin c0 = 33'h8639f002; c1 = 23'h11982d; c2 = 13'h24e; end
            9'd465: begin c0 = 33'h8616c8df; c1 = 23'h118ef7; c2 = 13'h24d; end
            9'd466: begin c0 = 33'h85f3b421; c1 = 23'h1185c8; c2 = 13'h24b; end
            9'd467: begin c0 = 33'h85d0b1b9; c1 = 23'h117ca1; c2 = 13'h249; end
            9'd468: begin c0 = 33'h85adc199; c1 = 23'h117380; c2 = 13'h247; end
            9'd469: begin c0 = 33'h858ae3b3; c1 = 23'h116a67; c2 = 13'h245; end
            9'd470: begin c0 = 33'h856817f9; c1 = 23'h116155; c2 = 13'h244; end
            9'd471: begin c0 = 33'h85455e5b; c1 = 23'h11584a; c2 = 13'h242; end
            9'd472: begin c0 = 33'h8522b6cd; c1 = 23'h114f46; c2 = 13'h240; end
            9'd473: begin c0 = 33'h85002140; c1 = 23'h114649; c2 = 13'h23e; end
            9'd474: begin c0 = 33'h84dd9da6; c1 = 23'h113d53; c2 = 13'h23d; end
            9'd475: begin c0 = 33'h84bb2bf1; c1 = 23'h113464; c2 = 13'h23b; end
            9'd476: begin c0 = 33'h8498cc13; c1 = 23'h112b7b; c2 = 13'h239; end
            9'd477: begin c0 = 33'h84767dff; c1 = 23'h11229a; c2 = 13'h237; end
            9'd478: begin c0 = 33'h845441a6; c1 = 23'h1119c0; c2 = 13'h236; end
            9'd479: begin c0 = 33'h843216fb; c1 = 23'h1110ec; c2 = 13'h234; end
            9'd480: begin c0 = 33'h840ffdf0; c1 = 23'h110820; c2 = 13'h232; end
            9'd481: begin c0 = 33'h83edf677; c1 = 23'h10ff5a; c2 = 13'h231; end
            9'd482: begin c0 = 33'h83cc0084; c1 = 23'h10f69b; c2 = 13'h22f; end
            9'd483: begin c0 = 33'h83aa1c08; c1 = 23'h10ede2; c2 = 13'h22d; end
            9'd484: begin c0 = 33'h838848f6; c1 = 23'h10e531; c2 = 13'h22c; end
            9'd485: begin c0 = 33'h83668740; c1 = 23'h10dc86; c2 = 13'h22a; end
            9'd486: begin c0 = 33'h8344d6da; c1 = 23'h10d3e2; c2 = 13'h228; end
            9'd487: begin c0 = 33'h832337b5; c1 = 23'h10cb44; c2 = 13'h227; end
            9'd488: begin c0 = 33'h8301a9c5; c1 = 23'h10c2ad; c2 = 13'h225; end
            9'd489: begin c0 = 33'h82e02cfd; c1 = 23'h10ba1c; c2 = 13'h223; end
            9'd490: begin c0 = 33'h82bec14f; c1 = 23'h10b193; c2 = 13'h222; end
            9'd491: begin c0 = 33'h829d66ae; c1 = 23'h10a90f; c2 = 13'h220; end
            9'd492: begin c0 = 33'h827c1d0e; c1 = 23'h10a092; c2 = 13'h21e; end
            9'd493: begin c0 = 33'h825ae460; c1 = 23'h10981c; c2 = 13'h21d; end
            9'd494: begin c0 = 33'h8239bc99; c1 = 23'h108fac; c2 = 13'h21b; end
            9'd495: begin c0 = 33'h8218a5ab; c1 = 23'h108743; c2 = 13'h21a; end
            9'd496: begin c0 = 33'h81f79f8a; c1 = 23'h107ee0; c2 = 13'h218; end
            9'd497: begin c0 = 33'h81d6aa29; c1 = 23'h107683; c2 = 13'h216; end
            9'd498: begin c0 = 33'h81b5c57a; c1 = 23'h106e2d; c2 = 13'h215; end
            9'd499: begin c0 = 33'h8194f173; c1 = 23'h1065dc; c2 = 13'h213; end
            9'd500: begin c0 = 33'h81742e04; c1 = 23'h105d93; c2 = 13'h212; end
            9'd501: begin c0 = 33'h81537b23; c1 = 23'h10554f; c2 = 13'h210; end
            9'd502: begin c0 = 33'h8132d8c3; c1 = 23'h104d12; c2 = 13'h20f; end
            9'd503: begin c0 = 33'h811246d7; c1 = 23'h1044db; c2 = 13'h20d; end
            9'd504: begin c0 = 33'h80f1c552; c1 = 23'h103caa; c2 = 13'h20b; end
            9'd505: begin c0 = 33'h80d15429; c1 = 23'h103480; c2 = 13'h20a; end
            9'd506: begin c0 = 33'h80b0f34f; c1 = 23'h102c5b; c2 = 13'h208; end
            9'd507: begin c0 = 33'h8090a2b7; c1 = 23'h10243d; c2 = 13'h207; end
            9'd508: begin c0 = 33'h80706256; c1 = 23'h101c25; c2 = 13'h205; end
            9'd509: begin c0 = 33'h8050321f; c1 = 23'h101413; c2 = 13'h204; end
            9'd510: begin c0 = 33'h80301207; c1 = 23'h100c07; c2 = 13'h202; end
            9'd511: begin c0 = 33'h80100200; c1 = 23'h100401; c2 = 13'h201; end
            default: begin c0 = 'x; c1 = 'x; c2 = 'x; end
        endcase
    end
endmodule

// sq(dmh) = floor(((2 dmh + 1) 2^3)^2 / 2^12): the square of the centre of the
// bucket dm >> 4 that the seed's C2 term multiplies.
module ot_hdc_sk_sq_rom__d4g_hc (
    input  wire [8:0] dmh,
    output reg  [13:0] sq
);
    always @* begin
        case (dmh)
            9'd0: sq = 14'h0;
            9'd1: sq = 14'h0;
            9'd2: sq = 14'h0;
            9'd3: sq = 14'h0;
            9'd4: sq = 14'h1;
            9'd5: sq = 14'h1;
            9'd6: sq = 14'h2;
            9'd7: sq = 14'h3;
            9'd8: sq = 14'h4;
            9'd9: sq = 14'h5;
            9'd10: sq = 14'h6;
            9'd11: sq = 14'h8;
            9'd12: sq = 14'h9;
            9'd13: sq = 14'hb;
            9'd14: sq = 14'hd;
            9'd15: sq = 14'hf;
            9'd16: sq = 14'h11;
            9'd17: sq = 14'h13;
            9'd18: sq = 14'h15;
            9'd19: sq = 14'h17;
            9'd20: sq = 14'h1a;
            9'd21: sq = 14'h1c;
            9'd22: sq = 14'h1f;
            9'd23: sq = 14'h22;
            9'd24: sq = 14'h25;
            9'd25: sq = 14'h28;
            9'd26: sq = 14'h2b;
            9'd27: sq = 14'h2f;
            9'd28: sq = 14'h32;
            9'd29: sq = 14'h36;
            9'd30: sq = 14'h3a;
            9'd31: sq = 14'h3e;
            9'd32: sq = 14'h42;
            9'd33: sq = 14'h46;
            9'd34: sq = 14'h4a;
            9'd35: sq = 14'h4e;
            9'd36: sq = 14'h53;
            9'd37: sq = 14'h57;
            9'd38: sq = 14'h5c;
            9'd39: sq = 14'h61;
            9'd40: sq = 14'h66;
            9'd41: sq = 14'h6b;
            9'd42: sq = 14'h70;
            9'd43: sq = 14'h76;
            9'd44: sq = 14'h7b;
            9'd45: sq = 14'h81;
            9'd46: sq = 14'h87;
            9'd47: sq = 14'h8d;
            9'd48: sq = 14'h93;
            9'd49: sq = 14'h99;
            9'd50: sq = 14'h9f;
            9'd51: sq = 14'ha5;
            9'd52: sq = 14'hac;
            9'd53: sq = 14'hb2;
            9'd54: sq = 14'hb9;
            9'd55: sq = 14'hc0;
            9'd56: sq = 14'hc7;
            9'd57: sq = 14'hce;
            9'd58: sq = 14'hd5;
            9'd59: sq = 14'hdd;
            9'd60: sq = 14'he4;
            9'd61: sq = 14'hec;
            9'd62: sq = 14'hf4;
            9'd63: sq = 14'hfc;
            9'd64: sq = 14'h104;
            9'd65: sq = 14'h10c;
            9'd66: sq = 14'h114;
            9'd67: sq = 14'h11c;
            9'd68: sq = 14'h125;
            9'd69: sq = 14'h12d;
            9'd70: sq = 14'h136;
            9'd71: sq = 14'h13f;
            9'd72: sq = 14'h148;
            9'd73: sq = 14'h151;
            9'd74: sq = 14'h15a;
            9'd75: sq = 14'h164;
            9'd76: sq = 14'h16d;
            9'd77: sq = 14'h177;
            9'd78: sq = 14'h181;
            9'd79: sq = 14'h18b;
            9'd80: sq = 14'h195;
            9'd81: sq = 14'h19f;
            9'd82: sq = 14'h1a9;
            9'd83: sq = 14'h1b3;
            9'd84: sq = 14'h1be;
            9'd85: sq = 14'h1c8;
            9'd86: sq = 14'h1d3;
            9'd87: sq = 14'h1de;
            9'd88: sq = 14'h1e9;
            9'd89: sq = 14'h1f4;
            9'd90: sq = 14'h1ff;
            9'd91: sq = 14'h20b;
            9'd92: sq = 14'h216;
            9'd93: sq = 14'h222;
            9'd94: sq = 14'h22e;
            9'd95: sq = 14'h23a;
            9'd96: sq = 14'h246;
            9'd97: sq = 14'h252;
            9'd98: sq = 14'h25e;
            9'd99: sq = 14'h26a;
            9'd100: sq = 14'h277;
            9'd101: sq = 14'h283;
            9'd102: sq = 14'h290;
            9'd103: sq = 14'h29d;
            9'd104: sq = 14'h2aa;
            9'd105: sq = 14'h2b7;
            9'd106: sq = 14'h2c4;
            9'd107: sq = 14'h2d2;
            9'd108: sq = 14'h2df;
            9'd109: sq = 14'h2ed;
            9'd110: sq = 14'h2fb;
            9'd111: sq = 14'h309;
            9'd112: sq = 14'h317;
            9'd113: sq = 14'h325;
            9'd114: sq = 14'h333;
            9'd115: sq = 14'h341;
            9'd116: sq = 14'h350;
            9'd117: sq = 14'h35e;
            9'd118: sq = 14'h36d;
            9'd119: sq = 14'h37c;
            9'd120: sq = 14'h38b;
            9'd121: sq = 14'h39a;
            9'd122: sq = 14'h3a9;
            9'd123: sq = 14'h3b9;
            9'd124: sq = 14'h3c8;
            9'd125: sq = 14'h3d8;
            9'd126: sq = 14'h3e8;
            9'd127: sq = 14'h3f8;
            9'd128: sq = 14'h408;
            9'd129: sq = 14'h418;
            9'd130: sq = 14'h428;
            9'd131: sq = 14'h438;
            9'd132: sq = 14'h449;
            9'd133: sq = 14'h459;
            9'd134: sq = 14'h46a;
            9'd135: sq = 14'h47b;
            9'd136: sq = 14'h48c;
            9'd137: sq = 14'h49d;
            9'd138: sq = 14'h4ae;
            9'd139: sq = 14'h4c0;
            9'd140: sq = 14'h4d1;
            9'd141: sq = 14'h4e3;
            9'd142: sq = 14'h4f5;
            9'd143: sq = 14'h507;
            9'd144: sq = 14'h519;
            9'd145: sq = 14'h52b;
            9'd146: sq = 14'h53d;
            9'd147: sq = 14'h54f;
            9'd148: sq = 14'h562;
            9'd149: sq = 14'h574;
            9'd150: sq = 14'h587;
            9'd151: sq = 14'h59a;
            9'd152: sq = 14'h5ad;
            9'd153: sq = 14'h5c0;
            9'd154: sq = 14'h5d3;
            9'd155: sq = 14'h5e7;
            9'd156: sq = 14'h5fa;
            9'd157: sq = 14'h60e;
            9'd158: sq = 14'h622;
            9'd159: sq = 14'h636;
            9'd160: sq = 14'h64a;
            9'd161: sq = 14'h65e;
            9'd162: sq = 14'h672;
            9'd163: sq = 14'h686;
            9'd164: sq = 14'h69b;
            9'd165: sq = 14'h6af;
            9'd166: sq = 14'h6c4;
            9'd167: sq = 14'h6d9;
            9'd168: sq = 14'h6ee;
            9'd169: sq = 14'h703;
            9'd170: sq = 14'h718;
            9'd171: sq = 14'h72e;
            9'd172: sq = 14'h743;
            9'd173: sq = 14'h759;
            9'd174: sq = 14'h76f;
            9'd175: sq = 14'h785;
            9'd176: sq = 14'h79b;
            9'd177: sq = 14'h7b1;
            9'd178: sq = 14'h7c7;
            9'd179: sq = 14'h7dd;
            9'd180: sq = 14'h7f4;
            9'd181: sq = 14'h80a;
            9'd182: sq = 14'h821;
            9'd183: sq = 14'h838;
            9'd184: sq = 14'h84f;
            9'd185: sq = 14'h866;
            9'd186: sq = 14'h87d;
            9'd187: sq = 14'h895;
            9'd188: sq = 14'h8ac;
            9'd189: sq = 14'h8c4;
            9'd190: sq = 14'h8dc;
            9'd191: sq = 14'h8f4;
            9'd192: sq = 14'h90c;
            9'd193: sq = 14'h924;
            9'd194: sq = 14'h93c;
            9'd195: sq = 14'h954;
            9'd196: sq = 14'h96d;
            9'd197: sq = 14'h985;
            9'd198: sq = 14'h99e;
            9'd199: sq = 14'h9b7;
            9'd200: sq = 14'h9d0;
            9'd201: sq = 14'h9e9;
            9'd202: sq = 14'ha02;
            9'd203: sq = 14'ha1c;
            9'd204: sq = 14'ha35;
            9'd205: sq = 14'ha4f;
            9'd206: sq = 14'ha69;
            9'd207: sq = 14'ha83;
            9'd208: sq = 14'ha9d;
            9'd209: sq = 14'hab7;
            9'd210: sq = 14'had1;
            9'd211: sq = 14'haeb;
            9'd212: sq = 14'hb06;
            9'd213: sq = 14'hb20;
            9'd214: sq = 14'hb3b;
            9'd215: sq = 14'hb56;
            9'd216: sq = 14'hb71;
            9'd217: sq = 14'hb8c;
            9'd218: sq = 14'hba7;
            9'd219: sq = 14'hbc3;
            9'd220: sq = 14'hbde;
            9'd221: sq = 14'hbfa;
            9'd222: sq = 14'hc16;
            9'd223: sq = 14'hc32;
            9'd224: sq = 14'hc4e;
            9'd225: sq = 14'hc6a;
            9'd226: sq = 14'hc86;
            9'd227: sq = 14'hca2;
            9'd228: sq = 14'hcbf;
            9'd229: sq = 14'hcdb;
            9'd230: sq = 14'hcf8;
            9'd231: sq = 14'hd15;
            9'd232: sq = 14'hd32;
            9'd233: sq = 14'hd4f;
            9'd234: sq = 14'hd6c;
            9'd235: sq = 14'hd8a;
            9'd236: sq = 14'hda7;
            9'd237: sq = 14'hdc5;
            9'd238: sq = 14'hde3;
            9'd239: sq = 14'he01;
            9'd240: sq = 14'he1f;
            9'd241: sq = 14'he3d;
            9'd242: sq = 14'he5b;
            9'd243: sq = 14'he79;
            9'd244: sq = 14'he98;
            9'd245: sq = 14'heb6;
            9'd246: sq = 14'hed5;
            9'd247: sq = 14'hef4;
            9'd248: sq = 14'hf13;
            9'd249: sq = 14'hf32;
            9'd250: sq = 14'hf51;
            9'd251: sq = 14'hf71;
            9'd252: sq = 14'hf90;
            9'd253: sq = 14'hfb0;
            9'd254: sq = 14'hfd0;
            9'd255: sq = 14'hff0;
            9'd256: sq = 14'h1010;
            9'd257: sq = 14'h1030;
            9'd258: sq = 14'h1050;
            9'd259: sq = 14'h1070;
            9'd260: sq = 14'h1091;
            9'd261: sq = 14'h10b1;
            9'd262: sq = 14'h10d2;
            9'd263: sq = 14'h10f3;
            9'd264: sq = 14'h1114;
            9'd265: sq = 14'h1135;
            9'd266: sq = 14'h1156;
            9'd267: sq = 14'h1178;
            9'd268: sq = 14'h1199;
            9'd269: sq = 14'h11bb;
            9'd270: sq = 14'h11dd;
            9'd271: sq = 14'h11ff;
            9'd272: sq = 14'h1221;
            9'd273: sq = 14'h1243;
            9'd274: sq = 14'h1265;
            9'd275: sq = 14'h1287;
            9'd276: sq = 14'h12aa;
            9'd277: sq = 14'h12cc;
            9'd278: sq = 14'h12ef;
            9'd279: sq = 14'h1312;
            9'd280: sq = 14'h1335;
            9'd281: sq = 14'h1358;
            9'd282: sq = 14'h137b;
            9'd283: sq = 14'h139f;
            9'd284: sq = 14'h13c2;
            9'd285: sq = 14'h13e6;
            9'd286: sq = 14'h140a;
            9'd287: sq = 14'h142e;
            9'd288: sq = 14'h1452;
            9'd289: sq = 14'h1476;
            9'd290: sq = 14'h149a;
            9'd291: sq = 14'h14be;
            9'd292: sq = 14'h14e3;
            9'd293: sq = 14'h1507;
            9'd294: sq = 14'h152c;
            9'd295: sq = 14'h1551;
            9'd296: sq = 14'h1576;
            9'd297: sq = 14'h159b;
            9'd298: sq = 14'h15c0;
            9'd299: sq = 14'h15e6;
            9'd300: sq = 14'h160b;
            9'd301: sq = 14'h1631;
            9'd302: sq = 14'h1657;
            9'd303: sq = 14'h167d;
            9'd304: sq = 14'h16a3;
            9'd305: sq = 14'h16c9;
            9'd306: sq = 14'h16ef;
            9'd307: sq = 14'h1715;
            9'd308: sq = 14'h173c;
            9'd309: sq = 14'h1762;
            9'd310: sq = 14'h1789;
            9'd311: sq = 14'h17b0;
            9'd312: sq = 14'h17d7;
            9'd313: sq = 14'h17fe;
            9'd314: sq = 14'h1825;
            9'd315: sq = 14'h184d;
            9'd316: sq = 14'h1874;
            9'd317: sq = 14'h189c;
            9'd318: sq = 14'h18c4;
            9'd319: sq = 14'h18ec;
            9'd320: sq = 14'h1914;
            9'd321: sq = 14'h193c;
            9'd322: sq = 14'h1964;
            9'd323: sq = 14'h198c;
            9'd324: sq = 14'h19b5;
            9'd325: sq = 14'h19dd;
            9'd326: sq = 14'h1a06;
            9'd327: sq = 14'h1a2f;
            9'd328: sq = 14'h1a58;
            9'd329: sq = 14'h1a81;
            9'd330: sq = 14'h1aaa;
            9'd331: sq = 14'h1ad4;
            9'd332: sq = 14'h1afd;
            9'd333: sq = 14'h1b27;
            9'd334: sq = 14'h1b51;
            9'd335: sq = 14'h1b7b;
            9'd336: sq = 14'h1ba5;
            9'd337: sq = 14'h1bcf;
            9'd338: sq = 14'h1bf9;
            9'd339: sq = 14'h1c23;
            9'd340: sq = 14'h1c4e;
            9'd341: sq = 14'h1c78;
            9'd342: sq = 14'h1ca3;
            9'd343: sq = 14'h1cce;
            9'd344: sq = 14'h1cf9;
            9'd345: sq = 14'h1d24;
            9'd346: sq = 14'h1d4f;
            9'd347: sq = 14'h1d7b;
            9'd348: sq = 14'h1da6;
            9'd349: sq = 14'h1dd2;
            9'd350: sq = 14'h1dfe;
            9'd351: sq = 14'h1e2a;
            9'd352: sq = 14'h1e56;
            9'd353: sq = 14'h1e82;
            9'd354: sq = 14'h1eae;
            9'd355: sq = 14'h1eda;
            9'd356: sq = 14'h1f07;
            9'd357: sq = 14'h1f33;
            9'd358: sq = 14'h1f60;
            9'd359: sq = 14'h1f8d;
            9'd360: sq = 14'h1fba;
            9'd361: sq = 14'h1fe7;
            9'd362: sq = 14'h2014;
            9'd363: sq = 14'h2042;
            9'd364: sq = 14'h206f;
            9'd365: sq = 14'h209d;
            9'd366: sq = 14'h20cb;
            9'd367: sq = 14'h20f9;
            9'd368: sq = 14'h2127;
            9'd369: sq = 14'h2155;
            9'd370: sq = 14'h2183;
            9'd371: sq = 14'h21b1;
            9'd372: sq = 14'h21e0;
            9'd373: sq = 14'h220e;
            9'd374: sq = 14'h223d;
            9'd375: sq = 14'h226c;
            9'd376: sq = 14'h229b;
            9'd377: sq = 14'h22ca;
            9'd378: sq = 14'h22f9;
            9'd379: sq = 14'h2329;
            9'd380: sq = 14'h2358;
            9'd381: sq = 14'h2388;
            9'd382: sq = 14'h23b8;
            9'd383: sq = 14'h23e8;
            9'd384: sq = 14'h2418;
            9'd385: sq = 14'h2448;
            9'd386: sq = 14'h2478;
            9'd387: sq = 14'h24a8;
            9'd388: sq = 14'h24d9;
            9'd389: sq = 14'h2509;
            9'd390: sq = 14'h253a;
            9'd391: sq = 14'h256b;
            9'd392: sq = 14'h259c;
            9'd393: sq = 14'h25cd;
            9'd394: sq = 14'h25fe;
            9'd395: sq = 14'h2630;
            9'd396: sq = 14'h2661;
            9'd397: sq = 14'h2693;
            9'd398: sq = 14'h26c5;
            9'd399: sq = 14'h26f7;
            9'd400: sq = 14'h2729;
            9'd401: sq = 14'h275b;
            9'd402: sq = 14'h278d;
            9'd403: sq = 14'h27bf;
            9'd404: sq = 14'h27f2;
            9'd405: sq = 14'h2824;
            9'd406: sq = 14'h2857;
            9'd407: sq = 14'h288a;
            9'd408: sq = 14'h28bd;
            9'd409: sq = 14'h28f0;
            9'd410: sq = 14'h2923;
            9'd411: sq = 14'h2957;
            9'd412: sq = 14'h298a;
            9'd413: sq = 14'h29be;
            9'd414: sq = 14'h29f2;
            9'd415: sq = 14'h2a26;
            9'd416: sq = 14'h2a5a;
            9'd417: sq = 14'h2a8e;
            9'd418: sq = 14'h2ac2;
            9'd419: sq = 14'h2af6;
            9'd420: sq = 14'h2b2b;
            9'd421: sq = 14'h2b5f;
            9'd422: sq = 14'h2b94;
            9'd423: sq = 14'h2bc9;
            9'd424: sq = 14'h2bfe;
            9'd425: sq = 14'h2c33;
            9'd426: sq = 14'h2c68;
            9'd427: sq = 14'h2c9e;
            9'd428: sq = 14'h2cd3;
            9'd429: sq = 14'h2d09;
            9'd430: sq = 14'h2d3f;
            9'd431: sq = 14'h2d75;
            9'd432: sq = 14'h2dab;
            9'd433: sq = 14'h2de1;
            9'd434: sq = 14'h2e17;
            9'd435: sq = 14'h2e4d;
            9'd436: sq = 14'h2e84;
            9'd437: sq = 14'h2eba;
            9'd438: sq = 14'h2ef1;
            9'd439: sq = 14'h2f28;
            9'd440: sq = 14'h2f5f;
            9'd441: sq = 14'h2f96;
            9'd442: sq = 14'h2fcd;
            9'd443: sq = 14'h3005;
            9'd444: sq = 14'h303c;
            9'd445: sq = 14'h3074;
            9'd446: sq = 14'h30ac;
            9'd447: sq = 14'h30e4;
            9'd448: sq = 14'h311c;
            9'd449: sq = 14'h3154;
            9'd450: sq = 14'h318c;
            9'd451: sq = 14'h31c4;
            9'd452: sq = 14'h31fd;
            9'd453: sq = 14'h3235;
            9'd454: sq = 14'h326e;
            9'd455: sq = 14'h32a7;
            9'd456: sq = 14'h32e0;
            9'd457: sq = 14'h3319;
            9'd458: sq = 14'h3352;
            9'd459: sq = 14'h338c;
            9'd460: sq = 14'h33c5;
            9'd461: sq = 14'h33ff;
            9'd462: sq = 14'h3439;
            9'd463: sq = 14'h3473;
            9'd464: sq = 14'h34ad;
            9'd465: sq = 14'h34e7;
            9'd466: sq = 14'h3521;
            9'd467: sq = 14'h355b;
            9'd468: sq = 14'h3596;
            9'd469: sq = 14'h35d0;
            9'd470: sq = 14'h360b;
            9'd471: sq = 14'h3646;
            9'd472: sq = 14'h3681;
            9'd473: sq = 14'h36bc;
            9'd474: sq = 14'h36f7;
            9'd475: sq = 14'h3733;
            9'd476: sq = 14'h376e;
            9'd477: sq = 14'h37aa;
            9'd478: sq = 14'h37e6;
            9'd479: sq = 14'h3822;
            9'd480: sq = 14'h385e;
            9'd481: sq = 14'h389a;
            9'd482: sq = 14'h38d6;
            9'd483: sq = 14'h3912;
            9'd484: sq = 14'h394f;
            9'd485: sq = 14'h398b;
            9'd486: sq = 14'h39c8;
            9'd487: sq = 14'h3a05;
            9'd488: sq = 14'h3a42;
            9'd489: sq = 14'h3a7f;
            9'd490: sq = 14'h3abc;
            9'd491: sq = 14'h3afa;
            9'd492: sq = 14'h3b37;
            9'd493: sq = 14'h3b75;
            9'd494: sq = 14'h3bb3;
            9'd495: sq = 14'h3bf1;
            9'd496: sq = 14'h3c2f;
            9'd497: sq = 14'h3c6d;
            9'd498: sq = 14'h3cab;
            9'd499: sq = 14'h3ce9;
            9'd500: sq = 14'h3d28;
            9'd501: sq = 14'h3d66;
            9'd502: sq = 14'h3da5;
            9'd503: sq = 14'h3de4;
            9'd504: sq = 14'h3e23;
            9'd505: sq = 14'h3e62;
            9'd506: sq = 14'h3ea1;
            9'd507: sq = 14'h3ee1;
            9'd508: sq = 14'h3f20;
            9'd509: sq = 14'h3f60;
            9'd510: sq = 14'h3fa0;
            9'd511: sq = 14'h3fe0;
            default: sq = 'x;
        endcase
    end
endmodule

// Scoped source: rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection projection engine (HCP) of the re-specified DeepSeek-V4.1
// decode die: docs/ARCH_SPEC_V41.md section 6 item 7, gap-table row
// "hyper-connection projection" (2,048 FP32 MAC lanes).
//
// FUNCTION (tools/hdc_golden_v41.py Model.hc_mixes under R-ARITH "chunk8").
// Per position p, with flat = the BF16 4-copy residual (K = 4 x dim elements)
// and fn the [nout, K] binary32 projection:
//   ss      = csum(mul(flat, flat))                        (the norm's sum of squares)
//   r       = rsqrt(add(div(ss, nf), eps))                  (hdc_golden rsqrt: magic + 3 Newton steps)
//   mix[o]  = mul(csum(mul(fn[o, :], flat)), r)             (o = 0 .. nout-1)
// csum = chunks of 8 contiguous terms summed sequentially from +0, the chunk
// sums added by a pairwise tree padded with +0.  Every operation is one
// binary32 op of rtl/hdc/ot_hdc_fastfp.sv (3-stage add / multiply, RNE,
// gradual underflow, canonical +0) or the IEEE divider ot_hdc_fdiv__d4g_hc.  With
// cmd_scale = 0 the engine returns the raw csum dot products (mix[o] =
// csum(...) exactly; the ss task and the scale are skipped).
//
// LANES.  8 groups x W lanes = 8W FP32 MAC lanes (W = 256: 2,048).  A lane is
// one multiplier feeding one adder whose sum re-enters exactly 3 cycles later
// (the add latency), so a lane interleaves 3 chunk accumulations ("slots") and
// retires one multiply-add per cycle.  A TASK is one aligned run of W chunks
// (8W terms) of one accumulation (position p, row o, run r): the W lanes of a
// group each own one chunk of the run.  One task issues per cycle.  Task n
// (issued in cycle n) belongs to group (n div 3) mod 8, slot n mod 3, and its
// term k (k = 0 .. 7) is multiplied in cycle n + 3k (plus a fixed offset): so
// every lane is busy every cycle, the 8 groups are always at 8 DIFFERENT terms
// k, and the chunk sums of exactly one task complete per cycle.
//
// MEMORIES (outside the engine; fixed read latency ML cycles from the
// registered address to the data at the input port, no handshake).  Both are
// banked by term k, so the 8 groups never conflict:
//   weight bank k, word wbase + o*R + r, lane l:  fn[o][8*(r*W + l) + k]      (binary32)
//   x      bank k, word xbase + p*R + r, lane l:  flat_p[8*(r*W + l) + k]     (BF16)
// with R = ceil(nchunk / W) runs, nchunk = K/8, words past the vector ignored
// (lanes l >= nchunk - r*W of the last run are masked to +0 operands).  Bank k
// in cycle c serves the task issued in cycle c - 3k; its data is rotated to
// that task's group (a one-hot AND-OR by the group field the task carries).
//
// REDUCTION, exactly the csum tree.  The W chunk sums of a task enter a
// pipelined pairwise tree of log2(W) adder levels: that is the csum subtree of
// an aligned run of W chunks.  The run sums of one accumulation (r = 0 .. R-1)
// enter the TAIL: TL levels, level l holding one pending left sibling.  At
// level l an event with bit l of r set adds the stored sibling and moves up;
// with bit l clear it is stored and stops -- unless it is the accumulation's
// last run, whose right sibling is all padding, so it moves up unchanged
// (added to +0).  Every addition is the tree's own pair, so the result is
// csum's padded tree bit for bit (padding past pow2(nchunk) only adds +0).
// Requires R <= 2^TL (fault otherwise) and K a multiple of 8.
//
// ORDER.  Positions p = 0 .. npos-1; per position the ss task run (if
// cmd_scale) then rows o = 0 .. nout-1, each its R runs.  Raw sums enter a
// DF-entry FIFO; issue reserves an entry per accumulation (credit), so the
// engine never drops a result.  The scalar unit turns ss into r (one fdiv,
// one add, one multiply, sequenced: ~90 cycles per position, while the rows
// of that position accumulate), and each raw row sum leaves through one
// multiplier as mix = raw * r (raw * 1.0 = raw when cmd_scale = 0).
//
// PROTOCOL.  cmd_valid/cmd_ready: one command at a time (cmd_ready rises again
// after the command's last result is accepted).  o_valid/o_ready: results in
// (p, o) order, o_last on the command's final result.  Every output is a flop;
// every input is registered before use.  fault (sticky per command): a
// nonfinite operand or overflow anywhere, a divide fault, or R > 2^TL.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_hcp__d4g_hc #(
    parameter integer W    = 8,         // lanes per group (power of two >= 2); lanes = 8W (spec: W = 256)
    parameter integer TL   = 9,         // tail levels: runs per accumulation R <= 2^TL (spec: 4)
    parameter integer PMAX = 8,         // positions per command (power of two)
    parameter integer OMAX = 32,        // rows per position (power of two)
    parameter integer AW   = 16,        // bank word address width
    parameter integer CW   = 16,        // chunk-count width (nchunk = K/8)
    parameter integer ML   = 2,         // memory read latency
    parameter integer DF   = 32,        // raw-result FIFO depth (power of two)
    // el1011-hcvm-hc SYSTOLIC lanes (opt-in, default off; cycles change): SYS = 1 builds no lane groups and no bank
    // rotation.  The 8W lanes live outside in 8 bank stages (ot_hdc_v41x_hcp_stage__d4g_hc, one per bank, chained): the task
    // descriptor leaves on sd_* (tap 0), stage k multiplies term k from its OWN bank and adds it to the partial chunk
    // sum of stage k - 1 (stage 0 adds to +0), so csum's chunk order ((0 + t0) + t1) .. + t7 is kept op for op; stage
    // 7's W chunk sums come back on sys_sum SYS_LAT cycles after tap 0 (the tree leaves at tap SYS_LAT + 1).
    parameter integer SYS  = 0,
    parameter integer SYS_LAT = 0,
    parameter integer PW   = (PMAX > 1) ? $clog2(PMAX) : 1,
    parameter integer OXW  = (OMAX > 1) ? $clog2(OMAX) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    // command
    input  wire              cmd_valid,
    output reg               cmd_ready,
    input  wire [PW:0]       cmd_npos,          // 1 .. PMAX
    input  wire [OXW:0]      cmd_nout,          // 1 .. OMAX
    input  wire [CW-1:0]     cmd_nchunk,        // K / 8, >= 1
    input  wire              cmd_scale,
    input  wire [31:0]       cmd_nf,            // binary32 of K (the mean's divisor)
    input  wire [31:0]       cmd_eps,
    input  wire [AW-1:0]     cmd_wbase,
    input  wire [AW-1:0]     cmd_xbase,
    // weight banks (binary32) and x banks (BF16), bank k at [k*...]
    output reg  [7:0]        w_re,
    output reg  [8*AW-1:0]   w_addr,
    input  wire [8*W*32-1:0] w_data,
    output reg  [7:0]        x_re,
    output reg  [8*AW-1:0]   x_addr,
    input  wire [8*W*16-1:0] x_data,
    // results
    output reg               o_valid,
    input  wire              o_ready,
    output reg  [PW-1:0]     o_pos,
    output reg  [OXW-1:0]    o_idx,
    output reg  [31:0]       o_data,
    output reg               o_last,
    output reg               fault,
    output reg               idle,
    // SYS = 1: the descriptor to stage 0, the chunk sums and lane faults back from stage 7
    output wire              sd_v,
    output wire              sd_ss,
    output wire [$clog2(W):0] sd_nv,
    output wire [AW-1:0]     sd_wa,
    output wire [AW-1:0]     sd_xa,
    input  wire [W*32-1:0]   sys_sum,
    input  wire              sys_fault
);
    localparam integer LW  = $clog2(W);
    localparam integer NVW = LW + 1;
    localparam integer DFW = $clog2(DF);
    // descriptor fields
    localparam integer F_V   = 0;
    localparam integer F_SS  = 1;
    localparam integer F_LR  = 2;                 // last run
    localparam integer F_GRP = 3;                 // 3 bits
    localparam integer F_NV  = 6;                 // NVW bits
    localparam integer F_WA  = F_NV + NVW;
    localparam integer F_XA  = F_WA + AW;
    localparam integer F_POS = F_XA + AW;
    localparam integer F_IDX = F_POS + PW;
    localparam integer F_R   = F_IDX + OXW;       // TL low bits of the run index
    localparam integer F_LO  = F_R + TL;          // last output of the command
    localparam integer DW    = F_LO + 1;
    // pipeline taps (descriptor delay-line index of the task a stage holds)
    localparam integer T_OP   = 21 + ML + 3;                 // group operands of term 7
    localparam integer T_LEAF = SYS ? SYS_LAT + 1 : 31 + ML; // tree leaves
    localparam integer T_TAIL = T_LEAF + 3 * LW;             // tree output = tail level 0 input
    localparam integer NDL    = T_TAIL + 3 * TL + 1;

    genvar gk, gg, gl, gv;
    integer i;

    // ------------------------------------------------------------------ command / issue
    reg              busy, active;
    reg [PW:0]       npos_r;
    reg [OXW:0]      nout_r;
    reg [CW-1:0]     nrun_r, nlast_r;              // runs per accumulation; lanes of the last run
    reg              scale_r;
    reg [31:0]       nf_r, eps_r;
    reg [PW-1:0]     p;
    reg [OXW-1:0]    o;
    reg              ssph;
    reg [CW-1:0]     r;
    reg [AW-1:0]     wbase_r, wcur, xpos;
    reg [4:0]        ph24;                          // free-running cycle mod 24
    reg [DFW:0]      acc_cnt;                       // accumulations reserved, not yet popped
    wire             pop_raw;
    wire [CW-1:0]    nrun_c = (cmd_nchunk + W - 1) >> LW;
    wire             first_r = (r == 0);
    wire             last_r = (r == nrun_r - 1'b1);
    wire             credit = (acc_cnt < DF);
    wire             iss = active && (!first_r || credit);
    wire             last_o = ssph ? 1'b0 : ({1'b0, o} == nout_r - 1'b1);
    wire             last_p = ({1'b0, p} == npos_r - 1'b1);
    reg  [DW-1:0]    d0;
    wire             tl_over_c = (nrun_c > (1 << TL));
    localparam [NVW-1:0] WNV = W;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; active <= 1'b0; cmd_ready <= 1'b0; ph24 <= 5'd0; acc_cnt <= 0;
        end else begin
            ph24 <= (ph24 == 5'd23) ? 5'd0 : ph24 + 5'd1;
            cmd_ready <= !busy && !(cmd_valid && cmd_ready);
            acc_cnt <= acc_cnt + (iss && first_r) - pop_raw;
            if (cmd_valid && cmd_ready) begin
                busy <= 1'b1; active <= 1'b1;
            end else if (iss && last_r && last_o && last_p) begin
                active <= 1'b0;
            end
            if (o_valid && o_ready && o_last) busy <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (cmd_valid && cmd_ready) begin
            npos_r <= cmd_npos; nout_r <= cmd_nout; scale_r <= cmd_scale;
            nrun_r <= nrun_c; nlast_r <= ((cmd_nchunk - 1'b1) & (W - 1)) + 1'b1;
            nf_r <= cmd_nf; eps_r <= cmd_eps; wbase_r <= cmd_wbase;
            p <= 0; o <= 0; r <= 0; ssph <= cmd_scale; wcur <= cmd_wbase; xpos <= cmd_xbase;
        end else if (iss) begin
            if (!last_r) r <= r + 1'b1;
            else begin
                r <= 0;
                if (ssph) ssph <= 1'b0;
                else if (!last_o) o <= o + 1'b1;
                else begin
                    o <= 0; p <= p + 1'b1; ssph <= scale_r; wcur <= wbase_r; xpos <= xpos + nrun_r;
                end
            end
            if (!ssph && !(last_r && last_o)) wcur <= wcur + 1'b1;
        end
        // the task descriptor entering the delay line (a bubble still carries its group)
        d0 <= {DW{1'b0}};
        d0[F_V] <= iss;
        d0[F_SS] <= ssph;
        d0[F_LR] <= last_r;
        d0[F_GRP +: 3] <= ph24 / 3;
        d0[F_NV +: NVW] <= last_r ? nlast_r[NVW-1:0] : WNV;
        d0[F_WA +: AW] <= wcur;
        d0[F_XA +: AW] <= xpos + r;
        d0[F_POS +: PW] <= p;
        d0[F_IDX +: OXW] <= o;
        d0[F_R +: TL] <= r[TL-1:0];
        d0[F_LO] <= !ssph && last_o && last_p;
    end
    // delay line: dl[i] = d0 delayed i cycles (dl[0] = d0); the valid bit is reset
    reg  [NDL-1:0]        dlv;                      // valid bits (reset)
    reg  [(DW-1)*NDL-1:0] dld;                      // the other fields (no reset)
    wire [DW*(NDL+1)-1:0] dl;
    assign dl[DW-1:0] = d0;
    generate for (gv = 0; gv < NDL; gv = gv + 1) begin : g_dl
        assign dl[DW*(gv+1) +: DW] = {dld[(DW-1)*gv +: DW-1], dlv[gv]};
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) dlv <= {NDL{1'b0}};
        else for (i = 0; i < NDL; i = i + 1) dlv[i] <= dl[DW*i + F_V];
    end
    always @(posedge clk)
        for (i = 0; i < NDL; i = i + 1) dld[(DW-1)*i +: DW-1] <= dl[DW*i + 1 +: DW-1];

    // ------------------------------------------------------------------ bank addresses (term k at tap 3k)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w_re <= 8'd0; x_re <= 8'd0; end
        else for (i = 0; i < 8; i = i + 1) begin
            w_re[i] <= dl[DW*(3*i) + F_V] && !dl[DW*(3*i) + F_SS];
            x_re[i] <= dl[DW*(3*i) + F_V];
        end
    end
    always @(posedge clk)
        for (i = 0; i < 8; i = i + 1) begin
            w_addr[AW*i +: AW] <= dl[DW*(3*i) + F_WA +: AW];
            x_addr[AW*i +: AW] <= dl[DW*(3*i) + F_XA +: AW];
        end

    reg [W*32-1:0] leaf;
    reg            leaf_v;
    wire           lane_fault_any;
    assign sd_v = d0[F_V]; assign sd_ss = d0[F_SS]; assign sd_nv = d0[F_NV +: NVW]; assign sd_wa = d0[F_WA +: AW];
    assign sd_xa = d0[F_XA +: AW];
    generate if (SYS == 0) begin : g_flat
    // ------------------------------------------------------------------ input registers
    reg [8*W*32-1:0] w_in;
    reg [8*W*16-1:0] x_in;
    always @(posedge clk) begin
        w_in <= w_data;
        x_in <= x_data;
    end

    // ------------------------------------------------------------------ rotation to groups, masking
    // bank k's input register holds the task at tap 3k + 2 + ML
    wire [63:0] sel;                                  // sel[8g + k]
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_sel
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_k
            //: qualified by the task's valid bit: a bubble's group field may be stale (the delay line's data
            //: bits carry no reset), and only valid tasks are guaranteed one per group
            assign sel[8*gg + gk] = dl[DW*(3*gk + 2 + ML) + F_V] && (dl[DW*(3*gk + 2 + ML) + F_GRP +: 3] == gg);
        end
    end

    reg  [7:0]        gfirst, glast;                // first: a = +0 (term 0, or no task)
    reg  [7:0]        gov;                          // the group holds a task's operands
    wire [8*W-1:0]    lane_fault;
    wire [8*W*32-1:0] gsum;
    reg  [7:0]        lastv [0:6];                  // group's last-term flag, delayed 0..6 from gw
    reg  [7:0]        fst   [0:3];                  // group's first flag, delayed 0..3
    for (gg = 0; gg < 8; gg = gg + 1) begin : g_grp
        reg          ov, oss;
        reg [NVW-1:0] onv;
        reg [W*32-1:0] ow;
        reg [W*16-1:0] ox;
        integer k2;
        always @(*) begin
            ov = 1'b0; oss = 1'b0; onv = {NVW{1'b0}}; ow = {(W*32){1'b0}}; ox = {(W*16){1'b0}};
            for (k2 = 0; k2 < 8; k2 = k2 + 1) begin
                ov  = ov  | sel[8*gg + k2];
                oss = oss | (sel[8*gg + k2] & dl[DW*(3*k2 + 2 + ML) + F_SS]);
                onv = onv | ({NVW{sel[8*gg + k2]}} & dl[DW*(3*k2 + 2 + ML) + F_NV +: NVW]);
                ow  = ow  | ({(W*32){sel[8*gg + k2]}} & w_in[W*32*k2 +: W*32]);
                ox  = ox  | ({(W*16){sel[8*gg + k2]}} & x_in[W*16*k2 +: W*16]);
            end
        end
        for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
            wire        lv = ov && (gl < onv);
            wire [31:0] xw = {ox[16*gl +: 16], 16'h0000};
            reg  [31:0] gx, gw;                    // the lane's operands (lane-local registers)
            always @(posedge clk) begin
                gx <= lv ? xw : 32'd0;
                gw <= lv ? (oss ? xw : ow[32*gl +: 32]) : 32'd0;
            end
            // the lane: product, then the 3-slot interleaved accumulation
            wire [31:0] prod, sum;
            wire [1:0]  e0, e1;
            wire        v0, v1;
            ot_hdc_fp32_mul_fast__d4g_hc u_mul (.clk(clk), .rst_n(rst_n), .valid_in(gov[gg]),
                                        .a(gw), .b(gx),
                                        .y(prod), .err(e0), .valid_out(v0));
            ot_hdc_fp32_add_fast__d4g_hc u_add (.clk(clk), .rst_n(rst_n), .valid_in(v0),
                                        .a(fst[2][gg] ? 32'd0 : sum), .b(prod),
                                        .y(sum), .err(e1), .valid_out(v1));
            assign gsum[32*(W*gg + gl) +: 32] = sum;
            //: errors count only on a task's terms (the valid chains ride the units' own pipes)
            assign lane_fault[W*gg + gl] = (v0 && (|e0)) || (v1 && (|e1));
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) gov[gg] <= 1'b0; else gov[gg] <= ov;
        always @(posedge clk) begin
            gfirst[gg] <= sel[8*gg + 0] || !ov;
            glast[gg]  <= sel[8*gg + 7];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 7; i = i + 1) lastv[i] <= 8'd0;
        end else begin
            lastv[0] <= glast;
            for (i = 1; i < 7; i = i + 1) lastv[i] <= lastv[i-1];
        end
    end
    always @(posedge clk) begin
        fst[0] <= gfirst;
        for (i = 1; i < 4; i = i + 1) fst[i] <= fst[i-1];
    end
    //: fst[2] is the first flag of the term whose product the adder takes now;
    //: lastv[5] marks the group whose adder output is a finished chunk sum.
    wire [7:0] done_g = lastv[5];

    // ------------------------------------------------------------------ tree over the W chunk sums
    integer g3;
    always @(posedge clk) begin
        leaf <= {(W*32){1'b0}};
        for (g3 = 0; g3 < 8; g3 = g3 + 1)
            if (done_g[g3]) leaf <= gsum[W*32*g3 +: W*32];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= |done_g;
    end
    assign lane_fault_any = |lane_fault;
    end else begin : g_sys
    // the stage chain is outside: stage 7's chunk sums of the task at tap T_LEAF - 1 arrive on sys_sum now
    always @(posedge clk) leaf <= dl[DW*(T_LEAF-1) + F_V] ? sys_sum : {(W*32){1'b0}};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) leaf_v <= 1'b0;
        else leaf_v <= dl[DW*(T_LEAF-1) + F_V];
    assign lane_fault_any = sys_fault;
    end endgenerate
    wire [31:0] root;
    wire        tree_fault;
    wire        tree_vo;
    ot_hdc_v41x_addtree__d4g_hc #(.N(W)) u_tree (.clk(clk), .rst_n(rst_n), .v(leaf_v), .x(leaf), .y(root), .vo(tree_vo),
                                         .fault(tree_fault));
    wire [LW*3:0] tvv;
    ot_hdc_v41x_vline__d4g_hc #(.D(3*LW)) u_tvv (.clk(clk), .rst_n(rst_n), .v(leaf_v), .vd(tvv));

    // ------------------------------------------------------------------ tail: pairwise tree over runs
    wire [32*(TL+1)-1:0] ev_val;
    wire [TL:0]          ev_v;
    wire [TL-1:0]        tail_fault;
    assign ev_val[31:0] = root;
    assign ev_v[0] = tvv[3*LW];
    generate for (gv = 0; gv < TL; gv = gv + 1) begin : g_tail
        localparam integer TAP = T_TAIL + 3 * gv;
        wire bitl  = dl[DW*TAP + F_R + gv];
        wire lastr = dl[DW*TAP + F_LR];
        wire go    = ev_v[gv] && (bitl || lastr);
        reg [31:0] slot;
        always @(posedge clk) if (ev_v[gv] && !bitl && !lastr) slot <= ev_val[32*gv +: 32];
        wire [1:0] e;
        ot_hdc_fp32_add_fast__d4g_hc u_a (.clk(clk), .rst_n(rst_n), .valid_in(go),
                                  .a(bitl ? slot : 32'd0), .b(ev_val[32*gv +: 32]),
                                  .y(ev_val[32*(gv+1) +: 32]), .err(e), .valid_out(ev_v[gv+1]));
        assign tail_fault[gv] = ev_v[gv+1] && (|e);
    end endgenerate
    localparam integer T_RAW = T_TAIL + 3 * TL;
    wire raw_v   = ev_v[TL] && dl[DW*T_RAW + F_LR];
    wire raw_bad = ev_v[TL] && !dl[DW*T_RAW + F_LR];      // R > 2^TL

    // ------------------------------------------------------------------ raw-result FIFO
    localparam integer RQW = 1 + 1 + PW + OXW + 32;       // {last out, ss, pos, idx, value}
    reg  [RQW-1:0] rq [0:DF-1];
    reg  [DFW:0]   rq_wp, rq_rp;
    wire           rq_ne = (rq_wp != rq_rp);
    wire [RQW-1:0] rq_h = rq[rq_rp[DFW-1:0]];
    reg  [RQW-1:0] raw_w;
    reg            raw_wv;
    always @(posedge clk) begin
        raw_w <= {dl[DW*(T_RAW) + F_LO], dl[DW*(T_RAW) + F_SS], dl[DW*(T_RAW) + F_POS +: PW],
                  dl[DW*(T_RAW) + F_IDX +: OXW], ev_val[32*TL +: 32]};
        if (raw_wv) rq[rq_wp[DFW-1:0]] <= raw_w;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rq_wp <= 0; rq_rp <= 0; raw_wv <= 1'b0; end
        else begin
            raw_wv <= raw_v;
            if (raw_wv) rq_wp <= rq_wp + 1'b1;
            if (pop_raw) rq_rp <= rq_rp + 1'b1;
        end
    end
    wire          h_lo  = rq_h[RQW-1];
    wire          h_ss  = rq_h[RQW-2];
    wire [PW-1:0] h_pos = rq_h[32 + OXW +: PW];
    wire [OXW-1:0] h_idx = rq_h[32 +: OXW];
    wire [31:0]   h_val = rq_h[31:0];

    // ------------------------------------------------------------------ scalar r unit
    reg  [31:0]     rv [0:PMAX-1];
    reg  [PMAX-1:0] r_ok;
    reg  [3:0]      st;
    reg             pend;
    reg  [1:0]      it;
    reg  [PW-1:0]   rs_pos;
    reg  [31:0]     rs_q, rs_h, rs_y, rs_a;
    localparam [3:0] S_IDLE = 4'd0, S_DIV = 4'd1, S_EPS = 4'd2, S_HALF = 4'd3, S_YY = 4'd4, S_HY = 4'd5,
                     S_SUB = 4'd6, S_MY = 4'd7;
    wire rs_take = rq_ne && h_ss && (st == S_IDLE);
    // units
    reg         dv, av, mv;
    reg  [31:0] da, db, aa, ab, ma, mb;
    wire [31:0] dy, ay, my;
    wire        dvo, avo, mvo, dfl;
    wire [1:0]  aerr, merr;
    ot_hdc_fdiv__d4g_hc u_div (.clk(clk), .rst_n(rst_n), .v(dv), .a(da), .b(db), .y(dy), .vo(dvo), .fault(dfl));
    ot_hdc_fp32_add_fast__d4g_hc u_sa (.clk(clk), .rst_n(rst_n), .valid_in(av), .a(aa), .b(ab), .y(ay), .err(aerr),
                               .valid_out(avo));
    ot_hdc_fp32_mul_fast__d4g_hc u_sm (.clk(clk), .rst_n(rst_n), .valid_in(mv), .a(ma), .b(mb), .y(my), .err(merr),
                               .valid_out(mvo));
    wire rs_fault = (dvo && dfl) || (avo && (|aerr)) || (mvo && (|merr));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pend <= 1'b0; dv <= 1'b0; av <= 1'b0; mv <= 1'b0; r_ok <= {PMAX{1'b0}};
        end else begin
            dv <= 1'b0; av <= 1'b0; mv <= 1'b0;
            if (cmd_valid && cmd_ready) r_ok <= {PMAX{1'b0}};
            case (st)
                S_IDLE: if (rs_take) begin st <= S_DIV; pend <= 1'b0; end
                S_DIV:  if (!pend) begin dv <= 1'b1; pend <= 1'b1; end
                        else if (dvo) begin pend <= 1'b0; st <= S_EPS; end
                S_EPS:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_HALF; end
                S_HALF: if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_YY; end
                S_YY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_HY; end
                S_HY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin pend <= 1'b0; st <= S_SUB; end
                S_SUB:  if (!pend) begin av <= 1'b1; pend <= 1'b1; end
                        else if (avo) begin pend <= 1'b0; st <= S_MY; end
                S_MY:   if (!pend) begin mv <= 1'b1; pend <= 1'b1; end
                        else if (mvo) begin
                            pend <= 1'b0;
                            if (it == 2'd2) begin st <= S_IDLE; r_ok[rs_pos] <= 1'b1; end
                            else st <= S_YY;
                        end
                default: st <= S_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        if (st == S_IDLE && rs_take) begin
            rs_pos <= h_pos; da <= h_val; db <= nf_r; it <= 2'd0;
        end
        if (st == S_DIV && pend && dvo) begin aa <= dy; ab <= eps_r; end
        if (st == S_EPS && pend && avo) begin
            ma <= ay; mb <= 32'h3F000000;                         // half = v * 0.5
            rs_y <= 32'h5F3759DF - {1'b0, ay[31:1]};              // y0 from v's bits
        end
        if (st == S_HALF && pend && mvo) begin rs_h <= my; ma <= rs_y; mb <= rs_y; end
        if (st == S_YY && pend && mvo) begin ma <= rs_h; mb <= my; end
        if (st == S_HY && pend && mvo) begin aa <= 32'h3FC00000; ab <= {~my[31], my[30:0]}; end
        if (st == S_SUB && pend && avo) begin ma <= rs_y; mb <= ay; end
        if (st == S_MY && pend && mvo) begin
            rs_y <= my; ma <= my; mb <= my; it <= it + 1'b1;
            if (it == 2'd2) rv[rs_pos] <= my;
        end
    end

    // ------------------------------------------------------------------ output: raw * r
    localparam integer OQ = 8;
    localparam integer OTW = 1 + PW + OXW;
    reg  [3:0]  oinf;                                 // products in flight
    reg  [3:0]  ocnt;
    wire        o_room = ({1'b0, oinf} + {1'b0, ocnt} + {4'd0, o_valid}) < OQ;
    wire        h_ok = !scale_r || r_ok[h_pos];
    wire        take_out = rq_ne && !h_ss && h_ok && o_room;
    assign pop_raw = rs_take || take_out;
    reg         ov_in;
    reg  [31:0] oa, ob;
    reg  [OTW-1:0] otag_in;
    wire [31:0] oy;
    wire [1:0]  oerr;
    wire        ovo;
    wire [OTW-1:0] otag;
    ot_hdc_fp32_mul_fast__d4g_hc u_om (.clk(clk), .rst_n(rst_n), .valid_in(ov_in), .a(oa), .b(ob), .y(oy), .err(oerr),
                               .valid_out(ovo));
    ot_hdc_delay__d4g_hc #(.W(OTW), .D(3)) u_otag (.clk(clk), .rst_n(rst_n), .d(otag_in), .q(otag));
    reg  [OTW+31:0] oq [0:OQ-1];
    reg  [3:0]      oq_wp, oq_rp;
    wire            oq_ne = (oq_wp != oq_rp);
    wire            o_load = oq_ne && (!o_valid || o_ready);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov_in <= 1'b0; oinf <= 4'd0; ocnt <= 4'd0; oq_wp <= 4'd0; oq_rp <= 4'd0; o_valid <= 1'b0;
        end else begin
            ov_in <= take_out;
            oinf <= oinf + {3'd0, take_out} - {3'd0, ovo};
            ocnt <= ocnt + {3'd0, ovo} - {3'd0, o_load};
            if (ovo) oq_wp <= (oq_wp == OQ - 1) ? 4'd0 : oq_wp + 4'd1;
            if (o_load) oq_rp <= (oq_rp == OQ - 1) ? 4'd0 : oq_rp + 4'd1;
            if (o_load) o_valid <= 1'b1;
            else if (o_ready) o_valid <= 1'b0;
        end
    end
    always @(posedge clk) begin
        if (take_out) begin
            oa <= h_val; ob <= scale_r ? rv[h_pos] : 32'h3F800000; otag_in <= {h_lo, h_pos, h_idx};
        end
        if (ovo) oq[oq_wp] <= {otag, oy};
        if (o_load) {o_last, o_pos, o_idx, o_data} <= oq[oq_rp];
    end

    // ------------------------------------------------------------------ fault, idle
    reg lf_r, tf_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; idle <= 1'b1; lf_r <= 1'b0; tf_r <= 1'b0; end
        else begin
            lf_r <= lane_fault_any;
            tf_r <= tree_fault || (|tail_fault) || raw_bad || rs_fault || (ovo && (|oerr));
            if (cmd_valid && cmd_ready) fault <= tl_over_c;
            else if (lf_r || tf_r) fault <= 1'b1;
            idle <= !busy;
        end
    end
endmodule

// Valid delay line with a tap per stage (vd[k] = v delayed k cycles).
module ot_hdc_v41x_vline__d4g_hc #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    generate if (D == 0) begin : g0
        assign vd = v;
    end else begin : gd
        reg [D-1:0] line;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) line <= {D{1'b0}};
            else line <= (line << 1) | {{(D-1){1'b0}}, v};
        end
        assign vd = {line, v};
    end endgenerate
endmodule

// Pairwise tree ((x0 + x1) + (x2 + x3)) + ... over N binary32 inputs (N a power
// of two), one ot_hdc_fp32_add_fast__d4g_hc per node, 3 cycles per level, II 1.  v
// travels with the operands (vo = v delayed 3 log2 N); a node's error counts
// only on a valid pass, and fault is registered one cycle after it.
module ot_hdc_v41x_addtree__d4g_hc #(parameter integer N = 2) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [N*32-1:0] x,
    output wire [31:0]   y,
    output wire          vo,
    output reg           fault
);
    wire [1:0] e;
    generate if (N == 1) begin : g_one
        assign y = x;
        assign vo = v;
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= 1'b0;
    end else if (N == 2) begin : g_two
        ot_hdc_fp32_add_fast__d4g_hc u_a (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(x[31:0]), .b(x[63:32]), .y(y),
                                  .err(e), .valid_out(vo));
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= vo && (|e);
    end else begin : g_rec
        wire [31:0] yl, yr;
        wire        fl, fr, vl, vr;
        ot_hdc_v41x_addtree__d4g_hc #(.N(N / 2)) u_l (.clk(clk), .rst_n(rst_n), .v(v), .x(x[0 +: N*16]), .y(yl), .vo(vl),
                                               .fault(fl));
        ot_hdc_v41x_addtree__d4g_hc #(.N(N / 2)) u_r (.clk(clk), .rst_n(rst_n), .v(v), .x(x[N*16 +: N*16]), .y(yr), .vo(vr),
                                               .fault(fr));
        ot_hdc_fp32_add_fast__d4g_hc u_a (.clk(clk), .rst_n(rst_n), .valid_in(vl), .a(yl), .b(yr), .y(y), .err(e),
                                  .valid_out(vo));
        always @(posedge clk or negedge rst_n) if (!rst_n) fault <= 1'b0; else fault <= (vo && (|e)) || fl || fr;
    end endgenerate
endmodule

// el1011-hcvm-hc: one SYSTOLIC bank stage of the HCP (SYS = 1).  Stage k holds W FP32 MAC lanes beside bank k's
// weight and x memories.  The task descriptor enters through pin flops (local cycle 0 = the flat engine's tap 3k),
// addresses its own bank (registered, local 1), takes the data ML cycles later (local 1 + ML) into input registers,
// forms the masked lane operands (local 3 + ML), multiplies (3 stages) and adds the product to the partial chunk sum
// that stage k - 1 hands over (pin flop, local 6 + ML; stage 0 adds to +0 through the `first` strap): the term order of
// csum is the flat engine's ((0 + t0) + t1) .. + t7, one binary32 op each, so the chunk sums are bit-identical.  The
// descriptor leaves after 3 registers (the next stage's pin flop makes the hop 4 cycles), the partial sums leave from
// the adder's output register, the lane-fault flag from a register.  No datapath register carries a reset; the
// per-lane operand enables are replicated kept registers (one per lane, no select net over all 32 lanes).
module ot_hdc_v41x_hcp_stage__d4g_hc #(
    parameter integer W   = 8,
    parameter integer AW  = 16,
    parameter integer ML  = 2,
    parameter integer NVW = $clog2(W) + 1,
    // pipelined IEEE units (1.2 GHz: 8-stage multiply, 7-stage add, ot_hdc_fp32_*_lat, bit for bit the fast units);
    // the stage hop is LA + 1 cycles (adder output register -> next stage's pin flop)
    parameter integer LM  = 8,
    parameter integer LA  = 7,
    // el1011-hbm-hcvm/hc round 3 (hc_tile-sys-048ca3d9e-b: rst relay -> u_add.y RESETN -310 ps, add y -> sum_out
    // pin -162 ps wire): SOR 1 registers sum_out at the seam (hop LA + 1 + SOR); LRST 1 gives every lane its own kept
    // reset flop (no rst_n net over 32 lanes' fp pipes); ADRST 0 builds the adders with data-bit reset off (valid only)
    parameter integer SOR = 0,
    parameter integer LRST = 0,
    parameter integer ADRST = 1,
    // el1011-hbm-hcvm/hc round 4 (hc_tile-sys-faa39cbe9-b EARLY_FAIL_HOLD: ONE clock root over 56,560 sinks, avg sink wire
    // 538 um, FF insertion 415..682 ps -> hold stuck at -165 ps inside u_mul pipes; textbook REFUSE > 15k sinks/root):
    // LG 8 = the lanes live in W/8 HARD lane-group leaves (ot_hdc_v41x_hcp_lanes__d4g_hc, own clock tree, ~13k sinks each);
    // the leaf's pin flops ARE the old input registers (w_in, x_in, sum_q, lv_r/ss_r, gov, fst_q) and its outputs are
    // the adder/seam registers + the registered group fault, so every latency is unchanged (SYS_LAT unchanged).
    parameter integer LG = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              first,
    input  wire              d_v,
    input  wire              d_ss,
    input  wire [NVW-1:0]    d_nv,
    input  wire [AW-1:0]     d_wa,
    input  wire [AW-1:0]     d_xa,
    output wire              o_v,
    output wire              o_ss,
    output wire [NVW-1:0]    o_nv,
    output wire [AW-1:0]     o_wa,
    output wire [AW-1:0]     o_xa,
    input  wire [W*32-1:0]   sum_in,
    output wire [W*32-1:0]   sum_out,
    input  wire              f_in,
    output reg               f_out,
    output reg               w_re,
    output reg  [AW-1:0]     w_addr,
    input  wire [W*32-1:0]   w_data,
    output reg               x_re,
    output reg  [AW-1:0]     x_addr,
    input  wire [W*16-1:0]   x_data
);
    localparam integer NC = (1 + ML > LA + SOR) ? 1 + ML : LA + SOR;   // descriptor delay taps kept locally
    localparam integer DW = 2 + NVW + 2 * AW;
    reg  [NC:0]      cv;                                         // valid, taps 0..NC (reset)
    reg  [DW-2:0]    cd [0:NC];                                  // other fields (no reset)
    reg              fin_q;
    wire             lf_any;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cv <= '0; w_re <= 1'b0; x_re <= 1'b0; fin_q <= 1'b0; f_out <= 1'b0; end
        else begin
            cv <= {cv[NC-1:0], d_v};
            w_re <= cv[0] && !cd[0][DW-2];
            x_re <= cv[0];
            fin_q <= f_in;
            f_out <= fin_q || lf_any;
        end
    end
    always @(posedge clk) begin
        cd[0] <= {d_ss, d_nv, d_wa, d_xa};
        for (integer j = 1; j <= NC; j = j + 1) cd[j] <= cd[j-1];
        w_addr <= cd[0][2*AW-1:AW];
        x_addr <= cd[0][AW-1:0];
    end
    assign o_v = cv[LA + SOR]; assign {o_ss, o_nv, o_wa, o_xa} = cd[LA + SOR]; // tap j = local j: out at local LA + SOR
    generate if (LG == 0) begin : g_flat
    reg fst_q, gov, lf_q;
    assign lf_any = lf_q;
    always @(posedge clk) fst_q <= first;
    // input registers (local 2 + ML) and the per-lane enables of that task (computed a cycle early, replicated)
    reg [W*32-1:0] w_in; reg [W*16-1:0] x_in;
    (* keep = "true" *) reg [W-1:0] lv_r, ss_r;
    reg ov_r;
    wire [NVW-1:0] nv_e = cd[1 + ML][DW-3 -: NVW];               // the task at local 1 + ML
    always @(posedge clk) begin
        w_in <= w_data; x_in <= x_data;
        for (integer l = 0; l < W; l = l + 1) begin
            lv_r[l] <= cv[1 + ML] && (l < nv_e);
            ss_r[l] <= cd[1 + ML][DW-2];
        end
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
    reg [W*32-1:0] sum_q;
    always @(posedge clk) sum_q <= sum_in;
    wire [W-1:0] lfl;
    wire [W*32-1:0] y_l;
    if (SOR != 0) begin : g_sor
        reg [W*32-1:0] so_q; always @(posedge clk) so_q <= y_l; assign sum_out = so_q;
    end else begin : g_nsor
        assign sum_out = y_l;
    end
    for (genvar gl = 0; gl < W; gl = gl + 1) begin : g_lane
        wire lrn;
        if (LRST != 0) begin : g_lr
            (* keep = "true" *) reg r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= 1'b1;
            assign lrn = r;
        end else begin : g_nlr
            assign lrn = rst_n;
        end
        wire [31:0] xw = {x_in[16*gl +: 16], 16'h0000};
        reg  [31:0] gx, gw;
        always @(posedge clk) begin
            gx <= lv_r[gl] ? xw : 32'd0;
            gw <= lv_r[gl] ? (ss_r[gl] ? xw : w_in[32*gl +: 32]) : 32'd0;
        end
        wire [31:0] prod; wire [1:0] e0, e1; wire v0, v1;
        ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(LM)) u_mul (.clk(clk), .rst_n(lrn), .valid_in(gov), .a(gw), .b(gx), .y(prod),
                                    .err(e0), .valid_out(v0));
        ot_hdc_fp32_add_lat__d4g_hc #(.LAT(LA), .DRST(ADRST)) u_add (.clk(clk), .rst_n(lrn), .valid_in(v0), .a(fst_q ? 32'd0 : sum_q[32*gl +: 32]),
                                    .b(prod), .y(y_l[32*gl +: 32]), .err(e1), .valid_out(v1));
        assign lfl[gl] = (v0 && (|e0)) || (v1 && (|e1));
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gov <= 1'b0; lf_q <= 1'b0; end else begin gov <= ov_r; lf_q <= |lfl; end
    end else begin : g_lg
        // enables one cycle earlier (task at local ML) in the shell; the leaf's pin flops hold them at local 2 + ML
        localparam integer NG = W / LG;
        (* keep = "true" *) reg [W-1:0] lvs, sss;
        reg ov_r;
        wire [NVW-1:0] nv_p = cd[ML][DW-3 -: NVW];
        always @(posedge clk) for (integer l = 0; l < W; l = l + 1) begin
            lvs[l] <= cv[ML] && (l < nv_p);
            sss[l] <= cd[ML][DW-2];
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
        wire [NG-1:0] lfg;
        for (genvar gg = 0; gg < NG; gg = gg + 1) begin : g_grp
            // hard child: instantiated WITHOUT parameter overrides (its defaults are the hardened configuration)
            ot_hdc_v41x_hcp_lanes__d4g_hc u_lg (.clk(clk), .rst_n(rst_n), .fst(first), .gov_i(ov_r), .lv_i(lvs[gg*LG +: LG]),
                .ss_i(sss[gg*LG +: LG]), .w_i(w_data[gg*LG*32 +: LG*32]), .x_i(x_data[gg*LG*16 +: LG*16]),
                .s_i(sum_in[gg*LG*32 +: LG*32]), .y(sum_out[gg*LG*32 +: LG*32]), .lf(lfg[gg]));
        end
        // the leaves' registered group faults stand in for lf_q (same cycle)
        assign lf_any = |lfg;
    end endgenerate
endmodule

// el1011-hbm-hcvm/hc round 4: HARD LANE-GROUP LEAF of the systolic HC bank tile (ot_hdc_v41x_hcp_stage__d4g_hc LG = 8).  G FP32
// MAC lanes (product = w * x, partial chunk sum + product) exactly as the stage's flat g_lane, with its own clock tree.
// Every input lands in a pin flop that is the flat stage's input register (w_in, x_in, sum_q, lv_r, ss_r, gov, fst_q),
// every output is a flop (the seam register so_q when SOR, the adder output otherwise; lf = the flat lf_q), so the
// stage latency is bit-for-bit and cycle-for-cycle the flat one.  The defaults ARE the hardened configuration (the
// stage instantiates it without overrides).
module ot_hdc_v41x_hcp_lanes__d4g_hc #(
    parameter integer G     = 8,
    parameter integer LM    = 8,
    parameter integer LA    = 7,
    parameter integer SOR   = 1,
    parameter integer LRST  = 1,
    parameter integer ADRST = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            fst,
    input  wire            gov_i,
    input  wire [G-1:0]    lv_i,
    input  wire [G-1:0]    ss_i,
    input  wire [G*32-1:0] w_i,
    input  wire [G*16-1:0] x_i,
    input  wire [G*32-1:0] s_i,
    output wire [G*32-1:0] y,
    output reg             lf
);
    reg [G*32-1:0] w_in, sum_q; reg [G*16-1:0] x_in;
    (* keep = "true" *) reg [G-1:0] lv_r, ss_r;
    reg fst_q, gov;
    always @(posedge clk) begin
        w_in <= w_i; x_in <= x_i; sum_q <= s_i; lv_r <= lv_i; ss_r <= ss_i; fst_q <= fst;
    end
    wire [G-1:0] lfl;
    wire [G*32-1:0] y_l;
    generate if (SOR != 0) begin : g_sor
        reg [G*32-1:0] so_q; always @(posedge clk) so_q <= y_l; assign y = so_q;
    end else begin : g_nsor
        assign y = y_l;
    end endgenerate
    genvar gl;
    generate for (gl = 0; gl < G; gl = gl + 1) begin : g_lane
        wire lrn;
        if (LRST != 0) begin : g_lr
            (* keep = "true" *) reg r; always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= 1'b1;
            assign lrn = r;
        end else begin : g_nlr
            assign lrn = rst_n;
        end
        wire [31:0] xw = {x_in[16*gl +: 16], 16'h0000};
        reg  [31:0] gx, gw;
        always @(posedge clk) begin
            gx <= lv_r[gl] ? xw : 32'd0;
            gw <= lv_r[gl] ? (ss_r[gl] ? xw : w_in[32*gl +: 32]) : 32'd0;
        end
        wire [31:0] prod; wire [1:0] e0, e1; wire v0, v1;
        ot_hdc_fp32_mul_lat__d4g_hc #(.LAT(LM)) u_mul (.clk(clk), .rst_n(lrn), .valid_in(gov), .a(gw), .b(gx), .y(prod),
                                    .err(e0), .valid_out(v0));
        ot_hdc_fp32_add_lat__d4g_hc #(.LAT(LA), .DRST(ADRST)) u_add (.clk(clk), .rst_n(lrn), .valid_in(v0),
                                    .a(fst_q ? 32'd0 : sum_q[32*gl +: 32]), .b(prod), .y(y_l[32*gl +: 32]), .err(e1),
                                    .valid_out(v1));
        assign lfl[gl] = (v0 && (|e0)) || (v1 && (|e1));
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gov <= 1'b0; lf <= 1'b0; end else begin gov <= gov_i; lf <= |lfl; end
endmodule


// Scoped source: rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Special-function pipes of the V4.1 vector stream unit (ot_hdc_v41x_vec), at
// the fast-FP depths and with NO padding:
//
//   ot_hdc_v41x_exp__d4g_hc       exp(x), DEPTH 49     } verbatim copies of ot_hdc_exp__d4g_hc and
//   ot_hdc_v41x_rsqrt__d4g_hc     1/sqrt(x), DEPTH 37  } ot_hdc_rsqrt__d4g_hc in rtl/hdc/ot_hdc_sfu.sv
//                                                on branch worktree-agent-a516a664e7d53536c
//                                                (acc46e61), renamed only.  The
//                                                main-line file keeps the five-stage
//                                                pipes under the old names.  Their
//                                                algorithms are tools/hdc_golden.py
//                                                exp and rsqrt, checked there on all
//                                                2^32 inputs.
//   ot_hdc_v41x_fdiv__d4g_hc      IEEE binary32 division, DEPTH 19 (rtl/hdc/v41/ot_hdc_fdiv__d4g_hc's
//                         digit recurrence, two quotient bits per stage, radix-4 select)
//   ot_hdc_v41x_softplus__d4g_hc  softplus and sqrt(softplus), DEPTH 162
//   ot_hdc_v41x_ins__d4g_hc       an insertion delay line: variable depth, in order
//
// They are built from the fast binary32 add and multiply (rtl/hdc/ot_hdc_fastfp.sv:
// LATENCY 3, II 1), which are bit-identical to the qualified five-stage pipes.
// ---------------------------------------------------------------------------

// exp(x): clamp to [-87, 88]; t = x*log2e; n = rint(t); two-constant Cody-Waite
// reduction; degree-6 Horner; 2^n added to the exponent.
//
// The golden forms n by the 1.5*2^23 trick: u = t + 1.5*2^23 is the exact sum
// rounded to an integer, ties to even (|t| < 2^22 puts u in [2^23, 2^24), where
// the ulp is 1, and 1.5*2^23 is even), and n = u - 1.5*2^23 is exact.  That is
// rint-to-even of t, so here it is one integer step on t's encoding.  n*ln2_hi
// (exact) and RN(n*ln2_lo) depend on n alone, n in [-126, 127] after the clamp:
// a 254-entry table holding the golden's own products.
module ot_hdc_v41x_exp__d4g_hc #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_hc)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat__d4g_hc: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer T_N = 1 + LM + 1;        // n registered
    localparam integer T_K = T_N + 1;           // table products registered
    localparam integer T_R1 = T_K + LA;
    localparam integer T_R = T_R1 + LA;
    localparam integer T_P = T_R + 6 * (LM + LA);
    localparam integer DEPTH = T_P + 1;         // 7 LM + 8 LA + 4: 49 (LM 3), 56 (LM 4)
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction
    //: {n*LN2_HI, RN(n*LN2_LO)}: the golden's binary32 products (hdc_golden.mul,
    //: canonical +0 at n = 0), indexed by n's low 8 bits.
    function automatic [63:0] ln2_nk(input [7:0] nk);
        case (nk)
            8'd130: ln2_nk = {32'hC2AEAC38, 32'hB93CBF94};   // n = -126
            8'd131: ln2_nk = {32'hC2AD4954, 32'hB93B4017};   // n = -125
            8'd132: ln2_nk = {32'hC2ABE670, 32'hB939C09A};   // n = -124
            8'd133: ln2_nk = {32'hC2AA838C, 32'hB938411C};   // n = -123
            8'd134: ln2_nk = {32'hC2A920A8, 32'hB936C19F};   // n = -122
            8'd135: ln2_nk = {32'hC2A7BDC4, 32'hB9354222};   // n = -121
            8'd136: ln2_nk = {32'hC2A65AE0, 32'hB933C2A5};   // n = -120
            8'd137: ln2_nk = {32'hC2A4F7FC, 32'hB9324328};   // n = -119
            8'd138: ln2_nk = {32'hC2A39518, 32'hB930C3AB};   // n = -118
            8'd139: ln2_nk = {32'hC2A23234, 32'hB92F442E};   // n = -117
            8'd140: ln2_nk = {32'hC2A0CF50, 32'hB92DC4B1};   // n = -116
            8'd141: ln2_nk = {32'hC29F6C6C, 32'hB92C4534};   // n = -115
            8'd142: ln2_nk = {32'hC29E0988, 32'hB92AC5B6};   // n = -114
            8'd143: ln2_nk = {32'hC29CA6A4, 32'hB9294639};   // n = -113
            8'd144: ln2_nk = {32'hC29B43C0, 32'hB927C6BC};   // n = -112
            8'd145: ln2_nk = {32'hC299E0DC, 32'hB926473F};   // n = -111
            8'd146: ln2_nk = {32'hC2987DF8, 32'hB924C7C2};   // n = -110
            8'd147: ln2_nk = {32'hC2971B14, 32'hB9234845};   // n = -109
            8'd148: ln2_nk = {32'hC295B830, 32'hB921C8C8};   // n = -108
            8'd149: ln2_nk = {32'hC294554C, 32'hB920494B};   // n = -107
            8'd150: ln2_nk = {32'hC292F268, 32'hB91EC9CE};   // n = -106
            8'd151: ln2_nk = {32'hC2918F84, 32'hB91D4A50};   // n = -105
            8'd152: ln2_nk = {32'hC2902CA0, 32'hB91BCAD3};   // n = -104
            8'd153: ln2_nk = {32'hC28EC9BC, 32'hB91A4B56};   // n = -103
            8'd154: ln2_nk = {32'hC28D66D8, 32'hB918CBD9};   // n = -102
            8'd155: ln2_nk = {32'hC28C03F4, 32'hB9174C5C};   // n = -101
            8'd156: ln2_nk = {32'hC28AA110, 32'hB915CCDF};   // n = -100
            8'd157: ln2_nk = {32'hC2893E2C, 32'hB9144D62};   // n = -99
            8'd158: ln2_nk = {32'hC287DB48, 32'hB912CDE5};   // n = -98
            8'd159: ln2_nk = {32'hC2867864, 32'hB9114E68};   // n = -97
            8'd160: ln2_nk = {32'hC2851580, 32'hB90FCEEA};   // n = -96
            8'd161: ln2_nk = {32'hC283B29C, 32'hB90E4F6D};   // n = -95
            8'd162: ln2_nk = {32'hC2824FB8, 32'hB90CCFF0};   // n = -94
            8'd163: ln2_nk = {32'hC280ECD4, 32'hB90B5073};   // n = -93
            8'd164: ln2_nk = {32'hC27F13E0, 32'hB909D0F6};   // n = -92
            8'd165: ln2_nk = {32'hC27C4E18, 32'hB9085179};   // n = -91
            8'd166: ln2_nk = {32'hC2798850, 32'hB906D1FC};   // n = -90
            8'd167: ln2_nk = {32'hC276C288, 32'hB905527F};   // n = -89
            8'd168: ln2_nk = {32'hC273FCC0, 32'hB903D302};   // n = -88
            8'd169: ln2_nk = {32'hC27136F8, 32'hB9025385};   // n = -87
            8'd170: ln2_nk = {32'hC26E7130, 32'hB900D407};   // n = -86
            8'd171: ln2_nk = {32'hC26BAB68, 32'hB8FEA915};   // n = -85
            8'd172: ln2_nk = {32'hC268E5A0, 32'hB8FBAA1A};   // n = -84
            8'd173: ln2_nk = {32'hC2661FD8, 32'hB8F8AB20};   // n = -83
            8'd174: ln2_nk = {32'hC2635A10, 32'hB8F5AC26};   // n = -82
            8'd175: ln2_nk = {32'hC2609448, 32'hB8F2AD2C};   // n = -81
            8'd176: ln2_nk = {32'hC25DCE80, 32'hB8EFAE32};   // n = -80
            8'd177: ln2_nk = {32'hC25B08B8, 32'hB8ECAF37};   // n = -79
            8'd178: ln2_nk = {32'hC25842F0, 32'hB8E9B03D};   // n = -78
            8'd179: ln2_nk = {32'hC2557D28, 32'hB8E6B143};   // n = -77
            8'd180: ln2_nk = {32'hC252B760, 32'hB8E3B249};   // n = -76
            8'd181: ln2_nk = {32'hC24FF198, 32'hB8E0B34E};   // n = -75
            8'd182: ln2_nk = {32'hC24D2BD0, 32'hB8DDB454};   // n = -74
            8'd183: ln2_nk = {32'hC24A6608, 32'hB8DAB55A};   // n = -73
            8'd184: ln2_nk = {32'hC247A040, 32'hB8D7B660};   // n = -72
            8'd185: ln2_nk = {32'hC244DA78, 32'hB8D4B766};   // n = -71
            8'd186: ln2_nk = {32'hC24214B0, 32'hB8D1B86B};   // n = -70
            8'd187: ln2_nk = {32'hC23F4EE8, 32'hB8CEB971};   // n = -69
            8'd188: ln2_nk = {32'hC23C8920, 32'hB8CBBA77};   // n = -68
            8'd189: ln2_nk = {32'hC239C358, 32'hB8C8BB7D};   // n = -67
            8'd190: ln2_nk = {32'hC236FD90, 32'hB8C5BC82};   // n = -66
            8'd191: ln2_nk = {32'hC23437C8, 32'hB8C2BD88};   // n = -65
            8'd192: ln2_nk = {32'hC2317200, 32'hB8BFBE8E};   // n = -64
            8'd193: ln2_nk = {32'hC22EAC38, 32'hB8BCBF94};   // n = -63
            8'd194: ln2_nk = {32'hC22BE670, 32'hB8B9C09A};   // n = -62
            8'd195: ln2_nk = {32'hC22920A8, 32'hB8B6C19F};   // n = -61
            8'd196: ln2_nk = {32'hC2265AE0, 32'hB8B3C2A5};   // n = -60
            8'd197: ln2_nk = {32'hC2239518, 32'hB8B0C3AB};   // n = -59
            8'd198: ln2_nk = {32'hC220CF50, 32'hB8ADC4B1};   // n = -58
            8'd199: ln2_nk = {32'hC21E0988, 32'hB8AAC5B6};   // n = -57
            8'd200: ln2_nk = {32'hC21B43C0, 32'hB8A7C6BC};   // n = -56
            8'd201: ln2_nk = {32'hC2187DF8, 32'hB8A4C7C2};   // n = -55
            8'd202: ln2_nk = {32'hC215B830, 32'hB8A1C8C8};   // n = -54
            8'd203: ln2_nk = {32'hC212F268, 32'hB89EC9CE};   // n = -53
            8'd204: ln2_nk = {32'hC2102CA0, 32'hB89BCAD3};   // n = -52
            8'd205: ln2_nk = {32'hC20D66D8, 32'hB898CBD9};   // n = -51
            8'd206: ln2_nk = {32'hC20AA110, 32'hB895CCDF};   // n = -50
            8'd207: ln2_nk = {32'hC207DB48, 32'hB892CDE5};   // n = -49
            8'd208: ln2_nk = {32'hC2051580, 32'hB88FCEEA};   // n = -48
            8'd209: ln2_nk = {32'hC2024FB8, 32'hB88CCFF0};   // n = -47
            8'd210: ln2_nk = {32'hC1FF13E0, 32'hB889D0F6};   // n = -46
            8'd211: ln2_nk = {32'hC1F98850, 32'hB886D1FC};   // n = -45
            8'd212: ln2_nk = {32'hC1F3FCC0, 32'hB883D302};   // n = -44
            8'd213: ln2_nk = {32'hC1EE7130, 32'hB880D407};   // n = -43
            8'd214: ln2_nk = {32'hC1E8E5A0, 32'hB87BAA1A};   // n = -42
            8'd215: ln2_nk = {32'hC1E35A10, 32'hB875AC26};   // n = -41
            8'd216: ln2_nk = {32'hC1DDCE80, 32'hB86FAE32};   // n = -40
            8'd217: ln2_nk = {32'hC1D842F0, 32'hB869B03D};   // n = -39
            8'd218: ln2_nk = {32'hC1D2B760, 32'hB863B249};   // n = -38
            8'd219: ln2_nk = {32'hC1CD2BD0, 32'hB85DB454};   // n = -37
            8'd220: ln2_nk = {32'hC1C7A040, 32'hB857B660};   // n = -36
            8'd221: ln2_nk = {32'hC1C214B0, 32'hB851B86B};   // n = -35
            8'd222: ln2_nk = {32'hC1BC8920, 32'hB84BBA77};   // n = -34
            8'd223: ln2_nk = {32'hC1B6FD90, 32'hB845BC82};   // n = -33
            8'd224: ln2_nk = {32'hC1B17200, 32'hB83FBE8E};   // n = -32
            8'd225: ln2_nk = {32'hC1ABE670, 32'hB839C09A};   // n = -31
            8'd226: ln2_nk = {32'hC1A65AE0, 32'hB833C2A5};   // n = -30
            8'd227: ln2_nk = {32'hC1A0CF50, 32'hB82DC4B1};   // n = -29
            8'd228: ln2_nk = {32'hC19B43C0, 32'hB827C6BC};   // n = -28
            8'd229: ln2_nk = {32'hC195B830, 32'hB821C8C8};   // n = -27
            8'd230: ln2_nk = {32'hC1902CA0, 32'hB81BCAD3};   // n = -26
            8'd231: ln2_nk = {32'hC18AA110, 32'hB815CCDF};   // n = -25
            8'd232: ln2_nk = {32'hC1851580, 32'hB80FCEEA};   // n = -24
            8'd233: ln2_nk = {32'hC17F13E0, 32'hB809D0F6};   // n = -23
            8'd234: ln2_nk = {32'hC173FCC0, 32'hB803D302};   // n = -22
            8'd235: ln2_nk = {32'hC168E5A0, 32'hB7FBAA1A};   // n = -21
            8'd236: ln2_nk = {32'hC15DCE80, 32'hB7EFAE32};   // n = -20
            8'd237: ln2_nk = {32'hC152B760, 32'hB7E3B249};   // n = -19
            8'd238: ln2_nk = {32'hC147A040, 32'hB7D7B660};   // n = -18
            8'd239: ln2_nk = {32'hC13C8920, 32'hB7CBBA77};   // n = -17
            8'd240: ln2_nk = {32'hC1317200, 32'hB7BFBE8E};   // n = -16
            8'd241: ln2_nk = {32'hC1265AE0, 32'hB7B3C2A5};   // n = -15
            8'd242: ln2_nk = {32'hC11B43C0, 32'hB7A7C6BC};   // n = -14
            8'd243: ln2_nk = {32'hC1102CA0, 32'hB79BCAD3};   // n = -13
            8'd244: ln2_nk = {32'hC1051580, 32'hB78FCEEA};   // n = -12
            8'd245: ln2_nk = {32'hC0F3FCC0, 32'hB783D302};   // n = -11
            8'd246: ln2_nk = {32'hC0DDCE80, 32'hB76FAE32};   // n = -10
            8'd247: ln2_nk = {32'hC0C7A040, 32'hB757B660};   // n = -9
            8'd248: ln2_nk = {32'hC0B17200, 32'hB73FBE8E};   // n = -8
            8'd249: ln2_nk = {32'hC09B43C0, 32'hB727C6BC};   // n = -7
            8'd250: ln2_nk = {32'hC0851580, 32'hB70FCEEA};   // n = -6
            8'd251: ln2_nk = {32'hC05DCE80, 32'hB6EFAE32};   // n = -5
            8'd252: ln2_nk = {32'hC0317200, 32'hB6BFBE8E};   // n = -4
            8'd253: ln2_nk = {32'hC0051580, 32'hB68FCEEA};   // n = -3
            8'd254: ln2_nk = {32'hBFB17200, 32'hB63FBE8E};   // n = -2
            8'd255: ln2_nk = {32'hBF317200, 32'hB5BFBE8E};   // n = -1
            8'd0  : ln2_nk = {32'h00000000, 32'h00000000};   // n = 0
            8'd1  : ln2_nk = {32'h3F317200, 32'h35BFBE8E};   // n = 1
            8'd2  : ln2_nk = {32'h3FB17200, 32'h363FBE8E};   // n = 2
            8'd3  : ln2_nk = {32'h40051580, 32'h368FCEEA};   // n = 3
            8'd4  : ln2_nk = {32'h40317200, 32'h36BFBE8E};   // n = 4
            8'd5  : ln2_nk = {32'h405DCE80, 32'h36EFAE32};   // n = 5
            8'd6  : ln2_nk = {32'h40851580, 32'h370FCEEA};   // n = 6
            8'd7  : ln2_nk = {32'h409B43C0, 32'h3727C6BC};   // n = 7
            8'd8  : ln2_nk = {32'h40B17200, 32'h373FBE8E};   // n = 8
            8'd9  : ln2_nk = {32'h40C7A040, 32'h3757B660};   // n = 9
            8'd10 : ln2_nk = {32'h40DDCE80, 32'h376FAE32};   // n = 10
            8'd11 : ln2_nk = {32'h40F3FCC0, 32'h3783D302};   // n = 11
            8'd12 : ln2_nk = {32'h41051580, 32'h378FCEEA};   // n = 12
            8'd13 : ln2_nk = {32'h41102CA0, 32'h379BCAD3};   // n = 13
            8'd14 : ln2_nk = {32'h411B43C0, 32'h37A7C6BC};   // n = 14
            8'd15 : ln2_nk = {32'h41265AE0, 32'h37B3C2A5};   // n = 15
            8'd16 : ln2_nk = {32'h41317200, 32'h37BFBE8E};   // n = 16
            8'd17 : ln2_nk = {32'h413C8920, 32'h37CBBA77};   // n = 17
            8'd18 : ln2_nk = {32'h4147A040, 32'h37D7B660};   // n = 18
            8'd19 : ln2_nk = {32'h4152B760, 32'h37E3B249};   // n = 19
            8'd20 : ln2_nk = {32'h415DCE80, 32'h37EFAE32};   // n = 20
            8'd21 : ln2_nk = {32'h4168E5A0, 32'h37FBAA1A};   // n = 21
            8'd22 : ln2_nk = {32'h4173FCC0, 32'h3803D302};   // n = 22
            8'd23 : ln2_nk = {32'h417F13E0, 32'h3809D0F6};   // n = 23
            8'd24 : ln2_nk = {32'h41851580, 32'h380FCEEA};   // n = 24
            8'd25 : ln2_nk = {32'h418AA110, 32'h3815CCDF};   // n = 25
            8'd26 : ln2_nk = {32'h41902CA0, 32'h381BCAD3};   // n = 26
            8'd27 : ln2_nk = {32'h4195B830, 32'h3821C8C8};   // n = 27
            8'd28 : ln2_nk = {32'h419B43C0, 32'h3827C6BC};   // n = 28
            8'd29 : ln2_nk = {32'h41A0CF50, 32'h382DC4B1};   // n = 29
            8'd30 : ln2_nk = {32'h41A65AE0, 32'h3833C2A5};   // n = 30
            8'd31 : ln2_nk = {32'h41ABE670, 32'h3839C09A};   // n = 31
            8'd32 : ln2_nk = {32'h41B17200, 32'h383FBE8E};   // n = 32
            8'd33 : ln2_nk = {32'h41B6FD90, 32'h3845BC82};   // n = 33
            8'd34 : ln2_nk = {32'h41BC8920, 32'h384BBA77};   // n = 34
            8'd35 : ln2_nk = {32'h41C214B0, 32'h3851B86B};   // n = 35
            8'd36 : ln2_nk = {32'h41C7A040, 32'h3857B660};   // n = 36
            8'd37 : ln2_nk = {32'h41CD2BD0, 32'h385DB454};   // n = 37
            8'd38 : ln2_nk = {32'h41D2B760, 32'h3863B249};   // n = 38
            8'd39 : ln2_nk = {32'h41D842F0, 32'h3869B03D};   // n = 39
            8'd40 : ln2_nk = {32'h41DDCE80, 32'h386FAE32};   // n = 40
            8'd41 : ln2_nk = {32'h41E35A10, 32'h3875AC26};   // n = 41
            8'd42 : ln2_nk = {32'h41E8E5A0, 32'h387BAA1A};   // n = 42
            8'd43 : ln2_nk = {32'h41EE7130, 32'h3880D407};   // n = 43
            8'd44 : ln2_nk = {32'h41F3FCC0, 32'h3883D302};   // n = 44
            8'd45 : ln2_nk = {32'h41F98850, 32'h3886D1FC};   // n = 45
            8'd46 : ln2_nk = {32'h41FF13E0, 32'h3889D0F6};   // n = 46
            8'd47 : ln2_nk = {32'h42024FB8, 32'h388CCFF0};   // n = 47
            8'd48 : ln2_nk = {32'h42051580, 32'h388FCEEA};   // n = 48
            8'd49 : ln2_nk = {32'h4207DB48, 32'h3892CDE5};   // n = 49
            8'd50 : ln2_nk = {32'h420AA110, 32'h3895CCDF};   // n = 50
            8'd51 : ln2_nk = {32'h420D66D8, 32'h3898CBD9};   // n = 51
            8'd52 : ln2_nk = {32'h42102CA0, 32'h389BCAD3};   // n = 52
            8'd53 : ln2_nk = {32'h4212F268, 32'h389EC9CE};   // n = 53
            8'd54 : ln2_nk = {32'h4215B830, 32'h38A1C8C8};   // n = 54
            8'd55 : ln2_nk = {32'h42187DF8, 32'h38A4C7C2};   // n = 55
            8'd56 : ln2_nk = {32'h421B43C0, 32'h38A7C6BC};   // n = 56
            8'd57 : ln2_nk = {32'h421E0988, 32'h38AAC5B6};   // n = 57
            8'd58 : ln2_nk = {32'h4220CF50, 32'h38ADC4B1};   // n = 58
            8'd59 : ln2_nk = {32'h42239518, 32'h38B0C3AB};   // n = 59
            8'd60 : ln2_nk = {32'h42265AE0, 32'h38B3C2A5};   // n = 60
            8'd61 : ln2_nk = {32'h422920A8, 32'h38B6C19F};   // n = 61
            8'd62 : ln2_nk = {32'h422BE670, 32'h38B9C09A};   // n = 62
            8'd63 : ln2_nk = {32'h422EAC38, 32'h38BCBF94};   // n = 63
            8'd64 : ln2_nk = {32'h42317200, 32'h38BFBE8E};   // n = 64
            8'd65 : ln2_nk = {32'h423437C8, 32'h38C2BD88};   // n = 65
            8'd66 : ln2_nk = {32'h4236FD90, 32'h38C5BC82};   // n = 66
            8'd67 : ln2_nk = {32'h4239C358, 32'h38C8BB7D};   // n = 67
            8'd68 : ln2_nk = {32'h423C8920, 32'h38CBBA77};   // n = 68
            8'd69 : ln2_nk = {32'h423F4EE8, 32'h38CEB971};   // n = 69
            8'd70 : ln2_nk = {32'h424214B0, 32'h38D1B86B};   // n = 70
            8'd71 : ln2_nk = {32'h4244DA78, 32'h38D4B766};   // n = 71
            8'd72 : ln2_nk = {32'h4247A040, 32'h38D7B660};   // n = 72
            8'd73 : ln2_nk = {32'h424A6608, 32'h38DAB55A};   // n = 73
            8'd74 : ln2_nk = {32'h424D2BD0, 32'h38DDB454};   // n = 74
            8'd75 : ln2_nk = {32'h424FF198, 32'h38E0B34E};   // n = 75
            8'd76 : ln2_nk = {32'h4252B760, 32'h38E3B249};   // n = 76
            8'd77 : ln2_nk = {32'h42557D28, 32'h38E6B143};   // n = 77
            8'd78 : ln2_nk = {32'h425842F0, 32'h38E9B03D};   // n = 78
            8'd79 : ln2_nk = {32'h425B08B8, 32'h38ECAF37};   // n = 79
            8'd80 : ln2_nk = {32'h425DCE80, 32'h38EFAE32};   // n = 80
            8'd81 : ln2_nk = {32'h42609448, 32'h38F2AD2C};   // n = 81
            8'd82 : ln2_nk = {32'h42635A10, 32'h38F5AC26};   // n = 82
            8'd83 : ln2_nk = {32'h42661FD8, 32'h38F8AB20};   // n = 83
            8'd84 : ln2_nk = {32'h4268E5A0, 32'h38FBAA1A};   // n = 84
            8'd85 : ln2_nk = {32'h426BAB68, 32'h38FEA915};   // n = 85
            8'd86 : ln2_nk = {32'h426E7130, 32'h3900D407};   // n = 86
            8'd87 : ln2_nk = {32'h427136F8, 32'h39025385};   // n = 87
            8'd88 : ln2_nk = {32'h4273FCC0, 32'h3903D302};   // n = 88
            8'd89 : ln2_nk = {32'h4276C288, 32'h3905527F};   // n = 89
            8'd90 : ln2_nk = {32'h42798850, 32'h3906D1FC};   // n = 90
            8'd91 : ln2_nk = {32'h427C4E18, 32'h39085179};   // n = 91
            8'd92 : ln2_nk = {32'h427F13E0, 32'h3909D0F6};   // n = 92
            8'd93 : ln2_nk = {32'h4280ECD4, 32'h390B5073};   // n = 93
            8'd94 : ln2_nk = {32'h42824FB8, 32'h390CCFF0};   // n = 94
            8'd95 : ln2_nk = {32'h4283B29C, 32'h390E4F6D};   // n = 95
            8'd96 : ln2_nk = {32'h42851580, 32'h390FCEEA};   // n = 96
            8'd97 : ln2_nk = {32'h42867864, 32'h39114E68};   // n = 97
            8'd98 : ln2_nk = {32'h4287DB48, 32'h3912CDE5};   // n = 98
            8'd99 : ln2_nk = {32'h42893E2C, 32'h39144D62};   // n = 99
            8'd100: ln2_nk = {32'h428AA110, 32'h3915CCDF};   // n = 100
            8'd101: ln2_nk = {32'h428C03F4, 32'h39174C5C};   // n = 101
            8'd102: ln2_nk = {32'h428D66D8, 32'h3918CBD9};   // n = 102
            8'd103: ln2_nk = {32'h428EC9BC, 32'h391A4B56};   // n = 103
            8'd104: ln2_nk = {32'h42902CA0, 32'h391BCAD3};   // n = 104
            8'd105: ln2_nk = {32'h42918F84, 32'h391D4A50};   // n = 105
            8'd106: ln2_nk = {32'h4292F268, 32'h391EC9CE};   // n = 106
            8'd107: ln2_nk = {32'h4294554C, 32'h3920494B};   // n = 107
            8'd108: ln2_nk = {32'h4295B830, 32'h3921C8C8};   // n = 108
            8'd109: ln2_nk = {32'h42971B14, 32'h39234845};   // n = 109
            8'd110: ln2_nk = {32'h42987DF8, 32'h3924C7C2};   // n = 110
            8'd111: ln2_nk = {32'h4299E0DC, 32'h3926473F};   // n = 111
            8'd112: ln2_nk = {32'h429B43C0, 32'h3927C6BC};   // n = 112
            8'd113: ln2_nk = {32'h429CA6A4, 32'h39294639};   // n = 113
            8'd114: ln2_nk = {32'h429E0988, 32'h392AC5B6};   // n = 114
            8'd115: ln2_nk = {32'h429F6C6C, 32'h392C4534};   // n = 115
            8'd116: ln2_nk = {32'h42A0CF50, 32'h392DC4B1};   // n = 116
            8'd117: ln2_nk = {32'h42A23234, 32'h392F442E};   // n = 117
            8'd118: ln2_nk = {32'h42A39518, 32'h3930C3AB};   // n = 118
            8'd119: ln2_nk = {32'h42A4F7FC, 32'h39324328};   // n = 119
            8'd120: ln2_nk = {32'h42A65AE0, 32'h3933C2A5};   // n = 120
            8'd121: ln2_nk = {32'h42A7BDC4, 32'h39354222};   // n = 121
            8'd122: ln2_nk = {32'h42A920A8, 32'h3936C19F};   // n = 122
            8'd123: ln2_nk = {32'h42AA838C, 32'h3938411C};   // n = 123
            8'd124: ln2_nk = {32'h42ABE670, 32'h3939C09A};   // n = 124
            8'd125: ln2_nk = {32'h42AD4954, 32'h393B4017};   // n = 125
            8'd126: ln2_nk = {32'h42AEAC38, 32'h393CBF94};   // n = 126
            8'd127: ln2_nk = {32'h42B00F1C, 32'h393E3F11};   // n = 127
            default: ln2_nk = 64'd0;
        endcase
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t;
    wire [2:0] f;
    ot_hdc_qmul_lat__d4g_hc #(LM) m_t (clk, rst_n, vd[1], xc, K_LOG2E, t, f[0]);   // 1 + LM

    // n = rint-to-even(t), |t| < 127.  With E = field - 127, the integer part
    // is the significand shifted right by 23 - E (E in [-1, 6]); below E = -1,
    // |t| < 1/2 and n = 0.
    wire [23:0] tm = {1'b1, t[22:0]};
    wire [7:0]  te = t[30:23];
    wire [4:0]  tsh = 5'd23 - (te[4:0] - 5'd31);      // 23 - E, as te - 127 = te[4:0] - 31 (mod 32)
    wire [23:0] tip = tm >> tsh;
    wire [4:0]  trb = tsh - 5'd1;
    wire        thalf = tm[trb];
    wire        tstk = |(tm & ~({24{1'b1}} << trb));
    wire [7:0]  tmag = (te < 8'd126) ? 8'd0 : (tip[7:0] + {7'd0, thalf && (tstk || tip[0])});
    reg  [8:0]  nint;
    always @(posedge clk) nint <= t[31] ? -{1'b0, tmag} : {1'b0, tmag};

    reg [31:0] a_hi, a_lo;
    always @(posedge clk) {a_hi, a_lo} <= ln2_nk(nint[7:0]);

    wire [31:0] r1, r, xc_d, lo_d;
    ot_hdc_delay__d4g_hc #(.W(32), .D(T_K - 1)) d_x (clk, rst_n, xc, xc_d);
    ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_r1 (clk, rst_n, vd[T_K], xc_d, {~a_hi[31], a_hi[30:0]}, r1, f[1]);
    ot_hdc_delay__d4g_hc #(.W(32), .D(LA)) d_lo (clk, rst_n, a_lo, lo_d);
    ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_r  (clk, rst_n, vd[T_R1], r1, {~lo_d[31], lo_d[30:0]}, r, f[2]);

    // Horner: p = C0; six times p = p*r + C[k]; r travels in (LM+LA)-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay__d4g_hc #(.W(32), .D(LM + LA)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_qmul_lat__d4g_hc #(LM) u_m (clk, rst_n, vd[T_R + (LM + LA)*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) u_a (clk, rst_n, vd[T_R + (LM + LA)*(k-1) + LM], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [8:0] nint_d;
    ot_hdc_delay__d4g_hc #(.W(9), .D(T_P - T_N)) d_n (clk, rst_n, nint, nint_d);
    // 2^n into the exponent field (a keep-prefix add in the serial-domain build, LM != 3)
    wire [31:0] y_n;
    wire        unused_cy;
    ot_hdc_kadd__d4g_hc #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_yn (.a(pa[6]), .b({{14{nint_d[8]}}, nint_d, 23'd0}), .cin(1'b0),
                                                      .s(y_n), .cout(unused_cy));
    always @(posedge clk) y <= y_n;

    assign fault = |{f, hf};
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_v41x_rsqrt__d4g_hc #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_hc)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat__d4g_hc: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer IT = 3 * LM + LA;
    localparam integer DEPTH = 1 + 3 * IT;      // 37 (LM 3), 46 (LM 4)
    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    wire [31:0] y0_n;
    wire        unused_cy;
    ot_hdc_kadd__d4g_hc #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_y0 (.a(32'h5F3759DF), .b(~{1'b0, x[31:1]}), .cin(1'b1), .s(y0_n),
                                                      .cout(unused_cy));
    always @(posedge clk) y0 <= y0_n;
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_qmul_lat__d4g_hc #(LM) m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // LM
    ot_hdc_delay__d4g_hc #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 1 + LM
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay__d4g_hc #(.W(32), .D(IT)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_qmul_lat__d4g_hc #(LM) m_yy (clk, rst_n, vd[1 + IT*k],             yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_qmul_lat__d4g_hc #(LM) m_hm (clk, rst_n, vd[1 + IT*k + LM],        hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_s  (clk, rst_n, vd[1 + IT*k + 2*LM],      32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay__d4g_hc #(.W(32), .D(2*LM + LA)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_qmul_lat__d4g_hc #(LM) m_y  (clk, rst_n, vd[1 + IT*k + 2*LM + LA], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION: II 1, fixed DEPTH 19.
//
// The function, the operand decode, the finish and the fault convention are
// those of rtl/hdc/v41/ot_hdc_fdiv__d4g_hc.sv, transcribed unchanged:
//   y = RN_even(a / b), gradual underflow, every zero result +0; a nonfinite
//   operand, a zero divisor or an overflowing quotient fails closed
//   (fault, y = +0).
// What changes is the recurrence.  It forms the same 27 quotient bits and the
// same final remainder, but TWO bits per register stage.  A stage takes x = 4R
// (2 ma in the first stage), with R < mb the running remainder, so x < 4 mb.
// It forms x - mb, x - 2 mb and x - 3 mb in parallel, and the digit
// q = floor(x / mb) in [0, 3] is the largest with a non-negative difference.
// That is one subtract and a select, not two subtracts in series: the routed
// SFU lane measured two serial restoring steps at 907 MHz.  3 mb is formed
// once, in a stage after the decode.  The last stage forms one bit.  A
// correctly rounded quotient is unique, so the result is the same bit for bit.
// Stages: 1 decode, 1 (3 mb), 14 recurrence, 3 finish.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_fdiv__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer QB = 27;
    localparam integer NS = (QB + 1) / 2;      // 14
    localparam integer DEPTH = 2 + NS + 3;     // 19

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    wire [33:0] na = norm(a[30:23], a[22:0]);
    wire [33:0] nb = norm(b[30:23], b[22:0]);

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_zero <= (a[30:0] == 31'd0);
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // 3 mb, once
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= d_sign; e_zero <= d_zero; e_bad <= d_bad; e_e <= d_e;
        e_ma <= d_ma; e_mb <= d_mb; e_mb3 <= {2'b0, d_mb} + {1'b0, d_mb, 1'b0};
    end

    reg [24:0]        r_rem  [0:NS-1];
    reg [QB-1:0]      r_q    [0:NS-1];
    reg [23:0]        r_mb   [0:NS-1];
    reg [25:0]        r_mb3  [0:NS-1];
    reg               r_sign [0:NS-1];
    reg               r_zero [0:NS-1];
    reg               r_bad  [0:NS-1];
    reg signed [10:0] r_e    [0:NS-1];

    genvar j;
    generate
        for (j = 0; j < NS; j = j + 1) begin : g_rec
            // quotient bits 2j and 2j+1 (bit 2^-k is restoring step k); stage NS-1 forms one bit
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            wire [27:0]   d1 = {1'b0, x} - {4'b0, mb};
            wire [27:0]   d2 = {1'b0, x} - {3'b0, mb, 1'b0};
            wire [27:0]   d3 = {1'b0, x} - {2'b0, mb3};
            wire [1:0]    q  = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
            wire [26:0]   r  = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
            always @(posedge clk) begin
                r_rem[j]  <= r[24:0];
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[NS-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_zero <= r_zero[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = (25'd1 << sh) - 25'd1;
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3: round to nearest even, encode ----------------------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    wire [30:0] code = {f2_field, f2_sig[22:0]} + {30'd0, rup};
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule

// ---------------------------------------------------------------------------
// softplus(x) and sqrt(softplus(x)): II 1, fixed DEPTH 162.  The operation order
// of rtl/hdc/v41/ot_hdc_softplus.sv (tools/hdc_golden_v41.softplus, .sqrt), on
// the fast units:
//     t = exp(-|x|)            49     ot_hdc_v41x_exp__d4g_hc
//     u = t / (t + 2)          3 + 19 ot_hdc_qadd__d4g_hc, ot_hdc_v41x_fdiv__d4g_hc
//     u2 = u * u               3
//     p = 1/17; p = p*u2 + 1/(2i+1), i = 7 .. 0      8 x (3 + 3)
//     l = (u * p) * 2          3 + 3
//     sp = max(x, 0) + l       3
//     r = sqrt(sp)             31     ot_hdc_fsqrt__d4g_hc
// The fault convention is ot_hdc_softplus's.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_softplus__d4g_hc #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat__d4g_hc)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat__d4g_hc: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] sp,
    output wire [31:0] r,
    output wire        vo,
    output wire        fault
);
    localparam integer T_EXP  = 7 * LM + 8 * LA + 4;   // ot_hdc_v41x_exp__d4g_hc DEPTH
    localparam integer T_DEN  = T_EXP + LA;
    localparam integer T_U    = T_DEN + 19;
    localparam integer T_U2   = T_U + LM;
    localparam integer T_P    = T_U2 + 8 * (LM + LA);
    localparam integer T_UP   = T_P + LM;
    localparam integer T_L    = T_UP + LM;
    localparam integer T_SP   = T_L + LA;
    localparam integer DEPTH  = T_SP + 31;       // 162 (LM 3), 180 (LM 4)
    localparam [32*9-1:0] C = {32'h3D70F0F1, 32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39,
                               32'h3E124925, 32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000};  // 1/17 .. 1/1
    function automatic [31:0] coef(input integer i);
        coef = C[32*(8-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    wire [31:0] t, den, t_d, u, u2, lp, l;
    wire f_exp, f_den, f_div, f_u2, f_up, f_l, f_sp, f_sq;
    ot_hdc_v41x_exp__d4g_hc #(.LM(LM), .LA(LA)) u_exp (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b1, x[30:0]}), .y(t), .vo(), .fault(f_exp));
    ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_den (clk, rst_n, vd[T_EXP], t, 32'h40000000, den, f_den);
    ot_hdc_delay__d4g_hc #(.W(32), .D(LA)) d_t (clk, rst_n, t, t_d);
    ot_hdc_v41x_fdiv__d4g_hc u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    ot_hdc_qmul_lat__d4g_hc #(LM) m_u2 (clk, rst_n, vd[T_U], u, u, u2, f_u2);

    wire [31:0] u2d [0:7];
    wire [31:0] pm  [1:8];
    wire [31:0] pa  [0:8];
    wire [16:1] hf;
    assign u2d[0] = u2;
    assign pa[0] = coef(0);
    genvar k;
    generate
        for (k = 1; k <= 8; k = k + 1) begin : g_h
            if (k < 8) begin : g_d
                ot_hdc_delay__d4g_hc #(.W(32), .D(LM + LA)) d_u2 (clk, rst_n, u2d[k-1], u2d[k]);
            end
            ot_hdc_qmul_lat__d4g_hc #(LM) u_m (clk, rst_n, vd[T_U2 + (LM + LA)*(k-1)], pa[k-1], u2d[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) u_a (clk, rst_n, vd[T_U2 + (LM + LA)*(k-1) + LM], pm[k], coef(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [31:0] u_d;
    ot_hdc_delay__d4g_hc #(.W(32), .D(T_P - T_U)) d_u (clk, rst_n, u, u_d);
    ot_hdc_qmul_lat__d4g_hc #(LM) m_up (clk, rst_n, vd[T_P], u_d, pa[8], lp, f_up);
    ot_hdc_qmul_lat__d4g_hc #(LM) m_l  (clk, rst_n, vd[T_UP], lp, 32'h40000000, l, f_l);

    reg  [31:0] mx;
    wire [31:0] mx_d, spv;
    wire x_nan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    always @(posedge clk) mx <= (x[31] && !x_nan) ? 32'd0 : x;
    ot_hdc_delay__d4g_hc #(.W(32), .D(T_L - 1)) d_mx (clk, rst_n, mx, mx_d);
    ot_hdc_qadd_lat__d4g_hc #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_sp (clk, rst_n, vd[T_L], mx_d, l, spv, f_sp);

    ot_hdc_fsqrt__d4g_hc u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    ot_hdc_delay__d4g_hc #(.W(32), .D(DEPTH - T_SP)) d_sp (clk, rst_n, spv, sp);

    wire f_sp_d;
    ot_hdc_delay__d4g_hc #(.W(1), .D(DEPTH - T_SP), .RESET(1)) d_fsp (clk, rst_n, f_sp, f_sp_d);
    assign fault = f_sp_d | f_sq | f_exp | f_den | f_div | f_u2 | (|hf) | f_up | f_l;
endmodule

// ---------------------------------------------------------------------------
// Insertion delay line: an item entering with depth choice k leaves exactly
// DEPTHS[k] cycles later (0 = a wire), all items through ONE exit.  It is a
// shift register toward the exit whose stage DEPTHS[k] also loads new items.
// Items keep their order only if every item leaves after the one before it;
// the controller guarantees that (ot_hdc_v41x_vec: the checkpoint rule).  A
// stage that is loaded while an item shifts into it raises `coll`.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_ins__d4g_hc #(
    parameter integer W = 32,
    parameter integer K = 2,                 // depth choices
    parameter [16*K-1:0] DEPTHS = {16'd3, 16'd0},   // choice k = DEPTHS[16k +: 16]
    parameter integer DMAX = 3,              // max over DEPTHS
    parameter integer RESET_DATA = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [K-1:0] sel,                 // one-hot depth choice
    input  wire [W-1:0] d,
    output wire         vo,
    output wire [W-1:0] q,
    output wire         coll,
    output wire         busy                 // an item is in the line
);
    function automatic has(input integer p, input [K-1:0] s);
        integer k;
        begin
            has = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p && s[k]) has = 1'b1;
        end
    endfunction
    function automatic canbe(input integer p);
        integer k;
        begin
            canbe = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p) canbe = 1'b1;
        end
    endfunction
    generate
        if (DMAX == 0) begin : g_wire
            assign vo = v; assign q = d; assign coll = 1'b0; assign busy = 1'b0;
        end else begin : g_line
            reg [W-1:0] r  [1:DMAX];
            reg         rv [1:DMAX];
            wire [DMAX+1:1] cl;
            assign cl[DMAX+1] = 1'b0;
            genvar p;
            for (p = 1; p <= DMAX; p = p + 1) begin : g_s
                wire [W-1:0] nx  = (p == DMAX) ? {W{1'b0}} : r[(p == DMAX) ? p : p + 1];
                wire         nxv = (p == DMAX) ? 1'b0 : rv[(p == DMAX) ? p : p + 1];
                if (canbe(p)) begin : g_ld
                    wire ld = v && has(p, sel);
                    assign cl[p] = ld && nxv;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= ld || nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= ld ? d : nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= ld ? d : nx;
                    end
                end else begin : g_sh
                    assign cl[p] = 1'b0;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= nx;
                    end
                end
            end
            wire now = v && has(0, sel);
            assign vo = now || rv[1];
            assign q  = now ? d : r[1];
            assign coll = (|cl) || (now && rv[1]);
            reg any;
            integer b;
            always @(*) begin
                any = 1'b0;
                for (b = 1; b <= DMAX; b = b + 1) any = any | rv[b];
            end
            assign busy = any;
        end
    endgenerate
endmodule

// Scoped source: rtl/lib/ot_rst_relay.sv
`timescale 1ns/1ps
// Registered, replicated local reset relay (synchronous-release reset tree).
//
// Design standard (coordinator 2026-10-10, drive-1010): a block's rst_n INPUT PORT drives only this relay.  The port net
// fans out to SYNC_STAGES synchronizer flops plus the asynchronous clear of the REGIONS*TREE_STAGES relay flops (assert
// stays asynchronous and immediate); release is synchronous and takes SYNC_STAGES + TREE_STAGES rising clk edges.
// Each region k then resets its own flops from rst_n[k], a flop output that placement can put next to that region, so no
// net from the port (or from one relay flop) spans the block.  On ~7 blocks the port -> thousands of reset flops net was
// the worst setup / hold path (hgi su_unit / su_ctl, idx-topk, qwen tile_e, ds qelem x1b).
//
// The region copies are logically identical, so synthesis would merge them: they are (* keep *) registers, which the
// ORFS flow's SYNTH_CANONICALIZE_TCL hook (physical/common_flow/ot_keep_regs.tcl, 0d3958d56) turns into kept flop cells.
//
// Consumers: release is delayed by RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES cycles (exactness is transaction-level; any
// logic that counts cycles from reset release must count from rst_n[k], never from the port).
module ot_rst_relay__d4g_hc #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

    // relay tree: stage t, region r.  Every stage is replicated per region so each copy drives only its own region.
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

    assign rst_n = relay_q[TREE_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay__d4g_hc: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay__d4g_hc: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay__d4g_hc: REGIONS must be >= 1");
    end
`endif
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Correctly rounded binary32 SQUARE ROOT for the V4.1 decode core: II 1, fixed
// DEPTH 31.  A stage-rebalanced copy of the qualified
// rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv (FRAC_SHIFT 15), with the decode
// core's port convention (v/a -> y/vo/fault).
//
// WHAT CHANGED, AND WHY.  The qualified pipe routes at 766 MHz on ASAP7: its
// critical path is the single finishing stage, which finds the root's leading
// bit by a priority encoder over all 28 root bits, shifts by a variable amount,
// rounds and encodes in one cycle.  But the leading bit is not variable: the
// radicand is a 24- or 25-bit significand times 2^(2*FRAC_SHIFT), so the root
// lies in [2^(11.5+F), 2^(12.5+F)) and its top bit is bit F+12 or bit F+11.
// Here the finish is a 2-way select on root[F+12] (stage 1: truncated
// significand, guard, sticky, exponent) and a separate round-and-encode
// (stage 2).  The digit recurrence and the decode stage are transcribed
// unchanged.  rtl/test/tb_hdc_fsqrt_equiv.sv drives both modules from one
// stimulus and requires the same code and the same refusal for every operand,
// one cycle later.
//
// FUNCTION.  y = RN_even(sqrt(a)); sqrt(+-0) = +0; subnormal arguments are
// normalised; a negative or nonfinite argument FAILS CLOSED (fault, y = +0).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;   // the root's possible top bit

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (as qualified) ------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage (as qualified) --------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire take = (shifted >= trial);
            always @(posedge clk) begin
                rem_stage[g]  <= take ? (shifted - trial) : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1 -------------------------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    reg [23:0] f_trunc;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg signed [EXP_W-1:0] f_unb;       // unbiased exponent before the rounding carry
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        if (hi) begin
            f_trunc  <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
            f_unb    <= $signed(TOP) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end else begin
            f_trunc  <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
            f_unb    <= $signed(TOP - 1) + half_stage[STAGES] - $signed(FRAC_SHIFT);
        end
    end

    // ---- finish 2: round to nearest even, encode --------------------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc[0]);
    wire [24:0] rounded  = {1'b0, f_trunc} + {24'd0, round_up};
    wire        carried  = rounded[24];
    wire [23:0] sig_out  = carried ? rounded[24:1] : rounded[23:0];
    wire signed [EXP_W-1:0] biased = f_unb + (carried ? 12'sd1 : 12'sd0) + 12'sd127;
    wire out_of_range = (biased < 12'sd1) || (biased > 12'sd254);
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased[7:0], sig_out[22:0]}; fault <= 1'b0; end
    end
endmodule

// Scoped source: rtl/hdc/v41/ot_hdc_fsqrt_c12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_fsqrt_c12__d4g_hc: the 1.2 GHz (0.833 ns ASAP7 SS) successor of rtl/hdc/v41/ot_hdc_fsqrt__d4g_hc.sv for the HBM SU
// (hbm-su closure, 2026-10-05).  Same ports, same DEPTH 31, the same {vo, y, fault} on every cycle, bit for bit
// (rtl/test/tb_hdc_fsqrt_c12_equiv.sv drives both from one stimulus).  New file; the original is unchanged.
// Timing-only rewrites (closure kit: kept prefix adders, precomputed carries), no register moved:
//   * digit stage: `shifted >= trial` and `shifted - trial` are ONE kept Kogge-Stone subtractor
//     (ot_hdc_ksadd_k__d4g_hc: shifted + ~trial + 1; its carry out is the take bit), instead of a behavioural compare and
//     subtract that ABC ripples (routed -114 ps in the SU side pipe);
//   * finish 1 also registers both candidate biased exponents (no rounding carry / carry) and their
//     out-of-range flags, from the stage's own half exponent and top-bit select;
//   * finish 2 is only the kept 24-bit rounding increment (ot_hdc_inc_k__d4g_hc) and a carry select (was -167 ps).
//     When the increment carries out, the rounded significand is 2^24, so the 23 stored fraction bits are the
//     increment's low 23 bits either way.
// Needs rtl/hdc/ot_hdc_prefix.sv (ot_hdc_ksadd_k__d4g_hc, ot_hdc_inc_k__d4g_hc) and ot_hdc_vline__d4g_hc (rtl/hdc/ot_hdc_sfu.sv).
// ---------------------------------------------------------------------------
module ot_hdc_fsqrt_c12__d4g_hc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer FRAC_SHIFT    = 15;
    localparam integer RADICAND_BITS = 25 + 2 * FRAC_SHIFT;
    localparam integer STAGES        = (RADICAND_BITS + 1) / 2;
    localparam integer RAD_W         = 2 * STAGES;
    localparam integer Q_W           = STAGES;
    localparam integer REM_W         = STAGES + 4;
    localparam integer EXP_W         = 12;
    localparam integer DEPTH         = STAGES + 3;
    localparam integer TOP           = FRAC_SHIFT + 12;

    wire [DEPTH:0] vd;
    ot_hdc_vline__d4g_hc #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // ---- stage 0: unpack, normalise, force an even exponent (unchanged) ----------------
    wire [7:0]  in_biased   = a[30:23];
    wire [22:0] in_fraction = a[22:0];
    wire in_nonfinite = (in_biased == 8'hff);
    wire in_zero      = (a[30:0] == 31'b0);
    wire in_negative  = a[31] && !in_zero;
    wire in_subnormal = (in_biased == 8'b0);
    integer bit_index;
    reg [4:0] leading_shift;
    always @* begin
        leading_shift = 5'd23;
        for (bit_index = 0; bit_index < 23; bit_index = bit_index + 1)
            if (in_fraction[bit_index])
                leading_shift = 5'd22 - bit_index[4:0];
    end
    wire [23:0] significand = in_subnormal ? ({1'b0, in_fraction} << leading_shift) : {1'b1, in_fraction};
    wire signed [EXP_W-1:0] argument_exponent = in_subnormal
        ? (-12'sd149 - $signed({7'b0, leading_shift}))
        : ($signed({4'b0, in_biased}) - 12'sd150);
    wire exponent_odd = argument_exponent[0];
    wire [24:0] even_significand = exponent_odd ? {significand, 1'b0} : {1'b0, significand};
    wire signed [EXP_W-1:0] even_exponent = exponent_odd ? (argument_exponent - 12'sd1) : argument_exponent;
    wire signed [EXP_W-1:0] half_exponent = even_exponent >>> 1;

    reg [RAD_W-1:0]        s0_radicand;
    reg signed [EXP_W-1:0] s0_half;
    reg                    s0_zero, s0_err;
    always @(posedge clk) begin
        s0_radicand <= {{(RAD_W - RADICAND_BITS){1'b0}}, even_significand, {(2 * FRAC_SHIFT){1'b0}}};
        s0_half <= half_exponent;
        s0_zero <= in_zero;
        s0_err  <= in_nonfinite || in_negative;
    end

    // ---- stages 1..STAGES: one root digit per stage, one kept subtractor -------------------
    reg [RAD_W-1:0]        rad_stage  [1:STAGES];
    reg [REM_W-1:0]        rem_stage  [1:STAGES];
    reg [Q_W-1:0]          root_stage [1:STAGES];
    reg signed [EXP_W-1:0] half_stage [1:STAGES];
    reg                    zero_stage [1:STAGES];
    reg                    err_stage  [1:STAGES];
    genvar g;
    generate
        for (g = 1; g <= STAGES; g = g + 1) begin : g_dig
            wire [RAD_W-1:0] src_rad  = (g == 1) ? s0_radicand : rad_stage[g-1];
            wire [REM_W-1:0] src_rem  = (g == 1) ? {REM_W{1'b0}} : rem_stage[g-1];
            wire [Q_W-1:0]   src_root = (g == 1) ? {Q_W{1'b0}} : root_stage[g-1];
            wire [REM_W-1:0] shifted  = {src_rem[REM_W-3:0], src_rad[RAD_W-1:RAD_W-2]};
            wire [REM_W-1:0] trial    = ({{(REM_W-Q_W){1'b0}}, src_root} << 2) | {{(REM_W-1){1'b0}}, 1'b1};
            wire [REM_W-1:0] diff;
            wire             take;      // carry out of shifted + ~trial + 1  ==  (shifted >= trial)
            ot_hdc_ksadd_k__d4g_hc #(.W(REM_W)) u_sub (.a(shifted), .b(~trial), .cin(1'b1), .s(diff), .cout(take));
            always @(posedge clk) begin
                rem_stage[g]  <= take ? diff : shifted;
                root_stage[g] <= {src_root[Q_W-2:0], take};
                rad_stage[g]  <= {src_rad[RAD_W-3:0], 2'b00};
                half_stage[g] <= (g == 1) ? s0_half : half_stage[g-1];
                zero_stage[g] <= (g == 1) ? s0_zero : zero_stage[g-1];
                err_stage[g]  <= (g == 1) ? s0_err  : err_stage[g-1];
            end
        end
    endgenerate

    // ---- finish 1: the root's top bit is TOP or TOP-1; both candidate exponents ------------
    wire [Q_W-1:0]   root = root_stage[STAGES];
    wire [REM_W-1:0] rem  = rem_stage[STAGES];
    wire hi = root[TOP];
    // biased = f_unb + 127 (+1 on a rounding carry); f_unb = half + (TOP - FRAC_SHIFT) (hi) or one less
    wire signed [EXP_W-1:0] h = half_stage[STAGES];
    wire signed [EXP_W-1:0] b_lo_hi = h + $signed(TOP - FRAC_SHIFT + 127);      // hi, no carry
    wire signed [EXP_W-1:0] b_lo_lo = h + $signed(TOP - 1 - FRAC_SHIFT + 127);  // lo, no carry
    wire signed [EXP_W-1:0] b_hi_hi = h + $signed(TOP - FRAC_SHIFT + 128);      // hi, carry
    wire [EXP_W-1:0] b0 = hi ? b_lo_hi : b_lo_lo;
    wire [EXP_W-1:0] b1 = hi ? b_hi_hi : b_lo_hi;                                 // lo + carry == hi, no carry
    reg [22:0] f_trunc_l;   // the truncated significand, low 23 bits
    reg        f_trunc23;
    reg        f_guard, f_sticky, f_zero, f_err;
    reg [7:0]  f_b0, f_b1;
    reg        f_oor0, f_oor1;
    always @(posedge clk) begin
        f_zero <= zero_stage[STAGES];
        f_err  <= err_stage[STAGES];
        f_b0 <= b0[7:0];
        f_b1 <= b1[7:0];
        f_oor0 <= ($signed(b0) < 12'sd1) || ($signed(b0) > 12'sd254);
        f_oor1 <= ($signed(b1) < 12'sd1) || ($signed(b1) > 12'sd254);
        if (hi) begin
            {f_trunc23, f_trunc_l} <= root[TOP -: 24];
            f_guard  <= root[TOP - 24];
            f_sticky <= (|root[TOP - 25:0]) || (|rem);
        end else begin
            {f_trunc23, f_trunc_l} <= root[TOP - 1 -: 24];
            f_guard  <= root[TOP - 25];
            f_sticky <= (|root[TOP - 26:0]) || (|rem);
        end
    end

    // ---- finish 2: kept rounding increment, carry select, encode --------------------------
    wire        round_up = f_guard && (f_sticky || f_trunc_l[0]);
    wire [23:0] rounded;
    wire        carried;
    ot_hdc_inc_k__d4g_hc #(.W(24)) u_inc (.a({f_trunc23, f_trunc_l}), .inc(round_up), .y(rounded), .co(carried));
    wire [7:0] biased = carried ? f_b1 : f_b0;
    wire       out_of_range = carried ? f_oor1 : f_oor0;
    always @(posedge clk) begin
        if (f_err || (!f_zero && out_of_range)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f_zero) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {1'b0, biased, rounded[22:0]}; fault <= 1'b0; end
    end
endmodule


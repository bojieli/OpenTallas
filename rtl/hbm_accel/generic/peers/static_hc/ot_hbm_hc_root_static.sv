`timescale 1ns/1ps
`default_nettype none
// Static HC ROOT engine (HBM-B-RTL2, plan (b) d4g, 2026-10-17), die master hc_eng (centre).  Successor of the
// single-block ot_hbm_hc_eng_static for the per-quadrant die: the projection datapath (8 bank tiles x 256 lanes) moves
// into 4 quarter engines ot_hbm_hc_qeng_static (hc_eng_<q>, 64 lanes x 8 banks each, beside the quadrant's hc_<q>),
// and this root keeps everything else of the full engine unchanged:
//   PROGRAMME  the folded F20 programme + table targets and ot_hbm_hc_eng_seq_static (same event word layout; the
//              ingest event is forwarded to quarter e_ingq with its wave index now QUARTER-LOCAL, 0 .. K/1024 - 1).
//   CORE       ot_hdc_v41x_hcp_sys1_static W = 256 SYS = 1 with TPRE = 6: issue, descriptor (tap 0 -> the 4 quarters,
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
// Pin registers: every input lands in a pin flop, every output is a flop; rst_n through ot_rst_relay.
// MUT (bench): 2 = tail pre-sigmoid eps dropped (unit 0); 21 = SAFE mix SRAM lane write mask dropped (whole line).
// ELEM-GAPS/HBMB 2026-10-18: every runtime-indexed part-select replaced by decoded constant-index slices (gate synthesis
// stalled in yosys SHARE); function and cycles unchanged.
// HC-XRDU 2026-10-18 (RELEASE_TREE H.STA.WIRE.8): LANDED root <-> quarter links.  On the d4g die the root <-> hub links are
// landed lanes (half-cycle stations + a 4-slot landing, fixed latency L = ceil(N/2) + 1 + E + pads edges from the driver
// pin to the sink pin), and the four quarters sit at different distances.  XRDQ / XRUQ give the compiled per-quarter
// latency (byte q = SW, SE, NW, NE; tools/hbm_die_v16/d4g_hc_xr.py derives them from the landed contract); XRD / XRU stay
// the compiler constants and must equal the per-quarter maximum.  Quarter q is padded INSIDE the root by XRD - XRDQ[q]
// stages before its descriptor / ingest out flops and by XRU - XRUQ[q] stages after its subtree-sum / gathered-mix pin
// flops (ot_hdc_delay, valid bits reset), so every quarter sees the same compiled timeline (no stagger, no runtime
// alignment).  XRDQ = XRUQ = 32'hffffffff (default) = every quarter at XRD / XRU = the previous form, byte-identical cycles.
// HBM-HC7-ROOT 10-20: reset tree whose port net loads only s0 (see the root's synced reset).  Release: s0 edge 1, s1
// edge 2, leaves edge 3 after the port rises (= ot_rst_relay SYNC 2 + TREE 1).
(* keep_hierarchy = 1 *) module ot_hbm_hc_rst_tree #(parameter integer REGIONS = 8) (
    input wire clk, rst_n_in, output wire [REGIONS-1:0] rst_n
);
    (* async_reg = "true", keep = "true" *) reg s0, s1;
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] lf;
    always @(posedge clk or negedge rst_n_in) if (!rst_n_in) s0 <= 1'b0; else s0 <= 1'b1;
    always @(posedge clk or negedge s0) if (!s0) s1 <= 1'b0; else s1 <= s0;
    always @(posedge clk or negedge s0) if (!s0) lf <= {REGIONS{1'b0}}; else lf <= {REGIONS{s1}};
    assign rst_n = lf;
endmodule
module ot_hbm_hc_root_static #(
    parameter integer K    = 20480,
    parameter [31:0]  NF   = 32'h46a00000,       // binary32(K)
    parameter integer XRD  = 0,                  // die relay stages root -> quarter (descriptor + ingest event)
    parameter integer XRU  = 0,                  // die relay stages quarter -> root (subtree sums)
    parameter [31:0]  XRDQ = 32'hffffffff,       // per-quarter landed root -> quarter latency (byte q), <= XRD; all-1 = XRD
    parameter [31:0]  XRUQ = 32'hffffffff,       // per-quarter landed quarter -> root latency (byte q), <= XRU; all-1 = XRU
    parameter integer QDRLY = 1,                 // quarter's centre <-> bank relays (ot_hbm_hc_qeng_static DRLY)
    parameter integer QCHX = 0,                  // HH-9 10-19: quarter bank-chain pin-register edges (qeng CPR 1 -> 11)
    parameter integer TLA  = 7,                  // quarter tree adder stages
    parameter integer SAFE = 0,                  // HBM-HC5 10-20: 1 = SRAM mix store + tail domain TD = 2 edges later (below)
    parameter integer TAILC = 0,                 // HBM-HCROOT6 10-20: 1 = hardened tail child tiles (+2 edges, emit TE = 2 later)
    parameter integer PTFS = 0,                  // HBM-HC7-ROOT 10-20: 1 = fanout-safe pass (targets _fs + reset tree, below)
    // HBM-COLLECT10/HCROOT 10-21 (xr4): tail child parameters passed through (TAILC 1 only).  The child's latency grows by
    // TX = child L - 496 edges (k3: TSDIV 16 TTPIPE 1 TSKP 1 -> L 947, TX 451; k3b: TSDIV 12 TTPIPE 1 TSKP 0 -> L 779, TX 283).
    // TX is NOT a hardware delay line here: the compiler places each emit TX edges later (tools/rtl_hbm_hc_eng_static_gate.py
    // --tail-x) and the per-unit tail launch spacing >= child L follows (next launch on a unit only after its emit).
    // TE stays 2 (child pin flop + fanout stage).  Defaults = the k2 child (TX 0), byte-identical to the previous root.
    parameter integer TSDIV = 7,
    parameter integer TTPIPE = 0,
    parameter integer TSKP = 0,
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
    // per-quarter pads (XRDQ / XRUQ all-1 = no pad)
    function automatic integer padq(input [31:0] v, input integer mx, input integer q);
        padq = (v == 32'hffffffff) ? 0 : mx - ((v >> (8 * q)) & 255);
    endfunction
    initial for (integer q = 0; q < 4; q = q + 1)
        if (padq(XRDQ, XRD, q) < 0 || padq(XRUQ, XRU, q) < 0) $fatal(1, "XRDQ/XRUQ byte above XRD/XRU");

    // ------------------------------------------------------------------ synced reset
    // L2H-HC 10-19 (SAFE item 3, reset cohorts): eight kept relay regions instead of one rn[0] for the whole root;
    // every copy releases on the same edge (SYNC 2 + TREE 1), so the schedule is unchanged.
    wire [7:0] rn;
    // HBM-HC7-ROOT 10-20 (PTFS 1, SAFE item 3): the port clears ONLY the first synchronizer stage; the second stage and the
    // region leaves are cleared by that stage (assert stays asynchronous: port -> s0 -> clear), so replicated leaves
    // (bound_fanout_clone: same D, same clear) load s0 / s1, never the port.  Release edge = ot_rst_relay (2 + 1 = 3).
    if (PTFS == 0) begin : g_rr
        ot_rst_relay #(.REGIONS(8)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    end else begin : g_rt
        ot_hbm_hc_rst_tree #(.REGIONS(8)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    end
    wire rst_pin = rn[0], rst_tgt = rn[1], rst_seq = rn[2], rst_dn = rn[3];
    wire rst_core = rn[4], rst_mix = rn[5], rst_tbl = rn[6], rst_tail = rn[7];

    // ------------------------------------------------------------------ pin registers
    reg [3:0] gv_p; reg [19:0] gr_p; reg [11:0] gp_p; reg [127:0] gd_p;
    reg [3:0] psv_p, psf_p, qf_p; reg [127:0] ps_p;
    always @(posedge clk or negedge rst_pin)
        if (!rst_pin) begin gv_p <= 0; psv_p <= 0; psf_p <= 0; qf_p <= 0; end
        else begin gv_p <= gathered_mix_v; psv_p <= qps_v; psf_p <= qps_f; qf_p <= q_fault; end
    always @(posedge clk) begin
        gr_p <= gathered_mix_row; gp_p <= gathered_mix_pos; gd_p <= gathered_mix_data; ps_p <= qps;
    end
    // landed quarter -> root: quarter q delayed by XRU - XRUQ[q] after its pin flops (every quarter at XRU)
    wire [3:0] gv_q; wire [19:0] gr_q; wire [11:0] gp_q; wire [127:0] gd_q;
    wire [3:0] psv_q, psf_q, qf_q; wire [127:0] ps_q;
    genvar gxu;
    for (gxu = 0; gxu < 4; gxu = gxu + 1) begin : g_xru
        localparam integer PU = padq(XRUQ, XRU, gxu);
        ot_hdc_delay #(.W(4), .D(PU), .RESET(1)) u_v (.clk(clk), .rst_n(rst_pin),
            .d({gv_p[gxu], psv_p[gxu], psf_p[gxu], qf_p[gxu]}),
            .q({gv_q[gxu], psv_q[gxu], psf_q[gxu], qf_q[gxu]}));
        ot_hdc_delay #(.W(72), .D(PU), .RESET(0)) u_d (.clk(clk), .rst_n(rst_pin),
            .d({gr_p[gxu*5 +: 5], gp_p[gxu*3 +: 3], gd_p[gxu*32 +: 32], ps_p[gxu*32 +: 32]}),
            .q({gr_q[gxu*5 +: 5], gp_q[gxu*3 +: 3], gd_q[gxu*32 +: 32], ps_q[gxu*32 +: 32]}));
    end
    // ------------------------------------------------------------------ folded F20 targets (pin flops inside)
    wire cfg_we, start_v, tbl_we_q, ptgt_fault, ttgt_fault, seq_active;
    wire [9:0] p_addr, start_base, tbl_addr_q; wire [255:0] p_data, tbl_data_q;
    wire [10:0] start_limit; wire [15:0] start_loops;
    // HBM-HC7-ROOT 10-20: PTFS 1 = the same target rebuilt fanout-safe (banked bitmap, kept copies; same ports, same
    // edges; program_cfg_data loads every edge -- its consumers, the programme / table SRAM write stages, read it only
    // with the write enable).  Equivalence: rtl/test/run_static_program_target_fs_eq.sh.
    if (PTFS == 0) begin : g_ptr
        ot_static_program_target #(.PCW(10), .TGT_PIN(1)) u_ptgt (.clk(clk), .rst_n(rst_tgt), .tgt(tgt), .cfg_v(cfg_v),
            .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
            .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
            .program_cfg_we(cfg_we), .program_cfg_addr(p_addr), .program_cfg_data(p_data), .program_start_v(start_v),
            .program_start_base(start_base), .program_start_limit(start_limit), .program_start_loops(start_loops),
            .configured(configured), .fault(ptgt_fault));
    end else begin : g_ptf
        ot_static_program_target_fs #(.PCW(10), .TGT_PIN(1)) u_ptgt (.clk(clk), .rst_n(rst_tgt), .tgt(tgt), .cfg_v(cfg_v),
            .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
            .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
            .program_cfg_we(cfg_we), .program_cfg_addr(p_addr), .program_cfg_data(p_data), .program_start_v(start_v),
            .program_start_base(start_base), .program_start_limit(start_limit), .program_start_loops(start_loops),
            .configured(configured), .fault(ptgt_fault));
    end
    // table target: only its row-write port has a consumer (a table is data; a launch on id tgt + 1 is never issued)
    if (PTFS == 0) begin : g_ttr
        ot_static_program_target #(.PCW(10), .TGT_PIN(1)) u_ttgt (.clk(clk), .rst_n(rst_tgt), .tgt(tgt + 8'd1), .cfg_v(cfg_v),
            .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
            .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
            .program_cfg_we(tbl_we_q), .program_cfg_addr(tbl_addr_q), .program_cfg_data(tbl_data_q), .program_start_v(),
            .program_start_base(), .program_start_limit(), .program_start_loops(), .configured(), .fault(ttgt_fault));
    end else begin : g_ttf
        ot_static_program_target_fs #(.PCW(10), .TGT_PIN(1)) u_ttgt (.clk(clk), .rst_n(rst_tgt), .tgt(tgt + 8'd1), .cfg_v(cfg_v),
            .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
            .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(seq_active),
            .program_cfg_we(tbl_we_q), .program_cfg_addr(tbl_addr_q), .program_cfg_data(tbl_data_q), .program_start_v(),
            .program_start_base(), .program_start_limit(), .program_start_loops(), .configured(), .fault(ttgt_fault));
    end

    // ------------------------------------------------------------------ programme
    localparam integer EW = 124;
    wire [EW-1:0] ev; wire ev_v; wire [19:0] ev_t; wire seq_done, seq_fault;
    ot_hbm_hc_eng_seq_static #(.W(EW)) u_seq (.clk(clk), .rst_n(rst_seq), .cfg_we(cfg_we), .cfg_addr(p_addr),
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
    wire sd_v, sd_ss; wire [NVW-1:0] sd_nv; wire [AW-1:0] sd_wa, sd_xa;   // HCP core descriptor tap (below)
    // landed root -> quarter: quarter q's ingest event and descriptor are delayed by XRD - XRDQ[q] BEFORE its out flops
    // (outputs stay flops; every quarter pin flop sees the event XRD + 2 edges after it fires)
    wire [3:0] dg_v, dd_v; wire [3:0] dg_kind, dd_ss; wire [7:0] dg_slot; wire [19:0] dg_lo, dg_w; wire [47:0] dg_cnt;
    wire [39:0] dg_word, dd_wa, dd_xa; wire [4*NVW-1:0] dd_nv;
    genvar gxd;
    for (gxd = 0; gxd < 4; gxd = gxd + 1) begin : g_xrd
        localparam integer PD = padq(XRDQ, XRD, gxd);
        ot_hdc_delay #(.W(2), .D(PD), .RESET(1)) u_v (.clk(clk), .rst_n(rst_dn),
            .d({e_ing && e_ingq == 2'(gxd), sd_v}), .q({dg_v[gxd], dd_v[gxd]}));
        ot_hdc_delay #(.W(56 + NVW), .D(PD), .RESET(0)) u_d (.clk(clk), .rst_n(rst_dn),
            .d({e_kind, e_slot, e_lo, e_w[4:0], e_cnt, e_word, sd_ss, sd_wa, sd_xa, sd_nv}),
            .q({dg_kind[gxd], dg_slot[gxd*2 +: 2], dg_lo[gxd*5 +: 5], dg_w[gxd*5 +: 5], dg_cnt[gxd*12 +: 12],
                dg_word[gxd*10 +: 10], dd_ss[gxd], dd_wa[gxd*10 +: 10], dd_xa[gxd*10 +: 10], dd_nv[gxd*NVW +: NVW]}));
    end
    always @(posedge clk or negedge rst_dn)
        if (!rst_dn) qi_v <= 4'd0; else qi_v <= dg_v;
    // decoded constant-index destinations (no runtime part-selects: yosys SHARE stall class)
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) if (dg_v[q]) begin
        qi_kind[q] <= dg_kind[q]; qi_slot[q*2 +: 2] <= dg_slot[q*2 +: 2]; qi_lo[q*5 +: 5] <= dg_lo[q*5 +: 5];
        qi_w[q*5 +: 5] <= dg_w[q*5 +: 5]; qi_cnt[q*12 +: 12] <= dg_cnt[q*12 +: 12]; qi_word[q*10 +: 10] <= dg_word[q*10 +: 10];
    end
    reg ev_fault;
    always @(posedge clk or negedge rst_core)
        if (!rst_core) ev_fault <= 1'b0; else if (e_ing && e_w[6:5] != 2'd0) ev_fault <= 1'b1;   // quarter wave index < 32

    // ------------------------------------------------------------------ HCP core (TPRE = 6: partial-sum tree root)
    wire o_valid, o_last, core_fault, core_idle; wire [2:0] o_pos; wire [4:0] o_idx; wire [31:0] o_data;
    ot_hdc_v41x_hcp_sys1_static #(.W(W), .TL(4), .PMAX(8), .OMAX(32), .AW(AW), .CW(16), .ML(ML), .DF(32),
        .STATIC_CALENDAR(1), .SYS(1), .SYS_LAT(SYS_LAT), .TPRE(6)) u_core (
        .clk(clk), .reduction_clk(clk), .scalar_clk(clk), .rst_n(rst_core), .calendar_pop(e_pop),
        .cmd_valid(e_launch), .cmd_ready(), .cmd_npos(e_npos), .cmd_nout(6'd24), .cmd_nchunk(16'(K / 8)),
        .cmd_scale(1'b1), .cmd_nf(NF), .cmd_eps(e_eps), .cmd_wbase(AW'({e_wslot, 8'd0})), .cmd_xbase({AW{1'b0}}),
        .w_re(), .x_re(), .w_addr(), .x_addr(), .w_data({(8*W*32){1'b0}}), .x_data({(8*W*16){1'b0}}),
        .o_valid(o_valid), .o_ready(1'b1), .o_pos(o_pos), .o_idx(o_idx), .o_data(o_data), .o_last(o_last),
        .fault(core_fault), .idle(core_idle),
        .sd_v(sd_v), .sd_ss(sd_ss), .sd_nv(sd_nv), .sd_wa(sd_wa), .sd_xa(sd_xa), .sys_sum(ps_q), .sys_fault(|psf_q));
    // descriptor -> the 4 quarters (out flops); quarter q's lanes are 64q .. 64q + 63 of the run
    always @(posedge clk or negedge rst_dn) if (!rst_dn) qd_v <= 4'd0; else qd_v <= dd_v;
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) begin
        qd_ss[q] <= dd_ss[q]; qd_wa[q*10 +: 10] <= dd_wa[q*10 +: 10]; qd_xa[q*10 +: 10] <= dd_xa[q*10 +: 10];
        qd_nv[q*7 +: 7] <= (dd_nv[q*NVW +: NVW] <= NVW'(64 * q)) ? 7'd0 : (dd_nv[q*NVW +: NVW] >= NVW'(64 * q + 64)) ? 7'd64
                           : 7'(dd_nv[q*NVW +: NVW] - NVW'(64 * q));
    end
    // the subtree sums of the task issued SYS_LAT edges ago must be in the pin flops now (all 4 quarters)
    reg [SYS_LAT-1:0] xv; reg ps_fault;
    always @(posedge clk or negedge rst_mix)
        if (!rst_mix) begin xv <= 0; ps_fault <= 1'b0; end
        else begin
            xv <= {xv[SYS_LAT-2:0], sd_v};
            if (psv_q != {4{xv[SYS_LAT-1]}}) ps_fault <= 1'b1;
        end

    // ------------------------------------------------------------------ tail-domain events
    // HBM-HC5 10-20 (H.STA.BLK.1.1, SAFE 1): the 6,144-b mix store is SRAM.  The tail reads the 24 mixes of its position
    // from three ot_sram_1r1w_128x256 macros (rows 8m .. 8m + 7 in macro m, address = position) instead of an 8-way
    // 768-b select over 6,144 flops, so every event on the tail side (table fetch e_tf, tail launch e_tl, emit) runs
    // TD = 2 edges later than its programme edge: read issued one edge after e_tl (it sees every mix write of an edge
    // <= e_tl - 1, exactly what the flop store gave the tail at e_tl), data on rd_out one edge later, inner tail launch
    // on the next edge.  The programme (compiler) is unchanged; the result pins move +2 edges (HC_MIX + 2, ledger).
    // The completeness check (have map) and every mix-write fault keep their programme edges.  SAFE 0 = TD 0 =
    // byte-identical to the previous form.
    localparam integer TD = SAFE ? 2 : 0;
    wire t_tl, t_tf, t_emit, t_tunit, t_eunit; wire [2:0] t_tpos; wire [6:0] t_tset; wire [3:0] t_qmask;
    // TAILC 1: the tail child tiles return their result 2 edges later (child pin flop + fanout stage): every emit-side
    // event (emit, its quarter mask and unit) moves TE = 2 more edges; launches / table fetches keep TD.
    localparam integer TE = TAILC ? 2 : 0;
    wire e_emit_te, e_eunit_te; wire [3:0] e_qmask_te;
    ot_hdc_delay #(.W(1), .D(TE), .RESET(1)) u_tev (.clk(clk), .rst_n(rst_tail), .d(e_emit), .q(e_emit_te));
    ot_hdc_delay #(.W(5), .D(TE), .RESET(0)) u_ted (.clk(clk), .rst_n(rst_tail), .d({e_qmask, e_eunit}),
        .q({e_qmask_te, e_eunit_te}));
    ot_hdc_delay #(.W(3), .D(TD), .RESET(1)) u_tdv (.clk(clk), .rst_n(rst_tail), .d({e_tl, e_tf, e_emit_te}),
        .q({t_tl, t_tf, t_emit}));
    ot_hdc_delay #(.W(16), .D(TD), .RESET(0)) u_tdd (.clk(clk), .rst_n(rst_tail),
        .d({e_tunit, e_tpos, e_tset, e_qmask_te, e_eunit_te}), .q({t_tunit, t_tpos, t_tset, t_qmask, t_eunit}));

    // ------------------------------------------------------------------ mix store
    reg [191:0] have; reg mix_fault; reg [3:0] gm_open;
    always @(posedge clk or negedge rst_mix) begin
        if (!rst_mix) begin have <= 0; mix_fault <= 0; gm_open <= 0; end
        else begin
            if (e_clear) have <= 0;
            if (e_gm) gm_open[e_gmq] <= e_gmo;
            if (o_valid && o_idx >= 5'd24) mix_fault <= 1'b1;
            for (integer q = 0; q < 4; q = q + 1)
                if (gv_q[q] && (!gm_open[q] || gr_q[q*5 +: 5] >= 5'd24)) mix_fault <= 1'b1;
            // decoded slot writes (slot = pos * 24 + row); same priority as before: core word, then quadrants 0..3
            for (integer p = 0; p < 8; p = p + 1) for (integer r = 0; r < 24; r = r + 1) begin
                if (o_valid && o_pos == 3'(p) && o_idx == 5'(r)) have[p*24 + r] <= 1'b1;
                for (integer q = 0; q < 4; q = q + 1)
                    if (gv_q[q] && gm_open[q] && gp_q[q*3 +: 3] == 3'(p) && gr_q[q*5 +: 5] == 5'(r))
                        have[p*24 + r] <= 1'b1;
            end
        end
    end
    // have map of the launching position (programme edge e_tl): decoded AND-OR select
    reg [23:0] have_at;
    always @* begin
        have_at = 24'd0;
        for (integer p = 0; p < 8; p = p + 1) if (e_tpos == 3'(p)) have_at = have_at | have[p*24 +: 24];
    end
    wire [767:0] mix_at;              // the 24 mixes of the launching position, at the inner tail launch (t_tl)
    wire mix_wfault;
    genvar gm, gj, gk;
    if (SAFE == 0) begin : g_mixf
        reg [8*24*32-1:0] mixes; reg [767:0] ma;
        always @(posedge clk) begin
            for (integer p = 0; p < 8; p = p + 1) for (integer r = 0; r < 24; r = r + 1) begin
                if (o_valid && o_pos == 3'(p) && o_idx == 5'(r)) mixes[(p*24 + r)*32 +: 32] <= o_data;
                for (integer q = 0; q < 4; q = q + 1)
                    if (gv_q[q] && gm_open[q] && gp_q[q*3 +: 3] == 3'(p) && gr_q[q*5 +: 5] == 5'(r))
                        mixes[(p*24 + r)*32 +: 32] <= gd_q[q*32 +: 32];
            end
        end
        // position e_tpos of the mix store: decoded AND-OR select (no runtime part-select)
        always @* begin
            ma = 768'd0;
            for (integer p = 0; p < 8; p = p + 1) if (e_tpos == 3'(p)) ma = ma | mixes[p*768 +: 768];
        end
        assign mix_at = ma; assign mix_wfault = 1'b0;
    end else begin : g_mixs
        // write stage (one register edge): writer k = 0 core word, 1 .. 4 quadrant k - 1 gathered word (the flop
        // store's priority: a later writer of the same slot wins).  Per macro m: one-hot lane selects, lane masks, the
        // address (position) and the five source words land in flops; the lane mux behind them feeds wd_in directly
        // (select flop -> 32 mux bits, mask flop -> 32 mask pins, source bit -> 24 lanes).  Two writers into one macro
        // on one edge must name the same position (they merge through the lane mask); different positions = fault
        // (static contract: the compiler never schedules that; the programmes here write one word an edge).
        wire [4:0] sv; wire [14:0] sp; wire [24:0] sr; wire [159:0] sd;
        assign sv[0] = o_valid && o_idx < 5'd24; assign sp[2:0] = o_pos; assign sr[4:0] = o_idx;
        assign sd[31:0] = o_data;
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_src
            assign sv[gk+1] = gv_q[gk] && gm_open[gk] && gr_q[gk*5 +: 5] < 5'd24;
            assign sp[(gk+1)*3 +: 3] = gp_q[gk*3 +: 3]; assign sr[(gk+1)*5 +: 5] = gr_q[gk*5 +: 5];
            assign sd[(gk+1)*32 +: 32] = gd_q[gk*32 +: 32];
        end
        reg [159:0] wd_s; reg [2:0] w_ce; reg [8:0] w_pos; reg [119:0] w_sel; reg [23:0] w_lane; reg wf;
        always @(posedge clk) wd_s <= sd;
        always @(posedge clk or negedge rst_mix)
            if (!rst_mix) begin w_ce <= 3'd0; wf <= 1'b0; end
            else for (integer m = 0; m < 3; m = m + 1) begin
                w_ce[m] <= 1'b0;
                for (integer k = 0; k < 5; k = k + 1) if (sv[k] && sr[k*5+3 +: 2] == 2'(m)) begin
                    w_ce[m] <= 1'b1;
                    for (integer k2 = 0; k2 < k; k2 = k2 + 1)
                        if (sv[k2] && sr[k2*5+3 +: 2] == 2'(m) && sp[k2*3 +: 3] != sp[k*3 +: 3]) wf <= 1'b1;
                end
            end
        always @(posedge clk) for (integer m = 0; m < 3; m = m + 1) begin
            for (integer k = 0; k < 5; k = k + 1) if (sv[k] && sr[k*5+3 +: 2] == 2'(m)) w_pos[m*3 +: 3] <= sp[k*3 +: 3];
            for (integer j = 0; j < 8; j = j + 1) begin
                w_lane[m*8 + j] <= 1'b0;
                for (integer k = 0; k < 5; k = k + 1) w_sel[(m*8 + j)*5 + k] <= 1'b0;
                for (integer k = 0; k < 5; k = k + 1) if (sv[k] && sr[k*5 +: 5] == 5'(m*8 + j)) begin
                    w_lane[m*8 + j] <= 1'b1;
                    for (integer k2 = 0; k2 < 5; k2 = k2 + 1) w_sel[(m*8 + j)*5 + k2] <= (k2 == k);
                end
            end
        end
        assign mix_wfault = wf;
        // read: issued the edge after e_tl, position e_tpos; rd_out holds until the next read
        reg rd_req; reg [2:0] rd_pos;
        always @(posedge clk or negedge rst_mix) if (!rst_mix) rd_req <= 1'b0; else rd_req <= e_tl;
        always @(posedge clk) rd_pos <= e_tpos;
        for (gm = 0; gm < 3; gm = gm + 1) begin : g_m
            reg [255:0] wd, wm;
            always @* for (integer j = 0; j < 8; j = j + 1) begin
                wd[j*32 +: 32] = 32'd0;
                for (integer k = 0; k < 5; k = k + 1)
                    wd[j*32 +: 32] = wd[j*32 +: 32] | ({32{w_sel[(gm*8 + j)*5 + k]}} & wd_s[k*32 +: 32]);
                wm[j*32 +: 32] = (MUT == 21) ? {32{1'b1}} : {32{w_lane[gm*8 + j]}};   // MUT 21: lane mask dropped
            end
            ot_sram_1r1w_128x256_m1_r2c2 u_mix (.clk(clk), .r_ce_in(rd_req), .r_addr_in({4'd0, rd_pos}),
                .rd_out(mix_at[gm*256 +: 256]), .w_ce_in(w_ce[gm]), .w_addr_in({4'd0, w_pos[gm*3 +: 3]}), .wd_in(wd),
                .w_mask_in(wm), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end

    // ------------------------------------------------------------------ bases/scales table (tail domain)
    reg [2:0] tf_cnt; reg [6:0] tf_set; reg [1:0] tf_row_q; reg tf_rd_q; reg [895:0] hold; reg tbl_fault;
    wire [255:0] tbl_rd;
    wire tf_rd = tf_cnt != 3'd0;
    wire [1:0] tf_row = 2'(4 - tf_cnt);
    ot_sram_1r1w_1024x256_m2_r2c2 u_tbl (.clk(clk), .r_ce_in(tf_rd), .r_addr_in({1'b0, tf_set, tf_row}),
        .rd_out(tbl_rd), .w_ce_in(tbl_we_q && !seq_active), .w_addr_in(tbl_addr_q), .wd_in(tbl_data_q),
        .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk or negedge rst_tbl) begin
        if (!rst_tbl) begin tf_cnt <= 0; tf_rd_q <= 0; tbl_fault <= 0; end
        else begin
            tf_rd_q <= tf_rd; tf_row_q <= tf_row;
            if (tf_rd) tf_cnt <= tf_cnt - 1'b1;
            if (t_tf) begin if (tf_rd) tbl_fault <= 1'b1; tf_cnt <= 3'd4; tf_set <= t_tset; end
            if (tbl_we_q && seq_active) tbl_fault <= 1'b1;
        end
    end
    always @(posedge clk) for (integer r = 0; r < 4; r = r + 1)
        if (tf_rd_q && tf_row_q == 2'(r)) hold[r*224 +: 224] <= tbl_rd[223:0];   // row payload (F20 header off)
    // set layout: base i = row i/7 word i%7 = hold word i (i < 24); scale j = row 3 word 3 + j = hold word 24 + j
    wire [767:0] t_bases = hold[767:0]; wire [95:0] t_scales = hold[863:768];

    // ------------------------------------------------------------------ tail units (tail domain)
    wire [1:0] tv, tfl; wire [1535:0] tres; reg [2:0] tpos [0:1]; reg [1:0] tready; reg tail_fault;
    genvar gu;
    for (gu = 0; gu < 2; gu = gu + 1) begin : g_tail
        wire go = t_tl && t_tunit == gu;
        if (TAILC == 0) begin : g_u
            ot_hbm_hc_tail_unit_static #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0)) u_t (.clk(clk), .rst_n(rst_tail),
                .launch(go), .mixes(mix_at), .bases(t_bases), .scales(t_scales),
                .result_v(tv[gu]), .result(tres[gu*768 +: 768]), .fault(tfl[gu]));
        end else begin : g_c
            ot_hbm_hc_tail_child_static #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0), .SDIV(TSDIV), .TPIPE(TTPIPE), .SKP(TSKP)) u_t (.clk(clk), .rst_n(rst_tail),
                .launch(go), .mixes(mix_at), .bases(t_bases), .scales(t_scales),
                .result_v(tv[gu]), .result(tres[gu*768 +: 768]), .fault(tfl[gu]));
        end
    end
    always @(posedge clk or negedge rst_tail) begin
        if (!rst_tail) begin tready <= 0; tail_fault <= 0; end
        else begin
            for (integer u = 0; u < 2; u = u + 1) begin
                if (tv[u]) tready[u] <= 1'b1;
                if (t_tl && t_tunit == u) begin tready[u] <= 1'b0; tpos[u] <= t_tpos; end
            end
            if (e_tl && have_at != 24'hffffff) tail_fault <= 1'b1;
            if (t_emit && !tready[t_eunit]) tail_fault <= 1'b1;
        end
    end

    // ------------------------------------------------------------------ result pins (all flops)
    always @(posedge clk or negedge rst_pin) begin
        if (!rst_pin) result_v <= 4'd0;
        else result_v <= t_emit ? t_qmask : 4'd0;
    end
    if (SAFE == 0) begin : g_resf
        wire [767:0] tres_e = t_eunit ? tres[1535:768] : tres[767:0];
        always @(posedge clk) if (t_emit) for (integer q = 0; q < 4; q = q + 1) if (t_qmask[q]) begin
            result_position[q*3 +: 3] <= tpos[t_eunit]; result[q*768 +: 768] <= tres_e;
        end
    end else begin : g_ress
        // SAFE: the emit enables / unit select reach 3,072 result flops through KEPT copies sized from the mapped census
        // (an enable flop maps to a mux: 2 endpoints a bit; a 2:1 data select: 3 a bit): en_c[q*48 + c] = emit &&
        // qmask[q] for result bits 16c .. 16c + 15 of quarter q (32 endpoints), us_c[q*96 + c] = emit unit for bits
        // 8c .. 8c + 7 (24 endpoints).  They are the second tail-domain delay stage (loaded from the first, d1), so they
        // rise on the same edge as t_emit (cycles unchanged).
        reg e_emit_d1, e_eunit_d1; reg [3:0] e_qmask_d1;
        always @(posedge clk or negedge rst_tail) if (!rst_tail) e_emit_d1 <= 1'b0; else e_emit_d1 <= e_emit_te;
        always @(posedge clk) begin e_qmask_d1 <= e_qmask_te; e_eunit_d1 <= e_eunit_te; end
        (* keep = "true", dont_touch = "true" *) reg [191:0] en_c;
        (* keep = "true", dont_touch = "true" *) reg [383:0] us_c;
        reg [3:0] en_p; reg us_p;
        always @(posedge clk) begin
            for (integer q = 0; q < 4; q = q + 1) begin
                en_c[q*48 +: 48] <= {48{e_emit_d1 && e_qmask_d1[q]}};
                us_c[q*96 +: 96] <= {96{e_eunit_d1}};
                en_p[q] <= e_emit_d1 && e_qmask_d1[q];
            end
            us_p <= e_eunit_d1;
        end
        always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) begin
            if (en_p[q]) result_position[q*3 +: 3] <= tpos[us_p];
            for (integer c = 0; c < 96; c = c + 1)
                if (en_c[q*48 + c/2])
                    result[q*768 + c*8 +: 8] <= us_c[q*96 + c] ? tres[768 + c*8 +: 8] : tres[c*8 +: 8];
        end
    end

    // ------------------------------------------------------------------ status
    always @(posedge clk or negedge rst_pin) begin
        if (!rst_pin) begin fault <= 0; program_active <= 0; program_done <= 0; end
        else begin
            program_active <= seq_active; program_done <= seq_done;
            if (seq_fault || ev_fault || ps_fault || (|qf_q) || core_fault || mix_fault || mix_wfault || tbl_fault || tail_fault ||
                (|tfl) || ptgt_fault || ttgt_fault) fault <= 1'b1;
        end
    end
endmodule
`default_nettype wire

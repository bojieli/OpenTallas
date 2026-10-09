`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_crom (stream qwen-system, 2026-10-08): the Qwen3-8B ROM die's CONSTANT ROM as hardware.
//
// Replaces the idealised 64-port array (543,233 / 541,953 x 64 b, host-preloaded, folded into the 2.16 mm2 sequencer
// reservation of r21b) with 48 ASAP7 ot_rom_4096x266_m8 mask-ROM macros (TT clk->q 586 ps), read through the stream
// unit's existing 64-lane port (crom_re / crom_addr / crom_q of ot_qfd_sp_su64_sfu_bv) plus the stage index.
//
// Store (tools/qwen_system/crom_image.py; the image the C++ runtime swapped per stage, held for all 37 stages):
//   region (layer-local word a)       content                       store
//   ZERO   [0,QK0) [POST0,QSCALE)     folded in/post norm rows      none: reads return 0
//   QK     [QK0,POST0)                q/k norm tiles of layer L     narrow, row L*LROWS + (a-QK0)/64
//   QSCALE QSCALE                     (0, 1/sqrt(128))              hardwired word
//   ROPE   [ROPE0,OSC0)               cos/sin of 8,192 positions    wide, row (a-ROPE0)/64
//   OSC    [OSC0,DSC0)                o true row scales, layer L    narrow, row L*LROWS + QKR + (a-OSC0)/64
//   DSC    [DSC0,END)                 down true row scales          narrow, row L*LROWS + QKR + 64 + (a-DSC0)/64
//   FNORM  stage HEAD, [0,4096)       final norm                    narrow, row FN_ROW0 + a/64
//   wide   = 16 macro columns x 4 lanes x 64 b, 2 deep (8,192 rows); narrow = 8 columns x 8 lanes x 32 b, 2 deep
//   (5,392 rows; the high word of a narrow constant is 0 in the stage image).
// Banking contract (crom_image.py contract: every constant read of the stage and head programs at every position
// class): lane l reads word rb + 64 r + l of one region, so each lane's word lives in its own macro column slot and
// every lane of a macro column reads one row.  The ROM checks it and FAILS CLOSED (sticky fault, first-cause code):
//   1 out of range (a >= END, or a >= 4096 at the head stage, or stage > HEAD), 2 lane misaligned ((a-rb) mod 64 != l),
//   3 rows disagree inside one macro column.
//
// Pipeline (safe-margin rules: pin flops, registered macro outputs, ~1 decode level per stage), edges after the strobe:
//   e1 IS   input station: re, addr, stage (no logic before the flops)
//   e2 T    per-lane region decode -> {kind, row} registers; fault terms registered
//   e3 M    the macro samples its address (macro column = first active lane's row, a 4:1 / 8:1 priority select)
//   e4 C    capture flops at every macro output (no logic before them)
//   e5 OS   per-lane select (depth, region, QSCALE / ZERO constants) into the output station, held when not read
// q answers 5 edges after the strobe at this master's pin: CRX = 4 in the stream unit's terms (1 + CRX).  The
// banked-VM stream unit runs its lanes at ML = max(IS+OS+CRX, VL = 7) = 7 with IS = OS = 1, so CRX = 4 costs 0 cycles
// when the ROM abuts the SU (no relay on the crom buses); each relay hop each way adds 1 to CRX.
// MUT = 1 (bench mutant): flips bit 0 of lane 0's answer.
// drive-0158 "-cl" options (REVIEW_20261009 addendum 02:35; all default 0 = the reviewed Q1 form, bit-identical):
//   OREG  = 1: e6 output pin station q_p (q_r -> q_p, no logic, anchored at the lane window by out_flop_at_pins.tcl);
//              q answers 6 edges after the strobe (CRX 5).  The select band (q_r, t_*) sits mid-block (crom48cl_pre_gpl.tcl).
//   IREL  = 1: one inbound relay stage on {re, addr, stage} (pin station -> band); +1 more edge (CRX 6 with OREG).
//   RSYNC = 1: reset tree = root 2-flop synchroniser (async assert, sync release) + one 2-flop synchroniser per
//              16-lane macro column; every lane flop resets from its column's synchroniser, faults from the root.
//              Reset release is 4 edges later than rst_n (the bench waits RWAIT = 4).
// struct-close "cl-a''" (REVIEW-0412 S6; default 0 = unchanged):
//   CHK   = 1: the range / alignment CHECK leaves the e2 data path.  crom48cl_a/c failed post-CTS TT -562/-607 on
//              u_is_a.line -> g_dec[53].tal (cells 1,020 ps): the 12-level region chain + the 24-bit subtract + the lane
//              compare in one stage.  The check is now computed BESIDE the decode in two registered stages: e2
//              registered region compares (one level of 24-bit constant compares) + the low 6 address bits, e3 the
//              kind from the flags and the alignment on 6 bits (off mod 64 = a mod 64 - base mod 64).  t_rng / t_al are
//              one edge later (+1 on the fault path only); the data path (tk / tr) is unchanged, 0 cycles.
//              The 64-lane fault reduction is two registered levels: per 16-lane macro column (beside its band
//              segment), then the root (+1 on the fault path; crom48cl f_dis -614 was one flop ORing 64 lanes over
//              777.6 um).  Out-of-range addresses are compiler bugs: the fault stays sticky / fail-closed.
// struct-close cl-a3 (drive-0212 0512; default 0 = unchanged):
//   DSPLIT = 1: the e2 region decode (line -> g_dec.tr -961 ps: ~1.3 ns of compare + 24-bit subtract + row add in one
//              stage) is split over two registered stages: e2a = the region compares (flags), the five constant
//              subtracts (a - base) >> 6 in parallel and the stage's row bases (lbase, + QKR, + QKR + 64); e2b = the kind
//              from the flags and one 13-bit row add + a 5:1 select.  +1 edge on the data path (q answers one edge
//              later: CRX + 1, the same +1 / SU op as cl-b).  The check path keeps its order: chk_rng / chk_al get one
//              more register, so faults stay aligned with the data and first-cause order is unchanged.
//              Also (with CHK): the macro-column row-disagree terms are REGISTERED per macro (w_dis / n_dis -> *_q)
//              before the 16-lane column OR (g_dec.tv -> g_fcol -790 ps: the priority select + 13-bit compares + the
//              4/2-macro OR + the column OR in one stage); that register replaces the cdq realign stage, 0 cycles.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_crom #(
    parameter integer SW = 64,
    parameter integer AW = 24,
    parameter integer LW = 6,
    parameter integer QK0 = 4096,
    parameter integer POST0 = 5376,
    parameter integer QSCALE = 9472,
    parameter integer ROPE0 = 9473,
    parameter integer OSC0 = 533761,
    parameter integer DSC0 = 537857,
    parameter integer END = 541953,
    parameter integer HEAD = 36,
    parameter integer HEAD_N = 4096,
    parameter integer QKR = 20,                 // QK rows a layer
    parameter integer LROWS = 148,              // narrow rows a layer
    parameter integer FN_ROW0 = 5328,
    parameter [63:0] QSCALE_WORD = 64'h3db504f3_00000000,
    parameter integer MUT = 0,
    parameter integer OREG = 0,
    parameter integer IREL = 0,
    parameter integer RSYNC = 0,
    parameter integer CHK = 0,
    parameter integer DSPLIT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [SW-1:0]     crom_re,
    input  wire [SW*AW-1:0]  crom_addr,
    input  wire [LW-1:0]     crom_stage,        // 0..35 decoder layer stages, HEAD the lm_head stage
    output wire [SW*64-1:0]  crom_q,
    output reg               fault,
    output reg  [1:0]        fault_code
);
    localparam integer RW = 13;                 // store row bits (8,192 wide rows / 5,392 narrow rows)
    localparam integer WL = 4, NL = 8;          // lanes a wide / narrow macro column
    localparam integer WC = SW / WL, NC = SW / NL;
    localparam [AW-1:0] A_QK0 = QK0, A_POST0 = POST0, A_QSC = QSCALE, A_ROPE0 = ROPE0, A_OSC0 = OSC0, A_DSC0 = DSC0,
                        A_END = END, A_HN = HEAD_N;
    localparam [RW-1:0] R_QKR = QKR, R_QKR64 = QKR + 64, R_FN0 = FN_ROW0;
    localparam [LW-1:0] S_HEAD = HEAD;
    localparam [2:0] K_ZERO = 3'd0, K_QSC = 3'd1, K_WIDE = 3'd2, K_NARROW = 3'd3, K_BAD = 3'd4;

    // ---- reset tree (RSYNC) ----
    localparam integer NCOL = 4, LPC = SW / NCOL;   // 16 lanes per physical macro column
    wire            rst_root;
    wire [NCOL-1:0] rst_col;
    wire [SW-1:0]   rst_l;
    genvar gc, gl;
    generate
        if (RSYNC != 0) begin : g_rsync
            reg [1:0] rs_root;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) rs_root <= 2'b00; else rs_root <= {rs_root[0], 1'b1};
            assign rst_root = rs_root[1];
            for (gc = 0; gc < NCOL; gc = gc + 1) begin : g_col
                reg [1:0] rs_c;
                always @(posedge clk or negedge rst_root)
                    if (!rst_root) rs_c <= 2'b00; else rs_c <= {rs_c[0], 1'b1};
                assign rst_col[gc] = rs_c[1];
            end
        end else begin : g_rdirect
            assign rst_root = rst_n;
            assign rst_col = {NCOL{rst_n}};
        end
        for (gl = 0; gl < SW; gl = gl + 1) begin : g_rl
            assign rst_l[gl] = rst_col[gl / LPC];
        end
    endgenerate

    // ---- e1: input station (+ IREL inbound relay stages toward the select band) ----
    wire [SW-1:0]    re0, re1;
    wire [SW*AW-1:0] a1;
    wire [LW-1:0]    st1;
    wire [SW*AW+LW-1:0] as0;
    generate
        for (gc = 0; gc < NCOL; gc = gc + 1) begin : g_is
            ot_hdc_delay #(.W(LPC), .D(1), .RESET(1)) u_is_re (.clk(clk), .rst_n(rst_col[gc]),
                .d(crom_re[gc*LPC +: LPC]), .q(re0[gc*LPC +: LPC]));
            ot_hdc_delay #(.W(LPC), .D(IREL), .RESET(1)) u_ir_re (.clk(clk), .rst_n(rst_col[gc]),
                .d(re0[gc*LPC +: LPC]), .q(re1[gc*LPC +: LPC]));
        end
    endgenerate
    ot_hdc_delay #(.W(SW*AW + LW), .D(1)) u_is_a (.clk(clk), .rst_n(rst_n), .d({crom_addr, crom_stage}), .q(as0));
    ot_hdc_delay #(.W(SW*AW + LW), .D(IREL)) u_ir_a (.clk(clk), .rst_n(rst_n), .d(as0), .q({a1, st1}));

    // ---- e2: per-lane region decode ----
    // narrow row of a layer-local region: stage * LROWS + off (LROWS = 148 = 128 + 16 + 4: three shifted adds)
    wire [RW-1:0] lbase = ({{(RW-LW){1'b0}}, st1} << 7) + ({{(RW-LW){1'b0}}, st1} << 4) + ({{(RW-LW){1'b0}}, st1} << 2);
    wire [SW-1:0]    t_v;
    wire [SW*3-1:0]  t_kind;
    wire [SW*RW-1:0] t_row;
    wire [SW-1:0]    t_rng, t_al;
    integer l;
    generate
        for (gl = 0; gl < SW; gl = gl + 1) begin : g_dec
            reg [AW-1:0] a, off;
            reg [2:0] k;
            reg [RW-1:0] r;
            reg al;
            always @(*) begin
                a = a1[gl*AW +: AW];
                off = 0; r = 0; al = 1'b1;
                if (st1 == S_HEAD) begin
                    if (a < A_HN) begin k = K_NARROW; off = a; r = R_FN0 + off[6 +: RW]; end
                    else k = K_BAD;
                end else if (st1 > S_HEAD) k = K_BAD;
                else if (a < A_QK0 || (a >= A_POST0 && a < A_QSC)) k = K_ZERO;
                else if (a < A_POST0) begin k = K_NARROW; off = a - A_QK0; r = lbase + off[6 +: RW]; end
                else if (a == A_QSC) k = K_QSC;
                else if (a < A_OSC0) begin k = K_WIDE; off = a - A_ROPE0; r = off[6 +: RW]; end
                else if (a < A_DSC0) begin k = K_NARROW; off = a - A_OSC0; r = lbase + R_QKR + off[6 +: RW]; end
                else if (a < A_END) begin k = K_NARROW; off = a - A_DSC0; r = lbase + R_QKR64 + off[6 +: RW]; end
                else k = K_BAD;
                if ((k == K_WIDE || k == K_NARROW) && off[5:0] != gl[5:0]) al = 1'b0;
            end
            reg tv, trng, tal;
            reg [2:0] tk;
            reg [RW-1:0] tr;
            always @(posedge clk or negedge rst_l[gl]) begin
                if (!rst_l[gl]) begin
                    tv <= 1'b0; trng <= 1'b0; tal <= 1'b0;
                end else begin
                    tv <= re1[gl];
                    trng <= (CHK == 0) && re1[gl] && k == K_BAD;
                    tal <= (CHK == 0) && re1[gl] && !al;
                end
            end
            // CHK: the check beside the decode (e2 compares registered, e3 kind + 6-bit alignment registered)
            wire chk_rng, chk_al;
            if (CHK != 0) begin : g_chk
                wire [AW-1:0] ca = a1[gl*AW +: AW];
                reg cv, c_head, c_hbad;
                reg [7:0] cf;
                reg [5:0] clo;
                always @(posedge clk or negedge rst_l[gl]) if (!rst_l[gl]) cv <= 1'b0; else cv <= re1[gl];
                always @(posedge clk) begin
                    c_head <= st1 == S_HEAD; c_hbad <= st1 > S_HEAD; clo <= ca[5:0];
                    cf <= {ca < A_HN, ca < A_QK0, ca < A_POST0, ca < A_QSC, ca == A_QSC, ca < A_OSC0, ca < A_DSC0, ca < A_END};
                end
                reg [2:0] ck; reg [5:0] cb;
                always @(*) begin
                    cb = 6'd0;
                    if (c_head) ck = cf[7] ? K_NARROW : K_BAD;
                    else if (c_hbad) ck = K_BAD;
                    else if (cf[6] || (!cf[5] && cf[4])) ck = K_ZERO;
                    else if (cf[5]) begin ck = K_NARROW; cb = A_QK0[5:0]; end
                    else if (cf[3]) ck = K_QSC;
                    else if (cf[2]) begin ck = K_WIDE; cb = A_ROPE0[5:0]; end
                    else if (cf[1]) begin ck = K_NARROW; cb = A_OSC0[5:0]; end
                    else if (cf[0]) begin ck = K_NARROW; cb = A_DSC0[5:0]; end
                    else ck = K_BAD;
                end
                wire [5:0] clane = clo - cb;
                reg qr, qa;
                always @(posedge clk or negedge rst_l[gl]) begin
                    if (!rst_l[gl]) begin qr <= 1'b0; qa <= 1'b0; end
                    else begin
`ifndef OT_CROM_MUT_NORNG
                        qr <= cv && ck == K_BAD;
`else
                        qr <= 1'b0;          // mutant: the off-path range check is dropped (out-of-range must fault)
`endif
                        qa <= cv && (ck == K_WIDE || ck == K_NARROW) && clane != gl[5:0];
                    end
                end
                assign chk_rng = qr; assign chk_al = qa;
            end else begin : g_nochk
                assign chk_rng = trng; assign chk_al = tal;
            end
            if (DSPLIT == 0) begin : g_d1
                always @(posedge clk) begin
                    tk <= k;
                    tr <= r;
                end
                assign t_v[gl] = tv; assign t_rng[gl] = chk_rng; assign t_al[gl] = chk_al;
            end else begin : g_d2
                // e2a: flags, the five region offsets (row part), the stage row bases
                wire [AW-1:0] da = a1[gl*AW +: AW];
                wire [AW-1:0] o_qk = da - A_QK0, o_ro = da - A_ROPE0, o_os = da - A_OSC0, o_ds = da - A_DSC0;
                reg dv, d_head, d_hbad;
                reg [7:0] df;
                reg [RW-1:0] r_hn, r_qk, r_ro, r_os, r_ds, b0, b1, b2;
                always @(posedge clk or negedge rst_l[gl]) if (!rst_l[gl]) dv <= 1'b0; else dv <= re1[gl];
                always @(posedge clk) begin
                    d_head <= st1 == S_HEAD; d_hbad <= st1 > S_HEAD;
                    df <= {da < A_HN, da < A_QK0, da < A_POST0, da < A_QSC, da == A_QSC, da < A_OSC0, da < A_DSC0, da < A_END};
                    r_hn <= da[6 +: RW]; r_qk <= o_qk[6 +: RW]; r_ro <= o_ro[6 +: RW]; r_os <= o_os[6 +: RW]; r_ds <= o_ds[6 +: RW];
`ifndef OT_CROM_MUT_DROW
                    b0 <= lbase; b1 <= lbase + R_QKR; b2 <= lbase + R_QKR64;
`else
                    b0 <= lbase; b1 <= lbase + R_QKR64; b2 <= lbase + R_QKR;   // mutant: the e2a row bases swapped
`endif
                end
                // e2b: kind (same priority as the one-stage decode) + one row add
                reg [2:0] k2; reg [RW-1:0] r2;
                always @(*) begin
                    r2 = 0;
                    if (d_head) begin if (df[7]) begin k2 = K_NARROW; r2 = R_FN0 + r_hn; end else k2 = K_BAD; end
                    else if (d_hbad) k2 = K_BAD;
                    else if (df[6] || (!df[5] && df[4])) k2 = K_ZERO;
                    else if (df[5]) begin k2 = K_NARROW; r2 = b0 + r_qk; end
                    else if (df[3]) k2 = K_QSC;
                    else if (df[2]) begin k2 = K_WIDE; r2 = r_ro; end
                    else if (df[1]) begin k2 = K_NARROW; r2 = b1 + r_os; end
                    else if (df[0]) begin k2 = K_NARROW; r2 = b2 + r_ds; end
                    else k2 = K_BAD;
                end
                reg tv2;
                always @(posedge clk or negedge rst_l[gl]) if (!rst_l[gl]) tv2 <= 1'b0; else tv2 <= dv;
                always @(posedge clk) begin tk <= k2; tr <= r2; end
                // the check stays one edge behind the data (as with DSPLIT = 0): one more register on it
                reg cr2, ca2;
                always @(posedge clk or negedge rst_l[gl]) if (!rst_l[gl]) begin cr2 <= 1'b0; ca2 <= 1'b0; end
                    else begin cr2 <= chk_rng; ca2 <= chk_al; end
                assign t_v[gl] = tv2; assign t_rng[gl] = cr2; assign t_al[gl] = ca2;
            end
            assign t_kind[gl*3 +: 3] = tk; assign t_row[gl*RW +: RW] = tr;
        end
    endgenerate

    // ---- e3: macro columns (address = first active lane's row) ----
    wire [WC-1:0]    w_ce;
    wire [WC*RW-1:0] w_row;
    wire [NC-1:0]    n_ce;
    wire [NC*RW-1:0] n_row;
    wire [WC-1:0]    w_dis;
    wire [NC-1:0]    n_dis;
    genvar g, d;
    generate
        for (g = 0; g < WC; g = g + 1) begin : g_wsel
            reg ce; reg [RW-1:0] row; reg dis;
            integer j;
            always @(*) begin
                ce = 1'b0; row = 0; dis = 1'b0;
                for (j = WL - 1; j >= 0; j = j - 1)
                    if (t_v[g*WL + j] && t_kind[(g*WL + j)*3 +: 3] == K_WIDE) begin ce = 1'b1; row = t_row[(g*WL + j)*RW +: RW]; end
                for (j = 0; j < WL; j = j + 1)
                    if (t_v[g*WL + j] && t_kind[(g*WL + j)*3 +: 3] == K_WIDE && t_row[(g*WL + j)*RW +: RW] != row) dis = 1'b1;
            end
            assign w_ce[g] = ce; assign w_row[g*RW +: RW] = row; assign w_dis[g] = dis;
        end
        for (g = 0; g < NC; g = g + 1) begin : g_nsel
            reg ce; reg [RW-1:0] row; reg dis;
            integer j;
            always @(*) begin
                ce = 1'b0; row = 0; dis = 1'b0;
                for (j = NL - 1; j >= 0; j = j - 1)
                    if (t_v[g*NL + j] && t_kind[(g*NL + j)*3 +: 3] == K_NARROW) begin ce = 1'b1; row = t_row[(g*NL + j)*RW +: RW]; end
                for (j = 0; j < NL; j = j + 1)
                    if (t_v[g*NL + j] && t_kind[(g*NL + j)*3 +: 3] == K_NARROW && t_row[(g*NL + j)*RW +: RW] != row) dis = 1'b1;
            end
            assign n_ce[g] = ce; assign n_row[g*RW +: RW] = row; assign n_dis[g] = dis;
        end
    endgenerate

    // the macros (their read register is the e3 stage) and the e4 capture flops
    wire [WC*2*266-1:0] w_rd;
    wire [NC*2*266-1:0] n_rd;
    reg  [WC*2*256-1:0] w_cap;
    reg  [NC*2*256-1:0] n_cap;
    generate
        for (g = 0; g < WC; g = g + 1) begin : g_w
            for (d = 0; d < 2; d = d + 1) begin : g_d
                `ifdef SYNTHESIS
                ot_rom_4096x266_m8 u_m (.clk(clk),
`else
                ot_rom_4096x266_m8 #(.INSTANCE($sformatf("crom_w_c%0d_d%0d", g, d))) u_m (.clk(clk),
`endif
                    .ce_in(w_ce[g] && w_row[g*RW + 12] == d[0]), .addr_in(w_row[g*RW +: 12]),
                    .rd_out(w_rd[(g*2 + d)*266 +: 266]));
                always @(posedge clk) w_cap[(g*2 + d)*256 +: 256] <= w_rd[(g*2 + d)*266 +: 256];
            end
        end
        for (g = 0; g < NC; g = g + 1) begin : g_n
            for (d = 0; d < 2; d = d + 1) begin : g_d
                `ifdef SYNTHESIS
                ot_rom_4096x266_m8 u_m (.clk(clk),
`else
                ot_rom_4096x266_m8 #(.INSTANCE($sformatf("crom_n_c%0d_d%0d", g, d))) u_m (.clk(clk),
`endif
                    .ce_in(n_ce[g] && n_row[g*RW + 12] == d[0]), .addr_in(n_row[g*RW +: 12]),
                    .rd_out(n_rd[(g*2 + d)*266 +: 266]));
                always @(posedge clk) n_cap[(g*2 + d)*256 +: 256] <= n_rd[(g*2 + d)*266 +: 256];
            end
        end
    endgenerate

    // per-lane side band through e3 / e4: valid, kind, depth bit
    wire [SW-1:0]  m_v, c_v;
    reg [SW*3-1:0] m_kind, c_kind;
    reg [SW-1:0]   m_dp, c_dp;
    generate
        for (gl = 0; gl < SW; gl = gl + 1) begin : g_sbv
            reg mv, cv;
            always @(posedge clk or negedge rst_l[gl]) begin
                if (!rst_l[gl]) begin mv <= 1'b0; cv <= 1'b0; end
                else begin mv <= t_v[gl]; cv <= mv; end
            end
            assign m_v[gl] = mv; assign c_v[gl] = cv;
        end
    endgenerate
    always @(posedge clk) begin
        m_kind <= t_kind; c_kind <= m_kind;
        for (l = 0; l < SW; l = l + 1) m_dp[l] <= t_row[l*RW + 12];
        c_dp <= m_dp;
    end

    // ---- e5: output station (held when not read) ----
    reg [SW*64-1:0] q_r;
    always @(posedge clk) begin
        for (l = 0; l < SW; l = l + 1) begin : g_out
            reg [63:0] w;
            case (c_kind[l*3 +: 3])
                K_WIDE:   w = w_cap[((l / WL)*2 + c_dp[l])*256 + (l % WL)*64 +: 64];
                K_NARROW: w = {32'd0, n_cap[((l / NL)*2 + c_dp[l])*256 + (l % NL)*32 +: 32]};
                K_QSC:    w = QSCALE_WORD;
                default:  w = 64'd0;
            endcase
            if (c_v[l]) q_r[l*64 +: 64] <= w;
        end
    end
    // ---- e6 (OREG): output pin station, no logic between q_p and the pin ----
    wire [SW*64-1:0] q_o;
    generate
        if (OREG != 0) begin : g_oreg
            reg [SW*64-1:0] q_p;
            always @(posedge clk) q_p <= q_r;
            assign q_o = q_p;
        end else begin : g_noreg
            assign q_o = q_r;
        end
    endgenerate
    assign crom_q = (MUT != 0) ? (q_o ^ {{(SW*64-1){1'b0}}, 1'b1}) : q_o;

    // ---- faults (sticky, first cause) ----
    // CHK: first OR level registered per 16-lane macro column (wide groups 4c..4c+3, narrow 2c, 2c+1), then the root
    wire [NCOL-1:0] fr_rng, fr_al, fr_dis;
    // DSPLIT: the disagree term of every macro registered beside the macro (before any OR)
    wire [WC-1:0] w_dis_f; wire [NC-1:0] n_dis_f;
    generate
        if (DSPLIT != 0) begin : g_disq
            reg [WC-1:0] w_dis_q; reg [NC-1:0] n_dis_q;
            always @(posedge clk or negedge rst_root)
                if (!rst_root) begin w_dis_q <= 0; n_dis_q <= 0; end else begin w_dis_q <= w_dis; n_dis_q <= n_dis; end
            assign w_dis_f = w_dis_q; assign n_dis_f = n_dis_q;
        end else begin : g_disc
            assign w_dis_f = w_dis; assign n_dis_f = n_dis;
        end
    endgenerate
    generate
        if (CHK != 0) begin : g_fcol
            for (gc = 0; gc < NCOL; gc = gc + 1) begin : g_c
                reg cr, ca_, cd;
                always @(posedge clk or negedge rst_root) begin
                    if (!rst_root) begin cr <= 1'b0; ca_ <= 1'b0; cd <= 1'b0; end
                    else begin
                        cr <= |t_rng[gc*LPC +: LPC]; ca_ <= |t_al[gc*LPC +: LPC];
                        cd <= (|w_dis_f[gc*(WC/NCOL) +: WC/NCOL]) || (|n_dis_f[gc*(NC/NCOL) +: NC/NCOL]);
                    end
                end
                if (DSPLIT == 0) begin : g_cdq
                    reg cdq;    // the row-disagree term is one stage earlier than the check terms: realign (first-cause order)
                    always @(posedge clk or negedge rst_root) if (!rst_root) cdq <= 1'b0; else cdq <= cd;
                    assign fr_rng[gc] = cr; assign fr_al[gc] = ca_; assign fr_dis[gc] = cdq;
                end else begin : g_cdr
                    // DSPLIT: cd ORs the per-macro registered disagree terms (w_dis_q / n_dis_q): already aligned
                    assign fr_rng[gc] = cr; assign fr_al[gc] = ca_; assign fr_dis[gc] = cd;
                end
            end
        end else begin : g_fflat
            assign fr_rng = {NCOL{|t_rng}}; assign fr_al = {NCOL{|t_al}}; assign fr_dis = {NCOL{(|w_dis) || (|n_dis)}};
        end
    endgenerate
    reg f_rng, f_al, f_dis;
    always @(posedge clk or negedge rst_root) begin
        if (!rst_root) begin
            f_rng <= 1'b0; f_al <= 1'b0; f_dis <= 1'b0; fault <= 1'b0; fault_code <= 2'd0;
        end else begin
            f_rng <= |fr_rng; f_al <= |fr_al; f_dis <= |fr_dis;
            if (!fault && (f_rng || f_al || f_dis)) begin
                fault <= 1'b1;
                fault_code <= f_rng ? 2'd1 : f_al ? 2'd2 : 2'd3;
            end
        end
    end
endmodule

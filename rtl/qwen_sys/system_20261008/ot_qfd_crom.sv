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
    parameter integer MUT = 0
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

    // ---- e1: input station ----
    wire [SW-1:0]    re1;
    wire [SW*AW-1:0] a1;
    wire [LW-1:0]    st1;
    ot_hdc_delay #(.W(SW), .D(1), .RESET(1)) u_is_re (.clk(clk), .rst_n(rst_n), .d(crom_re), .q(re1));
    ot_hdc_delay #(.W(SW*AW + LW), .D(1)) u_is_a (.clk(clk), .rst_n(rst_n), .d({crom_addr, crom_stage}), .q({a1, st1}));

    // ---- e2: per-lane region decode ----
    // narrow row of a layer-local region: stage * LROWS + off (LROWS = 148 = 128 + 16 + 4: three shifted adds)
    wire [RW-1:0] lbase = ({{(RW-LW){1'b0}}, st1} << 7) + ({{(RW-LW){1'b0}}, st1} << 4) + ({{(RW-LW){1'b0}}, st1} << 2);
    reg  [SW-1:0]    t_v;
    reg  [SW*3-1:0]  t_kind;
    reg  [SW*RW-1:0] t_row;
    reg  [SW-1:0]    t_rng, t_al;
    integer l;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            t_v <= 0; t_rng <= 0; t_al <= 0;
        end else begin
            for (l = 0; l < SW; l = l + 1) begin : g_dec
                reg [AW-1:0] a, off;
                reg [2:0] k;
                reg [RW-1:0] r;
                reg al;
                a = a1[l*AW +: AW];
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
                if ((k == K_WIDE || k == K_NARROW) && off[5:0] != l[5:0]) al = 1'b0;
                t_v[l] <= re1[l];
                t_kind[l*3 +: 3] <= k;
                t_row[l*RW +: RW] <= r;
                t_rng[l] <= re1[l] && k == K_BAD;
                t_al[l] <= re1[l] && !al;
            end
        end
    end

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
                ot_rom_4096x266_m8 #(.INSTANCE($sformatf("crom_w_c%0d_d%0d", g, d))) u_m (.clk(clk),
                    .ce_in(w_ce[g] && w_row[g*RW + 12] == d[0]), .addr_in(w_row[g*RW +: 12]),
                    .rd_out(w_rd[(g*2 + d)*266 +: 266]));
                always @(posedge clk) w_cap[(g*2 + d)*256 +: 256] <= w_rd[(g*2 + d)*266 +: 256];
            end
        end
        for (g = 0; g < NC; g = g + 1) begin : g_n
            for (d = 0; d < 2; d = d + 1) begin : g_d
                ot_rom_4096x266_m8 #(.INSTANCE($sformatf("crom_n_c%0d_d%0d", g, d))) u_m (.clk(clk),
                    .ce_in(n_ce[g] && n_row[g*RW + 12] == d[0]), .addr_in(n_row[g*RW +: 12]),
                    .rd_out(n_rd[(g*2 + d)*266 +: 266]));
                always @(posedge clk) n_cap[(g*2 + d)*256 +: 256] <= n_rd[(g*2 + d)*266 +: 256];
            end
        end
    endgenerate

    // per-lane side band through e3 / e4: valid, kind, depth bit
    reg [SW-1:0]   m_v, c_v;
    reg [SW*3-1:0] m_kind, c_kind;
    reg [SW-1:0]   m_dp, c_dp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_v <= 0; c_v <= 0; end
        else begin m_v <= t_v; c_v <= m_v; end
    end
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
    assign crom_q = (MUT != 0) ? (q_r ^ {{(SW*64-1){1'b0}}, 1'b1}) : q_r;

    // ---- faults (sticky, first cause) ----
    reg f_rng, f_al, f_dis;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            f_rng <= 1'b0; f_al <= 1'b0; f_dis <= 1'b0; fault <= 1'b0; fault_code <= 2'd0;
        end else begin
            f_rng <= |t_rng; f_al <= |t_al; f_dis <= (|w_dis) || (|n_dis);
            if (!fault && (f_rng || f_al || f_dis)) begin
                fault <= 1'b1;
                fault_code <= f_rng ? 2'd1 : f_al ? 2'd2 : 2'd3;
            end
        end
    end
endmodule

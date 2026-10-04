`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_window_stream_la_s81: the issue engine of ot_dsrom_window_stream_la (rtl/chip/, audited, unchanged)
// as bound into the S81 window source (claude/dsrom-s81-window-bind-20261004).
//   * issue: identical -- the next aligned group of IW 128-B granules, all-or-nothing on their pseudo-channels'
//     ready, tag = granule index, the whole 2,176-sector window in flight up to the controller queues;
//   * accounting: identical `run` / landed-sector count (busy until all 2,176 sectors have landed) and the same
//     per-beat checks (tag range, pseudo-channel of the sector, FP8 code 0x7f / E8M0 0xff poison) -> fault;
//   * the 128 x 4,224-b staging array and its per-row counters are NOT here: the beats are landed by
//     ot_dsrom_window_la_stage (68 single-write columns, four-row read port), which also checks double landing.
// Written in the Verilog subset the ORFS yosys front end accepts (no initialised automatic variables), so the
// simulated and the screened RTL are the same text.
// ---------------------------------------------------------------------------
module ot_dsrom_window_stream_la_s81 #(
    parameter integer NPC    = 32,
    parameter integer AW     = 30,
    parameter integer TAGW   = 13,
    parameter integer LENW   = 4,
    parameter integer BEATW  = 4,
    parameter integer IW     = 8,
    parameter integer ISSUE_PC = 0       // 1: per-pseudo-channel issue (no all-or-nothing group)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire [AW-1:0]         base,               // must be a multiple of 32 sectors
    output wire                  busy,
    output reg                   fault,
    output wire [NPC-1:0]        req_v,
    input  wire [NPC-1:0]        req_rdy,
    output wire [NPC*AW-1:0]     req_addr,
    output wire [NPC*LENW-1:0]   req_len,
    output wire [NPC*TAGW-1:0]   req_tag,
    input  wire [NPC-1:0]        rsp_v,               // accepted (landed) beats
    input  wire [NPC*TAGW-1:0]   rsp_tag,
    input  wire [NPC*BEATW-1:0]  rsp_beat,
    input  wire [NPC*256-1:0]    rsp_data
);
    localparam integer PITCH = 17;
    localparam integer NSECT = 128 * PITCH;              // 2,176
    localparam integer NGRAN = NSECT / 4;                // 544
    localparam integer LPC = $clog2(NPC);
    function [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = s[2 +: LPC] ^ s[2 + LPC +: LPC] ^ s[2 + 2 * LPC +: LPC];
    endfunction
    function poison_codes(input [255:0] c);
        integer z;
        begin
            poison_codes = 1'b0;
            for (z = 0; z < 32; z = z + 1) if (c[8*z +: 7] == 7'h7f) poison_codes = 1'b1;
        end
    endfunction
    function poison_scales(input [127:0] s);
        integer z;
        begin
            poison_scales = 1'b0;
            for (z = 0; z < 16; z = z + 1) if (s[8*z +: 8] == 8'hff) poison_scales = 1'b1;
        end
    endfunction
    reg [AW-1:0] b;
    reg [15:0] gnext;
    reg run;
    reg [15:0] landed;
    // ---- issue (ot_dsrom_window_stream_la) ----
    reg [NPC-1:0] v_c; reg [NPC*AW-1:0] a_c; reg [NPC*TAGW-1:0] t_c; reg [NPC*LENW-1:0] l_c;
    reg grp_ok;
    reg [AW-1:0] gs [0:IW-1];
    reg [LPC-1:0] gp [0:IW-1];
    integer i;
    always @* begin
        for (i = 0; i < IW; i = i + 1) begin
            gs[i] = b + ((gnext + i) << 2);
            gp[i] = pc_of(gs[i]);
        end
        v_c = 0; a_c = 0; t_c = 0; l_c = 0; grp_ok = run && gnext < NGRAN;
        for (i = 0; i < IW; i = i + 1) begin
            if (!req_rdy[gp[i]] || v_c[gp[i]]) grp_ok = 0;
            v_c[gp[i]] = 1'b1;
            a_c[gp[i]*AW +: AW] = gs[i]; t_c[gp[i]*TAGW +: TAGW] = gnext + i; l_c[gp[i]*LENW +: LENW] = 4;
        end
        if (!grp_ok) v_c = 0;
    end
    // ---- ISSUE_PC = 1: every pseudo-channel walks its own granules (one per aligned 32-granule group of the
    // stack's address space: granule 32 G + (p ^ (G ^ G >> 5) mod 32) maps to pseudo-channel p), skipping those
    // outside the window, and issues whenever ITS port is ready: no head-of-line blocking across channels ----
    localparam integer GW = AW - 2;
    wire [GW-1:0] a0 = b[AW-1:2];                         // first granule (absolute)
    wire [GW-6:0] g0 = a0[GW-1:5], g1 = (a0 + NGRAN - 1) >> 5;
    reg  [GW-6:0] cur [0:NPC-1];
    reg  [NPC-1:0] pc_done;
    reg  [NPC-1:0] v_p;
    reg  [NPC*AW-1:0] a_p; reg [NPC*TAGW-1:0] t_p;
    reg  [GW-1:0] ga [0:NPC-1];
    reg  [NPC-1:0] in_win;
    integer q;
    always @* begin
        v_p = 0; a_p = 0; t_p = 0;
        for (q = 0; q < NPC; q = q + 1) begin
            ga[q] = {cur[q], 5'(q) ^ (cur[q][4:0] ^ cur[q][9:5])};
            in_win[q] = ga[q] >= a0 && ga[q] < a0 + NGRAN;
            v_p[q] = run && !pc_done[q] && in_win[q];
            a_p[q*AW +: AW] = {ga[q], 2'b00};
            t_p[q*TAGW +: TAGW] = ga[q] - a0;
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pc_done <= '1; for (integer z = 0; z < NPC; z = z + 1) cur[z] <= 0; end
        else if (start && !run) begin pc_done <= '0; for (integer z = 0; z < NPC; z = z + 1) cur[z] <= base[AW-1:7]; end
        else for (integer z = 0; z < NPC; z = z + 1)
            if (run && !pc_done[z] && (!in_win[z] || req_rdy[z])) begin
                if (cur[z] == g1) pc_done[z] <= 1'b1; else cur[z] <= cur[z] + 1'b1;
            end
    assign req_v = ISSUE_PC ? v_p : v_c; assign req_addr = ISSUE_PC ? a_p : a_c;
    assign req_tag = ISSUE_PC ? t_p : t_c; assign req_len = ISSUE_PC ? {NPC{LENW'(4)}} : l_c;
    assign busy = run;
    // ---- landed beats: count and checks ----
    reg [NPC-1:0] bad_beat;
    reg [6:0] nbeats;
    reg [AW-1:0] sa;
    reg [15:0] sec;
    integer p, k;
    always @* begin
        nbeats = 0;
        for (p = 0; p < NPC; p = p + 1) begin
            sec = (rsp_tag[p*TAGW +: TAGW] << 2) + rsp_beat[p*BEATW +: BEATW];
            sa = b + sec;
            k = sec % PITCH;
            bad_beat[p] = rsp_v[p] && (sec >= NSECT || pc_of(sa) != p ||
                          (k < 16 ? poison_codes(rsp_data[p*256 +: 256]) : poison_scales(rsp_data[p*256 +: 128])));
            if (rsp_v[p]) nbeats = nbeats + 1;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; gnext <= 0; fault <= 0; landed <= 0; b <= 0;
        end else if (start && !run) begin
            run <= 1; gnext <= 0; landed <= 0; b <= base;
            if (base[4:0] != 0) fault <= 1'b1;
        end else if (run) begin
            if (grp_ok) gnext <= gnext + IW;
            if (|bad_beat) fault <= 1'b1;
            landed <= landed + nbeats;
            if (landed + nbeats == NSECT) run <= 0;
        end
    end
endmodule

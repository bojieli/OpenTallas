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
    parameter integer ISSUE_PC = 0,      // 1: per-pseudo-channel issue (no all-or-nothing group)
    // 1: margin-first timing (takeover-ds 2026-10-06, default off, ISSUE_PC=1 only).  The job start is
    // registered once (base adders split across two edges, +1 load cycle), the per-channel window
    // bounds are kept copies, the landed-beat poison flags are computed at the first edge and carried as
    // two bits (no 256-b data delay line), adders are log-depth, the population count is split in four.
    parameter bit MARGIN = 0
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
    // outside the window, and presents them from a request register whenever ITS port takes the previous one:
    // no head-of-line blocking across channels.  Only the first and last groups are partial, so the window test
    // is two group-equality compares and two 5-bit compares; the tag is the 10-bit offset from the first granule.
    localparam integer GW = AW - 7;                       // group index bits
    // group index G = {Ghi, Glo}: a window spans <= 18 groups, so Glo (5 bits) wraps at most once per job and Ghi
    // then takes the value Ghi1 = Ghi + 1 precomputed at the job start (no wide incrementer per channel)
    reg  [GW-6:0] ghi0, ghi1;
    reg  [4:0]    j0, j1;                                 // first / last granule within the first / last group
    reg  [4:0]    nlast;                                  // last group - first group (<= 17)
    reg  [NPC-1:0] hi_c;                                  // channel's Glo has wrapped (Ghi = ghi1)
    reg  [4:0]    Glo [0:NPC-1], Grel [0:NPC-1], jq [0:NPC-1];
    reg  [NPC-1:0] pdone, rv;
    reg  [AW-1:0] raddr [0:NPC-1];
    reg  [TAGW-1:0] rtag [0:NPC-1];
    reg  inw; reg [4:0] gl1; reg [GW-6:0] gh, ghn;
    integer q;
    // MARGIN: start_e/base_e are the start pulse and base one edge later; the last-granule sum is formed
    // in that edge's register.
    reg start_q; reg [AW-1:0] base_q; reg [AW-3:0] sa1_q;
    wire [AW-3:0] sa1_c;
    generate if (MARGIN) begin : g_sa1
        ot_hdc_ksadd_k #(.W(AW-2)) u_sa1 (.a(base[AW-1:2]), .b((AW-2)'(NGRAN - 1)), .cin(1'b0), .s(sa1_c), .cout());
    end else begin : g_sa1_plain
        assign sa1_c = base[AW-1:2] + (NGRAN - 1);
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin start_q <= 1'b0; base_q <= '0; sa1_q <= '0; end
        else begin start_q <= start; if (start) begin base_q <= base; sa1_q <= sa1_c; end end
    wire start_e = MARGIN ? start_q : start;
    wire [AW-1:0] base_e = MARGIN ? base_q : base;
    wire [AW-3:0] sa0 = base_e[AW-1:2];                   // the job's first granule (at start)
    wire [AW-3:0] sa1 = MARGIN ? sa1_q : sa1_c;           // its last granule
    wire [GW-6:0] shi0 = sa0[AW-3:10];
    // kept per-channel copies of the job bounds (MARGIN)
    reg [GW-6:0] ghi0_c [0:NPC-1], ghi1_c [0:NPC-1];
    reg [4:0] j0_c [0:NPC-1], j1_c [0:NPC-1], nlast_c [0:NPC-1];
    wire [AW-8:0] nl_c;
    wire [GW-6:0] shi1_c;
    generate if (MARGIN) begin : g_nl
        ot_hdc_ksadd_k #(.W(AW-7)) u_nl (.a(sa1[AW-3:5]), .b(~sa0[AW-3:5]), .cin(1'b1), .s(nl_c), .cout());
        ot_hdc_inc_k #(.W(GW-5)) u_shi1 (.a(shi0), .inc(1'b1), .y(shi1_c), .co());
    end else begin : g_nl_plain
        assign nl_c = '0; assign shi1_c = '0;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            pdone <= '1; rv <= '0; ghi0 <= 0; ghi1 <= 0; j0 <= 0; j1 <= 0; nlast <= 0; hi_c <= 0;
            for (q = 0; q < NPC; q = q + 1) begin Glo[q] <= 0; Grel[q] <= 0; jq[q] <= 0; raddr[q] <= 0; rtag[q] <= 0; end
        end else if (start_e && !run) begin
            pdone <= '0; rv <= '0; hi_c <= 0;
            ghi0 <= shi0; ghi1 <= shi0 + 1'b1; j0 <= sa0[4:0]; j1 <= sa1[4:0];
            nlast <= sa1[AW-3:5] - sa0[AW-3:5];
            for (q = 0; q < NPC; q = q + 1) begin
                Glo[q] <= sa0[9:5]; Grel[q] <= 0; jq[q] <= q[4:0] ^ sa0[9:5] ^ shi0[4:0];
                if (MARGIN) begin
                    ghi0_c[q] <= shi0; ghi1_c[q] <= shi1_c; j0_c[q] <= sa0[4:0]; j1_c[q] <= sa1[4:0];
                    nlast_c[q] <= nl_c[4:0];
                end
            end
        end else for (q = 0; q < NPC; q = q + 1)
            if (!rv[q] || req_rdy[q]) begin
                if (run && !pdone[q]) begin
                    gh = hi_c[q] ? (MARGIN ? ghi1_c[q] : ghi1) : (MARGIN ? ghi0_c[q] : ghi0);
                    inw = (Grel[q] != 5'd0 || jq[q] >= (MARGIN ? j0_c[q] : j0)) &&
                          (Grel[q] != (MARGIN ? nlast_c[q] : nlast) || jq[q] <= (MARGIN ? j1_c[q] : j1));
                    rv[q] <= inw;
                    raddr[q] <= {gh, Glo[q], jq[q], 2'b00};
                    rtag[q] <= {Grel[q], jq[q]} - {5'd0, (MARGIN ? j0_c[q] : j0)};
                    if (Grel[q] == (MARGIN ? nlast_c[q] : nlast)) pdone[q] <= 1'b1;
                    gl1 = Glo[q] + 1'b1;
                    ghn = (hi_c[q] || gl1 == 5'd0) ? (MARGIN ? ghi1_c[q] : ghi1) : (MARGIN ? ghi0_c[q] : ghi0);
                    if (gl1 == 5'd0) hi_c[q] <= 1'b1;
                    Glo[q] <= gl1; Grel[q] <= Grel[q] + 1'b1; jq[q] <= q[4:0] ^ gl1 ^ ghn[4:0];
                end else rv[q] <= 1'b0;
            end
    reg [NPC*AW-1:0] a_p; reg [NPC*TAGW-1:0] t_p;
    always @* for (q = 0; q < NPC; q = q + 1) begin a_p[q*AW +: AW] = raddr[q]; t_p[q*TAGW +: TAGW] = rtag[q]; end
    assign req_v = ISSUE_PC ? rv : v_c; assign req_addr = ISSUE_PC ? a_p : a_c;
    assign req_tag = ISSUE_PC ? t_p : t_c; assign req_len = ISSUE_PC ? {NPC{LENW'(4)}} : l_c;
    assign busy = run;
    // ---- landed beats: registered, then the column-16 (scale sector) test through a pipelined constant
    // multiply, the FP8 / E8M0 poison and range checks, and a two-half population count; every decision reads
    // registers.  The pseudo-channel-of-sector check is a simulation assertion (the controller's port contract).
    reg [NPC-1:0] v1, v2, v3, v4, v5, rng2, rng3, rng4, rng5, k16_5;
    reg [11:0] s1 [0:NPC-1], s2 [0:NPC-1], s3 [0:NPC-1];
    reg [23:0] x2 [0:NPC-1];
    reg [6:0] sl3 [0:NPC-1], sl4 [0:NPC-1];
    reg [11:0] t4 [0:NPC-1];
    reg [255:0] d1 [0:NPC-1], d2 [0:NPC-1], d3 [0:NPC-1], d4 [0:NPC-1], d5 [0:NPC-1];
    reg [NPC-1:0] bad_beat, bad_q;
    reg [4:0] nb_a, nb_b;
    reg [6:0] nb_q;
    reg [23:0] mm;
    reg pc_sim_bad;                                       // simulation assertion only (stays 0 in synthesis)
    integer p;
    // landed-beat arithmetic as explicit wires (MARGIN: log-depth adders), poison flags (MARGIN)
    wire [23:0] x2_c [0:NPC-1], mm_c [0:NPC-1];
    wire [11:0] t4_c [0:NPC-1], k16d_c [0:NPC-1];
    reg [NPC-1:0] pc1, pc2, pc3, pc4, pc5, ps1, ps2, ps3, ps4, ps5;
    reg [3:0] nbp [0:3];
`ifndef SYNTHESIS
    initial if (MARGIN && (ISSUE_PC == 0 || NPC != 32)) $fatal(1, "ot_dsrom_window_stream_la_s81: MARGIN needs ISSUE_PC=1, NPC=32");
`endif
    genvar pg;
    generate for (pg = 0; pg < NPC; pg = pg + 1) begin : g_land
        if (MARGIN) begin : g_ks
            ot_hdc_ksadd_k #(.W(24)) u_x2 (.a({12'd0, s1[pg]} << 12), .b(~({12'd0, s1[pg]} << 8)), .cin(1'b1),
                .s(x2_c[pg]), .cout());
            ot_hdc_ksadd_k #(.W(24)) u_mm (.a(x2[pg]), .b({12'd0, s2[pg]} << 4), .cin(1'b0), .s(mm_c[pg]), .cout());
            ot_hdc_ksadd_k #(.W(12)) u_t4 (.a(s3[pg]), .b(~{1'b0, sl3[pg], 4'b0000}), .cin(1'b1), .s(t4_c[pg]), .cout());
            ot_hdc_ksadd_k #(.W(12)) u_k16 (.a(t4[pg]), .b(~{5'd0, sl4[pg]}), .cin(1'b1), .s(k16d_c[pg]), .cout());
        end else begin : g_plain
            assign x2_c[pg] = ({12'd0, s1[pg]} << 12) - ({12'd0, s1[pg]} << 8);
            assign mm_c[pg] = x2[pg] + ({12'd0, s2[pg]} << 4);
            assign t4_c[pg] = s3[pg] - {sl3[pg], 4'b0000};
            assign k16d_c[pg] = t4[pg] - sl4[pg];
        end
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            v1 <= 0; v2 <= 0; v3 <= 0; v4 <= 0; v5 <= 0; rng2 <= 0; rng3 <= 0; rng4 <= 0; rng5 <= 0; k16_5 <= 0; bad_q <= 0;
            nb_a <= 0; nb_b <= 0; nb_q <= 0; pc_sim_bad <= 0;
            nbp[0] <= 0; nbp[1] <= 0; nbp[2] <= 0; nbp[3] <= 0;
        end else begin
            v1 <= rsp_v; v2 <= v1; v3 <= v2; v4 <= v3; v5 <= v4;
            for (p = 0; p < NPC; p = p + 1) begin
                s1[p] <= {rsp_tag[p*TAGW +: TAGW], 2'b00} + rsp_beat[p*BEATW +: BEATW];
                d1[p] <= rsp_data[p*256 +: 256];
                x2[p] <= x2_c[p];                                         // s1 * 3,840
                s2[p] <= s1[p]; rng2[p] <= s1[p] >= NSECT; d2[p] <= d1[p];
                mm = mm_c[p];                                               // s * 3,856; slot = s / 17 = mm >> 16
                sl3[p] <= mm[22:16]; s3[p] <= s2[p]; rng3[p] <= rng2[p]; d3[p] <= d2[p];
                t4[p] <= t4_c[p]; sl4[p] <= sl3[p];                         // s - 16 slot
                rng4[p] <= rng3[p]; d4[p] <= d3[p];
                k16_5[p] <= k16d_c[p] == 12'd16;                             // s - 17 slot == 16: the scale sector
                rng5[p] <= rng4[p]; d5[p] <= d4[p];
                if (MARGIN) begin
                    pc1[p] <= poison_codes(rsp_data[p*256 +: 256]); ps1[p] <= poison_scales(rsp_data[p*256 +: 128]);
                    pc2[p] <= pc1[p]; pc3[p] <= pc2[p]; pc4[p] <= pc3[p]; pc5[p] <= pc4[p];
                    ps2[p] <= ps1[p]; ps3[p] <= ps2[p]; ps4[p] <= ps3[p]; ps5[p] <= ps4[p];
                end
`ifndef SYNTHESIS
                if (v1[p] && pc_of(b + s1[p]) != p) pc_sim_bad <= 1'b1;
`endif
            end
            bad_q <= bad_beat;
            if (MARGIN) begin
                // four eight-beat counts of v4 (= v5 one edge earlier), summed at nb_a/nb_b's edge
                for (p = 0; p < 4; p = p + 1) nbp[p] <= $countones(v4[8*p +: 8]);
                nb_a <= {1'b0, nbp[0]} + {1'b0, nbp[1]}; nb_b <= {1'b0, nbp[2]} + {1'b0, nbp[3]};
            end else begin
                nb_a <= $countones(v5[NPC/2-1:0]); nb_b <= $countones(v5[NPC-1:NPC/2]);
            end
            nb_q <= nb_a + nb_b;
        end
    always @* begin
        for (p = 0; p < NPC; p = p + 1)
            bad_beat[p] = v5[p] && (rng5[p] || (MARGIN ? (k16_5[p] ? ps5[p] : pc5[p]) :
                          (k16_5[p] ? poison_scales(d5[p][127:0]) : poison_codes(d5[p]))));
    end
    reg [11:0] rem;                                       // sectors still to land
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; gnext <= 0; fault <= 0; landed <= 0; b <= 0; rem <= 0;
        end else if (start_e && !run) begin
            run <= 1; gnext <= 0; landed <= 0; rem <= NSECT; b <= base_e;
            if (base_e[4:0] != 0) fault <= 1'b1;
        end else if (run) begin
            if (grp_ok) gnext <= gnext + IW;
            if (|bad_q || pc_sim_bad) fault <= 1'b1;
            landed <= landed + nb_q;
            rem <= rem - nb_q;
            if (rem == {5'd0, nb_q}) run <= 0;
        end
    end
endmodule

// DIE-HBM-83-OPSG 11-06 (d44v part 57): hub form of the ot_hgi_su_lgroup2_lf instance in the operand group tiles
// ot_hgi_sfu_opsa_group0/1 and ot_hgi_sfu_opsb_group (N 16, M 16, LWB 15, AW 24, NLW 0, NS 8, MACRO 1, BREG 1, FREG 1; no sector
// reads, no lane writes, no STREAM landing: the group tiles tie them off).  Opt-in: the tiles use it only under `define
// OT_OPSG_GP; every other text is unchanged.
// Cause: the stage write is a 64-word to 16-bank crossbar and the read a 16-lane network, in ONE cycle with the wire across the
// 760 um tile (group0 CTS -392 ps, opsb_group -650 ps), on banks of 823-pin macros (channel count 8.66).
// Form: narrow banks (ot_hgi_su_lbank_n32, 90 signal pins) + a macro-free logic hub in the tile; only the bank buses leave the
// hub (88 nets per bank) and every haul is register to register.  All bank ops (reads and writes) move 2 edges together, so
// their order on every bank is kept:
//   inputs (the tile's IREG) -> decode -> S1 (per-bank read row + re, write row + we, one-hot word select of the winner,
//   kept copy of the stage data) -> write AND-OR -> S2 (wd; read/write controls delayed) -> haul -> g_bank[b] BREG next to
//   the macro -> SRAM -> g_bank[b].q_rd next to the macro -> haul -> g_hc hub copy -> lane network with kept one-hot selects
//   (fanout 32 each) -> q_out -> haul -> kit face flop at the pin.
// Latency vs ot_hgi_su_lgroup2_lf with the same inputs: rd + 5 edges (2 ops, q_rd, g_hc, q_out); flt + 0 (the checks read the
// same terms from the same inputs one register stage from the decode).
// MUT (bench mutants only, default 0): 1 bank 5 write data bypasses S2; 2 read select one edge early (lane network);
// 3 bank 3 stage-lane priority = LOWEST lane; 4 flt one edge early; 5 bank 9 read word bypasses q_rd; 6 bank 2 write row
// without the wrap increment; 7 lane 3 not gated by its candidate check; 8 mask ignored on (lane 2, word 3);
// 9 bank 11 read op one edge earlier than the writes (S2 bypass, read/write order breaks);
// 10 lane 0 read network takes lane-candidate select only (not any bank).
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_su_lgroup2_gp #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [15:0]   rq,        // qualified lane reads
    input  wire [15:0]   rr,        // raw lane read enables
    input  wire [383:0]  ra,
    output wire [511:0]  rd,
    input  wire [7:0]    sw_v,      // sector lanes: up to 8 consecutive words (stage)
    input  wire [119:0]  sw_addr,
    input  wire [63:0]   sw_mask,
    input  wire [2047:0] sw_d,
    output reg           flt
);
    localparam integer N = 16, LN = 4, RB = 11, AW = 24, LWB = 15, NS = 8, NW = 64, NCAND = 4;
    // candidate bank k of lane l (M = 16: NROT 1, NHALF 2, HM 8), same as cbank of ot_hgi_su_lgroup2_lf
    function automatic [LN-1:0] cbank(input integer l, input integer k);
        case (k)
            0: cbank = LN'(l);
            1: cbank = LN'(l ^ 1);
            2: cbank = LN'(l >> 1);
            default: cbank = LN'((l >> 1) + 8);
        endcase
    endfunction
    function automatic is_cand(input integer l, input integer b);
        integer k;
        is_cand = (l == 0) && (MUT != 10);
        for (k = 0; k < NCAND; k = k + 1) if (cbank(l, k) == LN'(b)) is_cand = 1'b1;
    endfunction
    // ---- decode: lane candidate check, per-bank lane read select (LOWEST lane that hits gives the row)
    wire [N-1:0] lok;
    wire [LN-1:0] lbk [0:N-1]; wire [RB-1:0] lrw [0:N-1];
    for (genvar l = 0; l < N; l = l + 1) begin : g_lf
        assign lbk[l] = ra[l*AW +: LN]; assign lrw[l] = ra[l*AW + LN +: RB];
        reg ok;
        always @* begin : okc
            integer k_;
            ok = (l == 0) || (MUT == 7 && l == 3);
            for (k_ = 0; k_ < NCAND; k_ = k_ + 1) if (cbank(l, k_) == lbk[l]) ok = 1'b1;
        end
        assign lok[l] = ok;
    end
    wire [N-1:0] i_re; wire [RB-1:0] i_ra [0:N-1];
    for (genvar b = 0; b < N; b = b + 1) begin : g_rs
        wire [N-1:0] h, oh;
        for (genvar l = 0; l < N; l = l + 1) begin : g_h
            assign h[l] = rr[l] && lok[l] && lbk[l] == LN'(b);
            if (l == 0) begin : g_o0 assign oh[l] = h[l]; end
            else begin : g_on assign oh[l] = h[l] && !(|h[l-1:0]); end
        end
        reg [RB-1:0] row;
        always @* begin : ao
            integer i_;
            row = {RB{1'b0}};
            for (i_ = 0; i_ < N; i_ = i_ + 1) row = row | ({RB{oh[i_]}} & lrw[i_]);
        end
        assign i_re[b] = |h; assign i_ra[b] = row;
    end
    // ---- decode: stage writes.  Bank b takes word off = b - addr[3:0] (mod 16, off < 8) of each sector lane; the HIGHEST lane
    // that hits wins; two hits = collision.  The winner is kept as a one-hot over the 64 stage words (lane * 8 + off).
    wire [N-1:0] i_we, i_cb; wire [RB-1:0] i_wa [0:N-1]; wire [NW-1:0] i_sel [0:N-1];
`ifdef OT_OPSG_ROT
    wire [NS-1:0] i_oh [0:N-1];
`endif
    for (genvar b = 0; b < N; b = b + 1) begin : g_ws
        wire [NS-1:0] h, oh; wire [RB-1:0] rw [0:NS-1]; wire [2:0] o3 [0:NS-1];
        for (genvar s = 0; s < NS; s = s + 1) begin : g_h
            wire [LWB-1:0] a = sw_addr[s*LWB +: LWB];
            wire [LN-1:0] off = LN'(b) - a[LN-1:0];
            assign o3[s] = off[2:0];
            assign h[s] = sw_v[s] && off < LN'(8) && (sw_mask[s*8 + off[2:0]] || (MUT == 8 && s == 2 && off[2:0] == 3'd3));
            assign rw[s] = (MUT == 6 && b == 2) ? a[LWB-1:LN] : a[LWB-1:LN] + RB'(LN'(b) < a[LN-1:0]);
            if (MUT == 3 && b == 3) begin : g_ml
                if (s == 0) begin : g_o0 assign oh[s] = h[s]; end else begin : g_on assign oh[s] = h[s] && !(|h[s-1:0]); end
            end else if (s == NS - 1) begin : g_ot assign oh[s] = h[s]; end
            else begin : g_on assign oh[s] = h[s] && !(|h[NS-1:s+1]); end
        end
        reg [RB-1:0] row; reg two; reg [NW-1:0] sel;
        always @* begin : ao
            integer i_;
            row = {RB{1'b0}}; two = 1'b0; sel = {NW{1'b0}};
            for (i_ = 0; i_ < NS; i_ = i_ + 1) begin
                row = row | ({RB{oh[i_]}} & rw[i_]);
                if (h[i_] && !oh[i_]) two = 1'b1;
                if (oh[i_]) sel[i_*8 + o3[i_]] = 1'b1;
            end
        end
        assign i_we[b] = |h; assign i_wa[b] = row; assign i_cb[b] = two; assign i_sel[b] = sel;
`ifdef OT_OPSG_ROT
        assign i_oh[b] = oh;
`endif
    end
`ifdef OT_OPSG_ROT
    // ---- opsbg_C3 (HBM-CORES-B 11-09), ROT form of the write crossbar, cycle-exact: the 64-word to 16-bank AND-OR (32768 terms, the
    // C2q GRT-0116 ball at x 560-720) is cut in two.  word = s*8 + off and off[2:0] = (b[2:0] - a[2:0]) mod 8 depends on the bank
    // only through b[2:0], so before S1 each sector lane rotates its 8 words by a[2:0] (3-stage barrel), and after S1 each bank
    // takes one of 8 lanes by the winner one-hot (4096 terms; a q_rot flop drives banks p and p+8 only).
    wire [2047:0] i_rot;
    for (genvar s = 0; s < NS; s = s + 1) begin : g_rot
        wire [2:0]   a3 = sw_addr[s*LWB +: 3];
        wire [255:0] r0 = sw_d[s*256 +: 256];
        wire [255:0] r1 = a3[0] ? {r0[223:0], r0[255:224]} : r0;
        wire [255:0] r2 = a3[1] ? {r1[191:0], r1[255:192]} : r1;
        wire [255:0] r3 = a3[2] ? {r2[127:0], r2[255:128]} : r2;
        assign i_rot[s*256 +: 256] = r3;
    end
    wire [N-1:0] s1_re, s1_we; wire [RB-1:0] s1_ra [0:N-1], s1_wa [0:N-1]; wire [NS-1:0] s1_oh [0:N-1]; wire [2047:0] s1_d;
    if (1) begin : g_s1
        (* keep *) reg [N-1:0] q_re, q_we; (* keep *) reg [N*RB-1:0] q_ra, q_wa; (* keep *) reg [N*NS-1:0] q_oh; (* keep *) reg [2047:0] q_rot;
        integer b_;
        always @(posedge clk) begin
            q_re <= i_re; q_we <= i_we; q_rot <= i_rot;
            for (b_ = 0; b_ < N; b_ = b_ + 1) begin q_ra[b_*RB +: RB] <= i_ra[b_]; q_wa[b_*RB +: RB] <= i_wa[b_]; q_oh[b_*NS +: NS] <= i_oh[b_]; end
        end
        for (genvar b = 0; b < N; b = b + 1) begin : g_o
            assign s1_ra[b] = q_ra[b*RB +: RB]; assign s1_wa[b] = q_wa[b*RB +: RB]; assign s1_oh[b] = q_oh[b*NS +: NS];
        end
        assign s1_re = q_re; assign s1_we = q_we; assign s1_d = q_rot;
    end
`else
    // ---- S1 (hub): decoded ops, kept stage data copy.  wa_1/ra_1 hold the decoded rows.
    wire [N-1:0] s1_re, s1_we; wire [RB-1:0] s1_ra [0:N-1], s1_wa [0:N-1]; wire [NW-1:0] s1_sel [0:N-1]; wire [2047:0] s1_d;
    if (1) begin : g_s1
        (* keep *) reg [N-1:0] q_re, q_we; (* keep *) reg [N*RB-1:0] q_ra, q_wa; (* keep *) reg [N*NW-1:0] q_sel; (* keep *) reg [2047:0] q_d;
        integer b_;
        always @(posedge clk) begin
            q_re <= i_re; q_we <= i_we; q_d <= sw_d;
            for (b_ = 0; b_ < N; b_ = b_ + 1) begin q_ra[b_*RB +: RB] <= i_ra[b_]; q_wa[b_*RB +: RB] <= i_wa[b_]; q_sel[b_*NW +: NW] <= i_sel[b_]; end
        end
        for (genvar b = 0; b < N; b = b + 1) begin : g_o
            assign s1_ra[b] = q_ra[b*RB +: RB]; assign s1_wa[b] = q_wa[b*RB +: RB]; assign s1_sel[b] = q_sel[b*NW +: NW];
        end
        assign s1_re = q_re; assign s1_we = q_we; assign s1_d = q_d;
    end
`endif
    // ---- S2 (hub): write AND-OR; read / write controls delayed
    wire [N-1:0] s2_re, s2_we; wire [RB-1:0] s2_ra [0:N-1], s2_wa [0:N-1]; wire [31:0] s2_wd [0:N-1];
    if (1) begin : g_s2
        (* keep *) reg [N-1:0] q_re, q_we; (* keep *) reg [N*RB-1:0] q_ra, q_wa; (* keep *) reg [N*32-1:0] q_wd;
        reg [31:0] wdat [0:N-1];
        always @* begin : wao
            integer b_, w_;
            for (b_ = 0; b_ < N; b_ = b_ + 1) begin
                wdat[b_] = 32'd0;
`ifdef OT_OPSG_ROT
                for (w_ = 0; w_ < NS; w_ = w_ + 1) wdat[b_] = wdat[b_] | ({32{s1_oh[b_][w_]}} & s1_d[32*(w_*8 + (b_ & 7)) +: 32]);
`else
                for (w_ = 0; w_ < NW; w_ = w_ + 1) wdat[b_] = wdat[b_] | ({32{s1_sel[b_][w_]}} & s1_d[32*w_ +: 32]);
`endif
            end
        end
        integer b_;
        always @(posedge clk) begin
            q_re <= s1_re; q_we <= s1_we;
            for (b_ = 0; b_ < N; b_ = b_ + 1) begin q_ra[b_*RB +: RB] <= s1_ra[b_]; q_wa[b_*RB +: RB] <= s1_wa[b_]; q_wd[b_*32 +: 32] <= wdat[b_]; end
        end
        for (genvar b = 0; b < N; b = b + 1) begin : g_o
            assign s2_ra[b] = q_ra[b*RB +: RB]; assign s2_wa[b] = q_wa[b*RB +: RB];
            assign s2_wd[b] = (MUT == 1 && b == 5) ? wdat[b] : q_wd[b*32 +: 32];
        end
        assign s2_re = q_re; assign s2_we = q_we;
    end
    // ---- banks: BREG next to the macro, macro, read register next to the macro.  Instance path u_g.g_bank[b].u_b.g_m11n.u_m
    wire [31:0] b_q [0:N-1];
    for (genvar b = 0; b < N; b = b + 1) begin : g_bank
        reg q_re, q_we; reg [RB-1:0] q_ra, q_wa; reg [31:0] q_wd; reg [31:0] q_rd;
        wire [31:0] b_rd;
        // no reset: the uncut bank takes every op issued before a reset edge, so the delayed op must land too
        always @(posedge clk) begin
            q_re <= (MUT == 9 && b == 11) ? s1_re[b] : s2_re[b]; q_ra <= (MUT == 9 && b == 11) ? s1_ra[b] : s2_ra[b];
            q_we <= s2_we[b]; q_wa <= s2_wa[b]; q_wd <= s2_wd[b]; q_rd <= b_rd;
        end
        ot_hgi_su_lbank_n32 #(.RB(RB), .MACRO(1), .LAT(0)) u_b (.clk(clk), .re(q_re), .ra(q_ra), .rd(b_rd),
            .we(q_we), .wa(q_wa), .wd(q_wd));
        assign b_q[b] = (MUT == 5 && b == 9) ? b_rd : q_rd;
    end
    // ---- g_hc (hub): kept copy of the 16 bank read words, then the lane network, then q_out
    wire [N*32-1:0] hc;
    if (1) begin : g_hc
        (* keep *) reg [N*32-1:0] q_rd;
        integer b_;
        always @(posedge clk) for (b_ = 0; b_ < N; b_ = b_ + 1) q_rd[32*b_ +: 32] <= b_q[b_];
        assign hc = q_rd;
    end
    // lane selects: the lgroup2_lf lb_q (holds while the lane is idle), lb_q2 (lb_d2), then 3 more delays + q_bs (the last is the kept one-hot)
    reg [LN-1:0] lb_q [0:N-1]; reg [LN-1:0] lb_d2 [0:N-1]; reg [LN-1:0] lb_d3 [0:N-1]; reg [LN-1:0] lb_d4 [0:N-1]; reg [LN-1:0] lb_d5 [0:N-1];
    integer l_;
    always @(posedge clk) begin
        for (l_ = 0; l_ < N; l_ = l_ + 1) begin
            if (rr[l_]) lb_q[l_] <= lbk[l_];
            lb_d2[l_] <= lb_q[l_]; lb_d3[l_] <= lb_d2[l_]; lb_d4[l_] <= lb_d3[l_]; lb_d5[l_] <= lb_d4[l_];
        end
    end
    (* keep *) reg [N*32-1:0] q_out;
    for (genvar l = 0; l < N; l = l + 1) begin : g_lane
        // one bit per bank; a bank that is not a candidate of this lane reads 0 (lgroup2_lf: dv = 0)
        (* keep *) reg [N-1:0] q_bs;
        wire [LN-1:0] sel_n = (MUT == 2) ? lb_d4[l] : lb_d5[l];
        reg [N-1:0] bs_n;
        always @* begin : bsn
            integer b_;
            for (b_ = 0; b_ < N; b_ = b_ + 1) bs_n[b_] = (sel_n == LN'(b_)) && is_cand(l, b_);
        end
        always @(posedge clk) q_bs <= bs_n;
        reg [31:0] w;
        always @* begin : wm
            integer b_;
            w = 32'd0;
            for (b_ = 0; b_ < N; b_ = b_ + 1) w = w | ({32{q_bs[b_]}} & hc[32*b_ +: 32]);
        end
        always @(posedge clk) q_out[32*l +: 32] <= w;
    end
    assign rd = q_out;
    // ---- fail-closed checks: the lgroup2_lf FREG terms, same edges; br_q = S1 read row
    reg [N-1:0] rq_q, lok_q; reg [RB-1:0] lr_q [0:N-1]; reg wcoll_q;
    integer c_;
    always @(posedge clk) begin
        rq_q <= rq; lok_q <= lok; wcoll_q <= |i_cb;
        for (c_ = 0; c_ < N; c_ = c_ + 1) lr_q[c_] <= lrw[c_];
    end
    wire [N+N:0] fterm;
    for (genvar b = 0; b < N; b = b + 1) begin : g_fb
        reg bad;
        always @* begin : fbc
            integer i_;
            bad = 1'b0;
            for (i_ = 0; i_ < N; i_ = i_ + 1) if (rq_q[i_] && lb_q[i_] == LN'(b) && lr_q[i_] != s1_ra[b]) bad = 1'b1;
        end
        assign fterm[b] = bad;
        assign fterm[N + b] = rq_q[b] && !lok_q[b];
    end
    assign fterm[2*N] = wcoll_q;
    reg [N+N:0] fq;
    always @(posedge clk) fq <= fterm;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else if ((MUT == 4) ? (|fterm) : (|fq)) flt <= 1'b1;
    end
endmodule
`default_nettype wire

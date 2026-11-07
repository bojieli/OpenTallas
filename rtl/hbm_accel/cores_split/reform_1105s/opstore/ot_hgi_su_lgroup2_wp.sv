// HBM-FORM-SPLIT-14-OPSB 11-06: write-pipelined, placement-local form of the ot_hgi_su_lgroup2_lf instance in
// ot_hgi_sfu_opsb_output (N 16, M 16, LWB 15, AW 24, NLW 16, NS 2, MACRO 1, BREG 1, FREG 1, RREG 2, OT_OPSB_N32; no lane
// reads, no stage writes, no STREAM landing: the opsb_output instance ties them off).  Opt-in: opsb_output uses it only
// under `define OT_OPSB_WP (ot_hgi_sfu_opsb_tiles.sv); every other text is unchanged.
// Cause (vD/vE routed, TT -310/-308): the lane-write decode q_la -> one-hot priority select -> 16 bank write regs ran in
// ONE cycle across the 760 um tile (16-19 cells ~610 ps + 336-398 ps wire), and the bank-local read registers sat at
// the sr_d face, 300-600 um from their SRAM (rd_out -> g_rq.q 3 cells, ~300 ps wire).  Global routing detour is small
// (routed / HPWL 1.025), so the fix is in the structure, not the router.
// Form (all ops move WP edges together, so the order of reads and writes on every bank is kept):
//   WP = 2: stage W1 registers the decoded write record (bank one-hot per lane, rows, data, the pairwise collision term,
//           the bad-lane term) and the sector-read request; WP = 1: no W1 (decode after the column copy).
//   g_col[c] (4 kept copies, one per 4-bank column) registers the record for its column: the haul to a column is a
//           register-to-register wire with no logic.  Each bank's select logic reads only its column's copy.
//   g_bank[b]: bank input regs (q_re/q_ra/q_we/q_wa/q_wd) and the bank read register q_rd, all next to the macro
//           (kit guide box per bank, gen_core_kit_hbm.py --reg-guide-boxes); macro instance path unchanged
//           (u_g.g_bank[b].u_b.g_m11n.u_m, the plan core_macros KNOWN rects).
//   g_fq: a kept copy of the 16 bank read words at the sr_d face (register-to-register haul), then the 16:1 sector
//           rotate into the face register; the select is delayed with it (same latency as RREG 2: sr_d_q).
//   g_fc: control copy (sector-read request, lane-write valid and the collision terms) for the fault and the response
//           valid / select registers, at the flt / sr_* face.
// Latency vs part 41 (RREG 0): sr_d / sr_rv + (2 + WP) edges; flt + WP edges.  rd is unused in opsb_output (not built).
// MUT (bench mutants only, default 0): 1 bank 5 write data bypasses its column copy; 2 sr_rv one edge early; 3 g_fq
// select not delayed; 4 flt one edge early; 5 bank 9 read word bypasses q_rd; 6 lane pair (0, 5) collision dropped (lane 0 is the only lane with any bank, so only (0, k) pairs collide with legal lanes).
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_su_lgroup2_wp #(
    parameter integer WP = 1,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    sr_v,
    input  wire [29:0]   sr_addr,
    output wire [511:0]  sr_d,
    output wire [1:0]    sr_rv,
    input  wire [15:0]   lw,
    input  wire [383:0]  lwa,
    input  wire [511:0]  lwd,
    output reg           flt
);
    localparam integer N = 16, LN = 4, RB = 11, LWB = 15, AW = 24, NS = 2, NP = 120;
    // lane fields of the write record
    wire [LN-1:0] i_bk [0:N-1]; wire [RB-1:0] i_rw [0:N-1];
    for (genvar g = 0; g < N; g = g + 1) begin : g_lf
        assign i_bk[g] = lwa[g*AW +: LN]; assign i_rw[g] = lwa[g*AW + LN +: RB];
    end
    // pairwise collision term of lanes i < j (same bank, different rows) and the bad-lane term (lane l > 0 off its
    // only candidate bank l: NROT = N / M = 1); same function as lw_cb / lw_bad of ot_hgi_su_lgroup2_lf, ORed over banks
    function automatic integer pidx(input integer i, input integer j);   // i < j
        pidx = i * N - (i * (i + 1)) / 2 + (j - i - 1);
    endfunction
    wire [NP-1:0] i_ne; wire [N-1:0] i_bad;
    for (genvar gi = 0; gi < N; gi = gi + 1) begin : g_pi
        assign i_bad[gi] = lw[gi] && (gi != 0) && (i_bk[gi] != LN'(gi));
        for (genvar gj = gi + 1; gj < N; gj = gj + 1) begin : g_pj
            assign i_ne[pidx(gi, gj)] = (i_bk[gi] == i_bk[gj]) && (i_rw[gi] != i_rw[gj]);
        end
    end
    // ---- stage W1 (WP = 2): the decoded write record + the sector-read request, one register stage
    wire [N-1:0] a_lw; wire [N*N-1:0] a_oh; wire [N*LN-1:0] a_bk; wire [N*RB-1:0] a_rw; wire [511:0] a_d;
    wire [NP-1:0] a_ne; wire [N-1:0] a_bad; wire [1:0] a_sv; wire [29:0] a_sa;
    wire [N*N-1:0] i_oh; wire [N*LN-1:0] i_bkv; wire [N*RB-1:0] i_rwv;
    for (genvar g = 0; g < N; g = g + 1) begin : g_iv
        for (genvar gb = 0; gb < N; gb = gb + 1) begin : g_ib assign i_oh[g*N + gb] = (i_bk[g] == LN'(gb)); end
        assign i_bkv[g*LN +: LN] = i_bk[g]; assign i_rwv[g*RB +: RB] = i_rw[g];
    end
    if (WP >= 2) begin : g_w1
        (* keep *) reg [N-1:0] q_lw; (* keep *) reg [N*N-1:0] q_oh; (* keep *) reg [N*RB-1:0] q_rw; (* keep *) reg [511:0] q_d;
        (* keep *) reg [NP-1:0] q_ne; (* keep *) reg [N-1:0] q_bad; (* keep *) reg [1:0] q_sv; (* keep *) reg [29:0] q_sa;
        always @(posedge clk) begin
            q_lw <= lw; q_oh <= i_oh; q_rw <= i_rwv; q_d <= lwd; q_ne <= i_ne; q_bad <= i_bad; q_sv <= sr_v; q_sa <= sr_addr;
        end
        assign a_lw = q_lw; assign a_oh = q_oh; assign a_bk = {N*LN{1'b0}}; assign a_rw = q_rw; assign a_d = q_d;
        assign a_ne = q_ne; assign a_bad = q_bad; assign a_sv = q_sv; assign a_sa = q_sa;
    end else begin : g_w0
        assign a_lw = lw; assign a_oh = {N*N{1'b0}}; assign a_bk = i_bkv; assign a_rw = i_rwv; assign a_d = lwd;
        assign a_ne = {NP{1'b0}}; assign a_bad = {N{1'b0}}; assign a_sv = sr_v; assign a_sa = sr_addr;
    end
    // ---- g_col[c]: per-column kept copy (register-to-register haul, no logic); WP 2 copies the column's 4 one-hot
    // bank bits per lane, WP 1 the raw 4-bit lane bank (decoded after the copy)
    wire [N-1:0] c_lw [0:3]; wire [N*4-1:0] c_x [0:3]; wire [N*RB-1:0] c_rw [0:3]; wire [511:0] c_d [0:3];
    wire [1:0] c_sv [0:3]; wire [29:0] c_sa [0:3];
    for (genvar gc = 0; gc < 4; gc = gc + 1) begin : g_col
        wire [N*4-1:0] x_in;
        for (genvar g = 0; g < N; g = g + 1) begin : g_x
            if (WP >= 2) begin : g_o assign x_in[g*4 +: 4] = a_oh[g*N + gc*4 +: 4]; end
            else begin : g_b assign x_in[g*4 +: 4] = a_bk[g*LN +: LN]; end
        end
        (* keep *) reg [N-1:0] q_lw; (* keep *) reg [N*4-1:0] q_x; (* keep *) reg [N*RB-1:0] q_rw; (* keep *) reg [511:0] q_d;
        (* keep *) reg [1:0] q_sv; (* keep *) reg [29:0] q_sa;
        always @(posedge clk) begin q_lw <= a_lw; q_x <= x_in; q_rw <= a_rw; q_d <= a_d; q_sv <= a_sv; q_sa <= a_sa; end
        assign c_lw[gc] = q_lw; assign c_x[gc] = q_x; assign c_rw[gc] = q_rw; assign c_d[gc] = q_d;
        assign c_sv[gc] = q_sv; assign c_sa[gc] = q_sa;
    end
    // ---- banks: select logic on the column copy, bank input regs, macro, bank read register
    wire [31:0] b_q [0:N-1];
    genvar gb;
    for (gb = 0; gb < N; gb = gb + 1) begin : g_bank
        localparam integer C = gb / 4, J = gb % 4;
        // lane writes: the HIGHEST lane whose bank is gb wins (lgroup2_lf g_lws)
        wire [N-1:0] h, oh;
        for (genvar gl = 0; gl < N; gl = gl + 1) begin : g_h
            if (WP >= 2) begin : g_o assign h[gl] = c_lw[C][gl] && c_x[C][gl*4 + J]; end
            else begin : g_b assign h[gl] = c_lw[C][gl] && (c_x[C][gl*4 +: 4] == LN'(gb)); end
            if (gl == N - 1) begin : g_ot assign oh[gl] = h[gl]; end
            else begin : g_on assign oh[gl] = h[gl] && !(|h[N-1:gl+1]); end
        end
        reg [RB-1:0] wrow; reg [31:0] wdat;
        always @* begin : wao
            integer i_;
            wrow = {RB{1'b0}}; wdat = 32'd0;
            for (i_ = 0; i_ < N; i_ = i_ + 1) begin
                wrow = wrow | ({RB{oh[i_]}} & c_rw[C][i_*RB +: RB]);
                wdat = wdat | ({32{oh[i_]}} & ((MUT == 1 && gb == 5) ? a_d[32*i_ +: 32] : c_d[C][32*i_ +: 32]));
            end
        end
        // sector reads: bank gb takes word off = gb - addr[LN-1:0] (off < 8) of each lane; the HIGHEST lane wins (g_srs)
        wire [NS-1:0] sh, soh; wire [RB-1:0] srw [0:NS-1];
        for (genvar gs = 0; gs < NS; gs = gs + 1) begin : g_s
            wire [LWB-1:0] a = c_sa[C][gs*LWB +: LWB];
            wire [LN-1:0] off = LN'(gb) - a[LN-1:0];
            assign sh[gs] = c_sv[C][gs] && off < LN'(8);
            assign srw[gs] = a[LWB-1:LN] + RB'(LN'(gb) < a[LN-1:0]);
            if (gs == NS - 1) begin : g_ot assign soh[gs] = sh[gs]; end
            else begin : g_on assign soh[gs] = sh[gs] && !(|sh[NS-1:gs+1]); end
        end
        reg [RB-1:0] rrow;
        always @* begin : rao
            integer i_;
            rrow = {RB{1'b0}};
            for (i_ = 0; i_ < NS; i_ = i_ + 1) rrow = rrow | ({RB{soh[i_]}} & srw[i_]);
        end
        // BREG: no reset (the uncut bank takes every op issued before a reset edge, so the delayed op must land too)
        reg q_re, q_we; reg [RB-1:0] q_ra, q_wa; reg [31:0] q_wd;
        always @(posedge clk) begin q_re <= |sh; q_ra <= rrow; q_we <= |h; q_wa <= wrow; q_wd <= wdat; end
        wire [31:0] b_rd;
        ot_hgi_su_lbank_n32 #(.RB(RB), .MACRO(1), .LAT(0)) u_b (.clk(clk), .re(q_re), .ra(q_ra), .rd(b_rd),
            .we(q_we), .wa(q_wa), .wd(q_wd));
        // bank read register next to the macro (RREG >= 1)
        reg [31:0] q_rd;
        always @(posedge clk) q_rd <= b_rd;
        assign b_q[gb] = (MUT == 5 && gb == 9) ? b_rd : q_rd;
    end
    // ---- g_fc: control copy at the flt / sr_* face: faults, response valid, sector selects
    reg [NS-1:0] srv1, srv2, srv_r1, srv_r2;
    reg [LN-1:0] sr_lo [0:NS-1]; reg [LN-1:0] sr_lo2 [0:NS-1]; reg [LN-1:0] sr_s_q [0:NS-1]; reg [LN-1:0] sr_s_q2 [0:NS-1];
    reg srv_q, wcoll_q; reg [1:0] fq;
    if (1) begin : g_fc
        (* keep *) reg [1:0] q_sv; (* keep *) reg [29:0] q_sa; (* keep *) reg [N-1:0] q_lw;
        wire [NP-1:0] ne; wire [N-1:0] bad;
        if (WP >= 2) begin : g_w2
            (* keep *) reg [NP-1:0] q_ne; (* keep *) reg [N-1:0] q_bad;
            always @(posedge clk) begin q_sv <= a_sv; q_sa <= a_sa; q_lw <= a_lw; q_ne <= a_ne; q_bad <= a_bad; end
            assign ne = q_ne; assign bad = q_bad;
        end else begin : g_w1c
            // WP 1: the copy holds the raw lane banks and rows; the pair / bad terms are computed after it
            (* keep *) reg [N*LN-1:0] q_bk; (* keep *) reg [N*RB-1:0] q_rw;
            always @(posedge clk) begin q_sv <= a_sv; q_sa <= a_sa; q_lw <= a_lw; q_bk <= a_bk; q_rw <= a_rw; end
            for (genvar gi = 0; gi < N; gi = gi + 1) begin : g_pi
                assign bad[gi] = q_lw[gi] && (gi != 0) && (q_bk[gi*LN +: LN] != LN'(gi));
                for (genvar gj = gi + 1; gj < N; gj = gj + 1) begin : g_pj
                    assign ne[pidx(gi, gj)] = (q_bk[gi*LN +: LN] == q_bk[gj*LN +: LN]) && (q_rw[gi*RB +: RB] != q_rw[gj*RB +: RB]);
                end
            end
        end
        // wcoll: any bad lane, or two writing lanes on one bank with different rows (= |lw_cb of lgroup2_lf)
        reg wc;
        always @* begin : wcc
            integer i_, j_;
            wc = |bad;
            for (i_ = 0; i_ < N; i_ = i_ + 1)
                for (j_ = i_ + 1; j_ < N; j_ = j_ + 1)
                    if (q_lw[i_] && q_lw[j_] && ne[pidx(i_, j_)] && !(MUT == 6 && i_ == 0 && j_ == 5)) wc = 1'b1;
        end
        // src: two sector lanes hit one bank with different rows (= |sr_cb of lgroup2_lf)
        reg sc;
        always @* begin : scc
            integer b_, s_; reg [LN-1:0] off; reg [RB-1:0] rw0, rw1; reg h0, h1;
            sc = 1'b0;
            for (b_ = 0; b_ < N; b_ = b_ + 1) begin
                off = LN'(b_) - q_sa[LN-1:0];         h0 = q_sv[0] && off < LN'(8);
                rw0 = q_sa[LWB-1:LN] + RB'(LN'(b_) < q_sa[LN-1:0]);
                off = LN'(b_) - q_sa[LWB +: LN];      h1 = q_sv[1] && off < LN'(8);
                rw1 = q_sa[LWB+LN +: RB] + RB'(LN'(b_) < q_sa[LWB +: LN]);
                if (h0 && h1 && rw0 != rw1) sc = 1'b1;
            end
        end
        integer s_;
        always @(posedge clk) begin
            srv_q <= sc; wcoll_q <= wc; fq <= {wcoll_q, srv_q};
            for (s_ = 0; s_ < NS; s_ = s_ + 1) begin
                if (q_sv[s_]) sr_lo[s_] <= q_sa[s_*LWB +: LN];
                sr_lo2[s_] <= sr_lo[s_]; sr_s_q[s_] <= sr_lo2[s_]; sr_s_q2[s_] <= sr_s_q[s_];
            end
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) srv1 <= {NS{1'b0}}; else srv1 <= q_sv;
    end
    always @(posedge clk) srv2 <= srv1;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin srv_r1 <= {NS{1'b0}}; srv_r2 <= {NS{1'b0}}; end
        else begin srv_r1 <= srv2; srv_r2 <= srv_r1; end
    assign sr_rv = (MUT == 2) ? srv_r1 : srv_r2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else if ((MUT == 4) ? (srv_q || wcoll_q) : (|fq)) flt <= 1'b1;
    end
    // ---- g_fq: kept copy of the 16 bank read words at the sr_d face, then the sector rotate
    if (1) begin : g_fq
        (* keep *) reg [N*32-1:0] q_rd;
        integer b_;
        always @(posedge clk) for (b_ = 0; b_ < N; b_ = b_ + 1) q_rd[32*b_ +: 32] <= b_q[b_];
        for (genvar gk = 0; gk < NS; gk = gk + 1) begin : g_srl
            wire [LN-1:0] sel = (MUT == 3) ? sr_s_q[gk] : sr_s_q2[gk];
            for (genvar gj = 0; gj < 8; gj = gj + 1) begin : g_sr
                wire [LN-1:0] bj = sel + gj;
                assign sr_d[256*gk + 32*gj +: 32] = q_rd[32*bj +: 32];
            end
        end
    end
endmodule
`default_nettype wire

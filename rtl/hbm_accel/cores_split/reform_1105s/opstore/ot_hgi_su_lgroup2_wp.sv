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
//   WP = 3 (vH, 11-06 vG routed: q_la (W / E face) -> lane decode -> W1 -238 ps, smell 1+7): stage W0 (g_w0r, kept)
//           relays lw / lane bank+row fields / sr_* into the centre box next to W1, so the face -> centre haul is
//           register-to-register; W1 then also resolves the per-bank lane priority (q_oh holds the WINNING lane one-hot,
//           bank side = one 16:1 AND-OR, COL -> BANK was 12 levels -238/-36 ps); lwd takes two kept delay registers
//           (g_wd, unboxed: the placer keeps them on the E-face -> column path).
//           W1 also registers the pair collision term AND both lanes writing, so the g_fc fault is one OR tree
//           (vF g_fc wcoll -159 ps / vG -38 ps).
//   g_fq select (all WP, smell 5: one select bit drove ~256 mux inputs through 6 buffers, FQ -> sr_d -59 ps): a kept
//           one-hot select register per output word (16 x 16), fanout 32 each.
// Latency vs part 41 (RREG 0): sr_d / sr_rv + (2 + WP) edges; flt + WP edges.  rd is unused in opsb_output (not built).
// MUT (bench mutants only, default 0): 1 bank 5 write data bypasses its column copy; 2 sr_rv one edge early; 3 g_fq
// select not delayed; 4 flt one edge early; 5 bank 9 read word bypasses q_rd; 6 lane pair (0, 5) collision dropped (lane 0 is the only lane with any bank, so only (0, k) pairs collide with legal lanes).
// 7 (WP 3 only) bank 3 W1 winner = the LOWEST writing lane.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_su_lgroup2_wp #(
    parameter integer WP = 1,
    parameter integer MUT = 0,
    parameter integer PRESELECT = 0,
    parameter integer LOCAL_COL = -1,
    parameter integer LOCAL_MUT = 0
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
    // ---- stage W0 (WP >= 3): kept relay of the lane-write valid, bank / row fields and the sector-read request
    wire [N-1:0] r_lw; wire [N*(LN+RB)-1:0] r_la; wire [1:0] r_sv; wire [29:0] r_sa;
    wire [N*(LN+RB)-1:0] i_la;
    for (genvar g = 0; g < N; g = g + 1) begin : g_la assign i_la[g*(LN+RB) +: LN+RB] = lwa[g*AW +: LN+RB]; end
    if (WP >= 3) begin : g_w0r
        (* keep *) reg [N-1:0] q_lw; (* keep *) reg [N*(LN+RB)-1:0] q_la; (* keep *) reg [1:0] q_sv; (* keep *) reg [29:0] q_sa;
        always @(posedge clk) begin q_lw <= lw; q_la <= i_la; q_sv <= sr_v; q_sa <= sr_addr; end
        assign r_lw = q_lw; assign r_la = q_la; assign r_sv = q_sv; assign r_sa = q_sa;
    end else begin : g_w0n
        assign r_lw = lw; assign r_la = i_la; assign r_sv = sr_v; assign r_sa = sr_addr;
    end
    wire [LN-1:0] i_bk [0:N-1]; wire [RB-1:0] i_rw [0:N-1];
    for (genvar g = 0; g < N; g = g + 1) begin : g_lf
        assign i_bk[g] = r_la[g*(LN+RB) +: LN]; assign i_rw[g] = r_la[g*(LN+RB) + LN +: RB];
    end
    // pairwise collision term of lanes i < j (same bank, different rows) and the bad-lane term (lane l > 0 off its
    // only candidate bank l: NROT = N / M = 1); same function as lw_cb / lw_bad of ot_hgi_su_lgroup2_lf, ORed over banks
    function automatic integer pidx(input integer i, input integer j);   // i < j
        pidx = i * N - (i * (i + 1)) / 2 + (j - i - 1);
    endfunction
    wire [NP-1:0] i_ne; wire [NP-1:0] i_nel; wire [N-1:0] i_bad;   // i_nel: pair term AND both lanes writing (WP 3)
    for (genvar gi = 0; gi < N; gi = gi + 1) begin : g_pi
        assign i_bad[gi] = r_lw[gi] && (gi != 0) && (i_bk[gi] != LN'(gi));
        for (genvar gj = gi + 1; gj < N; gj = gj + 1) begin : g_pj
            assign i_ne[pidx(gi, gj)] = (i_bk[gi] == i_bk[gj]) && (i_rw[gi] != i_rw[gj]);
            assign i_nel[pidx(gi, gj)] = r_lw[gi] && r_lw[gj] && i_ne[pidx(gi, gj)];
        end
    end
    // ---- stage W1 (WP = 2): the decoded write record + the sector-read request, one register stage
    wire [N-1:0] a_lw; wire [N*N-1:0] a_oh; wire [N*LN-1:0] a_bk; wire [N*RB-1:0] a_rw; wire [511:0] a_d;
    wire [NP-1:0] a_ne; wire [N-1:0] a_bad; wire [1:0] a_sv; wire [29:0] a_sa;
    wire [N*RB-1:0] a_rw_hi;
    wire [511:0] d_wd_hi;
    wire [511:0] d_wd;   // lwd after the two g_wd delay registers (WP >= 3)
    wire [N*N-1:0] i_oh; wire [N*N-1:0] i_win; wire [N*LN-1:0] i_bkv; wire [N*RB-1:0] i_rwv;
    for (genvar g = 0; g < N; g = g + 1) begin : g_iv
        for (genvar gb = 0; gb < N; gb = gb + 1) begin : g_ib assign i_oh[g*N + gb] = (i_bk[g] == LN'(gb)); end
        assign i_bkv[g*LN +: LN] = i_bk[g]; assign i_rwv[g*RB +: RB] = i_rw[g];
    end
    // WP >= 3: winning lane per bank (the HIGHEST writing lane on the bank), same layout as i_oh (lane * N + bank)
    for (genvar gb = 0; gb < N; gb = gb + 1) begin : g_wn
        wire [N-1:0] hb;
        for (genvar g = 0; g < N; g = g + 1) begin : g_h assign hb[g] = r_lw[g] && i_oh[g*N + gb]; end
        for (genvar g = 0; g < N; g = g + 1) begin : g_w
            if (MUT == 7 && gb == 3 && g == 0) begin : g_m0 assign i_win[g*N + gb] = hb[g]; end
            else if (MUT == 7 && gb == 3) begin : g_m assign i_win[g*N + gb] = hb[g] && !(|hb[g-1:0]); end
            else if (g == N - 1) begin : g_t assign i_win[g*N + gb] = hb[g]; end
            else begin : g_n assign i_win[g*N + gb] = hb[g] && !(|hb[N-1:g+1]); end
        end
    end
    if (WP >= 2) begin : g_w1
        (* keep *) reg [N-1:0] q_lw; (* keep *) reg [N*N-1:0] q_oh; (* keep *) reg [N*RB-1:0] q_rw;
        (* keep *) reg [NP-1:0] q_ne; (* keep *) reg [N-1:0] q_bad; (* keep *) reg [1:0] q_sv; (* keep *) reg [29:0] q_sa;
        always @(posedge clk) begin
            q_lw <= r_lw; q_oh <= (WP >= 3) ? i_win : i_oh; q_rw <= i_rwv; q_ne <= (WP >= 3) ? i_nel : i_ne; q_bad <= i_bad; q_sv <= r_sv; q_sa <= r_sa;
        end
        assign a_lw = q_lw; assign a_oh = q_oh; assign a_bk = {N*LN{1'b0}}; assign a_rw = q_rw;
        assign a_ne = q_ne; assign a_bad = q_bad; assign a_sv = q_sv; assign a_sa = q_sa;
        if (WP >= 3) begin : g_d3 assign a_d = d_wd; end
        else begin : g_d2 (* keep *) reg [511:0] q_d; always @(posedge clk) q_d <= lwd; assign a_d = q_d; end
    end else begin : g_w0
        assign a_lw = lw; assign a_oh = {N*N{1'b0}}; assign a_bk = i_bkv; assign a_rw = i_rwv; assign a_d = lwd;
        assign a_ne = {NP{1'b0}}; assign a_bad = {N{1'b0}}; assign a_sv = sr_v; assign a_sa = sr_addr;
    end
    // lwd delay for WP >= 3 (two kept registers, outside the W0 / W1 boxes)
    if (WP >= 3) begin : g_wd
        (* keep *) reg [511:0] q_d0; (* keep *) reg [511:0] q_d1;
        always @(posedge clk) begin q_d0 <= lwd; q_d1 <= q_d0; end
        assign d_wd = q_d1;
        if (PRESELECT) begin : g_hi
            (* keep *) reg [511:0] q_d1;
            always @(posedge clk) q_d1 <= q_d0;
            assign d_wd_hi = q_d1;
        end else begin : g_same assign d_wd_hi = q_d1; end
    end else begin : g_wdn
        assign d_wd = {512{1'b0}}; assign d_wd_hi = {512{1'b0}};
    end
    // Same-edge row-record copy limits each row bit to eight bank selectors. Disabled path is identical.
    if (PRESELECT && (LOCAL_COL >= 0 || LOCAL_COL == -2) && WP >= 3) begin : g_rowhi
        (* keep *) reg [N*RB-1:0] q_rw;
        always @(posedge clk) q_rw <= i_rwv;
        assign a_rw_hi=q_rw;
    end else begin : g_rowsame assign a_rw_hi=a_rw; end
    // PRESELECT (WP3): retime the pure winning-lane write mux before the column register.
    // Previously every 512-bit word bus crossed the block before selecting 32 bits per bank.
    // Now each column carries only four selected {we,row,data} records. Edge dates and faults are unchanged.
    // Two equal WD copies feed banks 0..7 / 8..15 in the central selection region.
    wire [N-1:0] pre_we;
    wire [RB-1:0] pre_wa [0:N-1]; wire [31:0] pre_wd [0:N-1];
    for(genvar psb=0;psb<N;psb=psb+1) begin : g_preselect
        wire [N-1:0] h;
        wire [511:0] data_in = psb < 8 ? d_wd : d_wd_hi;
        wire [N*RB-1:0] rows_in = psb < 8 ? a_rw : a_rw_hi;
        for(genvar psl=0;psl<N;psl=psl+1) begin : g_h
            assign h[psl] = a_lw[psl] && a_oh[psl*N+psb];
        end
        reg [RB-1:0] row; reg [31:0] data;
        always @* begin : choose
            integer j;
            row=0;data=0;
            for(j=0;j<N;j=j+1) begin
                row=row|({RB{h[j]}}&rows_in[j*RB+:RB]);
                data=data|({32{h[j]}}&data_in[j*32+:32]);
            end
        end
        assign pre_we[psb]=|h;assign pre_wa[psb]=row;assign pre_wd[psb]=data;
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
        if(PRESELECT) begin : g_selected
            wire [4*RB-1:0] rows; wire [127:0] words;
            for(genvar k=0;k<4;k=k+1) begin : pack
                assign rows[k*RB+:RB]=pre_wa[4*gc+k];
                assign words[k*32+:32]=pre_wd[4*gc+k];
            end
            if (WP >= 3 && (LOCAL_COL == gc || LOCAL_COL == -2)) begin : g_local
                wire [3:0] we; wire [4*RB-1:0] wa; wire [127:0] wd;
                for(genvar j=0;j<4;j=j+1) begin : g_bank
                    wire [N-1:0] wins;
                    for(genvar lane=0;lane<N;lane=lane+1) begin : g_wins
                        // WP3 i_win already includes the lane valid before its W1 register.
                        assign wins[lane]=a_oh[lane*N+gc*4+j];
                    end
                    (* keep_hierarchy = "yes" *) ot_hgi_opsb_selpipe #(.N(N),.RB(RB),.MUT((gc==3 && j==0)?LOCAL_MUT:0)) u_pipe(
                        .clk(clk),.sel(wins),.rows(gc<2?a_rw:a_rw_hi),.data(gc<2?d_wd:d_wd_hi),
                        .we(we[j]),.wa(wa[j*RB+:RB]),.wd(wd[j*32+:32]));
                end
                always @* begin q_lw={{(N-4){1'b0}},we};q_x=0;q_rw={{((N-4)*RB){1'b0}},wa};q_d={384'd0,wd};end
                always @(posedge clk) begin q_sv<=a_sv;q_sa<=a_sa;end
            end else begin : g_original
            always @(posedge clk) begin
                q_lw <= {{(N-4){1'b0}},pre_we[gc*4+:4]};q_x<=0;
                q_rw <= {{((N-4)*RB){1'b0}},rows};q_d <= {384'd0,words};
                q_sv<=a_sv;q_sa<=a_sa;
            end
            end
        end else begin : g_full
            always @(posedge clk) begin q_lw <= a_lw; q_x <= x_in; q_rw <= a_rw; q_d <= a_d; q_sv <= a_sv; q_sa <= a_sa; end
        end
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
            if (gl == N - 1 || WP >= 3) begin : g_ot assign oh[gl] = h[gl]; end   // WP 3: the copy holds winners
            else begin : g_on assign oh[gl] = h[gl] && !(|h[N-1:gl+1]); end
        end
        reg [RB-1:0] wrow; reg [31:0] wdat;
        always @* begin : wao
            integer i_;
            wrow = {RB{1'b0}}; wdat = 32'd0;
            if(PRESELECT) begin
                wrow=c_rw[C][J*RB+:RB];
                wdat=(MUT==1 && gb==5)?pre_wd[gb]:c_d[C][J*32+:32];
            end else begin
                for (i_ = 0; i_ < N; i_ = i_ + 1) begin
                    wrow = wrow | ({RB{oh[i_]}} & c_rw[C][i_*RB +: RB]);
                    wdat = wdat | ({32{oh[i_]}} & ((MUT == 1 && gb == 5) ? a_d[32*i_ +: 32] : c_d[C][32*i_ +: 32]));
                end
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
        always @(posedge clk) begin q_re <= |sh; q_ra <= rrow; q_we <= PRESELECT?c_lw[C][J]:|h; q_wa <= wrow; q_wd <= wdat; end
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
    reg [LN-1:0] sr_lo [0:NS-1]; reg [LN-1:0] sr_lo2 [0:NS-1]; reg [LN-1:0] sr_s_q [0:NS-1];
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
                    if ((WP >= 3 || (q_lw[i_] && q_lw[j_])) && ne[pidx(i_, j_)] && !(MUT == 6 && i_ == 0 && j_ == 5)) wc = 1'b1;
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
                sr_lo2[s_] <= sr_lo[s_]; sr_s_q[s_] <= sr_lo2[s_];
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
        // kept one-hot word select per output word (= the bank sr_s_q2 + gj names), fanout 32 each
        for (genvar gk = 0; gk < NS; gk = gk + 1) begin : g_srl
            wire [LN-1:0] sel_n = (MUT == 3) ? sr_lo2[gk] : sr_s_q[gk];   // registered once more below (= sr_s_q2)
            for (genvar gj = 0; gj < 8; gj = gj + 1) begin : g_sr
                (* keep *) reg [N-1:0] q_bs;
                always @(posedge clk) q_bs <= N'(1) << (LN'(sel_n + gj));
                reg [31:0] w;
                always @* begin : wm
                    integer b2_;
                    w = 32'd0;
                    for (b2_ = 0; b2_ < N; b2_ = b2_ + 1) w = w | ({32{q_bs[b2_]}} & q_rd[32*b2_ +: 32]);
                end
                assign sr_d[256*gk + 32*gj +: 32] = w;
            end
        end
    end
endmodule

// LOCAL_COL: retain the select gates WITH their existing column register edge, not in a naked combinational fence.
// HBM-HARD-6 11-08 (PS2d): LOCAL_COL = -2 = every column local (each bank gets its own selpipe next to its macro;
// PS2c GRT-0116: 23844 overflow at the col-2 central select between banks 9/10, col 3 local showed none). Same edges.
// Select is an already-valid-qualified WP3 winner. Each select bit sees <=7 child logic legs.
(* keep_hierarchy = "yes" *)
module ot_hgi_opsb_selpipe #(parameter integer N=16,RB=11,MUT=0)(
 input wire clk,input wire [N-1:0] sel,input wire [N*RB-1:0] rows,input wire [N*32-1:0] data,
 output wire we,output wire [RB-1:0] wa,output wire [31:0] wd);
 (* keep *) reg q_we;always @(posedge clk) q_we<=|sel;assign we=q_we;
 for(genvar seg=0;seg<4;seg=seg+1)begin:g_data
  wire [N*8-1:0] v;
  for(genvar lane=0;lane<N;lane=lane+1)begin:g_in
   assign v[lane*8+:8]=data[((MUT!=0)?(lane^1):lane)*32+seg*8+:8];
  end
  (* keep_hierarchy = "yes" *) ot_hgi_opsb_selreg8 #(.N(N),.W(8)) u_slice(.clk(clk),.sel(sel),.data(v),.q(wd[seg*8+:8]));
 end
 for(genvar seg=0;seg<(RB+7)/8;seg=seg+1)begin:g_row
  localparam integer W=(RB-seg*8>=8)?8:RB-seg*8;
  wire [N*W-1:0] v;
  for(genvar lane=0;lane<N;lane=lane+1)begin:g_in assign v[lane*W+:W]=rows[lane*RB+seg*8+:W];end
  (* keep_hierarchy = "yes" *) ot_hgi_opsb_selreg8 #(.N(N),.W(W)) u_slice(.clk(clk),.sel(sel),.data(v),.q(wa[seg*8+:W]));
 end
endmodule
(* keep_hierarchy = "yes" *)
module ot_hgi_opsb_selreg8 #(parameter integer N=16,W=8)(
 input wire clk,input wire [N-1:0] sel,input wire [N*W-1:0] data,output wire [W-1:0] q);
 reg [W-1:0] v;integer i;
 always @*begin v=0;for(i=0;i<N;i=i+1)v=v|({W{sel[i]}}&data[i*W+:W]);end
 (* keep *)reg[W-1:0] q_data;always @(posedge clk)q_data<=v;assign q=q_data;
endmodule

`default_nettype wire

`timescale 1ps/1fs
// ---------------------------------------------------------------------------
// HA8 weight + KV prefetch stream of one die (rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv), 1.2 GHz successor
// (fmax closure, 2026-10-04).  Same ports, parameters, controllers (ot_hbm_r14_stream_pc per PC) and outputs on every
// cycle; only the bookkeeping is restructured, with zero added cycles:
//   * per-PC sector counts: the 64-bit landed / moved pair becomes pend = landed - moved (<= CRED, the credit bound)
//     and moved as (mw words, mr sectors within the word, 0 <= mr < SPW).  The window-room test
//     moved < (C + WINW) * SPW is exactly mw < C + WINW; it is evaluated as (mw < WINW) || (mw - WINW < C) with
//     qw = mw - WINW (mod 2^(CW+1), from reset -WINW) kept as its own register so the synchronised count C only meets
//     one compare;
//   * complete words: min over PCs of floor(moved / SPW) = min over PCs of mw (floor is monotone), so the 64-bit
//     divide by SPW disappears; the min is tracked incrementally (d = mw - min per PC, no 128-way compare tree) with
//     the original MINLAT = 2 latency;
//   * per-PC descriptor bookkeeping: left = SPW * cfg_words - posted is kept as a register (decremented with each
//     descriptor, re-derived on every cycle without one), so dv / dn need no 64-bit subtract and compare in series.
//     cfg_words is the host's per-run constant (written with reset, before go); the registered product is exact
//     from the second cycle after reset.
//   * statistics (st_rd / st_room_block / st_desc_gap / st_cycles) lag the original's by one cycle (registered
//     per-cycle counts); a_gray, st_words and fault are unchanged on every cycle.
// ---------------------------------------------------------------------------
module ot_hbmacc_qwen_wstream_f12 #(
    parameter integer ENABLE   = 0,
    parameter integer NSTK     = 4,
    parameter integer REF_MODE = 1,
    parameter integer CRED     = 32,
    parameter integer RL       = 23,
    parameter integer SPW      = 24,
    parameter integer WINW     = 160,
    parameter integer MINLAT   = 2,
    parameter integer CW       = 32
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    input  wire [CW-1:0]     cfg_words,
    input  wire [CW-1:0]     c_gray,
    output wire [CW-1:0]     a_gray,
    output wire              fault,
    output wire [CW-1:0]     st_cycles,
    output wire [CW-1:0]     st_rd,
    output wire [CW-1:0]     st_room_block,
    output wire [CW-1:0]     st_desc_gap,
    output wire [CW-1:0]     st_words
);
    localparam integer NPC = 32 * NSTK;
    localparam integer PB  = $clog2(CRED + 2);          // pend bits (landed - moved <= CRED)
    localparam integer RB  = $clog2(SPW);
    localparam [CW:0]  QW0 = {(CW+1){1'b0}} - (CW+1)'(WINW);   // qw at reset: 0 - WINW
    function automatic [CW-1:0] g2b(input [CW-1:0] g);
        integer i; begin g2b[CW-1] = g[CW-1]; for (i = CW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i]; end
    endfunction
    generate if (MINLAT != 2) begin : g_bad_minlat
        ot_hbmacc_qwen_wstream_f12_needs_MINLAT_2 u_trap ();
    end endgenerate
    generate if (ENABLE == 0) begin : g_off
        assign a_gray = 0; assign fault = 0; assign st_cycles = 0; assign st_rd = 0; assign st_room_block = 0;
        assign st_desc_gap = 0; assign st_words = 0;
    end else begin : g_on
        reg [CW-1:0] c_s1, c_s2;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin c_s1 <= 0; c_s2 <= 0; end else begin c_s1 <= c_gray; c_s2 <= c_s1; end
        // Gray -> binary as a (* keep *) log-depth suffix XOR (the same function as g2b)
        localparam integer GL = $clog2(CW);
        (* keep *) wire [CW-1:0] sx [0:GL];
        assign sx[0] = c_s2;
        genvar gl, gb;
        for (gl = 1; gl <= GL; gl = gl + 1) begin : g_lv
            for (gb = 0; gb < CW; gb = gb + 1) begin : g_b
                if (gb + (1 << (gl - 1)) < CW) begin : g_x
                    assign sx[gl][gb] = sx[gl-1][gb] ^ sx[gl-1][gb + (1 << (gl - 1))];
                end else begin : g_p
                    assign sx[gl][gb] = sx[gl-1][gb];
                end
            end
        end
        wire [CW-1:0] c_bin = sx[GL];
        reg  [63:0] sec_r;                                    // SPW * cfg_words (host constant)
        always @(posedge clk) sec_r <= 64'(cfg_words) * 64'(SPW);
        localparam integer PERIOD = REF_MODE ? 118 : 3808;
        wire [NPC-1:0] col_v, busy, pc_desc_r, pc_fault, row_req;
        wire [3*NPC-1:0] cred_ret;
        reg  [18:0] nrow [0:NPC-1];
        reg  [63:0] posted [0:NPC-1];
        reg  [63:0] left [0:NPC-1];                         // sec_r - posted
        reg  [NPC-1:0] lnz;                                 // left != 0  (= posted < SPW * cfg_words)
        reg  [NPC-1:0] lbig;                                // left >= 1024
        reg         going;
        reg         arb_fault;
        genvar s;
        for (s = 0; s < NPC; s = s + 1) begin : g_pc
            wire        dv = going && lnz[s] && pc_desc_r[s];
            wire [10:0] dn = lbig[s] ? 11'd1024 : 11'(left[s]);
            wire [63:0] l_dec, l_re, p_add;
            wire        c0, c1, c2;
            ot_hdc_kadd #(.W(64), .K(1)) u_ldec (.a(left[s]), .b(~{53'd0, dn}), .cin(1'b1), .s(l_dec), .cout(c0));
            ot_hdc_kadd #(.W(64), .K(1)) u_lre  (.a(sec_r), .b(~posted[s]), .cin(1'b1), .s(l_re), .cout(c1));
            ot_hdc_kadd #(.W(64), .K(1)) u_padd (.a(posted[s]), .b({53'd0, dn}), .cin(1'b0), .s(p_add), .cout(c2));
            wire [63:0] left_nx = dv ? l_dec : l_re;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin nrow[s] <= 0; posted[s] <= 0; left[s] <= 0; lnz[s] <= 1'b0; lbig[s] <= 1'b0; end
                else begin
                    if (dv) begin nrow[s] <= nrow[s] + 1'b1; posted[s] <= p_add; end
                    left[s] <= left_nx;
                    lnz[s]  <= |left_nx;
                    lbig[s] <= |left_nx[63:10];
                end
            ot_hbm_r14_stream_pc #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(s % 32), .CRED(CRED),
                .REF_PHASE((((s / 32) * 29) + ((s % 32) * PERIOD) / 32) % PERIOD)) u_pc (
                .clk(clk), .rst_n(rst_n), .desc_v(dv), .desc_r(pc_desc_r[s]), .desc_row(nrow[s]), .desc_n(dn),
                .go(going), .next_posted(1'b1),
                .row_v(row_req[s]), .row_prio(), .row_gnt(1'b1), .row_op(), .row_bank(), .row_row(),
                .col_v(col_v[s]), .col_bank(), .col_col(),
                .cred_ret(cred_ret[s*3 +: 3]), .busy(busy[s]), .ref_fault(pc_fault[s]));
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin going <= 0; arb_fault <= 0; end
            else begin
                going <= go;
                for (integer c = 0; c < NPC / 2; c = c + 1) if (row_req[2*c] && row_req[2*c+1]) arb_fault <= 1'b1;
            end
        // ---- per PC: return pipeline, pending landed sectors, window move with room ---------------------
        reg [RL-1:0]  rpipe [0:NPC-1];
        reg [PB-1:0]  pend  [0:NPC-1];
        reg [CW:0]    mw    [0:NPC-1];                       // moved / SPW
        reg [RB-1:0]  mr    [0:NPC-1];                       // moved % SPW
        reg [CW:0]    qw    [0:NPC-1];                       // mw - WINW (meaningful when !mlo)
        reg [NPC-1:0] mlo;                                   // mw < WINW
        reg [2:0]     cret  [0:NPC-1];
        reg [CW-1:0]  n_rd, n_room, n_gap, n_cyc;
        wire [NPC-1:0] mv, blk;
        for (s = 0; s < NPC; s = s + 1) begin : g_mv
            wire q_ge;
            ot_hdc_kge #(.W(CW+1), .K(1)) u_room (.a(qw[s]), .b({1'b0, c_bin}), .ge(q_ge));
            wire room = mlo[s] || !q_ge;                       // mw < c_bin + WINW
            wire [CW:0] mw1, qw1;
            ot_hdc_kinc #(.W(CW+1), .K(1)) u_mw (.a(mw[s]), .inc(1'b1), .y(mw1));
            ot_hdc_kinc #(.W(CW+1), .K(1)) u_qw (.a(qw[s]), .inc(1'b1), .y(qw1));
            assign mv[s]  = (pend[s] != 0) && room;
            assign blk[s] = (pend[s] != 0) && !room;
            wire land = rpipe[s][RL-1];
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    rpipe[s] <= 0; pend[s] <= 0; mw[s] <= 0; mr[s] <= 0; qw[s] <= QW0; mlo[s] <= (WINW > 0); cret[s] <= 0;
                end else begin
                    rpipe[s] <= {rpipe[s][RL-2:0], col_v[s]};
                    pend[s] <= pend[s] + (land ? 1'b1 : 1'b0) - (mv[s] ? 1'b1 : 1'b0);
                    cret[s] <= mv[s] ? 3'd1 : 3'd0;
                    if (mv[s]) begin
                        if (mr[s] == RB'(SPW - 1)) begin
                            mr[s] <= 0; mw[s] <= mw1; qw[s] <= qw1;
                            if (&qw[s]) mlo[s] <= 1'b0;             // qw + 1 == 0: mw + 1 == WINW
                        end else mr[s] <= mr[s] + 1'b1;
                    end
                end
            assign cred_ret[s*3 +: 3] = cret[s];
        end
        // statistics: per-cycle counts registered first, accumulated a cycle later (the st_* outputs lag the original's
        // by one cycle; they are attribution statistics, not used by any hardware)
        integer p;
        reg [7:0] rd_now, room_now, gap_now;
        reg [7:0] rd_r, room_r, gap_r;
        reg       going_r;
        always @* begin
            rd_now = 0; room_now = 0; gap_now = 0;
            for (p = 0; p < NPC; p = p + 1) begin
                rd_now = rd_now + col_v[p];
                room_now = room_now + blk[p];
                gap_now = gap_now + (going && !busy[p] && lnz[p]);
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin n_rd <= 0; n_room <= 0; n_gap <= 0; n_cyc <= 0; rd_r <= 0; room_r <= 0; gap_r <= 0; going_r <= 0; end
            else begin
                rd_r <= rd_now; room_r <= room_now; gap_r <= gap_now; going_r <= going;
                n_rd <= n_rd + rd_r; n_room <= n_room + room_r; n_gap <= n_gap + gap_r;
                if (going_r) n_cyc <= n_cyc + 1;
            end
        // ---- complete words: min over the PCs' word counts, tracked incrementally ------------------------
        // Every mw rises by at most one a cycle, so min(mw) rises by at most one: with d[p] = mw[p] - amin (registers),
        // min(mw) at the next edge is amin + 1 exactly when every d[p] >= 1 now.  amin(t+1) = min(mw(t)) is the original's
        // mn[0]; m2 is its mn[1] (MINLAT = 2), so a_gray / st_words are unchanged on every cycle.
        reg  [CW:0] amin, m2;
        reg  [CW:0] d [0:NPC-1];
        wire [NPC-1:0] dnz;
        for (s = 0; s < NPC; s = s + 1) begin : g_d
            assign dnz[s] = |d[s];
        end
        wire inc_a = &dnz;
        for (s = 0; s < NPC; s = s + 1) begin : g_du
            wire up = mv[s] && (mr[s] == RB'(SPW - 1));        // mw[s] increments at this edge
            wire [CW:0] dp1, dm1;
            ot_hdc_kinc #(.W(CW+1), .K(1)) u_dp (.a(d[s]), .inc(1'b1), .y(dp1));
            ot_hdc_kadd #(.W(CW+1), .K(1)) u_dm (.a(d[s]), .b({(CW+1){1'b1}}), .cin(1'b0), .s(dm1), .cout());
            always @(posedge clk or negedge rst_n)
                if (!rst_n) d[s] <= 0;
                else if (up && !inc_a) d[s] <= dp1;
                else if (!up && inc_a) d[s] <= dm1;
        end
        wire [CW:0] amin1;
        ot_hdc_kinc #(.W(CW+1), .K(1)) u_amin (.a(amin), .inc(inc_a), .y(amin1));
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin amin <= 0; m2 <= 0; end
            else begin amin <= amin1; m2 <= amin; end
        wire [CW-1:0] a_bin = m2[CW-1:0];
        reg  [CW-1:0] a_g;
        always @(posedge clk or negedge rst_n) if (!rst_n) a_g <= 0; else a_g <= a_bin ^ (a_bin >> 1);
        assign a_gray = a_g;
        assign fault = (|pc_fault) | arb_fault;
        assign st_cycles = n_cyc; assign st_rd = n_rd; assign st_room_block = n_room; assign st_desc_gap = n_gap;
        assign st_words = a_bin;
    end endgenerate
endmodule

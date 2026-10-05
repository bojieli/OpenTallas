`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Built-in redundancy analysis (BIRA) for one SRAM at a time.
//
// Coordinates are PHYSICAL: a failure event is (row = addr / mux, vector of
// failing data bits); a spare IO column replaces one data bit in every column
// select, so the failing-bit vector is exactly the column coverage a spare
// column gives.
//
// During the March run (rec_en, one event per cycle, processed in the cycle
// it arrives -- no stall needed):
//   * the event's bits already owned by a spare column are dropped;
//   * the row is merged into the failure CAM (E entries {row, failing mask});
//   * online must-repair: a column failing in more than R distinct CAM rows
//     can only be repaired by a spare column, so it takes one immediately and
//     leaves every entry (freeing entries that become empty);
//   * running out of spare columns, or a new row finding no free entry,
//     marks the memory unrepairable (sticky).
// On `analyze` the exhaustive search visits every subset S of the CAM rows
// (2^E cycles): S is feasible when |S| <= R and the columns left uncovered by
// S, with the must-repair columns, fit in the remaining spares; the cheapest
// feasible S (fewest spares) wins, ties to the lowest subset index.  Rows and
// then columns are serialised into the repair word (E + DMAX cycles).
// A row with more failing columns than spare columns is thus forced into S:
// must-repair rows need no separate online rule.
//
// Timing structure (so the BIRA closes at the functional clock).  A failure
// event is captured into an event queue (QD entries) in the cycle it arrives;
// the queue raises `busy` -- which the controller already treats as a stall of
// operation issue -- while fewer than QSLACK entries are free, which covers the
// reads still in flight in the collar compare pipeline.  Each queued event is
// then processed over four registered stages with no overlap between events
// (the CAM state only changes in the last one):
//   P1  mask the event with the must-repair columns; CAM row match
//   P2  merge into the matching entry (or a new one); per-column row counts
//       -> the columns that must take a spare
//   P3  popcount of those columns; clear them from every entry
//   P4  free-slot search; commit or mark unrepairable
// `analyze` is latched and served once the queue is empty and P1..P4 idle.
// The exhaustive search takes three cycles per subset (uncovered-column OR,
// popcount, compare).  The allocation is identical to the
// single-cycle version (tools/rtl_mbist_campaign.py cross-checks it).
// ---------------------------------------------------------------------------
// The per-stage temporaries (tmn, tvn, cnt, cmc, spop, slot) are blocking
// intermediates inside the one clocked block.
// verilator lint_off BLKSEQ
module ot_mbist_bira #(
    parameter integer R    = 2,     // spare rows
    parameter integer C    = 2,     // spare IO columns
    parameter integer E    = 6,     // CAM entries (R * (C + 1) suffices when repairable)
    parameter integer RMAX = 16,
    parameter integer DMAX = 128,
    parameter integer CMAX = 8,
    parameter integer QD   = 8,     // event queue depth (power of two)
    parameter integer QSLACK = 4,   // free entries below which issue is stalled
    parameter integer R1   = (R > 0) ? R : 1,
    parameter integer C1   = (C > 0) ? C : 1
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               clear,
    input  wire               rec_en,
    input  wire               ev_valid,
    input  wire [RMAX-1:0]    ev_row,
    input  wire [DMAX-1:0]    ev_vec,
    input  wire               analyze,
    output wire               busy,
    output reg                done,
    output reg                repairable,
    output reg                unrep,          // sticky during recording
    output reg  [R1-1:0]      rr_en,
    output reg  [R1*RMAX-1:0] rr_addr,
    output reg  [C1-1:0]      cr_en,
    output reg  [C1*CMAX-1:0] cr_sel,
    output reg  [7:0]         n_must_cols,
    output reg  [7:0]         n_events
);
    localparam integer EW = (E <= 1) ? 1 : $clog2(E + 1);
    localparam integer SW = E + 1;
    localparam integer QW = (QD <= 2) ? 1 : $clog2(QD);
    localparam [7:0]  R8 = R[7:0];
    localparam [15:0] R16 = R[15:0], C16 = C[15:0], E16 = E[15:0], D16 = DMAX[15:0];
    localparam integer DI = (DMAX <= 2) ? 1 : $clog2(DMAX);
    localparam [2:0] S_IDLE = 3'd0, S_SRCH = 3'd1, S_ROWS = 3'd2, S_COLS = 3'd3, S_DONE = 3'd4,
                     S_SRCH3 = 3'd5, S_SRCH2 = 3'd6;

    reg [E-1:0]      valid;
    reg [RMAX-1:0]   row  [0:E-1];
    reg [DMAX-1:0]   mask [0:E-1];
    reg [DMAX-1:0]   mustcol;
    reg [7:0]        ncols;

    // Popcount as a balanced adder tree: level by level, pairs are summed, so the
    // depth is log2(DMAX) adders rather than a DMAX-long increment chain.
    localparam integer PT = (DMAX <= 1) ? 1 : (1 << $clog2(DMAX));
    function automatic [15:0] pop(input [DMAX-1:0] v);
        reg [15:0] t [0:PT-1];
        integer i, w;
        begin
            for (i = 0; i < PT; i = i + 1) t[i] = (i < DMAX) ? {15'd0, v[i]} : 16'd0;
            for (w = PT / 2; w >= 1; w = w / 2)
                for (i = 0; i < w; i = i + 1) t[i] = t[2 * i] + t[2 * i + 1];
            pop = t[0];
        end
    endfunction

    // ---- event queue ----------------------------------------------------------
    reg [RMAX-1:0] q_row [0:QD-1];
    reg [DMAX-1:0] q_vec [0:QD-1];
    reg [QW-1:0]   q_wp, q_rp;
    reg [QW:0]     q_n;
    wire           q_push = rec_en && ev_valid && !unrep;
    wire           q_full = (q_n == QD[QW:0]);

    // ---- per-event pipeline registers -----------------------------------------
    reg [3:0]      ph;                        // one-hot: P1..P4 busy
    reg [RMAX-1:0] p_row;
    reg [DMAX-1:0] p_vec;                     // event masked by the must-repair columns
    reg [E-1:0]    p_hit;
    reg [DMAX-1:0] p_tm [0:E];
    reg [E:0]      p_tv;
    reg [DMAX-1:0] p_new;                     // columns that must take a spare
    reg [15:0]     p_npop;
    wire           p_idle = (ph == 4'd0);
    wire           q_pop  = p_idle && (q_n != 0) && !unrep;

    // ---- search ---------------------------------------------------------------
    reg [2:0]      st;
    reg            ana_pend;
    reg [SW-1:0]   s;
    reg [E-1:0]    best;
    reg [15:0]     best_cost;
    reg            found;
    reg [DMAX-1:0] colset;
    reg [15:0]     k;
    integer        sl;
    reg [DMAX-1:0] cm_r;                      // uncovered columns of subset s (registered)
    reg            s_ok_r;                    // subset uses only valid entries and <= R rows
    reg [15:0]     s_pop_r;
    reg [15:0]     cm_pop_r;                  // popcount of cm_r (registered)
    // chunked popcount: 16-bit chunks counted in one stage, summed in the next
    localparam integer NCH = (DMAX + 15) / 16;
    reg [4:0]      p_part [0:NCH-1];
    reg            p_sum;                     // P3b pending

    assign busy = (st != S_IDLE && st != S_DONE) || ana_pend || (q_n + QSLACK[QW:0] > QD[QW:0]);

    integer i, j, c;
    reg [7:0]      cnt;
    reg [DMAX-1:0] cmc;
    reg [DMAX-1:0] tmn [0:E];
    reg [E:0]      tvn;
    integer        slot;
    reg [15:0]     spop;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid <= {E{1'b0}}; mustcol <= {DMAX{1'b0}}; ncols <= 8'd0; unrep <= 1'b0;
            st <= S_IDLE; s <= {SW{1'b0}}; best <= {E{1'b0}}; best_cost <= 16'hFFFF; found <= 1'b0;
            colset <= {DMAX{1'b0}}; k <= 16'd0; sl <= 0; done <= 1'b0; repairable <= 1'b0;
            rr_en <= {R1{1'b0}}; rr_addr <= {(R1*RMAX){1'b0}}; cr_en <= {C1{1'b0}}; cr_sel <= {(C1*CMAX){1'b0}};
            n_must_cols <= 8'd0; n_events <= 8'd0; ana_pend <= 1'b0;
            q_wp <= {QW{1'b0}}; q_rp <= {QW{1'b0}}; q_n <= {(QW+1){1'b0}}; ph <= 4'd0; p_sum <= 1'b0;
            cm_r <= {DMAX{1'b0}}; s_ok_r <= 1'b0; s_pop_r <= 16'd0; cm_pop_r <= 16'd0;
            for (j = 0; j < E; j = j + 1) begin row[j] <= {RMAX{1'b0}}; mask[j] <= {DMAX{1'b0}}; end
        end else if (clear) begin
            valid <= {E{1'b0}}; mustcol <= {DMAX{1'b0}}; ncols <= 8'd0; unrep <= 1'b0;
            st <= S_IDLE; done <= 1'b0; repairable <= 1'b0; found <= 1'b0; ana_pend <= 1'b0;
            rr_en <= {R1{1'b0}}; rr_addr <= {(R1*RMAX){1'b0}}; cr_en <= {C1{1'b0}}; cr_sel <= {(C1*CMAX){1'b0}};
            n_must_cols <= 8'd0; n_events <= 8'd0;
            q_wp <= {QW{1'b0}}; q_rp <= {QW{1'b0}}; q_n <= {(QW+1){1'b0}}; ph <= 4'd0; p_sum <= 1'b0;
        end else begin
            // ---- queue ----
            if (q_push && !q_full) begin
                q_row[q_wp] <= ev_row;
                q_vec[q_wp] <= ev_vec;
                q_wp <= q_wp + 1'b1;
            end
            if (q_push && q_full) unrep <= 1'b1;             // cannot happen with the stall; fail safe
            q_n <= q_n + {{QW{1'b0}}, q_push && !q_full} - {{QW{1'b0}}, q_pop};
            if (unrep) begin
                ph <= 4'd0;
                p_sum <= 1'b0;
            end else begin
                // ---- P1: mask, CAM match ----
                if (q_pop) begin
                    q_rp <= q_rp + 1'b1;
                    p_row <= q_row[q_rp];
                    p_vec <= q_vec[q_rp] & ~mustcol;
                    for (i = 0; i < E; i = i + 1) p_hit[i] <= valid[i] && (row[i] == q_row[q_rp]);
                    ph <= 4'b0001;
                end
                // ---- P2: merge, per-column counts ----
                if (ph[0]) begin
                    if (p_vec == {DMAX{1'b0}}) ph <= 4'd0;     // nothing new: event absorbed
                    else begin
                        for (i = 0; i < E; i = i + 1) begin
                            tmn[i] = p_hit[i] ? (mask[i] | p_vec) : mask[i];
                            tvn[i] = valid[i];
                        end
                        tmn[E] = (|p_hit) ? {DMAX{1'b0}} : p_vec;
                        tvn[E] = !(|p_hit);
                        for (c = 0; c < DMAX; c = c + 1) begin
                            cnt = 8'd0;
                            for (i = 0; i <= E; i = i + 1) cnt = cnt + {7'd0, tvn[i] & tmn[i][c]};
                            p_new[c] <= (cnt > R8);
                        end
                        for (i = 0; i <= E; i = i + 1) p_tm[i] <= tmn[i];
                        p_tv <= tvn;
                        if (n_events != 8'hFF) n_events <= n_events + 8'd1;
                        ph <= 4'b0010;
                    end
                end
                // ---- P3: popcount, clear the must-repair columns ----
                if (ph[1] && !p_sum) begin                 // P3a: chunk counts, clear columns
                    for (c = 0; c < NCH; c = c + 1)
                        p_part[c] <= pop16(p_new, c);
                    for (i = 0; i <= E; i = i + 1) p_tm[i] <= p_tm[i] & ~p_new;
                    p_sum <= 1'b1;
                end
                if (ph[1] && p_sum) begin                  // P3b: sum the chunks
                    p_npop <= parts_sum;
                    p_sum <= 1'b0;
                    ph <= 4'b0100;
                end
                // ---- P4: slot, commit ----
                if (ph[2]) begin
                    for (i = 0; i <= E; i = i + 1) tvn[i] = p_tv[i] & (p_tm[i] != {DMAX{1'b0}});
                    slot = E;
                    for (i = E - 1; i >= 0; i = i - 1) if (!tvn[i]) slot = i;
                    if (({8'd0, ncols} + p_npop) > C16 || (tvn[E] && slot == E)) unrep <= 1'b1;
                    else begin
                        mustcol <= mustcol | p_new;
                        ncols <= ncols + p_npop[7:0];
                        n_must_cols <= n_must_cols + p_npop[7:0];
                        for (j = 0; j < E; j = j + 1) begin
                            valid[j] <= tvn[j];
                            mask[j] <= p_tm[j];
                        end
                        if (tvn[E]) begin
                            valid[slot] <= 1'b1;
                            mask[slot] <= p_tm[E];
                            row[slot] <= p_row;
                        end
                    end
                    ph <= 4'd0;
                end
            end
            // ---- analysis ----
            case (st)
                S_IDLE: begin
                    if (analyze) ana_pend <= 1'b1;
                    if ((analyze || ana_pend) && (unrep || (q_n == 0 && p_idle && !q_push))) begin
                        ana_pend <= 1'b0;
                        s <= {SW{1'b0}}; found <= 1'b0; best_cost <= 16'hFFFF; best <= {E{1'b0}};
                        st <= unrep ? S_DONE : S_SRCH;
                        repairable <= 1'b0;
                    end
                end
                S_SRCH: begin                                  // subset s: uncovered columns
                    cmc = {DMAX{1'b0}};
                    for (i = 0; i < E; i = i + 1)
                        if (valid[i] && !s[i]) cmc = cmc | mask[i];
                    cm_r <= cmc;
                    s_ok_r <= ((s[E-1:0] & ~valid) == {E{1'b0}});
                    spop = 16'd0;
                    for (i = 0; i < E; i = i + 1) spop = spop + {15'd0, s[i]};
                    s_pop_r <= spop;
                    st <= S_SRCH2;
                end
                S_SRCH2: begin                                 // popcount of the uncovered columns
                    cm_pop_r <= pop(cm_r);
                    st <= S_SRCH3;
                end
                S_SRCH3: begin                                 // feasibility, best
                    if (s_ok_r && s_pop_r <= R16 && (cm_pop_r + {8'd0, ncols} <= C16)
                        && (!found || s_pop_r + cm_pop_r < best_cost)) begin
                        found <= 1'b1; best <= s[E-1:0]; best_cost <= s_pop_r + cm_pop_r;
                    end
                    if (s[E-1:0] == {E{1'b1}}) begin
                        st <= S_ROWS; k <= 16'd0; s <= {SW{1'b0}}; sl <= 0;
                    end else begin
                        s <= s + 1'b1;
                        st <= S_SRCH;
                    end
                end
                S_ROWS: begin
                    if (!found) st <= S_DONE;
                    else begin
                        if (k < E16) begin
                            if (best[k[EW-1:0]]) begin
                                rr_en[sl % R1] <= 1'b1;
                                rr_addr[(sl % R1)*RMAX +: RMAX] <= row[k[EW-1:0]];
                                sl <= sl + 1;
                            end
                            k <= k + 16'd1;
                        end else begin
                            colset <= mustcol | cm_best(best);
                            k <= 16'd0; sl <= 0;
                            st <= S_COLS;
                        end
                    end
                end
                S_COLS: begin
                    if (k < D16) begin
                        if (colset[k[DI-1:0]]) begin
                            cr_en[sl % C1] <= 1'b1;
                            cr_sel[(sl % C1)*CMAX +: CMAX] <= k[CMAX-1:0];
                            sl <= sl + 1;
                        end
                        k <= k + 16'd1;
                    end else begin
                        repairable <= 1'b1;
                        st <= S_DONE;
                    end
                end
                default: begin
                    done <= 1'b1;
                end
            endcase
        end
    end

    // popcount of the 16-bit chunk c of v, as a tree
    function automatic [4:0] pop16(input [DMAX-1:0] v, input integer ch);
        reg [4:0] t [0:15];
        integer n, w;
        begin
            for (n = 0; n < 16; n = n + 1) t[n] = (ch * 16 + n < DMAX) ? {4'd0, v[ch * 16 + n]} : 5'd0;
            for (w = 8; w >= 1; w = w / 2)
                for (n = 0; n < w; n = n + 1) t[n] = t[2 * n] + t[2 * n + 1];
            pop16 = t[0];
        end
    endfunction

    // sum of the chunk counts, as a tree
    localparam integer NCP = (NCH <= 1) ? 1 : (1 << $clog2(NCH));
    reg [15:0] parts_sum;
    reg [15:0] pst [0:NCP-1];
    integer pn, pw;
    always @* begin
        for (pn = 0; pn < NCP; pn = pn + 1) pst[pn] = (pn < NCH) ? {11'd0, p_part[pn]} : 16'd0;
        for (pw = NCP / 2; pw >= 1; pw = pw / 2)
            for (pn = 0; pn < pw; pn = pn + 1) pst[pn] = pst[2 * pn] + pst[2 * pn + 1];
        parts_sum = pst[0];
    end

    function automatic [DMAX-1:0] cm_best(input [E-1:0] b);
        integer q;
        begin
            cm_best = {DMAX{1'b0}};
            for (q = 0; q < E; q = q + 1)
                if (valid[q] && !b[q]) cm_best = cm_best | mask[q];
        end
    endfunction
endmodule
// verilator lint_on BLKSEQ

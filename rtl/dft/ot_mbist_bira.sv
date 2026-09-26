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
// ---------------------------------------------------------------------------
module ot_mbist_bira #(
    parameter integer R    = 2,     // spare rows
    parameter integer C    = 2,     // spare IO columns
    parameter integer E    = 6,     // CAM entries (R * (C + 1) suffices when repairable)
    parameter integer RMAX = 16,
    parameter integer DMAX = 128,
    parameter integer CMAX = 8,
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
    localparam [7:0]  R8 = R[7:0];
    localparam [15:0] R16 = R[15:0], C16 = C[15:0], E16 = E[15:0], D16 = DMAX[15:0];
    localparam integer DI = (DMAX <= 2) ? 1 : $clog2(DMAX);
    localparam [2:0] S_IDLE = 3'd0, S_SRCH = 3'd1, S_ROWS = 3'd2, S_COLS = 3'd3, S_DONE = 3'd4;

    reg [E-1:0]      valid;
    reg [RMAX-1:0]   row  [0:E-1];
    reg [DMAX-1:0]   mask [0:E-1];
    reg [DMAX-1:0]   mustcol;
    reg [7:0]        ncols;

    function automatic [15:0] pop(input [DMAX-1:0] v);
        integer i;
        begin
            pop = 16'd0;
            for (i = 0; i < DMAX; i = i + 1) pop = pop + {15'd0, v[i]};
        end
    endfunction

    // ---- online event processing (combinational) ----------------------------
    reg [DMAX-1:0] vecp, tm [0:E], newmust;
    reg [E:0]      tv;
    reg            anyhit, place_ok, apply_ok;
    reg [15:0]     npop;
    reg [7:0]      cnt;
    integer i, c, slot;
    always @* begin
        vecp = ev_vec & ~mustcol;
        anyhit = 1'b0;
        for (i = 0; i < E; i = i + 1) begin
            tv[i] = valid[i];
            tm[i] = mask[i];
            if (valid[i] && row[i] == ev_row) begin
                anyhit = 1'b1;
                tm[i] = mask[i] | vecp;
            end
        end
        tm[E] = anyhit ? {DMAX{1'b0}} : vecp;
        tv[E] = !anyhit && (vecp != {DMAX{1'b0}});
        newmust = {DMAX{1'b0}};
        for (c = 0; c < DMAX; c = c + 1) begin
            cnt = 8'd0;
            for (i = 0; i <= E; i = i + 1) cnt = cnt + {7'd0, tv[i] & tm[i][c]};
            newmust[c] = (cnt > R8);
        end
        npop = pop(newmust);
        apply_ok = ({8'd0, ncols} + npop) <= C16;
        if (apply_ok)
            for (i = 0; i <= E; i = i + 1) begin
                tm[i] = tm[i] & ~newmust;
                tv[i] = tv[i] & (tm[i] != {DMAX{1'b0}});
            end
        slot = E;
        for (i = E - 1; i >= 0; i = i - 1) if (!tv[i]) slot = i;
        place_ok = !tv[E] || (slot < E);
    end

    // ---- search -------------------------------------------------------------
    reg [2:0]      st;
    reg [SW-1:0]   s;
    reg [E-1:0]    best;
    reg [15:0]     best_cost;
    reg            found;
    reg [DMAX-1:0] colset;
    reg [15:0]     k;
    integer        sl;
    reg [DMAX-1:0] cm;
    reg [15:0]     cost_now;
    reg            feas;
    always @* begin
        cm = {DMAX{1'b0}};
        for (i = 0; i < E; i = i + 1)
            if (valid[i] && !s[i]) cm = cm | mask[i];
        feas = ((s[E-1:0] & ~valid) == {E{1'b0}}) && (pop({{(DMAX-E){1'b0}}, s[E-1:0]}) <= R16)
               && (pop(cm) + {8'd0, ncols} <= C16);
        cost_now = pop({{(DMAX-E){1'b0}}, s[E-1:0]}) + pop(cm);
    end
    assign busy = (st != S_IDLE) && (st != S_DONE);

    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid <= {E{1'b0}}; mustcol <= {DMAX{1'b0}}; ncols <= 8'd0; unrep <= 1'b0;
            st <= S_IDLE; s <= {SW{1'b0}}; best <= {E{1'b0}}; best_cost <= 16'hFFFF; found <= 1'b0;
            colset <= {DMAX{1'b0}}; k <= 16'd0; sl <= 0; done <= 1'b0; repairable <= 1'b0;
            rr_en <= {R1{1'b0}}; rr_addr <= {(R1*RMAX){1'b0}}; cr_en <= {C1{1'b0}}; cr_sel <= {(C1*CMAX){1'b0}};
            n_must_cols <= 8'd0; n_events <= 8'd0;
            for (j = 0; j < E; j = j + 1) begin row[j] <= {RMAX{1'b0}}; mask[j] <= {DMAX{1'b0}}; end
        end else if (clear) begin
            valid <= {E{1'b0}}; mustcol <= {DMAX{1'b0}}; ncols <= 8'd0; unrep <= 1'b0;
            st <= S_IDLE; done <= 1'b0; repairable <= 1'b0; found <= 1'b0;
            rr_en <= {R1{1'b0}}; rr_addr <= {(R1*RMAX){1'b0}}; cr_en <= {C1{1'b0}}; cr_sel <= {(C1*CMAX){1'b0}};
            n_must_cols <= 8'd0; n_events <= 8'd0;
        end else begin
            case (st)
                S_IDLE: begin
                    if (rec_en && ev_valid && !unrep && (ev_vec & ~mustcol) != {DMAX{1'b0}}) begin
                        if (n_events != 8'hFF) n_events <= n_events + 8'd1;
                        if (!apply_ok || !place_ok) unrep <= 1'b1;
                        else begin
                            mustcol <= mustcol | newmust;
                            ncols <= ncols + npop[7:0];
                            n_must_cols <= n_must_cols + npop[7:0];
                            for (j = 0; j < E; j = j + 1) begin
                                valid[j] <= tv[j];
                                mask[j] <= tm[j];
                            end
                            if (tv[E]) begin
                                valid[slot] <= 1'b1;
                                mask[slot] <= tm[E];
                                row[slot] <= ev_row;
                            end
                        end
                    end
                    if (analyze) begin
                        s <= {SW{1'b0}}; found <= 1'b0; best_cost <= 16'hFFFF; best <= {E{1'b0}};
                        st <= unrep ? S_DONE : S_SRCH;
                        repairable <= 1'b0;
                    end
                end
                S_SRCH: begin
                    if (feas && (!found || cost_now < best_cost)) begin
                        found <= 1'b1; best <= s[E-1:0]; best_cost <= cost_now;
                    end
                    if (s[E-1:0] == {E{1'b1}}) begin
                        st <= S_ROWS; k <= 16'd0; s <= {SW{1'b0}}; sl <= 0;
                    end else s <= s + 1'b1;
                end
                S_ROWS: begin
                    // serialise the chosen rows, one CAM entry per cycle
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
                            // columns: must-repair plus those the rows left uncovered
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

    function automatic [DMAX-1:0] cm_best(input [E-1:0] b);
        integer q;
        begin
            cm_best = {DMAX{1'b0}};
            for (q = 0; q < E; q = q + 1)
                if (valid[q] && !b[q]) cm_best = cm_best | mask[q];
        end
    endfunction
endmodule

`timescale 1ns/1ps
// ot_dsrom_wsrc_mirror (el1011-ds-misc 2026-10-11): the hardened tag-mirror sub-tile of ot_dsrom_window_source_ctl
// MARGIN 3.  One copy of the 128-entry {mv, tag[POS_W], user[USER_W]} mirror, banked by row[1:0] (4 banks x 32
// entries indexed by row[6:2]).  The job check reads four consecutive rows per cycle, which always fall in four
// distinct banks, so each bank serves exactly one read per cycle (no 128-way select, no per-lane table copies):
//   e1  pin flops: per-bank read row / use, j_user; write command (slot, tag-write, mv set / clear, row, user)
//   e2  per bank 8:1 by row[4:2] -> 4 group registers;   write applied to the bank selected by slot[1:0]
//   e3  4:1 by row[6:5] -> entry register
//   e4  compare -> bad[bank] (registered output)   bad = use && (!mv || tag != row || user != j_user)
// Writes land one edge later than MARGIN 2's mirror; mirror reads start >= 6 edges after the job accept edge and no
// write can be accepted after it, so no read observes the difference.  Only mv is reset.
// ---------------------------------------------------------------------------
module ot_dsrom_wsrc_mirror #(parameter integer POS_W = 21, USER_W = 10) (
    input  wire                 clk, rst_n,
    // write command (registered by the controller one edge after the prime / blk accept)
    input  wire                 wr_tag,          // write tag / user of the slot
    input  wire                 wr_set,          // mv <= 1
    input  wire                 wr_clr,          // mv <= 0 (wr_set has priority)
    input  wire [6:0]           wr_slot,
    input  wire [POS_W-1:0]     wr_row,
    input  wire [USER_W-1:0]    wr_user,
    // reads: one row per bank per cycle (bank b reads a row with row[1:0] == b)
    input  wire [4*POS_W-1:0]   rd_row,
    input  wire [3:0]           rd_use,
    input  wire [USER_W-1:0]    j_user,
    output reg  [3:0]           bad
);
    localparam integer EW = POS_W + USER_W;
    genvar bk;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_bank
        // ---- e1 pin flops (one copy of the write command per bank: 32-entry fanout) ----
        (* keep *) reg w_hit_q, w_tag_q, w_set_q, w_clr_q;
        reg [4:0] w_idx_q; reg [EW-1:0] w_d_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin w_hit_q <= 1'b0; w_tag_q <= 1'b0; w_set_q <= 1'b0; w_clr_q <= 1'b0; end
            else begin
                w_hit_q <= wr_slot[1:0] == 2'(bk);
                w_tag_q <= wr_tag; w_set_q <= wr_set; w_clr_q <= wr_clr;
            end
        always @(posedge clk) begin w_idx_q <= wr_slot[6:2]; w_d_q <= {wr_row, wr_user}; end
        reg [POS_W-1:0] r_row1, r_row2, r_row3; reg r_use1, r_use2, r_use3;
        reg [USER_W-1:0] ju1, ju2, ju3;
        always @(posedge clk) begin
            r_row1 <= rd_row[bk*POS_W +: POS_W]; r_use1 <= rd_use[bk]; ju1 <= j_user;
            r_row2 <= r_row1; r_use2 <= r_use1; ju2 <= ju1;
            r_row3 <= r_row2; r_use3 <= r_use2; ju3 <= ju2;
        end
        // ---- storage ----
        reg [EW-1:0] ent [0:31];
        reg [31:0] mv;
        integer e;
        always @(posedge clk)
            for (e = 0; e < 32; e = e + 1)
                if (w_hit_q && w_tag_q && w_idx_q == 5'(e)) ent[e] <= w_d_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) mv <= '0;
            else for (e = 0; e < 32; e = e + 1)
                if (w_hit_q && w_idx_q == 5'(e)) begin
                    if (w_set_q) mv[e] <= 1'b1; else if (w_clr_q) mv[e] <= 1'b0;
                end
        // ---- e2: 8:1 by row[4:2] into four groups (group g = entries {g, row[4:2]}) ----
        reg [EW-1:0] g_ent [0:3]; reg [3:0] g_mv;
        integer g;
        always @(posedge clk)
            for (g = 0; g < 4; g = g + 1) begin
                g_ent[g] <= ent[{g[1:0], r_row1[4:2]}];
                g_mv[g] <= mv[{g[1:0], r_row1[4:2]}];
            end
        // ---- e3: 4:1 by row[6:5] ----
        reg [EW-1:0] s_ent; reg s_mv;
        always @(posedge clk) begin s_ent <= g_ent[r_row2[6:5]]; s_mv <= g_mv[r_row2[6:5]]; end
        // ---- e4: compare ----
        always @(posedge clk or negedge rst_n)
            if (!rst_n) bad[bk] <= 1'b0;
`ifdef OT_MIRROR_MUTANT
            else bad[bk] <= r_use3 && (!s_mv || s_ent[EW-1:USER_W] != r_row3);   // negative control: user ignored
`else
            else bad[bk] <= r_use3 && (!s_mv || s_ent[EW-1:USER_W] != r_row3 || s_ent[USER_W-1:0] != ju3);
`endif
    end endgenerate
endmodule

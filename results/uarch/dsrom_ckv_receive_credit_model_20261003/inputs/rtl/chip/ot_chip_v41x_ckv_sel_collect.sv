`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// In-order collector of the all-gathered selected-CKV rows on one die.
//
// NSRC row sources (this die's own ot_chip_v41x_ckv_sel_fetch output and the
// three remote dies' outputs as delivered by the all-gather links) each
// deliver whole 288-B rows tagged with their selection rank and global id, in
// any order.  A row is written at its RANK in a K-row buffer (this buffer is
// the selected part of the attention staging: in an integrated die the row
// would be written at staging row window_count + rank directly) and marked
// present; the output then releases ranks 0, 1, 2 ... in order as soon as
// each is present (up to NOUT consecutive ranks per cycle), so the attention
// engine's q.k runs on the rows while later rows are still in flight.
//
// Every write is checked: rank < n_sel, the rank not already present, and the
// global id equal to the selection table's id at that rank (one table read
// port per source), so a row can never land at the wrong attention row.
//
// Interfaces
//   job     clr (with exp_n = n_sel, the number of ranks to release).
//   src     src_v[NSRC] (always accepted: one row per source per cycle),
//           src_rank, src_gid, src_row (2,304-bit DMA packed row).
//   table   tab_rank[NSRC] -> tab_gid[NSRC] (ot_chip_v41x_ckv_sel_ids read ports).
//   out     o_n (0 .. NOUT: consecutive present ranks from o_rank), o_rank,
//           o_gid[j], o_row[j] (rank o_rank + j); the consumer takes
//           o_take <= o_n of them this cycle (combinational).  Ranks leave in
//           ascending order.
//   status  done (all n_sel released), fault/fault_code {id, dup, range}.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_sel_collect #(
    parameter integer NSRC = 4,
    parameter integer POS_W = 21,
    parameter integer K = 512,
    parameter integer NOUT = 4,
    parameter bit RDREG = 0,        // 1: table read ports are synchronous; sources are registered one cycle
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   clr,
    input  wire [KW-1:0]          exp_n,
    input  wire [NSRC-1:0]        src_v,
    input  wire [NSRC*KW-1:0]     src_rank,
    input  wire [NSRC*POS_W-1:0]  src_gid,
    input  wire [NSRC*2304-1:0]   src_row,
    output wire [NSRC*KW-1:0]     tab_rank,
    input  wire [NSRC*POS_W-1:0]  tab_gid,
    output reg  [2:0]             o_n,
    input  wire [2:0]             o_take,
    output wire [KW-1:0]          o_rank,
    output wire [NOUT*POS_W-1:0]  o_gid,
    output wire [NOUT*2304-1:0]   o_row,
    output reg                    done,
    output reg  [KW-1:0]          max_present_ahead,  // stat: largest (present ranks) - (released)
    output reg                    fault,
    output reg  [2:0]             fault_code
);
    reg [2303:0] buf_row [0:K-1];
    reg [POS_W-1:0] buf_gid [0:K-1];
    reg [K-1:0] present;
    reg [KW-1:0] nexp, rd;
    reg [KW:0] npresent;
    // RDREG: the sources are registered while the table read (addressed by the raw source ranks) completes
    reg [NSRC-1:0] q_v;
    reg [NSRC*KW-1:0] q_rank;
    reg [NSRC*POS_W-1:0] q_gid;
    reg [NSRC*2304-1:0] q_row;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q_v <= 0; else q_v <= (clr ? '0 : src_v);
    always @(posedge clk) begin q_rank <= src_rank; q_gid <= src_gid; q_row <= src_row; end
    wire [NSRC-1:0] w_v = RDREG ? q_v : src_v;
    wire [NSRC*KW-1:0] w_rank = RDREG ? q_rank : src_rank;
    wire [NSRC*POS_W-1:0] w_gid = RDREG ? q_gid : src_gid;
    wire [NSRC*2304-1:0] w_row = RDREG ? q_row : src_row;
    assign tab_rank = src_rank;
    assign o_rank = rd;
    integer oj;
    reg ostop;
    always @(*) begin
        o_n = 0; ostop = 1'b0;
        for (oj = 0; oj < NOUT; oj = oj + 1)
            if (!ostop && !done && 32'(rd) + oj < 32'(nexp) && present[32'(rd) + oj]) o_n = o_n + 1'b1;
            else ostop = 1'b1;
    end
    genvar go;
    generate for (go = 0; go < NOUT; go = go + 1) begin : g_o
        wire [KW-1:0] ra = rd + KW'(go);
        assign o_gid[go*POS_W +: POS_W] = buf_gid[ra];
        assign o_row[go*2304 +: 2304] = buf_row[ra];
    end endgenerate

    integer i, j;
    reg dup;
    reg [KW:0] nwr;
    always @(*) begin
        dup = 1'b0; nwr = 0;
        for (i = 0; i < NSRC; i = i + 1) if (w_v[i]) begin
            nwr = nwr + 1'b1;
            for (j = 0; j < i; j = j + 1)
                if (w_v[j] && w_rank[j*KW +: KW] == w_rank[i*KW +: KW]) dup = 1'b1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            present <= 0; nexp <= 0; rd <= 0; done <= 0; fault <= 0; fault_code <= 0;
            npresent <= 0; max_present_ahead <= 0;
        end else if (clr) begin
            present <= 0; nexp <= exp_n; rd <= 0; done <= (exp_n == 0); npresent <= 0;
            max_present_ahead <= 0;
        end else begin
            if (dup) begin fault <= 1; fault_code[1] <= 1; end
            for (i = 0; i < NSRC; i = i + 1) if (w_v[i]) begin
                if (w_rank[i*KW +: KW] >= nexp) begin fault <= 1; fault_code[0] <= 1; end
                else if (present[w_rank[i*KW +: KW]]) begin fault <= 1; fault_code[1] <= 1; end
                else if (w_gid[i*POS_W +: POS_W] != tab_gid[i*POS_W +: POS_W]) begin
                    fault <= 1; fault_code[2] <= 1;
                end else begin
                    buf_row[w_rank[i*KW +: KW]] <= w_row[i*2304 +: 2304];
                    buf_gid[w_rank[i*KW +: KW]] <= w_gid[i*POS_W +: POS_W];
                    present[w_rank[i*KW +: KW]] <= 1'b1;
                end
            end
            npresent <= npresent + nwr;
            if ((npresent - (KW+1)'(rd)) > (KW+1)'(max_present_ahead))
                max_present_ahead <= KW'(npresent - (KW+1)'(rd));
            if (o_take > o_n) begin fault <= 1; fault_code[0] <= 1; end
            else if (o_take != 0) begin
                rd <= rd + KW'(o_take);
                if (rd + KW'(o_take) == nexp) done <= 1;
            end
        end
    end
endmodule

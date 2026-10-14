`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// V4.1x index select MASK-DROP stage (re-index layers L24/L28/L32/L36), one registered
// stage per quarter in front of ot_hdc_v41x_sel.
//
// The golden (tools/hdc_golden_v41.py Model.indexer) scores every key and then writes
// -inf at every position outside the candidate blocks; topk_lowest_index then selects the
// k largest, ties to the lower index.  As built, those -inf keys enter the select as
// valid lanes: until k finite keys have been seen the select's running bound stays at
// -inf and every -inf key survives (equal keys must survive), so a 1M stream with
// 16,384 candidates overflows the survivor memory and the select replays the segment
// twice (results/rtl/dsrom_1m_measured_20261004: 12,359 cycles against 4,198 for L20).
//
// MDROP = 1 drops the masked keys BEFORE the select: lane valid = key valid AND keep,
// and a beat left with no valid lane is not forwarded (except a quarter's last beat,
// which the select's contract needs, forwarded with whatever lanes remain).  Positions
// travel with the scores, so ascending order, values and the lower-index tie-break are
// untouched.  Exact whenever at least k keys of the segment are candidates: then no -inf
// key is in the golden top-k, and removing keys that are not selected and rank below
// every selected one leaves the top-k set (and its order) unchanged.  The candidate
// source keeps min(2,048, blocks) blocks, each holding >= 1 real position and all full
// but the newest, so a segment has >= min(k, n) candidates for k <= 16,377 at every
// context (n = the positions): always true for k = 512.  `short` is raised (sticky) if a
// segment nevertheless ends with fewer kept keys than k, so the condition is checked in
// hardware rather than assumed.
// MDROP = 0 (default) is the as-built behaviour: masked lanes are forwarded as -inf.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_sel_mdrop #(
    parameter integer Q     = 4,
    parameter integer W     = 16,
    parameter integer IW    = 20,
    parameter integer KW    = 10,
    parameter integer MDROP = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [Q-1:0]      in_valid,
    output wire [Q-1:0]      in_ready,
    input  wire [Q-1:0]      in_last,
    input  wire [Q*W-1:0]    in_lv,
    input  wire [Q*W-1:0]    in_keep,     // 1 = candidate position
    input  wire [Q*W*16-1:0] in_val,
    input  wire [Q*W*IW-1:0] in_idx,
    input  wire [KW-1:0]     in_k,
    output reg  [Q-1:0]      out_valid,
    input  wire [Q-1:0]      out_ready,
    output reg  [Q-1:0]      out_last,
    output reg  [Q*W-1:0]    out_lv,
    output reg  [Q*W*16-1:0] out_val,
    output reg  [Q*W*IW-1:0] out_idx,
    output reg  [KW-1:0]     out_k,
    output reg               short
);
    localparam [15:0] NINF = 16'hFF80;
    localparam integer CW = 10;                // kept keys per quarter, saturating (k <= 1,023)
    assign in_ready = ~out_valid | out_ready;
    // the fewer-than-k check, off the datapath: popcount -> saturating count -> sums -> compare
    reg  [Q-1:0]  pv_r, pl_r;                  // beat accepted / its last flag (registered)
    reg  [4:0]    pc_r [0:Q-1];                // kept lanes of the accepted beat
    reg  [CW-1:0] kept [0:Q-1];
    reg  [Q-1:0]  qend;                        // quarter's last beat counted this segment
    reg           chk_c, chk_d;
    reg  [CW:0]   s01, s23;
    reg  [CW+1:0] tot_d;
    reg  [KW-1:0] k_c, k_d;
    wire          snap = &qend;
    integer q, j;
    reg [W-1:0]   lv;
    reg [4:0]     pc;
    reg [CW:0]    nk;
    always @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 0; short <= 1'b0; qend <= 0; pv_r <= 0; pl_r <= 0; chk_c <= 1'b0; chk_d <= 1'b0;
            for (q = 0; q < Q; q = q + 1) kept[q] <= 0;
        end else begin
            for (q = 0; q < Q; q = q + 1) begin
                if (out_valid[q] && out_ready[q]) out_valid[q] <= 1'b0;
                lv = (MDROP != 0) ? (in_lv[W*q +: W] & in_keep[W*q +: W]) : in_lv[W*q +: W];
                pc = 0;
                for (j = 0; j < W; j = j + 1) pc = pc + {4'd0, lv[j]};
                pv_r[q] <= in_valid[q] && in_ready[q];
                pl_r[q] <= in_valid[q] && in_ready[q] && in_last[q];
                pc_r[q] <= pc;
                if (in_valid[q] && in_ready[q] && ((MDROP == 0) || (lv != 0) || in_last[q])) begin
                    out_valid[q] <= 1'b1;
                    out_last[q] <= in_last[q];
                    out_lv[W*q +: W] <= lv;
                    out_idx[W*IW*q +: W*IW] <= in_idx[W*IW*q +: W*IW];
                    for (j = 0; j < W; j = j + 1)
                        out_val[W*16*q + 16*j +: 16] <= ((MDROP == 0) && !in_keep[W*q + j])
                                                        ? NINF : in_val[W*16*q + 16*j +: 16];
                end
                // saturating count; a segment's counts are snapped and restarted once every quarter ended
                nk = {1'b0, snap ? {CW{1'b0}} : kept[q]} + {{(CW-4){1'b0}}, pv_r[q] ? pc_r[q] : 5'd0};
                kept[q] <= nk[CW] ? {CW{1'b1}} : nk[CW-1:0];
                qend[q] <= (snap ? 1'b0 : qend[q]) | pl_r[q];
            end
            out_k <= in_k;
            chk_c <= snap;
            if (snap) begin
                s01 <= {1'b0, kept[0]} + {1'b0, kept[1]};
                s23 <= {1'b0, kept[Q-2]} + {1'b0, kept[Q-1]};
                k_c <= out_k;
            end
            chk_d <= chk_c;
            if (chk_c) begin tot_d <= {1'b0, s01} + {1'b0, s23}; k_d <= k_c; end
            if (chk_d && (MDROP != 0) && (tot_d < {{(CW+2-KW){1'b0}}, k_d})) short <= 1'b1;
        end
    end
endmodule

// The drop stage followed by the select (the unit the re-index layer instantiates).
module ot_hdc_v41x_sel_mdrop_top #(
    parameter integer Q = 4, W = 16, IW = 20, K = 512, AW = 8, DG = 8, OD = 4, MDROP = 1,
    parameter integer KW = $clog2(K + 1), EW = 17 + IW
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [Q-1:0]      in_valid,
    output wire [Q-1:0]      in_ready,
    input  wire [Q-1:0]      in_last,
    input  wire [Q*W-1:0]    in_lv,
    input  wire [Q*W-1:0]    in_keep,
    input  wire [Q*W*16-1:0] in_val,
    input  wire [Q*W*IW-1:0] in_idx,
    input  wire [KW-1:0]     in_k,
    output wire [Q-1:0]      out_valid,
    input  wire [Q-1:0]      out_ready,
    output wire [Q-1:0]      out_last,
    output wire [Q*W-1:0]    out_lv,
    output wire [Q*W*16-1:0] out_val,
    output wire [Q*W*IW-1:0] out_idx,
    output wire [Q*W-1:0]    out_ninf,
    output wire [Q-1:0]      mem_we,
    output wire [Q*AW-1:0]   mem_waddr,
    output wire [Q*W*EW-1:0] mem_wdata,
    output wire [Q-1:0]      mem_re,
    output wire [Q*AW-1:0]   mem_raddr,
    input  wire [Q*W*EW-1:0] mem_rdata,
    output wire              rep_req,
    output wire              ovf,
    output wire              busy,
    output wire [Q*3*(AW+1)-1:0] stats,
    output wire              short
);
    wire [Q-1:0]      d_valid, d_ready, d_last;
    wire [Q*W-1:0]    d_lv;
    wire [Q*W*16-1:0] d_val;
    wire [Q*W*IW-1:0] d_idx;
    wire [KW-1:0]     d_k;
    ot_hdc_v41x_sel_mdrop #(.Q(Q), .W(W), .IW(IW), .KW(KW), .MDROP(MDROP)) u_drop (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_last(in_last), .in_lv(in_lv),
        .in_keep(in_keep), .in_val(in_val), .in_idx(in_idx), .in_k(in_k),
        .out_valid(d_valid), .out_ready(d_ready), .out_last(d_last), .out_lv(d_lv), .out_val(d_val),
        .out_idx(d_idx), .out_k(d_k), .short(short));
    ot_hdc_v41x_sel #(.Q(Q), .W(W), .IW(IW), .K(K), .AW(AW), .DG(DG), .OD(OD)) u_sel (
        .clk(clk), .rst_n(rst_n), .in_valid(d_valid), .in_ready(d_ready), .in_last(d_last),
        .in_lv(d_lv), .in_val(d_val), .in_idx(d_idx), .in_k(d_k),
        .out_valid(out_valid), .out_ready(out_ready), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re),
        .mem_raddr(mem_raddr), .mem_rdata(mem_rdata), .rep_req(rep_req), .ovf(ovf), .busy(busy), .stats(stats));
endmodule

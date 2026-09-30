`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Streaming WINDOW + selected-CKV row merger into ot_hdc_v41x_attn's KV port
// (DeepSeek-V4.1 indexed layer, T = window_count + n_sel <= 128 + 512).
//
// Row order is the golden's (tools/hdc_golden_v41.py Model.attention):
// the window rows oldest first (rows 0 .. window_count-1), then the selected
// compressed rows in selection-rank order (rank k -> row window_count + k,
// ranks ascending in position).  Rows leave as the engine's four-row beats:
// beat c holds rows 4c .. 4c+3, kv_m a prefix, a partial beat only at the end
// of the job; a partial last WINDOW beat is completed by the first CKV rows.
//
// Row formats (ot_hdc_v41x_attn group word, 16 per row, 265 bits):
//   WINDOW  4,224-bit packed row: 512 E4M3 codes (bits 0..4095, element e at
//           8e) + 16 UE8M0 scales (bits 4096.., one per 32) ->
//           {1'b0, scale[g], codes[g*32 +: 32]}.
//   CKV     2,304-bit DMA row: 512 E2M1 nibbles (element e at bits 4e, low
//           nibble of byte e/2 first) + 32 E4M3 scales (bits 2048.., one per
//           16) -> {1'b1, 120'b0, scale[2g+1], scale[2g], nibbles[g*32 +: 32]}.
// Both are the rows' STORED formats; the engine's tiles dequantise them
// exactly to the golden's qdq_fp8 / qdq_fp4_e4m3 BF16 values (E2M1 x E4M3 is
// at most an 8-bit significand, so the product is exact in BF16; note that
// the DMA's own FP8 element port ROUNDS that product to E4M3 and is not the
// golden value -- this merger forwards the raw codes, never that port).
//
// Interfaces (valid/ready)
//   job     job_v/job_ready, window_count (<= 128), n_sel (<= 512).
//   window  w_v/w_ready, w_m (row mask, a prefix), w_rows (4 x 4,224): the
//           job's window rows in order, beat-aligned (a beat carries rows
//           4c .. 4c + popcount(w_m) - 1; only the last window beat may be
//           partial).  Accepted one beat per cycle.
//   ckv     c_n (rows offered, 0..4: ranks c_rank .. c_rank + c_n - 1),
//           c_rows (4 x 2,304, row j = rank c_rank + j), c_take (rows taken
//           this cycle, combinational, <= c_n): ranks 0 .. n_sel-1 in order
//           (ot_chip_v41x_ckv_sel_collect output).  Up to four rows per cycle
//           fill the open beat from its first free lane (from lane 0 in the
//           cycle a full beat leaves), so a present run of rows streams at the
//           engine's four rows per cycle.
//   kv      kv_v/kv_ready, kv_m, kv_w (ot_hdc_v41x_attn kv port, NL = 4).
//   status  done (pulse after the job's last beat), fault {rank, window mask}.
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_stream_merge #(
    parameter integer K = 512,
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 job_v,
    output wire                 job_ready,
    input  wire [7:0]           window_count,
    input  wire [KW-1:0]        n_sel,
    input  wire                 w_v,
    output wire                 w_ready,
    input  wire [3:0]           w_m,
    input  wire [4*4224-1:0]    w_rows,
    input  wire [2:0]           c_n,
    output wire [2:0]           c_take,
    input  wire [KW-1:0]        c_rank,
    input  wire [4*2304-1:0]    c_rows,
    output wire                 kv_v,
    input  wire                 kv_ready,
    output wire [3:0]           kv_m,
    output wire [4*16*265-1:0]  kv_w,
    output reg                  done,
    output reg                  fault,
    output reg  [1:0]           fault_code
);
    reg run;
    reg [7:0] wcount;
    reg [10:0] total, next_row;
    reg [2:0] nlanes;
    reg [4*16*265-1:0] beat;
    assign job_ready = !run;

    wire in_win = run && next_row < {3'b0, wcount};
    wire in_ckv = run && next_row >= {3'b0, wcount} && next_row < total;
    assign kv_v = run && (nlanes == 3'd4 || (nlanes != 0 && next_row == total));
    assign kv_m = (nlanes == 3'd4) ? 4'hf : ((4'b1 << nlanes) - 4'b1);
    assign kv_w = beat;
    wire emit = kv_v && kv_ready;
    assign w_ready = in_win && (emit || nlanes == 0);
    wire wtake = w_v && w_ready;
    wire [2:0] clane = emit ? 3'd0 : nlanes;
    wire [2:0] room = 3'd4 - clane;
    wire [10:0] cleft = total - next_row;
    wire [2:0] cmax = (cleft < 11'(room)) ? 3'(cleft) : room;
    assign c_take = !in_ckv ? 3'd0 : (c_n < cmax) ? c_n : cmax;
    wire ctake = c_take != 0;

    wire [2:0] wn = 3'(w_m[0]) + 3'(w_m[1]) + 3'(w_m[2]) + 3'(w_m[3]);
    wire [10:0] wleft = {3'b0, wcount} - next_row;
    wire [2:0] wexp = (wleft >= 11'd4) ? 3'd4 : 3'(wleft);
    wire wmask_ok = w_m == ((wexp == 3'd4) ? 4'hf : ((4'b1 << wexp) - 4'b1));

    wire [4*16*265-1:0] wfmt;
    wire [4*16*265-1:0] cfmt;
    genvar g, l;
    generate for (l = 0; l < 4; l = l + 1) begin : g_wl
        for (g = 0; g < 16; g = g + 1) begin : g_wg
            assign wfmt[(l*16 + g)*265 +: 265] =
                {1'b0, w_rows[l*4224 + 4096 + 8*g +: 8], w_rows[l*4224 + 256*g +: 256]};
        end
    end endgenerate
    generate for (l = 0; l < 4; l = l + 1) begin : g_cl
        for (g = 0; g < 16; g = g + 1) begin : g_cg
            assign cfmt[(l*16 + g)*265 +: 265] = {1'b1, 120'b0, c_rows[l*2304 + 2048 + 16*g +: 16],
                                                  c_rows[l*2304 + 128*g +: 128]};
        end
    end endgenerate
    integer lj;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; wcount <= 0; total <= 0; next_row <= 0; nlanes <= 0; beat <= 0;
            done <= 0; fault <= 0; fault_code <= 0;
        end else begin
            done <= 0;
            if (!run) begin
                if (job_v) begin
                    wcount <= window_count;
                    total <= {3'b0, window_count} + 11'(n_sel);
                    next_row <= 0; nlanes <= 0;
                    if (window_count > 8'd128 || n_sel > KW'(K)) begin fault <= 1; fault_code[1] <= 1; end
                    else if (window_count == 0 && n_sel == 0) done <= 1;
                    else run <= 1;
                end
            end else begin
                if (emit && !wtake && !ctake) nlanes <= 0;
                if (wtake) begin
                    if (!wmask_ok) begin fault <= 1; fault_code[1] <= 1; end
                    beat <= wfmt;
                    nlanes <= wn;
                    next_row <= next_row + 11'(wn);
                end else if (ctake) begin
                    if (11'(c_rank) != next_row - {3'b0, wcount}) begin fault <= 1; fault_code[0] <= 1; end
                    for (lj = 0; lj < 4; lj = lj + 1)
                        if (lj >= 32'(clane) && lj < 32'(clane) + 32'(c_take))
                            beat[lj*16*265 +: 16*265] <= cfmt[(lj - 32'(clane))*16*265 +: 16*265];
                    nlanes <= clane + c_take;
                    next_row <= next_row + 11'(c_take);
                end
                if (emit && next_row == total && !wtake && !ctake) begin
                    run <= 0; done <= 1;
                end
            end
        end
    end
endmodule

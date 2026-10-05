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
//           fill the open beat from its first free lane.
//   kv      registered (kv_v, kv_m, kv_w from one of two beat buffers); a beat is
//           offered two cycles after its last row is accepted; one beat per cycle.
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
    // Two stages so that no decision drives the 16,960-bit beat directly, and two beat buffers so
    // that the rate stays at the engine's four rows per cycle:
    //   A (control): accepts window/CKV rows into the LOGICAL beat (fill buffer f, nlanes, next_row)
    //     and registers, per lane, a load enable, a source select and the buffer; the offered rows
    //     are captured every cycle (plain registers, no enable) into w_rows_q / c_rows_q.
    //   B (datapath): buf[fb_q][lane] <= ld_q[lane] ? source(sel_q[lane]) : itself.
    // A beat completed by A in cycle t is written by B at the end of t+1 and offered (kv_v, a
    // register) from t+2; meanwhile A fills the other buffer.  A stalls only when both buffers hold
    // completed, unemitted beats.
    reg run;
    reg [7:0] wcount;
    reg [10:0] total, next_row;
    reg [2:0] nlanes;
    reg f, o;                                  // fill buffer, output buffer
    reg [1:0] full;                            // buffer holds a completed beat (not yet emitted)
    reg [1:0] rdy;                             // ... and it is physically written (offered)
    reg [3:0] m0, m1;                          // lane masks of the completed beats
    reg [4*16*265-1:0] beat0, beat1;
    reg cq, cq_b;                              // beat completed last cycle, its buffer
    assign job_ready = !run;
    assign kv_v = rdy[o];
    assign kv_m = o ? m1 : m0;
    assign kv_w = o ? beat1 : beat0;
    wire emit = kv_v && kv_ready;
    wire open_ = run && !full[f];
    wire [2:0] clane = nlanes;
    wire in_win = open_ && next_row < {3'b0, wcount};
    wire in_ckv = open_ && next_row >= {3'b0, wcount} && next_row < total;
    assign w_ready = in_win && clane == 3'd0;
    wire wtake = w_v && w_ready;
    wire [2:0] room = 3'd4 - clane;
    wire [10:0] cleft = total - next_row;
    wire [2:0] cmax = (cleft < 11'(room)) ? 3'(cleft) : room;
    assign c_take = !in_ckv ? 3'd0 : (c_n < cmax) ? c_n : cmax;
    wire ctake = c_take != 0;

    wire [2:0] wn = 3'(w_m[0]) + 3'(w_m[1]) + 3'(w_m[2]) + 3'(w_m[3]);
    wire [10:0] wleft = {3'b0, wcount} - next_row;
    wire [2:0] wexp = (wleft >= 11'd4) ? 3'd4 : 3'(wleft);
    wire wmask_ok = w_m == ((wexp == 3'd4) ? 4'hf : ((4'b1 << wexp) - 4'b1));
    wire [2:0] nl_new = wtake ? wn : (clane + c_take);
    wire [10:0] nr_new = next_row + (wtake ? 11'(wn) : 11'(c_take));
    wire beat_done = (wtake || ctake) && (nl_new == 3'd4 || nr_new == total);
    wire [3:0] mask_new = (nl_new == 3'd4) ? 4'hf : ((4'b1 << nl_new) - 4'b1);

    // stage B registers
    reg [4*4224-1:0] w_rows_q;
    reg [4*2304-1:0] c_rows_q;
    reg [3:0] ld_q;
    reg [7:0] sel_q;
    reg srcw_q, fb_q;
    always @(posedge clk) begin w_rows_q <= w_rows; c_rows_q <= c_rows; end
    integer lj;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ld_q <= 0; sel_q <= 0; srcw_q <= 0; fb_q <= 0; end
        else begin
            srcw_q <= wtake; fb_q <= f;
            for (lj = 0; lj < 4; lj = lj + 1) begin
                ld_q[lj] <= wtake ? (lj < 32'(wn)) :
                            (ctake && lj >= 32'(clane) && lj < 32'(clane) + 32'(c_take));
                sel_q[lj*2 +: 2] <= wtake ? 2'(lj) : 2'(lj - 32'(clane));
            end
        end
    end
    genvar g, l;
    generate for (l = 0; l < 4; l = l + 1) begin : g_lane
        wire [1:0] sl = sel_q[l*2 +: 2];
        wire [4223:0] wr = w_rows_q[l*4224 +: 4224];
        wire [2303:0] cr = c_rows_q[32'(sl)*2304 +: 2304];
        for (g = 0; g < 16; g = g + 1) begin : g_grp
            wire [264:0] wf = {1'b0, wr[4096 + 8*g +: 8], wr[256*g +: 256]};
            wire [264:0] cf = {1'b1, 120'b0, cr[2048 + 16*g +: 16], cr[128*g +: 128]};
            always @(posedge clk) begin
                if (ld_q[l] && !fb_q) beat0[(l*16 + g)*265 +: 265] <= srcw_q ? wf : cf;
                if (ld_q[l] && fb_q) beat1[(l*16 + g)*265 +: 265] <= srcw_q ? wf : cf;
            end
        end
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 0; f <= 0; o <= 0; full <= 0; rdy <= 0; m0 <= 0; m1 <= 0; cq <= 0; cq_b <= 0;
            wcount <= 0; total <= 0; next_row <= 0; nlanes <= 0;
            done <= 0; fault <= 0; fault_code <= 0;
        end else begin
            done <= 0;
            if (!run) begin
                if (job_v) begin
                    wcount <= window_count;
                    total <= {3'b0, window_count} + 11'(n_sel);
                    next_row <= 0; nlanes <= 0; f <= 0; o <= 0; full <= 0; rdy <= 0; cq <= 0;
                    if (window_count > 8'd128 || n_sel > KW'(K)) begin fault <= 1; fault_code[1] <= 1; end
                    else if (window_count == 0 && n_sel == 0) done <= 1;
                    else run <= 1;
                end
            end else begin
                // B finished writing the beat completed last cycle: offer it
                cq <= beat_done; cq_b <= f;
                if (cq) rdy[cq_b] <= 1'b1;
                if (emit) begin
                    rdy[o] <= 1'b0; full[o] <= 1'b0; o <= ~o;
                    if (next_row == total && full[~o] == 1'b0) begin run <= 0; done <= 1; end
                end
                if (wtake && !wmask_ok) begin fault <= 1; fault_code[1] <= 1; end
                if (ctake && 11'(c_rank) != next_row - {3'b0, wcount}) begin fault <= 1; fault_code[0] <= 1; end
                if (wtake || ctake) begin
                    next_row <= nr_new;
                    if (beat_done) begin
                        nlanes <= 0; full[f] <= 1'b1; f <= ~f;
                        if (f) m1 <= mask_new; else m0 <= mask_new;
                    end else nlanes <= nl_new;
                end
            end
        end
    end
endmodule

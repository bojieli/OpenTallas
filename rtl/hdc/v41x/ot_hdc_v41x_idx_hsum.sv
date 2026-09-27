`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Post-pool head-sum stage of the V4.1 lightning indexer (spec R-U2: the
// FP4 x FP4 index dots run on the pooled block-dot engine; this stage takes
// the pool's per-head FP32 scores and produces the key's BF16 index score).
// Bit exact to tools/hdc_golden_v41.py Model.indexer after dots_q4:
//
//   score[h] = to_bf16(sc32[h])                 sc32 = dots_q4 (the pool's row)
//   term[h]  = to_bf16(mul(max(score[h], 0), wts[h]))
//   s        = to_bf16(reduce_rows(term, cls="idx"))   chunks of 8 heads
//                                                       sequential from +0,
//                                                       a padded pairwise tree
//   out      = keep ? s : -inf
//
// The same arithmetic as the tail of ot_hdc_v41x_idx_chunk plus
// ot_hdc_v41x_idx_tail, for IH heads per key and NKT keys per cycle.
// Protocol: i_v/i_kv/i_keep/i_score/i_fault one key beat per cycle, no
// back-pressure (fixed latency; the pool's output credit covers it); o_* the
// same beat LAT cycles later.  Head weights: w_v, w_head, w_w (BF16), one head
// per cycle, before the keys they weight (2-cycle settle).
// LAT = 1 (input) + 1 (to_bf16, ReLU) + 3 (product) + 21 (7 sequential adds)
//       + 3 log2(IH/8) (tree) + 1 (to_bf16, mask, output) = 33 at IH = 32.
// Faults fail closed as in the engine: a faulted score (pool fault), a BF16
// rounding to infinity, a product overflow or an adder refusal -> fault, 0.
// The standalone engine also REFUSES a UE8M0 scale byte >= 253 in q or in the
// key; the pool lane does not, so this stage applies the same rule: a key
// refused at ingest (i_ref, from ot_hdc_v41x_idx_kmerge) or any head whose q
// was loaded with such a scale (w_qsc) faults the key; cnt_refused counts.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_hsum #(
    parameter integer IH  = 32,
    parameter integer NKT = 1,
    parameter integer NBQ = 4           // q blocks per head (scale bytes checked)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  w_v,
    input  wire [7:0]            w_head,
    input  wire [15:0]           w_w,
    input  wire [NBQ*8-1:0]      w_qsc,       // the head's q UE8M0 scale bytes (refusal check)
    input  wire                  i_v,
    input  wire [NKT-1:0]        i_kv,
    input  wire [NKT-1:0]        i_ref,       // key refused at ingest (ot_hdc_v41x_idx_kmerge o_ref)
    input  wire [NKT-1:0]        i_keep,
    input  wire [NKT*IH*32-1:0]  i_score,     // key g, head h at [(g*IH+h)*32 +: 32]
    input  wire [NKT*IH-1:0]     i_fault,
    output reg                   o_v,
    output reg  [NKT-1:0]        o_kv,
    output reg  [NKT*16-1:0]     o_score,
    output reg  [NKT-1:0]        o_fault,
    output reg  [47:0]           cnt_refused  // keys faulted by a refused key or q scale
);
    localparam integer HC = 8;
    localparam integer NCH = IH / HC;
    localparam integer LV = (NCH <= 1) ? 0 : $clog2(NCH);
    localparam integer LAT_T = 1 + 3;                 // bf16/ReLU + product (after the input register)
    localparam integer LAT_C = LAT_T + 3 * (HC - 1);  // + the chain
    localparam integer LAT = LAT_C + 3 * LV;          // + the tree

    // head weights (registered write, as the engine's q port)
    reg [IH*16-1:0] qw;
    reg             rw_v;
    reg [7:0]       rw_h;
    reg [15:0]      rw_w;
    reg             rw_r;
    reg [IH-1:0]    qref;                           // head h's q holds a scale >= 253
    integer hq;
    always @(posedge clk) begin
        rw_v <= w_v && rst_n;
        rw_h <= w_head;
        rw_w <= w_w;
        rw_r <= 1'b0;
        for (hq = 0; hq < NBQ; hq = hq + 1) if (w_qsc[8*hq +: 8] >= 8'd253) rw_r <= 1'b1;
        for (hq = 0; hq < IH; hq = hq + 1)
            if (rw_v && rw_h == hq) begin qw[16*hq +: 16] <= rw_w; qref[hq] <= rw_r; end
    end
    wire anyq = |qref;

    reg              rv;
    reg [NKT-1:0]    rkv, rkeep;
    reg [NKT*IH*32-1:0] rsc;
    reg [NKT*IH-1:0] rf;
    reg [NKT-1:0]    rref;
    always @(posedge clk) begin
        rref <= i_ref;
        rv <= i_v && rst_n;
        rkv <= i_kv;
        rkeep <= i_keep;
        rsc <= i_score;
        rf <= i_fault;
    end
    wire [2*NKT:0] vl;
    ot_hdc_delay #(.W(2 * NKT + 1), .D(LAT), .RESET(1)) u_vl (.clk(clk), .rst_n(rst_n),
        .d({rkeep, rkv, rv}), .q(vl));
    wire [NKT-1:0] refd;                            // refused (key or q), with the key
    ot_hdc_delay #(.W(NKT), .D(LAT), .RESET(1)) u_rf (.clk(clk), .rst_n(rst_n),
        .d(rref | {NKT{anyq}}), .q(refd));
    integer cr;
    reg [$clog2(NKT+1)-1:0] nrf;
    always @* begin
        nrf = 0;
        for (cr = 0; cr < NKT; cr = cr + 1) nrf = nrf + (refd[cr] & vl[1 + cr]);
    end
    always @(posedge clk)
        if (!rst_n) cnt_refused <= 0;
        else if (vl[0]) cnt_refused <= cnt_refused + nrf;

    genvar g, h, c, l, i;
    generate
        for (g = 0; g < NKT; g = g + 1) begin : g_key
            wire [IH*16-1:0] term;
            wire [IH-1:0]    tfault;
            for (h = 0; h < IH; h = h + 1) begin : g_head
                wire [15:0] sc16;
                wire        sco;
                ot_hdc_v41x_bf16 u_sb (.x(rsc[(g*IH+h)*32 +: 32]), .y(sc16), .ovf(sco));
                reg  [15:0] s1;
                reg         f1;
                always @(posedge clk) begin
                    s1 <= sc16;
                    f1 <= rf[g*IH+h] || sco;
                end
                wire [15:0] tm;
                wire        tmo, f1d;
                ot_hdc_v41x_bmul u_m (.clk(clk), .a(s1), .w(qw[16*h +: 16]), .y(tm), .ovf(tmo));
                ot_hdc_delay #(.W(1), .D(3)) u_fd (.clk(clk), .rst_n(rst_n), .d(f1), .q(f1d));
                assign term[16*h +: 16] = tm;
                assign tfault[h] = f1d || tmo;
            end
            // chunk chains: seed with the chunk's first term (-0 -> +0), 7 adds
            wire [(LV+1)*NCH*32-1:0] t;
            wire [(LV+1)*NCH-1:0]    tf;
            for (c = 0; c < NCH; c = c + 1) begin : g_ch
                wire [HC*32-1:0] cs;
                wire [HC-1:0]    cf;
                assign cs[31:0] = (term[16*(HC*c) +: 15] == 15'd0) ? 32'd0 : {term[16*(HC*c) +: 16], 16'd0};
                assign cf[0] = tfault[HC*c];
                for (i = 1; i < HC; i = i + 1) begin : g_add
                    wire [16:0] tj;
                    ot_hdc_delay #(.W(17), .D(3 * (i - 1))) u_tj (.clk(clk), .rst_n(rst_n),
                        .d({tfault[HC*c+i], term[16*(HC*c+i) +: 16]}), .q(tj));
                    wire [1:0] err;
                    wire       vo_unused;
                    ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                        .a(cs[32*(i-1) +: 32]), .b({tj[15:0], 16'd0}), .y(cs[32*i +: 32]), .err(err),
                        .valid_out(vo_unused));
                    wire pf;
                    ot_hdc_delay #(.W(1), .D(3)) u_pf (.clk(clk), .rst_n(rst_n), .d(cf[i-1] || tj[16]), .q(pf));
                    assign cf[i] = pf || (err != 2'd0);
                end
                assign t[32*c +: 32] = cs[32*(HC-1) +: 32];
                assign tf[c] = cf[HC-1];
            end
            // the pairwise tree over the chunk sums
            for (l = 0; l < LV; l = l + 1) begin : g_lv
                for (i = 0; i < (NCH >> (l + 1)); i = i + 1) begin : g_add
                    wire [1:0] err;
                    wire       vo_unused;
                    ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                        .a(t[32*(l*NCH+2*i) +: 32]), .b(t[32*(l*NCH+2*i+1) +: 32]),
                        .y(t[32*((l+1)*NCH+i) +: 32]), .err(err), .valid_out(vo_unused));
                    wire pf;
                    ot_hdc_delay #(.W(1), .D(3)) u_pf (.clk(clk), .rst_n(rst_n),
                        .d(tf[l*NCH+2*i] || tf[l*NCH+2*i+1]), .q(pf));
                    assign tf[(l+1)*NCH+i] = pf || (err != 2'd0);
                end
            end
            wire [15:0] s16;
            wire        so;
            ot_hdc_v41x_bf16 u_b (.x(t[32*LV*NCH +: 32]), .y(s16), .ovf(so));
            always @(posedge clk) begin
                o_fault[g] <= tf[LV*NCH] || so || refd[g];
                o_score[16*g +: 16] <= (tf[LV*NCH] || so || refd[g]) ? 16'd0 : (vl[1 + NKT + g] ? s16 : 16'hFF80);
            end
        end
    endgenerate
    always @(posedge clk) begin
        o_v <= vl[0] && rst_n;
        o_kv <= vl[NKT:1];
    end
endmodule

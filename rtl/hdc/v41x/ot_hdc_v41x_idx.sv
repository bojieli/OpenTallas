`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// V4.1 lightning-indexer engine: one BF16 index score per key, keys streaming
// at NK per cycle, bit exact to tools/hdc_golden_v41.py Model.indexer under
// R-ARITH (HDC_V41_ARITH=chunk8):
//
//   score[h] = to_bf16(dots_q4(q[h], key))      NB 32-blocks, exact block dots
//                                               rounded once, csum (sequential
//                                               from +0: NB <= 8)
//   term[h]  = to_bf16(mul(max(score[h], 0), wts[h]))
//   s        = to_bf16(csum_h term[h])          chunks of 8 heads sequential
//                                               from +0, chunk sums a pairwise
//                                               tree (padded with +0)
//   out      = keep ? s : -inf                   (layer-20 candidate mask)
//
// Hierarchy (every module boundary registered, inputs and outputs):
//   ot_hdc_v41x_idx_chunk   THE TILE: 8 heads x NKT keys.  NKT x 8 x NB x 32
//                           FP4 MACs/cycle; per key the 8 head scores, the 8
//                           ReLU-weight terms and the chunk's sequential sum.
//   ot_hdc_v41x_idx_tail    per key: the pairwise tree over the IH/8 chunk
//                           sums, to_bf16, the mask.
//   ot_hdc_v41x_idx_engine  NK keys/cycle: IH/8 chunk tiles of NK keys, NK
//                           tails, the valid/ready credit and output FIFO.
//
// Key format (68 B at the shipped shape): NB x 32 E2M1 codes (4 bits each,
// dim d at [4d+3:4d]) then NB UE8M0 scale bytes: KEYW = NB*136 bits.  The
// index query is loaded once per token, one head per cycle on the q-load port
// (codes, scales, BF16 head weight), before the key stream starts.
//
// Timing (ot_hdc_fastfp adds, LATENCY 3): block dots 3 cycles after the input
// register; the NB-1 sequential block adds 3 each (block i's key operands are
// skewed 3(i-1) cycles so each block dot meets the running sum); score to
// BF16 + ReLU 1; the product 2; the 7 sequential head adds 3 each; the
// output register.  Tail: input register, log2(IH/8) tree levels x 3, to_bf16
// + mask + output register.
//
// Faults fail closed: any operand or intermediate the golden would compute as
// nonfinite (a block scale >= 2^126, a block value, sum, product or BF16
// rounding past the binary32 range, an adder refusal) marks the key; its
// output is 0 with `fault` set.  Wherever every golden intermediate is finite
// the engine is bit exact.
// ---------------------------------------------------------------------------

// Seed of a sequential sum from +0: add(+0, x) = x for finite x, except that a
// negative zero (a BF16 term that rounded to -0) becomes +0.
module ot_hdc_v41x_idx_chunk #(
    parameter integer NB  = 4,        // 32-blocks per head (index_head_dim / 32)
    parameter integer NKT = 1,        // keys per cycle through this tile
    parameter integer HB  = 0         // first head of this chunk (for the q-load port)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // q load: one head per cycle
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    // keys
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    // chunk sums
    output reg                   c_v,
    output reg  [NKT-1:0]        c_kv,
    output reg  [NKT*32-1:0]     c_sum,
    output reg  [NKT-1:0]        c_fault
);
    localparam integer HC = 8;
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = 3 + 3 * (NB - 1);       // block dots + sequential block adds
    localparam integer LAT_T  = LAT_SC + 1 + 2;         // + bf16/ReLU + product
    localparam integer LAT    = LAT_T + 3 * (HC - 1);   // + 7 sequential head adds

    // -- query registers (loaded between tokens) -----------------------------------
    reg [HC*NB*128-1:0] qc;
    reg [HC*NB*8-1:0]   qs;
    reg [HC*16-1:0]     qw;
    reg              rql_v;
    reg [7:0]        rql_head;
    reg [NB*128-1:0] rql_codes;
    reg [NB*8-1:0]   rql_sc;
    reg [15:0]       rql_w;
    always @(posedge clk) begin
        rql_v <= ql_v && rst_n;
        rql_head <= ql_head;
        rql_codes <= ql_codes;
        rql_sc <= ql_sc;
        rql_w <= ql_w;
    end
    integer hq;
    always @(posedge clk)
        for (hq = 0; hq < HC; hq = hq + 1)
            if (rql_v && rql_head == HB + hq) begin
                qc[hq*NB*128 +: NB*128] <= rql_codes;
                qs[hq*NB*8 +: NB*8] <= rql_sc;
                qw[hq*16 +: 16] <= rql_w;
            end

    // -- input register ---------------------------------------------------------------
    reg              rv;
    reg [NKT-1:0]    rkv;
    reg [NKT*KW-1:0] rkey;
    always @(posedge clk) begin
        rv <= k_v && rst_n;
        rkv <= k_kv;
        rkey <= k_key;
    end

    // validity and per-key valid bits travel on a reset line
    wire [NKT:0] vl;
    ot_hdc_delay #(.W(NKT + 1), .D(LAT), .RESET(1)) u_vl (.clk(clk), .rst_n(rst_n), .d({rkv, rv}), .q(vl));

    genvar g, h, bb;
    generate
        for (g = 0; g < NKT; g = g + 1) begin : g_key
            wire [KW-1:0] key = rkey[g*KW +: KW];
            // key block i, skewed so its block dot meets the running sum
            wire [NB*128-1:0] kc;
            wire [NB*8-1:0]   ks;
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_skew
                localparam integer DS = (bb == 0) ? 0 : 3 * (bb - 1);
                wire [135:0] kb_d;
                ot_hdc_delay #(.W(136), .D(DS)) u_sk (.clk(clk), .rst_n(rst_n),
                    .d({key[NB*128 + 8*bb +: 8], key[128*bb +: 128]}), .q(kb_d));
                assign kc[128*bb +: 128] = kb_d[127:0];
                assign ks[8*bb +: 8] = kb_d[135:128];
            end

            wire [HC*16-1:0] term;
            wire [HC-1:0]    tfault;
            for (h = 0; h < HC; h = h + 1) begin : g_head
                // block dots and the sequential block sum
                wire [NB*32-1:0] acc;
                wire [NB-1:0] afault;
                for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
                    wire [31:0] bv;
                    wire        bo;
                    ot_hdc_v41x_q4dot u_d (.clk(clk), .a(qc[(h*NB+bb)*128 +: 128]), .b(kc[128*bb +: 128]),
                                           .ua(qs[(h*NB+bb)*8 +: 8]), .ub(ks[8*bb +: 8]), .y(bv), .ovf(bo));
                    if (bb == 0) begin : g_first
                        assign acc[31:0] = bv;                 // add(+0, b0) = b0 (b0 is +0 or nonzero)
                        assign afault[0] = bo;
                    end else begin : g_add
                        wire [1:0] err;
                        wire       vo_unused;
                        wire       pf;                      // fault of the running sum, carried
                        ot_hdc_delay #(.W(1), .D(3)) u_pf (.clk(clk), .rst_n(rst_n), .d(afault[bb-1]), .q(pf));
                        ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                            .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
                        // the block fault is 3 cycles younger than the sum it joins
                        wire bo_d;
                        ot_hdc_delay #(.W(1), .D(3)) u_bf (.clk(clk), .rst_n(rst_n), .d(bo), .q(bo_d));
                        assign afault[bb] = pf || bo_d || (err != 2'd0);
                    end
                end
                // score to BF16, ReLU is inside the product unit
                wire [15:0] sc16;
                wire        sco;
                ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
                reg  [15:0] rsc;
                reg         rscf;
                always @(posedge clk) begin
                    rsc <= sc16;
                    rscf <= afault[NB-1] || sco;
                end
                wire [15:0] tm;
                wire        tmo;
                ot_hdc_v41x_bmul u_m (.clk(clk), .a(rsc), .w(qw[16*h +: 16]), .y(tm), .ovf(tmo));
                wire        rscf_d;
                ot_hdc_delay #(.W(1), .D(2)) u_tf (.clk(clk), .rst_n(rst_n), .d(rscf), .q(rscf_d));
                assign term[16*h +: 16] = tm;
                assign tfault[h] = rscf_d || tmo;
            end

            // the chunk's sequential sum: seed with term 0 (-0 -> +0), then 7 adds;
            // term j joins at add j, 3(j-1) cycles after the terms are formed
            wire [HC*32-1:0] cs;
            wire [HC-1:0] cf;
            assign cs[31:0] = (term[14:0] == 15'd0) ? 32'd0 : {term[15:0], 16'd0};
            assign cf[0] = tfault[0];
            for (h = 1; h < HC; h = h + 1) begin : g_chain
                wire [16:0] tj;
                ot_hdc_delay #(.W(17), .D(3 * (h - 1))) u_tj (.clk(clk), .rst_n(rst_n),
                    .d({tfault[h], term[16*h +: 16]}), .q(tj));
                wire [1:0] err;
                wire       vo_unused;
                ot_hdc_fp32_add_fast u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                    .a(cs[32*(h-1) +: 32]), .b({tj[15:0], 16'd0}), .y(cs[32*h +: 32]), .err(err), .valid_out(vo_unused));
                wire pf;
                ot_hdc_delay #(.W(1), .D(3)) u_pf (.clk(clk), .rst_n(rst_n), .d(cf[h-1] || tj[16]), .q(pf));
                assign cf[h] = pf || (err != 2'd0);
            end
            always @(posedge clk) begin
                c_sum[32*g +: 32] <= cs[32*(HC-1) +: 32];
                c_fault[g] <= cf[HC-1];
            end
        end
    endgenerate
    always @(posedge clk) begin
        c_v <= vl[0] && rst_n;
        c_kv <= vl[NKT:1];
    end
endmodule

// ---------------------------------------------------------------------------
// Per key: the pairwise tree over NCH chunk sums (NCH a power of two), to_bf16,
// the candidate mask (keep = 0 -> -inf), registered output.  LATENCY
// 1 + 3 log2(NCH) + 1.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_tail #(
    parameter integer NCH = 4,
    parameter integer NKT = 1
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  i_v,
    input  wire [NKT-1:0]        i_kv,
    input  wire [NKT-1:0]        i_keep,
    input  wire [NKT*NCH*32-1:0] i_sum,     // key g, chunk c at [(g*NCH+c)*32 +: 32]
    input  wire [NKT*NCH-1:0]    i_fault,
    output reg                   o_v,
    output reg  [NKT-1:0]        o_kv,
    output reg  [NKT*16-1:0]     o_score,
    output reg  [NKT-1:0]        o_fault
);
    localparam integer LV = (NCH <= 1) ? 0 : $clog2(NCH);
    reg                  rv;
    reg [NKT-1:0]        rkv, rkeep;
    reg [NKT*NCH*32-1:0] rsum;
    reg [NKT*NCH-1:0]    rf;
    always @(posedge clk) begin
        rv <= i_v && rst_n;
        rkv <= i_kv;
        rkeep <= i_keep;
        rsum <= i_sum;
        rf <= i_fault;
    end
    wire [2*NKT:0] vl;
    ot_hdc_delay #(.W(2 * NKT + 1), .D(3 * LV), .RESET(1)) u_vl (.clk(clk), .rst_n(rst_n),
        .d({rkeep, rkv, rv}), .q(vl));
    genvar g, l, i;
    generate
        for (g = 0; g < NKT; g = g + 1) begin : g_key
            // level l holds NCH >> l partial sums
            // level l, partial i at index l * NCH + i
            wire [(LV+1)*NCH*32-1:0] t;
            wire [(LV+1)*NCH-1:0]    tf;
            for (i = 0; i < NCH; i = i + 1) begin : g_in
                assign t[32*i +: 32] = rsum[(g * NCH + i) * 32 +: 32];
                assign tf[i] = rf[g * NCH + i];
            end
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
                o_fault[g] <= tf[LV*NCH] || so;
                o_score[16*g +: 16] <= (tf[LV*NCH] || so) ? 16'd0 : (vl[1 + NKT + g] ? s16 : 16'hFF80);
            end
        end
    endgenerate
    always @(posedge clk) begin
        o_v <= vl[0] && rst_n;
        o_kv <= vl[NKT:1];
    end
endmodule

// ---------------------------------------------------------------------------
// The engine: NK keys per beat.
//
// Protocol.  Keys: valid/ready.  A beat (k_valid && k_ready) carries NK key
// slots; k_kv marks the slots holding a key (a scan's last beat may be
// partial), k_keep the candidate mask (1 = scored, 0 = -inf).  Scores:
// valid/ready, one beat per key beat, in key order, the same slots; o_fault
// per slot.  The datapath never stalls: k_ready is a credit test -- beats in
// flight plus beats held in the output FIFO stay within FD -- so with a
// consumer that is always ready the engine takes a beat every cycle, and a
// consumer that stalls backs the key stream up without losing a beat.  FD >=
// LATENCY + 2 sustains one beat per cycle.  q load: ql_v, head index, codes,
// scales, BF16 weight; one head per cycle, before the keys it scores.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_engine #(
    parameter integer NK = 8,          // keys per cycle
    parameter integer IH = 32,         // index heads
    parameter integer NB = 4,          // 32-blocks per head
    parameter integer FD = 64          // output FIFO depth (beats)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 ql_v,
    input  wire [7:0]           ql_head,
    input  wire [NB*128-1:0]    ql_codes,
    input  wire [NB*8-1:0]      ql_sc,
    input  wire [15:0]          ql_w,
    input  wire                 k_valid,
    output wire                 k_ready,
    input  wire [NK-1:0]        k_kv,
    input  wire [NK-1:0]        k_keep,
    input  wire [NK*NB*136-1:0] k_key,
    output reg                  o_valid,
    input  wire                 o_ready,
    output reg  [NK-1:0]        o_kv,
    output reg  [NK*16-1:0]     o_score,
    output reg  [NK-1:0]        o_fault
);
    localparam integer NCH = IH / 8;
    localparam integer LVT = (NCH <= 1) ? 0 : $clog2(NCH);
    localparam integer LAT_C = 1 + 3 + 3 * (NB - 1) + 1 + 2 + 3 * 7 + 1;   // chunk in-reg .. out-reg
    localparam integer LAT_T = 1 + 3 * LVT + 1;
    localparam integer LAT = LAT_C + LAT_T;                              // k beat -> tail output
    localparam integer CW = $clog2(FD + 1);

    wire take = k_valid && k_ready;

    // chunks
    wire [NCH-1:0]        cv;
    wire [NK-1:0]         ckv [0:NCH-1];
    wire [NK*32-1:0]      csum [0:NCH-1];
    wire [NK-1:0]         cfl [0:NCH-1];
    genvar c, g;
    generate
        for (c = 0; c < NCH; c = c + 1) begin : g_ch
            ot_hdc_v41x_idx_chunk #(.NB(NB), .NKT(NK), .HB(8 * c)) u_c (
                .clk(clk), .rst_n(rst_n), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                .ql_w(ql_w), .k_v(take), .k_kv(k_kv), .k_key(k_key),
                .c_v(cv[c]), .c_kv(ckv[c]), .c_sum(csum[c]), .c_fault(cfl[c]));
        end
    endgenerate
    // the mask travels beside the chunks
    wire [NK-1:0] keep_d;
    ot_hdc_delay #(.W(NK), .D(LAT_C)) u_keep (.clk(clk), .rst_n(rst_n), .d(k_keep), .q(keep_d));
    reg [NK*NCH*32-1:0] tsum;
    reg [NK*NCH-1:0]    tfl;
    integer ci, gi;
    always @* begin
        for (gi = 0; gi < NK; gi = gi + 1)
            for (ci = 0; ci < NCH; ci = ci + 1) begin
                tsum[(gi * NCH + ci) * 32 +: 32] = csum[ci][32 * gi +: 32];
                tfl[gi * NCH + ci] = cfl[ci][gi];
            end
    end
    wire              tv;
    wire [NK-1:0]     tkv, tf;
    wire [NK*16-1:0]  ts;
    ot_hdc_v41x_idx_tail #(.NCH(NCH), .NKT(NK)) u_t (.clk(clk), .rst_n(rst_n), .i_v(cv[0]), .i_kv(ckv[0]),
        .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));

    // output FIFO behind a registered output; a beat bypasses the FIFO when it
    // is empty and the output register is free.  Credit: beats in flight plus
    // beats in the FIFO plus the output register stay within FD.
    localparam integer EW = NK * 18;
    localparam integer PW = (FD <= 2) ? 1 : $clog2(FD);
    reg [EW-1:0] fm [0:FD-1];
    reg [CW-1:0] fcnt, infl;
    reg [PW-1:0] wp, rp;
    wire deq = o_valid && o_ready;
    wire out_free = !o_valid || o_ready;
    wire from_fifo = (fcnt != 0) && out_free;
    wire bypass = tv && (fcnt == 0) && out_free;
    wire push = tv && !bypass;
    assign k_ready = rst_n && ((infl + fcnt + (o_valid ? 1 : 0)) < FD);
    always @(posedge clk) begin
        if (!rst_n) begin
            fcnt <= 0; infl <= 0; wp <= 0; rp <= 0; o_valid <= 1'b0;
        end else begin
            infl <= infl + (take ? 1 : 0) - (tv ? 1 : 0);
            if (push) begin
                fm[wp] <= {tf, tkv, ts};
                wp <= (wp == FD - 1) ? 0 : wp + 1;
            end
            fcnt <= fcnt + (push ? 1 : 0) - (from_fifo ? 1 : 0);
            if (from_fifo) begin
                {o_fault, o_kv, o_score} <= fm[rp];
                rp <= (rp == FD - 1) ? 0 : rp + 1;
                o_valid <= 1'b1;
            end else if (bypass) begin
                {o_fault, o_kv, o_score} <= {tf, tkv, ts};
                o_valid <= 1'b1;
            end else if (deq) o_valid <= 1'b0;
        end
    end
endmodule

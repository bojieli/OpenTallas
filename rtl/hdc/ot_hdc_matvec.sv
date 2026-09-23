`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Matrix-vector engine of the hardwired decode core.
//
// W lanes, each a pipelined FP32 multiply feeding a pipelined FP32 add.  A lane
// holds IL outputs in flight: the add result circulates back after exactly IL
// cycles (adder latency 5 plus IL-5 delay), so each output accumulates its K
// products strictly in order -- y = (((0 + w0 x0) + w1 x1) + ...) -- while the
// lane still retires one multiply-accumulate per cycle.  No accumulator file,
// no stall: the issue loop never waits, because weights come from a ROM (or
// the KV SRAM) at a fixed latency.
//
// Element order: tile t, then k, then slot j.  Output n = (t*IL + j)*W + l is
// lane l's slot j of tile t; its weight is lane l of word
// base + t*ts + k*ks + j*js.  x[k] is read once per k, BF16-rounded (RNE) when
// `round` is set.  Results are written one W-wide word per slot on the last k.
// An optional argmax (lowest index on ties) watches the result stream.
//
// Timing from an issue cycle c: memories return at c+1 (synchronous read),
// operands are captured at c+2 and conditioned at c+3, the product leaves the
// multiplier at c+8, the sum leaves the adder at c+13 and a result is written
// at c+14.
// ---------------------------------------------------------------------------
module ot_hdc_matvec #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    // instruction
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire              i_wsrc,      // 0 weight ROM (bf16), 1 KV SRAM (fp32)
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire              i_oen,
    input  wire              i_amax,
    // weight ROM
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [W*16-1:0]   wrom_q,
    // KV SRAM
    output reg               kv_re,
    output reg  [AW-1:0]     kv_addr,
    input  wire [W*32-1:0]   kv_q,
    // x read (vector memory, element)
    output reg               x_re,
    output reg  [AW-1:0]     x_addr,
    input  wire [31:0]       x_q,
    // result words
    output reg               ov,          // a result word (whether or not written)
    output reg               o_we,
    output reg  [AW-1:0]     o_addr,
    output reg  [W-1:0]      o_mask,
    output reg  [W*32-1:0]   o_data,
    // argmax
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    output wire              fault
);
    localparam integer LW = $clog2(W);
    localparam integer FB = IL - 5;       // circulation delay after the adder
    localparam integer TAGD = 13;         // issue -> adder output

    // -- issue loop -----------------------------------------------------------
    reg              active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r;
    reg [AW-1:0]     ts_r, ks_r, js_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, oa, ot;
    reg [NW:0]       nb, nb_t;             // first output index of the current slot / tile
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);

    assign ready = !active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 1'b0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 1'b0;
            if (go) begin
                active <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; k_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                ts_r <= i_ts; ks_r <= i_ks; js_r <= i_js;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= (i_k == 1);
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; oa <= i_obase; ot <= i_obase;
                nb <= 0; nb_t <= 0;
            end
        end else begin
            // this cycle's element: (t, k, j) at `cur`
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur; kv_addr <= cur;
            x_re <= (j == 0); x_addr <= xk;
            if (!j_last) begin
                j <= j + 1'b1; cur <= cur + js_r; oa <= oa + 1'b1; nb <= nb + W;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k + 1'b1; k_last <= (k + 2 == k_r);
                    base_k <= base_k + ks_r; cur <= base_k + ks_r; xk <= xk + 1'b1;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk - (k_r - 1'b1);
                    if (!t_last) begin
                        t <= t + 1'b1; t_last <= (t + 2 == tiles_r);
                        base_t <= base_t + ts_r; base_k <= base_t + ts_r; cur <= base_t + ts_r;
                        ot <= ot + IL; oa <= ot + IL;
                        nb_t <= nb_t + W * IL; nb <= nb_t + W * IL;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end

    // Tag of the element issued this cycle (registered alongside the address).
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round;
    reg [AW-1:0] e_oa;
    reg [NW:0]   e_nb;
    reg [NW:0]   e_rem;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0;
        else e_v <= active;
    end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= k_last;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsrc_r; e_round <= round_r;
        e_oa <= oa; e_nb <= nb; e_rem <= {1'b0, nout_r} - nb;
    end

    // -- operand capture (c+2) and conditioning (c+3) ------------------------
    // Stage 1 (c+1): the memories present data; the tag moves on.
    reg          s1_v, s1_first, s1_last, s1_oen, s1_amax, s1_wsrc, s1_round, s1_xnew;
    reg [AW-1:0] s1_oa;
    reg [NW:0]   s1_nb;
    reg [W-1:0]  s1_mask;
    integer l;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= e_v;
    end
    always @(posedge clk) begin
        s1_first <= e_first; s1_last <= e_last; s1_oen <= e_oen; s1_amax <= e_amax;
        s1_wsrc <= e_wsrc; s1_round <= e_round; s1_oa <= e_oa; s1_nb <= e_nb;
        s1_xnew <= x_re;   // x_re is registered with the same element
        for (l = 0; l < W; l = l + 1)
            s1_mask[l] <= !e_rem[NW] && (e_rem > l);
    end
    // Stage 2 (c+2): capture memory data.
    reg          s2_v, s2_first, s2_last, s2_oen, s2_amax, s2_round, s2_xnew;
    reg [AW-1:0] s2_oa;
    reg [NW:0]   s2_nb;
    reg [W-1:0]  s2_mask;
    reg [W*32-1:0] s2_w;
    reg [31:0]   s2_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= s1_v;
    end
    always @(posedge clk) begin
        s2_first <= s1_first; s2_last <= s1_last; s2_oen <= s1_oen; s2_amax <= s1_amax;
        s2_round <= s1_round; s2_xnew <= s1_xnew; s2_oa <= s1_oa; s2_nb <= s1_nb; s2_mask <= s1_mask;
        for (l = 0; l < W; l = l + 1)
            s2_w[32*l +: 32] <= s1_wsrc ? kv_q[32*l +: 32] : {wrom_q[16*l +: 16], 16'h0000};
        s2_x <= x_q;
    end
    // Stage 3 (c+3): BF16-round x once per k and hold it for the IL slots.
    reg          s3_v, s3_first;
    reg [31:0]   x_hold;
    reg [W*32-1:0] s3_w;
    wire [31:0]  x_bf16 = (s2_x + 32'h7FFF + {31'd0, s2_x[16]}) & 32'hFFFF0000;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_first <= s2_first;
        s3_w <= s2_w;
        if (s2_xnew) x_hold <= s2_round ? x_bf16 : s2_x;
    end
    // The rest of the tag rides a delay line from c+3 to the adder output (c+13).
    localparam integer TW = 1 + 1 + 1 + AW + (NW + 1) + W;
    wire [TW-1:0] tag_in = {s2_last, s2_oen, s2_amax, s2_oa, s2_nb, s2_mask};
    reg  [TW-1:0] s3_tag;
    always @(posedge clk) s3_tag <= tag_in;
    wire [TW-1:0] a_tag;
    ot_hdc_delay #(.W(TW), .D(10)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag));
    wire [10:0] vline;
    ot_hdc_vline #(.D(10)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    wire [5:0] fl_first;
    ot_hdc_vline #(.D(5)) u_first (.clk(clk), .rst_n(rst_n), .v(s3_first && s3_v), .vd(fl_first));

    // -- lanes -------------------------------------------------------------------
    wire [W*32-1:0] sum;
    wire [W-1:0]    lfault;
    genvar g;
    generate
        for (g = 0; g < W; g = g + 1) begin : g_lane
            wire [31:0] prod, fb, acc_in;
            wire f0, f1;
            ot_hdc_fmul u_mul (clk, rst_n, s3_v, s3_w[32*g +: 32], x_hold, prod, f0);
            // add input at c+8; the circulating sum from IL cycles earlier
            assign acc_in = fl_first[5] ? 32'd0 : fb;
            ot_hdc_fadd u_add (clk, rst_n, vline[5], acc_in, prod, sum[32*g +: 32], f1);
            ot_hdc_delay #(.W(32), .D(FB)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*g +: 32]), .q(fb));
            assign lfault[g] = f0 | f1;
        end
    endgenerate
    assign fault = |lfault;

    // -- results (c+13 -> written c+14) ----------------------------------------
    wire          r_v = vline[10];
    wire          r_last, r_oen, r_amax;
    wire [AW-1:0] r_oa;
    wire [NW:0]   r_nb;
    wire [W-1:0]  r_mask;
    assign {r_last, r_oen, r_amax, r_oa, r_nb, r_mask} = a_tag;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov <= 1'b0; o_we <= 1'b0;
        end else begin
            ov <= r_v && r_last;
            o_we <= r_v && r_last && r_oen;
        end
    end
    always @(posedge clk) begin
        o_addr <= r_oa; o_mask <= r_mask; o_data <= sum;
    end

    // -- argmax: a registered compare tree over the word, then a running best --
    // Keys order binary32 values as unsigned integers (zeros are canonical +0).
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer LV = (LW < 1) ? 1 : LW;
    // level lv holds W >> lv candidates: {valid, key, value, index}
    localparam integer CW = 1 + 32 + 32 + NW;
    wire [CW*W-1:0] lvl [0:LV];
    reg  [LV:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LV-1:0], r_v && r_last && r_amax};
    end
    genvar lv, e;
    generate
        for (e = 0; e < W; e = e + 1) begin : g_leaf
            reg [CW-1:0] c;
            always @(posedge clk)
                c <= {r_mask[e], okey(sum[32*e +: 32]), sum[32*e +: 32], r_nb[NW-1:0] + e[NW-1:0]};
            assign lvl[0][CW*e +: CW] = c;
        end
        for (lv = 1; lv <= LV; lv = lv + 1) begin : g_lvl
            for (e = 0; e < (W >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = lvl[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = lvl[lv-1][CW*(2*e+1) +: CW];
                reg  [CW-1:0] c;
                // lower index wins ties
                always @(posedge clk)
                    c <= (x0[CW-1] && (!x1[CW-1] || x0[CW-2 -: 32] >= x1[CW-2 -: 32])) ? x0 : x1;
                assign lvl[lv][CW*e +: CW] = c;
            end
            if ((W >> lv) < W) begin : g_pad
                assign lvl[lv][CW*W-1 : CW*(W >> lv)] = 0;
            end
        end
    endgenerate
    wire [CW-1:0] top = lvl[LV][CW-1:0];
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top[CW-34 -: 32];
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any <= 1'b0; am_idx <= 0; am_val <= 0; best_key <= 0;
        end else begin
            if (go && ready && i_amax) am_any <= 1'b0;
            else if (tv[LV] && top_v && (!am_any || top_key > best_key)) begin
                am_any <= 1'b1; best_key <= top_key; am_idx <= top_idx; am_val <= top_val;
            end
        end
    end

    assign idle = !active && !e_v && !s1_v && !s2_v && !s3_v && !(|vline) && !(|tv) && !ov;
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Expert union of a multi-position pass (DSpark verify / draft) on the V4.1 HBM
// comparator (default-off build).
//
// A verify pass carries P positions as P MMA columns of one weight pass.  Each
// position's router selects its own top-K routed experts; the layer streams the
// UNION of those experts once from HBM (ot_gpu_expert_fetch), and each expert's
// weight pass runs only the columns (positions) that selected it -- per column the
// arithmetic is exactly the one-position step's (MoE grouped GEMM, as a GPU's
// token-sorted expert dispatch does it).
//
//   clr      start a new union (the layer's first column);
//   add      one column's K ids (ascending, from ot_gpu_router_topk) and its column
//            number: sets the expert's bit and the column's bit of its mask;
//   flush    every column added: the union streams out ascending by id (the golden
//            runs and sums the experts in id order), one {id, column mask} a cycle
//            on a valid/ready port, last on the final one; an empty union never
//            happens (K >= 1).
// Scan: NE bits in WB-bit words, a find-first-set over the current word per cycle,
// an empty word skipped in one cycle (NE = 384, WB = 32: <= 12 idle cycles).
// ---------------------------------------------------------------------------
module ot_dshbm_expert_union_m #(
    parameter integer NE = 384,
    parameter integer K  = 6,
    parameter integer PM = 8,        // columns (positions) a pass
    parameter integer IW = 9,
    parameter integer WB = 32,
    parameter integer FAST = 0       // 1: 1.2 GHz SS successor (registered scan state + registered output slice:
                                     //    same {id, mask, last} stream, +1 cycle from flush to the first id)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              clr,
    input  wire              add_v,
    input  wire [$clog2(PM)-1:0] add_col,
    input  wire [K*IW-1:0]   add_ids,
    input  wire [K-1:0]      add_en,      // per id (K_eff <= K)
    input  wire              flush,
    output wire              out_v,
    input  wire              out_ready,
    output wire [IW-1:0]     out_id,
    output wire [PM-1:0]     out_mask,
    output wire              out_last,
    output wire              busy,
    output reg  [IW:0]       count        // union size of the last flush
);
    localparam integer NW = (NE + WB - 1) / WB;
    localparam integer NB = NW * WB;
    localparam integer WW = (NW > 1) ? $clog2(NW) : 1;
    localparam integer BW = $clog2(WB);
    reg [NB-1:0] sel;
    reg [PM-1:0] msk [0:NE-1];
    reg          scan;
    reg [WW-1:0] wp;
    integer i, k;
    generate if (FAST == 0) begin : g_base
    // current word and its lowest set bit
    wire [WB-1:0] word = sel[wp*WB +: WB];
    reg  [BW-1:0] ffs;
    reg           hit;
    always @(*) begin
        ffs = 0; hit = 1'b0;
        for (i = WB - 1; i >= 0; i = i - 1)
            if (word[i]) begin ffs = i; hit = 1'b1; end
    end
    wire [IW-1:0] cur = wp * WB + ffs;
    // is there another set bit after `cur`?  (the rest of this word or a later word)
    reg more;
    always @(*) begin
        more = 1'b0;
        for (i = 0; i < NB; i = i + 1)
            if (i > cur && sel[i]) more = 1'b1;
    end
    assign out_v    = scan && hit;
    assign out_id   = cur;
    assign out_mask = msk[cur];
    assign out_last = out_v && !more;
    assign busy     = scan;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel <= 0; scan <= 1'b0; wp <= 0; count <= 0;
        end else begin
            if (clr) begin
                sel <= 0;
                for (k = 0; k < NE; k = k + 1) msk[k] <= 0;
            end else if (add_v) begin
                for (k = 0; k < K; k = k + 1)
                    if (add_en[k]) begin
                        sel[add_ids[k*IW +: IW]] <= 1'b1;
                        msk[add_ids[k*IW +: IW]][add_col] <= 1'b1;
                    end
            end
            if (flush && !scan) begin
                scan <= 1'b1; wp <= 0; count <= 0;
            end else if (scan) begin
                if (!hit) begin
                    if (wp == NW - 1) scan <= 1'b0;
                    else wp <= wp + 1;
                end else if (out_ready) begin
                    sel[cur] <= 1'b0;
                    count <= count + 1;
                    if (!more) scan <= 1'b0;
                end
            end
        end
    end
    end else begin : g_fast
    // FAST = 1 (exact stream; WB a power of two): the scanner keeps the current word as a REGISTERED one-hot
    // head (hoh: its lowest set bit) plus the rest (word_r), the word's column masks (mw_r), a one-hot of the
    // NEXT word (wn_oh) and a "a later word is non-empty" flag, so every pick runs register to register.  Its
    // stream {id, mask, last} enters a two-entry registered output slice (full throughput): the port is
    // registers only and out_ready only reaches the slice.  The emitted stream equals FAST = 0's; the first id
    // leaves one cycle later; busy covers the slice; count is final when busy drops.
    // Protocol (as the DSpark top drives it): no add or clr while a scan runs.
    reg [WB-1:0]    hoh, word_r;
    reg [PM*WB-1:0] mw_r;
    reg [NW-1:0]    wn_oh;                  // one-hot of wp + 1
    reg             later_r;
    function automatic [WB-1:0] lowest(input [WB-1:0] x);
        integer q;
        reg seen;
        begin
            seen = 1'b0;
            for (q = 0; q < WB; q = q + 1) begin lowest[q] = x[q] && !seen; seen = seen || x[q]; end
        end
    endfunction
    reg  [BW-1:0]   ffs;
    reg  [PM-1:0]   om;
    always @(*) begin
        ffs = 0; om = 0;
        for (i = 0; i < WB; i = i + 1)
            if (hoh[i]) begin ffs = ffs | i[BW-1:0]; om = om | mw_r[i*PM +: PM]; end
    end
    wire hit  = |hoh;
    wire more = (|word_r) || later_r;
    wire [IW-1:0] cur = wp * WB + ffs;
    reg [NW-1:0] wnz;
    always @(*) for (i = 0; i < NW; i = i + 1) wnz[i] = |sel[i*WB +: WB];
    reg [PM*WB-1:0] mw_n;
    reg [WB-1:0]    word_n, low_n, low_r;
    reg             later_n;
    reg [NW-1:0]    wl_oh;                  // the word the scan loads this cycle (one-hot)
    reg [NW-1:0]    above;                  // words after the loaded one
    always @(*) begin
        wl_oh = (flush && !scan) ? {{(NW-1){1'b0}}, 1'b1} : wn_oh;
        word_n = 0; mw_n = 0; above = 0;
        for (i = 0; i < NW; i = i + 1)
            if (wl_oh[i]) word_n = word_n | sel[i*WB +: WB];
        for (i = 0; i < NB; i = i + 1)
            if (wl_oh[i / WB] && i < NE) mw_n[(i % WB)*PM +: PM] = mw_n[(i % WB)*PM +: PM] | msk[i];
        for (i = 1; i < NW; i = i + 1) above[i] = above[i-1] | wl_oh[i-1];
        later_n = |(wnz & above);
        low_n = lowest(word_n);
        low_r = lowest(word_r);
    end
    // ---- output slice ----
    localparam integer DW = IW + PM + 1;
    reg          v0, v1;
    reg [DW-1:0] q0, q1;
    wire         iready = !v1;
    wire         iv = scan && hit;
    wire [DW-1:0] id_ = {cur, om, !more};
    assign out_v    = v0;
    assign out_id   = q0[DW-1 -: IW];
    assign out_mask = q0[1 +: PM];
    assign out_last = v0 && q0[0];
    assign busy     = scan || v0 || v1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v0 <= 1'b0; v1 <= 1'b0; end
        else if (!v0 || out_ready) begin
            v0 <= v1 || (iv && iready); q0 <= v1 ? q1 : id_; v1 <= 1'b0;
        end else if (iv && iready) begin
            v1 <= 1'b1; q1 <= id_;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel <= 0; scan <= 1'b0; wp <= 0; count <= 0; hoh <= 0; word_r <= 0; mw_r <= 0; later_r <= 1'b0;
            wn_oh <= {{(NW-2){1'b0}}, 2'b10};
        end else begin
            if (clr) begin
                sel <= 0;
                for (k = 0; k < NE; k = k + 1) msk[k] <= 0;
            end else if (add_v) begin
                for (k = 0; k < K; k = k + 1)
                    if (add_en[k]) begin
                        sel[add_ids[k*IW +: IW]] <= 1'b1;
                        msk[add_ids[k*IW +: IW]][add_col] <= 1'b1;
                    end
            end
            if (flush && !scan) begin
                scan <= 1'b1; wp <= 0; count <= 0; wn_oh <= {{(NW-2){1'b0}}, 2'b10};
                hoh <= low_n; word_r <= word_n & ~low_n; mw_r <= mw_n; later_r <= later_n;
            end else if (scan) begin
                if (!hit) begin
                    if (wp == NW - 1) scan <= 1'b0;
                    else begin
                        wp <= wp + 1; wn_oh <= {wn_oh[NW-2:0], 1'b0};
                        hoh <= low_n; word_r <= word_n & ~low_n; mw_r <= mw_n; later_r <= later_n;
                    end
                end else if (iready) begin
                    sel[cur] <= 1'b0;
                    hoh <= low_r; word_r <= word_r & ~low_r;
                    count <= count + 1;
                    if (!more) scan <= 1'b0;
                end
            end
        end
    end
    end endgenerate
endmodule

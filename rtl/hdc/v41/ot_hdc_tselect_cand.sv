`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Candidate-block SELECT of the V4.1 indexer at shipped scale (layer 20):
// block max over 8 positions, pin the newest block, top-K blocks, ties to the
// lower block index.  A block-max front end on ot_hdc_tselect.
//
// Semantics are tools/hdc_golden_v41.py `Model.candidate_blocks`:
//     bs[i]   = max(s[8i .. 8i+7])            (positions past n are -inf)
//     bs[(n-1) // 8] = +inf                   (the newest block is pinned)
//     keep[i] = i in topk_lowest_index(bs, min(K, nb)) and bs[i] > -inf
// The unit emits the selected blocks in ascending block order (tselect's
// position-order output) with the block max as the value (key-canonical: a
// zero maximum leaves as +0) and out_ninf set for a -inf block, which the
// consumer drops (keep = selected and not ninf).
//
// Contract.  One segment is a die's (or the whole context's) index scores in
// ascending position order, P lanes per beat under valid/ready, positions
// DENSE: every beat but the last has all P lanes valid and the last beat's
// valid lanes are a non-empty prefix (lane 0 first).  `in_base` on the first
// beat is the block index of lane 0 (the range starts on a block boundary);
// `in_pin` with `in_last` pins the block holding the segment's last valid
// position (set it on the die that holds the newest position, or always for
// one unit); `in_k` with `in_last` is the runtime K.  Scores are BF16, NaN is
// outside the contract.
//
// Datapath: stage 1 lane keys (ot_hdc_tselect's order-preserving key, empty
// lanes as the key of -inf), stage 2 two max levels (64 -> 16), stage 3 the
// third level (-> P/8 block maxima), the pin and the key-to-BF16 inverse; a
// line register packs WB/(P/8) input beats into one WB-lane tselect beat.  A
// stall (the line waiting on tselect's in_ready, which is low only while a
// previous segment is still being selected) holds the whole front end.
//
// Latency, from the edge that accepts the last input beat to the out_last
// beat: 4 + tselect's 2 NL + LAT0 (+1), NL = ceil(blocks / WB); LAT0 = 47 at
// WB = 64.  At WB = 64 the tselect ingests one line per 8 input beats, so the
// block rate matches a 64-position score stream exactly and the two passes
// after the stream cost 2 x blocks / 64 cycles.
// ---------------------------------------------------------------------------
module ot_hdc_tselect_cand #(
    parameter integer P  = 64,        // score lanes per input beat (multiple of 8)
    parameter integer WB = 64,        // tselect lanes (multiple of P/8, WB*8/P a power of two)
    parameter integer IW = 17,        // block index width
    parameter integer K  = 2048,      // largest runtime K (candidate_topk_blocks)
    parameter integer AW = 11,        // tselect line-address width: at most 2^AW lines of WB blocks
    parameter integer KW = $clog2(K + 1)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_ready,
    input  wire              in_last,
    input  wire              in_pin,
    input  wire [P-1:0]      in_lv,
    input  wire [P*16-1:0]   in_val,
    input  wire [IW-1:0]     in_base,
    input  wire [KW-1:0]     in_k,
    output wire              out_valid,
    output wire              out_last,
    output wire [WB-1:0]     out_lv,
    output wire [WB*16-1:0]  out_val,
    output wire [WB*IW-1:0]  out_idx,
    output wire [WB-1:0]     out_ninf,
    output wire              mem_we,
    output wire [AW-1:0]     mem_waddr,
    output wire [WB*(17+IW)-1:0] mem_wdata,
    output wire              mem_re,
    output wire [AW-1:0]     mem_raddr,
    input  wire [WB*(17+IW)-1:0] mem_rdata,
    output wire              busy
);
    localparam integer NB  = P / 8;                 // blocks per input beat
    localparam integer R   = WB / NB;               // input beats per tselect line
    localparam integer RS  = (R > 1) ? $clog2(R) : 1;
    localparam [15:0]  KEY_NINF = 16'h007F;         // key of -inf (0xFF80)
    localparam [15:0]  PINF = 16'h7F80;
    localparam integer RM1I = R - 1;
    localparam [RS-1:0] RM1 = RM1I[RS-1:0];
    localparam integer NBI = NB;
    localparam [IW-1:0] NBW = NBI[IW-1:0];

    function automatic [15:0] fkey(input [15:0] v);
        fkey = (v[14:0] == 0) ? 16'h8000 : v[15] ? ~v : {1'b1, v[14:0]};
    endfunction
    function automatic [15:0] kmax(input [15:0] a, input [15:0] b);
        kmax = (a >= b) ? a : b;
    endfunction

    // tselect input line
    reg              line_v, line_last;
    reg  [WB-1:0]    line_lv;
    reg  [WB*16-1:0] line_val;
    reg  [WB*IW-1:0] line_idx;
    reg  [KW-1:0]    line_k;
    wire             t_ready;
    wire             adv = !(line_v && !t_ready);
    assign in_ready = adv;
    wire acc = in_valid && adv;

    // -- stage 1: lane keys, block flags, block index of lane 0 ---------------------------
    reg              first;
    reg  [IW-1:0]    bcnt;
    reg              a1_v, a1_last;
    reg  [KW-1:0]    a1_k;
    reg  [P*16-1:0]  a1_key;
    reg  [NB-1:0]    a1_bv, a1_bp;
    reg  [IW-1:0]    a1_idx;
    wire [P*16-1:0]  key_d;
    wire [NB-1:0]    bv_d, bp_d;
    genvar gl, gb;
    generate
        for (gl = 0; gl < P; gl = gl + 1) begin : g_key
            assign key_d[16*gl +: 16] = in_lv[gl] ? fkey(in_val[16*gl +: 16]) : KEY_NINF;
        end
        for (gb = 0; gb < NB; gb = gb + 1) begin : g_bf
            assign bv_d[gb] = in_lv[8*gb];
            if (gb == NB - 1) begin : g_lastb
                assign bp_d[gb] = in_last && in_pin && in_lv[8*gb];
            end else begin : g_midb
                assign bp_d[gb] = in_last && in_pin && in_lv[8*gb] && !in_lv[8*gb + 8];
            end
        end
    endgenerate
    wire [IW-1:0] base_now = first ? in_base : bcnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a1_v <= 1'b0; first <= 1'b1; end
        else if (adv) begin
            a1_v <= acc;
            if (acc) first <= in_last;
        end
    end
    always @(posedge clk) if (adv) begin
        a1_last <= in_last; a1_k <= in_k; a1_key <= key_d; a1_bv <= bv_d; a1_bp <= bp_d;
        a1_idx <= base_now;
        if (acc) bcnt <= base_now + NBW;
    end

    // -- stage 2: two max levels (8 lanes -> 2 per block) ----------------------------------
    reg              a2_v, a2_last;
    reg  [KW-1:0]    a2_k;
    reg  [NB*32-1:0] a2_key;
    reg  [NB-1:0]    a2_bv, a2_bp;
    reg  [IW-1:0]    a2_idx;
    wire [NB*32-1:0] m2_d;
    generate
        for (gb = 0; gb < NB; gb = gb + 1) begin : g_m2
            wire [15:0] l0 = kmax(a1_key[16*(8*gb+0) +: 16], a1_key[16*(8*gb+1) +: 16]);
            wire [15:0] l1 = kmax(a1_key[16*(8*gb+2) +: 16], a1_key[16*(8*gb+3) +: 16]);
            wire [15:0] l2 = kmax(a1_key[16*(8*gb+4) +: 16], a1_key[16*(8*gb+5) +: 16]);
            wire [15:0] l3 = kmax(a1_key[16*(8*gb+6) +: 16], a1_key[16*(8*gb+7) +: 16]);
            assign m2_d[32*gb +: 32] = {kmax(l2, l3), kmax(l0, l1)};
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) a2_v <= 1'b0;
        else if (adv) a2_v <= a1_v;
    end
    always @(posedge clk) if (adv) begin
        a2_last <= a1_last; a2_k <= a1_k; a2_key <= m2_d; a2_bv <= a1_bv; a2_bp <= a1_bp; a2_idx <= a1_idx;
    end

    // -- stage 3: block max, pin, key -> BF16 ----------------------------------------------
    reg              a3_v, a3_last;
    reg  [KW-1:0]    a3_k;
    reg  [NB*16-1:0] a3_val;
    reg  [NB-1:0]    a3_bv;
    reg  [IW-1:0]    a3_idx;
    wire [NB*16-1:0] v3_d;
    generate
        for (gb = 0; gb < NB; gb = gb + 1) begin : g_m3
            wire [15:0] k = kmax(a2_key[32*gb +: 16], a2_key[32*gb + 16 +: 16]);
            wire [15:0] v = k[15] ? {1'b0, k[14:0]} : ~k;
            assign v3_d[16*gb +: 16] = a2_bp[gb] ? PINF : v;
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) a3_v <= 1'b0;
        else if (adv) a3_v <= a2_v;
    end
    always @(posedge clk) if (adv) begin
        a3_last <= a2_last; a3_k <= a2_k; a3_val <= v3_d; a3_bv <= a2_bv; a3_idx <= a2_idx;
    end

    // -- line packer ------------------------------------------------------------------------
    reg  [RS-1:0] slot;
    wire          fresh = line_v || slot == 0;       // the line register starts a new line
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            line_v <= 1'b0; line_last <= 1'b0; slot <= 0;
        end else begin
            if (line_v && t_ready) line_v <= 1'b0;
            if (adv && a3_v) begin
                if (slot == RM1 || a3_last) begin
                    line_v <= 1'b1; line_last <= a3_last; slot <= 0;
                end else slot <= slot + 1'b1;
            end
        end
    end
    always @(posedge clk) if (adv && a3_v) line_k <= a3_k;
    generate
        for (gl = 0; gl < WB; gl = gl + 1) begin : g_line
            localparam integer SLI = gl / NB;
            localparam [RS-1:0] SL = SLI[RS-1:0];
            localparam integer OFI = gl % NB;
            localparam [IW-1:0] OF = OFI[IW-1:0];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) line_lv[gl] <= 1'b0;
                else if (adv && a3_v) begin
                    if (slot == SL) line_lv[gl] <= a3_bv[OFI];
                    else if (fresh) line_lv[gl] <= 1'b0;
                end
            end
            always @(posedge clk) if (adv && a3_v && slot == SL) begin
                line_val[16*gl +: 16] <= a3_val[16*OFI +: 16];
                line_idx[IW*gl +: IW] <= a3_idx + OF;
            end
        end
    endgenerate

    wire ts_busy;
    ot_hdc_tselect #(.W(WB), .VW(16), .IW(IW), .K(K), .AW(AW)) u_ts (
        .clk(clk), .rst_n(rst_n), .in_valid(line_v), .in_ready(t_ready), .in_last(line_last),
        .in_lv(line_lv), .in_val(line_val), .in_idx(line_idx), .in_k(line_k),
        .out_valid(out_valid), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re),
        .mem_raddr(mem_raddr), .mem_rdata(mem_rdata), .busy(ts_busy));
    assign busy = ts_busy || a1_v || a2_v || a3_v || line_v;
endmodule

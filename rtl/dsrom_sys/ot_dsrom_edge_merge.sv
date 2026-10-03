`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Position-order merge of the per-stack candidate lists (EDGE INDEX SCORER hub).
//
// Each stack's list arrives as dense W-lane beats (every beat full but the
// last, which may be empty), ascending in global position; positions are
// unique across stacks.  ot_dsrom_edge_merge2 merges two such streams into one,
// W elements per cycle, and ot_dsrom_edge_merge4 is the two-level tree over
// the four stacks of a die.
//
// merge2 (merge path, W per cycle).  Each side keeps a 2W-element ring of its
// next elements (two beat slots, refilled a whole beat at a time).  When each
// side shows W elements (or has received its last beat), let a and b be the
// next W of each, absent elements = +inf.  For sorted a, b the W smallest of
// a U b are a[0..x) U b[0..W-x) with
//     x = #{ i : a[i] < b[W-1-i] }          (a prefix of ones in i)
// and the lane-wise minima min(a[i], b[W-1-i]) are exactly those W elements as
// a bitonic sequence.  The loop is ring rotate -> W comparators -> popcount ->
// read-pointer add; the bitonic sort of the emitted W runs in a registered
// pipeline outside it (log2 W half-cleaner levels, two per register).  Every
// element of either side not yet shown is >= the shown ones of its side, so
// the emitted W are the W smallest remaining: the output is the sorted union.
// ---------------------------------------------------------------------------
module ot_dsrom_edge_merge2 #(
    parameter integer W  = 16,
    parameter integer IW = 20,       // position (the merge key)
    parameter integer PW = 16        // payload carried with each position (the score)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,          // clears the unit for a new pair of lists
    input  wire              a_valid,
    output wire              a_ready,
    input  wire              a_last,
    input  wire [W-1:0]      a_lv,           // dense prefix
    input  wire [W*IW-1:0]   a_idx,
    input  wire [W*PW-1:0]   a_pay,
    input  wire              b_valid,
    output wire              b_ready,
    input  wire              b_last,
    input  wire [W-1:0]      b_lv,
    input  wire [W*IW-1:0]   b_idx,
    input  wire [W*PW-1:0]   b_pay,
    output wire              o_valid,
    input  wire              o_ready,
    output wire              o_last,
    output wire [W-1:0]      o_lv,
    output wire [W*IW-1:0]   o_idx,
    output wire [W*PW-1:0]   o_pay
);
    localparam integer LW = $clog2(W);
    localparam integer EW = 1 + IW + PW;             // {invalid (=+inf), position, payload}; key = top 1+IW bits
    localparam integer CW = LW + 2;                  // element counters mod 4W
    localparam integer NSTG = (LW + 1) / 2;          // sort pipeline registers
    localparam integer OD = 8;                       // output FIFO depth (beats)

    integer iw, il, ir, isr;

    // -- the two sides --------------------------------------------------------------------------
    reg  [2*W*EW-1:0] ra, rb;                        // rings: element e at slot e mod 2W
    reg  [CW-1:0]     wa, wb, pa, pb;                // written / consumed element counts (mod 4W)
    reg               ea, eb;                        // last beat received
    wire [CW-1:0]     na = wa - pa, nb = wb - pb;    // elements present (0 .. 2W)
    assign a_ready = !ea && (na <= W);
    assign b_ready = !eb && (nb <= W);
    wire acc_a = a_valid && a_ready, acc_b = b_valid && b_ready;
    function automatic [LW:0] cnt(input [W-1:0] lv);
        integer e;
        begin
            cnt = 0;
            for (e = 0; e < W; e = e + 1) cnt = cnt + {{LW{1'b0}}, lv[e]};
        end
    endfunction

    // the shown windows (rotate by the read pointer)
    reg  [W*EW-1:0] wia, wib;
    always @(*) begin
        for (iw = 0; iw < W; iw = iw + 1) begin
            wia[EW*iw +: EW] = ra[EW*((pa + iw) % (2 * W)) +: EW];
            wib[EW*iw +: EW] = rb[EW*((pb + iw) % (2 * W)) +: EW];
            if (iw >= na) wia[EW*iw + EW - 1] = 1'b1;     // absent: +inf
            if (iw >= nb) wib[EW*iw + EW - 1] = 1'b1;
        end
    end
    // lane split
    reg  [W-1:0]    lt;
    reg  [LW:0]     x;
    always @(*) begin
        x = 0;
        for (il = 0; il < W; il = il + 1) begin
            // an absent A element (+inf) is never below; absent B is above every present A
            lt[il] = !wia[EW*il + EW - 1] && (wib[EW*(W-1-il) + EW - 1] ||
                     wia[EW*il + PW +: IW] < wib[EW*(W-1-il) + PW +: IW]);
            x = x + {{LW{1'b0}}, lt[il]};
        end
    end
    wire [CW-1:0] xa = {{(CW-LW-1){1'b0}}, x};
    wire [CW-1:0] wx = W[CW-1:0] - xa;
    wire [CW-1:0] xb = (nb < wx) ? nb : wx;          // B elements taken
    wire          sh_a = (na >= W) || ea, sh_b = (nb >= W) || eb;
    reg           done;                              // the last beat has been emitted
    reg  [3:0]    infl;                              // beats in the sort pipeline
    reg  [3:0]    fc;                                // output FIFO count
    wire          room = ({1'b0, fc} + {1'b0, infl}) < OD - 1;
    wire          fin  = ea && eb && (na - xa == 0) && (nb - xb == 0);
    wire          go   = sh_a && sh_b && !done && room && !start;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wa <= 0; wb <= 0; pa <= 0; pb <= 0; ea <= 1'b0; eb <= 1'b0; done <= 1'b0;
        end else if (start) begin
            wa <= 0; wb <= 0; pa <= 0; pb <= 0; ea <= 1'b0; eb <= 1'b0; done <= 1'b0;
        end else begin
            if (acc_a) begin
                for (ir = 0; ir < W; ir = ir + 1)
                    ra[EW*((wa % (2 * W)) + ir) +: EW] <= {!a_lv[ir], a_idx[IW*ir +: IW], a_pay[PW*ir +: PW]};
                wa <= wa + {{(CW-LW-1){1'b0}}, cnt(a_lv)};
                if (a_last) ea <= 1'b1;
            end
            if (acc_b) begin
                for (ir = 0; ir < W; ir = ir + 1)
                    rb[EW*((wb % (2 * W)) + ir) +: EW] <= {!b_lv[ir], b_idx[IW*ir +: IW], b_pay[PW*ir +: PW]};
                wb <= wb + {{(CW-LW-1){1'b0}}, cnt(b_lv)};
                if (b_last) eb <= 1'b1;
            end
            if (go) begin
                pa <= pa + xa;
                pb <= pb + xb;
                if (fin) done <= 1'b1;
            end
        end
    end

    // -- emitted W (bitonic) -> sorted, registered every two half-cleaner levels ----------------
    reg  [NSTG:0]      sv, sl;
    reg  [(NSTG+1)*W*EW-1:0] sd;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sv <= 0; sl <= 0; end
        else begin
            sv <= {sv[NSTG-1:0], go};
            sl <= {sl[NSTG-1:0], go && fin};
        end
    end
    always @(posedge clk)
        for (isr = 0; isr < W; isr = isr + 1)
            sd[EW*isr +: EW] <= lt[isr] ? wia[EW*isr +: EW] : wib[EW*(W-1-isr) +: EW];
    genvar g, h, q;
    generate
        for (g = 0; g < NSTG; g = g + 1) begin : g_st
            wire [W*EW-1:0] in0 = sd[W*EW*g +: W*EW];
            wire [(3*W)*EW-1:0] lvl;                 // two half-cleaner levels
            assign lvl[W*EW-1:0] = in0;
            for (h = 0; h < 2; h = h + 1) begin : g_lv
                localparam integer LV = 2 * g + h;   // level index: distance W >> (LV + 1)
                localparam integer D  = (LV < LW) ? (W >> (LV + 1)) : 0;
                for (q = 0; q < W; q = q + 1) begin : g_q
                    wire [EW-1:0] me = lvl[W*EW*h + EW*q +: EW];
                    if (D == 0) begin : g_pass
                        assign lvl[W*EW*(h+1) + EW*q +: EW] = me;
                    end else if ((q % (2 * D)) < D) begin : g_lo
                        wire [EW-1:0] pr = lvl[W*EW*h + EW*(q + D) +: EW];
                        assign lvl[W*EW*(h+1) + EW*q +: EW] = (pr[EW-1:PW] < me[EW-1:PW]) ? pr : me;
                    end else begin : g_hi
                        wire [EW-1:0] pr = lvl[W*EW*h + EW*(q - D) +: EW];
                        assign lvl[W*EW*(h+1) + EW*q +: EW] = (pr[EW-1:PW] < me[EW-1:PW]) ? me : pr;
                    end
                end
            end
            always @(posedge clk) sd[W*EW*(g+1) +: W*EW] <= lvl[2*W*EW +: W*EW];
        end
    endgenerate
    wire              s_v = sv[NSTG], s_l = sl[NSTG];
    wire [W*EW-1:0]   s_d = sd[W*EW*NSTG +: W*EW];

    // -- output FIFO ---------------------------------------------------------------------------
    reg  [W*EW:0]     of [0:OD-1];
    reg  [2:0]        oh, ot;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin oh <= 0; ot <= 0; fc <= 0; infl <= 0; end
        else if (start) begin oh <= 0; ot <= 0; fc <= 0; infl <= 0; end
        else begin
            if (s_v) begin of[ot] <= {s_l, s_d}; ot <= ot + 1'b1; end
            if (o_valid && o_ready) oh <= oh + 1'b1;
            fc   <= fc + {3'd0, s_v} - {3'd0, o_valid && o_ready};
            infl <= infl + {3'd0, go} - {3'd0, s_v};
        end
    end
    assign o_valid = fc != 0;
    wire [W*EW:0] oe = of[oh];
    assign o_last = oe[W*EW];
    generate
        for (g = 0; g < W; g = g + 1) begin : g_o
            assign o_lv[g]           = !oe[EW*g + EW - 1];
            assign o_idx[IW*g +: IW] = oe[EW*g + PW +: IW];
            assign o_pay[PW*g +: PW] = oe[EW*g +: PW];
        end
    endgenerate

`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && !start) begin
        if (acc_a && (a_lv & (a_lv + 1'b1)) != 0) $fatal(1, "merge2: side A beat not dense");
        if (acc_b && (b_lv & (b_lv + 1'b1)) != 0) $fatal(1, "merge2: side B beat not dense");
        if (acc_a && !a_last && a_lv != {W{1'b1}}) $fatal(1, "merge2: side A partial beat before last");
        if (acc_b && !b_last && b_lv != {W{1'b1}}) $fatal(1, "merge2: side B partial beat before last");
        if (go && (lt & (lt + 1'b1)) != 0) $fatal(1, "merge2: split not a prefix (input unsorted)");
    end
`endif
endmodule

// Four position-ordered lists (one per HBM stack) -> one, two merge levels.
module ot_dsrom_edge_merge4 #(
    parameter integer W  = 16,
    parameter integer IW = 20,
    parameter integer PW = 16
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               start,
    input  wire [3:0]         i_valid,
    output wire [3:0]         i_ready,
    input  wire [3:0]         i_last,
    input  wire [4*W-1:0]     i_lv,
    input  wire [4*W*IW-1:0]  i_idx,
    input  wire [4*W*PW-1:0]  i_pay,
    output wire               o_valid,
    input  wire               o_ready,
    output wire               o_last,
    output wire [W-1:0]       o_lv,
    output wire [W*IW-1:0]    o_idx,
    output wire [W*PW-1:0]    o_pay
);
    wire [1:0]        m_v, m_r, m_l;
    wire [2*W-1:0]    m_lv;
    wire [2*W*IW-1:0] m_idx;
    wire [2*W*PW-1:0] m_pay;
    genvar g;
    generate
        for (g = 0; g < 2; g = g + 1) begin : g_leaf
            ot_dsrom_edge_merge2 #(.W(W), .IW(IW), .PW(PW)) u_m (
                .clk(clk), .rst_n(rst_n), .start(start),
                .a_valid(i_valid[2*g]), .a_ready(i_ready[2*g]), .a_last(i_last[2*g]),
                .a_lv(i_lv[W*(2*g) +: W]), .a_idx(i_idx[W*IW*(2*g) +: W*IW]), .a_pay(i_pay[W*PW*(2*g) +: W*PW]),
                .b_valid(i_valid[2*g+1]), .b_ready(i_ready[2*g+1]), .b_last(i_last[2*g+1]),
                .b_lv(i_lv[W*(2*g+1) +: W]), .b_idx(i_idx[W*IW*(2*g+1) +: W*IW]),
                .b_pay(i_pay[W*PW*(2*g+1) +: W*PW]),
                .o_valid(m_v[g]), .o_ready(m_r[g]), .o_last(m_l[g]), .o_lv(m_lv[W*g +: W]),
                .o_idx(m_idx[W*IW*g +: W*IW]), .o_pay(m_pay[W*PW*g +: W*PW]));
        end
    endgenerate
    ot_dsrom_edge_merge2 #(.W(W), .IW(IW), .PW(PW)) u_root (
        .clk(clk), .rst_n(rst_n), .start(start),
        .a_valid(m_v[0]), .a_ready(m_r[0]), .a_last(m_l[0]),
        .a_lv(m_lv[0 +: W]), .a_idx(m_idx[0 +: W*IW]), .a_pay(m_pay[0 +: W*PW]),
        .b_valid(m_v[1]), .b_ready(m_r[1]), .b_last(m_l[1]),
        .b_lv(m_lv[W +: W]), .b_idx(m_idx[W*IW +: W*IW]), .b_pay(m_pay[W*PW +: W*PW]),
        .o_valid(o_valid), .o_ready(o_ready), .o_last(o_last), .o_lv(o_lv), .o_idx(o_idx), .o_pay(o_pay));
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-ROWX3 (2026-10-26): CROSS-DIE RANK-ORDER ROW TRANSPORT, one die half (dsdv_rowx_xm = re-pair + OR-merge stage +
// broadcast relay + ingress egress).  Spec: ~/coord/lanes/S81-ROWX.md "ROWX-3"; ruling COORD 19:18 RULING S81-ROWX-2.
//
// Problem.  In RO = 1 mode every one of the 16 (die, stack) owners exports the same 2,240-slot rank-order stream; a
// half is valid only on the one owner that holds the rank (x_own), so the 16 streams are slot-aligned and disjoint.
// Every receiver needs the slot-wise OR of the 15 OTHER owners' streams (its own halves would hit ingress fault 29),
// as PK2 words (two tiles per word).
//
// Structure: the 16 owners form a static chain (position POS 0..15, compiler-chosen; links on-die or die-to-die).
//   (1) re-pair  dsdv_rowx_rp: the half's export (8 tile windows of 40 words per pass) -> 1 PK2 slot / cycle.
//   (2) REDUCE   (POS 0 -> 15): at each own slot this stage pops the upstream partial from its landed crossing (POS 0:
//                none), ORs its own slot in and sends the result downstream (registered).  Own valid halves are
//                stamped with POS in the half's spare bits [171:168] (always 0 in the export format).  A slot where
//                the partial and the own word both hold a valid half = a rank claimed by two owners: sticky f_ovl.  A
//                valid half whose (rank, tile) is not the slot's = a misaligned stream: sticky f_slot.
//   (3) BROADCAST (POS 15 -> 0): POS 15's reduce output is the complete OR; it loops into its own broadcast landing,
//                and every stage pops its broadcast landing on its own booked slots and relays the word upstream.
//   (4) EGRESS   from the broadcast word: a half is kept iff valid and its tag != POS (the receiver's own rows are
//                excluded by construction; the tag bits are cleared, so the ingress sees the export's exact half),
//                slots of rank >= NR (the last pass's padding, a STATIC slot position, not data) are dropped, and a
//                CFG-written ROWS header (type 6, len 2,048, spec [0] = 1) leads.  The ingress therefore gets exactly
//                1 + 2,048 words per half for any selection.
// Schedule: fixed.  Slot s of POS d is popped at cycle S_d + s with S_d = S_(d-1) + HOP (compiler: XOFF / BC_OFF per
// die); every hop is registered (stage output flop -> link -> landing pin flop -> landing FIFO); the landing absorbs
// arrival jitter up to its depth; a missed slot is a sticky fault, never a stall.  No credit / ready / backpressure.
// Per-die cost: transport span = 42 (re-pair) + 15 HOP (reduce) + 4 + 15 HOP (broadcast) + 2,241 (slots + header).
// Faults (sticky; fcode): [0] ovl  [1] slot (reduce)  [2] late (reduce landing)  [3] ovf (reduce landing)
//   [4] late (broadcast landing)  [5] ovf (broadcast)  [6] re-pair input off its booked cycle  [7] slot (broadcast).
// Mutants (bench only): MUT 1 egress keeps the receiver's own halves; MUT 2 no overlap check; MUT 3 re-pair bank
//   (dsdv_rowx_rp); MUT 4 egress keeps the padding slot of rank NR.
// Window order assumed identity (window k of a pass = tile HB*8 + k): the compiler books pvs_t = PV0 + 40 (t & 7).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_rowx_xm #(parameter integer MUT = 0, parameter integer D = 16) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          cfg_v,
    input  wire [63:0]   cfg_d,          // [3:0] POS [4] head [5] tail [6] HB [22:7] XOFF [38:23] BC_OFF [50:39] NS [61:51] NR
    input  wire          hdr_v,
    input  wire [511:0]  hdr_d,          // the ROWS PK2 header word for this half's ingress
    input  wire          go,
    input  wire          x_v,            // export words of this half (from the entry P.V lane / pvrd)
    input  wire [512:0]  x_d,
    input  wire          ri_v,           // reduce partial from POS - 1
    input  wire [511:0]  ri_d,
    output reg           ro_v,           // reduce partial to POS + 1
    output reg  [511:0]  ro_d,
    input  wire          bi_v,           // broadcast from POS + 1
    input  wire [511:0]  bi_d,
    output reg           bo_v,           // broadcast to POS - 1
    output reg  [511:0]  bo_d,
    output reg           e_v,            // to the svc entry q (ROWS PK2 frame)
    output reg  [511:0]  e_d,
    output wire          fault,
    output wire [7:0]    fcode
);
    // ---------------------------------------------------------------- configuration (CFG-written, static per frame)
    reg [3:0] pos; reg head, tail, hb; reg [15:0] xoff, bc_off; reg [11:0] ns; reg [10:0] nr; reg [511:0] hdr;
    reg go_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pos <= 0; head <= 0; tail <= 0; hb <= 0; xoff <= 16'd2; bc_off <= 16'd2; ns <= 12'd2240; nr <= 11'd512;
                          go_r <= 0; end
        else begin
            go_r <= go;
            if (cfg_v) begin pos <= cfg_d[3:0]; head <= cfg_d[4]; tail <= cfg_d[5]; hb <= cfg_d[6]; xoff <= cfg_d[22:7];
                             bc_off <= cfg_d[38:23]; ns <= cfg_d[50:39]; nr <= cfg_d[61:51]; end
        end
    always @(posedge clk) if (hdr_v) hdr <= hdr_d;

    // ---------------------------------------------------------------- (1) re-pair
    wire o_v; wire [511:0] o_d; wire f_mis;
    dsdv_rowx_rp #(.MUT(MUT)) u_rp (.clk(clk), .rst_n(rst_n), .go(go), .xoff(xoff), .ns(ns), .x_v(x_v), .x_d(x_d),
                                    .o_v(o_v), .o_d(o_d), .f_mis(f_mis));

    // ---------------------------------------------------------------- half fields
    function automatic hv(input [255:0] h); hv = h[0]; endfunction
    function automatic [3:0] htile(input [255:0] h); htile = h[4:1]; endfunction
    function automatic [9:0] hrank(input [255:0] h); hrank = h[14:5]; endfunction
    function automatic [3:0] htag(input [255:0] h); htag = h[171:168]; endfunction
    // slot (n 0..79 in a pair window, q pair 0..3, rb = 80 p) -> rank, tiles
    function automatic [10:0] srank(input [10:0] rb, input [6:0] n);
        srank = rb + 11'((n < 7'd40) ? 2 * n : 2 * (n - 7'd40) + 1);
    endfunction
    function automatic bad(input [255:0] h, input [10:0] r, input [3:0] t);
        bad = h[0] && ({1'b0, h[14:5]} != r || h[4:1] != t);
    endfunction

    // ---------------------------------------------------------------- (2) reduce
    wire [511:0] rl_d; wire rl_late, rl_ovf;
    dsdv_rowx_lc #(.W(512), .D(D)) u_lr (.clk(clk), .rst_n(rst_n), .i_v(ri_v && !head), .i_d(ri_d), .pop(o_v && !head),
                                         .o_d(rl_d), .f_late(rl_late), .f_ovf(rl_ovf));
    wire [511:0] rin = head ? 512'd0 : rl_d;
    reg [6:0] rn; reg [1:0] rq; reg [10:0] rrb;
    wire [10:0] er = srank(rrb, rn);
    wire [3:0] et0 = {hb, rq, 1'b0}, et1 = {hb, rq, 1'b1};
    reg f_ovl, f_slot, f_bslot;
    function automatic [255:0] stamp(input [255:0] h, input [3:0] p);
        reg [255:0] x; x = h; if (h[0]) x[171:168] = p; stamp = x;
    endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ro_v <= 0; ro_d <= 0; rn <= 0; rq <= 0; rrb <= 0; f_ovl <= 0; f_slot <= 0; end
        else begin
            if (go_r) begin rn <= 0; rq <= 0; rrb <= 0; end
            ro_v <= o_v;
            if (o_v) begin
                ro_d <= rin | {stamp(o_d[511:256], pos), stamp(o_d[255:0], pos)};
                if (MUT != 2 && ((o_d[0] && rin[0]) || (o_d[256] && rin[256]))) f_ovl <= 1'b1;
                if (bad(o_d[255:0], er, et0) || bad(o_d[511:256], er, et1) || bad(rin[255:0], er, et0) || bad(rin[511:256], er, et1))
                    f_slot <= 1'b1;
                if (rn == 7'd79) begin rn <= 0; rq <= rq + 1'b1; if (rq == 2'd3) rrb <= rrb + 11'd80; end else rn <= rn + 1'b1;
            end
        end

    // ---------------------------------------------------------------- (3) broadcast + (4) egress
    reg barm, bhdr, bact; reg [15:0] bd; reg [11:0] bcu; reg [6:0] bn; reg [1:0] bq; reg [10:0] brb;
    wire [511:0] bl_d; wire bl_late, bl_ovf;
    dsdv_rowx_lc #(.W(512), .D(D)) u_lb (.clk(clk), .rst_n(rst_n), .i_v(tail ? ro_v : bi_v), .i_d(tail ? ro_d : bi_d),
                                         .pop(bact), .o_d(bl_d), .f_late(bl_late), .f_ovf(bl_ovf));
    wire [10:0] eb = srank(brb, bn);
    wire keep = (MUT == 4) ? (eb <= nr) : (eb < nr);
    function automatic [255:0] filt(input [255:0] h, input [3:0] p);
        reg [255:0] x; x = h; x[171:168] = 4'd0;
        filt = (h[0] && (MUT == 1 || h[171:168] != p)) ? x : 256'd0;
    endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin barm <= 0; bhdr <= 0; bact <= 0; bd <= 0; bcu <= 0; bn <= 0; bq <= 0; brb <= 0; bo_v <= 0; bo_d <= 0;
                          e_v <= 0; e_d <= 0; f_bslot <= 0; end
        else begin
            bhdr <= 1'b0;
            if (go_r) begin barm <= 1'b1; bd <= bc_off - 16'd2; end
            else if (barm) begin if (bd == 0) begin barm <= 1'b0; bhdr <= 1'b1; end else bd <= bd - 1'b1; end
            if (bhdr) begin bact <= 1'b1; bcu <= 0; bn <= 0; bq <= 0; brb <= 0; end
            bo_v <= bact; e_v <= bhdr || (bact && keep);
            if (bhdr) e_d <= hdr;
            if (bact) begin
                bo_d <= bl_d;
                e_d <= {filt(bl_d[511:256], pos), filt(bl_d[255:0], pos)};
                if (bad(bl_d[255:0], eb, {hb, bq, 1'b0}) || bad(bl_d[511:256], eb, {hb, bq, 1'b1})) f_bslot <= 1'b1;
                if (bn == 7'd79) begin bn <= 0; bq <= bq + 1'b1; if (bq == 2'd3) brb <= brb + 11'd80; end else bn <= bn + 1'b1;
                bcu <= bcu + 1'b1;
                if (bcu == ns - 12'd1) bact <= 1'b0;
            end
        end
    assign fcode = {f_bslot, f_mis, bl_ovf, bl_late, rl_ovf, rl_late, f_slot, f_ovl};
    assign fault = |fcode;
endmodule

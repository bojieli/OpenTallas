`timescale 1ns/1ps
`ifndef KVD_HEADS
`define KVD_HEADS 2
`endif
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B ROM TP8 die (track B), stack aggregator strip qkd_astk / qkd_astk_n (el1013-qwen-kvstrips 2026-10-13).
// The 220.3 x 7,817 slot held ot_qwen_nearhbm_attn_stack_h minus its engines: a 409,684-flop P.V bank (512 fp32 lanes
// with every staged node at one place: 8 x 16,384 b across one cut), an 8-write-port score / e memory and a Z tree
// with 32 parallel reads of a 2,048-entry table.  None of it can be one hardened block.  It becomes five masters,
// every port a register at the pin, every hop <= one head pitch (453.6 um):
//
//   qkd_astk_pv   the P.V tree cell: 8 fp32 adders (ANR, 7 stages) + two 2,048-b operand stores.  Two cells (X / Y:
//                 the lanes kk mod 4 < 2 / >= 2 of a head's 1,024-b node beat) at every head position of the strip
//                 take that head's node slice of the LEFT and of the RIGHT engine of the row (level 4 of the golden
//                 tree = engines (0,1) (2,3) (4,5) (6,7)): no node is staged anywhere else.  A second cell at the
//                 same position does one more level (5: row pairs, 6: half stacks, 7: the two rounds) on 128-b
//                 streams that run cell to cell through registered lanes (4 up, 4 down, lane = head).  The level-7
//                 cells put the result on a 256-b lane as the hub's P.V beats, in beat order (a token walks the
//                 heads).  A cut of the strip carries 2 x (8 x 134 + 263) = 2,670 b of P.V traffic.
//   qkd_astk_ep   one row engine's stack slice: the engine port (si / so of qkd_ectl), its score memory (2 x 256x128)
//                 and e-row memory (4 x 64x128; 57 um macros compiled for this column leaf), its copy of M, a station of the stack's command chain (start, T, q beats, M words,
//                 K-pass done), of the return chain (score count, running maximum, fault), of the chunk chain and of
//                 the e-row chain.  The golden's 8-write x 8-read score memory does not exist as a macro, and the
//                 engines' K pass (positions j = engine) and V pass (groups gam = engine mod 8) slice the positions
//                 across each other.  So the scores stay with the engine that made them; every slice runs the same
//                 sequence of chunks (gam, k) and adds ITS position's e to the chunk's partial sum as it walks the
//                 slices in order j = 0..7 -- the golden's sequential chunk sum, element by element -- and the
//                 chunk's eight bf16 e travel with it, then down the e-row chain to the slice that owns the group.
//   qkd_astk_ex   one head of the slice's exp datapath (subtract + exp, a 118-stage pipe of ~16k flops), four beside
//                 each ep.
//   qkd_astk_zn   one level of the Z tree behind slice 7 (4 in a row): the golden's pairwise order over the 16 chunk
//                 sums of a block; a chunk at or past T is +0, as in the golden.
//   qkd_astk_ctl  the stack's port: q / start / T in, layer word out, the hub words (lmax, Z block sums, Z done, P.V
//                 beats), K-pass completion count, the group count for the tree cells.
// The tree cells' lanes cross qkd_astk_ep and qkd_astk_ex (leaves of the same 108 um column) through
// registered feed-through lanes (qkd_astk_lanes), so no hop exceeds a leaf height.
//
// EXACTNESS.  The P.V tree is the golden's tree term for term: the leaves are the engines' level-3 group nodes in
// order rho = 0..15 (group rho from engine rho mod 8), paired (2i, 2i + 1) at every level; a missing right operand
// (fewer than 16 nonempty groups) leaves the left one unchanged, which is what the golden's flush does (x + 0 = x:
// every zero of these units is +0).  Nothing depends on arrival times: every transfer is tagged and counted.
// Composition bench: rtl/test/qwen_kv_die/ot_qwen_nearhbm_attn_stack_k.sv in the layer-step campaign (STACK=k).
//
// Stream word  SW = {d 128, g, idx 4, v}   (one kk slot of a node: the 4 beat values; 16 a node half)
// P.V word     PW = {d 256, g, beat 5, v}  (8 lanes = half a hub beat; X and Y cells emit the two halves together)
// Node control nc = {gam 4, g, beat 4, v}  (qkd_ectl so[421:412])      ci = {gmax 5, start}
// Bench mutants (`KVD_AKMUT): 1 pv: operand b of lane 3 taken from lane 2; 2 ep: e rows written one address off;
// 3 zn: the right operand dropped; 4 ctl: the two halves of a P.V beat swapped; 5 ex: e one ulp off.
// ---------------------------------------------------------------------------------------------------------------------
`ifndef KVD_AKMUT
`define KVD_AKMUT 0
`endif

// ---- P.V tree cell -------------------------------------------------------------------------------------------------
// cfg = {tdir, far, bth 3, ath 3, ym 2, bm 2, am 2, lvl 2, h 2}
//   h    head (lane index, P.V beat = 8 h + j)        lvl  0: level 4 (head pins), 1: 5, 2: 6, 3: 7
//   am / bm   operand source at levels 5 / 6 (7: am for both rounds): 0 local pin li, 1 up lane h, 2 down lane h
//   ym   result besides lo: 0 none, 1 into up lane h, 2 into down lane h (level 7: the P.V lane)
//   ath / bth  first leaf slot (mod 8) under each child: the child is present in round rho when gmax > 8 rho + th
//   far  the node control comes through the neighbouring cell (one cycle later)       tdir  token lane (0 up, 1 down)
// FLOW CONTROL: an operand store holds one item, so every stream has one credit: a cell starts an item only with the
// credit of the store it feeds (the cell above: lci; a lane: that lane's credit bit, which travels against the
// stream) and answers its own producers when its stores are free again (the engines: cra / crb).
// Frame: N is the hub end (the cell is flipped MX in the stacks whose hub is to the S).
module qkd_astk_pv #(
    parameter integer HEADS = `KVD_HEADS   // kvsys-elements r2: native TP8 = 1 (one group: items {round} only)
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [17:0]   cfg,
    input  wire [511:0]  wa,          // W  left engine's head: 16 kk slots of the node beat
    input  wire [511:0]  wb,          // E  right engine's head
    input  wire [9:0]    nc,          // W  left engine's node control
    input  wire [9:0]    nd,          // E  right engine's node control
    output wire [9:0]    nco,         // W  registered copy for the far cell
    output wire [9:0]    ndo,         // E
    output reg           cra,         // W  credit: the left engine's node is consumed
    output reg           crb,         // W  credit: the right engine's node is consumed
    input  wire [133:0]  li,          // S  local stream in
    output wire [133:0]  lo,          // N  result stream
    input  wire [535:0]  ui,          // S  up lanes in
    output wire [535:0]  uo,          // N
    input  wire [535:0]  di,          // N  down lanes in
    output wire [535:0]  do_,         // S
    input  wire [262:0]  pi,          // S  P.V lane
    output wire [262:0]  po,          // N
    input  wire [5:0]    ci,          // N  {gmax, start}
    output wire [5:0]    co,          // S
    input  wire          lci,         // N  credit from the local consumer (the cell above)
    output reg           lco,         // S  credit to the local producer (the cell below)
    input  wire [3:0]    kui,         // N  credits of the up lanes (they travel down)
    output wire [3:0]    kuo,         // S
    input  wire [3:0]    kdi,         // S  credits of the down lanes (they travel up)
    output wire [3:0]    kdo,         // N
    input  wire          tui,         // S  token lanes
    output reg           tuo,         // N
    input  wire          tdi,         // N
    output reg           tdo,         // S
    input  wire          fi,          // S  fault chain
    output reg           fo           // N
);
    localparam integer SW = 134, PW = 263, ADD_LAT = 7;
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [17:0] cf;
    always @(posedge ck) cf <= cfg;
    wire [1:0] h = cf[1:0], lvl = cf[3:2], am = cf[5:4], bm = cf[7:6], ym = cf[9:8];
    wire [2:0] ath = cf[12:10], bth = cf[15:13];
    wire       far = cf[16], tdir = cf[17];
    wire       l4 = lvl == 2'd0, l7 = lvl == 2'd3;
    // ---- pin flops: control lane, node control, tokens, fault ---------------------------------------------------------
    (* keep *) reg [5:0] cq;
    (* keep *) reg [9:0] ncq, ndq;
    (* keep *) reg       tu_q, td_q, fi_q, lci_q, kcu, kcd;      // kcu / kcd: the own lane's credit (this cell produces)
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin cq[0] <= 1'b0; ncq[0] <= 1'b0; ndq[0] <= 1'b0; tu_q <= 1'b0; td_q <= 1'b0; fi_q <= 1'b0; lci_q <= 1'b0;
                         kcu <= 1'b0; kcd <= 1'b0; end
        else begin cq[0] <= ci[0]; ncq[0] <= nc[0]; ndq[0] <= nd[0]; tu_q <= tui; td_q <= tdi; fi_q <= fi; lci_q <= lci;
                   kcu <= (h == 2'd0) ? kui[0] : (h == 2'd1) ? kui[1] : (h == 2'd2) ? kui[2] : kui[3];
                   kcd <= (h == 2'd0) ? kdi[0] : (h == 2'd1) ? kdi[1] : (h == 2'd2) ? kdi[2] : kdi[3]; end
    always @(posedge ck) begin cq[5:1] <= ci[5:1]; ncq[9:1] <= nc[9:1]; ndq[9:1] <= nd[9:1]; end
    assign co = cq; assign nco = ncq; assign ndo = ndq;
    wire       start = cq[0];
    wire [4:0] gmax = cq[5:1];
    // ---- lanes: one register a lane a cell (the output pin); the own lane's input has its own flop --------------------
    wire          yf, pcol, cr_u, cr_d;
    (* keep *) reg [SW-1:0] tu, td, lq;
    reg  [SW-1:0] yw;                                  // the result stream register (lo and the lane injection)
    wire [SW-1:0] ui_h = (h == 2'd0) ? ui[0 +: SW] : (h == 2'd1) ? ui[SW +: SW] : (h == 2'd2) ? ui[2*SW +: SW] : ui[3*SW +: SW];
    wire [SW-1:0] di_h = (h == 2'd0) ? di[0 +: SW] : (h == 2'd1) ? di[SW +: SW] : (h == 2'd2) ? di[2*SW +: SW] : di[3*SW +: SW];
    wire          blk_u = am == 2'd1 || (bm == 2'd1 && !l7);
    wire          blk_d = am == 2'd2 || (bm == 2'd2 && !l7);
    wire          inj_u = ym == 2'd1 && !l7 && yw[0];
    wire          inj_d = ym == 2'd2 && !l7 && yw[0];
    genvar gk;
    generate for (gk = 0; gk < 4; gk = gk + 1) begin : g_lane
        wire mine = h == gk;
        reg          uv, dv, kuv, kdv;
        reg [SW-2:0] ud, dd;
        always @(posedge ck or negedge rn_q)
            if (!rn_q) begin uv <= 1'b0; dv <= 1'b0; kuv <= 1'b0; kdv <= 1'b0; end
            else begin
                // credits: a consumer of the lane answers its producer; a producer takes the credit off the lane
                kuv <= (mine && blk_u) ? cr_u : (mine && ym == 2'd1 && !l7) ? 1'b0 : kui[gk];
                kdv <= (mine && blk_d) ? cr_d : (mine && ym == 2'd2 && !l7) ? 1'b0 : kdi[gk];
                uv <= (mine && inj_u) ? 1'b1 : (mine && blk_u) ? 1'b0 : ui[SW*gk];
                dv <= (mine && inj_d) ? 1'b1 : (mine && blk_d) ? 1'b0 : di[SW*gk];
            end
        always @(posedge ck) begin
            ud <= (mine && inj_u) ? yw[SW-1:1] : ui[SW*gk + 1 +: SW - 1];
            dd <= (mine && inj_d) ? yw[SW-1:1] : di[SW*gk + 1 +: SW - 1];
        end
        assign uo[SW*gk +: SW] = {ud, uv};
        assign do_[SW*gk +: SW] = {dd, dv};
        assign kuo[gk] = kuv; assign kdo[gk] = kdv;
    end endgenerate
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin tu[0] <= 1'b0; td[0] <= 1'b0; lq[0] <= 1'b0; end
        else begin tu[0] <= ui_h[0]; td[0] <= di_h[0]; lq[0] <= li[0]; end
    always @(posedge ck) begin tu[SW-1:1] <= ui_h[SW-1:1]; td[SW-1:1] <= di_h[SW-1:1]; lq[SW-1:1] <= li[SW-1:1]; end
    wire [SW-1:0] sa = (am == 2'd1) ? tu : (am == 2'd2) ? td : lq;
    wire [SW-1:0] sb = (bm == 2'd1) ? tu : (bm == 2'd2) ? td : lq;
    // ---- operand stores: SA[bb] = beat bb (16 kk slots x 32 b); a shift register on the head pins at level 4 ----------
    reg  [2047:0] SA, SB;                              // [512 bb + 32 s +: 32]
    reg  [4:0]   ca, cb;                               // kk slots held (0..16)
    reg          ena, enb;                             // level 4: the store follows the head pins
    (* keep *) reg [7:0] ena_c, enb_c;                 // the same, one copy a 256 flops of the store
    (* keep *) reg [47:0] jn_c;                        // jn[2:0], one copy a 32 b of the two operands
    reg          l7b;                                  // level 7: round 0 is in, the stream now fills b
    reg  [2:0]   it;                                   // item: {g, round} (level 7: g)
    reg  [3:0]   jn;                                   // next sub-beat (kk slots 2 jn, 2 jn + 1)
    reg          pace, run, f, ocr;
    reg  [6:0]   stl;                                  // restart: 127 cycles in which the lanes drain (nothing is taken)
    wire         quiet = stl == 7'd0;
    reg  [1:0]   tok;
    reg  [5:0]   gap;
    wire         rho = it[0];
    wire         gi  = l7 ? it[0] : it[1];
    wire         pa  = l7 ? (gmax != 5'd0) : (gmax > {1'b0, rho, ath});
    wire         pb  = l7 ? (gmax > 5'd8)  : (gmax > {1'b0, rho, bth});
    // HEADS 1 (native TP8): one group -- the items are {round} (l7: one item), as the golden's P.V tree stops after group 0
    wire         active = run && quiet && (l7 ? (HEADS == 1 ? !it[0] : !it[1]) : (HEADS == 1 ? !it[1] : !it[2]));
    wire         awv = !l4 && sa[0] && !(l7 && l7b) && quiet;
    wire         bwv = !l4 && (l7 ? (sa[0] && l7b) : sb[0]) && quiet;
    wire [SW-1:0] bws = l7 ? sa : sb;
    wire         afz = quiet && l4 && ena && ncq[0] && ncq[4:1] == (far ? 4'd1 : 4'd2);     // beat 3 is being shifted in
    wire         bfz = quiet && l4 && enb && ndq[0] && ndq[4:1] == (far ? 4'd1 : 4'd2);
    wire [4:0]   need = {jn[2:0] + 4'd1, 1'b0};
    wire         a_ok = !pa || ca >= need;
    wire         b_ok = !pb || cb >= need;
    wire         full = (!pa || ca == 5'd16) && (!pb || cb == 5'd16);
    wire         tok_in = (tdir ? td_q : tu_q) && quiet;
    wire         go7 = full && ((h == 2'd0) ? gap == 6'd0 : tok != 2'd0);
    wire         issue = active && (l7 ? (jn != 4'd0 || go7) : ((pa || pb) && a_ok && b_ok && !pace && (ocr || jn != 4'd0)));
    wire         cr_in = ((ym == 2'd1) ? kcu : (ym == 2'd2) ? kcd : lci_q) && quiet;
    // the operand stores are free again: at the item's last sub-beat; level 7 also when round 0 is in and round 1 may come
    wire         cr_a = (last && pa) || (l7 && awv && ca == 5'd15 && pb);
    wire         cr_b = last && pb && !l7;
    assign       cr_u = (am == 2'd1 && cr_a) || (bm == 2'd1 && cr_b);
    assign       cr_d = (am == 2'd2 && cr_a) || (bm == 2'd2 && cr_b);
    wire         last = issue && jn == 4'd7;
    integer s_, b_;
    always @(posedge ck) begin
        if (l4) begin
            for (s_ = 0; s_ < 8; s_ = s_ + 1) begin        // SA <= {wa, SA[2047:512]} in 8 slices of 64 b a beat
                if (ena_c[s_]) for (b_ = 0; b_ < 4; b_ = b_ + 1)
                    SA[512*b_ + 64*s_ +: 64] <= (b_ == 3) ? wa[64*s_ +: 64] : SA[512*(b_ + 1) + 64*s_ +: 64];
                if (enb_c[s_]) for (b_ = 0; b_ < 4; b_ = b_ + 1)
                    SB[512*b_ + 64*s_ +: 64] <= (b_ == 3) ? wb[64*s_ +: 64] : SB[512*(b_ + 1) + 64*s_ +: 64];
            end
        end else begin
            for (s_ = 0; s_ < 16; s_ = s_ + 1) for (b_ = 0; b_ < 4; b_ = b_ + 1) begin
                if (awv && sa[4:1] == s_) SA[512*b_ + 32*s_ +: 32] <= sa[6 + 32*b_ +: 32];
                if (bwv && bws[4:1] == s_) SB[512*b_ + 32*s_ +: 32] <= bws[6 + 32*b_ +: 32];
            end
        end
    end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin
            ca <= 5'd0; cb <= 5'd0; ena <= 1'b1; enb <= 1'b1; l7b <= 1'b0; it <= 3'd0; jn <= 4'd0; pace <= 1'b0; run <= 1'b0;
            ena_c <= 8'hff; enb_c <= 8'hff; jn_c <= 48'd0;
            f <= 1'b0; tok <= 2'd0; gap <= 6'd0; cra <= 1'b0; crb <= 1'b0; tuo <= 1'b0; tdo <= 1'b0; fo <= 1'b0; ocr <= 1'b1; lco <= 1'b0; stl <= 7'd0;
        end else begin
            cra <= 1'b0; crb <= 1'b0; pace <= 1'b0;
            lco <= !l4 && ((am == 2'd0 && cr_a) || (bm == 2'd0 && cr_b));
            if (cr_in) begin ocr <= 1'b1; if (ocr && !l7) f <= 1'b1; end
            if (issue && jn == 4'd0 && !l7) ocr <= 1'b0;
            tuo <= (l7 && !tdir) ? last : tu_q;
            tdo <= (l7 && tdir) ? last : td_q;
            fo <= fi_q | f;
            if (gap != 6'd0) gap <= gap - 6'd1;
            if (l7 && tok_in) tok <= tok + 2'd1;
            if (afz) begin ena <= 1'b0; ena_c <= 8'h00; ca <= 5'd16; end
            if (bfz) begin enb <= 1'b0; enb_c <= 8'h00; cb <= 5'd16; end
            if (stl != 7'd0) stl <= stl - 7'd1;
            if (quiet && l4 && ((ncq[0] && !ena && ncq[4:1] == 4'd0) || (ndq[0] && !enb && ndq[4:1] == 4'd0))) f <= 1'b1;   // a node over a held one
            if (awv) begin
                ca <= ca + 5'd1;
                if (ca == 5'd16 || sa[4:1] != ca[3:0]) f <= 1'b1;
                if (l7 && ca == 5'd15) l7b <= 1'b1;
            end
            if (bwv) begin
                cb <= cb + 5'd1;
                if (cb == 5'd16 || bws[4:1] != cb[3:0]) f <= 1'b1;
            end
            if (active && !l7 && !pa && !pb) it <= it + 3'd1;             // nothing under this node in this round
            if (issue) begin
                jn <= jn + 4'd1; jn_c <= {16{jn[2:0] + 3'd1}}; pace <= !l7;
                if (last) begin
                    jn <= 4'd0; jn_c <= 48'd0; it <= it + 3'd1; ca <= 5'd0; cb <= 5'd0; ena <= 1'b1; enb <= 1'b1; l7b <= 1'b0;
                    ena_c <= 8'hff; enb_c <= 8'hff;
                    cra <= l4 && pa; crb <= l4 && pb; gap <= 6'd48;
                    if (l7 && h != 2'd0) tok <= tok - 2'd1 + {1'b0, tok_in};
                end
            end
            if (start) begin
                ca <= 5'd0; cb <= 5'd0; ena <= 1'b1; enb <= 1'b1; l7b <= 1'b0; it <= 3'd0; jn <= 4'd0; pace <= 1'b0;
                ena_c <= 8'hff; enb_c <= 8'hff; jn_c <= 48'd0;
                run <= 1'b1; f <= 1'b0; tok <= 2'd0; gap <= 6'd0; ocr <= 1'b1; stl <= 7'd127;
            end
            if (quiet && (yf || pcol)) f <= 1'b1;
        end
    // ---- the sub-beat's operands (kk slots 2 jn and 2 jn + 1, 4 beats each), registered, and the 8 adders -------------
    reg  [255:0] a8, b8;
    integer j_, m_;
    always @* begin
        a8 = 256'd0; b8 = 256'd0;
        for (m_ = 0; m_ < 2; m_ = m_ + 1) for (b_ = 0; b_ < 4; b_ = b_ + 1) for (j_ = 0; j_ < 8; j_ = j_ + 1) begin
            if (jn_c[3*(4*m_ + b_) +: 3] == j_) a8[32*(4*m_ + b_) +: 32] = SA[512*b_ + 32*(2*j_ + m_) +: 32];
            if (jn_c[3*(8 + 4*m_ + b_) +: 3] == j_) b8[32*(4*m_ + b_) +: 32] = SB[512*b_ + 32*(2*j_ + m_) +: 32];
        end
        if (`KVD_AKMUT == 1) b8[32*3 +: 32] = b8[32*2 +: 32];
    end
    reg          ov;
    reg  [3:0]   otag;                                 // {j 3, g}
    reg  [255:0] oa, ob;
    always @(posedge ck or negedge rn_q) if (!rn_q) ov <= 1'b0; else ov <= issue;
    always @(posedge ck) begin otag <= {jn[2:0], gi}; oa <= pa ? a8 : 256'd0; ob <= pb ? b8 : 256'd0; end
    wire [255:0] y8;
    wire [7:0]   yv, ye;
    wire [4:0]   ytag;
    ot_hdc_delay #(.W(5), .D(ADD_LAT), .RESET(1)) u_tag (.clk(ck), .rst_n(rn_q), .d({ov, otag}), .q(ytag));
    genvar gi_;
    generate for (gi_ = 0; gi_ < 8; gi_ = gi_ + 1) begin : g_add
        wire [1:0] err;
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_add (.clk(ck), .rst_n(rn_q), .valid_in(ov),
            .a(oa[32*gi_ +: 32]), .b(ob[32*gi_ +: 32]), .y(y8[32*gi_ +: 32]), .err(err), .valid_out(yv[gi_]));
        assign ye[gi_] = yv[gi_] && err != 2'd0;
    end endgenerate
    assign       yf = |ye;
    // ---- result: two 128-b stream words a sub-beat (kk slot 2 j, then 2 j + 1); level 7: half a P.V beat ----------------
    reg  [127:0] yh;
    reg          yhv;
    reg  [3:0]   yht;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin yw[0] <= 1'b0; yhv <= 1'b0; end
        else begin
            yw[0] <= !l7 && (ytag[4] || yhv);
            yhv <= !l7 && ytag[4];
        end
    always @(posedge ck) begin
        if (ytag[4]) begin yw[SW-1:1] <= {y8[127:0], ytag[0], ytag[3:1], 1'b0}; yh <= y8[255:128]; yht <= ytag[3:0]; end
        else yw[SW-1:1] <= {yh, yht[0], yht[3:1], 1'b1};
    end
    assign lo = yw;
    (* keep *) reg [PW-1:0] pq;
    wire         pown = l7 && ytag[4];
    assign       pcol = pown && pi[0];
    always @(posedge ck or negedge rn_q) if (!rn_q) pq[0] <= 1'b0; else pq[0] <= pown | pi[0];
    always @(posedge ck) pq[PW-1:1] <= pown ? {y8, ytag[0], h, ytag[3:1]} : pi[PW-1:1];
    assign po = pq;
`ifdef KVD_AKDBG
    reg f_d;
    always @(posedge ck) begin
        f_d <= f;
        if (f && !f_d) $display("AKDBG %m t=%0t fault: cfg=%h it=%0d jn=%0d ca=%0d cb=%0d ena=%b enb=%b ocr=%b", $time, cf, it, jn, ca, cb, ena, enb, ocr);
        if (l4 && ((ncq[0] && !ena && ncq[4:1] == 4'd0) || (ndq[0] && !enb && ndq[4:1] == 4'd0))) $display("AKDBG %m t=%0t node over a held one nc=%h nd=%h", $time, ncq, ndq);
        if (awv && (ca == 5'd16 || sa[4:1] != ca[3:0])) $display("AKDBG %m t=%0t a stream idx %0d at count %0d", $time, sa[4:1], ca);
        if (bwv && (cb == 5'd16 || bws[4:1] != cb[3:0])) $display("AKDBG %m t=%0t b stream idx %0d at count %0d", $time, bws[4:1], cb);
        if (cr_in && ocr && !l7) $display("AKDBG %m t=%0t credit over credit", $time);
        if (yf) $display("AKDBG %m t=%0t adder error", $time);
        if (pcol) $display("AKDBG %m t=%0t P.V lane collision", $time);
        if (l4 && (afz || bfz)) $display("AKDBG %m t=%0t node in a=%b b=%b g=%b/%b gam=%0d/%0d it=%0d", $time, afz, bfz, ncq[5], ndq[5], ncq[9:6], ndq[9:6], it);
        if (l7 && issue && jn == 0) $display("AKDBG %m t=%0t emit g=%b h=%0d", $time, gi, h);
    end
`endif
endmodule

// kvsys-elements r2 2026-10-14: native TP8 master of the P.V tree cell (HEADS 1 fixed in RTL); the historical qkd_astk_pv
// view is the HEADS 2 build (it emits a second group's P.V beats on an empty stack: bench T=1 / T=129, 64 vs 32 beats).
module qkd_astk_pv_tp8 (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [17:0]     cfg,
    input  wire [511:0]    wa,
    input  wire [511:0]    wb,
    input  wire [9:0]      nc,
    input  wire [9:0]      nd,
    output wire [9:0]      nco,
    output wire [9:0]      ndo,
    output wire            cra,
    output wire            crb,
    input  wire [133:0]    li,
    output wire [133:0]    lo,
    input  wire [535:0]    ui,
    output wire [535:0]    uo,
    input  wire [535:0]    di,
    output wire [535:0]    do_,
    input  wire [262:0]    pi,
    output wire [262:0]    po,
    input  wire [5:0]      ci,
    output wire [5:0]      co,
    input  wire            lci,
    output wire            lco,
    input  wire [3:0]      kui,
    output wire [3:0]      kuo,
    input  wire [3:0]      kdi,
    output wire [3:0]      kdo,
    input  wire            tui,
    output wire            tuo,
    input  wire            tdi,
    output wire            tdo,
    input  wire            fi,
    output wire            fo
);
    qkd_astk_pv #(.HEADS(1)) u (.ck(ck), .rst_n(rst_n), .cfg(cfg), .wa(wa), .wb(wb), .nc(nc), .nd(nd), .nco(nco), .ndo(ndo), .cra(cra), .crb(crb), .li(li), .lo(lo), .ui(ui), .uo(uo), .di(di), .do_(do_), .pi(pi), .po(po), .ci(ci), .co(co), .lci(lci), .lco(lco), .kui(kui), .kuo(kuo), .kdi(kdi), .kdo(kdo), .tui(tui), .tuo(tuo), .tdi(tdi), .tdo(tdo), .fi(fi), .fo(fo));
endmodule

// ---- one column's lanes through a leaf that only passes them (qkd_astk_ep / qkd_astk_ex) ---------------------------
module qkd_astk_lanes (
    input  wire          ck,
    input  wire          rn,
    input  wire [535:0]  ui,
    output wire [535:0]  uo,
    input  wire [535:0]  di,
    output wire [535:0]  do_,
    input  wire [262:0]  pi,
    output wire [262:0]  po,
    input  wire [5:0]    ci,
    output wire [5:0]    co,
    input  wire [3:0]    kui,
    output wire [3:0]    kuo,
    input  wire [3:0]    kdi,
    output wire [3:0]    kdo,
    input  wire          tui,
    output wire          tuo,
    input  wire          tdi,
    output wire          tdo,
    input  wire          fi,
    output wire          fo
);
    (* keep *) reg [535:0] uq, dq;
    (* keep *) reg [262:0] pq;
    (* keep *) reg [5:0]   cq;
    (* keep *) reg         tu_q, td_q, f_q;
    (* keep *) reg [3:0]   ku_q, kd_q;
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_v
        always @(posedge ck or negedge rn)
            if (!rn) begin uq[134*k] <= 1'b0; dq[134*k] <= 1'b0; end
            else begin uq[134*k] <= ui[134*k]; dq[134*k] <= di[134*k]; end
        always @(posedge ck) begin uq[134*k + 1 +: 133] <= ui[134*k + 1 +: 133]; dq[134*k + 1 +: 133] <= di[134*k + 1 +: 133]; end
    end endgenerate
    always @(posedge ck or negedge rn)
        if (!rn) begin pq[0] <= 1'b0; cq[0] <= 1'b0; tu_q <= 1'b0; td_q <= 1'b0; f_q <= 1'b0; ku_q <= 4'd0; kd_q <= 4'd0; end
        else begin pq[0] <= pi[0]; cq[0] <= ci[0]; tu_q <= tui; td_q <= tdi; f_q <= fi; ku_q <= kui; kd_q <= kdi; end
    always @(posedge ck) begin pq[262:1] <= pi[262:1]; cq[5:1] <= ci[5:1]; end
    assign uo = uq; assign do_ = dq; assign po = pq; assign co = cq; assign tuo = tu_q; assign tdo = td_q; assign fo = f_q;
    assign kuo = ku_q; assign kdo = kd_q;
endmodule

// ---- the exp datapath of one head of one engine slice: e = exp(s - M), one position a cycle -------------------------
// xa [65:0] in  = {M 32 (the pass's value for this head), s 32, pos, v}       xe [33:0] out = {e 32, fault, v}
// Latency XL = 1 + ADD_LAT + XD + 1 (pin flop, subtract, ot_qwen_nearhbm_exp_p, output register); the units and their
// order are ot_qwen_nearhbm_exp_quad_h's.  One exp unit is a 109-stage pipe of ~15.6k flops, so a head is a leaf.
// The lanes of the column it stands in cross it (pure registered feed-through).
module qkd_astk_ex (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [65:0]   xa,
    output reg  [33:0]   xe,
    input  wire [535:0]  ui,   output wire [535:0] uo,   input  wire [535:0] di,   output wire [535:0] do_,
    input  wire [262:0]  pi,   output wire [262:0] po,   input  wire [5:0]   ci,   output wire [5:0]   co,
    input  wire [3:0]    kui,  output wire [3:0]   kuo,  input  wire [3:0]   kdi,  output wire [3:0]   kdo,
    input  wire          tui,  output wire         tuo,  input  wire         tdi,  output wire         tdo,
    input  wire          fi,   output wire         fo
);
    localparam integer ADD_LAT = 7, SFU_LA = 7, SFU_LM = 7;
    localparam integer XD = 7 * SFU_LM + 8 * SFU_LA + 4;
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep_hierarchy *) qkd_astk_lanes u_l (.ck(ck), .rn(rn_q), .ui(ui), .uo(uo), .di(di), .do_(do_), .pi(pi), .po(po),
        .ci(ci), .co(co), .kui(kui), .kuo(kuo), .kdi(kdi), .kdo(kdo), .tui(tui), .tuo(tuo), .tdi(tdi), .tdo(tdo), .fi(fi), .fo(fo));
    (* keep *) reg [65:0] xq;
    always @(posedge ck or negedge rn_q) if (!rn_q) xq[0] <= 1'b0; else xq[0] <= xa[0];
    always @(posedge ck) xq[65:1] <= xa[65:1];
    wire         pv1 = xq[0] && xq[1];
    wire         vD, posD;
    ot_hdc_delay #(.W(2), .D(ADD_LAT + XD), .RESET(1)) u_tag (.clk(ck), .rst_n(rn_q), .d(xq[1:0]), .q({posD, vD}));
    wire [31:0]  mm = xq[65:34];
    wire [31:0]  x, e;
    wire [1:0]   err;
    wire         vo, xvo, xf;
    ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_sub (.clk(ck), .rst_n(rn_q), .valid_in(pv1),
        .a(pv1 ? xq[33:2] : 32'd0), .b(pv1 ? {~mm[31], mm[30:0]} : 32'd0), .y(x), .err(err), .valid_out(vo));
    ot_qwen_nearhbm_exp_p #(.LA(SFU_LA), .LM(SFU_LM)) u_exp (.clk(ck), .rst_n(rn_q), .v(vo), .x(x), .y(e), .vo(xvo), .fault(xf));
    reg f;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin f <= 1'b0; xe[1:0] <= 2'b00; end
        else begin
            if ((vo && err != 2'd0) || (vD && posD && xf)) f <= 1'b1;
            xe[0] <= vD; xe[1] <= f;
        end
    always @(posedge ck) xe[33:2] <= e ^ ((`KVD_AKMUT == 5) ? 32'd1 : 32'd0);
endmodule

// ---- the sequence of one pass: the nonempty chunks (gam, k), gam-major; the same in every slice ---------------------
module qkd_astk_seq (
    input  wire          ck,
    input  wire          rn,
    input  wire          start,
    input  wire          trig,
    input  wire [13:0]   T,
    input  wire [1:0]    S,
    output reg           v,
    output reg           g,
    output reg  [3:0]    gam,
    output reg  [3:0]    k,
    output reg           klst,               // the group's last block
    output wire          busy,
    output wire          sg_o
);
    wire [13:0] base_s = {5'd0, S, 7'd0};
    wire        any_s = T > base_s;
    wire [13:0] rem = T - base_s;
    wire [4:0]  gmax = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));
    reg         act, sg;
    reg  [4:0]  gm;
    reg  [3:0]  kk;
    wire [13:0] kb = T - 14'd1 - base_s - {6'd0, gm[3:0], 3'd0};
    wire [3:0]  kl = kb[12:9];
    wire        emit = act && gm < gmax;
    assign busy = act; assign sg_o = sg;
    always @(posedge ck or negedge rn)
        if (!rn) begin act <= 1'b0; sg <= 1'b0; v <= 1'b0; gm <= 5'd0; kk <= 4'd0; end
        else begin
            v <= emit;
            if (act) begin
                if (!emit) begin act <= 1'b0; sg <= !sg; end
                else if (kk == kl) begin kk <= 4'd0; gm <= gm + 5'd1; end
                else kk <= kk + 4'd1;
            end else if (trig) begin act <= 1'b1; gm <= 5'd0; kk <= 4'd0; end
            if (start) begin act <= 1'b0; sg <= 1'b0; v <= 1'b0; end
        end
    always @(posedge ck) begin g <= sg; gam <= gm[3:0]; k <= kk; klst <= kk == kl; end
endmodule

// ---- one row engine's stack slice: port, memories, chains ------------------------------------------------------------
// sq = {stack 2, engine 3}.  The engine's K pass scores the positions j = engine of every group; its V pass reads e of
// the groups gam = engine (mod 8).  So: the scores stay here (512 x 128 SRAM by {g, k, gam}); every slice runs the
// same sequence of chunks (gam, k) and adds ITS position's e to the chunk's partial sum, which walks the slices in
// order j = 0..7 (the golden's sequential chunk sum, element by element); the chunk's eight bf16 e ride with it and
// come back down the return chain to the slice that owns the group (64 x 512 e SRAM, one row a chunk).
// so [424:0] in / si [633:0] out   the engine's control tile (qkd_ectl so / si, bit for bit)
// qi [571:0] in                    command bus (a tap) {M word 36 = {data 32, hh 2, g, v}, kdone 2, q_data 512,
//                                   q_beat 6, q_valid, T 14, start}
// xi [266:0] in / xo out           return chain {lmax 256, any 2, score count g1 4, g0 4, fault}
// zi [650:0] in / zo out           chunk chain {e row 512, sum 128, gam 4, k 4, g, token, v} (slice j - 1 -> j)
// ri [521:0] in                    e-row bus (a tap) {row 512, gam 4, k 4, g, v}: slice 7's zo, relayed down the strip
// xa [263:0] out / xe [135:0] in   the slice's four exp leaves qkd_astk_ex (head h: xa[66 h +: 66], xe[34 h +: 34])
// cr in                            node credit (from the engine's level-4 tree cell)
// The e read: address flop at the pin, SRAM, one of 8 slots, output flop at the pin = 3 cycles (the engine is built with
// KVD_ERL 3; the golden's contract is 1): every port is a flop at the pin.  A slice starts its pass 6 cycles after the token of the
// slice below, so the partial sum of a chunk meets this slice's e on the same edge whatever the wire between them.
module qkd_astk_ep #(
    parameter integer STATIC_SCHEDULE=0,
    parameter integer EXP_START_AGE=0,
    parameter integer HEADS=`KVD_HEADS
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    sq,
    input  wire [424:0]  so,
    output wire [633:0]  si,
    input  wire [571:0]  qi,
    input  wire [266:0]  xi,
    output reg  [266:0]  xo,
    input  wire [650:0]  zi,
    output reg  [650:0]  zo,
    input  wire [521:0]  ri,
    output reg  [263:0]  xa,
    input  wire [135:0]  xe,
    input  wire          cr,
    input  wire [535:0]  ui,   output wire [535:0] uo,   input  wire [535:0] di,   output wire [535:0] do_,
    input  wire [262:0]  pi,   output wire [262:0] po,   input  wire [5:0]   ci,   output wire [5:0]   co,
    input  wire [3:0]    kui,  output wire [3:0]   kuo,  input  wire [3:0]   kdi,  output wire [3:0]   kdo,
    input  wire          tui,  output wire         tuo,  input  wire         tdi,  output wire         tdo,
    input  wire          fi,   output wire         fo
);
    localparam integer ADD_LAT = 7, SFU_LA = 7, SFU_LM = 7;
    localparam integer XD = 7 * SFU_LM + 8 * SFU_LA + 4;
    localparam integer XL = 1 + ADD_LAT + XD + 1;      // qkd_astk_ex
    localparam integer DT = 2 + XL + 1;                // sequence word -> SRAM -> xa -> ex -> the xe pin flop
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep_hierarchy *) qkd_astk_lanes u_l (.ck(ck), .rn(rn_q), .ui(ui), .uo(uo), .di(di), .do_(do_), .pi(pi), .po(po),
        .ci(ci), .co(co), .kui(kui), .kuo(kuo), .kdi(kdi), .kdo(kdo), .tui(tui), .tuo(tuo), .tdi(tdi), .tdo(tdo), .fi(fi), .fo(fo));
    (* keep *) reg [4:0] sq_q;
    always @(posedge ck) sq_q <= sq;
    wire [1:0] S = sq_q[4:3];
    wire [2:0] Q = sq_q[2:0];
    // ---- pin flops -----------------------------------------------------------------------------------------------------
    (* keep *) reg [424:0] so_q;
    (* keep *) reg [571:0] qq;
    (* keep *) reg [266:0] xq;
    (* keep *) reg [650:0] zq;
    (* keep *) reg [521:0] rq;
    (* keep *) reg [135:0] eq;
    (* keep *) reg         cr_q;
    (* keep *) reg [7:0]   eqc;                        // the four leaves' {fault, v}
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin so_q[0] <= 1'b0; so_q[13] <= 1'b0; so_q[424] <= 1'b0; qq[0] <= 1'b0; qq[15] <= 1'b0; qq[536:534] <= 3'd0; xq[10:0] <= 11'd0;
                         zq[1:0] <= 2'b00; rq[0] <= 1'b0; eqc <= 8'd0; cr_q <= 1'b0; end
        else begin so_q[0] <= so[0]; so_q[13] <= so[13]; so_q[424] <= so[424]; qq[0] <= qi[0]; qq[15] <= qi[15]; qq[536:534] <= qi[536:534];
                   xq[10:0] <= xi[10:0]; zq[1:0] <= zi[1:0]; rq[0] <= ri[0];
                   eqc <= {xe[103:102], xe[69:68], xe[35:34], xe[1:0]}; cr_q <= cr; end
    always @(posedge ck) begin
        so_q[12:1] <= so[12:1]; so_q[423:14] <= so[423:14];
        qq[14:1] <= qi[14:1]; qq[533:16] <= qi[533:16]; qq[571:537] <= qi[571:537]; xq[266:11] <= xi[266:11];
        zq[650:2] <= zi[650:2]; rq[521:1] <= ri[521:1]; eq <= xe;
    end
    wire         start = qq[0];
    wire [13:0]  T = qq[14:1];
    // Compiler ages are measured in edges AFTER the local start edge.
    reg [15:0] schedule_age;
    reg schedule_active;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin schedule_age<=0; schedule_active<=0; end
        else if (start) begin schedule_age<=0; schedule_active<=1; end
        else if (schedule_active && schedule_age!=16'hffff) schedule_age<=schedule_age+1'b1;

    wire [1:0]   kdone = qq[535:534];
    wire         mv = qq[536], mg = qq[537];
    wire [1:0]   mh = qq[539:538];
    wire [31:0]  md = qq[571:540];
    wire         sc_v = so_q[13];
    wire [11:0]  sc_a = so_q[25:14];
    wire [127:0] sc_d = so_q[153:26];
    // ---- M, the pass trigger (slice 0: K pass done and M in; the others: the token) ------------------------------------
    reg  [255:0] M;
    reg  [2:0]   mc0, mc1, cyc8;
    reg  [1:0]   gone;
    reg  [3:0]   xd;                                   // e written {g1 round 1, g1 round 0, g0 round 1, g0 round 0}
    reg  [5:0]   tokd;
    reg          f;
    integer i_;
    always @(posedge ck) if (mv) for (i_ = 0; i_ < 8; i_ = i_ + 1) if ({mg, mh} == i_) M[32*i_ +: 32] <= md;
    wire [1:0]   go = {kdone[1] && mc1 == 3'd4, kdone[0] && mc0 == 3'd4};
    wire         a_v, a_g, a_kl, a_busy, a_sg, b_v, b_g, b_kl, b_busy, b_sg;
    wire [3:0]   a_gam, a_k, b_gam, b_k;
    // RESTART: a start flushes the delayed trigger and opens a settle window (the exp pipe and the buses drain: no join
    // check, no e-row write, no token, no pass start) -- a start may follow another one at any distance.
    reg  [7:0]   stl;
    wire         quiet = stl == 8'd0;
    wire static_trigger = schedule_active && schedule_age == EXP_START_AGE-1;
    wire trig = STATIC_SCHEDULE ? static_trigger : (quiet && ((Q == 3'd0) ? (!a_busy && go[a_sg] && !gone[a_sg]) : tokd[5]));
    initial if (STATIC_SCHEDULE && (HEADS != 1 || EXP_START_AGE <= DT+16))
        $fatal(1,"invalid static ASTK EXP profile");
    reg  [DT-1:0] tb_sr;
    always @(posedge ck or negedge rn_q) if (!rn_q) tb_sr <= {DT{1'b0}}; else tb_sr <= start ? {DT{1'b0}} : {tb_sr[DT-2:0], trig};
    wire         trig_b = tb_sr[DT-1];
    qkd_astk_seq u_sa (.ck(ck), .rn(rn_q), .start(start), .trig(trig), .T(T), .S(S), .v(a_v), .g(a_g), .gam(a_gam), .k(a_k),
                       .klst(a_kl), .busy(a_busy), .sg_o(a_sg));
    qkd_astk_seq u_sb (.ck(ck), .rn(rn_q), .start(start), .trig(trig_b), .T(T), .S(S), .v(b_v), .g(b_g), .gam(b_gam), .k(b_k),
                       .klst(b_kl), .busy(b_busy), .sg_o(b_sg));
    // ---- score memory (this engine's positions j = Q), the read towards the exp datapath -------------------------------
    // two 256 x 128 macros, one a pass g (a pass is written by the K pass and read by its exp pass: never both), {k, gam}
    wire [8:0]   sc_wa = sc_a[11:3];
    wire [127:0] sc_q0, sc_q1;
    reg          sc_rg;
    always @(posedge ck) sc_rg <= a_g;
    ot_sram_1r1w_256x128_m1_r2c2 u_sc0 (.clk(ck), .r_ce_in(a_v && !a_g), .r_addr_in({a_k, a_gam}), .rd_out(sc_q0),
        .w_ce_in(sc_v && !sc_wa[8]), .w_addr_in(sc_wa[7:0]), .wd_in(sc_d), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(16'd0), .cr_en(2'b00), .cr_sel(14'd0));
    ot_sram_1r1w_256x128_m1_r2c2 u_sc1 (.clk(ck), .r_ce_in(a_v && a_g), .r_addr_in({a_k, a_gam}), .rd_out(sc_q1),
        .w_ce_in(sc_v && sc_wa[8]), .w_addr_in(sc_wa[7:0]), .wd_in(sc_d), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(16'd0), .cr_en(2'b00), .cr_sel(14'd0));
    wire [127:0] sc_rd = sc_rg ? sc_q1 : sc_q0;
    reg          a_v1, a_g1, a_p1;
    wire         a_pos = {1'b0, a_k, S, a_gam, Q} < T;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin a_v1 <= 1'b0; xa[0] <= 1'b0; xa[66] <= 1'b0; xa[132] <= 1'b0; xa[198] <= 1'b0; end
        else begin a_v1 <= a_v; xa[0] <= a_v1; xa[66] <= a_v1; xa[132] <= a_v1; xa[198] <= a_v1; end
    always @(posedge ck) begin a_g1 <= a_g; a_p1 <= a_pos; end
    genvar gx;
    generate for (gx = 0; gx < 4; gx = gx + 1) begin : g_xa
        always @(posedge ck) xa[66*gx + 1 +: 65] <= {a_g1 ? M[128 + 32*gx +: 32] : M[32*gx +: 32], sc_rd[32*gx +: 32], a_p1};
    end endgenerate
    // ---- the join: this slice's e meets the chunk's partial sum and e row ------------------------------------------------
    function automatic [15:0] bf16(input [31:0] x);
        bf16 = x[31:16] + ((x[15] && (x[14:0] != 15'd0 || x[16])) ? 16'd1 : 16'd0);
    endfunction
    wire         b_pos = {1'b0, b_k, S, b_gam, Q} < T;
    wire         first = Q == 3'd0;
    wire [127:0] e = {eq[135:104], eq[101:70], eq[67:36], eq[33:2]};
    wire         e_v = eqc[0];
    wire         e_f = eqc[1] | eqc[3] | eqc[5] | eqc[7];
    wire [63:0]  e16 = b_pos ? {bf16(e[127:96]), bf16(e[95:64]), bf16(e[63:32]), bf16(e[31:0])} : 64'd0;
    wire [511:0] row_in = first ? 512'd0 : zq[650:139];
    wire [511:0] row_m;
    genvar gj;
    generate for (gj = 0; gj < 8; gj = gj + 1) begin : g_slot
        assign row_m[64*gj +: 64] = (Q == gj) ? e16 : row_in[64*gj +: 64];
    end endgenerate
    wire [520:0] jd;
    ot_hdc_delay #(.W(521), .D(ADD_LAT)) u_row (.clk(ck), .rst_n(rn_q), .d({row_m, b_gam, b_k, b_g}), .q(jd));
    wire [127:0] sum;
    wire [3:0]   sv_, se;
    genvar h;
    generate for (h = 0; h < 4; h = h + 1) begin : g_ch
        wire [1:0] err;
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_chain (.clk(ck), .rst_n(rn_q), .valid_in(b_v),
            .a(first ? 32'd0 : zq[11 + 32*h +: 32]), .b(b_pos ? e[32*h +: 32] : 32'd0), .y(sum[32*h +: 32]), .err(err),
            .valid_out(sv_[h]));
        assign se[h] = sv_[h] && err != 2'd0;
    end endgenerate
    reg          tok1;
    wire         j_bad = quiet && ((b_v != e_v) || (eqc[2] != e_v) || (eqc[4] != e_v) || (eqc[6] != e_v) || (!first && (b_v != zq[0] || (b_v && {zq[10:7], zq[6:3], zq[2]} != {b_gam, b_k, b_g}))));
    // ---- e rows: this engine's groups (gam = Q, Q + 8), one 512-b row a chunk --------------------------------------------
    wire         r_me = rq[0] && rq[8:6] == Q && quiet;
    wire [13:0]  rkb = T - 14'd1 - {5'd0, S, 7'd0} - {6'd0, rq[9:6], 3'd0};
    wire [511:0] e_row;
    reg  [2:0]   jq;
    reg  [63:0]  e_rdq;
    always @(posedge ck) jq <= so_q[3:1];
    // four 64 x 128 macros side by side in address: a quarter of the row each, {g, k, gam[3]}
    wire [5:0]   e_wa = {rq[1], rq[5:2], rq[9]} + ((`KVD_AKMUT == 2) ? 6'd1 : 6'd0);
    wire [5:0]   e_ra = {so_q[12], so_q[11:8], so_q[7]};
    ot_sram_1r1w_64x128_m1_r2c2 u_e0 (.clk(ck), .r_ce_in(so_q[0]), .r_addr_in(e_ra), .rd_out(e_row[127:0]),
        .w_ce_in(r_me), .w_addr_in(e_wa), .wd_in(rq[137:10]), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(14'd0));
    ot_sram_1r1w_64x128_m1_r2c2 u_e1 (.clk(ck), .r_ce_in(so_q[0]), .r_addr_in(e_ra), .rd_out(e_row[255:128]),
        .w_ce_in(r_me), .w_addr_in(e_wa), .wd_in(rq[265:138]), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(14'd0));
    ot_sram_1r1w_64x128_m1_r2c2 u_e2 (.clk(ck), .r_ce_in(so_q[0]), .r_addr_in(e_ra), .rd_out(e_row[383:256]),
        .w_ce_in(r_me), .w_addr_in(e_wa), .wd_in(rq[393:266]), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(14'd0));
    ot_sram_1r1w_64x128_m1_r2c2 u_e3 (.clk(ck), .r_ce_in(so_q[0]), .r_addr_in(e_ra), .rd_out(e_row[511:384]),
        .w_ce_in(r_me), .w_addr_in(e_wa), .wd_in(rq[521:394]), .w_mask_in({128{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(14'd0));
    wire [63:0]  e_rd = (jq == 3'd0) ? e_row[0 +: 64] : (jq == 3'd1) ? e_row[64 +: 64] : (jq == 3'd2) ? e_row[128 +: 64] :
                        (jq == 3'd3) ? e_row[192 +: 64] : (jq == 3'd4) ? e_row[256 +: 64] : (jq == 3'd5) ? e_row[320 +: 64] :
                        (jq == 3'd6) ? e_row[384 +: 64] : e_row[448 +: 64];
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin mc0 <= 3'd0; mc1 <= 3'd0; cyc8 <= 3'd0; xd <= 4'd0; gone <= 2'b00; tokd <= 6'd0; tok1 <= 1'b0; f <= 1'b0;
                         zo[1:0] <= 2'b00; stl <= 8'd0; end
        else begin
            cyc8 <= cyc8 + 3'd1;
            tokd <= {tokd[4:0], zq[1] && quiet};
            if (stl != 8'd0) stl <= stl - 8'd1;
            tok1 <= trig; zo[1] <= tok1; zo[0] <= sv_[0];
            if (trig && first) gone[a_sg] <= 1'b1;
            if (j_bad || (|se) || (trig && a_busy) ||
                (STATIC_SCHEDULE && trig && (!quiet || !go[0] || a_sg)) ||
                (STATIC_SCHEDULE && !first && (tokd[5] != static_trigger))) f <= 1'b1;
            if (mv) begin if (mg) mc1 <= mc1 + 3'd1; else mc0 <= mc0 + 3'd1; end
            if (r_me && rq[5:2] == rkb[12:9]) xd[{rq[1], rq[9]}] <= 1'b1;
            if (start) begin mc0 <= 3'd0; mc1 <= 3'd0; xd <= 4'd0; gone <= 2'b00; tokd <= 6'd0; f <= 1'b0; stl <= 8'(DT + 16); tok1 <= 1'b0; zo[1] <= 1'b0; end
        end
    always @(posedge ck) zo[650:2] <= {jd[520:9], sum, jd[8:5], jd[4:1], jd[0]};
    // ---- the engine's inputs ---------------------------------------------------------------------------------------------
    reg  [31:0]  xdq;
    integer b_;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) xdq <= 32'd0;
        else for (b_ = 0; b_ < 32; b_ = b_ + 1) xdq[b_] <= (b_[2:0] == Q) && xd[b_[4:3]];
    // every engine input from its own register at the pin; the e word is registered behind the SRAM (KVD_ERL 3)
    (* keep *) reg [569:0] sio;
    always @(posedge ck) begin e_rdq <= e_rd; sio[17:1] <= {cyc8, qq[14:1]}; sio[536:19] <= qq[533:16]; end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin sio[0] <= 1'b0; sio[18] <= 1'b0; sio[569:537] <= 33'd0; end
        else begin sio[0] <= qq[0]; sio[18] <= qq[15]; sio[568:537] <= xdq; sio[569] <= cr_q; end
    assign si = {sio[569], e_rdq, sio[568:0]};
    // ---- return chain: score count, running maximum, fault ----------------------------------------------------------------
    function automatic fgt(input [31:0] a, input [31:0] b);
        fgt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction
    wire [255:0] lm = so_q[409:154];
    wire [1:0]   la = so_q[411:410];
    integer g_, h_;
    always @(posedge ck) begin
        for (g_ = 0; g_ < 2; g_ = g_ + 1) for (h_ = 0; h_ < 4; h_ = h_ + 1)
            xo[11 + 32*(4*g_ + h_) +: 32] <= (la[g_] && (!xq[9 + g_] || fgt(lm[32*(4*g_ + h_) +: 32], xq[11 + 32*(4*g_ + h_) +: 32])))
                                              ? lm[32*(4*g_ + h_) +: 32] : xq[11 + 32*(4*g_ + h_) +: 32];
    end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) xo[10:0] <= 11'd0;
        else begin
            xo[0] <= xq[0] | so_q[424] | e_f | f;
            xo[4:1] <= xq[4:1] + {3'd0, sc_v && !sc_a[11]};
            xo[8:5] <= xq[8:5] + {3'd0, sc_v && sc_a[11]};
            xo[10:9] <= xq[10:9] | la;
        end
`ifdef KVD_AKDBG
    always @(posedge ck) begin
        if (rn_q && j_bad) $display("AKDBG %m t=%0t join: b_v=%b e_v=%b%b%b%b zq.v=%b tags %h vs %h", $time, b_v, eqc[0], eqc[2], eqc[4], eqc[6], zq[0], zq[10:2], {b_gam, b_k, b_g});
        if (|se) $display("AKDBG %m t=%0t chunk adder error", $time);
        if (trig && a_busy) $display("AKDBG %m t=%0t trigger while busy", $time);
        if (so_q[424]) $display("AKDBG %m t=%0t ENGINE fault", $time);
        if (e_f) $display("AKDBG %m t=%0t exp fault", $time);
        if (trig) $display("AKDBG %m t=%0t pass start sg=%b", $time, a_sg);
    end
`endif
endmodule

// ---- Z tree node: one level of the golden's pairwise tree over the 16 chunk sums of a block ----------------------------
// zc = {level 2, stack 2}; tc = {T 14, start}.  zi / zo = {sum 128 (4 heads), slot 4, k 4, g, v}: the chunks arrive
// gam-major (all blocks k of slot 0, then slot 1, ...), so the left operand of block k waits in entry k for the right
// one; a right operand that does not exist (128 S + 512 k + 8 gam >= T, the golden's zero mask) is +0.  Four nodes in a
// row behind slice 7 give the block sums.
module qkd_astk_zn (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    zc,
    input  wire [14:0]   tc,
    input  wire [137:0]  zi,
    output reg  [137:0]  zo,
    input  wire          fi,
    output reg           fo
);
    localparam integer ADD_LAT = 7;
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [3:0]   zc_q;
    (* keep *) reg [14:0]  tq;
    (* keep *) reg [137:0] zq;
    (* keep *) reg         fi_q;
    always @(posedge ck) begin zc_q <= zc; tq[14:1] <= tc[14:1]; zq[137:1] <= zi[137:1]; end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin tq[0] <= 1'b0; zq[0] <= 1'b0; fi_q <= 1'b0; end
        else begin tq[0] <= tc[0]; zq[0] <= zi[0]; fi_q <= fi; end
    wire [1:0]  S = zc_q[1:0], L = zc_q[3:2];
    wire [13:0] T = tq[14:1];
    wire        start = tq[0];
    reg  [5:0]  stl;                                    // restart: 32 cycles in which the chain drains
    wire        v = zq[0] && stl == 6'd0, g = zq[1];
    wire [3:0]  k = zq[5:2], slot = zq[9:6];
    wire [127:0] d = zq[137:10];
    // the right sibling's first chunk: gam = (slot | 1) << L
    wire [3:0]  sib = {slot[3:1], 1'b1};
    wire [3:0]  sgam = (L == 2'd0) ? sib : (L == 2'd1) ? {sib[2:0], 1'b0} : (L == 2'd2) ? {sib[1:0], 2'b00} : {sib[0], 3'b000};
    wire [14:0] cb = {6'd0, S, 7'd0} + {2'b00, k, 9'd0} + {8'd0, sgam, 3'd0};
    wire        pb = (cb < {1'b0, T}) && (`KVD_AKMUT != 3);
    reg  [127:0] sd [0:15];
    reg  [15:0]  sv;
    wire         put = v && !slot[0] && pb;
    wire         iss = v && (slot[0] || !pb);
    reg          ov, f;
    reg  [8:0]   ot;
    reg  [127:0] oa, ob;
    wire         of;
    always @(posedge ck) begin
        if (put) sd[k] <= d;
        ot <= {1'b0, slot[3:1], k, g};
        oa <= slot[0] ? sd[k] : d;
        ob <= slot[0] ? d : 128'd0;
    end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin sv <= 16'd0; ov <= 1'b0; f <= 1'b0; fo <= 1'b0; stl <= 6'd0; end
        else begin
            if (stl != 6'd0) stl <= stl - 6'd1;
            ov <= iss; fo <= fi_q | f;
            if (put) begin sv[k] <= 1'b1; if (sv[k]) f <= 1'b1; end
            if (v && slot[0]) begin sv[k] <= 1'b0; if (!sv[k]) f <= 1'b1; end
            if (of) f <= 1'b1;
            if (start) begin sv <= 16'd0; f <= 1'b0; stl <= 6'd32; end
        end
    wire [127:0] y;
    wire [3:0]   yv, ye;
    wire [9:0]   yt;
    ot_hdc_delay #(.W(10), .D(ADD_LAT), .RESET(1)) u_tag (.clk(ck), .rst_n(rn_q), .d({ov, ot}), .q(yt));
    genvar gh;
    generate for (gh = 0; gh < 4; gh = gh + 1) begin : g_add
        wire [1:0] err;
        ot_hdc_fp32_add_lat_sel #(.LAT(ADD_LAT), .NR(1)) u_add (.clk(ck), .rst_n(rn_q), .valid_in(ov),
            .a(oa[32*gh +: 32]), .b(ob[32*gh +: 32]), .y(y[32*gh +: 32]), .err(err), .valid_out(yv[gh]));
        assign ye[gh] = yv[gh] && err != 2'd0;
    end endgenerate
    assign of = |ye;
    always @(posedge ck or negedge rn_q) if (!rn_q) zo[0] <= 1'b0; else zo[0] <= yt[9];
    always @(posedge ck) zo[137:1] <= {y, yt[8:5], yt[4:1], yt[0]};
`ifdef KVD_AKDBG
    always @(posedge ck) if (rn_q && ((put && sv[k]) || (v && slot[0] && !sv[k]) || of)) $display("AKDBG %m t=%0t Z node: put=%b slot=%0d k=%0d sv=%b of=%b", $time, put, slot, k, sv[k], of);
`endif
endmodule

// ---- the stack's port -------------------------------------------------------------------------------------------------------
// st [1:0]  strap: the stack
// aq [539:0] in  = {q_data 512, q_beat 6, q_valid, layer 6, T 14, start}        lt [20:0] out = {layer 6, T 14, start}
// am [35:0]  in  = {data 32, hh 2, g, v} (M from the hub)
// ap [562:0] out = {pv_data 512, pv_beat 6, pv_g, pv_valid, pv_done 2, so_data 32, so_any, so_k 4, so_hh 2, so_g,
//                   so_type 2, so_valid}
// qo [571:0] out / xi [266:0] in   the engine chain;  co [5:0] out  the tree cells' {gmax, start};
// px / py [262:0] in  the two P.V lanes;  zi [137:0] in  the Z tree's block sums {sum 128, slot 4, k 4, g, v};
// fx / fy / fz in: tree and Z faults
module qkd_astk_ctl #(
    parameter integer HEADS = `KVD_HEADS,  // native TP8 = 1
    parameter integer STATIC_SCHEDULE=0,
    parameter integer LMAX_START_AGE=0,
    parameter integer Z_START_AGE=0,
    parameter integer Z_STRIDE=4
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [1:0]    st,
    input  wire [539:0]  aq,
    output reg  [20:0]   lt,
    input  wire [35:0]   am,
    output reg  [564:0]  ap,
    output reg           af,
    output reg  [571:0]  qo,
    input  wire [266:0]  xi,
    output reg  [5:0]    co,
    input  wire [262:0]  px,
    input  wire [262:0]  py,
    input  wire [137:0]  zi,
    input  wire          fx,
    input  wire          fy,
    input  wire          fz
);
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [1:0]   st_q;
    (* keep *) reg [539:0] aq_q;
    (* keep *) reg [35:0]  am_q;
    (* keep *) reg [266:0] xq;
    (* keep *) reg [262:0] pxq, pyq;
    (* keep *) reg [137:0] zq;
    (* keep *) reg         fx_q, fy_q, fz_q;
    always @(posedge ck) begin
        st_q <= st; aq_q[20:1] <= aq[20:1]; aq_q[539:22] <= aq[539:22]; am_q[35:1] <= am[35:1]; xq[266:11] <= xi[266:11];
        pxq[262:1] <= px[262:1]; pyq[262:1] <= py[262:1]; zq[137:1] <= zi[137:1];
    end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin aq_q[0] <= 1'b0; aq_q[21] <= 1'b0; am_q[0] <= 1'b0; xq[10:0] <= 11'd0; pxq[0] <= 1'b0; pyq[0] <= 1'b0;
                         zq[0] <= 1'b0; fx_q <= 1'b0; fy_q <= 1'b0; fz_q <= 1'b0; end
        else begin aq_q[0] <= aq[0]; aq_q[21] <= aq[21]; am_q[0] <= am[0]; xq[10:0] <= xi[10:0]; pxq[0] <= px[0]; pyq[0] <= py[0];
                   zq[0] <= zi[0]; fx_q <= fx; fy_q <= fy; fz_q <= fz; end
    wire         start = aq_q[0];
    wire [13:0]  T = aq_q[14:1];
    // Compiler ages are measured in edges AFTER the local start edge.
    reg [15:0] schedule_age;
    reg schedule_active;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin schedule_age<=0; schedule_active<=0; end
        else if (start) begin schedule_age<=0; schedule_active<=1; end
        else if (schedule_active && schedule_age!=16'hffff) schedule_age<=schedule_age+1'b1;

    // ---- stack geometry (the golden's expressions) ---------------------------------------------------------------------
    wire [13:0]  base_s = {5'd0, st_q, 7'd0};
    wire         any_s = T > base_s;
    wire [13:0]  rem = T - base_s;
    wire [4:0]   gmax_c = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));
    wire [13:0]  tail = {5'd0, T[8:0]};
    wire [13:0]  part = (tail > base_s) ? ((tail - base_s > 14'd128) ? 14'd128 : (tail - base_s)) : 14'd0;
    wire [11:0]  ns_c = {T[13:9], 7'd0} + part[11:0];
    wire [4:0]   nblk_c = !any_s ? 5'd0 : (((T - base_s - 14'd1) >> 9) + 14'd1);
    reg  [11:0]  n_s;
    reg  [4:0]   nblk;
    always @(posedge ck) begin n_s <= ns_c; nblk <= nblk_c; end
    // ---- K-pass completion and M count ---------------------------------------------------------------------------------
    reg  [11:0]  sc0, sc1;
    reg  [1:0]   kdone, lsent, zsent, pvd;
    reg  [2:0]   lh, mc0, mc1;
    reg  [4:0]   zn0, zn1;                             // block sums sent
    wire [1:0]   qgo = {(HEADS == 2) && kdone[1] && mc1 == 3'd4, kdone[0] && mc0 == 3'd4};
    // ---- Z block sums: a 16-entry queue, 4 messages each ---------------------------------------------------------------
    reg  [132:0] zf_m [0:15];                          // {sum 128, k 4, g}
    reg  [4:0]   zfw, zfr;
    reg  [1:0]   zh;
    reg          zovf;
    wire         z_ne = zfw != zfr;
    wire [132:0] z_hd = zf_m[zfr[3:0]];
    always @(posedge ck) if (zq[0] && stl == 7'd0) zf_m[zfw[3:0]] <= {zq[137:10], zq[5:2], zq[1]};
    wire         legacy_l_pend = (kdone[0] && !lsent[0]) || (HEADS == 2 && kdone[1] && lsent[0] && !lsent[1]);
    wire         lg = lsent[0];
    wire         legacy_zd0 = !zsent[0] && qgo[0] && zn0 == nblk && !z_ne;
    wire         legacy_zd1 = (HEADS == 2) && !zsent[1] && zsent[0] && qgo[1] && zn1 == nblk && !z_ne;
    wire l_slot = schedule_active && schedule_age >= LMAX_START_AGE-1 && schedule_age < LMAX_START_AGE+3;
    wire [15:0] z_age = schedule_age - (Z_START_AGE-1);
    wire z_window = schedule_active && schedule_age >= Z_START_AGE-1;
    wire z_slot = z_window && (z_age / Z_STRIDE < nblk) && (z_age % Z_STRIDE < 4);
    wire z_done_slot = z_window && z_age == nblk * Z_STRIDE;
    wire l_pend = STATIC_SCHEDULE ? l_slot : legacy_l_pend;
    wire z_emit = STATIC_SCHEDULE ? z_slot : z_ne;
    wire zd0 = STATIC_SCHEDULE ? z_done_slot : legacy_zd0;
    wire zd1 = STATIC_SCHEDULE ? 1'b0 : legacy_zd1;
    initial if (STATIC_SCHEDULE && (HEADS != 1 || LMAX_START_AGE < 1 ||
        Z_START_AGE < LMAX_START_AGE+4 || Z_STRIDE < 4)) $fatal(1,"invalid static ASTK CTL profile");
    // ---- P.V: the two lanes carry the two halves of a beat on the same edge ---------------------------------------------
    reg  [6:0]   stl;                                  // restart: 96 cycles in which the lanes and the Z nodes drain
    wire         quiet = stl == 7'd0;
    wire         pv_v = pxq[0] && pyq[0] && quiet;
    wire         pv_bad = quiet && ((pxq[0] != pyq[0]) || (pv_v && pxq[6:1] != pyq[6:1]));
    wire         z_in = zq[0] && quiet;
    wire [255:0] pdx = (`KVD_AKMUT == 4) ? pyq[262:7] : pxq[262:7];
    wire [255:0] pdy = (`KVD_AKMUT == 4) ? pxq[262:7] : pyq[262:7];
    // a beat's 16 lanes: kk = 4 j + i / 4, bb = i % 4; X holds kk mod 4 = 0, 1 and Y 2, 3 (each {slot 1, slot 0} x 4 beats)
    wire [511:0] pvw = {pdy, pdx};
    reg  [31:0]  lm_s, z_s;
    integer m_;
    always @* begin
        lm_s = 32'd0; z_s = 32'd0;
        for (m_ = 0; m_ < 8; m_ = m_ + 1) if ({lg, lh[1:0]} == m_) lm_s = xq[11 + 32*m_ +: 32];
        for (m_ = 0; m_ < 4; m_ = m_ + 1) if (zh == m_) z_s = z_hd[5 + 32*m_ +: 32];
    end
    reg          f;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin
            sc0 <= 12'd0; sc1 <= 12'd0; kdone <= 2'b00; lsent <= 2'b00; zsent <= 2'b00; pvd <= 2'b00; lh <= 3'd0; mc0 <= 3'd0;
            mc1 <= 3'd0; zn0 <= 5'd0; zn1 <= 5'd0; zfw <= 5'd0; zfr <= 5'd0; zh <= 2'd0; zovf <= 1'b0; f <= 1'b0; af <= 1'b0;
            ap[0] <= 1'b0; ap[45:43] <= 3'b000; lt[0] <= 1'b0; qo[0] <= 1'b0; qo[15] <= 1'b0; qo[536:534] <= 3'd0;
            co[0] <= 1'b0; stl <= 7'd0;
        end else begin
            lt[0] <= start; qo[0] <= start; qo[15] <= aq_q[21]; qo[535:534] <= kdone; qo[536] <= am_q[0]; co[0] <= start;
            ap[0] <= 1'b0; ap[45] <= pv_v; ap[44:43] <= pvd;
            af <= f | (quiet && (xq[0] | fx_q | fy_q | fz_q)) | zovf;
            if (pv_bad || (STATIC_SCHEDULE &&
                ((l_slot && !kdone[0]) || (z_slot && !z_ne) ||
                 (z_slot && (z_hd[0] || z_hd[4:1] != z_age / Z_STRIDE)) ||
                 (z_done_slot && (!qgo[0] || zn0 != nblk || z_ne))))) f <= 1'b1;
            if (pv_v && pxq[5:1] == 5'd31) pvd[pxq[6]] <= 1'b1;
            sc0 <= sc0 + {8'd0, xq[4:1]}; sc1 <= sc1 + {8'd0, xq[8:5]};
            if (sc0 == n_s) kdone[0] <= 1'b1;
            if (HEADS == 2 && sc1 == n_s) kdone[1] <= 1'b1;
            if (am_q[0]) begin if (am_q[1]) mc1 <= mc1 + 3'd1; else mc0 <= mc0 + 3'd1; end
            if (stl != 7'd0) stl <= stl - 7'd1;
            if (z_in) begin zfw <= zfw + 5'd1; if (zfw[3:0] == zfr[3:0] && zfw[4] != zfr[4]) zovf <= 1'b1; end
            // sideband: lmax first, then the Z block sums, then Z done
            if (l_pend) begin
                ap[0] <= 1'b1;
                if (lh == 3'd3) begin lh <= 3'd0; lsent[lg] <= 1'b1; end else lh <= lh + 3'd1;
            end else if (z_emit) begin
                ap[0] <= 1'b1;
                if (zh == 2'd3) begin
                    zh <= 2'd0; zfr <= zfr + 5'd1;
                    if (z_hd[0]) zn1 <= zn1 + 5'd1; else zn0 <= zn0 + 5'd1;
                end else zh <= zh + 2'd1;
            end else if (zd0 || zd1) begin
                ap[0] <= 1'b1; zsent[zd1] <= 1'b1;
            end
            if (start) begin
                sc0 <= 12'd0; sc1 <= 12'd0; kdone <= 2'b00; lsent <= 2'b00; zsent <= 2'b00; pvd <= 2'b00; lh <= 3'd0;
                mc0 <= 3'd0; mc1 <= 3'd0; zn0 <= 5'd0; zn1 <= 5'd0; zfw <= 5'd0; zfr <= 5'd0; zh <= 2'd0; f <= 1'b0; zovf <= 1'b0;
                stl <= 7'd96;
            end
        end
    always @(posedge ck) begin
        lt[20:1] <= aq_q[20:1];
        qo[14:1] <= T; qo[533:16] <= aq_q[539:22]; qo[571:537] <= am_q[35:1];
        co[5:1] <= gmax_c;
        ap[564:46] <= {pvw, 1'b0, pxq[5:1], pxq[6]};
        // {so_data 32, so_any, so_k 4, so_hh 2, so_g, so_type 2}
        // a stack without a position has no maximum (the return chain may still hold the last layer's)
        if (l_pend) ap[42:1] <= {lm_s, xq[9 + lg] && n_s != 12'd0, 4'd0, lh[1:0], lg, 2'd0};
        else if (z_emit) ap[42:1] <= {z_s, 1'b1, z_hd[4:1], zh, z_hd[0], 2'd1};
        else ap[42:1] <= {32'd0, 1'b1, 4'd0, 2'd0, zd1, 2'd2};
    end
`ifdef KVD_AKDBG
    always @(posedge ck) begin
        if (rn_q && pv_bad) $display("AKDBG %m t=%0t P.V lanes apart: x %b beat %0d g %b, y %b beat %0d g %b", $time, pxq[0], pxq[5:1], pxq[6], pyq[0], pyq[5:1], pyq[6]);
        if (zovf) $display("AKDBG %m t=%0t Z queue overflow", $time);
        if (xq[0] | fx_q | fy_q | fz_q) $display("AKDBG %m t=%0t fault in: chain %b x %b y %b z %b", $time, xq[0], fx_q, fy_q, fz_q);
        if (start) $display("AKDBG %m t=%0t start T=%0d", $time, T);
    end
`endif
endmodule

// kvsys-elements r2 2026-10-14: native TP8 master of the aggregator control leaf (HEADS 1 fixed in RTL, like
// qkd_ectl_a/b/c_tp8): the historical qkd_astk_ctl view is the HEADS 2 build and is not a native view.
module qkd_astk_ctl_tp8 #(
    parameter integer STATIC_SCHEDULE=0,
    parameter integer LMAX_START_AGE=0,
    parameter integer Z_START_AGE=0,
    parameter integer Z_STRIDE=4
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [1:0]    st,
    input  wire [539:0]  aq,
    output wire [20:0]   lt,
    input  wire [35:0]   am,
    output wire [564:0]  ap,
    output wire          af,
    output wire [571:0]  qo,
    input  wire [266:0]  xi,
    output wire [5:0]    co,
    input  wire [262:0]  px,
    input  wire [262:0]  py,
    input  wire [137:0]  zi,
    input  wire          fx,
    input  wire          fy,
    input  wire          fz
);
    qkd_astk_ctl #(.HEADS(1), .STATIC_SCHEDULE(STATIC_SCHEDULE), .LMAX_START_AGE(LMAX_START_AGE),
        .Z_START_AGE(Z_START_AGE), .Z_STRIDE(Z_STRIDE)) u (.ck(ck), .rst_n(rst_n), .st(st), .aq(aq), .lt(lt), .am(am), .ap(ap), .af(af), .qo(qo), .xi(xi),
        .co(co), .px(px), .py(py), .zi(zi), .fx(fx), .fy(fy), .fz(fz));
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ME result path (qwen-vm-me 2026-10-08): the W12 port elements' result rows from the band slabs to the banked vector
// memory, credit / valid, bit-exact.
//
// The spine writes a result BURST on every op-output edge (ot_qwen_me_spport_w12 r_v && r_last, the spine's `ov`):
// each of the 12 port elements writes up to PQ = 4 rows (16 x FP32 + a lane mask) at once, i.e. up to 8 rows per band
// and 48 per burst, at a fixed engine edge.  The banked VM takes one result row a cycle.  So:
//   ot_qfd_res_ser    one per band (beside the band's port slab): captures each burst of its NS = 8 slots at the engine
//                     edge (me_en sampling, so a paused engine's held outputs are taken once), stores it (one 64 x 512
//                     macro per slot for the data, flops for row / mask / slot header), and sends it as beats
//                     {row, mask, data, end} in slot order, one a cycle, under CRB credits from the merge; a burst with
//                     no row in this band sends one NUL beat {nul, end}.  rok (registered) is high while at least RS + 2
//                     bursts of room are left: it is ANDed into the die's me_mem_ok, so the engine (whose clock stops
//                     within RS edges of rok falling) can never overrun the band's store.
//   ot_qfd_res_merge  in the vector memory (the 6:1 merge onto its result row write): a CRB-deep input FIFO per band;
//                     bursts are merged in order, band 0's beats, then band 1's, ... band NB-1's (NUL heads of the
//                     bands ahead are popped in the same cycle), one row a cycle into a single write register that the
//                     VM's bank-write arbiter takes when the row's bank is free.  When the last row of a burst is
//                     written (or a burst had no row at all), land_cnt counts it: the tree top's progress / idle count
//                     LANDED bursts (ot_qwen_me_spctl_w12 LANDED = 1), so a consumer never reads a result row that is not
//                     in the memory.  Row order is the base's burst order, band order within a burst (rows of one burst
//                     are distinct, so the base's same-edge write order is preserved where it matters).
// MUT = 1 (ot_qfd_res_ser): slot 1's mask is replaced by slot 0's (bench must FAIL).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_rs_slotmem #(
    parameter integer DB = 32,
    parameter integer LDB = 5,
    parameter integer USE_MACRO = 0
) (
    input  wire           clk,
    input  wire           re,
    input  wire [LDB-1:0] raddr,
    output wire [511:0]   q,
    input  wire           we,
    input  wire [LDB-1:0] waddr,
    input  wire [511:0]   wdata
);
    generate if (USE_MACRO != 0) begin : g_mac
        wire [5:0] ra = raddr, wa = waddr;            // zero-extended to the macro's 64 lines
        ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdata), .w_mask_in({512{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end else begin : g_beh
        reg [511:0] mem [0:DB-1];
        reg [511:0] qr;
        always @(posedge clk) begin
            if (re) qr <= mem[raddr];
            if (we) mem[waddr] <= wdata;
        end
        assign q = qr;
    end endgenerate
endmodule


module ot_qfd_res_ser #(
    parameter integer NS = 8,
    parameter integer W = 16,
    parameter integer AW = 24,
    parameter integer RW = 20,
    parameter integer DB = 32,          // bursts held (power of 2, <= 64 with the macro)
    parameter integer RS = 12,          // stall-loop edges: rok low at edge t -> at most RS more engine edges
    parameter integer CRB = 4,          // credits (the merge's input FIFO depth for this band)
    parameter integer USE_MACRO = 0,
    parameter integer MUT = 0,
    // TSR = 1 (safe-qwen S-D2, 2026-10-08; 0 = unchanged): the beat's slot select t2_s -> o_data (8:1 x 512 b, routed
    // TT -1,143 post-CTS: t2_s[0] -> o_data[400], 30 of 34 cells buffers) comes from a REGISTERED copy per 64-bit output
    // slice (keep_hierarchy leaves, registered from t1_s with t2_s, so 0 added cycles); each copy drives one slice.
    parameter integer TSR = 0,
    // MEC = 1 (struct-close 2026-10-09, "-cl"; 0 = unchanged): the boundary capture loads EVERY edge instead of under
    // me_en.  tsr41-a66978536-tc-bal32 failed post-CTS TT -789.8 on me_en (input) -> c_data[*] load enables (4,096 b + the
    // header words).  Every use of the captured burst is gated by c_v (= me_en && i_ov of the same edge): slot writes,
    // header / row / mask writes, wp / n and the hi_bad fault, so a burst captured without me_en is never observed.
    // 0 cycles; me_en now drives one flop (c_v).
    parameter integer MEC = `ifdef OT_QFD_RES_MEC 1 `else 0 `endif,
    // RDS (struct-close 2026-10-09; 0 = unchanged): tsr42m failed post-CTS TT -757 (19,676 endpoints) on rp -> hdr[rp] ->
    // pick -> srow / smask[{rp, pick}] -> d_row / d_mask: the send decision AND the 512-entry flop-array read in one
    // stage.  The row / mask read leaves the decision stage: it is indexed by the REGISTERED {d_p, d_s} (the same index,
    // one edge later).  RDS = 1: t1_row / t1_mask <= srow / smask[{d_p, d_s}] (one 512:1 stage from flops);
    // RDS = 2: two registered levels, t1: the 8 slot rows of burst d_p (64:1), t2: the slot t1_s (8:1).  0 cycles: the
    // row / mask ride t1 / t2 beside the slot-memory read anyway.  Safe: burst d_p cannot be rewritten within 2 edges
    // (rok keeps n + RS + 2 <= DB, so wp never reaches a burst still being sent).
    parameter integer RDS = `ifdef OT_QFD_RES_RDS `OT_QFD_RES_RDS `else 0 `endif
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 me_en,
    // from the band's port elements (engine-clock registers: sampled on engine edges)
    input  wire                 i_ov,
    input  wire [NS-1:0]        i_we,
    input  wire [NS*AW-1:0]     i_addr,
    input  wire [NS*W-1:0]      i_mask,
    input  wire [NS*W*32-1:0]   i_data,
    // beats to the merge (credit / valid)
    output reg                  o_v,
    output reg                  o_end,
    output reg                  o_nul,
    output reg  [RW-1:0]        o_row,
    output reg  [W-1:0]         o_mask,
    output reg  [W*32-1:0]      o_data,
    input  wire                 o_cr,
    output reg                  rok,
    output reg                  fault
);
    localparam integer LDB = $clog2(DB);
    localparam integer LS = (NS > 1) ? $clog2(NS) : 1;
    localparam integer LC = $clog2(CRB + 1) + 1;
    // ---- capture (block boundary): one burst per engine edge ----
    reg               c_v;
    reg  [NS-1:0]     c_we;
    reg  [NS*AW-1:0]  c_addr;
    reg  [NS*W-1:0]   c_mask;
    reg  [NS*W*32-1:0] c_data;
`ifndef OT_QFD_RES_MUT_CVNOEN
    always @(posedge clk or negedge rst_n) if (!rst_n) c_v <= 1'b0; else c_v <= me_en && i_ov;
`else   // struct-close mutant for MEC: the burst valid ignores me_en (a paused engine's held burst is taken again)
    always @(posedge clk or negedge rst_n) if (!rst_n) c_v <= 1'b0; else c_v <= i_ov;
`endif
    always @(posedge clk) if (me_en || MEC != 0) begin c_we <= i_we & {NS{i_ov}}; c_addr <= i_addr; c_mask <= i_mask; c_data <= i_data; end
    // ---- store: slot s of burst wp ----
    reg  [NS-1:0]  hdr [0:DB-1];
    reg  [RW-1:0]  srow [0:NS*DB-1];
    reg  [W-1:0]   smask [0:NS*DB-1];
    reg  [LDB-1:0] wp, rp;
    reg  [LDB:0]   n;                    // bursts stored, not yet fully sent
    reg  [NS-1:0]  sent;
    reg  [LC-1:0]  cr;
    // ---- send decision ----
    wire [NS-1:0]  hm = hdr[rp] & ~sent;
    reg  [LS-1:0]  pick;
    reg            more;
    integer j;
    always @(*) begin
        pick = 0; more = 1'b0;
        for (j = NS - 1; j >= 0; j = j - 1) if (hm[j]) pick = j;
        more = |(hm & ~({{(NS-1){1'b0}}, 1'b1} << pick));
    end
    wire can = (n != 0) && (cr != 0);
    wire pop = can && !more;
    reg            d_v, d_nul, d_end;
    reg  [LS-1:0]  d_s;
    reg  [LDB-1:0] d_p;
    reg  [RW-1:0]  d_row;
    reg  [W-1:0]   d_mask;
    wire [W-1:0]   mk0 = smask[{rp, {LS{1'b0}}}];
    wire [W-1:0]   mk  = (MUT != 0 && pick == 1) ? mk0 : smask[{rp, pick}];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; n <= 0; sent <= 0; cr <= CRB[LC-1:0]; d_v <= 1'b0; fault <= 1'b0; rok <= 1'b0;
        end else begin
            d_v <= can;
            if (can) begin
                if (pop) begin rp <= rp + 1'b1; sent <= 0; end
                else sent <= sent | ({{(NS-1){1'b0}}, 1'b1} << pick);
            end
            if (c_v) wp <= wp + 1'b1;
            n <= n + (c_v ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            cr <= cr + (o_cr ? 1'b1 : 1'b0) - (can ? 1'b1 : 1'b0);
            rok <= ({1'b0, n} + (c_v ? 1 : 0) + RS + 2) <= DB;
            if ((c_v && n == DB) || (c_v && hi_bad) || (o_cr && cr == CRB[LC-1:0])) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        d_nul <= (hm == 0); d_end <= !more; d_s <= pick; d_p <= rp; d_row <= srow[{rp, pick}]; d_mask <= mk;
    end
    // writes of the captured burst
    integer s;
    reg [RW-1:0] ra;
    always @(posedge clk) if (c_v) begin
        hdr[wp] <= c_we;
        for (s = 0; s < NS; s = s + 1) begin
            srow[{wp, s[LS-1:0]}] <= c_addr[s*AW +: RW];
            smask[{wp, s[LS-1:0]}] <= c_mask[s*W +: W];
        end
    end
    reg hi_bad;
    integer q;
    always @(*) begin
        hi_bad = 1'b0;
        for (q = 0; q < NS; q = q + 1) if (c_we[q] && (|c_addr[q*AW + RW +: AW - RW])) hi_bad = 1'b1;
    end
    // ---- slot memories (one edge registered read), capture beside each, then the beat ----
    wire [NS*512-1:0] mq;
    reg  [NS*512-1:0] cap;
    reg  t1_v, t1_nul, t1_end, t2_v, t2_nul, t2_end, t3_v, t3_nul, t3_end;
    reg  [LS-1:0] t3_s; reg [RW-1:0] t3_row; reg [W-1:0] t3_mask;
    reg  [LS-1:0] t1_s, t2_s;
    reg  [RW-1:0] t1_row, t2_row;
    reg  [W-1:0]  t1_mask, t2_mask;
    genvar g;
    generate for (g = 0; g < NS; g = g + 1) begin : g_slot
        ot_qfd_rs_slotmem #(.DB(DB), .LDB(LDB), .USE_MACRO(USE_MACRO)) u_m (.clk(clk),
            .re(d_v && !d_nul && d_s == g), .raddr(d_p), .q(mq[g*512 +: 512]),
            .we(c_v && c_we[g]), .waddr(wp), .wdata(c_data[g*W*32 +: W*32]));
        always @(posedge clk) if (t1_v && !t1_nul && t1_s == g) cap[g*512 +: 512] <= mq[g*512 +: 512];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin t1_v <= 1'b0; t2_v <= 1'b0; t3_v <= 1'b0; o_v <= 1'b0; end
        else begin t1_v <= d_v; t2_v <= t1_v; t3_v <= t2_v; o_v <= (TSR == 2) ? t3_v : t2_v; end
    end
    // RDS row / mask read (see the parameter)
    wire [W-1:0]  mkd0 = smask[{d_p, {LS{1'b0}}}];
    wire [W-1:0]  mkd  = (MUT != 0 && d_s == 1) ? mkd0 : smask[{d_p, d_s}];
    reg  [RW-1:0] rb_row  [0:NS-1];
    reg  [W-1:0]  rb_mask [0:NS-1];
    integer rs_i;
    always @(posedge clk) for (rs_i = 0; rs_i < NS; rs_i = rs_i + 1) begin
        rb_row[rs_i]  <= srow[{d_p, rs_i[LS-1:0]}];
        rb_mask[rs_i] <= (MUT != 0 && rs_i == 1) ? mkd0 : smask[{d_p, rs_i[LS-1:0]}];
    end
    always @(posedge clk) begin
        t1_nul <= d_nul; t1_end <= d_end; t1_s <= d_s;
`ifndef OT_QFD_RES_MUT_RDS
        if (RDS == 1) begin t1_row <= srow[{d_p, d_s}]; t1_mask <= mkd; end
`else   // mutant: the row read indexed by the live rp (one burst late after a pop) instead of the registered d_p
        if (RDS == 1) begin t1_row <= srow[{rp, d_s}]; t1_mask <= smask[{rp, d_s}]; end
`endif
        else begin t1_row <= d_row; t1_mask <= d_mask; end
        t2_nul <= t1_nul; t2_end <= t1_end; t2_s <= t1_s;
`ifndef OT_QFD_RES_MUT_RDS
        if (RDS == 2) begin t2_row <= rb_row[t1_s]; t2_mask <= rb_mask[t1_s]; end
`else   // mutant: the second level selected by the stale slot (t2_s)
        if (RDS == 2) begin t2_row <= rb_row[t2_s]; t2_mask <= rb_mask[t2_s]; end
`endif
        else begin t2_row <= t1_row; t2_mask <= t1_mask; end
        t3_nul <= t2_nul; t3_end <= t2_end; t3_s <= t2_s; t3_row <= t2_row; t3_mask <= t2_mask;
        if (TSR == 2) begin o_nul <= t3_nul; o_end <= t3_end; o_row <= t3_row; o_mask <= t3_nul ? {W{1'b0}} : t3_mask; end
        else begin o_nul <= t2_nul; o_end <= t2_end; o_row <= t2_row; o_mask <= t2_nul ? {W{1'b0}} : t2_mask; end
    end
    // TSR = 2 (struct-close 2026-10-09, "-cl"): the 8:1 x 512 slot select becomes two registered levels: pair pre-select
    // pm[k] = cap of slot 2k / 2k+1 (one 2:1 per bit, next to the pair's capture flops, select = t2_s[0] from per-64-bit
    // kept copies), then o_data = pm[t3_s[2:1]] (4:1).  tsr41m-ci10 (core inset 10.8) failed post-place TT -1,035 on
    // g_odr.g_sl[4].u_c/q -> o_data[267]: one 8:1 level gathering 8 slot capture banks over the 777.6 um block
    // (wire 642 ps).  +1 cycle on the result beat (o_v / o_* move with it); credits unchanged.
    generate if (TSR == 2) begin : g_od2
        initial if (NS != 8 && NS != 4) $error("ot_qfd_res_ser TSR=2: NS == 4 or 8");
        reg [W*32-1:0] pm [0:NS/2-1];
        genvar k2, pr;
        for (k2 = 0; k2 < W * 32 / 64; k2 = k2 + 1) begin : g_sl2
            wire [2:0] sk;
            (* keep_hierarchy *) ot_qfd_rs_sel3 u_c (.clk(clk), .d(3'(t1_s)), .q(sk));     // = t2_s, per 64-bit slice
            wire [2:0] sk3;
            (* keep_hierarchy *) ot_qfd_rs_sel3 u_c3 (.clk(clk), .d(sk), .q(sk3));     // = t3_s
            for (pr = 0; pr < NS/2; pr = pr + 1) begin : g_pr
`ifndef OT_QFD_RES_MUT_PAIR
                always @(posedge clk) pm[pr][k2*64 +: 64] <= sk[0] ? cap[(2*pr+1)*512 + k2*64 +: 64] : cap[(2*pr)*512 + k2*64 +: 64];
`else           // mutant: the pair pre-select takes the wrong half
                always @(posedge clk) pm[pr][k2*64 +: 64] <= sk[0] ? cap[(2*pr)*512 + k2*64 +: 64] : cap[(2*pr+1)*512 + k2*64 +: 64];
`endif
            end
            always @(posedge clk) o_data[k2*64 +: 64] <= pm[(sk3 >> 1) & (NS/2 - 1)][k2*64 +: 64];
        end
    end else if (TSR == 0) begin : g_od
        always @(posedge clk) o_data <= cap[t2_s*512 +: 512];
    end else begin : g_odr
        initial if (NS > 8) $error("ot_qfd_res_ser TSR=1: NS <= 8 (3-bit select leaves)");
        genvar k;
        for (k = 0; k < W * 32 / 64; k = k + 1) begin : g_sl
            wire [2:0] sk;
            (* keep_hierarchy *) ot_qfd_rs_sel3 u_c (.clk(clk), .d(t1_s), .q(sk));
            always @(posedge clk) o_data[k*64 +: 64] <= cap[sk*512 + k*64 +: 64];
        end
    end endgenerate
endmodule

// TSR leaf: a kept 3-bit register (fixed width, no parameters: Yosys 0.68 asserts on parameterised keep_hierarchy)
module ot_qfd_rs_sel3 (input wire clk, input wire [2:0] d, output reg [2:0] q);
    always @(posedge clk) q <= d;
endmodule


module ot_qfd_res_merge #(
    parameter integer NB = 6,
    parameter integer W = 16,
    parameter integer RW = 20,
    parameter integer CRB = 4
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [NB-1:0]        b_v,
    input  wire [NB-1:0]        b_end,
    input  wire [NB-1:0]        b_nul,
    input  wire [NB*RW-1:0]     b_row,
    input  wire [NB*W-1:0]      b_mask,
    input  wire [NB*W*32-1:0]   b_data,
    output reg  [NB-1:0]        b_cr,
    // the write register (to the VM's bank-write arbiter)
    output reg                  m_v,
    output reg                  m_nowr,       // a burst-end token without a row
    output reg                  m_land,       // the burst ends with this entry
    output reg  [RW-1:0]        m_row,
    output reg  [W-1:0]         m_mask,
    output reg  [W*32-1:0]      m_data,
    input  wire                 m_take,
    output reg  [15:0]          land_cnt,
    output reg                  busy,
    output reg                  fault
);
    localparam integer LB = (NB > 1) ? $clog2(NB + 1) : 1;
    localparam integer LC = (CRB > 1) ? $clog2(CRB) : 1;
    localparam integer EW = 2 + RW + W + W*32;
    // ---- input registers (block boundary), then per-band FIFOs ----
    reg  [NB-1:0]      in_v;
    reg  [NB*EW-1:0]   in_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) in_v <= 0; else in_v <= b_v;
    genvar g;
    generate for (g = 0; g < NB; g = g + 1) begin : g_in
        always @(posedge clk) in_e[g*EW +: EW] <= {b_end[g], b_nul[g], b_row[g*RW +: RW], b_mask[g*W +: W], b_data[g*W*32 +: W*32]};
    end endgenerate
    reg  [EW-1:0]  fq [0:NB*CRB-1];
    reg  [LC-1:0]  fw [0:NB-1];
    reg  [LC-1:0]  fr [0:NB-1];
    reg  [LC:0]    fn [0:NB-1];
    wire [NB-1:0]  hv, hn, he;
    wire [NB*EW-1:0] hd;
    generate for (g = 0; g < NB; g = g + 1) begin : g_h
        assign hv[g] = (fn[g] != 0);
        assign hd[g*EW +: EW] = fq[g*CRB + fr[g]];
        assign he[g] = hd[g*EW + EW - 1];
        assign hn[g] = hd[g*EW + EW - 2];
    end endgenerate
    // ---- merge decision ----
    reg  [LB-1:0] ptr;
    wire          can_go = !m_v || m_take;
    reg  [NB-1:0] blk, popn;
    reg  [LB-1:0] fb;
    reg           fnd;
    integer b;
    always @(*) begin
        fnd = 1'b0; fb = NB[LB-1:0]; popn = 0;
        for (b = 0; b < NB; b = b + 1) blk[b] = (b >= ptr) && !(hv[b] && hn[b]);
        for (b = NB - 1; b >= 0; b = b - 1) if (blk[b]) fb = b;
        for (b = 0; b < NB; b = b + 1) popn[b] = (b >= ptr) && (b < fb);
    end
    wire          done_nul = (fb == NB);
    wire          row_ok = !done_nul && hv[fb];
    wire [EW-1:0] hsel = hd[fb*EW +: EW];
    wire [NB-1:0] pop = can_go ? (popn | (row_ok ? ({{(NB-1){1'b0}}, 1'b1} << fb) : {NB{1'b0}})) : {NB{1'b0}};
    reg           land_q;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ptr <= 0; m_v <= 1'b0; b_cr <= 0; land_cnt <= 0; land_q <= 1'b0; fault <= 1'b0; busy <= 1'b0;
            for (k = 0; k < NB; k = k + 1) begin fw[k] <= 0; fr[k] <= 0; fn[k] <= 0; end
        end else begin
            b_cr <= pop;
            for (k = 0; k < NB; k = k + 1) begin
                if (in_v[k]) fw[k] <= (fw[k] == CRB - 1) ? 0 : fw[k] + 1'b1;
                if (pop[k]) fr[k] <= (fr[k] == CRB - 1) ? 0 : fr[k] + 1'b1;
                fn[k] <= fn[k] + (in_v[k] ? 1'b1 : 1'b0) - (pop[k] ? 1'b1 : 1'b0);
                if (in_v[k] && fn[k] == CRB && !pop[k]) fault <= 1'b1;
            end
            land_q <= m_v && m_take && m_land;
            land_cnt <= land_cnt + (land_q ? 1'b1 : 1'b0);
            if (can_go) begin
                if (done_nul) begin
                    m_v <= 1'b1; m_nowr <= 1'b1; m_land <= 1'b1; ptr <= 0;
                end else if (row_ok) begin
                    m_v <= 1'b1; m_nowr <= 1'b0;
                    m_land <= hsel[EW-1] && (fb == NB - 1);
                    ptr <= hsel[EW-1] ? ((fb == NB - 1) ? 0 : fb + 1'b1) : fb;
                end else begin
                    m_v <= 1'b0; ptr <= fb;
                end
            end
            busy <= (|hv) || (|in_v) || m_v || ptr != 0 || land_q;
        end
    end
    always @(posedge clk) if (can_go && row_ok) begin
        m_row <= hsel[W*32 + W +: RW]; m_mask <= hsel[W*32 +: W]; m_data <= hsel[0 +: W*32];
    end
    generate for (g = 0; g < NB; g = g + 1) begin : g_fq
        always @(posedge clk) if (in_v[g]) fq[g*CRB + fw[g]] <= in_e[g*EW +: EW];
    end endgenerate
endmodule

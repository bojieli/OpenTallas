`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 streaming-domain (1.2 GHz at SS) attention ENGINE, current controller: the text of
// rtl/hdc/v41x/ot_hdc_v41x_attn.sv at main (945e8e7c6 REPL = 2 controller, slot-addressed p FIFO, PHYS stubs)
// with the FPL / FML / NBANKP latency parameters of rtl/hdc/v41x/ot_hdc_v41x_attn_lat.sv (cdc47f9a) re-applied by
// a three-way merge (git merge-file ours=attn_lat base=945e8e7c6^ theirs=945e8e7c6; three conflicts resolved:
// GUARD_Q = skew(7) + 2 with XD kept and CNTW = clog2(GUARD_Q + 3) (5 as built), the simulation-only set checker
// takes both edits, the transposer / PHYS stub modules come from the as-built file).  Module names suffixed _s;
// the tile is ot_hdc_v41x_attn_tile_l (rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv).  FPL = FML = 3, NBANKP = 0 is
// the as-built engine cycle for cycle.  A build lists ot_hdc_v41x_attn.sv (transposers, PHYS stubs, helpers),
// ot_hdc_v41x_attn_tile.sv, ot_hdc_v41x_attn_tile_lat.sv, ot_hdc_v41x_attn_staging.sv, ot_hdc_fastfp.sv and, for
// FPL > 3, ot_hdc_fp32_add_lat.sv and ot_hdc_prefix.sv.  (claude/hbm-fmax-attn-20261004, HBM-accelerator 1.2 GHz
// closure program.)
// ---------------------------------------------------------------------------
// Streaming binary-counter merge of one tile's p.v block partials.
module ot_hdc_v41x_attn_merge_s #(
    parameter integer H = 16,
    parameter integer DPT = 16,
    parameter integer MLEV = 4,
    parameter integer FPL = 3          // binary32 add latency
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,          // a p.v beat's block partial
    input  wire              ifin,        // of the job's last block
    input  wire [MLEV-1:0]   iblk,        // block index
    input  wire [H*32-1:0]   iy,
    input  wire [H-1:0]      if_,
    output wire              ov,          // a finished pv value (final blocks only)
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      of_
);
    wire [MLEV:0]          lv, lfin, llive;
    wire [(MLEV+1)*MLEV-1:0] lblk;
    wire [(MLEV+1)*H*32-1:0] lx;
    wire [(MLEV+1)*H-1:0]  lf;
    assign lv[0] = iv;
    assign lfin[0] = ifin;
    assign llive[0] = 1'b1;
    assign lblk[0 +: MLEV] = iblk;
    assign lx[0 +: H*32] = iy;
    assign lf[0 +: H] = if_;
    genvar gl, gh;
    generate
        for (gl = 0; gl < MLEV; gl = gl + 1) begin : g
            wire v = lv[gl];
            wire fin = lfin[gl];
            wire live = llive[gl];
            wire [MLEV-1:0] blk = lblk[gl*MLEV +: MLEV];
            wire use_ = blk[gl];
            wire store = v && live && !fin && !use_;
            // ring of DPT entries: head = entry of the beat's dim
            reg [H*33-1:0] ring [0:DPT-1];
            wire [H*33-1:0] head = ring[0];
            integer i;
            always @(posedge clk)
                if (v) begin
                    for (i = 0; i < DPT - 1; i = i + 1) ring[i] <= ring[i+1];
                    ring[DPT-1] <= store ? {lf[gl*H +: H], lx[gl*H*32 +: H*32]} : head;
                end
            for (gh = 0; gh < H; gh = gh + 1) begin : g_h
                wire [31:0] a = use_ ? head[gh*32 +: 32] : 32'd0;
                wire [31:0] y;
                wire af;
                ot_hdc_v41x_qaddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(a),
                                 .b(lx[(gl*H+gh)*32 +: 32]), .y(y), .fault(af));
                wire fdq;
                ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(lf[gl*H+gh] | (use_ & head[H*32+gh])), .q(fdq));
                assign lx[((gl+1)*H+gh)*32 +: 32] = y;
                assign lf[(gl+1)*H+gh] = fdq | af;
            end
            // the level's tags travel beside its adders (FPL cycles)
            ot_hdc_v41x_vdly #(.D(FPL)) u_dv (.clk(clk), .rst_n(rst_n), .d(v), .q(lv[gl+1]));
            ot_hdc_v41x_dly #(.W(2 + MLEV), .D(FPL)) u_dt (.clk(clk), .d({fin, live && (use_ || fin), blk}),
                .q({lfin[gl+1], llive[gl+1], lblk[(gl+1)*MLEV +: MLEV]}));
        end
    endgenerate
    assign ov = lv[MLEV] && lfin[MLEV] && llive[MLEV];
    assign oy = lx[MLEV*H*32 +: H*32];
    assign of_ = lf[MLEV*H +: H];
endmodule

// ---------------------------------------------------------------------------
// The block merge with PER-HEAD control copies (engine MFAN = 1): ot_hdc_v41x_attn_merge_s's function and ring
// order exactly, but every level's ring is split per head (H x 33 bits x DPT entries) and each head slice is
// steered by its own registered copy of the level's {v, fin, live, blk} (ot_hdc_v41x_kreg, a keep_hierarchy
// register, so synthesis cannot merge the equal copies):
// the shift enable of one 528-bit x DPT ring was one net with ~4,000 loads (routed SS -739 ps in the D = 64
// controller vehicle).  Level 0's copies need a register: the merge input (beat, tags, partials) is registered
// once, +1 cycle on the p.v output only (the engine delays pv_c by the same cycle).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_merge_x #(
    parameter integer H = 16,
    parameter integer DPT = 16,
    parameter integer MLEV = 4,
    parameter integer FPL = 3,
    parameter integer F12 = 0          // 1: FP32 adds are the 1.2 GHz f12 units (rtl/hdc/ot_hdc_fp32_f12.sv)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,
    input  wire              ifin,
    input  wire [MLEV-1:0]   iblk,
    input  wire [H*32-1:0]   iy,
    input  wire [H-1:0]      if_,
    output wire              ov,
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      of_
);
    // per level, per head: control copies {v, fin, live, blk}
    wire [(MLEV+1)*H-1:0]      cv, cfin, clive;
    wire [(MLEV+1)*H*MLEV-1:0] cblk;
    wire [(MLEV+1)*H*32-1:0]   lx;
    wire [(MLEV+1)*H-1:0]      lf;
    genvar gl, gh;
    generate
        // level 0: registered input, one control copy per head
        reg [H*32-1:0] r_iy;
        reg [H-1:0]    r_if;
        always @(posedge clk) begin r_iy <= iy; r_if <= if_; end
        assign lx[0 +: H*32] = r_iy;
        assign lf[0 +: H] = r_if;
        for (gh = 0; gh < H; gh = gh + 1) begin : g_c0
            wire c_v, c_fin;
            wire [MLEV-1:0] c_blk;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_cv (.clk(clk), .rst_n(rst_n), .d(iv), .q(c_v));
            ot_hdc_v41x_kreg #(.W(1 + MLEV), .R(0)) u_ct (.clk(clk), .rst_n(rst_n), .d({ifin, iblk}), .q({c_fin, c_blk}));
            assign cv[gh] = c_v;
            assign cfin[gh] = c_fin;
            assign clive[gh] = 1'b1;
            assign cblk[gh*MLEV +: MLEV] = c_blk;
        end
        for (gl = 0; gl < MLEV; gl = gl + 1) begin : g
            // the level's tags, from head 0's copies (all copies are equal), FPL - 1 shared stages + per-head copy
            wire v0 = cv[gl*H];
            wire fin0 = cfin[gl*H];
            wire live0 = clive[gl*H];
            wire [MLEV-1:0] blk0 = cblk[(gl*H)*MLEV +: MLEV];
            wire dv;
            wire [MLEV+1:0] dt;
            ot_hdc_v41x_vdly #(.D(FPL - 1)) u_dv (.clk(clk), .rst_n(rst_n), .d(v0), .q(dv));
            ot_hdc_v41x_dly #(.W(2 + MLEV), .D(FPL - 1)) u_dt (.clk(clk), .d({fin0, live0 && (blk0[gl] || fin0), blk0}),
                .q(dt));
            for (gh = 0; gh < H; gh = gh + 1) begin : g_h
                wire v = cv[gl*H+gh];
                wire fin = cfin[gl*H+gh];
                wire live = clive[gl*H+gh];
                wire [MLEV-1:0] blk = cblk[(gl*H+gh)*MLEV +: MLEV];
                wire use_ = blk[gl];
                wire store = v && live && !fin && !use_;
                reg [32:0] ring [0:DPT-1];
                wire [32:0] head = ring[0];
                integer i;
                always @(posedge clk)
                    if (v) begin
                        for (i = 0; i < DPT - 1; i = i + 1) ring[i] <= ring[i+1];
                        ring[DPT-1] <= store ? {lf[gl*H+gh], lx[(gl*H+gh)*32 +: 32]} : head;
                    end
                wire [31:0] a = use_ ? head[31:0] : 32'd0;
                wire [31:0] y;
                wire af;
                ot_hdc_v41x_qaddf #(.LAT(FPL), .F12(F12)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(a),
                                 .b(lx[(gl*H+gh)*32 +: 32]), .y(y), .fault(af));
                wire fdq;
                ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(lf[gl*H+gh] | (use_ & head[32])), .q(fdq));
                assign lx[((gl+1)*H+gh)*32 +: 32] = y;
                assign lf[(gl+1)*H+gh] = fdq | af;
                // next level's control copy for this head
                wire n_v, n_fin, n_live;
                wire [MLEV-1:0] n_blk;
                ot_hdc_v41x_kreg #(.W(1), .R(1)) u_nv (.clk(clk), .rst_n(rst_n), .d(dv), .q(n_v));
                ot_hdc_v41x_kreg #(.W(2 + MLEV), .R(0)) u_nt (.clk(clk), .rst_n(rst_n), .d(dt), .q({n_fin, n_live, n_blk}));
                assign cv[(gl+1)*H+gh] = n_v;
                assign cfin[(gl+1)*H+gh] = n_fin;
                assign clive[(gl+1)*H+gh] = n_live;
                assign cblk[((gl+1)*H+gh)*MLEV +: MLEV] = n_blk;
            end
        end
    endgenerate
    assign ov = cv[MLEV*H] && cfin[MLEV*H] && clive[MLEV*H];
    assign oy = lx[MLEV*H*32 +: H*32];
    assign of_ = lf[MLEV*H +: H];
endmodule


module ot_hdc_v41x_attn_s #(
    parameter integer H = 16,          // heads per die
    parameter integer D = 512,         // head_dim
    parameter integer TD = 64,         // tile width (dims per q.k beat / rows per p.v block)
    parameter integer NL = 4,          // row lanes (rows per cycle)
    parameter integer TROWS = 640,     // staging buffer rows
    parameter integer SC_CRED = 64,     // score-beat credits
    parameter integer PV_CRED = 64,    // pv-beat credits
    parameter bit SRAM_MACRO = 0,      // ASAP7 packed-row staging macro boundary
    parameter integer PWORDS = 1,      // probability words per p handshake (1 or 2)
    parameter integer ILV = 0,         // 1: position-interleaved verify mode (see the controller)
    parameter integer REPL = 0,        // 1 (needs ILV = 1): per-tile copies of the transposer read/write indices,
                                       //   the E-register q.k/p.v select and registered pad flags, and a 2-entry
                                       //   p-word input FIFO so q_ready/p_ready come from registers only;
                                       // 2: as 1, plus one register stage between every issue/fill decision and
                                       //   its per-tile copies and the staging read (q.k and p.v beats both enter
                                       //   the E register one cycle later; guards one cycle longer)
    parameter integer PHYS = 0,        // 1: physical characterisation only (transposers/merges stubbed)
    parameter integer NSTAGE = 1,      // 2 (needs ILV = 1): two staging buffers, the front job writes and reads
                                       //   one while the back job fills from the other (per-position row lists)
    parameter integer FPL = 3,         // binary32 add latency (7: 1.2 GHz streaming domain)
    parameter integer FML = 3,         // tile product latency
    parameter integer NBANKP = 0,      // stationary banks; 0 = as built (3 / 4 with PWORDS 2, +1 with ILV).  The
                                       // bank lifetime grows with the skew (6 FPL): at FPL 7 more banks keep p.v
                                       // at one beat per cycle (see the W11 stream record)
    parameter integer TILE_S = 0,      // 1: the head-group tile ot_hdc_v41x_attn_tile_s (same cycles; hardens
                                       //    hierarchically, rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv)
    parameter integer FPLX = 0,        // >0: FP32 add latency of the lane trees and block merges (default FPL)
    parameter integer F12 = 0,         // 1: every FP32 add is the 1.2 GHz f12 unit (LAT 4: ot_hdc_fp32_add_f12_l4,
                                       //    registered operands; LAT 5: ot_hdc_fp32_add_f12_l5x, operand mux in front)
    parameter integer TRX = 0,         // 1 (REPL >= 1): transposers with per-element one-hot read selects and per-row
                                       //    one-hot write enables (ot_hdc_v41x_attn_tr_x; same cycles)
    parameter integer MFAN = 0,        // 1: the block merges with per-head control copies (ot_hdc_v41x_attn_merge_x;
                                       //    +1 cycle on p.v results only)
    parameter integer NARROW = 0       // 1: block counters (load / fill / issue / filled / count) BKW bits wide, not
                                       //    16 (values never exceed NBLKMAX; same values and cycles for T <= TROWS):
                                       //    shortens the controller's compare/increment loops for 1.2 GHz
) (
    input  wire                   clk,
    input  wire                   rst_n,
    // job
    input  wire                   job_v,
    input  wire [15:0]            job_t,
    output wire                   job_ready,
    // q
    input  wire                   q_v,
    input  wire [D*16-1:0]        q_w,
    output wire                   q_ready,
    // kv rows
    input  wire                   kv_v,
    input  wire [NL-1:0]          kv_m,
    input  wire [NL*(D/32)*265-1:0] kv_w,
    output wire                   kv_ready,
    // scores
    output reg                    sc_v,
    output reg  [15:0]            sc_row,
    output reg  [NL-1:0]          sc_m,
    output reg  [NL*H*32-1:0]     sc_y,
    output reg  [NL*H-1:0]        sc_f,
    input  wire                   sc_cr,
    // probabilities
    input  wire                   p_v,
    input  wire [PWORDS*TD*16-1:0] p_w,
    output wire                   p_ready,
    // pv
    output reg                    pv_v,
    output reg  [7:0]             pv_c,
    output reg  [NL*(D/TD)*H*32-1:0] pv_y,
    output reg  [NL*(D/TD)*H-1:0] pv_f,
    input  wire                   pv_cr,
    // bench visibility
    output wire                   qk_iss,
    output wire                   pv_iss
);
    localparam integer S = D / TD;
    localparam integer NT = NL * S;
    localparam integer G = D / 32;
    localparam integer GW = 265;
    localparam integer ROWW = G * GW;
    localparam integer R = TD / H;
    localparam integer PB = H;                         // p words per full block
    localparam integer DPT = D / NT;
    localparam integer FILLC = TD / NL;                // fill beats per block
    localparam integer DEPTH = (TROWS + NL - 1) / NL;
    localparam integer AW = $clog2(DEPTH);
    localparam integer NBLKMAX = (TROWS + TD - 1) / TD;
    localparam integer MLEV = (NBLKMAX <= 1) ? 1 : $clog2(NBLKMAX);
    localparam integer BKW = (NARROW != 0) ? $clog2(NBLKMAX + 1) + 1 : 16;   // block counter width
    localparam integer NBANK = (NBANKP > 0) ? NBANKP : (((PWORDS >= 2) ? 4 : 3) + ((ILV != 0) ? 1 : 0));
    localparam integer BW = (NBANK > 4) ? $clog2(NBANK) : 2;
    localparam integer BD = (NBANK <= 4) ? 4 : (1 << $clog2(NBANK));   // block -> bank table entries
    localparam integer LA = (NBANKP == 0) ? 3 : NBANK - 1;           // p-load lookahead, blocks (3 as built)
    localparam integer LVT = $clog2(TD / 8);
    localparam integer FX = (FPLX > 0) ? FPLX : FPL;         // lane-tree / merge add latency
    localparam integer TLAT = 3 + FML + FPL * (7 + LVT);   // tile: input -> ov (27 + 3 LVT as built)
    localparam integer LS = (S <= 1) ? 0 : $clog2(S);  // lane-tree levels

    // write-after-read guards (cycles from an issue decision to a load of the same bank)
    function automatic integer skew(input integer i);
        skew = (i == 0) ? 0 : FPL * (i - 1);
    endfunction
    function automatic integer guard_p(input integer dummy);
        integer g, j, m, best;
        begin
            best = 0;
            for (g = 0; g < PB; g = g + 1) begin
                m = 0;
                for (j = 0; j < R; j = j + 1)
                    if (skew((R * g + j) % 8) > m) m = skew((R * g + j) % 8);
                if (m - g / PWORDS > best) best = m - g / PWORDS;
            end
            guard_p = best + 1;
        end
    endfunction
    localparam integer GUARD_P = guard_p(0);
    // the last skewed read of a bank is skew(7) cycles after the first (+2: the
    // load's pipeline offset; 20 as built)
    localparam integer GUARD_Q = skew(7) + 2;
    localparam integer XD = (REPL >= 2) ? 1 : 0;      // REPL = 2: extra decision -> copy/read stage
    localparam integer CNTW = $clog2(GUARD_Q + 3);    // holds GUARD_Q + 1 + XD (5 as built)
    generate
        if (NSTAGE != 1 && !(NSTAGE == 2 && ILV != 0)) begin : g_bad_nstage
            initial $error("ot_hdc_v41x_attn: NSTAGE must be 1, or 2 with ILV = 1");
        end
        if (REPL != 0 && ILV == 0) begin : g_bad_repl
            initial $error("ot_hdc_v41x_attn: REPL = 1 needs ILV = 1");
        end
        if (!(PWORDS == 1 || (PWORDS == 2 && (PB % 2) == 0))) begin : g_bad_pwords
            initial $error("ot_hdc_v41x_attn: PWORDS must be 1, or 2 with an even word count per block");
        end
    endgenerate

    // ================= controller =================
    // ILV = 0: one job at a time (act, T, nblk, phase_pv).
    // ILV = 1: two job contexts.  The FRONT job (act, T, nblk, reuse_f, phase_pv = its q.k has issued) loads its
    // q set and KV rows and issues q.k; the BACK job (act_b, T_b, nblk_b) loads probability blocks, fills the
    // transposers and issues p.v.  A front job whose q.k has issued moves to the back when the back is free, and
    // the front then accepts the next job.  Shared resources, per cycle:
    //   tile issue slot  p.v first when ready, else q.k   (a p.v beat enters the E register one cycle after its
    //                    decision, like a q.k beat, so the two never meet there)
    //   buffer read port fill first when allowed (at most two blocks ahead of p.v), else q.k
    //   stationary load  p word first, else q word  (q_ready drops for a cycle a p word is accepted)
    //   stationary banks NBANK = 4 (PWORDS = 1) or 5 (PWORDS = 2): the p.v blocks' banks plus one q set; a new
    //                    set takes the lowest free bank whose write-after-read guard has expired.
    reg  [BKW-1:0] fill_blk_d;
    reg  [7:0]    fill_cnt_d;
    reg           rd_qk, rd_fill;
    wire          fill_wr = rd_fill;
    reg        act;
    reg [15:0] T;
    reg [BKW-1:0] nblk;
    reg        phase_pv;
    reg        reuse_f;               // ILV: the front job keeps the staged rows (job_t[15])
    reg        act_b;                 // ILV: back job
    reg        fbuf, bbuf;            // NSTAGE = 2: staging buffer of the front / back job
    reg [15:0] T_b;
    reg [BKW-1:0] nblk_b;
    reg [15:0] wptr;                  // rows written
    reg [15:0] qk_row;                // next q.k row base
    reg [7:0]  q_cnt;                 // q words loaded
    reg [BW-1:0] q_bank;
    reg [BW-1:0] next_bank;
    reg [NBANK-1:0] held;
    reg [CNTW-1:0] bcnt [0:NBANK-1];
    reg [7:0]  sc_cred;
    reg [7:0]  pv_cred;
    // p loads
    reg [BKW-1:0] pl_blk;                // block being loaded
    reg [7:0]  pl_word;               // word within it
    reg [BW-1:0] pl_bank;
    reg [BW-1:0] blk_bank [0:BD-1];   // bank of block (index mod BD)
    // fills
    reg [BKW-1:0] fl_blk;
    reg [7:0]  fl_cnt;
    reg [BKW-1:0] filled_upto;           // blocks whose transposer fill is complete
    // p.v issue
    reg [BKW-1:0] iss_blk;
    reg [7:0]  iss_c;

    // the p side's job (ILV: the back job)
    wire [15:0] T_p = (ILV != 0) ? T_b : T;
    wire [BKW-1:0] nblk_p = (ILV != 0) ? nblk_b : nblk;
    wire        p_side = (ILV != 0) ? act_b : (act && (q_cnt == H));
    wire        pv_side = (ILV != 0) ? act_b : (act && phase_pv);
    wire [15:0] job_rows = (ILV != 0) ? {1'b0, job_t[14:0]} : job_t;

    wire [15:0] blk_rows0 = pl_blk * TD;                     // first row of the loading block
    wire [15:0] words_blk = ((T_p - blk_rows0) >= TD) ? PB : ((T_p - blk_rows0 + R - 1) / R);
    // bank allocation: ILV = 0 round robin (next_bank); ILV = 1 the lowest free bank
    localparam integer P_THR = GUARD_Q - GUARD_P + 1;
    reg [BW-1:0] q_alloc, p_alloc;
    reg          q_alloc_ok, p_alloc_ok;
    integer ab;
    always @* begin
        q_alloc = {BW{1'b0}}; p_alloc = {BW{1'b0}}; q_alloc_ok = 1'b0; p_alloc_ok = 1'b0;
        for (ab = NBANK - 1; ab >= 0; ab = ab - 1) begin
            if (!held[ab] && (bcnt[ab] == 0)) begin q_alloc = ab[BW-1:0]; q_alloc_ok = 1'b1; end
            if (!held[ab] && (bcnt[ab] <= P_THR)) begin p_alloc = ab[BW-1:0]; p_alloc_ok = 1'b1; end
        end
    end
    wire [BW-1:0] nb_q = (ILV != 0) ? q_alloc : next_bank;
    wire [BW-1:0] nb_p = (ILV != 0) ? p_alloc : next_bank;
    wire q_bank_ok = (ILV != 0) ? q_alloc_ok : (!held[next_bank] && (bcnt[next_bank] == 0));
    wire p_bank_ok = (ILV != 0) ? p_alloc_ok : (!held[next_bank] && (bcnt[next_bank] <= P_THR));

    assign job_ready = !act;
    wire job_go = job_v && job_ready;
    // p words: a new block needs a free bank and at most 3 blocks between the issuing and the loading one
    wire p_ready_i = p_side && (pl_blk < nblk_p) && ((pl_word != 0) || (p_bank_ok && (pl_blk < iss_blk + LA)));
    // REPL: a 2-entry skid between the p port and the loader, so p_ready and q_ready come from registers
    // only (no p_v -> q_ready path); a p word reaches the loader one cycle after its handshake
    wire p_v_i;
    wire [PWORDS*TD*16-1:0] p_w_i;
    generate if (REPL != 0) begin : g_pskid
        // two fixed slots: a push writes slot wp, the loader reads slot rp; a pop only moves rp (no wide mux enable
        // behind the loader's accept logic)
        reg [1:0] sk_n;
        reg       wp, rp;
        reg [PWORDS*TD*16-1:0] sk0, sk1;
        wire push = p_v && p_ready, pop = p_v_i && p_ready_i;
        assign p_ready = (sk_n != 2'd2);
        assign p_v_i = (sk_n != 2'd0);
        assign p_w_i = rp ? sk1 : sk0;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin sk_n <= 2'd0; wp <= 1'b0; rp <= 1'b0; end
            else begin
                sk_n <= sk_n + (push ? 2'd1 : 2'd0) - (pop ? 2'd1 : 2'd0);
                if (push) wp <= !wp;
                if (pop) rp <= !rp;
            end
        end
        always @(posedge clk) begin
            if (push && !wp) sk0 <= p_w;
            if (push && wp) sk1 <= p_w;
        end
    end else begin : g_pdirect
        assign p_ready = p_ready_i;
        assign p_v_i = p_v;
        assign p_w_i = p_w;
    end endgenerate
    wire p_go = p_v_i && p_ready_i;
    wire p_last_word = p_go && ((PWORDS == 1) ? (pl_word + 1 == words_blk) : ({8'd0, pl_word} + PWORDS >= words_blk));
    wire p_w2v = (PWORDS > 1) && ({8'd0, pl_word} + 1 < words_blk);   // second word of the pair is live
    assign q_ready = act && (q_cnt < H) && ((q_cnt != 0) || q_bank_ok) && !((ILV != 0) && p_go);
    wire q_go = q_v && q_ready;
    // ILV: a job without the reuse flag rewrites the staging only once the back job's fills are done
    assign kv_ready = act && (wptr < T) && ((ILV == 0) || (NSTAGE == 2) || reuse_f || !act_b || (fl_blk >= nblk_b));
    wire kv_go = kv_v && kv_ready;

    // p.v issue
    wire iss_loaded = (pl_blk > iss_blk) || (p_last_word && (pl_blk == iss_blk));
    wire iss_final = (iss_blk + 1 == nblk_p);
    wire pv_go_raw = pv_side && (iss_blk < nblk_p) && iss_loaded && (filled_upto > iss_blk) &&
                 (!iss_final || (pv_cred != 0));
    wire pv_go = pv_go_raw;
    wire fl_half_free = (fl_blk < iss_blk + 2) || ((fl_blk == iss_blk + 2) && pv_go_raw && (iss_c + 1 == DPT));
    wire fl_go = pv_side && (fl_blk < nblk_p) && fl_half_free;
    // q.k issue (ILV: after the fill and the p.v beat of the cycle)
    wire qk_rows_ok = (wptr >= T) || (qk_row + NL <= wptr);
    wire qk_go = act && !phase_pv && (q_cnt == H) && (qk_row < T) && qk_rows_ok && (sc_cred != 0) &&
                 !((ILV != 0) && (((NSTAGE == 1) && fl_go) || pv_go));
    wire [BW-1:0] iss_bank = (pl_blk == iss_blk) ? ((pl_word == 0) ? nb_p : pl_bank) : blk_bank[iss_blk % BD];
    assign qk_iss = qk_go;
    assign pv_iss = pv_go;
    // ILV: back takes the front job when the front's q.k has issued and the back is free
    wire hand = (ILV != 0) && act && phase_pv && !act_b;

    integer b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            act <= 1'b0; T <= 16'd0; nblk <= 16'd0; phase_pv <= 1'b0; wptr <= 16'd0; qk_row <= 16'd0;
            q_cnt <= 8'd0; q_bank <= {BW{1'b0}}; next_bank <= {BW{1'b0}}; held <= {NBANK{1'b0}};
            for (b = 0; b < NBANK; b = b + 1) bcnt[b] <= {CNTW{1'b0}};
            sc_cred <= SC_CRED; pv_cred <= PV_CRED;
            pl_blk <= 16'd0; pl_word <= 8'd0; pl_bank <= {BW{1'b0}};
            fl_blk <= 16'd0; fl_cnt <= 8'd0; filled_upto <= 16'd0; iss_blk <= 16'd0; iss_c <= 8'd0;
            reuse_f <= 1'b0; act_b <= 1'b0; T_b <= 16'd0; nblk_b <= 16'd0; fbuf <= 1'b0; bbuf <= 1'b0;
        end else begin
            for (b = 0; b < NBANK; b = b + 1)
                if (bcnt[b] != 0) bcnt[b] <= bcnt[b] - 1'b1;
            if (job_go) begin
                act <= 1'b1; T <= job_rows; nblk <= (job_rows + TD - 1) / TD; phase_pv <= 1'b0;
                qk_row <= 16'd0; q_cnt <= 8'd0;
                if (ILV == 0) begin
                    wptr <= 16'd0;
                    pl_blk <= 16'd0; pl_word <= 8'd0; fl_blk <= 16'd0; fl_cnt <= 8'd0; filled_upto <= 16'd0;
                    iss_blk <= 16'd0; iss_c <= 8'd0;
                end else begin
                    reuse_f <= job_t[15] && (NSTAGE == 1);
                    if (!job_t[15] || (NSTAGE != 1)) wptr <= 16'd0;
                end
            end
            if (hand) begin
                act_b <= 1'b1; T_b <= T; nblk_b <= nblk; act <= 1'b0; phase_pv <= 1'b0;
                if (NSTAGE == 2) begin bbuf <= fbuf; fbuf <= !fbuf; end
                pl_blk <= 16'd0; pl_word <= 8'd0; fl_blk <= 16'd0; fl_cnt <= 8'd0; filled_upto <= 16'd0;
                iss_blk <= 16'd0; iss_c <= 8'd0;
            end
            // q set
            if (q_go) begin
                if (q_cnt == 0) begin
                    q_bank <= nb_q;
                    held[nb_q] <= 1'b1;
                    next_bank <= (next_bank == NBANK - 1) ? {BW{1'b0}} : next_bank + 1'b1;
                end
                q_cnt <= q_cnt + 1'b1;
            end
            if (kv_go) wptr <= wptr + ((kv_m == {NL{1'b1}}) ? NL : count_ones(kv_m));
            if (qk_go) begin
                qk_row <= qk_row + NL;
                bcnt[q_bank] <= GUARD_Q + 1 + XD;
                if (qk_row + NL >= T) begin
                    phase_pv <= 1'b1;
                    held[q_bank] <= 1'b0;
                end
            end
            if (sc_cr && !qk_go) sc_cred <= sc_cred + 1'b1;
            else if (!sc_cr && qk_go) sc_cred <= sc_cred - 1'b1;
            // p words
            if (p_go) begin
                if (pl_word == 0) begin
                    pl_bank <= nb_p;
                    blk_bank[pl_blk % BD] <= nb_p;
                    held[nb_p] <= 1'b1;
                    next_bank <= (next_bank == NBANK - 1) ? {BW{1'b0}} : next_bank + 1'b1;
                end
                if (p_last_word) begin
                    pl_blk <= pl_blk + 1'b1;
                    pl_word <= 8'd0;
                end else begin
                    pl_word <= pl_word + PWORDS;
                end
            end
            // fills
            if (fl_go) begin
                if (fl_cnt + 1 == FILLC) begin
                    fl_cnt <= 8'd0;
                    fl_blk <= fl_blk + 1'b1;
                end else begin
                    fl_cnt <= fl_cnt + 1'b1;
                end
            end
            if (fill_wr && (fill_cnt_d + 1 == FILLC)) filled_upto <= fill_blk_d + 1'b1;
            // p.v issue (ILV: its operands are read one cycle later, so the bank's guard is one cycle longer)
            if (pv_go) begin
                bcnt[iss_bank] <= ((ILV != 0) ? GUARD_Q + 1 : GUARD_Q) + XD;
                if (iss_c + 1 == DPT) begin
                    iss_c <= 8'd0;
                    iss_blk <= iss_blk + 1'b1;
                    held[iss_bank] <= 1'b0;
                    if (iss_final) begin
                        if (ILV == 0) act <= 1'b0;
                        else act_b <= 1'b0;
                    end
                end else begin
                    iss_c <= iss_c + 1'b1;
                end
            end
            if (pv_cr && !(pv_go && iss_final)) pv_cred <= pv_cred + 1'b1;
            else if (!pv_cr && pv_go && iss_final) pv_cred <= pv_cred - 1'b1;
        end
    end

    // ILV: the p.v beat enters the E register one cycle after its decision
    reg              pv_go_d;
    reg [BW-1:0]     iss_bank_d;
    reg              iss_final_d;
    reg [BKW-1:0]    iss_blk_d;
    reg [7:0]        iss_c_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv_go_d <= 1'b0;
        else pv_go_d <= (ILV != 0) && pv_go;
    end
    always @(posedge clk) begin
        iss_bank_d <= iss_bank; iss_final_d <= iss_final; iss_blk_d <= iss_blk; iss_c_d <= iss_c;
    end
    // REPL = 2: a second stage
    reg              pv_go_dd;
    reg [BW-1:0]     iss_bank_dd;
    reg              iss_final_dd;
    reg [BKW-1:0]    iss_blk_dd;
    reg [7:0]        iss_c_dd;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv_go_dd <= 1'b0;
        else pv_go_dd <= (XD != 0) && pv_go_d;
    end
    always @(posedge clk) begin
        iss_bank_dd <= iss_bank_d; iss_final_dd <= iss_final_d; iss_blk_dd <= iss_blk_d; iss_c_dd <= iss_c_d;
    end
    wire             pv_e = (XD != 0) ? pv_go_dd : (ILV != 0) ? pv_go_d : pv_go;
    wire [BW-1:0]    e_iss_bank = (XD != 0) ? iss_bank_dd : (ILV != 0) ? iss_bank_d : iss_bank;
    wire             e_iss_final = (XD != 0) ? iss_final_dd : (ILV != 0) ? iss_final_d : iss_final;
    wire [BKW-1:0]   e_iss_blk = (XD != 0) ? iss_blk_dd : (ILV != 0) ? iss_blk_d : iss_blk;
    wire [7:0]       e_iss_c = (XD != 0) ? iss_c_dd : (ILV != 0) ? iss_c_d : iss_c;
    function automatic [15:0] count_ones(input [NL-1:0] m);
        integer i;
        begin
            count_ones = 16'd0;
            for (i = 0; i < NL; i = i + 1) count_ones = count_ones + m[i];
        end
    endfunction

    // ================= staging buffer =================
    genvar gl, gs, gk, gh;
    // one read per sub-bank per cycle: q.k rows or a fill beat
    wire [AW-1:0] rd_addr = qk_go ? AW'(qk_row / NL) : AW'(fl_blk * FILLC + fl_cnt);
    wire [15:0]   rd_row0 = qk_go ? qk_row : (fl_blk * TD + fl_cnt * NL);
    wire [NL*ROWW-1:0] rd_q;           // NSTAGE = 1: the one read port
    wire [NL*ROWW-1:0] rd_q_qk, rd_q_fl;   // q.k rows / fill rows (NSTAGE = 2: two buffers, read concurrently)
    wire [NL*ROWW-1:0] st_q0, st_q1;       // NSTAGE = 2: the two buffers' read data (TRX: muxed per tile)
    wire               st_fbuf_r, st_bbuf_r;
    reg  [15:0]   rd_r0;
    reg  [AW-1:0] rd_addr_r;          // REPL = 2: the staging read one cycle after the decision
    reg           rd_qk2;
    reg  [BW-1:0] rd_bank2;
    reg  [15:0]   rd_r0_2, rq_r0_2;
    reg  [NL-1:0] fpad_d1;
    integer pi2;
    reg  [BW-1:0] rd_bank;
    // row index of the q.k read and of the fill read (NSTAGE = 1: the shared read's)
    wire [15:0]   row_qk_c = (NSTAGE == 2) ? qk_row : rd_row0;
    wire [15:0]   row_fl_c = (NSTAGE == 2) ? (fl_blk * TD + fl_cnt * NL) : rd_row0;
    reg  [15:0]   rq_r0, rf_r0;
    wire [15:0]   r0_qk = (NSTAGE == 2) ? rq_r0 : rd_r0;
    wire [15:0]   r0_fl = (NSTAGE == 2) ? rf_r0 : rd_r0;
    generate if (NSTAGE == 2) begin : g_stage2
        reg fbuf_r, bbuf_r;
        wire [NL*ROWW-1:0] q0, q1;
        wire [AW-1:0] qa_c = AW'(qk_row / NL), fa_c = AW'(fl_blk * FILLC + fl_cnt);
        reg  [AW-1:0] qa_r, fa_r;
        reg           s0f_r, s1f_r, fbuf_rr, bbuf_rr;
        always @(posedge clk) begin
            qa_r <= qa_c; fa_r <= fa_c; s0f_r <= act_b && !bbuf; s1f_r <= act_b && bbuf;
            fbuf_rr <= fbuf_r; bbuf_rr <= bbuf_r;
        end
        wire [AW-1:0] qa = (XD != 0) ? qa_r : qa_c, fa = (XD != 0) ? fa_r : fa_c;
        wire s0f = (XD != 0) ? s0f_r : (act_b && !bbuf), s1f = (XD != 0) ? s1f_r : (act_b && bbuf);
        ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(SRAM_MACRO)) u_stage0 (
            .clk(clk), .wr_en({NL{kv_go && !fbuf}} & kv_m), .wr_addr(AW'(wptr / NL)), .wr_data(kv_w),
            .rd_addr(s0f ? fa : qa), .rd_data(q0));
        ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(SRAM_MACRO)) u_stage1 (
            .clk(clk), .wr_en({NL{kv_go && fbuf}} & kv_m), .wr_addr(AW'(wptr / NL)), .wr_data(kv_w),
            .rd_addr(s1f ? fa : qa), .rd_data(q1));
        always @(posedge clk) begin fbuf_r <= fbuf; bbuf_r <= bbuf; end
        assign rd_q_qk = ((XD != 0) ? fbuf_rr : fbuf_r) ? q1 : q0;
        assign rd_q_fl = ((XD != 0) ? bbuf_rr : bbuf_r) ? q1 : q0;
        assign st_q0 = q0; assign st_q1 = q1; assign st_fbuf_r = fbuf_r; assign st_bbuf_r = bbuf_r;
        assign rd_q = rd_q_qk;
    end else begin : g_stage1
        ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(TROWS), .SRAM_MACRO(SRAM_MACRO)) u_stage (
            .clk(clk), .wr_en({NL{kv_go}} & kv_m), .wr_addr(AW'(wptr / NL)), .wr_data(kv_w),
            .rd_addr((XD != 0) ? rd_addr_r : rd_addr), .rd_data(rd_q));
        assign rd_q_qk = rd_q;
        assign rd_q_fl = rd_q;
        assign st_q0 = rd_q; assign st_q1 = rd_q; assign st_fbuf_r = 1'b0; assign st_bbuf_r = 1'b0;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rd_qk <= 1'b0; rd_fill <= 1'b0; end
        else begin rd_qk <= qk_go; rd_fill <= fl_go && ((NSTAGE == 2) || !qk_go); end
    end
    always @(posedge clk) begin
        rd_r0 <= rd_row0; fill_blk_d <= fl_blk; fill_cnt_d <= fl_cnt; rd_bank <= q_bank;
        rq_r0 <= qk_row; rf_r0 <= fl_blk * TD + fl_cnt * NL;
        rd_addr_r <= rd_addr;
        rd_bank2 <= rd_bank; rd_r0_2 <= rd_r0; rq_r0_2 <= rq_r0;
        for (pi2 = 0; pi2 < NL; pi2 = pi2 + 1) fpad_d1[pi2] <= (row_fl_c + pi2) >= T_p;
    end
    // REPL = 2: the q.k read data and its tags arrive one cycle later (declarations above)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rd_qk2 <= 1'b0;
        else rd_qk2 <= (XD != 0) && rd_qk;
    end
    wire          rd_qk_s = (XD != 0) ? rd_qk2 : rd_qk;
    wire [BW-1:0] rd_bank_s = (XD != 0) ? rd_bank2 : rd_bank;
    wire [15:0]   r0_qk_s = (XD != 0) ? ((NSTAGE == 2) ? rq_r0_2 : rd_r0_2) : r0_qk;

    // element of dim x (0..31) of a group word, {pad, fmt, code, scale}
    function automatic [17:0] elem(input [GW-1:0] gw, input integer x, input pad);
        begin
            if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};
            else         elem = {pad, 1'b0, gw[8*x +: 8], gw[263:256]};
        end
    endfunction

    // ================= tile inputs (E1 register) =================
    reg              e_ld_v, e_ld_mode, e_ld_w2v;
    reg [BW-1:0]     e_ld_bank;
    reg [7:0]        e_ld_grp;
    reg [PWORDS*TD*16-1:0] e_p_w;
    reg [D*16-1:0]   e_q_w;
    reg              e_iv, e_pv;
    reg [BW-1:0]     e_ibank;
    reg [NT*TD*18-1:0] e_ib_c;         // REPL = 0: one E register for the issue operands
    wire [NT*TD*18-1:0] e_ib;          // REPL = 1: per-tile registers (g_tr[*].g_rx.e_ib_t)
    // tags carried to the outputs
    reg [15:0]       e_row0;
    reg [NL-1:0]     e_mask;
    reg              e_fin;
    reg [MLEV-1:0]   e_blk;
    reg [7:0]        e_c;

    // transposers (ot_hdc_v41x_attn_tr): per tile 2 halves x TD rows x DPT dims of 18-bit elements.
    // REPL = 1: every tile registers its own copy of the p.v read index (block half, dim), of the q.k/p.v
    // select, of the fill write index/enable and of the pad flags, from the controller's values on the same
    // edge as the shared _d copies (so no cycle moves), and holds its own E operand register.
    wire [NT*TD*18-1:0] tr_col;
    reg  [NL-1:0] qpad_r;              // REPL: (rd_r0 + r) >= T, registered with rd_r0
    reg  [NL-1:0] qpad_r2;
    always @(posedge clk) qpad_r2 <= qpad_r;
    wire [NL-1:0] qpad_s = (XD != 0) ? qpad_r2 : qpad_r;
    integer pi;
    always @(posedge clk) begin
        for (pi = 0; pi < NL; pi = pi + 1) begin
            qpad_r[pi] <= (row_qk_c + pi) >= T;
        end
    end
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_tr
            wire [NL*GW-1:0] w_g;
            wire [NL-1:0]    w_pad;
            wire [TD*18-1:0] eib_t;
            for (gl = 0; gl < NL; gl = gl + 1) begin : g_g
                assign w_g[gl*GW +: GW] = rd_q_fl[gl*ROWW + ((gk*DPT) / 32) * GW +: GW];
                assign w_pad[gl] = (XD != 0) ? fpad_d1[gl] : (REPL != 0) ? ((row_fl_c + gl) >= T_p) : ((r0_fl + gl) >= T_p);
            end
            if (PHYS == 0 && TRX != 0 && REPL != 0) begin : g_x
                // NSTAGE = 2: this tile's own copies of the front / back staging-buffer selects (the shared
                // fbuf_rr / bbuf_rr fanned out to every tile's fill and q.k operands)
                wire [NL*GW-1:0] w_gx;
                wire [TD*18-1:0] qk_x;
                if (NSTAGE == 2) begin : g_bs
                    wire bs, fs;
                    ot_hdc_v41x_kreg #(.W(2), .R(0)) u_sel (.clk(clk), .rst_n(rst_n),
                        .d((XD != 0) ? {st_bbuf_r, st_fbuf_r} : {bbuf, fbuf}), .q({bs, fs}));
                    wire [NL*ROWW-1:0] qf = bs ? st_q1 : st_q0;
                    wire [NL*ROWW-1:0] qq = fs ? st_q1 : st_q0;
                    for (gl = 0; gl < NL; gl = gl + 1) begin : g_g
                        assign w_gx[gl*GW +: GW] = qf[gl*ROWW + ((gk*DPT) / 32) * GW +: GW];
                    end
                    for (gs = 0; gs < TD; gs = gs + 1) begin : g_e
                        assign qk_x[gs*18 +: 18] = elem(qq[(gk / S)*ROWW + (((gk % S)*TD + gs) / 32) * GW +: GW],
                                                        ((gk % S)*TD + gs) % 32, qpad_s[gk / S]);
                    end
                end else begin : g_bs1
                    assign w_gx = w_g;
                    assign qk_x = qk_ib[gk*TD*18 +: TD*18];
                end
                ot_hdc_v41x_attn_tr_x #(.TD(TD), .DPT(DPT), .NL(NL), .XOFF((gk*DPT) % 32)) u_tr (
                    .clk(clk), .rst_n(rst_n),
                    .w_en_i((XD != 0) ? fill_wr : (fl_go && ((NSTAGE == 2) || !qk_go))),
                    .w_half_i((XD != 0) ? fill_blk_d[0] : fl_blk[0]),
                    .w_cnt_i((XD != 0) ? fill_cnt_d : fl_cnt),
                    .w_pad_i(w_pad), .w_g(w_gx),
                    .r_half_i((XD != 0) ? iss_blk_d[0] : iss_blk[0]),
                    .r_c_i((XD != 0) ? iss_c_d : iss_c),
                    .sel_i((XD != 0) ? pv_go_d : pv_go), .qk_ib(qk_x),
                    .col(tr_col[gk*TD*18 +: TD*18]), .eib(eib_t));
            end else if (PHYS == 0) begin : g_real
                ot_hdc_v41x_attn_tr #(.TD(TD), .DPT(DPT), .NL(NL), .XOFF((gk*DPT) % 32), .REPL(REPL)) u_tr (
                    .clk(clk), .rst_n(rst_n),
                    .w_en_i((XD != 0) ? fill_wr : (REPL != 0) ? (fl_go && ((NSTAGE == 2) || !qk_go)) : fill_wr),
                    .w_half_i((XD != 0) ? fill_blk_d[0] : (REPL != 0) ? fl_blk[0] : fill_blk_d[0]),
                    .w_cnt_i((XD != 0) ? fill_cnt_d : (REPL != 0) ? fl_cnt : fill_cnt_d),
                    .w_pad_i(w_pad), .w_g(w_g),
                    .r_half_i((XD != 0) ? iss_blk_d[0] : (REPL != 0) ? iss_blk[0] : e_iss_blk[0]),
                    .r_c_i((XD != 0) ? iss_c_d : (REPL != 0) ? iss_c : e_iss_c),
                    .sel_i((XD != 0) ? pv_go_d : pv_go), .qk_ib(qk_ib[gk*TD*18 +: TD*18]),
                    .col(tr_col[gk*TD*18 +: TD*18]), .eib(eib_t));
            end else begin : g_phs
                ot_hdc_v41x_attn_tr_phs #(.TD(TD), .DPT(DPT), .NL(NL), .XOFF((gk*DPT) % 32), .REPL(REPL)) u_tr (
                    .clk(clk), .rst_n(rst_n),
                    .w_en_i((XD != 0) ? fill_wr : (REPL != 0) ? (fl_go && ((NSTAGE == 2) || !qk_go)) : fill_wr),
                    .w_half_i((XD != 0) ? fill_blk_d[0] : (REPL != 0) ? fl_blk[0] : fill_blk_d[0]),
                    .w_cnt_i((XD != 0) ? fill_cnt_d : (REPL != 0) ? fl_cnt : fill_cnt_d),
                    .w_pad_i(w_pad), .w_g(w_g),
                    .r_half_i((XD != 0) ? iss_blk_d[0] : (REPL != 0) ? iss_blk[0] : e_iss_blk[0]),
                    .r_c_i((XD != 0) ? iss_c_d : (REPL != 0) ? iss_c : e_iss_c),
                    .sel_i((XD != 0) ? pv_go_d : pv_go), .qk_ib(qk_ib[gk*TD*18 +: TD*18]),
                    .col(tr_col[gk*TD*18 +: TD*18]), .eib(eib_t));
            end
            assign e_ib[gk*TD*18 +: TD*18] = (REPL != 0) ? eib_t : e_ib_c[gk*TD*18 +: TD*18];
        end
    endgenerate

    // q.k beat elements from the buffer read
    wire [NT*TD*18-1:0] qk_ib;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_qkl
            for (gs = 0; gs < S; gs = gs + 1) begin : g_qks
                for (gk = 0; gk < TD; gk = gk + 1) begin : g_qke
                    assign qk_ib[((gl*S + gs)*TD + gk)*18 +: 18] =
                        elem(rd_q_qk[gl*ROWW + ((gs*TD + gk) / 32) * GW +: GW], (gs*TD + gk) % 32,
                             (REPL != 0) ? qpad_s[gl] : ((r0_qk + gl) >= T));
                end
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin e_ld_v <= 1'b0; e_iv <= 1'b0; e_pv <= 1'b0; end
        else begin
            e_ld_v <= q_go || p_go;
            e_iv <= rd_qk_s || pv_e;
            e_pv <= pv_e;
        end
    end
    integer li;
    always @(posedge clk) begin
        e_ld_mode <= p_go;
        e_ld_w2v <= p_go && p_w2v;
        e_ld_bank <= p_go ? ((pl_word == 0) ? nb_p : pl_bank) : ((q_cnt == 0) ? nb_q : q_bank);
        e_ld_grp <= p_go ? pl_word : q_cnt;
        e_p_w <= p_w_i;
        e_q_w <= q_w;
        e_ibank <= pv_e ? e_iss_bank : rd_bank_s;
        e_ib_c <= pv_e ? tr_col : qk_ib;
        e_row0 <= r0_qk_s;
        for (li = 0; li < NL; li = li + 1) e_mask[li] <= (r0_qk_s + li) < T;
        e_fin <= e_iss_final;
        e_blk <= e_iss_blk[MLEV-1:0];
        e_c <= e_iss_c;
    end

`ifdef OT_ATTN_SETCHECK
    // ================= stationary-set checker (simulation only) =================
    // Every q set and p block gets a set id when its bank is allocated; every load carries its id and every beat
    // the id it means to read.  A shadow of tile 0's stationary operand replays the tile's timing (a load in the
    // E register at cycle n is visible from n + 2; a beat in the E register at cycle n reads chunk position k at
    // n + 2 + skew(k % 8), the old value on a same-edge write) and compares the id every non-pad read sees with
    // the beat's: a mismatch is a write-after-read or read-before-write violation of the bank guards.
    integer sck_ctr = 0, sck_qset = 0, sck_plset = 0, sck_reads = 0, sck_errors = 0, sck_ld = 0;
    integer sck_blkset [0:BD-1];
    integer sck_rdset, sck_rdset2, sck_issset, sck_issset_d, sck_issset_dd, e_ld_set, e_iset;
    integer sck_sh [0:NBANK*H*TD-1];
    integer sck_wset [0:63];
    reg [BW+10:0] sck_w [0:63];            // {valid, w2v, mode, grp[7:0], bank}
    integer sck_iset [0:63];
    reg [BW:0] sck_ib [0:63];              // {valid, bank}
    reg [TD-1:0] sck_ipad [0:63];
    integer sck_n = 0, sck_i, sck_h, sck_k, sck_d, sck_c, sck_g;
    initial begin
        for (sck_i = 0; sck_i < NBANK*H*TD; sck_i = sck_i + 1) sck_sh[sck_i] = -1;
        for (sck_i = 0; sck_i < 64; sck_i = sck_i + 1) begin sck_w[sck_i] = 0; sck_ib[sck_i] = 0; end
    end
    always @(posedge clk) begin
        // ids of the sets allocated / read this cycle (the controller's pre-edge values)
        sck_issset = (pl_blk == iss_blk) ? ((pl_word == 0) ? sck_ctr + 1 : sck_plset) : sck_blkset[iss_blk % BD];
        e_ld_set <= p_go ? ((pl_word == 0) ? sck_ctr + 1 : sck_plset) : ((q_cnt == 0) ? sck_ctr + 1 : sck_qset);
        sck_rdset <= sck_qset;
        sck_rdset2 <= sck_rdset;
        sck_issset_d <= sck_issset;
        sck_issset_dd <= sck_issset_d;
        e_iset <= pv_e ? ((XD != 0) ? sck_issset_dd : (ILV != 0) ? sck_issset_d : sck_issset)
                       : ((XD != 0) ? sck_rdset2 : sck_rdset);
        if (rst_n && q_go && q_cnt == 0) begin sck_ctr = sck_ctr + 1; sck_qset = sck_ctr; end
        if (rst_n && p_go && pl_word == 0) begin sck_ctr = sck_ctr + 1; sck_plset = sck_ctr; sck_blkset[pl_blk % BD] = sck_ctr; end
        // the E register of this cycle (sck_n)
        sck_w[(sck_n + 2) % 64] = {e_ld_v, e_ld_w2v, e_ld_mode, e_ld_grp, e_ld_bank};
        sck_wset[(sck_n + 2) % 64] = e_ld_set;
        sck_ib[sck_n % 64] = {e_iv, e_ibank};
        sck_iset[sck_n % 64] = e_iset;
        for (sck_k = 0; sck_k < TD; sck_k = sck_k + 1) sck_ipad[sck_n % 64][sck_k] = e_ib[sck_k*18 + 17];
        // writes visible from this cycle
        if (sck_w[sck_n % 64][BW+10]) begin
            sck_ld = sck_ld + 1;
            for (sck_h = 0; sck_h < H; sck_h = sck_h + 1)
                for (sck_k = 0; sck_k < TD; sck_k = sck_k + 1) begin
                    sck_g = sck_w[sck_n % 64][BW +: 8];
                    if (sck_w[sck_n % 64][BW+8] ? ((sck_k / R) == sck_g || (sck_w[sck_n % 64][BW+9] && (sck_k / R) == sck_g + 1))
                                                : (sck_h == sck_g))
                        sck_sh[(sck_w[sck_n % 64][BW-1:0] * H + sck_h) * TD + sck_k] = sck_wset[sck_n % 64];
                end
            sck_w[sck_n % 64] = 0;
        end
        // reads of this cycle: the beat in E at sck_n - 2 - skew
        for (sck_k = 0; sck_k < TD; sck_k = sck_k + 1) begin
            sck_d = ((sck_k % 8) == 0) ? 0 : skew(sck_k % 8);
            sck_c = sck_n - 2 - sck_d;
            if (sck_c >= 0 && sck_ib[sck_c % 64][BW] && !sck_ipad[sck_c % 64][sck_k])
                for (sck_h = 0; sck_h < H; sck_h = sck_h + 1) begin
                    sck_reads = sck_reads + 1;
                    if (sck_sh[(sck_ib[sck_c % 64][BW-1:0] * H + sck_h) * TD + sck_k] != sck_iset[sck_c % 64]) begin
                        sck_errors = sck_errors + 1;
                        if (sck_errors <= 8)
                            $display("SETCHK cycle %0d bank %0d head %0d pos %0d saw set %0d, beat of cycle %0d wants %0d",
                                     sck_n, sck_ib[sck_c % 64][BW-1:0], sck_h, sck_k,
                                     sck_sh[(sck_ib[sck_c % 64][BW-1:0] * H + sck_h) * TD + sck_k], sck_c, sck_iset[sck_c % 64]);
                    end
                end
        end
        // retire the beat whose last position has been read
        sck_c = sck_n - 2 - 18;
        if (sck_c >= 0) sck_ib[sck_c % 64] = 0;
        sck_n = sck_n + 1;
    end
`endif

    // ================= tiles =================
    wire [NT-1:0]      t_ov;
    wire [NT*H*32-1:0] t_y;
    wire [NT*H-1:0]    t_f;
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_t
            localparam integer SL = gk % S;
            wire [PWORDS*TD*16-1:0] ldw = e_ld_mode ? e_p_w : (PWORDS*TD*16)'(e_q_w[SL*TD*16 +: TD*16]);
            if (TILE_S != 0) begin : g_ts
                ot_hdc_v41x_attn_tile_s #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FML), .F12(F12)) u_t (
                    .clk(clk), .rst_n(rst_n), .ld_v(e_ld_v), .ld_mode(e_ld_mode), .ld_bank(e_ld_bank),
                    .ld_grp(e_ld_grp), .ld_w(ldw), .ld_w2v(e_ld_w2v), .iv(e_iv), .ibank(e_ibank), .ib(e_ib[gk*TD*18 +: TD*18]),
                    .ov(t_ov[gk]), .oy(t_y[gk*H*32 +: H*32]), .oflt(t_f[gk*H +: H]));
            end else begin : g_tl
                ot_hdc_v41x_attn_tile_l #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(FML)) u_t (
                    .clk(clk), .rst_n(rst_n), .ld_v(e_ld_v), .ld_mode(e_ld_mode), .ld_bank(e_ld_bank),
                    .ld_grp(e_ld_grp), .ld_w(ldw), .ld_w2v(e_ld_w2v), .iv(e_iv), .ibank(e_ibank), .ib(e_ib[gk*TD*18 +: TD*18]),
                    .ov(t_ov[gk]), .oy(t_y[gk*H*32 +: H*32]), .oflt(t_f[gk*H +: H]));
            end
        end
    endgenerate

    // tags to the tile outputs
    wire [15:0] t_row0;
    wire [NL-1:0] t_mask;
    wire t_pv, t_fin;
    wire [MLEV-1:0] t_blk;
    wire [7:0] t_c;
    ot_hdc_v41x_dly #(.W(16 + NL + 2 + MLEV + 8), .D(TLAT)) u_tag (.clk(clk),
        .d({e_row0, e_mask, e_pv, e_fin, e_blk, e_c}), .q({t_row0, t_mask, t_pv, t_fin, t_blk, t_c}));

    // ================= q.k lane trees =================
    wire [NL*H*32-1:0] ln_y;
    wire [NL*H-1:0]    ln_f;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_ln
            for (gh = 0; gh < H; gh = gh + 1) begin : g_lh
                wire [(2*S-1)*32-1:0] tn;
                wire [2*S-2:0] tf;
                for (gs = 0; gs < S; gs = gs + 1) begin : g_leaf
                    assign tn[(S-1+gs)*32 +: 32] = t_y[((gl*S + gs)*H + gh)*32 +: 32];
                    assign tf[S-1+gs] = t_f[(gl*S + gs)*H + gh];
                end
                for (gs = 0; gs < S - 1; gs = gs + 1) begin : g_node
                    wire [31:0] y;
                    wire f;
                    ot_hdc_v41x_qaddf #(.LAT(FX), .F12(F12)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(tn[(2*gs+1)*32 +: 32]),
                                     .b(tn[(2*gs+2)*32 +: 32]), .y(y), .fault(f));
                    wire fdq;
                    ot_hdc_v41x_dly #(.W(1), .D(FX)) u_fd (.clk(clk), .d(tf[2*gs+1] | tf[2*gs+2]), .q(fdq));
                    assign tn[gs*32 +: 32] = y;
                    assign tf[gs] = fdq | f;
                end
                assign ln_y[(gl*H + gh)*32 +: 32] = tn[31:0];
                assign ln_f[gl*H + gh] = tf[0];
            end
        end
    endgenerate
    wire ln_v, ln_pv;
    wire [15:0] ln_row0;
    wire [NL-1:0] ln_mask;
    ot_hdc_v41x_vdly #(.D(FX * LS + 1)) u_lnv (.clk(clk), .rst_n(rst_n), .d(t_ov[0] && !t_pv), .q(ln_v));
    ot_hdc_v41x_dly #(.W(16 + NL), .D(FX * LS + 1)) u_lnt (.clk(clk), .d({t_row0, t_mask}), .q({ln_row0, ln_mask}));
    // (the +1 above aligns with the register below; ln_y is FPL*LS after t_y)
    reg [NL*H*32-1:0] ln_yr;
    reg [NL*H-1:0]    ln_fr;
    always @(posedge clk) begin ln_yr <= ln_y; ln_fr <= ln_f; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sc_v <= 1'b0;
        else sc_v <= ln_v;
    end
    always @(posedge clk) begin
        sc_row <= ln_row0; sc_m <= ln_mask; sc_y <= ln_yr; sc_f <= ln_fr;
    end

    // ================= p.v merges =================
    wire [NT-1:0]      m_ov;
    wire [NT*H*32-1:0] m_y;
    wire [NT*H-1:0]    m_f;
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_m
            if (PHYS == 0) begin : g_real
            if (MFAN != 0) begin : g_x
            ot_hdc_v41x_attn_merge_x #(.H(H), .DPT(DPT), .MLEV(MLEV), .FPL(FX), .F12(F12)) u_m (
                .clk(clk), .rst_n(rst_n), .iv(t_ov[gk] && t_pv), .ifin(t_fin), .iblk(t_blk),
                .iy(t_y[gk*H*32 +: H*32]), .if_(t_f[gk*H +: H]), .ov(m_ov[gk]), .oy(m_y[gk*H*32 +: H*32]),
                .of_(m_f[gk*H +: H]));
            end else begin : g_s
            ot_hdc_v41x_attn_merge_s #(.H(H), .DPT(DPT), .MLEV(MLEV), .FPL(FX)) u_m (
                .clk(clk), .rst_n(rst_n), .iv(t_ov[gk] && t_pv), .ifin(t_fin), .iblk(t_blk),
                .iy(t_y[gk*H*32 +: H*32]), .if_(t_f[gk*H +: H]), .ov(m_ov[gk]), .oy(m_y[gk*H*32 +: H*32]),
                .of_(m_f[gk*H +: H]));
            end
            end else begin : g_phs
            ot_hdc_v41x_attn_merge_phs #(.H(H), .DPT(DPT), .MLEV(MLEV)) u_m (
                .clk(clk), .rst_n(rst_n), .iv(t_ov[gk] && t_pv), .ifin(t_fin), .iblk(t_blk),
                .iy(t_y[gk*H*32 +: H*32]), .if_(t_f[gk*H +: H]), .ov(m_ov[gk]), .oy(m_y[gk*H*32 +: H*32]),
                .of_(m_f[gk*H +: H]));
            end
        end
    endgenerate
    wire [7:0] m_c;
    ot_hdc_v41x_dly #(.W(8), .D(FX * MLEV + ((MFAN != 0) ? 1 : 0))) u_mc (.clk(clk), .d(t_c), .q(m_c));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pv_v <= 1'b0;
        else pv_v <= m_ov[0];
    end
    always @(posedge clk) begin
        pv_c <= m_c; pv_y <= m_y; pv_f <= m_f;
    end
endmodule

// (ot_hdc_v41x_kreg, the kept-hierarchy register: rtl/hdc/v41x/ot_hdc_v41x_kreg.sv, which a build lists)

// ---------------------------------------------------------------------------
// Per-tile TRANSPOSER for REPL >= 1 with the read and write selects decoded and duplicated (engine TRX = 1):
// ot_hdc_v41x_attn_tr (rtl/hdc/v41x/ot_hdc_v41x_attn.sv) at REPL != 0, same storage, same cycles.  There the
// registered read index (rb_t, rc_t) steered a 2*DPT:1 mux on all TD x 18 element bits (~9,000 loads; routed SS
// -431 ps in the controller vehicle).  Here every element has its own registered one-hot read select and its own
// q.k/p.v select (kept hierarchy copies, decoded from the controller's values one cycle earlier, exactly where
// tr registers rb_t / rc_t / sel_t), and every stored row its own registered write enable.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_tr_x #(
    parameter integer TD = 64,
    parameter integer DPT = 16,
    parameter integer NL = 4,
    parameter integer XOFF = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              w_en_i,
    input  wire              w_half_i,
    input  wire [7:0]        w_cnt_i,
    input  wire [NL-1:0]     w_pad_i,
    input  wire [NL*265-1:0] w_g,
    input  wire              r_half_i,
    input  wire [7:0]        r_c_i,
    input  wire              sel_i,
    input  wire [TD*18-1:0]  qk_ib,
    output wire [TD*18-1:0]  col,
    output wire [TD*18-1:0]  eib
);
    localparam integer GW = 265;
    localparam integer NS = 2 * DPT;          // read positions (half, dim)
    localparam integer NR = 2 * TD;           // stored rows (half, row)
    function automatic [17:0] elem(input [GW-1:0] gw, input integer x, input pad);
        begin
            if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};
            else         elem = {pad, 1'b0, gw[8*x +: 8], gw[263:256]};
        end
    endfunction
    // one-hot read position and write row, from the controller's values (registered below, as tr's rb_t/rc_t/fc_t)
    wire [NS-1:0] rsel_c;
    wire [NR-1:0] wrow_c;
    genvar gs, gr, gx;
    generate
        for (gs = 0; gs < NS; gs = gs + 1) begin : g_rs
            assign rsel_c[gs] = (r_half_i == (gs / DPT)) && (r_c_i == (gs % DPT));
        end
        for (gr = 0; gr < NR; gr = gr + 1) begin : g_ws
            assign wrow_c[gr] = w_en_i && (w_half_i == (gr / TD)) && (w_cnt_i == ((gr % TD) / NL));
        end
    endgenerate
    reg [NL-1:0] fp_t;
    always @(posedge clk) fp_t <= w_pad_i;
    reg [17:0] tr [0:NR*DPT-1];
    generate
        // writes: row gr (half gr/TD, row gr%TD) takes lane r = gr % NL of the fill word
        for (gr = 0; gr < NR; gr = gr + 1) begin : g_w
            wire we;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_we (.clk(clk), .rst_n(rst_n), .d(wrow_c[gr]), .q(we));
            for (gx = 0; gx < DPT; gx = gx + 1) begin : g_x
                always @(posedge clk)
                    if (we) tr[gr * DPT + gx] <= elem(w_g[(gr % NL)*GW +: GW], XOFF + gx, fp_t[gr % NL]);
            end
        end
        // reads: element gs selects position (half, dim) with its own one-hot copy
        for (gs = 0; gs < TD; gs = gs + 1) begin : g_c
            wire [NS-1:0] oh;
            wire          sel;
            ot_hdc_v41x_kreg #(.W(NS), .R(0)) u_rs (.clk(clk), .rst_n(rst_n), .d(rsel_c), .q(oh));
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_sl (.clk(clk), .rst_n(rst_n), .d(sel_i), .q(sel));
            reg [17:0] v;
            integer k;
            always @* begin
                v = 18'd0;
                for (k = 0; k < NS; k = k + 1)
                    v = v | ({18{oh[k]}} & tr[((k / DPT) * TD + gs) * DPT + (k % DPT)]);
            end
            assign col[gs*18 +: 18] = v;
            reg [17:0] e;
            always @(posedge clk) e <= sel ? v : qk_ib[gs*18 +: 18];
            assign eib[gs*18 +: 18] = e;
        end
    endgenerate
endmodule

`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-IDXRD (10-18): dsdv_idx_rg, the REGIONAL INDEX READER / SCORER of the S81-DV p4l die (release blocker MU.BAL.SX.3:
// bind9 had no index reader).  16 instances, one per regional HBM controller dsfd_ctrl_rg2 (2 pseudo-channels each),
// sid = chain position = region.  The DeepSeek-V4.1 lightning indexer runs where the keys are: every region scores the
// keys held in ITS two pseudo-channels with the UNCHANGED exact engine ot_hdc_v41x_idx_engine (NK 1: 32 heads x 128
// FP4 dims a key, the chunk8 golden arithmetic), and the 16 regions' scores meet on one neighbour-only SCORE CHAIN that
// leaves as selector-native BK beats (dsdv_bk_v format) for the die's selector dsdv_bk_sel (top-k, ties to the lower
// index).  Keys never cross the die; only scores do (16 b a key).
//
// KEY LAYOUT (compiler; the key writer svc_att host writes follows it).  Position p, word j = p >> 4, lane i = p & 15:
//   region r(p) = i ^ h(j),  h(j) = (j ^ j >> 4 ^ j >> 8 ^ j >> 12) & 15
// so every 16-position word has EXACTLY ONE key in every region (a full scan feeds all 16 regions evenly), and a
// gather (re-index) spreads clustered and strided candidate sets over the regions.  Region r stores the key of word j at
// local cell c = j & 15 of local group g = j >> 4, on PC g & 1, PC-local block n = g >> 1, sector base A = KB + 34 n:
//   codes  sectors A + 2 c, A + 2 c + 1        (key bits [255:0], [511:256]; 128 E2M1 codes)
//   scales sector  A + 32 + (c >> 3), bytes 4 (c & 7) .. +3   (key bits [543:512]; 4 x UE8M0)
// 34 sectors = 16 x 68 B, no padding.  KB = the user's index-key base (PC-local sector address, the same on every PC
// of the die): per-user bases are job-word content (MU-S81), not RTL state.
//
// JOB (one frame on the query chain qi; frame header as the SVC FRAME PROTOCOL v1: [511:508] type, [502:495] tag,
// [491:480] len, [458:449] user, spec [448:0]):
//   type 4 IDX_S  full scan of positions [B, B + N)                    len 64
//   type 8 IDX_G  gather (re-index) of NB candidate BLOCKS              len 64 + ceil(NB / 16)
//   spec [19:0] B (scan; 0 for a gather), [40:20] N (scan count, or NB), [50:41] k (<= 512), [80:51] KB,
//        [96:81] T0, [100:97] P (>= 2), [103:101] ik (= the selector's ingress-kind strap)
//        [106:104] om: OPEN lanes 1..3 (S81-L20DIE 10-19, bit i-1 = lane i): the reader emits neither the HDR nor the
//        empty BEAT of an open lane -- that lane belongs to a child die's candidate set (dsdv_idx_tx on the child, landed
//        by dsdv_idx_vmux here), which opens it with its own HDR.  om = 0 (default) = the record behaviour.
//   payload 0..63: query, word 2h = head h's 128 FP4 codes, word 2h + 1 = {[47:32] BF16 head weight, [31:0] scales}
//   payload 64..: (IDX_G) candidate block list, 16 entries a word ([32 e +: 17] = block b = positions 8 b .. 8 b + 7,
//                 the re-index candidate unit: dsrom_reindex_candidates 2,048 blocks = 16,384 keys), strictly
//                 ascending blocks; entry e of list word v = block ordinal o = 16 v + e, candidate ordinal c = 8 o + t
//                 for position 8 b + t.  A gather is scored in ORDINAL space: the selector sees c as its index (the
//                 list is ascending, so "ties to the lower index" is the same rule on ordinals as on positions); the
//                 ordinal -> position map stays with the list's owner.  A block lies in ONE 16-position word (lanes
//                 0..7 or 8..15), so every region owns at most ONE key of a block (t = (r ^ h(j))[2:0] when
//                 (r ^ h(j))[3] == b[0], j = b >> 1): the list needs no per-region filtering storage.  The list is
//                 kept in a list memory (LFD words; SRAM_MACRO: 2 x ot_sram_1r1w_256x256, 4,096 blocks a job).
// Frames of other types are skipped (len words).  Every frame is forwarded unchanged on qo (2 edges a hop).
//
// STATIC SCHEDULE (owner rule: no credit / ready / arbitration on the on-die production path).  Frame END (the last
// payload word) reaches every region's qi pin flop exactly 2 edges after its upstream neighbour's, and the score chain
// si -> so is 2 edges a hop as well, so ONE local clock (cycles since END) puts every region's insertions in the same
// passing beat.  From END + T0 every region drives the same compiled beat sequence (OR on the chain, identical bits):
//   +0 HDR q0 single (lane 0: [19:0] 16 j0, [29:20] k, [31:30] 0)      j0 = B >> 4, j1 = (B + N - 1) >> 4
//   +1 HDR q1, +2/+3 empty BEAT q1 (lv 0, last), +4 HDR q2, +5/+6 empty q2, +7 HDR q3, +8/+9 empty q3
//   +10 + P w  (w = 0 .. j1 - j0): BEAT word w on lane 0, part 0 (16 BF16 scores) then part 1 (lane valid, last on the
//   final word, the in-band fault flag); the region owning lane i of word w ORs its score / valid bit in.
// P = 2 is the 276-b rung's maximum (two V beats a word: 8 scores a cycle); the reader alone sustains P >= 1.41 (the
// stack's measured 11.35 keys a cycle).  A score not ready at its slot is a sticky fault (late) and sets the word's
// in-band fault flag: the selector fails closed.
// LANDING: 2 x ot_sram_1r1w_256x256 a PC (code sector 0 / 1 halves), read together: 1 key a cycle into the engine.
// HBM BOUNDARY (elastic, owner 10-15): reads go through the region's controller; landing is slot-addressed
// (LG slots x 16 key cells a PC, no overflow possible), keys wait in landing / the engine until their slot.
//
// HBM FACES: the tile is the registered station of the region's rq (682 b) / rd (562 b) link between the service slice
// dsdv_svc_rs and dsfd_ctrl_rg2.  The slice's requests pass with priority (+1 register each way); this reader issues
// only in cycles the slice does not, while the controller's outstanding count (every request, either owner, until its
// rk) is below DQ.  Responses tagged [16:15] = 3 are this reader's and are not passed on; rk pulses are returned to their
// owner in request order (per-PC owner FIFO), so the slice's credit counter sees exactly its own.  Static rule (compiler):
// the slice's and the reader's HBM windows do not overlap on a PC (a violation overflows the controller: its fault).
//
// Pins: every input lands in a flop at the pin, every output leaves a flop.  One clock ck.  Reset rst: async assert,
// 2-flop synchronous release.
// MUT (bench negative controls only): 1 lane hash off by one, 2 rk always returned to the slice, 3 scale sector of the
// neighbouring cell, 4 region 0's part-1 beat one cycle late, 5 response of the slice swallowed, 6 spec om ignored.
// S81-L20 idxrd2 (10-19, SAFE checklist 5/6): every memory is a 1R1W 1024 x 256 macro (ot_sram_1r1w_1024x256_m2_r2c2:
// 70.47 um faces, 415 contacts = 5.89 / um <= 6; the 256x256 family is 10.0 / um).  7 macros: landing 4 (code rows
// 0..127, the PC's scale rows 128..143 in its half-0 macro: 8 scales a row), list 2, item queue 1 (show-ahead head
// buffer).  The scale register file (2 x 128 x 32 b) and the item queue flops (256 x 29 b) are gone.  The consumer
// reads a scale ROW once (row cache, write-through on scale writes), then pops up to 8 keys of the row at 1 a cycle.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_idx_rg #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQ = 8,           // controller request buffer entries a PC (dsfd_ctrl_rg2 DQ)
    parameter integer LG = 8,           // landing slots a PC (16 key cells each)
    parameter integer IQD = 256,        // key items in flight (item queue) = the HBM request lead: >= (HBM latency ~240 + engine ~51 + jitter) x 0.5 key/cycle
    parameter integer SQD = 64,         // keys in the engine (<= ~51 at 1 key/cycle) + scores waiting for the assembler
    parameter integer LFD = 256,        // candidate-list words held (gather; 256 with SRAM_MACRO = 2 macros)
    parameter integer RQD = 16          // read jobs queued a PC (scan: a 16-key group; gather: one key)
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,            // query chain {d 512, v}
    output reg  [512:0]  qo,
    input  wire [275:0]  si,            // score chain (BK V beats)
    output reg  [275:0]  so,
    input  wire [681:0]  rqi,           // from dsdv_svc_rs
    output reg  [681:0]  rqo,           // to dsfd_ctrl_rg2
    input  wire [561:0]  rdi,           // from dsfd_ctrl_rg2
    output reg  [561:0]  rdo,           // to dsdv_svc_rs
    output reg  [9:0]    st             // {fault cause 8, busy, fault}
);
    localparam integer SLW = 3;            // slot field of the read tag (LG = 8)
    initial if (LG != 8) $fatal(1, "dsdv_idx_rg: LG must be 8 (3-bit tag slot field)");
    initial if (LFD > 1024 || IQD > 1024) $fatal(1, "dsdv_idx_rg: list / item queue memories are 1024 words");
    localparam integer IQW = $clog2(IQD), SQW = $clog2(SQD), LFW = $clog2(LFD), RQW = $clog2(RQD);

    // ------------------------------------------------------------------ reset
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [3:0] me;
    always @(posedge ck or negedge rn) if (!rn) me <= 4'd0; else me <= sid;

    // ------------------------------------------------------------------ pin registers / chains
    reg [512:0] qr;
    reg [275:0] sr;
    reg [681:0] rqr;
    reg [561:0] rdr;
    always @(posedge ck or negedge rn)
        if (!rn) begin qr[0] <= 1'b0; qo[0] <= 1'b0; sr[0] <= 1'b0; rqr[0] <= 1'b0; rqr[341] <= 1'b0;
                       rdr[277] <= 1'b0; rdr[278] <= 1'b0; rdr[279] <= 1'b0; rdr[557] <= 1'b0; rdr[558] <= 1'b0; rdr[559] <= 1'b0; end
        else begin qr[0] <= qi[0]; qo[0] <= qr[0]; sr[0] <= si[0]; rqr[0] <= rqi[0]; rqr[341] <= rqi[341];
                   rdr[277] <= rdi[277]; rdr[278] <= rdi[278]; rdr[279] <= rdi[279];
                   rdr[557] <= rdi[557]; rdr[558] <= rdi[558]; rdr[559] <= rdi[559]; end
    always @(posedge ck) begin
        qr[512:1] <= qi[512:1]; qo[512:1] <= qr[512:1]; sr[275:1] <= si[275:1];
        rqr[340:1] <= rqi[340:1]; rqr[681:342] <= rqi[681:342];
        rdr[276:0] <= rdi[276:0]; rdr[556:280] <= rdi[556:280]; rdr[561:560] <= rdi[561:560];
    end

    function automatic [3:0] hj(input [15:0] j);
        hj = j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12];
    endfunction
    // decoded (one-hot AND-OR) selects: no runtime-indexed part-select for synthesis
    function automatic [31:0] sel8x32(input [255:0] d, input [2:0] i);
        integer k_; sel8x32 = 32'd0;
        for (k_ = 0; k_ < 8; k_ = k_ + 1) if (i == 3'(k_)) sel8x32 = sel8x32 | d[32 * k_ +: 32];
    endfunction
    function automatic [16:0] sel16x17(input [511:0] d, input [3:0] i);
        integer k_; sel16x17 = 17'd0;
        for (k_ = 0; k_ < 16; k_ = k_ + 1) if (i == 4'(k_)) sel16x17 = sel16x17 | d[32 * k_ +: 17];
    endfunction

    // ------------------------------------------------------------------ forward declarations
    reg         wdone_p, wdone;
    reg  [7:0]  fc_set;
    // ------------------------------------------------------------------ job registers
    reg        act, infr, isj;               // job active / in a frame / the frame is an index job
    reg [11:0] left, pw;
    reg [3:0]  ftyp;
    reg        gat;                          // gather job
    reg [19:0] jb;                           // B
    reg [20:0] jn;                           // N / NC
    reg [9:0]  jk;
    reg [29:0] kb;
    reg [15:0] t0;
    reg [3:0]  pp;
    reg [2:0]  ik;
    reg [2:0]  om;                           // open lanes 1..3 (spec [106:104])
    reg [7:0]  tg;
    reg [15:0] j0, j1, nw;                   // first / last absolute word, word count
    reg [15:0] nlw;                          // gather: list words
    reg [7:0]  fc;                           // sticky fault causes
    wire       fault = |fc;
    wire       q_v = qr[0];
    wire [511:0] q_d = qr[512:1];
    wire       is_h = q_v && !infr;
    wire       is_p = q_v && infr;
    wire       hdr_job = is_h && (q_d[511:508] == 4'd4 || q_d[511:508] == 4'd8);
    wire [20:0] h_n = q_d[40:20];
    wire [20:0] h_end = 21'(q_d[19:0]) + h_n - 21'd1;
    wire       pay_job = is_p && isj;
    wire       end_w = pay_job && left == 12'd1;
    // query load
    reg [511:0] qhold;
    reg         ql_v;
    reg [7:0]   ql_h;
    reg [511:0] ql_c;
    reg [31:0]  ql_s;
    reg [15:0]  ql_w;
    reg [2:0]   qset;
    reg         q_done;
    // candidate block list (gather): written as it arrives, read by the walker's prefetcher
    wire        lf_push = pay_job && pw >= 12'd64;
    reg  [LFW:0] lf_wn;                      // list words written
    reg  [LFW:0] lf_rn;                      // list words read (requested)
    reg          lfr_e;
    reg  [LFW-1:0] lfr_a;
    wire [511:0] lf_q;
    // window clock
    reg         ended;
    reg [19:0]  tc;

    always @(posedge ck or negedge rn)
        if (!rn) begin
            act <= 1'b0; infr <= 1'b0; isj <= 1'b0; left <= 0; pw <= 0; ftyp <= 0; gat <= 0; jb <= 0; jn <= 0; jk <= 0;
            kb <= 0; t0 <= 0; pp <= 0; ik <= 0; om <= 0; tg <= 0; j0 <= 0; j1 <= 0; nw <= 0; nlw <= 0; ql_v <= 1'b0; ql_h <= 0;
            qset <= 0; q_done <= 1'b0; ended <= 1'b0; tc <= 0;
        end else begin
            ql_v <= 1'b0;
            if (is_h) begin
                ftyp <= q_d[511:508]; left <= q_d[491:480]; pw <= 0; infr <= q_d[491:480] != 12'd0;
                isj <= hdr_job;
                if (hdr_job && !act) begin
                    act <= 1'b1; gat <= q_d[511]; jb <= q_d[19:0]; jn <= h_n; jk <= q_d[50:41]; kb <= q_d[80:51];
                    t0 <= q_d[96:81]; pp <= q_d[100:97]; ik <= q_d[103:101]; om <= q_d[106:104]; tg <= q_d[502:495];
                    // gather: NB blocks = 8 NB ordinals = ceil(NB / 2) selector words, ceil(NB / 16) list words
                    if (q_d[511]) begin j0 <= 16'd0; j1 <= 16'(((h_n + 21'd1) >> 1) - 21'd1); nw <= 16'((h_n + 21'd1) >> 1);
                                        nlw <= 16'((h_n + 21'd15) >> 4); end
                    else begin j0 <= q_d[19:4]; j1 <= h_end[19:4]; nw <= 16'(h_end[19:4] - q_d[19:4] + 16'd1); nlw <= 16'd0; end
                    q_done <= 1'b0; ended <= 1'b0; tc <= 0;
                end
            end else if (is_p) begin
                left <= left - 12'd1; pw <= pw + 12'd1;
                if (left == 12'd1) infr <= 1'b0;
                if (pay_job && pw < 12'd64) begin
                    if (!pw[0]) qhold <= q_d;
                    else begin ql_v <= 1'b1; ql_h <= 8'(pw[6:1]); ql_c <= qhold; ql_s <= q_d[31:0]; ql_w <= q_d[47:32]; end
                end
            end
            if (ql_v && ql_h == 8'd31) qset <= 3'd5;
            else if (qset != 0) begin qset <= qset - 3'd1; if (qset == 3'd1) q_done <= 1'b1; end
            if (end_w && act) begin ended <= 1'b1; tc <= 0; end
            else if (ended && !wdone) tc <= tc + 20'd1;
            if (wdone_p) act <= 1'b0;
        end

    // ------------------------------------------------------------------ HBM faces: owner FIFOs, credits, rd filter
    // rq word (dsfd_ctrl_rg2): {wdata 256, wstrb 32, tag 17, len 4, addr 30, we, v}; rd word: {wd, rk, rv, beat 4,
    // tag 17, data 256}
    reg  [1:0]  i_v;                         // this reader's request this cycle (per PC)
    reg  [29:0] i_a [0:1];
    reg  [3:0]  i_l [0:1];
    reg  [16:0] i_t [0:1];
    reg  [15:0] own [0:1];                   // owner FIFO (1 = this reader), shift register
    reg  [4:0]  own_n [0:1];
    wire [1:0]  av_ = {rqr[341], rqr[0]};
    wire [1:0]  can = {(own_n[1] < 5'(DQ)) && !av_[1], (own_n[0] < 5'(DQ)) && !av_[0]};
    wire [1:0]  rk_in = {rdr[280 + 278], rdr[278]};
    wire [1:0]  rv_in = {rdr[280 + 277], rdr[277]};
    wire [16:0] rt [0:1];
    assign rt[0] = rdr[272:256];
    assign rt[1] = rdr[280 + 256 +: 17];
    wire [1:0]  mine_rv;
    assign mine_rv[0] = rv_in[0] && rt[0][16:15] == 2'b11;
    assign mine_rv[1] = rv_in[1] && rt[1][16:15] == 2'b11;
    wire [1:0]  iss = i_v & can;             // a request leaves this cycle
    integer p;
    always @(posedge ck or negedge rn)
        if (!rn) begin
            rqo[0] <= 1'b0; rqo[341] <= 1'b0; rdo[277] <= 1'b0; rdo[278] <= 1'b0; rdo[279] <= 1'b0;
            rdo[557] <= 1'b0; rdo[558] <= 1'b0; rdo[559] <= 1'b0;
            own[0] <= 0; own[1] <= 0; own_n[0] <= 0; own_n[1] <= 0;
        end else begin
            for (p = 0; p < 2; p = p + 1) begin : g_pc
                reg push, pop, ob;
                push = av_[p] || iss[p];
                pop = rk_in[p];
                ob = own[p][0];
                rqo[341 * p] <= push;
                // rk back to its owner, in request order
                if (MUT == 2) rdo[280 * p + 278] <= rk_in[p];
                else rdo[280 * p + 278] <= rk_in[p] && (own_n[p] != 0) && !ob;
                rdo[280 * p + 279] <= rdr[280 * p + 279];
                if (MUT == 5) rdo[280 * p + 277] <= rv_in[p] && !mine_rv[p] && !rt[p][0];
                else rdo[280 * p + 277] <= rv_in[p] && !mine_rv[p];
                if (pop && !push) begin own[p] <= own[p] >> 1; own_n[p] <= own_n[p] - 5'd1; end
                else if (push && !pop) begin own[p][own_n[p][3:0]] <= iss[p]; own_n[p] <= own_n[p] + 5'd1; end
                else if (push && pop) begin
                    own[p] <= (own[p] >> 1) | (16'(iss[p]) << (own_n[p][3:0] - 4'd1));
                end
            end
        end
    always @(posedge ck) begin
        for (p = 0; p < 2; p = p + 1) begin
            if (av_[p]) rqo[341 * p + 1 +: 340] <= rqr[341 * p + 1 +: 340];
            else rqo[341 * p + 1 +: 340] <= {256'd0, 32'd0, i_t[p], i_l[p], i_a[p], 1'b0};
            rdo[280 * p +: 277] <= rdr[280 * p +: 277];
        end
        rdo[561:560] <= rdr[561:560];
    end

    // ------------------------------------------------------------------ landing (per PC: LG slots x 16 cells)
    // code SRAM: entry {slot, cell, sector}; scale registers; arrival bits; slot state
    reg [1:0]   cdv [0:1][0:LG*16-1];        // code sectors landed
    reg         scv [0:1][0:LG*16-1];        // scale landed
    reg         sb  [0:1][0:LG-1];           // slot busy
    reg         scl_d [0:1][0:LG-1];         // slot closed (no more items)
    reg [4:0]   sni [0:1][0:LG-1];           // items allocated
    reg [4:0]   snc [0:1][0:LG-1];           // items consumed
    reg [5:0]   sne [0:1][0:LG-1];           // beats expected
    reg [5:0]   snr [0:1][0:LG-1];           // beats received
    reg [SLW-1:0] sa [0:1];                  // next slot to allocate
    reg [SLW-1:0] so_ [0:1];                 // open gather slot
    reg         sopen [0:1];
    // response decode -> landing writes
    // TWO landing memories a PC (index 2 pc + half): half 0 holds code sector 0 ([255:0]) of every cell, half 1 sector 1,
    // so the consumer reads a whole key in ONE cycle (1 key a cycle = 2x the P = 2 slot rate: the scorer runs ahead of
    // the window and recovers HBM refresh / latency bubbles instead of losing them for good).
    reg  [3:0]  lw_v;
    reg  [SLW+3:0] lw_a [0:3];
    reg  [255:0] lw_d [0:3];
    wire [255:0] lr_d [0:3];
    reg  [3:0]  lr_e;
    reg  [SLW+3:0] lr_a [0:3];
    // scale writes (registered one edge after the response, like the code writes): PC q -> its half-0 macro, row 128 + r
    reg  [1:0]   sw_v;
    reg  [3:0]   sw_r [0:1];                 // {slot, cell[3]}
    reg  [255:0] sw_d [0:1];
    reg  [255:0] sw_m [0:1];
    // scale row reads (consumer): one PC's half-0 macro, never in the same edge as that macro's code read
    reg          sr_e; reg sr_pc; reg [3:0] sr_r;
    genvar gp;
    generate for (gp = 0; gp < 4; gp = gp + 1) begin : g_land
        localparam bit H0 = (gp % 2) == 0;
        localparam integer QP = gp / 2;
        wire         s_rd = H0 && sr_e && sr_pc == QP[0];
        wire         s_wr = H0 && sw_v[QP];
        dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mem (
            .ck(ck), .re(lr_e[gp] || s_rd), .ra(s_rd ? {6'b001000, sr_r} : 10'(lr_a[gp])), .rd(lr_d[gp]),
            .we(lw_v[gp] || s_wr), .wa(s_wr ? {6'b001000, sw_r[QP]} : 10'(lw_a[gp])),
            .wd(s_wr ? sw_d[QP] : lw_d[gp]), .wm(s_wr ? sw_m[QP] : {256{1'b1}}));
    end endgenerate

    // ------------------------------------------------------------------ list memory (gather): 1 write + 1 read a cycle
    genvar hh;
    generate for (hh = 0; hh < 2; hh = hh + 1) begin : g_lm
        dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_mem (
            .ck(ck), .re(lfr_e), .ra(10'(lfr_a)), .rd(lf_q[256 * hh +: 256]),
            .we(lf_push), .wa(10'(lf_wn[LFW-1:0])), .wd(q_d[256 * hh +: 256]), .wm({256{1'b1}}));
    end endgenerate

    // ------------------------------------------------------------------ walker (items + requests)
    // item {pc, slot, cell, w (word - j0), lane, lw}
    localparam integer IW = 1 + SLW + 4 + 16 + 4 + 1;
    reg [IQW:0]  iq_n;                       // items queued (memory + read in flight + head buffer)
    reg [IQW-1:0] iq_w, iq_r;                // memory write / read pointers
    reg [IQW:0]  im_n;                       // items in the memory not yet read
    wire [255:0] iq_q;
    reg          ir_f;                       // memory read issued last edge: iq_q holds it now
    reg [IW-1:0] hq [0:2];                   // show-ahead head buffer (3 entries: 1 read a cycle sustained)
    reg [1:0]    hq_n;
    wire         ir_e = (im_n != 0) && ({1'b0, hq_n} + {2'b0, ir_f} <= 3'd2);   // arrival never overflows the 3 entries
    reg          ipush;
    reg [IW-1:0] ipd;
    wire         ipop;
    // walker state
    reg [2:0]   ws;                          // 0 idle, 1 scan group, 2 scan items, 3 gather list word, 6 gather key, 5 done
    reg [15:0]  wg;                          // scan: local group (16 words)
    reg [15:0]  wvm;                         // scan: valid cells of the group
    reg [4:0]   wc;                          // scan: next item cell
    reg         wpc;
    reg [SLW-1:0] wsl;
    reg [15:0]  gw;                          // gather: list word index
    reg [15:0]  gm;                          // gather: remaining owned entries of the head word
    reg [511:0] lh;                          // gather: head list word
    reg         ln_v;                        // gather: prefetched next list word
    reg [511:0] ln_d;
    reg         lfd1, lfd2;                  // list read in flight (memory read, then data)
    // per-PC READ JOB queues: the walker queues {gather, slot, landing cell, block base, key cell}; each PC's issuer sends
    // the job's requests (scan group: scales + 8 code reads; gather key: code + scale read) as fast as the controller
    // takes them, both PCs at once (the walker never waits on a request)
    localparam integer JW = 1 + SLW + 4 + 30 + 4;
    reg [JW-1:0] rjq [0:1][0:RQD-1];
    reg [RQW:0]  rj_n [0:1];
    reg [RQW-1:0] rj_w [0:1], rj_r [0:1];
    reg [3:0]    rj_k [0:1];                 // next request of the head job
    // scan helpers
    wire        s_pc = wg[0];
    wire [14:0] s_n = wg[15:1];
    reg  [15:0] s_vm;
    integer c;
    always @* begin
        for (c = 0; c < 16; c = c + 1) begin : g_vm
            reg [15:0] jj; reg [20:0] pos;
            jj = {wg[11:0], 4'(c)};
            pos = {1'b0, jj, (MUT == 1) ? (me ^ hj(jj) ^ 4'd1) : (me ^ hj(jj))};
            s_vm[c] = (jj >= j0) && (jj <= j1) && (pos >= 21'(jb)) && (pos < 21'(jb) + jn);
        end
    end
    // gather helpers: entries of the prefetched list word this region owns a key of (block b: word j = b >> 1,
    // the region's lane x = me ^ h(j) lies in the block when x[3] == b[0]; t = x[2:0])
    reg  [15:0]  n_om;
    always @* begin
        for (c = 0; c < 16; c = c + 1) begin : g_om
            reg [16:0] bb; reg [3:0] x;
            bb = ln_d[32 * c +: 17];
            x = me ^ hj(16'(bb >> 1));
            n_om[c] = (21'({gw, 4'(c)}) < jn) && (x[3] == bb[0]);
        end
    end
    reg [3:0] g_lo;
    always @* begin
        g_lo = 4'd0;
        for (c = 15; c >= 0; c = c - 1) if (gm[c]) g_lo = 4'(c);
    end
    wire [16:0] g_b = sel16x17(lh, g_lo);
    wire [15:0] g_j = 16'(g_b >> 1);                 // the position's word
    wire [3:0]  g_x = me ^ hj(g_j);
    wire [3:0]  g_ln = {g_lo[0], g_x[2:0]};          // selector lane: ordinal 8 o + t, o = 16 gw + g_lo
    wire [15:0] g_w = {gw[12:0], g_lo[3:1]};         // selector word: ordinal >> 4
    wire        g_lw = g_lo[0] || !gm[g_lo | 4'd1];  // this region's last key of the selector word
    // slot free condition
    wire [1:0] sfree;
    assign sfree[0] = !sb[0][sa[0]];
    assign sfree[1] = !sb[1][sa[1]];
    // consumer release (declared below)
    reg  [1:0]  rel_v, rel0, rel1;
    reg  [SLW-1:0] rel_s [0:1], rs0 [0:1], rs1 [0:1];
    // response beats
    wire [3:0]  rb [0:1];
    assign rb[0] = rdr[276:273];
    assign rb[1] = rdr[280 + 273 +: 4];
    wire [255:0] rdd [0:1];
    assign rdd[0] = rdr[255:0];
    assign rdd[1] = rdr[280 +: 256];

    integer q, e;
    always @(posedge ck or negedge rn)
        if (!rn) begin
            ws <= 3'd0; wg <= 0; wvm <= 0; wc <= 0; wpc <= 0; wsl <= 0; gw <= 0; gm <= 0; fc <= 8'd0;
            ln_v <= 1'b0; lfd1 <= 1'b0; lfd2 <= 1'b0; lfr_e <= 1'b0;
            for (q = 0; q < 2; q = q + 1) begin rj_n[q] <= 0; rj_w[q] <= 0; rj_r[q] <= 0; rj_k[q] <= 0; end
            lf_rn <= 0;
            i_v <= 2'b00; ipush <= 1'b0;
            for (q = 0; q < 2; q = q + 1) begin
                sa[q] <= 0; so_[q] <= 0; sopen[q] <= 1'b0;
                for (e = 0; e < LG; e = e + 1) begin sb[q][e] <= 1'b0; scl_d[q][e] <= 1'b0; sni[q][e] <= 0; snc[q][e] <= 0;
                                                     sne[q][e] <= 0; snr[q][e] <= 0; end
                for (e = 0; e < LG * 16; e = e + 1) begin cdv[q][e] <= 2'b00; scv[q][e] <= 1'b0; end
            end
            lw_v <= 4'b0000; iq_n <= 0; iq_w <= 0; lf_wn <= 0; sw_v <= 2'b00;
        end else begin : g_walk
            reg [7:0] fw;
            reg [1:0] rjpu, rjpo;                // read job queued / retired this cycle, per PC
            fw = 8'd0; rjpu = 2'b00; rjpo = 2'b00;
            ipush <= 1'b0;
            // ---------------- per-PC issuers: the head read job's next request whenever the request register is free
            for (q = 0; q < 2; q = q + 1) begin : g_iss
                reg jg; reg [SLW-1:0] js; reg [3:0] jc, jk; reg [29:0] jb_;
                {jg, js, jc, jb_, jk} = rjq[q][rj_r[q]];
                if (iss[q]) i_v[q] <= 1'b0;
                if (rj_n[q] != 0 && (!i_v[q] || iss[q])) begin
                    i_v[q] <= 1'b1;
                    if (!jg) begin                                        // scan group: scales, then 8 x 4 code sectors
                        if (rj_k[q] == 4'd0) begin i_a[q] <= jb_ + 30'd32; i_l[q] <= 4'd2;
                                                   i_t[q] <= {2'b11, 1'b0, 3'(js), 4'd0, 1'b1, 3'd0, 3'd0}; end
                        else begin i_a[q] <= jb_ + 30'(4 * (rj_k[q] - 4'd1)); i_l[q] <= 4'd4;
                                   i_t[q] <= {2'b11, 1'b0, 3'(js), 4'(2 * (rj_k[q] - 4'd1)), 1'b0, 3'd0, 3'd0}; end
                    end else begin                                        // gather key: 2 code sectors, then its scale
                        if (rj_k[q] == 4'd0) begin i_a[q] <= jb_ + 30'(2 * jk); i_l[q] <= 4'd2;
                                                   i_t[q] <= {2'b11, 1'b1, 3'(js), jc, 1'b0, 3'd0, 3'd0}; end
                        else begin i_a[q] <= jb_ + 30'd32 + 30'(jk[3]); i_l[q] <= 4'd1;
                                   i_t[q] <= {2'b11, 1'b1, 3'(js), jc, 1'b1, jk[2:0], 3'd0}; end
                    end
                    if (rj_k[q] == (jg ? 4'd1 : 4'd8)) begin rj_k[q] <= 4'd0; rj_r[q] <= rj_r[q] + 1'b1; rjpo[q] = 1'b1; end
                    else rj_k[q] <= rj_k[q] + 4'd1;
                end
            end
            // ---------------- walker
            if (hdr_job && !act) begin
                if (q_d[511]) begin ws <= 3'd3; gw <= 0; gm <= 0; end
                else begin ws <= 3'd1; wg <= {4'd0, q_d[19:8]}; end
            end else case (ws)
                3'd1: begin                                      // scan: next group = one landing slot + one read job
                    if (wg > {4'd0, j1[15:4]}) ws <= 3'd5;
                    else if (s_vm == 16'd0) wg <= wg + 16'd1;
                    else if (sfree[s_pc] && iq_n <= (IQW+1)'(IQD - 16) && rj_n[s_pc] < (RQW+1)'(RQD - 1)) begin
                        wpc <= s_pc; wsl <= sa[s_pc]; wvm <= s_vm; wc <= 0;
                        sb[s_pc][sa[s_pc]] <= 1'b1; scl_d[s_pc][sa[s_pc]] <= 1'b1;
                        sni[s_pc][sa[s_pc]] <= 5'(s_vm[0] + s_vm[1] + s_vm[2] + s_vm[3] + s_vm[4] + s_vm[5] + s_vm[6] + s_vm[7] +
                                                 s_vm[8] + s_vm[9] + s_vm[10] + s_vm[11] + s_vm[12] + s_vm[13] + s_vm[14] + s_vm[15]);
                        snc[s_pc][sa[s_pc]] <= 0; sne[s_pc][sa[s_pc]] <= 6'd34; snr[s_pc][sa[s_pc]] <= 0;
                        for (e = 0; e < 16; e = e + 1) begin cdv[s_pc][{sa[s_pc], 4'(e)}] <= 2'b00; scv[s_pc][{sa[s_pc], 4'(e)}] <= 1'b0; end
                        sa[s_pc] <= sa[s_pc] + 1'b1;
                        rjq[s_pc][rj_w[s_pc]] <= {1'b0, 3'(sa[s_pc]), 4'd0, kb + 30'(s_n) * 30'd34, 4'd0};
                        rj_w[s_pc] <= rj_w[s_pc] + 1'b1; rjpu[s_pc] = 1'b1;
                        ws <= 3'd2;
                    end
                end
                3'd2: begin                                      // scan: the group's items, one a cycle
                    if (wvm[wc[3:0]]) begin
                        ipush <= 1'b1;
                        ipd <= {wpc, wsl, wc[3:0], 16'({wg[11:0], wc[3:0]} - j0),
                                (MUT == 1) ? (me ^ hj({wg[11:0], wc[3:0]}) ^ 4'd1) : (me ^ hj({wg[11:0], wc[3:0]})), 1'b1};
                    end
                    wc <= wc + 5'd1;
                    if (wc == 5'd15) begin wg <= wg + 16'd1; ws <= 3'd1; end
                end
                3'd3: begin                                      // gather: take the next list word
                    if (gw >= nlw) begin
                        for (q = 0; q < 2; q = q + 1) if (sopen[q]) begin scl_d[q][so_[q]] <= 1'b1; sopen[q] <= 1'b0; end
                        ws <= 3'd5;
                    end else if (ln_v) begin lh <= ln_d; gm <= n_om; ws <= 3'd6; end
                end
                3'd6: begin                                      // gather: one owned key a cycle = landing cell + read job + item
                    if (gm == 16'd0) begin gw <= gw + 16'd1; ws <= 3'd3; end
                    else if (((!sopen[g_j[4]] || sni[g_j[4]][so_[g_j[4]]] == 5'd16) ? sfree[g_j[4]] : 1'b1) &&
                             iq_n < (IQW+1)'(IQD - 1) && rj_n[g_j[4]] < (RQW+1)'(RQD - 1)) begin : g_take
                        reg [SLW-1:0] s_; reg [3:0] cl;
                        if (!sopen[g_j[4]] || sni[g_j[4]][so_[g_j[4]]] == 5'd16) begin
                            if (sopen[g_j[4]]) scl_d[g_j[4]][so_[g_j[4]]] <= 1'b1;
                            s_ = sa[g_j[4]]; cl = 4'd0;
                            sb[g_j[4]][s_] <= 1'b1; scl_d[g_j[4]][s_] <= 1'b0; sni[g_j[4]][s_] <= 5'd1;
                            snc[g_j[4]][s_] <= 0; sne[g_j[4]][s_] <= 6'd3; snr[g_j[4]][s_] <= 0;
                            so_[g_j[4]] <= s_; sopen[g_j[4]] <= 1'b1; sa[g_j[4]] <= sa[g_j[4]] + 1'b1;
                        end else begin
                            s_ = so_[g_j[4]]; cl = 4'(sni[g_j[4]][s_]);
                            sni[g_j[4]][s_] <= sni[g_j[4]][s_] + 5'd1; sne[g_j[4]][s_] <= sne[g_j[4]][s_] + 6'd3;
                        end
                        cdv[g_j[4]][{s_, cl}] <= 2'b00; scv[g_j[4]][{s_, cl}] <= 1'b0;
                        rjq[g_j[4]][rj_w[g_j[4]]] <= {1'b1, s_, cl, kb + 30'(g_j[15:5]) * 30'd34, g_j[3:0]};
                        rj_w[g_j[4]] <= rj_w[g_j[4]] + 1'b1; rjpu[g_j[4]] = 1'b1;
                        ipush <= 1'b1;
                        ipd <= {g_j[4], s_, cl, g_w, g_ln, g_lw};
                        gm <= gm & ~(16'd1 << g_lo);
                    end
                end
                default: ;
            endcase
            if (wdone_p) ws <= 3'd0;
            for (q = 0; q < 2; q = q + 1) rj_n[q] <= rj_n[q] + (rjpu[q] ? 1'b1 : 1'b0) - (rjpo[q] ? 1'b1 : 1'b0);
            // ---------------- list memory: writes as the list arrives; one prefetched word ahead of the walker
            if (lf_push) begin
                lf_wn <= lf_wn + 1'b1;
                if (lf_wn == (LFW+1)'(LFD)) fw[0] = 1'b1;              // list longer than the list memory
            end
            if (hdr_job && !act) begin lf_wn <= 0; lf_rn <= 0; ln_v <= 1'b0; end
            lfr_e <= 1'b0; lfd1 <= lfr_e; lfd2 <= lfd1;
            if (gat && act && !ln_v && !lfr_e && !lfd1 && !lfd2 && lf_rn < lf_wn && 16'(lf_rn) < nlw) begin
                lfr_e <= 1'b1; lfr_a <= lf_rn[LFW-1:0]; lf_rn <= lf_rn + 1'b1;
            end
            if (lfd2) begin ln_v <= 1'b1; ln_d <= lf_q; end
            if (ws == 3'd3 && gw < nlw && ln_v && !lfd2) ln_v <= 1'b0;
            // ---------------- item queue
            if (ipush) iq_w <= iq_w + 1'b1;
            iq_n <= iq_n + (ipush ? 1'b1 : 1'b0) - (ipop ? 1'b1 : 1'b0);
            // ---------------- responses -> landing
            lw_v <= 4'b0000; sw_v <= 2'b00;
            // the registered scale write lands (macro edge); the cells' scale-valid bits follow it, so a consumer row
            // read issued after scv is seen always returns the new scale
            for (q = 0; q < 2; q = q + 1) if (sw_v[q])
                for (e = 0; e < 8; e = e + 1) if (sw_m[q][32 * e]) scv[q][{sw_r[q], 3'(e)}] <= 1'b1;
            for (q = 0; q < 2; q = q + 1) if (mine_rv[q]) begin : g_rsp
                reg g; reg [SLW-1:0] s_; reg [3:0] cl; reg sc; reg [2:0] by; reg [3:0] bt;
                g = rt[q][14]; s_ = rt[q][11 +: SLW]; cl = rt[q][10:7]; sc = rt[q][6]; by = rt[q][5:3]; bt = rb[q];
                if (!sb[q][s_] || snr[q][s_] >= sne[q][s_]) fw[1] = 1'b1;   // a response to no read
                snr[q][s_] <= snr[q][s_] + 6'd1;
                if (!sc) begin
                    reg [3:0] cc;
                    cc = g ? cl : cl + {3'd0, bt[1]};
                    lw_v[2 * q + bt[0]] <= 1'b1; lw_a[2 * q + bt[0]] <= {s_, cc}; lw_d[2 * q + bt[0]] <= rdd[q];
                    cdv[q][{s_, cc}] <= cdv[q][{s_, cc}] | (bt[0] ? 2'b10 : 2'b01);
                end else if (!g) begin
                    sw_v[q] <= 1'b1; sw_r[q] <= {s_, bt[0]}; sw_m[q] <= {256{1'b1}};
                    for (e = 0; e < 8; e = e + 1)
                        sw_d[q][32 * (3'(e) ^ ((MUT == 3) ? 3'd1 : 3'd0)) +: 32] <= rdd[q][32 * e +: 32];
                end else begin
                    sw_v[q] <= 1'b1; sw_r[q] <= {s_, cl[3]};
                    for (e = 0; e < 8; e = e + 1) begin
                        sw_m[q][32 * e +: 32] <= (3'(e) == cl[2:0]) ? 32'hffff_ffff : 32'd0;
                        sw_d[q][32 * e +: 32] <= sel8x32(rdd[q], by ^ ((MUT == 3) ? 3'd1 : 3'd0));
                    end
                end
            end
            for (q = 0; q < 2; q = q + 1) if (rk_in[q] && own_n[q] == 0) fw[1] = 1'b1;  // rk with no request
            // ---------------- slot release
            for (q = 0; q < 2; q = q + 1) begin
                if (rel_v[q]) snc[q][rel_s[q]] <= snc[q][rel_s[q]] + 5'd1;
                for (e = 0; e < LG; e = e + 1)
                    if (sb[q][e] && scl_d[q][e] && snc[q][e] == sni[q][e] && snr[q][e] == sne[q][e] && !(rel_v[q] && rel_s[q] == SLW'(e)))
                        sb[q][e] <= 1'b0;
            end
            fc <= fc | fc_set | fw;
        end

    // ------------------------------------------------------------------ consumer: landing -> engine (one key a cycle)
    // item queue memory + show-ahead head buffer
    dsdv_idx_m1k #(.SRAM_MACRO(SRAM_MACRO)) u_iq (
        .ck(ck), .re(ir_e), .ra(10'(iq_r)), .rd(iq_q),
        .we(ipush), .wa(10'(iq_w)), .wd({{(256-IW){1'b0}}, ipd}), .wm({256{1'b1}}));
    always @(posedge ck or negedge rn)
        if (!rn) begin iq_r <= 0; im_n <= 0; ir_f <= 1'b0; hq_n <= 2'd0; end
        else begin : g_hq
            reg [1:0] n1;
            ir_f <= ir_e;
            if (ir_e) iq_r <= iq_r + 1'b1;
            im_n <= im_n + (ipush ? 1'b1 : 1'b0) - (ir_e ? 1'b1 : 1'b0);
            n1 = hq_n - (ipop ? 2'd1 : 2'd0);
            if (ipop) begin hq[0] <= hq[1]; hq[1] <= hq[2]; end
            if (ir_f) hq[n1] <= iq_q[IW-1:0];
            hq_n <= n1 + (ir_f ? 2'd1 : 2'd0);
        end
    wire [IW-1:0] ih = hq[0];
    wire          h_pc = ih[IW-1];
    wire [SLW-1:0] h_sl = ih[IW-2 -: SLW];
    wire [3:0]    h_cl = ih[IW-2-SLW -: 4];
    wire [SLW+3:0] h_ci = {h_sl, h_cl};
    wire          h_land = (hq_n != 0) && cdv[h_pc][h_ci] == 2'b11 && scv[h_pc][h_ci];
    // scale row cache: {pc, slot, cell[3]} -> 8 scales; write-through on scale writes, pending-read merge
    reg           sc_v; reg sc_pc; reg [3:0] sc_r; reg [255:0] sc_d;
    reg           sr_p, sr_d1; reg [255:0] pm_d, pm_m;
    wire          sc_hit = sc_v && sc_pc == h_pc && sc_r == {h_sl, h_cl[3]};
    wire          h_ready = h_land && sc_hit;
    wire          sr_go = h_land && !sc_hit && !sr_p && act;
    function automatic [255:0] mrg(input [255:0] o, input [255:0] d, input [255:0] m);
        mrg = (o & ~m) | (d & m);
    endfunction
    reg  [SQW:0]  infl;                      // keys in the engine + scores waiting for the assembler
    wire          room = infl < (SQW+1)'(SQD - 2);
    assign ipop = h_ready && q_done && room && act;
    wire          k_ready;
    reg           k_v;
    reg  [543:0]  k_key;
    // stage 1: both halves of the key's cell read (lr_e), scale + metadata held; stage 2: SRAM data -> engine register
    reg           c_v; reg c_pc; reg [31:0] c_sc; reg [15:0] c_w; reg [3:0] c_ln; reg c_lw;
    reg           f1;  reg f_pc; reg [31:0] f_sc; reg [15:0] f_w; reg [3:0] f_ln; reg f_lw;
    always @(posedge ck or negedge rn)
        if (!rn) begin lr_e <= 4'b0000; rel_v <= 2'b00; rel0 <= 2'b00; rel1 <= 2'b00; c_v <= 1'b0; f1 <= 1'b0;
                       sr_e <= 1'b0; sr_p <= 1'b0; sr_d1 <= 1'b0; sc_v <= 1'b0; end
        else begin : g_cons
            reg [255:0] nd;
            integer qq;
            // scale row read: issue (sr_go) -> macro read edge (sr_e) -> load (sr_d1); scale writes landing at the read
            // edge or later are merged (the macro returns OLD on a same-edge write)
            sr_e <= sr_go; sr_d1 <= sr_e;
            if (sr_go) begin sr_p <= 1'b1; sr_pc <= h_pc; sr_r <= {h_sl, h_cl[3]}; sc_v <= 1'b0; pm_m <= '0; end
            for (qq = 0; qq < 2; qq = qq + 1)
                if (sw_v[qq] && sr_p && sr_pc == qq[0] && sr_r == sw_r[qq] && sr_e) begin
                    pm_d <= mrg(pm_d, sw_d[qq], sw_m[qq]); pm_m <= pm_m | sw_m[qq];
                end
            nd = sc_d;
            for (qq = 0; qq < 2; qq = qq + 1)
                if (sw_v[qq] && sc_v && sc_pc == qq[0] && sc_r == sw_r[qq]) nd = mrg(nd, sw_d[qq], sw_m[qq]);
            if (sr_d1) begin
                nd = mrg(lr_d[2 * sr_pc], pm_d, pm_m);
                for (qq = 0; qq < 2; qq = qq + 1)
                    if (sw_v[qq] && sr_pc == qq[0] && sr_r == sw_r[qq]) nd = mrg(nd, sw_d[qq], sw_m[qq]);
                sc_v <= 1'b1; sc_pc <= sr_pc; sc_r <= sr_r; sr_p <= 1'b0;
            end
            sc_d <= nd;
            lr_e <= 4'b0000; rel0 <= 2'b00; rel1 <= rel0; rel_v <= rel1;
            rs1[0] <= rs0[0]; rs1[1] <= rs0[1]; rel_s[0] <= rs1[0]; rel_s[1] <= rs1[1];
            c_v <= ipop;
            if (ipop) begin
                c_pc <= h_pc; c_w <= ih[20:5]; c_ln <= ih[4:1]; c_lw <= ih[0];
                c_sc <= sc_d[32 * h_cl[2:0] +: 32];
                lr_e[2 * h_pc] <= 1'b1; lr_e[2 * h_pc + 1] <= 1'b1;
                lr_a[2 * h_pc] <= h_ci; lr_a[2 * h_pc + 1] <= h_ci;
                rel0[h_pc] <= 1'b1; rs0[h_pc] <= h_sl;
            end
            f1 <= c_v;
            if (c_v) begin f_pc <= c_pc; f_sc <= c_sc; f_w <= c_w; f_ln <= c_ln; f_lw <= c_lw; end
        end
    // engine input register: the SRAM data is valid the cycle after the read (f1)
    reg [20:0] k_m;
    always @(posedge ck or negedge rn)
        if (!rn) k_v <= 1'b0;
        else begin
            k_v <= f1;
            if (f1) begin k_key <= {f_sc, lr_d[2 * f_pc + 1], lr_d[2 * f_pc]}; k_m <= {f_w, f_ln, f_lw}; end
        end
    wire        o_v;
    wire [0:0]  o_kv, o_f;
    wire [15:0] o_s;
    ot_hdc_v41x_idx_engine #(.NK(1), .IH(32), .NB(4), .FD(56)) u_eng (
        .clk(ck), .rst_n(rn), .ql_v(ql_v), .ql_head(ql_h), .ql_codes(ql_c), .ql_sc(ql_s), .ql_w(ql_w),
        .k_valid(k_v), .k_ready(k_ready), .k_kv(1'b1), .k_keep(1'b1), .k_key(k_key),
        .o_valid(o_v), .o_ready(1'b1), .o_kv(o_kv), .o_score(o_s), .o_fault(o_f),
        .cnt_keys_scored(), .cnt_headsums_fused(), .cnt_faults());
    // metadata beside the engine (in key order)
    reg [20:0] mq [0:SQD-1];
    reg [SQW-1:0] mq_w, mq_r;
    // score FIFO -> word assembler
    reg [37:0] sq [0:SQD-1];                  // {w 16, lane 4, lw, fault, score 16}
    reg [SQW-1:0] sq_w, sq_r;
    reg [SQW:0]   sq_n;
    reg           a_v;                       // assembling word
    reg [15:0]    a_w; reg [15:0] a_lv; reg [255:0] a_s; reg a_f;
    reg           r_v;                       // ready word
    reg [15:0]    r_w; reg [15:0] r_lv; reg [255:0] r_s; reg r_f;
    wire          r_take;
    reg           a_done;
    // a finished word moves to r when r is free or taken this cycle; the NEXT word starts assembling in the same cycle,
    // so a word of 2 scores (gather: up to 2 keys a region a word) still meets the next slot 2 cycles later
    wire          a_mv = a_v && a_done && (!r_v || r_take);
    wire          sq_pop = (sq_n != 0) && !(a_v && a_done && !a_mv);
    always @(posedge ck or negedge rn)
        if (!rn) begin mq_w <= 0; mq_r <= 0; sq_w <= 0; sq_r <= 0; sq_n <= 0; infl <= 0; a_v <= 1'b0; a_done <= 1'b0;
                       r_v <= 1'b0; end
        else begin
            if (k_v) begin mq[mq_w] <= k_m; mq_w <= mq_w + 1'b1; end
            if (o_v) begin
                sq[sq_w] <= {mq[mq_r], o_f[0], o_s}; sq_w <= sq_w + 1'b1; mq_r <= mq_r + 1'b1;
            end
            sq_n <= sq_n + (o_v ? 1'b1 : 1'b0) - (sq_pop ? 1'b1 : 1'b0);
            infl <= infl + (ipop ? 1'b1 : 1'b0) - (sq_pop ? 1'b1 : 1'b0);
            if (sq_pop) begin : g_as
                reg [37:0] t; t = sq[sq_r]; sq_r <= sq_r + 1'b1;
                if (!a_v || a_done) begin
                    a_v <= 1'b1; a_w <= t[37:22]; a_lv <= 16'd1 << t[21:18]; a_s <= 256'(t[15:0]) << (16 * t[21:18]);
                    a_f <= t[16]; a_done <= t[17];
                end else begin
                    a_lv <= a_lv | (16'd1 << t[21:18]); a_s <= a_s | (256'(t[15:0]) << (16 * t[21:18]));
                    a_f <= a_f | t[16]; a_done <= t[17];
                end
            end
            if (a_mv) begin
                r_v <= 1'b1; r_w <= a_w; r_lv <= a_lv; r_s <= a_s; r_f <= a_f;
                if (!sq_pop) a_v <= 1'b0;
            end else if (r_take) r_v <= 1'b0;
        end

    // ------------------------------------------------------------------ emission (the compiled window)
    wire [19:0] th = 20'(t0);
    reg  [15:0] ew;                          // next word
    reg  [19:0] et;                          // its part-0 cycle
    reg         p1;                          // part 1 due
    reg  [15:0] p1_lv; reg p1_f; reg p1_last;
    // header beats (identical in every region)
    function automatic [275:0] bk(input [2:0] kind, input [1:0] lane, input part, input single, input [11:0] tt,
                                  input [255:0] dd);
        bk = {dd, tt, single, part, lane, kind, 1'b1};
    endfunction
    wire [9:0]   e_ix = 10'(tc - th);
    wire         in_h = ended && tc >= th && tc < th + 20'd10;
    reg  [275:0] hb;
    always @* begin
        hb = '0;
        case (e_ix[3:0])
            4'd0: hb = bk(ik, 2'd0, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd0, jk, 20'({j0, 4'd0})});
            4'd1: hb = bk(ik, 2'd1, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd1, jk, 20'({j1 + 16'd1, 4'd0})});
            4'd2: hb = bk(ik, 2'd1, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
            4'd3: hb = bk(ik, 2'd1, 1'b1, 1'b0, 12'd0, {4'd2, tg, 227'd0, 1'b1, 16'd0});
            4'd4: hb = bk(ik, 2'd2, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd2, jk, 20'({j1 + 16'd1, 4'd0})});
            4'd5: hb = bk(ik, 2'd2, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
            4'd6: hb = bk(ik, 2'd2, 1'b1, 1'b0, 12'd0, {4'd2, tg, 227'd0, 1'b1, 16'd0});
            4'd7: hb = bk(ik, 2'd3, 1'b0, 1'b1, {4'd1, tg}, {224'd0, 2'd3, jk, 20'({j1 + 16'd1, 4'd0})});
            4'd8: hb = bk(ik, 2'd3, 1'b0, 1'b0, {4'd2, tg}, 256'd0);
            4'd9: hb = bk(ik, 2'd3, 1'b1, 1'b0, 12'd0, {4'd2, tg, 227'd0, 1'b1, 16'd0});
            default: hb = '0;
        endcase
        // open lanes (spec om): no HDR / empty BEAT of that lane (e_ix 1-3 lane 1, 4-6 lane 2, 7-9 lane 3)
        if (MUT != 6 && ((e_ix[3:0] >= 4'd1 && e_ix[3:0] <= 4'd3 && om[0]) || (e_ix[3:0] >= 4'd4 && e_ix[3:0] <= 4'd6 && om[1]) ||
            (e_ix[3:0] >= 4'd7 && e_ix[3:0] <= 4'd9 && om[2]))) hb = '0;
    end
    wire        slot = ended && !wdone && ew < nw && tc == et;
    wire [15:0] ej = ew + j0;                // absolute word
    wire [20:0] my_pos = {1'b0, ej, me ^ hj(ej)};
    wire        own_w = !gat && (my_pos >= 21'(jb)) && (my_pos < 21'(jb) + jn);   // scan: this word has my key
    assign r_take = slot && r_v && r_w == ew;
    wire        late = slot && ((own_w && !r_take) || (r_v && r_w < ew));
    wire [275:0] ins0 = bk(ik, 2'd0, 1'b0, 1'b0, {4'd2, tg}, r_take ? r_s : 256'd0);
    reg         p1_d;
    wire        p1_due = (MUT == 4 && me == 4'd0) ? p1_d : p1;
    // part 1 carries data[511:256]: {type 2, tag} at [511:500] (bk_vin takes a split word's type / tag from part 1),
    // [272] last, [271:256] lane valid; [8] = the word's in-band fault flag
    wire [275:0] ins1 = bk(ik, 2'd0, 1'b1, 1'b0, {11'd0, p1_f}, {4'd2, tg, 227'd0, p1_last, p1_lv});
    always @(posedge ck or negedge rn)
        if (!rn) begin ew <= 0; et <= 0; p1 <= 1'b0; p1_d <= 1'b0; wdone <= 1'b0; wdone_p <= 1'b0; so[0] <= 1'b0; fc_set <= 0; end
        else begin
            fc_set <= 0; wdone_p <= 1'b0; p1_d <= p1;
            if (hdr_job && !act) begin ew <= 0; et <= 20'(q_d[96:81]) + 20'd10; wdone <= 1'b0; end
            if (slot) begin
                p1 <= 1'b1; p1_lv <= r_take ? r_lv : 16'd0; p1_f <= (r_take && r_f) || late || fault;
                p1_last <= ew == nw - 16'd1;
                ew <= ew + 16'd1; et <= et + 20'(pp);
            end else p1 <= 1'b0;
            if (late) fc_set[2] <= 1'b1;
            if (r_take && r_f) fc_set[3] <= 1'b1;
            if (k_v && !k_ready) fc_set[4] <= 1'b1;
            if (hdr_job && act) fc_set[5] <= 1'b1;                          // a job while one is active
            if (hdr_job && !act && (q_d[100:97] < 4'd2 || h_n == 21'd0 || q_d[50:41] > 10'd512 ||
                (q_d[511] ? q_d[491:480] != 12'(64 + ((h_n + 21'd15) >> 4)) : q_d[491:480] != 12'd64))) fc_set[6] <= 1'b1;
            // window end: every slot passed -> nothing may be left
            if (ended && !wdone && ew == nw && !p1 && !p1_d) begin
                wdone <= 1'b1; wdone_p <= 1'b1;
                if (iq_n != 0 || infl != 0 || a_v || r_v || (ws != 3'd5 && ws != 3'd0)) fc_set[7] <= 1'b1;
            end
            so[0] <= sr[0] | (in_h ? hb[0] : 1'b0) | slot | p1_due;
        end
    always @(posedge ck)
        so[275:1] <= sr[275:1] | (in_h ? hb[275:1] : 275'd0) | (slot ? ins0[275:1] : 275'd0) | (p1_due ? ins1[275:1] : 275'd0);
    always @(posedge ck or negedge rn)
        if (!rn) st <= 10'd0; else st <= {fc, act, fault};
endmodule

// ===================================================================================================================
// dsdv_idx_m1k: 1024 x 256-b 1R1W memory, bit write mask, read latency 1 (address edge -> rd valid after it, held until
// the next read).  SRAM_MACRO 1: ot_sram_1r1w_1024x256_m2_r2c2 (faces 5.89 contacts / um); 0: behavioural, same timing.
// ===================================================================================================================
module dsdv_idx_m1k #(
    parameter bit SRAM_MACRO = 0
) (
    input  wire         ck,
    input  wire         re,
    input  wire [9:0]   ra,
    output wire [255:0] rd,
    input  wire         we,
    input  wire [9:0]   wa,
    input  wire [255:0] wd,
    input  wire [255:0] wm
);
    generate if (SRAM_MACRO) begin : g_m
        ot_sram_1r1w_1024x256_m2_r2c2 u_mem (
            .clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(rd),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm),
            .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end else begin : g_b
        reg [255:0] mem [0:1023];
        reg [255:0] q;
        always @(posedge ck) begin
            if (we) mem[wa] <= (mem[wa] & ~wm) | (wd & wm);
            if (re) q <= mem[ra];
        end
        assign rd = q;
    end endgenerate
endmodule

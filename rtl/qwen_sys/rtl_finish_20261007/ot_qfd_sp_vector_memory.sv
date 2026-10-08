`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sp_vector_memory (qwen-rtl-finish 2026-10-07): a BANKED vector memory with a parallel service of the
// matrix engine's x read, replacing the behavioural many-port array of the token bench
// (rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv `vm`) for the ME x port and the row ports.
//
// The x read.  Every ME issue cycle reads 2^SMAX = 2,048 seats, but seat c reads x_dc + (c mod S) * x_dcs (S = 2^split,
// ot_qwen_me_spctl_w12): S unique scalars on an arithmetic progression of stride d = x_dcs, replicated S-periodically.
// The tree top sends that as a descriptor (ot_qfd_sp_tree_top); this master serves it with
//   storage   NRB row banks, row = 16 elements (512 b), row r in bank r mod NRB at line r / NRB; a bank is two
//             ot_sram_1r1w_256x256 macros (USE_MACRO = 1) or a behavioural model with the same one-edge registered
//             read (USE_MACRO = 0, simulation).  Every macro output is captured in a flop beside the macro.
//   beats     a tuple's span x_dc .. x_dc + (S-1)*d is read as B = floor((S-1)*d / BEAT) + 1 beats of BEAT = (NRB-1)*16
//             consecutive elements: one beat reads NRB consecutive rows, one per bank (conflict-free by construction),
//             rotated into row order and shifted to the element (two registered rotate stages, one shift stage).
//   decimate  entry c of the assembly line takes beat element (c*d) mod BEAT of beat floor(c*d / BEAT): for every
//             stride d of the supported set DSET this is a fixed wire, so an entry is a |DSET|:1 mux plus a write
//             enable (no crossbar).  Strides outside DSET raise x_fault.
//   timing    fixed: a tuple registered by the tree top at engine edge k is on x_q at edge k + 1 + XVM, as the token
//             bench's VM (read at k + 1, XVM extra registers).  Its beats issue at k + XVM - 6 - B + j (j < B) and land
//             6 edges later; the line is copied to x_q (S-periodic replication) at k + XVM + 1 (all in ENGINE edges,
//             me_en: a paused engine pauses the x path exactly; a macro read and its capture take the two real edges
//             after the issuing engine edge, into a three-slot capture ring, so a pause cannot lose a beat).  A tuple equal to the
//             previous one (the IL-slot hold of weight ops: x_dc only moves when the slot or k loop does) is not re-read.
//             Requirement (else x_fault): a NEW tuple with B beats comes >= B engine edges after the previous new tuple
//             (B = 1 for every contiguous tuple of S <= BEAT, i.e. attention QK / PV every cycle; weight ops hold 8).
//             Within an op the issue loop meets it; across ops x_rdy (high once BMAX engine edges passed since the last
//             new tuple) gates the tree top's ready, so an op starts at most BMAX - 2 edges later than in the base
//             (priced as an issue-gap cost, zero when the previous op ended BMAX edges earlier).  XVM >= BMAX + 7.
//   order     the base reads at k + 1, before that edge's writes.  A row write landing on a row of a tuple that is not
//             yet on x_q is an x_hazard fault (programs never write an op's x operand during the op).
// Row ports (credit / valid, for the stream unit's row traffic, the collective, the sequencer and the serialized ME
// result word of the tree top): one row write a cycle (16-lane mask; ordered, applied at its edge) and one row read a
// cycle (granted when no beat issues; answered RL = 3 edges later, in order).
// NOT served here: the split stream unit's 3 x 64 scalar, fixed-latency, abutted lane ports (gate vm_su_service stays
// open); the row read port is their row-granular, credit / valid substitute.
// MUT = 1: the shift stage takes the element one lane off (bench must FAIL).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_rowbank #(
    parameter integer DEPTH = 256,
    parameter integer LAW = 8,
    parameter integer USE_MACRO = 0
) (
    input  wire          clk,
    input  wire          re,
    input  wire [LAW-1:0] raddr,
    output wire [511:0]  q,           // one edge after re (macro rd_out), held otherwise
    input  wire          we,
    input  wire [LAW-1:0] waddr,
    input  wire [15:0]   wmask,
    input  wire [511:0]  wdata
);
    wire [511:0] bm;
    genvar e;
    generate for (e = 0; e < 16; e = e + 1) begin : g_m
        assign bm[32*e +: 32] = {32{wmask[e]}};
    end endgenerate
    generate if (USE_MACRO != 0) begin : g_mac
        ot_sram_1r1w_256x256_m2_r2c2 u_lo (.clk(clk), .r_ce_in(re), .r_addr_in(raddr[7:0]), .rd_out(q[255:0]),
            .w_ce_in(we), .w_addr_in(waddr[7:0]), .wd_in(wdata[255:0]), .w_mask_in(bm[255:0]),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_256x256_m2_r2c2 u_hi (.clk(clk), .r_ce_in(re), .r_addr_in(raddr[7:0]), .rd_out(q[511:256]),
            .w_ce_in(we), .w_addr_in(waddr[7:0]), .wd_in(wdata[511:256]), .w_mask_in(bm[511:256]),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end else begin : g_beh
        reg [511:0] mem [0:DEPTH-1];
        reg [511:0] qr;
        integer i;
        initial for (i = 0; i < DEPTH; i = i + 1) mem[i] = 512'd0;
        always @(posedge clk) begin
            if (re) qr <= mem[raddr];
            if (we) mem[waddr] <= (mem[waddr] & ~bm) | (wdata & bm);
        end
        assign q = qr;
    end endgenerate
endmodule


module ot_qfd_sp_vector_memory #(
    parameter integer ELEMS = 177808,
    parameter integer NRB = 64,
    parameter integer AW = 24,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer XVM = 14,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer USE_MACRO = 0,
    parameter integer MUT = 0
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    me_en,      // engine clock enable (the ME's ICG enable): the x path's time base
    // x descriptor (tree top)
    input  wire                    x_dv,
    input  wire [AW-1:0]           x_dc,
    input  wire [AW-1:0]           x_dcs,
    input  wire [3:0]              x_dsp,
    output reg  [(1<<SMAX)*32-1:0] x_q,
    // row write (one a cycle)
    input  wire                    w_v,
    input  wire [AW-5:0]           w_row,
    input  wire [15:0]             w_mask,
    input  wire [511:0]            w_data,
    // row read (valid / ready request, in-order response RL edges later)
    input  wire                    r_v,
    output wire                    r_rdy,
    input  wire [AW-5:0]           r_row,
    output wire                    r_qv,
    output wire [511:0]            r_q,
    output wire                    x_rdy,      // a new op's first tuple may come (to the tree top's ready)
    output reg                     x_fault,
    output reg                     x_hazard
);
    localparam integer NX = 1 << SMAX;
    localparam integer LNRB = $clog2(NRB);
    localparam integer ROWS = (ELEMS + 15) / 16;
    localparam integer DEPTH = (ROWS + NRB - 1) / NRB;
    localparam integer LAW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer LB = $clog2(BMAX) + 1;
    localparam integer HL = XVM + 2;                     // descriptor history (engine edges)
    localparam integer RL = 3;
    // ---- descriptor history, in engine edges: age 0 = registered on the last engine edge ----
    reg  [HL-1:0] h_new;                                 // a new tuple (re-read)
    reg  [AW-1:0] h_dc [0:HL-1];
    reg  [AW-1:0] h_d  [0:HL-1];
    reg  [3:0]    h_sp [0:HL-1];
    reg  [LB-1:0] h_b  [0:HL-1];
    reg  [AW+12:0] h_span [0:HL-1];                      // last element offset (S-1)*d
    reg           p_v;                                   // previous descriptor (for the hold test)
    reg  [AW-1:0] p_dc, p_d;
    reg  [3:0]    p_sp;
    wire [AW+12:0] span_n = (({{13{1'b0}}, {AW{1'b0}}} | ((1 << x_dsp) - 1)) * x_dcs);
    wire           same = p_v && x_dv && p_dc == x_dc && p_d == x_dcs && p_sp == x_dsp;
    wire           nt = x_dv && !same;
    wire [AW+12:0] bq = span_n / BEAT;
    reg  [ND-1:0]  din;
    integer di;
    always @(*) begin
        for (di = 0; di < ND; di = di + 1) din[di] = (x_dcs == DSET[di*8 +: 8]);
    end
    integer a;
    // beats issued this edge: age a holds the tuple whose beat j = a - (XVM - 5 - B) is due
    reg            bi_v;
    reg  [LB-1:0]  bi_j;
    reg  [AW-1:0]  bi_dc, bi_d;
    reg  [3:0]     bi_sp;
    reg  [1:0]     bi_n;
    always @(*) begin
        bi_v = 1'b0; bi_j = 0; bi_dc = 0; bi_d = 0; bi_sp = 0; bi_n = 0;
        for (a = 0; a < HL; a = a + 1)
            if (h_new[a] && a + h_b[a] >= XVM - 7 && a <= XVM - 8) begin
                bi_v = 1'b1; bi_j = a + h_b[a] - (XVM - 7); bi_dc = h_dc[a]; bi_d = h_d[a]; bi_sp = h_sp[a];
                bi_n = bi_n + 1'b1;
            end
    end
    reg [LB+1:0] xcnt;
    assign x_rdy = (xcnt == BMAX);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) xcnt <= BMAX;
        else if (me_en) xcnt <= nt ? 0 : (xcnt == BMAX) ? xcnt : xcnt + 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            h_new <= 0; p_v <= 1'b0; x_fault <= 1'b0;
        end else if (me_en) begin
            h_new <= {h_new[HL-2:0], nt};
            p_v <= x_dv; p_dc <= x_dc; p_d <= x_dcs; p_sp <= x_dsp;
            if (nt && (bq >= BMAX || !(|din) || x_dsp > SMAX || x_dsp < SMIN)) x_fault <= 1'b1;
            if (bi_n > 1) x_fault <= 1'b1;               // a new tuple came before the previous one's beats ended
        end
    end
    always @(posedge clk) if (me_en) begin
        for (a = HL - 1; a > 0; a = a - 1) begin
            h_dc[a] <= h_dc[a-1]; h_d[a] <= h_d[a-1]; h_sp[a] <= h_sp[a-1]; h_b[a] <= h_b[a-1]; h_span[a] <= h_span[a-1];
        end
        h_dc[0] <= x_dc; h_d[0] <= x_dcs; h_sp[0] <= x_dsp; h_b[0] <= bq[LB-1:0] + 1'b1; h_span[0] <= span_n;
    end
    // ---- S0: bank read addresses (beat issue, priority) or the row read port ----
    wire [AW-1:0] ba = bi_dc + bi_j * BEAT;              // the beat's first element
    wire [AW-5:0] br0 = ba[AW-1:4];
    reg  [NRB-1:0] b_re;
    reg  [NRB*LAW-1:0] b_ra;
    assign r_rdy = !(me_en && bi_v);
    genvar gb;
    generate for (gb = 0; gb < NRB; gb = gb + 1) begin : g_s0
        //: the beat's row in bank gb: the one of br0 .. br0 + NRB - 1 congruent to gb
        wire [AW-5:0] rowb = br0 + ((gb - br0) & (NRB - 1));
        always @(posedge clk) begin
            b_re[gb] <= (me_en && bi_v) || (r_v && r_rdy && (r_row[LNRB-1:0] == gb));
            b_ra[gb*LAW +: LAW] <= (me_en && bi_v) ? rowb[LNRB +: LAW] : r_row[LNRB +: LAW];
        end
    end endgenerate
    // beat / row-read tags down the pipe (beat side advances on engine edges only)
    reg  s1_bv, s2_bv, s3_bv, s4_bv, s5_bv, s6_bv;
    reg  [1:0] bpp, s1_pp, s2_pp, s3_pp;                 // beat sequence mod 3: the capture slot
    reg  [LB-1:0] s1_j, s2_j, s3_j, s4_j, s5_j, s6_j;
    reg  [AW-1:0] s1_a, s2_a, s3_a, s4_a, s5_a;
    reg  [ND-1:0] s1_d, s2_d, s3_d, s4_d, s5_d, s6_d;
    reg  [3:0]    s1_sp, s2_sp, s3_sp, s4_sp, s5_sp, s6_sp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_bv <= 0; s2_bv <= 0; s3_bv <= 0; s4_bv <= 0; s5_bv <= 0; s6_bv <= 0; bpp <= 2'd0; end
        else if (me_en) begin
            s1_bv <= bi_v; s2_bv <= s1_bv; s3_bv <= s2_bv; s4_bv <= s3_bv; s5_bv <= s4_bv; s6_bv <= s5_bv;
            if (bi_v) bpp <= (bpp == 2'd2) ? 2'd0 : bpp + 2'd1;
        end
    end
    reg [ND-1:0] bdin;
    always @(*) for (di = 0; di < ND; di = di + 1) bdin[di] = (bi_d == DSET[di*8 +: 8]);
    always @(posedge clk) if (me_en) begin
        s1_j <= bi_j; s1_a <= ba; s1_d <= bdin; s1_sp <= bi_sp; s1_pp <= bpp; s2_pp <= s1_pp; s3_pp <= s2_pp;
        s6_j <= s5_j; s6_d <= s5_d; s6_sp <= s5_sp;
        s2_j <= s1_j; s2_a <= s1_a; s2_d <= s1_d; s2_sp <= s1_sp;
        s3_j <= s2_j; s3_a <= s2_a; s3_d <= s2_d; s3_sp <= s2_sp;
        s4_j <= s3_j; s4_a <= s3_a; s4_d <= s3_d; s4_sp <= s3_sp;
        s5_j <= s4_j; s5_a <= s4_a; s5_d <= s4_d; s5_sp <= s4_sp;
    end
    // ---- banks (S1: macro read), S2: capture beside the macro ----
    wire [NRB*512-1:0] bq_w;
    reg  [NRB*512-1:0] cap0, cap1, cap2;
    reg  m1, m2;                                         // a beat's read is registered / in the macros (real edges)
    reg  [1:0] m1_pp, m2_pp;
    genvar g;
    generate for (g = 0; g < NRB; g = g + 1) begin : g_bank
        ot_qfd_vm_rowbank #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_b (.clk(clk),
            .re(b_re[g]), .raddr(b_ra[g*LAW +: LAW]), .q(bq_w[g*512 +: 512]),
            .we(w_v && w_row[LNRB-1:0] == g), .waddr(w_row[LNRB +: LAW]), .wmask(w_mask), .wdata(w_data));
    end endgenerate
    // row-read response tags (not engine-gated)
    reg [RL-1:0] rr_v;
    reg [LNRB-1:0] rr_b0, rr_b1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rr_v <= 0;
        else rr_v <= {rr_v[RL-2:0], r_v && r_rdy};
    end
    always @(posedge clk) begin rr_b0 <= r_row[LNRB-1:0]; rr_b1 <= rr_b0; end
    reg [511:0] r_qr;
    always @(posedge clk) begin
        m1 <= me_en && bi_v; m1_pp <= bpp; m2 <= m1; m2_pp <= m1_pp;
        if (m2 && m2_pp == 2'd0) cap0 <= bq_w;            // beat words, captured beside the macros
        if (m2 && m2_pp == 2'd1) cap1 <= bq_w;
        if (m2 && m2_pp == 2'd2) cap2 <= bq_w;
        if (rr_v[1]) r_qr <= bq_w[rr_b1*512 +: 512];
    end
    assign r_qv = rr_v[2];
    assign r_q = r_qr;
    // ---- S3 (engine edge 3 after the issue): rotate banks into row order (coarse, by 8 banks), S4: fine (by 1) ----
    reg [NRB*512-1:0] rot1, rot2;
    integer i;
    wire [LNRB-1:0] rot = s3_a[4 +: LNRB];
    wire [NRB*512-1:0] capx = (s3_pp == 2'd0) ? cap0 : (s3_pp == 2'd1) ? cap1 : cap2;
    always @(posedge clk) if (me_en) begin
        for (i = 0; i < NRB; i = i + 1)
            rot1[i*512 +: 512] <= capx[((i + (rot & ~((NRB >= 8) ? 7 : 0))) % NRB)*512 +: 512];
    end
    wire [LNRB-1:0] rotf = s4_a[4 +: LNRB] & ((NRB >= 8) ? 7 : {LNRB{1'b1}});
    always @(posedge clk) if (me_en) begin
        for (i = 0; i < NRB; i = i + 1) rot2[i*512 +: 512] <= rot1[((i + ((NRB >= 8) ? rotf : 0)) % NRB)*512 +: 512];
    end
    // ---- S5: element shift (A mod 16), the beat vector, beyond ELEMS -> 0 ----
    reg [BEAT*32-1:0] bv;
    wire [3:0] sh = s5_a[3:0] + ((MUT != 0) ? 4'd1 : 4'd0);
    always @(posedge clk) if (me_en) begin
        for (i = 0; i < BEAT; i = i + 1)
            bv[i*32 +: 32] <= ((s5_a + i) < ELEMS) ? rot2[(i + sh)*32 +: 32] : 32'd0;
    end
    // ---- S6: decimate into the assembly line ----
    reg [NX*32-1:0] line;
    genvar c, dd;
    generate for (c = 0; c < NX; c = c + 1) begin : g_ent
        wire [ND-1:0] hit;
        wire [ND*32-1:0] src;
        for (dd = 0; dd < ND; dd = dd + 1) begin : g_d
            localparam integer DV = DSET[dd*8 +: 8];
            localparam integer JJ = (c * DV) / BEAT;
            localparam integer MM = (c * DV) % BEAT;
            if (JJ < BMAX) begin : g_ok
                assign hit[dd] = s6_d[dd] && (s6_j == JJ);
                assign src[dd*32 +: 32] = bv[MM*32 +: 32];
            end else begin : g_no
                assign hit[dd] = 1'b0;
                assign src[dd*32 +: 32] = 32'd0;
            end
        end
        reg [31:0] pick;
        integer k;
        always @(*) begin
            pick = 32'd0;
            for (k = 0; k < ND; k = k + 1) if (hit[k]) pick = src[k*32 +: 32];
        end
        always @(posedge clk) if (me_en && s6_bv && (|hit) && c < (1 << s6_sp)) line[c*32 +: 32] <= pick;
    end endgenerate
    // ---- copy-out: a new tuple's line at age XVM - 1 (= engine edge k + XVM + 1), S-periodic ----
    wire       co_v = h_new[XVM-1];
    wire [3:0] co_sp = h_sp[XVM-1];
    always @(posedge clk) if (me_en && co_v) begin
        for (i = 0; i < NX; i = i + 1) x_q[i*32 +: 32] <= line[(i & ((1 << co_sp) - 1))*32 +: 32];
    end
    // ---- x hazard: a row write onto the span of a new tuple not yet on x_q ----
    reg hz;
    always @(*) begin
        hz = 1'b0;
        for (a = 0; a <= XVM; a = a + 1)
            if (h_new[a] && w_v && ({w_row, 4'hf} >= h_dc[a]) && ({w_row, 4'h0} <= h_dc[a] + h_span[a])) hz = 1'b1;
        if (nt && w_v && ({w_row, 4'hf} >= x_dc) && ({w_row, 4'h0} <= x_dc + span_n)) hz = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_hazard <= 1'b0;
        else if (hz) x_hazard <= 1'b1;
    end
endmodule

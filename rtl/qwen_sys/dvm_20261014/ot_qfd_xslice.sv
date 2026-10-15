`timescale 1ns/1ps
// =====================================================================================================================
// Qwen TP8 compute die: DISTRIBUTED x SLICES (owner decision 2026-10-14, HANDOFF 0x; study el1014-qwen-dvm-study.log,
// build el1014-qwen-dvm-build.log).  The matrix engine's x operand is no longer read from the central vector memory:
// every tile column holds, next to its column head, exactly its 16 tiles' x footprints, filled by a broadcast along the
// head row that taps the VM write stream, and delivered to each tile by time-sharing the corridor's existing 128-bit
// x field (each tile gets ITS OWN quad line: the x-line functional gap of the two-root broadcast is closed).
//
// Masters (all register-at-the-pin on every functional port; each its own clock root):
//   ot_qfd_xs_tap    (qfd_xs_tap, 1)        VM write face: taps SU (64 el) and attention-return (16 el) writes inside
//                                           an armed x range, rounds them to the consumer's BF16 operand and emits the
//                                           head-row word {fill, ib, go} to both roots (go / ib of the tree top ride the
//                                           fill's pipeline: r3).
//   ot_qfd_xhead     (qfd_xhead_e/_w, 48)   column head: head-row station AND the column slice control (epochs, the 16
//                                           tile windows from the tids strap, pooled pairs, leaf write control, serial-
//                                           read TDM sequencer) and the N / S corridor launch {go, ib, xl, tag}.
//   ot_qfd_xs_leaf   (qfd_xs_leaf, 384)     2 tiles x 2 epochs x one 64-position slot of BF16 + per-element valid, one
//                                           serial 128:1 read tree per tile (r3: shaped to the 64.8-um column slot).
//   ot_qfd_xcst      (qfd_xcst_n/_s, 768)   corridor station: onward word, tap {go, ib, xl} to the tile, a capture
//                                           register for its own TDM slot and the tuple hold register that drives xl.
// The column (xhead + 8 leaves) is a die-placed N-S stack in the 64.8 x 1,313.28 corridor slot (ot_qfd_xslice_slots.sv).
//
// EXACTNESS BY CONSTRUCTION.  (1) Operand: the tile multiplies RNE16(x) when the op rounds (ot_qwen_w12_matvec.sv
// g_s3xd: (x + 0x7FFF + x[16]) & 0xFFFF0000) and x[31:16] when it does not; the tap stores exactly that 16-bit value
// hi16 and the tile receives {hi16, 16'h0}: its own re-round adds <= 0x8000 to a zero low half (no carry), so the
// multiplier operand is bit-identical.  (2) Addressing: the slice serves element xbase + c*xcs + k*xks for chunk
// c = (TG*t + i) mod S of tile t (the array's x network, ot_qwen_me_array_w12), j-invariant (xjs 0: the line is held
// for the IL = 8 edges of a tuple); a tile footprint (TG-1)*xcs + (k-1)*xks + 1 <= 64 sits in the tile's own
// 64-position slot at any alignment, 65 .. 128 is pooled over the tile pair that reads the same quad (64-aligned),
// anything else faults; every element read must have been written in this epoch (per-element valid): a violation is a
// sticky FAULT, never a stale value.
// (3) Ordering: fill and go travel the same in-order head row, the go reaches a column after every fill beat issued
// before it; the descriptor of the consumer op is compared with the go's own fields (xbase, xcs, xks, split, k, round)
// and an op without a matching filled epoch faults.
//
// Fill word (head row, FW bits, LSB first in the concatenation below):
//   desc:  dv, dep, dxb[AW], dxcs[XCW], dxks[XCW], dsp[4], dk[NW], drnd           (DESC = 2 + AW + 2*XCW + 4 + NW + 1)
//   data:  fv, fep, fb[AW-6] (aligned 64-element beat), foff[6] (write start mod 64), fm[64] (per lane), fd[64*16]
// A data beat travels UNROTATED (lane l = element 64*fb + foff + l); the column head rotates it by foff so that
// position p holds element 64*fb + p for p >= foff and element 64*(fb + 1) + p for p < foff: any 64-element write
// (any alignment) is ONE beat.
// =====================================================================================================================

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xs_tap: the x-fill tap at the VM write face (one instance).
//   xpf_*  arm descriptor (sequencer, issued before the consumer's producer writes): epochs alternate.
//   sw_*   SU lane write: element sw_a + l for lane l (stride 1), lanes with sw_m[l].
//   aw_*   attention-return write: element aw_a + l, l < 16.
// Pipeline: descriptor E1 pin registers, E2 range products, E3 range armed + DESC out; writes E1 pin registers, E2
// merged / classified (+ per-lane RNE carry), E3 rounded data out, UNROTATED (the column head rotates it).  SEQUENCER RULE: the first write of an armed range comes >= 3 edges
// after its XPF (the descriptor then leads the range's first data beat by >= 2 edges on the head row, the time an
// xhead needs to compute the tile windows).
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xs_tap #(
    parameter integer AW  = 24,
    parameter integer NW  = 18,
    parameter integer XCW = 12,
    parameter integer STATIC_SCHEDULE = 0,
    parameter integer NATIVE_AFFINE = 0,
    parameter integer MUT = 0            // 1: no rounding (truncation) -- bench mutant, must FAIL
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              xpf_v,
    input  wire [AW-1:0]     xpf_xbase,
    input  wire [XCW-1:0]    xpf_xcs,
    input  wire [XCW-1:0]    xpf_xks,
    input  wire [3:0]        xpf_split,
    input  wire [NW-1:0]     xpf_k,
    input  wire              xpf_round,
    input  wire              sw_v,
    input  wire [AW-1:0]     sw_a,
    input  wire [63:0]       sw_m,
    input  wire [64*32-1:0]  sw_d,
    input  wire              aw_v,
    input  wire [AW-1:0]     aw_a,
    input  wire [15:0]       aw_m,
    input  wire [16*32-1:0]  aw_d,
    // go / ib of the tree top (tt_ctlm): {ib, go}; they leave in the head-row word at the fill data's stage
    input  wire [3*NW+13*AW+13:0] gi,
    // the two head roots (W / E), each driven by its own registers: {fill, ib, go}
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] hw,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] he,
    // the column faults, chained inward along each head row
    input  wire              fw_i,
    input  wire              fe_i,
    output reg               fault
);
    localparam integer BW = AW - 6;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer FW = DESC + 2 + BW + 6 + 64 + 1024;
    // ---- go / ib: E1 pin register, E2, then the output stage with the fill (fill-before-go: a write accepted at an
    //      edge before the go's leaves before or with it, except an attention beat queued behind an SU beat, which can
    //      trail by <= 2 edges: the column head's FILL_LEAD) ----
    reg              g1_v, g2_v;
    reg [IBW-1:0]    g1_ib, g2_ib;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin g1_v <= 1'b0; g2_v <= 1'b0; end
        else begin g1_v <= gi[0]; g2_v <= g1_v; end
    always @(posedge clk) begin g1_ib <= gi[IBW:1]; g2_ib <= g1_ib; end
    reg fwq, feq;
    // ---- E1: pin registers ----
    reg              p_v, p_rnd;
    reg [AW-1:0]     p_xb;
    reg [XCW-1:0]    p_xcs, p_xks;
    reg [3:0]        p_sp;
    reg [NW-1:0]     p_k;
    reg              s1_v, a1_v;
    reg [AW-1:0]     s1_a, a1_a;
    reg [63:0]       s1_m;
    reg [64*32-1:0]  s1_d;
    reg [15:0]       a1_m;
    reg [16*32-1:0]  a1_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p_v <= 1'b0; s1_v <= 1'b0; a1_v <= 1'b0; end
        else begin p_v <= xpf_v; s1_v <= sw_v; a1_v <= aw_v; end
    always @(posedge clk) begin
        p_xb <= xpf_xbase; p_xcs <= xpf_xcs; p_xks <= xpf_xks; p_sp <= xpf_split; p_k <= xpf_k; p_rnd <= xpf_round;
        s1_a <= sw_a; s1_m <= sw_m; s1_d <= sw_d; a1_a <= aw_a; a1_m <= aw_m; a1_d <= aw_d;
    end
    // ---- E2: range products (span of the consumer's reads: (S-1)*xcs + (k-1)*xks) ----
    reg              q_v, q_rnd;
    reg [AW-1:0]     q_xb;
    reg [XCW-1:0]    q_xcs, q_xks;
    reg [3:0]        q_sp;
    reg [NW-1:0]     q_k;
    reg [AW-1:0]     q_s1, q_s2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q_v <= 1'b0; else q_v <= p_v;
    always @(posedge clk) begin
        q_xb <= p_xb; q_xcs <= p_xcs; q_xks <= p_xks; q_sp <= p_sp; q_k <= p_k; q_rnd <= p_rnd;
        if(NATIVE_AFFINE!=0)begin
            // Actual weight programs: xcs=k,xks=1. Total producer range is S*k,not two general products.
            q_s1 <= {{(AW-XCW){1'b0}},p_xcs} << p_sp;q_s2<=0;
        end else begin
            q_s1 <= ({{(AW-XCW){1'b0}}, p_xcs} << p_sp) - {{(AW-XCW){1'b0}}, p_xcs};
            q_s2 <= (p_k - 1'b1) * p_xks;
        end
    end
    // ---- E3: arm (epochs alternate) + descriptor out ----
    reg              ep_nx;
    reg  [1:0]       arm;
    reg  [AW-1:0]    lo [0:1];
    reg [AW-1:0] lo_minus64 [0:1];
    reg [1:0] lo_below64;
    reg  [AW:0]      hi [0:1];
    reg  [1:0]       rnd;
    reg  [DESC-1:0]  d_o [0:1];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ep_nx <= 1'b0; arm <= 2'b00; d_o[0] <= {DESC{1'b0}}; d_o[1] <= {DESC{1'b0}}; end
        else begin
            d_o[0][0] <= 1'b0; d_o[1][0] <= 1'b0;
            if (q_v) begin
                // XPF transfers write ownership to the next image.  The previous
                // epoch remains in the leaves for reads, but must no longer
                // classify producer writes: consecutive ops may reuse addresses.
                // MUT 5 restores the stale-owner bug as an observable control.
                if (MUT == 5) arm[ep_nx] <= 1'b1;
                else arm <= ep_nx ? 2'b10 : 2'b01;
                lo[ep_nx] <= q_xb;
                lo_minus64[ep_nx] <= q_xb - 64;
                lo_below64[ep_nx] <= (q_xb < 64);
                hi[ep_nx] <= (NATIVE_AFFINE!=0) ? ({1'b0,q_xb}+q_s1) : ({1'b0,q_xb}+q_s1+q_s2+1'b1);
                rnd[ep_nx] <= q_rnd;
                ep_nx <= ~ep_nx;
                d_o[0] <= {q_rnd, q_k, q_sp, q_xks, q_xcs, q_xb, ep_nx, 1'b1};
                d_o[1] <= {q_rnd, q_k, q_sp, q_xks, q_xcs, q_xb, ep_nx, 1'b1};
            end
        end
    // ---- writes: merge (SU first, attention return queued behind it), classify, round, rotate -> E2 out ----
    reg  [1:0]       kq_n;
    reg  [AW-1:0]    kq_a [0:1];
    reg  [15:0]      kq_m [0:1];
    reg  [16*32-1:0] kq_d [0:1];
    reg              q_ovf;
    wire             use_q = STATIC_SCHEDULE==0 && !s1_v && (kq_n != 0);
    wire             use_a = !s1_v && (kq_n == 0) && a1_v;
    wire             push  = a1_v && !use_a;
    wire             w_v   = s1_v | use_q | use_a;
    wire [AW-1:0]    w_a   = STATIC_SCHEDULE ? ((s1_a&{AW{s1_v}})|(a1_a&{AW{a1_v}})) : s1_v ? s1_a : use_q ? kq_a[0] : a1_a;
    wire [63:0]      w_m   = STATIC_SCHEDULE ? ((s1_m&{64{s1_v}})|({48'd0,a1_m}&{64{a1_v}})) : s1_v ? s1_m : use_q ? {48'd0, kq_m[0]} : {48'd0, a1_m};
    wire [64*32-1:0] w_d   = STATIC_SCHEDULE ? ((s1_d&{2048{s1_v}})|({1536'd0,a1_d}&{2048{a1_v}})) : s1_v ? s1_d : use_q ? {1536'd0, kq_d[0]} : {1536'd0, a1_d};
    generate if(STATIC_SCHEDULE!=0)begin : g_fixed_fill
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin kq_n<=0;q_ovf<=0;end
            else begin kq_n<=0;q_ovf<=s1_v && a1_v;end
    end else begin : g_legacy_fill
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin kq_n <= 2'd0; q_ovf <= 1'b0; end
        else begin
            if (use_q && !push) kq_n <= kq_n - 1'b1;
            else if (push && !use_q) begin if (kq_n == 2) q_ovf <= 1'b1; else kq_n <= kq_n + 1'b1; end
        end
    always @(posedge clk) begin
        if (use_q) begin
            kq_a[0] <= kq_a[1]; kq_m[0] <= kq_m[1]; kq_d[0] <= kq_d[1];
            if (push) begin kq_a[kq_n - 2'd1] <= a1_a; kq_m[kq_n - 2'd1] <= a1_m; kq_d[kq_n - 2'd1] <= a1_d; end
        end else if (push && kq_n < 2) begin
            kq_a[kq_n] <= a1_a; kq_m[kq_n] <= a1_m; kq_d[kq_n] <= a1_d;
        end
    end
    end endgenerate
    wire [AW:0] wa_lo = {1'b0, w_a};
// Range overlap: w_a+64>lo iff lo<64 or w_a>lo-64. Precompute the immutable lower threshold
    // at descriptor claim; remove the addition before the fill-stage comparator without changing any edge.
    wire [1:0]  hit;
    assign hit[0] = arm[0] && (wa_lo < hi[0]) && (lo_below64[0] || w_a > lo_minus64[0]);
    assign hit[1] = arm[1] && (wa_lo < hi[1]) && (lo_below64[1] || w_a > lo_minus64[1]);
    wire        hep = hit[1];
    wire        hrd = rnd[hep];
    wire [5:0]  off = w_a[5:0];
    // E2 (gate 11:35 xt1: merge -> classify -> round -> rotate in ONE stage was 23 levels, setup -524 ps): register the
    // merged, classified write with each lane's BF16 high half and its RNE carry; E3 adds the carry when the consumer
    // rounds.  The beat stays UNROTATED (lane l = element w_a + l): the column head rotates it on its leaf-write register
    // (ot_qfd_xhead lw_d / lw_m), where the word is already a register.  One more fill edge: FILL_LEAD 5 in the head.
    reg  [1023:0] h_d;
    reg  [63:0]   c_y;
    integer l;
    reg [31:0] xe;
    always @* begin
        for (l = 0; l < 64; l = l + 1) begin
            xe = w_d[32*l +: 32];
            h_d[16*l +: 16] = xe[31:16];
            c_y[l] = (xe[15:0] > 16'h8000) || (xe[15:0] == 16'h8000 && xe[16]);
        end
    end
    reg              e4_v, e4_ep, e4_rnd;
    reg [BW-1:0]     e4_b;
    reg [5:0]        e4_off;
    reg [63:0]       e4_m, e4_cy;
    reg [1023:0]     e4_h;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin e4_v <= 1'b0; fault <= 1'b0; fwq <= 1'b0; feq <= 1'b0; end
        else begin
            e4_v <= w_v && (hit != 2'b00);
            fwq <= fw_i; feq <= fe_i;
            if (q_ovf || (w_v && hit == 2'b11) || fwq || feq ||
                (NATIVE_AFFINE!=0 && p_v && (p_xks!=1 || p_xcs!=p_k ||
                 !(p_k==2 || p_k==6 || p_k==8 || p_k==24 || p_k==32)))) fault <= 1'b1;
        end
    always @(posedge clk) begin
        e4_ep <= hep; e4_rnd <= hrd && (MUT != 1); e4_b <= w_a[AW-1:6]; e4_off <= off; e4_m <= w_m; e4_cy <= c_y; e4_h <= h_d;
    end
    // E3: the consumer operand (RNE16 when the op rounds, else the high half), two kept copies (one per head root),
    // with the descriptor d_o and go / ib of the same stage
    wire [1023:0] e5_dn;
    integer k;
    reg [1023:0] e5n;
    always @* for (k = 0; k < 64; k = k + 1) e5n[16*k +: 16] = e4_h[16*k +: 16] + {15'd0, e4_rnd & e4_cy[k]};
    assign e5_dn = e5n;
    genvar gc;
    generate for (gc = 0; gc < 2; gc = gc + 1) begin : g_root
        (* keep *) reg              e5_v, e5_ep, g3_v;
        (* keep *) reg [BW-1:0]     e5_b;
        (* keep *) reg [5:0]        e5_off;
        (* keep *) reg [63:0]       e5_m;
        (* keep *) reg [1023:0]     e5_d;
        (* keep *) reg [IBW-1:0]    g3_ib;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e5_v <= 1'b0; g3_v <= 1'b0; end else begin e5_v <= e4_v; g3_v <= g2_v; end
        always @(posedge clk) begin
            e5_ep <= e4_ep; e5_b <= e4_b; e5_off <= e4_off; e5_m <= e4_m; e5_d <= e5_dn; g3_ib <= g2_ib;
        end
        wire [1+IBW+FW-1:0] w = {e5_d, e5_m, e5_off, e5_b, e5_ep, e5_v, d_o[gc], g3_ib, g3_v};
        if (gc == 0) begin : g_w assign hw = w; end else begin : g_e assign he = w; end
    end endgenerate
endmodule

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xs_leaf: x slice leaf, NTL = 2 tiles (r3, el1014-qwen-dvm-build.log 16:15: shaped to the 64.8-um column slot).
// STORAGE per tile and epoch: ONE 64-entry slot indexed by the element's position p = element mod 64 (a footprint of
// <= 64 elements occupies distinct positions whatever its alignment); a footprint of 65 .. 128 elements (gate_up, S 128)
// is POOLED by the column head over the two tiles of a pair that read the SAME quad (N station s / S station 7 - s:
// beat W in tile A's slot, beat W + 1 in tile B's), so a column holds 2 x 16 x 64 elements, not 2 x 16 x 128.
// WRITE CHAIN: the column's leaves of one corridor half form a chain from the head: the write word's pin registers are
// also the leaf's write outputs wo_* (no extra flop), w_ctl carries NCH leaves' controls (CTW = 9 b a tile), the leaf
// takes bits [17:0] and forwards the rest shifted down.  A leaf at chain depth d sees a write d edges after the first.
// READS are direct (one bus per leaf) and SERIAL: ONE 128:1 x 17-b tree per tile reads one element an edge (the four
// trees of 512:1 of r2 were ~60 % of the leaf); a line request presented at edge R reads element i at R + i and answers
// at R + 4 (q at the pins in the cycle after R + 4); each tile is read once per tuple (IL = 8 edges), so its tree is
// busy 4 edges of 8.  A write presented at edge W is readable by an element read at edge >= W + 1.
//   w_ctl per tile {en, d[1:0], wo[5:0]}: the beat word (rotated: position p holds element 64*fb + p for p >= w_off,
//   64*(fb + 1) + p for p < w_off) lands in the tile's slot at the positions whose beat is the tile's: tile window beat
//   W, start position wo (positions p >= wo hold beat W, p < wo beat W + 1); d = fb - W (00: 0, 01: +1, 10: -1).
//   c_v / c_ep: clear the epoch's valid bits (epoch claimed by a new descriptor; valid needs no reset: an epoch is
//   always claimed before it is filled or read).
//   r_p[i] (7 b) = {en, pos[5:0]}: element i of the line at slot position pos; a disabled element answers 0 (a pooled
//   line is the OR of the two tiles' answers).  q_bad: an enabled element was not written in this epoch.
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xs_leaf #(
    parameter integer EXTERNAL_WD_CAPTURE = 0, // opt-in: WD already captured by actual external512b masters
    parameter integer FILL_PIPE = 0,     // opt-in: separate input/output fill registers (+1 edge per leaf hop)
    parameter integer BANK_PIPE = 0,     // opt-in: four local32-entry banks, registered before final4:1 (+1 read edge)
    parameter integer NCH = 4,           // leaves in a chain
    parameter integer MUT = 0            // 2: tile 1's reads return tile 0's data (swapped tile) -- must FAIL
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          w_v,
    input  wire          w_ep,
    input  wire [5:0]    w_off,
    input  wire [63:0]   w_m,
    input  wire [1023:0] w_d,
    input  wire [NCH*18-1:0] w_ctl,         // 2 tiles x CTW = 18 b a leaf
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [NCH*18-1:0] wo_ctl,
    output wire          co_v,
    output wire          co_ep,
    input  wire          r_v,
    input  wire          r_t,
    input  wire          r_ep,
    input  wire [27:0]   r_p,
    output reg           q_v,
    output reg  [63:0]   q,
    output reg           q_bad
);
    function automatic integer ot_qfd_xs_nrep(input integer w, input integer ln, input integer lv);
        integer loads;
        begin
            loads = w << (ln - 1 - lv);
            ot_qfd_xs_nrep = (loads + 255) / 256;
            if (ot_qfd_xs_nrep < 1) ot_qfd_xs_nrep = 1;
        end
    endfunction
    function automatic integer ot_qfd_xs_mux_rep_sw(input integer w, input integer ln);
        integer lv;
        begin
            ot_qfd_xs_mux_rep_sw = 0;
            for (lv = 0; lv < ln; lv = lv + 1) ot_qfd_xs_mux_rep_sw = ot_qfd_xs_mux_rep_sw + ot_qfd_xs_nrep(w, ln, lv);
        end
    endfunction
    function automatic integer ot_qfd_xs_soff(input integer w, input integer ln, input integer lv);
        integer l;
        begin
            ot_qfd_xs_soff = 0;
            for (l = 0; l < lv; l = l + 1) ot_qfd_xs_soff = ot_qfd_xs_soff + ot_qfd_xs_nrep(w, ln, l);
        end
    endfunction
    localparam integer CTW = 9;
    localparam integer RSW = ot_qfd_xs_mux_rep_sw(17, 7);
    // pin registers (only the control bits are reset; the write chain's pin registers are its outputs)
    // (the read request's pins are registered per tile: its held request and its select registers)
    reg          wv, cv;
    reg          wep, cep;
    reg [5:0]    woff;
    reg [63:0]   wm;
    reg [1023:0] wd;
    generate if(EXTERNAL_WD_CAPTURE==0)begin:g_internal_wd_capture
        always @(posedge clk) wd<=w_d;
    end else begin:g_external_wd_capture
        always @* wd=w_d;
    end endgenerate
    reg [NCH*2*CTW-1:0] wctl;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wv <= 1'b0; cv <= 1'b0; end
        else begin wv <= w_v; cv <= c_v; end
    always @(posedge clk) begin
        wep <= w_ep; woff <= w_off; wm <= w_m; wctl <= w_ctl; cep <= c_ep;
    end
    generate if(FILL_PIPE==0)begin : g_fill_one_edge
    assign wo_v = wv; assign wo_ep = wep; assign wo_off = woff; assign wo_m = wm; assign wo_d = wd;
    assign wo_ctl = {{(2*CTW){1'b0}}, wctl[NCH*2*CTW-1:2*CTW]};
    assign co_v = cv; assign co_ep = cep;
    end else begin : g_fill_two_edges
        // One actual register at each face. The former aliased one-edge
        // pass-through required a raw S-input net to drive a cloned N flop,
        // in parallel with the bank capture (1096 cut-crossing raw nets).
        reg pv,pcv,pep,pcep;
        reg [5:0] poff;
        reg [63:0] pm;
        reg [1023:0] pd;
        reg [NCH*2*CTW-1:0] pctl;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin pv<=0;pcv<=0;end
            else begin pv<=wv;pcv<=cv;end
        always @(posedge clk)begin
            pep<=wep;pcep<=cep;poff<=woff;pm<=wm;pd<=wd;
            pctl<={{(2*CTW){1'b0}},wctl[NCH*2*CTW-1:2*CTW]};
        end
        assign wo_v=pv;assign wo_ep=pep;assign wo_off=poff;assign wo_m=pm;assign wo_d=pd;assign wo_ctl=pctl;
        assign co_v=pcv;assign co_ep=pcep;
    end endgenerate
    wire [63:0] tf;                                     // p >= w_off: the rotated beat word holds beat fb there
    genvar gp;
    generate for (gp = 0; gp < 64; gp = gp + 1) begin : g_tf
        assign tf[gp] = (gp >= woff);
    end endgenerate

    // ---- per tile: storage, one serial read tree, line assembly ----
    wire [16:0] tr [0:1];                               // the tree output {valid, data} of tile t
    wire [1:0]  done;                                   // tile t's last element is in its select registers
    wire [47:0] asm_d [0:1];
    wire [2:0]  asm_v [0:1];                            // enabled-and-valid of elements 0 .. 2
    wire [2:0]  asm_e [0:1];                            // enabled of elements 0 .. 2
    wire [1:0]  l_en;                                   // element 3 enabled
    wire [1:0]  coll;                                   // a request for a tile whose read is in flight
    wire [135:0] bank_result_all;
    wire [2176*2-1:0] mem_all;                          // {valid, data} of every entry, tile 0 then tile 1
    genvar gt, ge, lv, c;
    generate for (gt = 0; gt < 2; gt = gt + 1) begin : g_t
        wire        en  = wctl[CTW*gt + 8];
        wire [1:0]  dd  = wctl[CTW*gt + 6 +: 2];
        wire [5:0]  wo  = wctl[CTW*gt +: 6];
        wire [63:0] tw;
        for (ge = 0; ge < 64; ge = ge + 1) begin : g_tw
            assign tw[ge] = (ge >= wo);
        end
        // storage: entry e = {epoch, position}
        for (ge = 0; ge < 128; ge = ge + 1) begin : g_e
            localparam integer EE = ge >> 6, EP = ge & 63;
            wire cond = (dd == 2'b00) ? (tf[EP] == tw[EP]) : (dd == 2'b01) ? (tf[EP] && !tw[EP]) :
                        (dd == 2'b10) ? (!tf[EP] && tw[EP]) : 1'b0;
            wire we   = wv && (wep == EE) && en && cond && wm[EP];
            reg [15:0] m;
            reg        v;
            always @(posedge clk) if (we) m <= wd[16*EP +: 16];
            always @(posedge clk)
                if (cv && cep == EE) v <= 1'b0;
                else if (we) v <= 1'b1;
            assign mem_all[2176*gt + 17*ge +: 17] = {v, m};
        end
        // sequencer: the request's element 0 loads the select registers from the pins; elements 1 .. 3 from the held
        // request (this tile's held request hp / hep) on the next three edges
        wire       req = r_v && (r_t == gt);              // from the pins
        reg  [1:0] el;                                    // element index now in the select registers
        reg        sv;                                    // select registers hold an element of a request
        reg        hep;                                   // the held request (pin registers of this tile)
        reg [27:0] hp;
        always @(posedge clk) if (req) begin hep <= r_ep; hp <= r_p; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sv <= 1'b0; el <= 2'd0; end
            else if (req) begin sv <= 1'b1; el <= 2'd0; end
            else if (sv) begin el <= el + 1'b1; if (el == 2'd3) sv <= 1'b0; end
        assign coll[gt] = req && sv && (el != 2'd3);
        wire asv;
        wire [1:0] ael;
        wire aen;
        assign done[gt] = asv && (ael == 2'd3);
        // next element's select: from the pins (new request) or the held request
        wire [1:0] nel   = req ? 2'd0 : el + 1'b1;
        wire [6:0] nsel  = req ? {r_ep, r_p[5:0]} : {hep, hp[7*nel +: 6]};
        localparam integer SRC = (MUT == 2 && gt == 1) ? 0 : gt;
        if (BANK_PIPE == 0) begin : g_flat
            wire [RSW-1:0] sr;
            for (lv = 0; lv < 7; lv = lv + 1) begin : g_lv
                localparam integer NR = ot_qfd_xs_nrep(17, 7, lv);
                localparam integer OF = ot_qfd_xs_soff(17, 7, lv);
                for (c = 0; c < NR; c = c + 1) begin : g_c
                    (* keep *) reg f;
                    always @(posedge clk) f <= nsel[lv];
                    assign sr[OF + c] = f;
                end
            end
            ot_qfd_xs_mux_rep #(.W(17), .LN(7), .SW(RSW)) u_m (.d(mem_all[2176*SRC +: 2176]), .s(sr), .q(tr[gt]));
            assign asv=sv; assign ael=el; assign aen=hp[7*el+6];
        end else begin : g_banked
            // Complete local modules keep data masking beside storage. ABC
            // must not share masked512b data planes across distant banks.
            wire [67:0] bank_q;
            genvar bk;
            for(bk=0;bk<4;bk=bk+1)begin : g_bank
                ot_qfd_xs_local_bank #(.BANK(bk)) u_bank (
                    .clk(clk),.wv(wv),.wep(wep),.woff(woff),
                    .wm(wm[32*(bk%2)+:32]),.wd(wd[512*(bk%2)+:512]),
                    .cv(cv),.cep(cep),.en(en),.dd(dd),.wo(wo),
                    .r_sel(nsel[4:0]),.q(bank_q[17*bk+:17]));
            end
            assign bank_result_all[68*gt+:68]=bank_q;
            reg [1:0] bank_sel, bank_sel_q;
            reg vq, enq;
            reg [1:0] elq;
            always @(posedge clk)begin
                bank_sel<=nsel[6:5];bank_sel_q<=bank_sel;
                elq<=el;enq<=hp[7*el+6];
            end
            always @(posedge clk or negedge rst_n)
                if(!rst_n)vq<=0;else vq<=sv;
            ot_qfd_xs_mux_rep #(.W(17),.LN(2),.SW(2)) u_final
                (.d(bank_result_all[68*SRC+:68]),.s(bank_sel_q),.q(tr[gt]));
            assign asv=vq;assign ael=elq;assign aen=enq;
        end
        // assembly of elements 0 .. 2 (element 3 goes straight to the answer register)
        reg [47:0] ad;
        reg [2:0]  av, ae;
        wire       een = aen;                    // enable of the element in the select registers (held)
        always @(posedge clk)
            if (asv && ael != 2'd3) begin
                ad[16*ael +: 16] <= een ? tr[gt][15:0] : 16'd0;
                av[ael] <= een && tr[gt][16];
                ae[ael] <= een;
            end
        assign asm_d[gt] = ad; assign asm_v[gt] = av; assign asm_e[gt] = ae;
        assign l_en[gt] = BANK_PIPE!=0 ? aen : hp[27];
    end endgenerate
    // A tile is requested once per tuple (the head's TDM): a request while its previous read is in flight is a
    // collision and answers bad (fail-loud).  The two tiles' requests come on different edges, so they finish on
    // different edges; both finishing together also answers bad.
    wire       fin  = done[0] | done[1];
    wire       ft   = done[1];
    wire [15:0] l3  = l_en[ft] ? tr[ft][15:0] : 16'd0;
    wire       bad3 = l_en[ft] && !tr[ft][16];
    wire       badx = |(asm_e[ft] & ~asm_v[ft]);
    reg        coll_q;
    reg        coll_pipe;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)coll_pipe<=0;else coll_pipe<=|coll;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_v <= 1'b0; q_bad <= 1'b0; coll_q <= 1'b0; end
        else begin
            coll_q <= BANK_PIPE!=0 ? coll_pipe : |coll;
            q_v <= fin;
            q_bad <= fin && (bad3 || badx || (done[0] && done[1]) || coll_q);
        end
    always @(posedge clk) q <= {l3, asm_d[ft]};
endmodule



// Synthesis boundary for one real32-entry {valid,BF16} bank. Keep this
// hierarchy through ABC, then flatten into the hardened leaf for placement.
(* keep_hierarchy = "yes" *) module ot_qfd_xs_local_bank #(parameter integer BANK=0)(
    input wire clk,wv,wep,cv,cep,en,
    input wire [5:0] woff,wo,
    input wire [1:0] dd,
    input wire [31:0] wm,
    input wire [511:0] wd,
    input wire [4:0] r_sel,
    output wire [16:0] q
);
    wire [543:0] entries;
    genvar e,lv,c;
    generate for(e=0;e<32;e=e+1)begin:g_e
        localparam integer EP=(BANK%2)*32+e,EE=BANK/2;
        wire tf=(EP>=woff),tw=(EP>=wo);
        wire cond=(dd==0)?(tf==tw):(dd==1)?(tf&&!tw):(dd==2)?(!tf&&tw):1'b0;
        wire we=wv&&(wep==EE)&&en&&cond&&wm[e];
        reg [15:0] m;
        reg v;
        always @(posedge clk)if(we)m<=wd[16*e+:16];
        always @(posedge clk)if(cv&&cep==EE)v<=0;else if(we)v<=1;
        assign entries[17*e+:17]={v,m};
    end endgenerate
    wire [5:0] select_q;
    generate for(lv=0;lv<5;lv=lv+1)begin:g_lv
        localparam integer NR=(lv==0)?2:1,OF=(lv==0)?0:lv+1;
        for(c=0;c<NR;c=c+1)begin:g_c
            (* keep *) reg f;
            always @(posedge clk)f<=r_sel[lv];
            assign select_q[OF+c]=f;
        end
    end endgenerate
    wire [16:0] comb_q;
    ot_qfd_xs_mux_rep #(.W(17),.LN(5),.SW(6)) u_local(.d(entries),.s(select_q),.q(comb_q));
    (* keep *) reg [16:0] result_q;
    always @(posedge clk)result_q<=comb_q;
    assign q=result_q;
endmodule

// Fixed production candidate master: no runtime/parent parameter overrides.
// Qualified only with its own physical view and compiler+clock profile.
module qfd_xs_leaf_banked (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          w_v,
    input  wire          w_ep,
    input  wire [5:0]    w_off,
    input  wire [63:0]   w_m,
    input  wire [1023:0] w_d,
    input  wire [72-1:0] w_ctl,         // 2 tiles x CTW = 18 b a leaf
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [72-1:0] wo_ctl,
    output wire          co_v,
    output wire          co_ep,
    input  wire          r_v,
    input  wire          r_t,
    input  wire          r_ep,
    input  wire [27:0]   r_p,
    output wire           q_v,
    output wire  [63:0]   q,
    output wire           q_bad
);
    ot_qfd_xs_leaf #(.NCH(4),.BANK_PIPE(1),.FILL_PIPE(1)) u_leaf (
        .clk(clk),
        .rst_n(rst_n),
        .w_v(w_v),
        .w_ep(w_ep),
        .w_off(w_off),
        .w_m(w_m),
        .w_d(w_d),
        .w_ctl(w_ctl),
        .c_v(c_v),
        .c_ep(c_ep),
        .wo_v(wo_v),
        .wo_ep(wo_ep),
        .wo_off(wo_off),
        .wo_m(wo_m),
        .wo_d(wo_d),
        .wo_ctl(wo_ctl),
        .co_v(co_v),
        .co_ep(co_ep),
        .r_v(r_v),
        .r_t(r_t),
        .r_ep(r_ep),
        .r_p(r_p),
        .q_v(q_v),
        .q(q),
        .q_bad(q_bad));
endmodule

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xhead: column head with the column's x slice control (r3, el1014-qwen-dvm-build.log).
//   Head-row word a_d / b_d (HW bits) = {fill (FW), ib (IBW), go}, from the x tap (go and fill share ONE pipeline from
//   the tap: a go is never ahead of a fill beat the tap emitted before it); b_d is the onward copy = the input pin
//   registers themselves (in -> flop -> out across a 64.8-um tile).
//   Corridor words n_d / s_d (CW bits) = {tag (8), xl (128), ib (IBW), go}: go / ib leave DX edges after they entered
//   this head's pin registers; xl = two quad lines (2 x 64 b BF16) of the corridor's tiles, tag = {vB, sB[2:0], vA,
//   sA[2:0]} the station index each line is for.
//   tids: strap, the 2*NH tiles' reference ids (16 b each; rows 0 .. NH-1 = N stations 0 .. NH-1 outward, rows
//   NH .. 2NH-1 = S stations 0 .. NH-1 outward): the die tree pairs tiles in morton order, so ids are not affine in the
//   row (compute die lead 11:51, DIE_BUS_AUDIT row 5).
//   fault_i: the next column's fault (outward neighbour), chained inward along the head row to the tap.
//   STORAGE MODEL (ot_qfd_xs_leaf): one 64-position slot per tile and epoch.  A footprint fp = (TG-1)*xcs + (k-1)*xks + 1
//   <= 64 lives in its own tile's slot at positions (wo + rel) mod 64 (any alignment); 64 < fp <= 128 is POOLED: tile
//   pair (N station s, S station NH-1-s) must read the same quad (equal window start) at a 64-aligned start (checked,
//   else FAULT): beat W in the N tile's slot, beat W + 1 in the S tile's, one read of both serves both corridors.
//   TDM: tuple n is sent on NE = NH / 2 consecutive edges; N edge e carries stations e (A) and e + NE (B), S edge e
//   carries stations NH-1-e (A) and NE-1-e (B), so a pooled pair travels on the same edge.  Reads are serial in the leaf
//   (an element an edge): a line requested at TDM edge e answers 6 edges later (lr register, leaf select registers,
//   four element reads); the read of tuple 0 leaves on the edge after the go's FILL_LEAD delay.
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xhead #(
    parameter integer AW   = 24,
    parameter integer NW   = 18,
    parameter integer XCW  = 12,
    parameter integer TG   = 4,
    parameter integer IL   = 8,
    parameter integer NH   = 8,          // tiles per corridor (half column)
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer NATIVE_AFFINE = 0,
    parameter integer LEAF_BANK_PIPE = 0, // candidate real leaf pipeline, one extra read edge
    parameter integer REQ_PIPE = 0,       // read-request relay stages after lr (flat column: head -> far leaf ~650 um
                                          // in one edge fails TT; +REQ_PIPE read edges, compiler-visible through DX)
    parameter integer DX   = 10 + LEAF_BANK_PIPE + REQ_PIPE, // FILL_LEAD + 8 (lr register 1, leaf 5, answer pin register 1, launch 1)
    parameter integer FILL_LEAD = 2,     // the tap's two-entry attention-write queue (a queued beat can trail a go by 2)
    parameter integer MUT  = 0           // 3: the TDM sends each line to the wrong station (wrong line);
                                         // 4: reads the other epoch (stale buffer); 6: pooled line without its B half
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [16*2*NH-1:0] tids,
    input  wire          fault_i,
    input  wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] a_d,
    output wire          a_r,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] b_d,
    input  wire          b_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] n_d,
    input  wire          n_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] s_d,
    input  wire          s_r,
    // leaf write chains (two: N leaves 0 .. NH/2-1, S leaves NH/2 .. NH-1), leaf read buses (one per leaf)
    output reg  [1:0]    lw_v,
    output reg  [1:0]    lw_ep,
    output reg  [2*6-1:0] lw_off,
    output reg  [2*64-1:0] lw_m,
    output reg  [2*1024-1:0] lw_d,
    output reg  [NH*18-1:0] lw_ctl,
    output reg  [1:0]    lc_v,
    output reg  [1:0]    lc_ep,
    output wire [NH-1:0] lr_v,
    output wire [NH-1:0] lr_t,
    output wire [NH-1:0] lr_ep,
    output wire [NH*28-1:0] lr_p,
    input  wire [NH*64-1:0] lq,
    input  wire [NH-1:0] lq_v,
    input  wire [NH-1:0] lq_bad,
    output reg           fault
);
    localparam integer IBW  = 3 * NW + 13 * AW + 13;
    localparam integer BW   = AW - 6;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;
    localparam integer DATA = 2 + BW + 6 + 64 + 1024;
    localparam integer FW   = DESC + DATA;
    localparam integer HW   = 1 + IBW + FW;
    localparam integer CW   = 1 + IBW + 128 + 8;
    localparam integer NR   = 2 * NH;            // rows (tiles) of the column
    localparam integer NE   = NH / 2;            // TDM edges a tuple
    localparam integer QD   = 7 + LEAF_BANK_PIPE + REQ_PIPE;      // read issue -> answer usable: lr 1, (relay), leaf 5, answer pin register 1
    // leaf / tile of row r: N station s in N leaf s / 2 (tile s mod 2), S station s in S leaf (NH-1-s) / 2 (tile
    // (NH-1-s) mod 2): a pooled pair (N s, S NH-1-s) sits at the SAME chain depth, and every read at TDM edge e is of
    // a leaf at depth <= e + 2 (the far leaves are read last: a fill reaches depth d d edges after depth 0)
    function automatic integer lf(input integer rw);
        lf = (rw < NH) ? (rw >> 1) : NE + ((NH - 1 - (rw - NH)) >> 1);
    endfunction
    function automatic integer tb(input integer rw);
        tb = (rw < NH) ? (rw & 1) : ((NH - 1 - (rw - NH)) & 1);
    endfunction
    generate if (DX - FILL_LEAD != QD + 1) begin : g_bad_dx
        initial $error("ot_qfd_xhead: DX must be FILL_LEAD + %0d", QD + 1);
    end endgenerate

    // ---- input pin registers = the onward copy (head-row station), ready ----
    reg              g_pin;
    reg  [IBW-1:0]   ib_pin;
    reg  [FW-1:0]    f_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) g_pin <= 1'b0; else g_pin <= a_d[0];
    always @(posedge ck) begin ib_pin <= a_d[1 +: IBW]; f_q <= a_d[1 + IBW +: FW]; end
    assign b_d = {f_q, ib_pin, g_pin};
    reg br_q, nr_q, sr_q, ar_q, fi_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin br_q <= 1'b0; nr_q <= 1'b0; sr_q <= 1'b0; ar_q <= 1'b0; fi_q <= 1'b0; end
        else begin br_q <= b_r; nr_q <= n_r; sr_q <= s_r; ar_q <= br_q & nr_q & sr_q; fi_q <= fault_i; end
    assign a_r = ar_q;
    reg [16*NR-1:0] tid_q;                         // strap register (a constant tie at the die)
    always @(posedge ck) tid_q <= tids;

    // ---- go: FILL_LEAD edges (a queued attention beat and the far leaf's chain stages), then DX - FILL_LEAD to the
    //      corridors; ib is HELD, not delayed: gos are >= IL - 1 = 7 edges apart (a go while busy and not on the
    //      previous op's last edge faults), so hold registers (ib_q for the check, ib_c + one stage ib_c2 on the way
    //      out, DX - FILL_LEAD = 8 > 7) replace DX x IBW delay flops ----
    wire             g_q, g_dx;
    ot_hdc_delay #(.W(1), .D(FILL_LEAD), .RESET(1)) u_fill_go (.clk(ck), .rst_n(rst_n), .d(g_pin), .q(g_q));
    ot_hdc_delay #(.W(1), .D(DX - FILL_LEAD), .RESET(1)) u_gdx (.clk(ck), .rst_n(rst_n), .d(g_q), .q(g_dx));
    reg  [IBW-1:0]   ib_q, ib_c, ib_c2;            // ib of the go being checked / the go on its way to the corridors
    always @(posedge ck) begin
        if (g_pin) ib_q <= ib_pin;
        if (g_q) ib_c <= ib_q;
        ib_c2 <= ib_c;
    end

    // ---- fill fields ----
    wire              d_v   = f_q[0];
    wire              d_ep  = f_q[1];
    wire [AW-1:0]     d_xb  = f_q[2 +: AW];
    wire [XCW-1:0]    d_xcs = f_q[2 + AW +: XCW];
    wire [XCW-1:0]    d_xks = f_q[2 + AW + XCW +: XCW];
    wire [3:0]        d_sp  = f_q[2 + AW + 2*XCW +: 4];
    wire [NW-1:0]     d_k   = f_q[2 + AW + 2*XCW + 4 +: NW];
    wire              d_rnd = f_q[2 + AW + 2*XCW + 4 + NW];
    wire              fv    = f_q[DESC];
    wire              fep   = f_q[DESC + 1];
    wire [BW-1:0]     fb    = f_q[DESC + 2 +: BW];
    wire [5:0]        foff  = f_q[DESC + 2 + BW +: 6];
    wire [63:0]       fm    = f_q[DESC + 2 + BW + 6 +: 64];
    wire [1023:0]     fd    = f_q[DESC + 2 + BW + 6 + 64 +: 1024];

    // ---- epochs: 0 FREE, 1 FILL, 2 READ ----
    reg  [1:0]        st [0:1];
    reg  [AW-1:0]     e_xb  [0:1];
    reg  [XCW-1:0]    e_xcs [0:1];
    reg  [XCW-1:0]    e_xks [0:1];
    reg  [3:0]        e_sp  [0:1];
    reg  [NW-1:0]     e_k   [0:1];
    reg               e_rnd [0:1];
    reg               e_pool [0:1];
    // tile windows: beat W and start position of the tile's slot, per epoch and row
    reg  [BW-1:0]     wb  [0:1][0:NR-1];
    // {1'b0, W} + 1 and {1'b0, W} - 1 (BW + 1 bits, modulo 2^(BW+1)), precomputed with W in the descriptor's stage C:
    // the data beat's write enable/d then needs three BW-bit equality compares instead of an 19-bit subtraction
    reg  [BW:0]       wbp [0:1][0:NR-1];
    reg  [BW:0]       wbm [0:1][0:NR-1];
    reg  [5:0]        wo  [0:1][0:NR-1];      // write window start (pooled: 0, the slot is one whole beat)
    reg  [5:0]        ro  [0:1][0:NR-1];      // read offset = the footprint's start position (emin mod 64)
    // descriptor pipeline: masked quads + factors (stage A), products + footprint (stage B), windows + pool checks
    // (stage C, written at the end of the descriptor's third edge: the tap puts the first data beat >= 3 edges behind
    // its descriptor on the head row)
    reg               da_v, da_ep, dp_v, dp_ep;
    reg  [AW-1:0]     da_xb, dp_xb;
    reg  [XCW-1:0]    da_xcs, da_xks;
    reg  [NW-1:0]     da_km1;
    reg  [SMAX:0]     da_q [0:NR-1];
    reg  [AW-1:0]     dp_pr [0:NR-1];
    reg [NW-1:0] da_k;reg [5:0] dp_k;
    reg [7:0] first_abs [0:1][0:NR-1][0:3];
    reg [12:0] go_bad_bits;
    reg  [AW-1:0]     dp_fm;                        // footprint - 1
    integer r, e, i;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin da_v <= 1'b0; dp_v <= 1'b0; end else begin da_v <= d_v; dp_v <= da_v; end
    always @(posedge ck) begin
        da_ep <= d_ep; da_xb <= d_xb; da_xcs <= d_xcs; da_xks <= d_xks; da_km1 <= d_k - 1'b1; da_k<=d_k;
        // quad q = (tile id) mod (S / TG)
        for (r = 0; r < NR; r = r + 1)
            da_q[r] <= tid_q[16*r +: 16] & ((({{SMAX{1'b0}}, 1'b1}) << (d_sp - $clog2(TG))) - 1'b1);
        dp_ep <= da_ep; dp_xb <= da_xb;
        dp_k<=da_k[5:0];
        dp_fm <= (NATIVE_AFFINE!=0) ? (TG*da_k-1) : (TG - 1) * {{(AW-XCW){1'b0}}, da_xcs} + {{(AW-NW){1'b0}}, da_km1} * {{(AW-XCW){1'b0}}, da_xks};
        // first chunk TG * q; product TG * q * xcs
        for (r = 0; r < NR; r = r + 1)
            if(NATIVE_AFFINE!=0)case(da_k)
                2:dp_pr[r]<=da_q[r]<<(1+$clog2(TG));
                6:dp_pr[r]<=(da_q[r]<<(2+$clog2(TG)))+(da_q[r]<<(1+$clog2(TG)));
                8:dp_pr[r]<=da_q[r]<<(3+$clog2(TG));
                24:dp_pr[r]<=(da_q[r]<<(4+$clog2(TG)))+(da_q[r]<<(3+$clog2(TG)));
                32:dp_pr[r]<=da_q[r]<<(5+$clog2(TG));
                default:dp_pr[r]<=0;
            endcase else dp_pr[r] <= (da_q[r] * TG) * da_xcs;
    end
    reg [AW-1:0] emin [0:NR-1];
    reg          pool_n, pfault_n;
    always @* begin
        for (r = 0; r < NR; r = r + 1) emin[r] = dp_xb + dp_pr[r];
        pool_n = (dp_fm >= 64);
        pfault_n = (dp_fm >= 128);
        // pooled: the pair reads the same quad (equal start) and its footprint fits beats W, W + 1 (start + fp <= 128)
        if (pool_n)
            for (r = 0; r < NH; r = r + 1)
                if (emin[r] != emin[NH + NH - 1 - r] || {1'b0, emin[r][5:0]} + dp_fm[7:0] >= 8'd128) pfault_n = 1'b1;
    end
    always @(posedge ck)
        if (dp_v) begin
            e_pool[dp_ep] <= pool_n;
            for (r = 0; r < NR; r = r + 1) begin
                // pooled: the S tile of a pair holds beat W + 1
                wb[dp_ep][r] <= emin[r][AW-1:6] + ((pool_n && r >= NH) ? 1'b1 : 1'b0);
                // exact {1'b0, W} +/- 1 of the truncated W above, incl. the W wrap (emin beat all ones, pooled S tile)
                if (pool_n && r >= NH && (&emin[r][AW-1:6])) begin
                    wbp[dp_ep][r] <= {{BW{1'b0}}, 1'b1};
                    wbm[dp_ep][r] <= {(BW+1){1'b1}};
                end else begin
                    wbp[dp_ep][r] <= {1'b0, emin[r][AW-1:6]} + ((pool_n && r >= NH) ? 2'd2 : 2'd1);
                    wbm[dp_ep][r] <= (pool_n && r >= NH) ? {1'b0, emin[r][AW-1:6]} : ({1'b0, emin[r][AW-1:6]} - 1'b1);
                end
                wo[dp_ep][r] <= pool_n ? 6'd0 : emin[r][5:0];
                ro[dp_ep][r] <= emin[r][5:0];
                for(i=0;i<4;i=i+1) first_abs[dp_ep][r][i]<={2'b0,emin[r][5:0]}+i*dp_k;
            end
        end

    // ---- stage D (integrity only, one edge after stage C): a pooled read position first_abs + k (k = 0 .. K-1, 8-bit
    //      as the read path forms it) with bit 7 set is a fault.  Every row / element / k of the op is read, so the
    //      check is a static property of the descriptor: flag the epoch here, raise the fault when its go is consumed
    //      (the read path keeps no per-operand overflow adder) ----
    reg          dq_v, dq_ep, dq_pool;
    reg  [5:0]   dq_k;
    reg          e_pbad [0:1];
    reg          pbad_n;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) dq_v <= 1'b0; else dq_v <= dp_v;
    always @(posedge ck) begin dq_ep <= dp_ep; dq_pool <= pool_n; dq_k <= dp_k; end
    always @* begin
        pbad_n = 1'b0;
        for (r = 0; r < NR; r = r + 1)
            for (i = 0; i < 4; i = i + 1)
                if (first_abs[dq_ep][r][i][7] ||
                    ((dq_k != 6'd0) && ({1'b0, first_abs[dq_ep][r][i]} + {3'b000, dq_k} - 9'd1 >= 9'd128))) pbad_n = 1'b1;
    end
    always @(posedge ck) if (dq_v) e_pbad[dq_ep] <= dq_pool && pbad_n;

    // ---- the beat arrives unrotated (lane l = element 64*fb + foff + l): rotate lanes to positions (foff + l) mod 64
    //      in front of the leaf-write registers (f_q is a register; 6 levels of 2:1 per bit) ----
    wire [1023:0] rd_s [0:6];
    wire [63:0]   rm_s [0:6];
    assign rd_s[0] = fd;
    assign rm_s[0] = fm;
    genvar rs;
    generate for (rs = 0; rs < 6; rs = rs + 1) begin : g_rot
        localparam integer K = 1 << rs;
        assign rd_s[rs+1] = foff[rs] ? {rd_s[rs][1023-16*K:0], rd_s[rs][1023 -: 16*K]} : rd_s[rs];
        assign rm_s[rs+1] = foff[rs] ? {rm_s[rs][63-K:0], rm_s[rs][63 -: K]} : rm_s[rs];
    end endgenerate
    wire [1023:0] fd_r = rd_s[6];
    wire [63:0]   fm_r = rm_s[6];

    // ---- data beat -> leaf write control (one edge), to the leaf pins: per tile {en, d, wo} ----
    // d = fb - W in {0, +1, -1} as equality compares against the precomputed W, W + 1, W - 1 (no carry chain between
    // the beat register and the leaf-write control register; HEAD_MUT 7 / 8 / 9 drop the W + 1 / W - 1 / W match)
    reg  d0, dp1, dm1;
    reg  [NH*18-1:0] ctl;
    always @* begin
        ctl = {(NH*18){1'b0}};
        for (r = 0; r < NR; r = r + 1) begin
            d0  = (fb == wb[fep][r]) && (MUT != 9);
            dp1 = ({1'b0, fb} == wbp[fep][r]) && (MUT != 7);
            dm1 = ({1'b0, fb} == wbm[fep][r]) && (MUT != 8);
            ctl[18*lf(r) + 9*tb(r) +: 9] = {
                d0 || dp1 || dm1,                                                       // en
                dm1 ? 2'b10 : dp1 ? 2'b01 : 2'b00,                                      // d = fb - W
                wo[fep][r]};
        end
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin lw_v <= 1'b0; lc_v <= 1'b0; end
        else begin
            lw_v <= {2{fv && (st[fep] != 2'd0)}};
            lc_v <= {2{d_v}};
        end
    always @(posedge ck) begin
        // one kept copy of the write word per chain (N, S): each chain head is driven by its own flops
        lw_ep <= {2{fep}}; lw_off <= {2{foff}}; lw_m <= {2{fm_r}}; lw_d <= {2{fd_r}}; lw_ctl <= ctl; lc_ep <= {2{d_ep}};
    end

    // ---- the go: verify against the oldest filled epoch, then the TDM read sequencer ----
    wire [NW-1:0] b_tiles = ib_q[IBW - 2*NW +: NW];
    wire [NW-1:0] b_k     = ib_q[IBW - 3*NW +: NW];
    wire          b_wsrc  = ib_q[13*AW + 12];
    wire [AW-1:0] b_xbase = ib_q[8*AW + 12 +: AW];
    wire [AW-1:0] b_xks   = ib_q[7*AW + 12 +: AW];
    wire [AW-1:0] b_xjs   = ib_q[6*AW + 12 +: AW];
    wire [AW-1:0] b_xcs   = ib_q[5*AW + 12 +: AW];
    wire [3:0]    b_split = ib_q[5*AW + 5 +: 4];
    wire          b_round = ib_q[4*AW + 4];
    reg           ep_rd;                    // the next epoch a go consumes
    reg           busy;
    reg           rep;                      // the epoch being read
    reg  [NW-1:0] rnd_left, k_i, k_last;
    reg  [AW-1:0] kx;                       // k * xks
    reg  [XCW-1:0] rxcs, rxks;
    reg  [2:0]    ph;                       // TDM edge within the tuple (0 .. IL-1)
    wire          go_ok = (st[ep_rd] == 2'd1) && !b_wsrc && (b_xjs == 0) && (b_xbase == e_xb[ep_rd]) &&
                          (b_xcs == {{(AW-XCW){1'b0}}, e_xcs[ep_rd]}) && (b_xks == {{(AW-XCW){1'b0}}, e_xks[ep_rd]}) &&
                          (b_split == e_sp[ep_rd]) && (b_k == e_k[ep_rd]) && (b_round == e_rnd[ep_rd]) &&
                          (b_tiles != 0) && (b_k != 0);
    reg           f_pos;
    reg  [AW:0]   rel;
    reg  [5:0]    pos;
    localparam integer ABSW=NATIVE_AFFINE!=0 ? 8 : AW+1;
    reg [ABSW-1:0] ab;
    reg  [NH*28-1:0] rp;
    reg  [NH-1:0] rv;
    reg  [NH-1:0] rt;
    // the read of TDM edge 0 of tuple 0 leaves on the edge after the go's FILL_LEAD delay (positions from the descriptor)
    wire          rd_now = g_q || busy;
    wire [2:0]    ph_now = g_q ? 3'd0 : ph;
    wire          rep_now = g_q ? ((MUT == 4) ? ~ep_rd : ep_rd) : rep;
    wire          pool_now = e_pool[rep_now];
    wire [XCW-1:0] xcs_now = g_q ? e_xcs[ep_rd] : rxcs;
    wire [AW-1:0] kx_now = g_q ? {AW{1'b0}} : kx;
    wire          last = busy && (ph == IL - 1) && (k_i == k_last) && (rnd_left == 0);
    // the TDM edge on which row r is read: N e (line A), N e + NE (B), S NH-1-e (A), S NE-1-e (B)
    function automatic integer row_edge(input integer rw);
        begin
            if (rw < NE) row_edge = rw;
            else if (rw < NH) row_edge = rw - NE;
            else if (rw - NH >= NE) row_edge = NH - 1 - (rw - NH);
            else row_edge = NE - 1 - (rw - NH);
        end
    endfunction
    reg  [AW:0]   rel_i [0:3];
    always @* begin
        rp = {(NH*28){1'b0}}; rv = {NH{1'b0}}; rt = {NH{1'b0}}; f_pos = 1'b0;
        for (i = 0; i < 4; i = i + 1) rel_i[i] = i * xcs_now + kx_now;
        // every index below is static (row r, element i): no runtime part-select
        for (r = 0; r < NR; r = r + 1)
            if (rd_now && ph_now == row_edge(r)) begin
                rv[lf(r)] = 1'b1;
                rt[lf(r)] = tb(r);
                for (i = 0; i < 4; i = i + 1) begin
                    if(NATIVE_AFFINE!=0)begin
                        ab=first_abs[rep_now][r][i]+(g_q ? 6'd0 : k_i[5:0]);
                        if(pool_now)begin
                            rp[28*lf(r)+7*i+:7]={(r<NH)?!ab[6]:ab[6],ab[5:0]};
                        end else rp[28*lf(r)+7*i+:7]={1'b1,ab[5:0]};
                    end else begin
                    if (!pool_now) begin
                        // own slot: position (wo + rel) mod 64; a footprint <= 64 keeps rel < 64
                        if (rel_i[i] >= 64) f_pos = 1'b1;
                        pos = ro[rep_now][r] + rel_i[i][5:0];
                        rp[28*lf(r) + 7*i +: 7] = {1'b1, pos};
                    end else begin
                        // pooled: absolute position ro + rel: 0 .. 63 in the N tile's slot (beat W), 64 .. 127 in
                        // the S tile's (beat W + 1)
                        ab = {{(AW-5){1'b0}}, ro[rep_now][r]} + rel_i[i];
                        if (ab >= 128) f_pos = 1'b1;
                        rp[28*lf(r) + 7*i +: 7] = {(r < NH) ? !ab[6] : ab[6], ab[5:0]};
                    end                    end

                end
            end
    end
    reg  [NH-1:0]    lr0_v, lr0_t, lr0_ep;
    reg  [NH*28-1:0] lr0_p;
    always @(posedge ck) begin lr0_t <= rt; lr0_ep <= {NH{rep_now}}; lr0_p <= rp; end
    // read-request relay (REQ_PIPE stages; 0 = the lr register drives the leaf pins directly)
    ot_hdc_delay #(.W(NH), .D(REQ_PIPE), .RESET(1)) u_lrv (.clk(ck), .rst_n(rst_n), .d(lr0_v), .q(lr_v));
    ot_hdc_delay #(.W(2*NH+NH*28), .D(REQ_PIPE)) u_lrd (.clk(ck), .rst_n(rst_n), .d({lr0_t, lr0_ep, lr0_p}),
        .q({lr_t, lr_ep, lr_p}));

    // ---- answers -> corridor launch (the leaf q pins feed the corridor's output flops through one mux) ----
    // the answer of a read issued at TDM edge e is usable QD edges later: carry the edge and the mode along
    wire [2:0] phd;
    wire       vd, pd;
    ot_hdc_delay #(.W(3), .D(QD)) u_phd (.clk(ck), .rst_n(rst_n), .d(ph_now), .q(phd));
    ot_hdc_delay #(.W(1), .D(QD), .RESET(1)) u_vd (.clk(ck), .rst_n(rst_n), .d(rd_now && ph_now < NE), .q(vd));
    ot_hdc_delay #(.W(1), .D(QD)) u_pd (.clk(ck), .rst_n(rst_n), .d(pool_now), .q(pd));
    // the leaves' answers are registered at this tile's pins (register -> wire -> register: r3 gate boundary)
    reg  [NH*64-1:0] lqp;
    reg  [NH-1:0]    lqvp, lqbp;
    always @(posedge ck) lqp <= lq;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin lqvp <= {NH{1'b0}}; lqbp <= {NH{1'b0}}; end else begin lqvp <= lq_v; lqbp <= lq_bad; end
    reg [127:0] xn, xs;
    reg [7:0]   tn, ts;
    reg [2:0]   na, nb, sa, sb;
    reg [63:0]  qna, qnb, qsa, qsb;
    reg         miss;
    always @* begin
        xn = 128'd0; xs = 128'd0; tn = 8'd0; ts = 8'd0; miss = 1'b0;
        qna = 64'd0; qnb = 64'd0; qsa = 64'd0; qsb = 64'd0;
        na = phd; nb = phd + NE; sa = NH - 1 - phd; sb = NE - 1 - phd;
        // static selects: TDM edge e reads N rows e, e + NE and S rows NH + NH-1-e, NH + NE-1-e
        for (e = 0; e < NE; e = e + 1)
            if (phd == e) begin
                qna = lqp[64*lf(e) +: 64];
                qnb = lqp[64*lf(e + NE) +: 64];
                qsa = lqp[64*lf(NH + NH - 1 - e) +: 64];
                qsb = lqp[64*lf(NH + NE - 1 - e) +: 64];
                miss = !lqvp[lf(e)] || !lqvp[lf(e + NE)] || !lqvp[lf(NH + NH - 1 - e)] || !lqvp[lf(NH + NE - 1 - e)];
            end
        if (vd) begin
            if (pd) begin
                xn = (MUT == 6) ? {qnb, qna} : {qnb | qsb, qna | qsa};
                xs = xn;
            end else begin
                xn = {qnb, qna};
                xs = {qsb, qsa};
            end
            if (MUT == 3) begin na = (na + 1'b1) & (NH - 1); nb = (nb + 1'b1) & (NH - 1); sa = (sa + 1'b1) & (NH - 1); sb = (sb + 1'b1) & (NH - 1); end
            tn = {1'b1, nb, 1'b1, na};
            ts = {1'b1, sb, 1'b1, sa};
        end else miss = 1'b0;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)go_bad_bits<=0;
        else go_bad_bits<=g_q ? {
            busy && !last,b_k==0,b_tiles==0,b_round!=e_rnd[ep_rd],b_k!=e_k[ep_rd],
            b_split!=e_sp[ep_rd],b_xks!={{(AW-XCW){1'b0}},e_xks[ep_rd]},
            b_xcs!={{(AW-XCW){1'b0}},e_xcs[ep_rd]},b_xbase!=e_xb[ep_rd],
            b_xjs!=0,b_wsrc,st[ep_rd]!=1,1'b0} : 13'd0;
    reg flt;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            st[0] <= 2'd0; st[1] <= 2'd0; ep_rd <= 1'b0; busy <= 1'b0; flt <= 1'b0; lr0_v <= {NH{1'b0}};
            ph <= 3'd0; rep <= 1'b0; fault <= 1'b0;
        end else begin
            lr0_v <= rv;
            fault <= flt | fi_q;
            // descriptor: claim the epoch
            if (d_v) begin
                if(NATIVE_AFFINE!=0 && (d_xks!=1 || d_xcs!=d_k || !(d_k==2 || d_k==6 || d_k==8 || d_k==24 || d_k==32)))flt<=1;
                if (st[d_ep] != 2'd0) flt <= 1'b1;
                st[d_ep] <= 2'd1;
                e_xb[d_ep] <= d_xb; e_xcs[d_ep] <= d_xcs; e_xks[d_ep] <= d_xks; e_sp[d_ep] <= d_sp; e_k[d_ep] <= d_k;
                e_rnd[d_ep] <= d_rnd;
                if (d_sp < SMIN || d_sp > SMAX) flt <= 1'b1;
            end
            if (dp_v && pfault_n) flt <= 1'b1;
            if ((NATIVE_AFFINE!=0 ? (g_q && e_pbad[rep_now]) : f_pos) || (NATIVE_AFFINE!=0 && |go_bad_bits)) flt <= 1'b1;
            if (|lqbp) flt <= 1'b1;
            if (miss) flt <= 1'b1;                                          // a leaf did not answer its read
            // the go: consume the oldest filled epoch
            if (g_q) begin
                if (busy && last) st[(MUT == 4) ? ~rep : rep] <= 2'd0;     // back to back: the previous op's last edge
                if (NATIVE_AFFINE==0 && (!go_ok || (busy && !last))) flt <= 1'b1;
                else begin
                    st[ep_rd] <= 2'd2;
                    rep <= (MUT == 4) ? ~ep_rd : ep_rd;
                    ep_rd <= ~ep_rd;
                    busy <= 1'b1; ph <= 3'd1;
                    rnd_left <= b_tiles - 1'b1; k_i <= {NW{1'b0}}; k_last <= b_k - 1'b1; kx <= {AW{1'b0}};
                    rxcs <= b_xcs[XCW-1:0]; rxks <= b_xks[XCW-1:0];
                end
            end else if (busy) begin
                ph <= ph + 1'b1;
                if (ph == IL - 1) begin
                    if (k_i == k_last) begin
                        k_i <= {NW{1'b0}}; kx <= {AW{1'b0}};
                        if (rnd_left == 0) begin busy <= 1'b0; st[(MUT == 4) ? ~rep : rep] <= 2'd0; end
                        else rnd_left <= rnd_left - 1'b1;
                    end else begin
                        k_i <= k_i + 1'b1; kx <= kx + rxks;
                    end
                end
            end
        end
    (* keep *) reg [CW-1:0] n_q, s_q;
    always @(posedge ck) begin
        n_q <= {tn, xn, ib_c2, g_dx};
        s_q <= {ts, xs, ib_c2, g_dx};
    end
    assign n_d = n_q;
    assign s_d = s_q;
endmodule

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xcst: corridor station with the tile's x hold.  a_d / b_d = {tag, xl, ib, go} (CW), tap_d = {xl, ib, go}
// (the tile's E pins, 508 b at NW 18).  cap takes the line tagged with this station's index; hold <= cap every IL
// edges, the first XOFF edges after a go passed (the tile's x of tuple n is on its pins during its tuple n edges).
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xcst #(
    parameter integer AW   = 24,
    parameter integer NW   = 18,
    parameter integer IL   = 8,
    parameter integer XOFF = 3
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire          a_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    input  wire          b_r,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d
);
    // (no tap ready: the tile takes its x / ib / go in lockstep and never back-pressures; r3 drops the port the die
    //  tied to 1 -- DIE_BUS_AUDIT row 10)
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer CW  = 1 + IBW + 128 + 8;
    (* keep *) reg [CW-1:0] b_q;
    always @(posedge ck) b_q <= a_d;
    assign b_d = b_q;
    (* keep *) reg [IBW:0] t_q;
    always @(posedge ck) t_q <= a_d[IBW:0];
    reg [2:0]  sx;
    always @(posedge ck) sx <= sidx;
    // The corridor face is captured by b_q before tag decoding and the
    // station-select mux.  cap therefore has only register-to-register logic;
    // the fixed hold deadline is unchanged (the TDM line leads it).
    wire [127:0] xl  = b_q[1 + IBW +: 128];
    wire [7:0]   tag = b_q[1 + IBW + 128 +: 8];
    reg  [63:0]  cap;
    (* keep *) reg [63:0] hold;
    reg  [3:0]   cnt;
    reg          run;
    always @(posedge ck) begin
        if (tag[3] && tag[2:0] == sx) cap <= xl[63:0];
        else if (tag[7] && tag[6:4] == sx) cap <= xl[127:64];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin cnt <= 4'd0; run <= 1'b0; end
        // GO is captured by the existing corridor boundary b_q before it
        // fans into the run/count logic. Compensate that edge in the initial
        // countdown; the tuple's fixed hold deadline remains unchanged.
        else if (b_q[0]) begin cnt <= XOFF - 2; run <= 1'b1; end
        else if (run) cnt <= (cnt == 0) ? IL - 1 : cnt - 1'b1;
    // Original cap captured the raw face one edge before the hold deadline.
    // b_q now captures that face; forward its selected line at the same fixed
    // deadline, or retain cap when this edge belongs to another station.
    wire tag_a = tag[3] && tag[2:0] == sx;
    wire tag_b = tag[7] && tag[6:4] == sx;
    always @(posedge ck) if (run && cnt == 0)
        hold <= tag_a ? xl[63:0] : tag_b ? xl[127:64] : cap;
    genvar i;
    wire [127:0] xo;
    generate for (i = 0; i < 4; i = i + 1) begin : g_x
        assign xo[32*i +: 32] = {hold[16*i +: 16], 16'h0000};
    end endgenerate
    assign tap_d = {xo, t_q};
    reg br_q, ar_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin br_q <= 1'b0; ar_q <= 1'b0; end
        else begin br_q <= b_r; ar_q <= br_q; end
    assign a_r = ar_q;
endmodule

// Replicated-select mux tree: level lv (0 = the 2^(LN-1) muxes next to the data) takes nrep(lv) copies of select bit
// lv; mux k of the level uses copy k * nrep / nodes, so no select copy drives more than ~256 mux bits.
module ot_qfd_xs_mux_rep #(parameter integer W = 16, parameter integer LN = 9, parameter integer SW = 64) (
    input  wire [(W << LN)-1:0] d,
    input  wire [SW-1:0]        s,      // SW = ot_qfd_xs_mux_rep_sw(W, LN), checked below
    output wire [W-1:0]         q
);
    function automatic integer ot_qfd_xs_nrep(input integer w, input integer ln, input integer lv);
        integer loads;
        begin
            loads = w << (ln - 1 - lv);
            ot_qfd_xs_nrep = (loads + 255) / 256;
            if (ot_qfd_xs_nrep < 1) ot_qfd_xs_nrep = 1;
        end
    endfunction
    function automatic integer ot_qfd_xs_mux_rep_sw(input integer w, input integer ln);
        integer lv;
        begin
            ot_qfd_xs_mux_rep_sw = 0;
            for (lv = 0; lv < ln; lv = lv + 1) ot_qfd_xs_mux_rep_sw = ot_qfd_xs_mux_rep_sw + ot_qfd_xs_nrep(w, ln, lv);
        end
    endfunction
    function automatic integer ot_qfd_xs_soff(input integer w, input integer ln, input integer lv);
        integer l;
        begin
            ot_qfd_xs_soff = 0;
            for (l = 0; l < lv; l = l + 1) ot_qfd_xs_soff = ot_qfd_xs_soff + ot_qfd_xs_nrep(w, ln, l);
        end
    endfunction
    genvar lv, k;
    generate for (lv = 0; lv <= LN; lv = lv + 1) begin : g_l
        wire [(W << (LN - lv))-1:0] n;
        if (lv == 0) begin : g_in
            assign n = d;
        end else begin : g_mx
            localparam integer NODES = 1 << (LN - lv);
            localparam integer NR = ot_qfd_xs_nrep(W, LN, lv - 1);
            localparam integer OFF = ot_qfd_xs_soff(W, LN, lv - 1);
            for (k = 0; k < NODES; k = k + 1) begin : g_k
                assign n[W*k +: W] = s[OFF + (k * NR) / NODES] ? g_l[lv-1].n[W*(2*k+1) +: W] : g_l[lv-1].n[W*(2*k) +: W];
            end
        end
    end endgenerate
    assign q = g_l[LN].n;
endmodule

// Explicit 2^LN : 1 mux tree of W-bit words (no runtime-indexed select for synthesis to re-share).
module ot_qfd_xs_mux #(parameter integer W = 16, parameter integer LN = 9) (
    input  wire [(W << LN)-1:0] d,
    input  wire [LN-1:0]        s,
    output wire [W-1:0]         q
);
    genvar lv, k;
    generate for (lv = 0; lv <= LN; lv = lv + 1) begin : g_l
        wire [(W << (LN - lv))-1:0] n;
        if (lv == 0) begin : g_in
            assign n = d;
        end else begin : g_mx
            for (k = 0; k < (1 << (LN - lv)); k = k + 1) begin : g_k
                assign n[W*k +: W] = s[lv-1] ? g_l[lv-1].n[W*(2*k+1) +: W] : g_l[lv-1].n[W*(2*k) +: W];
            end
        end
    end endgenerate
    assign q = g_l[LN].n;
endmodule

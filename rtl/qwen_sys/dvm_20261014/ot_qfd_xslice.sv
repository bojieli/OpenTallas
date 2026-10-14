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
//                                           head-row fill word (descriptor + one aligned data beat an edge).
//   ot_qfd_xhead     (qfd_xhead_e/_w, 48)   column head: head-row station for {go, ib} AND the fill word, column slice
//                                           control (epochs, the 16 tile windows, leaf write control, TDM read
//                                           sequencer) and the N / S corridor launch {go, ib, xl, tag}.
//   ot_qfd_xs_leaf   (qfd_xs_leaf, 384)     2 tiles x 2 epochs x 2 aligned beats x 64 BF16 + per-element valid.
//   ot_qfd_xcst      (qfd_xcst_n/_s, 768)   corridor station: onward word, tap {go, ib, xl} to the tile, a capture
//                                           register for its own TDM slot and the tuple hold register that drives xl.
//
// EXACTNESS BY CONSTRUCTION.  (1) Operand: the tile multiplies RNE16(x) when the op rounds (ot_qwen_w12_matvec.sv
// g_s3xd: (x + 0x7FFF + x[16]) & 0xFFFF0000) and x[31:16] when it does not; the tap stores exactly that 16-bit value
// hi16 and the tile receives {hi16, 16'h0}: its own re-round adds <= 0x8000 to a zero low half (no carry), so the
// multiplier operand is bit-identical.  (2) Addressing: the slice serves element xbase + c*xcs + k*xks for chunk
// c = (TG*t + i) mod S of tile t (the array's x network, ot_qwen_me_array_w12), j-invariant (xjs 0: the line is held
// for the IL = 8 edges of a tuple); every read position is checked inside the tile's two-beat window and every element
// read must have been written in this epoch (per-element valid): a violation is a sticky FAULT, never a stale value.
// (3) Ordering: fill and go travel the same in-order head row, the go reaches a column after every fill beat issued
// before it; the descriptor of the consumer op is compared with the go's own fields (xbase, xcs, xks, split, k, round)
// and an op without a matching filled epoch faults.
//
// Fill word (head row, FW bits, LSB first in the concatenation below):
//   desc:  dv, dep, dxb[AW], dxcs[XCW], dxks[XCW], dsp[4], dk[NW], drnd           (DESC = 2 + AW + 2*XCW + 4 + NW + 1)
//   data:  fv, fep, fb[AW-6] (aligned 64-element beat), foff[6] (write start mod 64), fm[64] (per position), fd[64*16]
// A data beat is the write ROTATED so that position p holds element 64*fb + p for p >= foff and element
// 64*(fb + 1) + p for p < foff: any 64-element write (any alignment) is ONE beat.
// =====================================================================================================================

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xs_tap: the x-fill tap at the VM write face (one instance).
//   xpf_*  arm descriptor (sequencer, issued before the consumer's producer writes): epochs alternate.
//   sw_*   SU lane write: element sw_a + l for lane l (stride 1), lanes with sw_m[l].
//   aw_*   attention-return write: element aw_a + l, l < 16.
// Pipeline: descriptor E1 pin registers, E2 range products, E3 range armed + DESC out; writes E1 pin registers, E2
// merged / classified / rounded / rotated data out.  SEQUENCER RULE: the first write of an armed range comes >= 3 edges
// after its XPF (the descriptor then leads the range's first data beat by >= 2 edges on the head row, the time an
// xhead needs to compute the tile windows).
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xs_tap #(
    parameter integer AW  = 24,
    parameter integer NW  = 18,
    parameter integer XCW = 12,
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
    output wire [2+AW+2*XCW+4+NW+1 + 2+(AW-6)+6+64+1024 - 1:0] fo,
    output reg               fault
);
    localparam integer BW = AW - 6;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;
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
        q_s1 <= ({{(AW-XCW){1'b0}}, p_xcs} << p_sp) - {{(AW-XCW){1'b0}}, p_xcs};
        q_s2 <= (p_k - 1'b1) * p_xks;
    end
    // ---- E3: arm (epochs alternate) + descriptor out ----
    reg              ep_nx;
    reg  [1:0]       arm;
    reg  [AW-1:0]    lo [0:1];
    reg  [AW:0]      hi [0:1];
    reg  [1:0]       rnd;
    reg  [DESC-1:0]  d_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ep_nx <= 1'b0; arm <= 2'b00; d_o <= {DESC{1'b0}}; end
        else begin
            d_o[0] <= 1'b0;
            if (q_v) begin
                // XPF transfers write ownership to the next image.  The previous
                // epoch remains in the leaves for reads, but must no longer
                // classify producer writes: consecutive ops may reuse addresses.
                // MUT 5 restores the stale-owner bug as an observable control.
                if (MUT == 5) arm[ep_nx] <= 1'b1;
                else arm <= ep_nx ? 2'b10 : 2'b01;
                lo[ep_nx] <= q_xb;
                hi[ep_nx] <= {1'b0, q_xb} + q_s1 + q_s2 + 1'b1;
                rnd[ep_nx] <= q_rnd;
                ep_nx <= ~ep_nx;
                d_o <= {q_rnd, q_k, q_sp, q_xks, q_xcs, q_xb, ep_nx, 1'b1};
            end
        end
    // ---- writes: merge (SU first, attention return queued behind it), classify, round, rotate -> E2 out ----
    reg  [1:0]       kq_n;
    reg  [AW-1:0]    kq_a [0:1];
    reg  [15:0]      kq_m [0:1];
    reg  [16*32-1:0] kq_d [0:1];
    reg              q_ovf;
    wire             use_q = !s1_v && (kq_n != 0);
    wire             use_a = !s1_v && (kq_n == 0) && a1_v;
    wire             push  = a1_v && !use_a;
    wire             w_v   = s1_v | use_q | use_a;
    wire [AW-1:0]    w_a   = s1_v ? s1_a : use_q ? kq_a[0] : a1_a;
    wire [63:0]      w_m   = s1_v ? s1_m : use_q ? {48'd0, kq_m[0]} : {48'd0, a1_m};
    wire [64*32-1:0] w_d   = s1_v ? s1_d : use_q ? {1536'd0, kq_d[0]} : {1536'd0, a1_d};
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
    wire [AW:0] wa_lo = {1'b0, w_a};
    wire [AW:0] wa_hi = {1'b0, w_a} + 7'd64;
    wire [1:0]  hit;
    assign hit[0] = arm[0] && (wa_lo < hi[0]) && (wa_hi > {1'b0, lo[0]});
    assign hit[1] = arm[1] && (wa_lo < hi[1]) && (wa_hi > {1'b0, lo[1]});
    wire        hep = hit[1];
    wire        hrd = rnd[hep];
    wire [5:0]  off = w_a[5:0];
    // round every lane to the consumer operand, then rotate lanes so that lane l lands at position (off + l) mod 64
    reg  [1023:0] h_d;
    integer l;
    reg [31:0] xe;
    reg        cy;
    always @* begin
        for (l = 0; l < 64; l = l + 1) begin
            xe = w_d[32*l +: 32];
            cy = (xe[15:0] > 16'h8000) || (xe[15:0] == 16'h8000 && xe[16]);
            h_d[16*l +: 16] = (hrd && MUT != 1) ? (xe[31:16] + {15'd0, cy}) : xe[31:16];
        end
    end
    wire [1023:0] rd_s [0:6];
    wire [63:0]   rm_s [0:6];
    assign rd_s[0] = h_d;
    assign rm_s[0] = w_m;
    genvar rs;
    generate for (rs = 0; rs < 6; rs = rs + 1) begin : g_rot
        localparam integer K = 1 << rs;
        assign rd_s[rs+1] = off[rs] ? {rd_s[rs][1023-16*K:0], rd_s[rs][1023 -: 16*K]} : rd_s[rs];
        assign rm_s[rs+1] = off[rs] ? {rm_s[rs][63-K:0], rm_s[rs][63 -: K]} : rm_s[rs];
    end endgenerate
    wire [63:0]   r_m = rm_s[6];
    wire [1023:0] r_d = rd_s[6];
    reg              e5_v, e5_ep;
    reg [BW-1:0]     e5_b;
    reg [5:0]        e5_off;
    reg [63:0]       e5_m;
    reg [1023:0]     e5_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin e5_v <= 1'b0; fault <= 1'b0; end
        else begin
            e5_v <= w_v && (hit != 2'b00);
            if (q_ovf || (w_v && hit == 2'b11)) fault <= 1'b1;
        end
    always @(posedge clk) begin
        e5_ep <= hep; e5_b <= w_a[AW-1:6]; e5_off <= off; e5_m <= r_m; e5_d <= r_d;
    end
    assign fo = {e5_d, e5_m, e5_off, e5_b, e5_ep, e5_v, d_o};
endmodule

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xs_leaf: x slice leaf, NTL = 2 tiles.  WRITE CHAIN: the column's leaves of one corridor half form a chain from
// the head (cut analysis, el1014-qwen-dvm-build.log: a parallel fan of the 1,130-bit write word to 4 leaves is 1.4x the
// column-gap tracks at 0.55; the chain carries ONE word per cut): the write word's pin registers are also the leaf's
// write outputs wo_* (no extra flop), w_ctl carries NCH leaves' controls, the leaf takes bits [7:0] and forwards the
// rest shifted down.  A leaf at chain depth d sees a write d edges after the first.  Reads are direct (one bus per leaf).
// Every input is a pin register, the answer a pin register: a read
// presented at edge R answers at edge R + 2 (q at the pins in the cycle after R + 2); a write presented at edge W is
// readable by a read presented at edge >= W + 1 (both pass one pin register; the read of a same-edge write sees the
// old value and its valid bit, never a torn word).
//   w_ctl per tile {en_lo, s_lo, en_hi, s_hi}: positions p >= w_off go to beat slot s_hi when en_hi, positions
//   p < w_off to slot s_lo when en_lo (ot_qfd_xhead computes them from the tile window).
//   c_v / c_ep: clear the epoch's valid bits (epoch claimed by a new descriptor).
//   r_p[i] (7 b): element i of the line at position r_p[i] of the tile's 128-element window (slot r_p[i][6]).
// --------------------------------------------------------------------------------------------------------------------
module ot_qfd_xs_leaf #(
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
    input  wire [NCH*8-1:0] w_ctl,
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [NCH*8-1:0] wo_ctl,
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
    // pin registers
    reg          wv, wep, cv, cep, rv, rt, rep;
    reg [5:0]    woff;
    reg [63:0]   wm;
    reg [1023:0] wd;
    reg [NCH*8-1:0] wctl;
    reg [27:0]   rp;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wv <= 1'b0; cv <= 1'b0; rv <= 1'b0; end
        else begin wv <= w_v; cv <= c_v; rv <= r_v; end
    always @(posedge clk) begin
        wep <= w_ep; woff <= w_off; wm <= w_m; wd <= w_d; wctl <= w_ctl; cep <= c_ep; rt <= r_t; rep <= r_ep; rp <= r_p;
    end
    assign wo_v = wv; assign wo_ep = wep; assign wo_off = woff; assign wo_m = wm; assign wo_d = wd;
    assign wo_ctl = {8'd0, wctl[NCH*8-1:8]};
    assign co_v = cv; assign co_ep = cep;
    // storage: entry e = {tile, epoch, slot, position} (9 bits), one 16-bit register + one valid flop each
    wire [8191:0] mem_f;
    wire [511:0]  val_f;
    wire [63:0]   thermo;
    genvar ge, gp;
    generate for (gp = 0; gp < 64; gp = gp + 1) begin : g_th
        assign thermo[gp] = (gp >= woff);
    end endgenerate
    generate for (ge = 0; ge < 512; ge = ge + 1) begin : g_e
        localparam integer ET = ge >> 8, EE = (ge >> 7) & 1, ES = (ge >> 6) & 1, EP = ge & 63;
        wire hi_p = thermo[EP];
        wire en   = hi_p ? wctl[4*ET + 1] : wctl[4*ET + 3];
        wire sl   = hi_p ? wctl[4*ET + 0] : wctl[4*ET + 2];
        wire we   = wv && (wep == EE) && en && (sl == ES) && wm[EP];
        reg [15:0] m;
        reg        v;
        always @(posedge clk) if (we) m <= wd[16*EP +: 16];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) v <= 1'b0;
            else if (cv && cep == EE) v <= 1'b0;
            else if (we) v <= 1'b1;
        assign mem_f[16*ge +: 16] = m;
        assign val_f[ge] = v;
    end endgenerate
    // read: four elements of one tile's window through explicit 512:1 trees
    wire [63:0] qq;
    wire [3:0]  vv;
    genvar gi;
    generate for (gi = 0; gi < 4; gi = gi + 1) begin : g_rd
        wire [8:0] ix = {(MUT == 2) ? 1'b0 : rt, rep, rp[7*gi +: 7]};
        ot_qfd_xs_mux #(.W(17), .LN(9)) u_m (.d(interleave(mem_f, val_f)), .s(ix), .q({vv[gi], qq[16*gi +: 16]}));
    end endgenerate
    wire bad = ~&vv;
    function automatic [512*17-1:0] interleave(input [8191:0] m, input [511:0] v);
        integer k;
        begin
            for (k = 0; k < 512; k = k + 1) interleave[17*k +: 17] = {v[k], m[16*k +: 16]};
        end
    endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_v <= 1'b0; q_bad <= 1'b0; end
        else begin q_v <= rv; q_bad <= rv && bad; end
    always @(posedge clk) q <= qq;
endmodule

// --------------------------------------------------------------------------------------------------------------------
// ot_qfd_xhead: column head with the column's x slice control.
//   Head-row word a_d / b_d (HW bits) = {fill (FW), ib (IBW), go}: b_d is the onward copy (one kept flop each).
//   Corridor words n_d / s_d (CW bits) = {tag (8), xl (128), ib (IBW), go}: go / ib are the head-row go / ib DX + 1
//   edges after they entered this head (DX extra edges against a plain column head; the slice reads of a tuple run
//   ahead of the tiles by construction), xl = two quad lines (2 x 64 b BF16) of the corridor's tiles, tag =
//   {vB, sB[2:0], vA, sA[2:0]} the station index each line is for.
//   TDM: a corridor has NH tiles (station index s = 0 .. NH-1, s = 0 next to the head); tuple n of the op is sent on
//   NH / 2 consecutive edges, edge e carrying stations e (line A) and e + NH/2 (line B): leaves e/2 and e/2 + NH/4
//   (distinct leaves, one read port each).
//   Rows: tile id tid0 + r, r = 0 .. 2*NH-1; rows 0 .. NH-1 are the N corridor (station r), NH .. 2NH-1 the S corridor
//   (station r - NH); leaf j holds rows 2j, 2j+1.
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
    parameter integer DX   = 8,          // four-edge fill lead + four-edge read-to-corridor launch
    parameter integer FILL_LEAD = 4,     // includes the tap's two-entry attention-write queue
    parameter integer MUT  = 0           // 3: the TDM sends each line to the wrong station (wrong line);
                                         // 4: the reads use the OTHER epoch (stale buffer)   -- both must FAIL
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [15:0]   tid0,
    input  wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] a_d,
    output wire          a_r,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] b_d,
    input  wire          b_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] n_d,
    input  wire          n_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] s_d,
    input  wire          s_r,
    // leaves (NH: NH/2 in the N chain = rows 0 .. NH-1, NH/2 in the S chain): one write word per chain, its
    // ctl field the chain's NH/2 leaves (leaf j of the chain at bits 8j); the two chains carry the same data
    output reg  [1:0]    lw_v,
    output reg  [1:0]    lw_ep,
    output reg  [2*6-1:0] lw_off,
    output reg  [2*64-1:0] lw_m,
    output reg  [2*1024-1:0] lw_d,
    output reg  [NH*8-1:0] lw_ctl,
    output reg  [1:0]    lc_v,
    output reg  [1:0]    lc_ep,
    output reg  [NH-1:0] lr_v,
    output reg  [NH-1:0] lr_t,
    output reg  [NH-1:0] lr_ep,
    output reg  [NH*28-1:0] lr_p,
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
    localparam integer NL   = NH;                // leaves
    localparam integer LQ   = $clog2(1 << (SMAX - $clog2(TG)));   // bits of a quad index (S / TG <= 2^(SMAX - log2 TG))

    // ---- head row: onward copy, ready (as ot_qwen_die_station) ----
    (* keep *) reg [HW-1:0] b_q;
    always @(posedge ck) b_q <= a_d;
    assign b_d = b_q;
    reg br_q, nr_q, sr_q, ar_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin br_q <= 1'b0; nr_q <= 1'b0; sr_q <= 1'b0; ar_q <= 1'b0; end
        else begin br_q <= b_r; nr_q <= n_r; sr_q <= s_r; ar_q <= br_q & nr_q & sr_q; end
    assign a_r = ar_q;

    // ---- input pin register of the local copy ----
    reg              g_pin;
    reg  [IBW-1:0]   ib_pin;
    wire             g_q;
    wire [IBW-1:0]   ib_q;
    reg  [FW-1:0]    f_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) g_pin <= 1'b0; else g_pin <= a_d[0];
    always @(posedge ck) begin ib_pin <= a_d[1 +: IBW]; f_q <= a_d[1 + IBW +: FW]; end
    // Go travels directly along the head row; the last attention beat can still
    // be queued behind an SU beat in the tap. Give that queue and the far leaf's
    // write registers time to drain before launching reads. Instruction and
    // reads move together; fill and all missing-element fault checks stay live.
    ot_hdc_delay #(.W(1), .D(FILL_LEAD), .RESET(1)) u_fill_go (.clk(ck), .rst_n(rst_n), .d(g_pin), .q(g_q));
    ot_hdc_delay #(.W(IBW), .D(FILL_LEAD)) u_fill_ib (.clk(ck), .rst_n(rst_n), .d(ib_pin), .q(ib_q));

    // ---- go / ib to the corridors: DX more edges, then one kept output flop per corridor ----
    wire              g_dx;
    wire [IBW-1:0]    ib_dx;
    ot_hdc_delay #(.W(1), .D(DX-FILL_LEAD), .RESET(1)) u_gdx (.clk(ck), .rst_n(rst_n), .d(g_q), .q(g_dx));
    ot_hdc_delay #(.W(IBW), .D(DX-FILL_LEAD)) u_idx (.clk(ck), .rst_n(rst_n), .d(ib_q), .q(ib_dx));

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
    // tile windows: beat W and offset of the tile's first element, per epoch and row
    reg  [BW-1:0]     wb  [0:1][0:NR-1];
    reg  [5:0]        wo  [0:1][0:NR-1];
    // descriptor pipeline: products (stage 1), windows (stage 2)
    reg               dp_v, dp_ep;
    reg  [AW-1:0]     dp_xb;
    reg  [AW-1:0]     dp_pr [0:NR-1];
    integer r, e, i;
    reg  [SMAX:0]     qq;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) dp_v <= 1'b0; else dp_v <= d_v;
    always @(posedge ck) begin
        dp_ep <= d_ep; dp_xb <= d_xb;
        for (r = 0; r < NR; r = r + 1) begin
            // quad q = (tile id) mod (S / TG); first chunk TG * q; product TG * q * xcs
            qq = (tid0 + r) & ((({{SMAX{1'b0}}, 1'b1}) << (d_sp - $clog2(TG))) - 1'b1);
            dp_pr[r] <= (qq * TG) * d_xcs;
        end
    end
    reg [AW-1:0] emin;
    always @(posedge ck)
        if (dp_v) for (r = 0; r < NR; r = r + 1) begin
            emin = dp_xb + dp_pr[r];
            wb[dp_ep][r] <= emin[AW-1:6];
            wo[dp_ep][r] <= emin[5:0];
        end

    // ---- data beat -> leaf write control (one edge), to the leaf pins ----
    reg  [BW:0] dd;
    reg  [NH*8-1:0] ctl;
    always @* begin
        ctl = {(NH*8){1'b0}};
        for (r = 0; r < NR; r = r + 1) begin
            dd = {1'b0, fb} - {1'b0, wb[fep][r]};
            // {en_lo, s_lo, en_hi, s_hi} at bit 4*(r & 1) of leaf r >> 1
            ctl[8*(r >> 1) + 4*(r & 1) +: 4] = {
                (dd == 0) || (dd == {(BW+1){1'b1}}),     // en_lo: p < off lands in beat fb + 1 = W (d = -1) or W + 1 (d = 0)
                (dd == 0),                                // s_lo
                (dd == 0) || (dd == 1),                   // en_hi: p >= off lands in beat fb = W (d = 0) or W + 1 (d = 1)
                (dd == 1)};                               // s_hi
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
        lw_ep <= {2{fep}}; lw_off <= {2{foff}}; lw_m <= {2{fm}}; lw_d <= {2{fd}}; lw_ctl <= ctl; lc_ep <= {2{d_ep}};
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
    reg  [AW:0]   pe;
    reg  [NH*28-1:0] rp;
    reg  [NH-1:0] rv;
    reg  [NH-1:0] rt;
    // the read of TDM edge 0 of tuple 0 leaves on the edge after the go's pin flop (positions from the descriptor)
    wire          rd_now = g_q || busy;
    wire [2:0]    ph_now = g_q ? 3'd0 : ph;
    wire          rep_now = g_q ? ((MUT == 4) ? ~ep_rd : ep_rd) : rep;
    wire [XCW-1:0] xcs_now = g_q ? e_xcs[ep_rd] : rxcs;
    wire [AW-1:0] kx_now = g_q ? {AW{1'b0}} : kx;
    wire          last = busy && (ph == IL - 1) && (k_i == k_last) && (rnd_left == 0);
    integer s, ln;
    always @* begin
        rp = {(NH*28){1'b0}}; rv = {NH{1'b0}}; rt = {NH{1'b0}}; f_pos = 1'b0;
        if (rd_now && ph_now < NE) begin
            for (s = 0; s < 4; s = s + 1) begin
                // s: 0 N line A, 1 N line B, 2 S line A, 3 S line B
                r = ((s >= 2) ? NH : 0) + ph_now + ((s & 1) ? NE : 0);
                ln = r >> 1;
                rv[ln] = 1'b1;
                rt[ln] = r & 1;
                for (i = 0; i < 4; i = i + 1) begin
                    pe = {1'b0, {(AW-6){1'b0}}, wo[rep_now][r]} + i * xcs_now + kx_now;
                    if (pe >= 128) f_pos = 1'b1;
                    rp[28*ln + 7*i +: 7] = pe[6:0];
                end
            end
        end
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            st[0] <= 2'd0; st[1] <= 2'd0; ep_rd <= 1'b0; busy <= 1'b0; fault <= 1'b0; lr_v <= {NH{1'b0}};
            ph <= 3'd0; rep <= 1'b0;
        end else begin
            lr_v <= rv;
            // descriptor: claim the epoch
            if (d_v) begin
                if (st[d_ep] != 2'd0) fault <= 1'b1;
                st[d_ep] <= 2'd1;
                e_xb[d_ep] <= d_xb; e_xcs[d_ep] <= d_xcs; e_xks[d_ep] <= d_xks; e_sp[d_ep] <= d_sp; e_k[d_ep] <= d_k;
                e_rnd[d_ep] <= d_rnd;
                if (d_sp < SMIN || d_sp > SMAX) fault <= 1'b1;
            end
            if (f_pos) fault <= 1'b1;
            if (|lq_bad) fault <= 1'b1;
            // the go: consume the oldest filled epoch
            if (g_q) begin
                if (busy && last) st[(MUT == 4) ? ~rep : rep] <= 2'd0;     // back to back: the previous op's last edge
                if (!go_ok || (busy && !last)) fault <= 1'b1;
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
    always @(posedge ck) begin lr_t <= rt; lr_ep <= {NH{rep_now}}; lr_p <= rp; end

    // ---- answers -> corridor launch (the leaf q pins feed the corridor's output flops through one mux) ----
    // the answer of a read issued at TDM edge e arrives 3 edges later: carry the edge's station indices along
    wire [2:0] phd;
    wire       vd;
    ot_hdc_delay #(.W(3), .D(3)) u_phd (.clk(ck), .rst_n(rst_n), .d(ph_now), .q(phd));
    ot_hdc_delay #(.W(1), .D(3), .RESET(1)) u_vd (.clk(ck), .rst_n(rst_n), .d(rd_now && ph_now < NE), .q(vd));
    reg [127:0] xn, xs;
    reg [7:0]   tn, ts;
    reg [2:0]   sa, sb;
    always @* begin
        xn = 128'd0; xs = 128'd0; tn = 8'd0; ts = 8'd0;
        sa = (MUT == 3) ? (phd + 1'b1) & (NH - 1) : phd;
        sb = (MUT == 3) ? (phd + NE + 1'b1) & (NH - 1) : phd + NE;
        if (vd) begin
            xn = {lq[64*((phd + NE) >> 1) +: 64], lq[64*(phd >> 1) +: 64]};
            xs = {lq[64*(NE + ((phd + NE) >> 1)) +: 64], lq[64*(NE + (phd >> 1)) +: 64]};
            tn = {1'b1, sb, 1'b1, sa};
            ts = {1'b1, sb, 1'b1, sa};
        end
    end
    (* keep *) reg [CW-1:0] n_q, s_q;
    always @(posedge ck) begin
        n_q <= {tn, xn, ib_dx, g_dx};
        s_q <= {ts, xs, ib_dx, g_dx};
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
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    input  wire          tap_r
);
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer CW  = 1 + IBW + 128 + 8;
    (* keep *) reg [CW-1:0] b_q;
    always @(posedge ck) b_q <= a_d;
    assign b_d = b_q;
    (* keep *) reg [IBW:0] t_q;
    always @(posedge ck) t_q <= a_d[IBW:0];
    reg [2:0]  sx;
    always @(posedge ck) sx <= sidx;
    wire [127:0] xl  = a_d[1 + IBW +: 128];
    wire [7:0]   tag = a_d[1 + IBW + 128 +: 8];
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
        else if (a_d[0]) begin cnt <= XOFF - 1; run <= 1'b1; end
        else if (run) cnt <= (cnt == 0) ? IL - 1 : cnt - 1'b1;
    always @(posedge ck) if (run && cnt == 0) hold <= cap;
    genvar i;
    wire [127:0] xo;
    generate for (i = 0; i < 4; i = i + 1) begin : g_x
        assign xo[32*i +: 32] = {hold[16*i +: 16], 16'h0000};
    end endgenerate
    assign tap_d = {xo, t_q};
    reg br_q, tr_q, ar_q;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin br_q <= 1'b0; tr_q <= 1'b0; ar_q <= 1'b0; end
        else begin br_q <= b_r; tr_q <= tap_r; ar_q <= br_q & tr_q; end
    assign a_r = ar_q;
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

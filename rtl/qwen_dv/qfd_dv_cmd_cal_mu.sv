`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_cmd_cal_mu -- multi-user successor of qfd_dv_cmd_cal (MU-QWEN-SEQ, 2026-10-18).  NU = 1 (default) is
// qfd_dv_cmd_cal: same ports plus the new start_user / cmd_user / done_user / running_u / fault_code, every original
// output identical on every edge (lockstep bench rtl/test/mu_qwen_seq/, vs the unmodified module).  The die keeps
// instantiating qfd_dv_cmd_cal until a die lane adopts this module with NU > 1.
//
// WHY.  On the DV compute die (dv2f12/dv2f14) qfd_dv_cmd_cal is the run side of the tensor-group sequencer (it replaced
// the issue side of qfd_seq_su_static): every SU / STN / ROOT / PORTS / XC command of a stage is an image entry played at
// S + T_k from the stage start S.  It plays ONE segment at a time: a start while a segment plays is a fault.  A decode
// layer's segment spans most of the 6,886-cycle layer period (its collectives and the KV-die attention return land late
// in it), so the 4-slot calendar (users at shifts 0 / 1,722 / 3,443 / 5,165) needs up to 4 segments playing at once.
//
// MECHANISM (NU > 1).  NU playheads share the image store, its one read port and the one cmd register.  A start carries
// start_user; playhead start_user starts the stage's segment exactly as the single calendar does (same T_k, same fetch
// pipeline, same faults), while the other playheads keep playing untouched on that edge.  Each playhead owns the user
// context {segment, entry FIFO (8), issue time, fetch state}; the user index travels with every issued command
// (cmd_user, registered with cmd).  BOOT (seal) plays on playhead 0.
//   Store read port: lowest-index playhead that can read takes the edge (playhead 0 = the latency user's slot is never
//   delayed, so its fetch -- and therefore its whole timeline -- is the NU = 1 timeline bit for bit).  A filler loses at
//   most NU - 1 edges of prefetch: compiler rule T_0 >= 4 + (NU - 1) for a filler's first entry (late = FAULT).
//   Per-user relocation of the issued word (u = the playhead; u = 0 adds 0, so user 0's words are the image's words):
//     PORTS (kind 4): ar_base [27:4], dd_base [51:28], em_base [77:54] += u * UVM_STRIDE   (AR / attention / embedding
//                     landing regions per user: the per-user FP32 residual + staging region of the study)
//     STN   (kind 2) with dst bit 0 (VM): dbase [49:26] += u * UVM_STRIDE
//     SU    (kind 1): pidx [12:4] += u * PIDX_STRIDE (per-user SU instruction copies in the slice PROG store)
//     XC    (kind 0, sub 0): the collective tag (cmd [54:23]) carries the user at tag bit UTAG_LSB (cmd [23 + UTAG_LSB
//                     +: UB]); the image leaves those bits 0.  The engine's cross-die tag compare then separates users.
//   A carry out of a relocated field FAULTS.  UVM_STRIDE / PIDX_STRIDE 0 = no relocation (the compiler then writes
//   per-user absolute fields itself, which needs per-user images and is not possible with one shared image).
// FAULTS, NEVER STALLS (static schedule): everything that faults in qfd_dv_cmd_cal, plus (fault_code, sticky, cleared
// like `fault` when a new image opens):
//   [0] a start for a user whose playhead is still playing (or a start on the boot edge / past LAST_STAGE / unsealed)
//   [1] two playheads issue a command on the same edge (cmd collision; the lower user's word is issued)
//   [2] a playhead's entry is late (its prefetch lost the read port too long, or T_0 < 4 + arbitration)
//   [3] relocation carry, or an XC entry whose user tag bits are not 0, or two segment ends on one edge
//   [4] image fault (load order / seal / tcount overflow / zero delta / load while any playhead plays)
//   [5] store read port double-booked (two playheads' reads on one edge: only after a faulted start)
// MUT (bench only): 1..3 as qfd_dv_cmd_cal; 11 = relocation / tag / cmd_user from the wrong user ((u + 1) % NU);
//   12 = the per-user base dropped (no relocation); 13 = the old one-in-flight rule (a start while ANY playhead plays
//   faults and is refused); 14 = a start for a playing user is not faulted (silent restart); 15 = a start freezes every
//   playhead for that edge (the single calendar's global go gating), which shifts the other users' timelines;
//   16 = UFOLD user fields left at the image's 0 (the slices' per-user LM-head argmax then merges every user into user 0).
// UFOLD (MU-ADOPT-CTLM 10-19, opt-in, NU > 1 and UB <= 2 only): the issued word also carries its user in the two spare
//   fields the R4 per-user LM-head argmax (rtl/qwen_dv/mu/qfd_dv_amax_mu.sv) reads: STN (kind 2) cmd[52:51] and AMAX
//   (kind 6) cmd[9:8] := user (zero-extended to 2 bits).  The image leaves them 0 (non-zero = fault_code[3], as the XC
//   tag user bits).  Same register, same edge: 0 added latency; user 0's words are the image's words.
// EXPLICIT RANGE (MU-QW-B1 2026-10-19, B1 option 2: the op-start leaf qfd_sys_face_mu_dhuser OPSEG): a start with
//   start_rng = 1 plays the image entries [start_first, start_first + start_cnt) instead of the stage class's descriptor
//   (stage still names the running stage: LAST_STAGE check, and the caller's per-user stage bank).  Same playhead start,
//   fetch, T_k (the first entry's delta counts from the start edge, as a descriptor's first entry) and faults.  Range
//   check: start_cnt 0, start_first not 4-aligned (one store row = 4 entries), or start_first + start_cnt > nent ->
//   fault_code[0] and the start is refused (as any bad start).  start_rng = 0 (tie it so where unused): identical.
//   MUT 21 (bench only): the range is ignored (the stage class's descriptor plays).
// TLOAD (MU-QW-DIE 10-19: qfd_dv_cmd_cal's QLB-C4b LOCAL kind 3, d8b6a157e, ported so the MU calendar keeps the die's
//   slice-table load path tt_ctlm.tl -> dvs_W5.st_wi): an issued LOCAL kind 3 entry reads one 16-word PW block (row
//   [9:4], both store macros) on the next edge and puts {1, kind, dst, src, eaddr, tag, payload} on `tl` 2 edges after
//   the issue edge for one edge (0 otherwise); the block read takes the shared store read port, so NO playhead is
//   granted a read on the issue edge (the single calendar suppresses its fetch the same way; the compiler places
//   TLOAD entries in BOOT only, where playhead 0 plays alone).  Same fail-closed checks (fault_code[4]).  NU = 1:
//   lockstep-identical to qfd_dv_cmd_cal incl. tl.  MUT 4 / 5 (bench only): payload halves swapped / word one edge late.
// CTX_DW (MU-QW-DIE 2026-10-19, coordinator 0ka: the OPSEG fillers' initial context is boot-loaded through the image /
//   host config plane, no bench-only preload; opt-in, 0 = unchanged): image words DW5 / DW6 (reserved 0 today: a
//   non-zero DW5 / DW6 is a seal fault at CTX_DW 0) carry the per-user context record {DW6, DW5} and the seal no longer
//   requires them to be 0.  Outputs ctx_dw = {DW6, DW5} (the existing dwr[5] / dwr[6] registers, no new storage) and
//   ctx_load = one edge on the accepted seal (sealed rises without an image fault) -- the consumer (qfd_tt_ctlm_dv OPSEG)
//   checks the record and loads it.  CTX_DW 0: ctx_load is 0, ctx_dw is still {dwr[6], dwr[5]} (= 0 on every sealed image).
// CALPIPE (MU-DQ-CALPIPE / CALPIPE2 10-19, COORD 0ke; safe-design item 4: <= ~600 ps a stage at TT, wide muxes as
//   registered one-hot selects).  The kit gate's calendar paths were (a) reg->reg -884 / -801 ps: rp -> q_t FIFO-head mux
//   -> 20-bit tcount == ht compare -> fire -> pop / issue (and the relocation adders behind the issue mux), (b) macro->reg
//   -411.7 ps: rd[rd_bank] 512-bit mux -> 4 serial 20-bit adders (t_acc + d0 + .. + d3) -> q_t, (c) reg->macro -465.5 ps:
//   pw_d2 fanned out to both store macros' wd_in.  Now:
//   - registered head: each playhead keeps its head word / time in registers (hc_q / ht_q) and a registered fire_q
//     ("the head fires on this edge"), computed one edge ahead against tcount + 1 (precomputed next-compare);
//   - DELTA TIMER (no adder chain): the SRAM ring stores each entry's 12-b delta, not an accumulated time.  The next
//     head's time is ht_q + its delta (the previous head is the previous entry: the FIFO is in order and the last popped
//     entry stays in ht_q while the FIFO is empty; a start clears ht_q); its compare is (tcount + 1) - ht_q == delta,
//     the subtraction from registers in parallel with the head mux.  t_acc and the 4-adder chain are gone; the programme macro
//     output reaches write registers through the bank AND-OR (registered one-hot bank, shared: one entry read an edge) only;
//   - per-user SRAM ring: one 64x512 macro, two rows of four entries (eight entries total); wh selects the write row,
//     rp_oh rotates on pop. The macro reads ahead to the next head's row; a four-way 128-bit field select captures
//     directly into the head registers. Per macro: 512-bit WD register and 128-bit collision-forward register.
//     No runtime-indexed flop FIFO remains. Pending WD and read-before-write collisions forward without a stall;
//   - issue: each playhead's relocated word / relocation carry / TLOAD checks are computed from its registered head
//     (constant per-playhead stride), the issuing playhead is a one-hot AND-OR select;
//   - store write: one registered write stage per macro (ce / row / 64-b word / slot mask copies, each enabled by its
//     own bank, so they are not merged), placed at its macro.  +1 edge between a PW word and the macro write only (the
//     store is read only after the seal, >= 8 edges after the last PW word): no command / issue edge moves.
//   Issue edges, late / fault semantics, TLOAD and the shared read port are unchanged: NU = 1 stays edge-identical to
//   qfd_dv_cmd_cal (lockstep bench), compiler rules (T_0 >= 4 + (NU - 1)) unchanged.
//   MUT 33 (bench only): the precomputed next head on a pop takes FIFO slot rp instead of rp + 1 (one-hot not rotated).
// FIREDQ (QW-CTLM4 10-19, safe-design item 4: the kit gate's textbook lint named tcount -> fire_q ~745 ps / 20 levels =
//   20-b incrementer (tcount + 1) -> 20-b subtract (- ht_q) -> == dd): the relative head time is now a REGISTER,
//   dq = tcount + 1 - ht_q (MUT 1: tcount - ht_q), kept by induction: start -> 2 (MUT 1: 1), reset -> 1 (MUT 1: 0),
//   a non-frozen edge -> dq + run_q - (nh_v ? dd : 0) (the same edges on which tcount / ht_q move; frozen and refused
//   starts hold all three).  fire_n compares the dq register with dd: no adder from tcount before fire_q.  ZERO added
//   edges (edge-identical: lockstep with qfd_dv_cmd_cal at NU 1 and the compiled NU 4 timeline unchanged), no schedule
//   change.  tcount stays for the overflow / late faults only.  MUT 34 (bench only): a start loads dq = 1 (one short).
// CALR / TABLE_ROM (QW-F16SUB 10-19: the QW-F16PROG4 PRIVATE_CALR hunks ported onto CALPIPE/FIREDQ; opt-in, 0 = unchanged).
//   CALENDAR_ROM = 1: the image descriptor is CALR10 (d0 = 'CALR', nent 10 b, base 0) and the four-entry fetch reads the
//   immutable two-ROM calendar (qfd_dv_calendar_rom: pin register -> macro -> capture register) instead of the shared
//   programme store.  The store-side fetch pipeline gets ONE extra registered stage (rce_q -> rce2_q -> rd_v), so rd_v /
//   rd_n / the kept read-valid copies line up with the ROM capture register and every CALPIPE structure (per-user SRAM
//   ring, registered head, FIREDQ, kept selectors) is reused unchanged; the entry row (rds) is the ROM capture register.
//   +1 fetch edge: compiler rule T_0 >= 5 + (NU - 1) (late = FAULT, never a stall).  TLOAD is refused under CALR
//   (tl_bad).  TABLE_ROM = 1 (with CALENDAR_ROM): LOCAL kind 4 = explicit table-load pulse {table_load, table_stage,
//   table_user} on the issue register (stage 1..36, all other bits 0, else fault_code[4]); checks per playhead from the
//   registered head, as TLOAD.  BOUNDARY_RELOC of QW-F16PROG3 is NOT ported (unused by the CTLM gi).
// =====================================================================================================================
module qfd_dv_cmd_cal_mu #(
    parameter integer MUT = 0,
    parameter integer LAST_STAGE = 37,
    parameter integer TW = 20,                      // issue-time width (edges from the segment start)
    parameter integer NU = 1,                       // playheads (users in flight); 1 = qfd_dv_cmd_cal
    parameter integer UB = (NU > 1) ? $clog2(NU) : 1,
    parameter integer UVM_STRIDE = 0,               // per-user VM / landing base stride (address-field units)
    parameter integer PIDX_STRIDE = 0,              // per-user SU program-index stride
    parameter integer UTAG_LSB = 6,                 // XC tag bit of the user field
    parameter integer UFOLD = 0,                    // 1: user into STN cmd[52:51] / AMAX cmd[9:8] (NU > 1, UB <= 2)
    parameter integer TABLE_ROM = 0,                // opt-in LOCAL4 explicit table-load pulse (with CALENDAR_ROM)
    parameter integer CALENDAR_ROM = 0,             // opt-in CALR10 / two-ROM calendar fetch; +1 fetch edge
    parameter integer CTX_DW = 0                    // 1: DW5 / DW6 = the MU context record (ctx_dw / ctx_load)
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          pw_v,
    input  wire [9:0]    pw_addr,
    input  wire [63:0]   pw_data,
    input  wire          dw_v,
    input  wire [2:0]    dw_addr,
    input  wire [63:0]   dw_data,
    input  wire          start,
    input  wire [5:0]    stage,
    input  wire [UB-1:0] start_user,                // NU > 1: the user this start runs (ignored at NU = 1)
    input  wire          start_rng,                 // 1: explicit entry range (start_first / start_cnt); tie 0 if unused
    input  wire [9:0]    start_first,
    input  wire [9:0]    start_cnt,
    output reg  [115:0]  cmd,
    output reg  [UB-1:0] cmd_user,                  // the user of cmd / loc_* / su_issue / xc_issue (0 at NU = 1)
    output reg           loc_emb,
    output reg           loc_seg,
    output reg  [11:0]   loc_base,
    output reg           su_issue,
    output reg  [8:0]    su_pidx,
    output reg           xc_issue,
    output reg           table_load,                // TABLE_ROM: one edge, the issued LOCAL4 table-load request
    output reg  [5:0]    table_stage,
    output reg  [1:0]    table_user,
    output reg  [1087:0] tl,                        // TLOAD stream table word (W5 st_wi), one edge, else 0
    output reg  [75:0]   program_obs,
    output reg  [68:0]   descriptor_obs,
    output wire          image_ready,
    output wire          running,
    output wire [NU-1:0] running_u,
    output reg           done,
    output reg  [UB-1:0] done_user,
    output wire          fault,
    output wire [5:0]    fault_code,
    output wire [127:0]  ctx_dw,                    // {DW6, DW5} of the sealed image (CTX_DW)
    output wire          ctx_load                   // one edge: the image (with its context record) was sealed (CTX_DW)
);
    // ================================================================ image load (as qfd_dv_cmd_cal)
    reg         loading, sealed, sealed_d;
    reg  [10:0] pw_cnt;
    reg  [3:0]  dw_cnt;
    reg  [9:0]  meta_rows;
    reg  [63:0] dwr [0:6];
    wire [63:0] d0 = dwr[0];
    wire [9:0]  base = d0[25:16];
    wire [9:0]  nent = CALENDAR_ROM ? d0[9:0] : {1'b0, d0[8:0]};
    // CTLM7: seal_bad was ~710 ps of record arithmetic in front of the fault chain.  Its
    // register part is now computed from the EXACT next-state of dwr / meta_rows (dwr is
    // written only by dw_v && dw_addr != 7, meta_rows only by pw_v at addr 0 / 1017) and
    // registered (sb_r), so at the seal edge seal_bad = sb_r || dw_data != 0 -- bit-exact,
    // 0 added edges.  a + b > n is evaluated as the carry of a + b + ~n (3:2 compressed).
    wire        seal_bad;
    reg         sb_r, sb_n;
    integer     s;
    wire [63:0] dwr_n [0:6];
    genvar gsb;
    generate for (gsb = 0; gsb < 7; gsb = gsb + 1) begin : g_dwrn
        assign dwr_n[gsb] = (dw_v && dw_addr == gsb) ? dw_data : dwr[gsb];
    end endgenerate
    wire [9:0]  meta_n = !pw_v ? meta_rows : (pw_addr == 10'd0) ? 10'd0 : (pw_addr == 10'd1017) ? pw_data[27:18] : meta_rows;
    wire [63:0] d0_n = dwr_n[0];
    wire [9:0]  base_n = d0_n[25:16];
    wire [9:0]  nent_n = CALENDAR_ROM ? d0_n[9:0] : {1'b0, d0_n[8:0]};
    reg  [18:0] csa_s, csa_c, csa_t;
    always @* begin
        sb_n = (CALENDAR_ROM ? (d0_n[63:32] != 32'h43414c52 || d0_n[31:10] != 22'd0) :
               (d0_n[63:32] != 32'h43414c44 || d0_n[31:26] != 6'd0 || d0_n[15:9] != 7'd0 || base_n[2:0] != 3'd0 ||
                {1'b0, base_n} + {nent_n, 1'b0} > 11'd976 || {4'd0, base_n} < {meta_n, 4'd0})) ||
               nent_n == 10'd0 ||
               (CTX_DW == 0 && (dwr_n[5] != 64'd0 || dwr_n[6] != 64'd0));
        for (s = 1; s <= 4; s = s + 1) begin
            // {1'b0,a} + {1'b0,b} > n  <=>  a + b + (2^18 - 1 - n) >= 2^18 (19-bit, 3:2 compressed)
            csa_s = {3'd0, dwr_n[s][31:16]} ^ {3'd0, dwr_n[s][15:0]} ^ {1'b0, 8'hff, ~nent_n};
            csa_c = {(({3'd0, dwr_n[s][31:16]} & {3'd0, dwr_n[s][15:0]}) | ({3'd0, dwr_n[s][31:16]} & {1'b0, 8'hff, ~nent_n}) |
                      ({3'd0, dwr_n[s][15:0]} & {1'b0, 8'hff, ~nent_n})), 1'b0} & 19'h7ffff;
            csa_t = csa_s + csa_c;
            if (dwr_n[s][63:32] != 32'd0 ||
                (dwr_n[s][15:0] != 16'd0 && (dwr_n[s][17:16] != 2'd0 || csa_t[18])))
                sb_n = 1'b1;
        end
    end
    // CTLM8 (same value as sb_n): the seal check per candidate word, so the dw_v / pw_v decode only SELECTS.
    // One dw write replaces at most one word k; meta_n is meta_rows, 0 or pw_data[27:18].
    function automatic sgb8(input [63:0] d, input [9:0] n);
        reg [18:0] cs, cc, ct;
        begin
            cs = {3'd0, d[31:16]} ^ {3'd0, d[15:0]} ^ {1'b0, 8'hff, ~n};
            cc = {(({3'd0, d[31:16]} & {3'd0, d[15:0]}) | ({3'd0, d[31:16]} & {1'b0, 8'hff, ~n}) |
                   ({3'd0, d[15:0]} & {1'b0, 8'hff, ~n})), 1'b0} & 19'h7ffff;
            ct = cs + cc;
            sgb8 = d[63:32] != 32'd0 || (d[15:0] != 16'd0 && (d[17:16] != 2'd0 || ct[18]));
        end
    endfunction
    function automatic [9:0] nent8(input [63:0] d);
        nent8 = CALENDAR_ROM ? d[9:0] : {1'b0, d[8:0]};
    endfunction
    function automatic hdr8(input [63:0] d);   // header word checks except the metadata overlap
        reg [9:0] b, n;
        begin
            b = d[25:16]; n = nent8(d);
            hdr8 = (CALENDAR_ROM ? (d[63:32] != 32'h43414c52 || d[31:10] != 22'd0) :
                    (d[63:32] != 32'h43414c44 || d[31:26] != 6'd0 || d[15:9] != 7'd0 || b[2:0] != 3'd0 ||
                     {1'b0, b} + {n, 1'b0} > 11'd976)) || n == 10'd0;
        end
    endfunction
    wire        k0_8 = dw_v && dw_addr == 3'd0;
    wire        mz_8 = pw_v && pw_addr == 10'd0, mp_8 = pw_v && pw_addr == 10'd1017 && !mz_8;
    wire [9:0]  bo_8 = dwr[0][25:16], bw_8 = dw_data[25:16];
    wire        lt_o8 = mz_8 ? 1'b0 : mp_8 ? ({4'd0, bo_8} < {pw_data[27:18], 4'd0}) : ({4'd0, bo_8} < {meta_rows, 4'd0});
    wire        lt_w8 = mz_8 ? 1'b0 : mp_8 ? ({4'd0, bw_8} < {pw_data[27:18], 4'd0}) : ({4'd0, bw_8} < {meta_rows, 4'd0});
    wire        t0_o8 = hdr8(dwr[0]) || (!CALENDAR_ROM && lt_o8), t0_w8 = hdr8(dw_data) || (!CALENDAR_ROM && lt_w8);
    wire [9:0]  no_8 = nent8(dwr[0]), nw_8 = nent8(dw_data);
    reg         sb8;
    integer     s8;
    always @* begin
        sb8 = k0_8 ? t0_w8 : t0_o8;
        for (s8 = 1; s8 <= 4; s8 = s8 + 1)
            if ((dw_v && dw_addr == s8) ? sgb8(dw_data, no_8) : k0_8 ? sgb8(dwr[s8], nw_8) : sgb8(dwr[s8], no_8)) sb8 = 1'b1;
        if (CTX_DW == 0 && (((dw_v && dw_addr == 3'd5) ? dw_data : dwr[5]) != 64'd0 ||
                            ((dw_v && dw_addr == 3'd6) ? dw_data : dwr[6]) != 64'd0)) sb8 = 1'b1;
    end
    // CTLM7: the image end base + 2*nent (11 b, as the original expression) for the TLOAD
    // overlap check, registered from the exact next-state of dwr[0] (0 at reset = f(0)).
    reg  [10:0] bend_r; reg [7:0] bend_c;
    wire [10:0] bend_n = {1'b0, base_n} + {nent_n, 1'b0};
    wire [11:0] bend_up = {1'b0, bend_n} + 12'd15;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin sb_r <= 1'b1; bend_r <= 11'd0; bend_c <= 8'd0; end   // all-zero dwr: nent == 0 -> bad
        else begin sb_r <= sb8; bend_r <= bend_n; bend_c <= bend_up[11:4]; end   // CTLM8: sb8 == sb_n
    assign seal_bad = sb_r || dw_data != 64'd0;
    reg         pw_v2, pw_b2; reg [5:0] pw_row2; reg [7:0] pw_sl2; reg [63:0] pw_d2;
    reg         dw_v2; reg [2:0] dw_a2; reg [63:0] dw_d2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin pw_v2 <= 1'b0; dw_v2 <= 1'b0; end
        else begin pw_v2 <= pw_v; dw_v2 <= dw_v; end
    always @(posedge ck) begin
        pw_b2 <= pw_addr[3]; pw_row2 <= pw_addr[9:4]; pw_sl2 <= 8'd1 << pw_addr[2:0]; pw_d2 <= pw_data;
        dw_a2 <= dw_addr; dw_d2 <= dw_data;
    end
    wire [511:0] w_mask;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_mask
        assign w_mask[64*g +: 64] = {64{pw_sl2[g]}};
    end endgenerate
    wire [1:0]    m_ce = {pw_v2 && pw_b2, pw_v2 && !pw_b2};
    wire [1023:0] m_data = {2{{8{pw_d2}}}}, m_mask = {2{w_mask}};
    wire          ob_v, ob_full; wire [9:0] ob_addr; wire [63:0] ob_data;
    qkd_program_pw_observer_p u_obs (.macro_ce(m_ce), .macro_row({pw_row2, pw_row2}), .macro_data(m_data),
        .macro_mask(m_mask), .consumed_v(ob_v), .consumed_addr(ob_addr), .consumed_data(ob_data), .full_word(ob_full));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin program_obs <= 76'd0; descriptor_obs <= 69'd0; end
        else begin
            program_obs <= {ob_v, ob_full, ob_addr, ob_data};
            descriptor_obs <= {dw_v2, 1'b1, dw_a2, dw_d2};
        end

    // ================================================================ per-playhead state
    reg  [NU-1:0] run_q;
    reg  [9:0]    f_rem [0:NU-1], i_rem [0:NU-1];
    // CTLM7: f_idx split into its go-only low bits and the +4 stride high bits, so no
    // next-state mux has an optimizer don't-care (literal-X) arm on f_idx[1:0]
    reg  [1:0]    f_lo [0:NU-1]; reg [7:0] f_hi [0:NU-1];
    wire [9:0]    f_idx [0:NU-1];
    genvar gfi;
    generate for (gfi = 0; gfi < NU; gfi = gfi + 1) begin : g_fidx
        assign f_idx[gfi] = {f_hi[gfi], f_lo[gfi]};
    end endgenerate
    reg  [3:0]    fifo_n [0:NU-1], infl [0:NU-1];
    reg  [NU-1:0] wh;                               // write half: a push's entry j lands in slot {wh, j}
    reg  [7:0]    rp_oh [0:NU-1];                   // one-hot read pointer
    reg  [TW-1:0] tcount [0:NU-1];
    reg  [NU-1:0] rce_q, rbank_q, rd_v, rce2_q;        // rce2_q: CALENDAR_ROM extra fetch stage
    reg  [2:0]    r_n2_q [0:NU-1];
    reg  [5:0]    rrow_q [0:NU-1];
    reg  [2:0]    rd_n [0:NU-1], r_n_q [0:NU-1];
    reg  [1:0]    rdb_oh;                           // bank of the entry read on rd this edge (one-hot, shared)
    assign running_u = run_q;
    assign running = |run_q;

    // store read port: shared, one playhead's read an edge (a second one only after a faulted start: fault_code[5])
    reg          m_rce, m_rbank; reg [5:0] m_rrow; reg m_dbl;
    integer      a;
    always @* begin
        m_rce = 1'b0; m_rbank = 1'b0; m_rrow = 6'd0; m_dbl = 1'b0;
        for (a = 0; a < NU; a = a + 1)
            if (rce_q[a]) begin
                if (m_rce) m_dbl = 1'b1;
                m_rce = 1'b1; m_rbank = m_rbank | rbank_q[a]; m_rrow = m_rrow | rrow_q[a];
            end
    end
    // store write stage: one registered copy per macro (enabled by its own bank -> distinct, not merged)
    reg  [1:0]   w3_ce;
    reg  [5:0]   w3_row [0:1];
    reg  [63:0]  w3_d [0:1];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) w3_ce <= 2'b00;
        else w3_ce <= m_ce;
    always @(posedge ck) begin
        if (m_ce[0]) begin w3_row[0] <= pw_row2; w3_d[0] <= pw_d2; end
        if (m_ce[1]) begin w3_row[1] <= pw_row2; w3_d[1] <= pw_d2; end
    end
    wire [511:0] rd [0:1];
    reg          tl_rce_q, tl_v2, tl_v3; reg [5:0] tl_row_q; reg [63:0] tl_ctl_q, tl_ctl2, tl_ctl3; reg [1023:0] tl_pay3;
    wire         tl_fire;
    generate for (g = 0; g < 2; g = g + 1) begin : g_m
        wire [511:0] w3_mask;
        genvar h;
        for (h = 0; h < 8; h = h + 1) begin : g_wm
            genvar c;
            for (c = 0; c < 2; c = c + 1) begin : g_copy
                wire mask;
                qfd_calpipe_mask #(.COPY_ID(16*g+2*h+c)) u_mask (
                    .ck(ck), .write_ce(m_ce[g]), .mask_in(pw_sl2[h]), .mask(mask));
                assign w3_mask[64*h+32*c +: 32] = {32{mask}};
            end
        end
        ot_sram_1r1w_64x512_m1_r2c2 u_pm (.clk(ck), .r_ce_in((CALENDAR_ROM == 0 && m_rce && (m_rbank == g[0])) || tl_rce_q),
            .r_addr_in(tl_rce_q ? tl_row_q : m_rrow), .rd_out(rd[g]),
            .w_ce_in(w3_ce[g]), .w_addr_in(w3_row[g]), .wd_in({8{w3_d[g]}}), .w_mask_in(w3_mask),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end endgenerate
    // the entry row on rd (bank AND-OR by the registered one-hot bank; MUT 2: entry halves swapped)
    wire [511:0] rom_data;
    wire [511:0] rds = (CALENDAR_ROM != 0) ? rom_data : (({512{rdb_oh[0]}} & rd[0]) | ({512{rdb_oh[1]}} & rd[1]));
    reg  [127:0] ent [0:3];
    reg  [11:0]  dlt [0:3];
    integer      e;
    always @*
        for (e = 0; e < 4; e = e + 1) begin
            ent[e] = (MUT == 2) ? {rds[128*e +: 64], rds[128*e + 64 +: 64]} : rds[128*e +: 128];
            dlt[e] = ent[e][127:116];
        end

    // registered head (word, time) + registered "fires this edge", computed one edge ahead (see CALPIPE above)
    reg  [NU-1:0]  fire_q;
    reg  [115:0]   hc_q [0:NU-1];
    reg  [TW-1:0]  ht_q [0:NU-1];
    reg  [TW-1:0]  dq [0:NU-1];                     // FIREDQ: = tcount + 1 - ht_q (MUT 1: tcount - ht_q), registered
    // Two-row, eight-entry SRAM ring per playhead. One complete four-entry program
    // fetch is staged at the SRAM write pins. Read the row of the next head ahead
    // of its pop; the head register is the SRAM read-data capture. SRAM models are
    // read-before-write, so both pending writes and read/write collisions forward.
    wire [511:0] fq_rd [0:NU-1];
    wire [127:0] fq_word [0:NU-1];
    reg [NU-1:0] fq_we, fq_wa, fq_bypass;
    reg [511:0] fq_wd [0:NU-1];
    reg [127:0] fq_bd [0:NU-1];
    wire [2:0] fq_next [0:NU-1], fq_ahead [0:NU-1];
    wire [NU-1:0] fq_ra;
    // CTLM8 (FIREDQ head candidates): chunk-3 sources of dsel = fq_word[127:116] and its select flags, exported so
    // dq_n / fire_n / nh_t are computed per source in parallel and the late select only picks (exact, 0 edges)
    wire [11:0] dsw [0:NU-1], dsb [0:NU-1], dsr [0:NU-1];
    wire [NU-1:0] selw3, bp3, nx2;
    generate for (g = 0; g < NU; g = g + 1) begin : g_fifo
        reg [2:0] rp_bin;
        integer b;
        // CTLM7: OR encoder (rp_oh is one-hot by construction: reset / start 8'd1, rotate on pop),
        // equal to the last-wins loop on every reachable value; was an 8-deep priority chain
        always @* begin
            rp_bin = {|(rp_oh[g] & 8'hf0), |(rp_oh[g] & 8'hcc), |(rp_oh[g] & 8'haa)};
        end
        assign fq_next[g] = rp_bin + ((MUT == 33) ? 3'd0 : 3'd1);
        // CTLM8: bit 2 of rp + 1 straight from the one-hot pointer (rp in 3..6), no encoder + incrementer in the select
        assign nx2[g] = (MUT == 33) ? |(rp_oh[g] & 8'hf0) : |(rp_oh[g] & 8'h78);
        assign fq_ahead[g] = rp_bin + ((fire_q[g] && !frz_u[g] && !go_u[g]) ? 3'd2 : 3'd1);
        assign fq_ra[g] = fq_ahead[g][2];
        ot_sram_1r1w_64x512_m1_r2c2 u_fifo (
            .clk(ck), .r_ce_in(1'b1), .r_addr_in({5'd0, fq_ra[g]}), .rd_out(fq_rd[g]),
            .w_ce_in(fq_we[g]), .w_addr_in({5'd0, fq_wa[g]}), .wd_in(fq_wd[g]), .w_mask_in({512{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        // Distinct hierarchy-kept selector flops per32-bit data chunk and
        // per source; no selector register drives a full128/512-bit mux.
        wire do_pop = fire_q[g] && !frz_u[g] && !go_u[g];
        wire do_clear = go_u[g] && !start_bad && g_cnt_nz;
        genvar q;
        for (q = 0; q < 4; q = q + 1) begin : g_sel
            wire [3:0] ws, rs, bs;
            wire pend, bp;
            wire [31:0] wword, rword, bword;
            qfd_calpipe_selector #(.COPY_ID(12*g+3*q), .MUT(MUT)) u_ws (
                .ck(ck), .rst_n(rst_n), .pop(do_pop), .clear(do_clear),
                .pending_in(rd_v[g] && !frz_u[g] && !go_u[g]),
                .bypass_in(fq_we[g] && fq_wa[g] == fq_ra[g]), .sel(ws), .pending(), .bypass());
            qfd_calpipe_selector #(.COPY_ID(12*g+3*q+1), .MUT(MUT)) u_rs (
                .ck(ck), .rst_n(rst_n), .pop(do_pop), .clear(do_clear),
                .pending_in(rd_v[g] && !frz_u[g] && !go_u[g]),
                .bypass_in(fq_we[g] && fq_wa[g] == fq_ra[g]), .sel(rs), .pending(pend), .bypass(bp));
            qfd_calpipe_selector #(.COPY_ID(12*g+3*q+2), .MUT(MUT)) u_bs (
                .ck(ck), .rst_n(rst_n), .pop(do_pop), .clear(do_clear),
                .pending_in(rd_v[g] && !frz_u[g] && !go_u[g]),
                .bypass_in(fq_we[g] && fq_wa[g] == fq_ra[g]), .sel(bs), .pending(), .bypass());
            wire [3:0] ba = do_pop ? {bs[2:0],bs[3]} : bs;
            assign wword = ({32{ws[0]}} & fq_wd[g][q*32 +: 32]) |
                           ({32{ws[1]}} & fq_wd[g][128+q*32 +: 32]) |
                           ({32{ws[2]}} & fq_wd[g][256+q*32 +: 32]) |
                           ({32{ws[3]}} & fq_wd[g][384+q*32 +: 32]);
            assign rword = ({32{rs[0]}} & fq_rd[g][q*32 +: 32]) |
                           ({32{rs[1]}} & fq_rd[g][128+q*32 +: 32]) |
                           ({32{rs[2]}} & fq_rd[g][256+q*32 +: 32]) |
                           ({32{rs[3]}} & fq_rd[g][384+q*32 +: 32]);
            assign bword = ({32{ba[0]}} & fq_wd[g][q*32 +: 32]) |
                           ({32{ba[1]}} & fq_wd[g][128+q*32 +: 32]) |
                           ({32{ba[2]}} & fq_wd[g][256+q*32 +: 32]) |
                           ({32{ba[3]}} & fq_wd[g][384+q*32 +: 32]);
            assign fq_word[g][32*q +: 32] = (pend && fq_wa[g] == nx2[g]) ? wword :
                                            bp ? fq_bd[g][32*q +: 32] : rword;
            if (q == 3) begin : g_src3
                assign dsw[g] = wword[31:20]; assign dsr[g] = rword[31:20]; assign dsb[g] = fq_bd[g][127:116];
                assign selw3[g] = pend && fq_wa[g] == nx2[g]; assign bp3[g] = bp;
            end
            always @(posedge ck)
                if (fq_we[g] && fq_wa[g] == fq_ra[g]) fq_bd[g][32*q +: 32] <= bword;
        end
        // Match rd_v's pipeline/hold semantics in local kept CE copies.
        // Each copy enables exactly32 WD flops instead of one512-load CE.
        genvar c;
        for (c = 0; c < 16; c = c + 1) begin : g_wce
            wire valid;
            qfd_calpipe_readvalid #(.COPY_ID(16*g+c)) u_v (
                .ck(ck), .rst_n(rst_n), .clear(do_clear), .freeze(frz_u[g] || go_u[g]),
                .read_ce((CALENDAR_ROM != 0) ? rce2_q[g] : rce_q[g]), .valid(valid));
            always @(posedge ck)
                if (valid && !frz_u[g] && !go_u[g]) fq_wd[g][32*c +: 32] <= rds[32*c +: 32];
        end
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin fq_we[g] <= 1'b0; fq_bypass[g] <= 1'b0; end
            else begin
                fq_we[g] <= rd_v[g] && !frz_u[g] && !go_u[g];
                fq_bypass[g] <= fq_we[g] && fq_wa[g] == fq_ra[g];
            end
        always @(posedge ck) begin
            if (rd_v[g] && !frz_u[g] && !go_u[g]) fq_wa[g] <= wh[g];
        end
    end endgenerate

    // ================================================================ segment start
    wire       boot_go = sealed && !sealed_d && (MUT != 3);
    assign     ctx_dw = {dwr[6], dwr[5]};
    assign     ctx_load = (CTX_DW != 0) && sealed && !sealed_d && !fault;
    wire [1:0] sseg = (stage == 6'd0) ? 2'd0 : (stage == LAST_STAGE[5:0]) ? 2'd2 : 2'd1;
    wire       go = start || boot_go;
    wire [1:0] gseg = boot_go ? 2'd3 : sseg;
    // CTLM7: one-hot word select (gseg 0..3 -> dwr[1..4]), no index adder; the count-nonzero
    // test is taken per word from the registered dwr so do_clear does not wait on the 64-b mux
    wire [3:0]  gsel = {gseg == 2'd3, gseg == 2'd2, gseg == 2'd1, gseg == 2'd0};
    wire [63:0] gd = ({64{gsel[0]}} & dwr[1]) | ({64{gsel[1]}} & dwr[2]) | ({64{gsel[2]}} & dwr[3]) | ({64{gsel[3]}} & dwr[4]);
    wire [3:0]  dnz = {dwr[4][15:0] != 16'd0, dwr[3][15:0] != 16'd0, dwr[2][15:0] != 16'd0, dwr[1][15:0] != 16'd0};
    wire        g_rng = start && start_rng && !boot_go;
    wire [15:0] g_first = (g_rng && MUT != 21) ? {6'd0, start_first} : gd[31:16];
    wire [15:0] g_cnt = (g_rng && MUT != 21) ? {6'd0, start_cnt} : gd[15:0];
    // CTLM7: {0,first} + {0,cnt} > {0,nent}  <=>  bit 11 of first + cnt + (2^11 - 1 - nent), 3:2 compressed
    wire [11:0] rg_a = {2'd0, start_first}, rg_b = {2'd0, start_cnt}, rg_c = {2'b01, ~nent};
    wire [11:0] rg_s = rg_a ^ rg_b ^ rg_c;
    wire [11:0] rg_k = {((rg_a[10:0] & rg_b[10:0]) | (rg_a[10:0] & rg_c[10:0]) | (rg_b[10:0] & rg_c[10:0])), 1'b0};
    wire [11:0] rg_t;
    ot_ks_add #(.W(12)) u_rgks (.a(rg_s), .b(rg_k), .cin(1'b0), .s(rg_t));
    wire        rng_gt = rg_t[11];
    wire        g_cnt_nz = (g_rng && MUT != 21) ? (start_cnt != 10'd0) : |(gsel & dnz);   // == (g_cnt != 0)
    wire        rng_bad = g_rng && (start_cnt == 10'd0 || start_first[1:0] != 2'd0 ||
                                    rng_gt);
    wire [UB-1:0] go_user = (NU > 1 && !boot_go) ? start_user : {UB{1'b0}};
    // a start reaches only its own playhead (MUT 15: every playhead, the single calendar's gating)
    reg  [NU-1:0] go_u, frz_u;
    integer       b;
    always @* begin
        for (b = 0; b < NU; b = b + 1) begin
            go_u[b]  = go && (go_user == b[UB-1:0]);
            frz_u[b] = (MUT == 15) ? go : go_u[b];
        end
    end
    // start refusal: own playhead playing (MUT 13: any playhead; MUT 14: never)
    wire busy_sel = (MUT == 13) ? (|run_q) : (MUT == 14) ? 1'b0 : run_q[go_user];
    wire start_bad = !sealed || busy_sel || (start && boot_go) || (start && stage > LAST_STAGE[5:0]) || rng_bad;

    // ================================================================ fetch / head, per playhead (combinational)
    reg  [NU-1:0]  can_read, gnt, hv, late, hgo, zd;
    reg  [9:0]     waddr [0:NU-1];
    reg  [2:0]     f_n [0:NU-1];
    reg            any_gnt;
    reg  [NU-1:0]  run_n, nh_v, fire_n;
    reg  [TW-1:0]  dq_n [0:NU-1];
    reg  [115:0]   nh_c [0:NU-1];
    reg  [TW-1:0]  nh_t [0:NU-1];
    reg  [7:0]     rpa_oh [0:NU-1];
    reg  [TW-1:0]  tdif, ht_m;
    reg  [TW-1:0]  dq_x, dq_s; reg [TW:0] dq_c;   // CTLM7 dq_n compressor
    reg            c_pop, c_emp, s_w, s_b, s_r, s_l, s_z;   // CTLM8 candidate selects
    reg  [TW-1:0]  dq_sa [0:NU-1], dq_ca [0:NU-1]; wire [TW-1:0] dq_ks [0:NU-1];
    wire [4:0]     occ [0:NU-1];
    wire [3:0]     infl_g [0:NU-1], infl_ng [0:NU-1];
    // CTLM8 FIREDQ candidates per playhead and source s in {w, b, r, l = dlt[0]} (z = no dd: D = dq + run, T = ht_q):
    //   D_s = dq + run - X_s  = {dq_hi + k, (dq_lo + run) - X_s},  k in {-1, 0} from the 14-b low result
    //   T_s = ht_q + X_s      = {ht_hi + c, ht_lo + X_s},          c in {0, 1}
    //   E_s = (dq == X_s)     = (dq_hi == 0) && (dq_lo == X_s)
    // dq_hi +- 1 / ht_hi + 1 / dq_lo + run are register-only (off the late path); after X_s: one 14-b KS + 2:1 + select.
    wire [TW-1:0] cd_d [0:4*NU-1], cd_t [0:4*NU-1];   // index 4 * playhead + source
    wire [3:0]    cd_e [0:NU-1];
    wire [TW-1:0] cd_dz [0:NU-1];
    wire          cd_ez [0:NU-1];
    genvar gcd, gcs;
    generate for (gcd = 0; gcd < NU; gcd = gcd + 1) begin : g_cand
        wire [12:0]    plo;
        wire [TW-13:0] dhm, dhi, thp;
        ot_ks_add #(.W(13)) u_plo (.a({1'b0, dq[gcd][11:0]}), .b(13'd0), .cin(run_q[gcd]), .s(plo));
        ot_ks_add #(.W(TW-12)) u_dhm (.a(dq[gcd][TW-1:12]), .b({(TW-12){1'b1}}), .cin(1'b0), .s(dhm));
        ot_ks_add #(.W(TW-12)) u_dhp (.a(dq[gcd][TW-1:12]), .b({(TW-12){1'b0}}), .cin(1'b1), .s(dhi));
        ot_ks_add #(.W(TW-12)) u_thp (.a(ht_q[gcd][TW-1:12]), .b({(TW-12){1'b0}}), .cin(1'b1), .s(thp));
        // z: dq + run (plo carries into the high part when dq_lo = 4095 and run)
        assign cd_dz[gcd] = {plo[12] ? dhi : dq[gcd][TW-1:12], plo[11:0]};
        assign cd_ez[gcd] = (dq[gcd] == {TW{1'b0}});
        for (gcs = 0; gcs < 4; gcs = gcs + 1) begin : g_src
            wire [11:0] x = (gcs == 0) ? dsw[gcd] : (gcs == 1) ? dsb[gcd] : (gcs == 2) ? dsr[gcd] : dlt[0];
            wire [13:0] lo;   // {0, plo} - {00, x}: signed, -4095 .. 4096
            // = plo - x as dq_lo + ~x + run + 1: one 3:2 compressor + one 14-b KS (no plo carry chain in series)
            wire [13:0] la = {2'b00, dq[gcd][11:0]}, lb = {2'b11, ~x}, lc = {13'd0, run_q[gcd]};
            wire [13:0] ls = la ^ lb ^ lc, lk = {((la[12:0] & lb[12:0]) | (la[12:0] & lc[12:0]) | (lb[12:0] & lc[12:0])), 1'b1};
            ot_ks_add #(.W(14)) u_lo (.a(ls), .b(lk), .cin(1'b0), .s(lo));
            wire [12:0] tl;
            ot_ks_add #(.W(13)) u_tl (.a({1'b0, ht_q[gcd][11:0]}), .b({1'b0, x}), .cin(1'b0), .s(tl));
            // lo[13:12]: 11 = -1, 00 = 0, 01 = +1 (only with plo = 4096, x = 0)
            assign cd_d[4*gcd+gcs] = {lo[13] ? dhm : lo[12] ? dhi : dq[gcd][TW-1:12], lo[11:0]};
            assign cd_t[4*gcd+gcs] = {tl[12] ? thp : ht_q[gcd][TW-1:12], tl[11:0]};
            assign cd_e[gcd][gcs] = (dq[gcd][TW-1:12] == {(TW-12){1'b0}}) && (dq[gcd][11:0] == x);
        end
    end endgenerate
    genvar gks;
    generate for (gks = 0; gks < NU; gks = gks + 1) begin : g_dqks
        ot_ks_add #(.W(TW)) u_dqks (.a(dq_sa[gks]), .b(dq_ca[gks]), .cin(1'b0), .s(dq_ks[gks]));
        ot_ks_add #(.W(5)) u_occ (.a({1'b0, fifo_n[gks]}), .b({1'b0, infl[gks]}), .cin(1'b0), .s(occ[gks]));
        wire [3:0] rdx = rd_v[gks] ? {1'b0, rd_n[gks]} : 4'd0;
        assign infl_ng[gks] = infl[gks] - rdx;
        assign infl_g[gks] = infl[gks] + {1'b0, f_n[gks]} - rdx;
    end endgenerate
    reg  [115:0]   csel;
    reg  [11:0]    dsel, dd;
    reg  [3:0]     fn_ap;
    integer        u, j;
    always @* begin
        any_gnt = 1'b0;
        for (u = 0; u < NU; u = u + 1) begin
            waddr[u] = base + {f_idx[u][8:0], 1'b0};
            f_n[u] = (f_rem[u] >= 10'd4) ? 3'd4 : f_rem[u][2:0];
            // CTLM7: fifo_n + infl + 4 <= 8  <=>  fifo_n + infl <= 4 (5-bit, log-depth sum occ)
            can_read[u] = run_q[u] && f_rem[u] != 10'd0 && occ[u][4:3] == 2'd0 && (!occ[u][2] || occ[u][1:0] == 2'd0);
            // lowest-index playhead that is not being (re)started this edge takes the read port (none on a TLOAD
            // issue edge: the block read owns the next edge's port)
            gnt[u] = can_read[u] && !frz_u[u] && !any_gnt && !tl_fire;
            if (can_read[u] && !frz_u[u]) any_gnt = 1'b1;
            zd[u] = 1'b0;
            for (j = 0; j < 4; j = j + 1)
                if ((j < rd_n[u]) && dlt[j] == 12'd0) zd[u] = 1'b1;
            ht_m = ht_q[u] + ((MUT == 1) ? {{(TW-1){1'b0}}, 1'b1} : {TW{1'b0}});
            hv[u] = fifo_n[u] != 4'd0;
            late[u] = run_q[u] && hv[u] && tcount[u] > ht_m;
            hgo[u] = fire_q[u] && !frz_u[u] && hc_q[u][0];
            // next edge's head and its fire flag (used on a non-frozen edge; a frozen edge holds them)
            run_n[u] = run_q[u] && !(fire_q[u] && i_rem[u] == 10'd1);
            tdif = dq[u];                                    // FIREDQ: registered tcount + 1 - ht_q (no adder here)
            fn_ap = fifo_n[u] - (fire_q[u] ? 4'd1 : 4'd0);
            rpa_oh[u] = {rp_oh[u][6:0], rp_oh[u][7]};
            csel = fq_word[u][115:0];
            dsel = fq_word[u][127:116];
            if (MUT == 2) begin
                csel = {fq_word[u][63:0], fq_word[u][115:64]};
                dsel = fq_word[u][63:52];
            end
            nh_v[u] = 1'b1; nh_c[u] = hc_q[u]; dd = 12'd0;
            if (fn_ap != 4'd0) begin
                if (fire_q[u]) begin nh_c[u] = csel; dd = dsel; end           // pop: the next FIFO slot
            end else begin
                // Invalid data is immaterial; keep rd_v off the wide data mux.
                nh_c[u] = ent[0][115:0]; dd = dlt[0]; nh_v[u] = rd_v[u];
            end
            nh_t[u] = ht_q[u] + {{(TW-12){1'b0}}, dd};
            fire_n[u] = run_n[u] && nh_v[u] && tdif == {{(TW-12){1'b0}}, dd};
            // FIREDQ next value on a non-frozen edge: tcount moves by run_q, ht_q by dd when nh_v
            // CTLM7: dq + run - x (mod 2^TW) = dq + run + ~x + 1: one 3:2 compressor, the +1 in the free carry LSB
            dq_x = nh_v[u] ? {{(TW-12){1'b0}}, dd} : {TW{1'b0}};
            dq_s = dq[u] ^ {{(TW-1){1'b0}}, run_q[u]} ^ ~dq_x;
            dq_c = {((dq[u] & {{(TW-1){1'b0}}, run_q[u]}) | (dq[u] & ~dq_x) | ({{(TW-1){1'b0}}, run_q[u]} & ~dq_x)), 1'b1};
            dq_sa[u] = dq_s; dq_ca[u] = dq_c[TW-1:0];
            dq_n[u] = dq_ks[u];
            if (MUT != 2) begin
                // CTLM8: identical values, the late conditions only select among precomputed candidates
                c_pop = (fn_ap != 4'd0) && fire_q[u];
                c_emp = (fn_ap == 4'd0);
                s_w = c_pop && selw3[u]; s_b = c_pop && !selw3[u] && bp3[u]; s_r = c_pop && !selw3[u] && !bp3[u];
                s_l = c_emp && rd_v[u];
                s_z = !c_pop && !s_l;                       // fn_ap != 0 && !fire_q (dd = 0), or empty && !rd_v (dq_x = 0)
                dq_n[u] = ({TW{s_w}} & cd_d[4*u+0]) | ({TW{s_b}} & cd_d[4*u+1]) | ({TW{s_r}} & cd_d[4*u+2]) |
                          ({TW{s_l}} & cd_d[4*u+3]) | ({TW{s_z}} & cd_dz[u]);
                nh_t[u] = ({TW{s_w}} & cd_t[4*u+0]) | ({TW{s_b}} & cd_t[4*u+1]) | ({TW{s_r}} & cd_t[4*u+2]) |
                          ({TW{s_l}} & cd_t[4*u+3]) | ({TW{s_z}} & ht_q[u]);
                fire_n[u] = run_n[u] && !(c_emp && !rd_v[u]) &&
                            ((s_w && cd_e[u][0]) || (s_b && cd_e[u][1]) || (s_r && cd_e[u][2]) || (s_l && cd_e[u][3]) ||
                             (s_z && cd_ez[u]));
            end
        end
    end
    // CALENDAR_ROM: the granted playhead's 4-entry request goes to the two-ROM calendar (pin register inside); the
    // capture register returns on the rd_v edge of that playhead (rce_q -> rce2_q -> rd_v, as the ROM's pv -> mv -> valid)
    wire       rom_valid, rom_fault; wire [1:0] rom_user; wire [5:0] rom_stage; wire [2:0] rom_count;
    reg        rom_req; reg [9:0] rom_first; reg [2:0] rom_n; reg [1:0] rom_u;
    integer    ri;
    always @* begin
        rom_req = 1'b0; rom_first = 10'd0; rom_n = 3'd0; rom_u = 2'd0;
        for (ri = 0; ri < NU; ri = ri + 1) if (gnt[ri]) begin
            rom_req = 1'b1; rom_first = f_idx[ri]; rom_n = f_n[ri]; rom_u = 2'(ri);
        end
    end
    generate if (CALENDAR_ROM != 0) begin : g_calrom
        qfd_dv_calendar_rom #(.NENT(1023)) u_rom (.ck(ck), .rst_n(rst_n), .req(rom_req),
            .first(rom_first), .count(rom_n), .user_id(rom_u), .stage(6'd0),
            .install(pw_v && running), .running(running), .valid(rom_valid), .data(rom_data),
            .out_user(rom_user), .out_stage(rom_stage), .out_count(rom_count), .fault(rom_fault));
    end else begin : g_no_calrom
        assign rom_valid = 1'b0; assign rom_fault = 1'b0; assign rom_data = 512'd0;
        assign rom_user = 2'd0; assign rom_stage = 6'd0; assign rom_count = 3'd0;
        wire unused_rom = &{1'b0, rom_req, rom_first, rom_n, rom_u};
    end endgenerate
    // the ROM's own valid / user / count must agree with the playhead pipeline (a mismatch is an image fault)
    wire       rom_mis = (CALENDAR_ROM != 0) && (rom_valid != (|rd_v) ||
                         (rom_valid && (!rd_v[rom_user] || rd_n[rom_user] != rom_count)));
    wire unused_rs = &{1'b0, rom_stage};
    // per-playhead issue word: relocation for its user (constant stride), carry / tag checks, TLOAD checks -- all from
    // the registered head, beside the issue select
    reg  [115:0]  rcu [0:NU-1];
    reg  [NU-1:0] rbad, tlk, tlb, trk, trb;
    reg  [UB-1:0] ruu [0:NU-1];
    reg  [115:0]  hu;
    reg  [24:0]   uvb, r_ar, r_dd, r_em, r_db;
    reg  [9:0]    upx, r_px;
    reg  [10:0]   tlo, thi;
    integer       v;
    always @* begin
        for (v = 0; v < NU; v = v + 1) begin
            hu = hc_q[v];
            ruu[v] = (MUT == 11 && NU > 1) ? (v + 1) % NU : v;
            uvb = (NU > 1 && MUT != 12) ? 25'(ruu[v]) * 25'(UVM_STRIDE) : 25'd0;
            upx = (NU > 1 && MUT != 12) ? 10'(ruu[v]) * 10'(PIDX_STRIDE) : 10'd0;
            r_ar = {1'b0, hu[27:4]} + uvb; r_dd = {1'b0, hu[51:28]} + uvb; r_em = {1'b0, hu[77:54]} + uvb;
            r_db = {1'b0, hu[49:26]} + uvb; r_px = {1'b0, hu[12:4]} + upx;
            rcu[v] = hu; rbad[v] = 1'b0;
            if (NU > 1 && hu[115:112] != 4'hE) begin
                case (hu[3:1])
                    3'd4: begin rcu[v][27:4] = r_ar[23:0]; rcu[v][51:28] = r_dd[23:0]; rcu[v][77:54] = r_em[23:0];
                                rbad[v] = r_ar[24] | r_dd[24] | r_em[24]; end
                    3'd2: if (hu[24]) begin rcu[v][49:26] = r_db[23:0]; rbad[v] = r_db[24]; end
                    3'd1: begin rcu[v][12:4] = r_px[8:0]; rbad[v] = r_px[9]; end
                    3'd0: if (hu[5:4] == 2'd0) begin
                              if (hu[23 + UTAG_LSB +: UB] != {UB{1'b0}}) rbad[v] = 1'b1;
                              rcu[v][23 + UTAG_LSB +: UB] = ruu[v];
                          end
                    3'd6: if (UFOLD != 0) begin
                              if (hu[9:8] != 2'd0) rbad[v] = 1'b1;
                              rcu[v][9:8] = (MUT == 16) ? 2'd0 : 2'(ruu[v]);
                          end
                    default: ;
                endcase
                // STN user (UFOLD): beside the dbase relocation above, any dst
                if (UFOLD != 0 && hu[3:1] == 3'd2) begin
                    if (hu[52:51] != 2'd0) rbad[v] = 1'b1;
                    rcu[v][52:51] = (MUT == 16) ? 2'd0 : 2'(ruu[v]);
                end
            end
            // TLOAD (LOCAL kind 3): block row / header / checks (as qfd_dv_cmd_cal)
            tlk[v] = hu[115:112] == 4'hE && hu[3:1] == 3'd3;
            tlo = {1'b0, hu[9:4], 4'd0}; thi = tlo + 11'd16;
            tlb[v] = hu[12:10] == 3'd0 || hu[12] || hu[111:73] != 39'd0 || {4'd0, hu[9:4]} < meta_rows ||
                     hu[9:4] >= 6'd61 || ({2'd0, hu[9:4]} < bend_c && hu[9:4] >= base[9:4]) || (CALENDAR_ROM != 0);
            // CTLM7: row*16 < bend <=> row < ceil(bend/16) (registered bend_c); row*16 + 16 > base <=> row >= base[9:4]
            // TABLE_ROM (LOCAL kind 4): explicit table-load request, checked from the registered head
            trk[v] = (TABLE_ROM != 0) && (CALENDAR_ROM != 0) && hu[115:112] == 4'hE && hu[3:1] == 3'd4;
            trb[v] = hu[111:10] != 102'd0 || hu[9:4] < 6'd1 || hu[9:4] > 6'd36;
        end
    end
    // the issuing playhead: the lowest with a go entry this edge (one-hot select); a second one is a collision
    reg  [NU-1:0] isel; reg i_any, i_col;
    reg  [115:0]  ic, rc; reg r_bad, tl_bad, tl_go, tr_go, tr_bad; reg [UB-1:0] ru;
    integer       c;
    always @* begin
        i_any = 1'b0; i_col = 1'b0; isel = {NU{1'b0}};
        for (c = 0; c < NU; c = c + 1) begin
            isel[c] = hgo[c] && !i_any;
            if (hgo[c]) begin if (i_any) i_col = 1'b1; i_any = 1'b1; end
        end
        ic = 116'd0; rc = 116'd0; r_bad = 1'b0; tl_bad = 1'b0; tl_go = 1'b0; tr_go = 1'b0; tr_bad = 1'b0; ru = {UB{1'b0}};
        // CTLM7: AND-OR select (isel one-hot), no per-playhead mux chain
        for (c = 0; c < NU; c = c + 1) begin
            ic = ic | ({116{isel[c]}} & hc_q[c]); rc = rc | ({116{isel[c]}} & rcu[c]); r_bad = r_bad | (isel[c] & rbad[c]);
            tl_bad = tl_bad | (isel[c] & tlb[c]); tl_go = tl_go | (isel[c] & tlk[c]); tr_go = tr_go | (isel[c] & trk[c]);
            tr_bad = tr_bad | (isel[c] & trb[c]); ru = ru | ({UB{isel[c]}} & ruu[c]);
        end
    end
    wire [2:0]    i_kind = ic[3:1];
    wire          i_loc = ic[115:112] == 4'hE;
    assign        tl_fire = tl_go;
    wire [5:0]    tl_row = ic[9:4];
    wire [2:0]    tl_kind = ic[12:10];
    generate if (CALENDAR_ROM != 0 && NU > 4) begin : g_calrom_users_bad
        initial $error("qfd_dv_cmd_cal_mu: CALENDAR_ROM requires NU <= 4");
    end endgenerate
    generate if (UFOLD != 0 && (NU < 2 || UB > 2)) begin : g_ufold_bad
        initial $error("qfd_dv_cmd_cal_mu: UFOLD needs 2 <= NU <= 4");
    end endgenerate

    // ================================================================ sequential
    integer k, kk;
    reg     d_any, d_col; reg [UB-1:0] d_u;
    reg [NU-1:0] dn;
    reg [NU-1:0] dr; reg sd, dr_any, dr_col, g_any, g_top; reg [UB-1:0] dr_hi, g_idx;   // CTLM8 completion select
    reg f_g; reg [5:0] fc_g;   // CTLM7 fault = |registered site flags | f_g
    reg [6:0] r4; reg [NU-1:0] r4g, r4h, r2, r0; reg [1:0] r3; reg r1, r5;
    wire f_p = |{r4, r4g, r4h, r3, r2, r1, r0, r5};
    wire [5:0] fc_p = {r5, |{r4, r4g, r4h}, |r3, |r2, r1, |r0};
    reg [6:0] fx4; reg [NU-1:0] fx4g, fx4h, fx0, fx2; reg [1:0] fx3; reg fx1, fx5;   // CTLM7 fault-site flags
    always @(posedge ck or negedge rst_n) begin
        // CTLM7: defined on the reset branch too (was a literal-X mux arm per d_u bit)
        d_any = 1'b0; d_col = 1'b0; d_u = {UB{1'b0}};
        dn = {NU{1'b0}};
        dr = {NU{1'b0}}; sd = 1'b0; dr_any = 1'b0; dr_col = 1'b0; g_any = 1'b0; g_top = 1'b0; dr_hi = {UB{1'b0}}; g_idx = {UB{1'b0}};
        fx4 = 7'd0; fx4g = {NU{1'b0}}; fx4h = {NU{1'b0}}; fx0 = {NU{1'b0}}; fx2 = {NU{1'b0}}; fx3 = 2'd0; fx1 = 1'b0; fx5 = 1'b0;
        if (!rst_n) begin
            loading <= 1'b0; sealed <= 1'b0; sealed_d <= 1'b0; pw_cnt <= 11'd0; dw_cnt <= 4'd0; meta_rows <= 10'd0;
            for (s = 0; s < 7; s = s + 1) dwr[s] <= 64'd0;
            run_q <= {NU{1'b0}}; done <= 1'b0; done_user <= {UB{1'b0}}; f_g <= 1'b0; fc_g <= 6'd0; r4 <= 7'd0; r4g <= {NU{1'b0}}; r4h <= {NU{1'b0}}; r3 <= 2'd0; r2 <= {NU{1'b0}}; r1 <= 1'b0; r0 <= {NU{1'b0}}; r5 <= 1'b0;
            for (k = 0; k < NU; k = k + 1) begin
                f_lo[k] <= 2'd0; f_hi[k] <= 8'd0; f_rem[k] <= 10'd0; i_rem[k] <= 10'd0; fifo_n[k] <= 4'd0; infl[k] <= 4'd0;
                rp_oh[k] <= 8'd1; tcount[k] <= {TW{1'b0}};
                rrow_q[k] <= 6'd0; r_n_q[k] <= 3'd0; rd_n[k] <= 3'd0; r_n2_q[k] <= 3'd0;
                hc_q[k] <= 116'd0; ht_q[k] <= {TW{1'b0}};
                dq[k] <= (MUT == 1) ? {TW{1'b0}} : {{(TW-1){1'b0}}, 1'b1};
            end
            wh <= {NU{1'b0}}; fire_q <= {NU{1'b0}}; rdb_oh <= 2'b00;
            rce_q <= {NU{1'b0}}; rbank_q <= {NU{1'b0}}; rd_v <= {NU{1'b0}}; rce2_q <= {NU{1'b0}};
            cmd <= 116'd0; cmd_user <= {UB{1'b0}}; loc_emb <= 1'b0; loc_seg <= 1'b0; loc_base <= 12'd0;
            su_issue <= 1'b0; su_pidx <= 9'd0; xc_issue <= 1'b0;
            table_load <= 1'b0; table_stage <= 6'd0; table_user <= 2'd0;
            tl <= 1088'd0; tl_rce_q <= 1'b0; tl_v2 <= 1'b0; tl_v3 <= 1'b0; tl_row_q <= 6'd0;
            tl_ctl_q <= 64'd0; tl_ctl2 <= 64'd0; tl_ctl3 <= 64'd0; tl_pay3 <= 1024'd0;
        end else begin
            sealed_d <= sealed;
            done <= 1'b0;
            f_g <= fault; fc_g <= fault_code;   // hold (the pw addr-0 image start below overrides)
            d_any = 1'b0; d_col = 1'b0; d_u = {UB{1'b0}};
            // ---------------- image load (never while any segment plays)
            if (pw_v) begin
                if (pw_addr == 10'd0) begin
                    f_g <= running; fc_g <= running ? 6'b010000 : 6'd0;
                    loading <= 1'b1; sealed <= 1'b0; pw_cnt <= 11'd1; dw_cnt <= 4'd0; meta_rows <= 10'd0;
                end else begin
                    if (running || !loading || {1'b0, pw_addr} != pw_cnt) begin fx4[0] = 1'b1; end
                    pw_cnt <= pw_cnt + 11'd1;
                    if (pw_addr == 10'd1017) meta_rows <= pw_data[27:18];
                end
            end
            if (dw_v) begin
                if (running || !loading || pw_cnt != 11'd1024 || {1'b0, dw_addr} != dw_cnt || pw_v) begin
                    fx4[1] = 1'b1;
                end
                dw_cnt <= dw_cnt + 4'd1;
                if (dw_addr != 3'd7) dwr[dw_addr] <= dw_data;
                else begin
                    loading <= 1'b0;
                    if (seal_bad) begin fx4[2] = 1'b1; end else sealed <= 1'b1;
                end
            end
            if (m_dbl) begin fx5 = 1'b1; end
            if (rom_fault || rom_mis) begin fx4[3] = 1'b1; end
            if (m_rce) rdb_oh <= {m_rbank, !m_rbank};
            // ---------------- playheads
            for (k = 0; k < NU; k = k + 1) begin
                if (go_u[k]) begin
                    if (start_bad) begin fx0[k] = 1'b1; end
                    else if (g_cnt_nz) begin
                        run_q[k] <= 1'b1; f_lo[k] <= g_first[1:0]; f_hi[k] <= g_first[9:2]; f_rem[k] <= g_cnt[9:0]; i_rem[k] <= g_cnt[9:0];
                        tcount[k] <= {{(TW-1){1'b0}}, 1'b1}; ht_q[k] <= {TW{1'b0}};
                        dq[k] <= (MUT == 1 || MUT == 34) ? {{(TW-1){1'b0}}, 1'b1} : {{(TW-2){1'b0}}, 2'd2};
                        fifo_n[k] <= 4'd0; infl[k] <= 4'd0; wh[k] <= 1'b0; rp_oh[k] <= 8'd1;
                        rce_q[k] <= 1'b0; rce2_q[k] <= 1'b0; rd_v[k] <= 1'b0; fire_q[k] <= 1'b0;
                    end else begin
                        dn[k] = 1'b1;
                    end
                end else if (!frz_u[k]) begin
                    fire_q[k] <= fire_n[k];
                    dq[k] <= dq_n[k];
                    if (nh_v[k]) begin hc_q[k] <= nh_c[k]; ht_q[k] <= nh_t[k]; end
                    if (run_q[k]) begin
                        tcount[k] <= tcount[k] + {{(TW-1){1'b0}}, 1'b1};
                        if (&tcount[k]) begin fx4g[k] = 1'b1; end
                    end
                    rce_q[k] <= gnt[k]; rbank_q[k] <= waddr[k][3]; rrow_q[k] <= waddr[k][9:4]; r_n_q[k] <= f_n[k];
                    if (gnt[k]) begin f_hi[k] <= f_hi[k] + 8'd1; f_rem[k] <= f_rem[k] - {7'd0, f_n[k]}; end
                    rce2_q[k] <= rce_q[k]; r_n2_q[k] <= r_n_q[k];
                    rd_v[k] <= (CALENDAR_ROM != 0) ? rce2_q[k] : rce_q[k];
                    rd_n[k] <= (CALENDAR_ROM != 0) ? r_n2_q[k] : r_n_q[k];
                    // CTLM7: both outcomes from registers, the late grant only selects
                    infl[k] <= gnt[k] ? infl_g[k] : infl_ng[k];
                    if (rd_v[k]) begin
                        wh[k] <= !wh[k];
                        if (zd[k]) begin fx4h[k] = 1'b1; end
                    end
                    fifo_n[k] <= fifo_n[k] + {1'b0, (rd_v[k] ? rd_n[k] : 3'd0)} - (fire_q[k] ? 4'd1 : 4'd0);
                    if (late[k]) begin fx2[k] = 1'b1; end
                    if (fire_q[k]) begin
                        rp_oh[k] <= rpa_oh[k]; i_rem[k] <= i_rem[k] - 10'd1;
                        if (i_rem[k] == 10'd1) begin
                            run_q[k] <= 1'b0;
                            dn[k] = 1'b1;
                        end
                    end
                end
            end
            // CTLM7: at most one completion per playhead per edge; any / two-or-more / last index
            // in parallel (was a serial chain through all NU playheads)
            d_any = |dn; d_col = |(dn & (dn - {{(NU-1){1'b0}}, 1'b1}));
            for (k = 0; k < NU; k = k + 1) if (dn[k]) d_u = k[UB-1:0];
            // CTLM8 (same values): run completions dr come from registers only; the start's late refusal
            // (start_bad: pin decode -> range adder) only selects -- no dn - 1 / last-index chain after it.
            // dn = dr | (go_u & sd): a started playhead never also completes by run on the same edge.
            sd = !start_bad && !g_cnt_nz;
            dr_any = 1'b0; dr_hi = {UB{1'b0}}; g_any = 1'b0; g_idx = {UB{1'b0}};
            for (k = 0; k < NU; k = k + 1) begin
                dr[k] = !go_u[k] && !frz_u[k] && fire_q[k] && i_rem[k] == 10'd1;
                if (dr[k]) begin dr_any = 1'b1; dr_hi = k[UB-1:0]; end
                if (go_u[k]) begin g_any = 1'b1; g_idx = k[UB-1:0]; end
            end
            dr_col = |(dr & (dr - {{(NU-1){1'b0}}, 1'b1}));
            g_top = !dr_any || (g_idx > dr_hi);
            d_any = dr_any || (g_any && sd);
            d_col = dr_col || (g_any && sd && dr_any);
            d_u = (g_any && sd && g_top) ? g_idx : dr_any ? dr_hi : {UB{1'b0}};
            if (d_any) begin done <= 1'b1; done_user <= d_u; end
            if (NU > 1 && d_col) begin fx3[0] = 1'b1; end
            // ---------------- issue register (one word an edge, all playheads)
            cmd <= 116'd0; loc_emb <= 1'b0; loc_seg <= 1'b0; su_issue <= 1'b0; xc_issue <= 1'b0; table_load <= 1'b0;
            // TLOAD pipeline: issue edge -> macro read -> tl register (-> +1 edge under MUT 5)
            tl_rce_q <= tl_fire; tl_v2 <= tl_rce_q; tl_v3 <= tl_v2;
            if (tl_fire) begin
                tl_row_q <= tl_row;
                tl_ctl_q <= {1'b1, tl_kind, ic[16:13], ic[20:17], ic[44:21], ic[72:45]};
            end
            tl_ctl2 <= tl_ctl_q; tl_ctl3 <= tl_ctl2;
            tl_pay3 <= (MUT == 4) ? {rd[0], rd[1]} : {rd[1], rd[0]};
            if (MUT == 5) tl <= tl_v3 ? {tl_ctl3, tl_pay3} : 1088'd0;
            else          tl <= tl_v2 ? {tl_ctl2, (MUT == 4) ? {rd[0], rd[1]} : {rd[1], rd[0]}} : 1088'd0;
            if (NU > 1 && i_col) begin fx1 = 1'b1; end
            if (i_any) begin
                if (NU > 1) cmd_user <= ru;
                // fx3[1] / fx4[4..6] are set flat below (CTLM7)
                if (i_loc) begin
                    if (i_kind == 3'd1) loc_emb <= 1'b1;
                    else if (i_kind == 3'd2) begin loc_seg <= 1'b1; loc_base <= ic[15:4]; end
                    else if (tr_go) begin
                        if (!tr_bad) begin table_load <= 1'b1; table_stage <= ic[9:4]; table_user <= 2'(ru); end
                    end
                    else if (i_kind == 3'd3) begin end
                    else begin end
                end else begin
                    cmd <= rc;
                    su_issue <= i_kind == 3'd1; su_pidx <= rc[12:4]; xc_issue <= i_kind == 3'd0;
                end
            end
            // CTLM7: every fault site above sets its own flag; fault / fault_code are set
            // once here from balanced ORs (was a serial priority chain of 15 sites).  This
            // stays last, so it overrides the pw addr-0 'fault <= running' exactly as before.
            // CTLM7: the issue-register fault sites, flat (same guards as the if nest above)
            fx3[1] = i_any && (NU > 1) && r_bad;
            fx4[4] = i_any && i_loc && i_kind != 3'd1 && i_kind != 3'd2 && tr_go && tr_bad;
            fx4[5] = i_any && i_loc && i_kind != 3'd1 && i_kind != 3'd2 && !tr_go && i_kind == 3'd3 && tl_bad;
            fx4[6] = i_any && i_loc && i_kind != 3'd1 && i_kind != 3'd2 && !tr_go && i_kind != 3'd3;
            // the raw site flags are registered; their OR is taken after the flops (exact)
            r4 <= fx4; r4g <= fx4g; r4h <= fx4h; r3 <= fx3; r2 <= fx2; r1 <= fx1; r0 <= fx0; r5 <= fx5;
        end
    end
    // fault(t+1) = F(t) | (pw addr-0 ? running : fault(t)) exactly, as two registers (set / hold)
    assign fault = f_p | f_g;
    assign fault_code = fc_p | fc_g;
    assign image_ready = sealed && !fault;
endmodule

// Parameter identity and keep_hierarchy retain physically distinct selector
// flops through Yosys flatten/opt_merge. Each output select bit feeds32data bits.
(* keep_hierarchy = 1 *)
module qfd_calpipe_selector #(parameter integer COPY_ID = 0, parameter integer MUT = 0) (
    input wire ck, rst_n, pop, clear, pending_in, bypass_in,
    output reg [3:0] sel, output reg pending, bypass
);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin sel <= (MUT == 33) ? 4'b0001 : 4'b0010; pending <= 1'b0; bypass <= 1'b0; end
        else begin
            pending <= pending_in; bypass <= bypass_in;
            if (clear) sel <= (MUT == 33) ? 4'b0001 : 4'b0010;
            else if (pop) sel <= {sel[2:0], sel[3]};
        end
endmodule

(* keep_hierarchy = 1 *)
module qfd_calpipe_readvalid #(parameter integer COPY_ID = 0) (
    input wire ck, rst_n, clear, freeze, read_ce, output reg valid
);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) valid <= 1'b0;
        else if (clear) valid <= 1'b0;
        else if (!freeze) valid <= read_ce;
endmodule

(* keep_hierarchy = 1 *)
module qfd_calpipe_mask #(parameter integer COPY_ID = 0) (
    input wire ck, write_ce, mask_in, output reg mask
);
    always @(posedge ck) if (write_ce) mask <= mask_in;
endmodule

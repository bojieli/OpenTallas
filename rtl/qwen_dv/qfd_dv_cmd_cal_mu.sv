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
//   RUNTIME context (MU-DQ-BOOTCTX 10-19, coordinator 0kg (1), CTX_DW 1 only): a DW write with dw_addr 5 while the image
//   is SEALED and not loading (no PW on the edge) is the face's runtime context word (qfd_sys_face_fill_ctx, from the
//   KV die's kind12 HOST context record) -- not an image write and not a fault (it was an image-order fault before):
//   dwr[5] takes the word (the same register, no new storage) and ctx_rt pulses on the next edge with ctx_dw[63:0] =
//   the word.  The segment store, the seal and every playhead are untouched.  CTX_DW 0: unchanged (a fault).
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
    output reg  [1087:0] tl,                        // TLOAD stream table word (W5 st_wi), one edge, else 0
    output reg  [75:0]   program_obs,
    output reg  [68:0]   descriptor_obs,
    output wire          image_ready,
    output wire          running,
    output wire [NU-1:0] running_u,
    output reg           done,
    output reg  [UB-1:0] done_user,
    output reg           fault,
    output reg  [5:0]    fault_code,
    output wire [127:0]  ctx_dw,                    // {DW6, DW5} of the sealed image (CTX_DW)
    output wire          ctx_load,                  // one edge: the image (with its context record) was sealed (CTX_DW)
    output reg           ctx_rt                     // one edge: a runtime context word is in ctx_dw[63:0] (CTX_DW)
);
    // ================================================================ image load (as qfd_dv_cmd_cal)
    reg         loading, sealed, sealed_d;
    reg  [10:0] pw_cnt;
    reg  [3:0]  dw_cnt;
    reg  [9:0]  meta_rows;
    reg  [63:0] dwr [0:6];
    wire [63:0] d0 = dwr[0];
    wire [9:0]  base = d0[25:16];
    wire [8:0]  nent = d0[8:0];
    reg         seal_bad;
    integer     s;
    always @* begin
        seal_bad = d0[63:32] != 32'h43414c44 || d0[31:26] != 6'd0 || d0[15:9] != 7'd0 || base[2:0] != 3'd0 ||
                   nent == 9'd0 || {1'b0, base} + {1'b0, nent, 1'b0} > 11'd976 || {4'd0, base} < {meta_rows, 4'd0} ||
                   (CTX_DW == 0 && (dwr[5] != 64'd0 || dwr[6] != 64'd0)) || dw_data != 64'd0;
        for (s = 1; s <= 4; s = s + 1)
            if (dwr[s][63:32] != 32'd0 ||
                (dwr[s][15:0] != 16'd0 && (dwr[s][17:16] != 2'd0 || {1'b0, dwr[s][31:16]} + {1'b0, dwr[s][15:0]} > {8'd0, nent})))
                seal_bad = 1'b1;
    end
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
    qkd_program_pw_observer u_obs (.macro_ce(m_ce), .macro_row({pw_row2, pw_row2}), .macro_data(m_data),
        .macro_mask(m_mask), .consumed_v(ob_v), .consumed_addr(ob_addr), .consumed_data(ob_data), .full_word(ob_full));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin program_obs <= 76'd0; descriptor_obs <= 69'd0; end
        else begin
            program_obs <= {ob_v, ob_full, ob_addr, ob_data};
            descriptor_obs <= {dw_v2, 1'b1, dw_a2, dw_d2};
        end

    // ================================================================ per-playhead state
    reg  [NU-1:0] run_q;
    reg  [9:0]    f_idx [0:NU-1], f_rem [0:NU-1], i_rem [0:NU-1];
    reg  [3:0]    fifo_n [0:NU-1], infl [0:NU-1];
    reg  [2:0]    wp [0:NU-1], rp [0:NU-1];
    reg  [115:0]  q_cmd [0:8*NU-1];
    reg  [TW-1:0] q_t [0:8*NU-1];
    reg  [TW-1:0] t_acc [0:NU-1], tcount [0:NU-1];
    reg  [NU-1:0] rce_q, rbank_q, rd_v, rd_bank;
    reg  [5:0]    rrow_q [0:NU-1];
    reg  [2:0]    rd_n [0:NU-1], r_n_q [0:NU-1];
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
    wire [511:0] rd [0:1];
    reg          tl_rce_q, tl_v2, tl_v3; reg [5:0] tl_row_q; reg [63:0] tl_ctl_q, tl_ctl2, tl_ctl3; reg [1023:0] tl_pay3;
    wire         tl_fire;
    generate for (g = 0; g < 2; g = g + 1) begin : g_m
        ot_sram_1r1w_64x512_m1_r2c2 u_pm (.clk(ck), .r_ce_in((m_rce && (m_rbank == g[0])) || tl_rce_q),
            .r_addr_in(tl_rce_q ? tl_row_q : m_rrow), .rd_out(rd[g]),
            .w_ce_in(m_ce[g]), .w_addr_in(pw_row2), .wd_in(m_data[512*g +: 512]), .w_mask_in(m_mask[512*g +: 512]),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    end endgenerate

    // ================================================================ segment start
    wire       boot_go = sealed && !sealed_d && (MUT != 3);
    assign     ctx_dw = {dwr[6], dwr[5]};
    assign     ctx_load = (CTX_DW != 0) && sealed && !sealed_d && !fault;
    wire [1:0] sseg = (stage == 6'd0) ? 2'd0 : (stage == LAST_STAGE[5:0]) ? 2'd2 : 2'd1;
    wire       go = start || boot_go;
    wire [1:0] gseg = boot_go ? 2'd3 : sseg;
    wire [63:0] gd = dwr[{1'b0, gseg} + 3'd1];
    wire        g_rng = start && start_rng && !boot_go;
    wire [15:0] g_first = (g_rng && MUT != 21) ? {6'd0, start_first} : gd[31:16];
    wire [15:0] g_cnt = (g_rng && MUT != 21) ? {6'd0, start_cnt} : gd[15:0];
    wire        rng_bad = g_rng && (start_cnt == 10'd0 || start_first[1:0] != 2'd0 ||
                                    {1'b0, start_first} + {1'b0, start_cnt} > {2'd0, nent});
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

    // ================================================================ fetch / issue, per playhead (combinational)
    reg  [NU-1:0]  can_read, gnt, hv, fire, late, hgo;
    reg  [9:0]     waddr [0:NU-1];
    reg  [2:0]     f_n [0:NU-1];
    reg  [127:0]   ent [0:NU-1][0:3];
    reg  [TW-1:0]  et [0:NU-1][0:3];
    reg  [NU-1:0]  zd;
    reg  [115:0]   hc [0:NU-1];
    reg  [TW-1:0]  ht [0:NU-1];
    reg            any_gnt;
    integer        u, j;
    always @* begin
        any_gnt = 1'b0;
        for (u = 0; u < NU; u = u + 1) begin
            waddr[u] = base + {f_idx[u][8:0], 1'b0};
            f_n[u] = (f_rem[u] >= 10'd4) ? 3'd4 : f_rem[u][2:0];
            can_read[u] = run_q[u] && f_rem[u] != 10'd0 && ({1'b0, fifo_n[u]} + {1'b0, infl[u]} + 5'd4 <= 5'd8);
            // lowest-index playhead that is not being (re)started this edge takes the read port (none on a TLOAD
            // issue edge: the block read owns the next edge's port)
            gnt[u] = can_read[u] && !frz_u[u] && !any_gnt && !tl_fire;
            if (can_read[u] && !frz_u[u]) any_gnt = 1'b1;
            zd[u] = 1'b0;
            for (j = 0; j < 4; j = j + 1) begin
                ent[u][j] = (MUT == 2) ? {rd[rd_bank[u]][128*j +: 64], rd[rd_bank[u]][128*j + 64 +: 64]}
                                       : rd[rd_bank[u]][128*j +: 128];
                if ((j < rd_n[u]) && ent[u][j][127:116] == 12'd0) zd[u] = 1'b1;
            end
            et[u][0] = t_acc[u] + {{(TW-12){1'b0}}, ent[u][0][127:116]};
            for (j = 1; j < 4; j = j + 1) et[u][j] = et[u][j-1] + {{(TW-12){1'b0}}, ent[u][j][127:116]};
            hc[u] = q_cmd[8*u + {29'd0, rp[u]}];
            ht[u] = q_t[8*u + {29'd0, rp[u]}] + ((MUT == 1) ? {{(TW-1){1'b0}}, 1'b1} : {TW{1'b0}});
            hv[u] = fifo_n[u] != 4'd0;
            fire[u] = run_q[u] && hv[u] && tcount[u] == ht[u];
            late[u] = run_q[u] && hv[u] && tcount[u] > ht[u];
            hgo[u] = fire[u] && !frz_u[u] && hc[u][0];
        end
    end
    // the issuing playhead: the lowest with a go entry this edge; a second one is a collision
    reg  [UB-1:0] iu; reg i_any, i_col;
    integer       c;
    always @* begin
        iu = {UB{1'b0}}; i_any = 1'b0; i_col = 1'b0;
        for (c = NU - 1; c >= 0; c = c - 1) if (hgo[c]) begin iu = c[UB-1:0]; end
        for (c = 0; c < NU; c = c + 1) if (hgo[c]) begin if (i_any) i_col = 1'b1; i_any = 1'b1; end
    end
    // relocation of the issued word for its user (NU > 1; user 0 adds 0)
    wire [115:0]  ic = hc[iu];
    wire [2:0]    i_kind = ic[3:1];
    wire          i_loc = ic[115:112] == 4'hE;
    // TLOAD (LOCAL kind 3): block row / header / checks (as qfd_dv_cmd_cal)
    assign        tl_fire = i_any && i_loc && i_kind == 3'd3;
    wire [5:0]    tl_row = ic[9:4];
    wire [2:0]    tl_kind = ic[12:10];
    wire [10:0]   tl_lo = {1'b0, tl_row, 4'd0}, tl_hi = tl_lo + 11'd16;
    wire          tl_bad = tl_kind == 3'd0 || tl_kind[2] || ic[111:73] != 39'd0 || {4'd0, tl_row} < meta_rows ||
                           tl_row >= 6'd61 || (tl_lo < {1'b0, base} + {1'b0, nent, 1'b0} && tl_hi > {1'b0, base});
    wire [UB-1:0] ru = (MUT == 11 && NU > 1) ? ((iu == NU - 1) ? {UB{1'b0}} : iu + 1'b1) : iu;
    wire [24:0]   ub = (NU > 1 && MUT != 12) ? 25'(ru) * 25'(UVM_STRIDE) : 25'd0;
    wire [9:0]    up = (NU > 1 && MUT != 12) ? 10'(ru) * 10'(PIDX_STRIDE) : 10'd0;
    wire [24:0]   r_ar = {1'b0, ic[27:4]} + ub, r_dd = {1'b0, ic[51:28]} + ub, r_em = {1'b0, ic[77:54]} + ub,
                  r_db = {1'b0, ic[49:26]} + ub;
    wire [9:0]    r_px = {1'b0, ic[12:4]} + up;
    reg  [115:0]  rc; reg r_bad;
    always @* begin
        rc = ic; r_bad = 1'b0;
        if (NU > 1 && !i_loc) begin
            case (i_kind)
                3'd4: begin rc[27:4] = r_ar[23:0]; rc[51:28] = r_dd[23:0]; rc[77:54] = r_em[23:0];
                            r_bad = r_ar[24] | r_dd[24] | r_em[24]; end
                3'd2: if (ic[24]) begin rc[49:26] = r_db[23:0]; r_bad = r_db[24]; end
                3'd1: begin rc[12:4] = r_px[8:0]; r_bad = r_px[9]; end
                3'd0: if (ic[5:4] == 2'd0) begin
                          if (ic[23 + UTAG_LSB +: UB] != {UB{1'b0}}) r_bad = 1'b1;
                          rc[23 + UTAG_LSB +: UB] = ru;
                      end
                3'd6: if (UFOLD != 0) begin
                          if (ic[9:8] != 2'd0) r_bad = 1'b1;
                          rc[9:8] = (MUT == 16) ? 2'd0 : 2'(ru);
                      end
                default: ;
            endcase
            // STN user (UFOLD): beside the dbase relocation above, any dst
            if (UFOLD != 0 && i_kind == 3'd2) begin
                if (ic[52:51] != 2'd0) r_bad = 1'b1;
                rc[52:51] = (MUT == 16) ? 2'd0 : 2'(ru);
            end
        end
    end
    generate if (UFOLD != 0 && (NU < 2 || UB > 2)) begin : g_ufold_bad
        initial $error("qfd_dv_cmd_cal_mu: UFOLD needs 2 <= NU <= 4");
    end endgenerate

    // ================================================================ sequential
    integer k;
    reg     d_any, d_col; reg [UB-1:0] d_u;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            loading <= 1'b0; sealed <= 1'b0; sealed_d <= 1'b0; pw_cnt <= 11'd0; dw_cnt <= 4'd0; meta_rows <= 10'd0;
            for (s = 0; s < 7; s = s + 1) dwr[s] <= 64'd0;
            ctx_rt <= 1'b0;
            run_q <= {NU{1'b0}}; done <= 1'b0; done_user <= {UB{1'b0}}; fault <= 1'b0; fault_code <= 6'd0;
            for (k = 0; k < NU; k = k + 1) begin
                f_idx[k] <= 10'd0; f_rem[k] <= 10'd0; i_rem[k] <= 10'd0; fifo_n[k] <= 4'd0; infl[k] <= 4'd0;
                wp[k] <= 3'd0; rp[k] <= 3'd0; t_acc[k] <= {TW{1'b0}}; tcount[k] <= {TW{1'b0}};
                rrow_q[k] <= 6'd0; r_n_q[k] <= 3'd0; rd_n[k] <= 3'd0;
            end
            rce_q <= {NU{1'b0}}; rbank_q <= {NU{1'b0}}; rd_v <= {NU{1'b0}}; rd_bank <= {NU{1'b0}};
            cmd <= 116'd0; cmd_user <= {UB{1'b0}}; loc_emb <= 1'b0; loc_seg <= 1'b0; loc_base <= 12'd0;
            su_issue <= 1'b0; su_pidx <= 9'd0; xc_issue <= 1'b0;
            tl <= 1088'd0; tl_rce_q <= 1'b0; tl_v2 <= 1'b0; tl_v3 <= 1'b0; tl_row_q <= 6'd0;
            tl_ctl_q <= 64'd0; tl_ctl2 <= 64'd0; tl_ctl3 <= 64'd0; tl_pay3 <= 1024'd0;
        end else begin
            sealed_d <= sealed;
            done <= 1'b0;
            d_any = 1'b0; d_col = 1'b0; d_u = {UB{1'b0}};
            // ---------------- image load (never while any segment plays)
            if (pw_v) begin
                if (pw_addr == 10'd0) begin
                    fault <= running; fault_code <= running ? 6'b010000 : 6'd0;
                    loading <= 1'b1; sealed <= 1'b0; pw_cnt <= 11'd1; dw_cnt <= 4'd0; meta_rows <= 10'd0;
                end else begin
                    if (running || !loading || {1'b0, pw_addr} != pw_cnt) begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                    pw_cnt <= pw_cnt + 11'd1;
                    if (pw_addr == 10'd1017) meta_rows <= pw_data[27:18];
                end
            end
            ctx_rt <= 1'b0;
            if (dw_v && CTX_DW != 0 && sealed && !loading && !pw_v && dw_addr == 3'd5) begin
                dwr[5] <= dw_data; ctx_rt <= 1'b1;                 // runtime context word (see the header)
            end else if (dw_v) begin
                if (running || !loading || pw_cnt != 11'd1024 || {1'b0, dw_addr} != dw_cnt || pw_v) begin
                    fault <= 1'b1; fault_code[4] <= 1'b1;
                end
                dw_cnt <= dw_cnt + 4'd1;
                if (dw_addr != 3'd7) dwr[dw_addr] <= dw_data;
                else begin
                    loading <= 1'b0;
                    if (seal_bad) begin fault <= 1'b1; fault_code[4] <= 1'b1; end else sealed <= 1'b1;
                end
            end
            if (m_dbl) begin fault <= 1'b1; fault_code[5] <= 1'b1; end
            // ---------------- playheads
            for (k = 0; k < NU; k = k + 1) begin
                if (go_u[k]) begin
                    if (start_bad) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                    else if (g_cnt != 16'd0) begin
                        run_q[k] <= 1'b1; f_idx[k] <= g_first[9:0]; f_rem[k] <= g_cnt[9:0]; i_rem[k] <= g_cnt[9:0];
                        t_acc[k] <= {TW{1'b0}}; tcount[k] <= {{(TW-1){1'b0}}, 1'b1};
                        fifo_n[k] <= 4'd0; infl[k] <= 4'd0; wp[k] <= 3'd0; rp[k] <= 3'd0; rce_q[k] <= 1'b0; rd_v[k] <= 1'b0;
                    end else begin
                        if (d_any) d_col = 1'b1;
                        d_any = 1'b1; d_u = k[UB-1:0];
                    end
                end else if (!frz_u[k]) begin
                    if (run_q[k]) begin
                        tcount[k] <= tcount[k] + {{(TW-1){1'b0}}, 1'b1};
                        if (&tcount[k]) begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                    end
                    rce_q[k] <= gnt[k]; rbank_q[k] <= waddr[k][3]; rrow_q[k] <= waddr[k][9:4]; r_n_q[k] <= f_n[k];
                    if (gnt[k]) begin f_idx[k] <= f_idx[k] + 10'd4; f_rem[k] <= f_rem[k] - {7'd0, f_n[k]}; end
                    rd_v[k] <= rce_q[k]; rd_bank[k] <= rbank_q[k]; rd_n[k] <= r_n_q[k];
                    infl[k] <= infl[k] + (gnt[k] ? {1'b0, f_n[k]} : 4'd0) - (rd_v[k] ? {1'b0, rd_n[k]} : 4'd0);
                    if (rd_v[k]) begin
                        for (j = 0; j < 4; j = j + 1)
                            if (j < rd_n[k]) begin
                                q_cmd[8*k + {29'd0, 3'(wp[k] + j[2:0])}] <= ent[k][j][115:0];
                                q_t[8*k + {29'd0, 3'(wp[k] + j[2:0])}] <= et[k][j];
                            end
                        wp[k] <= wp[k] + rd_n[k];
                        t_acc[k] <= et[k][rd_n[k][1:0] - 2'd1];
                        if (zd[k]) begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                    end
                    fifo_n[k] <= fifo_n[k] + {1'b0, (rd_v[k] ? rd_n[k] : 3'd0)} - (fire[k] ? 4'd1 : 4'd0);
                    if (late[k]) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
                    if (fire[k]) begin
                        rp[k] <= rp[k] + 3'd1; i_rem[k] <= i_rem[k] - 10'd1;
                        if (i_rem[k] == 10'd1) begin
                            run_q[k] <= 1'b0;
                            if (d_any) d_col = 1'b1;
                            d_any = 1'b1; d_u = k[UB-1:0];
                        end
                    end
                end
            end
            if (d_any) begin done <= 1'b1; done_user <= d_u; end
            if (NU > 1 && d_col) begin fault <= 1'b1; fault_code[3] <= 1'b1; end
            // ---------------- issue register (one word an edge, all playheads)
            cmd <= 116'd0; loc_emb <= 1'b0; loc_seg <= 1'b0; su_issue <= 1'b0; xc_issue <= 1'b0;
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
            if (NU > 1 && i_col) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (i_any) begin
                if (NU > 1) cmd_user <= ru;
                if (NU > 1 && r_bad) begin fault <= 1'b1; fault_code[3] <= 1'b1; end
                if (i_loc) begin
                    if (i_kind == 3'd1) loc_emb <= 1'b1;
                    else if (i_kind == 3'd2) begin loc_seg <= 1'b1; loc_base <= ic[15:4]; end
                    else if (i_kind == 3'd3) begin if (tl_bad) begin fault <= 1'b1; fault_code[4] <= 1'b1; end end
                    else begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                end else begin
                    cmd <= rc;
                    su_issue <= i_kind == 3'd1; su_pidx <= rc[12:4]; xc_issue <= i_kind == 3'd0;
                end
            end
        end
    end
    assign image_ready = sealed && !fault;
endmodule

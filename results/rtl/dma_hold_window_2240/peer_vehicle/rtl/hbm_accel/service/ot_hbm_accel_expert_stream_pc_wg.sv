// Additive Opt4 candidate. Original LA remains byte-identical.
// Eight-sector GU descriptors use absolute j0 and explicit keep-open.
`timescale 1ps/1fs
// HA4 R5a-LA (HBM accelerator): routed-expert stream sequencer for ONE HBM3E pseudo-channel with a
// one-deep descriptor LOOKAHEAD.  Successor of ot_hbm_accel_expert_stream_pc (R5a, the 52ce3e9c1 r6
// sequencer + `notice`); default-off (ENABLE=0 ties every output to zero); nothing pinned
// instantiates it.
//
// Why: R5a streams one (expert, PC) descriptor of 49 sectors at a time and every expert lives in
// bank set 0, so each new expert closes the same four banks (tRTP + tRP) and reopens them (tRCD):
// ~44 idle cycles per 49 RDs, 0.395 TB/s of the 1.0 TB/s stack (results/rtl/hbm_accel_ha4_20261004).
//
// What changes (everything else is the R5a logic):
//  1. A descriptor carries a bank SET (desc_set): PC-local sector j of the descriptor lives in bank
//     {desc_set + j[9:7], j[1:0]} (mod 8 sets), column j[6:2], row desc_row.  The loader places
//     expert e in set e mod NSETS (ot_hbm_accel_expert_fetch_stream_la), so consecutive experts
//     usually sit in different banks.
//  2. One NEXT descriptor register (nx_*).  desc_r = !nx_v: a descriptor is accepted while the
//     current one streams.  When the current stream is in its last set and the next descriptor's
//     set differs, the "set k+1" ACT group targets the NEXT descriptor's set and row, so its banks
//     are open (tRCD elapsed) when the current stream issues its last RD.  At the last RD the next
//     descriptor is promoted in the same cycle (no idle cycle); only banks that the lookahead did
//     not open for it become stale.  The ACT row is registered with the command (c_row).
//  3. Refresh keys protect the next descriptor's set and every set in `prot` (the sets of the
//     task's queued experts, from the dispatcher); while idle, `notice` protects NOTICE_PROT.
//     Unprotected sets are taken in IDLE order (IDLE0 first), so a parking set the loader leaves
//     empty (set 7 with NSETS = 7) absorbs the refreshes of a routed window.
// DRAM rules and the strict refresh schedule are the R5a ones (checked by the bench).
module ot_hbm_accel_expert_stream_pc_wg #(
  parameter integer ENABLE   = 0,
  parameter integer REF_MODE = 1,
  parameter integer PC       = 0,
  parameter integer T_RCD = 19, T_RP = 16, T_RAS = 28, T_RTP = 6, T_CCDL = 3,
  parameter integer T_RRDS = 3, T_RRDL = 4, T_FAW = 15, T_RFC = 342, T_RFCPB = 196,
  parameter integer T_REFI = 3808, T_REFIPB = 118, T_RREFD = 8,
  parameter integer CRED = 64,
  parameter integer REF_PHASE = 0,
  parameter [7:0]   NOTICE_PROT = 8'h7F,
  parameter integer PULL = 16,
  parameter integer REPICK = 1,
  parameter integer RESERVE = 1,
  parameter integer TAILPULL = 12,
  parameter integer STEER = 0,
  parameter integer NWIN = 0,             // >0: cycles from `notice` rise to the routed window's first ACT
  parameter integer RAMP = 48,
  parameter integer IDLE0 = 7, IDLE1 = 3, IDLE2 = 4, IDLE3 = 2,
  parameter integer IDLE4 = 5, IDLE5 = 1, IDLE6 = 6, IDLE7 = 0
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [2:0] desc_set, input wire desc_bgx, input wire [10:0] desc_n,
  input wire [10:0] desc_j0, input wire desc_keep,
  input  wire        go, input wire next_posted, input wire notice, input wire [7:0] prot,
  output wire        row_v, output wire row_prio, input wire row_gnt,
  output wire [2:0]  row_op, output wire [4:0] row_bank, output wire [18:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  input  wire [2:0]  cred_ret,
  output wire        busy, output wire ref_fault
);
  localparam [2:0] PRE=0, ACT=1, RD=2, REFAB=4, PREALL=5, REFPB=6;
  generate if (!ENABLE) begin : off
    assign desc_r=0; assign row_v=0; assign row_prio=0; assign row_op=0; assign row_bank=0;
    assign row_row=0; assign col_v=0; assign col_bank=0; assign col_col=0; assign busy=0;
    assign ref_fault=0;
  end else begin : on
    localparam integer PERIOD = REF_MODE ? T_REFIPB : T_REFI;
    localparam integer LEAD   = T_RAS + T_RP + 4;
    localparam integer RW     = $clog2(2 * PERIOD + 4);
    localparam integer RPH    = REF_PHASE + ((REF_PHASE + PERIOD + PC) % 2);
    function automatic [2:0] idle_rank(input [2:0] s);
      idle_rank = (s==3'(IDLE0))?0:(s==3'(IDLE1))?1:(s==3'(IDLE2))?2:(s==3'(IDLE3))?3:
                  (s==3'(IDLE4))?4:(s==3'(IDLE5))?5:(s==3'(IDLE6))?6:7;
    endfunction
    reg [10:0] j, n; reg [18:0] row; reg [2:0] s0; reg bgx;
    reg [31:0] open, done, stale, refreshed, la;
    reg [1:0] rrds_c; reg [3:0] noact_c; reg [RW-1:0] ref_c; reg ref_pend; reg [4:0] rb; reg fault_r;
    reg [7:0] credit; reg running; reg [31:0] blk;
    reg streaming; reg [2:0] last; reg [10:0] nm1;
    reg nx_v; reg [18:0] nx_row; reg [2:0] nx_set; reg [10:0] nx_n; reg nx_bgx; reg [10:0] nx_j0; reg nx_keep, keep;
    reg [3:0] act_age; reg pull_ok;            // cycles since the last ACT (saturating); pulled REFpb allowed
    wire [2:0] kr = j[9:7];                 // set relative to the descriptor
    wire [2:0] ka = s0 + kr;                // absolute bank set
    wire [1:0] rd_bg = j[1:0] ^ {bgx, 1'b0};     // BG swizzle: a descriptor with bgx=1 starts at BG 2
    wire [4:0] rd_bank = {ka, rd_bg};
    // the "k+1" ACT group: the current descriptor's next set, else the NEXT descriptor's set
    wire k1_cur = (kr != 3'd7) && (kr + 3'd1 <= last);
    wire k1_nx  = !k1_cur && nx_v && (nx_set != ka) && (nx_n != 0);
    wire k1v    = k1_cur || k1_nx;
    wire [2:0] k1a = k1_cur ? ka + 3'd1 : nx_set;
    // ---- refresh windows -------------------------------------------------------------
    wire ref_due = (ref_c == 0);
    reg  phase;
    wire slot_next = (phase != 1'(PC % 2));
    wire [RW-1:0] ref_n = ref_due ? RW'(PERIOD - 1) : ref_c - 1'b1;
    wire ref_due_n = (ref_n == 0);
    wire act_block = REF_MODE ? (ref_n != 0 && ref_n < RW'(T_RREFD))
                              : (ref_n <= RW'(T_RP + T_RAS + 2));
    wire rd_block  = REF_MODE ? 1'b0 : (ref_c <= RW'(T_RP + T_RTP + 2));
    wire preall_ok = !REF_MODE && ref_n <= RW'(T_RP + 2) && ref_n >= RW'(T_RP) && (|open);
    // ---- row command (combinational) and its events ------------------------------------
    reg r_v, r_prio, r_la; reg [2:0] r_op; reg [4:0] r_bank; reg [18:0] r_row;
    reg c_v, c_prio, c_la; reg [2:0] c_op; reg [4:0] c_bank; reg [31:0] c_oh; reg [18:0] c_row;
    wire row_fire = c_v && row_gnt;
    wire [31:0] open_nx = !row_fire ? open : (c_op == ACT) ? (open | c_oh) : (c_op == PRE) ? (open & ~c_oh) :
                          (c_op == PREALL) ? 32'b0 : open;
    wire [31:0] la_nx = !row_fire ? la : (c_op == ACT && c_la) ? (la | c_oh) : (c_op == PRE) ? (la & ~c_oh) :
                        (c_op == PREALL) ? 32'b0 : la;
    wire rd_ok;
    wire [7:0] cr_inc = credit + 8'(cred_ret), cr_dec = credit + 8'(cred_ret) - 8'd1;
    // ---- per-bank timing state (down-counters; 0 = allowed) ------------------------------
    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy;
    wire [223:0] keys;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      reg [4:0] rcd, ras; reg [8:0] aok; reg [2:0] rtp;
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = rd_ok && rd_bank == 5'(b);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; end
        else begin
          if (act_e) begin rcd <= 5'(T_RCD - 1); ras <= 5'(T_RAS - 1); end
          else begin if (rcd != 0) rcd <= rcd - 1'b1; if (ras != 0) ras <= ras - 1'b1; end
          if (rd_e) rtp <= 3'(T_RTP - 1); else if (rtp != 0) rtp <= rtp - 1'b1;
          if (act_e) aok <= 9'(T_RAS + T_RP - 1);
          else if (rfa_e) aok <= 9'(T_RFC - 1);
          else if (rfp_e) aok <= 9'(T_RFCPB - 1);
          else if (pre_e && aok < 9'(T_RP)) aok <= 9'(T_RP - 1);
          else if (aok != 0) aok <= aok - 1'b1;
        end
      assign rcd_z[b] = (rcd == 0); assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0);
      assign aok_z[b] = (aok == 0); assign aok_busy[b] = (aok > 9'(LEAD));
      // REFpb key (lower = refreshed first): 127 refreshed; streaming: open 24 (finished/stale) /
      // 32, the current descriptor's sets within two 16..18, the next descriptor's set or a queued
      // expert's set 16, upcoming = distance, unprotected 8 + IDLE rank; idle: protected (notice
      // or queued) 16, else IDLE rank (+32 open); +64 if still busy from an earlier tRFCpb / tRC.
      localparam [2:0] S = 3'(b >> 2);
      wire [2:0] d = S - ka;
      wire ahead = (d <= last - kr) || next_posted;
      wire protS = prot[S] || (nx_v && S == nx_set);
      // RESERVE: the parking set (outside NOTICE_PROT) is refreshed last in a round except under
      // `notice` before the ids arrive, so it is still unrefreshed when a routed window opens and absorbs
      // the REFpbs due before `prot` is known; once streaming, unneeded sets absorb them.
      wire park = RESERVE != 0 && !NOTICE_PROT[S];
      wire [6:0] base = !streaming ? (open[b] ? 7'd32 + 7'(idle_rank(S)) :
                                      (protS || (notice && NOTICE_PROT[S])) ? 7'd16 :
                                      (park && !notice) ? 7'd15 : 7'(idle_rank(S))) :
                        open[b] ? ((done[b] || stale[b]) ? 7'd24 : 7'd32) :
                        (ahead && d <= 3'd2) ? 7'd16 + 7'(3'd2 - d) :
                        protS ? 7'd16 :
                        park ? 7'd15 :
                        ahead ? 7'(d) : 7'd8 + 7'(idle_rank(S));
      assign keys[b*7 +: 7] = refreshed[b] ? 7'd127 : base + ((!open[b] && aok_busy[b]) ? 7'd64 : 7'd0);
    end
    // ---- per-bank-group state ----------------------------------------------------------
    wire [3:0] rrdl_z, ccdl_z, faw_z;
    for (genvar g = 0; g < 4; g = g + 1) begin : bgs
      reg [2:0] rrdl; reg [1:0] ccdl; reg [3:0] faw;
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      wire faw_take = row_fire && c_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rrdl <= 0; ccdl <= 0; faw <= 0; end
        else begin
          if (act_g) rrdl <= 3'(T_RRDL - 1); else if (rrdl != 0) rrdl <= rrdl - 1'b1;
          if (rd_ok && rd_bg == 2'(g)) ccdl <= 2'(T_CCDL - 1); else if (ccdl != 0) ccdl <= ccdl - 1'b1;
          if (faw_take) faw <= 4'(T_FAW - 1); else if (faw != 0) faw <= faw - 1'b1;
        end
      assign rrdl_z[g] = (rrdl == 0); assign ccdl_z[g] = (ccdl == 0); assign faw_z[g] = (faw == 0);
    end
    wire faw_ok = |faw_z;
    // ---- REFpb bank choice: argmin of keys, ties to the lowest bank (registered tree) ----
    function automatic [8:0] min4(input [27:0] k4, input [1:0] dummy);
      reg [6:0] ka4, kb4; reg ia, ib;
      begin
        ka4 = (k4[13:7] < k4[6:0]) ? k4[13:7] : k4[6:0];   ia = (k4[13:7] < k4[6:0]);
        kb4 = (k4[27:21] < k4[20:14]) ? k4[27:21] : k4[20:14]; ib = (k4[27:21] < k4[20:14]);
        min4 = (kb4 < ka4) ? {kb4, 1'b1, ib} : {ka4, 1'b0, ia};
      end
    endfunction
    reg [6:0] s1k [0:7]; reg [4:0] s1i [0:7]; reg [6:0] s2k [0:1]; reg [4:0] s2i [0:1]; reg [4:0] bsel; reg [6:0] bkey;
    wire [71:0] m1; wire [17:0] m2; reg [223:0] keys_r;
    for (genvar q = 0; q < 8; q = q + 1) begin : st1
      assign m1[q*9 +: 9] = min4(keys_r[q*28 +: 28], 2'd0);
    end
    for (genvar q = 0; q < 2; q = q + 1) begin : st2
      assign m2[q*9 +: 9] = min4({s1k[4*q+3], s1k[4*q+2], s1k[4*q+1], s1k[4*q]}, 2'd0);
    end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        for (integer q = 0; q < 8; q = q + 1) begin s1k[q] <= 7'd127; s1i[q] <= 0; end
        for (integer q = 0; q < 2; q = q + 1) begin s2k[q] <= 7'd127; s2i[q] <= 0; end
        bsel <= 0; bkey <= 7'd127; keys_r <= {32{7'd127}};
      end else begin
        keys_r <= keys;
        for (integer q = 0; q < 8; q = q + 1) begin
          s1k[q] <= m1[q*9 + 2 +: 7]; s1i[q] <= {3'(q), m1[q*9 +: 2]};
        end
        for (integer q = 0; q < 2; q = q + 1) begin
          s2k[q] <= m2[q*9 + 2 +: 7]; s2i[q] <= s1i[4*q + m2[q*9 +: 2]];
        end
        bsel <= (s2k[1] < s2k[0]) ? s2i[1] : s2i[0];
        bkey <= (s2k[1] < s2k[0]) ? s2k[1] : s2k[0];
      end
    // ---- column: one RD per cycle ------------------------------------------------------
    assign rd_ok = running && streaming && !rd_block && open[rd_bank] && !stale[rd_bank] && !la[rd_bank] &&
                   rcd_z[rd_bank] && ccdl_z[rd_bg] && credit != 0 && !blk[rd_bank];
    // ---- row: refresh > forced PRE > ACT ahead (set k, then the k+1 group) > PRE finished ----
    wire [31:0] act_okb = ~open & ~blk & aok_z & {8{rrdl_z}};
    wire [3:0] grp_k  = act_okb[{ka, 2'b00} +: 4] & ~done[{ka, 2'b00} +: 4];
    wire [3:0] grp_k1 = k1v ? (act_okb[{k1a, 2'b00} +: 4] & (k1_cur ? ~done[{k1a, 2'b00} +: 4] : 4'hF)) : 4'b0;
    // ACTs follow each descriptor's RD order: with the BG swizzle the order within a set is
    // BG 2,3,0,1, so the candidate groups are swizzled before the lowest-first pick (an involution)
    wire x1 = k1_cur ? bgx : nx_bgx;
    function automatic [3:0] swz(input [3:0] g, input x); swz = x ? {g[1:0], g[3:2]} : g; endfunction
    wire [7:0] act_cand = {swz(grp_k1, x1), swz(grp_k, bgx)};
    wire [7:0] act_s8 = act_cand & (~act_cand + 8'd1);
    wire [7:0] act_oh8 = {swz(act_s8[7:4], x1), swz(act_s8[3:0], bgx)};
    wire [31:0] pre_cand = open & (done | stale) & ~blk & ras_z & rtp_z;
    wire [31:0] pre_oh, act_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : oh
      if (b == 0) begin : z assign pre_oh[b] = pre_cand[b]; end
      else begin : nz assign pre_oh[b] = pre_cand[b] & ~(|pre_cand[b-1:0]); end
      assign act_oh[b] = (3'(b >> 2) == ka) ? act_oh8[b & 3] :
                         (k1v && 3'(b >> 2) == k1a) ? act_oh8[4 + (b & 3)] : 1'b0;
    end
    function automatic [4:0] ffs32(input [31:0] v);
      reg [15:0] v16; reg [7:0] v8; reg [3:0] v4; reg [1:0] v2;
      begin
        ffs32[4] = ~|v[15:0];  v16 = ffs32[4] ? v[31:16] : v[15:0];
        ffs32[3] = ~|v16[7:0]; v8 = ffs32[3] ? v16[15:8] : v16[7:0];
        ffs32[2] = ~|v8[3:0];  v4 = ffs32[2] ? v8[7:4] : v8[3:0];
        ffs32[1] = ~|v4[1:0];  v2 = ffs32[1] ? v4[3:2] : v4[1:0];
        ffs32[0] = ~v2[0];
      end
    endfunction
    wire act_ok_any = streaming && !act_block && noact_c == 0 && rrds_c == 0 && faw_ok && (|act_cand);
    wire [2:0] act_sel = 3'(ffs32({24'b0, act_cand}));
    wire [4:0] pre_sel = ffs32(pre_cand);
    wire forced_pre = REF_MODE && ref_pend && |(blk & open & ras_z & rtp_z);
    reg [31:0] r_oh;
    // REFpb PULL-IN (refresh early, never late): while idle under `notice`, a pending REFpb whose bank
    // is unprotected issues as soon as it is legal, so the stream that follows the router does not
    // meet a due refresh (tRREFD) in its first ACTs.  The next REFpb is then due PERIOD later.
    wire idle_nt  = notice && !streaming && !nx_v;
    wire [6:0] rb_key = keys[rb*7 +: 7];
    // TAILPULL: when `notice` rises on an idle sequencer whose refresh round has at most TAILPULL banks
    // left, those banks are refreshed at once (tRREFD apart, early, never late), so they finish
    // (tRFCpb) before the routed window and the window starts a fresh round with every bank eligible.
    // Without it a window that meets the round's tail is forced to refresh the banks it streams.
    // Contract: TAILPULL * tRREFD + tRFCpb (12 * 8 + 196 = 292 cycles) <= the notice lead (293 at 300 ns).
    reg notice_q; reg tpull;
    wire [5:0] n_left = 6'd32 - 6'($countones(refreshed));
    wire tp_start = REF_MODE && TAILPULL > 0 && notice && !notice_q && !streaming && !nx_v &&
                    n_left <= 6'(TAILPULL);
    wire pull_now = REF_MODE && (PULL > 0 || tpull) && idle_nt && ref_pend && pull_ok && !ref_due_n && !ref_due && noact_c == 0 &&
                    !open[rb] && aok_z[rb] && !(c_v && c_op == ACT) && act_age >= 4'(T_RREFD) &&
                    !(c_v && c_op == REFPB);
    // STEER (default 0): in-stream REFpb slot steering.  A REFpb becomes pending LEAD (48) cycles before
    // it is due; instead of waiting for the due cycle (where its tRREFD ACT block can land on the ACT
    // group that opens the next expert's banks, or on the stream's first ACTs), it issues EARLY at the
    // first cycle in which no ACT is wanted (every bank of the current and the lookahead set is open
    // or finished) and its bank is closed, unprotected (key < 16) and idle.  Early, never late: the
    // next REFpb is then due PERIOD later (the pulled-in path below).
    wire [3:0] want_k  = ~open[{ka, 2'b00} +: 4] & ~done[{ka, 2'b00} +: 4];
    wire [3:0] want_k1 = k1v ? (~open[{k1a, 2'b00} +: 4] & (k1_cur ? ~done[{k1a, 2'b00} +: 4] : 4'hF)) : 4'b0;
    wire act_wanted = streaming && (|want_k || |want_k1);
    wire steer_now = REF_MODE && STEER != 0 && ref_pend && !ref_due_n && !ref_due && noact_c == 0 &&
                     streaming && !act_wanted &&
                     rb_key < 7'd16 && !open[rb] && aok_z[rb] && act_age >= 4'(T_RREFD) &&
                     !(c_v && (c_op == ACT || c_op == REFPB));
    // NWIN (default 0 = off): ramp-aware notice.  The static schedule raises `notice` NWIN cycles before
    // the routed window's first ACT.  A REFpb that would fall due inside [NWIN - T_RREFD, NWIN + RAMP] --
    // where its tRREFD would delay the window's first ACTs, i.e. the first access -- is issued as soon as
    // it is pending (LEAD cycles early) while still idle, so its ACT block ends before the window opens.
    // At most one REFpb per notice is moved (the schedule drifts earlier by <= LEAD once).
    reg [9:0] nt_c;
    wire [10:0] due_at = 11'(nt_c) + 11'(ref_c);
    wire ramp_pull = REF_MODE && NWIN > 0 && idle_nt && ref_pend && !ref_due_n && !ref_due && noact_c == 0 &&
                     due_at >= 11'(NWIN - T_RREFD) && due_at <= 11'(NWIN + RAMP) &&
                     rb_key < 7'd16 && !open[rb] && aok_z[rb] && act_age >= 4'(T_RREFD) &&
                     !(c_v && (c_op == ACT || c_op == REFPB));
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0; r_row = row; r_la = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (pull_now || steer_now || ramp_pull) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (act_ok_any) begin
        r_v = 1; r_op = ACT; r_oh = act_oh;
        r_bank = {(act_sel >= 3'd4) ? k1a : ka, act_sel[1:0] ^ {(act_sel >= 3'd4) ? x1 : bgx, 1'b0}};
        r_la = (act_sel >= 3'd4) && k1_nx;
        r_row = r_la ? nx_row : row;
      end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    assign row_v = c_v; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = c_row;
    assign col_v = rd_ok; assign col_bank = rd_bank; assign col_col = j[6:2];
    assign desc_r = !nx_v && !fault_r;
    assign busy = streaming || nx_v; assign ref_fault = fault_r;
    // descriptor flow: the current stream ends at its last RD; the NEXT descriptor (or a new one
    // offered now when there is none) becomes current on that edge.
    wire REFPB_REPICK_OK = REF_MODE && REPICK != 0 && ref_pend && !ref_due_n && !ref_due &&
                           bkey < 7'd16 && rb_key >= 7'd16 && bsel != rb && !refreshed[bsel] && !open[bsel] && aok_z[bsel] &&
                           !(r_v && (r_op == REFPB || (r_op == ACT && r_bank == bsel))) &&
                           !(c_v && (c_op == REFPB || (c_op == ACT && c_bank == bsel)));
    wire cur_end  = streaming && rd_ok && (j == nm1);
    wire cur_free = !streaming || cur_end;
    wire take_nx  = cur_free && nx_v;
    wire take_in  = cur_free && !nx_v && desc_v && !fault_r;
    wire park_in  = !cur_free && !nx_v && desc_v && !fault_r;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        streaming <= 0; last <= 0; nm1 <= 0; s0 <= 0;
        j <= 0; n <= 0; row <= 0; open <= 0; done <= 0; stale <= 0; refreshed <= 0; la <= 0;
        rrds_c <= 0; noact_c <= 0; ref_pend <= 0; blk <= 0; rb <= 0; fault_r <= 0; credit <= 8'(CRED);
        ref_c <= RW'(RPH + PERIOD); running <= 0; phase <= 0;
        c_v <= 0; c_prio <= 0; c_op <= PRE; c_bank <= 0; c_oh <= 0; c_row <= 0; c_la <= 0;
        nx_v <= 0; nx_row <= 0; nx_set <= 0; nx_n <= 0; nx_bgx <= 0; nx_j0 <= 0; nx_keep <= 0; keep <= 0; bgx <= 0; act_age <= 4'hF; pull_ok <= 0; notice_q <= 0; nt_c <= 0; tpull <= 0;
      end else begin
        notice_q <= notice;
        nt_c <= !notice ? 10'd0 : (nt_c != 10'h3FF) ? nt_c + 1'b1 : nt_c;
        if (tp_start) tpull <= 1'b1; else if (!idle_nt) tpull <= 1'b0;
        if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
        if (noact_c != 0) noact_c <= noact_c - 1'b1;
        credit <= rd_ok ? cr_dec : cr_inc;
        ref_c <= ref_n; phase <= ~phase;
        c_v <= slot_next && r_v; c_prio <= r_prio; c_op <= r_op; c_bank <= r_bank; c_oh <= r_oh;
        // an ACT chosen as lookahead for the next descriptor but registered on the edge that makes that
        // descriptor current must not mark its bank lookahead (la), else the bank is never readable
        c_row <= r_row; c_la <= r_la && !(take_nx || take_in);
        if (REF_MODE && !ref_pend && (ref_c == RW'(LEAD) ||
                                      (PULL > 0 && idle_nt && bkey < 7'd16 && ref_c > RW'(LEAD) && ref_c <= RW'(LEAD + PULL)) ||
                                      (tpull && idle_nt && !refreshed[bsel] && !open[bsel] && aok_z[bsel] &&
                                       !(c_v && c_op == REFPB) && !(r_v && r_op == REFPB)))) begin
          ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; pull_ok <= (bkey < 7'd16) || tpull;
        end
        // REPICK: the bank is latched LEAD cycles before the REFpb is due, often before the router's
        // later ids (hence `prot`) have arrived.  While pending and not yet issuing, move the REFpb to
        // the argmin bank when the latched one has become protected (key >= 16) and the argmin is an
        // unprotected (key < 16), closed bank with no ACT in flight to it.
        else if (REFPB_REPICK_OK) begin
          rb <= bsel; blk <= 32'b1 << bsel; pull_ok <= 1'b1;
        end
        if (row_fire && c_op == ACT) act_age <= 4'd1; else if (act_age != 4'hF) act_age <= act_age + 1'b1;
        if (REF_MODE && row_fire && c_op == REFPB && !ref_due) ref_c <= RW'(PERIOD - 1);   // pulled in
        if (ref_due && (!row_fire || !(c_op == REFPB || c_op == REFAB) ||
                        (REF_MODE && (|(blk & open) || |(blk & ~aok_z))) || (!REF_MODE && |open))) fault_r <= 1;
        if (streaming && go) running <= 1;
        // column
        if (rd_ok) begin
          j <= j + 1'b1;
          if (j[6:2] == 5'd31 && !keep) done[rd_bank] <= 1'b1;

        end
        // row
        la <= la_nx;
        if (row_fire) case (c_op)
          ACT: begin open <= open | c_oh; rrds_c <= 2'(T_RRDS - 1); end
          PRE: begin open <= open & ~c_oh; stale <= stale & ~c_oh; end
          PREALL: begin open <= 0; stale <= 0; end
          REFPB: begin
            noact_c <= 4'(T_RREFD - 1); ref_pend <= 0; blk <= 0;
            if (&(refreshed | (32'b1 << rb))) tpull <= 1'b0;      // the round's tail is done
            refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
          end
          default: ;
        endcase
        // Final chunk closes only its own class, also if no successor exists.
        if(cur_end && !keep) stale <= (stale & open_nx) | (open_nx & (32'hF << (int'(s0)*4)));
        // descriptors
        if (cur_end && !take_nx && !take_in) streaming <= 0;
        if (park_in) begin nx_v <= 1; nx_row <= desc_row; nx_set <= desc_set; nx_n <= desc_n; nx_bgx <= desc_bgx; nx_j0 <= desc_j0; nx_keep <= desc_keep; end
        if (take_nx || take_in) begin
          j <= take_nx ? nx_j0 : desc_j0; done <= 0;
          keep <= take_nx ? nx_keep : desc_keep;
          n   <= take_nx ? nx_n : desc_n;
          row <= take_nx ? nx_row : desc_row;
          s0  <= take_nx ? nx_set : desc_set;
          bgx <= take_nx ? nx_bgx : desc_bgx;
          streaming <= take_nx ? (nx_n != 0) : (desc_n != 0);
          nm1  <= (take_nx ? nx_j0 + nx_n : desc_j0 + desc_n) - 11'd1;
          last <= 3'(((take_nx ? nx_j0 + nx_n : desc_j0 + desc_n) - 11'd1) >> 7);
          // rows still open for the old descriptor close first; rows the lookahead opened for this
          // one stay open and become readable
          stale <= (stale & open_nx & ~la_nx) |
                   ((cur_end && !keep) ? (open_nx & (32'hF << (int'(s0)*4))) : 32'b0);
          la <= 32'b0;
          nx_v <= 1'b0;
          if (!take_nx) running <= running && streaming;   // a fresh descriptor after idle waits for go
        end
      end
    end
  end endgenerate
endmodule

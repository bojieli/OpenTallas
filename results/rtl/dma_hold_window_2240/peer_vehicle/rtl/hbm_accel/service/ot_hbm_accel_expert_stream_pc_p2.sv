// P2: pinned notice sequencer plus explicit fail-stop complementary mutable-state rails.
`timescale 1ps/1fs
// HA4 (HBM accelerator) successor of rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv r6 @ 52ce3e9c1
// (sha256 7489b12b...), byte-for-byte the same logic plus ONE input, `notice`: the static decode
// schedule's routed-expert window.  While idle (no descriptor) and notice=1, REFpb bank choice
// treats sets 0..2 as protected exactly as a posted descriptor at set 0 would (the routed-expert
// layout puts every expert's sectors in set 0), so refresh stays strictly on schedule but lands on
// other sets.  notice=0 reproduces r6 exactly.
// Default-off streaming-read sequencer for ONE HBM3E pseudo-channel (near-HBM attention).
// ENABLE=0 (default) ties every output to zero; nothing in r14 instantiates it, and no
// pinned r14 file changes.  Model: tools/qwen_hbm_sustained_bw_model.py (same policy).
//
// Clock: the HBM controller clock, CK/2 (DFI 1:2) = 1.024 ns, so tCCD_S = BL8 = 1 cycle and
// one RD issues per cycle per PC.  Timing parameters are the ot_hdc_hbm_model.sv picosecond
// values ceiled to 1.024 ns cycles (tREFI/tREFIpb floored: refresh never late).
//
// One descriptor (row, n sectors) per layer, posted ahead of `go` (the consumer's start): a
// posted descriptor already protects the sets the stream needs first from refresh and opens
// its first rows; RDs start at go.  next_posted=1 (back-to-back layers) lets protection wrap
// into the next layer's first sets.  Idle refresh order (nothing posted): IDLE0..7.  PC-local sector j maps to
//   BG = j[1:0], column = j[6:2] (32 sectors = 1 KB row), bank set = j[9:7]; bank = {set,BG}.
// The stream rotates BG every sector (tCCD_L met at a 4-cycle BG period), opens the banks of
// the current and next set ahead of use (tRCD hidden), reads each row end to end (31 hits
// per ACT) and closes finished banks.  One RD is issued only against a consumer credit.
//
// Refresh is strictly on schedule (issued on the due cycle, never postponed):
//   REF_MODE 0: REFab every tREFI; RD/ACT stop early enough for PREab + tRP to land on due.
//   REF_MODE 1: REFpb every tREFI/32, each bank once per 32-command round; the bank is chosen
//     LEAD cycles ahead: closed, not needed within tRFCpb + tRCD (outside the stream's
//     current set and next two), nearest-upcoming first; forced (protected/open) only if no
//     such bank remains in the round.
// Row commands leave through a per-channel row-command slot shared by the channel's two PCs
// (row_v/row_gnt; refresh-class requests carry row_prio).  Column commands own the PC's slot.
// Row slot: the channel's two PCs alternate cycles (PC[0] = cycle parity, TDM), and each PC
// decides its row command on the cycle before its slot and issues it from a register, so no
// combinational arbitration or decision sits in front of the timing-state update.  Refresh
// periods are therefore even (tREFIpb 118 cycles = 120.8 ns <= 121.875 ns).
module ot_hbm_accel_expert_stream_pc_p2 #(
  parameter integer ENABLE   = 0,
  parameter integer REF_MODE = 1,
  parameter integer PC       = 0,
  parameter integer T_RCD = 19, T_RP = 16, T_RAS = 28, T_RTP = 6, T_CCDL = 3,
  parameter integer T_RRDS = 3, T_RRDL = 4, T_FAW = 15, T_RFC = 342, T_RFCPB = 196,
  parameter integer T_REFI = 3808, T_REFIPB = 118, T_RREFD = 8,
  parameter integer CRED = 32,
  parameter integer REF_PHASE = 0,
  parameter integer IDLE0 = 3, IDLE1 = 4, IDLE2 = 2, IDLE3 = 5,
  parameter integer IDLE4 = 1, IDLE5 = 6, IDLE6 = 0, IDLE7 = 7
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [10:0] desc_n,
  input  wire        go, input wire next_posted, input wire notice,
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
    // first refresh due on one of this PC's row slots (cycle parity == PC[0]); PERIOD is even
    localparam integer RPH    = REF_PHASE + ((REF_PHASE + PERIOD + PC) % 2);
    function automatic [2:0] idle_rank(input [2:0] s);
      idle_rank = (s==3'(IDLE0))?0:(s==3'(IDLE1))?1:(s==3'(IDLE2))?2:(s==3'(IDLE3))?3:
                  (s==3'(IDLE4))?4:(s==3'(IDLE5))?5:(s==3'(IDLE6))?6:7;
    endfunction
    (* keep = 1 *) reg [10:0] j, n; (* keep = 1 *) reg [10:0] j_bar, n_bar; (* keep = 1 *) reg [18:0] row; (* keep = 1 *) reg [18:0] row_bar;
    (* keep = 1 *) reg [31:0] open, done, stale, refreshed; (* keep = 1 *) reg [31:0] open_bar, done_bar, stale_bar, refreshed_bar;
    (* keep = 1 *) reg [1:0] rrds_c; (* keep = 1 *) reg [1:0] rrds_c_bar; (* keep = 1 *) reg [3:0] noact_c; (* keep = 1 *) reg [3:0] noact_c_bar; (* keep = 1 *) reg [RW-1:0] ref_c; (* keep = 1 *) reg [RW-1:0] ref_c_bar; (* keep = 1 *) reg ref_pend; (* keep = 1 *) reg ref_pend_bar; (* keep = 1 *) reg [4:0] rb; (* keep = 1 *) reg [4:0] rb_bar; (* keep = 1 *) reg fault_r; (* keep = 1 *) reg fault_r_bar;
    (* keep = 1 *) reg [6:0] credit; (* keep = 1 *) reg [6:0] credit_bar; (* keep = 1 *) reg running; (* keep = 1 *) reg running_bar; (* keep = 1 *) reg [31:0] blk; (* keep = 1 *) reg [31:0] blk_bar;   // blk: one-hot of rb while a REFpb is pending
    (* keep = 1 *) reg streaming; (* keep = 1 *) reg streaming_bar; (* keep = 1 *) reg [2:0] last; (* keep = 1 *) reg [2:0] last_bar; (* keep = 1 *) reg [10:0] nm1; (* keep = 1 *) reg [10:0] nm1_bar;   // registered at descriptor accept
    wire [2:0] k = j[9:7];
    wire [4:0] rd_bank = {j[9:7], j[1:0]};
    wire [1:0] rd_bg = j[1:0];
    // ---- refresh windows -------------------------------------------------------------
    wire ref_due = (ref_c == 0);
    (* keep = 1 *) reg  phase; (* keep = 1 *) reg phase_bar;                                       // cycle parity; this PC's row slot when == PC[0]
    wire slot_next = (phase != 1'(PC % 2));           // the next cycle is this PC's row slot
    wire [RW-1:0] ref_n = ref_due ? RW'(PERIOD - 1) : ref_c - 1'b1;   // ref_c of the next cycle
    wire ref_due_n = (ref_n == 0);
    wire act_block = REF_MODE ? (ref_n != 0 && ref_n < RW'(T_RREFD))
                              : (ref_n <= RW'(T_RP + T_RAS + 2));
    wire rd_block  = REF_MODE ? 1'b0 : (ref_c <= RW'(T_RP + T_RTP + 2));
    wire preall_ok = !REF_MODE && ref_n <= RW'(T_RP + 2) && ref_n >= RW'(T_RP) && (|open);
    // ---- row command (combinational) and its events ------------------------------------
    (* keep = 1 *) reg r_v, r_prio; (* keep = 1 *) reg [2:0] r_op; (* keep = 1 *) reg [4:0] r_bank;      // decision for the next cycle
    (* keep = 1 *) reg c_v, c_prio; (* keep = 1 *) reg c_v_bar, c_prio_bar; (* keep = 1 *) reg [2:0] c_op; (* keep = 1 *) reg [2:0] c_op_bar; (* keep = 1 *) reg [4:0] c_bank; (* keep = 1 *) reg [4:0] c_bank_bar; (* keep = 1 *) reg [31:0] c_oh; (* keep = 1 *) reg [31:0] c_oh_bar;   // issued this cycle
    wire row_fire = c_v && row_gnt;
    wire [31:0] open_nx = !row_fire ? open : (c_op == ACT) ? (open | c_oh) : (c_op == PRE) ? (open & ~c_oh) :
                          (c_op == PREALL) ? 32'b0 : open;
    wire rd_ok;
    wire [6:0] cr_inc = credit + 7'(cred_ret), cr_dec = credit + 7'(cred_ret) - 7'd1;
    // ---- per-bank timing state (down-counters; 0 = allowed) ------------------------------
    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy;
    wire [223:0] keys; wire [31:0] bank_bad; wire [3:0] bg_bad;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      (* keep = 1 *) reg [4:0] rcd, ras; (* keep = 1 *) reg [4:0] rcd_bar, ras_bar; (* keep = 1 *) reg [8:0] aok; (* keep = 1 *) reg [8:0] aok_bar; (* keep = 1 *) reg [2:0] rtp; (* keep = 1 *) reg [2:0] rtp_bar;
      assign bank_bad[b] = (rcd != ~rcd_bar) || (ras != ~ras_bar) || (aok != ~aok_bar) || (rtp != ~rtp_bar);
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = rd_ok && rd_bank == 5'(b);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin begin rcd <= 0; rcd_bar <= ~(0); end begin ras <= 0; ras_bar <= ~(0); end begin aok <= 0; aok_bar <= ~(0); end begin rtp <= 0; rtp_bar <= ~(0); end end
        else begin
          if (act_e) begin begin rcd <= 5'(T_RCD - 1); rcd_bar <= ~(5'(T_RCD - 1)); end begin ras <= 5'(T_RAS - 1); ras_bar <= ~(5'(T_RAS - 1)); end end
          else begin if (rcd != 0) begin rcd <= rcd - 1'b1; rcd_bar <= ~(rcd - 1'b1); end if (ras != 0) begin ras <= ras - 1'b1; ras_bar <= ~(ras - 1'b1); end end
          if (rd_e) begin rtp <= 3'(T_RTP - 1); rtp_bar <= ~(3'(T_RTP - 1)); end else if (rtp != 0) begin rtp <= rtp - 1'b1; rtp_bar <= ~(rtp - 1'b1); end
          if (act_e) begin aok <= 9'(T_RAS + T_RP - 1); aok_bar <= ~(9'(T_RAS + T_RP - 1)); end
          else if (rfa_e) begin aok <= 9'(T_RFC - 1); aok_bar <= ~(9'(T_RFC - 1)); end
          else if (rfp_e) begin aok <= 9'(T_RFCPB - 1); aok_bar <= ~(9'(T_RFCPB - 1)); end
          else if (pre_e && aok < 9'(T_RP)) begin aok <= 9'(T_RP - 1); aok_bar <= ~(9'(T_RP - 1)); end
          else if (aok != 0) begin aok <= aok - 1'b1; aok_bar <= ~(aok - 1'b1); end
        end
      assign rcd_z[b] = (rcd == 0); assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0);
      assign aok_z[b] = (aok == 0); assign aok_busy[b] = (aok > 9'(LEAD));
      // REFpb key: 127 refreshed; streaming/posted: open 24 (finished) / 32, protected (needed
      // within the next two sets) 16..18 farthest first, upcoming = distance, passed 8 + set;
      // idle: IDLE rank (+32 open); +64 if still busy from an earlier tRFCpb / tRC.
      localparam [2:0] S = 3'(b >> 2);
      wire [2:0] d = S - k;
      wire ahead = (S >= k && S <= last) || next_posted;
      wire [6:0] base = (!streaming && notice) ? (open[b] ? 7'd32 : (S <= 3'd2) ? 7'd16 + 7'(3'd2 - S) : 7'(S)) :
                        !streaming ? 7'(idle_rank(S)) + (open[b] ? 7'd32 : 7'd0) :
                        open[b] ? ((done[b] || stale[b]) ? 7'd24 : 7'd32) :
                        (ahead && d <= 3'd2) ? 7'd16 + 7'(3'd2 - d) :
                        ahead ? 7'(d) : 7'd8 + 7'(S);
      assign keys[b*7 +: 7] = refreshed[b] ? 7'd127 : base + ((!open[b] && aok_busy[b]) ? 7'd64 : 7'd0);
    end
    // ---- per-bank-group state ----------------------------------------------------------
    wire [3:0] rrdl_z, ccdl_z, faw_z;
    for (genvar g = 0; g < 4; g = g + 1) begin : bgs
      (* keep = 1 *) reg [2:0] rrdl; (* keep = 1 *) reg [2:0] rrdl_bar; (* keep = 1 *) reg [1:0] ccdl; (* keep = 1 *) reg [1:0] ccdl_bar; (* keep = 1 *) reg [3:0] faw; (* keep = 1 *) reg [3:0] faw_bar;
      assign bg_bad[g] = (rrdl != ~rrdl_bar) || (ccdl != ~ccdl_bar) || (faw != ~faw_bar);
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire faw_take = row_fire && c_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin begin rrdl <= 0; rrdl_bar <= ~(0); end begin ccdl <= 0; ccdl_bar <= ~(0); end begin faw <= 0; faw_bar <= ~(0); end end
        else begin
          if (act_g) begin rrdl <= 3'(T_RRDL - 1); rrdl_bar <= ~(3'(T_RRDL - 1)); end else if (rrdl != 0) begin rrdl <= rrdl - 1'b1; rrdl_bar <= ~(rrdl - 1'b1); end
          if (rd_ok && rd_bg == 2'(g)) begin ccdl <= 2'(T_CCDL - 1); ccdl_bar <= ~(2'(T_CCDL - 1)); end else if (ccdl != 0) begin ccdl <= ccdl - 1'b1; ccdl_bar <= ~(ccdl - 1'b1); end
          if (faw_take) begin faw <= 4'(T_FAW - 1); faw_bar <= ~(4'(T_FAW - 1)); end else if (faw != 0) begin faw <= faw - 1'b1; faw_bar <= ~(faw - 1'b1); end
        end
      assign rrdl_z[g] = (rrdl == 0); assign ccdl_z[g] = (ccdl == 0); assign faw_z[g] = (faw == 0);
    end
    wire faw_ok = |faw_z;
    // ---- REFpb bank choice: argmin of keys, ties to the lowest bank ----------------------
    // registered keys, then three registered 4-way stages (32 -> 8 -> 2 -> 1); the choice taken
    // at ref_c == LEAD reflects the bank state 4 cycles earlier (protection spans 3 sets).
    function automatic [8:0] min4(input [27:0] k4, input [1:0] dummy);   // {key, idx2}
      (* keep = 1 *) reg [6:0] ka, kb; (* keep = 1 *) reg ia, ib;
      begin
        ka = (k4[13:7] < k4[6:0]) ? k4[13:7] : k4[6:0];   ia = (k4[13:7] < k4[6:0]);
        kb = (k4[27:21] < k4[20:14]) ? k4[27:21] : k4[20:14]; ib = (k4[27:21] < k4[20:14]);
        min4 = (kb < ka) ? {kb, 1'b1, ib} : {ka, 1'b0, ia};
      end
    endfunction
    (* keep = 1 *) reg [6:0] s1k [0:7]; (* keep = 1 *) reg [6:0] s1k_bar [0:7]; (* keep = 1 *) reg [4:0] s1i [0:7]; (* keep = 1 *) reg [4:0] s1i_bar [0:7]; (* keep = 1 *) reg [6:0] s2k [0:1]; (* keep = 1 *) reg [6:0] s2k_bar [0:1]; (* keep = 1 *) reg [4:0] s2i [0:1]; (* keep = 1 *) reg [4:0] s2i_bar [0:1]; (* keep = 1 *) reg [4:0] bsel; (* keep = 1 *) reg [4:0] bsel_bar;
    wire [71:0] m1; wire [17:0] m2; (* keep = 1 *) reg [223:0] keys_r; (* keep = 1 *) reg [223:0] keys_r_bar;
    for (genvar q = 0; q < 8; q = q + 1) begin : st1
      assign m1[q*9 +: 9] = min4(keys_r[q*28 +: 28], 2'd0);
    end
    for (genvar q = 0; q < 2; q = q + 1) begin : st2
      assign m2[q*9 +: 9] = min4({s1k[4*q+3], s1k[4*q+2], s1k[4*q+1], s1k[4*q]}, 2'd0);
    end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        for (integer q = 0; q < 8; q = q + 1) begin begin s1k[q] <= 7'd127; s1k_bar[q] <= ~(7'd127); end begin s1i[q] <= 0; s1i_bar[q] <= ~(0); end end
        for (integer q = 0; q < 2; q = q + 1) begin begin s2k[q] <= 7'd127; s2k_bar[q] <= ~(7'd127); end begin s2i[q] <= 0; s2i_bar[q] <= ~(0); end end
        begin bsel <= 0; bsel_bar <= ~(0); end begin keys_r <= {32{7'd127}}; keys_r_bar <= ~({32{7'd127}}); end
      end else begin
        begin keys_r <= keys; keys_r_bar <= ~(keys); end
        for (integer q = 0; q < 8; q = q + 1) begin
          begin s1k[q] <= m1[q*9 + 2 +: 7]; s1k_bar[q] <= ~(m1[q*9 + 2 +: 7]); end begin s1i[q] <= {3'(q), m1[q*9 +: 2]}; s1i_bar[q] <= ~({3'(q), m1[q*9 +: 2]}); end
        end
        for (integer q = 0; q < 2; q = q + 1) begin
          begin s2k[q] <= m2[q*9 + 2 +: 7]; s2k_bar[q] <= ~(m2[q*9 + 2 +: 7]); end begin s2i[q] <= s1i[4*q + m2[q*9 +: 2]]; s2i_bar[q] <= ~(s1i[4*q + m2[q*9 +: 2]]); end
        end
        begin bsel <= (s2k[1] < s2k[0]) ? s2i[1] : s2i[0]; bsel_bar <= ~((s2k[1] < s2k[0]) ? s2i[1] : s2i[0]); end
      end
    // ---- column: one RD per cycle ------------------------------------------------------
    assign rd_ok = running && streaming && !rd_block && open[rd_bank] && !stale[rd_bank] &&
                   rcd_z[rd_bank] && ccdl_z[rd_bg] && credit != 0 && !blk[rd_bank];
    // ---- row: refresh > forced PRE > ACT ahead (sets k, k+1) > PRE finished -----------
    function automatic [4:0] act_bank(input integer c, input [2:0] kk);
      act_bank = {(c >= 4) ? kk + 3'd1 : kk, 2'(c & 3)};
    endfunction
    // candidates (no dynamic indexing on the decision path): per-bank ACT eligibility, the 4-bank
    // groups of sets k and k+1, lowest-first one-hot selection; PRE of finished banks, lowest first
    wire [31:0] act_okb = ~open & ~done & ~blk & aok_z & {8{rrdl_z}};
    wire [3:0] grp_k  = act_okb[{k, 2'b00} +: 4];
    wire [3:0] grp_k1 = (k != 3'd7 && k + 3'd1 <= last) ? act_okb[{k + 3'd1, 2'b00} +: 4] : 4'b0;
    wire [7:0] act_cand = {grp_k1, grp_k};
    wire [7:0] act_oh8 = act_cand & (~act_cand + 8'd1);
    wire [31:0] pre_cand = open & (done | stale) & ~blk & ras_z & rtp_z;
    wire [31:0] pre_oh, act_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : oh
      if (b == 0) begin : z assign pre_oh[b] = pre_cand[b]; end
      else begin : nz assign pre_oh[b] = pre_cand[b] & ~(|pre_cand[b-1:0]); end
      assign act_oh[b] = (3'(b >> 2) == k) ? act_oh8[b & 3] :
                         (3'(b >> 2) == k + 3'd1 && k != 3'd7) ? act_oh8[4 + (b & 3)] : 1'b0;
    end
    function automatic [4:0] ffs32(input [31:0] v);   // index of the lowest set bit (tree)
      (* keep = 1 *) reg [15:0] v16; (* keep = 1 *) reg [7:0] v8; (* keep = 1 *) reg [3:0] v4; (* keep = 1 *) reg [1:0] v2;
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
    (* keep = 1 *) reg [31:0] r_oh;
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (act_ok_any) begin r_v = 1; r_op = ACT; r_bank = act_bank(act_sel, k); r_oh = act_oh; end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    wire protect_bad = (|bank_bad) || (|bg_bad) || (j != ~j_bar) || (n != ~n_bar) || (row != ~row_bar) || (open != ~open_bar) || (done != ~done_bar) || (stale != ~stale_bar) || (refreshed != ~refreshed_bar) || (rrds_c != ~rrds_c_bar) || (noact_c != ~noact_c_bar) || (ref_c != ~ref_c_bar) || (ref_pend != ~ref_pend_bar) || (rb != ~rb_bar) || (fault_r != ~fault_r_bar) || (credit != ~credit_bar) || (running != ~running_bar) || (blk != ~blk_bar) || (streaming != ~streaming_bar) || (last != ~last_bar) || (nm1 != ~nm1_bar) || (phase != ~phase_bar) || (c_v != ~c_v_bar) || (c_prio != ~c_prio_bar) || (c_op != ~c_op_bar) || (c_bank != ~c_bank_bar) || (c_oh != ~c_oh_bar) || (bsel != ~bsel_bar) || (keys_r != ~keys_r_bar) || (s1k[0] != ~s1k_bar[0]) || (s1k[1] != ~s1k_bar[1]) || (s1k[2] != ~s1k_bar[2]) || (s1k[3] != ~s1k_bar[3]) || (s1k[4] != ~s1k_bar[4]) || (s1k[5] != ~s1k_bar[5]) || (s1k[6] != ~s1k_bar[6]) || (s1k[7] != ~s1k_bar[7]) || (s1i[0] != ~s1i_bar[0]) || (s1i[1] != ~s1i_bar[1]) || (s1i[2] != ~s1i_bar[2]) || (s1i[3] != ~s1i_bar[3]) || (s1i[4] != ~s1i_bar[4]) || (s1i[5] != ~s1i_bar[5]) || (s1i[6] != ~s1i_bar[6]) || (s1i[7] != ~s1i_bar[7]) || (s2k[0] != ~s2k_bar[0]) || (s2k[1] != ~s2k_bar[1]) || (s2i[0] != ~s2i_bar[0]) || (s2i[1] != ~s2i_bar[1]);
    (* keep = 1 *) reg poison; always @(posedge clk or negedge rst_n) if (!rst_n) poison<=0; else if (protect_bad) poison<=1;
    assign row_v = c_v && !protect_bad && !poison; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = row;
    assign col_v = rd_ok && !protect_bad && !poison; assign col_bank = rd_bank; assign col_col = j[6:2];
    assign desc_r = !streaming && !fault_r && !protect_bad && !poison;
    assign busy = streaming; assign ref_fault = fault_r || protect_bad || poison;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        begin streaming <= 0; streaming_bar <= ~(0); end begin last <= 0; last_bar <= ~(0); end begin nm1 <= 0; nm1_bar <= ~(0); end
        begin j <= 0; j_bar <= ~(0); end begin n <= 0; n_bar <= ~(0); end begin row <= 0; row_bar <= ~(0); end begin open <= 0; open_bar <= ~(0); end begin done <= 0; done_bar <= ~(0); end begin stale <= 0; stale_bar <= ~(0); end begin refreshed <= 0; refreshed_bar <= ~(0); end
        begin rrds_c <= 0; rrds_c_bar <= ~(0); end begin noact_c <= 0; noact_c_bar <= ~(0); end begin ref_pend <= 0; ref_pend_bar <= ~(0); end begin blk <= 0; blk_bar <= ~(0); end begin rb <= 0; rb_bar <= ~(0); end begin fault_r <= 0; fault_r_bar <= ~(0); end begin credit <= 7'(CRED); credit_bar <= ~(7'(CRED)); end
        begin ref_c <= RW'(RPH + PERIOD); ref_c_bar <= ~(RW'(RPH + PERIOD)); end begin running <= 0; running_bar <= ~(0); end begin phase <= 0; phase_bar <= ~(0); end
        begin c_v <= 0; c_v_bar <= ~(0); end begin c_prio <= 0; c_prio_bar <= ~(0); end begin c_op <= PRE; c_op_bar <= ~(PRE); end begin c_bank <= 0; c_bank_bar <= ~(0); end begin c_oh <= 0; c_oh_bar <= ~(0); end
      end else begin
        if (rrds_c != 0) begin rrds_c <= rrds_c - 1'b1; rrds_c_bar <= ~(rrds_c - 1'b1); end
        if (noact_c != 0) begin noact_c <= noact_c - 1'b1; noact_c_bar <= ~(noact_c - 1'b1); end
        begin credit <= rd_ok ? cr_dec : cr_inc; credit_bar <= ~(rd_ok ? cr_dec : cr_inc); end      // both sums precomputed; rd_ok only selects
        // refresh schedule
        begin ref_c <= ref_n; ref_c_bar <= ~(ref_n); end begin phase <= ~phase; phase_bar <= ~(~phase); end
        // register the row decision for this PC's next slot (an off-slot cycle issues nothing)
        begin c_v <= slot_next && r_v; c_v_bar <= ~(slot_next && r_v); end begin c_prio <= r_prio; c_prio_bar <= ~(r_prio); end begin c_op <= r_op; c_op_bar <= ~(r_op); end begin c_bank <= r_bank; c_bank_bar <= ~(r_bank); end begin c_oh <= r_oh; c_oh_bar <= ~(r_oh); end
        if (REF_MODE && ref_c == RW'(LEAD)) begin begin ref_pend <= 1; ref_pend_bar <= ~(1); end begin rb <= bsel; rb_bar <= ~(bsel); end begin blk <= 32'b1 << bsel; blk_bar <= ~(32'b1 << bsel); end end
        // a due refresh that cannot issue (bank open / not granted) is a held fault
        if (ref_due && (!row_fire || !(c_op == REFPB || c_op == REFAB) ||
                        (REF_MODE && (|(blk & open) || |(blk & ~aok_z))) || (!REF_MODE && |open))) begin fault_r <= 1; fault_r_bar <= ~(1); end
        if (streaming && go) begin running <= 1; running_bar <= ~(1); end
        // column
        if (rd_ok) begin
          begin j <= j + 1'b1; j_bar <= ~(j + 1'b1); end
          if (j == nm1) begin streaming <= 0; streaming_bar <= ~(0); end
          if (j[6:2] == 5'd31) begin done[rd_bank] <= 1'b1; done_bar[rd_bank] <= 1'b0; end
        end
        // row
        if (row_fire) case (c_op)
          ACT: begin begin open <= open | c_oh; open_bar <= ~(open | c_oh); end begin rrds_c <= 2'(T_RRDS - 1); rrds_c_bar <= ~(2'(T_RRDS - 1)); end end
          PRE: begin begin open <= open & ~c_oh; open_bar <= ~(open & ~c_oh); end begin stale <= stale & ~c_oh; stale_bar <= ~(stale & ~c_oh); end end
          PREALL: begin begin open <= 0; open_bar <= ~(0); end begin stale <= 0; stale_bar <= ~(0); end end
          REFPB: begin
            begin noact_c <= 4'(T_RREFD - 1); noact_c_bar <= ~(4'(T_RREFD - 1)); end begin ref_pend <= 0; ref_pend_bar <= ~(0); end begin blk <= 0; blk_bar <= ~(0); end
            begin refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb)); refreshed_bar <= ~((&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb))); end
          end
          default: ;
        endcase
        // descriptor
        if (desc_v && !streaming && !fault_r) begin
          begin j <= 0; j_bar <= ~(0); end begin n <= desc_n; n_bar <= ~(desc_n); end begin row <= desc_row; row_bar <= ~(desc_row); end begin done <= 0; done_bar <= ~(0); end begin running <= 0; running_bar <= ~(0); end
          begin streaming <= (desc_n != 0); streaming_bar <= ~((desc_n != 0)); end begin nm1 <= desc_n - 11'd1; nm1_bar <= ~(desc_n - 11'd1); end begin last <= 3'((desc_n - 11'd1) >> 7); last_bar <= ~(3'((desc_n - 11'd1) >> 7)); end
          begin stale <= open_nx; stale_bar <= ~(open_nx); end                     // rows still open from the old descriptor close first
        end
      end
    end
  end endgenerate
endmodule

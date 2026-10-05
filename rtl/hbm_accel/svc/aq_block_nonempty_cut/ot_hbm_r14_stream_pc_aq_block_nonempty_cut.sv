`timescale 1ps/1fs
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
//
// WR_EN = 1 (default 0; WR_EN = 0 is the r6 sequencer exactly: every write term is a constant
// zero): a WQ-entry write queue (bank, column; the row is the current descriptor's row) for the
// token's K/V write-back of the REAL_MEM runtime (ot_qwen_hbm_stream_ack).  The head write issues
// a WR on the PC's column slot when its bank is open on the current row (tRCD as for a read),
// tCCD_L is met and T_RTW cycles have passed since the last RD; while the head is issuable, new
// RDs stop (so tRTW can expire), and after a WR, RDs wait T_WTR (CWL + BL8 + tWTR_L).  A closed
// target bank is opened by a write ACT (priority over the stream's ACT-ahead, never to a bank
// chosen for refresh); a bank opened only for writes is precharged once no queued write needs
// it, after write recovery T_WRR (CWL + BL8 + tWR).  A descriptor is accepted only with the
// write queue empty.
//
// PULLIN = N > 0 (REF_MODE 1; default 0: every pull-in term is a constant zero and the schedule is
// the strict one above): STREAM-AWARE PULL-IN.  While the PC is not reading (no descriptor, or a
// posted descriptor before go, or its stream finished) it issues up to N REFpb AHEAD of schedule
// (the JEDEC pull-in allowance), each to the round's best bank whose key says closed, unprotected
// and not busy (key < 16, or 20: a closed bank of the write-back set, which the strict schedule
// otherwise leaves to the end of the round and then forces in the middle of the next stream), never within LEAD + 8 cycles of a due slot, tRREFD after any ACT /
// REFpb; a scheduled slot that falls while the stream is READING finds a refresh already done and is
// skipped (pin - 1); slots while not reading are issued as scheduled, so the banked pull-ins are
// spent only inside a stream.  So a
// layer's window stream (~9 scheduled slots at P8191) starts up to N refreshes ahead and is not
// interrupted by forced refreshes of the banks it is about to read.  No REFpb is ever later than
// the strict schedule; the round rule (each bank once per 32) is unchanged.
//
// AQ_RD = 1 (WR_EN = 1; default 0: every term below is a constant zero): the write queue becomes the
// PC's ACCESS queue -- an entry pushed with wr_rd = 1 is a TAGGED READ (near-HBM row client) of
// (bank, column) on the current descriptor's row.  Entries issue strictly in queue order (a read
// after a queued write-back of the same sector sees it).  A read head issues when its bank is open on
// the row with full tRCD, tCCD_L met and tWTR passed after a write (no tRTW); it sets tRTP of its
// bank and tRTW like a stream RD, never write recovery.  col_aq flags the column command as a
// queued read (col_we = 0).  ARBITRATION (the stream keeps its bandwidth): a read head is
// background -- it issues only in a cycle the stream does not, and its bank's ACT yields to the
// stream's ACT-ahead -- until it has waited AQ_STARVE cycles, then it takes priority as a write-back
// head does (stops new stream RDs until it issues).  A bank holding a queued access is never
// precharged (hold_n, the current queue), nor a write-opened bank the stream still needs.
module ot_hbm_r14_stream_pc_aq_block_nonempty_cut #(
  parameter integer ENABLE   = 0,
  parameter integer REF_MODE = 1,
  parameter integer PC       = 0,
  parameter integer T_RCD = 19, T_RP = 16, T_RAS = 28, T_RTP = 6, T_CCDL = 3,
  parameter integer T_RRDS = 3, T_RRDL = 4, T_FAW = 15, T_RFC = 342, T_RFCPB = 196,
  parameter integer T_REFI = 3808, T_REFIPB = 118, T_RREFD = 8,
  parameter integer CRED = 32,
  parameter integer REF_PHASE = 0,
  parameter integer IDLE0 = 3, IDLE1 = 4, IDLE2 = 2, IDLE3 = 5,
  parameter integer IDLE4 = 1, IDLE5 = 6, IDLE6 = 0, IDLE7 = 7,
  parameter integer WR_EN = 0, WQ = 4, T_RTW = 10, T_WTR = 14, T_WRR = 28, T_RCDW = 10,
  parameter integer PULLIN = 0,
  parameter integer AQ_RD = 0,
  parameter integer AQ_STARVE = 64,
  parameter integer AQ_SLOT_READY_LOOKAHEAD = 0,
  parameter integer AQ_BLOCK_NONEMPTY_LOOKAHEAD = 0,
  parameter integer AQ_HOLD_LOOKAHEAD = 0
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [10:0] desc_n,
  input  wire        go, input wire next_posted,
  output wire        row_v, output wire row_prio, input wire row_gnt,
  output wire [2:0]  row_op, output wire [4:0] row_bank, output wire [18:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  input  wire [2:0]  cred_ret,
  output wire        busy, output wire ref_fault,
  // WR_EN: write queue (push wr_v && wr_r) and the WR flag of the column command
  input  wire        wr_v, input wire [4:0] wr_bank, input wire [4:0] wr_col,
  output wire        wr_r, output wire col_we,
  // AQ_RD: the pushed entry is a tagged read; the column command is a queued read
  input  wire        wr_rd, output wire col_aq
);
  localparam [2:0] PRE=0, ACT=1, RD=2, REFAB=4, PREALL=5, REFPB=6;
  generate if (!ENABLE) begin : off
    assign desc_r=0; assign row_v=0; assign row_prio=0; assign row_op=0; assign row_bank=0;
    assign row_row=0; assign col_v=0; assign col_bank=0; assign col_col=0; assign busy=0;
    assign ref_fault=0; assign wr_r=0; assign col_we=0; assign col_aq=0;
  end else begin : on
    localparam W = (WR_EN != 0);
    localparam integer WQW = (WQ > 1) ? $clog2(WQ) : 1;
    localparam integer PERIOD = REF_MODE ? T_REFIPB : T_REFI;
    localparam integer LEAD   = T_RAS + T_RP + 4;
    localparam integer RW     = $clog2(2 * PERIOD + 4);
    // first refresh due on one of this PC's row slots (cycle parity == PC[0]); PERIOD is even
    localparam integer RPH    = REF_PHASE + ((REF_PHASE + PERIOD + PC) % 2);
    function automatic [2:0] idle_rank(input [2:0] s);
      idle_rank = (s==3'(IDLE0))?0:(s==3'(IDLE1))?1:(s==3'(IDLE2))?2:(s==3'(IDLE3))?3:
                  (s==3'(IDLE4))?4:(s==3'(IDLE5))?5:(s==3'(IDLE6))?6:7;
    endfunction
    reg [10:0] j, n; reg [18:0] row;
    reg [31:0] open, done, stale, refreshed;
    reg [1:0] rrds_c; reg [3:0] noact_c; reg [RW-1:0] ref_c; reg ref_pend; reg [4:0] rb; reg fault_r;
    reg [6:0] credit; reg running; reg [31:0] blk;   // blk: one-hot of rb while a REFpb is pending
    reg streaming; reg [2:0] last; reg [10:0] nm1;   // registered at descriptor accept
    wire [2:0] k = j[9:7];
    wire [4:0] rd_bank = {j[9:7], j[1:0]};
    wire [1:0] rd_bg = j[1:0];
    // r8: the RD bank as a registered one-hot (rd_oh, rd_bgoh) and credit != 0 as a registered
    // flag, updated exactly with j / credit, so rd_ok is an AND-OR of flops (no j-decoded mux).
    reg [31:0] rd_oh; reg [3:0] rd_bgoh; reg cred_nz;
    wire [10:0] j_p1 = j + 11'd1;
    // ---- write queue (WR_EN) ------------------------------------------------------------
    reg [4:0] wq_bank [0:WQ-1]; reg [4:0] wq_col [0:WQ-1]; reg wq_rd [0:WQ-1];
    localparam AQ = (WR_EN != 0) && (AQ_RD != 0);
    reg hr;                                           // AQ_RD: the head entry is a read (registered)
    reg [WQW:0] wq_n; reg [WQW-1:0] wq_rp;
    reg [3:0] rtw_c, wtr_c;
    reg [31:0] wopen;                                 // banks opened by a write ACT (precharged after)
    reg c_w;                                          // the registered row command is a write ACT
    // r9 (1.2 GHz timing, cycle-identical to the s4 base): wq_n != 0, rtw_c == 0, wtr_c == 0 are registered flags
    reg wq_ner, rtw_z, wtr_z;
    wire wq_ne = W && wq_ner;
    // the head write's bank/column are REGISTERED copies (hb_oh one-hot), kept off the queue index
    reg [4:0] hb, hc; reg [31:0] hb_oh; reg [3:0] hbg_oh;
    // r9: every queue SLOT keeps its bank as a registered one-hot (wq_boh) and bank-group one-hot (wq_bgoh),
    // written at push, a registered valid bit (wq_pv) and an age matrix (wq_older[p*WQ + q]: slot q is older
    // than slot p), so the write-ACT candidate and the hold set are AND-OR reductions of flops.  WQ must be a
    // power of two (the pointers wrap at 2^WQW, as before).
    reg [31:0] wq_boh [0:WQ-1]; reg [3:0] wq_bgoh [0:WQ-1]; reg [WQ-1:0] wq_pv, rp_oh; reg [WQ*WQ-1:0] wq_older;
    reg [31:0] hold_n, hold;                          // banks a queued write needs (never precharged;
    integer hi;                                       // registered: one cycle behind the queue)
    always @* begin
      hold_n = 0;
      for (hi = 0; hi < WQ; hi = hi + 1) if (W && wq_pv[hi]) hold_n = hold_n | wq_boh[hi];
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) hold <= 0; else hold <= hold_n;
    // Exact current-queue bank mask: remove only an accepted head pop and
    // include only an accepted push. Keep the previous queue mask `hold` too.
    // Both pop/no-pop reductions are formed from old slot flops in parallel;
    // wr_ok selects the result late. Duplicated banks remain protected.
    wire wr_ok;
    wire [31:0] aq_hold_now;
    if (AQ_HOLD_LOOKAHEAD != 0 && AQ) begin : aq_hold_cut
      reg [31:0] current;
      reg [31:0] after_pop;
      integer p;
      always @* begin
        after_pop = 32'b0;
        for (p=0; p<WQ; p=p+1)
          after_pop = after_pop | ({32{wq_pv[p] && !rp_oh[p]}} & wq_boh[p]);
      end
      wire [31:0] next_mask = (wr_ok ? after_pop : hold_n) |
                            ((wr_v && wr_r) ? (32'b1 << wr_bank) : 32'b0);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) current <= 32'b0; else current <= next_mask;
      assign aq_hold_now = current;
    end else begin : aq_hold_uncut
      assign aq_hold_now = hold_n;
    end

    // ---- refresh windows -------------------------------------------------------------
    wire ref_due = (ref_c == 0);
    reg  phase;                                       // cycle parity; this PC's row slot when == PC[0]
    wire slot_next = (phase != 1'(PC % 2));           // the next cycle is this PC's row slot
    wire [RW-1:0] ref_n = ref_due ? RW'(PERIOD - 1) : ref_c - 1'b1;   // ref_c of the next cycle
    wire ref_due_n = (ref_n == 0);
    wire act_block = REF_MODE ? (ref_n != 0 && ref_n < RW'(T_RREFD))
                              : (ref_n <= RW'(T_RP + T_RAS + 2));
    wire rd_block  = REF_MODE ? 1'b0 : (ref_c <= RW'(T_RP + T_RTP + 2));
    wire preall_ok = !REF_MODE && ref_n <= RW'(T_RP + 2) && ref_n >= RW'(T_RP) && (|open);
    // ---- row command (combinational) and its events ------------------------------------
    reg r_v, r_prio; reg [2:0] r_op; reg [4:0] r_bank;      // decision for the next cycle
    reg c_v, c_prio; reg [2:0] c_op; reg [4:0] c_bank; reg [31:0] c_oh;   // issued this cycle
    wire row_fire = c_v && row_gnt;
    wire [31:0] open_nx = !row_fire ? open : (c_op == ACT) ? (open | c_oh) : (c_op == PRE) ? (open & ~c_oh) :
                          (c_op == PREALL) ? 32'b0 : open;
    wire rd_ok;
    wire [6:0] cr_inc = credit + 7'(cred_ret), cr_dec = credit + 7'(cred_ret) - 7'd1;
    // ---- per-bank timing state (down-counters; 0 = allowed) ------------------------------
    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy, rcdw_z, rcd_zn, rcdw_zn;
    wire [223:0] keys;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      reg [4:0] rcd, ras; reg [8:0] aok; reg [2:0] rtp; reg aok_zr, rcd_zr;   // == 0 flags, registered
      reg [4:0] wrr;
      wire wr_e = W && wr_ok && hb_oh[b] && !(AQ && hr);
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = (rd_ok && rd_oh[b]) || (AQ && wr_ok && hr && hb_oh[b]);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; aok_zr <= 1'b1; rcd_zr <= 1'b1; wrr <= 0; end
        else begin
          rcd_zr <= rcd_zn[b];
          if (wr_e) wrr <= 5'(T_WRR - 1); else if (wrr != 0) wrr <= wrr - 1'b1;
          if (act_e) begin rcd <= 5'(T_RCD - 1); ras <= 5'(T_RAS - 1); end
          else begin if (rcd != 0) rcd <= rcd - 1'b1; if (ras != 0) ras <= ras - 1'b1; end
          if (rd_e) rtp <= 3'(T_RTP - 1); else if (rtp != 0) rtp <= rtp - 1'b1;
          if (act_e) aok <= 9'(T_RAS + T_RP - 1);
          else if (rfa_e) aok <= 9'(T_RFC - 1);
          else if (rfp_e) aok <= 9'(T_RFCPB - 1);
          else if (pre_e && aok < 9'(T_RP)) aok <= 9'(T_RP - 1);
          else if (aok != 0) aok <= aok - 1'b1;
          // the same priority, evaluated as "is the next aok zero" (exact, registered flag)
          if (act_e) aok_zr <= (T_RAS + T_RP - 1 == 0);
          else if (rfa_e) aok_zr <= (T_RFC - 1 == 0);
          else if (rfp_e) aok_zr <= (T_RFCPB - 1 == 0);
          else if (pre_e && aok < 9'(T_RP)) aok_zr <= (T_RP - 1 == 0);
          else aok_zr <= (aok <= 9'd1);
        end
      assign rcd_zn[b] = act_e ? (T_RCD - 1 == 0) : (rcd <= 5'd1);
      // next (rcd <= K): a down-counter that holds at 0, so rcd' <= K <=> rcd <= K + 1 (K = T_RCD - T_RCDW)
      assign rcdw_zn[b] = act_e ? (T_RCD - 1 <= T_RCD - T_RCDW) : ({1'b0, rcd} <= 6'(T_RCD - T_RCDW + 1));
      assign rcd_z[b] = rcd_zr; assign rcdw_z[b] = (rcd <= 5'(T_RCD - T_RCDW)); assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0) && (!W || wrr == 0);
      assign aok_z[b] = aok_zr; assign aok_busy[b] = (aok > 9'(LEAD));
      // REFpb key: 127 refreshed; streaming/posted: open 24 (finished) / 32, protected (needed
      // within the next two sets) 16..18 farthest first, upcoming = distance, passed 8 + set;
      // idle: IDLE rank (+32 open); +64 if still busy from an earlier tRFCpb / tRC.
      localparam [2:0] S = 3'(b >> 2);
      wire [2:0] d = S - k;
      wire ahead = (S >= k && S <= last) || next_posted;
      // WR_EN: the descriptor's last set holds the token's write-back sectors (the service writes
      // only there): its closed banks rank 20, after every other closed bank, streaming or not.
      wire wset = W && S == last && !open[b];
      wire [6:0] base = wset ? 7'd20 :
                        !streaming ? 7'(idle_rank(S)) + (open[b] ? 7'd32 : 7'd0) :
                        open[b] ? ((done[b] || stale[b]) ? 7'd24 : 7'd32) :
                        (ahead && d <= 3'd2) ? 7'd16 + 7'(3'd2 - d) :
                        ahead ? 7'(d) : 7'd8 + 7'(S);
      assign keys[b*7 +: 7] = refreshed[b] ? 7'd127 : base + ((!open[b] && aok_busy[b]) ? 7'd64 : 7'd0);
    end
    // ---- per-bank-group state ----------------------------------------------------------
    wire [3:0] rrdl_z, ccdl_z, faw_z;
    for (genvar g = 0; g < 4; g = g + 1) begin : bgs
      reg [2:0] rrdl; reg [1:0] ccdl; reg [3:0] faw; reg rrdl_zr, faw_zr, ccdl_zr;   // registered (== 0) flags
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire ccdl_e = (rd_ok && rd_bgoh[g]) || (W && wr_ok && hb[1:0] == 2'(g));
      wire faw_take = row_fire && c_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rrdl <= 0; ccdl <= 0; faw <= 0; rrdl_zr <= 1'b1; faw_zr <= 1'b1; ccdl_zr <= 1'b1; end
        else begin
          if (act_g) rrdl <= 3'(T_RRDL - 1); else if (rrdl != 0) rrdl <= rrdl - 1'b1;
          if (ccdl_e) ccdl <= 2'(T_CCDL - 1); else if (ccdl != 0) ccdl <= ccdl - 1'b1;
          if (faw_take) faw <= 4'(T_FAW - 1); else if (faw != 0) faw <= faw - 1'b1;
          rrdl_zr <= act_g ? (T_RRDL - 1 == 0) : (rrdl <= 3'd1);
          ccdl_zr <= ccdl_e ? (T_CCDL - 1 == 0) : (ccdl <= 2'd1);
          faw_zr  <= faw_take ? (T_FAW - 1 == 0) : (faw <= 4'd1);
        end
      assign rrdl_z[g] = rrdl_zr; assign ccdl_z[g] = ccdl_zr; assign faw_z[g] = faw_zr;
    end
    wire faw_ok = |faw_z;
    // ---- REFpb bank choice: argmin of keys, ties to the lowest bank ----------------------
    // registered keys, then three registered 4-way stages (32 -> 8 -> 2 -> 1); the choice taken
    // at ref_c == LEAD reflects the bank state 4 cycles earlier (protection spans 3 sets).
    function automatic [8:0] min4(input [27:0] k4, input [1:0] dummy);   // {key, idx2}
      reg [6:0] ka, kb; reg ia, ib;
      begin
        ka = (k4[13:7] < k4[6:0]) ? k4[13:7] : k4[6:0];   ia = (k4[13:7] < k4[6:0]);
        kb = (k4[27:21] < k4[20:14]) ? k4[27:21] : k4[20:14]; ib = (k4[27:21] < k4[20:14]);
        min4 = (kb < ka) ? {kb, 1'b1, ib} : {ka, 1'b0, ia};
      end
    endfunction
    reg [6:0] s1k [0:7]; reg [4:0] s1i [0:7]; reg [6:0] s2k [0:1]; reg [4:0] s2i [0:1]; reg [4:0] bsel;
    reg [6:0] bkey;                                   // PULLIN: the key of bsel
    reg [31:0] bsel_oh;                               // r9: one-hot copy of bsel
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
        bsel <= 0; keys_r <= {32{7'd127}}; bkey <= 7'd127; bsel_oh <= 32'b1;
      end else begin
        keys_r <= keys;
        for (integer q = 0; q < 8; q = q + 1) begin
          s1k[q] <= m1[q*9 + 2 +: 7]; s1i[q] <= {3'(q), m1[q*9 +: 2]};
        end
        for (integer q = 0; q < 2; q = q + 1) begin
          s2k[q] <= m2[q*9 + 2 +: 7]; s2i[q] <= s1i[4*q + m2[q*9 +: 2]];
        end
        bsel <= (s2k[1] < s2k[0]) ? s2i[1] : s2i[0];
        bsel_oh <= 32'b1 << ((s2k[1] < s2k[0]) ? s2i[1] : s2i[0]);
        bkey <= (s2k[1] < s2k[0]) ? s2k[1] : s2k[0];
      end
    // ---- column: one RD per cycle ------------------------------------------------------
    // the head write is issuable but for tRTW / tCCD_L: RDs stop so it can go
    reg [7:0] hwait;                                  // AQ_RD: cycles the read head has waited
    wire starve = AQ && hr && hwait >= 8'(AQ_STARVE);
    wire head_prio = !(AQ && hr) || starve;
    // AQ: every access-queue head waits full tRCD.  r9b: the per-bank column-readiness vectors
    //   rdyr_q = open & ~stale & rcd_z & ~blk        (a stream RD / a queued read)
    //   rdyw_q = open & ~stale & rcdw_z & ~blk       (a write)
    // are REGISTERED, each bit formed from the next-cycle value of its terms, so wr_bank_rdy and the RD bank test
    // are one AND-OR of flops with the head / RD one-hot
    reg [31:0] rdyr_q, rdyw_q;
    // Default-off exact current-slot flags. Read pointer remains current, with no early grant.
    reg [WQ-1:0] aq_slot_ready_q;
    wire wr_bank_rdy = (AQ_SLOT_READY_LOOKAHEAD != 0 && AQ) ?
      (wq_ne && |(rp_oh & wq_pv & aq_slot_ready_q)) :
      (wq_ne && |(hb_oh & (AQ ? rdyr_q : rdyw_q)));
    wire rd_ok_base = running && streaming && !rd_block && |(rd_oh & rdyr_q) &&
                      |(rd_bgoh & ccdl_z) && cred_nz;
    assign wr_ok = wr_bank_rdy && |(hbg_oh & ccdl_z) && ((AQ && hr) ? wtr_z : rtw_z) && !rd_block &&
                   (head_prio || !rd_ok_base);
    assign rd_ok = rd_ok_base && !(W && ((wr_bank_rdy && head_prio) || !wtr_z));
    // ---- row: refresh > forced PRE > ACT ahead (sets k, k+1) > PRE finished -----------
    function automatic [4:0] act_bank(input integer c, input [2:0] kk);
      act_bank = {(c >= 4) ? kk + 3'd1 : kk, 2'(c & 3)};
    endfunction
    // candidates (no dynamic indexing on the decision path): per-bank ACT eligibility, the 4-bank
    // groups of sets k and k+1, lowest-first one-hot selection; PRE of finished banks, lowest first
    wire [31:0] act_okb = ~open & ~done & ~blk & aok_z & {8{rrdl_z}};
    // r8: k as a registered one-hot (koh) and the k+1 validity as a registered flag (k1v), both
    // updated exactly with j/last, so the set selection is an AND-OR, not a k-decoded mux.
    reg [7:0] koh; reg k1v;
    wire [7:0] k1oh = {koh[6:0], 1'b0};                 // set k+1 (none when k == 7)
    reg [3:0] grp_k, grp_k1;
    always @* begin
      grp_k = 4'b0; grp_k1 = 4'b0;
      for (integer s = 0; s < 8; s = s + 1) begin
        grp_k  = grp_k  | ({4{koh[s]}}  & act_okb[4*s +: 4]);
        grp_k1 = grp_k1 | ({4{k1oh[s] & k1v}} & act_okb[4*s +: 4]);
      end
    end
    wire [7:0] act_cand = {grp_k1, grp_k};
    wire [7:0] act_oh8 = act_cand & (~act_cand + 8'd1);
    // AQ_RD: a bank the stream still needs (set k .. last, not done) is never precharged as write-opened,
    // and the current queue (hold_n, not only the registered hold) protects the banks of queued accesses
    reg [31:0] sneed;
    always @* for (integer b = 0; b < 32; b = b + 1) sneed[b] = AQ && streaming && !done[b] && 3'(b >> 2) >= k && 3'(b >> 2) <= last;
    wire [31:0] pre_cand = open & (done | stale | (W ? (wopen & ~sneed) : 32'b0)) & ~blk & ras_z & rtp_z &
                           ~(W ? (hold | (AQ ? aq_hold_now : 32'b0)) : 32'b0);
    wire [31:0] pre_oh, act_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : oh
      if (b == 0) begin : z assign pre_oh[b] = pre_cand[b]; end
      else begin : nz assign pre_oh[b] = pre_cand[b] & ~(|pre_cand[b-1:0]); end
      assign act_oh[b] = (koh[b >> 2] & act_oh8[b & 3]) | (k1oh[b >> 2] & act_oh8[4 + (b & 3)]);
    end
    function automatic [4:0] ffs32(input [31:0] v);   // index of the lowest set bit (tree)
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
    // next-cycle k and last (the same updates as j and last below)
    wire desc_acc = desc_v && !streaming && !fault_r;
    wire k_step = rd_ok && (j[6:0] == 7'h7f);
    wire [2:0] k_n = desc_acc ? 3'd0 : k_step ? k + 3'd1 : k;
    wire [2:0] last_n = desc_acc ? 3'((desc_n - 11'd1) >> 7) : last;
    wire [7:0] koh_n = desc_acc ? 8'b1 : k_step ? {koh[6:0], koh[7]} : koh;
    // write ACT: closed target bank, not chosen (or about to be chosen) for refresh
    // any queued write's bank may open (oldest first), so a burst of writes opens its banks together
    // r9: per slot, from flops: the refresh exclusion (bank == bsel while ref_c is LEAD or LEAD + 1, refwin
    // registered with ref_c) joins the one-hot reduction; oldest active slot = no older active slot (wq_older)
    reg refwin;
    wire [WQ-1:0] wq_act;
    for (genvar p = 0; p < WQ; p = p + 1) begin : wqa
      assign wq_act[p] = W && wq_pv[p] && (|(wq_boh[p] & ~open & ~blk & aok_z & ~((REF_MODE && refwin) ? bsel_oh : 32'b0))) &&
                         (|(wq_bgoh[p] & rrdl_z));
    end
    // The candidate (oldest queued write whose bank can open) is REGISTERED and re-validated at use
    // against the current bank state with one-hot reductions, keeping the queue indexing and the
    // bank-state muxes off the row-decision path.
    reg wcand; reg [4:0] wab_n; reg wcrd_n; reg [31:0] wab_oh_n; reg [WQ-1:0] pwin;
    integer ai, ar;
    always @* begin
      for (ai = 0; ai < WQ; ai = ai + 1) pwin[ai] = wq_act[ai] && !(|(wq_older[ai*WQ +: WQ] & wq_act));
      wcand = |wq_act; wab_n = 0; wcrd_n = 1'b0; wab_oh_n = 0;
      for (ai = 0; ai < WQ; ai = ai + 1) if (pwin[ai]) begin
        wab_n = wab_n | wq_bank[ai]; wab_oh_n = wab_oh_n | wq_boh[ai]; wcrd_n = wcrd_n | (AQ && wq_rd[ai]);
      end
      if (!wcand) wab_oh_n = 32'b1;                   // s4: 1 << 0 when there is no candidate
    end
    reg wcand_q; reg [4:0] wab; reg [31:0] wab_oh; reg wcrd_q;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin wcand_q <= 1'b0; wab <= 0; wab_oh <= 0; wcrd_q <= 1'b0; end
      else begin wcand_q <= W && wcand; wab <= wab_n; wab_oh <= wab_oh_n; wcrd_q <= wcrd_n; end
    wire wact_ok = wcand_q && !(|(wab_oh & (open | blk))) && (|(wab_oh & aok_z)) && rrdl_z[wab[1:0]] &&
                   !(REF_MODE && refwin && |(wab_oh & bsel_oh)) &&
                   !act_block && noact_c == 0 && rrds_c == 0 && faw_ok;
    // ---- PULLIN: refresh ahead of schedule while not reading ---------------------------------
    localparam integer PIW = $clog2(PULLIN + 2);
    localparam PI = (REF_MODE != 0) && (PULLIN > 0);
    reg [PIW-1:0] pin;                                // REFpb issued ahead of the schedule
    reg ep;                                           // a pulled-in REFpb is pending (rb / blk)
    reg skip;                                         // this due slot was paid ahead: nothing issues
    reg [3:0] sact;                                   // cycles since the last ACT / REFpb (saturating)
    // Owner-selected mandatory clock repair: mirror the exact blocked-vector
    // transition, not a delayed refresh decision. Every other blk user stays.
    reg blk_nonempty_q;
    reg blk_nonempty_n;
    wire blk_any_for_ep = (AQ_BLOCK_NONEMPTY_LOOKAHEAD != 0) ? blk_nonempty_q : (|blk);
    wire pi_idle = !streaming || !running;
    wire ep_start = PI && pi_idle && !ep && !ref_pend && 32'(pin) < PULLIN && ref_c > RW'(LEAD + 8) &&
                    (bkey < 7'd16 || bkey == 7'd20) && !blk_any_for_ep && sact >= 4'd6;   // bsel/bkey see a REFpb / ACT 5 cycles late
    wire ep_rdy = PI && ep && !(|(blk & open)) && (|(blk & aok_z)) && noact_c == 0 && sact >= 4'(T_RREFD + 2) &&
                  ref_c > RW'(LEAD + 8);   // bsel at LEAD must not see a REFpb in flight
    reg [31:0] r_oh;
    reg r_w;
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0; r_w = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (ep_rdy) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (W && wact_ok && !(AQ && wcrd_q && act_ok_any && !starve)) begin r_v = 1; r_op = ACT; r_bank = wab; r_oh = wab_oh; r_w = 1; end
      else if (act_ok_any) begin r_v = 1; r_op = ACT; r_bank = act_bank(act_sel, k); r_oh = act_oh; end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    assign row_v = c_v; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = row;
    assign col_v = rd_ok || (W && wr_ok); assign col_we = W && wr_ok && !(AQ && hr); assign col_aq = AQ && wr_ok && hr;
    assign col_bank = (W && wr_ok) ? hb : rd_bank; assign col_col = (W && wr_ok) ? hc : j[6:2];
    assign wr_r = W && wq_n != (WQW+1)'(WQ);
    assign desc_r = !streaming && !fault_r && !wq_ne;
    assign busy = streaming; assign ref_fault = fault_r;
    // r9: next-cycle open / stale / blk (exactly the updates below), for the wr_bank_rdy look-ahead
    wire [31:0] stale_n = desc_acc ? open_nx : (row_fire && c_op == PRE) ? (stale & ~c_oh) :
                          (row_fire && c_op == PREALL) ? 32'b0 : stale;
    reg [31:0] blk_n;
    always @* begin
      blk_n = blk;
      if (!PI) begin
        if (REF_MODE && ref_c == RW'(LEAD)) blk_n = 32'b1 << bsel;
      end else begin
        if (ref_c == RW'(LEAD)) begin
          if (!ep && !(pin != 0 && !pi_idle)) blk_n = 32'b1 << bsel;
        end else if (ep_start) blk_n = 32'b1 << bsel;
        else if (ep && |(blk & open)) blk_n = 32'b0;
      end
      if (row_fire && c_op == REFPB) blk_n = 32'b0;
    end
    // SAME set/clear/hold order as blk_n and the actual blk register below.
    // bsel is five bits: each SET's 32-bit onehot is nonzero. REFPB accepted
    // at this edge clears even when an earlier LEAD/ep_start branch SETs.
    always @* begin
      blk_nonempty_n = blk_nonempty_q;
      if (!PI) begin
        if (REF_MODE && ref_c == RW'(LEAD)) blk_nonempty_n = 1'b1;
      end else begin
        if (ref_c == RW'(LEAD)) begin
          if (!ep && !(pin != 0 && !pi_idle)) blk_nonempty_n = 1'b1;
        end else if (ep_start) blk_nonempty_n = 1'b1;
        else if (ep && |(blk & open)) blk_nonempty_n = 1'b0;
      end
      if (row_fire && c_op == REFPB) blk_nonempty_n = 1'b0;
    end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) blk_nonempty_q <= 1'b0;
      else if (AQ_BLOCK_NONEMPTY_LOOKAHEAD != 0) blk_nonempty_q <= blk_nonempty_n;
      else blk_nonempty_q <= 1'b0;
    wire [31:0] rdyr_n = open_nx & ~stale_n & rcd_zn & ~blk_n;
    wire [31:0] rdyw_n = open_nx & ~stale_n & rcdw_zn & ~blk_n;
    wire wpush = W && wr_v && wr_r;
    wire [WQW-1:0] wq_wp = WQW'(wq_rp + wq_n);
    // Capture the actual next bank of each slot independently of pop/head selection.
    // A popped slot may retain a flag; wq_pv blocks it until an accepted push overwrites it.
    for (genvar sr = 0; sr < WQ; sr = sr + 1) begin : slot_ready
      wire accepted_here = wpush && wq_wp == WQW'(sr);
      wire [31:0] next_bank_oh = accepted_here ? (32'b1 << wr_bank) : wq_boh[sr];
      always @(posedge clk or negedge rst_n) begin
        if (!rst_n) aq_slot_ready_q[sr] <= 1'b0;
        else if (AQ_SLOT_READY_LOOKAHEAD != 0 && AQ)
          aq_slot_ready_q[sr] <= (wq_pv[sr] || accepted_here) && |(next_bank_oh & rdyr_n);
      end
    end

    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        streaming <= 0; last <= 0; nm1 <= 0;
        j <= 0; n <= 0; row <= 0; open <= 0; done <= 0; stale <= 0; refreshed <= 0;
        rrds_c <= 0; noact_c <= 0; ref_pend <= 0; blk <= 0; rb <= 0; fault_r <= 0; credit <= 7'(CRED);
        ref_c <= RW'(RPH + PERIOD); running <= 0; phase <= 0;
        c_v <= 0; c_prio <= 0; c_op <= PRE; c_bank <= 0; c_oh <= 0;
        koh <= 8'b1; k1v <= 1'b0; rd_oh <= 32'b1; rd_bgoh <= 4'b1; cred_nz <= (CRED != 0);
        wq_n <= 0; wq_rp <= 0; rtw_c <= 0; wtr_c <= 0; wopen <= 0; c_w <= 0; hb <= 0; hc <= 0; hb_oh <= 0; hr <= 0;
        pin <= 0; ep <= 0; skip <= 0; sact <= 0; hwait <= 0;
        wq_ner <= 1'b0; rtw_z <= 1'b1; wtr_z <= 1'b1; hbg_oh <= 4'b0; rdyr_q <= 32'b0; rdyw_q <= 32'b0; wq_pv <= 0; rp_oh <= WQ'(1);
        refwin <= (RW'(RPH + PERIOD) == RW'(LEAD) || RW'(RPH + PERIOD) == RW'(LEAD + 1));
      end else begin
        if (AQ) begin if (!wq_ne || !hr || wr_ok) hwait <= 0; else if (hwait != 8'hff) hwait <= hwait + 1'b1; end
        if (W) begin
          if (rd_ok || (AQ && wr_ok && hr)) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
          if (wr_ok && !(AQ && hr)) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;
          rtw_z <= (rd_ok || (AQ && wr_ok && hr)) ? (T_RTW - 1 == 0) : (rtw_c <= 4'd1);
          wtr_z <= (wr_ok && !(AQ && hr)) ? (T_WTR - 1 == 0) : (wtr_c <= 4'd1);
          wq_ner <= (wq_n + (wpush ? 1'b1 : 1'b0) - (wr_ok ? 1'b1 : 1'b0)) != 0;
          if (wpush) begin
            wq_boh[wq_wp] <= 32'b1 << wr_bank; wq_bgoh[wq_wp] <= 4'b1 << wr_bank[1:0];
            for (ai = 0; ai < WQ; ai = ai + 1)
              for (ar = 0; ar < WQ; ar = ar + 1)
                if (wq_wp == WQW'(ai)) wq_older[ai*WQ + ar] <= wq_pv[ar] && ar != ai;
                else if (wq_wp == WQW'(ar)) wq_older[ai*WQ + ar] <= 1'b0;
          end
          // slot valid: a push sets slot rp + n, a pop clears slot rp (never the same slot: no push when full)
          wq_pv <= (wq_pv | (wpush ? (WQ'(1) << wq_wp) : WQ'(0))) & ~(wr_ok ? rp_oh : WQ'(0));
          if (wr_ok) rp_oh <= {rp_oh[WQ-2:0], rp_oh[WQ-1]};
          if (wr_v && wr_r) begin
            wq_bank[WQW'(wq_rp + wq_n)] <= wr_bank; wq_col[WQW'(wq_rp + wq_n)] <= wr_col;
            if (AQ) wq_rd[WQW'(wq_rp + wq_n)] <= wr_rd;
          end
          wq_n <= wq_n + (wr_v && wr_r ? 1'b1 : 1'b0) - (wr_ok ? 1'b1 : 1'b0);
          if (wr_ok) wq_rp <= WQW'(wq_rp + 1'b1);
          // next head: the entry after the popped one if it exists, else the entry pushed now
          // r9: both outcomes (pop / no pop) are formed from flops and inputs in parallel; wr_ok only selects
          begin : headn
            reg [4:0] nb0, nc0, nb1, nc1; reg nr0, nr1;
            if (wq_n != 0) begin nb0 = wq_bank[wq_rp]; nc0 = wq_col[wq_rp]; nr0 = AQ && wq_rd[wq_rp]; end
            else begin nb0 = wr_bank; nc0 = wr_col; nr0 = AQ && wr_rd; end
            if (wq_n - 1'b1 != 0) begin nb1 = wq_bank[WQW'(wq_rp + 1'b1)]; nc1 = wq_col[WQW'(wq_rp + 1'b1)]; nr1 = AQ && wq_rd[WQW'(wq_rp + 1'b1)]; end
            else begin nb1 = wr_bank; nc1 = wr_col; nr1 = AQ && wr_rd; end
            hb <= wr_ok ? nb1 : nb0; hc <= wr_ok ? nc1 : nc0; hr <= wr_ok ? nr1 : nr0;
            hb_oh <= wr_ok ? (32'b1 << nb1) : (32'b1 << nb0); hbg_oh <= wr_ok ? (4'b1 << nb1[1:0]) : (4'b1 << nb0[1:0]);
          end
          // write-opened banks: set by a write ACT, cleared by PRE/PREALL or a stream RD (the stream owns it)
          wopen <= ((wopen | ((row_fire && c_op == ACT && c_w) ? c_oh : 32'b0))
                    & ~((row_fire && c_op == PRE) ? c_oh : 32'b0)
                    & ~(rd_ok ? rd_oh : 32'b0))
                   & {32{!(row_fire && c_op == PREALL)}};
        end
        if (desc_acc) begin rd_oh <= 32'b1; rd_bgoh <= 4'b1; end
        else if (rd_ok) begin rd_oh <= 32'b1 << {j_p1[9:7], j_p1[1:0]}; rd_bgoh <= 4'b1 << j_p1[1:0]; end
        cred_nz <= rd_ok ? (cr_dec != 7'd0) : (cr_inc != 7'd0);
        koh <= koh_n; k1v <= (k_n != 3'd7) && (k_n + 3'd1 <= last_n);
        if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
        if (noact_c != 0) noact_c <= noact_c - 1'b1;
        credit <= rd_ok ? cr_dec : cr_inc;      // both sums precomputed; rd_ok only selects
        // refresh schedule
        rdyr_q <= rdyr_n; rdyw_q <= W ? rdyw_n : 32'b0;
        ref_c <= ref_n; phase <= ~phase; refwin <= (ref_n == RW'(LEAD) || ref_n == RW'(LEAD + 1));
        // register the row decision for this PC's next slot (an off-slot cycle issues nothing)
        c_v <= slot_next && r_v; c_prio <= r_prio; c_op <= r_op; c_bank <= r_bank; c_oh <= r_oh; c_w <= W && r_w;
        if (!PI) begin
          if (REF_MODE && ref_c == RW'(LEAD)) begin ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; end
        end else begin
          if (row_fire && (c_op == ACT || c_op == REFPB)) sact <= 0; else if (sact != 4'hf) sact <= sact + 1'b1;
          if (ref_c == RW'(LEAD)) begin
            if (ep) begin ref_pend <= 1; ep <= 0; end                 // a pending pull-in becomes this slot's REFpb
            else if (pin != 0 && !pi_idle) begin pin <= pin - 1'b1; skip <= 1; end  // paid ahead: skip (only while reading)
            else begin ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; end
          end else if (ep_start) begin ep <= 1; rb <= bsel; blk <= 32'b1 << bsel; end
          else if (ep && |(blk & open)) begin ep <= 0; blk <= 0; end   // the chosen bank opened meanwhile
          if (ref_due) skip <= 0;
        end
        // a due refresh that cannot issue (bank open / not granted) is a held fault
        if (ref_due && !(PI && skip) && (!row_fire || !(c_op == REFPB || c_op == REFAB) ||
                        (REF_MODE && (|(blk & open) || |(blk & ~aok_z))) || (!REF_MODE && |open))) fault_r <= 1;
        if (streaming && go) running <= 1;
        // column
        if (rd_ok) begin
          j <= j_p1;
          if (j == nm1) streaming <= 0;
          if (j[6:2] == 5'd31) done <= done | rd_oh;
        end
        // row
        if (row_fire) case (c_op)
          ACT: begin open <= open | c_oh; rrds_c <= 2'(T_RRDS - 1); end
          PRE: begin open <= open & ~c_oh; stale <= stale & ~c_oh; end
          PREALL: begin open <= 0; stale <= 0; end
          REFPB: begin
            noact_c <= 4'(T_RREFD - 1); ref_pend <= 0; blk <= 0;
            if (PI && ep && !ref_pend) begin ep <= 0; pin <= pin + 1'b1; end
            refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
          end
          default: ;
        endcase
        // descriptor
        if (desc_v && !streaming && !fault_r) begin
          j <= 0; n <= desc_n; row <= desc_row; done <= 0; running <= 0;
          streaming <= (desc_n != 0); nm1 <= desc_n - 11'd1; last <= 3'((desc_n - 11'd1) >> 7);
          stale <= open_nx;                     // rows still open from the old descriptor close first
        end
      end
    end
  end endgenerate
endmodule

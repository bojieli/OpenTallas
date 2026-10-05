`timescale 1ps/1fs
// DS-V4.1 HBM accelerator KV write-back (2026-10-04): ot_hbm_accel_expert_stream_pc (r6 + notice) plus a
// default-off posted-write path whose writes carry their OWN DRAM row (bank, row, column, 256-bit data), so the
// token's KV / index-key write-back can land anywhere in a 1M-context history while the read stream runs.
// WB_EN = 0 (default) is the parent sequencer exactly (every write term is a constant zero; no pinned file changes).
// WB_EN = 1: a WQ-entry in-order write queue.  A queued write's closed bank is opened by a WRITE ACT (oldest
// entry first, never to a bank chosen for refresh, never across an earlier queued write to the same bank on a
// different row); a write-opened bank (wopen) is invisible to the stream (no RD, no stream ACT/PRE).  The head
// WR issues on the PC's column slot when its bank is write-open on its row, tRCDWR (T_RCDW) and tCCD_L are met
// and T_RTW cycles have passed since the last RD; while the head is issuable RDs stop (so tRTW can expire), and
// after a WR, RDs wait T_WTR (CWL + BL8 + tWTR_L).  A write-open bank no queued write needs is precharged after
// write recovery T_WRR (CWL + BL8 + tWR) and tRAS.  A bank a queued write needs is protected from REFpb choice
// (key 16) and a forced refresh PRE waits for write recovery.  wr_ack pulses on each WR issue (the bench adds the
// r9 (2026-10-04, 1.2 GHz closure; cycle-identical to r0 sha256 8189205b..., lockstep bench
// results/rtl/hbm_accel_fmax_inventory_20261004/svc): the r14 r8b changes (registered == 0 flags of every
// timing counter, the current set k and the RD bank as registered one-hots, credit != 0 registered) and the
// write queue as per-slot registered state (bank one-hots, row-hit and older-conflict flags, one-hot read
// pointer), so the queue scans are AND-OR reductions of flops; and Yosys-parsable (r0 used automatic
// variables inside an always block, which Yosys rejects).
// DRAM write + response path to make the posted-write ACK the visibility fence counts).
module ot_hbm_accel_stream_pc_wb #(
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
  parameter integer WB_EN = 0, WQ = 8, T_RTW = 10, T_WTR = 14, T_WRR = 28, T_RCDW = 10,
  // r9d WA_LATE = 1 (default 0 = r0 cycle-exact): the write-ACT candidate (oldest openable queued write) is
  // selected from this cycle's queue/bank state and registered, then re-validated at use (bank still closed, not
  // chosen for refresh, tRC/tRRD met).  The candidate can be one cycle late (a write that arrived or a bank that
  // closed in the previous cycle is seen a cycle later); it never violates an ordering rule, because a
  // candidate's older-write conflicts can only clear while it waits.
  parameter integer WA_LATE = 0
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [10:0] desc_n,
  input  wire        go, input wire next_posted, input wire notice,
  output wire        row_v, output wire row_prio, input wire row_gnt,
  output wire [2:0]  row_op, output wire [4:0] row_bank, output wire [18:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  input  wire [2:0]  cred_ret,
  output wire        busy, output wire ref_fault,
  // WB_EN: posted write queue (push wq_v && wq_r), the WR flag/data of the column command, WR issue pulse
  input  wire        wq_v, input wire [4:0] wq_bank, input wire [18:0] wq_row, input wire [4:0] wq_col,
  input  wire [255:0] wq_data, output wire wq_r,
  output wire        col_we, output wire [255:0] col_wdata, output wire [18:0] col_row, output wire wr_ack,
  output wire        wq_empty
);
  localparam [2:0] PRE=0, ACT=1, RD=2, REFAB=4, PREALL=5, REFPB=6;
  generate if (!ENABLE) begin : off
    assign desc_r=0; assign row_v=0; assign row_prio=0; assign row_op=0; assign row_bank=0;
    assign row_row=0; assign col_v=0; assign col_bank=0; assign col_col=0; assign busy=0;
    assign ref_fault=0; assign wq_r=0; assign col_we=0; assign col_wdata=0; assign col_row=0; assign wr_ack=0;
    assign wq_empty=1;
  end else begin : on
    localparam W = (WB_EN != 0);
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
    // r9: the RD bank as a registered one-hot (rd_oh, rd_bgoh) and credit != 0 as a registered flag, updated
    // exactly with j / credit, so rd_ok is an AND-OR of flops (no j-decoded mux) -- the r14 r8b change.
    reg [31:0] rd_oh; reg [3:0] rd_bgoh; reg cred_nz;
    wire [10:0] j_p1 = j + 11'd1;
    // ---- posted write queue (WB_EN) ----------------------------------------------------
    reg [4:0] wqb [0:WQ-1]; reg [18:0] wqr [0:WQ-1]; reg [4:0] wqc [0:WQ-1]; reg [255:0] wqd [0:WQ-1];
    reg [WQW:0] wq_n; reg [WQW-1:0] wq_rp, wq_wp;
    reg [31:0] wopen;                                 // banks open on a WRITE row (invisible to the stream)
    reg [18:0] wrow [0:31];                           // the row a write-open bank holds
    reg [3:0] rtw_c, wtr_c;
    reg rtw_z, wtr_nz, wq_ner;                        // r9: registered rtw_c == 0, wtr_c != 0, wq_n != 0
    reg c_w;                                          // the registered row command is a write ACT / write PRE
    reg [18:0] c_wrow;
    wire [31:0] rcdw_z, wrr_z, rcdw_zn;
    // r9: per queue SLOT p (physical entry), registered at push and kept exact afterwards:
    //   sl_v[p]    the slot holds a queued write (set at push, cleared at pop);
    //   sl_boh[p]  its bank one-hot, sl_bgoh[p] its bank-group one-hot;
    //   sl_hit[p]  wrow[bank] == row (updated when a write ACT loads wrow[bank], or at push);
    //   sl_conf[p] the slots holding an OLDER write to the same bank on a different row (the r0 "blocked"
    //              relation; a column is cleared when its slot is pushed again, so only older entries count).
    // rp_oh is the read pointer as a one-hot.  The queue scans of r0 (wneed, wneed_row_ok, the oldest
    // openable write) become AND-OR reductions of these flops; nothing on the row-decision path indexes the
    // queue or the bank state with a binary index.  WQ must be a power of two (pointers wrap at 2^WQW).
    reg [WQ-1:0] sl_v, sl_hit, rp_oh;
    reg [31:0] sl_boh [0:WQ-1]; reg [3:0] sl_bgoh [0:WQ-1]; reg [WQ*WQ-1:0] sl_conf, sl_old;   // [p*WQ +: WQ]
    // r9b: everything the row/column decisions need from the queue is REGISTERED, computed one cycle ahead
    // from the next-cycle slot state (n* below): the oldest openable write (wa_*), the write-open banks a
    // queued write needs on their row (wnro_q), the head write's bank/row/column/data and its issuability
    // (wbr_q = r0 wr_bank_rdy).  Each register equals, at every cycle, the r0 combinational value.
    reg wa_v; reg [4:0] wa_b; reg [18:0] wa_r; reg [31:0] wa_oh; reg [3:0] wa_bgoh;
    reg [31:0] wnro_q, hb_oh; reg [3:0] hbg_oh; reg [4:0] hb, hc; reg [18:0] hr; reg [255:0] hd; reg wbr_q;
    reg [31:0] wneed;
    integer e, f;
    always @* begin
      wneed = 0;
      for (e = 0; e < WQ; e = e + 1) if (W && sl_v[e]) wneed = wneed | sl_boh[e];
    end
    wire wq_ne = W && wq_ner;
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
    wire rd_ok, wr_ok;
    wire [6:0] cr_inc = credit + 7'(cred_ret), cr_dec = credit + 7'(cred_ret) - 7'd1;
    // ---- per-bank timing state (down-counters; 0 = allowed) ------------------------------
    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy;
    wire [223:0] keys;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      reg [4:0] rcd, ras; reg [8:0] aok; reg [2:0] rtp; reg [4:0] rcdw, wrr;
      reg aok_zr, rcd_zr, rcdw_zr, wrr_zr;          // r9: registered == 0 flags (same event priority)
      wire wr_e  = W && wr_ok && hb_oh[b];
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = rd_ok && rd_oh[b];
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
          rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; rcdw <= 0; wrr <= 0;
          aok_zr <= 1'b1; rcd_zr <= 1'b1; rcdw_zr <= 1'b1; wrr_zr <= 1'b1;
        end else begin
          if (W) begin
            if (act_e) rcdw <= 5'(T_RCDW - 1); else if (rcdw != 0) rcdw <= rcdw - 1'b1;
            if (wr_e) wrr <= 5'(T_WRR - 1); else if (wrr != 0) wrr <= wrr - 1'b1;
            rcdw_zr <= rcdw_zn[b];
            wrr_zr  <= wr_e ? (T_WRR - 1 == 0) : (wrr <= 5'd1);
          end
          rcd_zr <= act_e ? (T_RCD - 1 == 0) : (rcd <= 5'd1);
          if (act_e) begin rcd <= 5'(T_RCD - 1); ras <= 5'(T_RAS - 1); end
          else begin if (rcd != 0) rcd <= rcd - 1'b1; if (ras != 0) ras <= ras - 1'b1; end
          if (rd_e) rtp <= 3'(T_RTP - 1); else if (rtp != 0) rtp <= rtp - 1'b1;
          if (act_e) aok <= 9'(T_RAS + T_RP - 1);
          else if (rfa_e) aok <= 9'(T_RFC - 1);
          else if (rfp_e) aok <= 9'(T_RFCPB - 1);
          else if (pre_e && aok < 9'(T_RP)) aok <= 9'(T_RP - 1);
          else if (aok != 0) aok <= aok - 1'b1;
          if (act_e) aok_zr <= (T_RAS + T_RP - 1 == 0);
          else if (rfa_e) aok_zr <= (T_RFC - 1 == 0);
          else if (rfp_e) aok_zr <= (T_RFCPB - 1 == 0);
          else if (pre_e && aok < 9'(T_RP)) aok_zr <= (T_RP - 1 == 0);
          else aok_zr <= (aok <= 9'd1);
        end
      assign rcd_z[b] = rcd_zr; assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0);
      assign aok_z[b] = aok_zr; assign aok_busy[b] = (aok > 9'(LEAD));
      assign rcdw_z[b] = W ? rcdw_zr : 1'b1;
      assign rcdw_zn[b] = W ? (act_e ? (T_RCDW - 1 == 0) : (rcdw <= 5'd1)) : 1'b1; assign wrr_z[b] = W ? wrr_zr : 1'b1;
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
      // WB_EN: a closed bank a queued write needs is protected (16); a write-open bank counts as open (32)
      wire [6:0] wbase = (W && wopen[b]) ? 7'd32 : (W && wneed[b] && !open[b]) ? 7'd16 : base;
      assign keys[b*7 +: 7] = refreshed[b] ? 7'd127 : wbase + ((!open[b] && aok_busy[b]) ? 7'd64 : 7'd0);
    end
    // ---- per-bank-group state ----------------------------------------------------------
    wire [3:0] rrdl_z, ccdl_z, faw_z;
    for (genvar g = 0; g < 4; g = g + 1) begin : bgs
      reg [2:0] rrdl; reg [1:0] ccdl; reg [3:0] faw; reg rrdl_zr, faw_zr, ccdl_zr;   // registered (== 0) flags
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      wire ccdl_e = (rd_ok && rd_bgoh[g]) || (W && wr_ok && hbg_oh[g]);
      // FAW slot g takes this ACT if it is the lowest free slot
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
        bsel <= 0; keys_r <= {32{7'd127}};
      end else begin
        keys_r <= keys;
        for (integer q = 0; q < 8; q = q + 1) begin
          s1k[q] <= m1[q*9 + 2 +: 7]; s1i[q] <= {3'(q), m1[q*9 +: 2]};
        end
        for (integer q = 0; q < 2; q = q + 1) begin
          s2k[q] <= m2[q*9 + 2 +: 7]; s2i[q] <= s1i[4*q + m2[q*9 +: 2]];
        end
        bsel <= (s2k[1] < s2k[0]) ? s2i[1] : s2i[0];
      end
    // ---- column: one RD per cycle ------------------------------------------------------
    // WB_EN: the head write is issuable but for tRTW / tCCD_L: RDs stop so it can go; after a WR, RDs wait tWTR
    wire wr_bank_rdy = W && wbr_q;
    assign wr_ok = wr_bank_rdy && |(hbg_oh & ccdl_z) && rtw_z && !rd_block;
    assign rd_ok = running && streaming && !rd_block &&
                   |(rd_oh & open & ~stale & rcd_z & ~blk & ~(W ? wopen : 32'b0)) &&
                   |(rd_bgoh & ccdl_z) && cred_nz && !(W && (wr_bank_rdy || wtr_nz));
    // ---- row: refresh > forced PRE > ACT ahead (sets k, k+1) > PRE finished -----------
    function automatic [4:0] act_bank(input integer c, input [2:0] kk);
      act_bank = {(c >= 4) ? kk + 3'd1 : kk, 2'(c & 3)};
    endfunction
    // candidates (no dynamic indexing on the decision path): per-bank ACT eligibility, the 4-bank
    // groups of sets k and k+1, lowest-first one-hot selection; PRE of finished banks, lowest first
    wire [31:0] act_okb = ~open & ~done & ~blk & aok_z & {8{rrdl_z}};
    // r9 (r14 r8b): k as a registered one-hot (koh) and the k+1 validity as a registered flag (k1v)
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
    wire [31:0] pre_cand = open & (done | stale) & ~blk & ras_z & rtp_z & ~(W ? wopen : 32'b0);
    // WB_EN: write ACT (oldest openable queued write) and write PRE (a write-open bank no queued write needs on
    // its row, after write recovery and tRAS)
    wire wact_ok = W && wa_v && !act_block && noact_c == 0 && rrds_c == 0 && faw_ok && |(wa_oh & aok_z & ~(WA_LATE ? open : 32'b0)) &&
                   !(|(wa_oh & blk)) && |(wa_bgoh & rrdl_z);
    wire [31:0] wpre_cand = W ? (wopen & ~wnro_q & ~blk & ras_z & wrr_z) : 32'b0;
    wire [31:0] pre_oh, act_oh, wpre_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : oh
      if (b == 0) begin : z assign pre_oh[b] = pre_cand[b]; assign wpre_oh[b] = wpre_cand[b]; end
      else begin : nz
        assign pre_oh[b] = pre_cand[b] & ~(|pre_cand[b-1:0]); assign wpre_oh[b] = wpre_cand[b] & ~(|wpre_cand[b-1:0]);
      end
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
    wire forced_pre = REF_MODE && ref_pend && |(blk & open & ras_z & rtp_z & wrr_z);
    wire [4:0] wpre_sel = ffs32(wpre_cand);
    // next-cycle k and last (the same updates as j and last below)
    wire desc_acc = desc_v && !streaming && !fault_r;
    wire k_step = rd_ok && (j[6:0] == 7'h7f);
    wire [2:0] k_n = desc_acc ? 3'd0 : k_step ? k + 3'd1 : k;
    wire [2:0] last_n = desc_acc ? 3'((desc_n - 11'd1) >> 7) : last;
    wire [7:0] koh_n = desc_acc ? 8'b1 : k_step ? {koh[6:0], koh[7]} : koh;
    reg r_w; reg [18:0] r_wrow;
    reg [31:0] r_oh;
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0; r_w = 0; r_wrow = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (|wpre_cand) begin r_v = 1; r_op = PRE; r_bank = wpre_sel; r_oh = wpre_oh; r_w = 1; end
      else if (wact_ok) begin r_v = 1; r_op = ACT; r_bank = wa_b; r_oh = wa_oh; r_w = 1; r_wrow = wa_r; end
      else if (act_ok_any) begin r_v = 1; r_op = ACT; r_bank = act_bank(act_sel, k); r_oh = act_oh; end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    assign row_v = c_v; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = (W && c_w) ? c_wrow : row;
    assign col_v = rd_ok || (W && wr_ok); assign col_bank = (W && wr_ok) ? hb : rd_bank;
    assign col_col = (W && wr_ok) ? hc : j[6:2];
    assign col_we = W && wr_ok; assign col_wdata = (W && wr_ok) ? hd : 256'b0;
    assign col_row = (W && wr_ok) ? hr : 19'b0; assign wr_ack = W && wr_ok;
    assign wq_r = W && wq_n != (WQW+1)'(WQ); assign wq_empty = !wq_ne;
    assign desc_r = !streaming && !fault_r;
    assign busy = streaming; assign ref_fault = fault_r;
    // push-time slot state: the new write's row hit (against wrow as it will be after this cycle's write
    // ACT, if any) and its conflict set (valid older slots on the same bank with a different row)
    wire push = W && wq_v && wq_r;
    wire wact_fire = row_fire && c_w && c_op == ACT;
    // r9d: every bank's row compared with the pushed row in parallel, then selected by the pushed bank
    reg [31:0] wrow_eq;
    always @* for (integer b = 0; b < 32; b = b + 1) wrow_eq[b] = (wrow[b] == wq_row);
    wire [31:0] wq_boh_in = 32'b1 << wq_bank;
    wire push_hit = (wact_fire && |(c_oh & wq_boh_in)) ? (c_wrow == wq_row) : |(wrow_eq & wq_boh_in);
    reg [WQ-1:0] push_conf;
    always @* begin
      push_conf = 0;
      for (e = 0; e < WQ; e = e + 1) push_conf[e] = sl_v[e] && wqb[e] == wq_bank && wqr[e] != wq_row;
    end
    // ---- r9b: next-cycle queue/slot state (exactly the sequential updates below) and its registered digests
    wire [WQ-1:0] nv = (sl_v | (push ? (WQ'(1) << wq_wp) : WQ'(0))) & ~(wr_ok ? rp_oh : WQ'(0));
    wire [WQ-1:0] nrp = wr_ok ? {rp_oh[WQ-2:0], rp_oh[WQ-1]} : rp_oh;
    wire [31:0] nwopen = wact_fire ? (wopen | c_oh) : (row_fire && c_op == PRE && (c_oh & wopen) != 0) ? (wopen & ~c_oh) : wopen;
    wire [31:0] nblk = (row_fire && c_op == REFPB) ? 32'b0 : (REF_MODE && ref_c == RW'(LEAD)) ? (32'b1 << bsel) : blk;
    wire nwq_ne = (wq_n + (WQW+1)'(push) - (WQW+1)'(wr_ok)) != 0;
    reg [32*WQ-1:0] nboh; reg [4*WQ-1:0] nbgoh; reg [5*WQ-1:0] nwqb, nwqc; reg [19*WQ-1:0] nwqr; reg [256*WQ-1:0] nwqd;
    reg [WQ-1:0] nhit, nact, pwin_n; reg [WQ*WQ-1:0] nconf, nold;
    reg wa_v_n; reg [4:0] wa_b_n; reg [18:0] wa_r_n; reg [31:0] wa_oh_n; reg [3:0] wa_bgoh_n;
    reg [31:0] wnro_n, hb_oh_n; reg [3:0] hbg_oh_n; reg [4:0] hb_n, hc_n; reg [18:0] hr_n; reg [255:0] hd_n; reg h_hit_n;
    always @* begin
      for (e = 0; e < WQ; e = e + 1) begin
        if (push && wq_wp == WQW'(e)) begin
          nboh[e*32 +: 32] = 32'b1 << wq_bank; nbgoh[e*4 +: 4] = 4'b1 << wq_bank[1:0];
          nwqb[e*5 +: 5] = wq_bank; nwqc[e*5 +: 5] = wq_col; nwqr[e*19 +: 19] = wq_row; nwqd[e*256 +: 256] = wq_data;
          nhit[e] = push_hit;
        end else begin
          nboh[e*32 +: 32] = sl_boh[e]; nbgoh[e*4 +: 4] = sl_bgoh[e];
          nwqb[e*5 +: 5] = wqb[e]; nwqc[e*5 +: 5] = wqc[e]; nwqr[e*19 +: 19] = wqr[e]; nwqd[e*256 +: 256] = wqd[e];
          nhit[e] = (wact_fire && |(c_oh & sl_boh[e])) ? (c_wrow == wqr[e]) : sl_hit[e];
        end
        for (f = 0; f < WQ; f = f + 1)
        begin
          // r9c: a popped slot's column is cleared too, so "blocked" needs no valid mask; sl_old is the age
          // matrix (slot f holds an older write than slot e), set at push from the slots still valid
          nconf[e*WQ + f] = (push && wq_wp == WQW'(e)) ? (push_conf[f] && !(wr_ok && rp_oh[f])) :
                            ((push && wq_wp == WQW'(f)) || (wr_ok && rp_oh[f])) ? 1'b0 : sl_conf[e*WQ + f];
          nold[e*WQ + f] = (push && wq_wp == WQW'(e)) ? (sl_v[f] && !(wr_ok && rp_oh[f]) && f != e) :
                           (push && wq_wp == WQW'(f)) ? 1'b0 : sl_old[e*WQ + f];
        end
      end
      for (e = 0; e < WQ; e = e + 1)
        nact[e] = WA_LATE ? (sl_v[e] && !(|sl_conf[e*WQ +: WQ]) && !(|(sl_boh[e] & open)))
                          : (nv[e] && !(|nconf[e*WQ +: WQ]) && !(|(nboh[e*32 +: 32] & open_nx)));
      for (e = 0; e < WQ; e = e + 1)
        pwin_n[e] = nact[e] && !(|((WA_LATE ? sl_old[e*WQ +: WQ] : nold[e*WQ +: WQ]) & nact));
      wa_v_n = |nact; wa_b_n = 0; wa_r_n = 0; wa_oh_n = 0; wa_bgoh_n = 0; wnro_n = 0;
      hb_oh_n = 0; hbg_oh_n = 0; hb_n = 0; hc_n = 0; hr_n = 0; hd_n = 0; h_hit_n = 1'b0;
      for (e = 0; e < WQ; e = e + 1) begin
        if (pwin_n[e] && !WA_LATE) begin
          wa_b_n = wa_b_n | nwqb[e*5 +: 5]; wa_r_n = wa_r_n | nwqr[e*19 +: 19];
          wa_oh_n = wa_oh_n | nboh[e*32 +: 32]; wa_bgoh_n = wa_bgoh_n | nbgoh[e*4 +: 4];
        end
        if (pwin_n[e] && WA_LATE) begin
          wa_b_n = wa_b_n | wqb[e]; wa_r_n = wa_r_n | wqr[e]; wa_oh_n = wa_oh_n | sl_boh[e]; wa_bgoh_n = wa_bgoh_n | sl_bgoh[e];
        end
        if (W && nv[e] && nhit[e]) wnro_n = wnro_n | (nboh[e*32 +: 32] & nwopen);
        if (nrp[e]) begin
          hb_oh_n = hb_oh_n | nboh[e*32 +: 32]; hbg_oh_n = hbg_oh_n | nbgoh[e*4 +: 4]; h_hit_n = h_hit_n | nhit[e];
          hb_n = hb_n | nwqb[e*5 +: 5]; hc_n = hc_n | nwqc[e*5 +: 5]; hr_n = hr_n | nwqr[e*19 +: 19];
          hd_n = hd_n | nwqd[e*256 +: 256];
        end
      end
    end
    wire wbr_n = W && nwq_ne && h_hit_n && |(hb_oh_n & nwopen & rcdw_zn & ~nblk);
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        wa_v <= 1'b0; wa_b <= 0; wa_r <= 0; wa_oh <= 0; wa_bgoh <= 0; wnro_q <= 0; wbr_q <= 1'b0;
        hb_oh <= 0; hbg_oh <= 0; hb <= 0; hc <= 0; hr <= 0; hd <= 0;
      end else if (W) begin
        wa_v <= wa_v_n; wa_b <= wa_b_n; wa_r <= wa_r_n; wa_oh <= wa_oh_n; wa_bgoh <= wa_bgoh_n; wnro_q <= wnro_n;
        wbr_q <= wbr_n; hb_oh <= hb_oh_n; hbg_oh <= hbg_oh_n; hb <= hb_n; hc <= hc_n; hr <= hr_n; hd <= hd_n;
      end
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        streaming <= 0; last <= 0; nm1 <= 0;
        j <= 0; n <= 0; row <= 0; open <= 0; done <= 0; stale <= 0; refreshed <= 0;
        rrds_c <= 0; noact_c <= 0; ref_pend <= 0; blk <= 0; rb <= 0; fault_r <= 0; credit <= 7'(CRED);
        ref_c <= RW'(RPH + PERIOD); running <= 0; phase <= 0;
        c_v <= 0; c_prio <= 0; c_op <= PRE; c_bank <= 0; c_oh <= 0;
        koh <= 8'b1; k1v <= 1'b0; rd_oh <= 32'b1; rd_bgoh <= 4'b1; cred_nz <= (CRED != 0);
        wq_n <= 0; wq_rp <= 0; wq_wp <= 0; wopen <= 0; rtw_c <= 0; wtr_c <= 0; c_w <= 0; c_wrow <= 0;
        rtw_z <= 1'b1; wtr_nz <= 1'b0; wq_ner <= 1'b0; sl_v <= 0; sl_hit <= 0; rp_oh <= WQ'(1);
      end else begin
        if (W) begin
          if (rd_ok) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
          if (wr_ok) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;
          rtw_z  <= rd_ok ? (T_RTW - 1 == 0) : (rtw_c <= 4'd1);
          wtr_nz <= wr_ok ? (T_WTR - 1 != 0) : (wtr_c > 4'd1);
          if (push) begin
            wqb[wq_wp] <= wq_bank; wqr[wq_wp] <= wq_row; wqc[wq_wp] <= wq_col; wqd[wq_wp] <= wq_data;
            wq_wp <= (wq_wp == WQW'(WQ - 1)) ? '0 : wq_wp + 1'b1;
            sl_boh[wq_wp] <= 32'b1 << wq_bank; sl_bgoh[wq_wp] <= 4'b1 << wq_bank[1:0];
          end
          // slot valid: a push sets slot wq_wp, a pop clears slot wq_rp (distinct: no push when full)
          sl_v <= nv;
          sl_conf <= nconf; sl_old <= nold;
          for (e = 0; e < WQ; e = e + 1) sl_hit[e] <= nhit[e];
          if (wr_ok) begin wq_rp <= (wq_rp == WQW'(WQ - 1)) ? '0 : wq_rp + 1'b1; rp_oh <= nrp; end
          wq_n <= wq_n + (WQW+1)'(push) - (WQW+1)'(wr_ok);
          wq_ner <= (wq_n + (WQW+1)'(push) - (WQW+1)'(wr_ok)) != 0;
          if (wact_fire) begin wopen[c_bank] <= 1'b1; wrow[c_bank] <= c_wrow; end
          if (row_fire && c_op == PRE && (c_oh & wopen) != 0) wopen <= wopen & ~c_oh;   // write or forced PRE
        end
        if (desc_acc) begin rd_oh <= 32'b1; rd_bgoh <= 4'b1; end
        else if (rd_ok) begin rd_oh <= 32'b1 << {j_p1[9:7], j_p1[1:0]}; rd_bgoh <= 4'b1 << j_p1[1:0]; end
        cred_nz <= rd_ok ? (cr_dec != 7'd0) : (cr_inc != 7'd0);
        koh <= koh_n; k1v <= (k_n != 3'd7) && (k_n + 3'd1 <= last_n);
        if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
        if (noact_c != 0) noact_c <= noact_c - 1'b1;
        credit <= rd_ok ? cr_dec : cr_inc;      // both sums precomputed; rd_ok only selects
        // refresh schedule
        ref_c <= ref_n; phase <= ~phase;
        // register the row decision for this PC's next slot (an off-slot cycle issues nothing)
        c_v <= slot_next && r_v; c_prio <= r_prio; c_op <= r_op; c_bank <= r_bank; c_oh <= r_oh;
        if (W) begin c_w <= r_w; c_wrow <= r_wrow; end
        if (REF_MODE && ref_c == RW'(LEAD)) begin ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; end
        // a due refresh that cannot issue (bank open / not granted) is a held fault
        if (ref_due && (!row_fire || !(c_op == REFPB || c_op == REFAB) ||
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
            refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
          end
          default: ;
        endcase
        // descriptor
        if (desc_v && !streaming && !fault_r) begin
          j <= 0; n <= desc_n; row <= desc_row; done <= 0; running <= 0;
          streaming <= (desc_n != 0); nm1 <= desc_n - 11'd1; last <= 3'((desc_n - 11'd1) >> 7);
          stale <= open_nx & ~(W ? wopen : 32'b0);  // rows still open from the old descriptor close first
        end
      end
    end
  end endgenerate
endmodule

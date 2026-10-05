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
  parameter integer WB_EN = 0, WQ = 8, T_RTW = 10, T_WTR = 14, T_WRR = 28, T_RCDW = 10
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
    wire [1:0] rd_bg = j[1:0];
    // ---- posted write queue (WB_EN) ----------------------------------------------------
    reg [4:0] wqb [0:WQ-1]; reg [18:0] wqr [0:WQ-1]; reg [4:0] wqc [0:WQ-1]; reg [255:0] wqd [0:WQ-1];
    reg [WQW:0] wq_n; reg [WQW-1:0] wq_rp, wq_wp;
    reg [31:0] wopen;                                 // banks open on a WRITE row (invisible to the stream)
    reg [18:0] wrow [0:31];                           // the row a write-open bank holds
    reg [3:0] rtw_c, wtr_c;
    reg c_w;                                          // the registered row command is a write ACT / write PRE
    reg [18:0] c_wrow;
    wire [31:0] rcdw_z, wrr_z;
    // queued-write needs: wneed (bank one-hot), and the oldest openable write (bank closed, no earlier queued
    // write to the same bank on a different row)
    reg [31:0] wneed, wneed_row_ok;                   // wneed_row_ok[b]: some queued write needs b on wrow[b]
    reg wa_v; reg [4:0] wa_b; reg [18:0] wa_r;
    always @* begin
      wneed = 0; wneed_row_ok = 0; wa_v = 0; wa_b = 0; wa_r = 0;
      if (W) for (integer e = 0; e < WQ; e = e + 1) if (e < wq_n) begin : scan
        automatic integer q = (wq_rp + e) % WQ;
        automatic bit blocked = 0;
        for (integer f = 0; f < WQ; f = f + 1) if (f < e) begin
          automatic integer qf = (wq_rp + f) % WQ;
          if (wqb[qf] == wqb[q] && wqr[qf] != wqr[q]) blocked = 1;
        end
        wneed[wqb[q]] = 1'b1;
        if (wopen[wqb[q]] && wrow[wqb[q]] == wqr[q]) wneed_row_ok[wqb[q]] = 1'b1;
        if (!wa_v && !blocked && !open[wqb[q]]) begin wa_v = 1; wa_b = wqb[q]; wa_r = wqr[q]; end
      end
    end
    wire [4:0] hb = wqb[wq_rp]; wire [18:0] hr = wqr[wq_rp];
    wire wq_ne = W && wq_n != 0;
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
      wire wr_e  = W && wr_ok && hb == 5'(b);
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = rd_ok && rd_bank == 5'(b);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; rcdw <= 0; wrr <= 0; end
        else begin
          if (W) begin
            if (act_e) rcdw <= 5'(T_RCDW - 1); else if (rcdw != 0) rcdw <= rcdw - 1'b1;
            if (wr_e) wrr <= 5'(T_WRR - 1); else if (wrr != 0) wrr <= wrr - 1'b1;
          end
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
      assign rcdw_z[b] = (rcdw == 0); assign wrr_z[b] = (wrr == 0);
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
      reg [2:0] rrdl; reg [1:0] ccdl; reg [3:0] faw;
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire faw_take = row_fire && c_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rrdl <= 0; ccdl <= 0; faw <= 0; end
        else begin
          if (act_g) rrdl <= 3'(T_RRDL - 1); else if (rrdl != 0) rrdl <= rrdl - 1'b1;
          if ((rd_ok && rd_bg == 2'(g)) || (W && wr_ok && hb[1:0] == 2'(g))) ccdl <= 2'(T_CCDL - 1); else if (ccdl != 0) ccdl <= ccdl - 1'b1;
          if (faw_take) faw <= 4'(T_FAW - 1); else if (faw != 0) faw <= faw - 1'b1;
        end
      assign rrdl_z[g] = (rrdl == 0); assign ccdl_z[g] = (ccdl == 0); assign faw_z[g] = (faw == 0);
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
    wire wr_bank_rdy = wq_ne && wopen[hb] && wrow[hb] == hr && rcdw_z[hb] && !blk[hb];
    assign wr_ok = wr_bank_rdy && ccdl_z[hb[1:0]] && rtw_c == 0 && !rd_block;
    assign rd_ok = running && streaming && !rd_block && open[rd_bank] && !stale[rd_bank] &&
                   rcd_z[rd_bank] && ccdl_z[rd_bg] && credit != 0 && !blk[rd_bank] &&
                   !(W && (wopen[rd_bank] || wr_bank_rdy || wtr_c != 0));
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
    wire [31:0] pre_cand = open & (done | stale) & ~blk & ras_z & rtp_z & ~(W ? wopen : 32'b0);
    // WB_EN: write ACT (oldest openable queued write) and write PRE (a write-open bank no queued write needs on
    // its row, after write recovery and tRAS)
    wire wact_ok = W && wa_v && !act_block && noact_c == 0 && rrds_c == 0 && faw_ok && aok_z[wa_b] &&
                   !blk[wa_b] && rrdl_z[wa_b[1:0]];
    wire [31:0] wpre_cand = W ? (wopen & ~wneed_row_ok & ~blk & ras_z & wrr_z) : 32'b0;
    wire [31:0] pre_oh, act_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : oh
      if (b == 0) begin : z assign pre_oh[b] = pre_cand[b]; end
      else begin : nz assign pre_oh[b] = pre_cand[b] & ~(|pre_cand[b-1:0]); end
      assign act_oh[b] = (3'(b >> 2) == k) ? act_oh8[b & 3] :
                         (3'(b >> 2) == k + 3'd1 && k != 3'd7) ? act_oh8[4 + (b & 3)] : 1'b0;
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
    reg r_w; reg [18:0] r_wrow;
    reg [31:0] r_oh;
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0; r_w = 0; r_wrow = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (|wpre_cand) begin r_v = 1; r_op = PRE; r_bank = wpre_sel; r_oh = 32'b1 << wpre_sel; r_w = 1; end
      else if (wact_ok) begin r_v = 1; r_op = ACT; r_bank = wa_b; r_oh = 32'b1 << wa_b; r_w = 1; r_wrow = wa_r; end
      else if (act_ok_any) begin r_v = 1; r_op = ACT; r_bank = act_bank(act_sel, k); r_oh = act_oh; end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    assign row_v = c_v; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = (W && c_w) ? c_wrow : row;
    assign col_v = rd_ok || (W && wr_ok); assign col_bank = (W && wr_ok) ? hb : rd_bank;
    assign col_col = (W && wr_ok) ? wqc[wq_rp] : j[6:2];
    assign col_we = W && wr_ok; assign col_wdata = (W && wr_ok) ? wqd[wq_rp] : 256'b0;
    assign col_row = (W && wr_ok) ? hr : 19'b0; assign wr_ack = W && wr_ok;
    assign wq_r = W && wq_n != (WQW+1)'(WQ); assign wq_empty = !wq_ne;
    assign desc_r = !streaming && !fault_r;
    assign busy = streaming; assign ref_fault = fault_r;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        streaming <= 0; last <= 0; nm1 <= 0;
        j <= 0; n <= 0; row <= 0; open <= 0; done <= 0; stale <= 0; refreshed <= 0;
        rrds_c <= 0; noact_c <= 0; ref_pend <= 0; blk <= 0; rb <= 0; fault_r <= 0; credit <= 7'(CRED);
        ref_c <= RW'(RPH + PERIOD); running <= 0; phase <= 0;
        c_v <= 0; c_prio <= 0; c_op <= PRE; c_bank <= 0; c_oh <= 0;
        wq_n <= 0; wq_rp <= 0; wq_wp <= 0; wopen <= 0; rtw_c <= 0; wtr_c <= 0; c_w <= 0; c_wrow <= 0;
      end else begin
        if (W) begin
          if (rd_ok) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
          if (wr_ok) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;
          if (wq_v && wq_r) begin
            wqb[wq_wp] <= wq_bank; wqr[wq_wp] <= wq_row; wqc[wq_wp] <= wq_col; wqd[wq_wp] <= wq_data;
            wq_wp <= (wq_wp == WQW'(WQ - 1)) ? '0 : wq_wp + 1'b1;
          end
          if (wr_ok) wq_rp <= (wq_rp == WQW'(WQ - 1)) ? '0 : wq_rp + 1'b1;
          wq_n <= wq_n + (WQW+1)'(wq_v && wq_r) - (WQW+1)'(wr_ok);
          if (row_fire && c_w && c_op == ACT) begin wopen[c_bank] <= 1'b1; wrow[c_bank] <= c_wrow; end
          if (row_fire && c_op == PRE && (c_oh & wopen) != 0) wopen <= wopen & ~c_oh;   // write or forced PRE
        end
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
          j <= j + 1'b1;
          if (j == nm1) streaming <= 0;
          if (j[6:2] == 5'd31) done[rd_bank] <= 1'b1;
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

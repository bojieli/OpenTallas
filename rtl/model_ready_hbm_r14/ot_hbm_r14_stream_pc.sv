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
module ot_hbm_r14_stream_pc #(
  parameter integer ENABLE   = 0,
  parameter integer REF_MODE = 1,
  parameter integer PC       = 0,
  parameter integer T_RCD = 19, T_RP = 16, T_RAS = 28, T_RTP = 6, T_CCDL = 3,
  parameter integer T_RRDS = 3, T_RRDL = 4, T_FAW = 15, T_RFC = 342, T_RFCPB = 196,
  parameter integer T_REFI = 3808, T_REFIPB = 119, T_RREFD = 8,
  parameter integer CRED = 32,
  parameter integer REF_PHASE = 0,
  parameter integer IDLE0 = 3, IDLE1 = 4, IDLE2 = 2, IDLE3 = 5,
  parameter integer IDLE4 = 1, IDLE5 = 6, IDLE6 = 0, IDLE7 = 7
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [10:0] desc_n,
  input  wire        go, input wire next_posted,
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
    localparam integer RW     = $clog2(2 * PERIOD + 2);
    function automatic [2:0] idle_rank(input [2:0] s);
      idle_rank = (s==3'(IDLE0))?0:(s==3'(IDLE1))?1:(s==3'(IDLE2))?2:(s==3'(IDLE3))?3:
                  (s==3'(IDLE4))?4:(s==3'(IDLE5))?5:(s==3'(IDLE6))?6:7;
    endfunction
    reg [10:0] j, n; reg [18:0] row;
    reg [31:0] open, done, stale, refreshed;
    reg [1:0] rrds_c; reg [3:0] noact_c; reg [RW-1:0] ref_c; reg ref_pend; reg [4:0] rb; reg fault_r;
    reg [6:0] credit; reg running;
    wire streaming = (j < n);
    wire [2:0] k = j[9:7];
    wire [10:0] nm1 = n - 11'd1;
    wire [2:0] last = nm1[9:7];
    wire [4:0] rd_bank = {j[9:7], j[1:0]};
    wire [1:0] rd_bg = j[1:0];
    // ---- refresh windows -------------------------------------------------------------
    wire ref_due = (ref_c == 0);
    wire act_block = REF_MODE ? (ref_c != 0 && ref_c < RW'(T_RREFD))
                              : (ref_c <= RW'(T_RP + T_RAS + 2));
    wire rd_block  = REF_MODE ? 1'b0 : (ref_c <= RW'(T_RP + T_RTP + 2));
    wire preall_ok = !REF_MODE && ref_c <= RW'(T_RP + 2) && ref_c >= RW'(T_RP) && (|open);
    // ---- row command (combinational) and its events ------------------------------------
    reg r_v, r_prio; reg [2:0] r_op; reg [4:0] r_bank;
    wire row_fire = r_v && row_gnt;
    wire rd_ok;
    // ---- per-bank timing state (down-counters; 0 = allowed) ------------------------------
    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy;
    wire [223:0] keys;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      reg [4:0] rcd, ras; reg [8:0] aok; reg [2:0] rtp;
      wire act_e = row_fire && r_op == ACT && r_bank == 5'(b);
      wire pre_e = row_fire && ((r_op == PRE && r_bank == 5'(b)) || r_op == PREALL);
      wire rfa_e = row_fire && r_op == REFAB;
      wire rfp_e = row_fire && r_op == REFPB && rb == 5'(b);
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
      // REFpb key: 127 refreshed; streaming/posted: open 24 (finished) / 32, protected (needed
      // within the next two sets) 16..18 farthest first, upcoming = distance, passed 8 + set;
      // idle: IDLE rank (+32 open); +64 if still busy from an earlier tRFCpb / tRC.
      localparam [2:0] S = 3'(b >> 2);
      wire [2:0] d = S - k;
      wire ahead = (S >= k && S <= last) || next_posted;
      wire [6:0] base = !streaming ? 7'(idle_rank(S)) + (open[b] ? 7'd32 : 7'd0) :
                        open[b] ? ((done[b] || stale[b]) ? 7'd24 : 7'd32) :
                        (ahead && d <= 3'd2) ? 7'd16 + 7'(3'd2 - d) :
                        ahead ? 7'(d) : 7'd8 + 7'(S);
      assign keys[b*7 +: 7] = refreshed[b] ? 7'd127 : base + ((!open[b] && aok_busy[b]) ? 7'd64 : 7'd0);
    end
    // ---- per-bank-group state ----------------------------------------------------------
    wire [3:0] rrdl_z, ccdl_z, faw_z;
    for (genvar g = 0; g < 4; g = g + 1) begin : bgs
      reg [2:0] rrdl; reg [1:0] ccdl; reg [3:0] faw;
      wire act_g = row_fire && r_op == ACT && r_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire faw_take = row_fire && r_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
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
    // ---- REFpb bank choice: argmin of keys, ties to the lowest bank ----------------------
    reg [6:0] bkey; reg [4:0] bsel;
    always @* begin
      bkey = 7'd127; bsel = 0;
      for (integer b = 31; b >= 0; b = b - 1)
        if (keys[b*7 +: 7] <= bkey) begin bkey = keys[b*7 +: 7]; bsel = 5'(b); end
    end
    // ---- column: one RD per cycle ------------------------------------------------------
    assign rd_ok = running && streaming && !rd_block && open[rd_bank] && !stale[rd_bank] &&
                   rcd_z[rd_bank] && ccdl_z[rd_bg] && credit != 0 && !(ref_pend && rb == rd_bank);
    // ---- row: refresh > forced PRE > ACT ahead (sets k, k+1) > PRE finished -----------
    function automatic [4:0] act_bank(input integer c, input [2:0] kk);
      act_bank = {(c >= 4) ? kk + 3'd1 : kk, 2'(c & 3)};
    endfunction
    integer ci, bi;
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; ci = 0; bi = 0;
      if (REF_MODE && ref_due && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; end
      else if (!REF_MODE && ref_due) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (REF_MODE && ref_pend && open[rb] && ras_z[rb] && rtp_z[rb]) begin
        r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; end
      else begin
        if (streaming && !act_block && noact_c == 0 && rrds_c == 0 && faw_ok)
          for (ci = 7; ci >= 0; ci = ci - 1)
            if ((ci < 4 || (k != 3'd7 && k + 3'd1 <= last)) && !open[act_bank(ci, k)] && !done[act_bank(ci, k)] &&
                !(ref_pend && rb == act_bank(ci, k)) && aok_z[act_bank(ci, k)] && rrdl_z[ci & 3]) begin
              r_v = 1; r_op = ACT; r_bank = act_bank(ci, k); end
        if (!r_v)
          for (bi = 31; bi >= 0; bi = bi - 1)
            if (open[bi] && (done[bi] || stale[bi]) && !(ref_pend && rb == 5'(bi)) && ras_z[bi] && rtp_z[bi]) begin
              r_v = 1; r_op = PRE; r_bank = 5'(bi); end
      end
    end
    assign row_v = r_v; assign row_prio = r_prio; assign row_op = r_op; assign row_bank = r_bank;
    assign row_row = row;
    assign col_v = rd_ok; assign col_bank = rd_bank; assign col_col = j[6:2];
    assign desc_r = !streaming && !fault_r;
    assign busy = streaming; assign ref_fault = fault_r;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        j <= 0; n <= 0; row <= 0; open <= 0; done <= 0; stale <= 0; refreshed <= 0;
        rrds_c <= 0; noact_c <= 0; ref_pend <= 0; rb <= 0; fault_r <= 0; credit <= 7'(CRED);
        ref_c <= RW'(REF_PHASE + PERIOD); running <= 0;
      end else begin
        if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
        if (noact_c != 0) noact_c <= noact_c - 1'b1;
        credit <= credit + 7'(cred_ret) - 7'(rd_ok);
        // refresh schedule
        if (ref_due) ref_c <= RW'(PERIOD - 1); else ref_c <= ref_c - 1'b1;
        if (REF_MODE && ref_c == RW'(LEAD)) begin ref_pend <= 1; rb <= bsel; end
        // a due refresh that cannot issue (bank open / not granted) is a held fault
        if (ref_due && (!row_gnt || (REF_MODE && (!ref_pend || open[rb] || !aok_z[rb]))
                        || (!REF_MODE && |open))) fault_r <= 1;
        // descriptor
        if (desc_v && !streaming && !fault_r) begin
          j <= 0; n <= desc_n; row <= desc_row; done <= 0; running <= 0;
          stale <= open & ~((row_fire && r_op == PRE) ? (32'b1 << r_bank) : 32'b0);  // old rows close first
        end
        if (streaming && go) running <= 1;
        // column
        if (rd_ok) begin
          j <= j + 1'b1;
          if (j[6:2] == 5'd31) done[rd_bank] <= 1'b1;
        end
        // row
        if (row_fire) case (r_op)
          ACT: begin open[r_bank] <= 1; rrds_c <= 2'(T_RRDS - 1); end
          PRE: begin open[r_bank] <= 0; stale[r_bank] <= 0; end
          PREALL: begin open <= 0; stale <= 0; end
          REFPB: begin
            noact_c <= 4'(T_RREFD - 1); ref_pend <= 0;
            refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
          end
          default: ;
        endcase
      end
    end
  end endgenerate
endmodule

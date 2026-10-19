`timescale 1ps/1fs
// HBM-BW 2026-10-19: MULTI-ROW access-queue sequencer for ONE HBM3E pseudo-channel (successor of the AQ_RD path of
// ot_hbm_r14_stream_pc_strap, which stays byte-identical).  Same clock (CK/2 = 1.024 ns), same timing parameters, same
// per-channel TDM row slot (PC[0] = cycle parity), same REFpb schedule (one REFpb every tREFIpb = 118 cycles, each bank
// once per 32-command round, chosen LEAD cycles ahead, never late: a due REFpb that cannot issue is a held fault).
//
// What changes (measured cause of the ~52 B/edge HBM boundary, lanes/HBM-BW.md):
//  * the strap's AQ entries all address ONE descriptor row: the owning leaf had to drain every queued access AND every
//    read response, precharge every bank and post a new descriptor before ANY access to another row (~55-60 exposed
//    cycles per distinct-row 64-line block).  Here every queued entry carries its own ROW and every bank its own open
//    row (orow): an entry's bank is ACTIVATED with the entry's row as soon as it is queued (oldest first, the oldest
//    entry of a bank decides), so the next block's rows open while the current block's columns stream (tRCD hidden by
//    the 32-entry queue); a bank is precharged as soon as no queued entry needs its open row.
//  * REFpb bank choice (MRKEY=1): never a bank a queued entry needs or an open bank; among the rest, the bank whose
//    bank-set (bank[4:2]) is FARTHEST AHEAD of the newest queued entry's set in the cyclic set order (d = set - tail_set
//    mod 8: d = 7, 0, 1, 2, 3 are protected; d = 6 first, then 5, then 4).  COMPILER CONTRACT (smb_unit layout): a
//    block owns one bank-set of each of its PCs and consecutive blocks of the static fetch order advance the set
//    cyclically (routed experts alternate two sets), so a refreshed bank (blocked LEAD + tRFCpb = 244 cycles) is not
//    needed for >= 4 blocks.  MRKEY=0: the strap's idle ranking (diagnostic).  Protected window = tail-2 .. tail+3
//    (routed experts cycle THREE sets, so a set is re-used two blocks later).
//  * PULLIN (JEDEC pull-in, default 8): REFpb ahead of schedule on unprotected banks; a slot whose best bank is protected
//    is skipped while pulled-in credit remains (the round-end forced refresh of a needed bank was a ~190-cycle stall).
// Column commands stay strictly in queue order (the K response order is the request order, as before).
module ot_hbm_r14_aq_pc_safe #(
  parameter integer T_RCD = 19, T_RP = 16, T_RAS = 28, T_RTP = 6, T_CCDL = 3,
  parameter integer T_RRDS = 3, T_RRDL = 4, T_FAW = 15, T_RFCPB = 196,
  parameter integer T_REFIPB = 118, T_RREFD = 8,
  parameter integer T_RTW = 10, T_WTR = 14, T_WRR = 28, T_RCDW = 10,
  parameter integer WQ = 32, RW_ROW = 19,
  parameter integer IDLE0 = 3, IDLE1 = 4, IDLE2 = 2, IDLE3 = 5, IDLE4 = 1, IDLE5 = 6, IDLE6 = 0, IDLE7 = 7,
  parameter integer MRKEY = 1,
  parameter integer PULLIN = 8
)(
  input  wire        clk, rst_n,
  input  wire        slot_parity, input wire [7:0] refresh_reload,
  output wire        row_v, output wire [2:0] row_op, output wire [4:0] row_bank, output wire [RW_ROW-1:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  output wire        ref_fault,
  input  wire        wr_v, input wire [4:0] wr_bank, input wire [4:0] wr_col, input wire [RW_ROW-1:0] wr_row,
  input  wire        wr_rd, output wire wr_r, output wire col_we, output wire col_aq,
  output wire [31:0] dbg_held
);
  localparam [2:0] PRE=0, ACT=1, REFPB=6;
  localparam integer PERIOD = T_REFIPB;
  localparam integer LEAD = T_RAS + T_RP + 4;
  localparam integer RW = $clog2(2 * PERIOD + 4);
  localparam integer WQW = $clog2(WQ);
  initial if (PERIOD != 118) $fatal(1, "HBM refresh class mismatch");
  function automatic [2:0] idle_rank(input [2:0] s);
    idle_rank = (s==3'(IDLE0))?0:(s==3'(IDLE1))?1:(s==3'(IDLE2))?2:(s==3'(IDLE3))?3:
                (s==3'(IDLE4))?4:(s==3'(IDLE5))?5:(s==3'(IDLE6))?6:7;
  endfunction
  // ---- access queue (ring) -------------------------------------------------------------
  // FIFO metadata is SRAM. Only the head and per-bank summaries are flops.
  wire [255:0] qm;
  wire [WQW-1:0] qwp = WQW'(q_rp + q_n);
  wire qpush=wr_v&&wr_r;
  wire [WQW-1:0] qread=wr_ok ? q_rp+1'b1 : q_rp;
  reg qfresh; reg [WQW-1:0] qfresh_addr; reg [29:0] qfresh_data;
  wire [29:0] qhead=(qfresh&&qfresh_addr==q_rp)?qfresh_data:qm[29:0];
  ot_sram_1r1w_128x256_m1_r2c2 u_queue(.clk(clk),.r_ce_in(1'b1),.r_addr_in(7'(qread)),.rd_out(qm),
    .w_ce_in(qpush),.w_addr_in(7'(qwp)),.wd_in({226'b0,wr_bank,wr_col,wr_row,wr_rd}),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  reg [WQW:0] bank_n[0:31];
  reg [RW_ROW-1:0] look_row[0:31];
  always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin qfresh<=0;qfresh_addr<=0;qfresh_data<=0;
      for(integer b=0;b<32;b=b+1)begin bank_n[b]<=0;end
    end else begin
      qfresh<=qpush;qfresh_addr<=qwp;qfresh_data<={wr_bank,wr_col,wr_row,wr_rd};
      for(integer b=0;b<32;b=b+1)begin
        case({qpush&&wr_bank==b,wr_ok&&hb==b})
          2'b10:bank_n[b]<=bank_n[b]+1'b1;
          2'b01:bank_n[b]<=bank_n[b]-1'b1;
          default:bank_n[b]<=bank_n[b];
        endcase
        // The globally oldest head is authoritative across row conflicts. Incoming
        // traffic establishes lookahead while a bank has no outstanding sectors.

      end
    end
  end
  always @(posedge clk)begin
    for(integer b=0;b<32;b=b+1)begin
      if(q_ne&&hb==b)look_row[b]<=hrow;
      else if(qpush&&wr_bank==b&&bank_n[b]==0)look_row[b]<=wr_row;
    end
    if(row_fire&&c_op==ACT)orow[c_bank]<=c_row;
  end
  reg [WQW:0] q_n; reg [WQW-1:0] q_rp;
  wire [4:0] hb=qhead[29:25], hc=qhead[24:20]; wire [RW_ROW-1:0] hrow=qhead[19:1]; wire hr=qhead[0];   // registered head (valid when q_n != 0)
  reg [2:0] tail_set;                                   // bank-set of the newest pushed entry
  // ---- bank / group state ---------------------------------------------------------------
  reg [31:0] open, refreshed, blk;
  reg [RW_ROW-1:0] orow [0:31];
  reg [1:0] rrds_c; reg [3:0] noact_c; reg [RW-1:0] ref_c; reg ref_pend; reg [4:0] rb; reg fault_r;
  reg [3:0] rtw_c, wtr_c; reg phase;
  reg c_v; reg [2:0] c_op; reg [4:0] c_bank; reg [31:0] c_oh; reg [RW_ROW-1:0] c_row;
  wire row_fire = c_v;
  wire q_ne = q_n != 0;
  wire ref_due = (ref_c == 0);
  wire slot_next = (phase != slot_parity);
  wire [RW-1:0] ref_n = ref_due ? RW'(PERIOD - 1) : ref_c - 1'b1;
  wire ref_due_n = (ref_n == 0);
  always @(posedge clk) if (!rst_n) ref_c <= RW'(refresh_reload); else ref_c <= ref_n;
  wire act_block = (ref_n != 0 && ref_n < RW'(T_RREFD));
  // ---- queue-derived bank sets (held = a queued entry needs the bank's OPEN row; need = any queued entry) ---------
  reg [31:0] held, need, act_cand_oh; reg act_cand; reg [4:0] act_b; reg [RW_ROW-1:0] act_row;
  // Per-bank summaries replace the old WQ-wide indexed scan. Four groups
  // select independently; one additional registered stage chooses a group.
  reg [3:0] ac_v;reg[4:0]ac_b[0:3];reg[RW_ROW-1:0]ac_row[0:3];
  reg ac2_v;reg[4:0]ac2_b;reg[RW_ROW-1:0]ac2_row;
  always @* begin
    held=0;need=0;
    for(integer b=0;b<32;b=b+1)begin
      need[b]=bank_n[b]!=0;
      held[b]=bank_n[b]!=0&&open[b]&&look_row[b]==orow[b];
    end
    act_b=ac2_b;act_row=ac2_row;act_cand_oh=32'b1<<ac2_b;
    act_cand=ac2_v&&bank_n[ac2_b]!=0&&!open[ac2_b]&&!blk[ac2_b]&&look_row[ac2_b]==ac2_row;
  end
  always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin ac_v<=0;ac2_v<=0;ac2_b<=0;ac2_row<=0;
      for(integer g=0;g<4;g=g+1)begin ac_b[g]<=0;ac_row[g]<=0;end
    end else begin
      for(integer g=0;g<4;g=g+1)begin:SG
        reg found;found=0;ac_v[g]<=0;
        for(integer j=0;j<8;j=j+1)if(!found&&bank_n[g*8+j]!=0&&!open[g*8+j]&&!blk[g*8+j])begin
          found=1;ac_v[g]<=1;ac_b[g]<=5'(g*8+j);ac_row[g]<=look_row[g*8+j];
        end
      end
      begin:S2 reg found;found=0;ac2_v<=0;
        for(integer g=0;g<4;g=g+1)if(!found&&ac_v[g])begin found=1;ac2_v<=1;ac2_b<=ac_b[g];ac2_row<=ac_row[g];end
      end
    end
  end
  assign dbg_held = held;
  // ---- per-bank timing ------------------------------------------------------------------
  wire [31:0] rcd_z, rcdw_z, ras_z, rtp_z, aok_z, aok_busy;
  wire hit_rd = col_v && !col_we, hit_wr = col_v && col_we;
  for (genvar b = 0; b < 32; b = b + 1) begin : bank
    reg [4:0] rcd, ras, wrr; reg [8:0] aok; reg [2:0] rtp;
    wire act_e = row_fire && c_op == ACT && c_oh[b];
    wire pre_e = row_fire && c_op == PRE && c_oh[b];
    wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
    wire rd_e = hit_rd && hb == 5'(b);
    wire wr_e = hit_wr && hb == 5'(b);
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; wrr <= 0; end
      else begin
        if (wr_e) wrr <= 5'(T_WRR - 1); else if (wrr != 0) wrr <= wrr - 1'b1;
        if (act_e) begin rcd <= 5'(T_RCD - 1); ras <= 5'(T_RAS - 1); end
        else begin if (rcd != 0) rcd <= rcd - 1'b1; if (ras != 0) ras <= ras - 1'b1; end
        if (rd_e) rtp <= 3'(T_RTP - 1); else if (rtp != 0) rtp <= rtp - 1'b1;
        if (act_e) aok <= 9'(T_RAS + T_RP - 1);
        else if (rfp_e) aok <= 9'(T_RFCPB - 1);
        else if (pre_e && aok < 9'(T_RP)) aok <= 9'(T_RP - 1);
        else if (aok != 0) aok <= aok - 1'b1;
      end
    assign rcd_z[b] = (rcd == 0); assign rcdw_z[b] = (rcd <= 5'(T_RCD - T_RCDW));
    assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0) && (wrr == 0);
    assign aok_z[b] = (aok == 0); assign aok_busy[b] = (aok > 9'(LEAD));
  end
  // ---- per-bank-group --------------------------------------------------------------------
  wire [3:0] rrdl_z, ccdl_z; wire faw_ok;
  reg [3:0] fawq [0:3];
  for (genvar g = 0; g < 4; g = g + 1) begin : bgs
    reg [2:0] rrdl; reg [1:0] ccdl;
    wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
    wire ccdl_e = col_v && hb[1:0] == 2'(g);
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin rrdl <= 0; ccdl <= 0; end
      else begin
        if (act_g) rrdl <= 3'(T_RRDL - 1); else if (rrdl != 0) rrdl <= rrdl - 1'b1;
        if (ccdl_e) ccdl <= 2'(T_CCDL - 1); else if (ccdl != 0) ccdl <= ccdl - 1'b1;
      end
    assign rrdl_z[g] = (rrdl == 0); assign ccdl_z[g] = (ccdl == 0);
  end
  // tFAW: four ACT time stamps (down-counters); an ACT needs a free (zero) one
  assign faw_ok = (fawq[0] == 0) || (fawq[1] == 0) || (fawq[2] == 0) || (fawq[3] == 0);
  // ---- REFpb choice: argmin of keys (registered, 4 cycles stale like the strap) --------------------------------------
  reg [6:0] keys [0:31];
  integer kb;
  always @* for (kb = 0; kb < 32; kb = kb + 1) begin : keyb
    reg [2:0] s, d; reg prot;
    s = 3'(kb >> 2); d = s - tail_set; prot = (d >= 3'd6) || (d <= 3'd3);
    if (refreshed[kb]) keys[kb] = 7'd127;
    else if (MRKEY == 0) keys[kb] = 7'(idle_rank(s)) + (open[kb] ? 7'd32 : 7'd0) + ((!open[kb] && aok_busy[kb]) ? 7'd64 : 7'd0);
    else if (need[kb]) keys[kb] = 7'd120;
    else if (open[kb]) keys[kb] = 7'd112;
    else keys[kb] = (prot ? 7'd32 + 7'(d) : 7'(3'd5 - d)) + (aok_busy[kb] ? 7'd64 : 7'd0);
  end
  reg[6:0] rkey;wire[6:0]bkey;wire[4:0]bsel;
  // Balanced registered tournament: one 7-bit comparison per stage. The old
  // 32-way serial priority reduction followed by three delay flops is removed.
  wire[6:0]rk[0:5][0:31];wire[4:0]rs[0:5][0:31];
  for(genvar k=0;k<32;k=k+1)begin:K0 assign rk[0][k]=keys[k];assign rs[0][k]=5'(k);end
  for(genvar l=0;l<5;l=l+1)begin:KL
    for(genvar k=0;k<(16>>l);k=k+1)begin:KP
      reg[6:0]key_q;reg[4:0]sel_q;
      always @(posedge clk or negedge rst_n)if(!rst_n)begin key_q<=127;sel_q<=0;end
      else if(rk[l][2*k]<=rk[l][2*k+1])begin key_q<=rk[l][2*k];sel_q<=rs[l][2*k];end
      else begin key_q<=rk[l][2*k+1];sel_q<=rs[l][2*k+1];end
      assign rk[l+1][k]=key_q;assign rs[l+1][k]=sel_q;
    end
  end
  assign bkey=rk[5][0];assign bsel=rs[5][0];
  // ---- column: the head entry, strictly in order --------------------------------------------------------------------
  wire [31:0] hb_oh = 32'b1 << hb;
  wire [31:0] pre_fl = (c_v && c_op == PRE) ? c_oh : 32'b0;
  wire head_bank_rdy = q_ne && |(hb_oh & open & (hr ? rcd_z : rcdw_z) & ~blk & ~pre_fl) && orow[hb] == hrow;
  wire wr_ok = head_bank_rdy && ccdl_z[hb[1:0]] && (hr ? (wtr_c == 0) : (rtw_c == 0));
  assign col_v = wr_ok; assign col_we = wr_ok && !hr; assign col_aq = wr_ok && hr;
  assign col_bank = hb; assign col_col = hc;
  assign wr_r = q_n != (WQW+1)'(WQ);
  // ---- row command: REFpb due > forced PRE > ACT (oldest queued closed bank) > PRE (open row no entry needs) ----------
  wire forced_pre = ref_pend && |(blk & open & ras_z & rtp_z);
  wire [31:0] pre_cand = open & ~held & ~blk & ras_z & rtp_z;
  reg [4:0] pre_sel; integer pi_;
  always @* begin pre_sel = 0; for (pi_ = 31; pi_ >= 0; pi_ = pi_ - 1) if (pre_cand[pi_]) pre_sel = 5'(pi_); end
  // ---- PULLIN (JEDEC pull-in): while a closed, unneeded, unprotected bank (key < 16) is available, issue up to PULLIN
  // REFpb AHEAD of the schedule; a scheduled slot whose best bank is protected (key >= 32) is then skipped (paid ahead).
  // No REFpb is ever later than the strict schedule; each bank still once per 32-command round.
  reg [3:0] pin; reg ep, skip; reg [3:0] sact;
  wire ep_start = (PULLIN > 0) && !ep && !ref_pend && 32'(pin) < PULLIN && ref_c > RW'(LEAD + 12) && bkey < 7'd16 &&
                  sact >= 4'd6;
  wire ep_rdy = ep && !(|(blk & open)) && (|(blk & aok_z)) && noact_c == 0 && sact >= 4'(T_RREFD + 2) && ref_c > RW'(LEAD + 2);
  wire act_ok = act_cand && (|(act_cand_oh & aok_z)) && rrdl_z[act_b[1:0]] && rrds_c == 0 && faw_ok && !act_block &&
                noact_c == 0 && !((ref_c == RW'(LEAD) || ref_c == RW'(LEAD + 1) || ep_start) && act_b == bsel);
  reg r_v; reg [2:0] r_op; reg [4:0] r_bank; reg [31:0] r_oh; reg [RW_ROW-1:0] r_row;
  always @* begin
    r_v = 0; r_op = PRE; r_bank = 0; r_oh = 0; r_row = 0;
    if (ref_due_n && ref_pend) begin r_v = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
    else if (ep_rdy) begin r_v = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
    else if (forced_pre) begin r_v = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
    else if (act_ok) begin r_v = 1; r_op = ACT; r_bank = act_b; r_oh = act_cand_oh; r_row = act_row; end
    else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = 32'b1 << pre_sel; end
  end
  assign row_v = c_v; assign row_op = c_op; assign row_bank = c_bank; assign row_row = c_row;
  assign ref_fault = fault_r;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      q_n <= 0; q_rp <= 0; tail_set <= 0;
      open <= 0; refreshed <= 0; blk <= 0; rrds_c <= 0; noact_c <= 0; ref_pend <= 0; rb <= 0; fault_r <= 0;
      rtw_c <= 0; wtr_c <= 0; phase <= 0; rkey <= 127; pin <= 0; ep <= 0; skip <= 0; sact <= 0; c_v <= 0; c_op <= PRE; c_bank <= 0; c_oh <= 0; c_row <= 0;
      for (integer f = 0; f < 4; f = f + 1) fawq[f] <= 0;

    end else begin
      // queue
      if(qpush)tail_set<=wr_bank[4:2];
      case({qpush,wr_ok})
        2'b10:q_n<=q_n+1'b1;2'b01:q_n<=q_n-1'b1;default:q_n<=q_n;
      endcase
      if (wr_ok) q_rp <= WQW'(q_rp + 1'b1);
      if (col_aq) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
      if (col_we) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;
      if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
      if (noact_c != 0) noact_c <= noact_c - 1'b1;
      for (integer f = 0; f < 4; f = f + 1) if (fawq[f] != 0) fawq[f] <= fawq[f] - 1'b1;
      phase <= ~phase;
      c_v <= slot_next && r_v; c_op <= r_op; c_bank <= r_bank; c_oh <= r_oh; c_row <= r_row;
      if (row_fire && (c_op == ACT || c_op == REFPB)) sact <= 0; else if (sact != 4'hf) sact <= sact + 1'b1;
      if (ref_c == RW'(LEAD)) begin
        if (ep) begin ref_pend <= 1; ep <= 0; end                               // a pending pull-in becomes this slot
        else if (pin != 0 && bkey >= 7'd32) begin pin <= pin - 1'b1; skip <= 1; end   // paid ahead: skip
        else begin ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; rkey <= bkey; end
      end else if (ep_start) begin ep <= 1; rb <= bsel; blk <= 32'b1 << bsel; rkey <= bkey; end
      else if (ep && |(blk & open)) begin ep <= 0; blk <= 0; end
      if (ref_due) skip <= 0;
      if (ref_due && !skip && (!row_fire || c_op != REFPB || |(blk & open) || |(blk & ~aok_z))) fault_r <= 1;
      if (row_fire) case (c_op)
        ACT: begin
          open <= open | c_oh; rrds_c <= 2'(T_RRDS - 1);
          begin : fawt
            reg tk; tk = 0;
            for (integer f = 0; f < 4; f = f + 1) if (!tk && fawq[f] == 0) begin fawq[f] <= 4'(T_FAW - 1); tk = 1; end
          end
        end
        PRE: open <= open & ~c_oh;
        REFPB: begin
          noact_c <= 4'(T_RREFD - 1); ref_pend <= 0; blk <= 0;
          if (ep && !ref_pend) begin ep <= 0; pin <= pin + 1'b1; end
          refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
        end
        default: ;
      endcase
    end
  end
endmodule

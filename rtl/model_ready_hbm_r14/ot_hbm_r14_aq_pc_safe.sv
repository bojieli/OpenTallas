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
  parameter integer PULLIN = 8,
  parameter integer ROW_REGIONS = 0
)(
  input  wire        clk, rst_n, input wire[63:0]reset_regions,
  input  wire        slot_parity, input wire [7:0] refresh_reload,
  output wire        row_v, output wire [2:0] row_op, output wire [4:0] row_bank, output wire [RW_ROW-1:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  output wire        ref_fault,
  input  wire        wr_v, input wire [4:0] wr_bank, input wire [4:0] wr_col, input wire [RW_ROW-1:0] wr_row,
  input wire [8*RW_ROW-1:0] wr_row_regions,
  input  wire        wr_rd, output wire wr_r, output wire col_we, output wire col_aq,
  output wire [31:0] dbg_held
);
  localparam [2:0] PRE=0, ACT=1, REFPB=6;
  localparam integer PERIOD = T_REFIPB;
  localparam integer LEAD = T_RAS + T_RP + 4;
  localparam integer RW = $clog2(2 * PERIOD + 4);
  localparam integer WQW = $clog2(WQ);
  initial if(ROW_REGIONS!=0&&ROW_REGIONS!=8)$fatal(1,"AQ ROW_REGIONS must be0 or8");
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
  wire[31:0]bank_col;
  // Keep the current head in flops and prefetch its successor. On a pop,
  // request the following successor while capturing the SRAM's old output.
  // SRAM clk->q therefore ends at the head flops, outside column eligibility.
  // The two overlapped heads sustain one pop per edge, including ring wrap.
  (* keep="true",dont_touch="true" *) reg[WQW-1:0]q_rp_plus1,q_rp_plus2;
  wire [WQW-1:0] qread=wr_ok ? q_rp_plus2 : q_rp_plus1;
  reg qfresh; reg [WQW-1:0] qfresh_addr; reg [29:0] qfresh_data;
  reg [29:0] qhead;
  (* keep="true",dont_touch="true" *) reg head_read_global;
  (* keep="true",dont_touch="true" *) reg[4:0]head_bank_global;
  always @(posedge clk)head_read_global<=head_d[0];
  // Same-edge local head copies: each row bit drives eight comparators and
  // eight look-row capture muxes; each read flag serves eight bank timers.
  (* keep="true",dont_touch="true" *) reg [19:0] head_local[0:7];
  // Canonical head mux owns hold/advance once. Local copies capture the
  // identical next state unconditionally at the original head edge.
  wire [3:0] head_capture_regions,head_push_regions;
  wire [29:0] head_d;
  (* keep="true",dont_touch="true" *) reg [WQW-1:0] fresh_addr_local[0:3],successor_local[0:3];
  (* keep="true",dont_touch="true" *) reg [3:0] fresh_local;
  for(genvar g=0;g<4;g=g+1)begin:HEAD_IDENTITY_LOCAL
    always @(posedge clk)fresh_addr_local[g]<=qwp;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin
      successor_local[g]<=1;fresh_local[g]<=0;
    end else begin
      successor_local[g]<=wr_ok?q_rp_plus1+1'b1:q_rp_plus1;
      fresh_local[g]<=qpush;
    end
    assign head_push_regions[g]=qpush&&((q_n_local[g]==0)||(wr_ok&&q_n_local[g]==1));
    assign head_capture_regions[g]=head_push_regions[g]||(wr_ok&&q_n_local[g]>1);
  end
  for(genvar g=0;g<4;g=g+1)begin:HEAD_WORD_LOCAL
    localparam LO=(g==3)?20:g*8;
    localparam B=(g==3)?10:((g==2)?4:8);
    wire [B-1:0] pref=(fresh_local[g]&&fresh_addr_local[g]==successor_local[g])?
       qfresh_data[LO+:B]:qm[LO+:B];
    wire [29:0] pushed={wr_bank,wr_col,wr_row,wr_rd};
    wire[B-1:0]held_word;
    if(g==3)assign held_word={head_bank_global,qhead[24:20]};
    else assign held_word=qhead[LO+:B];
    assign head_d[LO+:B]=head_capture_regions[g]?
       (head_push_regions[g]?pushed[LO+:B]:pref):held_word;
  end
  for(genvar g=0;g<8;g=g+1)begin:HEAD_LOCAL
    always @(posedge clk)
      `ifdef BW_AQ_MUT_HEAD
      head_local[g]<=head_d[19:0] ^ (g==0?20'd2:20'd0);
`else
      head_local[g]<=head_d[19:0];
`endif
  end
  (* keep="true",dont_touch="true" *) reg [4:0] head_bank_local;
  (* keep="true",dont_touch="true" *) reg [4:0] look_head_bank_local[0:1];
  for(genvar h=0;h<2;h=h+1)begin:LOOK_BANK_LOCAL
    always @(posedge clk)look_head_bank_local[h]<=head_d[29:25];
  end
  wire [31:0] hb_oh=32'b1<<head_bank_local;
  wire [WQW-1:0] qsuccessor=q_rp_plus1;
  wire [29:0] qprefetch=(qfresh&&qfresh_addr==qsuccessor)?qfresh_data:qm[29:0];
  wire head_from_push=qpush&&((q_n==0)||(wr_ok&&q_n==1));
  wire [29:0] head_next=head_from_push?{wr_bank,wr_col,wr_row,wr_rd}:qprefetch;
  always @(posedge clk)begin
    qhead<=head_d;
    head_bank_local<=head_d[29:25];head_bank_global<=head_d[29:25];
  end
  ot_sram_1r1w_128x256_m1_r2c2 u_queue(.clk(clk),.r_ce_in(1'b1),.r_addr_in(7'(qread)),.rd_out(qm),
    .w_ce_in(qpush),.w_addr_in(7'(qwp)),.wd_in({226'b0,wr_bank,wr_col,wr_row,wr_rd}),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  (* keep="true",dont_touch="true" *) reg [WQW:0] bank_n[0:31];
  (* keep="true",dont_touch="true" *) reg [WQW:0] bank_n_word_local[0:1][0:31];
  reg [RW_ROW-1:0] look_row[0:31];
  // Same-edge reset copies from the parent relay: each bank resets its own
  // 27 timer flops and seven count bits rather than a thousand-sink reset net.
  for(genvar b=0;b<32;b=b+1)begin:BCOUNT
    wire bp=(wr_v&&(q_n_local[b/8]!=(WQW+1)'(WQ)))&&wr_bank==b;
    wire [WQW:0] bn_next=bank_n[b]+(bp&&!bank_col[b]?(WQW+1)'(1):
                    (!bp&&bank_col[b]?{(WQW+1){1'b1}}:(WQW+1)'(0)));
    always @(posedge clk or negedge reset_regions[b])if(!reset_regions[b])bank_n[b]<=0;
      else bank_n[b]<=bn_next;
    for(genvar k=0;k<2;k=k+1)begin:WORD_COUNT
      always @(posedge clk or negedge reset_regions[b])
        if(!reset_regions[b])bank_n_word_local[k][b]<=0;
        else bank_n_word_local[k][b]<=bn_next;
    end
  end
  always @(posedge clk or negedge rst_n)if(!rst_n)qfresh<=0;else qfresh<=qpush;
  always @(posedge clk)begin qfresh_addr<=qwp;qfresh_data<={wr_bank,wr_col,wr_row,wr_rd};end
  always @(posedge clk)begin
    for(integer b=0;b<32;b=b+1)begin
      for(integer k=0;k<3;k=k+1)begin
        for(integer bit_=0;bit_<8;bit_=bit_+1)if(k*8+bit_<RW_ROW)begin
          if((q_n_local[b/8]!=0)&&
             (k==0?head_bank_local:look_head_bank_local[k-1])==5'(b))
            look_row[b][k*8+bit_]<=head_local[b/4][k*8+bit_+1];
          else if(wr_v&&(q_n_local[b/8]!=(WQW+1)'(WQ))&&wr_bank==b&&
              (k==0?bank_n[b]:bank_n_word_local[k-1][b])==0)
            look_row[b][k*8+bit_]<=
`ifdef BW_AQ_MUT_WRROW
              ((ROW_REGIONS==8&&b/4==3&&k*8+bit_==0)?1'b1:1'b0)^
`endif
              (ROW_REGIONS==8?wr_row_regions[(b/4)*RW_ROW+k*8+bit_]:wr_row[k*8+bit_]);
          if(row_word_act_local[k][b/8]&&c_oh[b])
            orow[b][k*8+bit_]<=row_local[b/8][k*8+bit_];
        end
      end
    end
  end
  reg [WQW:0] q_n; reg [WQW-1:0] q_rp;
  wire [4:0] hb=head_bank_global, hc=qhead[24:20]; wire [RW_ROW-1:0] hrow=qhead[19:1]; wire hr=head_read_global;   // registered head (valid when q_n != 0)
  (* keep="true",dont_touch="true" *) reg [2:0] tail_set_regions[0:7];
  for(genvar t=0;t<8;t=t+1)begin:TAIL_SET_REGION
    always @(posedge clk or negedge rst_n)if(!rst_n)tail_set_regions[t]<=0;
      else if(wr_v&&(q_n_local[t/2]!=(WQW+1)'(WQ)))tail_set_regions[t]<=wr_bank[4:2];
  end
  // ---- bank / group state ---------------------------------------------------------------
  reg [31:0] open, refreshed;
  (* keep="true",dont_touch="true" *) reg [4:0] blk_bank;
  (* keep="true",dont_touch="true" *) reg blk_valid;
  wire [31:0] blk;
  (* keep="true",dont_touch="true" *) reg[4:0]blk_bank_regions[1:3];
  (* keep="true",dont_touch="true" *) reg[3:1]blk_valid_regions;
  reg [RW_ROW-1:0] orow [0:31];
  reg [1:0] rrds_c; reg [3:0] noact_c; reg [RW-1:0] ref_c; reg ref_pend; reg [4:0] rb; reg fault_r;
  reg [3:0] rtw_c, wtr_c; reg phase;
  reg c_v; reg [2:0] c_op; reg [4:0] c_bank; wire [31:0] c_oh;
  (* keep="true",dont_touch="true" *) reg [4:0] command_bank_local;
  (* keep="true",dont_touch="true" *) reg command_bank_valid; reg [RW_ROW-1:0] c_row;
  (* keep="true",dont_touch="true" *) reg[4:0]command_bank_regions[1:3];
  (* keep="true",dont_touch="true" *) reg[3:1]command_valid_regions;
  wire blk_set=(ref_c==RW'(LEAD))?
     (!ep&&!(pin!=0&&(bkey>=7'd32||ref_choice_protected))):ep_start;
  wire blk_clear=((ref_c!=RW'(LEAD))&&!ep_start&&ep&&|(blk&open))||
     (row_fire&&c_op==REFPB);
  for(genvar g=1;g<4;g=g+1)begin:BANK_CONTROL_REGION
    always @(posedge clk or negedge reset_regions[32+g])
      if(!reset_regions[32+g])begin
        command_bank_regions[g]<=0;command_valid_regions[g]<=0;
        blk_bank_regions[g]<=0;blk_valid_regions[g]<=0;
      end else begin
        command_bank_regions[g]<=r_bank;command_valid_regions[g]<=slot_next&&r_v;
        blk_bank_regions[g]<=blk_set?bsel:blk_bank;
        blk_valid_regions[g]<=blk_clear?1'b0:(blk_set?1'b1:blk_valid);
      end
  end
  for(genvar b=0;b<32;b=b+1)begin:BANK_CONTROL_DECODE
    if(b/8==0)begin
      assign c_oh[b]=command_bank_valid&&command_bank_local==5'(b);
      assign blk[b]=blk_valid&&blk_bank==5'(b);
    end else begin
      assign c_oh[b]=command_valid_regions[b/8]&&command_bank_regions[b/8]==5'(b);
      assign blk[b]=blk_valid_regions[b/8]&&blk_bank_regions[b/8]==5'(b);
    end
  end

  // Registered decoded commands share the original command capture edge.
  // The three decoded controls and row word are local to sixteen banks.
  (* keep="true",dont_touch="true" *) reg [21:0] row_local[0:3];
  (* keep="true",dont_touch="true" *) reg [3:0] row_word_act_local[0:2];
  for(genvar g=0;g<4;g=g+1)begin:ROW_LOCAL
    for(genvar k=0;k<3;k=k+1)begin:WORD_ACT
      always @(posedge clk or negedge reset_regions[32+g])
        if(!reset_regions[32+g])row_word_act_local[k][g]<=0;
        else row_word_act_local[k][g]<=slot_next&&r_v&&r_op==ACT;
    end
    // Only validity/opcode flags reset. The row word is consumed only by ACT.
    always @(posedge clk)row_local[g][18:0]<=r_row;
    always @(posedge clk or negedge reset_regions[32+g])
      if(!reset_regions[32+g])row_local[g][21:19]<=0;
      else row_local[g][21:19]<={slot_next&&r_v&&r_op==ACT,
                                slot_next&&r_v&&r_op==PRE,
                                slot_next&&r_v&&r_op==REFPB};
  end
  wire row_fire = c_v;
  wire [WQW:0] q_n_next=q_n+((qpush&&!wr_ok)?(WQW+1)'(1):
                               ((!qpush&&wr_ok)?{(WQW+1){1'b1}}:(WQW+1)'(0)));
  (* keep="true",dont_touch="true" *) reg [WQW:0] q_n_local[0:3];
  for(genvar qg=0;qg<4;qg=qg+1)begin:QUEUE_COUNT_LOCAL
    always @(posedge clk or negedge rst_n)
      if(!rst_n)q_n_local[qg]<=0;else q_n_local[qg]<=q_n_next;
  end
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
  reg ac2_v;reg[4:0]ac2_b;wire[RW_ROW-1:0]ac2_row=ac2_row_local[0];
  (* keep="true",dont_touch="true" *) reg [31:0] ac2_oh;
  (* keep="true",dont_touch="true" *) reg [RW_ROW-1:0] ac2_row_local[0:1];
  (* keep="true",dont_touch="true" *) reg [3:0] ac_v_local[0:4];
  wire [31:0] act_row_match;
  for(genvar b=0;b<32;b=b+1)begin:ACT_MATCH
    assign act_row_match[b]=look_row[b]==ac2_row_local[b/8];
  end
  always @* begin
    held=0;need=0;
    for(integer b=0;b<32;b=b+1)begin
      need[b]=bank_n[b]!=0;
      held[b]=bank_n[b]!=0&&open[b]&&look_row[b]==orow[b];
    end
    act_b=ac2_b;act_row=ac2_row;act_cand_oh=ac2_oh;
    act_cand=ac2_v&&|(ac2_oh&need&~open&~blk&act_row_match);
  end
  always @(posedge clk or negedge reset_regions[63])begin
    if(!reset_regions[63])begin ac_v<=0;ac2_v<=0;ac2_b<=0;ac2_oh<=0;
      for(integer k=0;k<2;k=k+1)ac2_row_local[k]<=0;
      for(integer k=0;k<5;k=k+1)ac_v_local[k]<=0;
      for(integer g=0;g<4;g=g+1)begin ac_b[g]<=0;ac_row[g]<=0;end
    end else begin
      for(integer g=0;g<4;g=g+1)begin:SG
        reg found;found=0;ac_v[g]<=0;
        for(integer k=0;k<5;k=k+1)ac_v_local[k][g]<=0;
        for(integer j=0;j<8;j=j+1)if(!found&&bank_n[g*8+j]!=0&&!open[g*8+j]&&!blk[g*8+j])begin
          found=1;ac_v[g]<=1;
          for(integer k=0;k<5;k=k+1)ac_v_local[k][g]<=1;ac_b[g]<=5'(g*8+j);ac_row[g]<=look_row[g*8+j];
        end
      end
          for(integer k=0;k<2;k=k+1)begin
            for(integer b=0;b<RW_ROW;b=b+1)
              begin:SROW
                reg found_row;
                found_row=0;ac2_row_local[k][b]<=ac2_row_local[0][b];
                for(integer j=0;j<4;j=j+1)if(!found_row&&ac_v_local[b/8][j])begin
                  found_row=1;ac2_row_local[k][b]<=ac_row[j][b];
                end
              end
          end
      // Independent existing-edge one-hot captures use retained local valid
      // state, avoiding one winner enable driving 32 one-hot plus row flops.
      for(integer b=0;b<32;b=b+1)begin:ACT_ONEHOT_LOCAL
        reg found;found=0;ac2_oh[b]<=0;
        for(integer g=0;g<4;g=g+1)if(!found&&ac_v_local[3+b/16][g])begin
          found=1;
`ifdef BW_AQ_MUT_ACT
          ac2_oh[b]<=((ac_b[g]^5'd1)==5'(b));
`else
          ac2_oh[b]<=(ac_b[g]==5'(b));
`endif
        end
      end
      begin:S2 reg found;found=0;ac2_v<=0;
        for(integer g=0;g<4;g=g+1)if(!found&&ac_v[g])begin found=1;ac2_v<=1;ac2_b<=ac_b[g];
        end
      end
    end
  end
  assign dbg_held = held;
  // ---- per-bank timing ------------------------------------------------------------------
  wire [31:0] rcd_z, rcdw_z, ras_z, rtp_z, aok_z, aok_busy;
  wire hit_rd = col_v && !col_we, hit_wr = col_v && col_we;
  for (genvar b = 0; b < 32; b = b + 1) begin : bank
    reg [4:0] rcd, ras, wrr; reg [8:0] aok; reg [2:0] rtp;
    wire act_e = row_local[b/8][21] && c_oh[b];
    wire pre_e = row_local[b/8][20] && c_oh[b];
    wire rfp_e = row_local[b/8][19] && c_oh[b];
    wire rd_e = bank_col[b] && head_local[b/4][0];
    wire wr_e = bank_col[b] && !head_local[b/4][0];
    always @(posedge clk or negedge reset_regions[b])
      if (!reset_regions[b]) begin rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; wrr <= 0; end
      else begin
        // Saturation belongs in the arithmetic datapath. Each command
        // selects one reload value, without a separate wide DFFE enable.
        wrr <= wr_e ? 5'(T_WRR-1) : wrr-5'(wrr!=0);
        rcd <= act_e ? 5'(T_RCD-1) : rcd-5'(rcd!=0);
        ras <= act_e ? 5'(T_RAS-1) : ras-5'(ras!=0);
        rtp <= rd_e ? 3'(T_RTP-1) : rtp-3'(rtp!=0);
        aok <= act_e ? 9'(T_RAS+T_RP-1) :
               rfp_e ? 9'(T_RFCPB-1) :
               ((pre_e&&aok<9'(T_RP)) ? 9'(T_RP-1) : aok-9'(aok!=0));
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
    // Share the ACT summary's same-edge region rather than the main AQ
    // reset; mapped main-region load then stays below256 after address copies.
    always @(posedge clk or negedge reset_regions[63])
      if (!reset_regions[63]) begin rrdl <= 0; ccdl <= 0; end
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
    s = 3'(kb >> 2); d = s - tail_set_regions[kb/4]; prot = (d >= 3'd6) || (d <= 3'd3);
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
      always @(posedge clk or negedge reset_regions[32+(32-(32>>l))+k])if(!reset_regions[32+(32-(32>>l))+k])begin key_q<=127;sel_q<=0;end
      else if(rk[l][2*k]<=rk[l][2*k+1])begin key_q<=rk[l][2*k];sel_q<=rs[l][2*k];end
      else begin key_q<=rk[l][2*k+1];sel_q<=rs[l][2*k+1];end
      assign rk[l+1][k]=key_q;assign rs[l+1][k]=sel_q;
    end
  end
  assign bkey=rk[5][0];assign bsel=rs[5][0];
  // Separate retained final selector captures for each live 32-bank lookup.
  (* keep="true",dont_touch="true" *) reg [4:0] refresh_sel_local[0:15];
  for(genvar k=0;k<16;k=k+1)begin:REFRESH_LOCAL
    always @(posedge clk or negedge reset_regions[62])
      if(!reset_regions[62])refresh_sel_local[k]<=0;
      else refresh_sel_local[k]<=(rk[4][0]<=rk[4][1]?rs[4][0]:rs[4][1])
`ifdef BW_AQ_MUT_REFRESH
        ^(k==0?5'd1:5'd0)
`endif
        ;
  end
  // ---- column: the head entry, strictly in order --------------------------------------------------------------------
  wire [31:0] pre_fl;
  for(genvar b=0;b<32;b=b+1)begin:OPEN_LOCAL
    assign pre_fl[b]=row_local[b/8][20]&&c_oh[b];
    always @(posedge clk or negedge reset_regions[b])
      if(!reset_regions[b])open[b]<=0;
      else if(row_local[b/8][21]&&c_oh[b])open[b]<=1;
      else if(row_local[b/8][20]&&c_oh[b])open[b]<=0;
  end
  // Compare rows locally in parallel instead of selecting a 19-bit word
  // through a 32:1 mux before comparing it. Each head-row bit has 32 loads.
  wire [31:0] head_row_match;
  for(genvar b=0;b<32;b=b+1)begin:HEAD_ROW
    assign head_row_match[b]=(orow[b]==head_local[b/4][19:1]);
  end
  wire [31:0] head_timer_ready;
  for(genvar b=0;b<32;b=b+1)begin:HEAD_TIMER
    assign head_timer_ready[b]=head_local[b/4][0]?rcd_z[b]:rcdw_z[b];
    // The one-hot bank owns its eligibility; the global column result no
    // longer broadcasts into all32 local timer/count update cones.
    assign bank_col[b]=(q_n_local[b/8]!=0)&&hb_oh[b]&&open[b]&&head_timer_ready[b]&&
      !blk[b]&&!pre_fl[b]&&head_row_match[b]&&ccdl_z[b%4]&&
      (head_local[b/4][0]?(wtr_c==0):(rtw_c==0));
  end
  wire head_bank_rdy = q_ne && |(hb_oh & open & head_timer_ready & ~blk & ~pre_fl & head_row_match);
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
`ifdef BW_MUT_REF_STALE
  wire ref_choice_fresh=1'b1;
  wire ref_choice_protected=1'b0;
`else
  // Tournament keys are pipelined. A completed early REF updates the live
  // bank state several edges before its key emerges. Never reserve that stale
  // candidate again: use its already-earned refresh credit for this slot.
  // Current bank state must be fresh. A stronger live cyclic-distance guard
  // was measured separately: it did not fix the full L02 static miss and
  // starved the legal mixed transaction trace. Keep the proven state check.
  wire[3:0] refresh_live_lookup;
  for(genvar f=0;f<4;f=f+1)begin:REFRESH_FIELD
    wire[3:0] selected;
    wire[31:0] states=(f==0)?refreshed:(f==1)?need:(f==2)?open:aok_busy;
    for(genvar g=0;g<4;g=g+1)begin:GROUP
      wire[4:0]sel=refresh_sel_local[f*4+g];
      wire[7:0]local_states=states[g*8+:8];
      assign selected[g]=(sel[4:3]==2'(g))&&local_states[sel[2:0]];
    end
    assign refresh_live_lookup[f]=|selected;
  end
  wire ref_choice_fresh=!(|refresh_live_lookup);
  wire ref_choice_protected=|refresh_live_lookup;
`endif
  wire ep_start = ref_choice_fresh && (PULLIN > 0) && !ep && !ref_pend && 32'(pin) < PULLIN && ref_c > RW'(LEAD + 12) && bkey < 7'd16 &&
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
      q_n <= 0; q_rp <= 0;q_rp_plus1<=1;q_rp_plus2<=2;
      refreshed <= 0; blk_valid <= 0;blk_bank<=0; rrds_c <= 0; noact_c <= 0; ref_pend <= 0; rb <= 0; fault_r <= 0;
      rtw_c <= 0; wtr_c <= 0; phase <= 0; rkey <= 127; pin <= 0; ep <= 0; skip <= 0; sact <= 0; c_v <= 0; c_op <= PRE; c_bank <= 0; command_bank_local<=0;command_bank_valid<=0; c_row <= 0;
      for (integer f = 0; f < 4; f = f + 1) fawq[f] <= 0;

    end else begin
      // queue
      case({qpush,wr_ok})
        2'b10:q_n<=q_n+1'b1;2'b01:q_n<=q_n-1'b1;default:q_n<=q_n;
      endcase
      if (wr_ok) begin q_rp<=q_rp_plus1;q_rp_plus1<=q_rp_plus1+1'b1;q_rp_plus2<=q_rp_plus2+1'b1;end
      if (col_aq) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
      if (col_we) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;
      if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
      if (noact_c != 0) noact_c <= noact_c - 1'b1;
      for (integer f = 0; f < 4; f = f + 1) if (fawq[f] != 0) fawq[f] <= fawq[f] - 1'b1;
      phase <= ~phase;
      c_v <= slot_next && r_v; c_op <= r_op; c_bank <= r_bank; command_bank_local<=r_bank;command_bank_valid<=slot_next&&r_v; c_row <= r_row;
      if (row_fire && (c_op == ACT || c_op == REFPB)) sact <= 0; else if (sact != 4'hf) sact <= sact + 1'b1;
      if (ref_c == RW'(LEAD)) begin
        if (ep) begin ref_pend <= 1; ep <= 0; end                               // a pending pull-in becomes this slot
        else if (pin != 0 && (bkey >= 7'd32 || ref_choice_protected)) begin pin <= pin - 1'b1; skip <= 1; end   // paid ahead: skip
        else begin ref_pend <= 1; rb <= bsel; blk_bank<=bsel;blk_valid<=1'b1; rkey <= bkey; end
      end else if (ep_start) begin ep <= 1; rb <= bsel; blk_bank<=bsel;blk_valid<=1'b1; rkey <= bkey; end
      else if (ep && |(blk & open)) begin ep <= 0; blk_valid<=0; end
      if (ref_due) skip <= 0;
      if (ref_due && !skip && (!row_fire || c_op != REFPB || |(blk & open) || |(blk & ~aok_z))) fault_r <= 1;
      if (row_fire) case (c_op)
        ACT: begin
          rrds_c <= 2'(T_RRDS - 1);
          begin : fawt
            reg tk; tk = 0;
            for (integer f = 0; f < 4; f = f + 1) if (!tk && fawq[f] == 0) begin fawq[f] <= 4'(T_FAW - 1); tk = 1; end
          end
        end
        PRE: begin end
        REFPB: begin
          noact_c <= 4'(T_RREFD - 1); ref_pend <= 0; blk_valid<=0;
          if (ep && !ref_pend) begin ep <= 0; pin <= pin + 1'b1; end
          refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
        end
        default: ;
      endcase
    end
  end
endmodule

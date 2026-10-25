`timescale 1ps/1fs
// Native static K/V controller timing core. Derived from source-exact physical
// JEDEC scheduler ot_hbm_r14_stream_pc_srow, retaining its timing/refresh rules.
// No read-credit input, credit counter, consumer-ready or backpressure state.
// Production RD events issue only at the compiler's reserved_rd cycles; a slot
// without JEDEC permission faults and never reschedules that operation.
// PROFILE1 discovers maximum legal slots; PROFILE2 samples a paced request
// calendar. Both are compiler/bench vehicles, never production modes.
// Descriptor range [desc_first,desc_n) permits K 0..255 and V 512..767 without
// reading unused head g=1. Normal acquisition is read-only: SROW/WR_EN/AQ_RD=0.
module ot_qkd_static_kv_timing #(
  parameter integer CORE_CLOCK = 0, // optin: timing in exactly833ps controller edges
  parameter integer SROW = 0,                 // static-row queue (emb-hbm); 0 = ot_hbm_r14_stream_pc_ready exactly
  parameter integer SQD = 4,                  // static queue entries (power of two)
  parameter integer S_STARVE = 8,             // cycles a static head waits before it takes priority
  parameter integer TWIN = 0,                 // twin-copy switch (refresh / conflict avoidance)
  parameter integer TWIN_ROFF = 0,            // twin row offset (two's complement, 19 b)
  parameter integer READY_CUT = 0,
  parameter integer ENABLE   = 0,
  parameter integer REF_MODE = 1,
  parameter integer PC       = 0,
  parameter integer T_RCD = CORE_CLOCK ? ((19*1024+832)/833) : 19, T_RP = CORE_CLOCK ? ((16*1024+832)/833) : 16, T_RAS = CORE_CLOCK ? ((28*1024+832)/833) : 28, T_RTP = CORE_CLOCK ? ((6*1024+832)/833) : 6, T_CCDL = CORE_CLOCK ? ((3*1024+832)/833) : 3,
  parameter integer T_RRDS = CORE_CLOCK ? ((3*1024+832)/833) : 3, T_RRDL = CORE_CLOCK ? ((4*1024+832)/833) : 4, T_FAW = CORE_CLOCK ? ((15*1024+832)/833) : 15, T_RFC = CORE_CLOCK ? ((342*1024+832)/833) : 342, T_RFCPB = CORE_CLOCK ? ((196*1024+832)/833) : 196,
  // Refresh deadlines round DOWN to an even number: each PC owns alternate row slots.
  parameter integer T_REFI = CORE_CLOCK ? (2*((3808*1024)/(2*833))) : 3808, T_REFIPB = CORE_CLOCK ? (2*((118*1024)/(2*833))) : 118, T_RREFD = CORE_CLOCK ? ((8*1024+832)/833) : 8,
  parameter integer PROFILE = 0, // 0 strict production,1 maximum-legal compiler,2 paced compiler
  parameter integer REF_PHASE = 0,
  parameter integer IDLE0 = 3, IDLE1 = 4, IDLE2 = 2, IDLE3 = 5,
  parameter integer IDLE4 = 1, IDLE5 = 6, IDLE6 = 0, IDLE7 = 7,
  parameter integer WR_EN = 0, WQ = 4, T_RTW = CORE_CLOCK ? ((10*1024+832)/833) : 10, T_WTR = CORE_CLOCK ? ((14*1024+832)/833) : 14, T_WRR = CORE_CLOCK ? ((28*1024+832)/833) : 28, T_RCDW = CORE_CLOCK ? ((10*1024+832)/833) : 10,
  parameter integer PULLIN = 0,
  parameter integer AQ_RD = 0,
  parameter integer AQ_STARVE = 64,
  parameter integer CONTEXT_DESC = 0,
  parameter integer STATIC_REFRESH = 0 // new descriptor ABI, legacy default unchanged
)(
  input  wire        clk, rst_n,
  input  wire        desc_v, output wire desc_r,
  input  wire [18:0] desc_row, input wire [10:0] desc_n,
  input  wire        go, input wire next_posted,
  output wire        row_v, output wire row_prio, input wire row_gnt,
  output wire [2:0]  row_op, output wire [4:0] row_bank, output wire [18:0] row_row,
  output wire        col_v, output wire [4:0] col_bank, output wire [4:0] col_col,
  input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
  // KV-TOK B 2026-10-24: controller boot window (maintenance mode before the calendar first owns the PC; driven by the
  // parent's boot-window state, never by a reservation): the static queue head's column issues when JEDEC-legal with no
  // reserved_static_col.  0 = original (every static column needs its reservation).
  input wire boot_static_col,
  input wire [9:0] desc_first,
  input wire desc_context,desc_vpass,desc_k_order_b,input wire [7:0] desc_k_count0,
  output wire schedule_fault,
  output wire phase_idle,
  output wire        busy, output wire ref_fault,
  // WR_EN: write queue (push wr_v && wr_r) and the WR flag of the column command
  input  wire        wr_v, input wire [4:0] wr_bank, input wire [4:0] wr_col,
  output wire        wr_r, output wire col_we,
  // AQ_RD: the pushed entry is a tagged read; the column command is a queued read
  input  wire        wr_rd, output wire col_aq,
  // SROW: static-row queue (push s_v && s_r) and the static flag of the column command
  input wire [346:0] s_context,output wire [346:0] col_context,
  input  wire        s_v, input wire s_we, input wire [4:0] s_bank, input wire [4:0] s_col, input wire [18:0] s_row,
  output wire        s_r, output wire col_sr, output wire s_pop
);
`ifdef SYNTHESIS
  initial if(PROFILE!=0)$error("Compiler profile cannot be a native physical master");
`endif
  // Keep legacy widths exactly; grow counters when the physical timing needs
  // more833ps cycles (RAS/WRR35, FAW19, WTR18 otherwise truncate).
  localparam integer RAS_W = ($clog2(T_RAS)>5) ? $clog2(T_RAS) : 5;
  localparam integer WRR_W = ($clog2(T_WRR)>5) ? $clog2(T_WRR) : 5;
  localparam integer FAW_W = ($clog2(T_FAW)>4) ? $clog2(T_FAW) : 4;
  localparam integer WTR_W = ($clog2(T_WTR)>4) ? $clog2(T_WTR) : 4;
  localparam [2:0] PRE=0, ACT=1, RD=2, REFAB=4, PREALL=5, REFPB=6;
  generate if (!ENABLE) begin : off
    assign desc_r=0; assign row_v=0; assign row_prio=0; assign row_op=0; assign row_bank=0;
    assign row_row=0; assign col_v=0; assign col_bank=0; assign col_col=0; assign busy=0;
    assign ref_fault=0; assign schedule_fault=0; assign phase_idle=1; assign wr_r=0; assign col_we=0; assign col_aq=0;
    assign s_r=0; assign col_sr=0; assign s_pop=0;assign col_context=0;
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
    reg v_consumer_order;
    reg context_active,context_v,context_kb;reg [7:0] context_k0;
    reg [8:0] ordinal,context_count;
    function automatic [10:0] context_sector(input [8:0] o,input vp,kb,input [7:0] k0);
      context_sector=!vp&&kb?(o<k0?{3'b0,o[7:0]}:{3'b0,1'b1,7'(o-k0)}):{1'b0,vp,1'b0,o[3],o[7:4],o[2:0]};
    endfunction
    wire context_accept=CONTEXT_DESC!=0 && desc_context;
    wire [10:0] first_sector=context_accept?context_sector(9'd0,desc_vpass,desc_k_order_b,desc_k_count0):{1'b0,desc_first};
    reg [31:0] open, done, stale, refreshed;
    reg [1:0] rrds_c; reg [3:0] noact_c; reg [RW-1:0] ref_c; reg ref_pend; reg [4:0] rb; reg fault_r;
    reg running; reg [31:0] blk;   // blk: one-hot of rb while a REFpb is pending
    reg streaming; reg [2:0] last; reg [10:0] nm1;   // registered at descriptor accept
    wire [2:0] k = j[9:7];
    wire [4:0] rd_bank = {j[9:7], j[1:0]};
    wire [1:0] rd_bg = j[1:0];
    // r8: the RD bank as a registered one-hot (rd_oh, rd_bgoh) and credit != 0 as a registered
    // flag, updated exactly with j / credit, so rd_ok is an AND-OR of flops (no j-decoded mux).
    reg [31:0] rd_oh; reg [3:0] rd_bgoh;
    // Native full-context V alternates eight-sector chunks across the two
    // V bank sets. Match actual n-major V consumption so a 128-row ring can
    // be admitted with compiled pacing; physical-linear V acquisition cannot.
    wire [7:0] v_ordinal={j[6:3],j[7],j[2:0]};
    wire [7:0] v_next=v_ordinal+8'd1;
    wire [10:0] j_p1 = context_active ? context_sector(ordinal+9'd1,context_v,context_kb,context_k0) : v_consumer_order ? {3'b010,v_next[3],v_next[7:4],v_next[2:0]} : j+11'd1;
    // ---- write queue (WR_EN) ------------------------------------------------------------
    reg [4:0] wq_bank [0:WQ-1]; reg [4:0] wq_col [0:WQ-1]; reg wq_rd [0:WQ-1];
    localparam AQ = (WR_EN != 0) && (AQ_RD != 0);
    reg hr;                                           // AQ_RD: the head entry is a read (registered)
    reg [WQW:0] wq_n; reg [WQW-1:0] wq_rp;
    // KVCTRL core_s4 (2026-10-16): the next-head select is restructured, cycle-identical: each entry keeps its bank
    // ONE-HOT from push time and wq_rp1 = wq_rp + 1 is a register, so both head candidates are read in parallel and
    // the late wr_ok picks between them last (was: wr_ok -> wq_rp + 1 -> 4:1 read -> 5:32 decode, 18 levels).
    reg [31:0] wq_oh [0:WQ-1]; reg [WQW-1:0] wq_rp1;
    reg [3:0] rtw_c; reg [WTR_W-1:0] wtr_c;
    reg [31:0] wopen;                                 // banks opened by a write ACT (precharged after)
    reg c_w;                                          // the registered row command is a write ACT
    wire wq_ne = W && wq_n != 0;
    // the head write's bank/column are REGISTERED copies (hb_oh one-hot), kept off the queue index
    reg [4:0] hb, hc; reg [31:0] hb_oh;
    wire [5*WQ-1:0] wq_bq;                            // queued write banks, oldest first
    wire [WQ-1:0] wq_in;                              // queue entry valid
    for (genvar i = 0; i < WQ; i = i + 1) begin : wqe
      assign wq_bq[i*5 +: 5] = wq_bank[WQW'(wq_rp + i)];
      assign wq_in[i] = W && i < wq_n;
    end
    reg [31:0] hold_n, hold;                          // banks a queued write needs (never precharged;
    integer hi;                                       // registered: one cycle behind the queue)
    // KVCTRL core_s4: the same set (every queued entry's bank) from per-SLOT valid bits and the stored one-hots, with no
    // wq_rp-relative index / decode (core_s1 routed TT: wq_rp -> wq_bq -> hold_n -> s_pre_ok -> s_pblk -> rd_ok -> rd_oh
    // -20.54 ps, 24 levels; SS -525.84). Membership is order-free, so the OR is identical.
    reg [WQ-1:0] wq_v;                                // physical slot holds a queued entry
    always @* begin
      hold_n = 0;
      for (hi = 0; hi < WQ; hi = hi + 1) if (W && wq_v[hi]) hold_n = hold_n | wq_oh[hi];
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) hold <= 0; else hold <= hold_n;
    wire wr_ok, wr_ok0, rd_ok0;
    // ---- static-row queue (SROW) -------------------------------------------------------------
    localparam S = (SROW != 0);
    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;
    reg [4:0] sq_bank [0:SQD-1]; reg [4:0] sq_col [0:SQD-1]; reg [18:0] sq_row [0:SQD-1]; reg sq_we [0:SQD-1];
    reg [SQW:0] sq_n; reg [SQW-1:0] sq_rp;
    reg [346:0] sq_context[0:SQD-1];reg [346:0] shead_context;
    assign col_context=shead_context;
    wire sq_ne = S && sq_n != 0;
    // the head, REGISTERED (sb_oh one-hot): bank, column, row, direction; scm: committed (its ACT issued or it hit);
    // sfl: switched to the twin once.  so_*: the newest static-opened bank and its row (cleared by its PRE).
    reg [4:0] sb, sc; reg [18:0] srw; reg swe, sfl, scm; reg [31:0] sb_oh;
    reg so_v; reg [4:0] so_b; reg [18:0] so_row;
    reg [7:0] swait;
    reg c_s, c_sp; reg [18:0] c_srow;                 // the registered row command is a static ACT / static PRE
    wire sprio = sq_ne && swait >= 8'(S_STARVE);
    wire s_hit = sq_ne && so_v && so_b == sb && so_row == srw && |(sb_oh & open);
    wire [31:0] shold = s_hit ? sb_oh : 32'b0;        // never precharge the bank the head is about to access
    wire s_go;                                        // the static head's column command issues this cycle
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

    // ---- per-bank timing state (down-counters; 0 = allowed) ------------------------------
    wire [31:0] rcd_z, ras_z, rtp_z, aok_z, aok_busy, rcdw_z;
    wire [223:0] keys;
    reg [4:0] bsel;reg [4:0] refresh_rr;
    initial if(STATIC_REFRESH!=0 && (PULLIN!=0 || REF_MODE!=1))$fatal(1,"static RR refresh requires REFpb/no pullin");
    always @(posedge clk or negedge rst_n)if(!rst_n)refresh_rr<=0;else if(row_fire&&c_op==REFPB)refresh_rr<=refresh_rr+5'd1;
    // Exact next-state eligibility; no extra decision cycle. The cut is
    // specialised to strict refresh and the write-only queue used by Qwen.
    localparam READY_ACTIVE = READY_CUT && PULLIN == 0 && AQ_RD == 0;
    reg [31:0] write_ready_bank;
    wire [31:0] ready_stale_next = desc_acc ? open_nx :
      (row_fire && c_op == PREALL) ? 32'b0 :
      (row_fire && c_op == PRE) ? stale & ~c_oh :
      (row_fire && c_op == ACT && S && c_s) ? stale | c_oh : stale;
    wire [31:0] ready_blk_next = (row_fire && c_op == REFPB) ? 32'b0 :
      (REF_MODE && ref_c == RW'(LEAD)) ? (32'b1 << bsel) : blk;
    for (genvar b = 0; b < 32; b = b + 1) begin : bank
      reg [4:0] rcd; reg [RAS_W-1:0] ras; reg [8:0] aok; reg [2:0] rtp; reg aok_zr, rcd_zr;   // == 0 flags, registered
      reg [WRR_W-1:0] wrr;
      wire wr_e = (W && wr_ok && hb_oh[b] && !(AQ && hr)) || (s_go && swe && sb_oh[b]);
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = (rd_ok && rd_oh[b]) || (AQ && wr_ok && hr && hb_oh[b]) || (s_go && !swe && sb_oh[b]);
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rcd <= 0; ras <= 0; aok <= 0; rtp <= 0; aok_zr <= 1'b1; rcd_zr <= 1'b1; wrr <= 0; end
        else begin
          rcd_zr <= act_e ? (T_RCD - 1 == 0) : (rcd <= 5'd1);
          if (wr_e) wrr <= WRR_W'(T_WRR - 1); else if (wrr != 0) wrr <= wrr - 1'b1;
          if (act_e) begin rcd <= 5'(T_RCD - 1); ras <= RAS_W'(T_RAS - 1); end
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
      if (READY_ACTIVE) begin : ready_cut
        // Saturating rcd decrement: (next rcd <= threshold) is
        // exactly (current rcd <= threshold+1), unless ACT reloads it.
        wire rcdw_next = act_e ? (T_RCD-1 <= T_RCD-T_RCDW) :
          (rcd <= T_RCD-T_RCDW+1);
        always @(posedge clk or negedge rst_n)
          if (!rst_n) write_ready_bank[b] <= 1'b0;
          else write_ready_bank[b] <= open_nx[b] && !ready_stale_next[b] &&
            !ready_blk_next[b] && rcdw_next;
      end
      assign rcd_z[b] = rcd_zr; assign rcdw_z[b] = (rcd <= 5'(T_RCD - T_RCDW)); assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0) && (!W || wrr == 0);
      assign aok_z[b] = aok_zr; assign aok_busy[b] = (aok > 9'(LEAD));
      // REFpb key: 127 refreshed; streaming/posted: open 24 (finished) / 32, protected (needed
      // within the next two sets) 16..18 farthest first, upcoming = distance, passed 8 + set;
      // idle: IDLE rank (+32 open); +64 if still busy from an earlier tRFCpb / tRC.
      localparam [2:0] S = 3'(b >> 2);
      wire [2:0] d = context_active ? (S==k?3'd0:3'd1) : S-k;
      wire ahead = (context_active ? (context_v ? (S==4 || S==5) : (S==0 || S==1)) : (S >= k && S <= last)) || next_posted;
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
      reg [2:0] rrdl; reg [1:0] ccdl; reg [FAW_W-1:0] faw; reg rrdl_zr, faw_zr, ccdl_zr;   // registered (== 0) flags
      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire ccdl_e = (rd_ok && rd_bgoh[g]) || (W && wr_ok && hb[1:0] == 2'(g)) || (s_go && sb[1:0] == 2'(g));
      wire faw_take = row_fire && c_op == ACT && faw == 0 && (g == 0 || !(|faw_z[g == 0 ? 0 : g-1:0]));
      always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rrdl <= 0; ccdl <= 0; faw <= 0; rrdl_zr <= 1'b1; faw_zr <= 1'b1; ccdl_zr <= 1'b1; end
        else begin
          if (act_g) rrdl <= 3'(T_RRDL - 1); else if (rrdl != 0) rrdl <= rrdl - 1'b1;
          if (ccdl_e) ccdl <= 2'(T_CCDL - 1); else if (ccdl != 0) ccdl <= ccdl - 1'b1;
          if (faw_take) faw <= FAW_W'(T_FAW - 1); else if (faw != 0) faw <= faw - 1'b1;
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
    reg [6:0] s1k [0:7]; reg [4:0] s1i [0:7]; reg [6:0] s2k [0:1]; reg [4:0] s2i [0:1];
    reg [6:0] bkey;                                   // PULLIN: the key of bsel
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
        bsel <= 0; keys_r <= {32{7'd127}}; bkey <= 7'd127;
      end else begin
        keys_r <= keys;
        for (integer q = 0; q < 8; q = q + 1) begin
          s1k[q] <= m1[q*9 + 2 +: 7]; s1i[q] <= {3'(q), m1[q*9 +: 2]};
        end
        for (integer q = 0; q < 2; q = q + 1) begin
          s2k[q] <= m2[q*9 + 2 +: 7]; s2i[q] <= s1i[4*q + m2[q*9 +: 2]];
        end
        bsel <= STATIC_REFRESH!=0?refresh_rr:((s2k[1] < s2k[0]) ? s2i[1] : s2i[0]);
        bkey <= (s2k[1] < s2k[0]) ? s2k[1] : s2k[0];
      end
    // ---- column: one RD per cycle ------------------------------------------------------
    // the head write is issuable but for tRTW / tCCD_L: RDs stop so it can go
    reg [7:0] hwait;                                  // AQ_RD: cycles the read head has waited
    wire starve = AQ && hr && hwait >= 8'(AQ_STARVE);
    wire head_prio = !(AQ && hr) || starve;
    wire wr_bank_rdy = wq_ne && (READY_ACTIVE ? |(hb_oh & write_ready_bank) : |(hb_oh & open & ~stale & (AQ ? rcd_z : rcdw_z) & ~blk));   // AQ: every access-queue head waits full tRCD (no hr on this path)
    wire rd_ok_base = running && streaming && !rd_block && |(rd_oh & open & ~stale & rcd_z & ~blk) &&
                      |(rd_bgoh & ccdl_z);
    assign wr_ok0 = wr_bank_rdy && ccdl_z[hb[1:0]] && ((AQ && hr) ? (wtr_c == 0) : (rtw_c == 0)) && !rd_block &&
                   (head_prio || !rd_ok_base);
    assign rd_ok0 = rd_ok_base && !(W && ((wr_bank_rdy && head_prio) || wtr_c != 0));
    // static column command: the head hit (its bank open on its row), tRCD (write: tRCDW), tCCD_L, tWTR (read) / tRTW
    // (write), the bank not chosen for refresh.  Background (a cycle neither the stream nor the KV queue uses) until it
    // starves.  s_pblk: the bank a static PRE was just decided for / is issuing takes no column command meanwhile.
    reg [31:0] s_pblk;
    wire s_col_ok = s_hit && ccdl_z[sb[1:0]] && !(|(sb_oh & blk)) && !rd_block &&
                    (swe ? (W && |(sb_oh & rcdw_z) && rtw_c == 0) : (|(sb_oh & rcd_z) && wtr_c == 0));
    wire legal_static = s_col_ok && (sprio || (!rd_ok_base && !(W && wr_ok0)));
    assign s_go = legal_static && (PROFILE == 1 || reserved_static_col || boot_static_col);
    wire legal_rd = rd_ok0 && !s_go && !(|(rd_oh & s_pblk));
    assign rd_ok = legal_rd && (PROFILE == 1 || reserved_rd);
    reg fault_schedule;
    assign schedule_fault = fault_schedule;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) fault_schedule <= 0;
      else if (PROFILE == 0 && ((reserved_rd && !legal_rd) || (reserved_static_col && !legal_static) || (reserved_write_col && !legal_write) || (({1'b0,reserved_rd}+{1'b0,reserved_static_col}+{1'b0,reserved_write_col})>1))) fault_schedule <= 1;
    wire legal_write = wr_ok0 && !s_go && !(|(hb_oh & s_pblk));
    assign wr_ok = legal_write && (PROFILE == 1 || reserved_write_col);
    // ---- row: refresh > forced PRE > ACT ahead (sets k, k+1) > PRE finished -----------
    function automatic [4:0] act_bank(input integer c, input [2:0] kk);
      act_bank = {(c >= 4) ? (context_active ? (kk ^ 3'd1) : kk + 3'd1) : kk, 2'(c & 3)};
    endfunction
    // candidates (no dynamic indexing on the decision path): per-bank ACT eligibility, the 4-bank
    // groups of sets k and k+1, lowest-first one-hot selection; PRE of finished banks, lowest first
    wire [31:0] act_okb = ~open & ~done & ~blk & aok_z & {8{rrdl_z}};
    // r8: k as a registered one-hot (koh) and the k+1 validity as a registered flag (k1v), both
    // updated exactly with j/last, so the set selection is an AND-OR, not a k-decoded mux.
    reg [7:0] koh; reg k1v;
    wire [7:0] k1oh = context_active ? (context_v?(koh^8'h30):(koh^8'h03)) : {koh[6:0], 1'b0};                 // set k+1 (none when k == 7)
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
    always @* for (integer b = 0; b < 32; b = b + 1) sneed[b] = (AQ || context_active) && streaming && !done[b] && (context_active ? (context_v ? (3'(b>>2)==4 || 3'(b>>2)==5) : (3'(b>>2)==0 || 3'(b>>2)==1)) : (3'(b >> 2) >= k && 3'(b >> 2) <= last));
    wire [31:0] pre_cand = open & (done | stale | (W ? (wopen & ~sneed) : 32'b0)) & ~blk & ras_z & rtp_z & ~shold &
                           ~(W ? (hold | (AQ ? hold_n : 32'b0)) : 32'b0);
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
    wire v_set_flip=v_consumer_order && rd_ok && j[2:0]==3'd7;
    wire [2:0] k_n = desc_acc ? first_sector[9:7] : context_active&&rd_ok ? j_p1[9:7] : v_set_flip ? (k^3'd1) : k_step ? k+3'd1 : k;
    wire [2:0] last_n = desc_acc ? (context_accept ? (desc_vpass?3'd5:3'd1) : 3'((desc_n - 11'd1) >> 7)) : last;
    wire [7:0] koh_n = desc_acc ? (8'b1 << first_sector[9:7]) : context_active&&rd_ok ? (8'b1 << j_p1[9:7]) : v_set_flip ? {koh[6],koh[7],koh[4],koh[5],koh[2],koh[3],koh[0],koh[1]} : k_step ? {koh[6:0],koh[7]} : koh;
    // write ACT: closed target bank, not chosen (or about to be chosen) for refresh
    // any queued write's bank may open (oldest first), so a burst of writes opens its banks together
    wire [WQ-1:0] wq_act;
    for (genvar i = 0; i < WQ; i = i + 1) begin : wqa
      wire [4:0] bq = wq_bq[i*5 +: 5];
      assign wq_act[i] = wq_in[i] && !open[bq] && !blk[bq] && aok_z[bq] && rrdl_z[bq[1:0]] &&
                         !(REF_MODE && (ref_c == RW'(LEAD) || ref_c == RW'(LEAD + 1)) && bq == bsel);
    end
    // The candidate (oldest queued write whose bank can open) is REGISTERED and re-validated at use
    // against the current bank state with one-hot reductions, keeping the queue indexing and the
    // bank-state muxes off the row-decision path.
    reg wcand; reg [4:0] wab_n; reg wcrd_n;
    integer ai;
    always @* begin
      wcand = 1'b0; wab_n = 0; wcrd_n = 1'b0;
      for (ai = WQ - 1; ai >= 0; ai = ai - 1) if (wq_act[ai]) begin
        wcand = 1'b1; wab_n = wq_bq[ai*5 +: 5]; wcrd_n = AQ && wq_rd[WQW'(wq_rp + ai)];
      end
    end
    reg wcand_q; reg [4:0] wab; reg [31:0] wab_oh; reg wcrd_q;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin wcand_q <= 1'b0; wab <= 0; wab_oh <= 0; wcrd_q <= 1'b0; end
      else begin wcand_q <= W && wcand; wab <= wab_n; wab_oh <= 32'b1 << wab_n; wcrd_q <= wcrd_n; end
    wire wact_ok = wcand_q && !(|(wab_oh & (open | blk))) && (|(wab_oh & aok_z)) && rrdl_z[wab[1:0]] &&
                   !(REF_MODE && (ref_c == RW'(LEAD) || ref_c == RW'(LEAD + 1)) && wab == bsel) &&
                   !act_block && noact_c == 0 && rrds_c == 0 && faw_ok;
    // ---- PULLIN: refresh ahead of schedule while not reading ---------------------------------
    localparam integer PIW = $clog2(PULLIN + 2);
    localparam PI = (REF_MODE != 0) && (PULLIN > 0);
    reg [PIW-1:0] pin;                                // REFpb issued ahead of the schedule
    reg ep;                                           // a pulled-in REFpb is pending (rb / blk)
    reg skip;                                         // this due slot was paid ahead: nothing issues
    reg [3:0] sact;                                   // cycles since the last ACT / REFpb (saturating)
    wire pi_idle = !streaming || !running;
    wire ep_start = PI && pi_idle && !ep && !ref_pend && 32'(pin) < PULLIN && ref_c > RW'(LEAD + 8) &&
                    (bkey < 7'd16 || bkey == 7'd20) && !(|(blk)) && sact >= 4'd6;   // bsel/bkey see a REFpb / ACT 5 cycles late
    wire ep_rdy = PI && ep && !(|(blk & open)) && (|(blk & aok_z)) && noact_c == 0 && sact >= 4'(T_RREFD + 2) &&
                  ref_c > RW'(LEAD + 8);   // bsel at LEAD must not see a REFpb in flight
    reg [31:0] r_oh;
    reg r_w, r_s, r_sp;
    // ---- static row commands (SROW) -----------------------------------------------------------
    // the twin bank (other bank-group pair) as a one-hot permutation of the head's
    wire [31:0] ab_oh;
    for (genvar b = 0; b < 32; b = b + 1) begin : twin_oh
      assign ab_oh[b] = sb_oh[b ^ 2];
    end
    wire s_refsel = REF_MODE && (ref_c == RW'(LEAD) || ref_c == RW'(LEAD + 1));   // bsel is about to be taken
    wire s_unav = (|(sb_oh & ((aok_busy & ~open) | blk))) || (|(sb_oh & open) && !s_hit) || (s_refsel && sb == bsel);
    wire s_av_a = !(|(ab_oh & (open | blk | aok_busy))) && (|(ab_oh & aok_z)) && !(s_refsel && (sb ^ 5'd2) == bsel);
    wire s_sw = S && (TWIN != 0) && sq_ne && !swe && !sfl && !scm && !s_hit && s_unav && s_av_a;
    wire s_act_ok = sq_ne && !s_sw && !(|(sb_oh & (open | blk))) && (|(sb_oh & aok_z)) && rrdl_z[sb[1:0]] &&
                    !(s_refsel && sb == bsel) && !act_block && noact_c == 0 && rrds_c == 0 && faw_ok;
    wire s_pre_ok = sq_ne && !s_sw && !s_hit && (|(sb_oh & open & ras_z & rtp_z & ~blk & ~hold & ~hold_n));
    always @* begin
      r_v = 0; r_prio = 0; r_op = PRE; r_bank = 0; r_oh = 0; r_w = 0; r_s = 0; r_sp = 0;
      if (REF_MODE && ref_due_n && ref_pend) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (!REF_MODE && ref_due_n) begin r_v = 1; r_prio = 1; r_op = REFAB; end
      else if (preall_ok) begin r_v = 1; r_prio = 1; r_op = PREALL; end
      else if (ep_rdy) begin r_v = 1; r_prio = 1; r_op = REFPB; r_bank = rb; r_oh = blk; end
      else if (forced_pre) begin r_v = 1; r_prio = 1; r_op = PRE; r_bank = rb; r_oh = blk; end
      else if (S && sprio && s_pre_ok) begin r_v = 1; r_op = PRE; r_bank = sb; r_oh = sb_oh; r_sp = 1; end
      else if (S && sprio && s_act_ok) begin r_v = 1; r_op = ACT; r_bank = sb; r_oh = sb_oh; r_s = 1; end
      else if (W && wact_ok && !(AQ && wcrd_q && act_ok_any && !starve)) begin r_v = 1; r_op = ACT; r_bank = wab; r_oh = wab_oh; r_w = 1; end
      else if (act_ok_any) begin r_v = 1; r_op = ACT; r_bank = act_bank(act_sel, k); r_oh = act_oh; end
      else if (S && s_act_ok) begin r_v = 1; r_op = ACT; r_bank = sb; r_oh = sb_oh; r_s = 1; end
      else if (|pre_cand) begin r_v = 1; r_op = PRE; r_bank = pre_sel; r_oh = pre_oh; end
    end
    assign row_v = c_v; assign row_prio = c_prio; assign row_op = c_op; assign row_bank = c_bank;
    assign row_row = (S && c_s) ? c_srow : row;
    always @* s_pblk = ((S && slot_next && r_v && r_sp) ? r_oh : 32'b0) | ((S && c_v && c_sp) ? c_oh : 32'b0);
    assign col_v = rd_ok || (W && wr_ok) || s_go; assign col_we = (W && wr_ok && !(AQ && hr)) || (s_go && swe);
    assign col_aq = AQ && wr_ok && hr; assign col_sr = s_go;
    assign col_bank = s_go ? sb : (W && wr_ok) ? hb : rd_bank; assign col_col = s_go ? sc : (W && wr_ok) ? hc : j[6:2];
    assign s_r = S && sq_n != (SQW+1)'(SQD); assign s_pop = s_go;
    assign wr_r = W && wq_n != (WQW+1)'(WQ);
    assign desc_r = !streaming && !fault_r && !wq_ne;
    assign phase_idle = !streaming && !wq_ne && !sq_ne;
    assign busy = streaming; assign ref_fault = fault_r;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        streaming <= 0;v_consumer_order<=0;context_active<=0;context_v<=0;context_kb<=0;context_k0<=0;ordinal<=0;context_count<=0; last <= 0; nm1 <= 0;
        j <= 0; n <= 0; row <= 0; open <= 0; done <= 0; stale <= 0; refreshed <= 0;
        rrds_c <= 0; noact_c <= 0; ref_pend <= 0; blk <= 0; rb <= 0; fault_r <= 0;
        ref_c <= RW'(RPH + PERIOD); running <= 0; phase <= 0;
        c_v <= 0; c_prio <= 0; c_op <= PRE; c_bank <= 0; c_oh <= 0; c_s <= 0; c_sp <= 0; c_srow <= 0;
        sq_n <= 0; sq_rp <= 0; sb <= 0; sc <= 0; srw <= 0; swe <= 0; sb_oh <= 0; sfl <= 0; scm <= 0; swait <= 0;
        so_v <= 0; so_b <= 0; so_row <= 0;
        koh <= 8'b1; k1v <= 1'b0; rd_oh <= 32'b1; rd_bgoh <= 4'b1;
        wq_n <= 0; wq_rp <= 0; wq_rp1 <= WQW'(1); wq_v <= '0; rtw_c <= 0; wtr_c <= 0; wopen <= 0; c_w <= 0; hb <= 0; hc <= 0; hb_oh <= 0; hr <= 0;
        pin <= 0; ep <= 0; skip <= 0; sact <= 0; hwait <= 0;
      end else begin
        if (AQ) begin if (!wq_ne || !hr || wr_ok) hwait <= 0; else if (hwait != 8'hff) hwait <= hwait + 1'b1; end
        if (W) begin
          if (rd_ok || (AQ && wr_ok && hr) || (s_go && !swe)) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
          if ((wr_ok && !(AQ && hr)) || (s_go && swe)) wtr_c <= WTR_W'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;
          if (wr_v && wr_r) begin
            wq_bank[WQW'(wq_rp + wq_n)] <= wr_bank; wq_col[WQW'(wq_rp + wq_n)] <= wr_col;
            wq_oh[WQW'(wq_rp + wq_n)] <= 32'b1 << wr_bank;
            if (AQ) wq_rd[WQW'(wq_rp + wq_n)] <= wr_rd;
          end
          wq_n <= wq_n + (wr_v && wr_r ? 1'b1 : 1'b0) - (wr_ok ? 1'b1 : 1'b0);
          begin : slotv
            reg [WQ-1:0] v; v = wq_v;
            if (wr_ok) v[wq_rp] = 1'b0;
            if (wr_v && wr_r) v[WQW'(wq_rp + wq_n)] = 1'b1;
            wq_v <= v;
          end
          if (wr_ok) begin wq_rp <= wq_rp1; wq_rp1 <= WQW'(wq_rp1 + 1'b1); end
          // next head: the entry after the popped one if it exists, else the entry pushed now
          begin : headn
            // identical to: rpn = wr_ok ? wq_rp + 1 : wq_rp; head = (wq_n - wr_ok != 0) ? q[rpn] : the pushed entry
            reg [4:0] b0, c0, b1, c1; reg r0, r1, ne0, ne1; reg [31:0] o0, o1;
            b0 = wq_bank[wq_rp];  c0 = wq_col[wq_rp];  r0 = AQ && wq_rd[wq_rp];  o0 = wq_oh[wq_rp];
            b1 = wq_bank[wq_rp1]; c1 = wq_col[wq_rp1]; r1 = AQ && wq_rd[wq_rp1]; o1 = wq_oh[wq_rp1];
            ne0 = wq_n != 0; ne1 = wq_n != 1;
            if (wr_ok) begin
              if (ne1) begin hb <= b1; hc <= c1; hb_oh <= o1; hr <= r1; end
              else begin hb <= wr_bank; hc <= wr_col; hb_oh <= 32'b1 << wr_bank; hr <= AQ && wr_rd; end
            end else begin
              if (ne0) begin hb <= b0; hc <= c0; hb_oh <= o0; hr <= r0; end
              else begin hb <= wr_bank; hc <= wr_col; hb_oh <= 32'b1 << wr_bank; hr <= AQ && wr_rd; end
            end
          end
          // write-opened banks: set by a write ACT, cleared by PRE/PREALL or a stream RD (the stream owns it)
          wopen <= ((wopen | ((row_fire && c_op == ACT && c_w) ? c_oh : 32'b0))
                    & ~((row_fire && c_op == PRE) ? c_oh : 32'b0)
                    & ~(rd_ok ? rd_oh : 32'b0))
                   & {32{!(row_fire && c_op == PREALL)}};
        end
        if (desc_acc) begin rd_oh <= 32'b1 << {first_sector[9:7],first_sector[1:0]}; rd_bgoh <= 4'b1 << first_sector[1:0]; end
        else if (rd_ok) begin rd_oh <= 32'b1 << {j_p1[9:7], j_p1[1:0]}; rd_bgoh <= 4'b1 << j_p1[1:0]; end

        koh <= koh_n; k1v <= (desc_acc ? context_accept : context_active) || ((k_n != 3'd7) && (k_n + 3'd1 <= last_n));
        if (rrds_c != 0) rrds_c <= rrds_c - 1'b1;
        if (noact_c != 0) noact_c <= noact_c - 1'b1;

        // refresh schedule
        ref_c <= ref_n; phase <= ~phase;
        // register the row decision for this PC's next slot (an off-slot cycle issues nothing)
        c_v <= slot_next && r_v; c_prio <= r_prio; c_op <= r_op; c_bank <= r_bank; c_oh <= r_oh; c_w <= W && r_w;
        c_s <= S && slot_next && r_v && r_s; c_sp <= S && slot_next && r_v && r_sp; c_srow <= srw;
        // ---- static queue: push, pop, head (registered), twin switch, commit, wait counter, static-open bank
        if (S) begin : sq
          reg [SQW-1:0] rpn; reg chg;
          if (s_v && s_r) begin
            sq_bank[SQW'(sq_rp + sq_n)] <= s_bank; sq_col[SQW'(sq_rp + sq_n)] <= s_col;
            sq_row[SQW'(sq_rp + sq_n)] <= s_row; sq_we[SQW'(sq_rp + sq_n)] <= s_we;
            sq_context[SQW'(sq_rp + sq_n)]<=s_context;
          end
          sq_n <= sq_n + ((s_v && s_r) ? 1'b1 : 1'b0) - (s_go ? 1'b1 : 1'b0);
          if (s_go) sq_rp <= SQW'(sq_rp + 1'b1);
          rpn = s_go ? SQW'(sq_rp + 1'b1) : sq_rp;
          chg = s_go || sq_n == 0;
          if (chg) begin
            if (sq_n - (s_go ? 1'b1 : 1'b0) != 0) begin
              shead_context<=sq_context[rpn];
              sb <= sq_bank[rpn]; sc <= sq_col[rpn]; srw <= sq_row[rpn]; swe <= sq_we[rpn]; sb_oh <= 32'b1 << sq_bank[rpn];
            end else begin
              shead_context<=s_context;
              sb <= s_bank; sc <= s_col; srw <= s_row; swe <= s_we; sb_oh <= 32'b1 << s_bank;
            end
            sfl <= 1'b0; scm <= 1'b0;
          end else if (s_sw) begin
            sb <= sb ^ 5'd2; srw <= 19'(srw + 19'(TWIN_ROFF)); sb_oh <= ab_oh; sfl <= 1'b1;
          end else if (s_hit || (row_fire && c_op == ACT && c_s)) scm <= 1'b1;
          if (!sq_ne || chg || s_sw) swait <= 0; else if (swait != 8'hff) swait <= swait + 1'b1;
          if (row_fire && c_op == ACT && c_s) begin so_v <= 1'b1; so_b <= c_bank; so_row <= c_srow; end
          else if (row_fire && (c_op == PREALL || (c_op == PRE && c_bank == so_b))) so_v <= 1'b0;
        end
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
          if (context_active ? ordinal+9'd1==context_count : j==nm1) streaming<=0;
          if(context_active)ordinal<=ordinal+9'd1;
          if (!context_active && j[6:2] == 5'd31) done <= done | rd_oh;
          if(context_active && ordinal+9'd1==context_count)done<=done|32'hffffffff;
        end
        // row
        if (row_fire) case (c_op)
          ACT: begin open <= open | c_oh; rrds_c <= 2'(T_RRDS - 1); if (S && c_s) stale <= stale | c_oh; end
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
          j <= first_sector; n <= desc_n; row <= desc_row;
          context_active<=context_accept;context_v<=desc_vpass;context_kb<=desc_k_order_b;context_k0<=desc_k_count0;ordinal<=0;context_count<=desc_n[8:0];
          v_consumer_order <= !context_accept && desc_first==10'd512 && desc_n==11'd768; done <= 0; running <= 0;
          streaming <= (desc_n != 0); nm1 <= desc_n - 11'd1; last <= context_accept ? (desc_vpass?3'd5:3'd1) : 3'((desc_n - 11'd1) >> 7);
          stale <= open_nx;                     // rows still open from the old descriptor close first
        end
      end
    end
  end endgenerate
endmodule

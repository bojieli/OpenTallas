`timescale 1ps/1fs
// hbm-fully-measured (2026-10-04): successor COPY of rtl/test/hbm_accel/tb_hbm_accel_dskv_stream.sv (that file stays
// byte-identical) for the DS HBM accelerator's per-die critical-path loads at position 1,048,575, at main's corrected
// REFpb checker (54dcb2ab6: tRREFD after REFpb, REFpb bank once per round, tRFCpb).  Changes vs the original:
//   * +post_lead_ps (default 200 ns, the original POST_LEAD_PS): 0 = a token-dependent scan whose address is known
//     only at `go` (embedding row);
//   * MODE 1 (GATHER) takes any number of random-row sectors per PC (+nrows up to 56 rows a stack): each PC keeps a
//     queue of single-sector descriptors and posts the next one as soon as its sequencer is free (desc_r); every
//     sector carries a distinct pattern, checked in issue order;
//   * the BW line also prints the number of descriptors.
// Everything else (stream PC, landing crossing, DRAM checker, consumer) is the original.
// HBM path audit (2026-10-04): DS-V4.1 HBM-accelerator KV/index LOAD paths of ONE HBM3E stack at the 1M
// target context, on the measured streaming controller (ot_hbm_accel_expert_stream_pc with notice=0, which
// is byte-for-byte the 52ce3e9c1 r6 stream PC; nothing pinned changes).  Minimum component: one stack (32 PCs);
// the die's four stacks are identical and independent (keys / rows are sharded by position), so the die figure
// is four times this one.
// MODE 0 (SCAN): the index-key scan of one scanning layer.  Per die at position 1,048,575 (W19 TP-96 program
//   results/rtl/w19_hbm_tp96_program_oreduce.json, keys sharded by position over 96 dies, 68 B a key,
//   tools/arch_budget_v41.py IDX_KEY_B): L20/24/28/32/36 1,048,576/96 = 10,923 keys = 742,764 B = 185,691 B a
//   stack = 182 sectors a PC (NSECT 182); L2/8/14 524,288/96 keys -> 91 sectors a PC.  The key region is
//   known before the index query, so the descriptor is POSTED at t_post (rows open ahead) and RDs start at
//   `go` = the query time t_go.  Consumer: NK keys per 1.2 GHz cycle on this stack (NK = 0: unthrottled, one
//   sector a PC a cycle); NK*68 B of credit a clk.
// MODE 1 (GATHER): selected compressed-KV rows after the 96 x 512 merge: addresses are known only at t_go,
//   so the descriptors are posted AT t_go.  NROWS rows of 288 B (9 sectors, interleaved over 9 PCs, one
//   sector each, one random DRAM row each).
// DRAM: the R5a bench checker (tb_hbm_accel_expert_first_access.sv, 52ce3e9c1 constants, JESD238 refresh,
// every command checked).  RD data returns PHY_CMD + CL + BL8 + RSP + NOC after the RD (ASSUMED path terms,
// 15 ns each way, as in R5a).  Data: every consumed sector is compared with the backing pattern of its
// (PC, sector) location, so the scorer receives exactly the stored bytes.
// Plusargs: +mode +nsect +nk +nrows +t_go_ps +notice_lead_ps (0: no notice) +prefetch_ps (scan RDs before the query)  +mut=1 (corrupt one sector)  +mut=2 (tRCD check +1 ns).  Prints one BW line + verdict.
module tb_dshbm_1m_streams;
  parameter integer REF_MODE = 1;
  integer MODE = 0;                          // +mode: 0 scan, 1 gather
  integer NSECT = 182;                       // +nsect: scan sectors a PC
  integer NK = 0;                            // +nk: scan consumer keys / clk on this stack (0 = unthrottled)
  integer NROWS = 2;                         // +nrows: gather 288-B rows on this stack
  integer POST_LEAD_PS = 200000;             // +post_lead_ps: scan descriptor posted this long before go
  parameter integer NOC_PS = 5000, PHY_CMD_PS = 5000;
  parameter integer LAW = 5;                 // landing crossing depth 2**LAW = PC credits (R5a: 5)
  integer MUT = 0;
  localparam integer NPC = 32, CYC = 1024, CLK = 833, PERIOD = REF_MODE ? 118 : 3808;
  localparam longint BURST=1024, TCCDL=2560, CL=12500, RCD=19375, RP=16250, RAS=28125, RTP=5625,
    RRDS=2500, RRDL=3125, FAW=15000, RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;
  localparam integer ROW_BASE = 100;

  reg clk = 0, hclk = 0, rst_n = 0, hrst_n = 0;
  always #416.5 clk = ~clk;
  always #(CYC/2) hclk = ~hclk;

  function automatic [255:0] pat(input integer pc, input integer j); pat = {8{32'((pc << 16) | j) ^ 32'hA500_0000}}; endfunction

  // ---------------- per-PC descriptors and the stream PCs ----------------
  reg  [NPC-1:0] dv = 0; wire [NPC-1:0] dr; reg [NPC*19-1:0] drow = 0; reg [NPC*11-1:0] dn = 0; reg go = 0; reg notice = 0;
  longint notice_lead = 0, prefetch = 0;   // +prefetch_ps: scan RDs start this long before the query (go)
  wire [NPC-1:0] row_v, col_v, busy, pfault; wire [NPC*3-1:0] row_op; wire [NPC*5-1:0] row_bank, col_bank, col_col;
  wire [NPC*19-1:0] row_row; reg [NPC-1:0] rd_v = 0; reg [NPC*256-1:0] rd_data = 0;
  wire [NPC*3-1:0] cred_ret; wire [NPC-1:0] l_empty, l_full; reg [NPC-1:0] l_re; wire [NPC*256-1:0] l_q;
  for (genvar p = 0; p < NPC; p = p + 1) begin : pc
    ot_hbm_accel_expert_stream_pc #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(p), .CRED(1 << LAW),
      .REF_PHASE((p * PERIOD) / 32 % PERIOD)) u (
      .clk(hclk), .rst_n(hrst_n), .desc_v(dv[p]), .desc_r(dr[p]), .desc_row(drow[p*19 +: 19]), .desc_n(dn[p*11 +: 11]),
      .go(go), .next_posted(1'b0), .notice(notice),
      .row_v(row_v[p]), .row_prio(), .row_gnt(1'b1), .row_op(row_op[p*3 +: 3]), .row_bank(row_bank[p*5 +: 5]),
      .row_row(row_row[p*19 +: 19]), .col_v(col_v[p]), .col_bank(col_bank[p*5 +: 5]), .col_col(col_col[p*5 +: 5]),
      .cred_ret(cred_ret[p*3 +: 3]), .busy(busy[p]), .ref_fault(pfault[p]));
    ot_hbm_accel_cdc_fifo #(.W(256), .AW(LAW)) u_land (
      .wclk(hclk), .wrst_n(hrst_n), .we(rd_v[p]), .wdata(rd_data[p*256 +: 256]), .full(l_full[p]),
      .rd_freed(cred_ret[p*3 +: 3]), .rclk(clk), .rrst_n(rst_n), .re(l_re[p]), .rdata(l_q[p*256 +: 256]),
      .empty(l_empty[p]));
  end

  // ---------------- backing array and DRAM checker (R5a bench) ----------------
  bit [255:0] mem [longint];
  function automatic longint midx(input integer pc, bk, rw, col); midx = ((longint'(pc) * 32 + bk) * 65536 + rw) * 32 + col; endfunction
  longint now;
  bit     b_open [0:31][0:31]; int b_row [0:31][0:31];
  longint b_act [0:31][0:31], b_pre [0:31][0:31], b_rd [0:31][0:31], b_ref_end [0:31][0:31];
  longint p_last_act [0:31], p_last_rd [0:31], p_last_ref [0:31], p_last_refpb_any [0:31];
  longint p_act_bg [0:31][0:3], p_rd_bg [0:31][0:3], p_faw [0:31][0:3];
  bit [31:0] p_round [0:31];
  longint viol = 0, n_act = 0, n_rd = 0, n_ref = 0, n_ret = 0;
  longint rq_due [0:31][$]; bit [255:0] rq_dat [0:31][$];
  longint hcyc = 0, t_go = 0, t_rd_first = -1, t_rd_last = -1, t_ret_first = -1, t_ret_last = -1, lfault = 0;
  task automatic v(input string what, input integer pc, input integer bk);
    if (viol < 20) $display("VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
    viol++;
  endtask
  always @(posedge hclk) if (hrst_n) begin
    now = $time;
    if (hcyc == 0) for (int p = 0; p < 32; p++) p_last_ref[p] += now;
    for (int p = 0; p < 32; p++) begin
      if (row_v[p]) begin
        automatic int op = row_op[p*3 +: 3], bk = row_bank[p*5 +: 5], rw = row_row[p*19 +: 19], g = bk & 3;
        case (op)
          1: begin
            n_act++;
            if (b_open[p][bk]) v("ACT to open bank", p, bk);
            if (now < b_pre[p][bk] + RP) v("tRP", p, bk);
            if (now < b_act[p][bk] + RAS + RP) v("tRC", p, bk);
            if (now < p_last_act[p] + RRDS) v("tRRD_S", p, bk);
            if (now < p_act_bg[p][g] + RRDL) v("tRRD_L", p, bk);
            if (now < p_faw[p][0] + FAW) v("tFAW", p, bk);
            if (now < b_ref_end[p][bk]) v("ACT during refresh", p, bk);
            if (now < p_last_refpb_any[p] + RREFD) v("tRREFD", p, bk);
            b_open[p][bk] = 1; b_row[p][bk] = rw; b_act[p][bk] = now;
            p_last_act[p] = now; p_act_bg[p][g] = now;
            p_faw[p][0] = p_faw[p][1]; p_faw[p][1] = p_faw[p][2]; p_faw[p][2] = p_faw[p][3]; p_faw[p][3] = now;
          end
          0: begin
            if (!b_open[p][bk]) v("PRE closed bank", p, bk);
            if (now < b_act[p][bk] + RAS) v("tRAS", p, bk);
            if (now < b_rd[p][bk] + RTP) v("tRTP", p, bk);
            b_open[p][bk] = 0; b_pre[p][bk] = now;
          end
          5: for (int b = 0; b < 32; b++) if (b_open[p][b]) begin
            if (now < b_act[p][b] + RAS) v("tRAS (PREab)", p, b);
            if (now < b_rd[p][b] + RTP) v("tRTP (PREab)", p, b);
            b_open[p][b] = 0; b_pre[p][b] = now;
          end
          4: begin
            n_ref++;
            for (int b = 0; b < 32; b++) begin
              if (b_open[p][b]) v("REFab with open bank", p, b);
              if (now < b_pre[p][b] + RP) v("tRP (REFab)", p, b);
              if (now < b_ref_end[p][b]) v("REFab during refresh", p, b);
              b_ref_end[p][b] = now + RFC;
            end
            if (now - p_last_ref[p] > REFI) v("REFab late", p, 0);
            p_last_ref[p] = now;
          end
          6: begin
            n_ref++;
            if (b_open[p][bk]) v("REFpb to open bank", p, bk);
            if (now < b_pre[p][bk] + RP) v("tRP (REFpb)", p, bk);
            if (now < b_act[p][bk] + RAS + RP) v("tRC (REFpb)", p, bk);
            if (now < b_ref_end[p][bk]) v("REFpb during refresh", p, bk);
            if (now < p_last_act[p] + RREFD) v("tRREFD (REFpb after ACT)", p, bk);
            if (now < p_last_refpb_any[p] + RREFD) v("tRREFD (REFpb after REFpb)", p, bk);
            if (p_round[p][bk]) v("REFpb bank twice in one round", p, bk);
            p_round[p][bk] = 1; if (&p_round[p]) p_round[p] = 0;
            if (now - p_last_ref[p] > REFI / 32) v("REFpb late", p, bk);
            p_last_ref[p] = now; p_last_refpb_any[p] = now;
            b_ref_end[p][bk] = now + RFCPB;
          end
          default: v("unknown row op", p, bk);
        endcase
      end
      if (now - p_last_ref[p] > (REF_MODE ? REFI / 32 : REFI)) begin v("refresh overdue", p, 0); p_last_ref[p] = now; end
      if (col_v[p]) begin
        automatic int bk = col_bank[p*5 +: 5], cl = col_col[p*5 +: 5], g = bk & 3;
        n_rd++;
        if (now >= t_go - prefetch) begin if (t_rd_first < 0) t_rd_first = now; t_rd_last = now; end
        if (!b_open[p][bk]) v("RD closed bank", p, bk);
        if (now < b_act[p][bk] + RCD + (MUT == 2 ? 1000 : 0)) v("tRCD", p, bk);
        if (now < p_last_rd[p] + BURST) v("tCCD_S", p, bk);
        if (now < p_rd_bg[p][g] + TCCDL) v("tCCD_L", p, bk);
        if (now < b_ref_end[p][bk]) v("RD during refresh", p, bk);
        p_last_rd[p] = now; p_rd_bg[p][g] = now; b_rd[p][bk] = now;
        rq_due[p].push_back(now + PHY_CMD_PS + CL + BURST + RSP + NOC_PS);
        rq_dat[p].push_back(mem.exists(midx(p, bk, b_row[p][bk], cl)) ? mem[midx(p, bk, b_row[p][bk], cl)] : '1);
      end
    end
    for (int p = 0; p < 32; p++) begin
      if (rq_due[p].size() != 0 && rq_due[p][0] <= now) begin
        rd_v[p] <= 1; rd_data[p*256 +: 256] <= rq_dat[p].pop_front(); void'(rq_due[p].pop_front());
        if (t_ret_first < 0) t_ret_first = now; t_ret_last = now; n_ret++;
        if (l_full[p]) lfault++;
      end else rd_v[p] <= 0;
    end
    hcyc <= hcyc + 1;
  end

  // ---------------- consumer (clk): scorer at NK keys a cycle, in-order data check per PC ----------------
  integer exp_n [0:NPC-1]; integer got [0:NPC-1]; integer exp_j [0:NPC-1][0:15];
  int qrow [0:NPC-1][$];
  longint bad = 0, good = 0, t_cons_first = -1, t_cons_last = -1, credit_b = 0;
  integer rr = 0;
  reg [NPC-1:0] re_c; integer npop;
  always @* begin
    automatic longint avail = credit_b + NK * 68; automatic int budget = (NK == 0) ? NPC : int'(avail / 32);
    re_c = 0; npop = 0;
    for (int k = 0; k < NPC; k++) begin
      automatic int p = (rr + k) % NPC;
      if (budget > 0 && !l_empty[p] && $time >= t_go) begin re_c[p] = 1; budget--; npop++; end
    end
    l_re = re_c;
  end
  always @(posedge clk) if (rst_n) begin
    for (int p = 0; p < NPC; p++) if (re_c[p]) begin
      automatic int j = (MODE == 0) ? got[p] : exp_j[p][got[p]];
      if (l_q[p*256 +: 256] !== pat(p, j)) begin if (bad < 5) $display("DATA MISMATCH pc=%0d j=%0d", p, j); bad++; end
      else good++;
      got[p]++;
      if (t_cons_first < 0) t_cons_first = $time; t_cons_last = $time;
    end
    if (NK != 0) begin
      credit_b = credit_b + NK * 68 - 32 * npop;
      if (credit_b > 4 * 32) credit_b = 4 * 32;     // an idle scorer banks at most 4 sectors of issue slots
    end
    rr = (rr + 1) % NPC;
  end

  // static-schedule notice (R5a): from t_go - lead until the transfer has started; while a PC is idle it keeps
  // REFpb off sets 0..2 (the scan's first sets; every gather row's bank)
  always @(posedge hclk) if (hrst_n) notice <= (notice_lead > 0) && ($time >= t_go - notice_lead) && ($time < t_go + 2000000);

  // ---------------- gather feeder (MODE 1): next single-sector descriptor as soon as the PC is free ----------
  reg feed = 0; longint n_desc = 0;
  always @(posedge hclk) if (hrst_n && feed) begin
    for (int p = 0; p < NPC; p++) begin
      if (dv[p]) dv[p] <= 0;
      else if (dr[p] && !busy[p] && qrow[p].size() != 0) begin
        dv[p] <= 1; dn[p*11 +: 11] <= 11'd1; drow[p*19 +: 19] <= 19'(qrow[p].pop_front()); n_desc++;
      end
    end
  end

  // ---------------- stimulus ----------------
  integer total;
  initial begin
    automatic longint t_post;
    if (!$value$plusargs("t_go_ps=%d", t_go)) t_go = 8000000;
    if (!$value$plusargs("mut=%d", MUT)) MUT = 0;
    if (!$value$plusargs("mode=%d", MODE)) MODE = 0;
    if (!$value$plusargs("nsect=%d", NSECT)) NSECT = 182;
    if (!$value$plusargs("nk=%d", NK)) NK = 0;
    if (!$value$plusargs("nrows=%d", NROWS)) NROWS = 2;
    if (!$value$plusargs("notice_lead_ps=%d", notice_lead)) notice_lead = 0;
    if (!$value$plusargs("prefetch_ps=%d", prefetch)) prefetch = 0;
    if (!$value$plusargs("post_lead_ps=%d", POST_LEAD_PS)) POST_LEAD_PS = 200000;
    for (int p = 0; p < 32; p++) begin
      got[p] = 0; exp_n[p] = 0;
      p_last_act[p] = -1000000; p_last_rd[p] = -1000000; p_last_refpb_any[p] = -1000000; p_round[p] = 0;
      begin : ph
        automatic int base = ((p * PERIOD) / 32) % PERIOD;
        p_last_ref[p] = longint'(base + ((base + PERIOD + p) % 2)) * CYC;
      end
      for (int g = 0; g < 4; g++) begin p_act_bg[p][g] = -1000000; p_rd_bg[p][g] = -1000000; p_faw[p][g] = -1000000; end
      for (int b = 0; b < 32; b++) begin
        b_open[p][b] = 0; b_act[p][b] = -1000000; b_pre[p][b] = -1000000; b_rd[p][b] = -1000000; b_ref_end[p][b] = 0;
      end
    end
    total = 0;
    if (MODE == 0) begin
      for (int p = 0; p < NPC; p++) begin
        for (int j = 0; j < NSECT; j++) mem[midx(p, ((j >> 7) & 7) * 4 + (j & 3), ROW_BASE, (j >> 2) & 31)] = pat(p, j);
        exp_n[p] = NSECT; total += NSECT;
      end
    end else begin
      // row r's 9 sectors: global sector s = 9 r + q -> PC s % 32, the PC's single sector (j = 0) at a random DRAM row
      for (int s = 0; s < 9 * NROWS; s++) begin
        automatic int p = s % NPC; automatic int rw = 1000 + ((s * 7919 + 13) % 30000);
        mem[midx(p, 0, rw, 0)] = pat(p, 1000 + exp_n[p]); qrow[p].push_back(rw); exp_j[p][exp_n[p]] = 1000 + exp_n[p];
        exp_n[p]++; total++;
      end
    end
    if (MUT == 1) begin automatic longint i = midx(3, 0, MODE == 0 ? ROW_BASE : qrow[3][0], 0); mem[i][13] = ~mem[i][13]; end
    @(posedge hclk); #1; hrst_n = 1; rst_n = 1;
    t_post = (MODE == 0) ? t_go - POST_LEAD_PS : t_go;
    while ($time < t_post) @(posedge hclk);
    if (MODE == 0) begin
      for (int p = 0; p < NPC; p++) if (exp_n[p] != 0) begin
        dv[p] <= 1; dn[p*11 +: 11] <= 11'(NSECT); drow[p*19 +: 19] <= 19'(ROW_BASE);
      end
      @(posedge hclk); dv <= 0;
    end else feed <= 1;
      while ($time < t_go - prefetch) @(posedge hclk);
    go <= 1;
  end
  initial begin
    automatic bit done; automatic longint bytes;
    wait (rst_n);
    forever begin
      @(posedge clk);
      done = 1; for (int p = 0; p < NPC; p++) if (got[p] < exp_n[p]) done = 0;
      if (done && t_cons_last > 0) break;
      if ($time > t_go + 50000000) begin $display("BW TIMEOUT"); break; end
      if (|pfault) begin $display("PC REFRESH FAULT"); break; end
    end
    bytes = longint'(total) * 32;
    $display("BW prefetch_ps=%0d notice_lead_ps=%0d mode=%0d ref_mode=%0d nsect=%0d nk=%0d nrows=%0d t_go_ps=%0d bytes=%0d rd_first=%0d rd_last=%0d ret_first=%0d ret_last=%0d cons_first=%0d cons_last=%0d good=%0d bad=%0d viol=%0d lfault=%0d act=%0d rd=%0d ref=%0d ndesc=%0d post_lead_ps=%0d",
             prefetch, notice_lead, MODE, REF_MODE, NSECT, NK, NROWS, t_go, bytes, t_rd_first - t_go, t_rd_last - t_go, t_ret_first - t_go,
             t_ret_last - t_go, t_cons_first - t_go, t_cons_last - t_go, good, bad, viol, lfault, n_act, n_rd, n_ref, n_desc, POST_LEAD_PS);
    $display("BW verdict=%s", (bad == 0 && viol == 0 && lfault == 0 && good == total && !(|pfault)) ? "PASS" : "FAIL");
    $finish;
  end
endmodule

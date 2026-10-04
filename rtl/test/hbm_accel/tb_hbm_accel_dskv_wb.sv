`timescale 1ps/1fs
// DS-V4.1 HBM accelerator KV write-back at 1M (2026-10-04): ONE HBM3E stack (32 PCs) of the write-back unit
// (ot_hbm_accel_dskv_wb, STACK) on the write-capable stream PC (ot_hbm_accel_stream_pc_wb WB_EN=1; WB_EN=0 is the
// r6 + notice stream PC), refresh live (REFpb), every DRAM command checked (the R5a / dskv-audit checker plus the
// write rules: tRCDWR, tRTW, tWTR_S/L, tWR before PRE, WR to an open bank on its row).
// Phases: (1) a BACKGROUND read stream on all 32 PCs (NBG sectors a PC, its own rows), go at t_bg; (2) at t_inj
// the layer's new rows (window row, compressed-KV row, index key: the golden bytes, from +rows file) enter the
// unit, which posts the stack's sectors; posted-write ACK = WR + PHY_CMD + CWL + BL8 + RSP + NOC; (3) when the
// background is consumed AND the fence is ok (every issued write ACKed), READBACK descriptors re-read every
// written PC row region j = 0 .. max written j through the same stream PCs, and every sector is compared with the
// golden image (golden bytes where written, the untouched background pattern elsewhere); the DRAM array at every
// expected write address is also compared directly.
// Files (python tools/hbm_accel_dskv_wb.py): +rows=FILE  lines "kind slot r2 <1088 hex>" (data byte 0 last);
// +shadow=FILE lines "slot <1088 hex>"; +exp=FILE lines "pc bank row col <64 hex>" (the stack's expected writes).
// Plusargs: +pos +die +t_inj_ps +nbg (0: no background) +nowb=1 (no rows: background alone) +mut=1 (corrupt a
// written DRAM sector after the fence) +mut=2 (fence skipped: readback posted at t_inj) +mut=3 (flip a bit of the
// injected row data) +mut=4 (checker tRCDWR + 1 ns).
module tb_hbm_accel_dskv_wb;
  parameter integer STACK = 1;
  parameter integer NOC_PS = 5000, PHY_CMD_PS = 5000;
  localparam integer NPC = 32, CYC = 1024, PERIOD = 118, LAW = 6;
  localparam longint BURST=1024, TCCDL=2560, CL=12500, CWL=6250, RCD=19375, RCDWR=9375, RP=16250, RAS=28125,
    RTP=5625, WR=20625, WTRS=4375, WTRL=6250, RTW=9948, RRDS=2500, RRDL=3125, FAW=15000, RFCPB=200000,
    REFI=3900000, RSP=10000, RREFD=8000;
  localparam integer BG_ROW = 100;
  integer MUT = 0, NBG = 1024, NOWB = 0;
  longint t_inj = 6000000, t_bg = 5000000;
  reg [19:0] POS = 20'd1048575; reg [6:0] DIE = 7'd31;

  reg clk = 0, hclk = 0, rst_n = 0, hrst_n = 0;
  always #416.5 clk = ~clk;
  always #(CYC/2) hclk = ~hclk;

  function automatic [255:0] pat(input integer pc, input integer bk, input integer rw, input integer cl);
    reg [31:0] w;
    w = (32'(pc) * 32'h9E3779B1 + 32'(bk) * 32'h85EBCA77 + 32'(rw) * 32'hC2B2AE3D + 32'(cl) * 32'h27D4EB2F) ^ 32'hA5A5A5A5;
    pat = {8{w}};
  endfunction

  // ---------------- PCs ----------------
  reg  [NPC-1:0] dv = 0; wire [NPC-1:0] dr; reg [NPC*19-1:0] drow = 0; reg [NPC*11-1:0] dn = 0; reg [NPC-1:0] go = 0;
  wire [NPC-1:0] row_v, col_v, busy, pfault, col_we, wr_ack, wq_r, wq_empty;
  wire [NPC*3-1:0] row_op; wire [NPC*5-1:0] row_bank, col_bank, col_col; wire [NPC*19-1:0] row_row, col_row;
  wire [NPC*256-1:0] col_wdata;
  reg [NPC-1:0] rd_v = 0; reg [NPC*256-1:0] rd_data = 0;
  wire [NPC*3-1:0] cred_ret; wire [NPC-1:0] l_empty, l_full; reg [NPC-1:0] l_re; wire [NPC*256-1:0] l_q;
  reg [NPC-1:0] pwq_v = 0; reg [NPC*5-1:0] pwq_bank = 0, pwq_col = 0; reg [NPC*19-1:0] pwq_row = 0;
  reg [NPC*256-1:0] pwq_data = 0;
  for (genvar p = 0; p < NPC; p = p + 1) begin : pc
    ot_hbm_accel_stream_pc_wb #(.ENABLE(1), .REF_MODE(1), .PC(p), .CRED(1 << LAW), .WB_EN(1),
      .REF_PHASE((p * PERIOD) / 32 % PERIOD)) u (
      .clk(hclk), .rst_n(hrst_n), .desc_v(dv[p]), .desc_r(dr[p]), .desc_row(drow[p*19 +: 19]), .desc_n(dn[p*11 +: 11]),
      .go(go[p]), .next_posted(1'b0), .notice(1'b0),
      .row_v(row_v[p]), .row_prio(), .row_gnt(1'b1), .row_op(row_op[p*3 +: 3]), .row_bank(row_bank[p*5 +: 5]),
      .row_row(row_row[p*19 +: 19]), .col_v(col_v[p]), .col_bank(col_bank[p*5 +: 5]), .col_col(col_col[p*5 +: 5]),
      .cred_ret(cred_ret[p*3 +: 3]), .busy(busy[p]), .ref_fault(pfault[p]),
      .wq_v(pwq_v[p]), .wq_bank(pwq_bank[p*5 +: 5]), .wq_row(pwq_row[p*19 +: 19]), .wq_col(pwq_col[p*5 +: 5]),
      .wq_data(pwq_data[p*256 +: 256]), .wq_r(wq_r[p]), .col_we(col_we[p]), .col_wdata(col_wdata[p*256 +: 256]),
      .col_row(col_row[p*19 +: 19]), .wr_ack(wr_ack[p]), .wq_empty(wq_empty[p]));
    ot_hbm_accel_cdc_fifo #(.W(256), .AW(LAW)) u_land (
      .wclk(hclk), .wrst_n(hrst_n), .we(rd_v[p]), .wdata(rd_data[p*256 +: 256]), .full(l_full[p]),
      .rd_freed(cred_ret[p*3 +: 3]), .rclk(clk), .rrst_n(rst_n), .re(l_re[p]), .rdata(l_q[p*256 +: 256]),
      .empty(l_empty[p]));
  end

  // ---------------- write-back unit ----------------
  reg u_row_v = 0; reg [1:0] u_kind = 0; reg [5:0] u_slot = 0; reg u_r2 = 0; reg [4351:0] u_data = 0;
  reg u_sh_v = 0; reg [2:0] u_sh_slot = 0; reg [4351:0] u_sh_data = 0;
  wire u_row_r, u_wq_v, u_fence; wire [4:0] u_pc, u_bank, u_col; wire [18:0] u_row; wire [255:0] u_wdata;
  wire [15:0] u_iss, u_ack; reg [5:0] ack_n = 0;
  ot_hbm_accel_dskv_wb #(.ENABLE(1), .STACK(STACK)) u_wb (
    .clk(hclk), .rst_n(hrst_n), .die(DIE), .pos(POS),
    .row_v(u_row_v), .row_kind(u_kind), .row_slot(u_slot), .row_r2(u_r2), .row_data(u_data), .row_r(u_row_r),
    .sh_v(u_sh_v), .sh_slot(u_sh_slot), .sh_data(u_sh_data),
    .wq_v(u_wq_v), .wq_pc(u_pc), .wq_bank(u_bank), .wq_row(u_row), .wq_col(u_col), .wq_data(u_wdata), .wq_r(1'b1),
    .ack_n(ack_n), .issued(u_iss), .acked(u_ack), .fence_ok(u_fence));

  // write-request network: each posted sector reaches its PC PHY_CMD + NOC after it leaves the unit
  longint wn_due [0:NPC-1][$]; reg [4:0] wn_b [0:NPC-1][$]; reg [18:0] wn_r [0:NPC-1][$]; reg [4:0] wn_c [0:NPC-1][$];
  reg [255:0] wn_d [0:NPC-1][$];
  longint ack_due [$];
  longint now, hcyc = 0;
  longint n_wr_posted = 0;
  always @(posedge hclk) if (hrst_n) begin
    automatic int na = 0;
    now = $time;
    if (u_wq_v) begin
      wn_due[u_pc].push_back(now + NOC_PS + PHY_CMD_PS); wn_b[u_pc].push_back(u_bank); wn_r[u_pc].push_back(u_row);
      wn_c[u_pc].push_back(u_col); wn_d[u_pc].push_back(u_wdata); n_wr_posted++;
    end
    for (int p = 0; p < NPC; p++) begin
      automatic bit hv;
      if (pwq_v[p] && wq_r[p]) begin            // the PC takes the presented head at this edge
        void'(wn_due[p].pop_front()); void'(wn_b[p].pop_front()); void'(wn_r[p].pop_front());
        void'(wn_c[p].pop_front()); void'(wn_d[p].pop_front());
      end
      hv = wn_due[p].size() != 0 && wn_due[p][0] <= now + CYC;
      pwq_v[p] <= hv;
      if (hv) begin
        pwq_bank[p*5 +: 5] <= wn_b[p][0]; pwq_row[p*19 +: 19] <= wn_r[p][0]; pwq_col[p*5 +: 5] <= wn_c[p][0];
        pwq_data[p*256 +: 256] <= wn_d[p][0];
      end
    end
    while (ack_due.size() != 0 && ack_due[0] <= now) begin void'(ack_due.pop_front()); na++; end
    ack_n <= 6'(na);
  end

  // ---------------- backing array and DRAM checker ----------------
  bit [255:0] mem [longint];
  function automatic longint midx(input integer p, bk, rw, cl); midx = ((longint'(p) * 32 + bk) * 1048576 + rw) * 32 + cl; endfunction
  function automatic [255:0] memrd(input integer p, bk, rw, cl);
    memrd = mem.exists(midx(p, bk, rw, cl)) ? mem[midx(p, bk, rw, cl)] : pat(p, bk, rw, cl);
  endfunction
  bit     b_open [0:31][0:31]; int b_row [0:31][0:31];
  longint b_act [0:31][0:31], b_pre [0:31][0:31], b_rd [0:31][0:31], b_wr [0:31][0:31], b_ref_end [0:31][0:31];
  longint p_last_act [0:31], p_last_rd [0:31], p_last_wr [0:31], p_last_ref [0:31], p_last_refpb_any [0:31];
  longint p_act_bg [0:31][0:3], p_col_bg [0:31][0:3], p_faw [0:31][0:3]; int p_last_wr_bg [0:31];
  bit [31:0] p_round [0:31];
  longint viol = 0, n_act = 0, n_rd = 0, n_wr = 0, n_ref = 0, lfault = 0;
  longint rq_due [0:31][$]; bit [255:0] rq_dat [0:31][$];
  longint t_wr_first = -1, t_wr_last = -1, t_fence = -1;
  task automatic v(input string what, input integer p, input integer bk);
    if (viol < 20) $display("VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, p, bk, what);
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
            if (now < b_wr[p][bk] + CWL + BURST + WR) v("tWR", p, bk);
            b_open[p][bk] = 0; b_pre[p][bk] = now;
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
          default: v("unexpected row op", p, bk);
        endcase
      end
      if (now - p_last_ref[p] > REFI / 32) begin v("refresh overdue", p, 0); p_last_ref[p] = now; end
      if (col_v[p]) begin
        automatic int bk = col_bank[p*5 +: 5], cl = col_col[p*5 +: 5], g = bk & 3;
        if (!b_open[p][bk]) v("column command to closed bank", p, bk);
        if (now < p_last_rd[p] + BURST || now < p_last_wr[p] + BURST) v("tCCD_S", p, bk);
        if (now < p_col_bg[p][g] + TCCDL) v("tCCD_L", p, bk);
        if (now < b_ref_end[p][bk]) v("column command during refresh", p, bk);
        p_col_bg[p][g] = now;
        if (col_we[p]) begin
          n_wr++;
          if (now < b_act[p][bk] + RCDWR + (MUT == 4 ? 1000 : 0)) v("tRCDWR", p, bk);
          if (now < p_last_rd[p] + RTW) v("tRTW", p, bk);
          if (b_row[p][bk] != col_row[p*19 +: 19]) v("WR row mismatch", p, bk);
          p_last_wr[p] = now; p_last_wr_bg[p] = g; b_wr[p][bk] = now;
          mem[midx(p, bk, b_row[p][bk], cl)] = col_wdata[p*256 +: 256];
          if (t_wr_first < 0) t_wr_first = now; t_wr_last = now;
          ack_due.push_back(now + PHY_CMD_PS + CWL + BURST + RSP + NOC_PS);
        end else begin
          n_rd++;
          if (now < b_act[p][bk] + RCD) v("tRCD", p, bk);
          if (now < p_last_wr[p] + CWL + BURST + ((p_last_wr_bg[p] == g) ? WTRL : WTRS)) v("tWTR", p, bk);
          p_last_rd[p] = now; b_rd[p][bk] = now;
          rq_due[p].push_back(now + PHY_CMD_PS + CL + BURST + RSP + NOC_PS);
          rq_dat[p].push_back(memrd(p, bk, b_row[p][bk], cl));
        end
      end
    end
    for (int p = 0; p < 32; p++) begin
      if (rq_due[p].size() != 0 && rq_due[p][0] <= now) begin
        rd_v[p] <= 1; rd_data[p*256 +: 256] <= rq_dat[p].pop_front(); void'(rq_due[p].pop_front());
        if (l_full[p]) lfault++;
      end else rd_v[p] <= 0;
    end
    hcyc <= hcyc + 1;
  end

  // ---------------- consumer: per-PC in-order expected queues ----------------
  bit [255:0] exq [0:NPC-1][$]; int exk [0:NPC-1][$];       // expected data; kind 0 background 1 readback
  longint bad = 0, good = 0, rb_good = 0, bg_last = -1, rb_last = -1;
  always @* begin
    for (int p = 0; p < NPC; p++) l_re[p] = !l_empty[p];
  end
  always @(posedge clk) if (rst_n) begin
    for (int p = 0; p < NPC; p++) if (!l_empty[p]) begin
      if (exq[p].size() == 0) begin if (bad < 5) $display("UNEXPECTED sector pc=%0d", p); bad++; end
      else begin
        automatic bit [255:0] e = exq[p].pop_front(); automatic int kd = exk[p].pop_front();
        if (l_q[p*256 +: 256] !== e) begin if (bad < 5) $display("DATA MISMATCH pc=%0d kind=%0d t=%0d", p, kd, $time); bad++; end
        else begin good++; if (kd) rb_good++; end
        if (kd) rb_last = $time; else bg_last = $time;
      end
    end
  end

  // ---------------- inputs ----------------
  string f_rows, f_sh, f_exp;
  int n_rows = 0, n_sh = 0, n_exp_wr = 0;
  reg [1:0] r_kind [0:15]; reg [5:0] r_slot [0:15]; reg r_r2 [0:15]; reg [4351:0] r_dat [0:15];
  reg [2:0] s_slot [0:7]; reg [4351:0] s_dat [0:7];
  int e_pc [0:255], e_bk [0:255], e_rw [0:255], e_cl [0:255]; reg [255:0] e_dat [0:255];
  bit rows_in = 0;
  longint t_rows_done = -1;
  task automatic load_files();
    int fd, a, b2, c, d; reg [4351:0] x; reg [255:0] y;
    if ($value$plusargs("rows=%s", f_rows)) begin
      fd = $fopen(f_rows, "r");
      while ($fscanf(fd, "%d %d %d %h\n", a, b2, c, x) == 4) begin
        r_kind[n_rows] = 2'(a); r_slot[n_rows] = 6'(b2); r_r2[n_rows] = c[0]; r_dat[n_rows] = x; n_rows++;
      end
      $fclose(fd);
    end
    if ($value$plusargs("shadow=%s", f_sh)) begin
      fd = $fopen(f_sh, "r");
      while ($fscanf(fd, "%d %h\n", a, x) == 2) begin s_slot[n_sh] = 3'(a); s_dat[n_sh] = x; n_sh++; end
      $fclose(fd);
    end
    if ($value$plusargs("exp=%s", f_exp)) begin
      fd = $fopen(f_exp, "r");
      while ($fscanf(fd, "%d %d %d %d %h\n", a, b2, c, d, y) == 5) begin
        e_pc[n_exp_wr] = a; e_bk[n_exp_wr] = b2; e_rw[n_exp_wr] = c; e_cl[n_exp_wr] = d; e_dat[n_exp_wr] = y; n_exp_wr++;
      end
      $fclose(fd);
    end
  endtask
  function automatic int jmax_of(input int p, input int rw);   // highest written PC-local j in (pc, row)
    jmax_of = -1;
    for (int i = 0; i < n_exp_wr; i++) if (e_pc[i] == p && e_rw[i] == rw) begin
      automatic int jj = ((e_bk[i] >> 2) << 7) | (e_cl[i] << 2) | (e_bk[i] & 3);
      if (jj > jmax_of) jmax_of = jj;
    end
  endfunction
  function automatic [255:0] golden(input int p, bk, rw, cl);
    golden = pat(p, bk, rw, cl);
    for (int i = 0; i < n_exp_wr; i++)
      if (e_pc[i] == p && e_bk[i] == bk && e_rw[i] == rw && e_cl[i] == cl) golden = e_dat[i];
  endfunction
  always @(posedge hclk) if (hrst_n && t_fence < 0 && rows_in && u_fence && $time > t_inj) t_fence = $time;
  // readback: one descriptor a (pc, row) region, posted when allowed, expected = golden image
  int rb_pc [0:63], rb_row [0:63], rb_n [0:63]; int n_rb = 0; longint t_rb_go = -1;
  task automatic post_readback();
    for (int i = 0; i < n_rb; i++) begin
      automatic int p = rb_pc[i];
      while (!dr[p]) @(posedge hclk);
      for (int jj = 0; jj < rb_n[i]; jj++) begin
        exq[p].push_back(golden(p, ((jj >> 7) & 7) * 4 + (jj & 3), rb_row[i], (jj >> 2) & 31)); exk[p].push_back(1);
      end
      dv[p] <= 1; drow[p*19 +: 19] <= 19'(rb_row[i]); dn[p*11 +: 11] <= 11'(rb_n[i]); go[p] <= 1;
      @(posedge hclk); dv[p] <= 0;
      @(posedge hclk);
    end
  endtask

  // ---------------- stimulus ----------------
  initial begin
    void'($value$plusargs("t_inj_ps=%d", t_inj));
    void'($value$plusargs("t_bg_ps=%d", t_bg));
    void'($value$plusargs("mut=%d", MUT));
    void'($value$plusargs("nbg=%d", NBG));
    void'($value$plusargs("nowb=%d", NOWB));
    begin int tmp; if ($value$plusargs("pos=%d", tmp)) POS = 20'(tmp); if ($value$plusargs("die=%d", tmp)) DIE = 7'(tmp); end
    load_files();
    if (NOWB) n_exp_wr = 0;
    for (int p = 0; p < 32; p++) begin
      p_last_act[p] = -1000000; p_last_rd[p] = -1000000; p_last_wr[p] = -1000000; p_last_refpb_any[p] = -1000000;
      p_round[p] = 0; p_last_wr_bg[p] = 0;
      begin : ph
        automatic int base = ((p * PERIOD) / 32) % PERIOD;
        p_last_ref[p] = longint'(base + ((base + PERIOD + p) % 2)) * CYC;
      end
      for (int g = 0; g < 4; g++) begin p_act_bg[p][g] = -1000000; p_col_bg[p][g] = -1000000; p_faw[p][g] = -1000000; end
      for (int b = 0; b < 32; b++) begin
        b_open[p][b] = 0; b_act[p][b] = -1000000; b_pre[p][b] = -1000000; b_rd[p][b] = -1000000;
        b_wr[p][b] = -1000000; b_ref_end[p][b] = 0;
      end
    end
    // readback regions: every (pc, row) with an expected write
    for (int i = 0; i < n_exp_wr; i++) begin
      automatic bit seen = 0;
      for (int r = 0; r < n_rb; r++) if (rb_pc[r] == e_pc[i] && rb_row[r] == e_rw[i]) seen = 1;
      if (!seen) begin rb_pc[n_rb] = e_pc[i]; rb_row[n_rb] = e_rw[i]; rb_n[n_rb] = jmax_of(e_pc[i], e_rw[i]) + 1; n_rb++; end
    end
    @(posedge hclk); #1; hrst_n = 1; rst_n = 1;
    // shadow (the owner's open key block) loaded at bring-up
    for (int i = 0; i < n_sh; i++) begin
      @(posedge hclk); u_sh_v <= 1; u_sh_slot <= s_slot[i]; u_sh_data <= s_dat[i];
    end
    @(posedge hclk); u_sh_v <= 0;
    // background stream
    while ($time < t_bg - 200000) @(posedge hclk);
    if (NBG > 0) for (int p = 0; p < NPC; p++) begin
      dv[p] <= 1; drow[p*19 +: 19] <= 19'(BG_ROW); dn[p*11 +: 11] <= 11'(NBG);
      for (int jj = 0; jj < NBG; jj++) begin exq[p].push_back(pat(p, ((jj >> 7) & 7) * 4 + (jj & 3), BG_ROW, (jj >> 2) & 31)); exk[p].push_back(0); end
    end
    @(posedge hclk); dv <= 0;
    while ($time < t_bg) @(posedge hclk);
    go <= '1;
    // rows
    while ($time < t_inj) @(posedge hclk);
    if (MUT == 2) fork post_readback(); join_none
    if (!NOWB) for (int i = 0; i < n_rows; i++) begin
      u_row_v <= 1; u_kind <= r_kind[i]; u_slot <= r_slot[i]; u_r2 <= r_r2[i];
      u_data <= (MUT == 3 && i == n_rows - 1) ? r_dat[i] ^ 4352'd1 : r_dat[i];
      @(posedge hclk); while (!u_row_r) @(posedge hclk);
      u_row_v <= 0; @(posedge hclk);
    end
    rows_in = 1; t_rows_done = $time;
    // fence, then the next token's read of the written regions
    if (MUT != 2) begin
      if (n_exp_wr > 0) wait (t_fence > 0);
      while (busy != 0) @(posedge hclk);
      if (MUT == 1 && n_exp_wr > 0) begin automatic longint i = midx(e_pc[0], e_bk[0], e_rw[0], e_cl[0]); mem[i][13] = ~mem[i][13]; end
      t_rb_go = $time;
      post_readback();
    end
  end
  initial begin
    automatic bit done; automatic int dram_bad = 0;
    wait (rst_n);
    forever begin
      @(posedge clk);
      done = (t_rows_done > 0) && (t_fence > 0 || n_exp_wr == 0) && busy == 0;
      for (int p = 0; p < NPC; p++) if (exq[p].size() != 0 || !l_empty[p]) done = 0;
      if (MUT != 2 && t_rb_go < 0 && n_exp_wr > 0) done = 0;
      if (done) break;
      if ($time > t_inj + 60000000) begin $display("WB TIMEOUT"); break; end
      if (|pfault) begin $display("PC REFRESH FAULT"); break; end
    end
    for (int i = 0; i < n_exp_wr; i++) if (memrd(e_pc[i], e_bk[i], e_rw[i], e_cl[i]) !== e_dat[i]) dram_bad++;
    $display("WB stack=%0d pos=%0d die=%0d t_inj_ps=%0d nbg=%0d nowb=%0d mut=%0d exp_wr=%0d posted=%0d issued=%0d wr=%0d wr_first=%0d wr_last=%0d fence=%0d bg_last=%0d rb_last=%0d rb_go=%0d good=%0d rb_good=%0d bad=%0d dram_bad=%0d viol=%0d lfault=%0d act=%0d rd=%0d ref=%0d",
             STACK, POS, DIE, t_inj, NBG, NOWB, MUT, n_exp_wr, n_wr_posted, u_iss, n_wr,
             t_wr_first < 0 ? -1 : t_wr_first - t_inj, t_wr_last < 0 ? -1 : t_wr_last - t_inj,
             t_fence < 0 ? -1 : t_fence - t_inj, bg_last < 0 ? -1 : bg_last - t_bg, rb_last < 0 ? -1 : rb_last - t_inj,
             t_rb_go < 0 ? -1 : t_rb_go - t_inj, good, rb_good, bad, dram_bad, viol, lfault, n_act, n_rd, n_ref);
    $display("WB verdict=%s", (bad == 0 && dram_bad == 0 && viol == 0 && lfault == 0 && !(|pfault) &&
                                n_wr == n_exp_wr && n_wr_posted == n_exp_wr) ? "PASS" : "FAIL");
    $finish;
  end
endmodule

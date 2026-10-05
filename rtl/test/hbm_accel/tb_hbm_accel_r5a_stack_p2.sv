`timescale 1ps/1fs
// HA4 R5a SRAM-staging successor bench (copy of tb_hbm_accel_expert_first_access.sv with the DUT
// ot_hbm_accel_expert_fetch_p2 on the compiled 1R1W macros' behavioural model, and +stall=<pct>:
// random SM back-pressure on s_ready).
// HA4 R5a bench: routed-expert FIRST ACCESS on the streaming controller with refresh live.
//   top-6 ids (clk, 1.2 GHz) -> NoC -> ot_hbm_accel_expert_fetch_stream (id CDC, dispatch, 32
//   ot_hbm_accel_expert_stream_pc at CK/2 = 1.024 ns, landing CDC FIFOs, SM staging/release)
//   -> HBM3E behavioural device below.
// DRAM: per-PC bank/timing checker in picoseconds with the 52ce3e9c1 bench constants (Ramulator2
// HBM3 preset as in ot_hdc_hbm_model.sv, JESD238 tREFI 3.9 us / tRFC 350 ns, tRFCpb 200 ns from
// ot_hdc_v41x_idx_hbm.sv, tRREFD 8 ns assumed).  Every command is checked and refresh must never be
// overdue.  RD data returns PHY_CMD + CL + BL8 + RSP + NOC after the RD (PHY_CMD, RSP and NOC are
// ASSUMED path latencies, the same terms the c52 bench charged as REQ_PS/RSP_PS = 15 ns each way).
// Data: the backing array holds, at the stream location of (expert, line-order L, quarter), the
// c52 bench pattern of that SM line's c52 address; every released line is compared with it, so the
// SMs receive exactly the bytes ot_gpu_expert_fetch would deliver.
// Plusargs: +t_route_ps=<router top-6 time>  +notice_lead_ps=<0: no notice>  +mut=<negative control>
// Prints one FIRST line (times from top-6 out) and a verdict.
module tb_hbm_accel_r5a_stack_p2;
 import ot_gpu_w6_secded_pkg::*;
  parameter integer REF_MODE = 1;
  parameter integer PHASE = 0;
  parameter integer HPHASE_PS = 0;           // hclk phase against clk
  parameter integer NOC_PS = 5000, PHY_CMD_PS = 5000;
  integer MUT = 0, STALL = 0;                // +mut=1: corrupt one sector (negative control); 2: tRCD check +1 ns
  reg [7:0] s_rdy = 8'hFF;
  localparam integer NSM = 8, NPC = 32, NSECT = 49, NLINE = 392, NIDS = 6, ROW_BASE = 0;
  localparam integer CYC = 1024; localparam realtime CLK = 833.333333333;
  localparam longint BURST=1024, TCCDL=2560, CL=12500, RCD=19375, RP=16250, RAS=28125, RTP=5625,
    RRDS=2500, RRDL=3125, FAW=15000, RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;
  // c52 layout (results/rtl/w19_expert_fetch.json layout): lines and w1/w3 lines per SM, offsets
  localparam integer LINES [0:7] = '{53, 53, 43, 43, 50, 50, 50, 50};
  localparam integer W13 [0:7]   = '{43, 43, 43, 43, 22, 22, 22, 22};
  localparam integer OFF [0:7]   = '{0, 53, 106, 149, 192, 242, 292, 342};
  localparam integer EXP_LINES = 392;

  reg clk = 0, hclk = 0, rst_n = 0; wire hrst_n=dut.on.hreset_n;
  always #(CLK/2) clk = ~clk;
  initial begin #(HPHASE_PS); forever #(CYC/2) hclk = ~hclk; end

  // ---------------- static layout: line order L -> (sm, line); w1/w3 of every SM first ----------------
  integer lut_sm [0:NLINE-1], lut_ln [0:NLINE-1];
  reg [NLINE*16-1:0] cfg_lut; reg [NSM*16-1:0] cfg_lines;
  initial begin
    automatic integer L = 0;
    for (int i = 0; i < 64; i++) for (int m = 0; m < NSM; m++) if (i < W13[m]) begin lut_sm[L] = m; lut_ln[L] = i; L++; end
    for (int i = 0; i < 64; i++) for (int m = 0; m < NSM; m++) if (i < LINES[m] - W13[m]) begin
      lut_sm[L] = m; lut_ln[L] = W13[m] + i; L++; end
    if (L != NLINE) begin $display("LAYOUT ERROR %0d", L); $finish; end
    for (int l = 0; l < NLINE; l++) cfg_lut[l*16 +: 16] = {8'(lut_sm[l]), 8'(lut_ln[l])};
    for (int m = 0; m < NSM; m++) cfg_lines[m*16 +: 16] = 16'(LINES[m]);
  end
  function automatic [255:0] pat(input [31:0] s); pat = {8{s ^ 32'hA500_0000}}; endfunction

  // ---------------- DUT ----------------
  reg e_valid = 0; wire e_ready; reg [8:0] e_id = 0; reg notice = 0;
  wire [NPC-1:0] row_v, col_v; wire [NPC*3-1:0] row_op; wire [NPC*5-1:0] row_bank, col_bank, col_col;
  wire [NPC*19-1:0] row_row; reg [NPC-1:0] rd_v = 0; reg [NPC*256-1:0] rd_data = 0;
  wire [NSM-1:0] s_valid; wire [NSM*1024-1:0] s_data; wire fault;
  reg cfg_v=0;wire cfg_r;wire[511:0] col_ordinal;reg[511:0] rsp_ordinal=0;
  ot_hbm_accel_expert_stack_p2 #(.ENABLE(1),.REF_MODE(REF_MODE),.PHASE(PHASE)) dut(
   .stream_clk(clk),.service_clk(hclk),.por_n(rst_n),.cfg_v(cfg_v),.cfg_r(cfg_r),
   .cfg_lines(cfg_lines),.cfg_lut(cfg_lut),.e_valid(e_valid),.e_ready(e_ready),.e_id(e_id),.notice(notice),
   .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
   .col_v(col_v),.col_bank(col_bank),.col_col(col_col),.col_ordinal(col_ordinal),
   .rsp_v(rd_v),.rsp_data(rd_data),.rsp_ordinal(rsp_ordinal),
   .s_valid(s_valid),.s_ready(s_rdy),.s_data(s_data),.fault(fault));
  // Exercise faults on the actual receiver's held code, not a free external
  // encoder. One flipped DATA position corrects; two positions refuse.
  initial begin
   wait(rst_n);
   if(MUT==3||MUT==4)begin
    wait(dut.on.sm[0].v0);@(negedge clk);
    if(MUT==3)begin
     if(dut.on.sm[0].coded[2])force dut.on.sm[0].coded[2]=0;
     else force dut.on.sm[0].coded[2]=1;
    end else begin
     if(dut.on.sm[0].coded[0])force dut.on.sm[0].coded[0]=0;
     else force dut.on.sm[0].coded[0]=1;
     if(dut.on.sm[0].coded[1])force dut.on.sm[0].coded[1]=0;
     else force dut.on.sm[0].coded[1]=1;
    end
    @(posedge clk);#1;release dut.on.sm[0].coded[2];release dut.on.sm[0].coded[0];release dut.on.sm[0].coded[1];
   end
   if(MUT==9)begin
    wait(dut.on.sm[0].v1);@(negedge clk);
    if(dut.on.sm[0].captured[2])force dut.on.sm[0].captured[2]=0;
    else force dut.on.sm[0].captured[2]=1;
   end
  end
  initial begin
   wait(rst_n);@(negedge clk);cfg_v=1;
   @(posedge clk);while(!cfg_r)@(posedge clk);
   @(negedge clk);cfg_v=0;
  end
  initial begin
    wait(rst_n);if(MUT==6)begin
      while($time<t_route+NOC_PS+10000)@(posedge clk);
      force dut.on.fetch.on.loc[0].ix=32'd123;
    end
  end
  // Corrupt after the SRAM code has reached the captured correction stage,
  // before its first publication. The real syndrome and packet rails, rather
  // than an upstream encoded test word, must refuse these faults.
  initial begin
    wait(rst_n);
    if(MUT==7 || MUT==8)begin
      wait(dut.on.fetch.on.sm[0].v2); @(negedge clk);
      if(MUT==7)begin
        if(dut.on.fetch.on.sm[0].synd[0])force dut.on.fetch.on.sm[0].synd[0]=1'b0;
        else force dut.on.fetch.on.sm[0].synd[0]=1'b1;
      end else begin
        if(dut.on.fetch.on.sm[0].packet2[2])force dut.on.fetch.on.sm[0].packet2[2]=1'b0;
        else force dut.on.fetch.on.sm[0].packet2[2]=1'b1;
      end
    end
  end
  // ---------------- backing array: [pc][bank][row][col] ----------------
  bit [255:0] mem [longint];
  function automatic longint midx(input integer pc, bk, rw, col); midx = ((longint'(pc) * 32 + bk) * 65536 + rw) * 32 + col; endfunction
  integer ids [0:NIDS-1] = '{61, 69, 112, 170, 299, 357};     // c52 bench golden router top-6 (ar_L0)

  // ---------------- DRAM checker (ps) ----------------
  longint now;
  bit     b_open [0:31][0:31]; int b_row [0:31][0:31];
  longint b_act [0:31][0:31], b_pre [0:31][0:31], b_rd [0:31][0:31], b_ref_end [0:31][0:31];
  longint p_last_act [0:31], p_last_rd [0:31], p_last_ref [0:31], p_last_refpb_any [0:31];
  longint p_act_bg [0:31][0:3], p_rd_bg [0:31][0:3], p_faw [0:31][0:3];
  bit [31:0] p_round [0:31];
  longint viol = 0, n_act = 0, n_rd = 0, n_ref = 0, n_ref_set0_window = 0;
  bit[15:0] rq_seq[0:31][$]; longint rq_due [0:31][$]; bit [255:0] rq_dat [0:31][$];
  longint hcyc = 0, t_route = 0, notice_lead = 0, t_first_cmd = -1, ref_block_ps = 0;
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
            if (t_first_cmd < 0 && now >= t_route) t_first_cmd = now;
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
        if (!b_open[p][bk]) v("RD closed bank", p, bk);
        if (now < b_act[p][bk] + RCD + (MUT == 2 ? 1000 : 0)) v("tRCD", p, bk);
        if (now < p_last_rd[p] + BURST) v("tCCD_S", p, bk);
        if (now < p_rd_bg[p][g] + TCCDL) v("tCCD_L", p, bk);
        if (now < b_ref_end[p][bk]) v("RD during refresh", p, bk);
        // a set-0 bank under refresh at the router time is the collision R5a removes
        p_last_rd[p] = now; p_rd_bg[p][g] = now; b_rd[p][bk] = now;
        rq_seq[p].push_back(col_ordinal[p*16+:16]);
        rq_due[p].push_back(now + PHY_CMD_PS + CL + BURST + RSP + NOC_PS);
        rq_dat[p].push_back(mem.exists(midx(p, bk, b_row[p][bk], cl)) ? mem[midx(p, bk, b_row[p][bk], cl)] : '1);
      end
    end
    // returns: one sector per PC per hclk, in RD order
    for (int p = 0; p < 32; p++) begin
      if (rq_due[p].size() != 0 && rq_due[p][0] <= now) begin
        rsp_ordinal[p*16+:16] <= rq_seq[p].pop_front() ^ ((MUT==5&&p==7&&dut.on.phy[7].returned==0)?16'd1:16'd0);
        rd_v[p] <= 1; rd_data[p*256 +: 256] <= rq_dat[p].pop_front(); void'(rq_due[p].pop_front());
      end else rd_v[p] <= 0;
    end
    // set-0 refresh in progress at the router time (diagnostic)
    hcyc <= hcyc + 1;
  end

  // ---------------- consumer (clk): release order and data check ----------------
  integer cnt [0:NSM-1]; longint t_w13 [0:NSM-1], t_e1 [0:NSM-1], t_done [0:NSM-1];
  longint bad = 0, good = 0, t_ids = -1;
  always @(posedge clk) if (rst_n) begin
    for (int m = 0; m < NSM; m++) if (s_valid[m] && s_rdy[m]) begin
      automatic int k = cnt[m] / LINES[m], l = cnt[m] % LINES[m];
      automatic longint line = longint'(ids[k]) * EXP_LINES + OFF[m] + l;
      for (int q = 0; q < 4; q++) if (s_data[m*1024 + q*256 +: 256] !== pat(32'(line * 4 + q))) begin
        if (bad < 5) $display("DATA MISMATCH sm=%0d k=%0d line=%0d q=%0d", m, k, l, q);
        bad++;
      end else good++;
      cnt[m]++;
      if (cnt[m] == W13[m]) t_w13[m] = $time;
      if (cnt[m] == LINES[m]) t_e1[m] = $time;
      if (cnt[m] == LINES[m] * NIDS) t_done[m] = $time;
    end
    if (fault) begin $display("DUT FAULT at %0d ps sm0_delivered=%0d", $time,cnt[0]); $finish; end
  end

  always @(posedge clk) for (int m = 0; m < NSM; m++) s_rdy[m] <= (STALL == 0) || ($urandom_range(99) >= STALL);

  // ---------------- stimulus ----------------
  initial begin
    automatic bit fl = 1;
    if (!$value$plusargs("t_route_ps=%d", t_route)) t_route = 8000000;
    if (!$value$plusargs("notice_lead_ps=%d", notice_lead)) notice_lead = 0;
    if (!$value$plusargs("mut=%d", MUT)) MUT = 0;
    if (!$value$plusargs("stall=%d", STALL)) STALL = 0;
    for (int k = 0; k < NIDS; k++)
      for (int L = 0; L < NLINE; L++) for (int q = 0; q < 4; q++) begin
        automatic int s = 4 * L + q, p = s % NPC, j = s / NPC;
        automatic longint line = longint'(ids[k]) * EXP_LINES + OFF[lut_sm[L]] + lut_ln[L];
        mem[midx(p, j & 3, ROW_BASE + ids[k], (j >> 2) & 31)] = pat(32'(line * 4 + q));
      end
    if (MUT == 1) begin automatic longint i = midx(7, 1, ROW_BASE + ids[0], 0); mem[i][13] = ~mem[i][13]; end
    for (int m = 0; m < NSM; m++) begin cnt[m] = 0; t_w13[m] = -1; t_e1[m] = -1; t_done[m] = -1; end
    for (int p = 0; p < 32; p++) begin
      p_last_act[p] = -1000000; p_last_rd[p] = -1000000; p_last_refpb_any[p] = -1000000; p_round[p] = 0;
      begin : ph
        automatic int P = REF_MODE ? 118 : 3808;
        automatic int base = (PHASE + (p * P) / 32) % P;
        p_last_ref[p] = longint'(base + ((base + P + p) % 2)) * CYC;   // + first active edge (below)
      end
      for (int g = 0; g < 4; g++) begin p_act_bg[p][g] = -1000000; p_rd_bg[p][g] = -1000000; p_faw[p][g] = -1000000; end
      for (int b = 0; b < 32; b++) begin
        b_open[p][b] = 0; b_act[p][b] = -1000000; b_pre[p][b] = -1000000; b_rd[p][b] = -1000000; b_ref_end[p][b] = 0;
      end
    end
    // both resets released together on an hclk edge so the RTL refresh phase matches the checker
    @(posedge hclk); #1; rst_n = 1;
  end
  // notice: static schedule (hclk domain), from t_route - lead until the stream has started
  always @(posedge hclk) if (hrst_n) notice <= (notice_lead > 0) && ($time >= t_route - notice_lead) && ($time < t_route + 2000000);
  // ids: top-6 out at t_route (clk), through NOC_PS of wire, then one a cycle
  initial begin
    wait (rst_n);
    while ($time < t_route + NOC_PS) @(posedge clk);
    t_ids = $time;
    for (int k = 0; k < NIDS; k++) begin
      e_valid <= 1; e_id <= 9'(ids[k]);
      @(posedge clk); while (!e_ready) @(posedge clk);
    end
    e_valid <= 0;
  end
  initial begin
    automatic longint w13 = 0, e1 = 0, dn = 0;
    wait (rst_n);
    forever begin
      @(posedge clk);
      begin
        automatic bit all = 1;
        for (int m = 0; m < NSM; m++) if (t_done[m] < 0) all = 0;
        if (all) break;
      end
      if ($time > t_route + 20000000) begin $display("FIRST TIMEOUT"); $finish; end
    end
    for (int m = 0; m < NSM; m++) begin
      if (t_w13[m] > w13) w13 = t_w13[m]; if (t_e1[m] > e1) e1 = t_e1[m]; if (t_done[m] > dn) dn = t_done[m];
    end
    $display("FIRST ref_mode=%0d phase=%0d t_route_ps=%0d notice_lead_ps=%0d first_act_ps=%0d w13_first_all_ps=%0d exp1_all_ps=%0d done_ps=%0d good=%0d bad=%0d viol=%0d act=%0d rd=%0d ref=%0d",
             REF_MODE, PHASE, t_route, notice_lead, t_first_cmd < 0 ? -1 : t_first_cmd - t_route,
             w13 - t_route, e1 - t_route, dn - t_route, good, bad, viol, n_act, n_rd, n_ref);
    $display("FIRST verdict=%s", (bad == 0 && viol == 0 && good == longint'(NIDS) * NLINE * 4) ? "PASS" : "FAIL");
    $finish;
  end
endmodule

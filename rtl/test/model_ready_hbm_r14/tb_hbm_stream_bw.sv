`timescale 1ps/1fs
// Near-HBM KV stream bench for ot_hbm_r14_stream_stack (one HBM3E stack, 32 PCs).
//  * DRAM: a behavioural per-PC bank/timing checker in picoseconds with the
//    ot_hdc_hbm_model.sv parameters (tRCD, tRP, tRAS, tRC, tRTP, tCCD_S/L, tRRD_S/L, tFAW,
//    CL, response path; JESD238 tREFI/tRFC, tRFCpb; tRREFD assumed 8 ns).  Every command is
//    checked; refresh is checked strictly on schedule (REFab interval <= tREFI, REFpb
//    interval <= tREFI/32, every bank once per 32-command round).  RD data comes from a
//    backing array, at the open row, CL + BL8 + response path after the RD.
//  * Source: the bench fills the backing array from a source function src(layer, s) through
//    its own copy of the KV map (s = stack stream sector: BG s[1:0], PC s[6:2], column
//    s[11:7], bank set s[14:12], row = layer).
//  * Consumer: per-PC landing FIFO of CRED sectors (credits to the sequencer); pops in
//    stream order, up to 32 sectors per cycle and 4 per PC (one 128 B KV row), and compares
//    every byte against src(layer, s).
// Layer L: descriptor posted HINT cycles before go_L = round(L * PERIOD_PS / 1024); go_L for
// B2B=1 is the cycle after layer L-1's last sector (next_posted=1).
module tb_hbm_stream_bw;
  parameter integer REF_MODE = 1;
  parameter integer HINT = 320;
  parameter integer LAYERS = 36;
  parameter integer PHASE = 0;
  parameter integer B2B = 0;
  parameter integer CRED = 32;
  parameter longint PERIOD_PS = 5234167;      // 6,281 cycles at 1.2 GHz
  parameter integer MUT = 0;                  // negative controls: 1 tRCD check +1 ns, 2 one corrupted sector, 3 REFpb interval check -2 ns
  localparam integer NS = 1024;               // sectors per PC per layer
  localparam integer CYC = 1024;              // ps per controller cycle (CK/2)
  // timing (ps): ot_hdc_hbm_model.sv defaults; RFCPB from ot_hdc_v41x_idx_hbm.sv; RREFD assumed
  localparam longint BURST=1024, TCCDL=2560, CL=12500, RCD=19375, RP=16250, RAS=28125, RTP=5625,
    RRDS=2500, RRDL=3125, FAW=15000, RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;

  reg clk = 0, rst_n = 0;
  always #(CYC/2) clk = ~clk;
  reg desc_v = 0; wire desc_r; reg go = 0;
  wire [31:0] row_v, col_v, busy; wire [95:0] row_op; wire [159:0] row_bank, col_bank, col_col;
  wire [607:0] row_row; reg [95:0] cred_ret = 0; wire fault;
  reg [18:0] desc_row = 0;
  ot_hbm_r14_stream_stack #(.ENABLE(1), .REF_MODE(REF_MODE), .CRED(CRED), .PHASE(PHASE)) dut (
    .clk(clk), .rst_n(rst_n), .desc_v(desc_v), .desc_r(desc_r), .desc_row(desc_row), .desc_n(11'(NS)),
    .go(go), .next_posted(B2B != 0), .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),
    .col_v(col_v), .col_bank(col_bank), .col_col(col_col), .cred_ret(cred_ret), .busy(busy), .fault(fault),
    .wr_v(32'b0), .wr_bank(160'b0), .wr_col(160'b0), .wr_r(), .col_we());

  function automatic [255:0] src(input integer layer, input integer s);
    for (integer w = 0; w < 8; w++) src[32*w +: 32] = (32'(layer) * 32'h01000193 ^ 32'(s * 8 + w)) * 32'h9E3779B1 ^ 32'h5bd1e995;
  endfunction
  // backing array [pc][bank][row][col]
  bit [255:0] mem [0:32*32*LAYERS*32-1];
  function automatic integer midx(input integer pc, bk, rw, col);
    midx = ((pc * 32 + bk) * LAYERS + rw) * 32 + col;
  endfunction

  // ---- DRAM state / checker (ps) --------------------------------------------------------
  longint now;
  bit     b_open [0:31][0:31]; int b_row [0:31][0:31];
  longint b_act [0:31][0:31], b_pre [0:31][0:31], b_rd [0:31][0:31], b_ref_end [0:31][0:31];
  longint p_last_act [0:31], p_last_rd [0:31], p_last_ref [0:31], p_last_refpb_any [0:31];
  longint p_act_bg [0:31][0:3], p_rd_bg [0:31][0:3], p_faw [0:31][0:3];
  bit [31:0] p_round [0:31];
  longint viol = 0, n_act = 0, n_pre = 0, n_rd = 0, n_ref = 0, n_preall = 0, max_ref_gap = 0;
  task automatic v(input string what, input integer pc, input integer bk);
    if (viol < 20) $display("VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
    viol++;
  endtask
  // return pipeline: per PC FIFO of (due cycle, data)
  longint rq_due [0:31][$]; bit [255:0] rq_dat [0:31][$];
  // consumer landing FIFOs
  bit [255:0] land [0:31][$];

  integer layer_go [0:LAYERS-1]; longint layer_first [0:LAYERS-1], layer_last [0:LAYERS-1];
  longint cyc = 0; integer cur = -1;          // layer being consumed
  integer pos = 0;                            // stream sector within the layer
  longint bad = 0, good = 0;
  integer posted = 0, launched = 0;
  integer max_land = 0;

  function automatic integer go_cycle(input integer L);
    go_cycle = 64 + int'((longint'(L) * PERIOD_PS + CYC / 2) / CYC);
  endfunction

  always @(posedge clk) if (rst_n) begin
    now = cyc * CYC;
    // ---------- commands issued this cycle (sampled before the edge) ----------
    for (int p = 0; p < 32; p++) begin
      if (row_v[p]) begin
        automatic int op = row_op[p*3 +: 3], bk = row_bank[p*5 +: 5], rw = row_row[p*19 +: 19], g = bk & 3;
        case (op)
          1: begin // ACT
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
          0: begin // PRE
            n_pre++;
            if (!b_open[p][bk]) v("PRE closed bank", p, bk);
            if (now < b_act[p][bk] + RAS) v("tRAS", p, bk);
            if (now < b_rd[p][bk] + RTP) v("tRTP", p, bk);
            b_open[p][bk] = 0; b_pre[p][bk] = now;
          end
          5: begin // PREab
            n_preall++;
            for (int b = 0; b < 32; b++) if (b_open[p][b]) begin
              if (now < b_act[p][b] + RAS) v("tRAS (PREab)", p, b);
              if (now < b_rd[p][b] + RTP) v("tRTP (PREab)", p, b);
              b_open[p][b] = 0; b_pre[p][b] = now;
            end
          end
          4: begin // REFab
            n_ref++;
            for (int b = 0; b < 32; b++) begin
              if (b_open[p][b]) v("REFab with open bank", p, b);
              if (now < b_pre[p][b] + RP) v("tRP (REFab)", p, b);
              if (now < b_ref_end[p][b]) v("REFab during refresh", p, b);
              b_ref_end[p][b] = now + RFC;
            end
            if (now - p_last_ref[p] > REFI) v("REFab late", p, 0);
            if (now - p_last_ref[p] > max_ref_gap) max_ref_gap = now - p_last_ref[p];
            p_last_ref[p] = now;
          end
          6: begin // REFpb
            n_ref++;
            if (b_open[p][bk]) v("REFpb to open bank", p, bk);
            if (now < b_pre[p][bk] + RP) v("tRP (REFpb)", p, bk);
            if (now < b_act[p][bk] + RAS + RP) v("tRC (REFpb)", p, bk);
            if (now < b_ref_end[p][bk]) v("REFpb during refresh", p, bk);
            if (now < p_last_act[p] + RREFD) v("tRREFD (REFpb after ACT)", p, bk);
            if (now < p_last_refpb_any[p] + RREFD) v("tRREFD (REFpb after REFpb)", p, bk);
            if (p_round[p][bk]) v("REFpb bank twice in one round", p, bk);
            p_round[p][bk] = 1; if (&p_round[p]) p_round[p] = 0;
            if (now - p_last_ref[p] > REFI / 32 - (MUT == 3 ? 2000 : 0)) v("REFpb late", p, bk);
            if (now - p_last_ref[p] > max_ref_gap) max_ref_gap = now - p_last_ref[p];
            p_last_ref[p] = now; p_last_refpb_any[p] = now;
            b_ref_end[p][bk] = now + RFCPB;
          end
          default: v("unknown row op", p, bk);
        endcase
      end
      // a refresh may never be overdue (strict schedule), checked every cycle
      if (now - p_last_ref[p] > (REF_MODE ? REFI / 32 : REFI)) begin
        v("refresh overdue", p, 0); p_last_ref[p] = now;
      end
      if (col_v[p]) begin
        automatic int bk = col_bank[p*5 +: 5], cl = col_col[p*5 +: 5], g = bk & 3;
        n_rd++;
        if (!b_open[p][bk]) v("RD closed bank", p, bk);
        if (now < b_act[p][bk] + RCD + (MUT == 1 ? 1000 : 0)) v("tRCD", p, bk);
        if (now < p_last_rd[p] + BURST) v("tCCD_S", p, bk);
        if (now < p_rd_bg[p][g] + TCCDL) v("tCCD_L", p, bk);
        if (now < b_ref_end[p][bk]) v("RD during refresh", p, bk);
        p_last_rd[p] = now; p_rd_bg[p][g] = now; b_rd[p][bk] = now;
        rq_due[p].push_back((now + CL + BURST + RSP + CYC - 1) / CYC);
        rq_dat[p].push_back(mem[midx(p, bk, b_row[p][bk], cl)]);
      end
    end
    for (int c = 0; c < 16; c++) if (row_v[2*c] && row_v[2*c+1]) v("two row commands on one channel slot", 2*c, 0);
    // ---------- returns land ----------
    for (int p = 0; p < 32; p++)
      while (rq_due[p].size() != 0 && rq_due[p][0] <= cyc) begin
        land[p].push_back(rq_dat[p].pop_front()); void'(rq_due[p].pop_front());
        if (land[p].size() > CRED) v("landing FIFO overflow (credit)", p, 0);
        if (land[p].size() > max_land) max_land = land[p].size();
      end
    // ---------- in-order consumer ----------
    begin
      automatic int popped [0:31] = '{default: 0};
      automatic int taken = 0;
      while (cur >= 0 && cur < LAYERS && pos < 32 * NS && taken < 32) begin
        automatic int pc = (pos >> 2) & 31;
        if (popped[pc] >= 4 || land[pc].size() == 0) break;
        if (land[pc][0] !== src(cur, pos)) begin
          if (bad < 10) $display("DATA MISMATCH layer=%0d s=%0d", cur, pos);
          bad++;
        end else good++;
        void'(land[pc].pop_front()); popped[pc]++; taken++;
        if (pos == 0) layer_first[cur] = cyc;
        pos++;
        if (pos == 32 * NS) begin layer_last[cur] = cyc; cur++; pos = 0; end
      end
      for (int p = 0; p < 32; p++) cred_ret[p*3 +: 3] <= 3'(popped[p]);
    end
    // ---------- layer control: post (desc), then go ----------
    desc_v <= 0; go <= 0;
    if (posted < LAYERS && posted == launched && desc_r && !desc_v &&
        (B2B != 0 ? (posted == 0 || cur >= posted) : (cyc >= go_cycle(posted) - HINT))) begin
      desc_v <= 1; desc_row <= 19'(posted); posted <= posted + 1;
    end
    if (launched < posted && !desc_v) begin
      automatic longint tgo = (B2B != 0) ? cyc : go_cycle(launched);
      if (cyc >= tgo) begin
        go <= 1; layer_go[launched] = int'(cyc + 1); if (launched == 0) cur = 0; launched <= launched + 1;
      end
    end
    if (fault) begin $display("CONTROLLER FAULT at cycle %0d", cyc); $finish; end
    cyc <= cyc + 1;
    if (cur == LAYERS) begin : done
      longint worst = 0, sum = 0, worst_first = 0, best_first = 1 << 30, over = 0, need = 1165084;
      $display("RESULT ref_mode=%0d hint=%0d b2b=%0d phase=%0d cred=%0d layers=%0d", REF_MODE, HINT, B2B, PHASE, CRED, LAYERS);
      for (int L = 0; L < LAYERS; L++) begin
        automatic longint t = (layer_last[L] + 1 - layer_go[L]) * CYC;
        automatic longint f = (layer_first[L] - layer_go[L]) * CYC;
        $display("LAYER %0d go=%0d first_ps=%0d stream_ps=%0d data_ps=%0d", L, layer_go[L], f, t,
                 (layer_last[L] + 1 - layer_first[L]) * CYC);
        if (t > worst) worst = t; sum += t; if (t > need) over++;
        if (f > worst_first) worst_first = f; if (f < best_first) best_first = f;
      end
      $display("SUMMARY worst_stream_ps=%0d mean_stream_ps=%0d first_data_ps_min=%0d first_data_ps_max=%0d layers_over_need=%0d",
               worst, sum / LAYERS, best_first, worst_first, over);
      $display("SUMMARY bytes_per_layer=%0d worst_Bps=%0d mean_Bps=%0d", 32 * NS * 32,
               longint'(1048576.0 / (real'(worst) * 1e-12)), longint'(1048576.0 / (real'(sum) / LAYERS * 1e-12)));
      $display("SUMMARY sectors_good=%0d sectors_bad=%0d violations=%0d cmds ACT=%0d PRE=%0d PREab=%0d REF=%0d RD=%0d max_ref_gap_ps=%0d max_landing=%0d",
               good, bad, viol, n_act, n_pre, n_preall, n_ref, n_rd, max_ref_gap, max_land);
      $display("SUMMARY verdict=%s", (bad == 0 && viol == 0 && good == longint'(LAYERS) * 32 * NS) ? "PASS" : "FAIL");
      $finish;
    end
  end

  initial begin
    for (int L = 0; L < LAYERS; L++)
      for (int s = 0; s < 32 * NS; s++)
        mem[midx((s >> 2) & 31, ((s >> 12) & 7) * 4 + (s & 3), L, (s >> 7) & 31)] = src(L, s);
    if (MUT == 2) mem[midx(5, 9, LAYERS - 1, 17)][77] ^= 1'b1;
    for (int p = 0; p < 32; p++) begin
      p_last_act[p] = -1000000; p_last_rd[p] = -1000000;
      begin : ph
        automatic int P = REF_MODE ? 118 : 3808;                     // RTL refresh period (cycles)
        automatic int base = (PHASE + (p * P) / 32) % P;
        p_last_ref[p] = longint'(base + ((base + P + p) % 2)) * CYC;  // first due one period later
      end p_last_refpb_any[p] = -1000000;
      p_round[p] = 0;
      for (int g = 0; g < 4; g++) begin p_act_bg[p][g] = -1000000; p_rd_bg[p][g] = -1000000; p_faw[p][g] = -1000000; end
      for (int b = 0; b < 32; b++) begin
        b_open[p][b] = 0; b_act[p][b] = -1000000; b_pre[p][b] = -1000000; b_rd[p][b] = -1000000; b_ref_end[p][b] = 0;
      end
    end
    repeat (4) @(posedge clk);
    rst_n = 1;
  end
endmodule

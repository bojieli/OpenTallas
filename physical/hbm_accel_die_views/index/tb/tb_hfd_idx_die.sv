`timescale 1ps/1fs
`default_nettype none
// CLAUDE hbm-indexer 2026-10-08: die-level exact bench of the real indexer: 4 x hfd_idx_score (one per HBM stack) +
// hfd_idx_sel, connected through LEG-stage relay chains (the die nets), driven by
//   * an svc model per stack (8 line ports, port p sends lines p, p+8, ... in order, random gaps, 2^FA credits each),
//   * a VM model (FP32 query blocks, 4 credits),
//   * keep-bitmap and frame-start sources,
// and sinking the top-k / candidate streams with credit return.  Every score beat of every stack, every top-k lane
// and every candidate lane is written out; tools/hbm_idx_die_bench.py compares them with the golden
// (tools/hdc_golden_v41.py Model.indexer / candidate_blocks / topk_lowest_index).
module tb_hfd_idx_die;
  parameter integer LEG = 24;          // relay stages per die net (each direction)
  parameter integer FA = 4;
  parameter integer KEYLEG = 0;       // service key data and credit return stages
  parameter integer LA = 6;
  parameter integer CRED = 64;
  parameter integer T = 1;             // scorer blocks a stack (1: one L16 block; 4: four L4 column taps)
  localparam integer L = 16 / T, NP = L / 2, SW = 38 * L + 2, NB_ = 4 * T;
  reg ck = 1'b0;
  always #416 ck = ~ck;                 // 832 ps (1.2 GHz)
  reg rst = 1'b0;
  integer cyc = 0;
  always @(posedge ck) cyc <= cyc + 1;
  // ------------------------------------------------------------------ DUT
  wire [4*571-1:0] qo;
  wire [570:0] qx [0:NB_-1];
  wire [570:0] qi [0:NB_-1];
  wire [SW-1:0] so [0:NB_-1];
  wire [NB_*SW-1:0] si;
  wire [NB_-1:0] sc, sco;
  wire [3:0] stq [0:NB_-1];
  reg  [89:0] fs = 90'd0;
  reg  [1047:0] qb = 1048'd0;
  wire qbr;
  reg  [344:0] kin = 345'd0;
  wire [611:0] to; wire [71:0] co;
  reg toc = 1'b0, coc = 1'b0;
  wire [1:0] ev;
  reg [8*1099-1:0] ik [0:3];            // the stack's 8 line ports (port p: lines p, p+8, ...)
  wire [7:0] ikc [0:3];
  genvar g;
  generate for (g = 0; g < NB_; g = g + 1) begin : gs
    localparam integer QQ = g / T, TT = g % T;
    wire [NP-1:0] ikc_;
    wire [NP*1099-1:0] ik_delayed;
    for (genvar kp = 0; kp < NP; kp = kp + 1) begin : key_leg
      wire [1097:0] kd;
      wire kv, kc;
      wire [0:0] unused_credit_data;
      hfd_idx_pipe #(.W(1098), .N(KEYLEG)) u_key (.ck(ck), .rst_n(rst),
        .v(ik[QQ][(TT*NP+kp)*1099]), .d(ik[QQ][(TT*NP+kp)*1099+1 +: 1098]), .qv(kv), .q(kd));
      assign ik_delayed[kp*1099 +: 1099] = {kd, kv};
      hfd_idx_pipe #(.W(1), .N(KEYLEG)) u_credit (.ck(ck), .rst_n(rst),
        .v(ikc_[kp]), .d(1'b0), .qv(kc), .q(unused_credit_data));
      assign ikc[QQ][TT*NP+kp] = kc;
    end
    hfd_idx_score #(.FA(FA), .CRED(CRED), .L(L), .LANE0(TT * L)) u_s (.ck(ck), .rst(rst), .ik(ik_delayed),
      .ikf({NP{1'b0}}), .ikc(ikc_), .q(qi[g]), .qx(qx[g]), .s(so[g]), .sc(sco[g]), .st(stq[g]));
    // die nets: q bus out, score beats back, credits back (LEG relay stages each)
    wire qv_, sv_, cv_; wire [569:0] qd_; wire [SW-2:0] sd_;
    // q bus: the stack's first block over the LEG-stage die net, each further column tap from the previous tap's qx
    // over a 2-stage hop
    if (TT == 0) begin : gq0
      hfd_idx_pipe #(.W(570), .N(LEG)) u_pq (.ck(ck), .rst_n(rst), .v(qo[QQ*571]), .d(qo[QQ*571+1 +: 570]), .qv(qv_),
        .q(qd_));
    end else begin : gqn
      hfd_idx_pipe #(.W(570), .N(2)) u_pq (.ck(ck), .rst_n(rst), .v(qx[g-1][0]), .d(qx[g-1][570:1]), .qv(qv_), .q(qd_));
    end
    assign qi[g] = {qd_, qv_};
    hfd_idx_pipe #(.W(SW-1), .N(LEG)) u_ps (.ck(ck), .rst_n(rst), .v(so[g][0]), .d(so[g][SW-1:1]), .qv(sv_), .q(sd_));
    assign si[g*SW +: SW] = {sd_, sv_};
    wire [0:0] cd_unused;
    hfd_idx_pipe #(.W(1), .N(LEG)) u_pc (.ck(ck), .rst_n(rst), .v(sc[g]), .d(1'b0), .qv(cv_), .q(cd_unused));
    assign sco[g] = cv_;
  end endgenerate
  hfd_idx_sel #(.T(T), .LA(LA)) u_x (.ck(ck), .rst(rst), .fs(fs), .qb(qb), .qbr(qbr), .kin(kin), .qo(qo), .si(si), .sc(sc),
    .to(to), .toc(toc), .co(co), .coc(coc), .ev(ev));
  // ------------------------------------------------------------------ stimulus memories
  localparam integer MAXL = 40000, MAXQ = 1024;
  reg [1087:0] lines [0:MAXL-1];
  reg [1046:0] qblk [0:MAXQ-1];
  reg [341:0] keepm [0:63];
  integer nframes, fr, q, p;
  integer f_ndie [0:15], f_rank [0:15], f_pos [0:15], f_cand [0:15], f_keep [0:15], f_k [0:15], f_expfault [0:15];
  integer f_loff [0:15][0:3], f_nl [0:15][0:3], f_qoff [0:15];
  integer seed, gap16, fd_s, fd_t, fd_c, fd_f, rc;
  integer sent [0:3][0:7], cred [0:3][0:7];
  integer qsent, qcred;
  reg run_lines, run_q;
  integer t0, t_done, t_first_score, t_last_score;
  reg [31:0] lfsr = 32'h1;
  function automatic bit rnd_gap(input integer sixteenths);
    lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
    return (lfsr[3:0] < sixteenths[3:0]);
  endfunction
  // svc line model
  always @(posedge ck) begin
    for (q = 0; q < 4; q = q + 1) for (p = 0; p < 8; p = p + 1) begin
      if (ikc[q][p]) cred[q][p] = cred[q][p] + 1;
      ik[q][p*1099] <= 1'b0;
      if (run_lines && sent[q][p] * 8 + p < f_nl[fr][q] && cred[q][p] > 0 && !rnd_gap(gap16)) begin
        ik[q][p*1099] <= 1'b1;
        ik[q][p*1099+1 +: 10] <= 10'(sent[q][p] * 8 + p);
        ik[q][p*1099+11 +: 1088] <= lines[f_loff[fr][q] + sent[q][p] * 8 + p];
        sent[q][p] = sent[q][p] + 1; cred[q][p] = cred[q][p] - 1;
      end
    end
  end
  // VM query model
  always @(posedge ck) begin
    if (qbr) qcred = qcred + 1;
    qb[0] <= 1'b0;
    if (run_q && qsent < 128 && qcred > 0 && !rnd_gap(gap16)) begin
      qb <= {qblk[f_qoff[fr] + qsent], 1'b1};
      qsent = qsent + 1; qcred = qcred - 1;
    end
  end
  // sinks (credit return after a registered cycle) and monitors
  integer z, lanes_t, lanes_c;
  always @(posedge ck) begin
    toc <= to[0]; coc <= co[0];
    // to = {idx20 x16 [611:292], val16 x16 [291:36], ninf16 [35:20], lv16 [19:4], q2 [3:2], last [1], v [0]}
    if (to[0]) for (z = 0; z < 16; z = z + 1) if (to[4 + z])
      $fdisplay(fd_t, "%0d %0d %04h %0d", fr, to[292 + 20*z +: 20], to[36 + 16*z +: 16], to[20 + z]);
    if (co[0]) for (z = 0; z < 2; z = z + 1) if (co[4 + z])
      $fdisplay(fd_c, "%0d %0d %04h", fr, co[38 + 17*z +: 17], co[6 + 16*z +: 16]);
    // score beat {idx20 x L, score16 x L, kv L, fault L, last, v}
    for (q = 0; q < NB_; q = q + 1) if (so[q][0]) begin
      if (t_first_score < 0) t_first_score = cyc;
      t_last_score = cyc;
      for (z = 0; z < L; z = z + 1) if (so[q][2 + L + z])
        $fdisplay(fd_s, "%0d %0d %04h %0d", fr, so[q][2 + 18*L + 20*z +: 20], so[q][2 + 2*L + 16*z +: 16], so[q][2 + z]);
    end
  end
  // ------------------------------------------------------------------ frame sequencer
  string dir, odir;
  integer fl;
  initial begin
    if (!$value$plusargs("DIR=%s", dir)) dir = ".";
    if (!$value$plusargs("ODIR=%s", odir)) odir = ".";
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("GAP=%d", gap16)) gap16 = 3;
    lfsr = 32'(seed) | 32'h1;
    $readmemh({dir, "/lines.mem"}, lines);
    $readmemh({dir, "/qblk.mem"}, qblk);
    $readmemh({dir, "/keep.mem"}, keepm);
    fl = $fopen({dir, "/frames.txt"}, "r");
    rc = $fscanf(fl, "%d", nframes);
    for (fr = 0; fr < nframes; fr = fr + 1) begin
      rc = $fscanf(fl, "%d %d %d %d %d %d %d %d", f_ndie[fr], f_rank[fr], f_pos[fr], f_cand[fr], f_keep[fr], f_k[fr],
                   f_qoff[fr], f_expfault[fr]);
      for (q = 0; q < 4; q = q + 1) rc = $fscanf(fl, "%d %d", f_loff[fr][q], f_nl[fr][q]);
    end
    $fclose(fl);
    fd_s = $fopen({odir, "/out_scores.txt"}, "w"); fd_t = $fopen({odir, "/out_topk.txt"}, "w");
    fd_c = $fopen({odir, "/out_cand.txt"}, "w"); fd_f = $fopen({odir, "/out_frames.txt"}, "w");
    for (q = 0; q < 4; q = q + 1) for (p = 0; p < 8; p = p + 1) begin sent[q][p] = 0; cred[q][p] = 1 << FA; end
    run_lines = 0; run_q = 0; qcred = 4; fr = 0;
    repeat (4) @(negedge ck);
    rst = 1'b1;
    repeat (8) @(negedge ck);
    for (fr = 0; fr < nframes; fr = fr + 1) begin
      for (q = 0; q < 4; q = q + 1) for (p = 0; p < 8; p = p + 1) sent[q][p] = 0;
      qsent = 0; t_first_score = -1; t_last_score = -1;
      if (f_keep[fr]) for (q = 0; q < 4; q = q + 1) begin
        kin = {keepm[fr * 4 + q], 2'(q), 1'b1}; @(negedge ck); kin[0] = 1'b0;
        repeat (3) @(negedge ck);
      end
      fs = {1'(f_keep[fr]), 1'(f_cand[fr]), 10'(f_k[fr]), 14'(f_ndie[fr]), 7'(f_rank[fr]), 20'(f_pos[fr]), 4'(fr),
            32'h1d0 + 32'(fr), 1'b1};
      t0 = cyc;
      @(negedge ck); fs[0] = 1'b0;
      run_lines = 1; run_q = 1;
      t_done = -1;
      while (t_done < 0 && cyc - t0 < 200000) begin
        @(negedge ck);
        if (ev[0]) t_done = cyc;
        if (ev[1] && f_expfault[fr]) t_done = cyc;
      end
      run_lines = 0; run_q = 0;
      $fdisplay(fd_f, "%0d done=%0d fault=%0d cycles=%0d first_score=%0d last_score=%0d", fr, t_done >= 0, ev[1],
                t_done - t0, t_first_score - t0, t_last_score - t0);
      $display("HBMIDX_FRAME %0d done=%0d fault=%0d cycles=%0d first_score=%0d last_score=%0d", fr, t_done >= 0, ev[1],
               t_done - t0, t_first_score - t0, t_last_score - t0);
      repeat (20) @(negedge ck);
      if (f_expfault[fr]) break;
    end
    $fclose(fd_s); $fclose(fd_t); $fclose(fd_c); $fclose(fd_f);
    $display("HBMIDX_END frames=%0d", nframes);
    $finish;
  end
endmodule
`default_nettype wire

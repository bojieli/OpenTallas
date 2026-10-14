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
module tb_hbm_idx_parent_cut_native;
  parameter integer LEG = 24;          // relay stages per die net (each direction)
  parameter integer FA = 6;
  parameter integer KEYLEG = 0;       // service key data and credit return stages
  parameter integer LA = 7;
  parameter integer CRED = 128;
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
  wire [35167:0] ikflat;
  wire [31:0] ikcflat;
  wire [15:0] status;
  wire co_quarter_last;
  for(genvar s=0;s<4;s=s+1) begin:gobserve
   assign ikflat[s*8792+:8792]=ik[s];
   assign ikc[s]=ikcflat[s*8+:8];
   assign so[s]=si[s*610+:610];
  end
  ot_hbm_idx_parent_cut_native dut(
   .clk_score({4{ck}}),.clk_line({32{ck}}),.clk_line_mem({96{ck}}),
   .clk_query(ck),.clk_quant(ck),.clk_quant_delay(ck),.clk_query_bank({4{ck}}),
   .clk_top(ck),.clk_top_ctl(ck),.clk_top_slice({4{ck}}),.clk_top_hist({8{ck}}),.clk_top_pack({8{ck}}),.clk_top_search({2{ck}}),
   .clk_score_fifo({4{ck}}),.clk_score_mem({12{ck}}),.clk_top_mem({12{ck}}),.clk_selector(ck),.clk_ordered(ck),
   .clk_engine({16{ck}}),.clk_meta({16{ck}}),.clk_tail({16{ck}}),
   .clk_chunk({64{ck}}),.clk_hslice({2048{ck}}),.rst_n(rst),
   .ik(ikflat),.ikc(ikcflat),.fs(fs),.qb(qb),.qbr(qbr),.kin(kin),
   .to(to),.toc(toc),.co(co),.coc(coc),.ev(ev),
   .co_quarter_last(co_quarter_last),.score_observe(si),.status(status));
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
  // hgi-1010/g2: every always block loops over its OWN variables.  The module-level q / p are the frame sequencer's;
  // the svc model and the score recorder used to share q, so at every clock edge they left q = 4 / NB_ under the
  // sequencer's keep loop (which waits on clock edges): only stack 0 ever got its keep bitmap (F1 keep frame: stacks
  // 1..3 scored every key -inf, 2,624 of 10,928 keys wrong).
  integer qs, ps;
  always @(posedge ck) begin
    for (qs = 0; qs < 4; qs = qs + 1) for (ps = 0; ps < 8; ps = ps + 1) begin
      if (ikc[qs][ps]) cred[qs][ps] = cred[qs][ps] + 1;
      ik[qs][ps*1099] <= 1'b0;
      if (run_lines && sent[qs][ps] * 8 + ps < f_nl[fr][qs] && cred[qs][ps] > 0 && !rnd_gap(gap16)) begin
        ik[qs][ps*1099] <= 1'b1;
        ik[qs][ps*1099+1 +: 10] <= 10'(sent[qs][ps] * 8 + ps);
        ik[qs][ps*1099+11 +: 1088] <= lines[f_loff[fr][qs] + sent[qs][ps] * 8 + ps];
        sent[qs][ps] = sent[qs][ps] + 1; cred[qs][ps] = cred[qs][ps] - 1;
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
  integer z, lanes_t, lanes_c, qr;
  always @(posedge ck) begin
    toc <= to[0]; coc <= co[0];
    // to = {idx20 x16 [611:292], val16 x16 [291:36], ninf16 [35:20], lv16 [19:4], q2 [3:2], last [1], v [0]}
    if (to[0]) for (z = 0; z < 16; z = z + 1) if (to[4 + z])
      $fdisplay(fd_t, "%0d %0d %04h %0d", fr, to[292 + 20*z +: 20], to[36 + 16*z +: 16], to[20 + z]);
    if (co[0]) for (z = 0; z < 2; z = z + 1) if (co[4 + z])
      $fdisplay(fd_c, "%0d %0d %04h", fr, co[38 + 17*z +: 17], co[6 + 16*z +: 16]);
    // score beat {idx20 x L, score16 x L, kv L, fault L, last, v}
    for (qr = 0; qr < NB_; qr = qr + 1) if (so[qr][0]) begin
      if (t_first_score < 0) t_first_score = cyc;
      t_last_score = cyc;
      for (z = 0; z < L; z = z + 1) if (so[qr][2 + L + z])
        $fdisplay(fd_s, "%0d %0d %04h %0d", fr, so[qr][2 + 18*L + 20*z +: 20], so[qr][2 + 2*L + 16*z +: 16], so[qr][2 + z]);
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

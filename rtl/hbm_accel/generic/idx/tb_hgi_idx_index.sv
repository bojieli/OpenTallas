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
// hgi-takeover 2026-10-09: tb_hfd_idx_die with the frame driven by an IDX.INDEX RECORD through ot_hgi_idx_unit /
// ot_hgi_idx_index (spec G18): A (query), B (head weights), C (keep bitmap) staged in a VM model, O / R / D read back
// from the VM after each frame and written in the bench's out_topk / out_cand format, so tools/hbm_idx_die_bench.py
// compare checks them against the same golden.  MUT 2: head weight of the next head; MUT 3: R from the wrong lane.
module tb_hgi_idx_index;
  parameter integer MUT = 0;
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
  wire [89:0] fs;
  wire [1047:0] qb;
  wire qbr;
  wire [344:0] kin;
  wire [611:0] to; wire [71:0] co;
  wire toc, coc;
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
  // ---- the IDX unit (record -> frame adapter) and its VM model (one request outstanding, 2..6 cycles)
  reg [1818:0] rec = 0; wire [2:0] uret; wire [337:0] vmq; reg [273:0] vmr = 0;
  ot_hgi_idx_unit #(.MUT(MUT)) u_unit (.clk(ck), .rst_n(rst), .rec(rec), .ret(uret), .vmq(vmq), .vmr(vmr),
    .sel_fs(fs), .sel_qb(qb), .sel_qbr(qbr), .sel_kin(kin), .sel_to(to), .sel_toc(toc), .sel_co(co), .sel_coc(coc),
    .sel_ev(ev));
  // VM model (fast path): up to 4 requests outstanding, pipelined (6..8 cycles, never before the predecessor), in order
  reg [31:0] vm [0:262143];
  reg [337:0] vqq [0:7]; integer vqt [0:7]; integer qh2 = 0, qn2 = 0, maxo2 = 0, tnow = 0, tlast = 0;
  always @(posedge ck) begin
    tnow = tnow + 1;
    vmr[273] <= 1'b0;
    if (qn2 > 0 && vqt[qh2 % 8] <= tnow) begin : serve
      reg [337:0] vq; vq = vqq[qh2 % 8]; qh2 = qh2 + 1; qn2 = qn2 - 1;
      for (integer w = 0; w < 8; w = w + 1) begin
        if (vq[336] && &vq[16 + 4*w +: 4]) vm[{vq[323:309], 3'(w)}] = vq[48 + 32*w +: 32];
        vmr[32*w +: 32] <= vq[336] ? 32'd0 : vm[{vq[323:309], 3'(w)}];
      end
      vmr[256] <= vq[336]; vmr[272:257] <= vq[15:0]; vmr[273] <= 1'b1;
    end
    if (vmq[337]) begin
      if (qn2 >= 4) $fatal(1, "VM: more than 4 outstanding");
      vqq[(qh2 + qn2) % 8] = vmq;
      tlast = (tnow + 6 + ($urandom % 3) > tlast + 1) ? tnow + 6 + ($urandom % 3) : tlast + 1;
      vqt[(qh2 + qn2) % 8] = tlast; qn2 = qn2 + 1; if (qn2 > maxo2) maxo2 = qn2;
    end
  end
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
  
  reg run_lines;
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
  // sinks (credit return after a registered cycle) and monitors
  integer z, lanes_t, lanes_c, ufault, ncand;
  function automatic [255:0] md(input [2:0] fmt, input [39:0] base_, input [19:0] n_, input [19:0] m_, input [31:0] str_);
    begin md = 256'd0; md[1:0] = 2'd1; md[4:2] = fmt; md[47:8] = base_; md[67:48] = n_; md[87:68] = m_; md[119:88] = str_; end
  endfunction
  always @(posedge ck) begin
    // to = {idx20 x16 [611:292], val16 x16 [291:36], ninf16 [35:20], lv16 [19:4], q2 [3:2], last [1], v [0]}
    if (to[0]) for (z = 0; z < 16; z = z + 1) if (to[4 + z]) lanes_t = lanes_t + 1;
    if (co[0]) for (z = 0; z < 2; z = z + 1) if (co[4 + z]) lanes_c = lanes_c + 1;
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
    run_lines = 0; fr = 0;
    repeat (4) @(negedge ck);
    rst = 1'b1;
    repeat (8) @(negedge ck);
    for (fr = 0; fr < nframes; fr = fr + 1) begin
      for (q = 0; q < 4; q = q + 1) for (p = 0; p < 8; p = p + 1) sent[q][p] = 0;
      t_first_score = -1; t_last_score = -1;
      // stage A / B / C in the VM, then send the IDX.INDEX record
      for (q = 0; q < 128; q = q + 1) for (p = 0; p < 32; p = p + 1) vm[18'h01000 + 32*q + p] = qblk[f_qoff[fr] + q][7 + 32*p +: 32];
      for (q = 0; q < 32; q = q + 1) vm[18'h02000 + q] = {qblk[f_qoff[fr] + 4*q][1046:1031], 16'd0};
      // G18a: C = the layer-20 candidate table [block ids | values]: every kept owned block listed with a finite value,
      // plus decoys the engine must ignore (other ranks' blocks; own blocks at -inf)
      ncand = 0;
      if (f_keep[fr]) for (q = 0; q < 4; q = q + 1) for (p = 0; p < 342; p = p + 1) begin
        if (keepm[fr * 4 + q][p] && ncand < 2040) begin
          vm[18'h06000 + ncand] = 96 * (342 * q + p) + f_rank[fr]; vm[18'h07000 + ncand] = 32'h3F80_0000 + p; ncand = ncand + 1;
        end else if ((p % 97) == 5 && ncand < 2040) begin
          vm[18'h06000 + ncand] = 96 * (342 * q + p) + f_rank[fr]; vm[18'h07000 + ncand] = 32'hFF80_0000; ncand = ncand + 1;
        end else if ((p % 89) == 7 && ncand < 2040) begin
          vm[18'h06000 + ncand] = 96 * (342 * q + p) + ((f_rank[fr] + 1) % 96); vm[18'h07000 + ncand] = 32'h4000_0000; ncand = ncand + 1;
        end
      end
      for (q = 0; q < 8192; q = q + 1) vm[18'h03000 + q] = 32'hDEADBEEF;
      lanes_t = 0; lanes_c = 0;
      begin : mkrec
        reg [127:0] h; h = 0; h[127:124] = 4'd9; h[123:118] = 6'd0;
        h[99:93] = {2'b01, 1'b1, 1'(f_cand[fr]), 1'(f_keep[fr]), 2'b11};          // R O D C B A
        h[88:64] = {11'd0, 1'(f_keep[fr]), 1'(f_cand[fr]), 12'(f_k[fr])}; h[63:32] = 32'(f_ndie[fr]); h[31:0] = 32'd20;
        rec = {8'(f_rank[fr]), 20'(f_pos[fr]), 21'd512, 21'd512, 21'd4096, 21'(ncand == 0 ? 1 : ncand), 21'd32, 21'd4096,
               md(3'd0, 40'h04000, 20'd512, 20'd1, 32'd0), md(3'd5, 40'h03000, 20'd512, 20'd1, 32'd0),
               md(3'd0, 40'h05000, 20'd2048, 20'd2, 32'd4096), md(3'd5, 40'h06000, 20'(ncand == 0 ? 1 : ncand), 20'd2, 32'd4096),
               md(3'd0, 40'h02000, 20'd32, 20'd1, 32'd0), md(3'd0, 40'h01000, 20'd4096, 20'd1, 32'd0), h, 1'b1};
      end
      @(negedge ck); rec[0] = 1'b0;
      t0 = cyc;
      run_lines = 1;
      t_done = -1; ufault = 0;
      while (t_done < 0 && cyc - t0 < 200000) begin
        @(negedge ck);
        if (uret[1]) t_done = cyc;
        if (uret[2]) begin t_done = cyc; ufault = 1; end
      end
      run_lines = 0;
      // read the results back from the VM in the bench's output format
      for (q = 0; q < lanes_t; q = q + 1)
        $fdisplay(fd_t, "%0d %0d %04h %0d", fr, vm[18'h03000 + q], vm[18'h04000 + q][31:16], vm[18'h04000 + q] == 32'hFF800000);
      if (f_cand[fr]) for (q = 0; q < lanes_c; q = q + 1)
        $fdisplay(fd_c, "%0d %0d %04h", fr, vm[18'h05000 + q], vm[18'h05000 + 4096 + q][31:16]);
      $fdisplay(fd_f, "%0d done=%0d fault=%0d cycles=%0d first_score=%0d last_score=%0d", fr, t_done >= 0 && !ufault, ufault,
                t_done - t0, t_first_score - t0, t_last_score - t0);
      $display("HGIIDX_FRAME %0d done=%0d fault=%0d cycles=%0d first_score=%0d last_score=%0d", fr, t_done >= 0 && !ufault, ufault,
               t_done - t0, t_first_score - t0, t_last_score - t0);
      repeat (20) @(negedge ck);
      if (f_expfault[fr]) break;
    end
    $fclose(fd_s); $fclose(fd_t); $fclose(fd_c); $fclose(fd_f);
    $display("HGIIDX_END frames=%0d", nframes);
    $finish;
  end
endmodule
`default_nettype wire

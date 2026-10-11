// [svc-ep] 2026-10-10: native driver + scoreboard for the PS native endpoint on the REAL generated segments (--nep), included
// by tb_svc_ps_body.svh (ifdef NEP) after the legacy / PS-stream body, which keeps running on the same PCs.  The driver is the
// loader kport's die-side protocol on lq / lr (ot_hfd_loader_kport field order; NO 16 transactions issued-not-consumed, NQ 4
// request credits, RB 64 response sectors reserved at issue; writes one sector a packet against WQ 16 credits returned by
// WR_G (lr[291:284], Gray count of writes popped into their PC queue); a read is admitted only when no write is unpopped)
// through N_CH register stages each way (the die's lq / lr station hops).
//   phase 1  random mix while the legacy traffic runs: writes and reads (bursts 1..4 inside one row, multi-outstanding)
//            over 16 hot rows -- every beat exact, in issue order, read-after-write per PC (expected = the model at issue)
//   phase 2  READ RATE: 256 one-row reads (4 sectors) on consecutive rows, as fast as the protocol allows (legacy idle)
//   phase 3  WRITE RATE: 512 sequential sectors, one packet a cycle when a credit is free
//   phase 4  read-back of phase 3 (landing + data)
// NXL (tb top) = extra PHY cycles on native requests (the RTT knob).  Reports NEP_RATE / NEP_WRATE lines.
  localparam integer N_NO = 16, N_NQ = 4, N_RB = 64, N_WQ = 16, N_CH = 13;
  reg [349:0] lqs [0:N_CH]; reg [292:0] lrs [1:N_CH]; wire [293:0] lr_w; wire [292:0] lr0 = lr_w[292:0];
  wire [350:0] lq_w = {ck, lqs[N_CH]};
  integer ci_;
  initial for (ci_ = 0; ci_ <= N_CH; ci_ = ci_ + 1) begin lqs[ci_] = 350'd0; if (ci_ > 0) lrs[ci_] = 293'd0; end
  always @(posedge ck) begin : chn
    integer i;
    for (i = N_CH; i > 0; i = i - 1) lqs[i] <= lqs[i-1];
    lrs[1] <= lr0;
    for (i = N_CH; i > 1; i = i - 1) lrs[i] <= lrs[i-1];
  end
  // expected beats (in issue order)
  reg [4:0] e_pc [0:8191]; reg [15:0] e_tg [0:8191]; reg [3:0] e_bt [0:8191]; reg [255:0] e_dt [0:8191]; reg e_last [0:8191];
  reg [2:0] e_ln [0:8191];
  integer eh = 0, et = 0;
  reg [255:0] mm [bit [29:0]];
  integer nmode = 0, ncred = N_NQ, infl = 0, rbres = 0, sent_w = 0, popped = 0, nops = 0, nbeats = 0, nerr0 = 0;
  reg [7:0] wb_prev = 8'd0;
  integer t_first = -1, t_rsp1 = -1, t_last = 0, rr_n = 0, w_first = -1, w_last = 0, w_land0 = 0, w_landt = 0, cyc = 0;
  integer f_reads = 0, f_writes = 0, f_bursts = 0, max_infl = 0, wr_base0 = 0, wr_land_t = -1;
  reg [29:0] hot [0:15];
  reg nep_done = 1'b0;
  reg f_have = 1'b0, f_wr; integer f_h, f_s0, f_L, raw_seen = 0;
  function automatic [7:0] g2b(input [7:0] g);
    integer i; begin g2b[7] = g[7]; for (i = 6; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i]; end
  endfunction
  function automatic [29:0] rowadr(input integer j);     // row j of a region: 4 aligned sectors, PCs spread by kport_map
    rowadr = 30'h0100_0000 + 30'(j * 4);
  endfunction
  wire legacy_done = ne >= 48 && ps_n >= PS_N && !ps_busy && ps_cr_out == 0 && done_lines == want_lines &&
                     kv_got == kv_want && ik_got == ik_want && sent[0] + sent[1] + sent[2] + sent[3] + sent[4] + sent[5] +
                     sent[6] + sent[7] == 8 * NREQ;
  task automatic issue_read(input [29:0] a, input integer L, inout reg [349:0] w);
    integer b; reg [15:0] tg;
    begin
      tg = 16'(nops);
      w[292] = 1'b1; w[297:293] = owner(a); w[327:298] = a; w[343:328] = tg; w[349:346] = 4'(L);
      for (b = 0; b < L; b = b + 1) begin
        e_pc[et % 8192] = owner(a); e_tg[et % 8192] = tg; e_bt[et % 8192] = 4'(b); e_last[et % 8192] = (b == L - 1);
        e_ln[et % 8192] = 3'(L);
        e_dt[et % 8192] = mm.exists(a + 30'(b)) ? mm[a + 30'(b)] : g0(a + 30'(b)); et = et + 1;
      end
      ncred = ncred - 1; infl = infl + 1; rbres = rbres + L; nops = nops + 1; f_reads = f_reads + 1; if (L > 1) f_bursts = f_bursts + 1;
      if (infl > max_infl) max_infl = infl;
    end
  endtask
  task automatic issue_write(input [29:0] a, input [255:0] d, inout reg [349:0] w);
    begin
      w[0] = 1'b1; w[5:1] = owner(a); w[35:6] = a; w[291:36] = d;
      mm[a] = d; sent_w = sent_w + 1; nops = nops + 1; f_writes = f_writes + 1;
    end
  endtask
  integer k_;
  initial for (k_ = 0; k_ < 16; k_ = k_ + 1) hot[k_] = {$urandom} & 30'h00ff_fffc;
  always @(posedge ck) if (rst && bench_ready && !nep_done) begin : drv
    reg [292:0] r; reg [349:0] w; integer unp, L, s0, h; reg rd_ok, wr_ok; reg [29:0] a;
    cyc = cyc + 1;
    r = lrs[N_CH];
    w = 350'd0; w[344] = 1'b1;
    if (r[0]) ncred = ncred + 1;
    if (r[283] || r[292]) begin if (nerr0 < 4) $display("ERR native fault bit lr[283] %0d lr[292] %0d", r[283], r[292]);
      nerr0 = nerr0 + 1; err = err + 1; end
    if (r[1]) begin
      if (eh == et) begin err = err + 1; $display("ERR native beat with nothing outstanding"); end
      else begin
        if (r[6:2] !== e_pc[eh % 8192] || r[22:7] !== e_tg[eh % 8192] || r[26:23] !== e_bt[eh % 8192] || r[282:27] !== e_dt[eh % 8192]) begin
          err = err + 1;
          if (nerr0 < 6) $display("ERR native beat %0d: pc %0d/%0d tag %h/%h beat %0d/%0d data %s", eh, r[6:2], e_pc[eh % 8192],
                                  r[22:7], e_tg[eh % 8192], r[26:23], e_bt[eh % 8192], r[282:27] === e_dt[eh % 8192] ? "ok" : "BAD");
          nerr0 = nerr0 + 1;
        end
        if (e_last[eh % 8192]) begin infl = infl - 1; rbres = rbres - e_ln[eh % 8192]; end
        eh = eh + 1; nbeats = nbeats + 1;
        if (nmode == 2) begin if (t_rsp1 < 0) t_rsp1 = cyc; t_last = cyc; rr_n = rr_n + 1; end
      end
    end
    popped = popped + 8'(g2b(r[291:284]) - wb_prev); wb_prev = g2b(r[291:284]);
    unp = sent_w - popped;
    rd_ok = ncred > 0 && infl < N_NO && unp == 0;
    wr_ok = unp < N_WQ;
    case (nmode)
      0: nmode = 1;
      1: begin   // functional mix (2,000 ops), random gaps
        // the next op is drawn once and HELD until the protocol admits it (a read waits for every write to pop: the
        // kport's RAW rule), so reads and writes interleave in runs and reads follow writes to the same rows
        if (nops < 2000 && !f_have && ($urandom % 3) != 0) begin
          f_have = 1'b1; f_wr = ($urandom % 8) < 3; f_h = $urandom % 16; f_s0 = $urandom % 4; f_L = 1 + ($urandom % (4 - f_s0));
        end
        if (f_have) begin
          if (f_wr && wr_ok) begin issue_write(hot[f_h] + 30'(f_s0), {$urandom, $urandom, $urandom, $urandom, $urandom,
                                                                     $urandom, $urandom, $urandom}, w); f_have = 1'b0; end
          else if (!f_wr && rd_ok && rbres + f_L <= N_RB) begin issue_read(hot[f_h] + 30'(f_s0), f_L, w); f_have = 1'b0;
            if (raw_seen < 1000000 && mm.exists(hot[f_h] + 30'(f_s0))) raw_seen = raw_seen + 1; end
        end
        if (nops >= 2000 && !f_have && eh == et && unp == 0 && legacy_done) begin nmode = 2; nops = 0; end
      end
      2: begin   // read rate: 256 rows
        if (nops < 256 && rd_ok && rbres + 4 <= N_RB) begin if (t_first < 0) t_first = cyc; issue_read(rowadr(nops), 4, w); end
        if (nops == 256 && eh == et) begin
          $display("NEP_RATE read sectors=%0d cycles=%0d rate=%0.3f B/cycle RTT=%0d cycles (NO %0d NQ %0d RB %0d CH %0d NXL %0d, max in flight %0d)",
                   rr_n, t_last - t_first + 1, 32.0 * rr_n / (t_last - t_first + 1), t_rsp1 - t_first, N_NO, N_NQ, N_RB, N_CH, NXL, max_infl);
          nmode = 3; nops = 0; wr_base0 = n_wr_land;
        end
      end
      3: begin   // write rate: 512 sequential sectors
        if (nops < 512 && wr_ok) begin if (w_first < 0) w_first = cyc;
          issue_write(30'h0200_0000 + 30'(nops), {8{$urandom}}, w); end
        if (n_wr_land - wr_base0 >= 512 && wr_land_t < 0) wr_land_t = cyc;
        if (nops == 512 && sent_w == popped && wr_land_t >= 0) begin
          w_last = cyc;
          $display("NEP_WRATE write sectors=512 cycles(popped)=%0d rate=%0.3f B/cycle; landed at the PHY in %0d cycles (%0.3f B/cycle) (WQ %0d CH %0d)",
                   w_last - w_first + 1, 32.0 * 512 / (w_last - w_first + 1), wr_land_t - w_first + 1,
                   32.0 * 512 / (wr_land_t - w_first + 1), N_WQ, N_CH);
          nmode = 4; nops = 0;
        end
      end
      4: begin   // read-back of the write-rate region
        if (nops < 128 && rd_ok && rbres + 4 <= N_RB) issue_read(30'h0200_0000 + 30'(4 * nops), 4, w);
        if (nops == 128 && eh == et) nmode = 5;
      end
      5: nep_done = 1'b1;
    endcase
    lqs[0] <= w;
  end
  task automatic nep_report;
    $display("NEP_BENCH native ops: reads %0d (bursts %0d, reads of written sectors %0d) writes %0d beats %0d, max in flight %0d, PHY landed writes %0d, landing errors %0d, mode %0d",
             f_reads, f_bursts, raw_seen, f_writes, nbeats, max_infl, n_wr_land, n_land_bad, nmode);
    if (raw_seen < 100) begin err = err + 1; $display("ERR native mix exercised only %0d reads of written sectors", raw_seen); end
    if (nmode != 5) begin err = err + 1; $display("ERR native driver incomplete (mode %0d, beats %0d/%0d)", nmode, eh, et); end
  endtask

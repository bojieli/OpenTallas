`timescale 1ns/1ps
// DIE-KV-64/RF-E 11-03: transaction co-sim, qkd_hr_ingest_eng__rf_core (= the face-recut core, gold) vs the
// rf_wrap'd qkd_hr_ingest_eng (reset relay + registered write face + held done).  Each DUT pulls the same host
// stream (descriptors / payload beats) on its own handshakes with independent random gaps and w_rdy back-pressure;
// the written (addr, data) sequences and the done (tag, count) sequences must be identical.  The wrapper is also
// checked for: done only after its last sector left the port; busy low with w_v low => every core write and done
// has left; done queue never overflows.
module tb;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n = 0;
  localparam integer NP = 4096;
  reg [511:0] prog_d [0:NP-1]; reg prog_c [0:NP-1];   // c: 0 descriptor, 1 payload
  integer np;
  // ---------------- source / sink per DUT
  reg [31:0] seed;
  integer pg = 0, pw = 0;                 // program pointers
  reg gv, ggap, wgap, grdy, wrdy; reg [7:0] wst = 0;
  wire g_drdy, g_inrdy, g_wv, g_dv, g_busy, w_drdy, w_inrdy, w_wv, w_dv, w_busy;
  wire [31:0] g_wa, w_wa, g_ns, w_ns, g_ra, w_ra; wire [255:0] g_wd, w_wd; wire [7:0] g_tg, w_tg; wire g_rv, w_rv;
  wire g_hd = (pg < np) && !ggap; wire w_hd = (pw < np) && !wgap;
  reg [511:0] junk;
  wire [511:0] g_head = g_hd ? prog_d[pg] : junk; wire [511:0] w_head = w_hd ? prog_d[pw] : ~junk;
  wire g_isd = g_hd && !prog_c[pg]; wire g_isp = g_hd && prog_c[pg];
  wire w_isd = w_hd && !prog_c[pw]; wire w_isp = w_hd && prog_c[pw];
  qkd_hr_ingest_eng__rf_core G (.ck(ck), .busy(g_busy), .d_data(g_head[255:0]), .d_rdy(g_drdy), .d_v(g_isd),
    .done_tag(g_tg), .done_v(g_dv), .in_data(g_head), .in_rdy(g_inrdy), .in_v(g_isp), .n_sectors(g_ns),
    .r_addr(g_ra), .r_v(g_rv), .rd_data(junk[255:0]), .rd_v(1'b0), .rst_n(rst_n), .w_addr(g_wa), .w_data(g_wd),
    .w_rdy(grdy), .w_v(g_wv));
  qkd_hr_ingest_eng W (.ck(ck), .busy(w_busy), .d_data(w_head[255:0]), .d_rdy(w_drdy), .d_v(w_isd),
    .done_tag(w_tg), .done_v(w_dv), .in_data(w_head), .in_rdy(w_inrdy), .in_v(w_isp), .n_sectors(w_ns),
    .r_addr(w_ra), .r_v(w_rv), .rd_data(junk[255:0]), .rd_v(1'b0), .rst_n(rst_n), .w_addr(w_wa), .w_data(w_wd),
    .w_rdy(wrdy), .w_v(w_wv));
  // ---------------- logs
  localparam integer NL = 65536;
  reg [287:0] gwl [0:NL-1]; reg [287:0] wwl [0:NL-1]; reg [39:0] gdl [0:4095]; reg [39:0] wdl [0:4095];
  integer gwn = 0, wwn = 0, gdn = 0, wdn = 0, bad = 0, cyc = 0, idle_chk = 0, cld = 0, cdn = 0, maxq = 0, k;
  always @(posedge ck) if (rst_n) begin
    cyc = cyc + 1;
    if (g_isd && g_drdy) pg = pg + 1; else if (g_isp && g_inrdy) pg = pg + 1;
    if (w_isd && w_drdy) pw = pw + 1; else if (w_isp && w_inrdy) pw = pw + 1;
    if (g_wv && grdy) begin gwl[gwn] = {g_wa, g_wd}; gwn = gwn + 1; end
    if (w_wv && wrdy) begin wwl[wwn] = {w_wa, w_wd}; wwn = wwn + 1; end
    if (g_dv) begin gdl[gdn] = {g_tg, g_ns}; gdn = gdn + 1; end
    if (w_dv) begin
      wdl[wdn] = {w_tg, w_ns}; wdn = wdn + 1;
      // done only after its last sector left the port: port transfers so far >= sectors the done counts
      if (wwn < w_ns) begin bad = bad + 1; if (bad < 8) $display("EARLY DONE cyc=%0d ns=%0d port=%0d", cyc, w_ns, wwn); end
    end
    if (W.rf_ld) cld = cld + 1;
    if (W.rf_cdv) cdn = cdn + 1;
    if (W.rf_qn > maxq) maxq = W.rf_qn;
    if (W.rf_qn == 2 && W.rf_cdv && !W.rf_rel) begin bad = bad + 1; $display("DONE QUEUE OVERFLOW cyc=%0d", cyc); end
    if (!w_busy && !w_wv) begin
      idle_chk = idle_chk + 1;
      if (cld != wwn + (W.rf_ld ? 1 : 0) || cdn != wdn + (W.rf_cdv ? 1 : 0)) begin
        bad = bad + 1; if (bad < 8) $display("IDLE LEAK cyc=%0d loads=%0d port=%0d cdone=%0d done=%0d", cyc, cld, wwn, cdn, wdn); end
    end
  end
  always @(negedge ck) begin
    ggap = ({$random(seed)} % 4) == 0; wgap = ({$random(seed)} % 3) == 0;
    grdy = ({$random(seed)} % 5) != 0; wrdy = ({$random(seed)} % 2) != 0;
    if (({$random(seed)} % 400) == 0) begin grdy = 0; wrdy = 0; end
    if (wst != 0) begin wst = wst - 1; wrdy = 0; end else if (({$random(seed)} % 150) == 0) wst = 20 + {$random(seed)} % 60;
    for (k = 0; k < 16; k = k + 1) junk[32*k +: 32] = $random(seed);
  end
  // ---------------- program
  function [511:0] rnd512; input integer s; integer q; begin for (q = 0; q < 16; q = q + 1) rnd512[32*q +: 32] = $random(seed); end endfunction
  task add(input c, input [511:0] d); begin prog_c[np] = c; prog_d[np] = d; np = np + 1; end endtask
  reg [255:0] dsc; integer i, n, b, mode, nd, nbt, tt, cycles, zf;
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    if (!$value$plusargs("nd=%d", nd)) nd = 60;
    if (!$value$plusargs("cycles=%d", cycles)) cycles = 40000;
    if (!$value$plusargs("zf=%d", zf)) zf = 4;
    np = 0; ggap = 0; wgap = 0; grdy = 1; wrdy = 1; junk = 0;
    for (i = 0; i < nd && np < NP - 200; i = i + 1) begin
      mode = (({$random(seed)} % 6) == 0) ? 1 : 0;
      dsc = 0; dsc[7] = ({$random(seed)} % 3) != 0; dsc[15:8] = i; dsc[47:16] = $random(seed) & 32'h00ff_ffe0;
      if (mode != 1) begin                      // RAW: n0 sectors, nb = n0 / 2 beats
        n = 2 * (1 + (((({$random(seed)} % 3) == 0)) ? {$random(seed)} % 24 : {$random(seed)} % 3));
        if (({$random(seed)} % zf) == 0) n = 0;   // empty RAW (no sector): a done with no write
        dsc[3:0] = 0; dsc[167:144] = n; dsc[255:240] = n / 2; nbt = n / 2;
      end else begin                            // QKV FP8, 2 heads x 128, positions [t_lo, 16)
        tt = {$random(seed)} % 4;
        dsc[3:0] = 1; dsc[5:4] = 2; dsc[6] = 0; dsc[79:48] = dsc[47:16] + 32'h0001_0000;
        dsc[111:80] = 4; dsc[143:112] = 4; dsc[171:168] = 7; dsc[219:216] = 2; dsc[228:224] = tt; dsc[236:232] = 16;
        nbt = 2 * (16 - tt) * 2 * 128 / 64;     // K then V, (16 - tlo) positions x 2 heads x 128 B
      end
      add(0, {256'd0, dsc});
      for (b = 0; b < nbt; b = b + 1) add(1, rnd512(0));
    end
    $display("PROGRAM entries=%0d descriptors=%0d", np, i);
    repeat (4) @(negedge ck); rst_n = 1;
    i = 0; n = 0;
    while (i < cycles && n < 64) begin
      @(negedge ck); i = i + 1;
      if (pg == np && pw == np && !g_busy && !g_wv && !w_busy && !w_wv) n = n + 1; else n = 0;
    end
    n = (gwn < wwn) ? gwn : wwn;
    for (i = 0; i < n; i = i + 1) if (gwl[i] !== wwl[i]) begin bad = bad + 1; if (bad < 8) $display("W MISMATCH #%0d %h / %h", i, gwl[i][287:256], wwl[i][287:256]); end
    n = (gdn < wdn) ? gdn : wdn;
    for (i = 0; i < n; i = i + 1) if (gdl[i] !== wdl[i]) begin bad = bad + 1; if (bad < 8) $display("DONE MISMATCH #%0d %h / %h", i, gdl[i], wdl[i]); end
    if (gwn != wwn || gdn != wdn) begin bad = bad + 1; $display("COUNT DIFF writes %0d/%0d dones %0d/%0d", gwn, wwn, gdn, wdn); end
    $display("SIM cycles=%0d consumed=%0d/%0d writes=%0d/%0d dones=%0d/%0d idle_checks=%0d max_doneq=%0d mismatches=%0d",
             cyc, pg, pw, gwn, wwn, gdn, wdn, idle_chk, maxq, bad);
    $finish;
  end
endmodule

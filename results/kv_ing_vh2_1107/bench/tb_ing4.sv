`timescale 1ns/1ps
// KV-ING-8 11-07: vH2 wrapper qkd_hr_ingest_eng on the DIE-KV-70/ING 11-04 transaction co-sim, qkd_host_native_engine at the wrapper's parameters (gold) vs qkd_host_native_engine_ing2.
// Each DUT pulls the same host stream on its own handshakes with independent random gaps and w_rdy back-pressure; write (addr, data)
// sequences and done (tag, n_sectors) sequences must be identical; done must count its own last sector.  Program kinds (+pm):
// 0 mix, 1 QKV only, 2 stream only.  Kind 2 entries (sync) wait for that DUT's !busy (an empty-payload QKV descriptor takes a beat
// that is at the port on its one in_rdy edge: source behaviour kept, not a host pattern).
module tb;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n = 0;
  localparam integer NP = 40000;
  reg [511:0] prog_d [0:NP-1]; reg [1:0] prog_c [0:NP-1];
  integer np;
  reg [31:0] seed;
  // DIE-KV-73/ING: Verilator $random(seed) did not follow +seed (36 ING1 seeds were 3 distinct runs); own xorshift, seed really varies
  function automatic [31:0] rr(); seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5); rr = seed; endfunction
  integer pg = 0, pw = 0;
  reg ggap, wgap, grdy, wrdy; reg [7:0] wst = 0;
  wire g_drdy, g_inrdy, g_wv, g_dv, g_busy, w_drdy, w_inrdy, w_wv, w_dv, w_busy;
  wire [31:0] g_wa, w_wa, g_ns, w_ns; wire [255:0] g_wd, w_wd; wire [7:0] g_tg, w_tg;
  wire g_hd = (pg < np) && !ggap; wire w_hd = (pw < np) && !wgap;
  reg [511:0] junk;
  wire [511:0] g_head = g_hd ? prog_d[pg] : junk; wire [511:0] w_head = w_hd ? prog_d[pw] : ~junk;
  wire g_isd = g_hd && prog_c[pg] == 0; wire g_isp = g_hd && prog_c[pg] == 1;
  wire w_isd = w_hd && prog_c[pw] == 0; wire w_isp = w_hd && prog_c[pw] == 1;
  wire g_sync = pg < np && prog_c[pg] == 2; wire w_sync = pw < np && prog_c[pw] == 2;
  qkd_host_native_engine #(.APIPE(0), .AW(32), .DQ(4), .HDMAX(128), .KVHMAX(2), .NATIVE_ROWS(1), .QKV(1), .QMUT(0), .QPIPE(2)) G (
    .clk(ck), .clk_bank({ck, ck}), .clk_out(ck), .rst_n(rst_n), .d_v(g_isd), .d_rdy(g_drdy), .d_data(g_head[255:0]),
    .in_v(g_isp), .in_rdy(g_inrdy), .in_data(g_head), .w_v(g_wv), .w_rdy(grdy), .w_addr(g_wa), .w_data(g_wd),
    .r_v(), .r_rdy(1'b0), .r_addr(), .rd_v(1'b0), .rd_data(256'd0), .done_v(g_dv), .done_tag(g_tg), .busy(g_busy), .n_sectors(g_ns), .n_beats());
  qkd_hr_ingest_eng W (.ck(ck), .rst_n(rst_n), .d_v(w_isd), .d_rdy(w_drdy), .d_data(w_head[255:0]),
    .in_v(w_isp), .in_rdy(w_inrdy), .in_data(w_head), .w_v(w_wv), .w_rdy(wrdy), .w_addr(w_wa), .w_data(w_wd),
    .done_v(w_dv), .done_tag(w_tg), .busy(w_busy), .n_sectors(w_ns), .r_addr(), .r_v(), .rd_data(256'd0), .rd_v(1'b0));
  localparam integer NL = 200000;
  reg [287:0] gwl [0:NL-1]; reg [287:0] wwl [0:NL-1]; reg [39:0] gdl [0:4095]; reg [39:0] wdl [0:4095];
  integer gwn = 0, wwn = 0, gdn = 0, wdn = 0, bad = 0, cyc = 0, k;
  integer g_last = 0, w_last = 0, minw = 200, carry_ra = 0, carry_row = 0;
  reg pw_v = 0, pw_r = 0; reg [31:0] pw_a = 0; reg [255:0] pw_d = 0;
  always @(posedge ck) if (rst_n) begin
    cyc = cyc + 1;
    if (g_sync) begin if (!g_busy && !g_wv) pg = pg + 1; end
    else if (g_isd && g_drdy) pg = pg + 1; else if (g_isp && g_inrdy) pg = pg + 1;
    if (w_sync) begin if (!w_busy && !w_wv) pw = pw + 1; end
    else if (w_isd && w_drdy) pw = pw + 1; else if (w_isp && w_inrdy) pw = pw + 1;
    if (g_wv && grdy) begin gwl[gwn] = {g_wa, g_wd}; gwn = gwn + 1; g_last = cyc; end
    if (w_wv && wrdy) begin wwl[wwn] = {w_wa, w_wd}; wwn = wwn + 1; w_last = cyc; end
    if (g_dv) begin gdl[gdn] = {g_tg, g_ns}; gdn = gdn + 1; end
    if (W.u_eng.fi_n != 2'd0 || W.fc_in_v || W.fc_d_v || W.u_eng.busy || W.o_v || W.s_n != 2'd0) if (!w_busy) begin bad = bad + 1; if (bad < 8) $display("BUSY CONTRACT cyc=%0d fi %0d eng %b o %b s %0d", cyc, W.u_eng.fi_n, W.u_eng.busy, W.o_v, W.s_n); end
    // port rules: w_v and its payload hold until taken
    if (pw_v && !pw_r && (!w_wv || pw_a !== w_wa || pw_d !== w_wd)) begin bad = bad + 1; if (bad < 8) $display("W NOT STABLE cyc=%0d", cyc); end
    pw_v = w_wv; pw_r = wrdy; pw_a = w_wa; pw_d = w_wd;
    // no storage overflow
    if (W.u_eng.fi_push && W.u_eng.fi_n == 2'd3 && !W.u_eng.fi_pop) begin bad = bad + 1; if (bad < 8) $display("IN FIFO OVERFLOW cyc=%0d", cyc); end
    if (W.u_eng.p_d_v && W.u_eng.dq_n == 3'd4 && !W.u_eng.d_pop) begin bad = bad + 1; if (bad < 8) $display("DQ OVERFLOW cyc=%0d", cyc); end
    if (W.s_keep && W.s_n == 2'd2 && !W.s_take) begin bad = bad + 1; if (bad < 8) $display("SKID OVERFLOW cyc=%0d", cyc); end
    if (W.u_eng.er_m !== W.er_w || W.u_eng.er_st !== W.er_w || W.u_eng.er_s !== {35{W.er_w}}) begin bad = bad + 1; if (bad < 8) $display("READY COPIES DIFFER cyc=%0d", cyc); end
    if (w_dv) begin
      wdl[wdn] = {w_tg, w_ns}; wdn = wdn + 1;
      if (wwn < w_ns) begin bad = bad + 1; if (bad < 8) $display("EARLY DONE cyc=%0d ns=%0d port=%0d", cyc, w_ns, wwn); end
    end
  end
  integer full = 0;
  always @(negedge ck) begin
    if (full) begin ggap = 0; wgap = 0; grdy = 1; wrdy = 1; end else begin
    ggap = ({rr()} % 4) == 0; wgap = ({rr()} % 3) == 0;
    grdy = ({rr()} % 5) != 0; wrdy = ({rr()} % 2) != 0;
    if (({rr()} % 400) == 0) begin grdy = 0; wrdy = 0; end
    if (wst != 0) begin wst = wst - 1; wrdy = 0; end else if (({rr()} % 150) == 0) wst = 20 + {rr()} % 60;
    end
    for (k = 0; k < 16; k = k + 1) junk[32*k +: 32] = rr();
  end
  // floats around the quantiser's edges, and raw random
  function [31:0] rndf; input integer dummy; reg [7:0] e; reg [31:0] r; begin
    r = rr();
    case ({rr()} % 8)
      0: e = 8'd0;
      1: e = 110 + {rr()} % 14;
      2: e = 114 + {rr()} % 10;
      3: e = 130 + {rr()} % 10;
      4: e = 255;
      default: e = 118 + {rr()} % 20;
    endcase
    case ({rr()} % 6)
      0: r[22:0] = 23'h080000 << ({rr()} % 4);      // ties
      1: r[22:0] = 23'h7fffff;
      2: r[19:0] = 20'h80000;
      default: ;
    endcase
    rndf = {r[31], e, r[22:0]};
  end endfunction
  function [511:0] rbeat; input integer fmt; integer q; begin
    for (q = 0; q < 16; q = q + 1) rbeat[32*q +: 32] = (fmt == 0) ? rndf(0) : rr();
    if (fmt == 1) for (q = 0; q < 32; q = q + 1) begin : b reg [31:0] f; f = rndf(0); rbeat[16*q +: 16] = f[31:16]; end
  end endfunction
  task add(input [1:0] c, input [511:0] d); begin prog_c[np] = c; prog_d[np] = d; np = np + 1; end endtask
  reg [255:0] dsc; integer i, n, b, mode, nd, nbt, tl, th, cycles, fmt, kvh, pm, rb, pitch, ring, ldie, die, lns, f0;
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    seed = seed * 32'd2654435761 + 32'd12345;
    if (!$value$plusargs("nd=%d", nd)) nd = 40;
    if (!$value$plusargs("cycles=%d", cycles)) cycles = 400000;
    if (!$value$plusargs("pm=%d", pm)) pm = 0;
    if (!$value$plusargs("full=%d", full)) full = 0;
    if (!$value$plusargs("minw=%d", minw)) minw = 200;
    np = 0; ggap = 0; wgap = 0; grdy = 1; wrdy = 1; junk = 0;
    for (i = 0; i < nd && np < NP - 6000; i = i + 1) begin
      mode = {rr()} % 8;
      if (pm == 1) mode = 0; if (pm == 2) mode = 1 + {rr()} % 7; if (pm == 3 && ({rr()} % 2)) mode = 9;
      dsc = 0; dsc[7] = ({rr()} % 3) != 0; dsc[15:8] = i;
      dsc[47:16] = {rr()} & 32'h00ff_ffc0;
      if (mode <= 2) begin                       // QKV
        fmt = {rr()} % 4; kvh = 1 + {rr()} % 2;
        tl = {rr()} % 16; th = tl + 1 + {rr()} % (16 - tl);
        if (({rr()} % 12) == 0) th = tl;   // empty payload
        dsc[3:0] = 1; dsc[5:4] = fmt; dsc[79:48] = dsc[47:16] + 32'd32768;
        dsc[111:80] = 32768; dsc[143:112] = 32768; dsc[171:168] = 7; dsc[219:216] = kvh; dsc[228:224] = tl; dsc[236:232] = th;
        nbt = 2 * (th - tl) * kvh * 128 / ((fmt == 0) ? 16 : (fmt == 1) ? 32 : 64);
        add(0, {256'd0, dsc});
        for (b = 0; b < nbt; b = b + 1) add(1, rbeat(fmt >= 2 ? 2 : fmt));
        if (th == tl) add(2, 0);
      end else if (mode <= 4 || mode == 9) begin   // RAW (9: r3 burst, descriptor only)
        n = 2 * (1 + {rr()} % 24); if (({rr()} % 5) == 0) n = 0;
        b = {rr()} % 2;                 // an extra pad beat sometimes
        if (mode == 9) begin n = 0; b = 0; end   // r3 +pm=3: descriptor only
        dsc[3:0] = 0; dsc[167:144] = n; dsc[255:240] = n / 2 + b; nbt = n / 2 + b;
        if (({rr()} % 3) == 0) begin dsc[31:16] = 16'hffff - ({rr()} % 16'd24); dsc[39:32] = {rr()} % 256; end
        add(0, {256'd0, dsc});
        for (b = 0; b < nbt; b = b + 1) add(1, rbeat(2));
      end else if (mode <= 6) begin              // ROWS
        rb = ({rr()} % 3 == 0) ? 288 : ({rr()} % 2) ? 528 : 1 + {rr()} % 300;
        pitch = (rb + 31) / 32 + {rr()} % 2; if (pitch > 31) pitch = 31;
        if (rb > pitch * 32) rb = pitch * 32;
        n = 1 + {rr()} % 40; ring = ({rr()} % 3 == 0) ? 8 << ({rr()} % 3) : 0;
        ldie = {rr()} % 3; die = {rr()} % (1 << ldie); lns = {rr()} % 3;
        if (ring != 0) begin ldie = 0; die = 0; lns = 0; end
        dsc[3:0] = 2; dsc[79:48] = 32'h0010_0000; dsc[84:80] = pitch; dsc[143:112] = ring;
        f0 = {rr()} % 200; if (({rr()} % 3) == 0) f0 = 65535 - ({rr()} % 30); dsc[167:144] = f0; dsc[183:168] = rb; dsc[199:184] = n;
        dsc[217:216] = ldie; dsc[231:224] = die; dsc[233:232] = lns;
        nbt = (n * rb + 63) / 64; dsc[255:240] = nbt;
        add(0, {256'd0, dsc});
        for (b = 0; b < nbt; b = b + 1) add(1, rbeat(2));
      end else begin                             // IKEY, whole 16-key groups
        n = 16 * (1 + {rr()} % 4);
        ldie = {rr()} % 3; die = {rr()} % (1 << ldie); lns = {rr()} % 3;
        dsc[3:0] = 3; dsc[79:48] = 32'h0010_0000; f0 = 16 * ({rr()} % 300); if (({rr()} % 3) == 0) f0 = 65536 - 16 * (1 + {rr()} % 3);
        dsc[167:144] = f0; dsc[199:184] = n; dsc[217:216] = ldie; dsc[231:224] = die; dsc[233:232] = lns;
        nbt = (n * 68 + 63) / 64; dsc[255:240] = nbt;
        add(0, {256'd0, dsc});
        for (b = 0; b < nbt; b = b + 1) add(1, rbeat(2));
      end
    end
    $display("PROGRAM entries=%0d descriptors=%0d", np, i);
    repeat (4) @(negedge ck); rst_n = 1;
    i = 0; n = 0;
    while (i < cycles && n < 64) begin
      @(negedge ck); i = i + 1;
      if (pg == np && pw == np && !g_busy && !g_wv && !w_busy && !w_wv) n = n + 1; else n = 0;
    end
    if (n < 64) begin bad = bad + 1; $display("NOT DONE pg=%0d pw=%0d/%0d gb=%b wb=%b", pg, pw, np, g_busy, w_busy); end
    n = (gwn < wwn) ? gwn : wwn;
    for (i = 0; i < n; i = i + 1) if (gwl[i] !== wwl[i]) begin bad = bad + 1; if (bad < 8) $display("W MISMATCH #%0d a %h / %h d %h / %h", i, gwl[i][287:256], wwl[i][287:256], gwl[i][255:0], wwl[i][255:0]); end
    n = (gdn < wdn) ? gdn : wdn;
    for (i = 0; i < n; i = i + 1) if (gdl[i] !== wdl[i]) begin bad = bad + 1; if (bad < 8) $display("DONE MISMATCH #%0d %h / %h", i, gdl[i], wdl[i]); end
    if (gwn != wwn || gdn != wdn) begin bad = bad + 1; $display("COUNT DIFF writes %0d/%0d dones %0d/%0d", gwn, wwn, gdn, wdn); end
    if (g_ns !== w_ns) begin bad = bad + 1; $display("NSEC DIFF %0d/%0d", g_ns, w_ns); end
    $display("SIM cycles=%0d consumed=%0d/%0d writes=%0d/%0d dones=%0d/%0d last_w=%0d/%0d mismatches=%0d", cyc, pg, pw, gwn, wwn, gdn, wdn, g_last, w_last, bad);
    if (wwn < minw) begin bad = bad + 1; $display("LOW COVERAGE writes=%0d < %0d", wwn, minw); end
    if (bad == 0) $display("PASS"); else $display("FAIL");
    $finish;
  end
endmodule

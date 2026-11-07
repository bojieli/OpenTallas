#!/usr/bin/env python3
"""tb_ing4.sv from tb_ing3.sv: the DUT is now the whole wrapper; adds port-stability, FIFO-overflow, coverage checks and boundary stimulus."""
from pathlib import Path
def rep(t, a, b, n=1):
    assert t.count(a) == n, (a, t.count(a)); return t.replace(a, b)
t = Path("results/kv_ing_rf3_1105/bench/tb_ing3.sv").read_text()
t = rep(t, "// KV-ING-1 11-05: r3 (ing3) on the DIE-KV-70/ING 11-04 transaction co-sim,", "// KV-ING-8 11-07: vH2 wrapper qkd_hr_ingest_eng on the DIE-KV-70/ING 11-04 transaction co-sim,")
a = t.index("  qkd_host_native_engine_ing3 W ("); b = t.index("  localparam integer NL = 200000;")
t = t[:a] + """  qkd_hr_ingest_eng W (.ck(ck), .rst_n(rst_n), .d_v(w_isd), .d_rdy(w_drdy), .d_data(w_head[255:0]),
    .in_v(w_isp), .in_rdy(w_inrdy), .in_data(w_head), .w_v(w_wv), .w_rdy(wrdy), .w_addr(w_wa), .w_data(w_wd),
    .done_v(w_dv), .done_tag(w_tg), .busy(w_busy), .n_sectors(w_ns), .r_addr(), .r_v(), .rd_data(256'd0), .rd_v(1'b0));
""" + t[b:]
t = rep(t, """    if (W.fi_n != 2'd0 || W.fd_n != 2'd0 || W.busy) if (!w_busy) begin bad = bad + 1; if (bad < 8) $display("BUSY CONTRACT cyc=%0d fi %0d fd %0d eng %b", cyc, W.fi_n, W.fd_n, W.busy); end
""", """    if (W.u_eng.fi_n != 2'd0 || W.fc_in_v || W.fc_d_v || W.u_eng.busy || W.o_v || W.s_n != 2'd0) if (!w_busy) begin bad = bad + 1; if (bad < 8) $display("BUSY CONTRACT cyc=%0d fi %0d eng %b o %b s %0d", cyc, W.u_eng.fi_n, W.u_eng.busy, W.o_v, W.s_n); end
    // port rules: w_v and its payload hold until taken
    if (pw_v && !pw_r && (!w_wv || pw_a !== w_wa || pw_d !== w_wd)) begin bad = bad + 1; if (bad < 8) $display("W NOT STABLE cyc=%0d", cyc); end
    pw_v = w_wv; pw_r = wrdy; pw_a = w_wa; pw_d = w_wd;
    // no storage overflow
    if (W.u_eng.fi_push && W.u_eng.fi_n == 2'd3 && !W.u_eng.fi_pop) begin bad = bad + 1; if (bad < 8) $display("IN FIFO OVERFLOW cyc=%0d", cyc); end
    if (W.u_eng.p_d_v && W.u_eng.dq_n == 3'd4 && !W.u_eng.d_pop) begin bad = bad + 1; if (bad < 8) $display("DQ OVERFLOW cyc=%0d", cyc); end
    if (W.s_keep && W.s_n == 2'd2 && !W.s_take) begin bad = bad + 1; if (bad < 8) $display("SKID OVERFLOW cyc=%0d", cyc); end
    if (W.u_eng.er_m !== W.er_w || W.u_eng.er_st !== W.er_w || W.u_eng.er_s !== {35{W.er_w}}) begin bad = bad + 1; if (bad < 8) $display("READY COPIES DIFFER cyc=%0d", cyc); end
""")
t = rep(t, "  integer g_last = 0, w_last = 0;\n", "  integer g_last = 0, w_last = 0, minw = 200, carry_ra = 0, carry_row = 0;\n  reg pw_v = 0, pw_r = 0; reg [31:0] pw_a = 0; reg [255:0] pw_d = 0;\n")
# boundary stimulus: 16-bit carries of the RAW address and of st_row
t = rep(t, "        add(0, {256'd0, dsc});\n        for (b = 0; b < nbt; b = b + 1) add(1, rbeat(2));\n      end else if (mode <= 6) begin", "        if (({rr()} % 3) == 0) begin dsc[31:16] = 16'hffff - ({rr()} % 16'd24); dsc[39:32] = {rr()} % 256; end\n        add(0, {256'd0, dsc});\n        for (b = 0; b < nbt; b = b + 1) add(1, rbeat(2));\n      end else if (mode <= 6) begin")
t = rep(t, "        f0 = {rr()} % 200; dsc[167:144] = f0;", "        f0 = {rr()} % 200; if (({rr()} % 3) == 0) f0 = (({rr()} % 3) == 0) ? 65535 : 65535 - ({rr()} % 30); if (({rr()} % 4) == 0) f0 = f0 + (({rr()} % 256) << 16); dsc[167:144] = f0;")
t = rep(t, "f0 = 16 * ({rr()} % 300);\n", "f0 = 16 * ({rr()} % 300); if (({rr()} % 3) == 0) f0 = 65536 - 16 * (1 + {rr()} % 3); if (({rr()} % 4) == 0) f0 = f0 + (({rr()} % 256) << 16); if (({rr()} % 2) == 0) dsc[18:16] = {rr()} % 8;\n")
# long write stalls: a stream done pending while the next descriptor could already reach the face
t = rep(t, "else if (({rr()} % 150) == 0) wst = 20 + {rr()} % 60;", "else if (({rr()} % 150) == 0) wst = (({rr()} % 8) == 0) ? 250 : 20 + {rr()} % 60;")
t = rep(t, 'if (!$value$plusargs("full=%d", full)) full = 0;', 'if (!$value$plusargs("full=%d", full)) full = 0;\n    if (!$value$plusargs("minw=%d", minw)) minw = 200;')
t = rep(t, '''    if (bad == 0) $display("PASS"); else $display("FAIL");''', '''    if (wwn < minw) begin bad = bad + 1; $display("LOW COVERAGE writes=%0d < %0d", wwn, minw); end
    if (bad == 0) $display("PASS"); else $display("FAIL");''')
Path("results/kv_ing_vh2_1107/bench").mkdir(parents=True, exist_ok=True)
Path("results/kv_ing_vh2_1107/bench/tb_ing4.sv").write_text(t)

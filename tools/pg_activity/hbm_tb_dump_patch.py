#!/usr/bin/env python3
"""PG-ACTIVITY-4 (10-27): make tb_hgi_sm_e2e dump the real SM g_sm[0].u_sm per case, switched by plusargs.
Verilator 5.050 ignores $dumpoff/$dumpon and a second $dumpfile (tested), so one process = one case window:
  +C0=c +C1=c+1 +DUMP +VCD=file [+DUMPMAX=n]  -> $dumpvars at the record issue of case c, $finish after min(retire, n) cycles
  no +DUMP                                   -> unchanged bench (full 14-case HGI_SM_E2E PASS check), no trace cost
  hbm_tb_dump_patch.py IN.sv OUT.sv"""
import sys
src, dst = sys.argv[1:3]
t = open(src).read()
def sub(old, new):
    global t
    assert t.count(old) == 1, ("anchor not unique", old, t.count(old))
    t = t.replace(old, new)
sub("integer xi, xbad = 0, c0;", "integer xi, xbad = 0, c0, c1, dmax; reg dump_en; reg [1023:0] vcdf;")
sub('if (!$value$plusargs("C0=%d", c0)) c0 = 0;',
    'if (!$value$plusargs("C0=%d", c0)) c0 = 0;\n'
    '        if (!$value$plusargs("C1=%d", c1)) c1 = NCASE;\n'
    '        dump_en = $test$plusargs("DUMP");\n'
    '        if (!$value$plusargs("DUMPMAX=%d", dmax)) dmax = 2000;\n'
    '        if (!$value$plusargs("VCD=%s", vcdf)) vcdf = "sm_case.vcd";\n'
    '        if (dump_en && c1 != c0 + 1) begin $display("ERR +DUMP needs exactly one case (+C1=C0+1)"); $finish; end\n'
    '        if (dump_en) $dumpfile(vcdf);')
sub("for (c = c0; c < NCASE; c = c + 1) begin", "for (c = c0; c < c1; c = c + 1) begin")
sub("@(posedge clk); t0 = cyc; #0.1 rec_v = 0;",
    "@(posedge clk); t0 = cyc; #0.1 rec_v = 0;\n"
    "            if (dump_en) begin $dumpvars(0, tb_hgi_sm_e2e.g_sm[0].u_sm); $display(\"DUMP_ON case %0d cycle %0d\", c, cyc); $fflush; end")
sub("t = 0; while (k < nr && nf == 0 && t < 400000) begin @(posedge clk); t = t + 1; end",
    "t = 0; while (k < nr && nf == 0 && t < 400000 && !(dump_en && t >= dmax)) begin @(posedge clk); t = t + 1; end\n"
    "            if (dump_en) begin $display(\"DUMP_OFF case %0d cycle %0d window %0d retired %0d of %0d faults %0d\", c, cyc, cyc - t0, k, nr, nf); $dumpflush; $finish; end")
open(dst, "w").write(t)
print("patched", dst)

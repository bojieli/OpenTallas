#!/usr/bin/env python3
"""TOK-FUNC-S81/HEADMTP: latency-probe copy of tb_s81sl_rstop_xo (the RG-HEAD 16-stop die-ring egress bench), master swapped
to the current end-slice ring stop ot_s81sl_rstopt_xo (as tools/s81_slice/rstopt_xo_bench.sh does).  The tb source is not
edited; the copy only adds a cycle counter, the injection edge of each of the 80 flagged ring beats and the s_0N ro_w egress
edge, and prints  RSTOP_LAT pass=<fl> n=<n> min=<c> max=<c> per_slice_max=<16 values>  after each ring pass.
    python3 tools/s81_dv/tokfunc/rstop_lat_tb.py SRC_TB OUT_TB
"""
import sys

src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
rep = [
    ("ot_s81sl_rstop_xo u ", "ot_s81sl_rstopt_xo u "),
    ("    reg [W-1:0] want [0:79]; integer want_src [0:79];",
     "    reg [W-1:0] want [0:79]; integer want_src [0:79];\n"
     "    integer lcyc = 0, t_inj [0:79], t_eg [0:79], lq, lmin, lmax, lsl [0:15];\n"
     "    always @(posedge clk) lcyc <= lcyc + 1;"),
    ("            end else eg_seen[ix] = 1'b1;", "            end else begin eg_seen[ix] = 1'b1; t_eg[ix] = lcyc; end"),
    ("                ring_beat(sl, k, want[5 * sl + k]); idle(35);",
     "                t_inj[5 * sl + k] = lcyc; ring_beat(sl, k, want[5 * sl + k]); idle(35);"),
    ("            idle(60);\n",
     "            idle(60);\n"
     "            lmin = 1 << 30; lmax = -1; for (sl = 0; sl < 16; sl = sl + 1) lsl[sl] = -1;\n"
     "            for (lq = 0; lq < 80; lq = lq + 1) if (eg_seen[lq]) begin\n"
     "                if (t_eg[lq] - t_inj[lq] < lmin) lmin = t_eg[lq] - t_inj[lq];\n"
     "                if (t_eg[lq] - t_inj[lq] > lmax) lmax = t_eg[lq] - t_inj[lq];\n"
     "                if (t_eg[lq] - t_inj[lq] > lsl[lq / 5]) lsl[lq / 5] = t_eg[lq] - t_inj[lq]; end\n"
     "            $display(\"RSTOP_LAT pass=%0d n=%0d min=%0d max=%0d per_slice_max=%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\",\n"
     "                     fl, eg_n, lmin, lmax, lsl[0], lsl[1], lsl[2], lsl[3], lsl[4], lsl[5], lsl[6], lsl[7], lsl[8], lsl[9],\n"
     "                     lsl[10], lsl[11], lsl[12], lsl[13], lsl[14], lsl[15]);\n"),
]
for a, b in rep:
    n = t.count(a)
    if n != (2 if a.startswith("ot_s81sl_rstop_xo u ") else 1):
        raise SystemExit(f"patch anchor count {n}: {a[:60]!r}")
    t = t.replace(a, b)
open(dst, "w").write(t)
print("RSTOP_LAT_TB written", dst)

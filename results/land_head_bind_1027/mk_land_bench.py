#!/usr/bin/env python3
"""LAND-HEAD-BIND-1 crossing bench: the REAL generated landed wrapper (gen2, rings + ring reset relays + monitor
collectors as emitted) against the REAL non-landed wrapper of the same type (gen0 reference), same stimulus.

Each landed input bus is launched by a source register on its own forwarded clock fclk = clk + PHASE (TT/FF window
offsets); the reference gets the same sequence on clk.  Pass: every output bit of the landed type equals the reference
output exactly K=3 cycles earlier (fixed +K), for every cycle after warm-up, and no landing fault.  Discrimination: the
same comparison at K-1 and K+1 must mismatch (the bench sees the latency).
usage: mk_land_bench.py GEN_LANDED GEN_REF MODULE OUT_DIR"""
import re
import sys
from pathlib import Path

land, ref, mod, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
K = 3


def ports(text):
    hdr = re.search(r"(?ms)^module \w+ \((.*?)^\);", text).group(1)
    res = []
    for ln in hdr.splitlines():
        ln = re.sub(r"//.*", "", ln).strip().rstrip(",")
        m = re.match(r"(input|output)\s+wire\s*(\[(\d+):0\])?\s*(\w+)$", ln)
        if m:
            res.append((m.group(1), int(m.group(3)) + 1 if m.group(3) else 1, m.group(4)))
    return res


lt = (land / f"{mod}.sv").read_text()
rt = (ref / f"{mod}.sv").read_text().replace(f"module {mod} (", f"module {mod}__ref (").replace(
    f"endmodule : {mod}", f"endmodule : {mod}__ref")
(out / f"{mod}__ref.sv").write_text(rt)
LP, RP = ports(lt), ports(rt)
rnames = {n for _, _, n in RP}
data_in = [(w, n) for d, w, n in RP if d == "input" and w > 1]
landed_in = [n for _, n in data_in if f"fclk_in_{n}" in {x for _, _, x in LP}]
outs = [(w, n) for d, w, n in RP if d == "output"]
L = ["`timescale 1ps/1ps", f"module tb_{mod};",
     "  int PHASE; int cyc = 0; int bad[3] = '{0, 0, 0}; int faults = 0; int seen_ready = 0;",
     "  reg clk = 0; reg fclk = 0; reg arst_n = 0; reg start_i = 0;",
     "  initial begin #417; clk = 1; forever #417 clk = ~clk; end",
     "  // fclk edge n = clk edge n + PHASE (PHASE in (-417, 417): negative = the forwarded clock leads)",
     "  initial begin if (!$value$plusargs(\"PHASE=%d\", PHASE)) PHASE = 0; #(417 + PHASE); fclk = 1; forever #417 fclk = ~fclk; end"]
for w, n in data_in:
    L += [f"  reg [{w - 1}:0] seq_{n} [0:4095];", f"  reg [{w - 1}:0] src_{n} = 0, ref_{n} = 0;"]
for w, n in outs:
    L += [f"  wire [{w - 1}:0] l_{n}, r_{n};", f"  reg [{w - 1}:0] h_{n} [0:7];"]
L.append("  initial begin")
for w, n in data_in:
    words = (w + 31) // 32
    L.append(f"    for (int i = 0; i < 4096; i++) seq_{n}[i] = {{{', '.join(['$urandom()'] * words)}}};")
L.append("  end")
# sequence index advances once per cycle; the landed copy launches on fclk, the reference on clk
L += ["  int si = 0, fi = 0;",
      "  always @(posedge clk) begin cyc <= cyc + 1; si <= si + 1; arst_n <= cyc > 8; start_i <= cyc > 12; end",
      "  always @(posedge fclk) fi <= fi + 1;"]
for w, n in data_in:
    ep = f"{w - 1}"
    L.append(f"  always @(posedge clk) begin ref_{n} <= seq_{n}[si & 4095]; ref_{n}[{ep}] <= cyc > 20; end")
    L.append(f"  always @(posedge fclk) begin src_{n} <= seq_{n}[fi & 4095]; src_{n}[{ep}] <= fi > 20; end")
# fclk counter fi starts PHASE later; align: the landed source must carry the SAME index per launch edge as the ref
conn_l, conn_r = [], []
for d, w, n in LP:
    if n == "clk" or re.fullmatch(r"clk_t\d+", n):
        conn_l.append(f".{n}(clk)")
    elif n in ("arst_n", "start_i"):
        conn_l.append(f".{n}({n})")
    elif n.startswith("fclk_in_"):
        conn_l.append(f".{n}(fclk)")
    elif n.startswith("cland_dn_ready_"):
        conn_l.append(f".{n}(1'b1)")
    elif n.startswith("cland_dn_fault_"):
        conn_l.append(f".{n}(1'b0)")
    elif d == "input":
        conn_l.append(f".{n}({'src_' if n in landed_in else 'ref_'}{n})")
    elif n.startswith(("fclk_out_", "cland_up_", "rst_o", "start_o")) or n.startswith("landing_"):
        L.append(f"  wire lx_{n};")
        conn_l.append(f".{n}(lx_{n})")
    else:
        conn_l.append(f".{n}(l_{n})")
for d, w, n in RP:
    if n == "clk" or re.fullmatch(r"clk_t\d+", n):
        conn_r.append(f".{n}(clk)")
    elif n in ("arst_n", "start_i"):
        conn_r.append(f".{n}({n})")
    elif d == "input":
        conn_r.append(f".{n}(ref_{n})")
    elif n.startswith(("rst_o", "start_o")):
        L.append(f"  wire rx_{n};")
        conn_r.append(f".{n}(rx_{n})")
    else:
        conn_r.append(f".{n}(r_{n})")
L.append(f"  {mod} u_l ({', '.join(conn_l)});")
L.append(f"  {mod}__ref u_r ({', '.join(conn_r)});")
ups = [n for _, _, n in LP if n.startswith("cland_up_fault_")]
upr = [n for _, _, n in LP if n.startswith("cland_up_ready_")]
L.append("  always @(posedge clk) begin")
for w, n in outs:
    L.append(f"    for (int j = 7; j > 0; j--) h_{n}[j] <= h_{n}[j - 1]; h_{n}[0] <= r_{n};")
L.append("    if (cyc > 80) begin")
for k_i, k in enumerate((K - 1, K, K + 1)):
    cond = " || ".join(f"(l_{n} !== h_{n}[{k - 1}])" for _, n in outs)
    L.append(f"      if ({cond}) bad[{k_i}] = bad[{k_i}] + 1;")
if ups:
    L.append(f"      if ({' || '.join('lx_' + n for n in ups)}) faults = faults + 1;")
if upr:
    L.append(f"      if ({' && '.join('lx_' + n for n in upr)}) seen_ready = 1;")
else:
    L.append("      seen_ready = 1;")
L += ["    end",
      "    if (cyc == 1200) begin",
      f"      $display(\"BENCH {mod} PHASE=%0d landed_inputs={len(landed_in)} outputs={len(outs)} mism_K-1=%0d mism_K=%0d mism_K+1=%0d faults=%0d ready=%0d\", PHASE, bad[0], bad[1], bad[2], faults, seen_ready);",
      "      if (bad[1] == 0 && bad[0] > 0 && bad[2] > 0 && faults == 0 && seen_ready) $display(\"PASS\"); else $display(\"FAIL\");",
      "      $finish;", "    end", "  end", "endmodule"]
(out / f"tb_{mod}.sv").write_text("\n".join(L) + "\n")
print(out / f"tb_{mod}.sv", "landed inputs", landed_in, "outputs", [n for _, n in outs])

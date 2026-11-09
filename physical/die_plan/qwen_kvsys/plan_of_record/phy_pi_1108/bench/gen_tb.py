#!/usr/bin/env python3
"""PHY RE-FORM bench: lock-step testbench OLD bound wrapper vs NEW (re-formed) wrapper, same stimulus.

Checks every cycle (after the first 4):
  * the six PI out buses: NEW data(t) == OLD data(t-DEPTH) (all bits, X-free), NEW epoch(t) == OLD epoch(t-DEPTH) except
    in the DEPTH cycles after an asynchronous reset assertion (every station epoch is async-reset, so the epoch drops at
    once; the data pipeline has no reset);
  * every other output: NEW == OLD in the same cycle;
  * probe (reported, must be 0 for the hrst relay to be invisible): cycles where the host-reset face register epoch
    u_bin_i_host_hbm_rst_n.eq differs between OLD and NEW (only kv3_phy).
Stimulus: random data inputs every cycle; arst_n low 10, release, async assertion at 300 for 7 cycles, release, run to
700; START (cland_tstart_in / cland_fstart_in_*) high from cycle 3 after reset (earliest start: the landing reset chain
is the only guard) or from cycle 40 (--late-start); straps constant; forwarded clocks = clk.
usage: gen_tb.py OLD.sv MODULE DEPTH OUT_TB.sv [--late-start]
"""
import re
import sys
from pathlib import Path

PI = ("o_phy_Q__sN_fhN", "o_phy_Q__sN_piN", "o_phy_Q__sN_piN_d1", "o_phy_Q__sN_piN_d2", "o_phy_Q__sN_piN_d3",
      "o_phy_Q__sN_rhN")


def ports(txt):
    head = re.search(r"^module\s+\w+\s*\((.*?)^\);", txt, re.S | re.M)[1]
    out = []
    for m in re.finditer(r"\b(input|output)\s+wire\s+(?:\[(\d+):0\]\s*)?(\w+)", head):
        out.append((m[1], int(m[2]) + 1 if m[2] else 1, m[3]))
    return out


def main(argv):
    late = "--late-start" in argv
    argv = [a for a in argv if a != "--late-start"]
    oldf, mod, depth, outf = argv
    depth = int(depth)
    P = ports(Path(oldf).read_text())
    L = ["`timescale 1ns/1ps", "`default_nettype none", "module tb;", "  reg clk = 0; always #5 clk = ~clk;",
         "  reg arst_n = 0; reg start = 0; integer cyc = 0; integer errs = 0; integer probe = 0; integer asrt = -100;"]
    conn = []
    for d, w, n in P:
        if d == "input":
            if n == "clk":
                conn.append((n, "clk"))
            elif n == "arst_n":
                conn.append((n, "arst_n"))
            elif n.startswith("fclk_in"):
                conn.append((n, "clk"))
            elif "start" in n:
                conn.append((n, "start"))
            elif n.startswith("ri_") and n.endswith("rst_n"):
                conn.append((n, f"{{{w}{{arst_n}}}}"))
            elif n.startswith("strap_ca_k"):
                L.append(f"  wire [{w - 1}:0] s_{n} = {w}'d4;")
                conn.append((n, f"s_{n}"))
            elif n.startswith("strap"):
                L.append(f"  wire [{w - 1}:0] s_{n} = '0;")
                conn.append((n, f"s_{n}"))
            else:
                L.append(f"  reg [{w - 1}:0] r_{n};")
                conn.append((n, f"r_{n}"))
        else:
            L.append(f"  wire [{w - 1}:0] o_{n}, n_{n};")
    L.append(f"  {mod} u_old (" + ", ".join(f".{n}({e})" for n, e in conn) + ", "
             + ", ".join(f".{n}(o_{n})" for d, w, n in P if d == "output") + ");")
    L.append(f"  {mod}_new u_new (" + ", ".join(f".{n}({e})" for n, e in conn) + ", "
             + ", ".join(f".{n}(n_{n})" for d, w, n in P if d == "output") + ");")
    pis = [(w, n) for d, w, n in P if d == "output" and n in PI]
    for w, n in pis:
        L.append(f"  reg [{w - 1}:0] h_{n} [0:{depth}];")
    L.append("  integer k;")
    L.append("  always @(posedge clk) begin")
    for w, n in pis:
        L.append(f"    for (k = {depth}; k > 0; k = k - 1) h_{n}[k] <= h_{n}[k-1]; h_{n}[0] <= o_{n};")
    L.append("  end")
    # compare just before the next rising edge (outputs settled)
    L.append("  always @(negedge clk) if (cyc > 4) begin")
    for w, n in pis:
        L.append(f"    if (n_{n}[{w - 2}:0] !== h_{n}[{depth - 1}][{w - 2}:0]) begin errs = errs + 1; "
                 f"if (errs < 20) $display(\"MISMATCH data {n} cyc %0d new %h old-{depth} %h\", cyc, n_{n}[{w - 2}:0], "
                 f"h_{n}[{depth - 1}][{w - 2}:0]); end")
        L.append(f"    if (!(cyc >= asrt && cyc < asrt + {depth} + 1) && n_{n}[{w - 1}] !== h_{n}[{depth - 1}][{w - 1}]) "
                 f"begin errs = errs + 1; if (errs < 20) $display(\"MISMATCH epoch {n} cyc %0d new %b old-{depth} %b\", "
                 f"cyc, n_{n}[{w - 1}], h_{n}[{depth - 1}][{w - 1}]); end")
    for d, w, n in P:
        if d == "output" and n not in PI:
            L.append(f"    if (n_{n} !== o_{n}) begin errs = errs + 1; if (errs < 20) "
                     f"$display(\"MISMATCH {n} cyc %0d new %h old %h\", cyc, n_{n}, o_{n}); end")
    if "host_hbm_rst_n" in " ".join(n for _, _, n in P):
        L.append("    if (u_new.u_bin_i_host_hbm_rst_n.eq !== u_old.u_bin_i_host_hbm_rst_n.eq) begin probe = probe + 1; if (probe < 12) $display(\"PROBE host eq cyc %0d new %b old %b arst_n %b\", cyc, u_new.u_bin_i_host_hbm_rst_n.eq, u_old.u_bin_i_host_hbm_rst_n.eq, arst_n); end")
    L.append("  end")
    rnd = [(w, n) for d, w, n in P if d == "input" and ("r_" + n) in " ".join(e for _, e in conn)]
    L.append("  task drive; begin")
    for w, n in rnd:
        L.append(f"    for (k = 0; k < {w}; k = k + 32) r_{n}[k +: 32] = $random;" if w > 32 else
                 f"    r_{n} = $random;")
    L.append("  end endtask")
    L.append("  initial begin")
    L.append("    drive;")
    L.append("    repeat (700) begin @(negedge clk); cyc = cyc + 1; drive;")
    L.append("      if (cyc == 10) arst_n = 1;")
    L.append("      if (cyc == 300) begin #2 arst_n = 0; asrt = cyc + 1; end")
    L.append("      if (cyc == 307) arst_n = 1;")
    s = 40 if late else 3
    L.append(f"      if (cyc == 10 + {s}) start = 1;")
    L.append("    end")
    L.append("    $display(\"BENCH %s errs %0d host_eq_probe %0d up_ready_old %b new %b\", errs ? \"FAIL\" : \"PASS\", "
             "errs, probe, o_cland_up_ready, n_cland_up_ready);")
    L.append("    $finish;")
    L.append("  end")
    L.append("endmodule")
    Path(outf).write_text("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

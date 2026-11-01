"""old-vs-new 4-state equivalence-from-reset testbench generator (iverilog).
usage: mktb.py ports.json top_new top_old 'PARAMS_NEW' 'PARAMS_OLD' cycles seed out.sv [rst_ports] [const port=val ...]
Both instances get the same random inputs every cycle; reset ports are held asserted (0) for 6 edges, then
released.  Every output bit is compared on every cycle after release: a bit that is X/Z in OLD may be anything in
NEW (refinement of an unknown power-up); a bit that is known in OLD must be identical (===) in NEW, else MISMATCH.
Clocks: every port whose name starts with 'clk' toggles together."""
import json, sys
ports = json.load(open(sys.argv[1]))
top_n, top_o, pn, po, cyc, seed, out = sys.argv[2:9]
rst = set((sys.argv[9] if len(sys.argv) > 9 else "rst_n").split(","))
const = dict(a.split("=") for a in sys.argv[10:])
L = ["`timescale 1ns/1ps", "module tb;", "  reg clk = 0;"]
ins = [(n, w) for n, d, w in ports if d == "input"]
outs = [(n, w) for n, d, w in ports if d == "output"]
for n, w in ins:
    if n.startswith("clk"):
        continue
    L.append(f"  reg [{w-1}:0] {n};")
for n, w in outs:
    L.append(f"  wire [{w-1}:0] {n}_n, {n}_o;")
def conns(sfx):
    c = []
    for n, w in ins:
        c.append(f".{n}({('{%d{clk}}' % w) if n.startswith('clk') else n})")
    for n, w in outs:
        c.append(f".{n}({n}_{sfx})")
    return ", ".join(c)
L.append(f"  {top_n} #({pn}) u_n ({conns('n')});")
L.append(f"  {top_o} #({po}) u_o ({conns('o')});")
L += ["  integer cyc, i, bad = 0, xref = 0, cmp = 0, seed = %s;" % seed,
      "  task automatic rnd; begin"]
for n, w in ins:
    if n.startswith("clk") or n in rst:
        continue
    if n in const:
        L.append(f"    {n} = {const[n]};")
    else:
        L.append(f"    for (i = 0; i < {w}; i = i + 32) {n}[i +: 32] = $random(seed);" if w > 32 else f"    {n} = $random(seed);")
L += ["  end endtask",
      "  initial begin"]
for n in rst:
    if any(p == n for p, _ in ins):
        L.append(f"    {n} = 0;")
L += ["    rnd;",
      "    for (cyc = 0; cyc < %s; cyc = cyc + 1) begin" % cyc,
      "      #1 clk = 1; #1;",
      "      if (cyc >= 6) begin"]
for n, w in outs:
    L += [f"        for (i = 0; i < {w}; i = i + 1) begin",
          f"          if ({n}_o[i] === 1'bx || {n}_o[i] === 1'bz) begin if ({n}_n[i] !== {n}_o[i]) xref = xref + 1; end",
          f"          else begin cmp = cmp + 1; if ({n}_n[i] !== {n}_o[i]) begin bad = bad + 1; if (bad < 20) $display(\"MISMATCH cyc %0d {n}[%0d] new %b old %b\", cyc, i, {n}_n[i], {n}_o[i]); end end",
          "        end"]
L += ["      end",
      "      #1 clk = 0;"]
for n in rst:
    if any(p == n for p, _ in ins):
        L.append(f"      if (cyc == 5) {n} = {{$bits({n}){{1'b1}}}};")
L += ["      rnd; #1;",
      "    end",
      "    $display(\"RESULT cycles %0d compared_bits %0d mismatches %0d old_X_refined_by_new %0d\", " + cyc + ", cmp, bad, xref);",
      "    $finish;",
      "  end",
      "endmodule"]
open(out, "w").write("\n".join(L) + "\n")

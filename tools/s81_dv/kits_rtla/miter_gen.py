#!/usr/bin/env python3
"""S81-KITS-RTLA (2026-10-24): old-vs-new lockstep miter for a pin-register RTL fix.

    python3 miter_gen.py OUT_DIR TOP OLD_FILE[:mod,mod...] [--cycles N] [--seed S] [--param K=V ...]

Extracts module TOP (plus the listed extra modules) from OLD_FILE -- the exact RTL the c2 kit synthesised -- renames
every one of them <name>_old (references inside the extracted text too) and writes OUT_DIR/old_top.sv.  Then writes
OUT_DIR/tb_miter.sv: TOP_old and the fixed TOP (from the repo sources the caller compiles) on the SAME random stimulus
(async reset low 8 edges, then random pulses; 1-bit inputs random with a per-phase density 1/16 .. 1/2; buses random),
every output bit compared with !== on every posedge after reset (both are cycle-exact by construction: 0-cycle fix).
Narrowed outputs (OWNER DECISION 8: constant pins dropped) compare the old bits under the new range; --pack BUS compares
a packed BF16 bus (new[16k+j] == old[32k+16+j]); the dropped old bits are constant (TIELO in the raw netlists).
Prints MITER PASS|FAIL top T cycles N mismatches M, plus per-output activity (cycles high / value changes) so the
bench shows that the fixed pins were exercised.  Exit is the caller's (grep MITER PASS)."""
import argparse
import re
from pathlib import Path


def block(text, name):
    m = re.search(r"^\s*(\(\*[^)]*\*\)\s*)?module\s+%s\b" % re.escape(name), text, re.M)
    assert m, name
    e = re.search(r"^\s*endmodule\b", text[m.start():], re.M)
    return text[m.start():m.start() + e.end()]


def ports(text, name):
    hdr = block(text, name)
    hdr = re.sub(r"//[^\n]*", "", hdr)
    hdr = re.sub(r"\(\*.*?\*\)", "", hdr, flags=re.S)
    # ANSI port list: after the parameter list "#( ... )" the next "( ... );"
    i = hdr.index("module")
    j = hdr.index("#", i) if re.match(r"module\s+\w+\s*#", hdr[i:]) else None
    k = hdr.index("(", j if j is not None else i)
    if j is not None:
        d = 0
        for p in range(k, len(hdr)):
            d += hdr[p] == "("
            d -= hdr[p] == ")"
            if d == 0:
                k = hdr.index("(", p)
                break
    e = hdr.index(");", k)
    plist = hdr[k + 1:e]
    out, cur = [], None
    for tok in re.split(r",", plist):
        tok = tok.strip()
        m = re.match(r"(input|output)\s+(?:wire|reg|logic)?\s*(?:signed\s*)?(\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(\w+)$", tok)
        if m:
            cur = (m.group(1), int(m.group(3)) if m.group(2) else 0, int(m.group(4)) if m.group(2) else 0)
            out.append(cur + (m.group(5),))
        elif re.match(r"^\w+$", tok) and cur:
            out.append(cur + (tok,))
        elif tok:
            raise ValueError("port token %r" % tok)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("top")
    ap.add_argument("old", help="OLD_FILE[+OLD_FILE...][:extra,modules]")
    ap.add_argument("--new", required=True, help="fixed source file holding TOP (port list)")
    ap.add_argument("--cycles", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--pack", action="append", default=[],
                    help="output bus packed in the fix (OWNER DECISION 8): new[16k+j] == old[32k+16+j], 8 lanes")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f, _, extra = a.old.partition(":")
    mods = [a.top] + [x for x in extra.split(",") if x]
    ot = "\n".join(Path(x).read_text() for x in f.split("+"))
    txt = "\n".join(block(ot, m) for m in mods)
    for m in sorted(mods, key=len, reverse=True):
        txt = re.sub(r"\b%s\b" % re.escape(m), m + "_old", txt)
    (out / "old_top.sv").write_text("`timescale 1ns/1ps\n" + txt + "\n")
    Pn = ports(Path(a.new).read_text(), a.top)
    Po = ports(txt, a.top + "_old")
    assert [(d, n) for d, _, _, n in Pn] == [(d, n) for d, _, _, n in Po], ("port lists differ", Pn, Po)
    assert [p for p in Pn if p[0] == "input"] == [p for p in Po if p[0] == "input"], "input ranges differ"
    O = {n: (m, l) for d, m, l, n in Po}
    # (dir, width, name) for the stimulus; outputs carry old / new ranges for the compare (narrowed / packed buses)
    P = [(d, m - l + 1, n) for d, m, l, n in Pn]
    NR = {n: (m, l) for d, m, l, n in Pn}
    ins = [p for p in P if p[0] == "input" and p[2] not in ("clk", "ck", "rst_n")]
    outs = [p for p in P if p[0] == "output"]
    clk = "ck" if any(p[2] == "ck" for p in P) else "clk"
    has_rst = any(p[2] == "rst_n" for p in P)

    def old_view(n):
        """the old output's bits that correspond to the new port, as an expression"""
        om, ol = O[n]
        nm, nl = NR[n]
        if n in a.pack:
            return "{" + ", ".join("%s_a[%d:%d]" % (n, 32 * k + 31, 32 * k + 16) for k in range(7, -1, -1)) + "}"
        if (om, ol) == (nm, nl):
            return "%s_a" % n
        assert ol <= nl <= nm <= om, (n, O[n], NR[n])
        return "%s_a[%d:%d]" % (n, nm, nl)

    def old_dropped(n):
        """the old output's bits the fix dropped (must be constant 0), or None"""
        om, ol = O[n]
        nm, nl = NR[n]
        if n in a.pack:
            return "(%s_a & {8{32'h0000ffff}})" % n
        if (om, ol) == (nm, nl):
            return None
        parts = (["%s_a[%d:%d]" % (n, om, nm + 1)] if om > nm else []) + (["%s_a[%d:%d]" % (n, nl - 1, ol)] if nl > ol else [])
        return "{" + ", ".join(parts) + "}"
    par = ", ".join(".%s(%s)" % tuple(x.split("=", 1)) for x in a.param)
    par = " #(%s)" % par if par else ""
    L = ["`timescale 1ns/1ps", "module tb_miter;", "    reg %s = 0; always #1 %s = ~%s;" % (clk, clk, clk),
         "    reg rst_n = 0;", "    integer s, cyc, bad, dens, rp;"]
    for d, w, n in ins:
        L.append("    reg [%d:0] %s = 0;" % (w - 1, n))
    for d, w, n in outs:
        L.append("    wire [%d:%d] %s_a; wire [%d:%d] %s_b; integer act_%s = 0, chg_%s = 0;"
                 % (O[n][0], O[n][1], n, NR[n][0], NR[n][1], n, n, n))
    conn = lambda sfx: ", ".join([".%s(%s)" % (clk, clk)] + ([".rst_n(rst_n)"] if has_rst else []) +
                                 [".%s(%s)" % (n, n) for d, w, n in ins] + [".%s(%s_%s)" % (n, n, sfx) for d, w, n in outs])
    L.append("    %s_old%s u_old (%s);" % (a.top, par, conn("a")))
    L.append("    %s%s u_new (%s);" % (a.top, par, conn("b")))
    L.append("    function [31:0] rnd32; input integer dummy; begin rnd32 = $random(s); end endfunction")
    L.append("    initial begin")
    L.append("        s = %d; bad = 0; dens = 4; rp = 0;" % a.seed)
    L.append("        repeat (8) @(negedge %s); rst_n = 1;" % clk)
    L.append("        for (cyc = 0; cyc < %d; cyc = cyc + 1) begin" % a.cycles)
    L.append("            @(negedge %s);" % clk)
    L.append("            if (cyc % 2000 == 0) dens = $random(s) & 7;               // 1-bit input density phase (0 = quiet: sticky state must hold)")
    L.append("            if (cyc % 997 == 500) rst_n = 0; else rst_n = 1;          // reset pulses mid-run")
    for d, w, n in ins:
        if w == 1:
            L.append("            %s = (($random(s) & 15) < dens);" % n)
        else:
            nw = (w + 31) // 32
            L.append("            %s = {%s};" % (n, ", ".join(["rnd32(0)"] * nw)))
    L.append("        end")
    L.append("        repeat (50) @(negedge %s);" % clk)
    for d, w, n in outs:
        L.append('        $display("MITER_ACT %s w %0d cycles_nonzero %%0d changes %%0d", act_%s, chg_%s);' % (n, w, n, n))
    L.append('        $display("MITER %%s top %s cycles %%0d mismatches %%0d", bad == 0 ? "PASS" : "FAIL", cyc, bad);' % a.top)
    L.append("        $finish;")
    L.append("    end")
    L.append("    always @(posedge %s) if (cyc > 0) begin" % clk)
    for d, w, n in outs:
        L.append("        if (%s !== %s_b) begin bad = bad + 1; if (bad < 6) $display(\"MISMATCH cyc %%0d %s old %%h new %%h\", cyc, %s, %s_b); end"
                 % (old_view(n), n, n, old_view(n), n))
        L.append("        if (|%s_b) act_%s = act_%s + 1;" % (n, n, n))
        if old_dropped(n):
            L.append("        if (|%s) begin bad = bad + 1; if (bad < 6) $display(\"DROPPED_BITS_NONZERO cyc %%0d %s\", cyc); end"
                     % (old_dropped(n), n))
    L.append("    end")
    for d, w, n in outs:
        L.append("    reg [%d:%d] %s_p; always @(posedge %s) begin if (cyc > 0 && %s_p !== %s_b) chg_%s = chg_%s + 1; %s_p <= %s_b; end"
                 % (NR[n][0], NR[n][1], n, clk, n, n, n, n, n, n))
    L.append("endmodule")
    (out / "tb_miter.sv").write_text("\n".join(L) + "\n")
    print("wrote", out / "old_top.sv", out / "tb_miter.sv", "inputs", len(ins), "outputs", len(outs))


if __name__ == "__main__":
    main()

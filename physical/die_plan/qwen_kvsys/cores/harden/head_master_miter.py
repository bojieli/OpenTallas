#!/usr/bin/env python3
"""Lockstep a head strap master against an old kit at matching parent ID values.

Inputs use --port-map JSON to rename old member ports to a selected master;
--strap PORT=VALUE supplies master-only ID ports, and --force-input PORT=VALUE
holds the corresponding old ID. All declared clocks share the die clock.
Resets assert at boot and mid-run. Outputs compare every active edge, including
invalid cycles. Behavioral SRAM models preserve the old kit read/write edges.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))



def vfiles(kit):
    m = re.search(r"^export VERILOG_FILES = (.*)$", (kit / "config.mk").read_text(), re.M)
    return [Path(x).name for x in m.group(1).split()]


SRAM = """module {n} (input wire clk, input wire r_ce_in, input wire [{a1}:0] r_addr_in, output reg [{w1}:0] rd_out,
 input wire w_ce_in, input wire [{a1}:0] w_addr_in, input wire [{w1}:0] wd_in, input wire [{w1}:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [{w1}:0] m [0:{d1}];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("out")
    ap.add_argument("--new-mod-file")
    ap.add_argument("--cycles", type=int, default=20000)
    ap.add_argument("--port-map", help="JSON old-port -> new-port mapping")
    ap.add_argument("--force-input", action="append", default=[], help="old input PORT=VALUE driven identically to mapped new input")
    ap.add_argument("--new-mod", help="new top module name (strap master: kv3_astk)")
    ap.add_argument("--strap", action="append", default=[], help="NEW-only input PORT=VALUE held constant (ID straps)")
    ap.add_argument("--no-drops", action="store_true", help="old kit already carries the am g drop (compare 1:1)")
    a = ap.parse_args()
    old, new, out = Path(a.old), Path(a.new), Path(a.out)
    shutil.rmtree(out, ignore_errors=True)
    (out / "o").mkdir(parents=True)
    (out / "n").mkdir()
    cjo = json.load(open(old / "core.json"))
    cjn = json.load(open(new / "core.json"))
    mod = cjo["module"]
    drops = {}
    nmod = a.new_mod or mod
    straps = dict(s.split("=", 1) for s in a.strap)
    portmap = json.load(open(a.port_map)) if a.port_map else {}
    forced = dict(s.split("=",1) for s in a.force_input)
    extra_new = set(cjn["port_decl"]) - {portmap.get(p,p) for p in cjo["port_decl"]}
    if extra_new != set(straps):
        raise SystemExit(f"new-only ports {sorted(extra_new)} must all be --strap PORT=VAL (got {sorted(straps)})")
    fo, fn = vfiles(old), vfiles(new)
    names = set()
    for f in fo:
        names |= set(re.findall(r"^\s*module\s+(\w+)", (old / "rtl" / f).read_text(), re.M))
    pat = re.compile(r"\b(" + "|".join(sorted(names, key=len, reverse=True)) + r")\b")
    srams = set()
    for f in fo:
        (out / "o" / f).write_text(pat.sub(lambda m: m.group(1) + "_o", (old / "rtl" / f).read_text()))
    for f in fn:
        shutil.copy(new / "rtl" / f, out / "n" / f)
    if a.new_mod_file:
        shutil.copy(a.new_mod_file, out / "n" / f"{nmod}.sv")
    for p in list((old / "rtl").glob("*.svh")) + list((old / "rtl").glob("*.vh")):
        shutil.copy(p, out / "o" / p.name)
        shutil.copy(p, out / "n" / p.name)
    for f in fo + fn:
        mm = re.match(r"(ot_sram_1r1w_(\d+)x(\d+)_m1_r2c2)_bb\.v$", f)
        if mm:
            srams.add((mm.group(1), int(mm.group(2)), int(mm.group(3))))
    models = []
    for n, d, w in sorted(srams):
        for sfx in ("", "_o"):
            models.append(SRAM.format(n=n + sfx, a1=(d - 1).bit_length() - 1, w1=w - 1, d1=d - 1))
    (out / "sram_models.sv").write_text("`timescale 1ns/1ps\n" + "".join(models))
    src = [f"o/{f}" for f in fo if not f.endswith("_bb.v")] + [f"n/{f}" for f in fn if not f.endswith("_bb.v")]
    (out / "files.f").write_text("\n".join(src + ["sram_models.sv", "tb.sv"]) + "\n")
    # ---- testbench ----
    ins = {p: d for p, d in cjo["port_decl"].items() if d[0] == "input"}
    outs = {p: d for p, d in cjo["port_decl"].items() if d[0] == "output"}
    clk = [p for p in ins if p in ("ck", "clk") or p.endswith("__clk")]
    rst = [p for p in ins if re.search(r"rst", p)]
    assert clk and rst, (clk, rst)
    L = ["`timescale 1ns/1ps", "module tb;", "  reg ck = 0; always #0.5 ck = ~ck; reg rn = 0;"]
    conn_o, conn_n, cmp_o, cmp_n, drop_bits = [], [], [], [], []
    for p, (dr, hi, lo) in cjo["port_decl"].items():
        np = portmap.get(p,p)
        if p in clk:
            conn_o.append(f".{p}(ck)")
            conn_n.append(f".{np}(ck)")
            continue
        if p in rst:
            conn_o.append(f".{p}(rn)")
            conn_n.append(f".{np}(rn)")
            continue
        nhi = cjn["port_decl"][np][1]
        if dr == "input":
            hi = 0 if hi is None else hi
            L.append(f"  reg [{hi}:0] i_{p} = 0;")
            if p in drops:
                d = drops[p]
                L.append(f"  wire [{nhi}:0] in_{p} = {{i_{p}[{hi}:{d + 1}], i_{p}[{d - 1}:0]}};")
                L.append(f"  wire [{hi}:0] io_{p} = {{i_{p}[{hi}:{d + 1}], 1'b0, i_{p}[{d - 1}:0]}};")
                conn_o.append(f".{p}(io_{p})")
                conn_n.append(f".{np}(in_{p})")
            else:
                conn_o.append(f".{p}(i_{p})")
                conn_n.append(f".{np}(i_{p})")
        else:
            hi = 0 if hi is None else hi
            nhi = 0 if nhi is None else nhi
            L.append(f"  wire [{hi}:0] o_{p}; wire [{nhi}:0] n_{p};")
            conn_o.append(f".{p}(o_{p})")
            conn_n.append(f".{np}(n_{p})")
            if p in drops:
                d = drops[p]
                cmp_o.append(f"o_{p}[{hi}:{d + 1}], o_{p}[{d - 1}:0]")
                drop_bits.append(f"o_{p}[{d}]")
            else:
                cmp_o.append(f"o_{p}")
            cmp_n.append(f"n_{p}")
    L.append(f"  {mod}_o u_o ({', '.join(conn_o)});")
    for p, v in straps.items():
        conn_n.append(f".{p}({v})")
    L.append(f"  {nmod} u_n ({', '.join(conn_n)});")
    L.append(f"  wire [99999:0] vo = {{{', '.join(cmp_o)}}};")
    L.append(f"  wire [99999:0] vn = {{{', '.join(cmp_n)}}};")
    L.append(f"  wire dz = |{{{', '.join(drop_bits)}}};" if drop_bits else "  wire dz = 1'b0;")
    tog = []
    for p in drops:
        if outs.get(p):
            tog.append(f"o_{p}")
        else:
            tog.append(f"i_{p}")
    L.append(f"  wire [99999:0] tg = {{{', '.join(tog)}}}; reg [99999:0] tg_q = 0;" if tog else
             "  wire [99999:0] tg = 0; reg [99999:0] tg_q = 0;")
    L.append("  integer n, mis = 0, dzc = 0, edges = 0, tgc = 0;")
    L.append("  always @(negedge ck) if (rn) begin edges = edges + 1;")
    L.append("    if (vo !== vn) begin mis = mis + 1; if (mis < 6) $display(\"MISMATCH edge=%0d\", edges); end")
    L.append("    if (dz !== 1'b0) begin dzc = dzc + 1; if (dzc < 4) $display(\"DROPPED BIT NONZERO edge=%0d\", edges); end")
    L.append("    if (tg !== tg_q) tgc = tgc + 1; tg_q = tg; end")
    L.append("  initial begin")
    L.append(f"    for (n = 0; n < {a.cycles}; n = n + 1) begin")
    L.append("      @(posedge ck); #0.1;")
    L.append(f"      rn = !(n < 4 || (n > {a.cycles // 2} && n < {a.cycles // 2 + 3}));")
    for p, (dr, hi, lo) in ins.items():
        if p in clk or p in rst:
            continue
        if p in forced:
            L.append(f"      i_{p} = {forced[p]};")
            continue
        hi = 0 if hi is None else hi
        words = (hi + 32) // 32
        L.append(f"      i_{p} = {{{', '.join(['$urandom'] * words)}}}; i_{p}[0] = ($urandom % 4 == 0);")
    L.append("    end")
    L.append(f"    $display(\"CORE MITER {mod} %s mismatches=%0d dropped_bit_nonzero=%0d edges=%0d dropped_port_changes=%0d\","
             f" (mis == 0 && dzc == 0 && {'tgc > 100' if tog else 'edges > 100'}) ? \"PASS\" : \"FAIL\", mis, dzc, edges, tgc);")
    L.append("    $finish;")
    L.append("  end")
    L.append("endmodule")
    (out / "tb.sv").write_text("\n".join(L) + "\n")
    print(out, len(src), "files", sorted(srams))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""S81-LNB-1 11-08: formal proof kit for kit_ln_copies.py (class LN-BROADCAST), old bound RTL vs new.

The transform is local, so the proof has three parts:
  (1) TEXT   every line of the new bound module outside the edits is byte-identical to the old one: removing the
             copy block and undoing the slice / rst_n / REGIONS / width edits gives the old text exactly;
  (2) CF     a yosys miter of the original native memory (gold) against the copy modules (gate), all write inputs
             shared, compare = every consumer's slice (gold RD_DATA[hi:lo] vs the copy's output word), equal initial
             state (sat -set-init-zero on both sides, the LEC convention), k-induction (sat -tempinduct);
  (3) RELAY  a miter of the old ot_rst_relay (REGIONS R) bit k against every new lane bit of the widened relay.
Mutants (each must FAIL its proof): cf_word (one copy reads the next word), cf_drop (one write statement dropped),
cf_order (two write statements of one bit swapped across ports), relay_early (lane bit taken from sync_q, one stage
early).
  python3 kit_ln_copies_proof.py OLD.sv NEW.sv MODS.sv REPORT.json NATIVE_DIR OT_RST_RELAY.sv --out DIR
writes DIR/{text.json, cf_<case>/(miter.sv, prove.ys), relay_<case>/...} and DIR/run.sh (yosys from $YOSYS)."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_ln_copies as K  # noqa: E402


def text_check(old, new, rep):
    """(1): undo the edits on NEW, compare with OLD"""
    t = new
    cf, rl = rep.get("cf"), rep.get("relay")
    if cf:
        a = t.index("    // S81-LNB-1 kit_ln_copies:")
        b = a
        for _ in range(1 + 2 * cf["readers"]):
            b = t.index("\n", b) + 1
        nat = K.parse_native(Path(cf["native_file"]).read_text())
        rd_of = {}
        for (hi, lo), n in nat["reads"].items():
            rd_of.setdefault(n, []).append((hi, lo))
        ww = nat["ww"]
        # rebuild the original instance line from the first copy's connections
        first = t[a:b].split("\n")[2]
        conns = re.search(r"\((\.RD_DATA.*)\);\s*$", first).group(1)
        conns = re.sub(r"\.RD_DATA\(\w+\)", "", conns, count=1).lstrip(", ")
        olds = re.search(r"^([ \t]*)(ot_bind_native_[0-9a-f]{24}) " + re.escape(cf["mem"]) + r" \((.*)\);$", old, re.M)
        t = t[:a] + olds.group(0) + "\n" + t[b:]
        rdw = re.search(r"\.RD_DATA\((\w+)\)", olds.group(3)).group(1)
        if olds.group(3) != f".RD_DATA({rdw}), " + conns:
            return False, "copy connections differ from the original instance"
        # slices: restore per consumer, using the old text as the oracle of which original read word range was used
        for c in cf["copies"]:
            wn = f"lnc_{c['consumer']}_RD"
            om = re.search(r"^[ \t]*assign\s+" + re.escape(c["consumer"]) + r"\s*=.*$", old, re.M).group(0)
            nm = re.search(r"^[ \t]*assign\s+" + re.escape(c["consumer"]) + r"\s*=.*$", t, re.M)
            olds_sl = re.findall(re.escape(rdw) + r"\[(\d+):(\d+)\]", om)
            news_sl = re.findall(re.escape(wn) + r"\[(\d+):(\d+)\]", nm.group(0))
            if len(olds_sl) != len(news_sl):
                return False, f"{c['consumer']}: slice count differs"
            for (oh, ol), (nh, nl) in zip(olds_sl, news_sl):
                word = nat["reads"][(int(oh), int(ol))]
                i = c["words"].index(word)
                if (int(nh), int(nl)) != (ww * i + ww - 1, ww * i):
                    return False, f"{c['consumer']}: slice [{oh}:{ol}] (word {word}) -> copy [{nh}:{nl}] wrong"
            t = t[:nm.start()] + om + t[nm.end():]
        dl = re.search(r"^[ \t]*wire\s+\[\d+:0\]\s+" + re.escape(rdw) + r"\s*;[ \t]*\n", old, re.M)
        # the declaration was removed: put it back at the same place (the line before it in OLD anchors it)
        prev = old[:dl.start()].rsplit("\n", 2)[-2] + "\n"
        k = t.index(prev) + len(prev)
        t = t[:k] + dl.group(0) + t[k:]
    if rl:
        R, N, rw = rl["regions_original"], rl["regions"], None
        for L in rl["lanes"]:
            rw = L["rst_n"].split("[")[0]
            ln = re.escape(L["instance"])
            m = re.search(r"(" + ln + r"\s*\((?:[^;])*?\.rst_n\()" + re.escape(L["rst_n"]) + r"\)", t)
            om = re.search(r"(" + ln + r"\s*\((?:[^;])*?\.rst_n\()([^)]*)\)", old)
            t = t[:m.start()] + m.group(1) + om.group(2) + ")" + t[m.end():]
        t = t.replace(f".REGIONS({N}), .SYNC_STAGES", f".REGIONS({R}), .SYNC_STAGES", 1)
        t = re.sub(r"(wire\s+)\[" + str(N - 1) + r":0\](\s+" + re.escape(rw) + r"\s*;)", rf"\g<1>[{R - 1}:0]\2", t, count=1)
    return t == old, "byte-identical outside the edits" if t == old else "residual difference"


def cf_case(nat_text, nat, mods, rep, mut=None):
    """miter: gold native memory vs the copy modules; mut in (None, 'cf_word', 'cf_drop', 'cf_order')"""
    cf = rep["cf"]
    ww = nat["ww"]
    if mut:
        first = cf["copies"][0]["module"]
        name_rx = re.compile(r"(module " + first + r"\(.*?endmodule\n)", re.S)
        body = name_rx.search(mods).group(1)
        if mut == "cf_word":
            ws = cf["copies"][0]["words"]
            nb = re.sub(r"assign RD_DATA\[(\d+):(\d+)\] = w" + str(ws[0]) + ";",
                        lambda m: f"assign RD_DATA[{m.group(1)}:{m.group(2)}] = w{ws[1]};", body, count=1)
        elif mut == "cf_drop":
            ls = body.split("\n")
            i = next(j for j, x in enumerate(ls) if "<=" in x and "==" in x)
            nb = "\n".join(ls[:i] + ls[i + 1:])
        else:
            # swap two writes of the same bit with DIFFERENT data (same data = an equivalent, useless mutant)
            ls = body.split("\n")
            wr = [(k, re.search(r"(w\d+\[\d+\]) <= (WR_DATA\[\d+\])", x)) for k, x in enumerate(ls)]
            wr = [(k, m.groups()) for k, m in wr if m]
            i, j = next((i, j) for n, (i, (t1, d1)) in enumerate(wr) for (j, (t2, d2)) in wr[n + 1:] if t1 == t2 and d1 != d2)
            ls[i], ls[j] = ls[j], ls[i]
            nb = "\n".join(ls)
        mods = mods.replace(body, nb)
    P = [p for p in nat["ports"] if p != "RD_DATA"]
    W = {p: nat["decl"][p][1] for p in P}
    L = ["module lnc_miter(input wire clk, " + ", ".join(f"input wire [{W[p] - 1}:0] {p}" for p in P if p != "WR_CLK") +
         ", output wire trigger);",
         f"  wire [{W['WR_CLK'] - 1}:0] WR_CLK = {{{W['WR_CLK']}{{clk}}}};",
         f"  wire [{nat['decl']['RD_DATA'][1] - 1}:0] G;",
         f"  {nat['module']} u_gold (.RD_DATA(G), " + ", ".join(f".{p}({p})" for p in P) + ");"]
    terms = []
    old_reads = {}
    for (hi, lo), n in nat["reads"].items():
        old_reads.setdefault(n, (hi, lo))
    for c in cf["copies"]:
        nw = len(c["words"])
        L.append(f"  wire [{ww * nw - 1}:0] C_{c['consumer']};")
        L.append(f"  {c['module']} u_{c['consumer']} (.RD_DATA(C_{c['consumer']}), " + ", ".join(f".{p}({p})" for p in P) + ");")
        for i, n in enumerate(c["words"]):
            hi, lo = old_reads[n]
            terms.append(f"(G[{hi}:{lo}] != C_{c['consumer']}[{ww * i + ww - 1}:{ww * i}])")
    L.append("  assign trigger = " + " | ".join(terms) + ";")
    L.append("endmodule\n")
    return nat_text + "\n" + mods + "\n" + "\n".join(L)


def relay_case(R, N, k, lanes, mut=None):
    """old relay bit k vs new relay bits R..N-1 (same rst_n_in, same clk)"""
    if mut == "relay_early":
        gate = "  wire [N-1:0] B; ot_rst_relay #(.REGIONS(N), .SYNC_STAGES(2), .TREE_STAGES(1)) u_new (.clk(clk), .rst_n_in(rst_n_in), .rst_n(B));\n" \
               "  wire [N-1:0] Bm = {B[N-1:R+1], u_new.sync_q[1], B[R-1:0]};\n"
        bsig = "Bm"
    else:
        gate = "  wire [N-1:0] B; ot_rst_relay #(.REGIONS(N), .SYNC_STAGES(2), .TREE_STAGES(1)) u_new (.clk(clk), .rst_n_in(rst_n_in), .rst_n(B));\n"
        bsig = "B"
    gate = gate.replace("N-1", str(N - 1)).replace("(N)", f"({N})").replace("R+1", str(R + 1)).replace("R-1", str(R - 1))
    terms = [f"({bsig}[{R + i}] != A[{k}])" for i in range(lanes)] + [f"({bsig}[{j}] != A[{j}])" for j in range(R)]
    return ("module relay_miter(input wire clk, input wire rst_n_in, output wire trigger);\n"
            f"  wire [{R - 1}:0] A; ot_rst_relay #(.REGIONS({R}), .SYNC_STAGES(2), .TREE_STAGES(1)) u_old (.clk(clk), .rst_n_in(rst_n_in), .rst_n(A));\n"
            + gate + "  assign trigger = " + " | ".join(terms) + ";\nendmodule\n")


YS = """read_verilog -sv {files}
hierarchy -check -top {top}
proc; opt_clean; memory -nomap; memory_map; opt -fast; flatten; opt_clean
async2sync
sat -verify -tempinduct -prove trigger 0 -set-init-zero -seq 1 -maxsteps 8 -show-inputs {top}
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("mods"); ap.add_argument("report")
    ap.add_argument("native_dir"); ap.add_argument("relay_sv"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rep = json.loads(Path(a.report).read_text())
    ok, why = text_check(Path(a.old).read_text(), Path(a.new).read_text(), rep)
    (out / "text.json").write_text(json.dumps(dict(byte_identical_outside_edits=ok, detail=why), indent=1) + "\n")
    cases = []
    mods = Path(a.mods).read_text()
    if rep.get("cf"):
        nf = Path(a.native_dir) / f"{rep['cf']['module']}.sv"
        nat_text = nf.read_text(); nat = K.parse_native(nat_text)
        for mut in (None, "cf_word", "cf_drop", "cf_order"):
            d = out / f"cf_{mut or 'base'}"; d.mkdir(exist_ok=True)
            (d / "miter.sv").write_text(cf_case(nat_text, nat, mods, rep, mut))
            (d / "prove.ys").write_text(YS.format(files="miter.sv", top="lnc_miter"))
            cases.append((d.name, mut is None))
    if rep.get("relay"):
        rl = rep["relay"]
        for mut in (None, "relay_early"):
            d = out / f"relay_{mut or 'base'}"; d.mkdir(exist_ok=True)
            (d / "miter.sv").write_text(Path(a.relay_sv).read_text() + "\n" +
                                        relay_case(rl["regions_original"], rl["regions"], rl["shared_bit"], len(rl["lanes"]), mut))
            (d / "prove.ys").write_text(YS.format(files="miter.sv", top="relay_miter").replace("-set-init-zero", "-set-init-zero"))
            cases.append((d.name, mut is None))
    sh = ["#!/bin/bash", "# expect: base cases PROVED (rc 0), mutants FAILED (rc != 0)", 'Y=${YOSYS:-yosys}', "cd \"$(dirname \"$0\")\"", "fail=0"]
    for n, expect in cases:
        sh.append(f"( cd {n} && $Y -q -l prove.log -s prove.ys >/dev/null 2>&1 ); rc=$?; echo \"{n} rc=$rc expect={'PROVE' if expect else 'FAIL'}\"")
        sh.append(f"if [ {'$rc -ne 0' if expect else '$rc -eq 0'} ]; then fail=1; fi")
    sh.append('echo "RESULT fail=$fail"; exit $fail')
    (out / "run.sh").write_text("\n".join(sh) + "\n")
    print(json.dumps(dict(text=ok, detail=why, cases=[c[0] for c in cases])))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

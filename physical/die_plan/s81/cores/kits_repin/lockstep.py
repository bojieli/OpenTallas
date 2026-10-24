#!/usr/bin/env python3
"""kits_repin: lockstep equivalence bench of a kit-local RTL patch (recipes.json rtl_patch) against the UNMODIFIED repo
module.  Gold = the repo top file (module renamed <top>__gold); gate = the kit's patched top; both get the same random
inputs every cycle (all input ports, random async resets of random length), and EVERY output bit is compared on EVERY
cycle after the first reset.  The mutant run (recipe 'mutant' applied to the patched top) must be caught (FAIL), else the
bench is blind.

    python3 lockstep.py --core ot_s81sl_vq [--cycles 200000] [--seed 1] --out DIR     -> DIR/lockstep.json
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
S81 = REPO / "physical/die_plan/s81"
sys.path.insert(0, str(HERE))
from gen_kit_repin import apply_patch, lef_dirs  # noqa: E402

VERILATOR = Path.home() / ".local/opentallas-tools/bin/verilator"


def ports(rec):
    dirs = lef_dirs(S81 / rec["stub_lef"])
    w = {}
    for p in json.load(open(S81 / rec["pins_file"]))["pins"]:
        m = re.match(r"^(.*)\[(\d+)\]$", p["name"])
        b, i = (m.group(1), int(m.group(2))) if m else (p["name"], None)
        w[b] = max(w.get(b, 0), (i + 1) if i is not None else 1)
        dirs.setdefault(b, dirs.get(p["name"]))
    d = {b: dirs.get(b) or dirs.get(f"{b}[0]") for b in w}
    return w, d


def tb(top, params, w, d, clk, rst, ract, cycles, seed):
    pr = ("#(" + ", ".join(f".{k}({v})" for k, v in params.items()) + ")") if params else ""
    ins = [b for b in w if d[b] == "INPUT" and b not in (clk, rst)]
    outs = [b for b in w if d[b] == "OUTPUT"]
    L = ["`timescale 1ns/1ps", "module tb_lockstep;", f"  reg {clk} = 0; reg {rst} = {ract};"]
    L += [f"  reg [{w[b] - 1}:0] {b} = 0;" for b in ins]
    L += [f"  wire [{w[b] - 1}:0] g_{b}, n_{b};" for b in outs]
    conn = lambda pfx: ", ".join([f".{clk}({clk})", f".{rst}({rst})"] + [f".{b}({b})" for b in ins] +
                                 [f".{b}({pfx}{b})" for b in outs])
    L += [f"  {top}__gold {pr} u_g ({conn('g_')});", f"  {top} {pr} u_n ({conn('n_')});"]
    L += ["  integer cyc = 0, mism = 0, live = 0, rsts = 0, fault_hi = 0, fault_edges = 0; reg was_f = 0;",
          "  task automatic rnd; begin"]
    for b in ins:
        n = (w[b] + 31) // 32
        L.append(f"    {b} = {{" + ", ".join(["$urandom"] * n) + "};")
    L += ["  end endtask",
          f"  always #1 {clk} = ~{clk};",
          f"  always @(posedge {clk}) begin cyc <= cyc + 1;",
          f"    if (live) begin"]
    for b in outs:
        L.append(f"      if (g_{b} !== n_{b}) begin mism = mism + 1; if (mism <= 10) $display(\"MISMATCH cyc=%0d {b} gold=%h new=%h\", cyc, g_{b}, n_{b}); end")
    if "fault" in outs:
        L.append("      if (g_fault) fault_hi = fault_hi + 1; if (g_fault && !was_f) fault_edges = fault_edges + 1; was_f = g_fault;")
    L += ["    end", "  end",
          f"  initial begin void'($urandom({seed})); rnd(); repeat (4) @(negedge {clk}); {rst} = {1 - ract}; live = 1;",
          f"    while (cyc < {cycles}) begin @(negedge {clk}); rnd();",
          f"      if ($urandom % 512 == 0) begin {rst} = {ract}; rsts = rsts + 1; repeat ($urandom % 4 + 1) @(negedge {clk}); {rst} = {1 - ract}; end",
          "    end",
          f"    $display(\"LOCKSTEP cycles=%0d resets=%0d mismatches=%0d fault_hi_cycles=%0d fault_rises=%0d outputs={len(outs)} inputs={len(ins)}\", cyc, rsts, mism, fault_hi, fault_edges);",
          "    if (mism == 0) $display(\"PASS\"); else $display(\"FAIL\");",
          "    $finish;", "  end", "endmodule"]
    return "\n".join(L) + "\n"


def run(core, out, cycles, seed, mutant):
    rec = json.load(open(HERE / "recipes.json"))[core]
    spec = json.load(open(REPO / rec["ref_tile"] / "spec.json"))
    pt = rec["rtl_patch"]
    top = spec["top"]
    o = Path(out) / ("mut" if mutant else "base")
    o.mkdir(parents=True, exist_ok=True)
    orig = (REPO / pt["file"]).read_text()
    gold = re.sub(rf"^module {top}\b", f"module {top}__gold", orig, count=1, flags=re.M)
    assert gold != orig
    gate = apply_patch(orig, pt["edits"], pt["file"])
    if mutant:
        gate = apply_patch(gate, [pt["mutant"]], "mutant")
    (o / f"{top}__gold.sv").write_text(gold)
    (o / f"{top}.sv").write_text(gate)
    w, d = ports(rec)
    clk, rst, ract = spec["clock_port"], pt["reset"]["port"], pt["reset"]["active"]
    (o / "tb_lockstep.sv").write_text(tb(top, spec.get("params", {}), w, d, clk, rst, ract, cycles, seed))
    srcs = [str(REPO / f) for f in spec["sources"] if f != pt["file"]] + [str(REPO / f) for f in pt.get("sim_extra", [])]
    inc = sorted({str((REPO / f).parent) for f in rec.get("includes", [])})
    cmd = [str(VERILATOR), "--binary", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD", "--top-module", "tb_lockstep",
           "-Mdir", str(o / "obj"), "--build-jobs", "16", *[f"-I{i}" for i in inc], *srcs, str(o / f"{top}__gold.sv"),
           str(o / f"{top}.sv"), str(o / "tb_lockstep.sv")]
    b = subprocess.run(cmd, capture_output=True, text=True)
    (o / "build.log").write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(build="FAIL", log=str(o / "build.log"), tail=(b.stdout + b.stderr)[-1500:])
    r = subprocess.run([str(o / "obj" / "Vtb_lockstep")], capture_output=True, text=True)
    (o / "run.log").write_text(r.stdout + r.stderr)
    ls = [x for x in r.stdout.splitlines() if x.startswith(("LOCKSTEP", "PASS", "FAIL", "MISMATCH"))]
    return dict(build="OK", result=("PASS" if "PASS" in r.stdout.splitlines() else "FAIL"), lines=ls[:14])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--cycles", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base = run(a.core, a.out, a.cycles, a.seed, False)
    mut = run(a.core, a.out, a.cycles, a.seed, True)
    rec = json.load(open(HERE / "recipes.json"))[a.core]
    v = "PASS" if base.get("result") == "PASS" and mut.get("result") == "FAIL" else "FAIL"
    res = dict(core=a.core, bench="kits_repin lockstep (verilator, random inputs every cycle incl. random async resets, every "
               "output bit compared every cycle) of the kit-local rtl_patch vs the unmodified repo module",
               patch_file=rec["rtl_patch"]["file"], cycles=a.cycles, seed=a.seed, base=base, mutant=mut,
               mutant_edit=rec["rtl_patch"]["mutant"], verdict=v,
               repo_rev=subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                                       text=True).stdout.strip())
    Path(a.out, "lockstep.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

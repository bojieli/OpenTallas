#!/usr/bin/env python3
"""DIE-HBM-30-S: diagnostic Yosys synth of the q_hub_nw soft logic after the xq_pegress fold (d29d bind b29d).
Hard cores of the plan type = black boxes (read -lib); everything else in the bound partition module = synthesised.
Source closure via the bind's own LintSources (tools/die_plan/bind_verify.py). usage: mk_hub_synth.py BINDDIR PLANJSON TYPE OUTDIR"""
import json, re, sys
from pathlib import Path
W = "/srv/opentallas-scratch2/claude/wt/die-hbm-27/tools/die_plan"
sys.path.insert(0, W)
import bind_elab as E
import bind_verify as BV
bd, planf, typ, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
ab0 = json.load(open(bd / "asbuilt.json")); rep = json.load(open(bd / "out/bind_report.json"))
base = ab0["base"]
P = json.load(open(planf)); v = P["partition_types"][typ]
norm = lambda s: re.sub(r"_+", "_", s.replace(".", "_"))
hi = {norm(h["inst"]) for h in v["hard_cores"]}
hub = bd / f"out/rtl/hbm_arch_q_hub__{typ}.sv"
s = hub.read_text()
ins = re.findall(r"^\s*([A-Za-z_]\w*)\s+(?:#\((?:.|\n)*?\)\s*)?([A-Za-z_\\][\w\[\]\.\\$]*)\s*\(", s, re.M)
hard_m, soft_m, hard_i = set(), set(), []
for m, i in ins:
    if m == "module": continue
    k = norm(i[2:] if i.startswith("u_u_") else i)
    if k in hi: hard_m.add(m); hard_i.append(i)
    else: soft_m.add(m)
assert not (hard_m & soft_m), hard_m & soft_m
idx = E.module_index(ab0.get("rtl_roots", ["rtl"]), ab0.get("files", []), base)
prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab0.get("prefer", [])] + rep.get("extra_lib", [])
LS = BV.LintSources(ab0, base, rep, idx, prefer)
gen = [f for f in rep["files"] if "native_glue" in f or Path(f).name == "bind_cells.sv"]
cl, miss = LS.closure(sorted(soft_m - {"ot_dp_rrelay", "ot_dp_st", "ot_dp_dly"}))
hardf = []
for m in sorted(hard_m):
    f, _ = E.pick({m: LS._cands(m)}, m, LS._prefer_for(m))
    if f and f not in hardf: hardf.append(f)
    if not f: miss.add(m) if isinstance(miss, set) else miss.append(m)
defs = " ".join("-D" + d for d in ab0.get("defines", []))
lib = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
L = []
L.append("read_liberty -lib " + lib + "/*RVT_TT*.lib*") if False else None
for f in hardf: L.append(f"read_verilog -sv -lib {defs} {f}")
for f in cl + gen: L.append(f"read_verilog -sv {defs} {f}")
L.append(f"read_verilog -sv {defs} {hub}")
L += [f"hierarchy -check -top hbm_arch_q_hub__{typ}", "tee -o " + str(out / "stat_hier_pre.txt") + " stat",
      "synth -flatten -top hbm_arch_q_hub__" + typ, "tee -o " + str(out / "stat_generic.txt") + " stat",
      "dfflegalize -cell $_DFF_P_ 01 -cell $_DFF_PN0_ 01 -cell $_DFF_PN1_ 01 -cell $_DFFE_PP_ 01 -cell $_DFFE_PN0P_ 01 -cell $_DFFE_PN1P_ 01",
      "tee -o " + str(out / "stat_legal.txt") + " stat"]
(out / "hub_synth.ys").write_text("\n".join(x for x in L if x) + "\n")
json.dump(dict(type=typ, hard_modules=sorted(hard_m), hard_insts=len(hard_i), soft_modules=sorted(soft_m), closure=cl,
               hard_files=hardf, missing=sorted(miss), gen=gen), open(out / "hub_synth_inputs.json", "w"), indent=1)
print("hard", len(hard_m), len(hard_i), "soft", len(soft_m), "closure", len(cl), "missing", sorted(miss))
# --- hard cores: port-only stubs (yosys -lib parse of some composed hard-core bodies fails; only ports matter) ---
stub = []
for m in sorted(hard_m):
    f, _ = E.pick({m: LS._cands(m)}, m, LS._prefer_for(m))
    t = Path(f).read_text(errors="replace")
    mm = re.search(r"^\s*module\s+" + re.escape(m) + r"\b", t, re.M)
    end = t.index("endmodule", mm.start())
    body = re.sub(r"/\*.*?\*/", "", t[mm.start():end], flags=re.S)
    body = re.sub(r"//[^\n]*", "", body)
    hdr_end = body.index(");") + 2
    decl, code = [], False
    for l in body[hdr_end:].splitlines():
        if re.match(r"\s*(generate|always|assign|for|initial|if|case|genvar)\b", l): code = True
        if re.match(r"\s*(input|output|inout|parameter)\b", l) and l.rstrip().endswith(";"): decl.append(l)
        elif not code and re.match(r"\s*localparam\b", l) and l.rstrip().endswith(";"): decl.append(l)
    # keep `define-dependent widths simple: lines must end in ';'
    stub.append("(* blackbox *)\n" + body[:hdr_end] + "\n" + "\n".join(decl) + "\nendmodule\n")
pre = "".join(l for l in open(f) if False)
(out / "hard_stubs.sv").write_text("\n".join(stub))
ys = (out / "hub_synth.ys").read_text().splitlines()
ys = [l for l in ys if " -lib " not in l]
ys.insert(0, f"read_verilog -sv {defs} {out / 'hard_stubs.sv'}")
(out / "hub_synth.ys").write_text("\n".join(ys) + "\n")
print("stubs", len(stub))

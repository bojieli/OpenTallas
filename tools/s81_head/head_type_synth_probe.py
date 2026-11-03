#!/usr/bin/env python3
"""DH58-RFRTL 11-03: ORFS synth-only probe dir for a plan type (or any module) whose kit does not exist yet.

Writes DIR/{config.mk,constraint.sdc,rtl/,macros/,run.sh}: the plan type's sources (repo-relative, copied from --root),
the hard cores' liberties as ADDITIONAL_LIBS, signed hard cores without a liberty as SYNTH_BLACKBOXES, the plan's
verilog_defines, SYNTH_HIERARCHICAL 0 and SYNTH_MEMORY_MAX_BITS raised (the memory census is read from mem.json;
memories > 4096 bits are reported, not mapped silently).  run.sh = `make synth` in openroad/orfs:asap7lock.

  head_type_synth_probe.py PLAN.json TYPE --root REPO --out DIR [--top MODULE] [--extra f.sv ...] [--blackbox M ...]
     [--view DIR ...] [--place]
--view DIR: a signed hard core's view dir (M.lef + M_tt.lib): M is cut out of the sources and bound to its liberty.
--place (pre-build quick-place gate, advisory): macro LEFs as ADDITIONAL_LEFS, run.sh target `place` (floorplan at
CORE_UTILIZATION 40 + global/detail place), then quick_sta.tcl: estimate_parasitics -placement, worst setup/hold slack.
"""
import argparse, json, shutil, sys
from pathlib import Path

RUN = """#!/bin/bash
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); MEM=${1:-24}; CPUS=${2:-8}
T=${TARGET:-$(cat "$K/target" 2>/dev/null || echo synth)}
docker run --rm --name dh58probe-$(basename "$K")-$$ --cpus=$CPUS --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work \\
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc \\
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS $T > /work/$T.log 2>&1; rc=\\$?; \\
   if [ \\$rc = 0 ] && [ $T = place ]; then make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base RUN_SCRIPT=/work/quick_sta.tcl run > /work/quick_sta.log 2>&1; rc=\\$?; fi; \\
   chown -R $(id -u):$(id -g) /work; exit \\$rc"
"""


QUICK_STA = """# DH58-RFRTL quick-place STA (advisory pre-build gate): placement parasitics, ideal clock
source $::env(SCRIPTS_DIR)/load.tcl
load_design 3_place.odb 3_place.sdc
estimate_parasitics -placement
puts "QUICK_STA begin"
report_worst_slack -max -digits 1
report_worst_slack -min -digits 1
report_tns -digits 1
report_design_area
report_checks -path_delay max -group_path_count 3 -format end
report_checks -path_delay max -fields {fanout cap slew} -digits 1
puts "QUICK_STA end"
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    ap.add_argument("type")
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--top")
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--blackbox", nargs="*", default=[])
    ap.add_argument("--max-bits", type=int, default=1 << 30)
    ap.add_argument("--view", nargs="*", default=[], type=Path)
    ap.add_argument("--place", action="store_true")
    ap.add_argument("--clock", default=None, help="clock port (default: ck if the top declares it, else clk)")
    a = ap.parse_args(argv)
    t = json.loads(a.plan.read_text())["partition_types"][a.type]
    top = a.top or t["module"]
    (a.out / "rtl").mkdir(parents=True, exist_ok=True)
    (a.out / "macros").mkdir(exist_ok=True)
    files = []
    for s in list(t.get("sources") or []) + a.extra:
        p = a.root / s
        if not p.exists():                         # memories_v2 and v1 trees: try the other one
            alt = Path(str(s).replace("asap7_memory_macros/", "asap7_memory_macros_v2/"))
            p = a.root / alt if (a.root / alt).exists() else p
        d = a.out / "rtl" / p.name
        shutil.copy(p, d)
        for h in p.parent.glob("*.svh"):               # `include files next to the source
            shutil.copy(h, a.out / "rtl" / h.name)
        files.append(f"/work/rtl/{p.name}")
    libs, bbs = [], list(a.blackbox)
    for h in t.get("hard_cores") or []:
        if h.get("lib"):
            lp = a.root / h["lib"]
            if lp.name not in [Path(x).name for x in libs]:
                shutil.copy(lp, a.out / "macros" / lp.name)
                libs.append(f"/work/macros/{lp.name}")
        elif h["module"] not in bbs:
            bbs.append(h["module"])
    # yosys SYNTH_BLACKBOXES only matches modules by their final (possibly parameterized) name, which misses a signed
    # core instanced with parameters; so a blackboxed module defined in a copied source is cut out of that source and
    # replaced by a port-only (* blackbox *) stub (its interface is the signed core's).
    import re
    views = {}
    for v in a.view:
        lef = sorted(v.glob("*.lef"))[0]
        views[lef.stem] = (lef, v / f"{lef.stem}_tt.lib")
    bbs = [m for m in bbs if m not in views]
    for m in views:                                    # signed view: drop its RTL and the parameter overrides on its
        for f in list(files):                          # instances (the liberty cell has none)
            q = a.out / "rtl" / Path(f).name
            txt = q.read_text()
            txt2 = re.sub(r"^\s*module\s+%s\b.*?^\s*endmodule\b" % re.escape(m), "", txt, flags=re.S | re.M)
            txt2 = re.sub(r"\b%s\s*#\s*\((?:[^()]|\([^()]*\))*\)" % re.escape(m), m, txt2)
            if txt2 != txt:
                q.write_text(txt2)
        lef, lib = views[m]
        shutil.copy(lib, a.out / "macros" / lib.name); libs.append(f"/work/macros/{lib.name}")
        shutil.copy(lef, a.out / "macros" / lef.name)
    for m in bbs:
        for f in list(files):
            q = a.out / "rtl" / Path(f).name
            txt = q.read_text()
            mm = re.search(r"^\s*module\s+%s\b.*?^\s*endmodule\b" % re.escape(m), txt, re.S | re.M)
            if not mm:
                continue
            body = mm.group(0)
            hdr = body[:body.index(");") + 2]
            hdr = re.sub(r"output\s+reg\b", "output wire", hdr)
            q.write_text(txt[:mm.start()] + txt[mm.end():])
            st = a.out / "rtl" / f"{m}_bbstub.v"
            st.write_text("(* blackbox *)\n" + hdr.strip() + "\nendmodule\n")
            files.append(f"/work/rtl/{st.name}")
    defs = " ".join(["-DSYNTHESIS"] + [f"-D{d}" for d in t.get("verilog_defines") or []])
    cfg = [f"export DESIGN_NAME = {top}", "export PLATFORM = asap7", f"export VERILOG_FILES = {' '.join(files)}",
           f"export VERILOG_DEFINES = {defs}", "export SDC_FILE = /work/constraint.sdc",
           "export SYNTH_HIERARCHICAL = 0", "export VERILOG_INCLUDE_DIRS = /work/rtl", "export SYNTH_REPEATABLE_BUILD = 1",
           f"export SYNTH_MEMORY_MAX_BITS = {a.max_bits}",
           "export CORE_UTILIZATION = 40", "export PLACE_DENSITY = 0.45"]
    if libs:
        cfg.append(f"export ADDITIONAL_LIBS = {' '.join(libs)}")
    if a.place:
        lefs = []
        for l in libs:
            stem = Path(l).name[:-len("_tt.lib")] if Path(l).name.endswith("_tt.lib") else Path(l).stem
            cand = [a.out / "macros" / f"{stem}.lef"]
            for h in t.get("hard_cores") or []:
                if h.get("lib") and Path(h["lib"]).name == Path(l).name:
                    src = a.root / Path(h["lib"]).parent / f"{stem}.lef"
                    if src.exists():
                        shutil.copy(src, cand[0])
            if cand[0].exists():
                lefs.append(f"/work/macros/{stem}.lef")
            else:
                raise SystemExit(f"--place: no LEF for {stem}")
        if lefs:
            cfg.append(f"export ADDITIONAL_LEFS = {' '.join(lefs)}")
            cfg.append("export MACRO_PLACE_HALO = 2 2")
        if a.view:                                     # a signed core's LEF has its PG on M5 (no default ASAP7 macro
            # grid connects it, PDN-0233): the quick-place gate builds no PG grid at all (placement + parasitics only)
            (a.out / "pdn.tcl").write_text("# DH58 quick-place: PG connections only, no grid (advisory timing estimate)\n"
                                           "add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power\n"
                                           "add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground\n"
                                           "global_connect\n")
            cfg.append("export PDN_TCL = /work/pdn.tcl")
        (a.out / "target").write_text("place\n")
        (a.out / "quick_sta.tcl").write_text(QUICK_STA)
    if bbs:
        cfg.append(f"export SYNTH_BLACKBOXES = {' '.join(bbs)}")
    (a.out / "config.mk").write_text("\n".join(cfg) + "\n")
    clk = a.clock
    if not clk:
        import re as _re
        srcs = "".join((a.out / "rtl" / Path(f).name).read_text(errors="ignore") for f in files)
        mt = _re.search(r"module\s+%s\b(.*?)\);" % _re.escape(top), srcs, _re.S)
        clk = "ck" if mt and _re.search(r"\bck\b", mt.group(1)) else "clk"
    (a.out / "constraint.sdc").write_text(
        f"create_clock -name clk -period 833 [get_ports {{{clk}}}]\n"
        "set_input_delay 166.6 -clock clk [delete_from_list [all_inputs] [get_ports {%s}]]\n"
        "set_output_delay 166.6 -clock clk [all_outputs]\n" % clk)
    (a.out / "run.sh").write_text(RUN)
    (a.out / "run.sh").chmod(0o755)
    (a.out / "probe.json").write_text(json.dumps(dict(type=a.type, top=top, files=files, libs=libs, blackboxes=bbs,
                                                      defines=defs), indent=1))
    print(a.out, top, len(files), "files", len(libs), "libs", bbs)


if __name__ == "__main__":
    sys.exit(main())

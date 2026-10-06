#!/usr/bin/env python3
"""CLAUDE WFC: the DS-ROM wavefront package controller (ot_rom_pkg_ctrl_wfc) as ONE small hardened element.

The WFC element is the controller only (src = SOURCE 1, stg = SOURCE 0, FULL_SHAPE die parameters).  The vector
memory, the cfg/prompt producers and the book ROMs are their own hardened elements; the WFC talks to them through
its existing ports (IO at 20 % of the period against the neighbour's register, in context).  With REC_SRAM the
SOURCE engine's 866 per-user records + issued-token rings live in 1R1W 512x128 SRAM macros (4 at full shape)
instead of 215k flops.

  prep   write a case dir: config.mk, constraint.sdc, run.sh (ORFS in the pinned image, then per-corner signoff
         STA with tools/dsrom_wf_close.py's block / incontext / reg2reg modes, macro libs included)
             python3 tools/dsrom_wfc_split_physical.py prep --inst src|stg --case DIR --src SRCDIR --util 45
                     [--knob REC_SRAM=1 ...] [--cores 12] [--orfs-var K=V ...]
  sta    signoff STA on a finished case (also run by run.sh)
  check  kept-copy and macro counts in the synthesized and routed netlists, the SDC limits the flow loaded
  record collect cases into a JSON record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_wf_close as WF  # noqa: E402

CTRL = "rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv"
MACRO = "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2"
MNAME = "ot_sram_1r1w_512x128_m4_r2c2"
PERIOD_PS = 833
KNOBS_DEFAULT = {"src": dict(REC_SRAM=1, UPOS_LWR=1, CONTROL_PIPE=1, CFG_Q=1, PRECOMP=1, IN_DEC=1, TXQ_SLICE=1),
                 "stg": dict(UPOS_LWR=1, CONTROL_PIPE=1, PRECOMP=1, IN_DEC=1, TXQ_SLICE=1)}
# Estimated die-tree insertion delay [min, max] ps at the element's clock pins (r1 routes: src 505..588,
# stg 312..401).  The routed SDC times IO against io_clk carrying it as SOURCE latency (kept after CTS
# propagates the clocks), i.e. the neighbours' registers hang off the same tree -- the same model as
# the signoff "incontext" mode, which re-times the IO against the block's own measured min/max.
# Without it every input is hold-padded by ~insertion - 20 % (r1: 300-500 ps of BUFx2 chains on
# cfg/in_data/in_valid/vm_rq), which then fails setup in context.
IO_LAT = {"src": (480, 600), "stg": (290, 410)}

SDC = """# CLAUDE WFC element: 1.2 GHz, SS 60 ps setup / FF 25 ps hold uncertainty, IO at 20 % of the period
create_clock -name core_clk -period {p} [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set ins [lsearch -all -inline -not [all_inputs] [get_ports clk]]
""" + """{io_clk}"""
SDC_IDEAL_IO = """set_input_delay {io} -clock core_clk $ins
set_output_delay {io} -clock core_clk [all_outputs]
"""
SDC_IO_CLK = """# neighbours on the same die tree: IO against io_clk with the estimated insertion as source latency;
# core_clk carries the mid estimate as ideal network latency until CTS replaces it with the real tree
set_clock_latency {lmid} [get_clocks core_clk]
create_clock -name io_clk -period {p}
set_clock_latency -source -min {lmin} [get_clocks io_clk]
set_clock_latency -source -max {lmax} [get_clocks io_clk]
set_clock_uncertainty -setup 60 [get_clocks io_clk]
set_clock_uncertainty -hold 25 [get_clocks io_clk]
set_input_delay {io} -clock io_clk $ins
set_output_delay {io} -clock io_clk [all_outputs]
"""
SDC_TAIL = """set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
"""


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cmd_prep(a):
    case = a.case.resolve()
    case.mkdir(parents=True, exist_ok=True)
    knobs = dict(KNOBS_DEFAULT[a.inst])
    for kv in a.knob:
        k, v = kv.split("=")
        knobs[k] = int(v)
    params = dict(WF.INST[a.inst]) | knobs
    macros = bool(knobs.get("REC_SRAM")) and a.inst == "src"
    nick = f"wfc_{a.inst}_{case.name}".replace("-", "_")
    vfiles = [f"/src/{CTRL}"] + ([f"/src/{MACRO}/{MNAME}_bb.v"] if macros else [])
    lines = [f"export DESIGN_NICKNAME = {nick}", "export DESIGN_NAME = ot_rom_pkg_ctrl_wfc", "export PLATFORM = asap7",
             "export VERILOG_FILES = " + " ".join(vfiles), "export VERILOG_DEFINES = -DSYNTHESIS",
             "export VERILOG_TOP_PARAMS = " + " ".join(f"{k} {v}" for k, v in params.items()),
             "export SDC_FILE = /work/constraint.sdc",
             f"export CORE_UTILIZATION = {a.util}", "export CORE_ASPECT_RATIO = 1", "export CORE_MARGIN = 2",
             f"export PLACE_DENSITY = {a.density}", f"export PLACE_DENSITY_LB_ADDON = {a.lb_addon}",
             "export SYNTH_REPEATABLE_BUILD = 1", "export SYNTH_HIERARCHICAL = 0", "export SYNTH_MEMORY_MAX_BITS = 65536",
             "export LEC_CHECK = 0", "export TNS_END_PERCENT = 100", "export SETUP_SLACK_MARGIN = 0",
             "export HOLD_SLACK_MARGIN = 0", "export SKIP_REPORT_METRICS = 0", "export REPORT_CLOCK_SKEW = 1",
             "export CORNER = WC", "export ADDER_MAP_FILE = ", "export ASAP7_USE_VT = RVT",
             "export CORNERS = WC BC",
             "export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)" + (f" /src/{MACRO}/{MNAME}_ss.lib" if macros else ""),
             "export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)" + (f" /src/{MACRO}/{MNAME}_ff.lib" if macros else "")]
    if macros:
        lines += [f"export ADDITIONAL_LEFS = /src/{MACRO}/{MNAME}.lef", f"export ADDITIONAL_LIBS = /src/{MACRO}/{MNAME}_ss.lib",
                  f"export SYNTH_BLACKBOXES = {MNAME}", "export MACRO_PLACE_HALO = 4 4",
                  "export GDS_ALLOW_EMPTY = ot_sram.*"]
    for kv in a.orfs_var:
        k, v = kv.split("=", 1)
        lines.append(f"export {k} = {v}")
    (case / "config.mk").write_text("\n".join(lines) + "\n")
    io = round(0.2 * PERIOD_PS, 1)
    if a.ideal_io:
        ioc = SDC_IDEAL_IO.format(io=io)
    else:
        lmin, lmax = IO_LAT[a.inst] if a.io_lat is None else map(int, a.io_lat.split(","))
        ioc = SDC_IO_CLK.format(p=PERIOD_PS, io=io, lmin=lmin, lmax=lmax, lmid=(lmin + lmax) // 2)
    (case / "constraint.sdc").write_text(SDC.format(p=PERIOD_PS, io_clk=ioc) + SDC_TAIL)
    src = a.src.resolve()
    run = f"""#!/bin/bash
# CLAUDE WFC {a.inst} {case.name}: ORFS route, then signoff STA.  /src = pinned source {src}
set -u
W={case}; S={src}; IMG=openroad/orfs:latest
cd $W; echo "start $(date -Is)" > $W/status
/srv/opentallas-scratch/admit.sh {a.need} -- docker run --rm --name claude-wfc-{case.parent.name}-{nick} -v $S:/src:ro -v $W:/work \\
  -w /OpenROAD-flow-scripts/flow $IMG bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; \\
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work \\
  FLOW_VARIANT=base NUM_CORES={a.cores} finish" > $W/flow.log 2>&1
echo "flow_rc=$?" >> $W/status
cd $S && python3 tools/dsrom_wfc_split_physical.py sta --case $W {'--macros' if macros else ''} > $W/sta.log 2>&1
echo "sta_rc=$?" >> $W/status
python3 tools/dsrom_wfc_split_physical.py check --case $W > $W/check.log 2>&1
echo "end $(date -Is)" >> $W/status
"""
    (case / "run.sh").write_text(run)
    (case / "run.sh").chmod(0o755)
    (case / "case.json").write_text(json.dumps(dict(inst=a.inst, params=params, util=a.util, macros=macros,
                                                     orfs_var=a.orfs_var, src=str(src),
                                                     ctrl_sha256=sha(src / CTRL)), indent=1) + "\n")
    print(case / "run.sh")


def cmd_sta(a):
    case = a.case.resolve()
    tcl = WF.STA_TCL.replace("set ck [get_clocks]", "set ck [get_clocks core_clk]")
    # incontext / reg2reg re-time the IO against the measured insertion: drop the routed SDC's io_clk IO first
    tcl = tcl.replace("unset_input_delay $ins\n",
                      "catch {unset_input_delay -clock [get_clocks io_clk] $ins}\n"
                      "catch {unset_output_delay -clock [get_clocks io_clk] [all_outputs]}\nunset_input_delay $ins\n")
    assert "io_clk" in tcl
    if a.macros:
        tcl = tcl.replace("read_db $::env(WF_ODB)",
                          f"read_liberty /src/{MACRO}/{MNAME}_[string tolower $::env(WF_LIB)].lib\n"
                          "read_db $::env(WF_ODB)")
        WF.STA_TCL = tcl
    # corner_sta mounts the case dir at /work; the macro lib comes from /src
    orig = subprocess.run

    def run(c, *k, **kw):
        if c and c[0] == "docker" and a.macros:
            c = c[:3] + ["-v", f"{ROOT}:/src:ro"] + c[3:]
        return orig(c, *k, **kw)
    WF.subprocess.run = run
    nick = next(case.rglob("results/asap7/*/base/6_final.odb")).parent.parent.name
    rec = WF.corner_sta(case, nick, case)
    print(json.dumps({c: {m: (v.get(m) or {}).get("setup_wns_ps") for m in ("block", "incontext", "reg2reg")} |
                      {"hold_" + m: (v.get(m) or {}).get("hold_wns_ps") for m in ("block", "incontext", "reg2reg")}
                      for c, v in rec["corners"].items()}, indent=1))


def cmd_check(a):
    case = a.case.resolve()
    out = {}
    syn = next(case.rglob("results/asap7/*/base/1_2_yosys.v"), None) or next(case.rglob("results/asap7/*/base/1_synth.v"), None)
    fin = next(case.rglob("results/asap7/*/base/6_final.v"), None)
    for tag, f in (("synth", syn), ("final", fin)):
        if f and f.is_file():
            t = f.read_text(errors="replace")
            out[tag] = dict(file=str(f.relative_to(case)), sram_macros=len(re.findall(rf"\b{MNAME}\b\s+\S+\s*\(", t)),
                            upos_wr_l=len(re.findall(r"g_local_write\.wr_l", t)) or len(re.findall(r"wr_l\$", t)),
                            upos_wd_l=len(set(re.findall(r"(g_upos\[\d+\]\.ug[./]g_local_write[./]wd_l)\[", t))))
    sdcs = {}
    for name in ("1_synth.sdc", "4_cts.sdc", "6_final.sdc"):
        p = next(case.rglob(f"results/asap7/*/base/{name}"), None)
        if p:
            t = p.read_text(errors="replace")
            sdcs[name] = [l for l in t.splitlines() if re.search(r"set_max_transition|set_max_fanout|uncertainty|_delay", l)][:12]
    out["sdc"] = sdcs
    m = next(case.rglob("logs/asap7/*/base/6_report.json"), None) or next(case.rglob("reports/asap7/*/base/6_finish.rpt"), None)
    out["metrics_file"] = str(m) if m else None
    (case / "check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--inst", choices=["src", "stg"], required=True)
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--src", type=Path, required=True)
    p.add_argument("--util", type=int, default=45)
    p.add_argument("--lb-addon", type=float, default=0.05)
    p.add_argument("--density", type=float, default=0.6)
    p.add_argument("--knob", action="append", default=[])
    p.add_argument("--orfs-var", action="append", default=[])
    p.add_argument("--cores", type=int, default=12)
    p.add_argument("--need", type=int, default=24)
    p.add_argument("--io-lat", default=None, help="MIN,MAX ps io_clk source latency (default per inst)")
    p.add_argument("--ideal-io", action="store_true", help="r1 SDC: IO against the ideal core_clk")
    s = sub.add_parser("sta")
    s.add_argument("--case", type=Path, required=True)
    s.add_argument("--macros", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--case", type=Path, required=True)
    a = ap.parse_args()
    {"prep": cmd_prep, "sta": cmd_sta, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()

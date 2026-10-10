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
KNOBS_DEFAULT = {"src": dict(REC_SRAM=1, UPOS_LWR=1, CONTROL_PIPE=1, CFG_Q=1, PRECOMP=1, IN_DEC=1, TXQ_SLICE=1, RDY_LT=1, FANOUT_COPY=1, MARGIN=1,
                             LINK_REG=1, LINK_SEL=1, VM_REG=1, RD_PIPE=1, SLEW_COPY=1),
                 "stg": dict(UPOS_LWR=1, CONTROL_PIPE=1, PRECOMP=1, IN_DEC=1, TXQ_SLICE=1, RDY_LT=1, FANOUT_COPY=1, MARGIN=1,
                             LINK_REG=1, LINK_SEL=1, VM_REG=1, SLEW_COPY=1)}
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
# --die-skew S: the neighbour's register sits on the same die tree but its clock may arrive up to S ps before /
# after ours.  Floorplan / place: io_clk carries the estimated insertion widened by S (setup direction only
# matters there).  From CTS on (clocks propagated) the repair stages time the IO against core_clk's arrival at
# one of the element's own boundary registers (-reference_pin, so per corner -- an SS latency estimate would
# over-pad BC hold on every output), widened by S plus the element's insertion spread (SPREAD_PS).  OpenSTA
# cannot re-read a written -reference_pin SDC (Signal 11 on the next timing update), so the hooks apply it
# after the stage's load and put the io_clk form back before the stage writes its SDC.  The CTS repair runs in
# the POST_CTS hook (SKIP_CTS_REPAIR_TIMING = 1) with the die model; the GRT repair between the GRT hooks.
SPREAD_PS = 60
HOOK_APPLY = """# CLAUDE WFC die IO model (propagated clocks): IO vs core_clk at a boundary register, +-{skew} +- {spread} ps
# only inside the POST_CTS repair (the GRT stage crashed OpenSTA with it: Sim::findDisabledEdges)
if {{![info exists wfc_in_cts]}} {{ puts "WFC_IO_MODEL skip"; return }}
set_propagated_clock [all_clocks]
set wfc_ins [lsearch -all -inline -not [all_inputs] [get_ports clk]]
catch {{unset_input_delay -clock [get_clocks io_clk] $wfc_ins}}
catch {{unset_output_delay -clock [get_clocks io_clk] [all_outputs]}}
set wfc_refp [lindex [get_pins -quiet {{g_link_reg.u_rx.pv*/CLK}}] 0]
if {{$wfc_refp == ""}} {{ set wfc_refp [lindex [all_registers -edge_triggered -clock_pins] 0] }}
puts "WFC_IO_MODEL apply ref [get_full_name $wfc_refp]"
set_input_delay -max {imax} -clock core_clk -reference_pin $wfc_refp $wfc_ins
set_input_delay -min {imin} -clock core_clk -reference_pin $wfc_refp $wfc_ins
set_output_delay -max {imax} -clock core_clk -reference_pin $wfc_refp [all_outputs]
set_output_delay -min {imin} -clock core_clk -reference_pin $wfc_refp [all_outputs]
"""
HOOK_RESTORE = """# CLAUDE WFC: back to the io_clk form before the stage writes its SDC.  The later repairs (GRT) keep the
# setup-direction die model (io_clk latency widened by the skew) but a HOLD-LAX IO minimum: the IO hold was repaired
# in the POST_CTS hook against the per-corner die model; an absolute io_clk latency would re-pad BC output hold
# by the SS-BC insertion difference
if {{![info exists wfc_in_cts]}} {{ puts "WFC_IO_MODEL skip"; return }}
set wfc_ins [lsearch -all -inline -not [all_inputs] [get_ports clk]]
unset_input_delay -clock [get_clocks core_clk] $wfc_ins
unset_output_delay -clock [get_clocks core_clk] [all_outputs]
set_input_delay -max {io} -clock io_clk $wfc_ins
set_input_delay -min {io} -clock io_clk $wfc_ins
set_output_delay -max {io} -clock io_clk [all_outputs]
set_output_delay -min {olax} -clock io_clk [all_outputs]
unset wfc_in_cts
puts "WFC_IO_MODEL restore (hold-lax IO)"
"""
HOOK_POST_CTS = """set wfc_in_cts 1
source /work/wfc_io_apply.tcl
repair_timing_helper
set result [catch {{ log_cmd detailed_placement }} msg]
if {{ $result != 0 }} {{ error "Detailed placement failed in CTS: $msg" }}
check_placement -verbose
log_cmd estimate_parasitics -placement
source /work/wfc_io_restore.tcl
"""
SDC_TAIL = """set_load 2.0 [all_outputs]
set_max_fanout 32 [current_design]
set_max_transition 320 [current_design]
"""


DRV_TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(WF_LIB)_*.lib*]] { read_liberty $f }
if {$::env(WF_XLIB) != ""} { read_liberty $::env(WF_XLIB) }
read_db $::env(WF_ODB)
read_sdc $::env(WF_SDC)
read_spef $::env(WF_SPEF)
set_propagated_clock [all_clocks]
puts "DRVBEGIN"
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "DRVEND"
"""


def drv_check(case, macros, corners=("SS", "FF")):
    """max slew / cap / fanout violators at SS and FF on the routed netlist + RCX parasitics (the routed SDC limits)."""
    res = next(case.rglob("results/asap7/*/base/6_final.odb")).parent
    (case / "wf_drv.tcl").write_text(DRV_TCL)
    rel = lambda q: "/work/" + str(q.relative_to(case))
    out = {}
    for lib in corners:
        c = ["docker", "run", "--rm", "-v", f"{case}:/work"] + (["-v", f"{ROOT}:/src:ro"] if macros else []) + [
             "-e", f"WF_LIB={lib}", "-e", f"WF_ODB={rel(res / '6_final.odb')}", "-e", f"WF_SDC={rel(res / '6_final.sdc')}",
             "-e", f"WF_SPEF={rel(res / '6_final.spef')}",
             "-e", "WF_XLIB=" + (f"/src/{MACRO}/{MNAME}_{lib.lower()}.lib" if macros else ""),
             "openroad/orfs:latest", "bash", "-lc",
             "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/wf_drv.tcl"]
        p = subprocess.run(c, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (case / f"wf_drv_{lib}.log").write_text(log)
        body = log.split("DRVBEGIN", 1)[-1].split("DRVEND", 1)[0] if "DRVEND" in log else None
        cnt = {}
        if body is not None:
            sect = None
            for line in body.splitlines():
                s = line.strip().lower()
                if s in ("max slew", "max capacitance", "max fanout"):
                    sect = s.split()[1]; cnt[sect] = 0
                elif sect and "(VIOLATED)" in line:
                    cnt[sect] += 1
        out[lib] = dict(done=body is not None, violators={k: cnt.get(k, 0) for k in ("slew", "capacitance", "fanout")})
    return out


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
    if a.die_skew:
        lines += ["export SKIP_CTS_REPAIR_TIMING = 1", "export POST_CTS_TCL = /work/wfc_post_cts.tcl"]
        io0 = round(0.2 * PERIOD_PS, 1)
        apply = HOOK_APPLY.format(skew=a.die_skew, spread=SPREAD_PS,
                                  imax=round(io0 + a.die_skew + SPREAD_PS, 1), imin=round(io0 - a.die_skew - SPREAD_PS, 1))
        if a.link_hold_pad:
            # r12 (superseded): an extra -reference_pin min delay on in_* changed nothing (identical netlist)
            apply += ("set_input_delay -min {:.1f} -clock core_clk -reference_pin $wfc_refp [get_ports {{in_*}}]\n"
                      .format(io0 - a.die_skew - SPREAD_PS - a.link_hold_pad))
        if a.link_hold_abs_min is not None:
            # hold by repair on the stage-link inputs (in_*, the inter-region crossing): an ABSOLUTE min input delay
            # (ps after the ideal edge) at the FF die-model arrival minus a pad, so the POST_CTS hold repair buffers
            # them at BC (r11 src routed FF hold -4.7 ps region on in_data -> u_rx.pd: arrival lmin_FF - 150 + 166.6
            # = 288.1 ps).  WC is over-padded (in_* setup slack ~380 ps at SS); the GRT stage stays hold-lax.
            apply += ("set wfc_lk [get_ports {{in_*}}]\nunset_input_delay -clock core_clk $wfc_lk\n"
                      "set_input_delay -max {:.1f} -clock core_clk -reference_pin $wfc_refp $wfc_lk\n"
                      "set_input_delay -min {:.1f} -clock core_clk $wfc_lk\n"
                      .format(io0 + a.die_skew + SPREAD_PS, a.link_hold_abs_min))
        (case / "wfc_io_apply.tcl").write_text(apply)
        (case / "wfc_io_restore.tcl").write_text(HOOK_RESTORE.format(io=io0, olax=round(io0 + 400, 1)))
        (case / "wfc_post_cts.tcl").write_text(HOOK_POST_CTS.format())
    (case / "config.mk").write_text("\n".join(lines) + "\n")
    io = round(0.2 * PERIOD_PS, 1)
    rp = a.route_period or PERIOD_PS
    for name, per in (("constraint.sdc", rp), ("signoff.sdc", PERIOD_PS)):
        if a.ideal_io:
            ioc = SDC_IDEAL_IO.format(io=io)
        else:
            lmin, lmax = IO_LAT[a.inst] if a.io_lat is None else map(int, a.io_lat.split(","))
            sk = a.die_skew if name == "constraint.sdc" else 0
            ioc = SDC_IO_CLK.format(p=per, io=io, lmin=lmin - sk, lmax=lmax + sk, lmid=(lmin + lmax) // 2)
        # the route may be over-constrained (owner margin rule: ~770 ps); signoff is always at 833 ps
        (case / name).write_text(SDC.format(p=per, io_clk=ioc) + SDC_TAIL)
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
                                                     route_period_ps=rp, die_skew_ps=a.die_skew, link_hold_pad_ps=a.link_hold_pad, link_hold_abs_min_ps=a.link_hold_abs_min,
                                                     orfs_var=a.orfs_var, src=str(src),
                                                     ctrl_sha256=sha(src / CTRL)), indent=1) + "\n")
    print(case / "run.sh")


LINK_PORTS = "in_* out_*"
REGION_INTER_PS, REGION_INTRA_PS, REGION_HOLD_UNC_PS = 150, 90, 50
REGION_TCL = (
    f"set lk_in [get_ports {{in_*}}]\nset lk_out [get_ports {{out_*}}]\n"
    "create_clock -name vlk -period $per\n"
    f"set_clock_latency -min [expr $lmin - {REGION_INTER_PS}] [get_clocks vlk]\n"
    f"set_clock_latency -max [expr $lmax + {REGION_INTER_PS}] [get_clocks vlk]\n"
    f"set_clock_latency -min [expr $lmin - {REGION_INTRA_PS}] [get_clocks vclk]\n"
    f"set_clock_latency -max [expr $lmax + {REGION_INTRA_PS}] [get_clocks vclk]\n"
    "set_clock_uncertainty -setup $::env(WF_USETUP) [get_clocks {vclk vlk}]\n"
    f"set_clock_uncertainty -hold {REGION_HOLD_UNC_PS} [get_clocks {{vclk vlk}}]\n"
    "unset_input_delay $lk_in\nunset_output_delay $lk_out\n"
    "set_input_delay $io -clock vlk $lk_in\nset_output_delay $io -clock vlk $lk_out\n"
    "rep region\n"
    "unset_input_delay $lk_in\nunset_output_delay $lk_out\n"
    "set_input_delay $io -clock vclk $lk_in\nset_output_delay $io -clock vclk $lk_out\n"
    "set_clock_uncertainty -hold $::env(WF_UHOLD) [get_clocks vclk]\n")


def cmd_sta(a):
    case = a.case.resolve()
    tcl = WF.STA_TCL.replace("set ck [get_clocks]", "set ck [get_clocks core_clk]")
    # incontext / reg2reg re-time the IO against the measured insertion: drop the routed SDC's io_clk IO first
    tcl = tcl.replace("unset_input_delay $ins\n",
                      "catch {unset_input_delay -clock [get_clocks io_clk] $ins}\n"
                      "catch {unset_output_delay -clock [get_clocks io_clk] [all_outputs]}\nunset_input_delay $ins\n")
    assert "io_clk" in tcl
    if (case / "signoff.sdc").is_file():     # sign off at 833 ps whatever period the route was constrained to
        tcl = tcl.replace("read_sdc $::env(WF_SDC)", "read_sdc /work/signoff.sdc")
    # die150: IO against a die clock arriving up to 150 ps before / after the element's own measured insertion
    tcl = tcl.replace("rep incontext\n", "rep incontext\nset_clock_latency -min [expr $lmin - 150] [get_clocks vclk]\n"
                      "set_clock_latency -max [expr $lmax + 150] [get_clocks vclk]\nrep die150\n"
                      "set_clock_latency -min $lmin [get_clocks vclk]\nset_clock_latency -max $lmax [get_clocks vclk]\n")
    assert "rep die150" in tcl
    # region (owner clarification 2026-10-06 + OWNER 18:15 acceptance): the die clock-arrival term is 150 ps only on
    # ports that cross a die wire to a different clock region -- the WFC stage link (in_* / out_*); every other port
    # (core, VM, prefill, token, config) meets a neighbour in the same clock region: measured pair skew + margin,
    # 90 ps (65 measured + 25).  Hold against the IO with 50 ps hold IO uncertainty (FF insertion).
    tcl = tcl.replace("rep die150\n", "rep die150\n" + REGION_TCL, 1)
    assert "rep region" in tcl
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
    WF.subprocess.run = orig
    drv = drv_check(case, a.macros)
    (case / "wf_drv.json").write_text(json.dumps(drv, indent=1) + "\n")
    print(json.dumps(drv))
    print(json.dumps({c: {"insertion_ps": v.get("insertion_ps")} |
                      {m: (v.get(m) or {}).get("setup_wns_ps") for m in ("block", "incontext", "die150", "region", "reg2reg")} |
                      {"hold_" + m: (v.get(m) or {}).get("hold_wns_ps") for m in ("block", "incontext", "die150", "region", "reg2reg")}
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


def case_record(case: Path):
    """One routed case: what it is, signoff STA (SS/FF; block / incontext / reg2reg), DRV, DRC/antenna, area."""
    cj = json.loads((case / "case.json").read_text())
    sta = json.loads((case / "wf_sta.json").read_text()) if (case / "wf_sta.json").is_file() else {}
    drv = json.loads((case / "wf_drv.json").read_text()) if (case / "wf_drv.json").is_file() else {}
    rep = next(case.rglob("logs/asap7/*/base/6_report.json"), None)
    rte = next(case.rglob("logs/asap7/*/base/5_2_route.json"), None)
    m = json.loads(rep.read_text()) if rep else {}
    r = json.loads(rte.read_text()) if rte else {}
    corners = sta.get("corners", {})
    ss, ff = corners.get("SS", {}), corners.get("FF", {})
    def v(c, mode, f):
        return (c.get(mode) or {}).get(f)
    def nn(x):
        return isinstance(x, (int, float)) and x >= 0
    drc, ant = r.get("detailedroute__route__drc_errors"), r.get("detailedroute__antenna__violating__nets")
    drv_ok = bool(drv) and all(d.get("done") and not any(d["violators"].values()) for d in drv.values())
    timing = {mode: dict(ss_setup_ps=v(ss, mode, "setup_wns_ps"), ss_hold_ps=v(ss, mode, "hold_wns_ps"),
                         ff_setup_ps=v(ff, mode, "setup_wns_ps"), ff_hold_ps=v(ff, mode, "hold_wns_ps"),
                         ss_failing=[v(ss, mode, "failing_setup"), v(ss, mode, "failing_hold")],
                         ff_failing=[v(ff, mode, "failing_setup"), v(ff, mode, "failing_hold")],
                         ss_worst_setup_path=v(ss, mode, "worst_max_path"))
              for mode in ("block", "incontext", "die150", "region", "reg2reg")}
    closed = (all(nn(timing[mode][f]) for mode in ("incontext", "reg2reg")
                  for f in ("ss_setup_ps", "ss_hold_ps", "ff_hold_ps"))
              and drc == 0 and ant == 0 and drv_ok and bool(ss.get("done")) and bool(ff.get("done")))
    margin_closed = (closed and all(isinstance(timing[m]["ss_setup_ps"], (int, float)) and timing[m]["ss_setup_ps"] >= 60
                                    for m in ("incontext", "reg2reg"))
                     and all(isinstance(timing[m]["ff_hold_ps"], (int, float)) and timing[m]["ff_hold_ps"] >= 15
                             for m in ("incontext", "reg2reg")))
    # owner acceptance (UPDATE 2 + die-integration addendum): SS setup >= +40 and FF hold >= +15 in context,
    # reg2reg AND with the die clock +-150 ps against the IO (die150); SS hold >= 0 there too
    def ge(x, lim):
        return isinstance(x, (int, float)) and x >= lim
    accepted = (closed and all(ge(timing[m]["ss_setup_ps"], 40) and ge(timing[m]["ff_hold_ps"], 15) and
                               ge(timing[m]["ss_hold_ps"], 0) for m in ("incontext", "reg2reg", "die150")))
    # OWNER 18:15 (2026-10-06): accept at SS >= +15 / FF >= +15 at 833.333 with the agreed IO budgets (region:
    # 150 ps inter-region on the stage link, 90 ps intra-region elsewhere, 50 ps hold IO uncertainty)
    accepted_region = (closed and timing["region"]["ss_setup_ps"] is not None and
                       all(ge(timing[m]["ss_setup_ps"], 15) and ge(timing[m]["ff_hold_ps"], 15) and
                           ge(timing[m]["ss_hold_ps"], 0) for m in ("incontext", "reg2reg", "region")))
    return dict(inst=cj["inst"], route_period_ps=cj.get("route_period_ps"), die_skew_ps=cj.get("die_skew_ps", 0),
                accepted_40_15_die150=accepted, accepted_15_15_region=accepted_region, margin_closed=margin_closed, util=cj["util"], params=cj["params"], orfs_var=cj.get("orfs_var"),
                source_dir=cj["src"], ctrl_sha256=cj["ctrl_sha256"],
                insertion_ps=dict(SS=ss.get("insertion_ps"), FF=ff.get("insertion_ps")), timing=timing,
                drv=drv, drc_errors=drc, antenna_violating_nets=ant,
                stdcell_area_um2=m.get("finish__design__instance__area__stdcell"),
                macro_area_um2=m.get("finish__design__instance__area__macros"),
                die_area_um2=m.get("finish__design__die__area"),
                utilization=m.get("finish__design__instance__utilization"),
                artifacts_sha256=sta.get("artifacts_sha256"), closed=closed)


def cmd_record(a):
    rec = dict(schema="opentallas.rtl.dsrom_wfc_split_physical.v1",
               block="ot_rom_pkg_ctrl_wfc as one hardened WFC element (src = SOURCE 1, stg = SOURCE 0), full shape",
               period_ps=PERIOD_PS, setup_uncertainty_ps=60, hold_uncertainty_ps=25, io_fraction=0.2,
               closure_rule="SS setup and SS/FF hold >= 0 in incontext (IO at 20 % vs a virtual clock carrying the "
                            "element's own measured min/max insertion: neighbours on the same die tree) and reg2reg; "
                            "DRC 0, antenna 0, max slew/cap/fanout violators 0 at SS and FF on RCX parasitics. "
                            "block (IO vs io_clk at the routed SDC's estimated insertion) is reported, not gating.",
               cases={str(Path(c).name if Path(c).parent.name == "" else Path(c).parent.name + "/" + Path(c).name):
                      case_record(Path(c).resolve()) for c in a.case},
               notes=a.note)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: dict(closed=v["closed"], margin_closed=v["margin_closed"], accepted=v["accepted_15_15_region"], accepted_40_die150=v["accepted_40_15_die150"], region=v["timing"]["region"]["ss_setup_ps"], region_ff_hold=v["timing"]["region"]["ff_hold_ps"],
                              die150=v["timing"]["die150"]["ss_setup_ps"],
                              incontext=v["timing"]["incontext"]["ss_setup_ps"],
                              ff_hold=v["timing"]["incontext"]["ff_hold_ps"], drv=v["drv"])
                      for k, v in rec["cases"].items()}, indent=1))


REF_STAGE = ROOT / "results/rtl/dsrom_wavefront_verify_20261004/record.json"   # the reference controller (wave 1)


def stage_jobs(txt):
    jobs, outs = [], []
    for line in txt.splitlines():
        if line.startswith("JOB "):
            jobs.append({k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", line)})
        elif line.startswith("OUT "):
            outs.append(int(re.search(r"cycle=(\d+)", line).group(1)))
    return jobs, outs


def cmd_closure(a):
    """closure.json for tools/dsrom_1m_allmeasured.wfc_closure: the routed record (src + stg cases), the exact
    benches, and the cycle charge measured on the stage bench against the reference controller."""
    rec = json.loads(a.record.read_text())
    els = {}
    for key, inst in (("src", "src"), ("stg", "stg")):
        k = next(c for c in rec["cases"] if rec["cases"][c]["inst"] == inst)
        c = rec["cases"][k]
        t = c["timing"]
        els[inst] = dict(route=k, accepted=c["accepted_15_15_region"], accepted_40_15_die150=c["accepted_40_15_die150"],
                         ss_setup_ps=min(t[m]["ss_setup_ps"] for m in ("incontext", "reg2reg")),
                         ff_hold_ps=min(t[m]["ff_hold_ps"] for m in ("incontext", "reg2reg")),
                         die150_ss_setup_ps=t["die150"]["ss_setup_ps"], die150_ff_hold_ps=t["die150"]["ff_hold_ps"],
                         region_ss_setup_ps=t["region"]["ss_setup_ps"], region_ff_hold_ps=t["region"]["ff_hold_ps"],
                         drc=c["drc_errors"], antenna=c["antenna_violating_nets"], drv=c["drv"],
                         route_period_ps=c["route_period_ps"], die_skew_ps=c["die_skew_ps"])
    ref = json.loads(REF_STAGE.read_text())["stage_wave1"]["jobs"]
    jobs, outs = stage_jobs(a.stage_tail.read_text())
    assert len(jobs) == len(ref) == len(outs) and "PASS" in a.stage_tail.read_text().split()
    handoff = max(jobs[i]["start"] - jobs[i - 1]["done"] for i in range(1, len(jobs)))
    ref_handoff = max(j["handoff_after_prev_done"] for j in ref[1:])
    out_lat = max(o - j["done"] for j, o in zip(jobs, outs))
    ref_out = max(j["out_done_after_done"] for j in ref)
    entry = jobs[0]["start"] - ref[0]["start"]
    busy0 = ref[0]["busy"]
    exact = all(x in a.bench_summary.read_text() for x in ("EQUIV PASS",)) and a.exact
    accepted = all(e["accepted"] for e in els.values())
    out = dict(schema="opentallas.rtl.dsrom_wfc_split_closure.v1", source_commit=a.source_commit,
               accepted=accepted, exact=exact,
               verdict=("CLOSED: src and stg WFC elements routed at 770 ps with the +-150 ps die IO model, signed off at "
                        "833.333 ps: SS >= +15 / FF >= +15 in context, reg2reg and region (150 ps stage link, 90 ps intra-region, "
                        "50 ps hold IO uncertainty); DRC / antenna / DRV 0; exact"
                        if accepted and exact else "NOT CLOSED"),
               acceptance_rule="OWNER 18:15 (2026-10-06): SS setup >= +15, FF hold >= +15 at 833.333 (incontext, reg2reg, region: 150 ps on the stage link, 90 ps intra-region, 50 ps hold IO uncertainty), "
                               "DRC 0, antenna 0, max slew / cap / fanout violators 0 at SS and FF",
               elements=els, physical_record=str(a.record_rel), bench_summary=str(a.bench_rel),
               stage_bench=str(a.stage_rel),
               charge=dict(handoff_cycles=handoff, reference_handoff_cycles=ref_handoff,
                           measured_interval_overhead=round(handoff / busy0, 6),
                           reference_interval_overhead=round(ref_handoff / busy0, 6),
                           hop_delta_cycles=(out_lat - ref_out) + entry,
                           hop_delta_parts=dict(done_to_out_cycles=out_lat, reference_done_to_out_cycles=ref_out,
                                                entry_start_delta_cycles=entry),
                           basis="stage bench w1 (L20 stage, 6 jobs) vs the reference ot_rom_pkg_ctrl_wf wave-1 run "
                                 "(results/rtl/dsrom_wavefront_verify_20261004/record.json): handoff = max done -> next start; "
                                 "hop charge = (done -> outbound flit) delta + first-job entry delta (inbound link), "
                                 "conservatively both on every stage hop"))
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(accepted=accepted, exact=exact, charge=out["charge"]), indent=1))
    return 0 if accepted and exact else 1


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
    p.add_argument("--route-period", type=int, default=None, help="over-constrained route period ps (signoff stays 833)")
    p.add_argument("--die-skew", type=int, default=0, help="ps: io_clk min/max source latency widened by this (die150 budget)")
    p.add_argument("--link-hold-pad", type=int, default=0, help="ps: extra hold pad on the stage-link inputs in_* in the POST_CTS repair")
    p.add_argument("--link-hold-abs-min", type=float, default=None, help="ps: absolute min input delay on in_* in the POST_CTS hold repair")
    s = sub.add_parser("sta")
    s.add_argument("--case", type=Path, required=True)
    s.add_argument("--macros", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--case", type=Path, required=True)
    r = sub.add_parser("record")
    r.add_argument("--case", action="append", required=True)
    r.add_argument("--note", action="append", default=[])
    r.add_argument("--out", type=Path, required=True)
    z = sub.add_parser("closure")
    z.add_argument("--record", type=Path, required=True)
    z.add_argument("--stage-tail", type=Path, required=True)
    z.add_argument("--bench-summary", type=Path, required=True)
    z.add_argument("--exact", action="store_true", help="every positive bench PASS and every negative FAIL (checked by hand)")
    z.add_argument("--source-commit", required=True)
    z.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "closure":
        a.record_rel, a.bench_rel, a.stage_rel = (p.resolve().relative_to(ROOT) for p in (a.record, a.bench_summary, a.stage_tail))
    sys.exit({"prep": cmd_prep, "sta": cmd_sta, "check": cmd_check, "record": cmd_record, "closure": cmd_closure}[a.cmd](a))


if __name__ == "__main__":
    main()

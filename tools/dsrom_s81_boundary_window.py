#!/usr/bin/env python3
"""Boundary timing windows of a routed DS-ROM unit, for the S81 deferred-input-hold check (CLAUDE S81-RERUN, item 10).

Several fused / recovery units were closed with their IO cut (su_norm: hold false path on every non-clock input;
run_abi3_physical.py --false-path-io: setup AND hold of every input and output; results/rtl/dsrom_recovery_20261004/
combined/deferred_input_hold.json).  Their parent must check those boundaries.  This tool measures, on the unit's own
routed database (6_final odb + spef, propagated clock), the window every port needs from its parent:

  input  p: the SDC's IO false paths and IO delays are dropped and p gets set_input_delay 0 (min and max) on the
            unit clock, so with the clock edge at the unit's clk PORT as the reference
              req_min_ps(p)  = -hold slack  (the earliest the parent may change p after the edge; FF corner)
              max_arr_ps(p)  =  setup slack (the latest the parent's data may arrive at p;        SS corner)
  output p: set_output_delay 0, so  out_min_ps(p) = FF hold slack + 25 ps (earliest change after the edge) and
            out_max_ps(p) = T - 60 ps - SS setup slack (latest valid)
plus write_timing_model's min / max clock tree path (the unit's internal insertion) at both corners.

`check` composes the windows with a common-clock parent driver / capture register (the S81 glue: an ASAP7 DFF of
ot_fwd_link_stage / the r9 boundary banks) under two parent clock policies:
  P0  parent CTS treats the unit clk pin as a plain sink: launch / capture registers at the port's edge (offset 0);
  P1  parent CTS balances with the unit's insertion (liberty min/max_clock_tree_path, as r9 does for the q element):
      parent registers clocked at the unit's internal arrival (offset = min / max clock tree path).
and reports, per port group, whether a feasible launch-clock offset exists at all and whether P0 / P1 lie inside it.

    python3 tools/dsrom_s81_boundary_window.py emit --base <orfs results base> --top T --out DIR [--lib-glob G]
    (run DIR/run.sh on the compute host)  then  python3 tools/dsrom_s81_boundary_window.py check --dir DIR [...]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

T_PS = 833.0
SETUP_U, HOLD_U = 60.0, 25.0
# ASAP7 DFFHQNx1 (ot_fwd_link_stage / bank registers), asap7sc7p5t_SEQ_RVT_{FF,SS}_nldm_220123.lib tables:
# FF clk->QN min = cell_fall at clock slew 5 ps / 0.72 fF (32.2 ps, the most optimistic = worst for hold);
# SS clk->QN max = cell_rise at clock slew 40 ps / 5.76 fF (115.6 ps); D setup SS <= 28.6, D hold FF <= 13.6 ps
# (rise / fall constraint tables at data slew <= 40 ps).
DFF = dict(clkq_min_ff=32.2, clkq_max_ss=115.6, setup_ss=28.6, hold_ff=13.6)

TCL = r'''
set C {corner}
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $L/asap7sc7p5t_*_RVT_${{C}}_nldm_*.lib*] {{ read_liberty $f }}
foreach f [glob -nocomplain {lib_glob}] {{ if {{[string match -nocase "*_{c}.lib" $f]}} {{ read_liberty $f }} }}
read_db /b/{odb}
read_sdc /o/boundary.sdc
read_spef /b/{spef}
set_propagated_clock [all_clocks]
set ck [lindex [all_clocks] 0]
set clkn {{}}
foreach s [get_property $ck sources] {{ lappend clkn [get_full_name $s] }}
set ins {{}}
foreach p [all_inputs] {{ if {{[lsearch -exact $clkn [get_full_name $p]] < 0}} {{ lappend ins $p }} }}
set_input_delay 0 -clock $ck $ins
set_output_delay 0 -clock $ck [all_outputs]
set fo [open /o/window_${{C}}.tsv w]
set chk [expr {{"$C" eq "FF" ? "min" : "max"}}]
foreach p $ins {{
  set pe [find_timing_paths -from $p -path_delay $chk -group_path_count 1 -endpoint_path_count 1]
  if {{[llength $pe]}} {{ puts $fo "in\t[get_full_name $p]\t[get_property [lindex $pe 0] slack]" }} else {{ puts $fo "in\t[get_full_name $p]\tinf" }}
}}
foreach p [all_outputs] {{
  set pe [find_timing_paths -to $p -path_delay $chk -group_path_count 1 -endpoint_path_count 1]
  if {{[llength $pe]}} {{ puts $fo "out\t[get_full_name $p]\t[get_property [lindex $pe 0] slack]" }} else {{ puts $fo "out\t[get_full_name $p]\tinf" }}
}}
close $fo
write_timing_model -library_name {top}_{c} /o/{top}_{c}.lib
set_false_path -from $ins
set_false_path -to [all_outputs]
report_worst_slack -$chk
puts "OT_WINDOW_DONE {corner}"
'''

DROP = re.compile(r"^\s*(set_false_path|set_input_delay|set_output_delay|set_load|set_driving_cell|set_input_transition)\b")


def emit(a):
    base, out = Path(a.base), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    odb = a.odb or ("6_final.odb" if (base / "6_final.odb").exists() else "5_route.odb")
    sdc_src = base / (a.sdc or "6_final.sdc")
    spef = a.spef or "6_final.spef"
    stmts, cur = [], []
    for ln in sdc_src.read_text().splitlines():
        cur.append(ln)
        if not ln.rstrip().endswith("\\"):
            stmts.append(cur)
            cur = []
    if cur:
        stmts.append(cur)
    lines, dropped = [], 0
    for st in stmts:
        txt = " ".join(st)
        # IO constraints go; a false path is dropped only when it names ports (internal false paths are kept)
        if DROP.match(txt) and (not txt.lstrip().startswith("set_false_path") or "get_ports" in txt
                                or "all_inputs" in txt or "all_outputs" in txt):
            dropped += 1
            continue
        lines += st
    (out / "boundary.sdc").write_text("\n".join(lines) + "\n")
    for corner in ("SS", "FF"):
        (out / f"window_{corner}.tcl").write_text(TCL.format(corner=corner, c=corner.lower(), odb=odb, spef=spef,
                                                              lib_glob=a.lib_glob or "/x/none", top=a.top))
    mnt = f"-v {a.lib_dir}:/x:ro " if a.lib_dir else ""
    run = ["#!/bin/bash", "# GENERATED by tools/dsrom_s81_boundary_window.py (CLAUDE S81-RERUN)", "set -u",
           f"O=$(readlink -f $(dirname $0)); B={base}"]
    for corner in ("SS", "FF"):
        run.append(f"docker run --rm --name bw_{a.name}_{corner} -v $B:/b:ro -v $O:/o {mnt}openroad/orfs:asap7lock "
                   f"bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit "
                   f"/o/window_{corner}.tcl > /o/window_{corner}.log 2>&1; chmod -R a+rwX /o'")
    (out / "run.sh").write_text("\n".join(run) + "\n")
    (out / "run.sh").chmod(0o755)
    (out / "meta.json").write_text(json.dumps(dict(name=a.name, top=a.top, base=str(base), odb=odb, spef=spef,
                                                   sdc=str(sdc_src), sdc_lines_dropped=dropped, lib_glob=a.lib_glob,
                                                   lib_dir=a.lib_dir), indent=1) + "\n")
    print(out)


def _bus(name):
    m = re.match(r"^(.*?)\[\d+\]$", name)
    return m.group(1) if m else name


def _tree(lib):
    t = Path(lib).read_text()
    r = {}
    for k in ("min_clock_tree_path", "max_clock_tree_path"):
        m = re.search(k + r";\s*cell_rise\(scalar\)\s*\{\s*values\(\"([-\d.]+)\"\)", t)
        r[k] = float(m.group(1)) if m else None
    return r


def check(a):
    d = Path(a.dir)
    meta = json.loads((d / "meta.json").read_text())
    top = meta["top"]
    win = {}
    for corner in ("SS", "FF"):
        for ln in (d / f"window_{corner}.tsv").read_text().splitlines():
            kind, port, s = ln.split("\t")
            s = float(s) if s != "inf" else float("inf")
            win.setdefault((kind, _bus(port)), {}).setdefault(corner, []).append(s)
    tree = {c: _tree(d / f"{top}_{c}.lib") for c in ("ss", "ff")}
    i_min_ff = tree["ff"]["min_clock_tree_path"] or 0.0
    i_max_ss = tree["ss"]["max_clock_tree_path"] or 0.0
    groups = []
    for (kind, bus), cs in sorted(win.items()):
        ss = min(cs.get("SS", [float("inf")]))
        ff = min(cs.get("FF", [float("inf")]))
        g = dict(kind=kind, port=bus, bits=len(cs.get("SS", cs.get("FF", []))), ss_slack_ps=ss, ff_slack_ps=ff)
        if kind == "in":
            req_min, max_arr = -ff, ss
            # parent launch-clock offset o (relative to the port edge): data arrives in [o + clkq_min, o + clkq_max + w]
            lo = req_min - DFF["clkq_min_ff"]
            hi = max_arr - DFF["clkq_max_ss"] - a.wire_ps
            g.update(req_min_ps=round(req_min, 2), max_arr_ps=round(max_arr, 2), offset_window_ps=[round(lo, 2),
                     round(hi, 2)], feasible=lo <= hi, P0=lo <= 0 <= hi, P1=lo <= i_min_ff and i_max_ss <= hi)
        else:
            out_min, out_max = ff + HOLD_U, T_PS - SETUP_U - ss
            # parent capture-clock offset o: setup out_max + w <= T - 60 + o - tsu ; hold out_min >= o + th + 25
            lo = out_max + a.wire_ps + DFF["setup_ss"] + SETUP_U - T_PS
            hi = out_min - DFF["hold_ff"] - HOLD_U
            g.update(out_min_ps=round(out_min, 2), out_max_ps=round(out_max, 2), offset_window_ps=[round(lo, 2),
                     round(hi, 2)], feasible=lo <= hi, P0=lo <= 0 <= hi, P1=lo <= i_min_ff and i_max_ss <= hi)
        groups.append(g)
    fails = [g["port"] for g in groups if not g["feasible"]]
    rec = dict(schema="opentallas.dsrom-s81.boundary-window.v1", tool="tools/dsrom_s81_boundary_window.py",
               unit=meta["name"], top=top, base=meta["base"], wire_ps=a.wire_ps, dff=DFF,
               clock_tree_path_ps=tree, groups=groups,
               summary=dict(groups=len(groups), infeasible=fails,
                            P0_pass=all(g["P0"] for g in groups if g["ss_slack_ps"] != float("inf") or g["ff_slack_ps"] != float("inf")),
                            P1_pass=all(g["P1"] for g in groups if g["ss_slack_ps"] != float("inf") or g["ff_slack_ps"] != float("inf")),
                            P0_fail=[g["port"] for g in groups if not g["P0"]],
                            P1_fail=[g["port"] for g in groups if not g["P1"]]))
    txt = json.dumps(rec, indent=1).replace("Infinity", '"inf"')
    (d / "boundary_window.json").write_text(txt + "\n")
    print(json.dumps(rec["summary"], indent=1), json.dumps(tree))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("emit")
    p.add_argument("--base", required=True)
    p.add_argument("--top", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--odb")
    p.add_argument("--spef")
    p.add_argument("--sdc")
    p.add_argument("--lib-dir", help="host directory with macro liberty files, mounted at /x")
    p.add_argument("--lib-glob", help="glob inside the container, e.g. /x/*.lib")
    p = sub.add_parser("check")
    p.add_argument("--dir", required=True)
    p.add_argument("--wire-ps", type=float, default=30.0, help="parent wire from the bank register to the port (SS)")
    a = ap.parse_args()
    return emit(a) if a.cmd == "emit" else check(a)


if __name__ == "__main__":
    raise SystemExit(main())

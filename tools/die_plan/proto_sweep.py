#!/usr/bin/env python3
"""PROTO sweep (lane PROTO 2026-10-24, virtual prototyping before detailed route): per partition TYPE of a die plan,
the G2 partition probe (g2.part_probe: exact outline + plan pins, one boundary flop per pin bit, ft station flops at
their sites, hard-core / leaf outlines as placement blockages + M1..obs_max obstructions) extended with

  * one ideal clock on every flop (port ot_clk, 833 ps or the plan period), plan IO budget (0.2 T in/out delay),
    60 / 25 ps setup / hold uncertainty, TT + FF corners (RVT NLDM);
  * repair_design (repeaters / buffers on the long pin -> reg and station -> station wires) + re-legalisation;
  * GRT on M2..top with the partition's own logic modelled as a capacity adjustment (g2 --adjust, default 0.5);
  * STA on GRT parasitics: TT setup WNS / TNS / violators, FF hold WNS / violators, max slew / cap violators;
  * a geometry dump (outline, blockages, flops, pins, buffers, GRT congestion gcells) for proto_render.py.

It is a SKELETON prototype: the partition's own logic is not synthesised (only its routing demand, as capacity), so
timing covers the plan's wires only (pin -> pin register, ft station hops, repeater pitch).  Read-only diagnostic:
nothing is written into the plan.

    proto_sweep.py gen     PLAN.json --out DIR --types a,b|--all [--adjust 0.5] [--skip a,b]
    proto_sweep.py collect DIR [--json OUT]     # parse every DIR/part_*/ -> proto.json + classification
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g2  # noqa: E402
import schema as S  # noqa: E402
from proto_geometry import hop_stats  # noqa: E402

LIBS = ["AO", "INVBUF", "OA", "SEQ", "SIMPLE"]
LIBDIR = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"


def lib_files(corner):
    tag = {"tt": "TT", "ff": "FF"}[corner]
    out = []
    for k in LIBS:
        date = "220123" if k == "SEQ" else ("220122" if k == "INVBUF" else "211120")
        out.append(f"{LIBDIR}/asap7sc7p5t_{k}_RVT_{tag}_nldm_{date}.lib" + ("" if k == "SEQ" else ".gz"))
    return out


def mem_gb(P, tn):
    """honest memory request: GRT + pin access scale with area and pin count (measured on the first batch)."""
    w, h = P.types[tn]["outline_um"]
    a = w * h / 1e6
    return int(min(256, max(10, math.ceil(4 + 8 * a))))     # pilot: 0.67 mm2 4.7 GB, 1.47 mm2 10.6, 1.95 mm2 12.3


def over_routable(t, top):
    """boxes (x0, y0, x1, y1, obs_max) of every probe blockage whose routing obstruction stops below the partition top layer
    (same obstruction rule as g2.part_probe: obs_max, default M5): wires cross them on the layers above, so the
    repeaters of those wires belong in the islands outside them, never inside (tools/die_plan/gap_repeaters.tcl)."""
    out = []
    for c in g2.probe_blockages(t, top):
        if "origin_um" not in c or "outline_um" not in c:
            continue
        obs = c.get("obs_max", "M5")
        if int(obs[1:]) < int(top[1:]):
            x0, y0 = c["origin_um"]
            out.append((x0, y0, x0 + c["outline_um"][0], y0 + c["outline_um"][1], obs))
    return out


REPAIR_ARGS = "{-max_wire_length 450}"


def gap_repair_tcl(t, top):
    """placement-stage repair_design with repeater islands (gap_repeaters.tcl ot_gap_repair).

    Industry practice for feedthroughs routed over a hard macro on the layers above its OBS: the repeaters of those
    nets sit in islands in the channel rows outside the macros, on the ribbon's line, on the driver side of the
    crossing.  The cores are hard placement blockages before repair_design, but the resizer drops a new buffer on the
    Steiner point regardless (only DPL honours blockages, and DPL alone shoves it sideways into the nearest strip: QC
    slw_su_l1 G2 overflow 8,787).  ot_gap_repair moves such repeaters along their ribbon to the island; the GRT stage
    (ot_gap_repair_grt, after global_route) then re-runs repair_design on global-route parasitics with the islands in
    place, as ORFS global_route.tcl does, so the island repeaters are sized and spaced for the span they drive."""
    boxes = over_routable(t, top)
    return [
        "set ot_gap_cores {" + " ".join("{" + " ".join(f"{v:.3f}" for v in bx[:4]) + f" {bx[4]}}}" for bx in boxes)
        + "}",
        f"set ot_gap_top {top}",
        f"set ot_gap_m {g2.gen_phys.CORE_MARGIN_UM:g}",
        "source /work/gap_repeaters.tcl",
        f"ot_gap_repair {REPAIR_ARGS}",
    ]


def gen_one(P, tn, out, adjust):
    d = g2.part_probe(P, tn, out, adjust=adjust, mem=32)
    v = (d / "probe.v").read_text()
    # every flop on one ideal clock port
    v = v.replace("module ftprobe (\n", "module ftprobe (\n  input ot_clk,\n", 1)
    v = re.sub(r"(DFFHQNx1_ASAP7_75t_R \S+ \()", r"\1.CLK(ot_clk), ", v)
    (d / "probe.v").write_text(v)
    tcl = (d / "probe.tcl").read_text().splitlines()
    # g2.probe_blockages only blocks hard cores that split a content leaf with an outline; a prototype must block
    # EVERY planned hard core (KV hg/hgi/pc/pv, QC su_l*, S81 leaves / svc / slices carry cores without such a leaf)
    t = P.types[tn]
    cov = {c.get("inst") for c in g2.probe_blockages(t)}
    extra = []
    for hc in t.get("hard_cores", []):
        if hc["inst"] in cov or "origin_um" not in hc or "outline_um" not in hc:
            continue
        x0, y0 = hc["origin_um"]
        x1, y1 = x0 + hc["outline_um"][0], y0 + hc["outline_um"][1]
        extra.append(f"create_blockage -region {{{x0:g} {y0:g} {x1:g} {y1:g}}}")
        for L in g2.lrange("M1", hc.get("obs_max", "M5")):
            extra.append(f"create_obstruction -region {{{x0:g} {y0:g} {x1:g} {y1:g}}} -layer {L}")
    pi = next(k for k, ln in enumerate(tcl) if ln.startswith("place_inst") or ln.startswith("detailed_placement"))
    tcl = tcl[:pi] + extra + tcl[pi:]
    n_extra = sum(1 for x in extra if x.startswith("create_blockage"))
    period = float(P.die.get("period_ps", 833))
    io = 0.2 * period
    head = ["define_corners tt ff"]
    for c in ("tt", "ff"):
        head += [f"read_liberty -corner {c} {f}" for f in lib_files(c)]
    # insert liberty right after the LEFs
    i = max(k for k, ln in enumerate(tcl) if ln.startswith("read_lef")) + 1
    tcl = tcl[:i] + head + tcl[i:]
    j = next(k for k, ln in enumerate(tcl) if ln.startswith("check_placement"))
    taps = [nm for nm, _, _ in g2.gen_phys.tap_pins(P, tn)]
    timing = [
        "set ot_t0 [clock seconds]",
        f"create_clock -name clk -period {period:g} [get_ports ot_clk]",
        "set ot_skip [list ot_clk " + " ".join(taps) + "]",
        "set ot_ins {}",
        "foreach p [get_ports -filter {direction == input}] { if {[lsearch -exact $ot_skip [get_name $p]] < 0} "
        "{ lappend ot_ins $p } }",
        f"if {{[llength $ot_ins]}} {{ set_input_delay {io:g} -clock clk $ot_ins }}",
        f"if {{[llength [all_outputs]]}} {{ set_output_delay {io:g} -clock clk [all_outputs] }}",
        "set_clock_uncertainty -setup 60 [all_clocks]",
        "set_clock_uncertainty -hold 25 [all_clocks]",
        # ASAP7 platform RC (the tech LEF carries none: set_wire_rc -layer gave zero wire C, pilot 10-24 21:5x)
        "source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl",
        "set_dont_use {*x1p*_ASAP7* *SL* *LVT* ICGx*}",
        "estimate_parasitics -placement",
        # repeaters at the owner spacing (450 um) also on pin nets; plan IO load 2 fF; 320 ps slew limit
        "set_load 2 [all_outputs]",
        "set_max_transition 320 [current_design]",
        *gap_repair_tcl(t, P.type_top_layer(tn)),
        "puts \"OT_REPAIR_S [expr {[clock seconds]-$ot_t0}]\"",
        # the ideal skeleton clock is not routed (the real clock tree is the partition's own logic: capacity adjust)
        "set ot_ck [[ord::get_db_block] findNet ot_clk]; $ot_ck setSpecial; $ot_ck setSigType CLOCK",
    ]
    tcl = tcl[:j + 1] + timing + tcl[j + 1:]
    k = next(k for k, ln in enumerate(tcl) if ln.startswith("if {[catch {pin_access}"))
    post = [
        # ORFS global_route.tcl order: repair_design on GRT parasitics + incremental GRT, islands kept (cores blocked)
        f"ot_gap_repair_grt {REPAIR_ARGS} {{-allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt}}",
        "ot_gap_check 4.0",
        "report_checks -path_delay max -scenes tt -format end -group_path_count 1000000 -endpoint_path_count 1 "
        "> /work/tt_setup_end.rpt",
        "report_checks -path_delay min -scenes ff -format end -group_path_count 1000000 -endpoint_path_count 1 "
        "> /work/ff_hold_end.rpt",
        "report_check_types -max_slew -max_capacitance -violators -scenes tt > /work/drv.rpt",
        "ot_drv_classify /work/drv.rpt /work/drv_class.tsv",
        "report_checks -path_delay max -scenes tt -group_path_count 5 -format full > /work/tt_setup.rpt",
        "report_checks -path_delay min -scenes ff -group_path_count 5 -format full > /work/ff_hold.rpt",
        "set ot_nb 0; foreach i [[ord::get_db_block] getInsts] { if {[regexp {^(BUF|INV|HB)} [[$i getMaster] getName]]} "
        "{ incr ot_nb } }",
        "puts \"OT_BUFS $ot_nb\"",
        # geometry dump for proto_render.py: insts (flops/buffers) and the GRT congestion report is in grt_congestion.rpt
        "set ot_f [open /work/insts.tsv w]",
        "set ot_dbu [[ord::get_db_block] getDbUnitsPerMicron]",
        "foreach i [[ord::get_db_block] getInsts] { set bb [$i getBBox]; "
        "puts $ot_f \"[$i getName]\\t[[$i getMaster] getName]\\t[expr {[$bb xMin]/double($ot_dbu)}]\\t"
        "[expr {[$bb yMin]/double($ot_dbu)}]\\t[expr {[$bb xMax]/double($ot_dbu)}]\\t"
        "[expr {[$bb yMax]/double($ot_dbu)}]\" }",
        "close $ot_f",
    ]
    tcl = tcl[:k] + post + tcl[k:]
    # bounded GRT effort: a prototype needs WHERE the overflow is, not 30 maze rounds (pilot: 20+ min per round)
    tcl = [ln.replace("-congestion_iterations 30", "-congestion_iterations 3") for ln in tcl]
    (d / "probe.tcl").write_text("\n".join(tcl) + "\n")
    (d / "gap_repeaters.tcl").write_text((Path(__file__).resolve().parent / "gap_repeaters.tcl").read_text())
    mem = mem_gb(P, tn)
    (d / "run.sh").write_text(f"""#!/bin/bash
# PROTO skeleton prototype (g2 partition probe + repair_design + GRT-RC STA TT/FF); run via ot-run --mem {mem}
D=$(cd $(dirname $0) && pwd)
N=proto-$(basename $D)-$$
docker run --rm --name ${{N:0:120}} --cpus=8 --memory={mem}g --memory-swap={mem}g -v $D:/work -w /work \\
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \\
  /usr/bin/time -v openroad -threads 8 -no_init -exit /work/probe.tcl > /work/grt.log 2> /work/time.log; \\
  rc=\\$?; echo EXIT \\$rc > /work/probe.exit; chmod -R a+rwX /work; exit \\$rc"
rc=$?
cat $D/probe.exit
exit $rc
""")
    meta = json.loads((d / "probe.json").read_text())
    meta.update(kind="proto-skeleton", mem_gb=mem, period_ps=period, io_delay_ps=io, core_blockages=n_extra,
                leaf_blockages=meta.get("leaf_blockages", 0) + n_extra)
    (d / "probe.json").write_text(json.dumps(meta, indent=1) + "\n")
    return d, mem


def end_slacks(text):
    """slack column of an OpenSTA `report_checks -format end` table (Endpoint  Required  Actual  Slack)."""
    out = []
    for ln in text.splitlines():
        p = ln.split()
        if len(p) < 4:
            continue
        if p[-1] in ("(VIOLATED)", "(MET)"):
            p = p[:-1]
        try:
            vals = [float(x) for x in p[-3:]]
        except ValueError:
            continue
        out.append(vals[-1])
    return out


def drv_classes(d):
    """max slew / cap violators split into INTERNAL pins (in-partition wires: must be 0), port legs (a pin on a net that
    has a top-level port = the die hop to the neighbour's first station, measured by the die reach scan) and the port
    pins themselves.  drv_class.tsv comes from ot_drv_classify in the probe; older probes fall back to the pin name
    (a hierarchical pin counts as INTERNAL: fail-closed)."""
    rows = []
    if (d / "drv_class.tsv").exists():
        for ln in (d / "drv_class.tsv").read_text().splitlines()[1:]:
            p = ln.split("\t")
            if len(p) >= 6:
                rows.append((p[0], p[1], float(p[3]), p[5]))
    else:
        chk = ""
        for ln in (d / "drv.rpt").read_text(errors="replace").splitlines():
            if ln.startswith("max slew"):
                chk = "slew"
            elif ln.startswith("max capacitance"):
                chk = "cap"
            m = re.match(r"(\S+)\s+[-\d.]+\s+([-\d.]+)\s+[-\d.]+\s+\(VIOLATED\)", ln)
            if m:
                rows.append((chk, m.group(1), float(m.group(2)), "internal" if "/" in m.group(1) else "port_pin"))
    out = dict(violators=len(rows), source="drv_class.tsv" if (d / "drv_class.tsv").exists() else "drv.rpt names")
    for cls in ("internal", "port_leg", "port_pin"):
        for chk in ("slew", "cap"):
            v = [val for c, _, val, k in rows if k == cls and c == chk]
            out[f"{cls}_{chk}"] = len(v)
            if v and chk == "slew":
                out[f"{cls}_slew_max_ps"] = round(max(v), 2)
    worst = sorted(((val, pin) for c, pin, val, k in rows if k == "internal" and c == "slew"), reverse=True)[:5]
    out["internal_worst"] = [f"{p} {v:g}" for v, p in worst]
    return out


def parse_dir(d):
    d = Path(d)
    meta = json.loads((d / "probe.json").read_text())
    log = (d / "grt.log").read_text(errors="replace") if (d / "grt.log").exists() else ""
    r = g2.parse_grt(log)
    r.update(meta)
    # run status from the files, not from the memory figure: probe.exit is written after openroad exits, OT_DONE is
    # the last line of the probe; a probe collected while still running is RUNNING / INCOMPLETE, never 'NOT RUN'
    if (d / "probe.exit").exists():
        r["exit"] = (d / "probe.exit").read_text().strip()
        r["status"] = "DONE" if (r["exit"] == "EXIT 0" and "OT_DONE" in log) else (
            "INCOMPLETE" if r["exit"] == "EXIT 0" else "FAILED")
    else:
        r["exit"] = "NOT RUN"
        r["status"] = "RUNNING" if log else "NOT RUN"
    gm = re.findall(r"OT_GAP pass (\d+) \((\w+)\) moved (\d+) of (\d+)", log)
    if gm:
        gp = re.search(r"OT_GAP_PASS (\d+) repeaters in gap rows, max \|dx\| ([0-9.]+) um, max \|dy\| ([0-9.]+) um, "
                       r"max ribbon dev ([0-9.]+)", log)
        gf = re.search(r"OT_GAP_FAIL (\d+)", log)
        r["gap_repeaters"] = dict(passes=[dict(stage=st, moved=int(mv), new=int(nw)) for _, st, mv, nw in gm],
                                  moved=sum(int(mv) for _, _, mv, _ in gm),
                                  last_pass_moved=int(gm[-1][2]), passed=bool(gp) and not gf,
                                  fail=int(gf.group(1)) if gf else (0 if gp else None),
                                  islands=int(gp.group(1)) if gp else None,
                                  max_dx_um=float(gp.group(2)) if gp else None,
                                  max_dy_um=float(gp.group(3)) if gp else None,
                                  max_ribbon_dev_um=float(gp.group(4)) if gp else None,
                                  unrepeatable=sum(int(x) for x in re.findall(r"OT_GAP_UNREPEATABLE pass \d+ (\d+)", log)))
    sta = {}
    for key, fn in (("tt_setup", "tt_setup_end.rpt"), ("ff_hold", "ff_hold_end.rpt")):
        sl = None
        if (d / fn).exists():
            sl = end_slacks((d / fn).read_text(errors="replace"))
        elif (d / (fn + ".slk")).exists():       # slack column only (fleet-side extract, keeps the copy-back small)
            sl = [float(x) for x in (d / (fn + ".slk")).read_text().split()]
        if sl is not None:
            sta[key + "_wns"] = round(min(sl), 2) if sl else None
            sta[key + "_tns"] = round(sum(x for x in sl if x < 0), 1)
            sta[key + "_viol"] = sum(1 for x in sl if x < 0)
            sta[key + "_endpoints"] = len(sl)
    if sta:
        r["sta"] = sta
    m = re.search(r"OT_BUFS (\d+)", log)
    r["repair_buffers"] = int(m.group(1)) if m else None
    if (d / "drv.rpt").exists():
        r["drv"] = drv_classes(d)
    tl = (d / "time.log").read_text(errors="replace") if (d / "time.log").exists() else ""
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", tl)
    r["peak_gb"] = round(int(m.group(1)) / 1e6, 2) if m else None
    m = re.search(r"Elapsed \(wall clock\) time.*: (\S+)", tl)
    r["wall"] = m.group(1) if m else None
    # congestion hot gcells (GRT report lists violations with bboxes)
    hot = []
    if (d / "grt_congestion.rpt").exists():
        for mm in re.finditer(r"bbox = \( *([\d.]+), *([\d.]+) *\) - \( *([\d.]+), *([\d.]+) *\) on Layer (\S+)",
                              (d / "grt_congestion.rpt").read_text(errors="replace")):
            hot.append([float(mm.group(i)) for i in range(1, 5)] + [mm.group(5)])
    r["hot_gcells"] = len(hot)
    if hot:
        txt = (d / "grt_congestion.rpt").read_text(errors="replace")
        slots = Counter(m.group(1) for m in re.finditer(r"net:n[qd]_st_(.+?)_\d+_\d+\b", txt))
        slots.update(m.group(1) + " (pin regs)" for m in re.finditer(r"net:n[qd]_bf_(.+?)_\d+\b", txt))
        r["hot_slots"] = slots.most_common(5)
        xs = [(x0 + x1) / 2 for x0, _, x1, _, _ in hot]
        ys = [(y0 + y1) / 2 for _, y0, _, y1, _ in hot]
        r["hot_bbox_um"] = [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]
    # legalisation displacement of the planned register sites (station / pin flops pushed out of cores = macro issue)
    if (d / "insts.tsv").exists() and (d / "probe.tcl").exists():
        plan = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
                re.finditer(r"place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}", (d / "probe.tcl").read_text())}
        disp = {"st": [], "bf": []}
        for ln in (d / "insts.tsv").read_text().splitlines():
            p = ln.split("\t")
            if len(p) >= 4 and p[0] in plan and p[0][:2] in disp:
                x0, y0 = plan[p[0]]
                disp[p[0][:2]].append(abs(float(p[2]) - x0) + abs(float(p[3]) - y0))
        r["displacement_um"] = {k: dict(max=round(max(v), 1), p90=round(sorted(v)[int(0.9 * (len(v) - 1))], 1),
                                        over50=sum(1 for x in v if x > 50)) for k, v in disp.items() if v}
    r["ft_hops"] = hop_stats(d)
    r["classify"] = classify(r, hot)
    (d / "proto.json").write_text(json.dumps(r, indent=1) + "\n")
    return r, hot


def classify(r, hot):
    """CLEAN: GRT 0 overflow, no unreachable pins, skeleton setup / hold within fixable range.
    HOTSPOT: local GRT overflow (< 2000, hot bbox < 10 % of the outline), sites moved 50-100 um, or fixable timing (WNS >= -100 ps).
    STRUCTURAL: wide overflow, pin access failure, or skeleton timing a re-pin / station change must fix."""
    st = r.get("status", "DONE" if r.get("exit") == "EXIT 0" and r.get("done") else "NOT RUN")
    if st in ("RUNNING", "INCOMPLETE"):
        return dict(cls=st, why=f"probe {st.lower()} at collect time ({r.get('exit')}): collect again when it exits")
    if r.get("exit") != "EXIT 0" or not r.get("done"):
        return dict(cls="NOT RUN", why=f"exit {r.get('exit')}")
    why = []
    ov = r.get("total_overflow") or 0
    w, h = r["outline_um"]
    area = w * h
    hot_area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1, _ in hot)
    frac = hot_area / area if area else 0
    noap = sum((r.get("pin_access_no_ap") or {}).values())
    sta = r.get("sta", {})
    tt = sta.get("tt_setup_wns")
    ff = sta.get("ff_hold_wns")
    cls = "CLEAN"
    # GRT gcells here are ~0.6 um, so the gcell-area share is always tiny: judge locality by the bbox of the hot
    # gcells (HOTSPOT = overflow < 2000 inside a bbox < 10 % of the outline; else a channel / plan problem)
    if hot:
        bx0, by0 = min(x[0] for x in hot), min(x[1] for x in hot)
        bx1, by1 = max(x[2] for x in hot), max(x[3] for x in hot)
        frac = (bx1 - bx0) * (by1 - by0) / area if area else 0
    if ov:
        cls = "HOTSPOT" if (frac < 0.10 and ov < 2000) else "STRUCTURAL"
        why.append(f"GRT overflow {ov} ({len(hot)} gcells, hot bbox {100 * frac:.1f}% of outline)")
    if noap:
        cls = "STRUCTURAL"
        why.append(f"{noap} pins without access")
    for k, lab in (("st", "ft station"), ("bf", "pin register")):
        dd = (r.get("displacement_um") or {}).get(k)
        if dd and dd["over50"]:
            if dd["max"] > 100:
                cls = "STRUCTURAL"
            elif cls == "CLEAN":
                cls = "HOTSPOT"
            why.append(f"{dd['over50']} {lab} sites legalised > 50 um away (max {dd['max']} um: planned site "
                       f"inside a core / blockage)")
    if tt is not None and tt < 0:
        if tt < -100:
            cls = "STRUCTURAL"
        elif cls == "CLEAN":
            cls = "HOTSPOT"
        why.append(f"skeleton TT setup WNS {tt:.1f} ps ({sta.get('tt_setup_viol')} endpoints)")
    if ff is not None and ff < 0:
        # > -30 ps = back-to-back station flops on one site (hold buffers fix it; not a plan problem)
        if cls == "CLEAN" and ff < -30:
            cls = "HOTSPOT"
        why.append(f"skeleton FF hold WNS {ff:.1f} ps ({sta.get('ff_hold_viol')} endpoints)")
    geometry = r.get("ft_hops") or {}
    if geometry.get("actual_sites") is False or geometry.get("errors"):
        cls = "STRUCTURAL"
        why.append("actual post-placement FT geometry unqualified: " +
                   "; ".join(geometry.get("errors") or ["actual station sites unavailable"]))
    if geometry.get("over_reach"):
        cls = "STRUCTURAL"
        legs = ", ".join(f"{k} {v:g}" for k, v in list(geometry["over_reach"].items())[:3])
        why.append(f"{len(geometry['over_reach'])} ft slots exceed 405 um at actual pin-bit coordinates ({legs} um)")
    gap = r.get("gap_repeaters")
    if gap is not None and not gap.get("passed"):
        cls = "STRUCTURAL"
        why.append(f"repeater island check failed ({gap.get('fail')} of {gap.get('moved')} island repeaters in a core "
                   f"or off the ribbon)")
    elif gap is not None and gap.get("moved"):
        why.append(f"{gap['islands']} over-core repeaters in islands (max dx {gap['max_dx_um']} / dy "
                   f"{gap['max_dy_um']} um, last pass moved {gap['last_pass_moved']})")
    if gap is not None and gap.get("unrepeatable"):
        cls = "STRUCTURAL"
        why.append(f"{gap['unrepeatable']} repeaters on hard-core crossings longer than the 290-um single-span reach "
                   f"(plan item: re-aspect the core or route the ribbon through a repeater channel)")
    drv = r.get("drv") or {}
    ni = drv.get("internal_slew", 0) + drv.get("internal_cap", 0)
    if ni:
        # an internal max-slew / max-cap violator is an under-driven in-partition wire: never CLEAN
        cls = "STRUCTURAL"
        why.append(f"{drv.get('internal_slew', 0)} internal max-slew (worst {drv.get('internal_slew_max_ps')} ps) + "
                   f"{drv.get('internal_cap', 0)} internal max-cap violators")
    npl = drv.get("port_leg_slew", 0) + drv.get("port_pin_slew", 0)
    if npl:
        why.append(f"port legs: {drv.get('port_leg_slew', 0)} driver + {drv.get('port_pin_slew', 0)} port max-slew "
                   f"(die hop, last station -> neighbour first station, in the die reach scan)")
    if geometry.get("st_in_core"):
        cls = "STRUCTURAL"
        why.append(f"{geometry['st_in_core']} planned ft station sites inside hard cores")
    return dict(cls=cls, why="; ".join(why) or "GRT 0 overflow, skeleton timing met", hot_frac=round(frac, 4))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("plan")
    g.add_argument("--out", required=True)
    g.add_argument("--types")
    g.add_argument("--all", action="store_true")
    g.add_argument("--skip", default="")
    g.add_argument("--adjust", type=float, default=0.5)
    c = sub.add_parser("collect")
    c.add_argument("dir")
    c.add_argument("--json")
    a = ap.parse_args(argv)
    if a.cmd == "gen":
        P = S.Plan(S.load(a.plan), Path(a.plan).resolve())
        skip = set(filter(None, a.skip.split(",")))
        types = sorted(P.types) if a.all else a.types.split(",")
        types = [t for t in types if t not in skip and not P.types[t].get("hard")]
        jobs = []
        for tn in types:
            d, mem = gen_one(P, tn, Path(a.out) / f"part_{tn}", a.adjust)
            jobs.append(dict(type=tn, dir=str(d), mem_gb=mem))
            print(f"{tn}\t{mem}\t{d}")
        (Path(a.out) / "jobs.json").write_text(json.dumps(jobs, indent=1) + "\n")
        return 0
    rows = {}
    for d in sorted(Path(a.dir).glob("part_*")):
        if (d / "probe.json").exists():
            rows[d.name[5:]], _ = parse_dir(d)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")
    for tn, r in rows.items():
        s = r.get("sta", {})
        dv = r.get("drv") or {}
        print(f"{tn}\t{r['classify']['cls']}\tov={r.get('total_overflow')}\ttt={s.get('tt_setup_wns')}\t"
              f"ff={s.get('ff_hold_wns')}\tdrv_int={dv.get('internal_slew')}/{dv.get('internal_cap')}\t"
              f"drv_port={dv.get('port_leg_slew')}+{dv.get('port_pin_slew')}\t"
              f"peak={r.get('peak_gb') if r.get('peak_gb') is not None else 'n/a'}\t{r['classify']['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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


def gap_bands(t, clearance=2.0):
    """y bands (lo, hi) of the partition outside every over-routable hard core (cores declaring obs_max below the
    partition top layer: M7 ribbons cross them, so their repeaters belong in the inter-core gap rows)."""
    m = g2.gen_phys.CORE_MARGIN_UM
    h = t["outline_um"][1]
    boxes = sorted((c["origin_um"][1], c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", [])
                   if "origin_um" in c and "outline_um" in c)
    bands, lo = [], m
    for a, b in boxes:
        if a - clearance > lo:
            bands.append((lo, a - clearance))
        lo = max(lo, b + clearance)
    if lo < h - m:
        bands.append((lo, h - m))
    return bands


def gap_repair_tcl(t, top):
    """repair_design, then (STRICT M7-ribbon types) gap-row repeater legalisation, then detailed placement.

    Industry practice for feedthroughs routed over a hard macro on the layers above its OBS: the repeaters of those
    nets sit in the channel rows between the macros (repeater islands), at the ribbon's x.  repair_design drops a
    buffer on the Steiner point, i.e. inside the macro footprint; plain DPL then shoves it sideways to the nearest
    free row (a 17-um side strip), which piles hundreds of repeaters into the strip and turns every ribbon into an
    E-W jog (QC slw_su_l1 G2 overflow 8,787).  Here every NEW buffer/inverter whose origin lies inside an over-routable
    core is moved, before DPL, to the nearest gap-band row at the same x; DPL then only resolves overlaps inside the
    band.  Fail-closed check after DPL: OT_GAP_FAIL counts moved repeaters that did not end in a gap band within 4 um
    of their ribbon x.  Same procs are meant for the partition kit flow (tools/die_plan/gap_repeaters.tcl)."""
    cores = [c for c in t.get("hard_cores", []) if "origin_um" in c and "outline_um" in c
             and c.get("obs_max") and int(c["obs_max"][1:]) < int(top[1:])]
    if not cores:
        return ["repair_design -max_wire_length 450", "detailed_placement -max_displacement {400 400}"]
    bands = gap_bands(t)
    boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
              c["origin_um"][1] + c["outline_um"][1]) for c in cores]
    m = g2.gen_phys.CORE_MARGIN_UM
    return [
        "set ot_gap_bands {" + " ".join(f"{{{a:.3f} {b:.3f}}}" for a, b in bands) + "}",
        "set ot_gap_cores {" + " ".join("{" + " ".join(f"{v:.3f}" for v in bx) + "}" for bx in boxes) + "}",
        f"set ot_gap_m {m:g}",
        "source /work/gap_repeaters.tcl",
        "ot_gap_before_repair",
        "repair_design -max_wire_length 450",
        "ot_gap_move_to_rows",
        "detailed_placement -max_displacement {400 400}",
        "ot_gap_check_after_dpl 4.0",
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
        "estimate_parasitics -global_routing",
        "report_checks -path_delay max -scenes tt -format end -group_path_count 1000000 -endpoint_path_count 1 "
        "> /work/tt_setup_end.rpt",
        "report_checks -path_delay min -scenes ff -format end -group_path_count 1000000 -endpoint_path_count 1 "
        "> /work/ff_hold_end.rpt",
        "report_check_types -max_slew -max_capacitance -violators -scenes tt > /work/drv.rpt",
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


def parse_dir(d):
    d = Path(d)
    meta = json.loads((d / "probe.json").read_text())
    log = (d / "grt.log").read_text(errors="replace") if (d / "grt.log").exists() else ""
    r = g2.parse_grt(log)
    r.update(meta)
    r["exit"] = (d / "probe.exit").read_text().strip() if (d / "probe.exit").exists() else "NOT RUN"
    gm = re.search(r"OT_GAP moved (\d+) of (\d+)", log)
    if gm:
        gp = re.search(r"OT_GAP_PASS (\d+) repeaters in gap rows, max \|dx\| ([0-9.]+)", log)
        gf = re.search(r"OT_GAP_FAIL (\d+)", log)
        r["gap_repeaters"] = dict(moved=int(gm.group(1)), new=int(gm.group(2)), passed=bool(gp) and not gf,
                                  fail=int(gf.group(1)) if gf else (0 if gp else None),
                                  max_dx_um=float(gp.group(2)) if gp else None)
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
        t = (d / "drv.rpt").read_text(errors="replace")
        r["drv"] = dict(violators=len(re.findall(r"VIOLATED", t)))
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
        why.append(f"gap-row repeater check failed ({gap.get('fail')} of {gap.get('moved')} moved repeaters off the gap rows)")
    elif gap is not None:
        why.append(f"{gap['moved']} over-core repeaters in gap rows (max dx {gap['max_dx_um']} um)")
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
        print(f"{tn}\t{r['classify']['cls']}\tov={r.get('total_overflow')}\ttt={s.get('tt_setup_wns')}\t"
              f"ff={s.get('ff_hold_wns')}\tpeak={r.get('peak_gb')}\t{r['classify']['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""HIER W2 rb station physical (el1011-hbm-no3, 2026-10-11; owner textbook audit class 1 / 6).

The flat station routed as ONE clock root over 34,996 sinks (520 x 160 um, util 33 %): ~33k direct flop pairs across
clock leaves needed 9-34k hold buffers.  HIER=1 (station RTL) puts the payload words in word-group slice tiles
(ot_hbm_w2_stn_slice: 8,8,8,8,5 W6 words); this driver hardens one slice as its own block with its own clock tree:

  tile  : one slice piece (slice8 / slice5) at NO=2|3 -> run.sh (ORFS route, ss/ff/tt timing-model + abstract LEF,
          sign-off corner STA at 833 ps).  The closure loop routes it, records the views, and the station top (next
          step) instantiates them.

Tile boundary (every port registered on the tile side, no logic between a pin and its flop except the per-word
phase compare into s_cbad and the u_cp enable copies):
  bottom face : din (station input data, captured by id_p), control seam inputs (gr, rst_p, rst_e, go_*, ph4) and
                outputs (grc_o, v_*, q for the last slice) toward the station control strip
  top face    : dout (the NO kept output launch copies -> station out_* pins)
Seam IO is referenced to a neighbour virtual clock at the tile's planning insertion (smh sdc_block nbr_clk form, as the
closed smh tcc/bdc pieces).  60 / 25 ps uncertainty (AGENTS policy); nothing is false-pathed (the reset copies are timed).
Reuses tools/hbm_accel_smh_physical.py (config_mk, sdc_block, run_sh, RUN) unchanged.
"""
import argparse
import os
import re
import shutil
import subprocess
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hbm_accel_smh_physical as smh  # noqa: E402

STN = "physical/hbm_w2_rb_station_20261006"


def route_hold_margin(arg_ps):
    """ORFS HOLD_SLACK_MARGIN (ps): the loop's HM (ns) alone, else --hold-margin.  Not smh.loop_hold_margin (HM + 25):
    the SDC's 25 ps hold uncertainty is already in every slack, so adding it again demanded ~50 ps on every direct flop
    pair (stnh-*-62a6e35aa-hm0: 4,156 in-margin endpoints at real slack ~+17 ps -> RSZ-0060)."""
    hm = os.environ.get("HM", "").strip()
    try:
        return f"{float(hm) * 1000.0:g}" if hm else str(arg_ps)
    except ValueError:
        return str(arg_ps)

SLICE_RTL = [f"{STN}/bank_veto_static.sv", f"{STN}/slice_static.sv"]
MASTER = {"slice8": "ot_hbm_w2_stn_slice8", "slice5": "ot_hbm_w2_stn_slice5"}
PIECES = {"slice8": dict(NW=8, NB=512, BASE=0, QOUT=0), "slice5": dict(NW=5, NB=280, BASE=32, QOUT=1)}


def ports(piece, no):
    p = PIECES[piece]
    bottom_in = ["din*", "gr", "rst_p", "rst_e", "go_commit", "go_repair", "go_check", "go_sel", "ph4*"]
    bottom_out = ["grc_o*", "v_same", "v_bad", "v_cbad", "v_ce", "v_ue", "v_clean"] + (["q*"] if p["QOUT"] else [])
    top_out = ["dout*"]
    n_bottom = p["NB"] + 9 + 3 + p["NW"] + 6 + (p["NW"] * 64 if p["QOUT"] else 0)
    n_top = no * p["NB"]
    return bottom_in, bottom_out, top_out, n_bottom, n_top


def pins_tcl(piece, no):
    bi, bo, to, _, _ = ports(piece, no)
    return ("# HIER slice pin faces (tools/hbm_w2_station_hier_physical.py): data in + control seam on the bottom (toward\n"
            "# the station control strip and the station input pins), output launch copies on the top (station out_* pins)\n"
            f"set_io_pin_constraint -region bottom:* -pin_names {{clk {' '.join(bi + bo)}}}\n"
            f"set_io_pin_constraint -region top:* -pin_names {{{' '.join(to)}}}\n")


def abstract_tcls(work: Path, name):
    for c in ("ss", "ff", "tt"):
        C = c.upper()
        t = ["set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7",
             "read_lef $PLAT/lef/asap7_tech_1x_201209.lef", "read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef",
             f"foreach f [lsort [glob $PLAT/lib/NLDM/*_RVT_{C}_nldm_2*.lib*]] {{ if {{![string match *250407* $f]}} {{ read_liberty $f }} }}",
             "set base [lindex [glob /work/results/asap7/*/base] 0]",
             "read_db $base/6_final.odb", "read_spef $base/6_final.spef",
             "create_clock -name core_clk -period 833 [get_ports clk]", "set_propagated_clock [all_clocks]",
             f"write_timing_model -library_name {name}_{c} /work/views/{name}_{c}.lib"]
        if c == "ss":
            t.append(f"write_abstract_lef /work/views/{name}.lef")
        t.append("exit")
        (work / f"abstract_{c}.tcl").write_text("\n".join(t) + "\n")
    (work / "abstract.tcl").write_text("source /work/abstract_ss.tcl\n")


def cmd_tile(a):
    a.hold_margin = route_hold_margin(a.hold_margin)
    work = Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    p = PIECES[a.piece]
    die = [a.width, a.height]
    nick = f"stnh_{a.piece}_no{a.no}_{a.label}"
    name = MASTER[a.piece]
    extra = {"PLACE_DENSITY": a.pd, "HOLD_SLACK_MARGIN": a.hold_margin, "CTS_BUF_DISTANCE": 60,
             "PLACE_PINS_ARGS": "-min_distance 1 -min_distance_in_tracks", "IO_PLACER_H": "M4 M6", "IO_PLACER_V": "M5 M7",
             "MIN_ROUTING_LAYER": "M2", "MAX_ROUTING_LAYER": "M7"}
    cfg = smh.config_mk(name, nick, die, [], extra)
    lines = [l for l in cfg.splitlines() if not l.startswith("export VERILOG_FILES")]
    lines.insert(3, "export VERILOG_FILES = " + " ".join(f"/src/{s}" for s in SLICE_RTL))
    params = dict(p, NO=a.no)
    lines.append(f"export VERILOG_TOP_PARAMS = NO {a.no}")
    if a.pin_access:   # child_lint (f): edge pins covered by the tile's own metal on pin layer +-1 -> parent DRT-0073
        # pin-access plan (ds-coll bf0080873): adjacent-layer keepout over the outer pin column before GRT, removed after DRT
        lines += ["export PRE_GLOBAL_ROUTE_TCL = /src/physical/redesign_ds/coll_split/pin_access_pregrt.tcl",
                  "export POST_DETAIL_ROUTE_TCL = /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl",
                  f"export OT_PK_FRAC = {a.pin_access}",
                  # above-only (preamble PIN-ACCESS KEEPOUT, cons c95527ec0): keep only the layer ABOVE each edge pin clear
                  # (the parent's access side, what child_lint f checks); blocking below too starved dense faces (hfd_hc)
                  "export OT_PK_ABOVE_ONLY = 1"]
    if a.pdn == "m7":   # second line: the tile owns M7 power stripes (its pins); the station joins them from M8
        lines.append(f"export PDN_TCL = /src/{STN}/pdn_slice_m7.tcl")
    (work / "config.mk").write_text("\n".join(lines) + "\n")
    (work / "pins.tcl").write_text(pins_tcl(a.piece, a.no))
    bi, bo, to, nb, nt = ports(a.piece, a.no)
    # nbr_clk form (as the CLOSED smh tcc/bdc pieces): io_ref's -reference_pin delays crash ORFS port buffering
    # (rsz::Resizer::bufferInputs SIGSEGV at 3_3_place_gp, stnh-*-148f24a40 x4)
    sdc = smh.sdc_block(a.lat, nbr_in=" ".join(x for x in bi), lat_ff=a.lat_ff, period=a.period, skew=a.skew)
    # no false path: the reset copies are registered releases from the control core and stay timed
    sdc = sdc.replace("set_false_path -from [get_ports rst_n]",
                      "# (no false path: rst_p / rst_e are registered release copies from the station control, timed)")
    (work / "constraint.sdc").write_text(sdc)
    abstract_tcls(work, name)
    mx = " ".join(f"{k}={v}" for k, v in (x.split("=", 1) for x in (a.make_var or [])))
    smh.run_sh(work, a.label, a.src, a.need, a.cores, [], target=a.stop_after or "finish", admit=not a.no_admit,
               make_extra=(mx + " ") if mx else "")
    rs = (work / "run.sh").read_text().replace("for c in ss ff; do", "for c in ss ff tt; do")
    (work / "run.sh").write_text(rs)
    geo = dict(piece=a.piece, no=a.no, params=params, die=die, pins_bottom=nb, pins_top=nt,
               pin_density_per_um=dict(bottom=round(nb / a.width, 2), top=round(nt / a.width, 2)), pd=a.pd)
    (work / "geometry.json").write_text(json.dumps(geo, indent=1) + "\n")
    print(f"wrote {work}: {name} {params} die {die} pins bottom {nb} top {nt}")


TOP = "ot_hbm_native_frame_station_rb"
TOP_RTL = [f"{STN}/bank_veto_static.sv", "rtl/common/ot_fwd_link_stage.sv", f"{STN}/station_rb_static.sv",
           f"{STN}/slice_static.sv"]


def lef_size(src: Path, view: str):
    m = re.search(r"^\s*SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", (src / view / (Path(view).name + ".lef")).read_text(), re.M)
    return float(m.group(1)), float(m.group(2))


LAT_TCL = """set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $PLAT/lib/NLDM/*_RVT_{C}_nldm_2*.lib*]] {{ if {{![string match *250407* $f]}} {{ read_liberty $f }} }}
{mlibs}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/6_final.odb
read_sdc $base/6_final_route.sdc
read_spef $base/6_final.spef
set_propagated_clock [all_clocks]
report_clock_latency -clock clk_sm -digits 2
exit
"""


def cmd_signoff_sdc(a):
    """Station sign-off SDC for the HIER top (the flat signoff.py model): routed clk_sm latency at SS and FF with the
    slice views read, then make_sdc.py sign-off mode (POLICY-HOLD) -> <base>/6_signoff.sdc (+ insertion record)."""
    work, src = Path(a.work), Path(a.src)
    base = next((work / "results/asap7").glob("*/base"))
    if not (base / "6_final_route.sdc").exists():
        shutil.copy2(base / "6_final.sdc", base / "6_final_route.sdc")
    lat = {}
    for c in ("SS", "FF"):
        mlibs = "\n".join(f"read_liberty /src/{m}/{Path(m).name}_{c.lower()}.lib" for m in a.macro)
        (work / f"lat_{c}.tcl").write_text(LAT_TCL.format(C=c, mlibs=mlibs))
        p = subprocess.run(["docker", "run", "--rm", "-v", f"{src}:/src:ro", "-v", f"{work}:/work", "openroad/orfs:asap7lock",
                            "bash", "-lc", f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/lat_{c}.tcl"],
                           capture_output=True, text=True)
        (work / f"lat_{c}.log").write_text(p.stdout + p.stderr)
        rise = p.stdout.split("fall ->")[0]
        mn = re.search(r"^\s*([0-9.]+)\s+network latency", rise, re.M)
        mx = re.search(r"^\s+([0-9.]+)\s+network latency", rise.split(mn.group(0))[1], re.M) if mn else None
        if not (mn and mx):
            raise SystemExit(f"no clk_sm latency at {c}: see {work}/lat_{c}.log")
        lat[c] = [float(mn.group(1)), float(mx.group(1))]
    subprocess.run([sys.executable, str(src / STN / "make_sdc.py"), "--period-ps", "833.333", "--l-max", f"{lat['SS'][1]:.2f}",
                    "--l-min", f"{lat['SS'][0]:.2f}", "--l-ff-min", f"{lat['FF'][0]:.2f}", "--l-ff-max", f"{lat['FF'][1]:.2f}",
                    "--out", str(base / "6_signoff.sdc")], check=True)
    (work / "signoff_insertion.json").write_text(json.dumps(lat, indent=1) + "\n")
    print("6_signoff.sdc", lat)


def cmd_top(a):
    """HIER station top: 4 slice8 + 1 slice5 macros in one row (20 um edge / channels), the control core (phase FSM,
    S2, ACK / receipt / permission banks) in a strip below the row, station pins on the flat station's faces."""
    a.hold_margin = route_hold_margin(a.hold_margin)
    work, src = Path(a.out), Path(a.src)
    work.mkdir(parents=True, exist_ok=True)
    w8, h8 = lef_size(src, a.view8)
    w5, h5 = lef_size(src, a.view5)
    e, ch = a.edge, a.chan
    hrow = max(h8, h5)
    die = [round(2 * e + 4 * w8 + w5 + 4 * ch, 3), round(e + a.ctl_h + ch + hrow + e, 3)]
    y = e + a.ctl_h + ch
    xs = [e + k * (w8 + ch) for k in range(4)] + [e + 4 * (w8 + ch)]
    macros = [a.view8, a.view5]
    nick = f"stnh_top_no{a.no}_{a.label}"
    extra = {"PLACE_DENSITY": a.pd, "HOLD_SLACK_MARGIN": a.hold_margin, "MACRO_PLACE_HALO": f"{a.halo} {a.halo}",
             "PLACE_PINS_ARGS": "-min_distance 1 -min_distance_in_tracks", "IO_PLACER_H": "M4 M6", "IO_PLACER_V": "M5 M7",
             "MIN_ROUTING_LAYER": "M2", "MAX_ROUTING_LAYER": "M7"}
    cfg = smh.config_mk(TOP, nick, die, macros, extra)
    lines = [l for l in cfg.splitlines() if not l.startswith(("export VERILOG_FILES", "export SDC_FILE"))]
    lines.insert(3, "export VERILOG_FILES = " + " ".join(f"/src/{s}" for s in TOP_RTL))
    lines.append("export SDC_FILE = /work/station.sdc")
    # hard slice tiles expose M6 power pins: parent grid with M5/M6 stripes + M7 straps, slices strapped M6-M7
    lines.append(f"export PDN_TCL = /src/{STN}/" + ("pdn_hier_m8.tcl" if a.pdn == "m8" else "pdn_hier.tcl"))
    # forwarded clock (ot_fwd_clk_inv u_clk0..3 -> fclk_o): keep ORFS repair_clock_inverters from cloning the forwarding
    # inverters into the register tree (as run_owned.py's flat station).  Without it (stnh-top-*-60091125e-m8) the
    # forwarded generated clocks lose their master (STA-1062 forwarded3 at clkbuf_regs_0_clk_sm/Y), ~1,000 control
    # registers have no clock path (CTS-0179), latency balancing against the slice macros' insertion delay
    # (min/max_clock_tree_path in the tile ETMs) fails -> NO3 hold -200 ps at slice pins / RSZ-0060, NO2 setup -264.
    lines.append(f"export PRE_CTS_TCL = /src/{STN}/forwarded_subtree.tcl")
    # the hardened slices are liberty cells (no parameters): the station instantiates them without #(.NO())
    lines = [l + " -DOT_STN_HARD" if l.startswith("export VERILOG_DEFINES") else l for l in lines]
    lines.append(f"export VERILOG_TOP_PARAMS = ENABLE 1 NO {a.no} REL_REG 1 SAFE 1 GRANT_SEAT 1 HIER 1")
    lines.append(f"export GDS_ALLOW_EMPTY = (ot_hbm_w2_stn_slice8|ot_hbm_w2_stn_slice5)")
    (work / "config.mk").write_text("\n".join(lines) + "\n")
    tcl = ["# HIER station: slice macros in one row, data bit order left -> right (words 0..36)",
           "set ot_s8 {}; set ot_s5 {}",
           "foreach ot_inst [[ord::get_db_block] getInsts] {",
           "  set ot_m [[$ot_inst getMaster] getName]",
           "  if {$ot_m eq \"ot_hbm_w2_stn_slice8\"} { lappend ot_s8 [$ot_inst getName] }",
           "  if {$ot_m eq \"ot_hbm_w2_stn_slice5\"} { lappend ot_s5 [$ot_inst getName] }",
           "}",
           "set ot_s8 [lsort -dictionary $ot_s8]",
           "if {[llength $ot_s8] != 4 || [llength $ot_s5] != 1} { error \"HIER station: expected 4 slice8 + 1 slice5, got $ot_s8 / $ot_s5\" }"]
    for k in range(4):
        tcl.append(f"place_macro -macro_name [lindex $ot_s8 {k}] -location {{{xs[k]} {y}}} -orientation R0")
    tcl.append(f"place_macro -macro_name [lindex $ot_s5 0] -location {{{xs[4]} {y}}} -orientation R0")
    (work / "macros.tcl").write_text("\n".join(tcl) + "\n")
    (work / "pins.tcl").write_text(
        "# station pin faces (as the flat station: run_owned.py --pin-region)\n"
        "set_io_pin_constraint -region bottom:* -pin_names {clk_sm por_n release_held in_* release_*}\n"
        "set_io_pin_constraint -region top:* -pin_names {fclk_o out_* ACK_* fault drained paused}\n")
    # route SDC: the station contract at the route period (make_sdc route mode, as run_owned.py)
    subprocess.run([sys.executable, str(src / STN / "make_sdc.py"), "--period-ps", str(a.period), "--l-max", str(a.l_max),
                    "--l-min", str(a.l_min), "--l-ff-min", str(a.l_ff_min), "--l-ff-max", str(a.l_ff_max),
                    "--io-ref-period-ps", "833.333", "--route-ss-hold", "--out", str(work / "station.sdc")], check=True)
    (work / "abstract.tcl").write_text("exit\n")
    (work / "abstract_ss.tcl").write_text("exit\n")   # the station top exports no view
    margs = " ".join(f"--macro {m}" for m in macros)
    smh.run_sh(work, a.label, a.src, a.need, a.cores, macros, target="finish", admit=not a.no_admit, make_extra="")
    rs = (work / "run.sh").read_text()
    rs = rs.replace('for c in ss ff; do', 'for c in ss; do')
    # station sign-off model: measured insertion -> make_sdc sign-off (POLICY-HOLD) as 6_signoff.sdc, then corner STA
    old = "  sed -E 's/-period [0-9.]+/-period 833.0000/g' $B/6_final.sdc > $B/6_signoff.sdc\n"
    assert rs.count(old) == 1
    rs = rs.replace(old, f"  python3 $S/tools/hbm_w2_station_hier_physical.py signoff-sdc --work $W --src $S {margs} > $W/signoff_sdc.log 2>&1\n"
                         "  echo \"signoff_sdc_rc=$?\" >> $W/status\n")
    rs = rs.replace("[ -f $B/6_final_route.sdc ] || cp $B/6_final.sdc $B/6_final_route.sdc; ", "")
    (work / "run.sh").write_text(rs)
    geo = dict(no=a.no, die=die, slice8=[w8, h8], slice5=[w5, h5], row_y=y, xs=xs, ctl_h=a.ctl_h, chan=ch, edge=e,
               views=macros, pd=a.pd)
    (work / "geometry.json").write_text(json.dumps(geo, indent=1) + "\n")
    print(f"wrote {work}: {TOP} HIER NO={a.no} die {die} slices at y {y} x {xs}")


def cmd_hub(a):
    """Station hub element (owner TWO-LEVEL HIERARCHY 10-11 ~21:00): the station glue extracted by
    tools/hbm_w2_station_hub_extract.py (same RTL as the bit-exact HIER station, slices everted to seam ports), hardened as
    its own small tile that the die places next to its 5 slice tiles.  Faces: slice seam ports (sl0..sl4, data-bit order
    left -> right) on the top face toward the slice row; station control pins (ACK / release / in_v / out_v / status,
    clk_sm, por_n) on the bottom.  Every port timed against the die-level neighbour clock (nbr_clk, as the slice tiles);
    PG = own full-length M7 stripes (pdn_slice_m7.tcl, die straps M8)."""
    a.hold_margin = route_hold_margin(a.hold_margin)
    work = Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    name = f"ot_hbm_w2_stn_hub_no{a.no}"
    die = [a.width, a.height]
    nick = f"stnh_hub_no{a.no}_{a.label}"
    extra = {"PLACE_DENSITY": a.pd, "HOLD_SLACK_MARGIN": a.hold_margin, "CTS_BUF_DISTANCE": 60,
             "PLACE_PINS_ARGS": "-min_distance 1 -min_distance_in_tracks", "IO_PLACER_H": "M4 M6", "IO_PLACER_V": "M5 M7",
             "MIN_ROUTING_LAYER": "M2", "MAX_ROUTING_LAYER": "M7"}
    cfg = smh.config_mk(name, nick, die, [], extra)
    lines = [l for l in cfg.splitlines() if not l.startswith("export VERILOG_FILES")]
    lines.insert(3, f"export VERILOG_FILES = /src/{STN}/hub/{name}.v")
    lines.append(f"export PDN_TCL = /src/{STN}/pdn_slice_m7.tcl")
    (work / "config.mk").write_text("\n".join(lines) + "\n")
    seam = " ".join(f"sl{k}_*" for k in range(5))
    (work / "pins.tcl").write_text(
        "# hub faces: slice seams on top (toward the slice row), station control pins on the bottom\n"
        f"set_io_pin_constraint -region top:* -pin_names {{{seam}}}\n"
        "set_io_pin_constraint -region bottom:* -pin_names {clk_sm por_n release_held in_v in_r out_v* out_r* ACK_* "
        "release_v release_r release_owner* release_frame* fclk_o drained paused fault}\n")
    v = (ROOT / STN / "hub" / f"{name}.v").read_text().split(f"module {name}(")[1].split("endmodule")[0]
    ins = sorted(set(re.findall(r"^  input\s+(?:\[\d+:\d+\]\s+)?(\S+)\s*;", v, re.M)) - {"clk_sm", "por_n"})
    sdc = smh.sdc_block(a.lat, nbr_in=" ".join(f"{x}*" if x.endswith(("owner", "frame", "_q", "_o", "_v", "_r")) else x for x in ins),
                        lat_ff=a.lat_ff, period=a.period, skew=a.skew)
    sdc = sdc.replace("[get_ports clk]", "[get_ports clk_sm]").replace("set_false_path -from [get_ports rst_n]",
                      "set_false_path -from [get_ports por_n]   ;# async power-on reset, synchronised in the hub")
    (work / "constraint.sdc").write_text(sdc)
    abstract_tcls(work, name)
    for c in ("ss", "ff", "tt"):
        f = work / f"abstract_{c}.tcl"
        f.write_text(f.read_text().replace("[get_ports clk]", "[get_ports clk_sm]"))
    smh.run_sh(work, a.label, a.src, a.need, a.cores, [], target="finish", admit=not a.no_admit, make_extra="")
    rs = (work / "run.sh").read_text().replace("for c in ss ff; do", "for c in ss ff tt; do")
    (work / "run.sh").write_text(rs)
    geo = dict(hub=name, no=a.no, die=die, pd=a.pd, seam_ports_top=seam, inputs=len(ins))
    (work / "geometry.json").write_text(json.dumps(geo, indent=1) + "\n")
    print(f"wrote {work}: {name} die {die}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("signoff-sdc")
    s.add_argument("--work", required=True)
    s.add_argument("--src", required=True)
    s.add_argument("--macro", action="append", default=[])
    tp = sp.add_parser("top")
    tp.add_argument("--no", type=int, choices=(2, 3), required=True)
    tp.add_argument("--view8", required=True, help="src-relative view dir .../ot_hbm_w2_stn_slice8")
    tp.add_argument("--view5", required=True, help="src-relative view dir .../ot_hbm_w2_stn_slice5")
    tp.add_argument("--ctl-h", type=float, default=60)
    tp.add_argument("--chan", type=float, default=20)
    tp.add_argument("--edge", type=float, default=20)
    tp.add_argument("--halo", type=float, default=10)
    tp.add_argument("--pd", type=float, default=0.55)
    tp.add_argument("--period", type=float, default=770)
    tp.add_argument("--l-max", type=float, default=510.0)
    tp.add_argument("--l-min", type=float, default=440.0)
    tp.add_argument("--l-ff-min", type=float, default=280.0)
    tp.add_argument("--l-ff-max", type=float, default=330.0)
    tp.add_argument("--hold-margin", default="10")
    tp.add_argument("--pdn", choices=("m7", "m8"), default="m7", help="m7: slices with M6 pins (default grid); m8: slices built --pdn m7")
    tp.add_argument("--src", required=True)
    tp.add_argument("--label", required=True)
    tp.add_argument("--out", required=True)
    tp.add_argument("--need", default="40")
    tp.add_argument("--cores", default="16")
    tp.add_argument("--no-admit", action="store_true")
    t = sp.add_parser("tile")
    h = sp.add_parser("hub")
    h.add_argument("--no", type=int, choices=(2, 3), required=True)
    h.add_argument("--width", type=float, required=True)
    h.add_argument("--height", type=float, required=True)
    h.add_argument("--pd", type=float, default=0.55)
    h.add_argument("--period", type=float, default=770)
    h.add_argument("--skew", type=float, default=60)
    h.add_argument("--lat", type=float, default=250)
    h.add_argument("--lat-ff", type=float, default=150)
    h.add_argument("--hold-margin", default="10")
    h.add_argument("--src", required=True)
    h.add_argument("--label", required=True)
    h.add_argument("--out", required=True)
    h.add_argument("--need", default="32")
    h.add_argument("--cores", default="16")
    h.add_argument("--no-admit", action="store_true")
    t.add_argument("--piece", choices=sorted(PIECES), required=True)
    t.add_argument("--no", type=int, choices=(2, 3), required=True)
    t.add_argument("--width", type=float, required=True)
    t.add_argument("--height", type=float, required=True)
    t.add_argument("--pd", type=float, default=0.55)
    t.add_argument("--period", type=float, default=770)
    t.add_argument("--skew", type=float, default=60)
    t.add_argument("--lat", type=float, default=250)
    t.add_argument("--lat-ff", type=float, default=150)
    t.add_argument("--hold-margin", default="10")
    t.add_argument("--make-var", action="append")
    t.add_argument("--pdn", choices=("default", "m7"), default="default")
    t.add_argument("--pin-access", default=None, help="OT_PK_FRAC: pin-access keepout hook (child_lint f)")
    t.add_argument("--stop-after", default=None)
    t.add_argument("--src", required=True)
    t.add_argument("--label", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--need", default="32")
    t.add_argument("--cores", default="16")
    t.add_argument("--no-admit", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "tile":
        cmd_tile(a)
    elif a.cmd == "hub":
        cmd_hub(a)
    elif a.cmd == "top":
        cmd_top(a)
    elif a.cmd == "signoff-sdc":
        cmd_signoff_sdc(a)


if __name__ == "__main__":
    main()

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
Seam IO is referenced to the tile's own register clock pin (smh sdc_block io_ref=True): the neighbour flop sits on the
same element clock tree.  60 / 25 ps uncertainty (AGENTS policy); nothing is false-pathed (the reset copies are timed).
Reuses tools/hbm_accel_smh_physical.py (config_mk, sdc_block, run_sh, RUN) unchanged.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hbm_accel_smh_physical as smh  # noqa: E402

STN = "physical/hbm_w2_rb_station_20261006"
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
            t.append(f"write_abstract_lef -bloat_occupied_layers /work/views/{name}.lef")
        t.append("exit")
        (work / f"abstract_{c}.tcl").write_text("\n".join(t) + "\n")
    (work / "abstract.tcl").write_text("source /work/abstract_ss.tcl\n")


def cmd_tile(a):
    a.hold_margin = smh.loop_hold_margin(a.hold_margin)
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
    (work / "config.mk").write_text("\n".join(lines) + "\n")
    (work / "pins.tcl").write_text(pins_tcl(a.piece, a.no))
    bi, bo, to, nb, nt = ports(a.piece, a.no)
    sdc = smh.sdc_block(a.lat, nbr_in=" ".join(x for x in bi), period=a.period, skew=a.skew, io_ref=True)
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("tile")
    t.add_argument("--piece", choices=sorted(PIECES), required=True)
    t.add_argument("--no", type=int, choices=(2, 3), required=True)
    t.add_argument("--width", type=float, required=True)
    t.add_argument("--height", type=float, required=True)
    t.add_argument("--pd", type=float, default=0.55)
    t.add_argument("--period", type=float, default=770)
    t.add_argument("--skew", type=float, default=60)
    t.add_argument("--lat", type=float, default=200)
    t.add_argument("--hold-margin", default="10")
    t.add_argument("--make-var", action="append")
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


if __name__ == "__main__":
    main()

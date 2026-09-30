#!/usr/bin/env python3
"""W18: hierarchical power grid and IR drop of the V4.1 ROM layer die.

A flat ASAP7 PDN of the 815 mm^2 die ran out of memory past 120 GB (W1).  The grid is therefore built and
analysed in three levels, each one an OpenROAD run that sees the level below only as an abstract:

  element  the hardened ROM-array pair (W10 p5, routed): its own M1/M2 rails and M5/M6 grid, sources at
           its M6 pins (tools/w18 pair_ir run on the routed odb).
  cluster  one column segment of ``rows`` pairs (tools/w18/die_floorplan.py): the pairs as macros (exact,
           non-bloated abstract), M1/M2 rails in the pin channels, M7 straps dropped on the pairs' M6 pins,
           and M8 straps that are the cluster's power pins.  Sources: the M8 straps (STRAPS).
  die      every cluster, hub partition, HBM service band, PHY and link module as an abstract whose power
           pins are M8 straps; the die grid is M9 straps and the micro-bump array.  Sources: the bumps.

The cluster's M8 pins carry the ALWAYS-ON rail; the cluster's internal grid is the switched rail behind the
power-switch ring at its boundary (stage power gating, W14 model; W10 reserved the switch area).  PSM has no
switch model, so the ring's drop is added analytically from the switch count and the on-resistance, and the
three levels' worst drops are summed (a conservative stack: the worst nodes need not coincide).

    python3 tools/w18/die_pdn.py cluster --floorplan F --pair-lef pair_exact.lef --run-dir D --pair-w 0.239
    python3 tools/w18/die_pdn.py die --floorplan F --pack P --run-dir D --pair-w 0.239 --hub-w-mm2 3.5
    python3 tools/w18/die_pdn.py record --run-dir D --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/w18"))
import die_floorplan as DF  # noqa: E402

IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
VDD_V = 0.7                       # ASAP7 TT nominal

# Grid choices (widths from the ASAP7 LEF width tables; fractions as W1's reservation: 25% of M8/M9).
M7 = dict(width=0.544, pitch=10.8, spacing=4.856)          # 10% of M7 (cluster, over the pairs)
M8 = dict(width=2.0, pitch=16.0, spacing=6.0)              # 25% of M8: cluster power pins
M9 = dict(width=2.0, pitch=16.0, spacing=6.0)              # 25% of M9: die straps
BUMP = dict(pitch=40.0, size=20.0)                          # micro-bump array (ASSUMED 40 um, 2.5D class)

# Power-switch ring (header PMOS).  ASAP7 has no characterised switch cell, so a ring cell is taken as a
# 4-finger-per-1x header built like INVx4's pull-up: R_on(one cell) ~= inv4 pull-up drive resistance
# (asap7 calibration inv4_r_kohm = 0.9125 kohm at TT) -- a switching-average resistance, i.e. conservative
# against a linear-region header.  ASSUMED.
SWITCH_CELL = dict(r_on_ohm=912.5, w_um=0.432, h_um=0.27, basis=(
    "ASSUMED: one header cell = the pull-up of an ASAP7 INVx4 (tools/mem_compiler asap7.calibration tt "
    "inv4_r_kohm 0.9125 kohm), 0.432 x 0.27 um; no ASAP7 power-switch cell is characterised"))


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def block_lef(name: str, w: float, h: float, note: str, pin_layer: str = "M8", obs_top: int = 7,
              grid: dict = M8) -> str:
    """A power abstract: VDD/VSS as full-width horizontal straps on ``pin_layer`` (same pattern as the parent
    expects), OBS M1..M<obs_top> over the whole block."""
    L = [f"# W18 power abstract: {note}", "VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;',
         f"MACRO {name}", "  CLASS BLOCK ;", f"  FOREIGN {name} 0 0 ;", "  SYMMETRY X Y ;",
         f"  SIZE {w:.3f} BY {h:.3f} ;"]
    ys = {"VDD": [], "VSS": []}
    y = grid["pitch"] / 4
    while y + grid["width"] < h - 0.5:
        ys["VDD"].append(y)
        y2 = y + grid["pitch"] / 2
        if y2 + grid["width"] < h - 0.5:
            ys["VSS"].append(y2)
        y += grid["pitch"]
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", f"      LAYER {pin_layer} ;"]
        L += [f"        RECT 0.500 {yy:.3f} {w - 0.5:.3f} {yy + grid['width']:.3f} ;" for yy in ys[net]]
        L += ["    END", f"  END {net}"]
    L += ["  OBS"] + [f"    LAYER M{i} ;\n      RECT 0 0 {w:.3f} {h:.3f} ;" for i in range(1, obs_top + 1)]
    L += ["  END", f"END {name}", "END LIBRARY", ""]
    return "\n".join(L)


PAIR_M6 = dict(width=0.288, pitch=5.4, spacing=2.412)     # W10 p5 pair: VDD/VSS M6 straps, 5.4 um per net


def tiles(x: float, y: float, w: float, h: float, tmax: float) -> list[tuple[float, float, float, float]]:
    """Split a block into current-map tiles (PSM draws an instance's current at its centre, on the grid's
    lowest layer, so a large block must be a map of small loads, not one point load)."""
    nx, ny = max(1, math.ceil(w / tmax - 1e-9)), max(1, math.ceil(h / tmax - 1e-9))
    tw, th = round(w / nx, 3), round(h / ny, 3)
    return [(round(x + i * tw, 3), round(y + j * th, 3), tw, th) for j in range(ny) for i in range(nx)]


def load_lef(name: str, w: float, h: float, note: str) -> str:
    """A die-level current-map tile: the block's own grid is M7 and below (OBS M2-M7), the die grid (M8/M9)
    runs over it; VDD/VSS are token M1 pins so the instance is on the nets (PSM draws its current at the
    nearest node of the die grid's lowest layer)."""
    return "\n".join([f"# W18 die-level load tile: {note}", "VERSION 5.8 ;", 'BUSBITCHARS "[]" ;',
                      'DIVIDERCHAR "/" ;', f"MACRO {name}", "  CLASS BLOCK ;", f"  FOREIGN {name} 0 0 ;",
                      "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;",
                      "  PIN VDD", "    DIRECTION INOUT ;", "    USE POWER ;", "    PORT", "      LAYER M1 ;",
                      "        RECT 0.100 0.100 0.200 0.200 ;", "    END", "  END VDD",
                      "  PIN VSS", "    DIRECTION INOUT ;", "    USE GROUND ;", "    PORT", "      LAYER M1 ;",
                      "        RECT 0.300 0.100 0.400 0.200 ;", "    END", "  END VSS",
                      "  OBS"] + [f"    LAYER M{i} ;\n      RECT 0 0 {w:.3f} {h:.3f} ;" for i in range(2, 8)]
                     + ["  END", f"END {name}", "END LIBRARY", ""])


def def_file(design: str, w: float, h: float, comps: list[tuple[str, str, float, float, str]]) -> str:
    d = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', f"DESIGN {design} ;",
         "UNITS DISTANCE MICRONS 1000 ;", f"DIEAREA ( 0 0 ) ( {round(w * 1000)} {round(h * 1000)} ) ;",
         f"COMPONENTS {len(comps)} ;"]
    orient = {"R0": "N", "MX": "FS", "MY": "FN", "R180": "S"}
    d += [f"- {n} {m} + FIXED ( {round(x * 1000)} {round(y * 1000)} ) {orient[o]} ;" for n, m, x, y, o in comps]
    d += ["END COMPONENTS", "END DESIGN", ""]
    return "\n".join(d)


PSM_TCL = r"""
proc ot_ir {net src} {
  set_pdnsim_net_voltage -net $net -voltage [expr {$net eq "VDD" ? __VDD__ : 0.0}]
  if {[catch {analyze_power_grid -net $net -source_type $src -voltage_file /run/ir_$net.rpt -error_file /run/ir_err_$net.rpt} err]} {
    puts "OT_IR net=$net status=FAIL err=$err"
  } else { puts "OT_IR net=$net status=PASS" }
}
foreach net {VDD VSS} {
  if {[catch {check_power_grid -net $net -error_file /run/pg_err_$net.rpt} err]} { puts "OT_PSM net=$net status=FAIL err=$err" } else { puts "OT_PSM net=$net status=PASS" }
}
"""


def cluster_case(a) -> dict:
    fp = json.loads(a.floorplan.read_text())
    pair = DF.lef_macro(a.pair_lef)
    rule = fp["cluster_rule"]
    rows = a.rows or rule["rows"]
    rp, cw = rule["row_pitch_um"], fp["clusters"][0]["w"]
    ch = rp - pair["h"]
    w, h = cw, round(rows * rp, 3)
    run = a.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=True)
    nt = a.tiles_per_pair
    tw = round(pair["w"] / nt, 3)
    tname = f"w18p_pairtile_{nt}"
    (run / "tile.lef").write_text(block_lef(tname, tw, pair["h"], f"1/{nt} of the W10 p5 pair: its M6 VDD/VSS "
                                            "straps (5.4 um per net), OBS M1-M5; M7 open for the cluster straps "
                                            "(the pair must be re-hardened with M7 power pins, W18 finding)",
                                            pin_layer="M6", obs_top=5, grid=PAIR_M6))
    comps = [(f"pair_{r}_t{i}", tname, round(i * tw, 3), round(r * rp + ch, 3), "R0")
             for r in range(rows) for i in range(nt)]
    (run / "top.def").write_text(def_file("w18_cluster", w, h, comps))
    power = {c[0]: a.pair_w / nt for c in comps}
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /run/tile.lef
read_def /run/top.def
initialize_floorplan -die_area {{0 0 {w:.3f} {h:.3f}}} -core_area {{0 0 {w:.3f} {h:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set block [ord::get_db_block]
foreach r [$block getRows] {{ odb::dbRow_destroy $r }}
puts "OT_STAT insts=[llength [$block getInsts]]"
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
set_voltage_domain -name {{CORE}} -power {{VDD}} -ground {{VSS}}
define_pdn_grid -name {{cl}} -voltage_domains {{CORE}} -pins {{M8}}
add_pdn_stripe -grid {{cl}} -layer {{M7}} -width {{{M7['width']}}} -spacing {{{M7['spacing']}}} -pitch {{{M7['pitch']}}} -offset {{2.0}}
add_pdn_stripe -grid {{cl}} -layer {{M8}} -width {{{M8['width']}}} -spacing {{{M8['spacing']}}} -pitch {{{M8['pitch']}}} -offset {{{M8['pitch'] / 4 - M8['width'] / 2 + 1.0}}}
add_pdn_connect -grid {{cl}} -layers {{M7 M8}}
define_pdn_grid -macro -cells {{{tname}}} -halo "0 0 0 0" -voltage_domains {{CORE}} -name {{PairGrid}}
add_pdn_connect -grid {{PairGrid}} -layers {{M6 M7}}
if {{[catch {{pdngen}} err]}} {{ puts "OT_PDN status=FAIL err=$err" }} else {{
  set nsw 0; foreach net [$block getNets] {{ foreach sw [$net getSWires] {{ incr nsw [llength [$sw getWires]] }} }}
  puts "OT_PDN status=PASS special_wire_shapes=$nsw" }}
puts "OT_TIME pdn_s=[expr {{[clock seconds]-$t0}}]"
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
{chr(10).join(f'set_pdnsim_inst_power -inst {n} -power {p:.6f}' for n, p in power.items())}
""" + PSM_TCL.replace("__VDD__", str(VDD_V)) + """
ot_ir VDD STRAPS
ot_ir VSS STRAPS
puts "OT_TIME psm_s=[expr {[clock seconds]-$t0}]"
exit
"""
    (run / "run.tcl").write_text(tcl)
    meta = dict(level="cluster", rows=rows, size_um=[w, h], pair=pair, pair_w=a.pair_w, tiles_per_pair=nt,
                cluster_w=round(rows * a.pair_w, 4), grid=dict(M7=M7, M8=M8, pair_M6=PAIR_M6),
                sources="STRAPS (M8 cluster pins)", loads="pair current-map tiles, current at tile centre on M7",
                pair_lef_sha256=sha(a.pair_lef), floorplan_sha256=sha(a.floorplan))
    (run / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def die_case(a) -> dict:
    fp = json.loads(a.floorplan.read_text())
    pk = json.loads(a.pack.read_text())
    W, H = fp["die"]["w_um"], fp["die"]["h_um"]
    run = a.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=True)
    lefs, comps, power, kinds = {}, [], {}, {}
    pair_mm2 = fp["pair"]["w"] * fp["pair"]["h"] / 1e6

    def blk(kind, w, h, note):
        nm = f"w18p_{kind}_{round(w * 1000)}x{round(h * 1000)}"
        if nm not in lefs:
            lefs[nm] = load_lef(nm, w, h, note)
        return nm

    win = a.window                     # die-level window (um): the bump array makes IR local
    wx0, wy0 = (win[0], win[1]) if win else (0.0, 0.0)

    def add(name, kind, x, y, w, h, watts, note, tmax):
        ts = tiles(x, y, w, h, tmax)
        for i, (tx, ty, tw, th) in enumerate(ts):
            pw_ = watts / len(ts)
            if win:
                cx0, cy0 = max(tx, win[0]), max(ty, win[1])
                cx1, cy1 = min(tx + tw, win[2]), min(ty + th, win[3])
                if cx1 - cx0 < 1.0 or cy1 - cy0 < 1.0:
                    continue
                pw_ *= (cx1 - cx0) * (cy1 - cy0) / (tw * th)
                tx, ty, tw, th = round(cx0 - wx0, 3), round(cy0 - wy0, 3), round(cx1 - cx0, 3), round(cy1 - cy0, 3)
            n = f"{name}_t{i}"
            comps.append((n, blk(kind, tw, th, note), tx, ty, "R0"))
            power[n] = pw_
            kinds[n] = kind

    for c in fp["clusters"]:
        rp = fp["cluster_rule"]["row_pitch_um"]
        for r in range(c["rows"]):
            watts = (a.duty * a.pair_w + (1 - a.duty) * a.pair_idle_w) if r < c["used_rows"] else a.pair_idle_w
            add(f"{c['name']}_r{r}", "cluster", c["x"], round(c["y"] + r * rp, 3), c["w"], rp, watts,
                "ROM-array cluster pair row (always-on M8 pins, switched grid inside)", 130.0)
    for nm, r in fp["hub"]["parts"].items():
        add(nm.lower(), "hub", r["x"], r["y"], r["w"], r["h"], r["w"] * r["h"] / 1e6 * a.hub_w_mm2,
            f"PLACEHOLDER {nm}: W11 hardened hub element pending", 500.0)
    for nm, r in fp["service"].items():
        add(nm.lower(), "service", r["x"], r["y"], r["w"], r["h"], r["w"] * r["h"] / 1e6 * a.hub_w_mm2,
            f"PLACEHOLDER {nm}: HBM service band (K-arb, KV streamer, key readers)", 500.0)
    for nm, master, x, y, o, grp in pk["instances"]:
        if grp not in ("HBM_PHY", "SERDES", "UCIE"):
            continue
        tl = Path(DF.PK.MACRO_DIR / master / f"{master}.lef")
        if tl.exists():
            mm = DF.lef_macro(tl)
            w, h = mm["w"], mm["h"]
        else:
            w, h = {"SERDES": (1000.08, 401.76), "UCIE": (1043.28, 388.8)}[grp]
        add(nm, grp.lower(), x, y, w, h, {"HBM_PHY": a.phy_w, "SERDES": a.serdes_w, "UCIE": a.ucie_w}[grp],
            f"{grp} power abstract ({master}); internal grid checked separately", 500.0)
    if win:
        W, H = round(win[2] - win[0], 3), round(win[3] - win[1], 3)
    for nm, t in lefs.items():
        (run / f"{nm}.lef").write_text(t)
    (run / "top.def").write_text(def_file("w18_die", W, H, comps))
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{chr(10).join(f'read_lef /run/{n}.lef' for n in lefs)}
read_def /run/top.def
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set block [ord::get_db_block]
foreach r [$block getRows] {{ odb::dbRow_destroy $r }}
puts "OT_STAT insts=[llength [$block getInsts]]"
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
set_voltage_domain -name {{CORE}} -power {{VDD}} -ground {{VSS}}
define_pdn_grid -name {{die}} -voltage_domains {{CORE}} -pins {{M9}}
add_pdn_stripe -grid {{die}} -layer {{M8}} -width {{{M8['width']}}} -spacing {{{M8['spacing']}}} -pitch {{{M8['pitch']}}} -offset {{{M8['pitch'] / 4 - M8['width'] / 2 + 1.0}}}
add_pdn_stripe -grid {{die}} -layer {{M9}} -width {{{M9['width']}}} -spacing {{{M9['spacing']}}} -pitch {{{M9['pitch']}}} -offset {{2.0}}
add_pdn_connect -grid {{die}} -layers {{M8 M9}}
if {{[catch {{pdngen}} err]}} {{ puts "OT_PDN status=FAIL err=$err" }} else {{
  set nsw 0; foreach net [$block getNets] {{ foreach sw [$net getSWires] {{ incr nsw [llength [$sw getWires]] }} }}
  puts "OT_PDN status=PASS special_wire_shapes=$nsw" }}
puts "OT_TIME pdn_s=[expr {{[clock seconds]-$t0}}]"
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
set_pdnsim_source_settings -bump_dx {int(BUMP['pitch'])} -bump_dy {int(BUMP['pitch'])} -bump_size {int(BUMP['size'])}
{chr(10).join(f'set_pdnsim_inst_power -inst {n} -power {p:.6f}' for n, p in power.items())}
""" + PSM_TCL.replace("__VDD__", str(VDD_V)) + """
ot_ir VDD BUMPS
ot_ir VSS BUMPS
puts "OT_TIME psm_s=[expr {[clock seconds]-$t0}]"
exit
"""
    (run / "run.tcl").write_text(tcl)
    tot = {}
    (run / "power_map.json").write_text(json.dumps({n: [kinds[n], round(p, 6)] for n, p in power.items()}))
    for n, p in power.items():
        tot[kinds[n]] = tot.get(kinds[n], 0.0) + p
    meta = dict(level="die", window_um=win, size_um=[W, H], grid_note=("die grid = M8 + M9 mesh over every block (the blocks' "
                "own grids are M7 and below: the cluster level analyses M7 from ideal M8 pins, so M8 is counted at "
                "both levels -- conservative); loads = current-map tiles"), instances=len(comps), abstracts=len(lefs),
                power_w_by_kind={k: round(v, 3) for k, v in tot.items()}, power_w_total=round(sum(power.values()), 3),
                pair_w=a.pair_w, duty=a.duty, pair_idle_w=a.pair_idle_w, hub_w_per_mm2=a.hub_w_mm2, phy_w=a.phy_w, serdes_w=a.serdes_w, ucie_w=a.ucie_w,
                grid=dict(M9=M9, block_pins=M8), bumps=BUMP, sources="BUMPS on M9 (micro-bump array)",
                floorplan_sha256=sha(a.floorplan), pack_sha256=sha(a.pack))
    (run / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def run_docker(run: Path, mem_gb: int, tag: str, host: str = "") -> dict:
    """Run run.tcl in the ORFS image, locally or on ``host`` (the run dir is mirrored there and back)."""
    cmd = ["docker", "run", "--rm", f"--memory={mem_gb}g", "--name", f"ot_w18_{tag}_{os.getpid()}",
           "-v", f"{run}:/run", IMAGE, "bash", "-c",
           f"'/usr/bin/time -v {OPENROAD} -exit -no_init /run/run.tcl > /run/openroad.log 2>&1; echo rc=$?'"]
    t = time.time()
    if host:
        subprocess.run(["ssh", host, f"mkdir -p {run.parent}"], check=True)
        subprocess.run(["rsync", "-a", "--delete", f"{run}/", f"{host}:{run}/"], check=True)
        r = subprocess.run(["ssh", host, " ".join(cmd)], capture_output=True, text=True)
        subprocess.run(["rsync", "-a", f"{host}:{run}/", f"{run}/"], check=True)
        img = subprocess.run(["ssh", host, f"docker image inspect {IMAGE} --format '{{{{.Id}}}}'"],
                             capture_output=True, text=True).stdout.strip()
    else:
        r = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        img = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                             capture_output=True, text=True).stdout.strip()
    return dict(wall_s=round(time.time() - t, 1), docker_rc=r.returncode, stdout=r.stdout[-200:],
                host=host or "local", image_id=img)


def parse(run: Path) -> dict:
    log = (run / "openroad.log").read_text() if (run / "openroad.log").exists() else ""
    tags = {}
    for line in log.splitlines():
        if line.startswith("OT_"):
            t, _, rest = line.partition(" ")
            tags.setdefault(t, []).append(rest)
    ir = {}
    cur = None
    for line in log.splitlines():
        m = re.search(r"Net\s*:\s*(\S+)", line)
        if m:
            cur = m.group(1)
            ir[cur] = {}
        for key in ("Supply voltage", "Worstcase voltage", "Average voltage", "Average IR drop",
                    "Worstcase IR drop", "Percentage drop"):
            if cur and line.strip().startswith(key):
                v = re.search(r"([-0-9.eE+]+)\s*(mV|V|%|uV)?\s*$", line.strip())
                if v:
                    val = float(v.group(1))
                    unit = v.group(2) or ""
                    ir[cur][key] = val * (1e-3 if unit == "mV" else 1e-6 if unit == "uV" else 1.0) \
                        if unit != "%" else val
    peak = next((l.split(":")[1].strip() for l in log.splitlines() if "Maximum resident set size" in l), None)
    errs = [l for l in log.splitlines() if l.startswith("[ERROR")][:20]
    return dict(tags=tags, ir=ir, peak_rss_kb=peak, errors=errs)


def switch_ring(cluster_w: float, perimeter_um: float, band_um: float, vdd: float = VDD_V) -> dict:
    """Header ring on the cluster boundary: cells fill a band of ``band_um`` around the perimeter."""
    n = int(perimeter_um // SWITCH_CELL["w_um"]) * int(band_um // SWITCH_CELL["h_um"])
    r = SWITCH_CELL["r_on_ohm"] / n
    i = cluster_w / vdd
    return dict(cells=n, band_um=band_um, r_on_total_mohm=round(r * 1e3, 4), current_a=round(i, 3),
                drop_mv=round(i * r * 1e3, 3), area_um2=round(perimeter_um * band_um, 1), basis=SWITCH_CELL["basis"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    for m in ("cluster", "die"):
        p = sub.add_parser(m)
        p.add_argument("--floorplan", type=Path, required=True)
        p.add_argument("--run-dir", type=Path, required=True)
        p.add_argument("--pair-w", type=float, default=0.239, help="W per pair (p5 ORFS default activity)")
        p.add_argument("--memory-gb", type=int, default=60)
        p.add_argument("--no-run", action="store_true")
        p.add_argument("--host", default="", help="run on this ssh host (run dir mirrored)")
        if m == "cluster":
            p.add_argument("--pair-lef", type=Path, required=True)
            p.add_argument("--rows", type=int, default=0)
            p.add_argument("--tiles-per-pair", type=int, default=4)
        else:
            p.add_argument("--pack", type=Path, required=True)
            p.add_argument("--hub-w-mm2", type=float, default=3.53, help="hub/service W/mm2 (default: pair density)")
            p.add_argument("--duty", type=float, default=1.0, help="ROM-field busy fraction (saturation map)")
            p.add_argument("--window", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"),
                           help="analyse this window of the die (um); default the whole die")
            p.add_argument("--pair-idle-w", type=float, default=0.00022, help="idle pair W (0.00022 ideal ICG)")
            p.add_argument("--phy-w", type=float, default=7.7, help="on-die HBM share per stack at full rate")
            p.add_argument("--serdes-w", type=float, default=0.5)
            p.add_argument("--ucie-w", type=float, default=0.5)
    a = ap.parse_args(argv)
    meta = cluster_case(a) if a.mode == "cluster" else die_case(a)
    if a.no_run:
        print(json.dumps(meta, indent=1)[:2000])
        return
    r = run_docker(a.run_dir.resolve(), a.memory_gb, a.mode, a.host)
    res = parse(a.run_dir.resolve())
    out = dict(schema="opentallas.v41.w18_pdn.v1", meta=meta, run=r, **res,
               tool_sha256=sha(Path(__file__)), image=IMAGE)
    if a.mode == "cluster":
        s = meta["size_um"]
        out["switch_ring"] = switch_ring(meta["cluster_w"], 2 * (s[0] + s[1]), 2.16)
    (a.run_dir / "result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("ir", "peak_rss_kb", "errors")} | {"tags": out["tags"]}, indent=1)[:3000])


if __name__ == "__main__":
    main()

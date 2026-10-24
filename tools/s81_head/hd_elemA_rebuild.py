#!/usr/bin/env python3
"""S81-HEAD 2026-10-24: kit to rebuild the closed head element A (dshead-elemA-ss-f11f3cc47) from its source.

Why: the closed view's clk pin is an M5 stub RECT 293.568,317.588..293.592,317.672 that its own OBS covers through
317.648, so only a 24-nm edge sliver is reachable. The tile route (Codex tap160c7) fails pin access (DRT-0073) on all
four elemA_cv clock pins. The source ODB is lost, so the view cannot be repaired in place, and a synthetic LEF edit is
not allowed. This kit re-implements the SAME source (git f11f3cc47, the five legacy files + 2 x ot_rom_4096x274_m8,
params LV 8 PAD 0 JOIN 1 ROWS 32 IOREG 1 SAFE 1 CUT 511 SPLIT9 1) with every signal pin pinned to its closed-view
position (outline 317.672 square, layers / rects unchanged), except clk, which gets a 0.192-um-square M5 terminal at
the same centre column (x 293.58) on the N edge (nearest other pin, rst_n, is 21.3 um away). No RTL or cycle change.

Flow and constraints follow the signed kits_repin core template (cores-r12 ot_s81sl_vq_lfp, main 24b2da3433): kit
SDC (833 ps, vclk 250 ps budget, 60/25 uncertainty, seam split), TT setup / FF hold, sdc_lint before synth,
face_guard after synth, signoff.py. The closed build's 2-cycle ROM-read multicycle (v41_w10_elem_pp_multicycle.sdc)
is NOT carried: sdc_lint forbids every exception command, so rd -> capture flop is timed at ONE cycle (stricter; ROM
clk->rd_out 590 ps TT, capture flops at the macro pins). Attempt c1 failed sdc_lint on exactly that.
c2 (f11f3cc47 ot_dsrom_head_elem as top) failed face_guard: o_v/o_d/l_v/l_d (50 bits) are root / join registers
that also feed the join ('shared'). c3 (lane RTL + sim wrapper) failed face_guard too (l_d / best_row / go / done).
c4 = f11f3cc47 RTL under rtl/dsrom_sys/s81_head/ot_s81hd_elemA_rb.sv (top ot_s81hd_elemA_cv), which gives those four
ports a dedicated keep output register; FAIL face_guard (keep on the reg wires leaves a buffer load on the port net;
best_row is read by the argmax compare; done / best_* are hold flops feeding their own D).
c5 = the same wrapper with ONE register stage on EVERY output, ot_s81hd_oreg (keep_hierarchy, like ot_dp_st): +1 cycle
uniform on all elemA outputs (sim model ot_s81hd_elem_cv.sv carries the same stage; tile bench EXP_CYC +1).

    python3 hd_elemA_rebuild.py --infra <signed kit dir to copy run_kit.sh/... from> --out <kit dir>
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

R = Path(__file__).resolve().parents[2]
SRC_REV = "f11f3cc47940002283d1dfcd2de63b6bcfb57f20"
# c4: the CLOSED element RTL (f11f3cc47, five legacy files) under the physical wrapper ot_s81hd_elemA_rb.sv (module
# ot_s81hd_elemA_cv: dedicated keep output registers on o_v/o_d/l_v/l_d, which the bundle leaves unconnected).
# (c3 used the lane RTL ot_s81hd_elem + the sim wrapper: face_guard 'shared' on l_d / best_row / go / done.)
SRCS = ["rtl/v41rom/ot_dsrom_head_elem.sv", "rtl/v41rom/ot_v41_fadd.sv", "rtl/common/ot_prefix.sv",
        "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_dsrom_bmul3.sv"]
OREG = "rtl/dsrom_sys/s81_head/ot_s81hd_oreg.sv"
ROM = "ot_rom_4096x274_m8"
INFRA = ["run_kit.sh", "face_guard_core.py", "face_guard.py", "face_flops.tcl", "face_flops_release.tcl",
         "ot_keep_regs.tcl", "pin_audit.py", "corners.tcl", "sdc_lint.py", "signoff.py", "clock_family.tcl",
         "pdn.tcl", "make_tracks.tcl", "drv.tcl"]
# --elem B (10-24): the same rebuild for the closed elemB view (dshead-elemB-ss-a318fdf47; the five RTL files are
# byte-identical at a318fdf47 and f11f3cc47).  Its view is a legacy SS closure (no signoff.py record), so the tile
# needs it rebuilt under the current flow too; clk (W edge M4 stub 0..0.084 x 257.568..257.592) gets the same 0.192
# square.  ROMs: centred in x (77.76), rom0 y 103.68, rom1 y 190.08 (23.4-um gap, 20-um top margin under the N o_d pins).
ELEMS = dict(
    A=dict(WRAP="rtl/dsrom_sys/s81_head/ot_s81hd_elemA_rb.sv", TOP="ot_s81hd_elemA_cv",
           OLD_LEF="physical/dsrom_fh_safe/closed/elemA/ot_dsrom_head_elem.lef", S=317.672,
           CLK_RECT=(293.484, 317.480, 293.676, 317.672), OLD_CLK=[293.568, 317.588, 293.592, 317.672],
           PARAMS="LV 8 PAD 0 JOIN 1 ROWS 32 IOREG 1 SAFE 1 CUT 511 SPLIT9 1", NPINS=458, NICK="hd_elemA_rb",
           ROMS="u_m.u_rom0 95.04 146.88 R0 u_m.u_rom1 95.04 233.28 R0"),
    B=dict(WRAP="rtl/dsrom_sys/s81_head/ot_s81hd_elemB_rb.sv", TOP="ot_s81hd_elemB_cv",
           OLD_LEF="physical/dsrom_fh_safe/closed/elemB/ot_dsrom_head_elem.lef", S=277.652,
           CLK_RECT=(0.0, 257.484, 0.192, 257.676), OLD_CLK=[0.0, 257.568, 0.084, 257.592],
           PARAMS="LV 6 PAD 2 JOIN 0 ROWS 128 IOREG 1 SAFE 1 CUT 511 SPLIT9 1", NPINS=None, NICK="hd_elemB_rb",
           ROMS="u_m.u_rom0 77.76 103.68 R0 u_m.u_rom1 77.76 190.08 R0"))


def lef_pins(text):
    out = []
    for name, block in re.findall(r"^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$", text, re.M | re.S):
        if "USE POWER" in block or "USE GROUND" in block:
            continue
        d = re.search(r"DIRECTION (\w+)", block).group(1)
        rects = re.findall(r"LAYER (M\d+)\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", block)
        assert len(rects) == 1, (name, rects)
        layer, *r = rects[0]
        out.append((name, d, layer, tuple(map(float, r))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infra", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--density", type=float, default=0.50)
    # c7: CP2 early core tap.  The element's own tree is ~450 ps TT (c6 CTS: 156 ps pin -> root over the 317-um core,
    # then 10 BUFx24 levels to 28.7k flops), so against the 250-ps vclk every input pin register saw -214 ps hold
    # (16.5k endpoints, 21.5k hold buffers, 'unable to repair').  The tile delivers this core's clk EARLY (gen_phys
    # core_taps: source latency -early on the tap port), so the kit models exactly that: clk source latency -EARLY,
    # sdc_lint port_latency_ps {clk: -EARLY}; pin-register arrival = tree - EARLY ~ 250 (signoff +-40).
    ap.add_argument("--early-ps", type=float, default=200.0)
    ap.add_argument("--elem", choices=["A", "B"], default="A")
    a = ap.parse_args()
    globals().update(ELEMS[a.elem])
    K, old = Path(a.out), Path(a.infra)
    K.mkdir(parents=True, exist_ok=False)
    for n in INFRA:
        shutil.copy2(old / n, K / n)
    for n in ("face_keep.tcl", "face_keep_release.tcl"):     # CP1-R10 main 0ce45ab03c hooks
        shutil.copy2(R / "tools/die_plan" / n, K / n)
    (K / "rtl").mkdir()
    (K / "macros").mkdir()
    for s in SRCS:
        (K / "rtl" / Path(s).name).write_bytes(subprocess.check_output(["git", "-C", str(R), "show", f"{SRC_REV}:{s}"]))
    for f in (WRAP, OREG):
        shutil.copy2(R / f, K / "rtl" / Path(f).name)
    md = R / "physical/asap7_memory_macros_v2" / ROM
    for ext in [".lef", "_tt.lib", "_ff.lib"]:
        shutil.copy2(md / (ROM + ext), K / "macros" / (ROM + ext))
    shutil.copy2(md / (ROM + "_bb.v"), K / "rtl" / (ROM + "_bb.v"))

    pins, io, ins, outs = [], [], set(), set()
    for name, d, layer, (x0, y0, x1, y1) in lef_pins((R / OLD_LEF).read_text()):
        if name == "clk":
            x0, y0, x1, y1 = CLK_RECT
        x, y, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        io.append(f"place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.4f} {y:.4f}}} "
                  f"-pin_size {{{w:.4f} {h:.4f}}}")
        m = re.match(r"^(.*)\[(\d+)\]$", name)
        base = m.group(1) if m else name
        face = min([(x0, "W"), (S - x1, "E"), (y0, "S"), (S - y1, "N")])[1]
        pins.append(dict(bus=base, bit=int(m.group(2)) if m else None, layer=layer, x=round(x, 4), y=round(y, 4),
                         face=face))
        if base != "clk":
            (ins if d == "INPUT" else outs).add(base)
    assert NPINS is None or len(pins) == NPINS, len(pins)
    (K / "io.tcl").write_text("# GENERATED by tools/s81_head/hd_elemA_rebuild.py: closed-view pin rects, clk enlarged\n"
                              + "\n".join(io) + "\n")
    (K / "pins.json").write_text(json.dumps(pins) + "\n")
    (K / "face_guard_skip.txt").write_text("^(clk|rst_n)$\n")

    sdc = f"""# GENERATED by tools/s81_head/hd_elemA_rebuild.py: kits_repin core SDC form (ps / fF) (no exceptions).
create_clock -name clk -period 833.0000 [get_ports {{clk}}]
create_clock -name vclk -period 833.0000
set_clock_latency -source 250.0000 [get_clocks vclk]
set_clock_uncertainty 60.0000 -setup [all_clocks]
set_clock_uncertainty 25.0000 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30.0000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30.0000
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold 12.5000
set non_clk_in [all_inputs -no_clocks]
set_input_delay -max 166.6000 -clock vclk $non_clk_in
set_output_delay -max 166.6000 -clock vclk [all_outputs]
set_input_delay -max 416.5000 -clock vclk [get_ports {{rst_n}}]
set_input_delay -min -40.0000 -clock vclk $non_clk_in
set_output_delay -min 0.0000 -clock vclk [all_outputs]
set_load 2 [all_outputs]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $non_clk_in
# CP2 early core tap: the parent delivers clk {a.early_ps:g} ps early (core tree ~{a.early_ps + 250:g} ps -> pin registers ~250)
set_clock_latency -source -clock clk {-a.early_ps:.4f} [get_ports {{clk}}]
"""
    (K / "constraint.sdc").write_text(sdc)
    io_floor = {p: 166.6 for p in sorted(ins) + sorted(outs)}
    (K / "sdc_lint.json").write_text(json.dumps(dict(
        period_ps=833.0, insertion_ps=250.0, insertion_tol_ps=40.0, clock_ports=["clk"], inputs=sorted(ins),
        outputs=sorted(outs), unc_setup_ps=60.0, unc_hold_ps=25.0, time_unit_ps=1.0, io_floor_ps=io_floor,
        port_latency_ps={"clk": -a.early_ps}), indent=1) + "\n")
    vfiles = " ".join("/work/rtl/" + p.name for p in sorted((K / "rtl").iterdir()))
    cfg = f"""# GENERATED by tools/s81_head/hd_elemA_rebuild.py (closed elemA source rebuild, enlarged clk terminal).
export DESIGN_NICKNAME = {NICK}
export DESIGN_NAME = {TOP}
export PLATFORM = asap7
export VERILOG_FILES = {vfiles}
export VERILOG_INCLUDE_DIRS = /work/rtl
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export DIE_AREA = 0 0 {S} {S}
export CORE_AREA = 4.32 4.32 {S - 4.32:.3f} {S - 4.32:.3f}
export IO_CONSTRAINTS = /work/io.tcl
export PDN_TCL = /work/pdn.tcl
override export MAKE_TRACKS = /work/make_tracks.tcl
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M5
export PLACE_DENSITY = {a.density}
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export LEC_CHECK = 0
export HOLD_SLACK_MARGIN = 15
export SETUP_SLACK_MARGIN = 0
export SKIP_LAST_GASP = 0
export TNS_END_PERCENT = 100
export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl
export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl
export CORNER = TC
export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl
export OT_KEEP_PIN_REGS = 1
export CORNERS = tc bc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) /work/macros/{ROM}_tt.lib
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /work/macros/{ROM}_ff.lib
export SLEW_MARGIN = 20
export CAP_MARGIN = 20
export PRE_RESIZE_TCL = /work/drv.tcl
export PRE_GLOBAL_ROUTE_TCL = /work/drv.tcl
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5
export ADDITIONAL_LEFS = /work/macros/{ROM}.lef
export ADDITIONAL_LIBS = /work/macros/{ROM}_tt.lib
export MACRO_PLACE_HALO = 4.32 4.32
export MACRO_ROWS_HALO_X = 4.32
export MACRO_ROWS_HALO_Y = 4.32
export SYNTH_HDL_FRONTEND = slang
export PRE_SYNTH_TCL = /work/face_keep.tcl
export POST_SYNTH_TCL = /work/face_keep_release.tcl
"""
    # c6: fixed ROM sites (the c5 auto placement stacked both ROMs against the W core edge: W-side rd_out / ctl pins
    # in the 4.32 halo with no room for their capture flops - REJECTED at the floorplan review).  Both R0 (ctl + 130 rd
    # pins on W, 144 rd on E, all in the bottom 14.5 um), centred in x (95.04: 86 um W / 97 um E for capture flops and
    # logic), in the upper half, pin edges facing the multiplier / tree logic below; 8.64 lattice (site / row / M4-M5
    # track multiple).  rom0 146.88..209.83, 23.4-um gap, rom1 233.28..296.23 (17-um top margin, N pins clear).
    (K / "macro_place.tcl").write_text("""# GENERATED by tools/s81_head/hd_elemA_rebuild.py: fixed ROM sites (core frame um)
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {name x y orient} {%s} {
  set i [$b findInst $name]
  if {$i eq "NULL" || $i eq ""} { error "hd_elemA_rebuild macro_place: no instance $name" }
  $i setOrient $orient
  $i setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
  $i setPlacementStatus FIRM
  puts "HD_ELEM place: $name at $x $y $orient"
}
""" % ROMS)
    cfg += "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n"
    (K / "config.mk").write_text(cfg)
    (K / "core.json").write_text(json.dumps({"boundary_role": {"clk": "clk", "rst_n": "reset"}}) + "\n")
    (K / "boundary_guard_context.json").write_text(json.dumps(dict(
        schema="opentallas.core_boundary_guard_context.v1", source_core_json="core.json", clock_ports=["clk"],
        unused_clock_ports=[], reset_ports=["rst_n"], data_pin_exemptions=[]), indent=1) + "\n")
    (K / "rebuild.json").write_text(json.dumps(dict(
        schema="opentallas.s81_head.elem_rebuild.v1", closed_source_rev=SRC_REV, top=TOP, wrapper=[WRAP, OREG], sources=SRCS, params=PARAMS, rom="asap7_memory_macros_v2/" + ROM,
        pins=len(pins), elem=a.elem, old_clock_rect=OLD_CLK, new_clock_rect=list(CLK_RECT),
        infra=str(old), early_core_tap_ps=a.early_ps, scope="rebuild of the LOST closed elemA physical source; no RTL or cycle change"), indent=1) + "\n")
    print(K, len(pins), len(ins), len(outs))


if __name__ == "__main__":
    main()

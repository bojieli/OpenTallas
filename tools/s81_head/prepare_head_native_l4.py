"""Stage a NEW native B source/physical kit; never inherit old run or verdicts.

The 293 live pins retain their old coordinates. Old A-only B inputs and unused
B outputs are absent from this master. A parent must bind the new interface and
new view explicitly; none of the previous physical closures qualify this kit.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from head_native_profile import timed_profile
from rom_addr_local import transform as local_addresses


def stage_sources(repo, out):
    """Stage the exact prepared native RTL for physical kits or source witnesses."""
    source_paths = ["rtl/common/ot_prefix.sv", "rtl/v41rom/ot_v41_fadd.sv",
        "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_dsrom_bmul3.sv",
        "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv",
        "rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv",
        "rtl/dsrom_sys/s81_head/ot_s81hd_elemB_l4_native.sv",
        "rtl/dsrom_sys/s81_head/ot_s81hd_rom_addr_copy.sv",
        "rtl/dsrom_sys/s81_head/ot_s81hd_rst_capture.sv"]
    profiled = {"ot_s81hd_elem.sv", "ot_s81hd_elemB_l4_native.sv", "ot_hdc_fp32_f12.sv",
                "ot_dsrom_bmul3.sv", "ot_s81hd_rom_addr_copy.sv"}
    tags, reports, hashes = 0, [], {}
    for relative in source_paths:
        path = repo / relative
        text = path.read_text()
        if path.name == "ot_s81hd_elem.sv": text = local_addresses(text)
        if path.name in profiled:
            text, record = timed_profile(text, path.name, tags)
            tags = record["next_tag"]
            reports.append(record)
        target = out / path.name
        target.write_text(text)
        hashes[path.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    return tags, reports, hashes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "rtl").mkdir()
    seed_files = ("constraint.sdc", "vclk_ff.sdc", "face_flops.tcl", "face_flops_release.tcl",
                  "pdn.tcl", "make_tracks.tcl", "macro_place.tcl", "setRC_rcx.tcl",
                  "prects_estimate.tcl", "prects_clear.tcl")
    for name in seed_files:
        shutil.copy2(args.seed / name, out / name)
    shutil.copytree(args.seed / "macros", out / "macros")
    shutil.copy2(args.seed / "rtl/ot_rom_4096x274_m8_bb.v", out / "rtl/ot_rom_4096x274_m8_bb.v")
    for name in ("face_keep.tcl", "face_keep_release.tcl", "face_guard_core.py",
                 "pin_audit.py"):
        if name == "face_guard_core.py":
            (out/name).write_bytes(subprocess.check_output(["git","-C",str(repo),"show","HEAD:physical/die_plan/hbm_arch_cores/face_guard_core.py"]))
        else: shutil.copy2(repo / "tools/die_plan" / name, out / name)
    shutil.copy2(repo / "physical/common_flow/ot_keep_regs.tcl", out / "ot_keep_regs.tcl")
    subprocess.run(["python3", "-I", str(repo / "tools/die_plan/signoff.py"),
                    "bundle", str(out), "--with", "postcts_gate.tcl"], check=True)
    shutil.copy2(repo / "tools/s81_head/head_rom_if.tcl", out / "head_rom_if.tcl")
    tags, reports, hashes = stage_sources(repo, out / "rtl")
    # Dedicated real port set. No replacement/tie/alias of removed pins.
    live = {"clk", "rst_n", "go", "x", "o_v", "o_d", "fault"}
    pins = [p for p in json.loads((args.seed / "pins.json").read_text()) if p["bus"] in live]
    assert len(pins) == 293, len(pins)
    (out / "pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    io = []
    for line in (args.seed / "io.tcl").read_text().splitlines():
        m = re.search(r"-pin_name\s+\{([^}]+)\}", line)
        if m and m[1].split("[")[0] in live: io.append(line)
    assert len(io) == 293, len(io)
    (out / "io.tcl").write_text("# Native B: unchanged coordinates of live pins only.\n" + "\n".join(io) + "\n")
    (out / "face_guard_skip.txt").write_text("^(clk|rst_n)$\n")
    # Seed SDC is narrowed to actual buses without touching period, bounds or IO budgets.
    for name in ("constraint.sdc", "vclk_ff.sdc"):
        text = (out / name).read_text()
        text = re.sub(r"(?m)^.*get_ports\s+\{(?:row0|b_v|b_d|l_v|l_d|done|best_row|best_bits|best_key)(?:\[[^}]*\])?\}.*\n", "", text)
        (out / name).write_text(text)
    rtl = " ".join("/work/rtl/" + p.name for p in sorted((out / "rtl").iterdir()))
    cfg = f"""# New native B; only SYNTH is authorized until LEC and geometry review.
export DESIGN_NICKNAME = hd_elemB_l4_native
export DESIGN_NAME = ot_s81hd_elemB_l4_native
export PLATFORM = asap7
export VERILOG_FILES = {rtl}
export VERILOG_INCLUDE_DIRS = /work/rtl
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export DIE_AREA = 0 0 277.652 277.652
export CORE_AREA = 4.32 4.32 273.332 273.332
export IO_CONSTRAINTS = /work/io.tcl
export PDN_TCL = /work/pdn.tcl
override export MAKE_TRACKS = /work/make_tracks.tcl
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M5
export PLACE_DENSITY = 0.5
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_HDL_FRONTEND = slang
export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl
export OT_KEEP_PIN_REGS = 1
export PRE_SYNTH_TCL = /work/face_keep.tcl
export POST_SYNTH_TCL = /work/face_keep_release.tcl
export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl
export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl
export PRE_FLOORPLAN_TCL = /work/prects_estimate.tcl
export MACRO_PLACEMENT_TCL = /work/macro_place.tcl
export MACRO_PLACE_HALO = 4.32 4.32
export MACRO_ROWS_HALO_X = 4.32
export MACRO_ROWS_HALO_Y = 4.32
export ADDITIONAL_LEFS = /work/macros/ot_rom_4096x274_m8.lef
export ADDITIONAL_LIBS = /work/macros/ot_rom_4096x274_m8_tt.lib
export CORNER = TC
export CORNERS = tc bc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) /work/macros/ot_rom_4096x274_m8_tt.lib
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /work/macros/ot_rom_4096x274_m8_ff.lib
export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl
export SET_RC_TCL = /work/setRC_rcx.tcl
export OT_HOLD_MM = 0
export SKIP_CTS_REPAIR_TIMING = 1
export SKIP_INCREMENTAL_REPAIR = 1
export HOLD_SLACK_MARGIN = 0
export OT_VCLK_TT = 250
export OT_VCLK_FF = 170
"""
    (out / "config.mk").write_text(cfg)
    profile = dict(kind="S81_HEAD_B_L4_TIMED_NATIVE", physical_view_adoption=False,
        top="ot_s81hd_elemB_l4_native", reset_input_timed=True,
        reset_delivery_cycles=1, synchronous_reset_consumption=True,
        earliest_go_capture_edge_after_input_release=3,
        earliest_go_accept_edge_after_input_release=4,
        activation_word_a_edge_after_go_pin="6+a",
        go_pin_register_cycles=1, die_start_is_element_go=False, start_bus="go",
        invalid_start="ignored while local reset; sticky fault when GO arrives before ready",
        input_ports=dict(clk=1, rst_n=1, go=1, x=256), output_ports=dict(o_v=1, o_d=32, fault=1),
        live_pins=293, removed_unused_inputs=50, removed_unused_outputs=115,
        arithmetic_latency=4, output_stage_cycles=1, rom_address_replicas=24,
        steady_state_extra_cycles=0, source_hashes=hashes, transformations=reports,
        physical_gates="fresh RTL/netlist LEC, planned+actual geometry review, new clock/reset/F6 gates before route")
    (out / "native_profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    print(out)


if __name__ == "__main__": main()

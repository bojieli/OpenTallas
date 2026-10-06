#!/usr/bin/env python3
"""One frozen final-source D4/N4 compile and three retained representative stages.

This recipe invokes the original HA8 frontend. It does not emit engine RTL,
generate golden data, alter source parameters, or simulate arithmetic in Python.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(sys.argv[1]).resolve()
SRC = ROOT / "src"
OLD = Path("/srv/opentallas-scratch/claude/hbm-fmax-qme/runs/build_tgt_me1_sh6c")
Q = Path("/srv/opentallas-scratch/claude/qwen-hbmacc-8k")
ADMIT = "/srv/opentallas-scratch/admit.sh"
FLAGS = ["--tp", "4", "--winw", "224", "--mem-extra", "1",
         "--arith-target", "--spine-h", "--scale-lat", "6", "--jobs", "16"]
ENV = dict(os.environ, NUM_CORES="16", OT_SYNTH_TIMEOUT_SECONDS="unlimited",
           OT_FLOW_TIMEOUT_SECONDS="unlimited")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, record):
    p = ROOT / name
    with p.open("x") as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write("\n")


def call(argv, out):
    with out.open("x") as log:
        rc = subprocess.call(argv, cwd=SRC, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    out.with_suffix(".exit").write_text(f"{rc}\n")
    return rc


if (ROOT / "model_delta.json").exists():
    raise SystemExit("Existing attempt: reuse its handles/results; no automatic restart")
if subprocess.check_output(["git", "status", "--porcelain"], cwd=SRC).strip():
    raise SystemExit("Pinned source must be clean")
sys.path.insert(0, str(SRC / "tools"))
import qwen_hbmacc_rt_token_w12 as HA

pins = {str(p.relative_to(SRC)): sha(p) for p in
        sorted(set(HA.SOURCES + HA.C.PIPES + HA.BASE.TILE_RTL +
                   [SRC / "rtl/hdc/ot_hdc_fp32_mul_lat.sv"]))}
if pins["rtl/hdc/ot_qwen_me_spine_h_w12.sv"] != "af266fe6c1dbf1f4b287caae55ec32045ee185a0fa933e42f04217c2ada5b7da":
    raise SystemExit("Selected final spine source mismatch")
save("source_pins.json", pins)
save("source_identity.json", {"snapshot_commit": subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=SRC, text=True).strip(), "source_root": str(SRC)})
prior = json.loads((OLD / "build_params.json").read_text())
selected = json.loads(json.dumps(prior))
selected["die"] = ["-GD=4" if x == "-GD=2" else x for x in prior["die"]]
selected["coll"] = ["-GN=4" if x == "-GN=2" else x for x in prior["coll"]]
save("expected_build_params.json", selected)
save("model_delta.json", {
    "schema": "opentallas.qwen.ha8.final-source.tp4-layer-vehicle.v1",
    "role": "existing source integration measurement; no hardware change or physical admission",
    "selected_build_params": selected,
    "delta_from_selected_tp2": {"die_D": [2, 4], "collective_N": [2, 4],
                               "all_other_compiled_parameters_identical": True},
    "legacy_tp4_is_not_selected": True,
    "compiled_templates": {"die": 1, "collective": 1, "tile": 1, "wstream": 1},
    "runtime_replication": {"dies": 4, "wstreams": 4, "tile_instances_per_die": 1536},
    "engine": {"G": 6144, "lanes": 16, "weight_bytes_per_accepted_word": 98304,
               "weight_MACs_per_active_edge": 98304, "weight_MACs_per_byte": 1,
               "result_groups_per_die": 96, "port_elements_per_die": 24,
               "result_bits_per_active_edge_per_die": 96 * 16 * 32,
               "additional_engine_ports_vs_selected_tp2_per_die": 0},
    "retained_port_area_model": "existing_port_model.json",
    "once_only_port_cell_reservation_per_die_um2": 1557514.92,
    "once_only_port_cell_reservation_tp4_um2": 4 * 1557514.92,
    "new_RTL_area_delta_vs_same_selected_TP4_source_um2": 0,
    "whole_die_area_or_route_fit": None,
    "new_cut_or_pipeline_edges_vs_selected_source": 0,
    "selected_arithmetic": {"ACC_LAT": 7, "TREE_LAT": 7, "MUL_LAT": 6,
                            "SCALE_LAT": 6, "MEM_EXTRA": 1, "KV_PREP": 3, "FAST_ISSUE": 1},
    "clock_ps": {"core": 833.333, "HBM_controller": 1024,
                 "SS_setup_uncertainty": 60, "FF_hold_uncertainty": 25},
    "HBM_per_die": {"stacks": 4, "PCs": 128, "sector_bytes": 32,
                    "sectors_per_PC_per_word": 24, "window_words": 224,
                    "window_bytes": 224 * 98304, "credits_per_PC": 32,
                    "read_bytes_per_controller_edge_upper_bound": 128 * 32},
    "collective": {"participants": 4, "lanes": 16, "FIFO_depth": 16,
                   "link_latency": 11, "bytes_per_cycle_parameter": 3600,
                   "track_capacity_and_physical_slot_fit": None},
    "stage_inputs": {"position": 8191, "token": 24,
                     "preroll_controller_cycles": {"L5": 5000, "L20": 1000, "head": 0}},
    "latency": {"final_source_TP4_stage_cycles": None,
                "purpose": "measure actual launches, pipeline, collective, HBM waits and retirement together",
                "no_legacy_transfer_or_TP2_cycle_division": True,
                "three_stage_batch_is_not_full_token": True,
                "interlayer_prefetch_carryover_qualification": None},
    "physical_qualified": False, "clock_adopted": False,
})
inputs = {}
for name in ("L5", "L20", "head"):
    folder = Q / "runs/b_p8191_w224" / name
    words = (folder / "stages.txt").read_text().split()
    if words[0] != name or len(words) != 6:
        raise SystemExit(f"Expected one genuine TP4 stage with four image paths: {folder}")
    for p in words[1:5]:
        if not Path(p).is_dir():
            raise SystemExit(f"Missing original stage image {p}")
    inputs[name] = {str(folder / f): sha(folder / f) for f in ("stages.txt", "preload.hex", "cmd.txt")}
save("input_pins.json", inputs)
build = ROOT / "build"
build.mkdir()
# Reuse byte-identical template archives; only D4 die/N4 collective need compilation.
for name in ("tile", "wst"):
    subprocess.run(["cp", "-a", "--reflink=auto", str(OLD / name), str(build / name)], check=True)
(build / "build_params.json").write_text(json.dumps(prior, indent=1))
save("reused_archives.json", {str(p.relative_to(build)): sha(p)
                             for p in sorted(build.rglob("*.a"))})
front = [sys.executable, str(SRC / "tools/qwen_hbmacc_rt_token_w12.py")]
rc = call([ADMIT, "72", "--", *front, "--build-only", "--workdir", str(build), *FLAGS], ROOT / "build.log")
if rc:
    raise SystemExit(rc)
actual = json.loads((build / "build_params.json").read_text())
if actual != selected:
    raise SystemExit("Compiled parameter table does not match selected D4/N4 contract")
save("build_identity.json", {"binary_sha256": sha(build / "qwen_hbmacc_rt"),
                            "params_verified": True, "compiled_D": 4, "compiled_N": 4})


def run_stage(name):
    out = ROOT / name
    folder = Q / "runs/b_p8191_w224" / name
    out.mkdir()
    cmd = [ADMIT, "8", "--", *front, "--workdir", str(out), "--build-dir", str(build), *FLAGS,
           "--stages", str(folder / "stages.txt"), "--preload", str(folder / "preload.hex"),
           "--layout", "/home/ubuntu/w12/img_tp4/L0-d0/layer0_rom.json",
           "--oracle-dir", str(Q / "gold/tp4/P8191"), "--kv-dir", str(Q / "gold/tp4/P8191/kv_pre"),
           "--pos", "8191", "--token", "24", "--threads", "4",
           "--preroll", str({"L5": 5000, "L20": 1000, "head": 0}[name]),
           # Host compares uint32 cycle counter to signed long. LONG_MAX removes the legacy cycle cutoff.
           "--max-cycles", "9223372036854775807"]
    (out / "command.json").write_text(json.dumps(cmd, indent=2) + "\n")
    return name, call(cmd, out / "driver.log")


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    codes = dict(pool.map(run_stage, ("L5", "L20", "head")))
save("terminal.json", {"stage_returncodes": codes,
                       "source_stable": all(sha(SRC / p) == h for p, h in pins.items()),
                       "full_token_measured": False, "physical_admission": False})
raise SystemExit(0 if all(code == 0 for code in codes.values()) else 1)

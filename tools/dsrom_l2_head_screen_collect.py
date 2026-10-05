#!/usr/bin/env python3
"""Collect the L2 head-MAC SS pre-layout screens (area from ORFS synth_stat, timing from OpenSTA SS) into one JSON."""
import glob, hashlib, json, re
from pathlib import Path
R = Path(__file__).resolve().parents[1]  # the screening checkout; work dirs under R/work
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
runs = {}
for w in sorted((R / "work").iterdir()):
    st = glob.glob(str(w / "reports/asap7/*/base/synth_stat.txt"))
    tj = w / ("ss_macro.json" if (w / "ss_macro.json").is_file() else "ss.json")
    if not st or not tj.is_file():
        continue
    area = float(re.findall(r"Chip area for module '\\(\S+)': ([0-9.]+)", Path(st[0]).read_text())[-1][1])
    t = json.loads(tj.read_text())
    cfg = (w / "config.mk").read_text()
    runs[w.name] = dict(top=re.search(r"DESIGN_NAME\s*=\s*(\S+)", cfg).group(1),
                        params=re.search(r"VERILOG_TOP_PARAMS\s*=\s*(.*)", cfg).group(1).strip() if "VERILOG_TOP_PARAMS" in cfg else "",
                        adder_map_off="ADDER_MAP_FILE" in cfg, corner_synth="WC", sta_libs="SS RVT (+ macro SS liberty)" if tj.name == "ss_macro.json" else "SS RVT",
                        cell_area_um2=area, ss_setup_wns_ps=t["ss_setup_wns_ps"], worst_start=t["worst_start"], worst_end=t["worst_end"],
                        worst_slack_by_stage_ps=dict(list(t["worst_slack_by_stage_ps"].items())[:12]))
srcs = {p: sha(R / p) for p in ("rtl/v41rom/ot_v41_rom_elem_nv_w10.sv", "rtl/v41rom/ot_v41_rom_elem_w10.sv", "rtl/v41rom/ot_v41_bf16_lanes2_mv.sv",
                               "rtl/v41rom/ot_v41_bf16_lanes2.sv", "rtl/v41rom/ot_v41_segtree2.sv", "rtl/v41rom/ot_v41_fadd.sv", "rtl/v41rom/ot_v41_bmul2.sv",
                               "rtl/v41rom/ot_v41_chain2.sv", "tools/gpu_ss_prelayout.py")}
print(json.dumps(dict(schema="opentallas.dsrom.l2_head_mac_screen.v1", host="ot-agidock128", period_ps=833.0, uncertainty_ps=60,
                      basis="pre-layout: ORFS yosys/abc at CORNER=WC with ADDER_MAP_FILE disabled, OpenSTA SS RVT libs, ideal clock, "
                            "60 ps setup uncertainty, inputs/outputs false-pathed; ROM macros as their SS liberty",
                      source_sha256=srcs, runs=runs), indent=1))

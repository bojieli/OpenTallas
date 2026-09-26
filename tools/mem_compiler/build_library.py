#!/usr/bin/env python3
"""Compile every macro in configs/memories/asap7_macros.json into physical/asap7_memory_macros/.

Also writes physical/asap7_memory_macros/index.json: one entry per macro with
its size, density, efficiency, TT/SS/FF clock-to-output and fmax, and the
SHA-256 of every view, so a consumer (the full-chip flow) can pin the views.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
import rom_gen  # noqa: E402
import sram_gen  # noqa: E402

CONFIG = asap7.ROOT / "configs/memories/asap7_macros.json"
OUT = asap7.ROOT / "physical/asap7_memory_macros"


def summary(sheet: dict) -> dict:
    a, t = sheet["area"], sheet["timing"]
    return {
        "kind": sheet["kind"], "spec": sheet["spec"], "capacity_bits": sheet["capacity_bits"],
        "width_um": a["macro_width_um"], "height_um": a["macro_height_um"],
        "area_um2": round(a["macro_area_um2"], 3),
        "density_mb_per_mm2": round(a["density_mb_per_mm2"], 3),
        "array_efficiency": round(a["array_efficiency"], 4),
        "clk_to_q_ps": {c: round(t[c]["clk_to_q_ps"], 1) for c in t},
        "min_period_ps": {c: round(t[c]["min_period_ps"], 1) for c in t},
        "fmax_mhz": {c: round(v, 1) for c, v in sheet["fmax_mhz"].items()},
        "read_energy_fj_tt": round(t["tt"]["read_energy_fj"], 2),
        "leakage_nw_tt": round(t["tt"]["leakage_nw"], 2),
        "views": sheet["views"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    cfg_name = str(args.config.resolve().relative_to(asap7.ROOT)) \
        if args.config.resolve().is_relative_to(asap7.ROOT) else str(args.config)
    index = {"schema": "opentallas.asap7-memory-macros.v1",
             "generated_by": "tools/mem_compiler/build_library.py",
             "config": cfg_name, "config_sha256": asap7.sha256_file(args.config),
             "calibration_sha256": asap7.sha256_file(asap7.CALIBRATION_JSON),
             "usage": {"lef": "<name>/<name>.lef", "liberty": "<name>/<name>_{tt,ss,ff}.lib",
                       "blackbox": "<name>/<name>_bb.v", "behavioural": "<name>/<name>.v",
                       "orfs": "tools/run_abi3_physical.py --macro-view <name>=physical/asap7_memory_macros/<name>"},
             "macros": {}}
    for s in cfg.get("sram", []):
        sheet = sram_gen.compile_macro(sram_gen.SramSpec(**s), args.out)
        index["macros"][s["name"]] = summary(sheet)
    for s in cfg.get("rom", []):
        sheet = rom_gen.compile_macro(rom_gen.RomSpec(**s), args.out)
        entry = summary(sheet)
        entry["analytical_model_comparison"] = sheet["analytical_model_comparison"]
        index["macros"][s["name"]] = entry
    (args.out / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    for name, e in index["macros"].items():
        print(f"{name:34s} {e['width_um']:7.2f} x {e['height_um']:7.2f} um  {e['density_mb_per_mm2']:7.2f} Mb/mm2 "
              f"eff {e['array_efficiency']:.3f}  fmax tt/ss/ff {e['fmax_mhz']['tt']:.0f}/{e['fmax_mhz']['ss']:.0f}/"
              f"{e['fmax_mhz']['ff']:.0f} MHz")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Compare the behavioural and ASAP7-macro packed attention stage in the same exact RTL job."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import rtl_hdc_v41x_attn_campaign as C

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results/rtl/hdc_v41x_attn_macro_stage.json"
SOURCES = [C.RTL_TILE, C.RTL_ENG, C.RTL_STAGE, C.SRAM_MODEL, *C.LIB,
           C.TB_ENG, Path(__file__).resolve(), Path(C.__file__).resolve()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/v41x_attn_macro_stage"))
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    cfg = {"H": 4, "D": 64, "TD": 16, "NL": 1, "TROWS": 72}
    rng = np.random.default_rng(9)
    jobs = [C.random_job(rng, 4, 64, t, min(t, 40)) for t in (72, 1, 33)]
    arms = {}
    for macro in (0, 1):
        run = C.run_engine(args.scratch, f"macro_{macro}", cfg, jobs,
                           extra={"SRAM_MACRO": macro, "MAXCYC": 200000})
        arms[str(macro)] = {k: run[k] for k in ("bit_exact", "cycles", "scores_checked", "score_errors",
                                                 "pv_checked", "pv_errors", "timeout", "per_job")}
    index = json.loads((ROOT / "physical/asap7_memory_macros/index.json").read_text())
    mem = index["macros"]["ot_sram_1r1w_256x256_m2_r2c2"]
    full_macros = 4 * ((16 * 265 + 255) // 256)
    record = {
        "schema": "hdc_v41x_attn_macro_stage/1",
        "status": "pass" if all(arms[x]["bit_exact"] and not arms[x]["timeout"] for x in arms)
                           and arms["0"]["cycles"] == arms["1"]["cycles"] else "fail",
        "scope": "reduced H4/D64/T72 three-job engine; shipped H16/D512/T640 and adapter bypass not tested",
        "config": cfg,
        "arms": arms,
        "full_geometry": {"rows": 640, "row_bits": 16 * 265, "lanes": 4,
                          "macro_width_bits": 256, "macro_depth": 256,
                          "macros_per_engine": full_macros,
                          "macro_footprint_mm2_per_engine": full_macros * mem["area_um2"] / 1e6,
                          "area_basis": "sum of compiled ASAP7 SRAM LEF footprint, no wrapper routing or die scaling"},
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"attention macro stage {record['status']}: {args.output}")
    if record["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

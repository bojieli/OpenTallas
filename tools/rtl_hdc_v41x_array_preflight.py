#!/usr/bin/env python3
"""Prepare and lint the adopted all-unit five-package switched RTL array."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_array_campaign as C


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--all-unit", action="store_true", required=True)
    args = ap.parse_args()
    assert C.ALL_UNIT
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    name = "b3_h2_switch_stall"
    body, hp, hmc, shared, fabric, users, _, stall, plen, ngen, _ = C.CONFIGS[name]
    model = C.V.Model()
    lay = C.P.Layout(model)
    C.A.place_head_parts(lay)
    roms = scratch / "roms"
    C.A.write_roms(roms, lay)
    C.ximg.write_banked(roms / "hbank.hex", C.ximg.hbank_image(lay, 8), 32, 8)
    C.ximg.write(roms, lay, hhw=8, mg=8)
    sectors, _ = C.P.qe_hbm_image(lay)
    (roms / "hbm_q.hex").write_text(C.P.hexwords(sectors, C.P.QSEC))
    base = C.P.Machine(lay, np.zeros(C.I.KV_WORDS * C.I.W_LANES, dtype=np.float32),
                       np.zeros(C.I.VM_ELEMS, dtype=np.float32))
    gold = C.A.golden_runs(model, ngen, scratch / "gold.json", plen)
    plan = C.A.Plan(lay, C.A.split(model, body), hp, hmc, shared)
    progs = [C.A.StageBuilder(plan.lay, qchunk=C.P.QCHUNK).stage(plan, k)
             for k in range(plan.n)]
    recs, states = C.A.run_pipeline(plan, progs, base, gold)
    assert all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in recs)
    cfg = scratch / f"cfg_{name}"
    steps = C.A.write_config(cfg, plan, progs, gold, states)
    sectors, first = C.P.qe_hbm_image(lay)
    for k, prog in enumerate(progs):
        ents = C.P.qe_fetch_list(lay, prog, first)
        assert ents, f"stage {k}: empty QE fetch list"
        (cfg / f"qlist_stage{k:02d}.hex").write_text(C.P.hexwords(C.P.encode_list(ents), C.P.LIST_BITS))
    obj = scratch / "obj"
    obj.mkdir(exist_ok=True)
    svh = obj / "v41_array_cfg.svh"
    svh.write_text(C.config_svh(plan, lay, fabric))
    flags = ["-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR",
             "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD", "-Wno-MODDUP", "-Wno-VARHIDDEN",
             "-Wno-UNOPTFLAT", "-Wno-PINMISSING"]
    defines = [f"+define+HDC_SW={C.I.SU_LANES}"] + [
        f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}"
        for x in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")
    ] + ["+define+HDC_W_HBM=1"]
    rtl = [str(p) for p in C.core.rtl_sources(True) if p.suffix == ".sv"]
    cmd = ["verilator", "--lint-only", *flags, "--top-module", "tb_hdc_v41x_array",
           f"-GUSERS={users}", f"-GSTALL={stall}", f"-I{obj}", f"-I{C.core.SVH.parent}",
           str(C.core.VLT), *defines, *rtl, *map(str, C.BENCH_AUX_RTL),
           str(C.LINK), str(C.ROUTER), str(C.CTRL), str(C.TB)]
    log = scratch / "lint.log"
    with log.open("w") as fh:
        rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
    images = {str(p.relative_to(scratch)): sha(p) for base_dir in (roms, cfg) for p in base_dir.rglob("*") if p.is_file()}
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [*C.sources(), Path(__file__)]}
    fixture = ROOT / "build/models/deepseek-v4.1-flash-reduced-v2/model-00001-of-00001.safetensors"
    result = {
        "schema": "opentallas.rtl.v41x_allunit_switched_preflight.v1",
        "status": "pass" if rc == 0 else "fail", "verilator_exit_code": rc,
        "config": name, "packages": plan.n, "users": users, "steps": steps,
        "all_unit_parameters": {"X_HE": 1, "X_ME": 1, "X_ATT": 1, "X_IDX": 2,
                                "X_SEL": 1, "X_EG": 1, "X_SU": 1, "W_HBM": 1},
        "isa_pipeline": recs, "source_sha256": sources, "image_sha256": images,
        "model_fixture_sha256": sha(fixture), "config_svh_sha256": sha(svh),
        "lint_log_sha256": sha(log), "lint_command": cmd,
        "claim_boundary": "ISA/image and Verilator lint preflight only. No RTL token or full-array pass yet.",
    }
    (scratch / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "packages": plan.n,
                      "isa_runs": len(recs), "image_files": len(images), "sources": len(sources)}))
    if rc:
        raise SystemExit(rc)


if __name__ == "__main__":
    main()

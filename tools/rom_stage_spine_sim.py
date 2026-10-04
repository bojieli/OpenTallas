#!/usr/bin/env python3
"""Power-aware exactness bench for the GATED STAGE CLOCK SPINE (ot_v41_rom_elem_pg_sp_w10 #(PG = 1, SPINE = 1)).

Same method as tools/rom_stage_pg_sim.py (b9e66e66d): the gated domain is the Yosys-flattened element whose every
stored bit is randomised when the header-switch model reports it unpowered; the reference is the unmodified RTL
element, always on; every public output is compared on every cycle (rtl/test/tb_v41_rom_elem_pg_sp.sv).  The
spine bench also fails if the spine gate passes a clock edge while the domain is unpowered.

    python3 tools/rom_stage_spine_sim.py --work <dir> --out results/rtl/rom_stage_spine_gate_20261004
Mutants (each must FAIL): no_restore | no_iso | short_lead | spine_late (spine starts at isolation release, so the
domain reset sees no clock edge)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import rom_stage_pg_sim as base

ROOT = base.ROOT
TB = "rtl/test/tb_v41_rom_elem_pg_sp.sv"
TOP = "tb_v41_rom_elem_pg_sp"
PG_RTL = ["rtl/v41rom/ot_v41_rom_elem_pg_sp_w10.sv", "rtl/v41rom/ot_v41_rom_pg_ao_sp.sv",
          "rtl/v41rom/ot_v41_stage_pg_sched.sv", "rtl/chip/ot_chip_v41_pg_ctrl.sv"]
base.CORRUPT = f"{TOP}.pwr_off"


def run(work: Path, mutant: str | None, flat: Path, ref: Path) -> dict:
    exe = work / f"tb_{mutant or 'base'}.vvp"
    defs = ["-DPG_MUTANT_" + mutant.upper()] if mutant else []
    cmd = (["iverilog", "-g2012", "-DSYNTHESIS", "-o", str(exe), "-s", TOP, *defs, str(ROOT / TB), str(flat), str(ref)]
           + [str(ROOT / f) for f in base.ELEM if f != "rtl/v41rom/ot_v41_rom_elem_w10.sv"]
           + [str(ROOT / f) for f in PG_RTL])
    subprocess.run(cmd, check=True, cwd=work)
    t0 = time.time()
    p = subprocess.run(["vvp", "-n", str(exe)], cwd=work, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (work / f"sim_{mutant or 'base'}.log").write_text(log)
    ok = "PASS " in log and "FATAL" not in log and "fatal" not in log.lower().replace("$fatal", "")
    return dict(mutant=mutant, pass_=ok, returncode=p.returncode, seconds=round(time.time() - t0, 1),
                tail=[ln for ln in log.splitlines() if ln.startswith(("PASS", "TOKEN", "WAKE", "SPINE", "FATAL", "ERROR"))
                      or "fatal" in ln.lower() or "mismatch" in ln.lower()][-40:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--mutants", default="spine_late,no_restore,no_iso,short_lead")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    raw = base.flatten(a.work)
    flat = a.work / "elem_flat_pgx.v"
    inv = base.instrument(raw, flat)
    ref = a.work / "elem_ref.v"
    base.ref_copy(ref)
    res = dict(schema="opentallas.rtl.rom_stage_spine_exact.v1", element_params=base.PARAMS, domain_state=inv,
               sources={f: base.sha(ROOT / f) for f in base.ELEM + PG_RTL + [TB, "tools/rom_stage_spine_sim.py",
                                                                            "tools/rom_stage_pg_sim.py"]},
               spine=1, runs=[run(a.work, None, flat, ref)])
    for m in [x for x in a.mutants.split(",") if x]:
        res["runs"].append(run(a.work, m, flat, ref))
    b = res["runs"][0]
    res["verdict"] = dict(exact_with_gating=b["pass_"],
                          mutants_detected={r["mutant"]: not r["pass_"] for r in res["runs"][1:]})
    print(json.dumps(res["verdict"], indent=1))
    for r in res["runs"]:
        print(r["mutant"], r["pass_"], r["seconds"], *r["tail"][-6:], sep="\n  ")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "exact.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0 if b["pass_"] and all(res["verdict"]["mutants_detected"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

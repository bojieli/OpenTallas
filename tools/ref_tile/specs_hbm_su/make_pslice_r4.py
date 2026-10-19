#!/usr/bin/env python3
"""HBM-SU r4 2026-10-17: kit spec for hbm_su_pslice_r4_1017 (ot_hbm_su_programme_pslice_q4 = ot_hbm_su_programme PIPE 2).

Same floorplan and exact pin plan as r3 (tools/ref_tile/specs_hbm_su/make_pslice_r3.py: 7 lattice SRAM column stacks,
dictionary stacks at the S command band, index 7 x 8 above, full-face S/N pins, clk S x~471, local TritonCTS); the
ports of pslice_q4 equal pslice_q2's. RTL r4 removes the r2 gate's fan-out classes (see the pslice_q4 header):
index output registers per 4-bank quad (each quad inside one 8-macro stack), funnel group = 4 quads = 2 adjacent stack
columns that face one shared channel; dictionary output registers per bank pair (every pair inside one stack).
Macro instance paths gain the PIPE 2 generate scope g_m4.
Usage: python3 tools/ref_tile/specs_hbm_su/make_pslice_r4.py   (from the repo root)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R3 = ROOT / "tools/ref_tile/specs_hbm_su/hbm_su_pslice_r3_1017.json"
OUT_SPEC = ROOT / "tools/ref_tile/specs_hbm_su/hbm_su_pslice_r4_1017.json"
SRC = "rtl/hbm_accel/generic/adapters/static_su/programme/"


def main():
    s = json.loads(R3.read_text())
    s["name"] = "hbm_su_pslice_r4_1017"
    s["top"] = "ot_hbm_su_programme_pslice_q4"
    s["sources"] = [p.replace("ot_hbm_su_programme_pslice_q2.sv", "ot_hbm_su_programme_pslice_q4.sv") for p in s["sources"]]
    assert SRC + "ot_hbm_su_programme_pslice_q4.sv" in s["sources"]
    for m in s["macros"]:
        assert m["inst"].startswith("*u_p.") and m["inst"].count("u_p.") == 1
        m["inst"] = m["inst"].replace("*u_p.", "*u_p.g_m4.")
    s["structural_change"] = (
        "SUCCESSOR of hbm_su_pslice_r2_1017 (gate FAIL 9272b2f43) and r3 (placement-only, RTL = r2): RTL r4 = "
        "ot_hbm_su_programme PIPE 2 removes the r2 fan-out classes structurally -- dt select_q[0] 8,961 loads "
        "(macro->pair_q -1253) -> per output register x 4-slice replicated select/one-hot hit registers (<= 64 loads); "
        "c_v -> 2,422 command flops (-898) -> 40 per-column x slice valid copies; cfg c_bank/c_data -> 98 macros "
        "(-418/-385) -> registered per-bank write enables + 4 regional row/data copies; 28-pair index funnel "
        "(psel->indices_r -408) -> 14 quad output registers + registered 4-quad group stage + 4:1 final. "
        "Clock sinks ~14.5k (< 15k) + 98 macros on one local root. Floorplan/pins = r3.")
    b = []
    for x in s["job"]["benches"]:
        x = dict(x)
        x["cmd"] = x["cmd"].replace("PIPE=1", "PIPE=2")
        x["name"] = x["name"].replace("_pipe1", "_pipe2")
        b.append(x)
    cf = dict(next(x for x in b if x["name"] == "part_mut_stale"))
    cf["name"] = "part_mut_cfgrep"
    cf["cmd"] = cf["cmd"].replace("/stale", "/cfgrep").replace("ONLY=stale", "ONLY=cfgrep")
    assert "ONLY=cfgrep" in cf["cmd"]
    cf["note"] = "the last replicated configuration copy's row one edge late"
    b.append(cf)
    assert all("PIPE=2" in x["cmd"] for x in b)
    s["job"]["benches"] = b
    s["job"]["tag"] = "r4"
    s["job"]["purpose"] = ("partitioned SU programme per-quarter producer r4 (ot_hbm_su_programme_pslice_q4, PIPE 2: "
                           "replicated select/config/valid fan-out, registered index funnel group stage, +4 edges) on "
                           "the r3 lattice floorplan + exact full-face pins + local CTS")
    s["job"]["views_to"] = "physical/ref_tile/hbm_su_pslice_r4_1017/views"
    s["job"]["record_to"] = "results/rtl/ref_tile/hbm_su_pslice_r4_1017"
    OUT_SPEC.write_text(json.dumps(s, indent=1) + "\n")
    print("spec", OUT_SPEC, "top", s["top"], "macros", len(s["macros"]))


if __name__ == "__main__":
    main()

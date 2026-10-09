#!/usr/bin/env python3
"""Closure-loop job specs of stream qwen-lane-band (2026-10-08): OPTION-B TT routes (corner TC, MM FF hold HM 50 ps,
rule H1, CTS fix hooks + consistent die-link budget via tt_overlay) of the r21m band-lane master qfd_sp_band_lanes
(ot_qfd_band_lanes), with the exact reassembly bench (6 bands + the tree top's upper levels against the existing
ot_qwen_spine_lane) and its negative mutants.  Benches gate adoption, not launch.

    mk_jobs.py --commit <sha> [--out DIR]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qwen_vm_me"))
import mk_jobs as VM  # noqa: E402

RUN = "rtl/test/qwen_lane_band/run_band_lanes.sh"


def bench(name, g, exp, ram=8):
    b = dict(name=name, cmd=f"mkdir -p {{RUN}}/bench && JOBS=8 bash {RUN} {{RUN}}/bench/{name} {g}",
             expect=exp, threads=8, peak_ram_gb=ram, needs=["verilator"])
    b["pass_regex" if exp == "pass" else "fail_regex"] = f"^{'PASS' if exp == 'pass' else 'FAIL'} qfd_band_lanes"
    return b


def benches(full=True):
    out = [bench("band_exact_nl16", "-GNL=16 -GNOPS=3000 -GSEED=3", "pass", 16),
           bench("band_mut_order", "-GNL=4 -GMUT=1 -GNOPS=800", "fail")]
    if full:
        out += [bench("band_exact_lnk2", "-GNL=4 -GLNK=2 -GNOPS=4000 -GSEED=7", "pass"),
                bench("band_mut_upper", "-GNL=4 -GMUT=2 -GNOPS=800", "fail")]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", type=Path, default=Path("/tmp/claude-review-20261003/closure_jobs"))
    a = ap.parse_args()
    cost = ("ME op result +5 + 2 LNK edges (band word pin station, tree-top pin flop, tree-top station, band-0 pin "
            "flop, ty station; LNK relays each way) against the monolithic lane")
    jobs = [
        VM.job("qfd_sp_band_lanes", a.commit, "r21m qfd_sp_band_lanes: one band's 16 spine lanes, tree levels 8..10 over "
               "the band's 8 level-7 positions (112 FP32 adders LAT 7), round-trip wait, band-0 tree-top mux (b0 strap), "
               "pin flops / stations; 777.6 x 1131.84 PD 0.50", benches(), 64, cycles=cost),
        VM.job("qfd_sp_band_lanes_t", a.commit, "r21m qfd_sp_band_lanes AGGRESSIVE variant: 777.6 x 1555.2 PD 0.40",
               benches(full=False), 64, cycles=cost),
    ]
    a.out.mkdir(parents=True, exist_ok=True)
    for name, spec in jobs:
        spec["owner"] = "Claude:qwen-lane-band"
        spec["source"] = dict(branch="claude/qwen-lane-band-20261008", commit=a.commit)
        for r in spec["record"]:
            if r["to"].startswith("results/rtl/qwen_vm_me_20261008/routes/"):
                r["to"] = f"results/rtl/qwen_lane_band_20261008/routes/{name}"
        (a.out / f"{name}.json").write_text(json.dumps(spec, indent=1) + "\n")
        print(a.out / f"{name}.json")


if __name__ == "__main__":
    main()

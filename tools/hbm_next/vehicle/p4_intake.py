#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19): intake check for the P = 4 layer benches (MTP verify layer, 4-user layer).

The vehicle plugs sibling-lane drops in as they land; this tool says, fail-closed, which layer bench is buildable now
and what each one still waits for.  Minimum-component form (AGENTS.md): the P = 4 layer is NOT a die slice until DIE
has a bound P = 4 die netlist; it is the per-unit P = 4 benches (SM4 tile hnx_rp4lp4, ATT4 lane hnx_rp4a4, UNITS N-row
engines) driven by the CMTP P-lane records of one layer, with the layer cycles composed on the static schedule
(collision = fault) and bit-exactness checked against the CMTP goldens (AR, MTP accept + reject, 4-user).
Single-user AR needs none of this: it is the d4g path (ar_repro.py).

    python3 tools/hbm_next/vehicle/p4_intake.py [--out results/arch/hbm_next_1019/veh/p4_intake.json]
"""
import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = "results/arch/hbm_next_1019"
NEEDS = {
    "CMTP.isa_rows": [f"{A}/cmtp/isa_rows.md", "tools/hbm_next/isa_rows.py"],
    "CMTP.records_mtp": [f"{A}/cmtp/records/mtp_verify_L*.json", f"{A}/cmtp/emitter/whole/mtp_N6/emitter.json"],
    "CMTP.records_mu4": [f"{A}/cmtp/records/mu4_L*.json", f"{A}/cmtp/emitter/whole/mu_N4/emitter.json"],
    "CMTP.goldens_mtp": [f"{A}/cmtp/goldens/ar_mtp_g5/manifest.json", f"{A}/cmtp/goldens/mtp_all*/manifest.json"],
    "CMTP.goldens_mu4": [f"{A}/cmtp/goldens/mu4*/manifest.json"],
    "CMTP.binary_images": [f"{A}/cmtp/images/**/*.json", f"{A}/cmtp/emit/**/*.json", f"{A}/cmtp/emitter/whole/*/*.hgi1r"],
    "CMTP.static_schedule_checker": ["tools/hbm_next/static_check.py", f"{A}/cmtp/static/static_check.json"],
    "SM4.rtl": ["rtl/hbm_next/sm/*.sv"],
    "SM4.bench_pass": [f"{A}/sm4/bench_summary.json", f"{A}/sm4/bench/leaf*/run_p4_m0_t0.log"],
    "SM4.layer_shape_bench": [f"{A}/veh/sm4_layer/sm4_layer.json"],
    "ATT4.rtl": ["rtl/hbm_next/att/*.sv"],
    "ATT4.bench_pass": [f"{A}/att4/bench/throughput.json", f"{A}/att4/bench/s0*.log"],
    "UNITS.hc_rows": ["rtl/hbm_next/hc/*.sv"],
    "UNITS.hc_bench": [f"{A}/units/hc/README.md", f"{A}/units/hc/witness/*.log"],
    "UNITS.coll_bench": [f"{A}/units/coll/README.md", f"{A}/units/coll/witness/*"],
    "UNITS.fused_rows": ["rtl/hbm_next/fused/*.sv", "rtl/hbm_next/su/*.sv"],
    "UNITS.coll_rows": ["rtl/hbm_next/coll/*.sv"],
    "UNITS.idx_rows": ["rtl/hbm_next/idx/*.sv"],
    "DIE.p4_netlist": ["physical/hbm_next/**/die.v", f"{A}/die/*die*.v"],
}
BENCHES = {
    "AR layer (P = 1 records on the P = 4 die)": dict(needs=[], via="ar_repro.py + d4g SW-slice binary (sw5/sw5e)"),
    "MTP verify layer (6 positions on 4 lanes, accept + reject)": dict(
        needs=["CMTP.isa_rows", "CMTP.records_mtp", "CMTP.goldens_mtp", "CMTP.binary_images",
               "CMTP.static_schedule_checker", "SM4.rtl",
               "SM4.bench_pass", "ATT4.rtl", "ATT4.bench_pass", "UNITS.hc_rows", "UNITS.fused_rows",
               "UNITS.coll_rows", "UNITS.idx_rows"], via="per-unit P = 4 benches driven by one layer's records"),
    "4-user layer": dict(
        needs=["CMTP.isa_rows", "CMTP.records_mu4", "CMTP.goldens_mu4", "CMTP.binary_images",
               "CMTP.static_schedule_checker", "SM4.rtl",
               "SM4.bench_pass", "ATT4.rtl", "ATT4.bench_pass", "UNITS.hc_rows", "UNITS.fused_rows",
               "UNITS.coll_rows", "UNITS.idx_rows"], via="per-unit P = 4 benches driven by one layer's records"),
    "per-unit P = 4 layer benches, cycles (one layer's records: L2/L3 MTP N = 6 + 4-user N = 4)": dict(
        needs=["CMTP.isa_rows", "UNITS.hc_bench", "UNITS.coll_bench", "SM4.bench_pass", "SM4.layer_shape_bench",
               "ATT4.bench_pass"], via="p4_layer_units.py records/plan + run_sm4_layer.sh; cycles in the S2 schedule "
                                       "(compose_grid PHYS axis); value-exact needs CMTP.binary_images"),
    "P = 4 quadrant slice (integration smoke, optional)": dict(needs=["DIE.p4_netlist", "CMTP.records_mtp"],
                                                               via="cut_slice.py on the P = 4 die.v"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    have = {k: sorted({str(Path(p).relative_to(ROOT)) for pat in pats for p in glob.glob(str(ROOT / pat), recursive=True)})
            for k, pats in NEEDS.items()}
    benches = {}
    for name, b in BENCHES.items():
        miss = [n for n in b["needs"] if not have[n]]
        benches[name] = dict(ready=not miss, missing=miss, via=b["via"])
    out = dict(schema="opentallas.hbm_next_1019.veh.p4_intake.v1", rule=__doc__, inputs=have, benches=benches)
    txt = json.dumps(out, indent=1) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(txt)
    for n, b in benches.items():
        print(("READY  " if b["ready"] else "WAIT   ") + n + ("" if b["ready"] else "  <- " + ", ".join(b["missing"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

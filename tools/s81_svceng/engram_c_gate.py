#!/usr/bin/env python3
"""s81-svceng-1011: exact + throughput gate of the Engram slab master dsfd_engram_c (engine 10, ADAPTER_CONTRACT_1011).

Bench rtl/test/tb_dsfd_engram_c.sv = the lookup campaign's bench (tools/rtl_dsrom_engram_lookup_campaign.py: official
NgramHashState windows, shipped-table hash, behavioural HBM regions and TP4 all-gather) with every engine a
dsfd_engram_c master driven by engine-10 descriptors; the consumer reads each slot through the master's VM port only
after the 4 ranks' DONE and compares element for element with the golden (the campaign's compare()).
Base modes must PASS; negative controls must FAIL: dropped start (one descriptor never sent), wrong descriptor
(window number + 1), early done (done at window release), dropped
done (endpoint MUT 4), wrong done tag (endpoint MUT 2).  Throughput: NSLOT 8, 200 ns HBM, back-to-back windows.
Usage: engram_c_gate.py --out DIR [--quick]"""
import argparse, json, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
import rtl_dsrom_engram_lookup_campaign as C  # noqa: E402

E = ROOT / "rtl/dsrom_sys/engram"
SRC = C.SOURCES + [E / "dsfd_engram_sink.sv", E / "ot_dsrom_engram_prefetch.sv", ROOT / "rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv",
                   ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
                   ROOT / "rtl/lib/ot_reset_sync.sv", ROOT / "rtl/lib/ot_async_fifo.sv",
                   ROOT / "rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv", ROOT / "rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv",
                   E / "dsfd_engram_c.sv"]
TB = ROOT / "rtl/test/tb_dsfd_engram_c.sv"
STRESS = dict(LAT=60, JIT=400, STALL=30, GAP=30, REORD=1, BUB=10, CDEL=300, AGLAT=20, AGJIT=60)
BASE = [("ideal_hbm_200ns", dict(LAT=240), None), ("stressed", STRESS, 500),
        ("crc_injection", dict(LAT=60, JIT=200, STALL=20, GAP=20, REORD=1, BUB=30, CDEL=100, AGLAT=20, AGJIT=40, ERR=1), 400),
        ("isolated_local_ag", dict(LAT=240, SPACED=1, AGLAT=4), 60),
        ("throughput_b2b", dict(LAT=240, AGLAT=4), 400)]
NEG = [("dropstart", dict(TBMUT=1)), ("wrongdesc", dict(TBMUT=2)), ("earlydone", dict(CMUT=5)),
       ("droppeddone", dict(EPMUT=4)), ("wrongtag", dict(EPMUT=2))]


def build(obj, g):
    exe = obj / "Vtb_dsfd_engram_c"
    subprocess.run(["verilator", *C.VL, "--top-module", "tb_dsfd_engram_c", "-GNSLOT=8",
                    *(f"-G{k}={v}" for k, v in g.items()), "-Mdir", str(obj), *map(str, SRC), str(TB), str(C.HARNESS),
                    "-CFLAGS", "-O1 -DVTOP=Vtb_dsfd_engram_c"], check=True, capture_output=True)
    return exe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--neg", choices=[n for n, _ in NEG])
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t = C.ES.shipped_tables()
    ev = C.build_events(np.random.default_rng(20261008), 120 if a.quick else 600)
    wins = C.official_windows(ev)
    if a.neg:      # negative-control bench: exit 1 when the mutant FAILS the bench (as required), 0 when missed
        g = dict(NEG)[a.neg]
        rec = C.run_mode(build(a.out / f"obj_{a.neg}", g), a.out, t, ev, wins, a.neg, STRESS, 200)
        print("ENGRAM_C_NEG", a.neg, "FAIL as required" if not rec.get("pass") else "MISSED")
        return 1 if not rec.get("pass") else 0
    jobs = [("base", {})] + NEG

    def one(j):
        name, g = j
        d = a.out / f"obj_{name}"
        try:
            exe = build(d, g)
        except subprocess.CalledProcessError as e:
            return name, {"build_failed": e.stderr.decode(errors="replace")[-800:]}
        if name == "base":
            res = {}
            for m, args, lim in BASE:
                res[m] = C.run_mode(exe, a.out, t, ev, wins, m, args, lim)
                print(m, "pass" if res[m].get("pass") else "FAIL", res[m].get("cycles"), flush=True)
            return name, res
        return name, C.run_mode(exe, a.out, t, ev, wins, name, STRESS, 200)

    with ThreadPoolExecutor(len(jobs)) as ex:
        out = dict(ex.map(one, jobs))
    base = out["base"]
    ok_base = all(isinstance(v, dict) and v.get("pass") for v in base.values()) if "build_failed" not in base else False
    negs = {n: (not out[n].get("pass")) and "build_failed" not in out[n] for n, _ in NEG}
    tp = base.get("throughput_b2b", {}) if ok_base else {}
    rec = {"schema": "opentallas.s81.engram-c-gate.v1", "verdict": "PASS" if ok_base and all(negs.values()) else "FAIL",
           "base": base, "negatives_caught": negs,
           "negatives": {n: {k: out[n].get(k) for k in ("bench_pass", "element_mismatches", "dumps", "all_dumps_present",
                                                        "build_failed")} for n, _ in NEG},
           "throughput_b2b_cycles_per_token": round(tp["cycles"] / tp["tokens"], 1) if tp.get("tokens") else None,
           "budget_lookup_local_cycles": 500}
    (a.out / "gate.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    print("ENGRAM_C_GATE", rec["verdict"], json.dumps(negs), "tput", rec["throughput_b2b_cycles_per_token"])
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Compose the Qwen3-8B ROM 8K token on the 4-stack full-bandwidth KV path (STREAM4) from measured layers.

Owner rules: simulate the minimum component, measure at the target context only (P = 8,191, one layer per type),
publish only measured compositions.  Inputs (each a tools/qwen_rom_rt_token_stream4_w12.py result, exact vs the GPU
ISA golden realmem-ctx8k/gold/P8191):
  * iso      L0 isolated (HBM from reset, no notice: the whole window fill is exposed);
  * chained  L0,L1,L2 chained with the straps (--early-go --posted-wb): L1/L2 are the steady layer, their window is
             streamed during the previous layer's MLP (cross-layer prefetch);
  * base     (optional) L0,L1,L2 chained without the straps (the notice only), for the A/B;
plus references: the REAL_MEM one-stack job and the KV_IDEAL job at P8191 (compute-only bound, same golden), and E /
head cycles from the P255 full-token record (they carry no KV term).  The token is composed as the P255 and the
realmem-ctx8k records compose it:
    7 + E + (L0_iso - 1) + 35 x chained_steady + (head - 1) + 37 stage switches
with chained_steady the mean of the chained L1/L2 (max as the bound).  The achieved HBM bandwidth of a layer is its
window (MEMSTAT fill_sectors x 32 B) over its fill time (fill_cycles at 1.2 GHz), against the 4-stack peak
4 x 32 PCs x 32 B / 1.024 ns = 4.000 TB/s.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PEAK_BPS = 4 * 32 * 32 / 1.024e-9
HZ = 1.2e9


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def job(d: Path) -> dict:
    r = json.loads((d / "result.json").read_text())
    exact = (r["status"] == "pass" and all(v["mismatches"] == 0 for v in r["layer_x_checks"].values())
             and all(v["k_mismatches"] == 0 and v["v_mismatches"] == 0 for v in r.get("token_kv_writeback_checks", {}).values()))
    st = {}
    for n, s in r["stages"].items():
        mem = s.get("memory", {})
        m0 = mem.get("die0", {})
        fc, fs = m0.get("fill_cycles", 0), m0.get("fill_sectors", 0)
        st[n] = {"cycles": s["cycles"], "memory_die0": m0,
                 "memory_dies_identical": len({json.dumps(v, sort_keys=True) for v in mem.values()}) <= 1,
                 "fill_TBps": round(fs * 32 / (fc / HZ) / 1e12, 3) if fc else None,
                 "fill_pct_of_peak": round(100 * fs * 32 / (fc / HZ) / PEAK_BPS, 1) if fc else None}
    return {"dir": str(d), "exact": exact, "status": r["status"], "configuration": r.get("configuration"),
            "straps": r.get("straps"), "binary_sha256": r.get("binary_sha256"), "result_sha256": sha(d / "result.json"),
            "x_checks": {k: v["mismatches"] for k, v in r["layer_x_checks"].items()},
            "kv_writeback_checks": r.get("token_kv_writeback_checks"), "writeback_drain": r.get("writeback_drain"),
            "stages": st}


def token(E, head, l0, steady):
    return 7 + E + (l0 - 1) + 35 * steady + (head - 1) + 37


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--iso", type=Path, required=True)
    ap.add_argument("--chained", type=Path, required=True)
    ap.add_argument("--base", type=Path)
    ap.add_argument("--realmem-iso", type=Path, required=True, help="REAL_MEM one-stack L0 at P8191 (realmem-ctx8k)")
    ap.add_argument("--realmem-chained", type=Path, help="REAL_MEM one-stack L0,L1,L2 at P8191 (if finished)")
    ap.add_argument("--ideal-iso", type=Path, required=True, help="KV_IDEAL L0 at P8191 (realmem-ctx8k)")
    ap.add_argument("--p255-summary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    p255 = json.loads(a.p255_summary.read_text())
    E, head = p255["per_layer_cycles"]["E"], p255["per_layer_cycles"]["head"]
    iso, ch = job(a.iso), job(a.chained)
    l0 = iso["stages"]["L0"]["cycles"]
    steady = [ch["stages"][n]["cycles"] for n in ("L1", "L2")]
    mean, mx = sum(steady) / 2, max(steady)
    tok, tok_max = token(E, head, l0, mean), token(E, head, l0, mx)
    rm, ide = job(a.realmem_iso), job(a.ideal_iso)
    rm_l0, ide_l0 = rm["stages"]["L0"]["cycles"], ide["stages"]["L0"]["cycles"]
    res = {
        "schema": "opentallas.qwen-rom-kv-fullbw.v1",
        "method": __doc__.split("\n\n", 1)[1].strip(),
        "position": 8191, "clock_ghz": HZ / 1e9, "peak_TBps_per_die": round(PEAK_BPS / 1e12, 3),
        "E_cycles_from_P255": E, "head_cycles_from_P255": head,
        "stream4": {
            "isolated_L0": iso, "chained_straps": ch,
            "per_layer_cycles": {"isolated_L0": l0, "chained": {n: ch["stages"][n]["cycles"] for n in ("L0", "L1", "L2")},
                                 "chained_steady_mean": mean, "chained_steady_max": mx},
            "token_cycles": round(tok), "token_cycles_max": tok_max,
            "token_us": round(tok / HZ * 1e6, 2), "tok_per_s": round(HZ / tok, 1), "tok_per_s_max_bound": round(HZ / tok_max, 1),
            "exact": iso["exact"] and ch["exact"]},
        "references": {
            "realmem_one_stack_isolated_L0": {"cycles": rm_l0, "exact": rm["exact"], "fill": rm["stages"]["L0"]["memory_die0"],
                                              "fill_TBps": rm["stages"]["L0"]["fill_TBps"],
                                              "fill_pct_of_4stack_peak": rm["stages"]["L0"]["fill_pct_of_peak"],
                                              "dir": rm["dir"], "result_sha256": rm["result_sha256"]},
            "kv_ideal_isolated_L0": {"cycles": ide_l0, "exact": ide["exact"], "dir": ide["dir"], "result_sha256": ide["result_sha256"]},
        },
    }
    s = res["stream4"]
    s["memory_term_isolated_L0"] = l0 - ide_l0
    s["memory_term_chained_steady_mean"] = mean - ide_l0
    s["isolated_L0_speedup_vs_realmem"] = round(rm_l0 / l0, 3)
    if a.base:
        b = job(a.base)
        bs = [b["stages"][n]["cycles"] for n in ("L1", "L2")]
        s["chained_no_straps"] = {"job": b, "cycles": {n: b["stages"][n]["cycles"] for n in ("L0", "L1", "L2")},
                                  "steady_mean": sum(bs) / 2, "token_cycles": round(token(E, head, l0, sum(bs) / 2))}
    if a.realmem_chained and (a.realmem_chained / "result.json").exists():
        rc = job(a.realmem_chained)
        rs = [rc["stages"][n]["cycles"] for n in ("L1", "L2")]
        tr = token(E, head, rm_l0, sum(rs) / 2)
        res["references"]["realmem_one_stack_chained"] = {"cycles": {n: rc["stages"][n]["cycles"] for n in ("L0", "L1", "L2")},
                                                           "exact": rc["exact"], "token_cycles": round(tr),
                                                           "tok_per_s": round(HZ / tr, 1), "dir": rc["dir"]}
        s["token_speedup_vs_realmem"] = round(tr / tok, 3)
    else:
        tr_iso = token(E, head, rm_l0, rm_l0 - 1)
        res["references"]["realmem_one_stack_token_isolated_lower_bound"] = {
            "token_cycles": round(tr_iso), "tok_per_s": round(HZ / tr_iso, 1),
            "note": "35 x (isolated L0 - 1): the REAL_MEM chained P8191 job had not finished; chained layers are slower (P255: +316..439)"}
        s["token_speedup_vs_realmem_isolated_bound"] = round(tr_iso / tok, 3)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in s.items() if k not in ("isolated_L0", "chained_straps", "chained_no_straps")}, indent=1))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("cycles", "fill_TBps", "fill_pct_of_4stack_peak", "token_cycles", "tok_per_s")}
                      for k, v in res["references"].items()}, indent=1))


if __name__ == "__main__":
    main()

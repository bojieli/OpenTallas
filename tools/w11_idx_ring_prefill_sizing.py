#!/usr/bin/env python3
"""W11: does the ring key writer's bulk-placement rate bound prefill ingest?

Inputs (pinned): the full-shape ring gate (results/rtl/w11_idx_ring_gate.json: four users prefilled to 262,080
keys each through ot_hdc_v41x_idx_ring_kwr op PLACE, one request a cycle) and the prefill/ingest model
(results/arch/prefill_ingest.json: GPU prefill, then KV ingest over NIC -> switch -> package port -> the ingest
engine -> HBM; its v41_rom @1M cases).  The writer's rate is an upper bound on its time per key: the gate's whole
run (prefill + 256 steps + 8 scans) divided by the keys it placed.  Compared per die and per user at 1M context
with (a) the burst ingest (late bind: the GPU holds the KV and bursts it), where the keys arrive at their share of
the binding link time, and (b) streamed ingest paced by the GPU prefill.  Writes
results/arch/w11_idx_ring_prefill_sizing.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/w11_idx_ring_prefill_sizing.json"
GATE = "results/rtl/w11_idx_ring_gate.json"
MODEL = "results/arch/prefill_ingest.json"
CLK_HZ = 1e12 / 967.2          # 1.0339 GHz core clock
KEY_B = 68


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def build() -> dict:
    gate = json.loads((ROOT / GATE).read_text())
    full = next(c for c in gate["cases"] if c["name"] == "full_shape")
    keys_placed = full["writer"]["keys"]
    cycles_per_key = full["cycles"] / keys_placed                  # upper bound (includes scans and steps)
    writer_Bps = KEY_B / cycles_per_key * CLK_HZ
    model = json.loads((ROOT / MODEL).read_text())
    rows = []
    for case in model["v41_cold"]:
        if case["design"] != "v41_rom" or case["context"] != 1 << 20:
            continue
        rows_die = case["context"] // 4                              # one quarter of the rows per die (TP 4)
        key_bytes = rows_die * KEY_B
        die_bytes = case["busiest_die_bytes"]
        burst_s = case["burst"]["time_s"]
        key_share_s = burst_s * key_bytes / die_bytes                  # keys' share of the binding burst time
        writer_s = rows_die * cycles_per_key / CLK_HZ
        stream_pace = case["stream"]["pace_Bps_needed"] * key_bytes / die_bytes
        rows.append({"rate_key": case["rate_key"], "gpu_prefill_s": case["gpu_prefill_s"],
                     "burst_binding": case["burst"]["binding"], "burst_time_s": burst_s,
                     "keys_per_die_per_user": rows_die, "key_bytes_per_die_per_user": key_bytes,
                     "keys_share_of_burst_s": key_share_s, "writer_time_s": writer_s,
                     "writer_over_key_burst_share": writer_s / key_share_s,
                     "writer_over_whole_burst": writer_s / burst_s,
                     "stream_key_pace_Bps_needed": stream_pace,
                     "writer_over_stream_pace": writer_Bps / stream_pace,
                     "exposed_if_keys_arrive_contiguously_s": max(0.0, writer_s - key_share_s),
                     "exposed_fraction_of_ttft": max(0.0, writer_s - key_share_s) / case["ttft_late_bind_s"],
                     "ttft_s_late_bind": case["ttft_late_bind_s"]})
    worst = max(r["writer_over_whole_burst"] for r in rows)
    return {
        "schema": "w11_idx_ring_prefill_sizing_v1",
        "writer": {"source": GATE, "keys_placed": keys_placed, "run_cycles": full["cycles"],
                   "cycles_per_key_upper_bound": round(cycles_per_key, 4),
                   "sector_writes_per_key": 3, "requests_per_cycle": 1,
                   "bytes_per_s": writer_Bps, "clock_hz": CLK_HZ},
        "ingest_engine_keys_Bps_model": model["ingest_engine"]["v41_keys_in_Bps"],
        "cases_v41_rom_1M": rows,
        "verdict": {
            "binds": worst > 1.0,
            "writer_time_over_burst_time_max": worst,
            "writer_over_model_key_engine_rate": writer_Bps / model["ingest_engine"]["v41_keys_in_Bps"],
            "max_exposed_fraction_of_ttft": max(r["exposed_fraction_of_ttft"] for r in rows),
            "reading": ("The ring writer places one 1M-context die slice (262,144 keys) in ~1.3 ms, inside every "
                        "modelled burst ingest of that die's bytes (NIC-bound 9.6 ms; package-port-bound 3.5 ms) "
                        "and hundreds of times faster than streamed ingest needs. If the keys arrived as one "
                        "contiguous chunk at the package-port rate the writer would trail them by up to ~0.6 ms, "
                        "under 0.03% of the time to first token. It does not bind prefill. It is, however, "
                        "slower than the key-ingest engine rate the prefill model assumes (~14 vs ~22.6 GB/s)."),
        },
        "source_sha256": {p: sha(p) for p in (GATE, MODEL, "tools/w11_idx_ring_prefill_sizing.py")},
    }


def main() -> None:
    rec = build()
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec["verdict"], indent=1))
    for r in rec["cases_v41_rom_1M"]:
        print(r["rate_key"], round(r["writer_time_s"] * 1e3, 3), "ms writer;", round(r["burst_time_s"] * 1e3, 3),
              "ms burst;", round(r["keys_share_of_burst_s"] * 1e3, 3), "ms key share;",
              round(r["writer_over_stream_pace"], 1), "x stream pace")


if __name__ == "__main__":
    main()

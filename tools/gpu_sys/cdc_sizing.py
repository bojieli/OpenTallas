#!/usr/bin/env python3
"""Analytical depth sizing of the asynchronous CDC FIFOs of the GPU-organised HBM comparator system.

The FIFO is rtl/gpu_sys/ot_gpu_cdc_fifo.sv over rtl/link/ot_link_afifo.sv (Gray pointers, SYNC-flop
synchronisers, full/empty decoded from the synchronised pointer, first-word fall-through head).

Slot round trip (worst phase).  A slot written at write edge t0 is reused only after
  1. the Gray write pointer, updated at t0, is captured by the first read edge strictly after t0 and
     reaches the end of the SYNC-flop chain at the SYNC-th read edge; empty is decoded from that register,
     so the pop is taken at read edge SYNC+1 at the latest: <= (SYNC + 1) * Tr after t0 (each read edge
     falls within one read period of the previous event, the first within (0, Tr]);
  2. the read pointer, updated at that pop edge, crosses back the same way: full is decoded from the
     SYNC-th write-domain synchroniser register, so the next push into the slot happens at write edge
     SYNC+1 at the latest: <= (SYNC + 1) * Tw after the pop.
Hence T_rt <= (SYNC + 1) * (Tw + Tr).  Each slot carries one entry per round trip, so the sustained rate
is min(1/Tw, 1/Tr, D / T_rt).  Sustaining r entries per slower-side cycle without bubbles needs
    D >= r * (SYNC + 1) * (Tw + Tr) / T_slow,
rounded up to a power of two 2^AW with AW >= 2 (the Gray full compare needs AW >= 2).  The mean-phase
round trip, (SYNC + 1/2) * (Tw + Tr), is also reported: it estimates the rate a too-shallow FIFO reaches
(D * T_slow / T_rt_mean), which the RTL bench measures for D = 4, 8, 16.

    python3 tools/gpu_sys/cdc_sizing.py               # JSON table on stdout
    python3 tools/gpu_sys/cdc_sizing.py --self-check  # analytical self-checks, exit status
"""
from __future__ import annotations

import argparse
import json
import math
import sys

SCHEMA = "opentallas.gpu_sys.cdc_sizing.v1"
SYNC_DEFAULT = 2

# Clock periods of the system top (ps), from the shared interface spec.
T_HOST, T_SM, T_MEM, T_LINK = 4000, 833, 1000, 900

NL = 16                                   # collective lanes
MREQ_W = 1 + 32 + 256 + 32 + 16           # we, addr, wdata, wstrb, tag = 337
MRSP_W = 16 + 1 + 256                     # tag, we, data = 273
COLL_REQ_W = NL * 32 + 1 + 8              # lanes + mode + count = 521
COLL_RSP_W = NL * 32                      # lanes = 512

# (name, write period, read period, entry width, required entries per slower-side cycle, note)
BOUNDARIES = [
    ("sm_to_mem_request", T_SM, T_MEM, MREQ_W, 1.0, "MREQ: we 1 + addr 32 + wdata 256 + wstrb 32 + tag 16"),
    ("mem_to_sm_response", T_MEM, T_SM, MRSP_W, 1.0, "MRSP: tag 16 + we 1 + data 256"),
    ("sm_to_link_collective", T_SM, T_LINK, COLL_REQ_W, 1.0, "16 lanes x 32 + mode 1 + count 8"),
    ("link_to_sm_collective", T_LINK, T_SM, COLL_RSP_W, 1.0, "16 lanes x 32"),
    ("host_to_sm_doorbell", T_HOST, T_SM, 32, 1.0, "32-bit doorbell / command word"),
    ("sm_to_host_completion", T_SM, T_HOST, 48, 1.0, "16-bit token tag + 32-bit RESULT payload"),
]

# Clock pairs the RTL bench measures (write ps, read ps).
BENCH_PAIRS = [(833, 1000), (1000, 833), (833, 900), (4000, 833), (833, 4000)]
BENCH_AWS = (2, 3, 4)
RATE_PASS = 0.99


def round_trip_ps(tw: float, tr: float, sync: int = SYNC_DEFAULT, worst: bool = True) -> float:
    k = (sync + 1) if worst else (sync + 0.5)
    return k * (tw + tr)


def min_depth(tw: float, tr: float, sync: int = SYNC_DEFAULT, rate: float = 1.0) -> tuple[int, int, float]:
    """(depth, AW, unrounded depth) sustaining `rate` entries per slower-side cycle at the worst phase."""
    t_slow = max(tw, tr)
    need = rate * round_trip_ps(tw, tr, sync) / t_slow
    aw = max(2, math.ceil(math.log2(max(need, 1.0)) - 1e-12))
    return 1 << aw, aw, need


def predicted_rate(tw: float, tr: float, depth: int, sync: int = SYNC_DEFAULT, worst: bool = False) -> float:
    """Entries per slower-side cycle with always-valid writer and always-ready reader."""
    t_slow = max(tw, tr)
    return min(1.0, depth * t_slow / round_trip_ps(tw, tr, sync, worst))


def fifo_bits(depth: int, width: int, aw: int, sync: int = SYNC_DEFAULT) -> int:
    """Storage + pointer flops: data, 2 x (bin, gray) pointers, 2 x SYNC synchroniser stages, wfreed/rbin_seen."""
    ptr = aw + 1
    return depth * width + 4 * ptr + 2 * sync * ptr + 2 * ptr + 1


def boundary_table(sync: int = SYNC_DEFAULT) -> list[dict]:
    rows = []
    for name, tw, tr, w, rate, note in BOUNDARIES:
        depth, aw, need = min_depth(tw, tr, sync, rate)
        rows.append({
            "boundary": name, "write_period_ps": tw, "read_period_ps": tr, "entry_width_bits": w,
            "width_note": note, "sync": sync, "required_entries_per_slow_cycle": rate,
            "round_trip_worst_ps": round_trip_ps(tw, tr, sync),
            "round_trip_mean_ps": round_trip_ps(tw, tr, sync, worst=False),
            "depth_needed_unrounded": round(need, 4), "depth": depth, "aw": aw,
            "flop_bits": fifo_bits(depth, w, aw, sync),
            "bandwidth_gbit_s": round(w * rate / max(tw, tr) * 1000, 3),
        })
    return rows


def bench_predictions(sync: int = SYNC_DEFAULT) -> list[dict]:
    out = []
    for tw, tr in BENCH_PAIRS:
        depth, aw, need = min_depth(tw, tr, sync)
        out.append({
            "write_period_ps": tw, "read_period_ps": tr, "predicted_depth": depth, "predicted_aw": aw,
            "depth_needed_unrounded": round(need, 4),
            "predicted_mean_rate": {str(1 << a): round(predicted_rate(tw, tr, 1 << a, sync), 4) for a in BENCH_AWS},
            "predicted_worst_rate": {str(1 << a): round(predicted_rate(tw, tr, 1 << a, sync, True), 4)
                                     for a in BENCH_AWS},
        })
    return out


# ---- full-shape ingress (restated finding, sizing-model output only) -----------------------------------------
SERVICE_CEILING_B_PER_CYCLE = 2763        # B/cycle/die at 1.2 GHz (hbm_bridge_dependency_and_fields.md s.3)
SM_INGEST_B_PER_CYCLE = 128 * 32          # 128 B/clk per SM (uarch_model.py:1599) x 32 SMs per die
PRICED_PAIRS, PRICED_W, PRICED_PAYLOAD_B = 32, 320, 32
SECTOR_B, HDR_BITS = 32, PRICED_W - 256   # one 32-byte sector + 64-bit header per priced entry


def full_shape(sync: int = SYNC_DEFAULT) -> dict:
    priced = PRICED_PAIRS * PRICED_PAYLOAD_B
    options = []
    # (label, write ps, read ps): async crossing inside the 1.2 GHz streaming domain (AGENTS.md clock domains),
    # and the system-top SM 833 ps -> mem 1000 ps crossing of this RTL.
    for label, tw, tr in (("sm_1200MHz_to_service_1200MHz", 833, 833), ("sm_833ps_to_mem_1000ps", 833, 1000)):
        t_slow = max(tw, tr)
        # bytes per slower-side cycle needed to carry the ceiling (defined per 833 ps cycle)
        need_b = SERVICE_CEILING_B_PER_CYCLE * t_slow / 833
        depth, aw, dneed = min_depth(tw, tr, sync)
        for k in (1, 2, 4):
            w = HDR_BITS + 256 * k
            pairs = math.ceil(need_b / (SECTOR_B * k))
            options.append({
                "crossing": label, "write_period_ps": tw, "read_period_ps": tr,
                "sectors_per_entry": k, "entry_width_bits": w, "pairs": pairs, "depth": depth, "aw": aw,
                "bytes_per_slow_cycle_needed": round(need_b, 1),
                "bytes_per_slow_cycle_carried": pairs * SECTOR_B * k,
                "flop_bits_per_die": pairs * fifo_bits(depth, w, aw, sync),
                "data_flop_bits_per_die": pairs * depth * w,
            })
    return {
        "label": "FULL-SHAPE SIZING MODEL OUTPUT -- NOT ADOPTED",
        "source": "/tmp/claude-review-20261003/hbm_bridge_dependency_and_fields.md section 3 (new finding)",
        "restated_finding": (
            "The priced ingress CDC is 32 pairs x 320 bits at one entry per cycle, carrying one 32-byte sector "
            "per pair: 1,024 B/cycle/die, which is 37% of the 2,763 B/cycle/die service ceiling and 25% of the "
            "32 x 128 B/clk SM ingest. It must be re-priced before W10."),
        "priced_bytes_per_cycle": priced,
        "service_ceiling_bytes_per_cycle": SERVICE_CEILING_B_PER_CYCLE,
        "priced_fraction_of_ceiling": round(priced / SERVICE_CEILING_B_PER_CYCLE, 4),
        "priced_fraction_of_sm_ingest": round(priced / SM_INGEST_B_PER_CYCLE, 4),
        "options": options,
    }


def table(sync: int = SYNC_DEFAULT) -> dict:
    return {
        "schema": SCHEMA, "sync": sync, "rate_pass_threshold": RATE_PASS,
        "model": "D >= r * (SYNC+1) * (Tw+Tr) / max(Tw,Tr), D = 2^AW, AW >= 2",
        "boundaries": boundary_table(sync), "bench_predictions": bench_predictions(sync),
        "full_shape_ingress": full_shape(sync),
    }


def self_check() -> list[str]:
    errs = []
    def want(cond, msg):
        if not cond:
            errs.append(msg)
    want(MREQ_W == 337 and MRSP_W == 273, "MREQ/MRSP widths")
    d, aw, need = min_depth(833, 1000)
    want((d, aw) == (8, 3) and abs(need - 5.499) < 1e-9, f"833/1000 depth {d} need {need}")
    want(min_depth(4000, 833)[0] == 4 and min_depth(833, 4000)[0] == 4, "host pair depth 4")
    want(min_depth(833, 833)[:2] == (8, 3), "same-period async depth 8 (need exactly 6)")
    want(min_depth(1000, 1000, sync=3)[0] == 8, "SYNC=3 equal periods: need 8 -> 8")
    want(min_depth(1000, 1000, sync=4)[0] == 16, "SYNC=4 equal periods: need 10 -> 16")
    for tw, tr in BENCH_PAIRS:
        dd, a, _ = min_depth(tw, tr)
        want(predicted_rate(tw, tr, dd, worst=True) >= 1.0, f"{tw}/{tr}: chosen depth sustains worst phase")
        if a > 2:
            want(predicted_rate(tw, tr, dd // 2) < RATE_PASS, f"{tw}/{tr}: half depth predicted short")
        want(min_depth(tw, tr) == min_depth(tr, tw), f"{tw}/{tr}: symmetric")
    fs = full_shape()
    want(fs["priced_bytes_per_cycle"] == 1024, "priced 1024 B/cycle")
    want(abs(fs["priced_fraction_of_ceiling"] - 0.3706) < 1e-3, "37% of ceiling")
    want(abs(fs["priced_fraction_of_sm_ingest"] - 0.25) < 1e-9, "25% of SM ingest")
    for o in fs["options"]:
        want(o["bytes_per_slow_cycle_carried"] >= o["bytes_per_slow_cycle_needed"], f"option carries {o}")
    one = [o for o in fs["options"] if o["crossing"].startswith("sm_1200") and o["sectors_per_entry"] == 1][0]
    want(one["pairs"] == 87, f"1-sector pairs at 1.2 GHz {one['pairs']} (86.3 beats/cycle)")
    for r in boundary_table():
        want(r["depth"] >= r["depth_needed_unrounded"] and r["depth"] >= 4, f"{r['boundary']} depth")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sync", type=int, default=SYNC_DEFAULT)
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    if a.self_check:
        errs = self_check()
        for e in errs:
            print("FAIL", e)
        print("CDC_SIZING SELF-CHECK", "FAIL" if errs else "PASS")
        return 1 if errs else 0
    json.dump(table(a.sync), sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

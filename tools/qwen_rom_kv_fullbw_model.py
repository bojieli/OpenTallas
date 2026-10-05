#!/usr/bin/env python3
"""Analytical model of the Qwen3-8B ROM full-bandwidth KV path (4 HBM3E stacks a die, STREAM4).

Sizes the path before/alongside the RTL (AGENTS.md design method): bytes per cycle at every port,
bits per cycle across every boundary, replica counts, and the per-layer / per-token latency
contribution at a context position P, with and without the cross-layer prefetch.  The measured RTL
numbers (tools/qwen_rom_kv_fullbw_collect.py) are compared against it.

Design point (tools/uarch_model.py QWEN_ROM_PRODUCT: k = 4 dies, stacks_per_die = 4):
  * per die NSTK = 4 HBM3E stacks x 32 pseudo-channels; the near-HBM stream controller
    (rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv) issues one 32-B RD per PC per controller cycle
    (HBM CK/2 = 1.024 ns), i.e. 1.0 TB/s a stack at 100 % column utilisation; the stream-aware
    REFpb costs ~4 % (0.958 TB/s a stack measured for the controller, tb_hbm_stream_bw);
  * FP8 KV, 2 KV heads a die (TP4 of 8), head_dim 128: 512 B a position a die a layer; the window of
    P is (P // 16 + 1) 16-position tiles of 256 sectors (8 KiB) each;
  * the core clock is 1.2 GHz (0.8333 ns); the stream lands into the tiles' KV slices
    (1,536 tiles x one 512-bit write a cycle).
"""
from __future__ import annotations

import argparse
import json

CORE_HZ = 1.2e9
CTL_NS = 1.024                 # controller clock (HBM CK/2)
SECTOR = 32                    # bytes
PCS_PER_STACK = 32
STACK_REF_EFF = 0.958          # measured sustained / peak of the stream controller, one stack
TILES = 1536
SLICE_WORD_BITS = 512


def window_sectors(P: int) -> int:
    return 256 * (P // 16 + 1)


def model(P: int, nstk: int = 4, layers: int = 36, attn_ideal: int | None = None) -> dict:
    pcs = nstk * PCS_PER_STACK
    peak_bps = pcs * SECTOR / (CTL_NS * 1e-9)                       # bytes/s a die
    peak_spc = peak_bps / CORE_HZ / SECTOR                          # sectors / core cycle
    sus_spc = peak_spc * STACK_REF_EFF
    sec = window_sectors(P)
    fill_peak = sec / peak_spc
    fill_sus = sec / sus_spc
    lat = 70                                                        # first-sector latency, core cycles (tRCD+CL+path+CDC)
    return {
        "P": P, "stacks_per_die": nstk, "pseudo_channels_per_die": pcs,
        "peak_TBps_per_die": round(peak_bps / 1e12, 3),
        "sustained_TBps_per_die_at_stack_eff": round(peak_bps * STACK_REF_EFF / 1e12, 3),
        "peak_sectors_per_core_cycle": round(peak_spc, 2),
        "target_90pct_sectors_per_core_cycle": round(0.9 * peak_spc, 2),
        "window": {"sectors": sec, "bytes": sec * SECTOR, "per_pc_sectors": sec // pcs},
        "fill_cycles": {"at_peak": round(fill_peak), "at_stack_eff": round(fill_sus), "plus_first_latency": round(fill_sus + lat)},
        "ports": {
            "controller_to_landing_bytes_per_ctl_cycle": pcs * SECTOR,
            "landing_to_slices_bytes_per_core_cycle": round(peak_spc * SECTOR, 1),
            "landing_bits_per_core_cycle": round(peak_spc * SECTOR * 8),
            "slice_write_capacity_bits_per_core_cycle": TILES * SLICE_WORD_BITS,
            "slice_writes_per_core_cycle_needed": f"{peak_spc:.0f} K-sector (1 write) .. {2 * peak_spc:.0f} V-sector (2 writes) of {TILES}",
            "landing_fifo": f"per PC CRED = 32 sectors (1 KiB), {pcs} KiB a die, crossing CK/2 -> core",
        },
        "replicas": {"stream_controllers": nstk, "pc_sequencers": pcs,
                     "note": "the routed one-stack controller (ot_hbm_r14_stream_stack) replicated per stack; one descriptor "
                             "broadcast, go to all; the landing adapter is per PC"},
        "per_layer": {
            "kv_fill_cycles_in_layer_without_prefetch": round(fill_sus + lat),
            "kv_fill_hidden_with_prefetch_if_mlp_window_ge": round(fill_sus + lat),
            "attention_ideal_cycles": attn_ideal,
        },
        "token": {"layers": layers,
                  "kv_bytes_per_token_per_die": sec * SECTOR * layers,
                  "kv_time_per_token_us_at_stack_eff": round(sec * SECTOR * layers / (peak_bps * STACK_REF_EFF) * 1e6, 2)},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--positions", default="255,1023,4095,8191")
    ap.add_argument("--stacks", default="1,4")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = {f"S{s}_P{p}": model(int(p), int(s)) for s in a.stacks.split(",") for p in a.positions.split(",")}
    txt = json.dumps(res, indent=1)
    if a.out:
        open(a.out, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()

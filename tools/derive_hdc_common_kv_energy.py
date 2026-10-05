#!/usr/bin/env python3
"""Normalize the reduced Qwen3 ROM/HBM energy comparison to one HBM KV path."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/physical_abi3/asap7/signoff/energy_per_token.json"
OUT = ROOT / "results/physical_abi3/asap7/signoff/energy_common_kv.json"


def derive() -> dict:
    source = json.loads(SOURCE.read_text())
    a = source["architectures"]
    rom = a["qwen3_8b_rom_reticle"]
    hbm = a["hbm_comparator"]
    kv_bytes = rom["memory"]["KV SRAM"]["bytes_per_token"]
    assert kv_bytes == hbm["memory"]["KV from HBM"]["bytes_per_token"]
    rom_total = rom["totals_j"]["token_TT"]
    sram_kv = rom["memory"]["KV SRAM"]["energy_j"]
    hbm_kv = hbm["memory"]["KV from HBM"]["energy_j"]
    streamer_logic = hbm["totals_j"]["logic_TT"] - rom["totals_j"]["logic_TT"]
    idle = hbm["static"]["HBM interface idle"]["energy_j"]
    adjusted = rom_total - sram_kv + hbm_kv + streamer_logic + idle
    comparator = hbm["totals_j"]["token_TT"]
    return {
        "schema": "hdc-common-hbm-kv-energy-v1",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "evidence": "derived: routed ASAP7 reduced-core activity plus modeled per-byte HBM KV and interface idle",
        "boundary": "same 263168-byte reduced Qwen3 KV step on both cores; neither result is full-size system energy",
        "common_kv_bytes": int(kv_bytes),
        "terms_j": {
            "rom_original": rom_total,
            "remove_rom_kv_sram": -sram_kv,
            "add_hbm_kv": hbm_kv,
            "add_shared_streamer_logic": streamer_logic,
            "add_hbm_interface_idle": idle,
        },
        "rom_common_hbm_kv_j": adjusted,
        "hbm_comparator_j": comparator,
        "hbm_over_rom": comparator / adjusted,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    result = derive()
    data = json.dumps(result, indent=2) + "\n"
    if args.check:
        assert OUT.exists() and OUT.read_text() == data, "common-KV energy snapshot drift"
    else:
        OUT.write_text(data)
    print(f"common-HBM-KV: ROM {result['rom_common_hbm_kv_j'] * 1e6:.6f} µJ; HBM {result['hbm_comparator_j'] * 1e6:.6f} µJ; ratio {result['hbm_over_rom']:.6f}×")


if __name__ == "__main__":
    main()

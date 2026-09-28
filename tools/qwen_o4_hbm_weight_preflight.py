#!/usr/bin/env python3
"""Source-pinned O4 INT8 weight-HBM layout and bandwidth boundary.

This is an address/traffic feasibility gate, not a token simulator.  It prices
the exact full-width words emitted by the adopted matrix tiling, including its
zero-padded lanes.  A small byte-level round trip checks that the HBM sectors
reconstruct the signed-code and BF16-scale ROM words without conversion.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import arch_budget_qwen3 as Q

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/qwen_o4_hbm_weight_preflight.json"
SECTOR_BYTES = 32
MATRIX_WORD_BYTES = Q.GROUPS_DIE * Q.W  # one signed INT8 code per lane
SCALE_WORD_BYTES = Q.GROUPS_DIE * Q.W * 2
_PINNED = (
    "tools/qwen_o4_hbm_weight_preflight.py",
    "tools/arch_budget_qwen3.py",
    "tools/hdc_qwen_int8_image.py",
    "rtl/hdc/ot_hdc_core_vector_weight.sv",
    "rtl/hdc/ot_hdc_matvec.sv",
    "rtl/hdc/hbm/ot_hdc_wstream.sv",
    "results/arch/qwen3_budget.json",
)


def sector_roundtrip() -> dict:
    """One core word and its scale word in little-endian lane order.

    The test includes both signed endpoints and nontrivial BF16 patterns.  It
    checks bytes, rather than an approximate floating-point comparison.
    """
    endpoints = bytes((0x80, 0xFF, 0x00, 0x01, 0x7F))
    code = (endpoints * math.ceil(MATRIX_WORD_BYTES / len(endpoints)))[:MATRIX_WORD_BYTES]
    scales = bytes((0x00, 0x3F, 0x80, 0x3F, 0x00, 0x40, 0x80, 0xBF))
    scale = (scales * math.ceil(SCALE_WORD_BYTES / len(scales)))[:SCALE_WORD_BYTES]
    def check(payload: bytes) -> dict:
        sectors = [payload[p:p + SECTOR_BYTES] for p in range(0, len(payload), SECTOR_BYTES)]
        assert all(len(s) == SECTOR_BYTES for s in sectors)
        assert b"".join(sectors) == payload
        return {"bytes": len(payload), "sectors": len(sectors), "sha256": hashlib.sha256(payload).hexdigest()}
    return {"code_word": check(code), "scale_word": check(scale),
            "code_endpoints": [int.from_bytes(bytes((x,)), "little", signed=True) for x in endpoints]}


def matrix_traffic(name: str, n: int, k: int, count: int = 1) -> dict:
    split, rounds, kc = Q.split_rounds(n, k, Q.GROUPS_DIE)
    word_cycles = rounds * kc * Q.IL
    useful = n * k * count
    streamed = word_cycles * MATRIX_WORD_BYTES * count
    scale_useful = n * 2 * count
    assert streamed >= useful and streamed % SECTOR_BYTES == 0
    return dict(name=name, rows_per_die=n, cols_per_die=k, count=count,
                k_split=split, rounds=rounds, k_per_chunk=kc,
                word_cycles=word_cycles * count,
                useful_code_bytes=useful, identical_rom_word_bytes=streamed,
                padding_bytes=streamed - useful, code_sectors=streamed // SECTOR_BYTES,
                useful_scale_bytes=scale_useful)


def evaluate() -> dict:
    assert (Q.DIES, Q.GROUPS_DIE, Q.W, Q.IL, Q.HBM["stacks"]) == (2, 6144, 16, 8, 8)
    per_layer, _ = Q.matrices()
    # Column-parallel qkv/gate_up, K-parallel o/down, row-parallel vocabulary.
    mats = []
    for name, (n, k) in per_layer.items():
        shape = (n // 2, k) if name in ("qkv", "gate_up") else (n, k // 2)
        mats.append(matrix_traffic(name, *shape, count=Q.Q["L"]))
    mats.append(matrix_traffic("lm_head", Q.Q["V"] // 2, Q.Q["H"]))
    useful = sum(m["useful_code_bytes"] for m in mats)
    streamed = sum(m["identical_rom_word_bytes"] for m in mats)
    scales = sum(m["useful_scale_bytes"] for m in mats)
    wl = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    model_weight = wl["workload"][str(Q.CTX_HEAD)]["weight_macs"]
    assert useful * Q.DIES == model_weight, (useful, model_weight)
    model = wl["hbm_comparator"][str(Q.CTX_HEAD)]["rom_format_int8"]
    kv_package = Q.kv_bytes(wl["workload"][str(Q.CTX_HEAD)], Q.KV_FMT_SPEC)
    # The modeled bytes are useful codes + per-MAC scale amortization + KV.
    assert abs(model["bytes_per_token"] - (model_weight * Q.hbm_weight_bytes_per_mac(Q.MATCHED_FMT)
                                              + kv_package)) < 1
    bw_die = Q.HBM["stacks_per_die"] * Q.HBM["stack_bytes_s"] * Q.HBM["efficiency"]
    clock = wl["clock_hz"] if "clock_hz" in wl else Q.CLOCK[0]
    code_cycles_lower = math.ceil(streamed / (bw_die / clock))
    bytes_per_cycle_die = bw_die / clock
    largest = max(mats, key=lambda m: m["word_cycles"] / m["count"])
    largest_words = largest["word_cycles"] // largest["count"]
    # A matvec consumes one full word/cycle once issued. Even if HBM delivers
    # continuously at the stated bandwidth, this many words must be ready
    # before the longest unchunked op to avoid an underflow. This excludes
    # HBM latency/refresh, so it is a lower bound on its buffer requirement.
    prefetched_words_min = max(0, largest_words - math.floor(
        largest_words * bytes_per_cycle_die / MATRIX_WORD_BYTES))
    model_scale = model_weight * (Q.hbm_weight_bytes_per_mac(Q.MATCHED_FMT) - 1)
    exact_weight_and_kv = Q.DIES * (streamed + scales) + kv_package
    package_extra = exact_weight_and_kv - model["bytes_per_token"]
    # Source residence includes every target/drafter tensor and the 8K KV;
    # 32-byte sector addresses are the existing controller's unit.
    cap = Q.rom_capacity()
    resident_pkg = sum(v["bytes"] for v in cap["rows"].values()) + kv_package
    resident_die = math.ceil(resident_pkg / Q.DIES)
    sector_addr_bits = math.ceil(math.log2(math.ceil(resident_die / SECTOR_BYTES)))
    stream_window_bytes = (1 << 11) * MATRIX_WORD_BYTES
    # A gate/up K round has 64*8 full-width words and cannot be divided by
    # the current ISA without changing the accumulator continuation. Price
    # its 512-word staging bank only as a sensitivity: the KV ring's modeled
    # density is a proxy, not a SRAM macro or routed result.
    round_window_words = 512
    round_window_bytes = round_window_words * MATRIX_WORD_BYTES
    round_stream_bytes_per_cycle = bw_die / clock
    round_prefetch_bytes_min = round_window_words * max(
        0, MATRIX_WORD_BYTES - round_stream_bytes_per_cycle)
    kv_buffer_bytes = wl["area"]["kv_prefetch_buffer_bytes"]
    kv_buffer_mm2 = wl["area"]["kv_prefetch_buffer_mm2"]
    round_window_proxy_mm2 = round_window_bytes / (kv_buffer_bytes / kv_buffer_mm2)
    # A token looks up one embedding row. Until the TP-2 row layout is
    # committed, use a conservative whole-hidden-row upper bound per die.
    embed_upper_package = Q.DIES * (Q.Q["H"] + 2)
    return {
        "schema": "opentallas.qwen-o4-hbm-weight-preflight.v1",
        "status": "pass",
        "claim_boundary": "Static full-shape INT8 code/scale address and traffic preflight plus byte-exact sector roundtrip; no O4 weight-HBM RTL, token bit-exactness, sustained controller measurement, full-die route, or throughput verdict.",
        "configuration": {"dies": Q.DIES, "groups_per_die": Q.GROUPS_DIE, "lanes_per_group": Q.W,
                          "int8_word_bytes": MATRIX_WORD_BYTES, "scale_word_bytes": SCALE_WORD_BYTES,
                          "hbm_stacks_per_die": Q.HBM["stacks_per_die"], "sector_bytes": SECTOR_BYTES},
        "matrix_traffic_per_die": mats,
        "ar_per_die": {"useful_code_bytes": useful, "rom_word_identical_code_bytes": streamed,
                       "padding_bytes": streamed - useful, "useful_scale_bytes": scales,
                       "code_sector_reads": streamed // SECTOR_BYTES,
                       "code_stream_cycles_lower_bound_at_stated_hbm_bw": code_cycles_lower},
        "package": {"modeled_weight_macs": model_weight,
                    "model_hbm_bytes_per_token_including_kv": model["bytes_per_token"],
                    "model_amortized_scale_bytes_per_token": model_scale,
                    "rom_word_identical_weight_and_kv_bytes_per_token": exact_weight_and_kv,
                    "delta_bytes_vs_model_if_fetching_identical_rom_words_and_scales": package_extra,
                    "bandwidth_only_upper_rate_for_identical_words_tokens_s":
                    Q.HBM["stacks"] * Q.HBM["stack_bytes_s"] * Q.HBM["efficiency"] / exact_weight_and_kv,
                    "resident_target_drafter_and_kv_bytes_lower_bound": resident_pkg,
                    "resident_bytes_per_die_even_partition_lower_bound": resident_die,
                    "minimum_sector_address_bits": sector_addr_bits},
        "existing_wstream_incompatibilities": {
            "weight_port": "BF16-only ot_hdc_core_whbm.wrom_q; O4 core has independent INT8 code and BF16 scale ports",
            "default_hbm_sector_address_bits": 24,
            "default_hbm_sector_address_bits_sufficient_for_resident_layout": sector_addr_bits <= 24,
            "default_window_bytes_if_scaled_to_full_o4_word": stream_window_bytes,
            "longest_unchunked_op": largest["name"],
            "longest_unchunked_op_words": largest_words,
            "minimum_prefetch_bytes_for_longest_unstalled_op_at_stated_hbm_bw":
            prefetched_words_min * MATRIX_WORD_BYTES,
            "default_burst_length_field_bits": 5,
            "sectors_per_o4_int8_word": MATRIX_WORD_BYTES // SECTOR_BYTES,
            "note": "A full-width 2048-word window would be 192 MiB per die, still below the longest unchunked op's required lead. Split the ISA weight op into bounded chunks or add an internal stall, then use PC-local sector windows and buffered scale words; a WB parameter change alone is not an implementation."},
        "staging_area_sensitivity": {
            "minimum_indivisible_gate_up_round_words": round_window_words,
            "code_window_bytes_per_die": round_window_bytes,
            "code_window_mib_per_die": round_window_bytes / (1024 * 1024),
            "sustained_hbm_bytes_per_core_cycle_per_die": round_stream_bytes_per_cycle,
            "core_code_bytes_per_cycle": MATRIX_WORD_BYTES,
            "minimum_starting_prefetch_mib_for_unstalled_round_with_perfect_streaming":
            round_prefetch_bytes_min / (1024 * 1024),
            "proxy_kv_buffer_bytes": kv_buffer_bytes,
            "proxy_kv_buffer_mm2": kv_buffer_mm2,
            "code_window_mm2_at_kv_buffer_density": round_window_proxy_mm2,
            "status": "conditional_unpriced",
            "boundary": "KV-buffer density is a budget proxy only. PC-local SRAM macro area, code/scale muxes, tag RAM, wiring, power and route are not measured; do not use the iso-area HBM headline as physically closed. Streaming within an uninterrupted K round saves little staging at this bandwidth. A substantially smaller buffer needs an exact FP32 accumulator continuation or a pipeline-wide stall, neither implemented."},
        "embedding_traffic_sensitivity": {
            "one_row_upper_bytes_per_die": Q.Q["H"] + 2,
            "package_upper_bytes_per_token": embed_upper_package,
            "fraction_of_rom_word_identical_weight_and_kv_traffic_upper":
            embed_upper_package / exact_weight_and_kv,
            "boundary": "Upper bound assumes a full hidden row on each TP-2 die. The exact row partition and HBM controller transaction count require the full-shape emitter; embedding bytes are excluded from the existing modeled matrix+KV rate."},
        "sector_roundtrip": sector_roundtrip(),
        "input_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in _PINNED},
    }


def main() -> None:
    r = evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print(f"{OUT}: {r['status']}; {r['package']['minimum_sector_address_bits']}-bit sector addresses needed")


if __name__ == "__main__":
    main()

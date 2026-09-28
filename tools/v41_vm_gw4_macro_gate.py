#!/usr/bin/env python3
"""Bound the full-shape GW4 vector-memory macro cost from the checked-in abstract.

This is an architecture calculation over an ASAP7 generated macro model, not
an integrated VM place-and-route or a measured silicon SRAM.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "ot_sram_1r1w_512x128_m4_r2c2"
MACRO = ROOT / "physical/asap7_memory_macros" / NAME / f"{NAME}.json"
OUTPUT = ROOT / "results/physical_abi3/asap7/chip/v41_vm_gw4_macro_gate.json"


def derive() -> dict:
    payload = MACRO.read_bytes()
    macro = json.loads(payload)
    resident_fp32_elements = 1 << 19
    word_bits = 512
    banks = 4
    macro_bits = 512 * 128
    width_macros = word_bits // 128
    words = resident_fp32_elements * 32 // word_bits
    words_per_bank = words // banks
    depth_macros = math.ceil(words_per_bank / 512)
    count = banks * width_macros * depth_macros
    tt = macro["timing"]["tt"]
    return {
        "scope": "macro-abstract capacity and one-read/one-write port lower bound; no integrated VM route",
        "source": {"path": str(MACRO.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest()},
        "geometry": {
            "resident_fp32_elements": resident_fp32_elements,
            "vm_words_64B": words,
            "banks": banks,
            "words_per_bank": words_per_bank,
            "macro_type": NAME,
            "macro_word_bits": 128,
            "macro_depth_words": 512,
            "macros_per_bank_width": width_macros,
            "macros_per_bank_depth": depth_macros,
            "macro_count": count,
            "macro_only_area_mm2": count * macro["area"]["macro_area_um2"] / 1e6,
        },
        "timing_energy_model_tt": {
            "macro_write_cycle_ps": tt["breakdown"]["write_cycle_ps"],
            "macro_read_cycle_ps": tt["breakdown"]["read_cycle_ps"],
            "macro_write_energy_fj": tt["write_energy_fj"],
            "four_64B_word_write_macro_energy_pj": banks * width_macros * tt["write_energy_fj"] / 1000,
        },
        "caveats": [
            "The macro compiler numbers are modeled abstracts, not routed SRAM transistor measurements.",
            "Area excludes depth-select logic, four-bank data rotation, placement channels, access wires and clock trees.",
            "The core has many more VM read/write ports than this one-read/one-write-per-bank collective slice; those remain unclosed.",
            "Blocking COLL makes core VM accesses idle during the gather; package-controller access must also be arbitrated.",
        ],
    }


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(derive(), indent=2, sort_keys=True) + "\n")
    print(OUTPUT.relative_to(ROOT))

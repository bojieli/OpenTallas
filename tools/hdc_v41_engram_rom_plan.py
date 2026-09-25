#!/usr/bin/env python3
"""Table-ROM organisation and area of the shipped DeepSeek-V4.1-Flash Engram.

The two Engram layers (1 and 14) each hold 24 hash columns.  Column c of a layer
indexes only [offset_c, offset_c + prime_c) of that layer's table, so the ROM is
BANKED BY COLUMN: 48 column banks, each prime_c (~16.0M) rows deep, addressed by
the residue.  A token reads exactly one row from every bank, so its 48 reads
never conflict and are issued together (rtl/hdc/v41/ot_hdc_engram_gather.sv).

Row: 256 E4M3 codes + 1 UE8M0 scale; the release packs it in 264 bytes
(metadata engram.row_bytes_packed), which is 2,112 bits = 33 macros x 64 bits
exactly and 8 gather beats x 264 bits.  Macro: 8,192 x 64 mask ROM, the
deepest ROMA instance and the one the model's rom.array_efficiency (0.52) is
taken at, so the model's density applies to exactly this macro.  A column bank
is ceil(prime / 8192) row groups of 33 macros; a read activates one row group
(33 macros, 2,112 bits into the bank's row register) and the row leaves over the
bank's gather port as 8 beats.

Area uses the analytical model's own density (src/opentallas/roofline.py
Technology.rom_bits_per_mm2 over configs/hardware/technology.json) at every
node it defines, and, for comparison, the Taalas HC1 whole-die envelope
(Llama-3.1-8B parameters x reference_parts.taalas_hc1.weight_bits_per_parameter
over its die area; self-reported part, assumed bits per parameter).
Writes results/rtl/hdc_v41_engram_rom_plan.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))
import hdc_v41_engram_shipped as ES  # noqa: E402
from opentallas.roofline import Technology  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_engram_rom_plan.json"
TECH = ROOT / "configs/hardware/technology.json"
MODEL = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
LLAMA = ROOT / "configs/models/anchors/llama-3.1-8b.json"
MACRO_ROWS, MACRO_BITS = 8192, 64


def plan() -> dict:
    t = ES.shipped_tables()
    meta = json.loads(MODEL.read_text())["metadata"]["engram"]
    tech = Technology.load(TECH)
    raw = json.loads(TECH.read_text())
    primes = [[int(p) for p in t.primes[li].reshape(-1)] for li in range(len(t.layer_ids))]
    rows = [sum(p) for p in primes]
    assert rows == meta["num_embeddings"] == ES.RELEASED_ROWS
    packed_bits = ES.PACKED_ROW_BYTES * 8
    min_bits = (ES.ROW_BYTES + 1) * 8
    assert packed_bits == 33 * MACRO_BITS == ES.BEATS * (8 * ES.BEAT_CODES + 8)
    macros_wide = packed_bits // MACRO_BITS
    groups = [[math.ceil(p / MACRO_ROWS) for p in lp] for lp in primes]
    n_groups = sum(map(sum, groups))
    macros = n_groups * macros_wide
    total_rows = sum(rows)
    bits = {"packed_264B": total_rows * packed_bits, "codes_and_scale_257B": total_rows * min_bits,
            "macro_capacity": macros * MACRO_ROWS * MACRO_BITS}
    col_bits = max(max(lp) for lp in primes) * packed_bits
    die = raw["reference_parts"]["taalas_hc1"]["die_area_mm2"]["value"]
    dens = {}
    for node in tech.node_names():
        d = tech.rom_bits_per_mm2(node).value
        dens[node] = {"rom_bits_per_mm2": d,
                      "area_mm2": {k: round(v / d, 1) for k, v in bits.items()},
                      "column_bank_mm2": round(col_bits / d, 1),
                      "column_banks_per_reticle_die": int(die // (col_bits / d)),
                      "reticle_dies_one_column_each": 48 if col_bits / d <= die else None}
    llama = json.loads(LLAMA.read_text())["total_parameters"]
    wbits = raw["reference_parts"]["taalas_hc1"]["weight_bits_per_parameter"]["value"]
    hc1 = llama * wbits / die
    per_token = 48 * ES.PACKED_ROW_BYTES
    assert per_token == meta["lookup_bytes_per_token"]
    ej = raw["energy"]["rom_read_j_per_byte"]["value"]
    return {
        "schema": "opentallas.hdc-v41-engram-rom-plan.v1",
        "claim_boundary": "arithmetic on the released table extents and the analytical model's ROM density; "
                          "no ROM macro was compiled or placed",
        "tables": {"layers": list(t.layer_ids), "rows_per_layer": rows, "released_rows": ES.RELEASED_ROWS,
                   "columns_per_layer": len(primes[0]), "column_rows_min": min(map(min, primes)),
                   "column_rows_max": max(map(max, primes)),
                   "row": {"codes": ES.ROW_BYTES, "code_format": "E4M3 (E4M3fn)", "scale": "1 byte UE8M0",
                           "packed_bytes": ES.PACKED_ROW_BYTES, "stored_bits": packed_bits}},
        "organisation": {
            "banking": "by hash column: 48 column banks (24 per layer), bank b = layer*24 + column holds that "
                       "column's prime-sized region and is addressed by the residue; one row per bank per "
                       "token, so the 48 reads of a token are conflict free and issue in one cycle",
            "macro": {"rows": MACRO_ROWS, "bits": MACRO_BITS,
                      "why": "the deepest ROMA instance, the one rom.array_efficiency 0.52 is taken at"},
            "row_group_macros": macros_wide,
            "row_groups_per_bank": {"min": min(map(min, groups)), "max": max(map(max, groups))},
            "row_groups_total": n_groups, "macros_total": macros,
            "read": "one row group (33 macros) per read -> 2,112-bit row register -> 8 gather beats",
            "gather_port": {"beat_bits": 264, "beats_per_row": ES.BEATS,
                            "beat_layout": "[255:0] 32 E4M3 codes, [263:256] side byte = scale on beat 0",
                            "response_ports": "one per layer in ot_hdc_engram_gather (24 banks round-robin), "
                                              "one beat per cycle, 192 beats per layer per token"},
            "prefetch_buffer": {"slots": 2, "bytes_per_slot": 2 * 24 * 256 * 2,
                                "bytes_total": 2 * 2 * 24 * 256 * 2, "word_bits": 512,
                                "why": "BF16 rows of token t are read by layers 1 and 14 while token t+1's are "
                                       "fetched"},
            "bytes_read_per_token": per_token,
            "read_energy_j_per_token": per_token * ej,
            "read_energy_basis": "energy.rom_read_j_per_byte (assumed) x bytes per token",
        },
        "area": {"bits": bits, "by_node": dens,
                 "hc1_envelope": {"bits_per_mm2": hc1,
                                  "basis": f"Llama-3.1-8B {llama:.0f} parameters x {wbits} bits "
                                           f"(assumed) / {die} mm2 (HC1, self-reported)",
                                  "area_mm2": {k: round(v / hc1, 1) for k, v in bits.items()}},
                 "reticle_die_mm2": die},
        "placement": "a column bank is 450-580 mm2 at the model's N5-N7 density, so each fits one reticle-class "
                     "die and no two do: the Engram ROM is 48 column dies (24 per layer) or the equivalent "
                     "wafer region, each answering one 4-byte request with one 264-byte row per token",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    rec = plan()
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v["area_mm2"] for k, v in rec["area"]["by_node"].items()}),
          rec["area"]["hc1_envelope"]["area_mm2"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

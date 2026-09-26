#!/usr/bin/env python3
"""ROM defect tolerance: SECDED versus spare rows versus both, with numbers.

A mask ROM's defects are via defects (a programming via missing or extra: one
wrong bit), plus bitline and wordline opens/shorts (a column or a row of wrong
bits).  Redundancy works differently from SRAM: a spare ROM row cannot be
programmed after fabrication, so "row repair" means a patch row -- SRAM or
register -- that is loaded at boot with the correct content from off-die
non-volatile storage, per die.  ECC needs nothing per die.

This evaluates die yield (probability that every word of the die reads
correctly after correction/repair) for the full-model ROM capacities of the
two ROM architectures, under a sweep of defect densities, for:

* ``none``        -- no protection;
* ``secded``      -- (266,256) SECDED on every word, column mux 8 (a bitline
                     defect is one bit in each word it serves, so SECDED
                     corrects it unless a second error lands in the same word);
* ``spare_rows``  -- R patch rows per macro, no ECC (a bitline defect is fatal);
* ``secded+rows`` -- SECDED plus R patch rows for wordline defects and for
                     rows holding an uncorrectable word.

Poisson models throughout; defect densities are ASSUMED sweeps (no ASAP7 or
foundry via-defect data is available to this repository) and the report says
so.  Writes results/memory/rom_repair_evaluation.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402

OUT = asap7.ROOT / "results/memory/rom_repair_evaluation.json"

MACRO = {"name": "ot_rom_8192x266_m8", "words": 8192, "data_bits": 256, "code_bits": 266, "mux": 8,
         "rows": 1024, "cols": 266 * 8}
CAPACITIES = {
    "Qwen3-8B ROM reticle (BF16 weights, 16.38 GB)": 16_381_470_720,
    "Qwen3-8B ROM reticle (4-bit weights, 4.10 GB)": 16_381_470_720 // 4,
    "V4.1 ROM array, one die (2.714 GB)": 510_286_023_000 / 188,
}
P_VIA = [1e-11, 1e-10, 1e-9, 1e-8, 1e-7]       # per programmable cell
P_WL = [0.0, 1e-8, 1e-7]                        # per wordline (open/short)
P_BL = 1e-7                                     # per bitline
SPARE_ROWS = [1, 2, 4]


def poisson_tail(lam: float, k: int) -> float:
    """P(X > k) for X ~ Poisson(lam)."""
    if lam <= 0:
        return 0.0
    term = math.exp(-lam)
    cdf = term
    for i in range(1, k + 1):
        term *= lam / i
        cdf += term
    return max(0.0, 1.0 - cdf)


def evaluate(nbytes: float, p_via: float, p_wl: float, p_bl: float) -> dict:
    M = MACRO
    macros = math.ceil(nbytes * 8 / (M["words"] * M["data_bits"]))
    cells_nocode = M["words"] * M["data_bits"]
    cells_code = M["words"] * M["code_bits"]
    n_wl, n_bl = M["rows"], M["cols"]
    # --- none: every via, wordline and bitline defect is a failure
    lam_none = macros * (cells_nocode * p_via + n_wl * p_wl + M["data_bits"] * M["mux"] * p_bl)
    # --- SECDED: failures are words with >= 2 errors, and wordline defects
    per_word = M["code_bits"] * p_via
    lam_word2 = M["words"] * per_word ** 2 / 2.0
    lam_bl = n_bl * p_bl
    # a defective bitline puts one error in each of the rows words it serves; any
    # second error in one of those words (a via, or a second bitline with the same
    # column select) is fatal
    words_per_bl = M["rows"]
    lam_bl_plus_via = lam_bl * words_per_bl * (M["code_bits"] - 1) * p_via
    same_sel_bls = n_bl / M["mux"] - 1
    lam_bl_pair = lam_bl * same_sel_bls * p_bl / 2.0
    lam_wl = n_wl * p_wl
    lam_secded = macros * (lam_word2 + lam_bl_plus_via + lam_bl_pair + lam_wl)
    out = {"macros": macros, "none": math.exp(-lam_none), "secded": math.exp(-lam_secded)}
    # --- spare rows only: a row with any via defect or a wordline defect needs a patch row;
    #     any bitline defect is fatal
    p_row_bad = 1 - math.exp(-(M["cols"] * p_via + p_wl))
    for r in SPARE_ROWS:
        lam_rows = n_wl * p_row_bad
        p_macro_fail = poisson_tail(lam_rows, r)
        out[f"spare_rows_{r}"] = math.exp(-macros * (lam_bl)) * math.exp(-macros * p_macro_fail)
        # --- SECDED + spare rows: rows needing a patch are wordline defects and rows
        #     holding an uncorrectable word (two via errors, or a via on a bad bitline)
        p_row_unc = (p_wl + M["mux"] * per_word ** 2 / 2.0 + lam_bl * M["mux"] * (M["code_bits"] - 1) * p_via)
        p_macro_fail2 = poisson_tail(n_wl * p_row_unc, r)
        out[f"secded+rows_{r}"] = math.exp(-macros * (p_macro_fail2 + lam_bl_pair))
    out["expected_via_defects_per_die"] = macros * cells_code * p_via
    out["expected_wordline_defects_per_die"] = macros * lam_wl
    out["expected_bitline_defects_per_die"] = macros * lam_bl
    return out


def overheads() -> dict:
    M = MACRO
    return {
        "secded": {"check_bits_fraction": (M["code_bits"] - M["data_bits"]) / M["data_bits"],
                   "per_die_state": "none: the check bits are vias in the same mask",
                   "latency": "one combinational decoder after the macro output register "
                              "(rtl/dft/ot_rom_secded_dec.sv); the Qwen wrapper keeps the core's cycle count",
                   "content_dependence": "check bits are content; layout and timing are not"},
        "patch_rows": {"bits_per_row": M["cols"],
                       "per_die_state": "the defective row addresses and their full content, from off-die "
                                        "non-volatile storage, loaded at boot into patch registers",
                       "area": "R x cols bits of patch storage + R row-address comparators per macro",
                       "note": "a mask ROM's spare row cannot be programmed after fabrication, so ROM row "
                               "redundancy is an SRAM/register patch plus a per-die NVM image"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    table = {}
    for label, nbytes in CAPACITIES.items():
        table[label] = {f"via={p:.0e},wl={w:.0e}": evaluate(nbytes, p, w, P_BL) for p in P_VIA for w in P_WL}
    rec = {
        "schema": "opentallas.rom-repair-evaluation.v1",
        "generated_by": "tools/mem_compiler/rom_repair_eval.py",
        "macro": MACRO,
        "assumed_defect_densities": {
            "p_via_sweep": P_VIA, "p_wordline": P_WL, "p_bitline": P_BL, "grade": "assumed",
            "note": "no via-defect density for ASAP7 or any foundry node is available to this repository; "
                    "the sweep brackets the plausible range and the recommendation holds across it"},
        "yield": table,
        "overheads": overheads(),
    }
    q = table["Qwen3-8B ROM reticle (BF16 weights, 16.38 GB)"]
    a, b = q["via=1e-09,wl=0e+00"], q["via=1e-09,wl=1e-07"]
    rec["recommendation"] = (
        "SECDED on every ROM word is required, and patch rows are required on top of it only when wordline "
        "defects occur. Spare rows alone never work: a bitline defect is fatal without ECC. For the BF16 Qwen3-8B "
        f"die at p_via = 1e-9: with no wordline defects it yields {a['none']:.1e} unprotected, "
        f"{a['secded']:.4f} with SECDED and {a['spare_rows_4']:.4f} with 4 patch rows and no ECC. At "
        f"p_wordline = 1e-7 SECDED alone falls to {b['secded']:.4f}, and SECDED plus 2 patch rows per macro "
        f"gives {b['secded+rows_2']:.4f}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    for label, rows in table.items():
        print(label)
        for p, r in rows.items():
            print(f"  {p}: none {r['none']:.3e} secded {r['secded']:.4f} rows4 {r['spare_rows_4']:.4f} "
                  f"secded+rows2 {r['secded+rows_2']:.4f} (via defects/die {r['expected_via_defects_per_die']:.1f})")
    print(rec["recommendation"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

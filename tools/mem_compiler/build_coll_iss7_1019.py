#!/usr/bin/env python3
"""HBM-COLLQ3-V7 (10-19): metadata macro of the 128-row COLL issuer v7 (ot_hgi_coll_static_issuer_v7_r128).

LEAD3-HBM decision (SAFE-DESIGN item 5): the 128-row issuer's 16 kb of runtime-indexed flop loop tables (v6 meta 128x64,
rowloops 128x32, rowcm1 128x32) move into SRAM. The 256-row v7 core keeps four metadata copies in ot_sram_1rw_256x64_m4_r2c2
(6.5 pins/um); at 128 rows that macro would carry a constant address MSB with half its rows unused, so this builds the
exact 128-word sibling with the QW-SRAM3 / COLL safe-pins recipe (tools/mem_compiler/build_qw_p192_1019.py, bb61ae67c):
0.192 um pin pitch (<= 5.21 pins/um), H = 24 mod 48 nm (M4 centres on track in R0/MX/MY/R180), core array, spare rows /
columns, ports, behaviour and operation latency unchanged; the Liberty adds the M4 lead RC (macro height - core height)
to clk->q / setup / min period / slew / pin and clock cap / energy.

    ot_sram_1rw_128x64_m2_r2c2_p192_mir  -> physical/asap7_memory_macros/<name>/

The data stack uses the existing ot_sram_1r1w_128x256_m1_r2c2_p192_mir (same recipe). Existing macros and index.json are
untouched (kits name the view directory explicitly). Analytical abstract only (no transistor layout, not silicon).

    python3 tools/mem_compiler/build_coll_iss7_1019.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asap7  # noqa: E402
import build_qw_p192_1019 as Q  # noqa: E402
import sram_gen as S  # noqa: E402

ROOT = HERE.parents[1]
MACROS = [  # name, words, bits, mux, spare rows, spare cols, unstretched sibling
    ("ot_sram_1rw_128x64_m2_r2c2_p192_mir", 128, 64, 2, 2, 2, "ot_sram_1rw_256x64_m4_r2c2 (256-row v7 metadata copy)"),
]


def main() -> int:
    asap7.METAL["pin_pitch_um"] = 0.192
    S.timing_model = Q.pin_access_timing
    S.macro_outline = Q.mirror_outline
    out = ROOT / "physical/asap7_memory_macros"
    for name, words, bits, mux, sr, sc, sib in MACROS:
        if (out / name).exists():
            raise SystemExit(f"{name} exists: macro views are written once")
        sheet = S.compile_macro(S.SramSpec(name, words, bits, mux, 1, "1rw", sr, sc), out)
        sheet["pin_access_contract"] = dict(
            pitch_um=0.192, max_density_per_um=1 / 0.192,
            exact_lead_um=sheet["area"]["macro_height_um"] - sheet["area"]["core_height_um"],
            timing="as build_qw_p192_1019.py: M4 lead Elmore 0.38RC + worst inv4/output-driver R*C on clk->q/setup/slew, "
                   "2x on min period; pin/clock cap and read/write energy recomputed; min hold unchanged (conservative)",
            sibling=sib, generator="tools/mem_compiler/build_coll_iss7_1019.py",
            recipe="tools/mem_compiler/build_qw_p192_1019.py (bb61ae67c build_coll_safe_pins_1019.py)",
            claim="Calibrated analytical abstract; no transistor layout or silicon; route access is qualified only by "
                  "the consuming tile gate/route")
        (out / name / (name + ".json")).write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
        a = sheet["area"]
        print(name, "W", a["macro_width_um"], "H", a["macro_height_um"], "pins/edge", a["outline"]["pins_per_edge"],
              "tt cq", round(sheet["timing"]["tt"]["clk_to_q_ps"], 1), "ss cq", round(sheet["timing"]["ss"]["clk_to_q_ps"], 1),
              "tt minper", round(sheet["timing"]["tt"]["min_period_ps"], 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

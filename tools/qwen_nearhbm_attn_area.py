#!/usr/bin/env python3
"""Area of the full near-HBM attention instance (Qwen3-8B ROM die, TP4: 4 stacks + hub) from SYNTHESISED cell area.

    python3 tools/qwen_nearhbm_attn_area.py --ss DIR_OF_SCREENS --r 6 --out results/.../area_estimate.json

Inputs are the pre-layout SS screens' Yosys synth_stat.txt (ORFS asap7, ABC speed script, adder map off): the row
engine (HD 128: 512 product units, 512 lane adders, 252 score-tree adders, 4 scale multipliers, control, a DQ-row
FIFO), the hub, and the unit tops (ot_hdc_fp32_add_lat7, ot_hdc_fp32_mul_lat6, ot_hdc_exp_q, ot_qwen_nearhbm_prod).
Blocks without their own screen are composed from those unit areas and counted flip-flops (FF_UM2 per bit, the
synthesised asap7 DFF area), each line stating its basis.  Memories use the repo's SRAM macro (ot_sram_1r1w_1024x256).
Pre-layout cell area only: no placement utilisation, clock tree, power grid or repeaters.
"""
import argparse
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def chip_area(screen_dir):
    for p in Path(screen_dir).glob("reports/asap7/*/base/synth_stat.txt"):
        m = re.findall(r"Chip area for (?:top )?module '\\?([^']+)': ([0-9.]+)", p.read_text())
        if m:
            return float(m[-1][1])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ss", type=Path, required=True)
    ap.add_argument("--r", type=int, default=6)
    ap.add_argument("--hd", type=int, default=128)
    ap.add_argument("--engine", default="row_engine", help="screen dir of the row engine")
    ap.add_argument("--engine-hd", type=int, default=128)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    HD, R, LN = a.hd, a.r, 4 * a.hd
    u = {k: chip_area(a.ss / k) for k in ("add7", "mul6", "exp_q", "recip_q", "prod", a.engine, "hub")}
    macros = json.loads((ROOT / "physical/asap7_memory_macros/index.json").read_text())["macros"]
    sram = macros["ot_sram_1r1w_1024x256_m2_r2c2"]
    p7 = json.loads((ROOT / "results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json").read_text())
    FF_UM2 = p7["cells"]["ASR_area_um2"] + p7["cells"]["INV_area_um2"]     # the model's register bit (0.42282 um2)
    eng = u[a.engine]
    eng_basis = "synthesised row engine"
    if a.engine_hd != HD:      # scale the per-lane part of a reduced-HD engine to HD
        lane = u["prod"] + u["add7"] + 32 * FF_UM2
        tree = (a.engine_hd // 2 - 1) * u["add7"]
        tree_full = (HD // 2 - 1) * u["add7"]
        eng = eng + (HD - a.engine_hd) * 4 * lane + 4 * (tree_full - tree)
        eng_basis = f"synthesised HD={a.engine_hd} engine + {HD - a.engine_hd}x4 lanes (prod + add7 + pad) + tree adders"
    stack = dict(
        row_engines=dict(n=R, um2=R * eng, basis=eng_basis + " (DQ = 8 row FIFO in flops)"),
        row_fifo_to_dq32=dict(um2=R * 24 * HD * 8 * FF_UM2, basis="24 more 1,024-b FIFO rows per engine for DQ = 32 (flops)"),
        exp_quads=dict(n=R, um2=R * 4 * (2 * u["add7"] + u["exp_q"]) + R * 4 * 32 * 9 * FF_UM2,
                       basis="4 x (sub add7 + exp_q + Z chain add7) + tag / pad flops"),
        pv_tree=dict(um2=LN * u["add7"] + (7 + 1) * LN * 32 * FF_UM2 + R * LN * 32 * 0.12,
                     basis=f"{LN} add7 bank + 7 pending + root registers ({8 * LN * 32} b) + an R:1 leaf mux (0.12 um2/bit/input)"),
        z_tree=dict(um2=16 * u["add7"] + (2048 + 1024) * 32 * FF_UM2, basis="16 add7 + chunk / work registers (96 kb)"),
        score_and_e_memories=dict(n_macros=6, um2=6 * sram["area_um2"],
                                  basis="score 4096 x 128 b + e 4096 x 64 b in ot_sram_1r1w_1024x256 (4 + 2: R reads and "
                                        "R writes a cycle need the bandwidth, as the pricing's 4 score macros)"),
        q_registers=dict(um2=8 * HD * 16 * FF_UM2, basis="8 x 128 BF16"),
    )
    stack_um2 = sum(v["um2"] for v in stack.values())
    hub = dict(um2=u["hub"], basis="synthesised hub (P.V beat buffer 128 kb in flops)")
    die_um2 = 4 * stack_um2 + hub["um2"]
    rec = dict(schema="qwen-nearhbm-attn-area.v1", hd=HD, row_engines_per_stack=R, lanes_per_stack=R * LN,
               units_synth_um2=u, ff_um2_per_bit=FF_UM2, sram_macro=dict(name="ot_sram_1r1w_1024x256_m2_r2c2",
               area_um2=sram["area_um2"], capacity_bits=sram["capacity_bits"]),
               per_stack=stack, per_stack_mm2=round(stack_um2 / 1e6, 3), hub=hub,
               die_mm2=round(die_um2 / 1e6, 3),
               pricing_r1_added_mm2=[13.85, 15.81],
               caveat="pre-layout synthesised cell area (no utilisation, CTS, PDN, repeaters); the stack blocks other "
                      "than the row engine are composed from synthesised unit areas")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict(per_stack_mm2=rec["per_stack_mm2"], die_mm2=rec["die_mm2"], units=u), indent=1))


if __name__ == "__main__":
    main()

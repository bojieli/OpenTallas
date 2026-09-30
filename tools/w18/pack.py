#!/usr/bin/env python3
"""W18: the V4.1 ROM layer-die pack (W1 generator, W10 re-fit mode) with a chosen HBM PHY abstract.

W1's generator hard-codes the v1 PHY view (``ot_hbm3e_phy_v41x_aw30``, pins off track, PDN-0006).  This
driver swaps in a legal v2 view (tools/mem_compiler/hbm_phy_gen.py --variant v41x_legal) and then runs W10's
re-fit unchanged, so the record differs from W10's only by the PHY.

    python3 tools/w18/pack.py --hbm-phy ot_hbm3e_phy_v41x_aw30_e8p5 \
        --q-pair results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json \
        --bf-pair results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json \
        --output results/floorplan/v41_pack_refit_w18_e8p5.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_pack as PK  # noqa: E402
import v41_floorplan_refit as RF  # noqa: E402


def use_phy(name: str) -> None:
    if not (PK.MACRO_DIR / name / f"{name}.lef").exists():
        raise SystemExit(f"no PHY view {name} under {PK.MACRO_DIR}")
    PK.HBM_PHY = name


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--hbm-phy", required=True)
    ap.add_argument("--die-w-um", type=float, default=0.0, help="shrink/grow the die (snapped to the joint grid)")
    ap.add_argument("--die-h-um", type=float, default=0.0)
    a, rest = ap.parse_known_args(argv)
    use_phy(a.hbm_phy)
    if a.die_w_um:
        PK.DIE_W = int(a.die_w_um / PK.X_STEP) * PK.X_STEP
    if a.die_h_um:
        PK.DIE_H = int(a.die_h_um / PK.Y_STEP) * PK.Y_STEP
    RF.main(rest)


if __name__ == "__main__":
    main()

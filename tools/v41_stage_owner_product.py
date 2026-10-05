#!/usr/bin/env python3
"""The V4.1 ROM PRODUCT's layer-to-stage owner file (W16), in results/arch/v41_stage_owner_preflight.json's schema.

    python3 tools/v41_stage_owner_product.py [--stages 42] [--out results/arch/v41_stage_owner_product.json]

The 40 layers' checkpoint bytes are cut into S equal-byte TP-4 stages, each cut at a whole routed-expert ID (a
dense tensor is never cut), as tools/v41_stage_owner_preflight.py does for the 28-stage placement.  S defaults to the
product's stage count from tools/uarch_model.py's consolidation fit (BF16 columns at W10b's 510.84 x 126.9 um q tile
and 1,002.89 x 142.56 um column outline, the product's measured SU+VM hub block (C_rotate), 4096m8, storage-only density, 12.5% overhead, ring credit).  Headroom is against that fit's per-die field capacity;
Engram spill is 0 (the product's 36 table dies hold every table row).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as U  # noqa: E402

OUT = ROOT / "results/arch/v41_stage_owner_product.json"
PRODUCT = dict(bf16="columns", pitch=U.PRODUCT_PITCH, depth="4096m8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(S=None):
    S = S or U.cons_min_stages("analytical", U.CONS["overhead"], "ring", U.PRODUCT_GEOM, PRODUCT["pitch"],
                               PRODUCT["bf16"], PRODUCT["depth"])
    cfg = U._V41_CFG
    dense, routed = cfg["layer_dense_weight_bytes"], cfg["layer_routed_weight_bytes"]
    n_exp = 384
    sizes = [a + b for a, b in zip(dense, routed)]
    sb = sum(sizes) / S
    start, cuts, owners, delta = 0.0, [], [], [0.0] * S
    for L, size in enumerate(sizes):
        end = start + size
        crossed = [s for s in range(1, S) if start < s * sb < end]
        assert len(crossed) <= 1, f"layer {L} crosses more than one stage cut"
        home = int(start // sb)
        if crossed:
            nxt = crossed[0]
            cut_b = nxt * sb - start
            if cut_b <= dense[L] and dense[L] - cut_b < cut_b:
                # the equal-byte cut falls in the later part of the layer's dense tensors, which are never cut: the
                # dense tensors stay on the earlier stage and every routed expert moves on (an expert cut at 0), the
                # smaller of the two shifts
                extra = dense[L] - cut_b
                delta[home] += extra
                delta[nxt] -= extra
                cuts.append(dict(layer=L, from_stage=home, to_stage=nxt, fluid_expert_cut=None,
                                 integer_expert_cut=0, earlier_expert_ids=None, later_expert_ids=[0, n_exp - 1],
                                 earlier_stage_added_bytes=extra,
                                 note="cut inside the dense tensors, past their midpoint: the dense tensors stay on "
                                      "the earlier stage, every routed expert moves to the later stage"))
                owners.append(dict(layer=L, dense_owner_stage=home,
                                   routed_expert_candidate_owners=[dict(stage=nxt, expert_ids=[0, n_exp - 1])]))
                start = end
                continue
            if cut_b <= dense[L]:
                # the equal-byte cut falls in the earlier part of the layer's dense tensors, which are never cut: the
                # whole layer moves to the next stage (its dense bytes before the cut shift there)
                delta[home] -= cut_b
                delta[nxt] += cut_b
                cuts.append(dict(layer=L, from_stage=home, to_stage=nxt, fluid_expert_cut=None,
                                 integer_expert_cut=0, earlier_expert_ids=None, later_expert_ids=[0, n_exp - 1],
                                 earlier_stage_added_bytes=-cut_b,
                                 note="cut inside the dense tensors: the whole layer moves to the later stage"))
                owners.append(dict(layer=L, dense_owner_stage=nxt,
                                   routed_expert_candidate_owners=[dict(stage=nxt, expert_ids=[0, n_exp - 1])]))
                start = end
                continue
            frac = (cut_b - dense[L]) / (routed[L] / n_exp)
            k = math.ceil(frac)
            assert 0 < k < n_exp
            extra = (k - frac) * routed[L] / n_exp
            delta[home] += extra
            delta[nxt] -= extra
            cuts.append(dict(layer=L, from_stage=home, to_stage=nxt, fluid_expert_cut=frac, integer_expert_cut=k,
                             earlier_expert_ids=[0, k - 1], later_expert_ids=[k, n_exp - 1],
                             earlier_stage_added_bytes=extra))
            parts = [dict(stage=home, expert_ids=[0, k - 1]), dict(stage=nxt, expert_ids=[k, n_exp - 1])]
        else:
            parts = [dict(stage=home, expert_ids=[0, n_exp - 1])]
        owners.append(dict(layer=L, dense_owner_stage=home, routed_expert_candidate_owners=parts))
        start = end
    assert len(cuts) <= S - 1
    # per-die capacity at the product fit: usable field less the stage's MAC strips and the BF16 columns, at the
    # storage-only density (the fit's own rule, U.cons_field_need_mm2)
    plan = U.cons_stage_plan(S)
    scale = U._cons_busiest_macros(S) / plan["busiest_macros"]
    usable = U.cons_field_usable_mm2(geom=U.PRODUCT_GEOM)
    a = U.DENSITY["analytical"]["mm2_per_B"]
    dr = U.ROM_DEPTH_OPTS["8192m8"]["mb_per_mm2"] / U.ROM_DEPTH_OPTS[PRODUCT["depth"]]["mb_per_mm2"]
    fq, fb = U._cons_pair_mm2(PRODUCT["pitch"]), U._cons_pair_mm2(PRODUCT["pitch"], True)
    nb = U.CONS_BF16["pairs"]
    head = []
    pairs_per_die = []
    for s in range(S):
        pairs = plan["macros_per_die"][s] * scale / 2
        pairs_per_die.append(round(pairs))
        strips = (pairs - nb) * (fq - 2 * U.CONS_MACRO_MM2) + nb * (fb - 2 * U.CONS_MACRO_MM2)
        head.append((usable - strips) / (a * dr) - sb / 4 - delta[s] / 4)
    srcs = [ROOT / "tools/uarch_model.py", ROOT / "configs/models/candidates/deepseek-v4.1-flash.json",
            ROOT / "results/floorplan/v41_die_macromap_expanded_woa.json", ROOT / "results/arch/v41_die_assembly.json",
            Path(__file__).resolve()]
    H = U.cons_head_dies("analytical", U.CONS["overhead"], "ring", U.PRODUCT_GEOM, PRODUCT["pitch"], "8192m8")
    return dict(schema="opentallas.v41.stage_owner_preflight.v1",
                status="coarse_integer_candidate_not_executable",
                claim_boundary="Whole routed-expert ID candidate from coarse checkpoint bytes only; no tensor image, "
                               "stage program, data-dependent schedule, inter-stage packet or bit-exact RTL proof.",
                basis=f"W16 V4.1 ROM PRODUCT split: {S} TP-4 stages ({4 * S} layer dies) + {H} head dies (8192m8 "
                      "ping-pong) + 36 Engram table dies; BF16 columns (1,024 pairs, W10b's 1,002.89 x 142.56 um "
                      "column outline) with q pairs at W10b's 510.84 x 126.9 um 1.2 GHz tile (floorplan sizes, routed "
                      f"closure pending) and W11's {U.PRODUCT_HUB['option']} SU+VM hub block "
                      f"({U.PRODUCT_HUB['block_mm2']} mm2, field less {U.PRODUCT_HUB['field_loss_mm2']} mm2; root "
                      "rulings 2026-10-01), 4096m8; capacity at the storage-only density (75.0 Mbit/mm2 + "
                      "SECDED), 12.5% overhead, ring credit, 90% fill; Engram spill 0",
                source_sha256={str(p.relative_to(ROOT)): digest(p) for p in srcs},
                stage_count=S, layer_dies=4 * S, expert_count=n_exp, cut_count=len(cuts), cuts=cuts,
                layer_owners=owners, pairs_per_die_by_stage=pairs_per_die,
                per_die_rounding_delta_bytes=[x / 4 for x in delta],
                per_die_headroom_after_rounding_before_engram_spill_bytes=head,
                per_die_headroom_after_rounding_and_engram_spill_bytes=head,
                min_per_die_headroom_after_rounding_and_engram_spill_bytes=min(head),
                missing_gates=["checkpoint tensor/scale/metadata placement by ROM address",
                               "program per stage and expert owner lookup for selected IDs",
                               "ordered cross-stage activation, expert-output and HC-state packets",
                               f"bit-exact two-stage then {S}-stage execution with measured link cycles"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=int, default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = derive(a.stages)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + "\n")
    print(a.out, rec["stage_count"], "stages", rec["cut_count"], "cuts, min headroom",
          round(rec["min_per_die_headroom_after_rounding_and_engram_spill_bytes"] / 1e6, 1), "MB")


if __name__ == "__main__":
    main()

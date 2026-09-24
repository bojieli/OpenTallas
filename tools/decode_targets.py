"""Per-target headline numbers read from a roofline results tree.

Shared by the legacy snapshot (``results/roofline/critical_path/legacy_serial_model_targets.json``,
read from the artifacts of commit ae4d7487, the last ones priced with the flat per-layer floor and
two all-reduces per layer) and by ``tools/decode_critical_path.py``, which applies the SAME selection
to the regenerated tree so the before/after table compares like with like.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: (key, study artifact directory relative to results/roofline, model name)
TARGETS = (
    ("qwen3_8b", "n5_vs_b200", "Qwen3-8B"),
    ("deepseek_v4_flash", "n5_vs_b200", "DeepSeek-V4-Flash-0731"),
    ("deepseek_v4_pro", "n5_vs_b200", "DeepSeek-V4-Pro-0813"),
    ("deepseek_v41_flash", "candidates/deepseek-v41-flash/n5_vs_b200", "DeepSeek-V4.1-Flash"),
    ("kimi_k3", "candidates/kimi-k3/n5_vs_b200", "Kimi-K3"),
    ("mimo_v26_pro", "candidates/mimo-v26-pro/n5_vs_b200", "MiMo-V2.6-Pro"),
    ("mimo_v26_flash", "candidates/mimo-v26-flash/n5_vs_b200", "MiMo-V2.6-Flash"),
)
#: The two V4.1 designs the ROM target is described by, re-evaluated by name.
NAMED_DESIGNS = (
    ("deepseek_v41_array_x188", "candidates/deepseek-v41-flash/n5_vs_b200",
     "DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188"),
    ("deepseek_v41_wafer_x12", "candidates/deepseek-v41-flash/n5_vs_b200",
     "DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12"),
)


def _rows(points: list, design: str) -> dict[int, dict]:
    return {int(q["batch_size"]): q for q in points if q["design"] == design}


def design_summary(points: list, design: str) -> dict[str, Any] | None:
    rows = _rows(points, design)
    if not rows:
        return None

    def rate(batch: int, key: str) -> float | None:
        row = rows.get(batch)
        return float(row[key]) if row and row["feasible"] else None

    return {
        "design": design,
        "per_user_b1": rate(1, "per_user_tokens_s"),
        "per_user_b64": rate(64, "per_user_tokens_s"),
        "aggregate_b64": rate(64, "aggregate_tokens_s"),
        "aggregate_max": max((float(q["aggregate_tokens_s"]) for q in rows.values() if q["feasible"]), default=None),
        "tensor_group_b1": rows[1].get("tensor_group") if 1 in rows else None,
        "tensor_group_b64": rows[64].get("tensor_group") if 64 in rows else None,
        "pipeline_stages_b1": rows[1].get("pipeline_stages") if 1 in rows else None,
        "collective_algorithms_b1": rows[1].get("collective_algorithms") if 1 in rows else None,
        "collectives_per_layer_b1": rows[1].get("collectives_per_layer") if 1 in rows else None,
    }


def fastest(points: list, family: str, batch: int) -> dict[str, Any] | None:
    rows = [q for q in points if q["family"] == family and int(q["batch_size"]) == batch and q["feasible"]]
    if not rows:
        return None
    best = max(rows, key=lambda q: q["per_user_tokens_s"])
    return {"design": best["design"], "per_user": best["per_user_tokens_s"],
            "aggregate": best["aggregate_tokens_s"], "tensor_group": best.get("tensor_group"),
            "parallelism": best.get("parallelism"),
            "collective_algorithms": best.get("collective_algorithms")}


def targets(results_root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, study, model in TARGETS:
        base = results_root / study
        ana = json.loads((base / "analytical.json").read_text())
        points = [q for q in json.loads((base / "points.json").read_text()) if q["model"] == model]
        sel = next(m for m in ana["design_selection"]["models"] if m["model"] == model)
        rec = sel["recommended"]
        out[key] = {
            "study": study,
            "model": model,
            "recommended": design_summary(points, rec["design"]) if rec else None,
            "fastest_rom_b1": fastest(points, "rom", 1),
            "fastest_rom_b64": fastest(points, "rom", 64),
            "fastest_gpu_b1": fastest(points, "gpu", 1),
            "fastest_gpu_b64": fastest(points, "gpu", 64),
        }
    return out

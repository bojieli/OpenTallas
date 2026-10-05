#!/usr/bin/env python3
"""Generate synthetic stress traces and small real-checkpoint router samples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.profiling import SOURCES
from opentallas.routing import checkpoint_router_sample, generate_synthetic_routes, trace_report
from opentallas.schema import ModelProfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--tokens", type=int, default=256)
    parser.add_argument("--checkpoint-tokens", type=int, default=8)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "routing")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "hf")
    args = parser.parse_args()
    if not args.all:
        parser.error("use --all")
    args.output.mkdir(parents=True, exist_ok=True)
    for source in SOURCES:
        model = ModelProfile.load(ROOT / "configs" / "models" / f"{source.slug}.json")
        if model.routed_weight_bytes == 0:
            output = {
                "model": model.name,
                "source_repo": model.source_repo,
                "source_revision": model.source_revision,
                "status": "not applicable: dense model has no expert router",
                "synthetic_scenarios": {},
                "checkpoint_router_sample": None,
            }
            target = args.output / f"{source.slug}.json"
            target.write_text(
                json.dumps(output, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"wrote {target}")
            continue
        scenarios = {}
        for name, alpha, persistence in (
            ("uniform", 0.0, 0.0),
            ("zipf_imbalanced", 0.8, 0.0),
            ("zipf_correlated", 0.8, 0.65),
        ):
            routes = generate_synthetic_routes(
                model,
                args.tokens,
                seed=7,
                zipf_alpha=alpha,
                persistence=persistence,
            )
            scenarios[name] = trace_report(model, routes, (1, 8, 64))
        checkpoint = checkpoint_router_sample(
            source,
            model,
            args.cache_dir,
            tokens=args.checkpoint_tokens,
        )
        output = {
            "model": model.name,
            "synthetic_scenarios": scenarios,
            "checkpoint_router_sample": checkpoint,
        }
        target = args.output / f"{source.slug}.json"
        target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

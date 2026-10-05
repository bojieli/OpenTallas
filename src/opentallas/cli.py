"""Command-line front end for a single analytical operating point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analytical import AnalyticalSimulator
from .config import load_architectures
from .schema import HardwareProfile, ModelProfile, SimulationRequest, SpeculationProfile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--hardware", type=Path, default=Path("configs/hardware/architectures.json"))
    parser.add_argument("--gpu", help="exact GPU architecture name; default simulates every GPU")
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--draft-tokens", type=int, default=0)
    parser.add_argument("--acceptance", type=float, default=0.0)
    parser.add_argument("--draft-cost-fraction", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    model = ModelProfile.load(args.model)
    gpus, rom, _ = load_architectures(args.hardware)
    if args.gpu:
        gpus = [gpu for gpu in gpus if gpu.name == args.gpu]
        if not gpus:
            raise SystemExit(f"unknown GPU architecture {args.gpu!r}")
    request = SimulationRequest(
        context_tokens=args.context,
        batch_size=args.batch,
        speculation=SpeculationProfile(
            draft_tokens=args.draft_tokens,
            acceptance_probability=args.acceptance,
            draft_cost_fraction=args.draft_cost_fraction,
        ),
    )
    simulator = AnalyticalSimulator(HardwareProfile(gpu=gpus[0], rom=rom))
    points = [simulator.simulate(model, gpu, request).to_dict() for gpu in gpus]
    points.append(simulator.simulate(model, rom, request).to_dict())
    print(json.dumps(points, indent=2, allow_nan=True))
    return 0

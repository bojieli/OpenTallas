#!/usr/bin/env python3
"""Generate measured model profiles from official Hugging Face metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.profiling import SOURCES, build_profile, profile_checkpoint, source_by_slug


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="profile all representative models")
    parser.add_argument("--model", choices=[source.slug for source in SOURCES], action="append")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "hf")
    args = parser.parse_args()
    slugs = [source.slug for source in SOURCES] if args.all else (args.model or [])
    if not slugs:
        parser.error("use --all or at least one --model")

    model_dir = ROOT / "configs" / "models"
    inventory_dir = ROOT / "data" / "inventory"
    model_dir.mkdir(parents=True, exist_ok=True)
    inventory_dir.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        source = source_by_slug(slug)
        print(f"profiling {source.repo}@{source.revision}", flush=True)
        config, inventory = profile_checkpoint(source, args.cache_dir, workers=args.workers)
        profile = build_profile(source, config, inventory)
        inventory_path = inventory_dir / f"{source.inventory_slug}.json"
        profile_path = model_dir / source.profile_dir / f"{slug}.json"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        # A placement variant shares its checkpoint's inventory verbatim.
        inventory_path.write_text(
            json.dumps(inventory.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        profile_path.write_text(
            json.dumps(profile.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"  {inventory.tensor_count:,} tensors, {inventory.checkpoint_bytes / 1e9:.3f} GB; "
            f"wrote {profile_path.relative_to(ROOT)}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

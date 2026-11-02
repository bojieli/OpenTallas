#!/usr/bin/env python3
"""Select the approved head-kit specialization in a NEW KV bind recipe.

Existing recipes and snapshots are never edited. The head score/data schedule
is unchanged. The accepted PORT_REGS diagnostic fault edge is +1; reset and
START boundaries remain part of the parent functional qualification.
"""
import argparse
import json
from pathlib import Path

BASE = "physical/die_plan/qwen_kvsys/bind/kvbind1025/composition_heads_astk_1clk_oddstrap.json"
HEADKIT = BASE.replace(".json", "_headkit.json.gz")


def select(recipe):
    if recipe.get("compose") not in (BASE, BASE + ".gz", HEADKIT, HEADKIT[:-3]):
        raise ValueError("recipe does not select the qualified head/ASTK composition")
    out = dict(recipe)
    out["compose"] = HEADKIT
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.recipe.resolve() == args.out.resolve() or args.out.exists():
        ap.error("--out must be a fresh recipe path")
    out = select(json.loads(args.recipe.read_text()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()

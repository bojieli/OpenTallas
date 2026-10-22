#!/usr/bin/env python3
"""Annotate extracted SPEF in every ORFS timing scene before finish metrics.

Applied only to final_outputs.tcl inside a new disposable flow container.
Existing containers, work directories and evidence are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ORIGINAL = "  read_spef $::env(RESULTS_DIR)/6_final.spef"
ANNOTATION = """  # OpenTallas: extracted parasitics must reach every configured scene.
  if {[info exists ::env(CORNERS)] && [llength $::env(CORNERS)] > 0} {
    foreach spef_corner $::env(CORNERS) {
      read_spef -corner $spef_corner $::env(RESULTS_DIR)/6_final.spef
    }
    unset spef_corner
  } else {
    read_spef $::env(RESULTS_DIR)/6_final.spef
  }"""


def patch_final_outputs(text: str) -> str:
    lines = text.splitlines()
    if lines.count(ORIGINAL) != 1:
        raise ValueError("expected exactly one original ORFS finish read_spef; refusing changed evaluator")
    return "\n".join(ANNOTATION if line == ORIGINAL else line for line in lines) + ("\n" if text.endswith("\n") else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluator", type=Path)
    args = parser.parse_args()
    original = args.evaluator.read_text()
    patched = patch_final_outputs(original)
    args.evaluator.write_text(patched)
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    print(json.dumps({"allcorner_spef_evaluator": str(args.evaluator),
                      "original_sha256": digest(original), "patched_sha256": digest(patched),
                      "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()

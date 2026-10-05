#!/usr/bin/env python3
"""Exact reduced Qwen TP-2 package gate with the existing scalar-core RTL.

This checks the two-die collective topology. It does not exercise the O4
INT8 weight path, vector core, full model, or a physical UCIe implementation.
"""
import hashlib
import json
import os
import tempfile
import argparse
from contextlib import nullcontext
from pathlib import Path

os.environ["HDC_SU_WIDTH"] = "1"
import rtl_hdc_package_tp_campaign as C  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/hdc_package_tp2_smoke.json"


def run(keep=None):
    C.TP = 2
    paths = {*C.sources(), Path(__file__)}
    source_pin = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(paths)}
    temporary = tempfile.TemporaryDirectory(prefix="hdc_tp2_") if keep is None else nullcontext(keep)
    with temporary as dirname:
        scratch = Path(dirname)
        scratch.mkdir(parents=True, exist_ok=True)
        img = C.images(scratch)
        expected = json.loads((img / "expect.json").read_text())
        assert expected["tp"] == 2
        assert expected["single_step"]["logits_bit_exact"]
        assert expected["end_to_end"]["logits_bit_exact"]
        words = 1 << (max(16384, expected["wrom_words"]) - 1).bit_length()
        package = C.run_pkg(scratch, img, C.link_params(), 1, 1, (), None, wrom_words=words)[0]
    source_current = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                         for name, digest in source_pin.items())
    return {
        "schema": "opentallas.hdc-package-tp2-smoke.v1",
        "status": "pass" if package["pass"] and source_current else ("stale" if not source_current else "fail"),
        "claim_boundary": "Reduced Qwen scalar-core two-die package; behavioural memories and UCIe delay model. "
                          "This is a topology and exact-state gate, not an O4 INT8/vector/physical-rate gate.",
        "configuration": {"dies": 2, "packages": 1, "users": 1, "wrom_words_per_die": words},
        "golden": expected,
        "package": package,
        "input_sha256": source_pin,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", type=Path, help="retain image, build and RTL stdout for diagnosis")
    args = parser.parse_args()
    result = run(args.keep)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(OUT, result["status"], result["package"]["total_cycles"])
    raise SystemExit(0 if result["status"] == "pass" else 1)

#!/usr/bin/env python3
"""Exact real layer-0 Q/K norm weight supply from HBM sectors."""
import argparse
import json
import subprocess
from pathlib import Path

import rtl_hdc_qwen_post_tp_scale_hbm as base

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [*base.SOURCES[:3], Path(__file__).resolve()]
CBASE, WORDS, SECTORS = 4096, 2560, 640


def extract(die_dir, target):
    manifest = die_dir / "layer0_rom.json"
    image = die_dir / "crom.hex"
    meta = json.loads(manifest.read_text())
    assert meta["constant_words"] == 543233
    with image.open() as src, target.open("w") as dst:
        count = 0
        for address, line in enumerate(src):
            if CBASE <= address < CBASE + WORDS:
                assert len(line.strip()) == 16
                dst.write(line)
                count += 1
    assert count == WORDS
    return {"manifest": base.digest(manifest), "crom": base.digest(image),
            "extracted": base.digest(target), "base": CBASE, "words": count}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--die0", type=Path, default=Path("/tmp/qwen-real-layer0-d0"))
    ap.add_argument("--die1", type=Path, default=Path("/tmp/qwen-real-layer0-d1"))
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/qwen-qk-norm-hbm"))
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/qwen_qk_norm_hbm.json")
    args = ap.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    images = {}
    for die, source in enumerate((args.die0, args.die1)):
        target = args.workdir / f"die{die}_qk_norm.hex"
        images[f"die{die}"] = extract(source, target)
    obj = args.workdir / "obj"
    command = ["verilator", "--cc", "--exe", "--build", "-O0", "-Wno-fatal",
               "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
               "--top-module", "tb_hdc_qwen_post_tp_scale_hbm",
               "-GROWS=1280", "-GBASE=4096", "-Mdir", str(obj),
               *map(str, SOURCES[:3]), "-CFLAGS", "-O0", "-j", "2"]
    build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (args.workdir / "build.log").write_text(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError((build.stdout + build.stderr)[-3000:])
    binary = obj / "Vtb_hdc_qwen_post_tp_scale_hbm"
    runs = {}
    for die in (0, 1):
        image = args.workdir / f"die{die}_qk_norm.hex"
        run = subprocess.run([str(binary), f"+IMG={image}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        (args.workdir / f"die{die}.log").write_text(run.stdout + run.stderr)
        passed = run.returncode == 0 and f"PASS Qwen CROM HBM words={WORDS} sectors={SECTORS}" in run.stdout
        runs[f"die{die}"] = {"status": "pass" if passed else "fail", "stdout": run.stdout[-1000:]}
        if not passed:
            raise RuntimeError(f"die{die} Q/K norm HBM gate failed: {run.stdout[-1000:]} {run.stderr[-1000:]}")
    record = {"schema": "opentallas.qwen-qk-norm-hbm.v1", "status": "pass",
              "claim_boundary": "Real checkpoint layer-0 Q/K norm weights from 640 32-byte HBM sectors per die, 2560 CROM words at [4096,6656), bit-exact one-cycle reads. Standalone source only; no complete layer, shared controller, KV, P&R or throughput claim.",
              "source_sha256": {str(p.relative_to(ROOT)): base.digest(p) for p in SOURCES},
              "image_sha256": images, "binary_sha256": base.digest(binary),
              "observed": {"dies": 2, "words_per_die": WORDS, "sectors_per_die": SECTORS},
              "runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(args.output, "pass", record["observed"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Exact CROM post-TP scale supply from the frozen real Qwen layer-0 images."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "rtl/hdc/hbm/ot_hdc_qwen_post_tp_scale_hbm.sv",
           ROOT / "rtl/test/tb_hdc_qwen_post_tp_scale_hbm.sv",
           ROOT / "rtl/test/qwen_post_tp_scale_hbm_harness.cpp", Path(__file__).resolve()]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(die_dir, target):
    manifest_path = die_dir / "layer0_rom.json"
    crom_path = die_dir / "crom.hex"
    manifest = json.loads(manifest_path.read_text())
    base, down = manifest["post_tp_scale_bases"]
    assert base == 535041 and down == base + 4096
    assert manifest["constant_words"] == base + 8192
    count = 0
    with crom_path.open() as src, target.open("w") as dst:
        for address, line in enumerate(src):
            if base <= address < base + 8192:
                assert len(line.strip()) == 16
                dst.write(line)
                count += 1
    assert count == 8192, count
    return {"manifest": digest(manifest_path), "crom": digest(crom_path),
            "extracted": digest(target), "base": base, "words": count}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--die0", type=Path, default=Path("/tmp/qwen-real-layer0-d0"))
    parser.add_argument("--die1", type=Path, default=Path("/tmp/qwen-real-layer0-d1"))
    parser.add_argument("--workdir", type=Path, default=Path("/tmp/qwen-post-tp-scale-hbm"))
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/rtl/qwen_post_tp_scale_hbm.json")
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    images = {}
    for die, path in enumerate((args.die0, args.die1)):
        image = args.workdir / f"die{die}_post_tp_scale.hex"
        images[f"die{die}"] = extract(path, image)
    obj = args.workdir / "obj"
    command = ["verilator", "--cc", "--exe", "--build", "-O0", "-Wno-fatal",
               "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
               "--top-module", "tb_hdc_qwen_post_tp_scale_hbm", "-Mdir", str(obj),
               *map(str, SOURCES[:2]), str(SOURCES[2]), "-CFLAGS", "-O0", "-j", "2"]
    build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (args.workdir / "build.log").write_text(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError((build.stdout + build.stderr)[-4000:])
    binary = obj / "Vtb_hdc_qwen_post_tp_scale_hbm"
    runs = {}
    for die in (0, 1):
        image = args.workdir / f"die{die}_post_tp_scale.hex"
        run = subprocess.run([str(binary), f"+IMG={image}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        (args.workdir / f"die{die}.log").write_text(run.stdout + run.stderr)
        passed = (run.returncode == 0 and
                  "PASS Qwen post-TP scale HBM 8192 words 2048 sectors" in run.stdout)
        runs[f"die{die}"] = {"status": "pass" if passed else "fail",
                              "stdout": run.stdout, "stderr": run.stderr}
        if not passed:
            raise RuntimeError(f"die{die} post-TP scale HBM gate failed:\n{run.stdout[-3000:]}\n{run.stderr[-1000:]}")
    data = {"schema": "opentallas.qwen-post-tp-scale-hbm.v1", "status": "pass",
            "claim_boundary": "Real checkpoint layer-0 o/down post-TP BF16 scales materialized as 8192 64-bit CROM words per die; a 32-PC behavioural HBM source fetches 2048 32-byte sectors, then serves every CROM read bit-exact in one cycle. Standalone supply gate only: no full layer/token, shared KV controller, placement, or throughput claim. Other CROM constants stay local.",
            "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in SOURCES},
            "image_sha256": images, "binary_sha256": digest(binary),
            "observed": {"dies": 2, "words_per_die": 8192, "sectors_per_die": 2048},
            "runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(args.output, "pass", data["observed"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Exact CROM post-TP scale supply from the frozen real Qwen layer-0 images."""
import argparse
import hashlib
import json
import shutil
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
    parser.add_argument("--head-image", type=Path,
                        help="Use the full-token binding's 4096-word head final-norm CROM image")
    parser.add_argument("--workdir", type=Path, default=Path("/tmp/qwen-post-tp-scale-hbm"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    images = {}
    image_names = []
    if args.head_image:
        image = args.workdir / "head_final_norm.hex"
        shutil.copyfile(args.head_image, image)
        assert len(image.read_text().splitlines()) == 4096
        images["head"] = {"source": digest(args.head_image), "extracted": digest(image),
                          "base": 0, "words": 4096}
        image_names.append(("head", image))
        rows, base = 2048, 0
    else:
        for die, path in enumerate((args.die0, args.die1)):
            image = args.workdir / f"die{die}_post_tp_scale.hex"
            images[f"die{die}"] = extract(path, image)
            image_names.append((f"die{die}", image))
        rows, base = 4096, 535041
    obj = args.workdir / "obj"
    command = ["verilator", "--cc", "--exe", "--build", "-O0", "-Wno-fatal",
               "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
               "--top-module", "tb_hdc_qwen_post_tp_scale_hbm",
               f"-GROWS={rows}", f"-GBASE={base}", "-Mdir", str(obj),
               *map(str, SOURCES[:2]), str(SOURCES[2]), "-CFLAGS", "-O0", "-j", "2"]
    build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (args.workdir / "build.log").write_text(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError((build.stdout + build.stderr)[-4000:])
    binary = obj / "Vtb_hdc_qwen_post_tp_scale_hbm"
    runs = {}
    for name, image in image_names:
        run = subprocess.run([str(binary), f"+IMG={image}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        (args.workdir / f"{name}.log").write_text(run.stdout + run.stderr)
        passed = (run.returncode == 0 and
                  f"PASS Qwen CROM HBM words={2*rows} sectors={rows//2}" in run.stdout)
        runs[name] = {"status": "pass" if passed else "fail",
                      "stdout": run.stdout, "stderr": run.stderr}
        if not passed:
            raise RuntimeError(f"{name} CROM HBM gate failed:\n{run.stdout[-3000:]}\n{run.stderr[-1000:]}")
    claim = ("Full-token binding's head final-norm 4096 64-bit CROM words "
             if args.head_image else
             "Real checkpoint layer-0 o/down post-TP BF16 scales materialized as 8192 64-bit CROM words per die ")
    claim += ("fetched through 32 PC-local 32-byte-sector banks and read bit-exact in one cycle. "
              "Standalone supply gate only: no full layer/token, shared KV controller, "
              "placement, or throughput claim. Other CROM constants stay local.")
    data = {"schema": "opentallas.qwen-crom-region-hbm.v1", "status": "pass",
            "claim_boundary": claim,
            "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in SOURCES},
            "image_sha256": images, "binary_sha256": digest(binary),
            "observed": {"dies": len(image_names), "words_per_die": 2*rows,
                         "sectors_per_die": rows//2},
            "runs": runs}
    output = args.output or ROOT / "results/rtl" / (
        "qwen_head_norm_hbm.json" if args.head_image else "qwen_post_tp_scale_hbm.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(output, "pass", data["observed"])


if __name__ == "__main__":
    main()

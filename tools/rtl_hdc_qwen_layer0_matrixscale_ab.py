#!/usr/bin/env python3
"""Source-matched real Qwen layer-0 ROM vs matrix/scale HBM campaign.

The two arms use identical program, matrix code/scale, CROM and X images.
The HBM arm sources matrix code, row scales and o/down post-TP scales from
bounded PC windows. Embedding, other constants and KV are outside this gate.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as C  # noqa: E402

RTL = [*C.HDC, *C.PIPES,
       *(ROOT / f"rtl/hdc/{x}.sv" for x in
         ("ot_hdc_dyn_ttiles", "ot_hdc_qwen_int8_arith", "ot_hdc_qwen_int8_embed_decode",
          "ot_hdc_core_vector_weight")),
       *(ROOT / f"rtl/rom/{x}.sv" for x in
         ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_oneshot_allreduce", "ot_rom_tp_seq")),
       ROOT / "rtl/hdc/hbm/ot_hdc_qwen_post_tp_scale_hbm.sv",
       ROOT / "rtl/hdc/hbm/ot_hdc_qwen_int8_pc_window.sv",
       ROOT / "rtl/test/tb_hdc_qwen_layer0_tp2_matrixscale_ab.sv"]
HARNESS = ROOT / "rtl/test/hdc_qwen_layer0_tp2_matrixscale_ab_harness.cpp"
SOURCES = sorted(set([*RTL, HARNESS, Path(__file__).resolve(), C.ISA_SVH]))
IMAGES = ("program.hex", "segments.hex", "matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex")
VECTORS = ("x_final", "t1_after_o_scale", "t1_after_down_scale", "k_pos0", "v_pos0")
PASS = re.compile(r"QWEN_LAYER0_TP2_MATRIXSCALE PASS dies=2 token=0 pos=0 matrix_hbm=(\d+) post_hbm=(\d+) cycles=(\d+)")
POST_TRAFFIC = re.compile(r"POST_SCALE_HBM die=(\d+) sectors=(\d+)")
MATRIX_TRAFFIC = re.compile(r"MATRIX_HBM die=(\d+) pc=(\d+) code_sectors=(\d+) scale_sectors=(\d+)")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def words(path):
    return [int(line, 16) for line in path.read_text().splitlines() if line]


def prepare(work, image_prefix, preload, oracle_dir):
    oracle = json.loads((oracle_dir / "oracle.json").read_text())
    assert oracle["status"] == "ISA_golden_only"
    image_hashes = {}
    for arm in ("rom", "hbm"):
        arm_dir = work / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        for die in (0, 1):
            dest = arm_dir / f"die{die}"
            dest.mkdir(exist_ok=True)
            for name in IMAGES:
                src = Path(f"{image_prefix}-d{die}") / name
                actual = sha(src)
                assert actual == oracle["input_image_sha256"][f"die{die}"][name], (die, name)
                image_hashes[f"die{die}/{name}"] = actual
                link = dest / name
                if not (link.is_symlink() and link.resolve() == src.resolve()):
                    if link.exists() or link.is_symlink():
                        link.unlink()
                    link.symlink_to(src)
        x = preload / "vm_x_fp32.hex"
        actual = sha(x)
        assert actual == oracle["x_preload_sha256"]
        image_hashes["vm_x_fp32.hex"] = actual
        link = arm_dir / "vm_x_fp32.hex"
        if not (link.is_symlink() and link.resolve() == x.resolve()):
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(x)
    return image_hashes, sha(oracle_dir / "oracle.json")


def build_command(obj, arm, jobs):
    return ["verilator", "--cc", "--exe", "--build", "-O1", "--unroll-count", "131072",
            "--unroll-limit", "131072",
            "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
            "-Wno-TIMESCALEMOD", "-Wno-PINMISSING",
            "--top-module", "tb_hdc_qwen_layer0_tp2_matrixscale_ab", "-GG=6144",
            f"-GMATRIX_HBM={arm}", f"-GPOST_SCALE_HBM={arm}",
            "-Mdir", str(obj), f"-I{C.ISA_SVH.parent}",
            *map(str, RTL), str(HARNESS), "-CFLAGS", "-O0", "-j", str(jobs)]


def run_arm(work, arm_name, jobs, skip_build, image_hashes, oracle_hash, oracle_dir):
    arm = 0 if arm_name == "rom" else 1
    arm_dir = work / arm_name
    obj = work / f"obj_{arm_name}"
    binary = obj / "Vtb_hdc_qwen_layer0_tp2_matrixscale_ab"
    command = build_command(obj, arm, jobs)
    start_sources = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    if not skip_build:
        cp = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (work / f"build_{arm_name}.log").write_text(cp.stdout + cp.stderr)
        if cp.returncode:
            raise RuntimeError(f"{arm_name} build failed: {(cp.stdout+cp.stderr)[-4000:]}")
    cp = subprocess.run([str(binary), f"+DIR={arm_dir}"], cwd=ROOT,
                        capture_output=True, text=True, timeout=7200)
    (work / f"sim_{arm_name}.log").write_text(cp.stdout + cp.stderr)
    match = PASS.search(cp.stdout)
    post_traffic = [(int(die), int(sectors)) for die, sectors in POST_TRAFFIC.findall(cp.stdout)]
    matrix_traffic = [(int(die), int(pc), int(code), int(scale))
                      for die, pc, code, scale in MATRIX_TRAFFIC.findall(cp.stdout)]
    matrix_totals = {die: (sum(row[2] for row in matrix_traffic if row[0] == die),
                           sum(row[3] for row in matrix_traffic if row[0] == die))
                     for die in (0, 1)}
    checks = {}
    for die in (0, 1):
        for name in VECTORS:
            actual = arm_dir / f"die{die}" / f"{name}.hex"
            expected = oracle_dir / f"die{die}_{name}.hex"
            got = words(actual) if actual.exists() else []
            want = words(expected)
            checks[f"die{die}_{name}"] = {
                "mismatches": sum(a != b for a, b in zip(got, want)) + abs(len(got)-len(want)),
                "words": len(got), "actual_sha256": sha(actual) if actual.exists() else None,
                "expected_sha256": sha(expected)}
    stable = (start_sources == {str(p.relative_to(ROOT)): sha(p) for p in SOURCES} and
              all(sha(arm_dir / path) == digest for path, digest in image_hashes.items()))
    passed = (cp.returncode == 0 and match is not None and
              int(match.group(1)) == arm and int(match.group(2)) == arm and
              stable and all(v["mismatches"] == 0 for v in checks.values()) and
              (arm == 0 or (sorted(post_traffic) == [(0, 2048), (1, 2048)] and
                            len(matrix_traffic) == 64 and
                            matrix_totals == {0: (3047424, 1472), 1: (3047424, 1472)})))
    data = {"status": "pass" if passed else "fail", "arm": arm_name,
            "cycles": int(match.group(3)) if match else None,
            "post_traffic": post_traffic, "matrix_traffic": matrix_traffic,
            "matrix_totals": matrix_totals,
            "checks": checks, "source_stable": stable, "source_sha256": start_sources,
            "image_sha256": image_hashes, "oracle_sha256": oracle_hash,
            "binary_sha256": sha(binary) if binary.exists() else None,
            "build_command": command, "stdout_tail": cp.stdout[-3000:]}
    (work / f"arm_{arm_name}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(arm_name, data["status"], data["cycles"])
    if not passed:
        raise RuntimeError(f"{arm_name} exact layer0 gate failed: {cp.stdout[-3000:]}")


def combine(work, output):
    rom, hbm = [json.loads((work / f"arm_{x}.json").read_text()) for x in ("rom", "hbm")]
    assert rom["status"] == hbm["status"] == "pass"
    assert rom["source_sha256"] == hbm["source_sha256"]
    assert rom["image_sha256"] == hbm["image_sha256"]
    assert rom["oracle_sha256"] == hbm["oracle_sha256"]
    assert {k: v["actual_sha256"] for k, v in rom["checks"].items()} == \
           {k: v["actual_sha256"] for k, v in hbm["checks"].items()}
    result = {"schema": "opentallas.qwen-layer0-matrixscale-ab.v1", "status": "pass",
              "claim_boundary": "Real checkpoint Qwen layer-0 TP-2 same-program/same-image matrix code, BF16 row scales and post-TP o/down true-scale source A/B only. Other constants, embedding and KV remain local. Behavioural independent 32-PC HBM sources, no shared controller, complete token, throughput or P&R claim.",
              "rom_cycles": rom["cycles"], "hbm_cycles": hbm["cycles"],
              "delta_cycles": hbm["cycles"]-rom["cycles"],
              "source_sha256": rom["source_sha256"], "image_sha256": rom["image_sha256"],
              "oracle_sha256": rom["oracle_sha256"], "rom": rom["checks"], "hbm": hbm["checks"],
              "hbm_post_traffic": hbm["post_traffic"],
              "hbm_matrix_totals": hbm["matrix_totals"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(output, "pass", result["delta_cycles"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--image-prefix", type=Path, default=Path("/tmp/qwen-real-layer0"))
    ap.add_argument("--preload-dir", type=Path, default=Path("/tmp/qwen-vocab-embed-token0"))
    ap.add_argument("--oracle-dir", type=Path, default=ROOT / "results/rtl/qwen_o4_layer0_oracle")
    ap.add_argument("--arm", choices=("rom", "hbm"))
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--combine", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/qwen_layer0_matrixscale_ab.json")
    args = ap.parse_args()
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if args.combine:
        combine(work, args.output)
        return
    images, oracle_hash = prepare(work, args.image_prefix, args.preload_dir, args.oracle_dir)
    if args.prepare_only:
        result = {"status": "images_and_oracle_pinned", "image_sha256": images,
                  "oracle_sha256": oracle_hash,
                  "claim_boundary": "The two copied layer-0 arms resolve to identical frozen real-checkpoint program, matrix, scale, CROM and X images and one ISA oracle. G6144 RTL A/B execution, exactness and cycle delta are pending.",
                  "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}}
        (work / "prepare.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(work / "prepare.json", result["status"])
    else:
        if not args.arm:
            ap.error("--arm is required unless --prepare-only or --combine")
        run_arm(work, args.arm, args.jobs, args.skip_build, images, oracle_hash, args.oracle_dir)


if __name__ == "__main__":
    main()

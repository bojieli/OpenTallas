#!/usr/bin/env python3
"""Full-shape (G6144) Qwen3-8B layer-0 TP-2 bit-exact run by runtime composition.

Replays rtl/test/tb_hdc_qwen_layer0_tp2.sv with both dies, the production TP
sequencer and one-shot all-reduce collective, and the real checkpoint INT8 image,
but with the matrix engine simulated as the sliced composition qualified by
tools/qwen_rt_matvec_gate.py (so no model elaborates 98,304 lanes).  Compares the
bench's dumped vectors with the independently produced ISA oracle
results/rtl/qwen_o4_layer0_oracle and writes a source-pinned record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as C  # noqa: E402
import rtl_hdc_qwen_layer0_tp2 as L0  # noqa: E402
import qwen_rt_core_emit  # noqa: E402

RT = ROOT / "rtl/test/qwen_runtime"
COMMON = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_fastfp",
                                            "ot_hdc_delay", "ot_hdc_sfu")] + [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
DIE_RTL = [*[p for p in C.HDC if p.name not in ("ot_hdc_matvec.sv", "ot_hdc_core.sv")], *C.PIPES,
           *(ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_dyn_ttiles", "ot_hdc_qwen_int8_arith",
                                               "ot_hdc_qwen_int8_embed_decode", "ot_hdc_core_vector_weight")),
           *(ROOT / f"rtl/rom/{n}.sv" for n in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_tp_seq")),
           RT / "ot_qwen_rt_matvec_seq.sv", RT / "ot_qwen_rt_die.sv"]
COLL_RTL = [ROOT / f"rtl/rom/{n}.sv" for n in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_oneshot_allreduce")]
SOURCES = sorted(set([*DIE_RTL, *COLL_RTL, *COMMON, RT / "ot_qwen_rt_matvec_slice.sv", RT / "ot_qwen_rt_tree.sv",
                      RT / "qwen_rt_matvec.hpp", RT / "qwen_rt_memory.hpp", RT / "qwen_rt_tp2.cpp",
                      ROOT / "rtl/test/tb_hdc_qwen_layer0_tp2.sv", C.ISA_SVH, Path(__file__),
                      ROOT / "tools/qwen_rt_core_emit.py", ROOT / "tools/qwen_rt_matvec_gate.py",
                      ROOT / "tools/qwen_o4_token_oracle.py", ROOT / "tools/qwen_o4_head_rom.py"]))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--emitter-prefix", type=Path, default=Path("/tmp/qwen-real-layer0"))
    ap.add_argument("--preload-dir", type=Path, default=Path("/tmp/qwen-vocab-embed-token0"))
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--groups", type=int, default=6144)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--result", type=Path)
    ap.add_argument("--stages", type=Path, help="token mode: stage file (name die0dir die1dir kv_reset)")
    ap.add_argument("--token-oracle", type=Path, help="token mode: tools/qwen_o4_token_oracle.py output directory")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--count-width", type=int, choices=(16, 18), default=16)
    ap.add_argument("--fullshape", type=int, choices=(0, 1), default=0,
                    help="QWEN_FULLSHAPE core/sequencer overlay (18-bit rows); the token run uses 1")
    args = ap.parse_args()
    G, NW = args.groups, args.count_width
    LG = (G - 1).bit_length()
    LO, HI = min(LG, 7), LG - min(LG, 7)
    out = args.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    oracle = json.loads((L0.GOLD / "oracle.json").read_text())
    image_pins = {} if args.stages else L0.prepare(out, args.emitter_prefix, args.preload_dir, oracle)
    start_pins = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([args.verilator, "-V"], text=True)).group(1)
    steps = []

    def run(name, cmd):
        t0 = time.monotonic()
        p = subprocess.run(["/usr/bin/time", "-f", "%M", "-o", str(out / f"{name}.rss"), *map(str, cmd)],
                           cwd=out, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append({"name": name, "seconds": round(time.monotonic() - t0, 2), "returncode": p.returncode,
                      "max_rss_kib": int((out / f"{name}.rss").read_text().split()[-1])})
        if p.returncode:
            raise SystemExit(f"{name} failed; see {out / (name + '.log')}\n{(p.stdout + p.stderr)[-3000:]}")

    core_sv = out / "gen" / "ot_qwen_rt_core.sv"
    core_sv.parent.mkdir(exist_ok=True)
    core_sv.write_text(qwen_rt_core_emit.emit(qwen_rt_core_emit.CORE.read_text()))
    common = [str(p) for p in COMMON]
    pc = [f"-GG={G}", "-GW=16", f"-GNW={NW}", "-GINT8_WEIGHT=1"]
    models = [
        ("die", "ot_qwen_rt_die", [str(core_sv), *map(str, DIE_RTL)], [f"-GG={G}", f"-GNW={NW}", f"-GSNW={NW}", f"-GQWEN_FULLSHAPE={args.fullshape}"]),
        ("coll", "ot_rom_oneshot_allreduce", [*map(str, COLL_RTL), *map(str, C.PIPES), *common],
         ["-GN=2", "-GLANES=16", "-GTAGW=32", "-GDEPTH=16", "-GLAT=11", "-GBPC_NUM=3600"]),
        ("slice", "ot_qwen_rt_matvec_slice", [str(RT / "ot_qwen_rt_matvec_slice.sv"), *common], pc),
        ("cella", "ot_qwen_rt_tree_cell", [str(RT / "ot_qwen_rt_tree.sv"), *common], ["-GW=16", "-GADDS=1"]),
        ("amaxlo", "ot_qwen_rt_amax_tree", [str(RT / "ot_qwen_rt_tree.sv")], [f"-GNW={NW}", f"-GLEVELS={LO}"]),
        ("amaxhi", "ot_qwen_rt_amax_tree", [str(RT / "ot_qwen_rt_tree.sv")], [f"-GNW={NW}", f"-GLEVELS={max(HI, 1)}"]),
    ]
    if not args.skip_build:
        for prefix, top, files, params in models:
            mdir = out / prefix
            if (mdir / f"V{prefix}__ALL.a").exists():
                continue
            run(f"verilate_{prefix}", [args.verilator, "--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "-Wno-WIDTH",
                                       "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-PINMISSING", f"-I{C.ISA_SVH.parent}",
                                       "--top-module", top, "--prefix", f"V{prefix}", "--Mdir", mdir, *params, *files])
            run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{args.jobs}", f"V{prefix}__ALL.a",
                                    "OPT_FAST=-O2", "OPT_SLOW=-O1"])
        archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}"}
        for prefix, *_ in models:
            archives += sorted((out / prefix).glob("*.a"))
            includes.add(f"-I{out / prefix}")
        run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}", *sorted(includes),
                     RT / "qwen_rt_tp2.cpp", "-Wl,--start-group", *archives, "-Wl,--end-group",
                     f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp", "-o", out / "layer0"])
    binary = out / "layer0"
    if args.build_only:
        print("built", binary)
        return
    if args.stages:
        return run_token(args, out, binary, start_pins, core_sv, steps)
    t0 = time.monotonic()
    with open(out / "sim.log", "w") as log:
        p = subprocess.run([str(binary), str(out)], cwd=out, stdout=log, stderr=subprocess.STDOUT, text=True,
                           env=dict(os.environ, RT_THREADS=str(args.threads)))
    wall = time.monotonic() - t0
    p.stdout = (out / "sim.log").read_text()
    p.stderr = ""
    match = re.search(r"QWEN_LAYER0_TP2 PASS dies=2 token=0 pos=0 cycles=(\d+) ", p.stdout)
    stats = re.search(r"RT_STATS (.*)", p.stdout)
    checks = {}
    for die in range(2):
        for name in L0.VECTORS:
            path = out / f"die{die}" / f"{name}.hex"
            got = L0.vector(path) if path.exists() else []
            want = L0.vector(L0.GOLD / f"die{die}_{name}.hex")
            first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)
            checks[f"die{die}_{name}"] = {
                "expected_words": len(want), "actual_words": len(got),
                "mismatches": sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want)),
                "first_mismatch": first, "actual_sha256": sha(path) if got else None,
                "expected_sha256": sha(L0.GOLD / f"die{die}_{name}.hex")}
    end_pins = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    stable = end_pins == start_pins and all(sha(out / k) == v for k, v in image_pins.items())
    good = p.returncode == 0 and bool(match) and stable and all(c["mismatches"] == 0 for c in checks.values())
    result = {
        "schema": "opentallas.qwen-rt-layer0-tp2.v1", "status": "pass" if good else "fail",
        "groups": G, "rtl_cycles": int(match.group(1)) if match else None,
        "runtime_stats": dict(kv.split("=") for kv in stats.group(1).split()) if stats else None,
        "simulate_wall_seconds": round(wall, 1), "checks": checks,
        "source_sha256": start_pins, "source_stable": stable, "image_sha256": image_pins,
        "oracle_sha256": sha(L0.GOLD / "oracle.json"), "binary_sha256": sha(binary),
        "generated_core_sha256": sha(core_sv), "steps": steps,
        "verilator": subprocess.check_output([args.verilator, "--version"], text=True).strip(),
        "claim_boundary": ("Real Qwen3-8B layer-0 token0/pos0 TP-2 G6144 RTL (production core, TP sequencer and "
                           "collective; matrix engine as the gate-qualified sliced runtime composition) versus the "
                           "independent ISA oracle. Bench profile: scalar SU (SU_VEC=0, SW=1), behavioural memories "
                           "and link. Cycle count is this bench profile, not the modeled SW1024 rate; no physical timing."),
    }
    target = args.result or (out / "result.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "rtl_cycles": result["rtl_cycles"],
                      "mismatches": {k: v["mismatches"] for k, v in checks.items()}}, indent=2))
    if not good:
        print(p.stdout[-3000:], p.stderr[-2000:])
        raise SystemExit(1)


def run_token(args, out, binary, start_pins, core_sv, steps) -> None:
    stages = [line.split() for line in args.stages.read_text().splitlines() if line.strip()]
    stage_pins = {}
    for name, d0, d1, _ in stages:
        for d, path in enumerate((d0, d1)):
            for f in L0.IMAGE_FILES:
                stage_pins[f"{name}/die{d}/{f}"] = sha(Path(path) / f)
    preload = args.preload_dir / "vm_x_fp32.hex"
    t0 = time.monotonic()
    with open(out / "token.log", "w") as log:
        p = subprocess.run([str(binary), "--stages", str(args.stages), str(out), str(preload)], cwd=out,
                           stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, RT_THREADS=str(args.threads)))
    wall = time.monotonic() - t0
    text = (out / "token.log").read_text()
    stage_lines = {m.group(1): m.group(0) for m in re.finditer(r"STAGE (\S+) done .*", text)}
    per_stage = {}
    for name, line in stage_lines.items():
        kv = dict(item.split("=", 1) for item in line.split()[3:])
        per_stage[name] = {"cycles": int(kv["cycles"]), "me_busy": kv["me_busy"], "next_token": kv["next_token"],
                           "next_val": kv["next_val"]}
    oracle = json.loads((args.token_oracle / "oracle.json").read_text()) if args.token_oracle else None
    checks = {}
    for name, *_ in stages:
        if not name.startswith("L"):
            continue
        n = int(name[1:])
        for d in (0, 1):
            got_p = out / f"{name}_die{d}_x.hex"
            want_p = args.token_oracle / f"L{n:02d}_die{d}_x.hex" if args.token_oracle else None
            got = L0.vector(got_p) if got_p.exists() else []
            want = L0.vector(want_p) if want_p and want_p.exists() else []
            checks[f"{name}_die{d}_x"] = {"words": len(got), "mismatches": sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want)),
                                          "actual_sha256": sha(got_p) if got else None,
                                          "expected_sha256": sha(want_p) if want else None}
    m = re.search(r"QWEN_TOKEN_TP2 PASS stages=(\d+) token=(\d+) val=([0-9a-f]+) die1_token=(\d+) cycles=(\d+)", text)
    token = int(m.group(2)) if m else None
    token_ok = bool(m) and oracle is not None and token == oracle.get("next_token") and int(m.group(4)) == token \
        and m.group(3) == oracle.get("next_logit_bits")
    end_pins = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    stable = end_pins == start_pins and all(
        sha(Path(dict(zip(("die0", "die1"), (d0, d1)))[k.split("/")[1]]) / k.split("/")[2]) == v
        for k, v in stage_pins.items() for name, d0, d1, _ in stages if k.split("/")[0] == name)
    good = p.returncode == 0 and token_ok and stable and all(c["mismatches"] == 0 for c in checks.values())
    result = {
        "schema": "opentallas.qwen-rt-token-tp2.v1", "status": "pass" if good else "fail",
        "groups": args.groups, "count_width": args.count_width, "fullshape": args.fullshape,
        "rtl_token": token, "rtl_logit_bits": m.group(3) if m else None,
        "oracle_token": oracle.get("next_token") if oracle else None,
        "oracle_logit_bits": oracle.get("next_logit_bits") if oracle else None,
        "oracle_top2_margin": oracle.get("top2_margin") if oracle else None,
        "total_cycles": int(m.group(5)) if m else None, "stages": per_stage, "layer_x_checks": checks,
        "simulate_wall_seconds": round(wall, 1), "source_sha256": start_pins, "source_stable": stable,
        "stage_image_sha256": stage_pins, "oracle_sha256": sha(args.token_oracle / "oracle.json") if oracle else None,
        "binary_sha256": sha(binary), "generated_core_sha256": sha(core_sv), "steps": steps,
        "claim_boundary": ("Connected Qwen3-8B token 0 at position 0: 36 G6144 TP-2 layers and the lm_head stage on the "
                           "production core, TP sequencer and collective, matrix engine as the gate-qualified sliced "
                           "composition, real checkpoint images. Embedding is preloaded (as the layer-0 bench); stage "
                           "sequencing (image-bank select, per-layer zero KV window) is the host's. Scalar-SU bench "
                           "profile cycles; no physical timing."),
    }
    target = args.result or (out / "token_result.json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "rtl_token": token, "oracle_token": result["oracle_token"],
                      "total_cycles": result["total_cycles"]}, indent=2))
    if not good:
        print(text[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()

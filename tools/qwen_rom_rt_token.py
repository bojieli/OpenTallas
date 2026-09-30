#!/usr/bin/env python3
"""Qwen3-8B O4 ROM die pair at the W12 design point: connected TP-2 token by runtime composition.

Builds (Verilator) the die model (TP sequencer + ot_qwen_rom_core: the production
core, vector stream unit SW = 1,024, matrix engine = the W12 array spine), the
collective, and ONE tile model (ot_qwen_rom_tile_logic) that the host instantiates
G/4 times per die (rtl/test/qwen_rom_runtime/qwen_rom_rt.cpp), then runs the
stage list (36 layers + lm_head, or a prefix) and compares every layer's X and
the token against the G = 5,120 ISA oracle (tools/qwen_o4_token_oracle.py).
Writes a source-pinned record.  Wire stages (BD, XVM, NWS, TWS, ORD) are
parameters, taken from the W12 floorplan.
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
import qwen_rom_rt_core_emit  # noqa: E402

RT = ROOT / "rtl/test/qwen_runtime"
RR = ROOT / "rtl/test/qwen_rom_runtime"
HDC = [p for p in C.HDC if p.name != "ot_hdc_core.sv"]
DIE_RTL = [*HDC, *C.PIPES,
           *(ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_dyn_ttiles", "ot_hdc_qwen_int8_arith",
                                               "ot_hdc_qwen_int8_embed_decode", "ot_hdc_cg", "ot_qwen_me_array")),
           *(ROOT / f"rtl/rom/{n}.sv" for n in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_tp_seq")),
           RR / "ot_qwen_rom_rt_die.sv"]
TILE_RTL = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_fastfp", "ot_hdc_delay",
                                              "ot_hdc_sfu", "ot_hdc_matvec", "ot_qwen_me_array", "ot_qwen_rom_tile")] \
    + [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
COLL_RTL = [ROOT / f"rtl/rom/{n}.sv" for n in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_oneshot_allreduce")]
SOURCES = sorted(set([*DIE_RTL, *TILE_RTL, *COLL_RTL, C.ISA_SVH, ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv",
                      RR / "qwen_rom_rt.cpp", RT / "qwen_rt_matvec.hpp", RT / "qwen_rt_memory.hpp",
                      Path(__file__), ROOT / "tools/qwen_rom_rt_core_emit.py"]))


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def vector(path: Path):
    return [int(x, 16) for x in path.read_text().split()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--stages", type=Path, required=True)
    ap.add_argument("--token-oracle", type=Path, required=True)
    ap.add_argument("--preload", type=Path, required=True)
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--groups", type=int, default=6144)
    ap.add_argument("--count-width", type=int, default=18)
    ap.add_argument("--su-width", type=int, default=1024)
    ap.add_argument("--lv", type=int, default=3)
    ap.add_argument("--smin", type=int, default=6)
    ap.add_argument("--smax", type=int, default=11)
    ap.add_argument("--tcut", type=int, default=6)
    ap.add_argument("--bd", type=int, required=True, help="instruction broadcast / x network stages")
    ap.add_argument("--xvm", type=int, default=1, help="extra vector-memory read registers (the conflict stage)")
    ap.add_argument("--nws", type=int, required=True, help="wire stages into each upper tree level")
    ap.add_argument("--tws", type=int, required=True, help="level-TCUT words to the spine top")
    ap.add_argument("--ord", type=int, default=2, help="result-write stages")
    ap.add_argument("--scale-local", type=int, choices=(0, 1), default=0,
                    help="port-local scale ROM (stage dirs from tools/qwen_rom_scale_local.py)")
    ap.add_argument("--code-banks", type=int, default=10)
    ap.add_argument("--vflags", default="", help="extra Verilator flags for the die model (e.g. W11's "
                    "'--unroll-count 4 -fno-dfg' for an SW=1,024 stream unit)")
    ap.add_argument("--hier-su", action="store_true", help="compile the stream unit as its own hierarchical block")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--result", type=Path)
    args = ap.parse_args()
    G, NW = args.groups, args.count_width
    out = args.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
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

    core_sv = out / "gen" / "ot_qwen_rom_core.sv"
    core_sv.parent.mkdir(exist_ok=True)
    core_sv.write_text(qwen_rom_rt_core_emit.emit(qwen_rom_rt_core_emit.CORE.read_text()))
    vs_sv = out / "gen" / "ot_hdc_vstream_rt.sv"
    vs_sv.write_text(qwen_rom_rt_core_emit.emit_vstream(qwen_rom_rt_core_emit.VSTREAM.read_text()))
    hier = out / "gen" / "hier.vlt"
    hier.write_text('`verilator_config\n' + ''.join(f'hier_block -module "{m}"\n' for m in
                    ("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")
                    + (("ot_hdc_vstream_rt",) if args.hier_su else ())))
    spine = [f"-GSMIN={args.smin}", f"-GSMAX={args.smax}", f"-GTCUT={args.tcut}", f"-GBD={args.bd}",
             f"-GXVM={args.xvm}", f"-GNWS={args.nws}", f"-GTWS={args.tws}", f"-GORD={args.ord}"]
    models = [
        ("die", "ot_qwen_rom_rt_die", [str(core_sv), str(vs_sv), *map(str, DIE_RTL)],
         [f"-GG={G}", f"-GNW={NW}", f"-GSNW={NW}", "-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1",
          f"-GSW={args.su_width}", f"-GLV={args.lv}", f"-GSCALE_LOCAL={args.scale_local}", *spine]),
        ("coll", "ot_rom_oneshot_allreduce", [*map(str, COLL_RTL), *map(str, C.PIPES), *map(str, TILE_RTL[:5])],
         ["-GN=2", "-GLANES=16", "-GTAGW=32", "-GDEPTH=16", "-GLAT=11", "-GBPC_NUM=3600"]),
        ("tile", "ot_qwen_rom_tile_logic", [*map(str, TILE_RTL)],
         [f"-GGT={G}", f"-GNW={NW}", f"-GSMIN={args.smin}", f"-GCODE_BANKS={args.code_banks}", "-GIREG=1",
          f"-GNREG={1 if args.nws > 0 else 0}", "-GKV_LOCAL=0"]),
    ]
    (out / "build_params.json").write_text(json.dumps({p: params for p, _, _, params in models}, indent=1))
    for prefix, top, files, params in models:
        mdir = out / prefix
        if (mdir / f"V{prefix}__ALL.a").exists():
            continue
        run(f"verilate_{prefix}", [args.verilator, "--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "-Wno-WIDTH",
                                   "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-PINMISSING", f"-I{C.ISA_SVH.parent}",
                                   "--top-module", top, "--prefix", f"V{prefix}", "--Mdir", mdir, *params, *files,
                                   *(["--hierarchical", str(hier), *args.vflags.split()] if prefix == "die" else [])])
        run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{args.jobs}", f"V{prefix}__ALL.a",
                                "OPT_FAST=-O2", "OPT_SLOW=-O1"])
    archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}", f"-I{RR}"}
    for prefix, *_ in models:
        archives += sorted((out / prefix).rglob("*.a"))
        includes.add(f"-I{out / prefix}")
        for h in (out / prefix).rglob("V*.h"):
            includes.add(f"-I{h.parent}")
    binary = out / "qwen_rom_rt"
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}",
                 f"-DSWIDTH={args.su_width}", f"-DSMAXB={args.smax}", f"-DTCUTL={args.tcut}", f"-DNWSD={args.nws}",
                 f"-DXVMD={args.xvm}", f"-DCBANKS={args.code_banks}", f"-DSMINV={args.smin}", *sorted(includes), RR / "qwen_rom_rt.cpp", "-Wl,--start-group", *archives,
                 "-Wl,--end-group", f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                 f"{vroot}/include/verilated_dpi.cpp",
                 "-o", binary])
    if args.build_only:
        print("built", binary)
        return
    stages = [line.split() for line in args.stages.read_text().splitlines() if line.strip()]
    stage_pins = {f"{n}/die{d}/{f}": sha(Path(p) / f) for n, d0, d1, _ in stages for d, p in enumerate((d0, d1))
                  for f in ("matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex", "program.hex", "segments.hex")}
    env = dict(os.environ, RT_THREADS=str(args.threads), RT_SCALE_LOCAL=str(args.scale_local))
    t0 = time.monotonic()
    with open(out / "token.log", "w") as log:
        p = subprocess.run([str(binary), "--stages", str(args.stages), str(out), str(args.preload)], cwd=out,
                           stdout=log, stderr=subprocess.STDOUT, env=env)
    wall = time.monotonic() - t0
    text = (out / "token.log").read_text()
    per_stage = {}
    for mm in re.finditer(r"STAGE (\S+) done (.*)", text):
        kv = dict(item.split("=", 1) for item in mm.group(2).split() if "=" in item)
        per_stage[mm.group(1)] = {"cycles": int(kv["cycles"]), "me_clock_edges": kv["me_busy"],
                                  "next_token": kv["next_token"], "next_val": kv["next_val"]}
    oracle = json.loads((args.token_oracle / "oracle.json").read_text())
    checks = {}
    for name, *_ in stages:
        if not name.startswith("L"):
            continue
        n = int(name[1:])
        for d in (0, 1):
            got_p, want_p = out / f"{name}_die{d}_x.hex", args.token_oracle / f"L{n:02d}_die{d}_x.hex"
            got = vector(got_p) if got_p.exists() else []
            want = vector(want_p) if want_p.exists() else []
            checks[f"{name}_die{d}_x"] = {"words": len(got), "mismatches": sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want)),
                                          "actual_sha256": sha(got_p) if got else None, "expected_sha256": sha(want_p) if want else None}
    m = re.search(r"QWEN_ROM_TOKEN_TP2 PASS stages=(\d+) token=(\d+) val=([0-9a-f]+) die1_token=(\d+) cycles=(\d+)", text)
    full = any(n == "head" for n, *_ in stages)
    token = int(m.group(2)) if m else None
    token_ok = (not full) or (bool(m) and token == oracle.get("next_token") and int(m.group(4)) == token
                              and m.group(3) == oracle.get("next_logit_bits"))
    end_pins = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    stable = end_pins == start_pins
    good = p.returncode == 0 and bool(m) and token_ok and stable and all(c["mismatches"] == 0 for c in checks.values())
    result = {
        "schema": "opentallas.qwen-rom-rt-token-tp2.v1", "status": "pass" if good else "fail",
        "design_point": {"groups_per_die": G, "tiles_per_die": G // 4, "count_width": NW, "su_width": args.su_width,
                         "su_reducer_time_levels": args.lv, "smin": args.smin, "smax": args.smax, "tree_cut": args.tcut,
                         "pruned": True, "kv_fp8": True, "scale_local": bool(args.scale_local)},
        "wire_stages": {"broadcast_and_x_network_bd": args.bd, "vm_conflict_register_xvm": args.xvm,
                        "upper_tree_level_nws": args.nws, "tree_to_spine_tws": args.tws, "result_write_ord": args.ord,
                        "engine_latency_added_xd_plus_ord": args.bd + (args.tcut - 2) * args.nws + args.tws + args.ord},
        "verilator_die_flags": args.vflags, "hier_su": args.hier_su,
        "stages_run": [s[0] for s in stages], "rtl_token": token, "rtl_logit_bits": m.group(3) if m else None,
        "oracle_token": oracle.get("next_token"), "oracle_logit_bits": oracle.get("next_logit_bits"),
        "total_cycles": int(m.group(5)) if m else None, "stages": per_stage, "layer_x_checks": checks,
        "simulate_wall_seconds": round(wall, 1), "source_sha256": start_pins, "source_stable": stable,
        "stage_image_sha256": stage_pins, "oracle_sha256": sha(args.token_oracle / "oracle.json"),
        "binary_sha256": sha(binary), "generated_core_sha256": sha(core_sv), "steps": steps,
        "claim_boundary": ("Connected Qwen3-8B token 0 at position 0 (or the listed stage prefix) on the W12 ROM die "
                           "design point: G=5,120 TP-2 dies, the production core with the vector stream unit and the "
                           "array spine, 1,280 tile elements a die composed by the host from one compiled tile model, "
                           "real checkpoint images. Embedding preloaded; stage sequencing (image-bank select, per-layer "
                           "zero KV window) is the host's. Wire stages are parameters; physical timing is not simulated."),
    }
    target = args.result or (out / "token_result.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "rtl_token": token, "oracle_token": result["oracle_token"],
                      "total_cycles": result["total_cycles"]}, indent=2))
    if not good:
        print(text[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()

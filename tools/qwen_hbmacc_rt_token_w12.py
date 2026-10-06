#!/usr/bin/env python3
"""HA8: Qwen3-8B HBM-accelerator token (or stage list) on the W12 datapath with weights and KV streamed from HBM.

Default-off successor of tools/qwen_rom_rt_token_w12.py (unchanged): the same emitted core, tile and collective
models, plus
  * the HA8 die rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12.sv (ME_STALL / KV_HBM gating on the prefetch
    stream, DYN constants for position P, cycle attribution),
  * per die the stream model rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv (NSTK stacks of the r14 streaming
    controller ot_hbm_r14_stream_pc, 52ce3e9c1) in its own 1.024 ns clock domain,
  * the host rtl/test/qwen_rom_runtime/qwen_hbmacc_rt_w12.cpp (position/token, per-layer KV window preload,
    stream plan, preroll).

The STREAM PLAN: per die, every HBM-resident code word of the stage list, and each layer's KV window of
positions < P, in consumption order (qkv, KV, o, gate/up, down).  SRAM residency: the lm_head first, then the
leading code words of the token (layer 0, 1, ...) up to --sram-mib per die.

    --build-only              build models + host into --workdir
    run: --stages --oracle-dir --preload --pos --token [--kv-dir] -> per-stage X / token checked bit-exactly
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as C  # noqa: E402
import qwen_rom_rt_core_emit_w12  # noqa: E402
import qwen_rom_rt_token_w12 as BASE  # noqa: E402
from qwen_rom_arithmetic_contract_w12 import flags as arithmetic_flags  # noqa: E402

RR = ROOT / "rtl/test/qwen_rom_runtime"
DIE_SV = RR / "ot_qwen_hbmacc_rt_die_w12.sv"
HOST = RR / "qwen_hbmacc_rt_w12.cpp"
WST_RTL = [ROOT / "rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv", ROOT / "rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv"]
DIE_RTL = [p for p in BASE.DIE_RTL if p.name != "ot_qwen_rom_rt_die_w12.sv"] + [DIE_SV]
SPINE_H = ROOT / "rtl/hdc/ot_qwen_me_spine_h_w12.sv"   # --spine-h: the hierarchical spine successor
SOURCES = sorted(set([*DIE_RTL, *BASE.TILE_RTL, *BASE.COLL_RTL, *WST_RTL, C.ISA_SVH, ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv",
                      HOST, BASE.RT / "qwen_rt_matvec.hpp", BASE.RT / "qwen_rt_memory.hpp", Path(__file__),
                      ROOT / "tools/qwen_rom_rt_token_w12.py", ROOT / "tools/qwen_rom_rt_core_emit_w12.py",
                      ROOT / "tools/qwen_rom_arithmetic_contract_w12.py", SPINE_H]))
WORD_BYTES = 6144 * 16          # one engine code word = one stream word
MIB = 1 << 20


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def vector(path: Path):
    return [int(x, 16) for x in path.read_text().split()]


# ------------------------------------------------------------------------------------------------ stream plan
def stage_segments(name: str, layout: list, head_words: int, kv_words: int):
    """Code segments (base, len) in consumption order, KV marker as ('KV', words)."""
    if name == "head":
        return [("lm_head", 0, head_words)]
    segs = []
    for m in sorted(layout, key=lambda r: r["base"]):
        segs.append((m["name"], m["base"], m["code_span_words"]))
        if m["name"] == "qkv" and kv_words:
            segs.append(("KV", None, kv_words))
    return segs


def make_plan(stage_names, layout, head_words, kv_words, sram_words, preroll_words=0, spread=False):
    """Returns (plan text, summary).  Kinds: 1 HBM code, 2 SRAM code, 3 KV (HBM).  sram_words: per-die budget
    for code words beyond the lm_head, given to the token's leading code words in order (layer 0 first) --
    the layer index decides, so a single-stage job of layer n reproduces the full token's assignment.
    spread=True (opt-in, --sram-spread): the same budget split evenly over the 36 layers instead (layer n gets
    sram_words // 36, plus one for n < sram_words % 36), each layer's share being its leading code words, so every
    layer streams most of its words and its SRAM part overlaps the stream."""
    lines, summary = [], []
    sidx = 0
    # SRAM assignment by absolute token order: layers 0..35 x code words
    per_layer = sum(m["code_span_words"] for m in layout)
    for name in stage_names:
        segs = []
        hbm_w = res_w = 0
        if name == "head":
            segs.append((0, head_words, 0, 2)); res_w += head_words
        else:
            n = int(name[1:])
            before = n * per_layer            # code words of earlier layers in token order
            left = max(0, sram_words - before)
            if spread:
                left = min(per_layer, sram_words // 36 + (1 if n < sram_words % 36 else 0))
            for nm, base, ln in stage_segments(name, layout, head_words, kv_words):
                if nm == "KV":
                    segs.append((0, ln, sidx, 3)); sidx += ln; hbm_w += ln
                    continue
                r = min(ln, left); left -= r
                if r:
                    segs.append((base, r, 0, 2)); res_w += r
                if ln - r:
                    segs.append((base + r, ln - r, sidx, 1)); sidx += ln - r; hbm_w += ln - r
        if len(segs) > 8:
            raise SystemExit(f"{name}: more than 8 segments")
        lines.append(f"STAGE {name} {len(segs)} " + " ".join(f"{b} {l} {s} {k}" for b, l, s, k in segs))
        summary.append({"stage": name, "hbm_words": hbm_w, "sram_words": res_w, "segments": segs})
    return "TOTAL %d\n" % sidx + "\n".join(lines) + "\n", summary, sidx


# ------------------------------------------------------------------------------------------------ build
def build(args, out: Path, steps: list):
    G, NW = args.groups, args.count_width
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([args.verilator, "-V"], text=True)).group(1)
    arithmetic = arithmetic_flags(args.arith_target)

    def run(name, cmd):
        t0 = time.monotonic()
        p = subprocess.run(["/usr/bin/time", "-f", "%M", "-o", str(out / f"{name}.rss"), *map(str, cmd)],
                           cwd=out, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append({"name": name, "seconds": round(time.monotonic() - t0, 2), "returncode": p.returncode})
        if p.returncode:
            raise SystemExit(f"{name} failed; see {out / (name + '.log')}\n{(p.stdout + p.stderr)[-3000:]}")

    gen = out / "gen"
    gen.mkdir(exist_ok=True)
    core_sv = gen / "ot_qwen_rom_core.sv"
    core_text = qwen_rom_rt_core_emit_w12.emit(qwen_rom_rt_core_emit_w12.CORE.read_text())
    if args.spine_h:
        if core_text.count("ot_qwen_me_spine_w12 #(") != 1:
            raise SystemExit("spine instance anchor")
        core_text = core_text.replace("ot_qwen_me_spine_w12 #(", f"ot_qwen_me_spine_h_w12 #(.SCALE_LAT({args.scale_lat}), ")
    core_sv.write_text(core_text)
    vs_sv = gen / "ot_hdc_vstream_rt.sv"
    vs_sv.write_text(qwen_rom_rt_core_emit_w12.emit_vstream(qwen_rom_rt_core_emit_w12.VSTREAM.read_text()))
    hier = gen / "hier.vlt"
    hier.write_text('`verilator_config\n' + ''.join(f'hier_block -module "{m}"\n' for m in
                    ("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")))
    spine = [f"-GSMIN={args.smin}", f"-GSMAX={args.smax}", f"-GTCUT={args.tcut}", f"-GBD={args.bd}",
             f"-GXVM={args.xvm}", f"-GNWS={args.nws}", f"-GTWS={args.tws}", f"-GORD={args.ord}"]
    models = [
        ("die", "ot_qwen_hbmacc_rt_die_w12", [str(core_sv), str(vs_sv), *map(str, DIE_RTL),
                                              *([str(SPINE_H), str(ROOT / "rtl/hdc/ot_hdc_fp32_mul_lat.sv")] if args.spine_h else [])],
         [f"-GG={G}", f"-GNW={NW}", f"-GSNW={NW}", "-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1", f"-GD={args.tp}",
          f"-GSW={args.su_width}", f"-GLV={args.lv}", "-GSCALE_LOCAL=0", f"-GMEM_EXTRA={args.mem_extra}",
          f"-GENABLE_AR256={int(args.enable_ar256)}", f"-GLAGW={args.lagw}", *spine, *arithmetic,
          *([f"-DOT_SPINE_H_SCALE_LAT={args.scale_lat}"] if args.spine_h else [])]),
        ("coll", "ot_rom_oneshot_allreduce", [*map(str, BASE.COLL_RTL), *map(str, C.PIPES), *map(str, BASE.TILE_RTL[:5])],
         [f"-GN={args.tp}", "-GLANES=16", "-GTAGW=32", f"-GDEPTH={args.coll_depth}", f"-GLAT={args.coll_lat}", "-GBPC_NUM=3600"]),
        ("tile", "ot_qwen_rom_tile_logic_w12", [*map(str, BASE.TILE_RTL)],
         [f"-GGT={G}", f"-GNW={NW}", f"-GSMIN={args.smin}", f"-GCODE_BANKS={args.code_banks}", "-GIREG=1",
          f"-GMEM_EXTRA={args.mem_extra}", f"-GNREG={1 if args.nws > 0 else 0}", "-GKV_LOCAL=0", *arithmetic]),
        ("wst", "ot_hbmacc_qwen_wstream", [*map(str, WST_RTL)],
         ["-GENABLE=1", f"-GNSTK={args.stacks}", f"-GREF_MODE={args.ref_mode}", f"-GWINW={args.winw}",
          f"-GSPW={WORD_BYTES // 32 // (32 * args.stacks)}", f"-GCRED={args.cred}"]),
    ]
    if WORD_BYTES % (32 * 32 * args.stacks):
        raise SystemExit("stream word does not divide evenly over the PCs")
    bp = out / "build_params.json"
    prior = json.loads(bp.read_text()) if bp.exists() else {}
    bp.write_text(json.dumps({p: params for p, _, _, params in models}, indent=1))
    for prefix, top, files, params in models:
        mdir = out / prefix
        if (mdir / f"V{prefix}__ALL.a").exists() and prior.get(prefix) == params:
            continue
        subprocess.run(["rm", "-rf", str(mdir)], check=True)
        run(f"verilate_{prefix}", [args.verilator, "--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "-Wno-WIDTH",
                                   "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-PINMISSING", f"-I{C.ISA_SVH.parent}",
                                   "--top-module", top, "--prefix", f"V{prefix}", "--Mdir", mdir, *params, *files,
                                   *(["--hierarchical", str(hier)] if prefix == "die" else [])])
        run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{args.jobs}", f"V{prefix}__ALL.a",
                                "OPT_FAST=-O2", "OPT_SLOW=-O1"])
    archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{BASE.RT}", f"-I{RR}"}
    for prefix, *_ in models:
        archives += sorted((out / prefix).rglob("*.a"))
        includes.add(f"-I{out / prefix}")
        for h in (out / prefix).rglob("V*.h"):
            includes.add(f"-I{h.parent}")
    binary = out / "qwen_hbmacc_rt"
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}",
                 f"-DSWIDTH={args.su_width}", f"-DSMAXB={args.smax}", f"-DTCUTL={args.tcut}", f"-DNWSD={args.nws}",
                 f"-DXVMD={args.xvm}", f"-DTPD={args.tp}", f"-DCBANKS={args.code_banks}", f"-DSMINV={args.smin}",
                 *sorted(includes), HOST, "-Wl,--start-group", *archives, "-Wl,--end-group",
                 f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp", f"{vroot}/include/verilated_dpi.cpp",
                 "-o", binary])
    return binary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True, help="run outputs")
    ap.add_argument("--build-dir", type=Path, help="models and binary (default: the workdir)")
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    # W12 design point (defaults: the retained TP2 G6144 SW64 token, results/rtl/qwen_rom_w12_runtime/terminal_20261001)
    ap.add_argument("--tp", type=int, choices=(2, 4), default=2)
    ap.add_argument("--groups", type=int, default=6144)
    ap.add_argument("--count-width", type=int, default=18)
    ap.add_argument("--su-width", type=int, default=64)
    ap.add_argument("--lv", type=int, default=7)
    ap.add_argument("--smin", type=int, default=6)
    ap.add_argument("--smax", type=int, default=11)
    ap.add_argument("--tcut", type=int, default=6)
    ap.add_argument("--bd", type=int, default=31)
    ap.add_argument("--xvm", type=int, default=1)
    ap.add_argument("--nws", type=int, default=4)
    ap.add_argument("--tws", type=int, default=30)
    ap.add_argument("--ord", type=int, default=4)
    ap.add_argument("--mem-extra", type=int, choices=(0, 1), default=0)
    ap.add_argument("--code-banks", type=int, default=10)
    ap.add_argument("--coll-lat", type=int, default=11)
    ap.add_argument("--coll-depth", type=int, default=16)
    ap.add_argument("--enable-ar256", action="store_true")
    ap.add_argument("--arith-target", action="store_true",
                    help="1.2 GHz ME arithmetic (tools/qwen_rom_arithmetic_contract_w12.py TARGET: ACC/TREE_LAT 7, MUL_LAT 6, "
                         "FAST_ISSUE 1, KV_PREP 3) on the die and tile models; default off")
    ap.add_argument("--spine-h", action="store_true",
                    help="the die core's ME spine is ot_qwen_me_spine_h_w12 (hierarchical successor); default off")
    ap.add_argument("--scale-lat", type=int, choices=(5, 6), default=6,
                    help="--spine-h post-scale multiplier latency (6: ot_hdc_fp32_mul_lat, closes at SS)")
    # HA8 memory system
    ap.add_argument("--stacks", type=int, default=4, help="HBM stacks per die")
    ap.add_argument("--ref-mode", type=int, choices=(0, 1), default=1)
    ap.add_argument("--winw", type=int, default=160, help="prefetch window, stream words (98,304 B each)")
    ap.add_argument("--lagw", type=int, default=40, help="words between the spine's read and the window release")
    ap.add_argument("--cred", type=int, default=32)
    ap.add_argument("--sram-mib", type=float, default=None,
                    help="die SRAM for weights (MiB per die); default: design point (a) 842 MiB / 2 dies, (b) 1,686 / 4")
    ap.add_argument("--sram-spread", action="store_true",
                    help="opt-in: split the layer SRAM budget evenly over the 36 layers (default: leading layers)")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--build-only", action="store_true")
    # run
    ap.add_argument("--stages", type=Path)
    ap.add_argument("--layout", type=Path, help="a layer<n>_rom.json of the stage images (matrix layout)")
    ap.add_argument("--head-words", type=int, default=None, help="lm_head code words per die (TP2 3,168)")
    ap.add_argument("--oracle-dir", type=Path, help="position-oracle P dir (L<nn>_die<d>_x.hex, head.json) or a P0 token oracle")
    ap.add_argument("--preload", type=Path)
    ap.add_argument("--pos", type=int, default=0)
    ap.add_argument("--token", type=int, default=0)
    ap.add_argument("--kv-dir", type=Path)
    ap.add_argument("--preroll", type=int, default=0, help="stream controller cycles before the first core edge")
    ap.add_argument("--max-cycles", type=int, default=400000000)
    ap.add_argument("--result", type=Path)
    args = ap.parse_args()
    out = args.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    bdir = (args.build_dir or args.workdir).resolve()
    bdir.mkdir(parents=True, exist_ok=True)
    start_pins = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    steps = []
    binary = bdir / "qwen_hbmacc_rt"
    if args.build_only or not binary.exists():
        binary = build(args, bdir, steps)
    if args.build_only:
        print("built", binary)
        return
    stages = [line.split() for line in args.stages.read_text().splitlines() if line.strip()]
    layout = json.loads(args.layout.read_text())["matrix_layout"]
    head_words = args.head_words if args.head_words is not None else (3168 if args.tp == 2 else 1584)
    kvh = 8 // args.tp
    kv_words = math.ceil(2 * kvh * args.pos * 128 / WORD_BYTES) if args.pos else 0
    sram_mib = args.sram_mib if args.sram_mib is not None else (842.0 / 2 if args.tp == 2 else 1686.0 / 4)
    head_bytes = head_words * WORD_BYTES
    sram_words = max(0, int((sram_mib * MIB - head_bytes - args.winw * WORD_BYTES) // WORD_BYTES))
    plan_text, plan_summary, total = make_plan([s[0] for s in stages], layout, head_words, kv_words, sram_words,
                                                spread=args.sram_spread)
    (out / "plan.txt").write_text(plan_text)
    env = dict(os.environ, RT_THREADS=str(args.threads))
    cmd = [str(binary), "--stages", str(args.stages), str(out), str(args.preload), "--plan", str(out / "plan.txt"),
           "--pos", str(args.pos), "--token", str(args.token), "--preroll", str(args.preroll), "--max-cycles", str(args.max_cycles)]
    if args.kv_dir:
        cmd += ["--kv-dir", str(args.kv_dir)]
    t0 = time.monotonic()
    with open(out / "token.log", "w") as log:
        p = subprocess.run(cmd, cwd=out, stdout=log, stderr=subprocess.STDOUT, env=env)
    wall = time.monotonic() - t0
    text = (out / "token.log").read_text()
    per_stage = {}
    for mm in re.finditer(r"STAGE (\S+) done (.*)", text):
        kv = dict(item.split("=", 1) for item in mm.group(2).split() if "=" in item)
        per_stage[mm.group(1)] = {"cycles": int(kv["cycles"]), "start_cyc": int(kv["start_cyc"]), "end_cyc": int(kv["end_cyc"]),
                                  "me_clock_edges": kv["me_busy"],
                                  "next_token": kv["next_token"], "next_val": kv["next_val"]}
    for mm in re.finditer(r"HBMSTAT (\S+) die(\d+) (.*)", text):
        kv = {k: int(v) for k, v in (item.split("=", 1) for item in mm.group(3).split())}
        per_stage.setdefault(mm.group(1), {})[f"die{mm.group(2)}"] = kv
    checks = {}
    for name, *_ in stages:
        if not name.startswith("L"):
            continue
        n = int(name[1:])
        for d in range(args.tp):
            got_p, want_p = out / f"{name}_die{d}_x.hex", args.oracle_dir / f"L{n:02d}_die{d}_x.hex"
            got = vector(got_p) if got_p.exists() else []
            want = vector(want_p) if want_p.exists() else []
            checks[f"{name}_die{d}_x"] = {"words": len(got), "mismatches": sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want)),
                                          "actual_sha256": sha(got_p) if got else None, "expected_sha256": sha(want_p) if want else None}
    m = re.search(r"QWEN_HBMACC_TOKEN PASS stages=(\d+) token=(\d+) val=([0-9a-f]+) die1_token=(\d+) cycles=(\d+)", text)
    full = any(n == "head" for n, *_ in stages)
    ofile = args.oracle_dir / "head.json"
    oracle = json.loads(ofile.read_text()) if ofile.exists() else json.loads((args.oracle_dir / "oracle.json").read_text())
    token = int(m.group(2)) if m else None
    token_ok = (not full) or (bool(m) and token == oracle.get("next_token") and int(m.group(4)) == token
                              and m.group(3) == oracle.get("next_logit_bits"))
    end_pins = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    stable = end_pins == start_pins
    good = p.returncode == 0 and bool(m) and token_ok and stable and all(c["mismatches"] == 0 for c in checks.values())
    result = {
        "schema": "opentallas.hbm-accel-qwen-token.v1", "status": "pass" if good else "fail",
        "design_point": {"tp": args.tp, "groups_per_die": args.groups, "su_width": args.su_width, "lv": args.lv,
                         "smin": args.smin, "smax": args.smax, "tcut": args.tcut, "bd": args.bd, "xvm": args.xvm,
                         "nws": args.nws, "tws": args.tws, "ord": args.ord, "mem_extra": args.mem_extra,
                         "code_banks": args.code_banks, "coll_lat": args.coll_lat, "coll_depth": args.coll_depth,
                         "ar256": bool(args.enable_ar256), "arith_target": bool(args.arith_target),
                         "spine_h": bool(args.spine_h), "scale_lat": args.scale_lat if args.spine_h else 5},
        "memory_system": {"stacks_per_die": args.stacks, "ref_mode": args.ref_mode, "window_words": args.winw,
                          "window_mib": round(args.winw * WORD_BYTES / MIB, 2), "lag_words": args.lagw, "cred": args.cred,
                          "sram_mib_per_die": sram_mib, "sram_code_words_beyond_head": sram_words, "sram_spread": args.sram_spread, "head_words": head_words,
                          "kv_words_per_layer": kv_words, "stream_words": total, "preroll_ctl_cycles": args.preroll,
                          "core_clock_ps": 833.333, "hbm_ctl_clock_ps": 1024},
        "position": args.pos, "token_in": args.token, "stages_run": [s[0] for s in stages], "plan": plan_summary,
        "rtl_token": token, "rtl_logit_bits": m.group(3) if m else None,
        "oracle_token": oracle.get("next_token"), "oracle_logit_bits": oracle.get("next_logit_bits"),
        "total_cycles": int(m.group(5)) if m else None, "stages": per_stage, "layer_x_checks": checks,
        "simulate_wall_seconds": round(wall, 1), "source_sha256": start_pins, "source_stable": stable,
        "oracle_dir": str(args.oracle_dir), "kv_dir": str(args.kv_dir) if args.kv_dir else None,
        "binary_sha256": sha(binary), "steps": steps,
        "claim_boundary": "HA8 vehicle: the W12 exact datapath (static schedule, lane-local fusion, no kernel launch) with "
                          "every HBM-resident code word and the KV window timed by the r14 streaming controller; window data "
                          "are served from the stage images (arrival timed, not carried); SS/FF, area and routing not claimed.",
    }
    target = args.result or (out / "token_result.json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "rtl_token": token, "oracle_token": result["oracle_token"],
                      "total_cycles": result["total_cycles"], "stages": {k: v.get("cycles") for k, v in per_stage.items()}}, indent=1))
    if not good:
        print(text[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Qwen3-8B HBM accelerator: the DSpark VERIFY layer (p positions) with weights and KV streamed from HBM.

Default-off successor of tools/qwen_hbmacc_rt_token_w12.py (HA8, unchanged) that combines it with the ROM verify
vehicle of tools/qwen_rom_rt_verify_w12.py (unchanged):
  * die rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12_vp.sv: the HA8 die with the VPOS core
    (tools/qwen_rom_verify_core_emit_w12.py), the sequencer successor ot_qwen_tp_seq_w12_vp (ENABLE_ARP) and
    MULTI-POSITION WEIGHT REUSE: the p-position program (tools/qwen_rom_verify_program_w12.py) issues every dense
    matvec p times back to back, so each HBM code word is read p times from the prefetch window while resident;
    a window slot is released on its p-th read (use counter), and a read of a released word faults;
  * per die the HA8 stream model (ot_hbmacc_qwen_wstream: r14 streaming controller, CK/2 domain, NSTK stacks);
  * host rtl/test/qwen_rom_runtime/qwen_hbmacc_rt_w12_vp.cpp (HA8 host + the VP host's verify changes + --nuse).

The stream plan is the HA8 plan (tools/qwen_hbmacc_rt_token_w12.make_plan): code words in consumption order with
the layer's KV window of positions < P0 after qkv; the KV words a verify block writes (P0 .. P0+p-1) are the
program's own writes.  The window must hold the largest matvec plus the release lag (checked here).

Exactness: every position's X after the layer is compared bit for bit with the golden of that position (the AR
decode at P0 + j: tools/qwen_hbmacc_position_oracle_gpu.py / tools/qwen_rom_position_oracle_gpu.py); with
--expect-head, the per-position argmax records are compared with the golden heads.

    --build-only    build the models and the host into --build-dir
    run: --stages --layout --preload --xbases --positions --pos --kv-dir --expect-x JSON [--preroll --winw ...]
"""
from __future__ import annotations

import argparse
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
import qwen_rom_verify_core_emit_w12  # noqa: E402
import qwen_rom_rt_token_w12 as BASE  # noqa: E402
import qwen_hbmacc_rt_token_w12 as HA  # noqa: E402
from qwen_rom_arithmetic_contract_w12 import flags as arithmetic_flags  # noqa: E402

RR = ROOT / "rtl/test/qwen_rom_runtime"
DIE_SV = RR / "ot_qwen_hbmacc_rt_die_w12_vp.sv"
HOST = RR / "qwen_hbmacc_rt_w12_vp.cpp"
SEQ_VP = ROOT / "rtl/rom/ot_qwen_tp_seq_w12_vp.sv"
USECOUNT = ROOT / "rtl/hbm_accel/qwen/ot_hbmacc_win_usecount.sv"
DIE_RTL = [p for p in BASE.DIE_RTL if p.name not in ("ot_qwen_rom_rt_die_w12.sv", "ot_qwen_tp_seq_w12.sv")] + [SEQ_VP, USECOUNT, DIE_SV]
SOURCES = sorted(set([*DIE_RTL, *BASE.TILE_RTL, *BASE.COLL_RTL, *HA.WST_RTL, C.ISA_SVH,
                      ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv", HOST, BASE.RT / "qwen_rt_matvec.hpp",
                      BASE.RT / "qwen_rt_memory.hpp", Path(__file__), ROOT / "tools/qwen_hbmacc_rt_token_w12.py",
                      ROOT / "tools/qwen_rom_rt_token_w12.py", ROOT / "tools/qwen_rom_rt_core_emit_w12.py",
                      ROOT / "tools/qwen_rom_verify_core_emit_w12.py", ROOT / "tools/qwen_rom_arithmetic_contract_w12.py"]))
WORD_BYTES = HA.WORD_BYTES
MIB = HA.MIB


def build(args, out: Path, steps: list):
    G, NW = args.groups, args.count_width
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([args.verilator, "-V"], text=True)).group(1)
    arithmetic = arithmetic_flags(False)

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
    core_sv.write_text(qwen_rom_verify_core_emit_w12.emit(qwen_rom_rt_core_emit_w12.CORE.read_text()))
    vs_sv = gen / "ot_hdc_vstream_rt.sv"
    vs_sv.write_text(qwen_rom_rt_core_emit_w12.emit_vstream(qwen_rom_rt_core_emit_w12.VSTREAM.read_text()))
    hier = gen / "hier.vlt"
    hier.write_text('`verilator_config\n' + ''.join(f'hier_block -module "{m}"\n' for m in
                    ("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")))
    spine = [f"-GSMIN={args.smin}", f"-GSMAX={args.smax}", f"-GTCUT={args.tcut}", f"-GBD={args.bd}",
             f"-GXVM={args.xvm}", f"-GNWS={args.nws}", f"-GTWS={args.tws}", f"-GORD={args.ord}"]
    models = [
        ("die", "ot_qwen_hbmacc_rt_die_w12_vp", [str(core_sv), str(vs_sv), *map(str, DIE_RTL)],
         [f"-GG={G}", f"-GNW={NW}", f"-GSNW={NW}", "-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1", f"-GD={args.tp}",
          f"-GSW={args.su_width}", f"-GLV={args.lv}", "-GSCALE_LOCAL=0", f"-GMEM_EXTRA={args.mem_extra}",
          f"-GENABLE_AR256={int(args.enable_ar256)}", f"-GLAGW={args.lagw}", f"-GVPOS={args.vpos}",
          f"-GENABLE_ARP={args.enable_arp}", "-GVWA=12", f"-GUSE_HW_RELEASE={int(args.hw_release)}", *spine, *arithmetic]),
        ("coll", "ot_rom_oneshot_allreduce", [*map(str, BASE.COLL_RTL), *map(str, C.PIPES), *map(str, BASE.TILE_RTL[:5])],
         [f"-GN={args.tp}", "-GLANES=16", "-GTAGW=32", f"-GDEPTH={args.coll_depth}", f"-GLAT={args.coll_lat}", "-GBPC_NUM=3600"]),
        ("tile", "ot_qwen_rom_tile_logic_w12", [*map(str, BASE.TILE_RTL)],
         [f"-GGT={G}", f"-GNW={NW}", f"-GSMIN={args.smin}", f"-GCODE_BANKS={args.code_banks}", "-GIREG=1",
          f"-GMEM_EXTRA={args.mem_extra}", f"-GNREG={1 if args.nws > 0 else 0}", "-GKV_LOCAL=0", *arithmetic]),
        ("wst", "ot_hbmacc_qwen_wstream", [*map(str, HA.WST_RTL)],
         ["-GENABLE=1", f"-GNSTK={args.stacks}", f"-GREF_MODE={args.ref_mode}", f"-GWINW={args.winw}",
          f"-GSPW={WORD_BYTES // 32 // (32 * args.stacks)}", f"-GCRED={args.cred}"]),
    ]
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
    binary = out / "qwen_hbmacc_rt_vp"
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}",
                 f"-DSWIDTH={args.su_width}", f"-DSMAXB={args.smax}", f"-DTCUTL={args.tcut}", f"-DNWSD={args.nws}",
                 f"-DXVMD={args.xvm}", f"-DTPD={args.tp}", f"-DCBANKS={args.code_banks}", f"-DSMINV={args.smin}",
                 *sorted(includes), HOST, "-Wl,--start-group", *archives, "-Wl,--end-group",
                 f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp", f"{vroot}/include/verilated_dpi.cpp",
                 "-o", binary])
    return binary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--build-dir", type=Path)
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    # W12 design point: the HA8 defaults (tools/qwen_hbmacc_rt_token_w12.py)
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
    ap.add_argument("--vpos", type=int, choices=(0, 1), default=1)
    ap.add_argument("--hw-release", action="store_true",
                    help="window release by the synthesizable rtl/hbm_accel/qwen/ot_hbmacc_win_usecount.sv (+2 cycles)")
    ap.add_argument("--enable-arp", type=int, choices=(0, 1), default=1)
    # memory system (HA8)
    ap.add_argument("--stacks", type=int, default=4)
    ap.add_argument("--ref-mode", type=int, choices=(0, 1), default=1)
    ap.add_argument("--winw", type=int, default=640, help="prefetch window, stream words; >= largest matvec + lagw")
    ap.add_argument("--lagw", type=int, default=40)
    ap.add_argument("--cred", type=int, default=32)
    ap.add_argument("--sram-mib", type=float, default=0.0,
                    help="die SRAM for weights per die (0: the stage's code words all stream from HBM)")
    ap.add_argument("--sram-spread", action="store_true", help="split the layer SRAM budget evenly over the 36 layers")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--build-only", action="store_true")
    # run
    ap.add_argument("--stages", type=Path, help="HA8 stage list: <name> <die image dirs...> <kv_reset> (verify images)")
    ap.add_argument("--layout", type=Path, help="layer<n>_rom.json of the AR images (matrix layout)")
    ap.add_argument("--head-words", type=int, default=None)
    ap.add_argument("--preload", type=Path, help="multi-position X preload (@base sections)")
    ap.add_argument("--positions", type=int, default=4)
    ap.add_argument("--xbases", required=False, default="")
    ap.add_argument("--pos", type=int, default=0, help="P0: first position of the verify block")
    ap.add_argument("--token", type=int, default=0)
    ap.add_argument("--kv-dir", type=Path, help="KV window of positions < P0 (oracle kv_pre of P0)")
    ap.add_argument("--expect-x", type=Path, help="JSON {p<j>_die<d>: golden X hex}")
    ap.add_argument("--expect-head", type=Path, help="JSON [{argmax_token, logit_bits}] per position (head stages)")
    ap.add_argument("--vm-elems", type=int, default=1 << 20)
    ap.add_argument("--nuse", type=int, default=None, help="window uses per HBM code word (default: --positions)")
    ap.add_argument("--preroll", type=int, default=0)
    ap.add_argument("--max-cycles", type=int, default=400000000)
    ap.add_argument("--result", type=Path)
    args = ap.parse_args()
    out = args.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    bdir = (args.build_dir or args.workdir).resolve()
    bdir.mkdir(parents=True, exist_ok=True)
    start_pins = {str(p.relative_to(ROOT)): HA.sha(p) for p in SOURCES}
    steps = []
    binary = bdir / "qwen_hbmacc_rt_vp"
    if args.build_only or not binary.exists():
        binary = build(args, bdir, steps)
    if args.build_only:
        print("built", binary)
        return
    nuse = args.nuse if args.nuse is not None else args.positions
    stages = [line.split() for line in args.stages.read_text().splitlines() if line.strip()]
    layout = json.loads(args.layout.read_text())["matrix_layout"]
    biggest = max(m["code_span_words"] for m in layout)
    if nuse > 1 and args.winw < biggest + args.lagw + 8:
        raise SystemExit(f"window {args.winw} words cannot hold the largest matvec ({biggest}) + lag ({args.lagw})")
    head_words = args.head_words if args.head_words is not None else (3168 if args.tp == 2 else 1584)
    kvh = 8 // args.tp
    kv_words = math.ceil(2 * kvh * args.pos * 128 / WORD_BYTES) if args.pos else 0
    head_bytes = head_words * WORD_BYTES
    sram_words = max(0, int((args.sram_mib * MIB - head_bytes - args.winw * WORD_BYTES) // WORD_BYTES))
    plan_text, plan_summary, total = HA.make_plan([s[0] for s in stages], layout, head_words, kv_words, sram_words,
                                                  spread=args.sram_spread)
    (out / "plan.txt").write_text(plan_text)
    xbases = [int(x) for x in args.xbases.split(",") if x]
    if xbases and len(xbases) != args.positions:
        raise SystemExit("--xbases must list --positions bases")
    env = dict(os.environ, RT_THREADS=str(args.threads), RT_VM_ELEMS=str(args.vm_elems))
    if xbases:
        env["RT_XBASES"] = ",".join(map(str, xbases))
    cmd = [str(binary), "--stages", str(args.stages), str(out), str(args.preload), "--plan", str(out / "plan.txt"),
           "--pos", str(args.pos), "--token", str(args.token), "--preroll", str(args.preroll),
           "--max-cycles", str(args.max_cycles), "--nuse", str(nuse)]
    if args.kv_dir:
        cmd += ["--kv-dir", str(args.kv_dir)]
    (out / "cmd.txt").write_text(" ".join(cmd) + "\n")
    t0 = time.monotonic()
    with open(out / "token.log", "w") as log:
        p = subprocess.run(cmd, cwd=out, stdout=log, stderr=subprocess.STDOUT, env=env)
    wall = time.monotonic() - t0
    text = (out / "token.log").read_text()
    per_stage = {}
    for mm in re.finditer(r"STAGE (\S+) done (.*)", text):
        kv = dict(item.split("=", 1) for item in mm.group(2).split() if "=" in item)
        per_stage[mm.group(1)] = {"cycles": int(kv["cycles"]), "start_cyc": int(kv["start_cyc"]), "end_cyc": int(kv["end_cyc"]),
                                  "me_clock_edges": kv["me_busy"]}
    for mm in re.finditer(r"HBMSTAT (\S+) die(\d+) (.*)", text):
        kv = {k: int(v) for k, v in (item.split("=", 1) for item in mm.group(3).split())}
        per_stage.setdefault(mm.group(1), {})[f"die{mm.group(2)}"] = kv
    for mm in re.finditer(r"VPSTAT (\S+) die(\d+) (.*)", text):
        kv = {k: int(v) for k, v in (item.split("=", 1) for item in mm.group(3).split())}
        per_stage.setdefault(mm.group(1), {}).setdefault(f"die{mm.group(2)}", {}).update(kv)
    checks = {}
    if args.expect_x:
        exp = json.loads(args.expect_x.read_text())
        for name, *_ in stages:
            if not name.startswith("L"):
                continue
            for d in range(args.tp):
                for j in range(args.positions if xbases else 1):
                    key = f"p{j}_die{d}"
                    got_p = out / (f"{name}_p{j}_die{d}_x.hex" if xbases else f"{name}_die{d}_x.hex")
                    want_p = Path(exp[key])
                    got = HA.vector(got_p) if got_p.exists() else []
                    want = HA.vector(want_p) if want_p.exists() else []
                    checks[f"{name}_{key}_x"] = {"words": len(got), "mismatches": sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want)),
                                                 "actual_sha256": HA.sha(got_p) if got else None,
                                                 "expected_sha256": HA.sha(want_p) if want else None, "expected": str(want_p)}
    m = re.search(r"QWEN_HBMACC_TOKEN PASS stages=(\d+) token=(\d+) val=([0-9a-f]+) die1_token=(\d+) cycles=(\d+)", text)
    full = any(n == "head" for n, *_ in stages)
    head_ok = True
    vt = {int(mm.group(1)): mm.group(2).split() for mm in re.finditer(r"VERIFY_TOKENS die=(\d+) n=\d+(.*)", text)}
    if full:
        heads = json.loads(args.expect_head.read_text()) if args.expect_head else None
        want = [f"t{j}={h['argmax_token']}/{h['logit_bits']}" for j, h in enumerate(heads[:args.positions])] if heads else None
        head_ok = bool(want) and len(vt) == args.tp and all(v == want for v in vt.values())
    end_pins = {str(q.relative_to(ROOT)): HA.sha(q) for q in SOURCES}
    stable = end_pins == start_pins
    reads_ok = all(per_stage[s].get(f"die{d}", {}).get("hbm_code_reads", -1) ==
                   nuse * next(x["hbm_words"] - sum(sg[1] for sg in x["segments"] if sg[3] == 3) for x in plan_summary if x["stage"] == s)
                   for s in per_stage for d in range(args.tp) if s != "head" and f"die{d}" in per_stage[s])
    good = (p.returncode == 0 and bool(m) and head_ok and stable and all(c["mismatches"] == 0 for c in checks.values())
            and (bool(checks) or full))
    result = {
        "schema": "opentallas.hbm-accel-qwen-verify-layer.v1", "status": "pass" if good else "fail",
        "verify": {"positions": args.positions, "pos0": args.pos, "x_bases": xbases, "nuse": nuse,
                   "per_die_tokens": vt, "head_exact": head_ok if full else None,
                   "hbm_code_reads_equal_nuse_x_words": reads_ok},
        "design_point": {"tp": args.tp, "groups_per_die": args.groups, "su_width": args.su_width, "lv": args.lv,
                         "smin": args.smin, "smax": args.smax, "tcut": args.tcut, "bd": args.bd, "xvm": args.xvm,
                         "nws": args.nws, "tws": args.tws, "ord": args.ord, "mem_extra": args.mem_extra,
                         "code_banks": args.code_banks, "coll_lat": args.coll_lat, "coll_depth": args.coll_depth,
                         "ar256": bool(args.enable_ar256), "hw_release": bool(args.hw_release), "vpos": args.vpos, "enable_arp": args.enable_arp},
        "memory_system": {"stacks_per_die": args.stacks, "ref_mode": args.ref_mode, "window_words": args.winw,
                          "window_mib": round(args.winw * WORD_BYTES / MIB, 2), "lag_words": args.lagw, "cred": args.cred,
                          "sram_mib_per_die": args.sram_mib, "sram_code_words_beyond_head": sram_words, "sram_spread": args.sram_spread,
                          "head_words": head_words, "kv_words_per_layer": kv_words, "stream_words": total,
                          "preroll_ctl_cycles": args.preroll, "largest_matvec_words": biggest,
                          "core_clock_ps": 833.333, "hbm_ctl_clock_ps": 1024},
        "stages_run": [s[0] for s in stages], "plan": plan_summary,
        "stages": per_stage, "layer_x_checks": checks, "total_cycles": int(m.group(5)) if m else None,
        "simulate_wall_seconds": round(wall, 1), "source_sha256": start_pins, "source_stable": stable,
        "kv_dir": str(args.kv_dir) if args.kv_dir else None, "binary_sha256": HA.sha(binary), "steps": steps,
        "claim_boundary": "HA8 vehicle with the ROM verify program: the W12 exact datapath, every HBM-resident code word "
                          "and the KV window of positions < P0 timed by the r14 streaming controller, each code word "
                          "reused by the p positions from the prefetch window; window data served from the stage images "
                          "(arrival timed, not carried); SS/FF, area and routing not claimed.",
    }
    target = args.result or (out / "token_result.json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "total_cycles": result["total_cycles"],
                      "stages": {k: v.get("cycles") for k, v in per_stage.items()}, "reads_ok": reads_ok}, indent=1))
    if not good:
        print(text[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Qwen3-8B ROM DSpark speculative step on the REAL_MEM runtime (opt-in, default-off).

Builds (Verilator) the DSpark verify REAL_MEM die rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vprm.sv
(the REAL_MEM die with the VPOS core, the sequencer successor ot_qwen_tp_seq_w12_vp with ENABLE_ARP, the
multi-position KV service rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv and the accept unit rtl/hdc/ot_hdc_accept.sv),
the collective and the hardened tile ot_qwen_rom_tile_w12, linked with the host
rtl/test/qwen_rom_runtime/qwen_rom_rt_w12_vprm.cpp, then runs a PLAN (see the host's header) and checks
every stage output named in an EXPECT json bit-exactly:

  {"stages": {"<stage>": {"x": {"p<j>_die<d>": "<expected X hex>"},
                          "kv": {"die<d>": "<expected kvblk hex>"}}},
   "tokens": [t0, t1, ..] (the verify head's per-position argmax),
   "accept": {"a": a, "n_emit": n, "bonus": b}}

The retained runtimes (qwen_rom_rt_token_w12_rm.py, qwen_rom_rt_verify_w12.py) are untouched.  Writes a
source-pinned record.
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
import qwen_rom_rt_token_w12_rm as RMT  # noqa: E402
import qwen_rom_rt_core_emit_w12  # noqa: E402
import qwen_rom_verify_core_emit_w12  # noqa: E402
import qwen_rom_core_dec_emit_w12  # noqa: E402
from qwen_rom_arithmetic_contract_w12 import flags as arithmetic_flags  # noqa: E402

RT, RR, C = RMT.RT, RMT.RR, RMT.C
SWAP = {ROOT / "rtl/rom/ot_qwen_tp_seq_w12.sv": ROOT / "rtl/rom/ot_qwen_tp_seq_w12_vp.sv",
        ROOT / "rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv": ROOT / "rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv",
        RR / "ot_qwen_rom_rt_die_w12_rm.sv": RR / "ot_qwen_rom_rt_die_w12_vprm.sv"}
DIE_RTL = [SWAP.get(p, p) for p in RMT.DIE_RTL] + [ROOT / "rtl/hdc/ot_hdc_accept.sv"]
assert all(p in RMT.DIE_RTL for p in SWAP), "parent file list moved"
TILE_RTL, COLL_RTL = RMT.TILE_RTL, RMT.COLL_RTL
SOURCES = sorted(set([*DIE_RTL, *TILE_RTL, *COLL_RTL, C.ISA_SVH, ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv",
                      RR / "qwen_rom_rt_w12_vprm.cpp", RT / "qwen_rt_matvec.hpp", RT / "qwen_rt_memory.hpp",
                      Path(__file__), Path(RMT.__file__), ROOT / "tools/qwen_rom_rt_core_emit_w12.py",
                      ROOT / "tools/qwen_rom_verify_core_emit_w12.py", ROOT / "tools/qwen_rom_core_dec_emit_w12.py", ROOT / "tools/qwen_rom_rt_rm_access.py",
                      ROOT / "tools/qwen_rom_rt_vprm_access.py", ROOT / "tools/qwen_rom_arithmetic_contract_w12.py"]))
sha = RMT.sha


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--build-dir", type=Path)
    ap.add_argument("--plan", type=Path)
    ap.add_argument("--expect", type=Path)
    ap.add_argument("--kv-dir", type=Path, help="L<layer>_die<d>.bin (u32 FP32 bits of the KV window before the first stage's P)")
    ap.add_argument("--kv-src", help="REGION prefix: <prefix>_die<d>.bin raw HBM region codes (a previous run's --dump-hbm)")
    ap.add_argument("--dump-hbm", action="store_true")
    ap.add_argument("--acc-commit", action="store_true", help="the accept unit commits the KV service (serial flow)")
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--groups", type=int, default=6144)
    ap.add_argument("--count-width", type=int, default=18)
    ap.add_argument("--su-width", type=int, default=64)
    ap.add_argument("--lv", type=int, default=7)
    ap.add_argument("--smin", type=int, default=7)
    ap.add_argument("--smax", type=int, default=11)
    ap.add_argument("--tcut", type=int, default=7)
    ap.add_argument("--bd", type=int, default=41)
    ap.add_argument("--xvm", type=int, default=1)
    ap.add_argument("--nws", type=int, default=5)
    ap.add_argument("--tws", type=int, default=38)
    ap.add_argument("--ord", type=int, default=7)
    ap.add_argument("--mem-extra", type=int, choices=(0, 1), default=1)
    ap.add_argument("--code-banks", type=int, default=5)
    ap.add_argument("--scale-banks", type=int, default=13)
    ap.add_argument("--tp", type=int, choices=(2, 4), default=4)
    ap.add_argument("--coll-lat", type=int, default=339)
    ap.add_argument("--coll-depth", type=int, default=1024)
    ap.add_argument("--hbm-layers", type=int, default=1)
    ap.add_argument("--fill-lat", type=int, default=8)
    ap.add_argument("--nrd", type=int, default=256)
    ap.add_argument("--lka", type=int, default=512)
    ap.add_argument("--crom-words", type=int, default=1 << 20)
    ap.add_argument("--vm-elems", type=int, default=1 << 20)
    ap.add_argument("--vpmax", type=int, default=4)
    ap.add_argument("--enable-ar256", type=int, default=1)
    ap.add_argument("--dec-la", type=int, choices=(0, 1), default=1,
                    help="core decode restructure DEC_LA (results/rtl/qwen_core_decode_closure_20261004)")
    ap.add_argument("--dec-la-bound", type=int, choices=(0, 1), default=0,
                    help="DEC_LA_BOUND (tools/qwen_rom_core_dec_bound_emit_w12.py); 0 = core unchanged")
    ap.add_argument("--dec-la-amq", type=int, choices=(0, 1), default=0,
                    help="DEC_LA_AMQ argmax boundary register (+1 cycle per core program END); 0 = core unchanged")
    ap.add_argument("--dec-la-issue-fb", type=int, choices=(0, 1, 2, 3), default=0,
                    help="DEC_LA issue fallback (tools/qwen_rom_core_issue_fallback_w12.py); 0 = core unchanged")
    ap.add_argument("--seq-la", type=int, choices=(0, 1), default=1,
                    help="sequencer timing look-ahead (ot_qwen_tp_seq_w12_vp LA; results/rtl/qwen_dspark_closure_20261004)")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--result", type=Path)
    args = ap.parse_args()
    arithmetic = arithmetic_flags(False)
    G, NW = args.groups, args.count_width
    out = args.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    bld = (args.build_dir or args.workdir).resolve()
    bld.mkdir(parents=True, exist_ok=True)
    start_pins = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([args.verilator, "-V"], text=True)).group(1)
    steps = []

    def run(name, cmd, env=None):
        t0 = time.monotonic()
        p = subprocess.run(["/usr/bin/time", "-f", "%M", "-o", str(out / f"{name}.rss"), *map(str, cmd)],
                           cwd=out, capture_output=True, text=True, env=env)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append({"name": name, "seconds": round(time.monotonic() - t0, 2), "returncode": p.returncode,
                      "max_rss_kib": int((out / f"{name}.rss").read_text().split()[-1])})
        if p.returncode:
            raise SystemExit(f"{name} failed; see {out / (name + '.log')}\n{(p.stdout + p.stderr)[-3000:]}")

    gen = bld / "gen"
    gen.mkdir(exist_ok=True)
    core_sv = gen / "ot_qwen_rom_core.sv"
    core_text = qwen_rom_core_dec_emit_w12.emit(qwen_rom_rt_core_emit_w12.CORE.read_text())
    if args.dec_la_bound:
        import qwen_rom_core_dec_bound_emit_w12
        core_text = qwen_rom_core_dec_bound_emit_w12.apply(core_text).replace(
            "parameter integer DEC_LA_BOUND = 0", "parameter integer DEC_LA_BOUND = 1")
    if args.dec_la_issue_fb:
        import qwen_rom_core_issue_fallback_w12
        core_text = qwen_rom_core_issue_fallback_w12.apply(core_text, args.dec_la_issue_fb, args.dec_la_issue_fb)
    if args.dec_la_amq:
        import qwen_rom_core_issue_fallback_w12
        core_text = qwen_rom_core_issue_fallback_w12.apply_amq(core_text).replace(
            "parameter integer DEC_LA_AMQ = 0", "parameter integer DEC_LA_AMQ = 1")
    if args.dec_la_issue_fb >= 3:
        import qwen_rom_core_issue_fallback_w12
        core_text = qwen_rom_core_issue_fallback_w12.apply_start(core_text)
    core_sv.write_text(core_text)
    vs_sv = gen / "ot_hdc_vstream_rt.sv"
    vs_sv.write_text(qwen_rom_rt_core_emit_w12.emit_vstream(qwen_rom_rt_core_emit_w12.VSTREAM.read_text()))
    hier = gen / "hier.vlt"
    hier.write_text('`verilator_config\n' + ''.join(f'hier_block -module "{m}"\n' for m in
                    ("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")))
    pub = gen / "public.vlt"
    pub.write_text(RMT.VLT)
    spine = [f"-GSMIN={args.smin}", f"-GSMAX={args.smax}", f"-GTCUT={args.tcut}", f"-GBD={args.bd}",
             f"-GXVM={args.xvm}", f"-GNWS={args.nws}", f"-GTWS={args.tws}", f"-GORD={args.ord}"]
    vwa = 12   # the sequencer port covers the all-reduce source T1 (p x 256 words from word 0), as the verify die
    models = [
        ("die", "ot_qwen_rom_rt_die_w12_vprm", [str(pub), str(core_sv), str(vs_sv), *map(str, DIE_RTL)],
         [f"-GG={G}", f"-GNW={NW}", f"-GSNW={NW}", "-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1", f"-GD={args.tp}",
          f"-GSW={args.su_width}", f"-GLV={args.lv}", "-GSCALE_LOCAL=0", f"-GMEM_EXTRA={args.mem_extra}", *spine,
          "-GREAL_MEM=1", f"-GSCALE_BANKS={args.scale_banks}", f"-GCROM_WORDS={args.crom_words}",
          f"-GHBM_LAYERS={args.hbm_layers}", "-GEMBED_ROM=0", f"-GFILL_LAT={args.fill_lat}", f"-GNRD={args.nrd}",
          f"-GLKA={args.lka}", f"-GVM_ELEMS={args.vm_elems}", "-GVPOS=1", "-GENABLE_ARP=1", f"-GVWA={vwa}",
          f"-GVPMAX={args.vpmax}", f"-GENABLE_AR256={args.enable_ar256}", f"-GSEQ_LA={args.seq_la}", f"-GDEC_LA={args.dec_la}", *arithmetic]),
        ("coll", "ot_rom_oneshot_allreduce", [*map(str, COLL_RTL), *map(str, C.PIPES), *map(str, TILE_RTL[:5])],
         [f"-GN={args.tp}", "-GLANES=16", "-GTAGW=32", f"-GDEPTH={args.coll_depth}", f"-GLAT={args.coll_lat}", "-GBPC_NUM=3600"]),
        ("tile", "ot_qwen_rom_tile_w12", [str(pub), *map(str, TILE_RTL)],
         [f"-GGT={G}", f"-GNW={NW}", f"-GSMIN={args.smin}", f"-GCODE_BANKS={args.code_banks}", f"-GMEM_EXTRA={args.mem_extra}",
          "-GKV_VB=131072", "-GKV_NH=2", *arithmetic]),
    ]
    bp = bld / "build_params.json"
    prior = json.loads(bp.read_text()) if bp.exists() else {}
    bp.write_text(json.dumps({p: params for p, _, _, params in models}, indent=1))
    for prefix, top, files, params in models:
        mdir = bld / prefix
        if (mdir / f"V{prefix}__ALL.a").exists():
            if prior.get(prefix) == params:
                continue
            subprocess.run(["rm", "-rf", str(mdir)], check=True)
        run(f"verilate_{prefix}", [args.verilator, "--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "-Wno-WIDTH",
                                   "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-PINMISSING", "-Wno-LATCH", "-Wno-MULTIDRIVEN",
                                   f"-I{C.ISA_SVH.parent}", "--top-module", top, "--prefix", f"V{prefix}", "--Mdir", mdir,
                                   *params, *files, *(["--hierarchical", str(hier)] if prefix == "die" else [])])
        run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{args.jobs}", f"V{prefix}__ALL.a",
                                "OPT_FAST=-O2", "OPT_SLOW=-O1"])
    run("access", [sys.executable, ROOT / "tools/qwen_rom_rt_vprm_access.py", "--die-header", bld / "die/Vdie___024root.h",
                   "--vm-elems", args.vm_elems, "--out", gen / "rm_access.hpp",
                   "--tile-header", bld / "tile/Vtile___024root.h", "--nport", G >> args.smin, "--scale-banks", args.scale_banks,
                   "--code-banks", args.code_banks, "--crom-words", args.crom_words, "--hbm-layers", args.hbm_layers,
                   "--kv-ideal", 0, "--embed-rom", 0])
    archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}", f"-I{RR}", f"-I{gen}"}
    for prefix, *_ in models:
        archives += sorted((bld / prefix).rglob("*.a"))
        includes.add(f"-I{bld / prefix}")
        for h in (bld / prefix).rglob("V*.h"):
            includes.add(f"-I{h.parent}")
    binary = bld / "qwen_rom_rt_vprm"
    if args.build_only or not binary.exists():
        run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}",
                     f"-DSWIDTH={args.su_width}", f"-DSMAXB={args.smax}", f"-DTCUTL={args.tcut}", f"-DNWSD={args.nws}",
                     f"-DXVMD={args.xvm}", f"-DTPD={args.tp}", f"-DCBANKS={args.code_banks}", f"-DSMINV={args.smin}",
                     *sorted(includes), RR / "qwen_rom_rt_w12_vprm.cpp", "-Wl,--start-group", *archives,
                     "-Wl,--end-group", f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                     f"{vroot}/include/verilated_dpi.cpp", "-o", binary])
    if args.build_only:
        print("built", binary)
        return
    plan = [ln.split() for ln in args.plan.read_text().splitlines() if ln.strip()]
    stage_pins = {}
    for t in plan:
        if t[0] == "STAGE":
            for d, pdir in enumerate(t[9:]):
                for f in ("matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex", "program.hex", "segments.hex"):
                    stage_pins[f"{t[1]}/die{d}/{f}"] = sha(Path(pdir) / f)
            if t[8] != "-":
                stage_pins[f"{t[1]}/xpreload"] = sha(t[8])
    cmd = [str(binary), "--plan", str(args.plan), str(out)]
    if args.kv_dir:
        cmd += ["--kv-dir", str(args.kv_dir)]
    if args.kv_src:
        cmd += ["--kv-src", args.kv_src]
    if args.dump_hbm:
        cmd += ["--dump-hbm", "1"]
    env = dict(os.environ, RT_THREADS=str(args.threads), RT_ACC_COMMIT=str(int(args.acc_commit)))
    t0 = time.monotonic()
    with open(out / "token.log", "w") as log:
        p = subprocess.run(cmd, cwd=out, stdout=log, stderr=subprocess.STDOUT, env=env)
    wall = time.monotonic() - t0
    text = (out / "token.log").read_text()
    per_stage = {}
    for mm in re.finditer(r"STAGE (\S+) done (.*)", text):
        kv = dict(item.split("=", 1) for item in mm.group(2).split() if "=" in item)
        per_stage[mm.group(1)] = {"cycles": int(kv["cycles"]), "me_clock_edges": kv["me_busy"], "pos": int(kv["pos"]),
                                  "np": int(kv["np"]), "layer": int(kv["layer"])}
    for mm in re.finditer(r"MEMSTAT (\S+) (die\d) (.*)", text):
        per_stage.setdefault(mm.group(1), {}).setdefault("memory", {})[mm.group(2)] = {
            k: int(v) for k, v in (item.split("=", 1) for item in mm.group(3).split())}
    tokens = {}
    for mm in re.finditer(r"VERIFY_TOKENS die=(\d) n=(\d+)(.*)", text):
        tokens[f"die{mm.group(1)}"] = [int(x.split("=")[1].split("/")[0]) for x in mm.group(3).split()]
    accepts = [dict(item.split("=", 1) for item in mm.group(1).split()) for mm in re.finditer(r"ACCEPT (.*)", text)]
    commits = re.findall(r"COMMIT .*", text)
    expect = json.loads(args.expect.read_text()) if args.expect else {"stages": {}}
    checks = {}
    for st, e in expect.get("stages", {}).items():
        for key, want_p in e.get("x", {}).items():
            got_p = out / f"{st}_{key}_x.hex"
            got = got_p.read_text().split() if got_p.exists() else []
            want = Path(want_p).read_text().split()
            mism = [i for i, (x, y) in enumerate(zip(got, want)) if x != y]
            checks[f"{st}_{key}_x"] = {"words": len(got), "mismatches": len(mism) + abs(len(got) - len(want)),
                                       "first_mismatch": ({"index": mism[0], "rtl": got[mism[0]], "golden": want[mism[0]]} if mism else None),
                                       "actual_sha256": sha(got_p) if got else None, "expected_sha256": sha(want_p)}
        for key, want_p in e.get("kv", {}).items():
            got_p = out / f"{st}_{key}_kvblk.hex"
            got = got_p.read_text().splitlines() if got_p.exists() else []
            want = Path(want_p).read_text().splitlines()
            checks[f"{st}_{key}_kvblk"] = {"codes": len(got), "mismatches": sum(x != y for x, y in zip(got, want)) + abs(len(got) - len(want))}
    tok_ok = True
    if "tokens" in expect:
        tok_ok = bool(tokens) and all(v[:len(expect["tokens"])] == expect["tokens"] for v in tokens.values())
    acc_ok = True
    if "accept" in expect:
        want = expect["accept"]
        acc_ok = len(accepts) == args.tp and all(int(x["a"]) == want["a"] and int(x["n_emit"]) == want["n_emit"]
                                                and int(x["bonus"]) == want["bonus"] for x in accepts)
    end_pins = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    stable = end_pins == start_pins
    m = re.search(r"QWEN_ROM_VPRM PASS stages=(\d+) cycles=(\d+).*RSS_KiB=(\d+)", text)
    good = (p.returncode == 0 and bool(m) and stable and all(c["mismatches"] == 0 for c in checks.values()) and tok_ok and acc_ok)
    result = {
        "schema": "opentallas.qwen-dspark-vprm-run.v1", "status": "pass" if good else "fail", "returncode": p.returncode,
        "design_point": {"tp": args.tp, "groups_per_die": G, "su_width": args.su_width, "su_reducer_time_levels": args.lv,
                         "smin": args.smin, "smax": args.smax, "tree_cut": args.tcut, "collective_lat_cycles": args.coll_lat,
                         "collective_depth": args.coll_depth, "code_banks": args.code_banks, "mem_extra": args.mem_extra,
                         "vpos": 1, "enable_arp": 1, "enable_ar256": args.enable_ar256, "vpmax": args.vpmax, "seq_la": args.seq_la, "dec_la": args.dec_la, "dec_la_issue_fb": args.dec_la_issue_fb, "dec_la_bound": args.dec_la_bound, "dec_la_amq": args.dec_la_amq,
                         "kv": "REAL_MEM: ot_qwen_rt_kv_mp_service + ot_qwen_hbm_model_ack NPC=32 CLK_PS=833 WR_ACK=1, KV_HBM=1, KV_VEC_WRITE_BRIDGE=1"},
        "wire_stages": {"bd": args.bd, "xvm": args.xvm, "nws": args.nws, "tws": args.tws, "ord": args.ord},
        "stages": per_stage, "verify_tokens": tokens, "accept": accepts, "commits": commits,
        "checks": checks, "tokens_ok": tok_ok, "accept_ok": acc_ok, "total_cycles": int(m.group(2)) if m else None,
        "simulate_wall_seconds": round(wall, 1), "max_rss_kib": int(m.group(3)) if m else None,
        "source_sha256": start_pins, "source_stable": stable, "stage_image_sha256": stage_pins,
        "plan_sha256": sha(args.plan), "expect_sha256": sha(args.expect) if args.expect else None,
        "binary_sha256": sha(binary), "generated_core_sha256": sha(core_sv), "steps": steps,
    }
    target = args.result or (out / "vprm_result.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "total_cycles": result["total_cycles"],
                      "stages": {k: v.get("cycles") for k, v in per_stage.items()}, "accept": accepts}, indent=2))
    if not good:
        print(text[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()

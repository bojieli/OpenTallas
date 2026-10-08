#!/usr/bin/env python3
"""Exactness regression: the Qwen3-8B ROM plain-AR STREAM4 token at P8191, rebuilt from THIS source tree.

The published full token (results/rtl/qwen_plain_ar_stream4_P8191_20261005: 193,955 cycles, 36 layers + RTL head,
next token 18 / winning logit 0x42282b99 on all 4 ranks, all 144 layer outputs and 144 current-KV writes exact)
was built from a mix of scratch snapshots (src4, a60af57e4 tagged backend, 1d44fd09d top).  This tool builds the
SAME configuration entirely from the tree it lives in, so a regression run says whether the CURRENT source still
produces that token:

  die  = ot_qwen_rom_rt_die_w12_stream4_tagged_ar (rtl/qwen_sys/baseline_ar_stream4) with the native tagged
         STREAM4 backend (rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv) in place of the ack model, HBM_LAYERS=36,
         BASELINE_AR=1, every other die/coll/tile parameter as selected for the published run;
  host = tools/runtime/qwen_baseline_ar_stream4/qwen_rom_rt_w12_stream4_fulltoken.cpp;
  checks as the published job's numerical_comparison (layer X, current K/V e4m3 codes, head token/logit, Xnorm).

    qwen_rom_fulltoken.py build --build DIR
    qwen_rom_fulltoken.py run   --build DIR --work DIR --stages {L0,full} [--threads 16]
    qwen_rom_fulltoken.py check --build DIR --work DIR --stages {L0,full}     # re-judge a finished run

Inputs default to the fixture paths on ot-epyc1tb / ot-epyc2 (/srv/opentallas-scratch/...).
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_rt_token_stream4_w12 as S4  # noqa: E402
import qwen_rom_rt_core_emit_w12 as EMIT  # noqa: E402
import rtl_hdc_decode_campaign as C  # noqa: E402
from qwen_rom_arithmetic_contract_w12 import flags as arithmetic_flags  # noqa: E402

TOP = "ot_qwen_rom_rt_die_w12_stream4_tagged_ar"
TOP_SV = ROOT / "rtl/qwen_sys/baseline_ar_stream4" / f"{TOP}.sv"
TAGGED = ROOT / "rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv"
ACK = ROOT / "rtl/hdc/kv/ot_qwen_hbm_stream4_ack.sv"
HOST = ROOT / "tools/runtime/qwen_baseline_ar_stream4/qwen_rom_rt_w12_stream4_fulltoken.cpp"
VERILATOR = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
FIX = Path("/srv/opentallas-scratch")
IMG = FIX / "claude/qwen-dspark-system/img_p1"
X_PRELOAD = FIX / "claude/realmem-ctx8k/gold/P8191/x_preload.hex"
KV_HISTORY = FIX / "codex/qwen-P8191-full36-history-r1/history"
GOLD = FIX / "claude/qwen-hbmacc-8k/gold/tp4/P8191"
# The full gold directory was deleted by the fleet sweeper on 2026-10-07 20:43 (EPYC1 and EPYC2).  The COMMITTED oracle
# record keeps the sha256 of every layer X file, every head Xnorm and the head argmax/logit, so those are checked by
# digest when the files are gone; current-token KV codes are checked wherever a gold kv_at_P JSON survives
# (realmem-ctx8k keeps layers 0-2) and the rest are reported as unverified.
REF = ROOT / "results/rtl/qwen_hbmacc_p8191_20261004/gold_tp4/oracle.json"
KV_GOLD = [GOLD / "kv_at_P", FIX / "claude/realmem-ctx8k/gold/P8191/kv_at_P"]
POS, TOKEN = 8191, 24
L0_MAX_CYCLES = 9000
# Published selection (results/rtl/qwen_plain_ar_stream4_P8191_20261005/measured_composition.json selected_parameters)
DIE = ["-GG=6144", "-GNW=18", "-GSNW=18", "-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1", "-GD=4", "-GSW=64", "-GLV=7",
       "-GSCALE_LOCAL=0", "-GMEM_EXTRA=1", "-GSMIN=7", "-GSMAX=11", "-GTCUT=7", "-GBD=41", "-GXVM=1", "-GNWS=5",
       "-GTWS=38", "-GORD=7", "-GREAL_MEM=1", "-GENABLE_AR256=1", "-GNSTK=4", "-GSCALE_BANKS=13",
       "-GCROM_WORDS=1048576", "-GHBM_LAYERS=36", "-GEMBED_ROM=1", "-GFILL_LAT=8", "-GNRD=256", "-GLKA=512",
       "-GWBW=4", "-GHBM_PHASE=0", "-GHBM_PULLIN=16", "-GBASELINE_AR=1"]
COLL = ["-GN=4", "-GLANES=16", "-GTAGW=32", "-GDEPTH=256", "-GLAT=339", "-GBPC_NUM=3600"]
TILE = ["-GGT=6144", "-GNW=18", "-GSMIN=7", "-GCODE_BANKS=5", "-GMEM_EXTRA=1", "-GKV_VB=131072", "-GKV_NH=2"]
LINK_DEFINES = ["-DGROUPS=6144", "-DCOUNTWIDTH=18", "-DSWIDTH=64", "-DSMAXB=11", "-DTCUTL=7", "-DNWSD=5", "-DXVMD=1",
                "-DTPD=4", "-DCBANKS=5", "-DSMINV=7"]
VFLAGS = ["--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
          "-Wno-PINMISSING", "-Wno-LATCH", "-Wno-MULTIDRIVEN"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sh(name, cmd, out, steps, cwd=None, env=None):
    t0 = time.monotonic()
    with open(out / f"{name}.log", "w") as log:
        p = subprocess.run(["/usr/bin/time", "-f", "%M", "-o", str(out / f"{name}.rss"), *map(str, cmd)],
                           cwd=cwd or out, stdout=log, stderr=subprocess.STDOUT, env=env)
    steps.append(dict(name=name, seconds=round(time.monotonic() - t0, 1), returncode=p.returncode))
    if p.returncode:
        raise SystemExit(f"{name} failed rc={p.returncode}; see {out / (name + '.log')}")


def die_sources():
    files = [TAGGED if f == ACK else f for f in S4.DIE_RTL]
    files = [f for f in files if f.name != "ot_qwen_rom_rt_die_w12_stream4.sv"]
    return [*files, S4.RR / "ot_qwen_rom_rt_die_w12_stream4.sv", TOP_SV]


def build(bld: Path, jobs: int):
    bld.mkdir(parents=True, exist_ok=True)
    steps = []
    gen = bld / "gen"
    gen.mkdir(exist_ok=True)
    core_sv = gen / "ot_qwen_rom_core.sv"
    core_sv.write_text(EMIT.emit(EMIT.CORE.read_text()))
    vs_sv = gen / "ot_hdc_vstream_rt.sv"
    vs_sv.write_text(EMIT.emit_vstream(EMIT.VSTREAM.read_text()))
    hier = gen / "hier.vlt"
    hier.write_text('`verilator_config\n' + ''.join(f'hier_block -module "{m}"\n' for m in
                    ("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")))
    pub = gen / "public.vlt"
    pub.write_text(S4.VLT)
    arith = arithmetic_flags(False)
    models = [("die", TOP, [pub, core_sv, vs_sv, *die_sources()], [*DIE, *arith]),
              ("coll", "ot_rom_oneshot_allreduce", [*S4.COLL_RTL, *C.PIPES, *S4.TILE_RTL[:5]], COLL),
              ("tile", "ot_qwen_rom_tile_w12", [pub, *S4.TILE_RTL], [*TILE, *arith])]
    for prefix, top, files, params in models:
        mdir = bld / prefix
        sh(f"verilate_{prefix}", [VERILATOR, *VFLAGS, f"-I{C.ISA_SVH.parent}", f"-I{TAGGED.parent}", "--top-module", top,
                                  "--prefix", f"V{prefix}", "--Mdir", mdir, *params, *files,
                                  *(["--hierarchical", hier] if prefix == "die" else [])], bld, steps)
        sh(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{jobs}", f"V{prefix}__ALL.a",
                               "OPT_FAST=-O2", "OPT_SLOW=-O1"], bld, steps)
    sh("access", [sys.executable, ROOT / "tools/qwen_rom_rt_baseline_ar_stream4_access.py",
                  "--die-header", bld / "die/Vdie___024root.h", "--tile-header", bld / "tile/Vtile___024root.h",
                  "--nport", 48, "--scale-banks", 13, "--code-banks", 5, "--crom-words", 1048576,
                  "--hbm-layers", 36, "--kv-ideal", 0, "--embed-rom", 1, "--out", gen / "rm_access.hpp"], bld, steps)
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([VERILATOR, "-V"], text=True)).group(1)
    includes = {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{S4.RT}", f"-I{S4.RR}", f"-I{gen}"}
    archives = []
    for prefix, *_ in models:
        archives += sorted((bld / prefix).rglob("*.a"))
        includes.add(f"-I{bld / prefix}")
        includes.update(f"-I{h.parent}" for h in (bld / prefix).rglob("V*.h"))
    exe = bld / "qwen_plain_ar_stream4"
    sh("link", ["g++", "-std=c++20", "-O2", "-pthread", *LINK_DEFINES, *sorted(includes), HOST,
                "-Wl,--start-group", *archives, "-Wl,--end-group",
                *(f"{vroot}/include/{p}" for p in ("verilated.cpp", "verilated_threads.cpp", "verilated_dpi.cpp")),
                "-o", exe], bld, steps)
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted({*die_sources(), *S4.TILE_RTL, *S4.COLL_RTL, HOST})}
    (bld / "build.json").write_text(json.dumps(dict(executable_sha256=sha(exe), steps=steps, source_sha256=pins),
                                               indent=1) + "\n")
    print("built", exe)


def e4m3(bits):
    import qwen_rom_rt_token_w12_rm as RM
    return RM.e4m3(bits)


def read_words(p):
    return [int(x, 16) for x in p.read_text().split()] if p.exists() else []


def sha_file(p):
    return sha(p) if p.exists() else None


def check(out, mode, layers):
    """Compare a run directory with the golden: files when present, else the committed oracle digests."""
    ref = json.loads(REF.read_text())["per_position"]["8191"]
    layer_x, kv, heads, norms, unverified = {}, {}, {}, {}, []
    for n in layers:
        for d in range(4):
            key = f"L{n}_die{d}"
            gp = GOLD / f"L{n:02d}_die{d}_x.hex"
            if gp.exists():
                got, want = read_words(out / f"{key}_x.hex"), read_words(gp)
                layer_x[key] = sum(a != b for a, b in zip(got, want)) + abs(len(got) - len(want))
            else:
                layer_x[key] = 0 if sha_file(out / f"{key}_x.hex") == ref["layer_x_sha256"][key] else 1
            if mode == "L0":
                continue  # current-KV readback happens after ACK retirement at the END of the token (full mode)
            gk = next((g / f"L{n}_die{d}.json" for g in KV_GOLD if (g / f"L{n}_die{d}.json").exists()), None)
            if gk is None or sha(gk) != ref["kv_at_P_sha256"][key]:
                unverified.append(key)
                continue
            gold = json.loads(gk.read_text())
            kp = out / f"{key}_kvP.hex"
            rows = [r.split() for r in kp.read_text().splitlines()] if kp.exists() else []
            for kind, field in (("K", "k_bits"), ("V", "v_bits")):
                got_c = [int(r[3], 16) for r in rows if r[0] == kind]
                want_c = [e4m3(int(b, 16)) for b in gold[field]]
                kv[f"{key}_{kind}"] = sum(a != b for a, b in zip(got_c, want_c)) + abs(len(got_c) - len(want_c))
    if mode == "full":
        h0 = ref["head"]["head_die0"]
        expected = [h0["argmax_local"], int(h0["logit_bits"], 16)]   # rank 0 holds the global winner (token 18)
        for d in range(4):
            heads[f"die{d}"] = read_words(out / f"head_die{d}_result.hex")
            norms[f"die{d}"] = 0 if sha_file(out / f"head_die{d}_xnorm.hex") == ref["head"][f"head_die{d}"]["xnorm_sha256"] else 1
        heads["expected"] = expected
    return layer_x, kv, heads, norms, unverified


def run(bld: Path, work: Path, mode: str, threads: int):
    work.mkdir(parents=True, exist_ok=True)
    # The full-token host refuses anything but [E,] L0..L35, head; the L0 mode runs the full list and stops at
    # --max-cycles once layer 0 has retired (published L0: cycles 7..6,051).
    layers = [0] if mode == "L0" else list(range(36))
    names = [f"L{n}" for n in layers] + ([] if mode == "L0" else ["head"])
    stages = work / "stages.txt"
    stages.write_text("".join(f"{n} " + " ".join(str(IMG / f"{n}-d{d}") for d in range(4)) + " 0\n"
                              for n in [f"L{n}" for n in range(36)] + ["head"]))
    out = work / "run"
    cmd = [bld / "qwen_plain_ar_stream4", "--stages", stages, out, X_PRELOAD, "--pos", POS, "--token", TOKEN,
           "--kv-dir", KV_HISTORY, "--kv-ideal", 0, "--early-go", 1, "--posted-wb", 1,
           *(["--max-cycles", L0_MAX_CYCLES] if mode == "L0" else [])]
    env = dict(os.environ, RT_THREADS=str(threads))
    env.pop("RT_PROGRESS", None)
    t0 = time.monotonic()
    with open(work / "runtime.log", "w") as log:
        p = subprocess.run(list(map(str, cmd)), stdout=log, stderr=subprocess.STDOUT, env=env, cwd=work)
    (work / "returncode").write_text(f"{p.returncode}\n")
    return finish(bld, work, mode, p.returncode, time.monotonic() - t0)


def finish(bld, work, mode, returncode, wall):
    """Judge a finished run directory (also used by the `check` phase to re-judge without re-simulating)."""
    layers = [0] if mode == "L0" else list(range(36))
    names = [f"L{n}" for n in layers] + ([] if mode == "L0" else ["head"])
    out = work / "run"

    class P:  # noqa: N801 -- the simulator's exit status
        pass
    p = P()
    p.returncode = returncode
    text = (work / "runtime.log").read_text()
    stage_cycles = {m[1]: int(m[2]) for m in re.finditer(r"^STAGE (\S+) done cycles=(\d+)", text, re.M)}
    if mode == "L0":
        stage_cycles = {k: v for k, v in stage_cycles.items() if k == "L0"}
    faults = re.findall(r"^STAGE \S+ done .*?(seq_fault=\S+ core_fault=\S+ coll_fault=\S+)", text, re.M)
    layer_x, kv, heads, norms, unverified = check(out, mode, layers)
    done = re.search(r"QWEN_ROM_STREAM4_PLAIN_AR_FULLTOKEN DONE stages=(\d+) cycles=(\d+)", text)
    drained = re.search(r"WRITEBACK drained=(\d)", text)
    exact = bool((mode == "L0" or (p.returncode == 0 and done)) and list(stage_cycles) == names
                 and all(v == 0 for v in layer_x.values()) and all(v == 0 for v in kv.values())
                 and all(v == 0 for v in norms.values())
                 and (mode != "full" or (len(heads) == 5 and all(v == heads["expected"] for v in heads.values()))))
    result = dict(schema="opentallas.exactness.qwen-rom-fulltoken.v1", mode=mode, exact=exact, returncode=p.returncode,
                  cycles=int(done[2]) if done else None, stage_cycles=stage_cycles,
                  next_token=heads.get("die0", [None, None])[0] if heads else None,
                  winning_logit_bits=f"{heads['die0'][1]:08x}" if heads.get("die0") and len(heads["die0"]) > 1 else None,
                  head_results=heads, head_xnorm_mismatches=norms,
                  layer_x_mismatches=sum(layer_x.values()), layer_x_checks=len(layer_x),
                  kv_mismatches=sum(kv.values()), kv_checks=len(kv) // 2,
                  bad_layer_x=[k for k, v in layer_x.items() if v][:8], bad_kv=[k for k, v in kv.items() if v][:8],
                  kv_unverified=unverified,
                  faults_nonzero=[f for f in faults if re.search(r"=(?!0\b)\S+", f)][:4],
                  writeback_drained=bool(drained and drained[1] == "1"), wall_seconds=round(wall, 1) if wall else None,
                  executable_sha256=sha(bld / "qwen_plain_ar_stream4"))
    (work / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("mode", "exact", "cycles", "next_token", "winning_logit_bits",
                                             "layer_x_mismatches", "kv_mismatches")}))
    return 0 if exact else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=("build", "run", "check"))
    ap.add_argument("--build", type=Path, required=True)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--stages", choices=("L0", "full"), default="L0")
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    if a.phase == "build":
        build(a.build.resolve(), a.jobs)
    elif a.phase == "check":
        w = a.work.resolve()
        text = (w / "runtime.log").read_text()
        rc = int((w / "returncode").read_text()) if (w / "returncode").exists() else \
            (0 if "PLAIN_AR_FULLTOKEN DONE" in text else 1)
        sys.exit(finish(a.build.resolve(), w, a.stages, rc, None))
    else:
        sys.exit(run(a.build.resolve(), a.work.resolve(), a.stages, a.threads))


if __name__ == "__main__":
    main()

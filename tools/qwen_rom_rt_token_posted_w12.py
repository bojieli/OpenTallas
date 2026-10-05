#!/usr/bin/env python3
"""Qwen3-8B ROM TP4 runtime with REAL memory services (default-off REAL_MEM configuration).

Builds (Verilator) the REAL_MEM die (rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_rm.sv:
sequencer + emitted core with KV_HBM = 1, KV_VEC_WRITE_BRIDGE = 1, ME_STALL = 1, RTL
program/descriptor/constant ROMs and vector memory, scale-ROM macro banks, the KV fill/write
service rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv and the HBM timing model with write-done
rtl/hdc/kv/ot_qwen_hbm_model_ack.sv), the collective, and the HARDENED tile element
ot_qwen_rom_tile_w12 (code-ROM and KV-slice macros) that the host instantiates G/4 times a die
(rtl/test/qwen_rom_runtime/qwen_rom_rt_w12_rm.cpp).  The host only preloads memory contents.

Runs a stage list (decoder layers) at a position P with the KV history of a position oracle
(tools/qwen_rom_position_oracle_w12.py), and compares every layer's X and every layer's
written-back token K/V bit-exactly against it.  Writes a source-pinned record.  The retained
default runtime (tools/qwen_rom_rt_token_w12.py) is untouched.
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as C  # noqa: E402
import qwen_rom_rt_core_emit_posted_w12 as qwen_rom_rt_core_emit_w12  # noqa: E402
from qwen_rom_arithmetic_contract_w12 import flags as arithmetic_flags  # noqa: E402

RT = ROOT / "rtl/test/qwen_runtime"
RR = ROOT / "rtl/test/qwen_rom_runtime"
MAC = ROOT / "physical/asap7_memory_macros"
HDC = [p for p in C.HDC if p.name != "ot_hdc_core.sv"]
DIE_RTL = [*HDC, *C.PIPES,
           *(ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_dyn_ttiles", "ot_hdc_qwen_int8_arith",
                                               "ot_hdc_qwen_int8_embed_decode", "ot_hdc_cg", "ot_qwen_me_array_w12", "ot_hdc_fp32_add_lat",
                                               "ot_hdc_prefix", "ot_qwen_w12_matvec", "ot_qwen_w12_arith", "ot_qwen_rt_rom_bank", "ot_qwen_rt_embed_rom")),
           ROOT / "rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv", ROOT / "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv",
           MAC / "ot_rom_4096x266_m8/ot_rom_4096x266_m8.v",
           *(ROOT / f"rtl/rom/{n}.sv" for n in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_qwen_tp_seq_w12")),
           RR / "ot_qwen_rom_rt_die_w12_posted.sv"]
TILE_RTL = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_fastfp", "ot_hdc_delay",
                                              "ot_hdc_sfu", "ot_hdc_matvec", "ot_qwen_me_array_w12", "ot_qwen_rom_tile_w12",
                                              "ot_hdc_fp32_add_lat", "ot_hdc_prefix", "ot_qwen_w12_matvec", "ot_qwen_w12_arith")] \
    + [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", MAC / "ot_rom_4096x266_m8/ot_rom_4096x266_m8.v",
       MAC / "ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"]
COLL_RTL = [ROOT / f"rtl/rom/{n}.sv" for n in ("ot_rom_pkg_link", "ot_rom_pkg_ctrl", "ot_rom_oneshot_allreduce")]
SOURCES = sorted(set([*DIE_RTL, *TILE_RTL, *COLL_RTL, C.ISA_SVH, ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv",
                      RR / "qwen_rom_rt_w12_posted.cpp", RT / "qwen_rt_matvec.hpp", RT / "qwen_rt_memory.hpp",
                      Path(__file__), ROOT / "tools/qwen_rom_rt_core_emit_w12.py", ROOT / "tools/qwen_rom_rt_rm_access.py",
                      ROOT / "tools/qwen_rom_embed_stage_w12.py",
                      ROOT / "tools/qwen_rom_arithmetic_contract_w12.py",
                      ROOT / "tools/qwen_rom_rt_core_emit_posted_w12.py"]))
VLT = """`verilator_config
public_flat_rw -module "ot_rom_4096x266_m8" -var "arr"
public_flat_rw -module "ot_sram_1r1w_128x256_m1_r2c2" -var "arr"
"""


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def e4m3(bits: int) -> int:
    s, e, m = bits >> 31, (bits >> 23) & 255, bits & 0x7fffff
    if e == 0 and m == 0:
        return s << 7
    if 121 <= e <= 135 and m & 0xfffff == 0:
        return (s << 7) | ((e - 120) << 3) | (m >> 20)
    if e == 120 and m & 0x1fffff == 0:
        return (s << 7) | 4 | (m >> 21)
    if e == 119 and m & 0x3fffff == 0:
        return (s << 7) | 2 | (m >> 22)
    if e == 118 and m == 0:
        return (s << 7) | 1
    raise ValueError(f'not E4M3: {bits:08x}')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True, help="run outputs")
    ap.add_argument("--build-dir", type=Path, help="models and binary (default: the workdir); runs may share one")
    ap.add_argument("--stages", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True, help="position-oracle P directory (L<nn>_die<d>_x.hex, kv_pre/, kv_at_P/)")
    ap.add_argument("--pos", type=int, required=True)
    ap.add_argument("--token", type=int, required=True)
    ap.add_argument("--real-mem", action="store_true", required=True, help="the REAL_MEM configuration (default-off)")
    ap.add_argument("--posted-kv", action="store_true", help="opt-in ordinary SU issue before write-done; retain retirement fences")
    ap.add_argument("--kv-ideal", action="store_true", help="A/B reference: KV service HBM bypassed, slices preloaded")
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
    ap.add_argument("--hbm-layers", type=int, default=3)
    ap.add_argument("--fill-lat", type=int, default=8)
    ap.add_argument("--nrd", type=int, default=256)
    ap.add_argument("--lka", type=int, default=512)
    ap.add_argument("--crom-words", type=int, default=1 << 20)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--no-embed-rom", action="store_true", help="preload X instead of the embedding stage E")
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
    source_receipt = bld / "posted_source_sha256.json"
    if source_receipt.exists() and json.loads(source_receipt.read_text()) != start_pins:
        raise SystemExit("successor build source changed; preserve this build and use a new pinned build directory")
    if not source_receipt.exists():
        source_receipt.write_text(json.dumps(start_pins, indent=2, sort_keys=True) + "\n")
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
    core_sv.write_text(qwen_rom_rt_core_emit_w12.emit(qwen_rom_rt_core_emit_w12.CORE.read_text()))
    vs_sv = gen / "ot_hdc_vstream_rt.sv"
    vs_sv.write_text(qwen_rom_rt_core_emit_w12.emit_vstream(qwen_rom_rt_core_emit_w12.VSTREAM.read_text()))
    hier = gen / "hier.vlt"
    hier.write_text('`verilator_config\n' + ''.join(f'hier_block -module "{m}"\n' for m in
                    ("ot_hdc_vstream_lane", "ot_hdc_fmul", "ot_hdc_qadd")))
    pub = gen / "public.vlt"
    pub.write_text(VLT)
    spine = [f"-GSMIN={args.smin}", f"-GSMAX={args.smax}", f"-GTCUT={args.tcut}", f"-GBD={args.bd}",
             f"-GXVM={args.xvm}", f"-GNWS={args.nws}", f"-GTWS={args.tws}", f"-GORD={args.ord}"]
    kv_ideal = int(args.kv_ideal)
    models = [
        ("die", "ot_qwen_rom_rt_die_w12_rm", [str(pub), str(core_sv), str(vs_sv), *map(str, DIE_RTL)],
         [f"-GG={G}", f"-GNW={NW}", f"-GSNW={NW}", "-GQWEN_FULLSHAPE=1", "-GME_IDLE_GATE=1", f"-GD={args.tp}",
          f"-GSW={args.su_width}", f"-GLV={args.lv}", "-GSCALE_LOCAL=0", f"-GMEM_EXTRA={args.mem_extra}", *spine,
          "-GREAL_MEM=1", f"-GPOSTED_KV={int(args.posted_kv)}", f"-GSCALE_BANKS={args.scale_banks}", f"-GCROM_WORDS={args.crom_words}",
          f"-GHBM_LAYERS={args.hbm_layers}", f"-GEMBED_ROM={int(not args.no_embed_rom)}", f"-GFILL_LAT={args.fill_lat}", f"-GNRD={args.nrd}", f"-GLKA={args.lka}", *arithmetic]),
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
            raise SystemExit(f"{prefix} build parameters changed; preserve objects and use a new build directory")
        run(f"verilate_{prefix}", [args.verilator, "--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "-Wno-WIDTH",
                                   "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-PINMISSING", "-Wno-LATCH", "-Wno-MULTIDRIVEN",
                                   f"-I{C.ISA_SVH.parent}", "--top-module", top, "--prefix", f"V{prefix}", "--Mdir", mdir,
                                   *params, *files, *(["--hierarchical", str(hier)] if prefix == "die" else [])])
        run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{args.jobs}", f"V{prefix}__ALL.a",
                                "OPT_FAST=-O2", "OPT_SLOW=-O1"])
    run("access", [sys.executable, ROOT / "tools/qwen_rom_rt_rm_access.py", "--die-header", bld / "die/Vdie___024root.h",
                   "--tile-header", bld / "tile/Vtile___024root.h", "--nport", G >> args.smin, "--scale-banks", args.scale_banks,
                   "--code-banks", args.code_banks, "--crom-words", args.crom_words, "--hbm-layers", args.hbm_layers,
                   "--kv-ideal", 0, "--embed-rom", int(not args.no_embed_rom), "--out", gen / "rm_access.hpp"])
    archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}", f"-I{RR}", f"-I{gen}"}
    for prefix, *_ in models:
        archives += sorted((bld / prefix).rglob("*.a"))
        includes.add(f"-I{bld / prefix}")
        for h in (bld / prefix).rglob("V*.h"):
            includes.add(f"-I{h.parent}")
    binary = bld / "qwen_rom_rt_rm"
    if args.build_only or not binary.exists() or any(not (bld / p_ / f"V{p_}__ALL.a").exists() for p_, *_ in models):
      run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}",
                 f"-DSWIDTH={args.su_width}", f"-DSMAXB={args.smax}", f"-DTCUTL={args.tcut}", f"-DNWSD={args.nws}",
                 f"-DXVMD={args.xvm}", f"-DTPD={args.tp}", f"-DCBANKS={args.code_banks}", f"-DSMINV={args.smin}",
                 *sorted(includes), RR / "qwen_rom_rt_w12_posted.cpp", "-Wl,--start-group", *archives,
                 "-Wl,--end-group", f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                 f"{vroot}/include/verilated_dpi.cpp", "-o", binary])
    if args.build_only:
        print("built", binary)
        return
    stages = [line.split() for line in args.stages.read_text().splitlines() if line.strip()]
    stage_pins = {f"{st[0]}/die{d}/{f}": sha(Path(p) / f) for st in stages for d, p in enumerate(st[1:-1])
                  for f in ("matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex", "program.hex", "segments.hex")}
    if any(st[0] == "E" for st in stages) and args.no_embed_rom:
        raise SystemExit("stage E needs the embedding ROM")
    # KV history (before P) as raw u32 for the host's HBM preload
    kvdir = out / "kv_pre_bin"
    kvdir.mkdir(exist_ok=True)
    kv_pins = {}
    for st in stages:
        if st[0] == "E":
            continue
        n = int(st[0][1:])
        for d in range(args.tp):
            src = args.oracle / "kv_pre" / f"L{n}_die{d}.npy"
            np.load(src).astype("<u4").tofile(kvdir / f"L{n}_die{d}.bin")
            kv_pins[f"L{n}_die{d}"] = sha(src)
    emb = json.loads((args.oracle / "embedding_row.json").read_text())
    if emb["token"] != args.token:
        raise SystemExit("oracle embedding row is another token")
    embed_bin = out / "embedding_row.bin"
    embed_bin.write_bytes(int(args.token).to_bytes(4, "little") + int(emb["scale_bf16"], 16).to_bytes(2, "little")
                          + bytes.fromhex(emb["codes_hex"]))
    env = dict(os.environ, RT_THREADS=str(args.threads))
    t0 = time.monotonic()
    with open(out / "token.log", "w") as log:
        p = subprocess.run([str(binary), "--stages", str(args.stages), str(out), str(args.oracle / "x_preload.hex"),
                            "--pos", str(args.pos), "--token", str(args.token), "--kv-dir", str(kvdir), "--embed-bin", str(embed_bin), "--kv-ideal", str(kv_ideal)], cwd=out,
                           stdout=log, stderr=subprocess.STDOUT, env=env)
    wall = time.monotonic() - t0
    text = (out / "token.log").read_text()
    per_stage = {}
    for mm in re.finditer(r"STAGE (\S+) done (.*)", text):
        kv = dict(item.split("=", 1) for item in mm.group(2).split() if "=" in item)
        per_stage[mm.group(1)] = {"cycles": int(kv["cycles"]), "me_clock_edges": kv["me_busy"]}
    for mm in re.finditer(r"MEMSTAT (\S+) (die\d) (.*)", text):
        per_stage.setdefault(mm.group(1), {}).setdefault("memory", {})[mm.group(2)] = {
            k: int(v) for k, v in (item.split("=", 1) for item in mm.group(3).split())}
    checks, kv_checks = {}, {}
    for name, *_ in stages:
        if name == "E":
            want_x = [ln for ln in (args.oracle / "x_preload.hex").read_text().split() if not ln.startswith("@")]
            for d in range(args.tp):
                got_p = out / f"E_die{d}_x.hex"
                got = got_p.read_text().split() if got_p.exists() else []
                mism = [i for i, (a, b) in enumerate(zip(got, want_x)) if a != b]
                checks[f"E_die{d}_x"] = {"words": len(got), "mismatches": len(mism) + abs(len(got) - len(want_x)),
                                         "first_mismatch": ({"index": mism[0], "rtl": got[mism[0]], "golden": want_x[mism[0]]}
                                                            if mism else None), "actual_sha256": sha(got_p) if got else None}
            continue
        n = int(name[1:])
        for d in range(args.tp):
            got_p, want_p = out / f"{name}_die{d}_x.hex", args.oracle / f"L{n:02d}_die{d}_x.hex"
            got = got_p.read_text().split() if got_p.exists() else []
            want = want_p.read_text().split() if want_p.exists() else []
            mism = [i for i, (a, b) in enumerate(zip(got, want)) if a != b]
            checks[f"{name}_die{d}_x"] = {"words": len(got), "mismatches": len(mism) + abs(len(got) - len(want)),
                                          "first_mismatch": ({"index": mism[0], "rtl": got[mism[0]], "golden": want[mism[0]]}
                                                             if mism else None),
                                          "actual_sha256": sha(got_p) if got else None, "expected_sha256": sha(want_p) if want else None}
            if not args.kv_ideal:
                kp = out / f"{name}_die{d}_kvP.hex"
                gold = json.loads((args.oracle / "kv_at_P" / f"L{n}_die{d}.json").read_text())
                want_k = [e4m3(int(b, 16)) for b in gold["k_bits"]]
                want_v = [e4m3(int(b, 16)) for b in gold["v_bits"]]
                rows = [ln.split() for ln in kp.read_text().splitlines()] if kp.exists() else []
                got_k = [int(r[3], 16) for r in rows if r[0] == "K"]
                got_v = [int(r[3], 16) for r in rows if r[0] == "V"]
                kv_checks[f"{name}_die{d}"] = {"k_codes": len(got_k), "v_codes": len(got_v),
                                               "k_mismatches": sum(a != b for a, b in zip(got_k, want_k)) + abs(len(got_k) - 256),
                                               "v_mismatches": sum(a != b for a, b in zip(got_v, want_v)) + abs(len(got_v) - 256)}
    end_pins = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    stable = end_pins == start_pins
    m = re.search(r"QWEN_ROM_REALMEM PASS stages=(\d+) cycles=(\d+).*RSS_KiB=(\d+)", text)
    good = (p.returncode == 0 and bool(m) and stable and all(c["mismatches"] == 0 for c in checks.values())
            and all(c["k_mismatches"] == 0 and c["v_mismatches"] == 0 for c in kv_checks.values()))
    result = {
        "schema": "opentallas.qwen-rom-rt-real-memory.v1", "status": "pass" if good else "fail",
        "configuration": "KV_IDEAL A/B reference (HBM bypassed, slices preloaded)" if args.kv_ideal else "REAL_MEM",
        "position": args.pos, "token": args.token, "returncode": p.returncode,
        "design_point": {"posted_kv": bool(args.posted_kv), "tp": args.tp, "groups_per_die": G, "su_width": args.su_width, "su_reducer_time_levels": args.lv,
                         "smin": args.smin, "smax": args.smax, "tree_cut": args.tcut, "collective_lat_cycles": args.coll_lat,
                         "collective_depth": args.coll_depth, "code_banks": args.code_banks, "mem_extra": args.mem_extra},
        "wire_stages": {"bd": args.bd, "xvm": args.xvm, "nws": args.nws, "tws": args.tws, "ord": args.ord},
        "memory_services": {"hbm": "ot_qwen_hbm_model_ack NPC=32 one HBM3E stack/die, CLK_PS=833, PC_RDY=1, WR_ACK=1",
                            "kv_fill": {"fill_lat": args.fill_lat, "outstanding_reads": args.nrd, "lookahead_units": args.lka,
                                        "request_sectors": 16},
                            "scale_rom": f"{G >> args.smin} ports x {args.scale_banks} ot_rom_4096x266_m8",
                            "code_rom": f"per tile 2 x {args.code_banks} ot_rom_4096x266_m8 (hardened ot_qwen_rom_tile_w12)",
                            "kv_slices": "per tile 2 x ot_sram_1r1w_128x256_m1_r2c2 (KV_LOCAL=1)"},
        "stages_run": [s[0] for s in stages], "total_cycles": int(m.group(2)) if m else None,
        "stages": per_stage, "layer_x_checks": checks, "token_kv_writeback_checks": kv_checks,
        "simulate_wall_seconds": round(wall, 1), "max_rss_kib": int(m.group(3)) if m else None,
        "source_sha256": start_pins, "source_stable": stable, "stage_image_sha256": stage_pins,
        "kv_history_sha256": kv_pins, "oracle_json_sha256": sha(args.oracle.parent / "oracle.json"),
        "binary_sha256": sha(binary), "generated_core_sha256": sha(core_sv), "steps": steps,
    }
    target = args.result or (out / "realmem_result.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "total_cycles": result["total_cycles"],
                      "stages": {k: v.get("cycles") for k, v in per_stage.items()}}, indent=2))
    if not good:
        print(text[-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()

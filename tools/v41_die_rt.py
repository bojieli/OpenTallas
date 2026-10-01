#!/usr/bin/env python3
"""W17: the adopted V4.1 TP-4 layer-die group by runtime composition -- build, run one full-shape layer, check.

    python3 tools/v41_die_rt.py build --work W [--jobs 8] [--attn-obj DIR]
    python3 tools/v41_die_rt.py run   --work W --images IMGROOT --out OUT [--threads 24] [--result R]

Models (Verilator 5.050, each compiled once): ot_v41_rt_die RANK 0..3 (the die: ot_chip_v41x_die FULL_SHAPE with
X_ROM -- the ROM-field spine in the core -- and the attention engine cut), ot_v41_pair (FP8/FP4-only and
BF16-capable), ot_v41_retn, ot_v41_ret_root, ot_hdc_v41x_attn (full geometry, hierarchical; built by the
`attn` step or given with --attn-obj).  Host: rtl/test/v41_runtime/v41_die_rt.cpp (4 dies, 4 ROM fields, 4
attention engines, W15 deterministic-release link delay lines).

IMGROOT/r<d>/: tools/v41_die_l0_images.py (program, CROM, HE banks, VM, HBM, cfg.txt, prime.txt, weights.json,
expect_vm.hex) + tools/v41_die_field.py (the ROM field of that rank).  The check: every rank's final vector memory
equals the TP-4 ISA executor's (itself bit-exact against the golden layer: results/rtl/w17_l0_fullshape_isa.json),
and the golden layer outputs are read back from their regions.
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
VERILATOR = os.environ.get("OT_VERILATOR", os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
RT = ROOT / "rtl/test/v41_runtime"
W10 = [ROOT / f"rtl/v41rom/{n}.sv" for n in ("ot_v41_ret", "ot_v41_rom_elem", "ot_v41_bterm", "ot_v41_chain",
                                              "ot_v41_segtree", "ot_v41_bf16_lanes")]
LEAF = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")] + \
       [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
DIE_EXTRA = [ROOT / "rtl/v41die/ot_v41_rom_adapt.sv", ROOT / "rtl/w17_runtime/v41die/ot_v41_spine.sv",
             ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv", RT / "ot_v41_rt_die.sv"]
ATTN = [ROOT / f"rtl/hdc/v41x/{n}.sv" for n in ("ot_hdc_v41x_attn_tile", "ot_hdc_v41x_attn", "ot_hdc_v41x_attn_staging")] + \
       [ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
        ROOT / "rtl/hdc/ot_hdc_fastfp.sv"]
ATTN_VLT = ROOT / "results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt"
HOST = [RT / "v41_die_rt.cpp", ROOT / "rtl/test/qwen_runtime/qwen_rt_matvec.hpp"]
ROM_PHW = 6
CL = dict(CL_LANES=16, CL_DEPTH=512, CL_RELAY=0)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def die_sources() -> list[Path]:
    import w17_runtime_rtl_chip_v41x_die_smoke as D
    return [Path(p) for p in D.sources("rtl")]


def l20_sources() -> list[Path]:
    return [ROOT / x for x in (ROOT / "tools/w11_ckvdie_src_l20.txt").read_text().split()]


def all_sources(l20: bool = False) -> list[Path]:
    die = l20_sources() + [ROOT / "tools/w11_ckvdie_src_l20.txt"] if l20 else die_sources() + DIE_EXTRA + [ROOT / "tools/w17_runtime_rtl_chip_v41x_die_smoke.py",
                                                        ROOT / "tools/rtl_hdc_v41x_decode_campaign.py"]
    return sorted(set(die + W10 + LEAF + ATTN + [ATTN_VLT] + HOST +
                      [ROOT / "rtl/w17_runtime/v41die/ot_v41_pair.sv", ROOT / "rtl/w17_runtime/v41die/ot_v41_retn.sv",
                       RT / "ot_rom_8192x274_m8_rt.sv",
                       ROOT / "rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh", Path(__file__)]))


def run(cmd, log: Path, cwd=None):
    t0 = time.monotonic()
    p = subprocess.run(["/usr/bin/time", "-v", *map(str, cmd)], cwd=cwd, capture_output=True, text=True)
    log.write_text(p.stdout + p.stderr)
    rss = re.search(r"Maximum resident set size \(kbytes\): (\d+)", p.stderr)
    step = dict(log=log.name, seconds=round(time.monotonic() - t0, 1), returncode=p.returncode,
                max_rss_kib=int(rss.group(1)) if rss else None)
    if p.returncode:
        raise SystemExit(f"{log.name} failed:\n{(p.stdout + p.stderr)[-4000:]}")
    return step


def build(a) -> dict:
    w = a.work.resolve()
    w.mkdir(parents=True, exist_ok=True)
    steps = []
    base = [VERILATOR, "--cc", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD"]
    mk = lambda pre: ["make", "-C", w / pre, "-f", f"V{pre}.mk", f"-j{a.jobs}", f"V{pre}__ALL.a",
                      "OPT_FAST=-O2", "OPT_SLOW=-O1", "OPT_GLOBAL=-O1"]
    models = []
    for r in range(4):
        if getattr(a, "l20", False):
            # the indexed-layer die: W11's selected-CKV die copies + ring indexer (tools/w11_ckvdie_src_l20.txt)
            l20 = l20_sources()
            models.append((f"die{r}", "ot_v41_rt_die_l20",
                           ["-fno-gate", "-DV41_ATT_CUT", f"-I{ROOT / 'rtl/hdc/v41'}", f"-GRANK={r}", f"-GROM_PHW={ROM_PHW}",
                            "-GX_IDX=2", "-GX_SEL=1", "-GIDX_RING=1", "-GSUN=256", "-GSUM=64",
                            *[f"-G{k}={v}" for k, v in CL.items()]], l20))
            continue
        models.append((f"die{r}", "ot_v41_rt_die",
                       ["-fno-gate", "-DV41_ATT_CUT", f"-I{ROOT / 'rtl/hdc/v41'}", f"-GRANK={r}", f"-GROM_PHW={ROM_PHW}",
                        *[f"-G{k}={v}" for k, v in CL.items()]], die_sources() + DIE_EXTRA))
    for pre, bf, xf in (("pq", 0, 4), ("pb", 1, 8)):
        models.append((pre, "ot_v41_pair", ["-DV41_RT", f"-GPHW={ROM_PHW}", f"-GBF16={bf}", f"-GXF={xf}"],
                       [ROOT / "rtl/w17_runtime/v41die/ot_v41_pair.sv", RT / "ot_rom_8192x274_m8_rt.sv", *W10, *LEAF]))
    models.append(("retn", "ot_v41_retn", ["-DV41_RT", "-GRD=64", "-GRST=1", "-GBYPASS=1"],
                   [ROOT / "rtl/w17_runtime/v41die/ot_v41_retn.sv", *W10, *LEAF]))
    models.append(("root", "ot_v41_ret_root", ["-GD=128", "-GQD=128"], [*W10, *LEAF]))
    for pre, top, extra, files in models:
        if a.only and pre not in a.only.split(","):
            continue
        if (w / pre / f"V{pre}__ALL.a").exists():
            continue
        steps.append(run(base + ["--top-module", top, "--prefix", f"V{pre}", "--Mdir", w / pre, *extra, *files],
                         w / f"verilate_{pre}.log"))
        steps.append(run(mk(pre), w / f"build_{pre}.log"))
    return dict(steps=steps)


def attn(a) -> dict:
    w = a.work.resolve()
    obj = w / "attn"
    cmd = [VERILATOR, "--cc", "--build", f"-j{a.jobs}", "--top-module", "ot_hdc_v41x_attn", "--prefix", "Vattn",
           "--Mdir", obj, "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD", "-Wno-lint", "-Wno-style",
           "--output-split", "20000", "--output-split-cfuncs", "2000", "--unroll-count", "1", "--unroll-limit",
           "131072", "-CFLAGS", "-O0", "-MAKEFLAGS", "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0", "--hierarchical",
           ATTN_VLT, "-GH=16", "-GD=512", "-GTD=32", "-GNL=4", "-GTROWS=640", "-GPWORDS=1", *ATTN]
    return dict(steps=[run(cmd, w / "verilate_attn.log")])


def link(a) -> Path:
    w = a.work.resolve()
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([VERILATOR, "-V"], text=True)).group(1)
    attn_obj = Path(a.attn_obj).resolve() if a.attn_obj else w / "attn"
    dirs = [w / p for p in ("die0", "die1", "die2", "die3", "pq", "pb", "retn", "root")] + [attn_obj]
    archives, inc = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}", f"-I{ROOT / 'rtl/test/qwen_runtime'}"}
    for d in dirs:
        # a hierarchical build carries its own libverilated.a (and libV<top>.a duplicating V<top>__ALL.a); the
        # host links the Verilator runtime once
        archives += sorted(x for x in d.rglob("*.a") if x.name != "libverilated.a" and
                           not (x.name.startswith("libV") and (x.parent / (x.name[3:-2] + "__ALL.a")).exists()))
        for h in d.rglob("V*.h"):
            inc.add(f"-I{h.parent}")
    exe = w / "v41_die_rt"
    pw = 32 * CL["CL_LANES"] + 3 + 32
    run(["g++", "-std=c++20", "-O2", "-pthread", f"-DROM_PHW={ROM_PHW}", f"-DCL_PW_BITS={pw}",
         *(["-DV41_L20"] if getattr(a, "l20", False) else []), *sorted(inc),
         RT / "v41_die_rt.cpp", "-Wl,--start-group", *archives, "-Wl,--end-group",
         f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
         f"{vroot}/include/verilated_dpi.cpp", "-o", exe], w / "link.log")
    return exe


def check(images: Path, out: Path) -> dict:
    res = {}
    for r in range(4):
        exp = (images / f"r{r}" / "expect_vm.hex").read_text().split()
        got = (out / f"vm{r}.hex").read_text().split()
        length_ok = len(exp) == len(got)
        bad = [i for i, (x, y) in enumerate(zip(exp, got)) if int(x, 16) != int(y, 16)]
        res[f"r{r}"] = dict(words=len(exp), actual_words=len(got), length_ok=length_ok,
                            pass_exact=length_ok and not bad, mismatches=len(bad), first=[(i, got[i], exp[i]) for i in bad[:8]])
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("build", "attn", "link", "run"))
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--only")
    ap.add_argument("--attn-obj")
    ap.add_argument("--images", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--threads", type=int, default=24)
    ap.add_argument("--max-cycles", type=int, default=400000)
    ap.add_argument("--result", type=Path)
    ap.add_argument("--wrong-edge", action="store_true")
    ap.add_argument("--l20", action="store_true", help="the L20 die (ot_v41_rt_die_l20: selected CKV + ring indexer)")
    a = ap.parse_args()
    if a.step == "build":
        print(json.dumps(build(a), indent=1))
        return 0
    if a.step == "attn":
        print(json.dumps(attn(a), indent=1))
        return 0
    if a.step == "link":
        print(link(a))
        return 0
    exe = a.work.resolve() / "v41_die_rt"
    tgt = a.result or (a.out / "result.json")
    if tgt.exists() or a.out.exists() and any(a.out.iterdir()):
        raise SystemExit("Refusing existing result/output; use unique paths")
    a.out.mkdir(parents=True, exist_ok=True)
    pins = {str(p.relative_to(ROOT)): sha(p) for p in all_sources(a.l20)}
    env = dict(os.environ, RT_THREADS=str(a.threads))
    t0 = time.monotonic()
    cmd = [str(exe), str(a.images.resolve()), str(a.out.resolve()), str(a.max_cycles)] + (["--wrong-edge"] if a.wrong_edge else [])
    p = subprocess.run(["/usr/bin/time", "-v", *cmd], capture_output=True, text=True, env=env,
                       cwd=a.images.resolve())
    (a.out / "run.log").write_text(p.stdout + p.stderr)
    lines = p.stdout.splitlines()
    done = [ln for ln in lines if ln.startswith("DONE")]
    rec = dict(schema="opentallas.rtl.w17_v41_die_rt_layer.v1", returncode=p.returncode, tail=lines[-6:], done=done,
               wall_s=round(time.monotonic() - t0, 1),
               rss=re.search(r"Maximum resident set size \(kbytes\): (\d+)", p.stderr).group(1)
               if "Maximum resident" in p.stderr else None,
               check=check(a.images, a.out) if p.returncode == 0 else None, images=str(a.images),
               image_record_sha256={f"r{r}/{f}": sha(a.images / f"r{r}" / f) for r in range(4)
                                    for f in ("prog.hex", "cfg.txt", "weights.json", "expect_vm.hex", "field_phases.json")
                                    if (a.images / f"r{r}" / f).exists()},
               source_sha256=pins, host_binary_sha256=sha(exe))
    completed = {int(m.group(1)) for ln in done
                 if (m := re.fullmatch(r"DONE die=([0-3]) cyc=\d+ core_cycles=\d+ fault=00", ln))}
    rec["pass_exact"] = (p.returncode == 0 and len(done) == 4 and completed == set(range(4))
                         and any(ln.startswith("END cycles=") for ln in lines)
                         and all(x["pass_exact"] for x in (rec["check"] or {}).values()))
    tgt.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("returncode", "tail", "done", "wall_s", "check")}, indent=1))
    return 0 if rec["pass_exact"] else 1


if __name__ == "__main__":
    sys.exit(main())

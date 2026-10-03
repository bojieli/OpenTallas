#!/usr/bin/env python3
"""Split-clock exact gate of the Qwen ROM decode core (reduced G4 / SU 16, BF16 weight ROM, KV SRAM).

    python3 rtl/test/two_clock/run_core_2clk.py --workdir SCRATCH --output R.json [--jobs N]

Builds three Verilator binaries of rtl/test/two_clock/tb_hdc_core_2clk.sv:
  pinned  -- the pinned rtl/hdc/ot_hdc_core_vector_weight.sv (reference cycles);
  cdc0    -- the emitted ot_hdc_core_vector_weight_2clk with ME_CDC = 0 (default-off: must be cycle-identical);
  cdc1    -- ME_CDC = 1: matrix engine on the 1.2 GHz clock behind ot_ratio_cdc_fifo crossings;
  cdc1_rowchase -- ME_CDC = 1 with ME_CDC_SAFE_CHASE = 0 (diagnostic: the single-clock row chase, not proven rate-safe).
Runs: one decode step on the golden-prefilled KV (every logit / vector-memory / KV word exact vs the ISA model)
and the 16-prompt + 3-generated multi-step run (every step's logits / VM / KV vs the ISA model's per-step snapshot,
generated ids vs the torch oracle), at +CLK=slow (all 0.9 GHz), +CLK=fast (all 1.2 GHz, reference only) and
+CLK=split (ME 1.2 GHz, the rest 0.9 GHz; three fclk divider phases).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as C  # noqa: E402

TB = ROOT / "rtl/test/two_clock/tb_hdc_core_2clk.sv"
HARNESS = ROOT / "rtl/test/two_clock/hdc_core_2clk_harness.cpp"
PINNED = ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv"
WRAP = ROOT / "rtl/hdc/ot_hdc_me_2clk.sv"
FIFO = ROOT / "rtl/common/ot_ratio_cdc_fifo.sv"
CG = ROOT / "rtl/hdc/ot_hdc_cg.sv"
DYN = ROOT / "rtl/hdc/ot_hdc_dyn_ttiles.sv"
EMIT = ROOT / "tools/qwen_two_clock_core_emit.py"
BASE_RTL = [p for p in C.HDC if p.name != "ot_hdc_core.sv"] + [DYN, *C.PIPES]
ENV = dict(os.environ, HDC_GROUPS="4", HDC_SU_WIDTH="16")
G, SW = 4, 16
SINGLE = re.compile(r"HDC2C me_cdc=(\d+) token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) "
                    r"ticks=(\d+) fault=(\d+) logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+) collisions=(\d+)")
MULTI = re.compile(r"HDC2C_MULTI me_cdc=(\d+) steps=(\d+) generated=(\d+) token_mismatches=(\d+) "
                   r"logit_mismatches=(\d+) vm_mismatches=(\d+) kv_mismatches=(\d+) collisions=(\d+) "
                   r"total_cycles=(\d+) total_ticks=(\d+)")
ORACLE = '''
import sys
from pathlib import Path
sys.path.insert(0,"tools")
import hdc_program as P
model,prompt,_,_=P.golden_state(16)
lay=P.Layout(model)
mach=P.Machine(lay,P.np.zeros(lay.kv_elems,dtype=P.F))
prog=P.build_program(lay)
out=Path(sys.argv[1]); steps=int(sys.argv[2])
tokens=[]; logits=[]; vm=[]; kv=[]
for step in range(steps):
    token=int(prompt[step]) if step<len(prompt) else int(tokens[-1])
    tokens.append(int(mach.run(prog,token,step)))
    logits.extend(int(x) for x in P.G.bits(mach.logits))
    vm.extend(int(x) for x in P.G.bits(mach.vm))
    kv.extend(int(x) for x in P.G.bits(mach.kv))
(out/"expect_logits_steps.hex").write_text(P.hexwords(logits,32))
(out/"expect_vm_steps.hex").write_text(P.hexwords(vm,32))
(out/"expect_kv_steps.hex").write_text(P.hexwords(kv,32))
print(len(P.G.bits(mach.logits)), len(P.G.bits(mach.vm)), len(P.G.bits(mach.kv)), *tokens)
'''


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(obj: Path, sources: list, defines: list, params: list, jobs: int) -> Path:
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "-Wno-PINMISSING", "--top-module", "tb_hdc_core_2clk",
           f"-GG={G}", f"-GSW={SW}", *params, *defines, "-Mdir", str(obj), f"-I{C.ISA_SVH.parent}",
           *map(str, sources), str(HARNESS), "-CFLAGS", "-O1", "-j", str(jobs)]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (obj.parent / f"{obj.name}.build.log").write_text(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError(f"build {obj.name} failed: {(p.stdout + p.stderr)[-3000:]}")
    return obj / "Vtb_hdc_core_2clk"


def run(exe: Path, img: Path, args: list, clk: str, fphase: int = 0) -> dict:
    argv = [str(exe), f"+DIR={img}", *args, f"+CLK={clk}", f"+FPHASE={fphase}"]
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    rec = dict(argv=argv[1:], returncode=p.returncode, passed="\nPASS" in p.stdout and p.returncode == 0,
               stdout_tail=p.stdout[-2500:])
    m = SINGLE.search(p.stdout)
    if m:
        rec.update(dict(zip(("me_cdc", "token", "pos", "next_token", "expect", "cycles", "ticks", "fault",
                             "logit_mismatch", "vm_mismatch", "kv_mismatch", "collisions"), map(int, m.groups()))))
    m = MULTI.search(p.stdout)
    if m:
        rec.update(dict(zip(("me_cdc", "steps", "generated", "token_mismatches", "logit_mismatches", "vm_mismatches",
                             "kv_mismatches", "collisions", "total_cycles", "total_ticks"), map(int, m.groups()))))
        rec["per_step"] = [dict(zip(("step", "cycles", "ticks"), map(int, x)))
                           for x in re.findall(r"STEP2C step=(\d+) .*? cycles=(\d+) ticks=(\d+)", p.stdout)]
    if "ticks" in rec:
        rec["token_ns"] = round(rec["ticks"] * 2500 / 9 / 1000, 3)
    if "total_ticks" in rec:
        rec["total_ns"] = round(rec["total_ticks"] * 2500 / 9 / 1000, 3)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    w = a.workdir.resolve()
    w.mkdir(parents=True, exist_ok=True)
    img = w / "img"
    gen = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img), "--context", "16"],
                         cwd=ROOT, env=ENV, capture_output=True, text=True)
    if gen.returncode:
        raise SystemExit("images: " + gen.stdout[-2000:] + gen.stderr[-2000:])
    steps = 16 + 3 - 1
    orc = subprocess.run([sys.executable, "-c", ORACLE, str(img), str(steps)], cwd=ROOT, env=ENV,
                         capture_output=True, text=True, check=True)
    subprocess.run([sys.executable, str(EMIT), "--out", str(w / "gen")], cwd=ROOT, check=True, capture_output=True)
    emitted = w / "gen/ot_hdc_core_vector_weight_2clk.sv"
    builds = {"pinned": ([*BASE_RTL, PINNED, TB], ["+define+PINNED_CORE"], []),
              "cdc0": ([*BASE_RTL, CG, FIFO, WRAP, emitted, TB], [], ["-GME_CDC=0"]),
              "cdc1": ([*BASE_RTL, CG, FIFO, WRAP, emitted, TB], [], ["-GME_CDC=1"]),
              "cdc1_rowchase": ([*BASE_RTL, CG, FIFO, WRAP, emitted, TB], [], ["-GME_CDC=1", "-GSAFE_CHASE=0"])}
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {k: ex.submit(build, w / f"obj_{k}", *v, a.jobs) for k, v in builds.items()}
        exes = {k: f.result() for k, f in futs.items()}
    single_args = (img / "run.args").read_text().split()
    multi_args = ["+MULTI", "+STEPEXP", "+NPROMPT=16", "+NGEN=3"]
    plan = []
    for kind, args in (("single", single_args), ("multi", multi_args)):
        plan += [(f"pinned/{kind}/slow", "pinned", args, "slow", 0),
                 (f"pinned/{kind}/fast", "pinned", args, "fast", 0),
                 (f"cdc0/{kind}/slow", "cdc0", args, "slow", 0),
                 (f"cdc0/{kind}/split", "cdc0", args, "split", 0),
                 (f"cdc1/{kind}/slow", "cdc1", args, "slow", 0)]
        plan += [(f"cdc1/{kind}/split/fphase{ph}", "cdc1", args, "split", ph) for ph in (0, 1, 2)]
        plan += [(f"cdc1_rowchase/{kind}/split/fphase{ph}", "cdc1_rowchase", args, "split", ph) for ph in (0, 1, 2)]
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = dict(zip([p[0] for p in plan], ex.map(lambda p: run(exes[p[1]], img, p[2], p[3], p[4]), plan)))
    srcs = sorted({*BASE_RTL, PINNED, WRAP, FIFO, CG, TB, HARNESS, EMIT, Path(__file__),
                   ROOT / "tools/hdc_program.py", ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_isa.py", C.ISA_SVH})
    rec = dict(schema="opentallas.qwen_rom_two_clock_core_gate.v1",
               configuration=dict(groups=G, su_width=SW, su="vector (ot_hdc_vstream)", weights="BF16 ROM",
                                  kv="SRAM (behavioural 1R1W, slow write / fast read clock)", context=16,
                                  multi=dict(prompt=16, generated=3, steps=steps), cdc_depth=4,
                                  tick_ps="2500/9", slow_ticks=4, fast_ticks=3),
               isa_oracle_stdout=orc.stdout.strip(), images_sha256={p.name: sha(p) for p in sorted(img.iterdir())
                                                                   if p.is_file()},
               emitted_core_sha256=sha(emitted), model_sha256=sha(ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"),
               simulator=subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in srcs}, runs=res)
    # cdc0/*/split is a NEGATIVE CONTROL: the single-clock core against fast-clocked engine memories must FAIL
    # (the bench sees a clock-domain mistake); every other run must PASS
    neg = {k for k in res if k.startswith("cdc0/") and "/split" in k}
    rec["negative_controls"] = {k: ("FAIL_AS_EXPECTED" if not res[k]["passed"] else "UNEXPECTED_PASS") for k in neg}
    ok = all(r["passed"] for k, r in res.items() if k not in neg) and all(not res[k]["passed"] for k in neg)
    s = {k: res[k] for k in res}
    ident = all(s[f"cdc0/{k}/slow"].get(f) == s[f"pinned/{k}/slow"].get(f)
                for k, f in (("single", "cycles"), ("multi", "total_cycles")))
    rec["cdc0_cycle_identical_to_pinned"] = ident
    rec["verdict"] = "PASS" if ok and ident else "FAIL"
    try:
        sl, sp = s["pinned/single/slow"], [s[f"cdc1/single/split/fphase{p}"] for p in (0, 1, 2)]
        ml, mp = s["pinned/multi/slow"], [s[f"cdc1/multi/split/fphase{p}"] for p in (0, 1, 2)]
        fs, fm = s["pinned/single/fast"], s["pinned/multi/fast"]
        rec["timing_summary"] = dict(
            single_step_ns=dict(all_0p9=sl["token_ns"], all_1p2_reference=fs["token_ns"],
                                split=[x["token_ns"] for x in sp]),
            single_step_slow_cycles=dict(all_0p9=sl["cycles"], split=[x["cycles"] for x in sp]),
            multi_total_ns=dict(all_0p9=ml["total_ns"], all_1p2_reference=fm["total_ns"],
                                split=[x["total_ns"] for x in mp]),
            multi_total_slow_cycles=dict(all_0p9=ml["total_cycles"], split=[x["total_cycles"] for x in mp]),
            split_vs_all_0p9_single=[round(x["token_ns"] / sl["token_ns"] - 1, 5) for x in sp],
            split_vs_all_0p9_multi=[round(x["total_ns"] / ml["total_ns"] - 1, 5) for x in mp],
            diagnostic_rowchase_unproven=dict(
                single_step_ns=[s[f"cdc1_rowchase/single/split/fphase{p}"]["token_ns"] for p in (0, 1, 2)],
                multi_total_ns=[s[f"cdc1_rowchase/multi/split/fphase{p}"]["total_ns"] for p in (0, 1, 2)]),
            cdc1_same_clock_overhead_slow_cycles=dict(
                single=s["cdc1/single/slow"]["cycles"] - sl["cycles"],
                multi=s["cdc1/multi/slow"]["total_cycles"] - ml["total_cycles"]))
    except KeyError as exc:
        rec["timing_summary_error"] = str(exc)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"], json.dumps(rec.get("timing_summary"), indent=1))
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

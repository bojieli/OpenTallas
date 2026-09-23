#!/usr/bin/env python3
"""Token-level RTL simulation of the hardwired decode core (HDC).

Runs, from the repository root:

1. the special-function pipelines (exp, reciprocal, rsqrt) under Icarus on
   18,010 golden vectors with random bubbles, bit for bit;
   the core's multipliers under Verilator: the stage-rebalanced FP32 multiplier
   cycle-equivalent to the qualified pipe, and the exact BF16 multiplier equal
   to it wherever it does not refuse, on 20 million edge-biased operand pairs;
2. a Verilator lint of the core;
3. the core under Verilator on the reduced Qwen3 vehicle:
   * one decode step at position 15 on the golden-prefilled KV cache, checked
     bit for bit against the ISA-level model (every logit, the whole vector
     memory, the whole KV cache) and against the oracle's next token;
   * an end-to-end run from an EMPTY KV cache: the core consumes all 16 prompt
     tokens (writing its own KV rows) and then generates 3 tokens, compared
     with the torch oracle's generated ids.

Images come from tools/hdc_program.py; arithmetic is tools/hdc_golden.py.
Writes results/rtl/hdc_decode_campaign.json.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402

OUT = ROOT / "results/rtl/hdc_decode_campaign.json"
PIPES = [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
ISA_SVH = ROOT / "rtl/hdc/ot_hdc_isa.svh"
HDC = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                          "ot_hdc_reduce", "ot_hdc_matvec", "ot_hdc_stream", "ot_hdc_core")]
TB_SFU = ROOT / "rtl/test/tb_hdc_sfu.sv"
TB_MUL = ROOT / "rtl/test/tb_hdc_mul_equiv.sv"
HARNESS_MUL = ROOT / "rtl/test/hdc_mul_equiv_harness.cpp"
MUL_VECTORS = 20_000_000
TB_CORE = ROOT / "rtl/test/tb_hdc_core.sv"
HARNESS = ROOT / "rtl/test/hdc_core_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_isa.py", ROOT / "tools/hdc_program.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
SINGLE = re.compile(r"HDC token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
UTIL = re.compile(r"UTIL me_issue_cycles=(\d+) su_issue_cycles=(\d+) both_idle_cycles=(\d+)")
STEP = re.compile(r"STEP pos=(\d+) in=(\d+) out=(\d+) gold=(\d+) cycles=(\d+) fault=(\d+)")
MULTI = re.compile(r"HDC_MULTI steps=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sfu_vectors(path: Path) -> int:
    rng = np.random.default_rng(1)
    F = np.float32
    ex = np.concatenate([rng.uniform(-100, 100, 3000), rng.uniform(-20, 5, 3000),
                         [0, -0.0, 88, -87, 88.5, -90, 1e-30, -1e-30, 0.3465735, -0.3465735]]).astype(F)
    rc = np.concatenate([np.exp(rng.uniform(-80, 80, 3000)), -np.exp(rng.uniform(-80, 80, 1000)),
                         rng.uniform(1, 40, 2000)]).astype(F)
    rs = np.concatenate([np.exp(rng.uniform(-80, 80, 3000)), rng.uniform(1e-6, 2, 3000)]).astype(F)
    lines = []
    for f, xs, fn in ((0, ex, G.exp), (1, rc, G.reciprocal), (2, rs, G.rsqrt)):
        for x, y in zip(xs, np.asarray(fn(xs), dtype=F)):
            lines.append(f"{f:x} {int(G.bits(x)):08x} {int(G.bits(y)):08x}\n")
    rng.shuffle(lines)
    path.write_text("".join(lines))
    return len(lines)


def run() -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        # 1. special functions
        n_vec = sfu_vectors(s / "sfu.txt")
        subprocess.run(["iverilog", "-g2012", "-o", str(s / "sfu.vvp"), str(TB_SFU),
                        *map(str, HDC[0:4]), *map(str, PIPES)], check=True)
        sfu = subprocess.run(["vvp", "-n", str(s / "sfu.vvp"), f"+VEC={s / 'sfu.txt'}"],
                             check=True, capture_output=True, text=True).stdout
        m = re.search(r"SFU vectors=(\d+) checked=(\d+) errors=(\d+)", sfu)
        sfu_rec = {"vectors": n_vec, "checked": int(m.group(2)), "errors": int(m.group(3)),
                   "pass": "PASS" in sfu and int(m.group(3)) == 0 and int(m.group(2)) == n_vec}
        # 1b. multipliers
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNUSED", "--top-module", "tb_hdc_mul_equiv", "-Mdir", str(s / "objm"),
                        str(HDC[1]), str(HDC[2]), *map(str, PIPES), str(TB_MUL), str(HARNESS_MUL),
                        "-CFLAGS", "-O1"], check=True, capture_output=True)
        mul = subprocess.run([str(s / "objm" / "Vtb_hdc_mul_equiv"), f"+N={MUL_VECTORS}"], check=True,
                             capture_output=True, text=True).stdout
        m1 = re.search(r"MULEQ checked=(\d+) mismatches=(\d+)", mul)
        m2 = re.search(r"BMULEQ checked=(\d+) faulted=(\d+) mismatches=(\d+)", mul)
        mul_rec = {"vectors": MUL_VECTORS, "fp32_rebalanced_checked": int(m1.group(1)),
                   "fp32_rebalanced_mismatches": int(m1.group(2)), "bf16_exact_checked": int(m2.group(1)),
                   "bf16_refused": int(m2.group(2)), "bf16_mismatches": int(m2.group(3)),
                   "pass": "PASS" in mul}
        # 2. lint
        lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_core",
                               f"-I{ISA_SVH.parent}", *map(str, HDC), *map(str, PIPES)], capture_output=True, text=True)
        # 3. core
        img = s / "img"
        subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img)], check=True,
                       capture_output=True)
        obj = s / "obj"
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNUSED", "-Wno-BLKSEQ", "--top-module", "tb_hdc_core", "-Mdir", str(obj),
                        f"-I{ISA_SVH.parent}",
                        *map(str, HDC), *map(str, PIPES), str(TB_CORE), str(HARNESS), "-CFLAGS", "-O1"],
                       check=True, capture_output=True)
        exe = str(obj / "Vtb_hdc_core")
        args = (img / "run.args").read_text().split()
        one = subprocess.run([exe, f"+DIR={img}", *args], check=True, capture_output=True, text=True).stdout
        multi = subprocess.run([exe, f"+DIR={img}", "+MULTI", "+NPROMPT=16", "+NGEN=3"], check=True,
                               capture_output=True, text=True).stdout
        expect = json.loads((img / "expect.json").read_text())
        prog_len = expect["prog_words"]
        # scaling point: 8 lane groups
        img8, obj8 = s / "img8", s / "obj8"
        env8 = dict(os.environ, HDC_GROUPS="8")
        subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img8)], check=True,
                       capture_output=True, env=env8)
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNUSED", "-Wno-BLKSEQ", "--top-module", "tb_hdc_core", "-GG=8", "-Mdir", str(obj8),
                        f"-I{ISA_SVH.parent}",
                        *map(str, HDC), *map(str, PIPES), str(TB_CORE), str(HARNESS), "-CFLAGS", "-O1"],
                       check=True, capture_output=True)
        one8 = subprocess.run([str(obj8 / "Vtb_hdc_core"), f"+DIR={img8}", *(img8 / "run.args").read_text().split()],
                              check=True, capture_output=True, text=True).stdout
    m = SINGLE.search(one)
    token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
    u = list(map(int, UTIL.search(one).groups()))
    single = {"token": token, "position": pos, "next_token": nxt, "oracle_next_token": exp_tok,
              "cycles": cycles, "fault": fault, "logit_mismatches": bad_lg,
              "vector_memory_mismatches": bad_vm, "kv_cache_mismatches": bad_kv,
              "me_issue_cycles": u[0], "su_issue_cycles": u[1], "both_units_idle_cycles": u[2],
              "pass": "PASS" in one and nxt == exp_tok and fault == 0 and bad_lg + bad_vm + bad_kv == 0}
    steps = [dict(zip(("position", "input", "output", "oracle", "cycles", "fault"), map(int, x.groups())))
             for x in STEP.finditer(multi)]
    mm = list(map(int, MULTI.search(multi).groups()))
    multi_rec = {"prompt_tokens": 16, "generated_tokens": [st["output"] for st in steps],
                 "oracle_generated_tokens": [st["oracle"] for st in steps], "steps": mm[0],
                 "mismatches": mm[2], "total_cycles": mm[3], "generation_steps": steps,
                 "pass": "PASS" in multi and mm[2] == 0}
    m8 = SINGLE.search(one8)
    u8 = list(map(int, UTIL.search(one8).groups()))
    scale8 = {"groups": 8, "next_token": int(m8.group(3)), "cycles": int(m8.group(5)),
              "logit_mismatches": int(m8.group(7)), "vector_memory_mismatches": int(m8.group(8)),
              "kv_cache_mismatches": int(m8.group(9)), "me_issue_cycles": u8[0], "su_issue_cycles": u8[1],
              "both_units_idle_cycles": u8[2],
              "pass": "PASS" in one8 and int(m8.group(3)) == int(m8.group(4)) and int(m8.group(6)) == 0}
    macs = 4 * (128 * 192 + 128 * 128 + 128 * 768 + 384 * 128) + 128 * 4096
    status = "pass" if sfu_rec["pass"] and mul_rec["pass"] and single["pass"] and scale8["pass"] and multi_rec["pass"] and lint.returncode == 0 \
        else "fail"
    return {
        "schema": "opentallas.hdc-decode-campaign.v1",
        "status": status,
        "claim_boundary": "functional token-level RTL simulation (Verilator, cycle-accurate at the core "
                          "boundary) with behavioural synchronous-read memories; clock rate is not "
                          "claimed here -- see the ASAP7 physical records.",
        "vehicle": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16, ffn 384, vocab 4096)",
        "parameters": {"lanes_per_group": I.W_LANES, "groups": I.GROUPS, "interleave": I.INTERLEAVE,
                       "kv_positions": I.T_MAX,
                       "program_instructions": prog_len},
        "weight_macs_per_token": macs,
        "sfu": sfu_rec,
        "multipliers": mul_rec,
        "single_step": single,
        "end_to_end": multi_rec,
        "scaling_8_groups": scale8,
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                         for p in (ISA_SVH, *HDC, *PIPES, TB_SFU, TB_MUL, HARNESS_MUL, TB_CORE, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    s = result["single_step"]
    print(result["status"], "next token", s["next_token"], "cycles", s["cycles"],
          "generated", result["end_to_end"]["generated_tokens"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

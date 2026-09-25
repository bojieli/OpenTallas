#!/usr/bin/env python3
"""Token-level RTL simulation of the DeepSeek-V4.1 hardwired decode core.

Runs, from the repository root:

1. a Verilator lint of ot_hdc_core_v41;
2. the core under Verilator on the reduced DeepSeek-V4.1-Flash
   (build/models/deepseek-v4.1-flash-reduced-v2):
   * one decode step at position 7 (the oracle prompt's last token) from the
     golden-prefilled state, checked bit for bit against the ISA-level model
     (tools/hdc_program_v41.py) -- every logit, the whole vector memory, the
     whole KV cache -- and its token against the golden's and the oracle's
     (3118); the issue trace gives a per-operator cycle breakdown;
   * an end-to-end run from an EMPTY state: the core consumes the 8 prompt
     tokens (writing its own KV rows, compressed rows, index keys, compressor
     slots and Engram history) and generates --ngen tokens, compared with the
     ISA model's (which equal hdc_golden_v41's, step for step bit-exact), and
     its final vector memory and KV cache with the ISA model's;
   * (--context N) one step at position N-1 of the prompt cycled to N tokens,
     where the index top-k SELECTS (N > 17 for ratio-1 layers, > 33 for
     ratio-2), checked against the ISA model;
   * (--sweep-lanes W,...) the single step again with the stream unit built
     W lanes wide (tools/hdc_isa_v41.SU_LANES, HDC_SW), each checked the same way.

Arithmetic is tools/hdc_golden_v41.py; images from tools/hdc_program_v41.py.
Writes results/rtl/hdc_v41_decode_campaign.json.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_decode_campaign.json"
RTL = ([ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"] +
       [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                           "ot_hdc_reduce", "ot_hdc_matvec")] +
       [ROOT / f"rtl/hdc/v41/{n}.sv" for n in ("ot_hdc_engram_tables_pkg", "ot_hdc_engram_hash", "ot_hdc_select",
                                               "ot_hdc_blockdot", "ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_fdiv",
                                               "ot_hdc_fsqrt", "ot_hdc_softplus", "ot_hdc_sinkhorn_seq",
                                               "ot_hdc_sk_arith", "ot_hdc_sk_recip_rom", "ot_hdc_sinkhorn",
                                               "ot_hdc_sinkhorn_mc",
                                               "ot_hdc_v41_stream", "ot_hdc_v41_qe", "ot_hdc_v41_xu",
                                               "ot_hdc_v41_hcproj", "ot_hdc_core_v41")])
SVH = ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh"
TB = ROOT / "rtl/test/tb_hdc_core_v41.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41_harness.cpp"
TOOLS = [ROOT / f"tools/{n}.py" for n in ("hdc_golden", "hdc_golden_v41", "hdc_isa_v41", "hdc_program_v41",
                                          "hdc_timing_v41")] + \
        [Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY",
              "-Wno-IMPORTSTAR")
SINGLE = re.compile(r"HDC41 token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
UTIL = re.compile(r"UTIL me_busy=(\d+) su_busy=(\d+) qe_busy=(\d+) xu_busy=(\d+) he_busy=(\d+) all_idle=(\d+)")
ISSUE = re.compile(r"ISSUE cyc=(\d+) pc=(\d+) unit=(\d+)")
STEP = re.compile(r"STEP pos=(\d+) in=(\d+) out=(\d+) gold=(\d+) cycles=(\d+) fault=(\d+)")
MULTI = re.compile(r"HDC41_MULTI steps=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+) "
                   r"vm_mismatch=(\d+) kv_mismatch=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def category(tag):
    """Operator class of a program tag ("L12.softmax" -> "softmax")."""
    return tag.split(".", 1)[1] if "." in tag else tag


def breakdown(trace, tags, cycles):
    """Sequencer-attributed cycles: the interval up to an instruction's issue is
    charged to that instruction's operator (what the core waited for to issue
    it); the tail after the last issue to 'drain'."""
    issues = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in ISSUE.finditer(trace)]
    by = collections.Counter()
    ops = collections.Counter()
    prev = 0
    for cyc, pc, _unit in issues:
        c = category(tags[pc])
        by[c] += cyc - prev
        ops[c] += 1
        prev = cyc
    by["drain"] += cycles - prev
    return issues, {k: {"cycles": v, "issued_ops": ops.get(k, 0), "share": round(v / cycles, 4)}
                    for k, v in sorted(by.items(), key=lambda kv: -kv[1])}


def build(scratch: Path, lanes=None) -> Path:
    obj = scratch / f"obj{lanes or ''}"
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "--top-module", "tb_hdc_core_v41", "-Mdir", str(obj),
                    f"-I{SVH.parent}", f"+define+HDC_SW={lanes or I.SU_LANES}", *map(str, RTL), str(TB),
                    str(HARNESS), "-CFLAGS", "-O1", "-j", "8"],
                   check=True, capture_output=True)
    return obj / "Vtb_hdc_core_v41"


def images(out: Path, *extra, lanes=None):
    env = dict(os.environ, HDC_SW=str(lanes or I.SU_LANES))
    r = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program_v41.py"), "--out", str(out), *extra],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"hdc_program_v41 failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def single(exe, img, trace=True):
    args = (img / "run.args").read_text().split()
    run = subprocess.run([str(exe), f"+DIR={img}", *args, *(["+TRACE"] if trace else [])], check=True,
                         capture_output=True, text=True).stdout
    m = SINGLE.search(run)
    token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
    u = list(map(int, UTIL.search(run).groups()))
    rec = {"token": token, "position": pos, "next_token": nxt, "isa_next_token": exp_tok, "cycles": cycles,
           "fault": fault, "logit_mismatches": bad_lg, "vector_memory_mismatches": bad_vm,
           "kv_cache_mismatches": bad_kv,
           "unit_busy_cycles": dict(zip(("me", "su", "qe", "xu", "he"), u[:5])), "all_units_idle_cycles": u[5],
           "pass": "PASS" in run and nxt == exp_tok and fault == 0 and bad_lg + bad_vm + bad_kv == 0}
    return rec, run


def banking(prog, pos, lanes):
    """How the stream unit's vectors would fare in a vector memory of `lanes`
    word-interleaved banks (bank = element address mod lanes) instead of the
    behavioural many-ported one: a vector's lanes read a stream at stride
    si (VEC_I) or so (VEC_O); stride 0 is one broadcast read, an odd stride hits
    distinct banks, an even one collides.  Counted per vector (issue cycle) over
    the vector-memory streams (A..D reads, element writes) of the token."""
    dyn = I.dyn_values(0, pos)
    vec = clean = 0
    worst = collections.Counter()
    for f in prog:
        if f["unit"] != I.UNIT_SU or f["su_vec"] == I.VEC_SCALAR:
            continue
        if (f["pred"] == I.PRED_ODD and not pos & 1) or (f["pred"] == I.PRED_NZ and pos == 0):
            continue
        no, ni = f["su_nout"] + dyn[f["su_d_nout"]], f["su_nin"] + dyn[f["su_d_nin"]]
        if not no or not ni:
            continue
        n = no * -(-ni // lanes) if f["su_vec"] == I.VEC_I else -(-no // lanes) * ni
        axis = "si" if f["su_vec"] == I.VEC_I else "so"
        strides = [f[f"{x}_{axis}"] >> (1 if x in "bd" and f["b_half"] and axis == "si" else 0)
                   for x in "abcd" if f[f"{x}_src"] == I.SRC_VM and not (x == "c" and f["c_pair"])]
        if f["dst"] == I.DST_VM:
            strides.append(f[f"o_{axis}"])
        ok = all(st == 0 or st % 2 for st in strides)
        vec += n
        clean += n if ok else 0
        if not ok:
            worst[f"{axis}:{sorted(set(st for st in strides if st and not st % 2))}"] += n
    return {"bank_model": f"{lanes} banks, element address mod {lanes}", "vector_cycles": vec,
            "conflict_free_vector_cycles": clean, "conflict_free_share": round(clean / vec, 4) if vec else 1.0,
            "colliding_strides": dict(worst.most_common(8))}


def lane_sweep(s: Path, widths) -> list:
    """The single step at other stream-unit widths: same arithmetic, other lane counts."""
    import hdc_timing_v41 as T
    out = []
    for w in widths:
        img = s / f"img_sw{w}"
        images(img, lanes=w)
        rec, _ = single(build(s, w), img, trace=False)
        saved, I.SU_LANES = I.SU_LANES, w
        try:
            rec["timing_model_cycles"] = T.simulate(T.load_prog(img), rec["position"])
        finally:
            I.SU_LANES = saved
        out.append(dict(su_lanes=w, **rec))
    return out


def run(ngen: int, context: int, sweep=()) -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_core_v41",
                               f"-GSW={I.SU_LANES}", f"-I{SVH.parent}", *map(str, RTL)], capture_output=True, text=True)
        img = s / "img"
        isa_out = images(img, "--multi", str(ngen))
        exe = build(s)
        expect = json.loads((img / "expect.json").read_text())
        tags = [ln.split(" ", 1)[1] for ln in (img / "prog_tags.txt").read_text().splitlines()]
        one, trace = single(exe, img)
        issues, bd = breakdown(trace, tags, one["cycles"])
        import hdc_timing_v41 as T
        prog = T.load_prog(img)
        tm, tiss = T.simulate(prog, one["position"], trace=True)
        model_at = {n: g for g, n, _ in tiss}
        err = [model_at[pc] - c for c, pc, _ in issues]
        one["timing_model"] = {"cycles": tm, "relative_error": round((tm - one["cycles"]) / one["cycles"], 6),
                               "max_abs_issue_error_cycles": max(map(abs, err))}
        one["vector_memory_banking"] = banking(prog, one["position"], I.SU_LANES)
        one["golden_next_token"] = expect["golden"]
        one["oracle_next_token"] = expect["oracle"]
        one["pass"] = one["pass"] and one["next_token"] == expect["golden"]
        multi = subprocess.run([str(exe), f"+DIR={img}", "+MULTI", "+NPROMPT=8", f"+NGEN={ngen}"], check=True,
                               capture_output=True, text=True).stdout
        steps = [dict(zip(("position", "input", "output", "isa_output", "cycles", "fault"), map(int, x.groups())))
                 for x in STEP.finditer(multi)]
        mm = list(map(int, MULTI.search(multi).groups()))
        gen = [st["output"] for st in steps[7:]]
        multi_rec = {"prompt_tokens": 8, "generated_tokens": gen,
                     "isa_generated_tokens": expect["multi"]["generated"],
                     "golden_generated_tokens": expect["multi"]["golden"],
                     "isa_logits_bit_exact_with_golden_every_step": expect["multi"]["all_logits_exact"],
                     "steps": mm[0], "mismatches": mm[2], "total_cycles": mm[3],
                     "final_vector_memory_mismatches": mm[4], "final_kv_cache_mismatches": mm[5],
                     "per_step": steps,
                     "pass": "PASS" in multi and mm[2] + mm[4] + mm[5] == 0 and gen == expect["multi"]["golden"]}
        longc = None
        if context:
            imgc = s / "imgc"
            images(imgc, "--context", str(context))
            rec, _ = single(exe, imgc, trace=False)
            longc = rec
        sweep_rec = lane_sweep(s, sweep) if sweep else None
    counts = collections.Counter(u for _, _, u in issues)
    status = "pass" if one["pass"] and multi_rec["pass"] and lint.returncode == 0 and \
        (longc is None or longc["pass"]) and all(r["pass"] for r in sweep_rec or ()) else "fail"
    return {
        "schema": "opentallas.hdc-v41-decode-campaign.v1",
        "status": status,
        "claim_boundary": "functional token-level RTL simulation (Verilator, cycle-accurate at the core boundary) "
                          "with behavioural synchronous-read memories (many-ported vector memory: four operand reads, "
                          "an element write and a reducer write per stream lane); the Sinkhorn "
                          "is the routed one-normalisation-per-step unit (ot_hdc_sinkhorn) run as a 7-core-cycle "
                          "multicycle path (its 151.9 MHz route at a 1 GHz core); clock rate is not claimed here.",
        "vehicle": "deepseek-v4.1-flash-reduced-v2 (dim 160, 40 layers, 64 heads of 32, hc 4, 12 experts top-6 "
                   "inter 64, window 128, index top-16, Engram layers 1 and 14, vocab 4040)",
        "parameters": {"su_lanes": I.SU_LANES, "me_lanes_per_group": I.W_LANES, "me_groups": I.GROUPS,
                       "interleave": I.INTERLEAVE,
                       "qe_blockdot_lanes": I.BL, "he_lanes": I.HE_LANES, "attention_rows_per_layer": I.T_MAX,
                       "program_instructions": expect["prog_words"],
                       "issued_per_unit": {n: counts.get(u, 0) for n, u in (("me", 1), ("su", 2), ("qe", 3),
                                                                            ("xu", 4), ("he", 5))},
                       "me_rom_words": expect["wrom_words"], "qe_rom_words": expect["qrom_words"],
                       "constant_rom_words": expect["crom_words"], "engram_rom_rows": expect["erom_words"]},
        "isa_model": isa_out.strip().splitlines(),
        "single_step": one,
        "per_operator_cycles": bd,
        "end_to_end": multi_rec,
        "long_context": longc,
        **({"su_lane_sweep": sweep_rec} if sweep_rec else {}),
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (SVH, *RTL, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--ngen", type=int, default=3)
    parser.add_argument("--context", type=int, default=40)
    parser.add_argument("--sweep-lanes", default="", help="also run the single step at these stream-unit widths, "
                                                          "e.g. 4,16")
    args = parser.parse_args()
    result = run(args.ngen, args.context, [int(x) for x in args.sweep_lanes.split(",") if x])
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    s = result["single_step"]
    print(result["status"], "next token", s["next_token"], "cycles", s["cycles"],
          "generated", result["end_to_end"]["generated_tokens"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

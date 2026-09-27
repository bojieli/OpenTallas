#!/usr/bin/env python3
"""Token-level RTL simulation of the RE-SPECIFIED DeepSeek-V4.1 decode core (ot_hdc_core_v41x).

The as-built campaign (tools/rtl_hdc_v41_decode_campaign.py) on ot_hdc_core_v41x: the as-built sequencer and
ISA with each unit replaced by an adapter onto its re-specified engine (rtl/hdc/v41x/ot_hdc_v41x_*_adapt.sv),
the engines' memories in their own layouts (tools/hdc_images_v41x.py).  --units picks the re-specified units
(the rest stay as built) and the ISA model runs with HDC_V41_ARITH = the R-ARITH classes those units bring.

Runs, from the repository root:

1. a Verilator lint of ot_hdc_core_v41x;
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

Arithmetic is tools/hdc_golden_v41.py; images from tools/hdc_program_v41.py and tools/hdc_images_v41x.py.
Writes results/rtl/hdc_v41x_decode_campaign.json.
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
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_decode_campaign.json"
# the re-specified units (bring-up switches of ot_hdc_core_v41x) and the R-ARITH classes each one brings
X_UNITS = ("he", "me", "att", "idx")
# idx: the index dots are FP4 x FP4 QDQ blocks, exact in binary32 in any order, so the indexer engine's
# lanes match the ISA under either contract; the "idx" class's other member, the SU head sum tagged
# "indexer", runs on the stream unit and switches with it (su)
X_CLASSES = {"he": ("he",), "me": ("me",), "att": ("att",), "idx": ()}
UNITS = X_UNITS           # set by main(): the units built re-specified
PARAMS = {"hhw": 8, "mg": 8}      # engine geometry of the build
RTL = ([ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"] +
       [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                           "ot_hdc_reduce", "ot_hdc_accept")] +
       [ROOT / f"rtl/hdc/v41/{n}.sv" for n in ("ot_hdc_engram_tables_pkg", "ot_hdc_engram_hash", "ot_hdc_select",
                                               "ot_hdc_blockdot", "ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_fdiv",
                                               "ot_hdc_fsqrt", "ot_hdc_softplus", "ot_hdc_sinkhorn_seq",
                                               "ot_hdc_sk_arith", "ot_hdc_sk_recip_rom", "ot_hdc_sinkhorn",
                                               "ot_hdc_sinkhorn_mc", "ot_hdc_v41_matvec",
                                               "ot_hdc_v41_stream", "ot_hdc_v41_qe", "ot_hdc_v41_xu",
                                               "ot_hdc_v41_hcproj")] +
       [ROOT / "rtl/hdc/ot_hdc_fastfp.sv"] +
       [ROOT / f"rtl/hdc/v41x/{n}.sv" for n in ("ot_hdc_v41x_hcp", "ot_hdc_v41x_he_adapt",
                                                 "ot_hdc_v41x_wgt_bdot", "ot_hdc_v41x_wgt_red", "ot_hdc_v41x_wgt_mac",
                                                 "ot_hdc_v41x_wgt_tile", "ot_hdc_v41x_me_adapt",
                                                 "ot_hdc_v41x_idx_arith", "ot_hdc_v41x_idx_adapt",
                                                 "ot_hdc_core_v41x")])
SVH = ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh"
TB = ROOT / "rtl/test/tb_hdc_core_v41x.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41x_harness.cpp"
TOOLS = [ROOT / f"tools/{n}.py" for n in ("hdc_golden", "hdc_golden_v41", "hdc_isa_v41", "hdc_program_v41",
                                          "hdc_timing_v41", "hdc_timing_v41x", "hdc_images_v41x")] + \
        [Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY",
              "-Wno-IMPORTSTAR")
SINGLE = re.compile(r"HDC41 token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
UTIL = re.compile(r"UTIL me_busy=(\d+) su_busy=(\d+) qe_busy=(\d+) xu_busy=(\d+) he_busy=(\d+) all_idle=(\d+)")
ISSUE = re.compile(r"ISSUE cyc=(\d+) pc=(\d+) unit=(\d+)")
STEP = re.compile(r"STEP pos=(\d+) in=(\d+) out=(\d+) gold=(\d+) cycles=(\d+) fault=(\d+)")
XCNT = re.compile(r"XCNT unit=(\w+) ops=(\d+) elems=(\d+)")
# classes whose counters the bench prints (a re-specified unit not listed here has no activation proof yet)
COUNTED = ("he", "me")
# coverage the runs do NOT prove, per unit (recorded, never counted as proven)
NOT_EXERCISED = {
    "he": ["MTP lane multiplier (mx_m > 1): the MTP program is not run on this core"],
    "me": ["wo_a in the checkpoint's FP8 image format (the image feeds it as expanded BF16)",
           "MTP lane multiplier (mx_m > 1) and the MTP layout's images"],
}


def counters(run):
    """{unit: {ops, elements}} from a bench log; the proof that each re-specified unit fired."""
    return {m.group(1): {"ops": int(m.group(2)), "elements": int(m.group(3))} for m in XCNT.finditer(run)}


def activation(cnt):
    """Every selected unit must have run ops and processed elements; one that stayed at 0 FAILS the run."""
    missing = [u for u in UNITS if u in COUNTED and (cnt.get(u, {}).get("ops", 0) == 0 or
                                                     cnt.get(u, {}).get("elements", 0) == 0)]
    uncounted = [u for u in UNITS if u not in COUNTED]
    return {"counters": cnt, "zero_counter_units": missing, "units_without_counters": uncounted,
            "pass": not missing and not uncounted}


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


def defines(lanes=None):
    return [f"+define+HDC_SW={lanes or I.SU_LANES}", f"+define+HDC_HHW={PARAMS['hhw']}",
            f"+define+HDC_MG={PARAMS['mg']}"] + \
        [f"+define+HDC_X_{u.upper()}={int(u in UNITS)}" for u in X_UNITS]


def arith():
    """HDC_V41_ARITH of the ISA model: the R-ARITH classes of the re-specified units."""
    cls = sorted({c for u in UNITS for c in X_CLASSES[u]})
    return "legacy" if not cls else ("chunk8" if set(cls) == set(V.ARITH_CLASSES) else ",".join(cls))


def build(scratch: Path, lanes=None) -> Path:
    obj = scratch / f"obj{lanes or ''}"
    r = subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                        "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "--top-module", "tb_hdc_core_v41x", "-Mdir", str(obj),
                        f"-I{SVH.parent}", *defines(lanes), *map(str, RTL), str(TB),
                        str(HARNESS), "-CFLAGS", "-O1", "-j", "8"],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"verilator failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    return obj / "Vtb_hdc_core_v41x"


def images(out: Path, *extra, lanes=None):
    env = dict(os.environ, HDC_SW=str(lanes or I.SU_LANES), HDC_V41_ARITH=arith())
    r = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program_v41.py"), "--out", str(out), *extra],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"hdc_program_v41 failed:\n{r.stdout}\n{r.stderr}")
    r2 = subprocess.run([sys.executable, str(ROOT / "tools/hdc_images_v41x.py"), "--out", str(out),
                         "--hhw", str(PARAMS["hhw"]), "--mg", str(PARAMS["mg"])], capture_output=True, text=True, env=env)
    if r2.returncode:
        raise SystemExit(f"hdc_images_v41x failed:\n{r2.stdout}\n{r2.stderr}")
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
    rec["activation"] = activation(counters(run))
    rec["pass"] = rec["pass"] and rec["activation"]["pass"]
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
        lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_core_v41x",
                               f"-GSW={I.SU_LANES}", f"-GHHW={PARAMS['hhw']}", f"-GMG={PARAMS['mg']}",
                               *[f"-GX_{u.upper()}={int(u in UNITS)}" for u in X_UNITS],
                               f"-I{SVH.parent}", *map(str, RTL)], capture_output=True, text=True)
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
                     "activation": activation(counters(multi)),
                     "pass": "PASS" in multi and mm[2] + mm[4] + mm[5] == 0 and gen == expect["multi"]["golden"]}
        multi_rec["pass"] = multi_rec["pass"] and multi_rec["activation"]["pass"]
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
        "schema": "opentallas.hdc-v41x-decode-campaign.v1",
        "respecified_units": list(UNITS),
        "as_built_units": [u for u in X_UNITS if u not in UNITS],
        "hdc_v41_arith": arith(),
        "engine_parameters": dict(PARAMS),
        "not_exercised": {u: NOT_EXERCISED.get(u, []) for u in UNITS},
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
    parser.add_argument("--units", default="he",
                        help="the re-specified units to build (the rest as built), e.g. he,qe; '' for none")
    parser.add_argument("--hhw", type=int, default=8, help="HCP lanes per group")
    parser.add_argument("--mg", type=int, default=8, help="ME weight tile chunk units (8*mg lanes)")
    args = parser.parse_args()
    global UNITS
    UNITS = tuple(u for u in args.units.split(",") if u)
    assert set(UNITS) <= set(X_UNITS), UNITS
    PARAMS["hhw"] = args.hhw
    PARAMS["mg"] = args.mg
    result = run(args.ngen, args.context, [int(x) for x in args.sweep_lanes.split(",") if x])
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    s = result["single_step"]
    print(result["status"], "next token", s["next_token"], "cycles", s["cycles"],
          "generated", result["end_to_end"]["generated_tokens"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

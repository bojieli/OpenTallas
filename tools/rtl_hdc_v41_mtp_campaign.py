#!/usr/bin/env python3
"""Multi-token prediction on the DeepSeek-V4.1 hardwired decode core: RTL campaign.

DSpark drafting (V4.1's own MTP head: three draft stages over a block of 5
positions, the Markov-biased lm_head, tools/hdc_golden_v41.py Model.draft) and
one multi-position verify pass of the main model per step (build_mtp in
tools/hdc_program_v41.py), on ot_hdc_core_v41 NSLOT = 8 with the lane
multiplier MP (one ROM / HBM weight read serves MP verify slots), under
Verilator (rtl/test/tb_hdc_core_v41_mtp.sv), for the ROM design and for the
HBM comparator (`HDC_WHBM: the quantised weights streamed from HBM by
ot_hdc_qstream, one fetch list per program).

Per configuration (target, MP, gamma, prompt, drafter) it checks, bit for bit:
* the emitted token stream against the golden's NON-speculative greedy stream
  (hdc_golden_v41.Model.generate), and the ISA model's per-position logits of
  every committed position against the golden's autoregressive logits;
* every head the RTL computes -- each prefill position's and every verify
  slot's, accepted or rejected -- against the ISA model's logits;
* every step's accepted count, and the final vector memory and KV SRAM (dead
  rows included) against the ISA model's.

Drafters: `dspark` (the released MTP weights; on the reduced vehicle the
weights are seeded random, so its acceptance is a FUNCTIONAL check only and
says nothing about the shipped model's), and `forced` (the golden
continuation with one draft corrupted per step, at a position cycling through
0 .. gamma: every accept length is exercised).  Acceptance statistics here are
never a performance claim: performance is reported as cycles per verify pass
(per gamma) and tok/s as a function of the acceptance length tau, whose value
must come from a citation or a shipped-model measurement.

Checks that fail on purpose (mutation): the RTL with the Engram-history
restore pointed at slot a+1 (HDC_MUTATE_RESTORE), and ISA models with the
compressor slot ring cut to 2 entries (a rejected slot's write aliases a live
entry) and without the dead-row poisoning invariant... every one must be
DETECTED.  The ISA model is also run with every row past the committed
positions poisoned (NaN) after each step: the tokens must not change.

    python3 tools/rtl_hdc_v41_mtp_campaign.py --part rom_m1 [--gamma 5] [--ngen 16]
    python3 tools/rtl_hdc_v41_mtp_campaign.py --merge PART.json ...

Writes results/rtl/hdc_v41_mtp_campaign.json (merge) or a part record.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_mtp_campaign.json"
RTL = ([ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"] +
       [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                           "ot_hdc_reduce", "ot_hdc_accept")] +
       [ROOT / f"rtl/hdc/v41/{n}.sv" for n in ("ot_hdc_engram_tables_pkg", "ot_hdc_engram_hash", "ot_hdc_select",
                                               "ot_hdc_blockdot", "ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_fdiv",
                                               "ot_hdc_fsqrt", "ot_hdc_softplus", "ot_hdc_sinkhorn_seq",
                                               "ot_hdc_sk_arith", "ot_hdc_sk_recip_rom", "ot_hdc_sinkhorn",
                                               "ot_hdc_sinkhorn_mc", "ot_hdc_v41_matvec",
                                               "ot_hdc_v41_stream", "ot_hdc_v41_qe", "ot_hdc_v41_xu",
                                               "ot_hdc_v41_hcproj", "ot_hdc_core_v41")])
RTL_HBM = [ROOT / "rtl/hdc/hbm/ot_hdc_qstream.sv", ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"]
SVH = ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh"
TB = ROOT / "rtl/test/tb_hdc_core_v41_mtp.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41_mtp_harness.cpp"
TOOLS = [ROOT / f"tools/{n}.py" for n in ("hdc_golden", "hdc_golden_v41", "hdc_isa_v41", "hdc_program_v41")] + \
    [Path(__file__)]
SUMMARY = re.compile(r"HDC41_MTP prompt=(\d+) generated=(\d+) iters=(\d+) token_mismatches=(\d+) "
                     r"accept_mismatches=(\d+) heads=(\d+) head_mismatches=(\d+) prefill_cycles=(\d+) "
                     r"iter_cycles=(\d+) draft_cycles=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
ITER = re.compile(r"ITER it=(\d+) pos=(\d+) in=(\d+) accepted=(\d+) emitted=(\d+) cycles=(\d+) draft_cycles=(\d+) "
                  r"fault=(\d+)")
UTIL = re.compile(r"UTIL me_busy=(\d+) su_busy=(\d+) qe_busy=(\d+) xu_busy=(\d+) he_busy=(\d+)")
PLAIN = re.compile(r"HDC41_PLAIN prompt=(\d+) generated=(\d+) token_mismatches=(\d+) heads=(\d+) "
                   r"head_mismatches=(\d+) prefill_cycles=(\d+) decode_cycles=(\d+) decode_steps=(\d+) "
                   r"vm_mismatch=(\d+) kv_mismatch=(\d+)")
QS = re.compile(r"QSTREAM q_stall_cycles=(\d+) q_words=(\d+) q_bad=(\d+) qs_fault=(\d+) fetched=(\d+) "
                r"consumed=(\d+) hbm_reads=(\d+)")
F = np.float32


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompts():
    """Three prompts: the oracle workload's (8 tokens), a 4-token slice of its
    gold continuation, and 6 tokens spread over the vocabulary."""
    p0, gold = V.prompt_and_expected()
    return {"oracle8": list(p0), "gold4": [int(t) for t in gold[:4]],
            "spread6": [0, 1377, 2754, 91, 3999, 640]}


# -- images ---------------------------------------------------------------------------------------
def forced_drafter(cont, gamma):
    """The golden continuation, draft (q mod (gamma+1)) corrupted (== gamma:
    none): accept lengths cycle through 0 .. gamma."""
    def f(q, d):
        d = [cont[q + 2 + i] if q + 2 + i < len(cont) else 0 for i in range(len(d))]
        k = q % (gamma + 1)
        if k < len(d):
            d[k] = (d[k] + 1) % 4040
        return d
    return f


def fetch_lists(lay, prog, entry):
    """The HBM image and the two programs' fetch lists, STEP's then ITER's."""
    sectors, first = P.qe_hbm_image(lay)
    step = P.encode_list(P.qe_fetch_list(lay, prog[:entry], first))
    it = P.encode_list(P.qe_fetch_list(lay, prog[entry:], first))
    return sectors, step + it, len(step)


def make_images(out, model, lay, prog, entry, prompt, ngen, gamma, drafter, hbm, golden):
    """ROM / program images, the ISA model's run and every expectation."""
    out.mkdir(parents=True, exist_ok=True)
    ref_tokens, ref_logits = golden
    cont = list(prompt) + list(ref_tokens)
    forced = forced_drafter(cont, gamma) if drafter == "forced" else None
    rec = {}
    t0 = time.time()
    toks, rows, steps = P.mtp_run(lay, prog, entry, prompt, ngen, gamma, forced=forced, record=rec)
    mach = rec["machine"]
    isa = {"tokens": toks, "equal_golden_tokens": toks == list(ref_tokens),
           "committed_logits_bit_exact_with_golden": bool(all(np.array_equal(G.bits(a), G.bits(b))
                                                               for a, b in zip(rows, ref_logits))),
           "accepted": [s["accepted"] for s in steps], "drafts": [s["drafts"] for s in steps],
           "targets": [s["targets"] for s in steps], "seconds": round(time.time() - t0, 1)}
    P.write_images(out, lay, prog)
    (out / "mtp_prompt.hex").write_text(P.hexwords(prompt, 16))
    (out / "exp_tokens.hex").write_text(P.hexwords(ref_tokens, 16))
    (out / "exp_accept.hex").write_text(P.hexwords(isa["accepted"], 16))
    heads = np.concatenate([np.asarray(h, dtype=F) for h in mach.head_log])
    assert len(mach.head_log) <= 1024
    (out / "exp_heads.hex").write_text(P.hexwords(G.bits(heads), 32))
    (out / "expect_vm.hex").write_text(P.hexwords(G.bits(mach.vm), 32))
    (out / "expect_kv.hex").write_text(P.hexwords(G.bits(mach.kv).reshape(-1), 32))
    frc = []
    for s in steps:
        d = list(s["drafts"]) + [0] * 8
        frc += d[:8]
    (out / "force.hex").write_text(P.hexwords(frc or [0], 16))
    args = [f"+NPROMPT={len(prompt)}", f"+NGEN={ngen}", f"+GAMMA={gamma}", f"+ENTRY={entry}"]
    if drafter == "forced":
        args.append("+FORCE")
    if hbm:
        sectors, lst, lbase = fetch_lists(lay, prog, entry)
        (out / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
        (out / "qlist.hex").write_text(P.hexwords(lst, P.LIST_BITS))
        args.append(f"+LBASE={lbase}")
        isa["hbm_sectors"] = len(sectors)
    (out / "run.args").write_text(" ".join(args) + "\n")
    isa["heads"] = len(mach.head_log)
    return isa


# -- RTL -------------------------------------------------------------------------------------------
def build(scratch: Path, mp: int, hbm: bool, defines=()) -> Path:
    tag = f"m{mp}{'h' if hbm else 'r'}{''.join(d[:3] for d in defines)}"
    obj = scratch / f"obj_{tag}"
    srcs = RTL + (RTL_HBM if hbm else [])
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "--top-module", "tb_hdc_core_v41_mtp", "-Mdir", str(obj),
                    f"-I{SVH.parent}", f"+define+HDC_SW={I.SU_LANES}", f"+define+HDC_MP={mp}",
                    *(["+define+HDC_WHBM"] if hbm else []), *[f"+define+{d}" for d in defines],
                    *map(str, srcs), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "4"],
                   check=True, capture_output=True)
    return obj / "Vtb_hdc_core_v41_mtp"


def simulate(exe: Path, img: Path, extra=()) -> dict:
    args = (img / "run.args").read_text().split()
    t0 = time.time()
    r = subprocess.run([str(exe), f"+DIR={img}", *args, *extra], capture_output=True, text=True)
    out = r.stdout
    m = SUMMARY.search(out)
    rec = {"returncode": r.returncode, "seconds": round(time.time() - t0, 1), "pass": "PASS" in out and m is not None}
    if not m:
        rec["tail"] = out.strip().splitlines()[-12:] + r.stderr.strip().splitlines()[-6:]
        return rec
    keys = ("prompt", "generated", "iters", "token_mismatches", "accept_mismatches", "heads", "head_mismatches",
            "prefill_cycles", "iter_cycles", "draft_cycles", "vm_mismatches", "kv_mismatches")
    rec.update(dict(zip(keys, map(int, m.groups()))))
    rec["per_iter"] = [dict(zip(("it", "pos", "input", "accepted", "emitted", "cycles", "draft_cycles", "fault"),
                                map(int, x.groups()))) for x in ITER.finditer(out)]
    u = UTIL.search(out)
    if u:
        rec["iter_unit_busy_cycles"] = dict(zip(("me", "su", "qe", "xu", "he"), map(int, u.groups())))
    q = QS.search(out)
    if q:
        rec["qstream"] = dict(zip(("q_stall_cycles", "q_words", "q_bad", "qs_fault", "fetched", "consumed",
                                   "hbm_reads"), map(int, q.groups())))
    it = rec["per_iter"]
    if it:
        rec["cycles_per_verify_pass"] = round(sum(x["cycles"] - x["draft_cycles"] for x in it) / len(it), 1)
        rec["draft_cycles_per_step"] = round(sum(x["draft_cycles"] for x in it) / len(it), 1)
        rec["cycles_per_step"] = round(sum(x["cycles"] for x in it) / len(it), 1)
        rec["cycles_per_emitted_token"] = round(sum(x["cycles"] for x in it) / sum(x["emitted"] for x in it), 1)
    return rec


# -- ISA-level mutation and invariant checks ---------------------------------------------------------
def isa_checks(model, gamma, prompt, ngen, golden):
    ref_tokens, ref_logits = golden
    cont = list(prompt) + list(ref_tokens)
    forced = forced_drafter(cont, gamma)
    out = {}
    lay = P.mtp_layout(model, gamma)
    prog, entry = P.build_mtp(lay, gamma, 1)
    toks, rows, steps = P.mtp_run(lay, prog, entry, prompt, ngen, gamma, forced=forced, poison=True)
    out["poisoned_dead_rows"] = {
        "tokens_equal_golden": toks == list(ref_tokens),
        "logits_bit_exact": bool(all(np.array_equal(G.bits(a), G.bits(b)) for a, b in zip(rows, ref_logits))),
        "accepted": [s["accepted"] for s in steps]}
    # mutation: a 2-entry compressor slot ring (rejected writes alias live entries)
    lay2 = P.Layout(model, mtp={"slots": max(model.dspark_block, gamma + 1), "ring": 2, "mutation": True})
    prog2, entry2 = P.build_mtp(lay2, gamma, 1)
    toks2, rows2, _ = P.mtp_run(lay2, prog2, entry2, prompt, ngen, gamma, forced=forced)
    diff = sum(not np.array_equal(G.bits(a), G.bits(b)) for a, b in zip(rows2, ref_logits))
    out["mutation_slot_ring_2"] = {"detected": toks2 != list(ref_tokens) or diff > 0,
                                   "logit_rows_differing": int(diff), "tokens_differ": toks2 != list(ref_tokens)}
    return out


def weight_words(prog):
    """Weight words a program section reads (ME from the weight ROM, QE LINQ,
    HE), each op once whatever its lane multiplier, and the words its ops
    would read one position at a time (x mx_m): the lane multiplier's saving.
    Routed-expert ops are counted per slot (each slot picks its own experts)."""
    rd = one = 0
    for f in prog:
        u, mm = f["unit"], max(1, f.get("mx_m", 0))
        if u == I.UNIT_ME and not f.get("me_wsrc", 0):
            n = f.get("me_tiles", 0) * f.get("me_k", 0) * I.INTERLEAVE
        elif u == I.UNIT_QE and f.get("qe_mode", 0) == I.QE_LINQ:
            n = f.get("qe_tiles", 0) * f.get("qe_nb", 0) * I.INTERLEAVE
        elif u == I.UNIT_HE:
            n = f.get("he_k", 0) * I.INTERLEAVE
        else:
            continue
        rd += n
        one += n * mm
    return {"weight_words_read": rd, "weight_words_one_position_at_a_time": one}


def golden_run(model, prompt, ngen):
    toks, rows = model.generate(prompt, ngen)
    return toks, rows


def plain_part(name, ngen, mp, hbm, prompt_names):
    """The ONE-POSITION baseline on the same bench and core build (NSLOT = 8, MP):
    the non-MTP decode program (Builder.build), prompt then greedy decode."""
    model = V.Model()
    ps = prompts()
    lay = P.Layout(model)
    prog = P.Builder(lay, qchunk=P.QCHUNK if hbm else None).build()
    rec = {"part": name, "mode": "plain", "mp": mp, "target": "hbm" if hbm else "rom", "runs": [],
           "program": {"instructions": len(prog), "weights": weight_words(prog)}}
    with tempfile.TemporaryDirectory(dir=os.environ.get("OT_SCRATCH")) as scratch:
        s = Path(scratch)
        jobs = []
        for pn in prompt_names:
            prompt = ps[pn]
            toks, rows = golden_run(model, prompt, ngen)
            img = s / f"img_{pn}"
            img.mkdir(parents=True)
            mach = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=F), np.zeros(lay.vm.size, dtype=F))
            seq = list(prompt)
            got = []
            for pos in range(len(prompt) + ngen - 1):
                a = mach.run(prog, seq[pos], pos)
                if pos >= len(prompt) - 1:
                    got.append(a)
                    seq.append(a)
            isa = {"tokens": got, "equal_golden_tokens": got == list(toks)}
            P.write_images(img, lay, prog)
            (img / "mtp_prompt.hex").write_text(P.hexwords(prompt, 16))
            (img / "exp_tokens.hex").write_text(P.hexwords(toks, 16))
            (img / "exp_accept.hex").write_text(P.hexwords([0], 16))
            heads = np.concatenate([np.asarray(h, dtype=F) for h in mach.head_log])
            (img / "exp_heads.hex").write_text(P.hexwords(G.bits(heads), 32))
            vm = np.zeros(I.VM_ELEMS_MTP, dtype=F)
            vm[:len(mach.vm)] = mach.vm
            (img / "expect_vm.hex").write_text(P.hexwords(G.bits(vm), 32))
            (img / "expect_kv.hex").write_text(P.hexwords(G.bits(mach.kv).reshape(-1), 32))
            args = [f"+NPROMPT={len(prompt)}", f"+NGEN={ngen}", "+PLAIN", "+ENTRY=0"]
            if hbm:
                sectors, first = P.qe_hbm_image(lay)
                (img / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
                (img / "qlist.hex").write_text(P.hexwords(P.encode_list(P.qe_fetch_list(lay, prog, first)),
                                                          P.LIST_BITS))
            (img / "run.args").write_text(" ".join(args) + "\n")
            jobs.append((pn, img, isa))
        exe = build(s, mp, hbm)
        with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            futs = [(pn, isa, ex.submit(subprocess.run, [str(exe), f"+DIR={img}",
                                                         *(img / "run.args").read_text().split()],
                                        capture_output=True, text=True)) for pn, img, isa in jobs]
            for pn, isa, fu in futs:
                out = fu.result().stdout
                m = PLAIN.search(out)
                r = {"pass": "PASS" in out and m is not None}
                if m:
                    r.update(dict(zip(("prompt", "generated", "token_mismatches", "heads", "head_mismatches",
                                       "prefill_cycles", "decode_cycles", "decode_steps", "vm_mismatches",
                                       "kv_mismatches"), map(int, m.groups()))))
                    r["cycles_per_token"] = round(r["decode_cycles"] / r["decode_steps"], 1)
                else:
                    r["tail"] = out.strip().splitlines()[-10:]
                q = QS.search(out)
                if q:
                    r["qstream"] = dict(zip(("q_stall_cycles", "q_words", "q_bad", "qs_fault", "fetched", "consumed",
                                             "hbm_reads"), map(int, q.groups())))
                rec["runs"].append({"prompt": pn, "isa": isa, "rtl": r, "pass": bool(r["pass"] and
                                                                                  isa["equal_golden_tokens"])})
    rec["pass"] = all(r["pass"] for r in rec["runs"])
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in (SVH, *RTL, *RTL_HBM, TB, HARNESS, *TOOLS)}
    return rec


def part(name, gamma, ngen, mp, hbm, prompt_names, drafters, mutate=False, isa_only_checks=False):
    model = V.Model()
    ps = prompts()
    rec = {"part": name, "gamma": gamma, "mp": mp, "target": "hbm" if hbm else "rom", "runs": []}
    lay = P.mtp_layout(model, gamma)
    prog, entry = P.build_mtp(lay, gamma, mp, qchunk=P.QCHUNK if hbm else None)
    rec["program"] = {"instructions": len(prog), "step_instructions": entry, "iter_instructions": len(prog) - entry,
                      "slots": lay.nslots, "slot_stride_elements": lay.slot_stride, "vm_elements_used": lay.vm.top,
                      "weight_ops_batched": sum(1 for f in prog[entry:] if f.get("mx_m", 0) > 1),
                      "step_weights": weight_words(prog[:entry]), "iter_weights": weight_words(prog[entry:])}
    with tempfile.TemporaryDirectory(dir=os.environ.get("OT_SCRATCH")) as scratch:
        s = Path(scratch)
        jobs = []
        for pn in prompt_names:
            prompt = ps[pn]
            golden = golden_run(model, prompt, ngen)
            for d in drafters:
                img = s / f"img_{pn}_{d}"
                isa = make_images(img, model, lay, prog, entry, prompt, ngen, gamma, d, hbm, golden)
                jobs.append((pn, d, img, isa, golden))
        exe = build(s, mp, hbm)
        mexe = build(s, mp, hbm, ("HDC_MUTATE_RESTORE",)) if mutate else None
        with ThreadPoolExecutor(max_workers=len(jobs) + 1) as ex:
            futs = [(pn, d, isa, ex.submit(simulate, exe, img)) for pn, d, img, isa, _ in jobs]
            mfut = None
            if mexe:
                forced_jobs = [j for j in jobs if j[1] == "forced"]
                if forced_jobs:
                    mfut = ex.submit(simulate, mexe, forced_jobs[0][2])
            for pn, d, isa, fu in futs:
                r = fu.result()
                ok = r.get("pass") and isa["equal_golden_tokens"] and isa["committed_logits_bit_exact_with_golden"]
                rec["runs"].append({"prompt": pn, "drafter": d, "isa": isa, "rtl": r, "pass": bool(ok)})
            if mfut:
                mr = mfut.result()
                rec["mutation_rtl_restore_slot_plus_1"] = {"detected": not mr.get("pass"),
                                                           **{k: v for k, v in mr.items() if k != "per_iter"}}
        if isa_only_checks:
            pn = prompt_names[0]
            rec["isa_checks"] = isa_checks(model, gamma, ps[pn], ngen, golden_run(model, ps[pn], ngen))
    rec["pass"] = all(r["pass"] for r in rec["runs"]) and \
        rec.get("mutation_rtl_restore_slot_plus_1", {"detected": True})["detected"] and \
        (not isa_only_checks or (rec["isa_checks"]["poisoned_dead_rows"]["tokens_equal_golden"] and
                                 rec["isa_checks"]["mutation_slot_ring_2"]["detected"]))
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in (SVH, *RTL, *RTL_HBM, TB, HARNESS, *TOOLS)}
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--part", help="the part name (its record goes to --output)")
    ap.add_argument("--gamma", type=int, default=5)
    ap.add_argument("--ngen", type=int, default=16)
    ap.add_argument("--mp", type=int, default=1)
    ap.add_argument("--hbm", action="store_true")
    ap.add_argument("--prompts", default="oracle8,gold4,spread6")
    ap.add_argument("--drafters", default="dspark,forced")
    ap.add_argument("--mutate", action="store_true")
    ap.add_argument("--isa-checks", action="store_true")
    ap.add_argument("--plain", action="store_true", help="the one-position baseline on the same bench")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--merge", nargs="*", type=Path, help="merge part records into results/rtl/hdc_v41_mtp_campaign.json")
    a = ap.parse_args()
    if a.merge:
        parts = [json.loads(p.read_text()) for p in a.merge]
        res = {"schema": "opentallas.hdc-v41-mtp-campaign.v1",
               "status": "pass" if all(p["pass"] for p in parts) else "fail",
               "claim_boundary": "functional token-level RTL simulation (Verilator) of DSpark multi-token prediction "
                                 "on the V4.1 decode core, ROM and HBM-weight targets; acceptance on the reduced "
                                 "vehicle (seeded random weights) is a functional check, not a performance figure; "
                                 "clock rate is not claimed here.",
               "parts": {p["part"]: p for p in parts}}
        (a.output or OUT).write_text(json.dumps(res, indent=1) + "\n")
        print(res["status"], [(p["part"], p["pass"]) for p in parts])
        return 0 if res["status"] == "pass" else 1
    if a.plain:
        rec = plain_part(a.part, a.ngen, a.mp, a.hbm, a.prompts.split(","))
    else:
        rec = part(a.part, a.gamma, a.ngen, a.mp, a.hbm, a.prompts.split(","), a.drafters.split(","), a.mutate,
                   a.isa_checks)
    out = a.output or (ROOT / f"results/rtl/hdc_v41_mtp_parts/{a.part}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(a.part, "pass" if rec["pass"] else "FAIL",
          [(r["prompt"], r.get("drafter"), r["pass"], r["rtl"].get("cycles_per_emitted_token",
                                                                   r["rtl"].get("cycles_per_token")))
           for r in rec["runs"]])
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

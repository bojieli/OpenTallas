#!/usr/bin/env python3
"""DSpark multi-token prediction on the RE-SPECIFIED V4.1 decode core (ot_hdc_core_v41x): RTL campaign.

Owner decision 2026-09-29: the V4.1 ROM design runs MTP with m = 1, TIME-MULTIPLEXED on the existing element
array -- no lane copies.  This campaign builds ot_hdc_core_v41x with NSLOT = 8 position slots and lane multiplier
MP = 1 (the default-off MTP parameters: NSLOT = 1 is the one-position core) and the re-specified units chosen by
--units (default he,me: the units whose end-to-end decode passes in results/rtl/hdc_v41x_decode_campaign.json),
and runs the DSpark program of tools/hdc_program_v41.py build_mtp under Verilator
(rtl/test/tb_hdc_core_v41x_mtp.sv):

* STEP program (entry 0): prefill / one-position decode, which also seeds every DSpark stage's window rows from
  the mean residual of target layers 37-39;
* ITER program (entry ENTRY): the DSpark draft (3 serial draft stages -- window attention over the seeded rows,
  top-3 MoE -- and the Markov-biased head, one SELECT per drafted token, TOKX latching it into the next slot),
  DYN (every slot's dynamic bank from its token and position), the verify pass of gamma + 1 positions merged
  op-major and issued one slot after another on the same engines (each verify slot's head argmax latched by
  AMAX), and ACCEPT (ot_hdc_accept: longest matching prefix a, bonus token = target a; the Engram hash history
  restored to slot a's snapshot; KV / compressor / index-key rows of rejected slots are DEAD rows by the
  program's invariant: never read before the committed position overwrites them).

Checks, bit for bit, per (prompt, drafter): every emitted token against the golden's NON-speculative greedy
stream (hdc_golden_v41.Model.generate); every head (prefill positions and every verify slot, accepted or not)
against the ISA model's logits; every step's accepted count; the final vector memory and KV SRAM (dead rows
included) against the ISA model's; and each re-specified unit's activation counters (a unit that never fired
fails the run).  The ISA model's committed logits are themselves checked bit-exact against the golden's
autoregressive logits.  Drafters: `dspark` (the reduced vehicle's seeded-random DSpark weights: acceptance is a
FUNCTIONAL check only) and `forced` (golden continuation with draft q mod (gamma + 1) corrupted: every accept
length 0 .. gamma is exercised).  --mutate also runs the forced image on a build with the Engram-history
restore pointed at slot a + 1 (HDC_MUTATE_RESTORE), which must be DETECTED.

    python3 tools/rtl_hdc_dspark_v41x_campaign.py --part NAME [--units he,me] [--gamma 5] [--ngen 12]
        [--prompts gold4] [--drafters dspark,forced] [--mutate] --output PART.json
"""
import argparse
import os
import sys

_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
_ap.add_argument("--part", required=True)
_ap.add_argument("--units", default="he,me")
_ap.add_argument("--gamma", type=int, default=5)
_ap.add_argument("--ngen", type=int, default=12)
_ap.add_argument("--prompts", default="gold4")
_ap.add_argument("--drafters", default="dspark,forced")
_ap.add_argument("--mutate", action="store_true")
_ap.add_argument("--jobs", type=int, default=8, help="Verilator C++ compile jobs")
_ap.add_argument("--fp", default="rtl", choices=("rtl", "dpi"),
                 help="dpi: the decode campaign's bit-equivalent fast-FP stand-ins (smaller C++ model)")
_ap.add_argument("--acc-guard", action="store_true",
                 help="ACCEPT on the protected DS MTP accept leaf (rtl/experimental/ds_mtp_accept_20261003) "
                      "through rtl/hdc/ot_hdc_mtp_accept_caller.sv (core ACC_GUARD = 1)")
_ap.add_argument("--workdir", help="keep images here and reuse them (img/isa.json) on a rerun")
_ap.add_argument("--output", required=True)
ARGS = _ap.parse_args() if __name__ == "__main__" else None

import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_decode_campaign as X  # noqa: E402  (unit lists, R-ARITH classes, RTL list, defines)

UNITS = tuple(u for u in (ARGS.units.split(",") if ARGS else ("he", "me")) if u)
assert set(UNITS) <= set(X.X_UNITS) and "idx" not in UNITS, UNITS   # idx: runtime HBM key writer, not covered
X.UNITS = UNITS
X.PARAMS["fp"] = ARGS.fp if ARGS else "rtl"
os.environ["HDC_V41_ARITH"] = X.arith()          # the ISA model and golden under the units' R-ARITH classes
os.environ["HDC_V41_IDX_FUSED"] = "0"

import hdc_golden_v41 as V  # noqa: E402
import hdc_images_v41x as IMG  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402
import rtl_hdc_v41_mtp_campaign as C  # noqa: E402  (images, expectations, drafters, log parsing)

V.set_arith(X.arith())                 # the decode campaign imported the golden before the env was set
assert V.ARITH == X.arith(), (V.ARITH, X.arith())
TB = ROOT / "rtl/test/tb_hdc_core_v41x_mtp.sv"
ACC_GUARD = bool(ARGS and ARGS.acc_guard)
SINK_HANDSHAKE = False # opt-in only through the cached-image executor
GUARD_SRC = [ROOT / "rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv",
             ROOT / "rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv",
             ROOT / "rtl/hdc/ot_hdc_mtp_accept_caller.sv"]
MTP_CORE = ROOT / "rtl/hdc/v41x/dspark/ot_hdc_core_v41x.sv"
BASE_CORE = ROOT / "rtl/hdc/v41x/ot_hdc_core_v41x.sv"


def sources(build=True):
    # Same-module successor, selected only by this campaign. The shared decode
    # campaign and current main core remain byte-identical.
    rtl = [MTP_CORE if p == BASE_CORE else p for p in X.rtl_sources(build)]
    assert rtl.count(MTP_CORE) == 1 and BASE_CORE not in rtl
    from dsrom_sink_handshake import select
    return select((GUARD_SRC if ACC_GUARD else []) + rtl, enable=SINK_HANDSHAKE)["sources"]


def guard_defines():
    return (["+define+HDC_ACC_GUARD=1", "+define+HDC_ACC_GUARD_ON"] if ACC_GUARD else []) + (["+define+OT_MTP_SINK_HANDSHAKE=1"] if SINK_HANDSHAKE else [])
HARNESS = ROOT / "rtl/test/hdc_core_v41x_mtp_harness.cpp"
TOOLS = [ROOT / f"tools/{n}.py" for n in ("hdc_golden", "hdc_golden_v41", "hdc_isa_v41", "hdc_program_v41",
                                          "hdc_images_v41x", "rtl_hdc_v41_mtp_campaign",
                                          "rtl_hdc_v41x_decode_campaign", "dsrom_sink_handshake")] + [Path(__file__).resolve()]
XCNT = re.compile(r"XCNT unit=(\w+) ops=(\d+) elems=(\d+)")
HIST = re.compile(r"ACCEPT_HIST a0=(\d+) a1=(\d+) a2=(\d+) a3=(\d+) a4=(\d+) a5=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(scratch: Path, defines=(), jobs=8) -> Path:
    tag = "".join(d[:3] for d in defines)
    obj = scratch / f"obj_x{tag}"
    r = subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                        "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-TIMESCALEMOD", "--top-module", "tb_hdc_core_v41x_mtp", "-Mdir", str(obj),
                        f"-I{X.SVH.parent}", *X.defines(), *guard_defines(), *[f"+define+{d}" for d in defines],
                        str(X.VLT), *map(str, sources(True)), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", str(jobs)],
                       capture_output=True, text=True)
    if r.returncode:
        errs = [ln for ln in (r.stdout + r.stderr).splitlines() if "rror" in ln][:40]
        raise SystemExit("verilator failed:\n" + "\n".join(errs) + "\n" + r.stderr[-3000:])
    return obj / "Vtb_hdc_core_v41x_mtp"


def run_one(exe: Path, img: Path) -> dict:
    args = (img / "run.args").read_text().split()
    t0 = time.time()
    r = subprocess.run([str(exe), f"+DIR={img}", *args], capture_output=True, text=True)
    (img / "rtl.log").write_text(r.stdout + r.stderr)
    out = r.stdout
    m = C.SUMMARY.search(out)
    rec = {"returncode": r.returncode, "seconds": round(time.time() - t0, 1), "pass": "PASS" in out and m is not None}
    if not m:
        rec["tail"] = out.strip().splitlines()[-16:] + r.stderr.strip().splitlines()[-6:]
        return rec
    keys = ("prompt", "generated", "iters", "token_mismatches", "accept_mismatches", "heads", "head_mismatches",
            "prefill_cycles", "iter_cycles", "draft_cycles", "vm_mismatches", "kv_mismatches")
    rec.update(dict(zip(keys, map(int, m.groups()))))
    rec["per_iter"] = [dict(zip(("it", "pos", "input", "accepted", "emitted", "cycles", "draft_cycles", "fault"),
                                map(int, x.groups()))) for x in C.ITER.finditer(out)]
    u = C.UTIL.search(out)
    if u:
        rec["iter_unit_busy_cycles"] = dict(zip(("me", "su", "qe", "xu", "he"), map(int, u.groups())))
    h = HIST.search(out)
    if h:
        rec["accept_histogram"] = list(map(int, h.groups()))
    cnt = {x.group(1): {"ops": int(x.group(2)), "elements": int(x.group(3))} for x in XCNT.finditer(out)}
    act = X.activation(cnt)
    rec["activation"] = act
    rec["pass"] = rec["pass"] and act["pass"]
    it = rec["per_iter"]
    if it:
        rec["cycles_per_step"] = round(sum(x["cycles"] for x in it) / len(it), 1)
        rec["draft_cycles_per_step"] = round(sum(x["draft_cycles"] for x in it) / len(it), 1)
        rec["verify_accept_cycles_per_step"] = round(sum(x["cycles"] - x["draft_cycles"] for x in it) / len(it), 1)
        rec["cycles_per_emitted_token"] = round(sum(x["cycles"] for x in it) / sum(x["emitted"] for x in it), 1)
        rec["prefill_cycles_per_position"] = round(rec["prefill_cycles"] / rec["prompt"], 1)
    return rec


def main() -> int:
    a = ARGS
    model = V.Model()
    ps = C.prompts()
    lay = P.mtp_layout(model, a.gamma)
    prog, entry = P.build_mtp(lay, a.gamma, 1)
    assert not any(f.get("mx_m", 0) > 1 for f in prog), "m = 1: no op may batch slots on one weight read"
    rec = {"schema": "opentallas.hdc-dspark-v41x-rtl-part.v1", "part": a.part, "core": "ot_hdc_core_v41x",
           "respecified_units": list(UNITS), "fp": X.PARAMS["fp"],
           "accept_unit": ("ot_hdc_mtp_accept_guarded (protected DS MTP accept leaf) via ot_hdc_mtp_accept_caller"
                           if ACC_GUARD else "ot_hdc_accept"), "hdc_v41_arith": V.ARITH, "gamma": a.gamma, "verify_positions":
           a.gamma + 1, "nslot": 8, "lane_multiplier_mp": 1, "ngen": a.ngen,
           "vehicle": {"checkpoint": "build/models/deepseek-v4.1-flash-reduced-v2", "layers": model.L,
                       "dim": model.dim, "window": model.window, "dspark_block": model.dspark_block,
                       "dspark_stages": model.n_mtp, "dspark_targets": model.dspark_targets,
                       "dspark_experts": [model.dspark_n_exp, model.dspark_k_exp]},
           "program": {"instructions": len(prog), "step_instructions": entry, "iter_instructions": len(prog) - entry,
                       "slots": lay.nslots, "slot_stride_elements": lay.slot_stride, "vm_elements_used": lay.vm.top,
                       "iter_weights": C.weight_words(prog[entry:])},
           "runs": []}
    scratch_root = os.environ.get("OT_SCRATCH")
    with tempfile.TemporaryDirectory(dir=scratch_root) as scratch:
        s = Path(scratch)
        wd = Path(a.workdir) if a.workdir else s
        jobs = []
        with ThreadPoolExecutor(max_workers=2) as bx:
            fexe = bx.submit(build, s, (), a.jobs)
            fmut = bx.submit(build, s, ("HDC_MUTATE_RESTORE",), a.jobs) if a.mutate else None
            for pn in a.prompts.split(","):
                prompt = ps[pn]
                golden = None
                for d in a.drafters.split(","):
                    img = wd / f"i_{pn}_{d}_g{a.gamma}_n{a.ngen}_{V.ARITH.replace(',', '')}"
                    if (img / "isa.json").exists():
                        isa = json.loads((img / "isa.json").read_text())
                    else:
                        golden = golden or C.golden_run(model, prompt, a.ngen)
                        isa = C.make_images(img, model, lay, prog, entry, prompt, a.ngen, a.gamma, d, False, golden)
                        isa["v41x_images"] = IMG.write(img, lay, X.PARAMS["hhw"], X.PARAMS["mg"])
                        (img / "isa.json").write_text(json.dumps(isa))
                    jobs.append((pn, d, img, isa))
                    print(pn, d, "isa", isa["equal_golden_tokens"], isa["committed_logits_bit_exact_with_golden"],
                          isa["accepted"], flush=True)
            exe = fexe.result()
            mexe = fmut.result() if fmut else None
        with ThreadPoolExecutor(max_workers=len(jobs) + 1) as ex:
            futs = [(pn, d, isa, ex.submit(run_one, exe, img)) for pn, d, img, isa in jobs]
            mfut = None
            if mexe:
                fj = [j for j in jobs if j[1] == "forced"]
                if fj:
                    mfut = ex.submit(run_one, mexe, fj[0][2])
            for pn, d, isa, fu in futs:
                r = fu.result()
                ok = bool(r.get("pass") and isa["equal_golden_tokens"] and isa["committed_logits_bit_exact_with_golden"]
                          and r.get("accept_mismatches", 1) == 0)
                rec["runs"].append({"prompt": pn, "drafter": d, "isa": isa, "rtl": r, "pass": ok})
                print(pn, d, "rtl", ok, {k: r.get(k) for k in ("iters", "prefill_cycles", "cycles_per_step",
                                                                 "draft_cycles_per_step", "seconds")}, flush=True)
            if mfut:
                mr = mfut.result()
                # detected = the mutant ran to its summary and the bit-exact checks caught it
                rec["mutation_rtl_restore_slot_plus_1"] = {"detected": "iters" in mr and not mr.get("pass"),
                                                           **{k: v for k, v in mr.items() if k != "per_iter"}}
    rec["pass"] = all(r["pass"] for r in rec["runs"]) and \
        rec.get("mutation_rtl_restore_slot_plus_1", {"detected": True})["detected"]
    srcs = [X.SVH, X.VLT, *sources(True), TB, HARNESS, *TOOLS]
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in srcs}
    Path(a.output).write_text(json.dumps(rec, indent=1) + "\n")
    print(a.part, "pass" if rec["pass"] else "FAIL")
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

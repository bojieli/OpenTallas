#!/usr/bin/env python3
"""Source-pinned Qwen reduced-vehicle FP32 prefill ingest -> KV image -> HBM token gate.

The RTL ingest engine produces packed E4M3 bytes.  Its actual final.mem bytes
populate the packed HBM bench and boot the active K tail through the streamer.
The diagnostic legacy-width mode decodes the same bytes to BF16 words.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
# These must precede *all* imports of hdc_golden/hdc_program.  The HBM core
# campaign uses the scalar, unsplit stream program; an import with the vector
# defaults generates a different prefill despite identical FP8 quantization.
os.environ["HDC_KV_FMT"] = "fp8"
os.environ["HDC_ATTN_SPLIT"] = "0"
os.environ["HDC_SU_WIDTH"] = "1"
import hdc_program as P  # noqa: E402
import kv_ingest_ref as R  # noqa: E402
import rtl_hdc_kv_ingest_campaign as IC  # noqa: E402
import rtl_hdc_kv_stream_campaign as KC  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_qwen_ingest_to_token.json")
    ap.add_argument("--weights", type=Path, help="checkpoint directory, also synced by remote_gate")
    ap.add_argument("--legacy-width", action="store_true", help="diagnostic: BF16-width HBM with FP8 core writes")
    ap.add_argument("--bisect", action="store_true", help="find first ISA instruction whose state differs")
    ap.add_argument("--probe-stop", type=int, help="run one cut point and retain first VM/KV mismatch lines")
    ap.add_argument("--two-token", action="store_true",
                    help="prefill through position 14, then run positions 15 and 16 across tail tile reuse")
    ap.add_argument("--physical-sector", action="store_true",
                    help="route logical FP8 KV traffic through 32-byte HBM sector bridge")
    args = ap.parse_args()
    if args.two_token and (args.bisect or args.probe_stop is not None):
        ap.error("--two-token cannot be combined with instruction probes")
    if args.physical_sector and args.legacy_width:
        ap.error("--physical-sector requires packed FP8 HBM")
    context = 16 if args.two_token else 64
    checkpoint = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if args.weights is not None and not checkpoint.exists():
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.weights / checkpoint.name, checkpoint)
    if not checkpoint.exists():
        raise FileNotFoundError(f"missing reduced Qwen3 checkpoint: {checkpoint}")
    cap = IC.qwen_capture(context)
    case = IC.case_qwen_reduced(R.FMT_FP32, cap)
    assert case["meta"]["image_equals_golden_cache"]
    nd, npay = len(case["descs"]), len(case["beats"])
    memw = IC.pow2(max(case["exp"].size // 32 + 1, 1024 + 64))
    with tempfile.TemporaryDirectory(prefix="qwen_ingest_token_") as td:
        work = Path(td)
        ing, img = work / "ing", work / "img"
        IC.write_case(ing, case, memw)
        ing_exe = IC.build(work / "ing_obj", memw, nd, npay, case["hd"], case["kvh"])
        ingest = IC.run(ing_exe, ing, nd, npay)
        packed = IC.final_image(ing, case["exp"].size)
        packed_equal = bool(np.array_equal(packed, case["exp"]))
        subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img),
                        "--context", str(context)], check=True, capture_output=True, text=True)
        word_bits = R.fp8_value(packed).view(np.uint32).reshape(-1, 16)
        decoded_hex = P.hexwords((P.pack_lanes(w, 32) for w in word_bits), 512)
        original_hex = (img / "kv.hex").read_text()
        image_equal = decoded_hex == original_hex
        # The token test's KV initialization must depend on the RTL's final.mem.
        (img / "kv.hex").write_text(decoded_hex)
        packed_words = packed.reshape(-1, 16)
        (img / "kv_fp8.hex").write_text(P.hexwords((int.from_bytes(w.tobytes(), "little")
                                                   for w in packed_words), 128))
        lay = P.Layout(P.golden_state(context)[0])
        second_token = None
        if args.two_token:
            # The first token is already the program's generated expectation.
            # Run the same ISA machine for one more position and retain its
            # complete terminal state, including the KV writes across tile 16.
            machine = P.Machine(lay, R.fp8_value(packed).copy())
            first_token = int(machine.run(P.build_program(lay), int(cap[1][-1]), context - 1))
            second_token = int(machine.run(P.build_program(lay), first_token, context))
            (img / "generated.hex").write_text(P.hexwords([first_token, second_token], 16))
            (img / "expect_logits.hex").write_text(P.hexwords(P.G.bits(machine.logits), 32))
            (img / "expect_vm.hex").write_text(P.hexwords(P.G.bits(machine.vm), 32))
            (img / "expect_kv.hex").write_text(P.hexwords(P.G.bits(machine.kv), 32))
        layout = {"LOG_HD": int(math.log2(lay.HD)), "LOG_TW": int(math.log2(lay.TW)),
                  "LLG": int(math.log2(lay.L * lay.KV)), "V0_WORD": lay.kv_v0 // 16}
        params = [*(f"-G{k}={v}" for k, v in layout.items()), f"-GNPC={KC.NPC}",
                  "-GPACKED_HBM=0" if args.legacy_width else "-GPACKED_HBM=1", "-GCORE_FP8=1",
                  f"-GPHYSICAL_HBM={int(args.physical_sector)}"]
        sector_rtl = ROOT / "rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv"
        sources = [*KC.core.HDC, *KC.KV_RTL, KC.HBM,
                   *( [sector_rtl] if args.physical_sector else [] ),
                   *KC.core.PIPES, KC.TB_CORE, KC.HARNESS_CORE]
        try:
            exe = KC.verilate("tb_hdc_core_hbm", work / "core_obj", sources, params)
        except subprocess.CalledProcessError as exc:
            print((exc.stderr or "")[-4000:], file=sys.stderr)
            raise
        run_args = (img / "run.args").read_text().split()
        if args.two_token:
            run_args = [a for a in run_args if not a.startswith("+EXPECT=")]
            run_args += [f"+EXPECT={second_token}", "+PREFILL_MULTI", "+NPROMPT=1", "+NGEN=2", "+CHECKLAST"]
        raw = KC.run(exe, f"+DIR={img}", *run_args, f"+LEAD={KC.LEAD}")
        token = KC.parse_core(raw)
        bisection = None
        if args.bisect or args.probe_stop is not None:
            def probe(stop: int) -> dict:
                cut = work / f"stop_{stop}"
                gen = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(cut),
                                      "--context", "64", "--stop", str(stop)],
                                     capture_output=True, text=True)
                if not (cut / "expect_kv.hex").exists():
                    raise RuntimeError(f"stop {stop} image generation failed (rc={gen.returncode}): "
                                       f"{gen.stdout[-500:]} {gen.stderr[-1000:]}")
                (cut / "kv.hex").write_text(decoded_hex)
                (cut / "kv_fp8.hex").write_text((img / "kv_fp8.hex").read_text())
                # A plain END directly after a matrix op can observe me_idle
                # before the registered go clears it.  A harmless stream op
                # with barrier=1 provides a real drain point for cut programs.
                program = P.build_program(lay)[:stop]
                program += [dict(unit=P.I.UNIT_SU, su_nout=1, su_nin=1, barrier=1),
                            dict(unit=P.I.UNIT_END, barrier=1)]
                (cut / "prog.hex").write_text(P.hexwords((P.I.encode(**f) for f in program),
                                                        P.I.INSTR_BITS))
                # Partial programs can end before the argmax exists.  hdc_program
                # then returns 1 and writes EXPECT=None, while VM/KV snapshots
                # remain valid and are exactly what this cut-point checks.
                run_args = [a if a != "+EXPECT=None" else "+EXPECT=0"
                            for a in (cut / "run.args").read_text().split()]
                output = KC.run(exe, f"+DIR={cut}", *run_args,
                                f"+LEAD={KC.LEAD}")
                rec = KC.parse_core(output)
                rec["first_state_mismatch_lines"] = [line for line in output.splitlines()
                                                      if line.startswith(("vm ", "kv "))][:12]
                # The bench initializes unwritten logits to all-ones, while
                # Machine starts at zero; a cut before the final projection
                # therefore cannot compare logits.  VM/KV are initialized
                # identically and locate the first numeric divergence.
                rec["exact_state"] = bool(rec.get("fault") == 0 and rec.get("stream_fault") == 0
                                          and all(rec.get(k) == 0 for k in
                                                  ("vector_memory_mismatches", "kv_cache_mismatches")))
                return rec
            if args.probe_stop is not None:
                bisection = {"probe_stop": args.probe_stop,
                             "probe": probe(args.probe_stop)}
            else:
                lo, hi = 0, len(P.build_program(lay))
                probes = {}
                while lo < hi:
                    mid = (lo + hi) // 2
                    probes[mid] = probe(mid)
                    if probes[mid]["exact_state"]:
                        lo = mid + 1
                    else:
                        hi = mid
                probes[lo] = probe(lo) if lo not in probes else probes[lo]
                bisection = {"first_failing_stop": lo, "program_length": len(P.build_program(lay)),
                             "probes": {str(k): v for k, v in sorted(probes.items())}}
        token_exact = (token.get("pass") and token.get("fault") == 0 and token.get("stream_fault") == 0
                       and token.get("next_token") == token.get("isa_next_token")
                       and all(token.get(k) == 0 for k in ("logit_mismatches", "vector_memory_mismatches",
                                                              "kv_cache_mismatches", "delivered_word_mismatches")))
        rec = {"pass": bool(ingest.get("pass") and packed_equal and image_equal and token_exact),
               "ingest": ingest, "packed_image_equals_reference": packed_equal,
               "decoded_image_equals_golden_kv_hex": image_equal, "token": token,
               "packed_image_sha256": hashlib.sha256(packed.tobytes()).hexdigest(),
               "descriptor_count": nd, "payload_beats": npay,
               "checkpoint_sha256": sha(checkpoint),
               "scope": ("Reduced Qwen3 vehicle, FP32 prefill through position 14 followed by two packed-FP8 tokens at positions 15 and 16 across the K tail tile boundary. Ingest RTL populates HBM, streamer boots the active tail, then writes and flushes KV. Full terminal logits, VM, KV and both token IDs are checked."
                         if args.two_token else
                         "Reduced Qwen3 vehicle context 64, one token after FP32 prefill. Ingest RTL packed FP8 output populates HBM model; streamer expands FP8 on read and packs FP8 on write; hardware tail boot transfers active K words. Legacy-width diagnostic uses BF16 HBM words and direct tail preload."),
               "legacy_width": args.legacy_width,
               "physical_sector": args.physical_sector,
               "physical_sector_boundary": ("Serialized, order-preserving 16-byte logical to 32-byte physical "
                                            "HBM read and partial-write RMW. Functional correctness gate; no "
                                            "HBM bandwidth or shipped scheduler claim." if args.physical_sector else None),
               "two_token": args.two_token,
               "first_token": first_token if args.two_token else None,
               "second_token": second_token,
               "instruction_bisection": bisection,
               "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                                [*IC.RTL, IC.TB, IC.HARNESS, *sources[:-1], sources[-1],
                                 ROOT / "tools/hdc_program.py", ROOT / "tools/kv_ingest_ref.py",
                                 ROOT / "tools/rtl_hdc_kv_ingest_campaign.py", Path(__file__)]}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rec, indent=2) + "\n")
        print(json.dumps({"pass": rec["pass"], "ingest": ingest.get("pass"),
                          "packed": packed_equal, "golden": image_equal, "token": token}, indent=2))
        if not rec["pass"]:
            print(raw[-2500:])
            raise SystemExit(1)


if __name__ == "__main__":
    main()

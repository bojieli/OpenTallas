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
    args = ap.parse_args()
    checkpoint = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if args.weights is not None and not checkpoint.exists():
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.weights / checkpoint.name, checkpoint)
    if not checkpoint.exists():
        raise FileNotFoundError(f"missing reduced Qwen3 checkpoint: {checkpoint}")
    cap = IC.qwen_capture()
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
                        "--context", "64"], check=True, capture_output=True, text=True)
        word_bits = R.fp8_value(packed).view(np.uint32).reshape(-1, 16)
        decoded_hex = P.hexwords((P.pack_lanes(w, 32) for w in word_bits), 512)
        original_hex = (img / "kv.hex").read_text()
        image_equal = decoded_hex == original_hex
        # The token test's KV initialization must depend on the RTL's final.mem.
        (img / "kv.hex").write_text(decoded_hex)
        packed_words = packed.reshape(-1, 16)
        (img / "kv_fp8.hex").write_text(P.hexwords((int.from_bytes(w.tobytes(), "little")
                                                   for w in packed_words), 128))
        lay = P.Layout(P.golden_state(64)[0])
        layout = {"LOG_HD": int(math.log2(lay.HD)), "LOG_TW": int(math.log2(lay.TW)),
                  "LLG": int(math.log2(lay.L * lay.KV)), "V0_WORD": lay.kv_v0 // 16}
        params = [*(f"-G{k}={v}" for k, v in layout.items()), f"-GNPC={KC.NPC}",
                  "-GPACKED_HBM=0" if args.legacy_width else "-GPACKED_HBM=1", "-GCORE_FP8=1"]
        sources = [*KC.core.HDC, *KC.KV_RTL, KC.HBM, *KC.core.PIPES, KC.TB_CORE, KC.HARNESS_CORE]
        try:
            exe = KC.verilate("tb_hdc_core_hbm", work / "core_obj", sources, params)
        except subprocess.CalledProcessError as exc:
            print((exc.stderr or "")[-4000:], file=sys.stderr)
            raise
        raw = KC.run(exe, f"+DIR={img}", *(img / "run.args").read_text().split(), f"+LEAD={KC.LEAD}")
        token = KC.parse_core(raw)
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
               "scope": "Reduced Qwen3 vehicle context 64, one token after FP32 prefill. Ingest RTL packed FP8 output populates HBM model; streamer expands FP8 on read and packs FP8 on write; hardware tail boot transfers active K words. Legacy-width diagnostic uses BF16 HBM words and direct tail preload.",
               "legacy_width": args.legacy_width,
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

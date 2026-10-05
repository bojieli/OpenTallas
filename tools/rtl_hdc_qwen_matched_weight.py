#!/usr/bin/env python3
"""Same scalar Qwen controller and program, changing only ROM/HBM weight supply.

The KV cache remains on the same timed HBM model in both runs. This is a
reduced-model, behavioral-memory cycle comparison, not a chip energy or
shipped-model performance estimate. The ROM path is synchronous (one cycle).
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
ENV = dict(os.environ, HDC_GROUPS="4", HDC_SU_WIDTH="1", HDC_RMAX="0",
           HDC_KV_FMT="bf16", HDC_ATTN_SPLIT="1")
os.environ.update(ENV)
import hdc_timing as timing  # noqa: E402
import rtl_hdc_decode_campaign as core  # noqa: E402
import rtl_hdc_hbm_campaign as hbm  # noqa: E402
os.environ.update(ENV)

TB = ROOT / "rtl/test/tb_hdc_qwen_matched_weight.sv"
HARNESS = ROOT / "rtl/test/hdc_qwen_matched_weight_harness.cpp"
SOURCES = [*core.HDC, ROOT / "rtl/hdc/ot_hdc_core_whbm.sv", *hbm.KV_RTL,
           hbm.HBM, hbm.WS_RTL, hbm.ARB, *core.PIPES, TB, HARNESS]
INPUTS = [*SOURCES, core.ISA_SVH, ROOT / "tools/hdc_program.py",
          ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_isa.py", Path(__file__)]
SINGLE = re.compile(r"HDC token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
STREAM = re.compile(r"MATCHED_WEIGHT ([^\n]+)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", type=Path, help="reuse a generated --wchunk 1536 image")
    ap.add_argument("--rom-executable", type=Path)
    ap.add_argument("--hbm-executable", type=Path)
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_qwen_matched_weight_single.json")
    args = ap.parse_args()
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    record = {
        "schema": "opentallas.qwen-matched-weight-single.v1",
        "configuration": {"controller": "ot_hdc_core_whbm", "groups": 4, "su_width": 1,
                          "kv_format": "bf16", "attention_split": 1, "position": 15,
                          "hbm_pseudo_channels": 4, "weight_chunk_words": 1536,
                          "weight_guaranteed_rate_x256": timing.w_rate(dict(timing.WH, npc=4)),
                          "clock_ps": hbm.CLK_PS},
        "boundary": "Reduced Qwen one-token behavioral RTL. Same scalar controller, chunked program, "
                    "arithmetic, KV HBM streamer/model, pseudo-channel timing, and initial state. "
                    "Only weight supply differs: synchronous ROM or the existing HBM weight streamer. "
                    "HBM event counters include shared KV traffic in both modes. Cycles are simulated; "
                    "no dynamic/static chip energy or shipped-model ratio is inferred.",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in INPUTS},
        "model_sha256": sha(model),
    }
    with tempfile.TemporaryDirectory(prefix="qwen_matched_weight_") as temp:
        scratch = Path(temp)
        img = args.image or (scratch / "image")
        if not args.image:
            gen = run([sys.executable, str(ROOT / "tools/hdc_program.py"),
                       "--out", str(img), "--wchunk", "1536"])
            if gen.returncode:
                raise RuntimeError(f"image generation failed: {gen.stderr[-4000:]}")
        record["image_sha256"] = {name: sha(img / name) for name in
                                  ("prog.hex", "wrom.hex", "crom.hex", "kv.hex", "hbm_w.hex",
                                   "run.args", "hbm.args", "expect_vm.hex", "expect_kv.hex", "expect_logits.hex")}
        run_args = (img / "run.args").read_text().split()
        hbm_args = (img / "hbm.args").read_text().split()
        for mode, whbm, reuse in (("rom", 0, args.rom_executable), ("hbm", 1, args.hbm_executable)):
            exe = reuse
            if exe is None:
                obj = scratch / f"obj_{mode}"
                cmd = ["verilator", "--cc", "--exe", "--build", "-O0", "-Wno-fatal",
                       "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-PINMISSING", "-Wno-TIMESCALEMOD",
                       "--top-module", "tb_hdc_qwen_matched_weight", "-Mdir", str(obj), "-j", "8",
                       f"-I{core.ISA_SVH.parent}", "-GWHBM=" + str(whbm),
                       *map(str, SOURCES), "-CFLAGS", "-O0"]
                build = run(cmd)
                if build.returncode:
                    raise RuntimeError(f"{mode} build failed: {(build.stdout + build.stderr)[-8000:]}")
                exe = obj / "Vtb_hdc_qwen_matched_weight"
            command = [str(exe), f"+DIR={img}", *run_args, *hbm_args,
                       f"+WRATE={record['configuration']['weight_guaranteed_rate_x256']}"]
            sim = run(command, timeout=1800)
            m, st = SINGLE.search(sim.stdout), STREAM.search(sim.stdout)
            rec = {"whbm": whbm, "binary_sha256": sha(exe), "returncode": sim.returncode,
                   "command_arguments": command[1:], "stdout_tail": sim.stdout[-4000:],
                   "stderr_tail": sim.stderr[-1000:]}
            if m:
                rec.update(zip(("token", "position", "next_token", "expected_token", "cycles", "core_fault",
                                "logit_mismatches", "vm_mismatches", "kv_mismatches"), map(int, m.groups())))
            if st:
                rec["stream"] = hbm.kv_pairs(st.group(1))
            s = rec.get("stream", {})
            rec["pass"] = bool(sim.returncode == 0 and "PASS" in sim.stdout and m and st and
                               rec["next_token"] == rec["expected_token"] and
                               all(rec[k] == 0 for k in ("core_fault", "logit_mismatches", "vm_mismatches",
                                                       "kv_mismatches")) and
                               all(s.get(k) == 0 for k in ("wq_bad", "ws_fault", "kvs_fault", "kvq_bad")) and
                               s.get("whbm") == whbm)
            record[mode] = rec
            print(mode, "pass" if rec["pass"] else "fail", rec.get("cycles"), flush=True)
            if not rec["pass"]:
                break
    if record.get("rom", {}).get("pass") and record.get("hbm", {}).get("pass"):
        a, b = record["rom"], record["hbm"]
        record["checks"] = {
            "same_token_position_and_oracle": all(a[k] == b[k] for k in
                ("token", "position", "next_token", "expected_token")),
            "rom_no_weight_hbm_reads": a["stream"]["fetched"] == 0 and a["stream"]["consumed"] == 0,
            "rom_and_hbm_have_kv_activity": a["stream"]["kv_ops"] > 0 and b["stream"]["kv_ops"] > 0,
            "rom_and_hbm_have_kv_hbm_reads": a["stream"]["hbm_reads"] > 0 and b["stream"]["hbm_reads"] > 0,
            "hbm_delivered_weight_words": b["stream"]["w_words"] > 0,
        }
        record["hbm_over_rom_cycles"] = round(b["cycles"] / a["cycles"], 6)
    record["status"] = "pass" if (record.get("rom", {}).get("pass") and
                                   record.get("hbm", {}).get("pass") and
                                   all(record.get("checks", {}).values())) else "fail"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(args.output, record["status"], flush=True)
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Reduced Qwen scalar W_HBM token with the adopted split-aware KV path.

The scalar weight-HBM controller has its own top, ot_hdc_core_whbm. This gate
checks a complete position-15 token, including streamed HBM weights and KV,
against the current Python ISA oracle. It does not exercise the vector KV
bridge or a consecutive-token physical HBM read-after-write.
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
# Set image semantics before imports. The historical KV campaign imported below
# resets both variables for its own unsplit scalar regression; restore our
# adopted configuration immediately afterward for this runner's children.
os.environ.update(HDC_GROUPS="4", HDC_SU_WIDTH="1", HDC_RMAX="0",
                  HDC_KV_FMT="bf16", HDC_ATTN_SPLIT="1")
import hdc_timing as T  # noqa: E402
import rtl_hdc_decode_campaign as C  # noqa: E402
import rtl_hdc_hbm_campaign as H  # noqa: E402
os.environ.update(HDC_SU_WIDTH="1", HDC_ATTN_SPLIT="1")

TB = ROOT / "rtl/test/tb_hdc_core_whbm.sv"
CORE = ROOT / "rtl/hdc/ot_hdc_core_whbm.sv"
SOURCES = [*C.HDC, CORE, *H.KV_RTL, H.HBM, H.WS_RTL, H.ARB, *C.PIPES, TB, H.HARNESS_CORE]
INPUTS = [*SOURCES, C.ISA_SVH, ROOT / "tools/hdc_program.py", ROOT / "tools/hdc_golden.py",
          ROOT / "tools/hdc_isa.py", ROOT / "tools/hdc_timing.py", Path(__file__)]
SINGLE = re.compile(r"HDC token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
STREAM = re.compile(r"WSTREAM ([^\n]+)")
MULTI = re.compile(r"HDC_MULTI steps=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+)")
STEP = re.compile(r"STEP pos=(\d+) in=(\d+) out=(\d+) gold=(\d+) cycles=(\d+) fault=(\d+)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("single", "multi"), default="single")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--executable", type=Path, help="reuse a Verilator binary built from these exact sources")
    args = ap.parse_args()
    if args.output is None:
        args.output = ROOT / f"results/rtl/hdc_qwen_whbm_split_{'e2e' if args.mode == 'multi' else 'single'}.json"
    env = dict(os.environ, HDC_GROUPS="4", HDC_SU_WIDTH="1", HDC_RMAX="0",
               HDC_KV_FMT="bf16", HDC_ATTN_SPLIT="1")
    record = {
        "schema": f"opentallas.hdc-qwen-whbm-split-{args.mode}.v1",
        "configuration": {"groups": 4, "su_width": 1, "kv_format": "bf16", "attention_split": 1,
                          "position": 15,
                          "hbm_pseudo_channels": 4, "weight_chunk_words": 1536,
                          "weight_guaranteed_rate_x256": T.w_rate(dict(T.WH, npc=4))},
        "claim_boundary": "Reduced Qwen functional and cycle-accurate RTL with weights and KV in the "
                          "timing-faithful behavioral HBM model; scalar stream and split-aware KV tail. "
                          "The multi mode covers empty-cache prompt and three generated tokens. No vector KV "
                          "bridge, physical K-flush ordering, or shipped-scale throughput claim.",
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in INPUTS},
        "model_sha256": sha(ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"),
    }
    with tempfile.TemporaryDirectory(prefix="hdc_qwen_whbm_split_") as tmp:
        tmp = Path(tmp)
        img = tmp / "img"
        gen = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img),
                              "--wchunk", "1536"], cwd=ROOT, env=env, capture_output=True, text=True)
        if gen.returncode:
            record.update(status="fail", phase="image", stderr=gen.stderr[-4000:])
        else:
            record["image_sha256"] = {name: sha(img / name) for name in
                                      ("prog.hex", "wrom.hex", "crom.hex", "kv.hex", "hbm_w.hex", "run.args", "hbm.args")}
            record["generation_stdout"] = gen.stdout.strip()
            exe = args.executable
            if exe is None:
                obj = tmp / "obj"
                cmd = ["verilator", "--cc", "--exe", "--build", "-O0", "-Wno-fatal", "-Wno-WIDTH",
                       "-Wno-UNUSED", "-Wno-PINMISSING", "-Wno-TIMESCALEMOD",
                       "--top-module", "tb_hdc_core_whbm", "-Mdir", str(obj), "-j", "4",
                       f"-I{C.ISA_SVH.parent}", *map(str, SOURCES), "-CFLAGS", "-O0"]
                build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
                if build.returncode:
                    record.update(status="fail", phase="build", stderr=(build.stdout + build.stderr)[-8000:])
                else:
                    exe = obj / "Vtb_hdc_core_whbm"
            if exe is not None and "status" not in record:
                record["binary_sha256"] = sha(exe)
                run_args = (["+MULTI", "+NPROMPT=16", "+NGEN=3"] if args.mode == "multi"
                            else (img / "run.args").read_text().split())
                run = subprocess.run([str(exe), f"+DIR={img}", *run_args,
                                      *(img / "hbm.args").read_text().split(),
                                      f"+WRATE={record['configuration']['weight_guaranteed_rate_x256']}"],
                                     cwd=ROOT, capture_output=True, text=True, timeout=1800)
                m = (MULTI if args.mode == "multi" else SINGLE).search(run.stdout)
                s = STREAM.search(run.stdout)
                if m:
                    names = (("steps", "generated", "mismatches", "total_cycles") if args.mode == "multi" else
                             ("token", "position", "next_token", "expected_token", "cycles", "core_fault",
                              "logit_mismatches", "vm_mismatches", "kv_mismatches"))
                    record.update(zip(names, map(int, m.groups())))
                if args.mode == "multi":
                    record["generation_steps"] = [dict(zip(("position", "input_token", "output_token", "gold_token",
                                                               "cycles", "fault"), map(int, mm.groups())))
                                                  for mm in STEP.finditer(run.stdout)]
                if s:
                    record["stream"] = H.kv_pairs(s.group(1))
                st = record.get("stream", {})
                exact = (record.get("steps") == 18 and record.get("generated") == 3 and
                         record.get("mismatches") == 0 and len(record["generation_steps"]) == 3 and
                         all(step["output_token"] == step["gold_token"] and step["fault"] == 0
                             for step in record["generation_steps"])) if args.mode == "multi" else (
                         m and record["next_token"] == record["expected_token"] and
                         all(record[k] == 0 for k in ("core_fault", "logit_mismatches", "vm_mismatches",
                                                      "kv_mismatches")))
                record.update(status="pass" if run.returncode == 0 and "PASS" in run.stdout and m and s and exact and
                              all(st.get(k) == 0 for k in ("wq_bad", "ws_fault", "kvs_fault", "kvq_bad"))
                              else "fail", phase="simulation", returncode=run.returncode,
                              stdout=run.stdout[-5000:], stderr=run.stderr[-2000:])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(args.output, record["status"], record.get("phase"))
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

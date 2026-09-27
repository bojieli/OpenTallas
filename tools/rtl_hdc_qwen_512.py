#!/usr/bin/env python3
"""Exact context-512 Qwen vector token through timed physical KV HBM."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

os.environ.update(HDC_GROUPS="4", HDC_SU_WIDTH="16", HDC_KV_FMT="fp8", HDC_ATTN_SPLIT="1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa as I  # noqa: E402
I.T_MAX = 512
I.VM_ELEMS = 8192
import hdc_program as P  # noqa: E402
P.TMAX = 512
P.S_STRIDE = 512
for _region in ("ATT", "T1", "GU", "ATTN", "U", "ACT"):
    P.VM[_region] += 8 * (512 - 64)
import rtl_hdc_spec_token_campaign as BASE  # noqa: E402
import rtl_hdc_qwen_vector_system_two_token as TWO  # noqa: E402

TB = ROOT / "rtl/test/tb_hdc_core_qwen_512.sv"
HBM = ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"
SOURCES = [*BASE.HDC, *BASE.PIPES, *BASE.BRIDGE_RTL, *TWO.KV, HBM, TB, BASE.HARNESS]
INPUTS = [*SOURCES, BASE.ISA_SVH, ROOT / "tools/hdc_isa.py", ROOT / "tools/hdc_program.py",
          ROOT / "tools/hdc_golden.py", Path(__file__)]
HDC = re.compile(r"HDC token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                 r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
LONG = re.compile(r"LONG_CONTEXT position=(\d+) token=(\d+) next=(\d+) expect=(\d+) cycles=(\d+) "
                  r"kv_reads=(\d+) kv_writes=(\d+) committed_writes=(\d+) boot_reads=(\d+) "
                  r"physical_byte_mismatches=(\d+) backpressure_cycles=(\d+) acts=(\d+) "
                  r"refreshes=(\d+) fault=(\d+)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_image(img):
    model, prompt, _, cache = P.golden_state(512)
    lay = P.Layout(model)
    assert lay.kv_elems == 131072 and len(lay.crom) <= 8192
    token, pos = int(prompt[-1]), 511
    initial_kv = lay.kv_image(cache)
    prog = P.build_program(lay)
    machine = P.Machine(lay, initial_kv)
    got = int(machine.run(prog, token, pos))
    # Independent arithmetic oracle, using the same pre-token cache but not
    # the ISA program or its VM, to catch an invalid long-context image.
    ref_cache = [list(c) for c in cache]
    ref = model.decode_token(token, pos, ref_cache)
    assert P.np.array_equal(P.G.bits(machine.logits), P.G.bits(ref)), "ISA/golden logits differ"
    assert P.np.array_equal(P.G.bits(machine.kv), P.G.bits(lay.kv_image(ref_cache))), "ISA/golden KV differ"
    img.mkdir(parents=True, exist_ok=True)
    (img / "wrom.hex").write_text(P.hexwords((P.pack_lanes(w, 16) for w in lay.words), 16 * P.W * P.GR))
    (img / "crom.hex").write_text(P.hexwords(((P.f32(hi) << 32) | P.f32(lo) for lo, hi in lay.crom), 64))
    (img / "kv.hex").write_text(P.hexwords((P.pack_lanes(w, 32) for w in P.G.bits(initial_kv).reshape(-1, P.W)), 32 * P.W))
    (img / "prog.hex").write_text(P.hexwords((I.encode(**f) for f in prog), I.INSTR_BITS))
    (img / "expect_logits.hex").write_text(P.hexwords(P.G.bits(machine.logits), 32))
    (img / "expect_vm.hex").write_text(P.hexwords(P.G.bits(machine.vm), 32))
    (img / "expect_kv.hex").write_text(P.hexwords(P.G.bits(machine.kv), 32))
    (img / "run.args").write_text(f"+TOKEN={token} +POS={pos} +EXPECT={got}\n")
    return {"position": pos, "input_token": token, "expected_token": got,
            "kv_words": initial_kv.size // P.W, "vm_elements": I.VM_ELEMS,
            "crom_words": len(lay.crom), "program_words": len(prog),
            "golden_logit_words": len(machine.logits), "prefill_positions": len(cache[0])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--qd", type=int, default=16)
    ap.add_argument("--pc-room", type=int, default=4)
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_qwen_context_512.json")
    args = ap.parse_args()
    work = args.workdir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    img, obj = work / "img", work / f"obj_qd{args.qd}_room{args.pc_room}"
    pins = {str(p.relative_to(ROOT)): sha(p) for p in INPUTS}
    rec = {"schema": "opentallas.qwen-vector-context-512.v1",
           "configuration": {"context_positions": 512, "position": 511, "groups": 4, "su_width": 16,
                             "reducer_levels": 5, "reducer_max_elements": 512, "kv_format": "fp8-e4m3",
                             "physical_hbm_sector_bytes": 32, "pseudo_channels": 4,
                             "hbm_queue_depth": args.qd, "hbm_pc_room": args.pc_room,
                             "hbm_pc_ready": 1, "clock_ps": 1000,
                             "weights": "synchronous ROM"},
           "claim_boundary": "Reduced Qwen vector one-token RTL with the existing parameterized "
                             "reducer extended to five temporal levels (512 score elements), seeded by "
                             "511 golden prefill positions. Physical FP8 K/V sectors use a four-PC timed "
                             "behavioral HBM model. Token, logits, VM, KV, and committed physical bytes "
                             "are compared exactly. This is not an 8K-context or a production bandwidth, "
                             "throughput, energy, or physical timing claim.",
           "source_sha256": pins,
           "model_sha256": sha(ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"),
           "workdir": str(work)}
    try:
        rec["oracle"] = generate_image(img)
        rec["image_sha256"] = {p.name: sha(p) for p in img.iterdir() if p.is_file()}
        exe = obj / "Vtb_hdc_core"
        manifest = work / f"source_qd{args.qd}_room{args.pc_room}.json"
        compiled = {str(p.relative_to(ROOT)): sha(p) for p in [*SOURCES, BASE.ISA_SVH]}
        previous = json.loads(manifest.read_text()) if manifest.exists() else {}
        reused = bool(args.reuse and exe.exists() and previous == compiled)
        if not reused:
            cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal",
                   "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-VARHIDDEN",
                   "-Wno-PINMISSING", "-Wno-TIMESCALEMOD", "--unroll-count", "65536",
                   "--top-module", "tb_hdc_core", "-GG=4", "-GSW=16", "-GKV_BRIDGE=0",
                   f"-GHBM_QD={args.qd}", f"-GHBM_PC_ROOM={args.pc_room}", "-Mdir", str(obj),
                   f"-I{BASE.ISA_SVH.parent}", *map(str, SOURCES), "-CFLAGS", "-O1"]
            build = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, MAKEFLAGS="-j8"),
                                   capture_output=True, text=True, timeout=3600)
            if build.returncode:
                raise RuntimeError("build: " + (build.stdout + build.stderr)[-10000:])
            manifest.write_text(json.dumps(compiled, sort_keys=True) + "\n")
        rec["binary_sha256"] = sha(exe)
        rec["binary_reused"] = reused
        run = subprocess.run([str(exe), f"+DIR={img}", *(img / "run.args").read_text().split()],
                             cwd=ROOT, capture_output=True, text=True, timeout=3600)
        rec["returncode"] = run.returncode
        rec["stdout"] = run.stdout
        rec["stderr"] = run.stderr[-4000:]
        h, q = HDC.search(run.stdout), LONG.search(run.stdout)
        if h:
            rec["token"] = dict(zip(("input", "position", "actual", "expected", "cycles",
                                     "fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"),
                                    map(int, h.groups())))
        if q:
            rec["physical_hbm"] = dict(zip(("position", "input", "actual", "expected", "cycles",
                                             "kv_reads", "kv_writes", "committed_writes", "boot_reads",
                                             "physical_byte_mismatches", "backpressure_cycles", "acts",
                                             "refreshes", "fault"), map(int, q.groups())))
        t, p = rec.get("token", {}), rec.get("physical_hbm", {})
        rec["status"] = "pass" if (run.returncode == 0 and "PASS" in run.stdout and
                                     t.get("position") == 511 and t.get("actual") == t.get("expected") == rec["oracle"]["expected_token"] and
                                     all(t.get(k) == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches")) and
                                     p.get("boot_reads") == 128 and p.get("kv_reads", 0) > 128 and
                                     p.get("kv_writes", 0) > 0 and p.get("committed_writes") == p.get("kv_writes") and
                                     p.get("physical_byte_mismatches") == p.get("fault") == 0 and
                                     p.get("acts", 0) > 0) else "fail"
        rec["phase"] = "simulation"
    except Exception as exc:
        rec.update(status="fail", phase="exception", error=str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(args.output, rec["status"], rec["phase"], flush=True)
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

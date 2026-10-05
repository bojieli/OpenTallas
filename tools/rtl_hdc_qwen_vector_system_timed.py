#!/usr/bin/env python3
"""Source-pinned Qwen vector KV gate on the timed four-pseudo-channel HBM model."""
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
import rtl_hdc_spec_token_campaign as BASE  # noqa: E402
import rtl_hdc_qwen_vector_system_two_token as TWO  # noqa: E402

TB = ROOT / "rtl/test/tb_hdc_core_qwen_system_timed.sv"
HBM = ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"
SOURCES = [*BASE.HDC, *BASE.PIPES, *BASE.BRIDGE_RTL, *TWO.KV, HBM, TB, BASE.HARNESS]
INPUTS = [*SOURCES, BASE.ISA_SVH, ROOT / "tools/hdc_program.py",
          ROOT / "tools/hdc_golden.py", Path(__file__)]
STEP = re.compile(r"KV_MULTI_STEP pos=(\d+) in=(\d+) out=(\d+) expect=(\d+) cycles=(\d+) "
                  r"fault=(\d+) lg_bad=(\d+) vm_bad=(\d+) kv_bad=(\d+) hbm_reads=(\d+) hbm_writes=(\d+)")
SUMMARY = re.compile(r"KV_MULTI steps=(\d+) generated=(\d+) total_cycles=(\d+) "
                     r"token_mismatches=(\d+) logit_mismatches=(\d+) vm_mismatches=(\d+) "
                     r"kv_mismatches=(\d+) physical_byte_mismatches=(\d+)")
PHYS = re.compile(r"KV_MULTI_PHYS boot_done=(\d+) boot_reads=(\d+) hbm_reads=(\d+) "
                  r"hbm_writes=(\d+) v_reads_after_write=(\d+) k_flush_writes=(\d+) "
                  r"physical_byte_mismatches=(\d+) fault=(\d+) drained=(\d+) committed_writes=(\d+)")
TIMING = re.compile(r"KV_MULTI_HBM_TIMING completed_reads=(\d+) acts=(\d+) row_hits=(\d+) "
                    r"refreshes=(\d+) backpressure_cycles=(\d+) rd_lat_avg_ps=(\d+) rd_lat_max_ps=(\d+)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--steps", type=int, default=18, choices=range(2, 19))
    ap.add_argument("--workdir", type=Path, help="persistent scratch directory for this exact source")
    ap.add_argument("--reuse", action="store_true", help="reuse executable after source-hash validation")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/hdc_qwen_vector_system_timed_g4sw16.json")
    args = ap.parse_args()
    env = dict(os.environ, HDC_GROUPS="4", HDC_SU_WIDTH="16", HDC_KV_FMT="fp8")
    pins = {str(p.relative_to(ROOT)): sha(p) for p in INPUTS}
    rec = {"schema": "opentallas.qwen-vector-system-timed.v1",
           "configuration": {"groups": 4, "su_width": 16, "prompt_tokens": 16,
                             "generated_tokens": 3, "steps_executed": args.steps,
                             "physical_hbm_bytes": 32, "kv_hbm_pseudo_channels": 4,
                             "clock_ps": 1000, "weight_supply": "synchronous on-core ROM",
                             "kv_hbm_model": "ot_hdc_hbm_model PC_RDY=1; timing and refresh enabled"},
           "claim_boundary": "Reduced Qwen functional and simulated-cycle RTL with autonomous physical K boot, "
                             "banked K tail, exact per-step ISA state, and the existing four-pseudo-channel "
                             "timing HBM controller for KV reads and writes only. Weights remain in synchronous "
                             "on-core ROM. HBM timing constants and controller latency are model assumptions; "
                             "the gate does not establish physical bandwidth, shipped-model rate, or chip energy.",
           "input_sha256": pins}
    work = args.workdir or Path(tempfile.mkdtemp(prefix="qwen_vec_system_timed_"))
    work.mkdir(parents=True, exist_ok=True)
    img, obj = work / "img", work / "obj"
    try:
        gen = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"),
                              "--out", str(img), "--context", "16"], cwd=ROOT, env=env,
                             capture_output=True, text=True)
        if gen.returncode:
            raise RuntimeError("image: " + gen.stderr[-4000:])
        oracle_code = '''
import sys
from pathlib import Path
sys.path.insert(0,"tools")
import hdc_program as P
model,prompt,_,_=P.golden_state(16)
lay=P.Layout(model)
mach=P.Machine(lay,P.np.zeros(lay.kv_elems,dtype=P.F))
prog=P.build_program(lay)
out=Path(sys.argv[1])
tokens=[]; logits=[]; vm=[]; kv=[]
for step in range(18):
    token=int(prompt[step]) if step<len(prompt) else int(tokens[-1])
    tokens.append(int(mach.run(prog,token,step)))
    logits.extend(int(x) for x in P.G.bits(mach.logits))
    vm.extend(int(x) for x in P.G.bits(mach.vm))
    kv.extend(int(x) for x in P.G.bits(mach.kv))
(out/"expect_tokens_steps.hex").write_text(P.hexwords(tokens,16))
(out/"expect_logits_steps.hex").write_text(P.hexwords(logits,32))
(out/"expect_vm_steps.hex").write_text(P.hexwords(vm,32))
(out/"expect_kv_steps.hex").write_text(P.hexwords(kv,32))
print(*tokens)
'''
        oracle = subprocess.run([sys.executable, "-c", oracle_code, str(img)], cwd=ROOT,
                                env=env, capture_output=True, text=True, check=True)
        rec["isa_tokens"] = [int(x) for x in oracle.stdout.split()]
        rec["image_sha256"] = {p.name: sha(p) for p in img.glob("*.hex")}
        exe = obj / "Vtb_hdc_core"
        manifest = work / "source_sha256.json"
        if not (args.reuse and exe.exists() and manifest.exists() and
                json.loads(manifest.read_text()) == pins):
            cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal",
                   "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-VARHIDDEN",
                   "--unroll-count", "65536", "--top-module", "tb_hdc_core",
                   "-GG=4", "-GSW=16", "-GKV_BRIDGE=0", "-Mdir", str(obj),
                   f"-I{BASE.ISA_SVH.parent}", *map(str, SOURCES), "-CFLAGS", "-O1"]
            build = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, MAKEFLAGS="-j8"),
                                   capture_output=True, text=True)
            if build.returncode:
                raise RuntimeError("build: " + (build.stdout + build.stderr)[-8000:])
            manifest.write_text(json.dumps(pins, sort_keys=True) + "\n")
        rec["binary_sha256"] = sha(exe)
        sim = subprocess.run([str(exe), f"+DIR={img}", "+SYSTEM_MULTI", "+NPROMPT=16",
                              "+NGEN=3", f"+STOPSTEP={args.steps}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=3600)
        steps = [dict(zip(("position", "input_token", "output_token", "expected_token",
                           "cycles", "fault", "logit_mismatches", "vm_mismatches",
                           "kv_mismatches", "hbm_reads", "hbm_writes"), map(int, m.groups())))
                 for m in STEP.finditer(sim.stdout)]
        rec["steps"] = steps
        match = SUMMARY.search(sim.stdout)
        phys = PHYS.search(sim.stdout)
        timing = TIMING.search(sim.stdout)
        if match:
            rec["summary"] = dict(zip(("steps", "generated", "total_cycles", "token_mismatches",
                                       "logit_mismatches", "vm_mismatches", "kv_mismatches",
                                       "physical_byte_mismatches"), map(int, match.groups())))
        if phys:
            rec["physical_hbm"] = dict(zip(("boot_done", "boot_reads", "reads", "writes",
                                             "v_reads_after_write", "k_flush_writes",
                                             "byte_mismatches", "fault", "drained", "committed_writes"),
                                           map(int, phys.groups())))
        if timing:
            rec["hbm_timing"] = dict(zip(("completed_reads", "acts", "row_hits", "refreshes",
                                           "backpressure_cycles", "read_latency_avg_ps",
                                           "read_latency_max_ps"), map(int, timing.groups())))
        s, p, t = rec.get("summary", {}), rec.get("physical_hbm", {}), rec.get("hbm_timing", {})
        exact = (sim.returncode == 0 and "PASS" in sim.stdout and len(steps) == args.steps and
                 s.get("steps") == args.steps and s.get("generated") == max(0, args.steps - 15) and
                 all(s.get(k) == 0 for k in ("token_mismatches", "logit_mismatches",
                                               "vm_mismatches", "kv_mismatches",
                                               "physical_byte_mismatches")) and
                 all(x["output_token"] == x["expected_token"] and x["fault"] == 0 for x in steps) and
                 p.get("boot_done") == 1 and p.get("boot_reads") == 128 and
                 p.get("v_reads_after_write", 0) > 0 and
                 (args.steps < 17 or p.get("k_flush_writes", 0) >= 128) and
                 p.get("fault") == 0 and p.get("drained") == 1 and
                 p.get("committed_writes") == p.get("writes") and
                 t.get("completed_reads") == p.get("reads") and t.get("acts", 0) > 0 and
                 t.get("read_latency_max_ps", 0) >= t.get("read_latency_avg_ps", 0) > 0)
        rec.update(status="pass" if exact else "fail", phase="simulation",
                   returncode=sim.returncode, stdout=sim.stdout[-16000:],
                   stderr=sim.stderr[-4000:])
    except Exception as exc:
        rec.update(status="fail", phase="exception", error=str(exc))
    rec["workdir"] = str(work)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(args.output, rec["status"], rec.get("phase"), flush=True)
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

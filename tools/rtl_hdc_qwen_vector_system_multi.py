#!/usr/bin/env python3
"""Source-pinned empty-cache Qwen prompt and generation on autonomous physical KV HBM."""
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

TB = ROOT / "rtl/test/tb_hdc_core_qwen_system_multi.sv"
SOURCES = [*BASE.HDC, *BASE.PIPES, *BASE.BRIDGE_RTL, *TWO.KV, TB, BASE.HARNESS]
INPUTS = [*SOURCES, BASE.ISA_SVH, ROOT / "tools/hdc_program.py",
          ROOT / "tools/hdc_golden.py", Path(__file__)]
STEP = re.compile(r"KV_MULTI_STEP pos=(\d+) in=(\d+) out=(\d+) expect=(\d+) cycles=(\d+) "
                  r"fault=(\d+) lg_bad=(\d+) vm_bad=(\d+) kv_bad=(\d+) hbm_reads=(\d+) hbm_writes=(\d+)")
SUMMARY = re.compile(r"KV_MULTI steps=(\d+) generated=(\d+) total_cycles=(\d+) "
                     r"token_mismatches=(\d+) logit_mismatches=(\d+) vm_mismatches=(\d+) "
                     r"kv_mismatches=(\d+) physical_byte_mismatches=(\d+)")
PHYS = re.compile(r"KV_MULTI_PHYS boot_done=(\d+) boot_reads=(\d+) hbm_reads=(\d+) "
                  r"hbm_writes=(\d+) v_reads_after_write=(\d+) k_flush_writes=(\d+) "
                  r"physical_byte_mismatches=(\d+) fault=(\d+) drained=(\d+)")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--steps", type=int, default=18, choices=range(2, 19))
    ap.add_argument("--workdir", type=Path, help="persistent scratch directory for this exact source")
    ap.add_argument("--reuse", action="store_true", help="reuse executable after source-hash validation")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/hdc_qwen_vector_system_multi_g4sw16.json")
    args = ap.parse_args()
    env = dict(os.environ, HDC_GROUPS="4", HDC_SU_WIDTH="16", HDC_KV_FMT="fp8")
    pins = {str(p.relative_to(ROOT)): sha(p) for p in INPUTS}
    rec = {"schema": "opentallas.qwen-vector-system-multi.v1",
           "configuration": {"groups": 4, "su_width": 16, "prompt_tokens": 16,
                             "generated_tokens": 3, "steps_executed": args.steps,
                             "physical_hbm_bytes": 32},
           "claim_boundary": "Reduced Qwen functional RTL with autonomous 128-sector physical HBM K boot, "
                             "banked K tail, physical HBM KV path, and exact per-step ISA state. "
                             "The behavioral HBM has one-cycle reads and no calibrated bandwidth or refresh; "
                             "cycles are not full-model throughput or chip energy.",
           "input_sha256": pins}
    work = args.workdir or Path(tempfile.mkdtemp(prefix="qwen_vec_system_multi_"))
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
        if match:
            rec["summary"] = dict(zip(("steps", "generated", "total_cycles", "token_mismatches",
                                       "logit_mismatches", "vm_mismatches", "kv_mismatches",
                                       "physical_byte_mismatches"), map(int, match.groups())))
        if phys:
            rec["physical_hbm"] = dict(zip(("boot_done", "boot_reads", "reads", "writes",
                                             "v_reads_after_write", "k_flush_writes",
                                             "byte_mismatches", "fault", "drained"),
                                           map(int, phys.groups())))
        s, p = rec.get("summary", {}), rec.get("physical_hbm", {})
        exact = (sim.returncode == 0 and "PASS" in sim.stdout and len(steps) == args.steps and
                 s.get("steps") == args.steps and s.get("generated") == max(0, args.steps - 15) and
                 all(s.get(k) == 0 for k in ("token_mismatches", "logit_mismatches",
                                               "vm_mismatches", "kv_mismatches",
                                               "physical_byte_mismatches")) and
                 all(x["output_token"] == x["expected_token"] and x["fault"] == 0 for x in steps) and
                 p.get("boot_done") == 1 and p.get("boot_reads") == 128 and
                 p.get("v_reads_after_write", 0) > 0 and
                 (args.steps < 17 or p.get("k_flush_writes", 0) >= 128) and
                 p.get("fault") == 0 and p.get("drained") == 1)
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

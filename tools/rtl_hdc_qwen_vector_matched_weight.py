#!/usr/bin/env python3
"""Matched vector ROM/HBM weight gate with the same timed four-PC HBM KV path."""
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
import rtl_hdc_qwen_vector_system_two_token as TWO  # KV source list
import hdc_timing as TIMING  # noqa: E402

TB = ROOT / "rtl/test/tb_hdc_core_qwen_vector_weight.sv"
CORE = ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv"
DYN_TTILES = ROOT / "rtl/hdc/ot_hdc_dyn_ttiles.sv"
WSTREAM = ROOT / "rtl/hdc/hbm/ot_hdc_wstream.sv"
ARB = ROOT / "rtl/hdc/hbm/ot_hdc_hbm_arb.sv"
HBM = ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"
SOURCES = [*BASE.HDC[:-1], DYN_TTILES, CORE, *BASE.PIPES, *BASE.BRIDGE_RTL, *TWO.KV, HBM, WSTREAM, ARB, TB, BASE.HARNESS]
INPUTS = [*SOURCES, BASE.ISA_SVH, ROOT / "tools/hdc_program.py",
          ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_isa.py",
          ROOT / "tools/hdc_timing.py", Path(__file__)]
STEP = re.compile(r"KV_MULTI_STEP pos=(\d+) in=(\d+) out=(\d+) expect=(\d+) cycles=(\d+) "
                  r"fault=(\d+) lg_bad=(\d+) vm_bad=(\d+) kv_bad=(\d+) hbm_reads=(\d+) hbm_writes=(\d+)")
SUMMARY = re.compile(r"KV_MULTI steps=(\d+) generated=(\d+) total_cycles=(\d+) "
                     r"token_mismatches=(\d+) logit_mismatches=(\d+) vm_mismatches=(\d+) "
                     r"kv_mismatches=(\d+) physical_byte_mismatches=(\d+)")
PHYS = re.compile(r"KV_MULTI_PHYS boot_done=(\d+) boot_reads=(\d+) hbm_reads=(\d+) "
                  r"hbm_writes=(\d+) v_reads_after_write=(\d+) k_flush_writes=(\d+) "
                  r"physical_byte_mismatches=(\d+) fault=(\d+) drained=(\d+) committed_writes=(\d+)")
TIMING_RE = re.compile(r"KV_MULTI_HBM_TIMING completed_reads=(\d+) acts=(\d+) row_hits=(\d+) "
                    r"refreshes=(\d+) backpressure_cycles=(\d+) rd_lat_avg_ps=(\d+) rd_lat_max_ps=(\d+)")


MATCHED = re.compile(r"MATCHED_WEIGHT whbm=(\d+) boot_cycles=(\d+) weight_req_reads=(\d+) weight_sector_reads=(\d+) weight_completed_sectors=(\d+) "
                     r"kv_completed_sectors=(\d+) weight_words=(\d+) weight_delivery_mismatches=(\d+) weight_fault=(\d+) "
                     r"weight_fault_why=(\d+) weight_fetched=(\d+) weight_consumed=(\d+) "
                     r"weight_stall_cycles=(\d+) embedding_stall_cycles=(\d+) "
                     r"arb_weight_denied_cycles=(\d+)")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--steps", type=int, default=2, choices=range(2, 19))
    ap.add_argument("--npc", type=int, default=4, choices=(1, 2, 4),
                    help="pseudo-channels shared by KV and weight traffic in both arms")
    ap.add_argument("--workdir", type=Path, help="persistent scratch directory for this exact source")
    ap.add_argument("--reuse", action="store_true", help="reuse executables after source-hash validation")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/hdc_qwen_vector_matched_weight_g4sw16.json")
    args = ap.parse_args()
    env = dict(os.environ, HDC_GROUPS="4", HDC_SU_WIDTH="16", HDC_KV_FMT="fp8")
    pins = {str(p.relative_to(ROOT)): sha(p) for p in INPUTS}
    rec = {"schema": "opentallas.qwen-vector-matched-weight.v1",
           "configuration": {"groups": 4, "su_width": 16, "steps_executed": args.steps,
                             "weight_chunk_words": 1536, "clock_ps": 1000,
                             "weight_rate_words_x256": TIMING.w_rate(dict(TIMING.WH,npc=args.npc)),
                             "kv_hbm_pseudo_channels": args.npc,
                             "kv_hbm_model": "ot_hdc_hbm_model PC_RDY=1; modeled timing/refresh"},
           "claim_boundary": "Reduced Qwen vector behavioral RTL. Both modes run the same chunked ISA program, "
                             "vector controller and arithmetic, autonomous physical K boot, physical K/V sectors, "
                             "and four-PC timed HBM controller for KV. Weight supply alone differs: synchronous "
                             "ROM versus shared timed HBM via ot_hdc_wstream/arbiter. Core cycles exclude pre-token "
                             "boot and exclude power/physical constraints. This is not a production bandwidth, "
                             "throughput, or energy estimate.",
           "source_sha256": pins}
    work = args.workdir or Path(tempfile.mkdtemp(prefix="qwen_vec_system_timed_"))
    work.mkdir(parents=True, exist_ok=True)
    img, obj = work / "img", work / "obj"
    try:
        gen = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"),
                              "--out", str(img), "--context", "16", "--wchunk", "1536"], cwd=ROOT, env=env,
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
prog=P.build_program(lay,wchunk=1536)
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
        rec["image_sha256"] = {p.name: sha(p) for p in img.iterdir() if p.is_file()}
        hbm_args = (img / "hbm.args").read_text().split()
        rec["model_sha256"] = sha(ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors")
        for mode, whbm in (("rom",0),("hbm",1)):
            mode_obj = work / f"obj_{mode}"
            exe = mode_obj / "Vtb_hdc_core"
            manifest = work / f"source_sha256_{mode}.json"
            mode_pins = dict(pins, mode=mode, npc=args.npc)
            # The executable depends on RTL, TB, harness and ISA offsets. The
            # runner and oracle can be tightened without recompiling a binary
            # whose compiled inputs still have the exact same hashes.
            compiled_pins = {str(p.relative_to(ROOT)): sha(p) for p in [*SOURCES, BASE.ISA_SVH]}
            prior = json.loads(manifest.read_text()) if manifest.exists() else {}
            binary_reused = bool(args.reuse and exe.exists() and prior.get("mode") == mode and
                                 prior.get("npc") == args.npc and
                                 all(prior.get(k) == v for k, v in compiled_pins.items()))
            if not binary_reused:
                cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal",
                       "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-VARHIDDEN",
                       "-Wno-PINMISSING", "-Wno-TIMESCALEMOD", "--unroll-count", "65536",
                       "--top-module", "tb_hdc_core", "-GG=4", "-GSW=16", "-GKV_BRIDGE=0",
                       f"-GWHBM={whbm}", f"-GSYS_NPC={args.npc}", "-Mdir", str(mode_obj), f"-I{BASE.ISA_SVH.parent}",
                       *map(str, SOURCES), "-CFLAGS", "-O1"]
                build = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, MAKEFLAGS="-j2"),
                                       capture_output=True, text=True)
                if build.returncode:
                    raise RuntimeError(f"{mode} build: " + (build.stdout + build.stderr)[-8000:])
                manifest.write_text(json.dumps(mode_pins, sort_keys=True) + "\n")
            command = [str(exe), f"+DIR={img}", "+SYSTEM_MULTI", "+NPROMPT=16", "+NGEN=3",
                       f"+STOPSTEP={args.steps}", *hbm_args,
                       f"+WRATE={rec['configuration']['weight_rate_words_x256']}"]
            sim = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=3600)
            steps = [dict(zip(("position", "input_token", "output_token", "expected_token",
                               "cycles", "fault", "logit_mismatches", "vm_mismatches",
                               "kv_mismatches", "kv_hbm_reads", "kv_hbm_writes"), map(int, m.groups())))
                     for m in STEP.finditer(sim.stdout)]
            entry={"binary_sha256":sha(exe),"binary_reused":binary_reused,"returncode":sim.returncode,"steps":steps,
                   "command_args":command[1:],"stdout_tail":sim.stdout[-16000:],"stderr_tail":sim.stderr[-4000:]}
            for regex,key,names in ((SUMMARY,"summary",("steps","generated","total_cycles","token_mismatches",
                "logit_mismatches","vm_mismatches","kv_mismatches","physical_byte_mismatches")),
                (PHYS,"physical_hbm",("boot_done","boot_reads","reads","writes","v_reads_after_write",
                    "k_flush_writes","byte_mismatches","fault","drained","committed_writes")),
                (TIMING_RE,"hbm_timing",("completed_reads","acts","row_hits","refreshes",
                    "backpressure_cycles","read_latency_avg_ps","read_latency_max_ps")),
                (MATCHED,"weights",("whbm","boot_cycles","weight_req_reads","weight_sector_reads","weight_completed_sectors","kv_completed_sectors","weight_words",
                    "weight_delivery_mismatches","weight_fault","weight_fault_why","weight_fetched",
                    "weight_consumed","weight_stall_cycles","embedding_stall_cycles",
                    "arb_weight_denied_cycles"))):
                m=regex.search(sim.stdout)
                if m: entry[key]=dict(zip(names,map(int,m.groups())))
            ss,ph,tt,ww=(entry.get(k,{}) for k in ("summary","physical_hbm","hbm_timing","weights"))
            accepted = ph.get("reads", 0) + ww.get("weight_sector_reads", 0)
            scheduled = tt.get("completed_reads", 0)
            delivered = ww.get("kv_completed_sectors", 0) + ww.get("weight_completed_sectors", 0)
            entry["hbm_read_pipeline"] = {
                "accepted_sectors": accepted,
                "scheduled_sectors": scheduled,
                "delivered_sectors": delivered,
                "queued_unscheduled_sectors": accepted - scheduled,
                "scheduled_undelivered_sectors": scheduled - delivered,
            }
            ok=(sim.returncode==0 and "PASS" in sim.stdout and len(steps)==args.steps and
                ss.get("steps")==args.steps and ss.get("generated")==max(0,args.steps-15) and
                all(ss.get(k)==0 for k in ("token_mismatches","logit_mismatches","vm_mismatches",
                                              "kv_mismatches","physical_byte_mismatches")) and
                all(x["output_token"]==x["expected_token"] and x["fault"]==0 for x in steps) and
                ph.get("boot_done")==1 and ph.get("boot_reads")==128 and
                ph.get("v_reads_after_write",0)>0 and ph.get("fault")==0 and ph.get("drained")==1 and
                ph.get("committed_writes")==ph.get("writes") and
                accepted >= scheduled >= delivered and
                ww.get("weight_sector_reads",0) >= ww.get("weight_completed_sectors",0) and
                ph.get("reads",0) >= ww.get("kv_completed_sectors",0) and
                tt.get("acts",0)>0 and tt.get("read_latency_avg_ps",0)>0 and
                ww.get("whbm")==whbm and ww.get("boot_cycles",0)>0 and
                ww.get("weight_delivery_mismatches")==0 and ww.get("weight_fault")==0 and
                (whbm==0 or (ww.get("weight_req_reads",0)>0 and ww.get("weight_consumed",0)>0)))
            entry["pass"]=bool(ok)
            rec[mode]=entry
            if not ok: break
        rec["status"]="pass" if rec.get("rom",{}).get("pass") and rec.get("hbm",{}).get("pass") else "fail"
        rec["phase"]="simulation"
    except Exception as exc:
        rec.update(status="fail", phase="exception", error=str(exc))
    rec["workdir"] = str(work)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(args.output, rec["status"], rec.get("phase"), flush=True)
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run both cached Qwen matched-vector weight modes concurrently over 18 steps."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_qwen_vector_matched_weight as BASE  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(regex, names, text):
    m = regex.search(text)
    return dict(zip(names, map(int, m.groups()))) if m else {}


def parse_mode(mode, whbm, log, exe, expected):
    output = log.read_text()
    steps = [dict(zip(("position", "input_token", "output_token", "expected_token",
                       "cycles", "fault", "logit_mismatches", "vm_mismatches",
                       "kv_mismatches", "kv_hbm_reads", "kv_hbm_writes"), map(int, m.groups())))
             for m in BASE.STEP.finditer(output)]
    summary = fields(BASE.SUMMARY, ("steps", "generated", "total_cycles", "token_mismatches",
                                    "logit_mismatches", "vm_mismatches", "kv_mismatches",
                                    "physical_byte_mismatches"), output)
    phys = fields(BASE.PHYS, ("boot_done", "boot_reads", "reads", "writes",
                              "v_reads_after_write", "k_flush_writes", "byte_mismatches",
                              "fault", "drained", "committed_writes"), output)
    timing = fields(BASE.TIMING_RE, ("completed_reads", "acts", "row_hits", "refreshes",
                                     "backpressure_cycles", "read_latency_avg_ps",
                                     "read_latency_max_ps"), output)
    weights = fields(BASE.MATCHED, ("whbm", "boot_cycles", "weight_req_reads",
                                    "weight_sector_reads", "weight_completed_sectors",
                                    "kv_completed_sectors", "weight_words",
                                    "weight_delivery_mismatches", "weight_fault",
                                    "weight_fault_why", "weight_fetched", "weight_consumed",
                                    "weight_stall_cycles", "embedding_stall_cycles",
                                    "arb_weight_denied_cycles"), output)
    accepted = phys.get("reads", 0) + weights.get("weight_sector_reads", 0)
    scheduled = timing.get("completed_reads", 0)
    delivered = weights.get("kv_completed_sectors", 0) + weights.get("weight_completed_sectors", 0)
    pipeline = {"accepted_sectors": accepted, "scheduled_sectors": scheduled,
                "delivered_sectors": delivered, "queued_unscheduled_sectors": accepted - scheduled,
                "scheduled_undelivered_sectors": scheduled - delivered}
    exact = ("PASS" in output and len(steps) == 18 and summary.get("steps") == 18 and
             summary.get("generated") == 3 and
             all(summary.get(k) == 0 for k in ("token_mismatches", "logit_mismatches",
                                               "vm_mismatches", "kv_mismatches",
                                               "physical_byte_mismatches")) and
             all(s["position"] == i and s["output_token"] == s["expected_token"] == expected[i] and
                 s["fault"] == s["logit_mismatches"] == s["vm_mismatches"] == s["kv_mismatches"] == 0
                 for i, s in enumerate(steps)) and
             phys.get("boot_done") == 1 and phys.get("boot_reads") == 128 and
             phys.get("v_reads_after_write", 0) > 0 and phys.get("k_flush_writes", 0) >= 128 and
             phys.get("byte_mismatches") == phys.get("fault") == 0 and
             phys.get("drained") == 1 and phys.get("committed_writes") == phys.get("writes") and
             weights.get("whbm") == whbm and weights.get("boot_cycles", 0) > 0 and
             weights.get("weight_delivery_mismatches") == weights.get("weight_fault") == 0 and
             accepted >= scheduled >= delivered and
             weights.get("weight_sector_reads", 0) >= weights.get("weight_completed_sectors", 0) and
             phys.get("reads", 0) >= weights.get("kv_completed_sectors", 0) and
             (whbm == 0 or (weights.get("weight_req_reads", 0) > 0 and
                            weights.get("weight_consumed", 0) > 0 and
                            weights.get("arb_weight_denied_cycles", 0) > 0)))
    return {"mode": mode, "pass": bool(exact), "steps": steps, "summary": summary,
            "physical_hbm": phys, "hbm_timing": timing, "weights": weights,
            "hbm_read_pipeline": pipeline, "binary_sha256": sha(exe),
            "stdout": output, "log_path": str(log)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    work = args.workdir.resolve()
    img = work / "img"
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    inputs = [*BASE.INPUTS, Path(__file__).resolve()]
    rec = {"schema": "opentallas.qwen-vector-matched-weight-full.v1",
           "configuration": {"groups": 4, "su_width": 16, "prompt_steps": 16,
                             "generated_steps": 3, "steps_executed": 18,
                             "weight_chunk_words": 1536, "clock_ps": 1000,
                             "kv_hbm_pseudo_channels": 4,
                             "weight_rate_words_x256": 201,
                             "mode_execution": "concurrent independent processes"},
           "claim_boundary": "Reduced Qwen vector behavioral RTL. Both modes use the same chunked ISA, "
                             "controller, arithmetic, and timed four-PC physical KV HBM. Only weight "
                             "supply differs (synchronous ROM versus a weight streamer sharing HBM). "
                             "Core cycles exclude pre-token K boot; modeled controller timing is not "
                             "production throughput, bandwidth, chip energy, or physical timing closure.",
           "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
           "model_sha256": sha(model),
           "image_sha256": {p.name: sha(p) for p in img.iterdir() if p.is_file()},
           "workdir": str(work)}
    expected = [int(s, 16) for s in (img / "expect_tokens_steps.hex").read_text().split()]
    rec["isa_tokens"] = expected
    assert len(expected) == 18
    hbm_args = (img / "hbm.args").read_text().split()
    jobs = {}
    try:
        for mode, whbm in (("rom", 0), ("hbm", 1)):
            exe = work / f"obj_{mode}/Vtb_hdc_core"
            manifest = json.loads((work / f"source_sha256_{mode}.json").read_text())
            assert manifest["mode"] == mode
            for source in [*BASE.SOURCES, BASE.BASE.ISA_SVH]:
                key = str(source.relative_to(ROOT))
                assert manifest[key] == sha(source), f"stale compiled input: {key}"
            assert exe.exists()
            log = work / f"full18_{mode}.log"
            command = [str(exe), f"+DIR={img}", "+SYSTEM_MULTI", "+NPROMPT=16",
                       "+NGEN=3", "+STOPSTEP=18", *hbm_args, "+WRATE=201"]
            stream = log.open("w")
            proc = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            jobs[mode] = (proc, stream, log, exe, command)
        deadline = time.monotonic() + 3600
        while any(proc.poll() is None for proc, *_ in jobs.values()):
            if time.monotonic() > deadline:
                raise TimeoutError("18-step matched-vector mode exceeded one hour")
            time.sleep(5)
        for mode, (proc, stream, log, exe, command) in jobs.items():
            stream.close()
            entry = parse_mode(mode, int(mode == "hbm"), log, exe, expected)
            entry["returncode"] = proc.returncode
            entry["command_args"] = command[1:]
            entry["pass"] = entry["pass"] and proc.returncode == 0
            rec[mode] = entry
        rec["status"] = "pass" if rec["rom"]["pass"] and rec["hbm"]["pass"] else "fail"
        rec["phase"] = "simulation"
    except Exception as exc:
        rec.update(status="fail", phase="exception", error=str(exc))
    finally:
        for proc, stream, *_ in jobs.values():
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill()
            stream.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(args.output, rec["status"], rec["phase"], flush=True)
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

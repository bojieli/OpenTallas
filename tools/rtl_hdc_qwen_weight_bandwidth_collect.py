#!/usr/bin/env python3
"""Collect source-pinned cross-host ROM/HBM logs for the reduced Qwen gate."""

import argparse
import hashlib
import json
from pathlib import Path

import rtl_hdc_qwen_vector_matched_weight as base

ROOT = Path(__file__).resolve().parents[1]
ARM = ROOT / "tools/rtl_hdc_qwen_weight_bandwidth_arm.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


FIELDS = (
    (base.SUMMARY, "summary", ("steps", "generated", "total_cycles", "token_mismatches",
                               "logit_mismatches", "vm_mismatches", "kv_mismatches",
                               "physical_byte_mismatches")),
    (base.PHYS, "physical_hbm", ("boot_done", "boot_reads", "reads", "writes",
                                 "v_reads_after_write", "k_flush_writes", "byte_mismatches",
                                 "fault", "drained", "committed_writes")),
    (base.TIMING_RE, "hbm_timing", ("completed_reads", "acts", "row_hits", "refreshes",
                                    "backpressure_cycles", "read_latency_avg_ps",
                                    "read_latency_max_ps")),
    (base.MATCHED, "weights", ("whbm", "boot_cycles", "weight_req_reads",
                                "weight_sector_reads", "weight_completed_sectors",
                                "kv_completed_sectors", "weight_words",
                                "weight_delivery_mismatches", "weight_fault",
                                "weight_fault_why", "weight_fetched", "weight_consumed",
                                "weight_stall_cycles", "embedding_stall_cycles",
                                "arb_weight_denied_cycles")),
)


def collect_arm(log, meta_path, binary, images, npc, whbm, tokens):
    meta = json.loads(meta_path.read_text())
    output = log.read_text()
    if meta["returncode"] != 0 or sha(log) != meta["log_sha256"]:
        raise ValueError(f"failed or modified log: {log}")
    if sha(binary) != meta["binary_sha256"]:
        raise ValueError(f"binary changed: {binary}")
    image_pins = {p.name: sha(p) for p in images.iterdir() if p.is_file()}
    if image_pins != meta["image_sha256"]:
        raise ValueError(f"images changed: {images}")
    command = meta["command"]
    expected_rate = base.TIMING.w_rate(dict(base.TIMING.WH, npc=npc))
    if "+STOPSTEP=2" not in command or f"+WRATE={expected_rate}" not in command:
        raise ValueError(f"wrong workload or weight rate: {log}")
    steps = [dict(zip(("position", "input_token", "output_token", "expected_token",
                       "cycles", "fault", "logit_mismatches", "vm_mismatches",
                       "kv_mismatches", "kv_hbm_reads", "kv_hbm_writes"), map(int, m.groups())))
             for m in base.STEP.finditer(output)]
    entry = {"binary_sha256": sha(binary), "returncode": meta["returncode"],
             "command_args": command[1:], "log_sha256": sha(log),
             "stdout_tail": output[-16000:], "stderr_tail": "", "steps": steps}
    for regex, key, names in FIELDS:
        match = regex.search(output)
        if match:
            entry[key] = dict(zip(names, map(int, match.groups())))
    ss, ph, timing, weights = (entry.get(k, {}) for k in
                                ("summary", "physical_hbm", "hbm_timing", "weights"))
    accepted = ph.get("reads", 0) + weights.get("weight_sector_reads", 0)
    scheduled = timing.get("completed_reads", 0)
    delivered = weights.get("kv_completed_sectors", 0) + weights.get("weight_completed_sectors", 0)
    entry["hbm_read_pipeline"] = {
        "accepted_sectors": accepted, "scheduled_sectors": scheduled,
        "delivered_sectors": delivered,
        "queued_unscheduled_sectors": accepted - scheduled,
        "scheduled_undelivered_sectors": scheduled - delivered,
    }
    entry["pass"] = bool(
        "PASS" in output and len(steps) == 2 and ss.get("steps") == 2 and
        ss.get("generated") == 0 and
        all(ss.get(k) == 0 for k in ("token_mismatches", "logit_mismatches",
                                      "vm_mismatches", "kv_mismatches", "physical_byte_mismatches")) and
        all(step["position"] == i and step["output_token"] == step["expected_token"] == tokens[i]
            and step["fault"] == step["logit_mismatches"] == step["vm_mismatches"] ==
            step["kv_mismatches"] == 0 for i, step in enumerate(steps)) and
        ph.get("boot_done") == 1 and ph.get("boot_reads") == 128 and
        ph.get("v_reads_after_write", 0) > 0 and ph.get("fault") == 0 and
        ph.get("byte_mismatches") == 0 and ph.get("drained") == 1 and
        ph.get("committed_writes") == ph.get("writes") and
        accepted >= scheduled >= delivered and
        weights.get("weight_sector_reads", 0) >= weights.get("weight_completed_sectors", 0) and
        ph.get("reads", 0) >= weights.get("kv_completed_sectors", 0) and
        timing.get("acts", 0) > 0 and timing.get("read_latency_avg_ps", 0) > 0 and
        weights.get("whbm") == whbm and weights.get("boot_cycles", 0) > 0 and
        weights.get("weight_delivery_mismatches") == weights.get("weight_fault") == 0 and
        (whbm == 0 or (weights.get("weight_req_reads", 0) > 0 and
                       weights.get("weight_consumed", 0) > 0)))
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npc", type=int, choices=(1, 4), required=True)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--rom-log", type=Path, required=True)
    ap.add_argument("--hbm-log", type=Path, required=True)
    ap.add_argument("--rom-binary", type=Path, required=True)
    ap.add_argument("--hbm-binary", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    image_pins = {p.name: sha(p) for p in args.images.iterdir() if p.is_file()}
    tokens = [int(s, 16) for s in (args.images / "expect_tokens_steps.hex").read_text().split()]
    assert len(tokens) == 18
    inputs = [*base.INPUTS, ARM, Path(__file__).resolve()]
    record = {
        "schema": "opentallas.qwen-vector-matched-weight.v1",
        "configuration": {"groups": 4, "su_width": 16, "steps_executed": 2,
                          "weight_chunk_words": 1536, "clock_ps": 1000,
                          "weight_rate_words_x256": base.TIMING.w_rate(dict(base.TIMING.WH, npc=args.npc)),
                          "kv_hbm_pseudo_channels": args.npc,
                          "kv_hbm_model": "ot_hdc_hbm_model PC_RDY=1; modeled timing/refresh"},
        "claim_boundary": "Reduced G4/SW16 Qwen vector RTL; two prompt steps on the same program, "
                          "images, controller, arithmetic and timed KV HBM in both arms. Only "
                          "weight source differs. HBM timing is behavioral; this is not full "
                          "INT8 TP-2 throughput, chip energy or physical timing.",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        "image_sha256": image_pins,
        "model_sha256": sha(ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"),
        "isa_tokens": tokens,
        "execution_host": "agidock 155.103.253.114, Ubuntu 26.04, GCC 15, generated by Verilator 4.038 on source host",
    }
    for mode, whbm, log, binary in (("rom", 0, args.rom_log, args.rom_binary),
                                   ("hbm", 1, args.hbm_log, args.hbm_binary)):
        record[mode] = collect_arm(log, log.with_suffix(log.suffix + ".json"), binary,
                                   args.images, args.npc, whbm, tokens)
    record["status"] = "pass" if record["rom"]["pass"] and record["hbm"]["pass"] else "fail"
    record["phase"] = "cross-host log collection"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(args.output, record["status"], flush=True)
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

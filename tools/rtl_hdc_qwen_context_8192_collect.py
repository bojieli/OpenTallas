#!/usr/bin/env python3
"""Collect a source-pinned 8K Qwen RTL run executed on an identical remote binary."""
import argparse
import json
from pathlib import Path

import rtl_hdc_qwen_context_8192 as GATE

SELF = Path(__file__).resolve()
LAUNCHER = GATE.ROOT / "tools/rtl_hdc_qwen_context_8192_remote.py"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/qwen_context_8192"))
    ap.add_argument("--remote-host", default="ot-pve2")
    ap.add_argument("--remote-dir", default="/tmp/qwen_context_8192")
    ap.add_argument("--output", type=Path, default=GATE.ROOT / "results/rtl/hdc_qwen_context_8192.json")
    args = ap.parse_args()
    work = args.workdir.resolve()
    prepared = json.loads((work / "prepared_image.json").read_text())
    rec = {
        "schema": "opentallas.qwen-vector-context-ladder.v1",
        "configuration": prepared["configuration"],
        "oracle": prepared["oracle"],
        "model_sha256": prepared["model_sha256"],
        "image_sha256": prepared["image_sha256"],
        "source_sha256": {**prepared["source_sha256"],
                          str(SELF.relative_to(GATE.ROOT)): GATE.sha(SELF),
                          str(LAUNCHER.relative_to(GATE.ROOT)): GATE.sha(LAUNCHER)},
        "workdir": str(work),
        "execution": {"host": args.remote_host, "directory": args.remote_dir,
                      "transport": "rsync then identical-binary remote execution"},
        "claim_boundary": "Reduced Qwen G4/SW16 one-token RTL at position 8191, seeded by golden prefill. "
                          "Token, all logits, VM, KV, and committed 32-byte physical HBM sectors are checked exactly. "
                          "K/V use the four-PC timed behavioral HBM model; weights use synchronous ROM. "
                          "This is not a production bandwidth, throughput, energy, or physical timing claim.",
    }
    try:
        if prepared["status"] != "prepared" or prepared["phase"] != "image":
            raise RuntimeError("missing prepared image pass")
        if prepared["configuration"]["context_positions"] != 8192:
            raise RuntimeError("prepared image is not context 8192")
        for name, digest in prepared["source_sha256"].items():
            if GATE.sha(GATE.ROOT / name) != digest:
                raise RuntimeError(f"source pin differs: {name}")
        model = GATE.ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
        if GATE.sha(model) != rec["model_sha256"]:
            raise RuntimeError("model pin differs")
        for name, digest in rec["image_sha256"].items():
            if GATE.sha(work / "img" / name) != digest:
                raise RuntimeError(f"image pin differs: {name}")
        binary = work / "obj_ctx8192_w16384_lead32768_qd16_room4/Vtb_hdc_core"
        rec["binary_sha256"] = GATE.sha(binary)
        remote = json.loads((work / "remote_manifest.json").read_text())
        if remote["binary_sha256"] != rec["binary_sha256"]:
            raise RuntimeError("remote binary digest differs")
        if remote["image_sha256"] != rec["image_sha256"]:
            raise RuntimeError("remote image digests differ")
        rec["execution"]["remote_manifest"] = remote
        stdout_path, stderr_path = work / "remote_stdout.log", work / "remote_stderr.log"
        stdout, stderr = stdout_path.read_text(), stderr_path.read_text()
        rec["stdout_sha256"] = GATE.sha(stdout_path)
        rec["stderr_sha256"] = GATE.sha(stderr_path)
        rec["stdout"] = stdout
        rec["stderr"] = stderr[-4000:]
        rec["returncode"] = int((work / "remote_exitcode").read_text().strip())
        h, q = GATE.HDC.search(stdout), GATE.LONG.search(stdout)
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
        rec["status"] = "pass" if (rec["returncode"] == 0 and "PASS" in stdout and
                                     "KV_WINDOW_UNDERFLOW" not in stdout and
                                     t.get("position") == 8191 and
                                     t.get("actual") == t.get("expected") == rec["oracle"]["expected_token"] and
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

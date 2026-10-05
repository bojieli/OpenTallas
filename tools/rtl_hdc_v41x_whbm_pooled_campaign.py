#!/usr/bin/env python3
"""Source-pinned V4.1x token gate with QE weights and pooled index keys in HBM.

The ROM image is an independent delivered-word oracle only. Index-key records
traverse bounded four-stack write queues and refresh-aware HBM timing models.
This is a reduced single-token functional gate, not a full-rate array result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_decode_campaign as core  # noqa: E402

TB = ROOT / "rtl/test/tb_hdc_core_v41x_whbm.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41x_whbm_harness.cpp"
QSTREAM = ROOT / "rtl/hdc/hbm/ot_hdc_qstream.sv"
HBM = ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"
DEFAULT_OUTPUT = ROOT / "results/rtl/hdc_v41x_whbm_pooled_single.json"
STREAM = re.compile(r"^QSTREAM (.*)$", re.MULTILINE)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(obj: Path) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [
        "verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal",
        "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR",
        "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN",
        "-Wno-UNOPTFLAT", "--top-module", "tb_hdc_core_v41x_whbm",
        *[f"+define+HDC_X_{unit}={2 if unit == 'IDX' else 1}"
          for unit in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
        "-Mdir", str(obj), f"-I{core.SVH.parent}", str(core.VLT),
        *map(str, core.rtl_sources(True)), str(QSTREAM), str(HBM), str(TB),
        str(HARNESS), "-CFLAGS", "-O1", "-j", "4",
    ]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"Verilator build failed:\n{run.stdout[-4000:]}\n{run.stderr[-4000:]}")
    return obj / "Vtb_hdc_core_v41x_whbm"


def run(image_dir: Path, executable: Path) -> dict:
    args = (image_dir / "run.args").read_text().split()
    cmd = [str(executable), f"+DIR={image_dir}", *args, "+QRATE=32"]
    sim = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    log = sim.stdout + sim.stderr
    token = core.SINGLE.search(log)
    stream = STREAM.search(log)
    writer = core.IDXHBMWR.search(log)
    if token is None or stream is None or writer is None:
        raise RuntimeError(f"no complete token/stream record (exit {sim.returncode}):\n{log[-5000:]}")
    fields = dict(re.findall(r"(\w+)=(-?\d+)", stream.group(1)))
    stats = {key: int(value) for key, value in fields.items()}
    wr = dict(zip(("records", "sector_writes", "fifo_highwater", "read_stall_cycles",
                   "writer_stall_cycles", "refresh_events", "refpb_mode"),
                  map(int, writer.groups())))
    names = ("input_token", "position", "next_token", "isa_next_token", "cycles",
             "fault", "logit_mismatches", "vm_mismatches", "kv_mismatches")
    step = dict(zip(names, map(int, token.groups())))
    passed = (sim.returncode == 0 and "PASS" in log and
              step["next_token"] == step["isa_next_token"] == 3118 and
              step["fault"] == 0 and step["logit_mismatches"] == 0 and
              step["vm_mismatches"] == 0 and step["kv_mismatches"] == 0 and
              stats.get("q_bad") == 0 and stats.get("qs_fault") == 0 and
              stats.get("q_words", 0) > 0 and stats.get("hbm_reads", 0) > 0 and
              wr["records"] == 4 and wr["sector_writes"] == 12 * wr["records"] and
              wr["fifo_highwater"] <= 4 and wr["refresh_events"] > 0 and wr["refpb_mode"] == 3)
    return {"status": "pass" if passed else "fail", "step": step, "stream": stats,
            "index_key_hbm_writer": wr,
            "simulation_exit": sim.returncode,
            "simulation_log_sha256": hashlib.sha256(log.encode()).hexdigest(),
            "simulation_tail": log[-3000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-dir", type=Path, default=Path("/tmp/codex_v41x_whbm_pool_img"))
    parser.add_argument("--object-dir", type=Path, default=Path("/tmp/codex_v41x_whbm_pool_obj"))
    parser.add_argument("--reuse-images", action="store_true")
    parser.add_argument("--reuse-executable", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    core.UNITS = tuple(core.X_UNITS)
    core.PARAMS["fp"] = "dpi"
    core.IDX_POOL = True
    core.RTL.extend(ROOT / f"rtl/hdc/v41x/{name}.sv" for name in (
        "ot_hdc_v41x_idx_pcol", "ot_hdc_v41x_idx_hsum", "ot_hdc_v41x_idx_pool_finish",
        "ot_hdc_v41x_idx_pool_batch", "ot_hdc_v41x_idx_pool_replica",
        "ot_hdc_v41x_idx_pool_adapt", "ot_hdc_v41x_idx_pool_kwr",
        "ot_hdc_v41x_idx_pool_hbm_bridge"))
    if not args.reuse_images:
        core.images(args.image_dir, "--hbm", "--multi", "3")
    exe = args.object_dir / "Vtb_hdc_core_v41x_whbm"
    if not args.reuse_executable:
        exe = build(args.object_dir)
    record = run(args.image_dir, exe)
    sources = [*core.rtl_sources(True), core.SVH, core.VLT, QSTREAM, HBM, TB, HARNESS,
               ROOT / "tools/rtl_hdc_v41x_whbm_pooled_campaign.py",
               ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_images_v41x.py"]
    record.update({
        "schema": "opentallas.rtl.hdc_v41x_whbm_pooled_single.v1",
        "claim_boundary": "Reduced V4.1 single token, all-unit X_IDX=2 pooled indexer, QE weights delivered from HBM, index keys written/read through timed four-stack HBM models; no full-size array or production throughput claim.",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "image_sha256": {name: sha(args.image_dir / name) for name in
                         ("prog.hex", "qrom.hex", "qlist.hex", "hbm_q.hex", "expect_logits.hex")},
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"], record["step"], record["stream"])
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

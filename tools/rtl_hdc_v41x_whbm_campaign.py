#!/usr/bin/env python3
"""Source-pinned one-token gate for adopted V4.1x with QE weights in HBM.

The ROM image is an independent delivered-word oracle only. Index keys remain
in their separate HBM model. This checks a reduced single token; it does not
establish the adopted pooled-indexer array or full-size throughput.
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
ME_WINDOW = ROOT / "rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv"
DEFAULT_OUTPUT = ROOT / "results/rtl/hdc_v41x_whbm_single.json"
STREAM = re.compile(r"^QSTREAM (.*)$", re.MULTILINE)
ME0 = re.compile(r"^M0_HBM (.*)$", re.MULTILINE)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(obj: Path, me0_hbm: bool = False) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [
        "verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal",
        "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR",
        "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN",
        "-Wno-UNOPTFLAT", "--top-module", "tb_hdc_core_v41x_whbm",
        *[f"+define+HDC_X_{unit}=1" for unit in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
        *(["+define+HDC_ME0_HBM=1", "+define+HDC_ME0_HBM_GATE=1"] if me0_hbm else []),
        "-Mdir", str(obj), f"-I{core.SVH.parent}", str(core.VLT),
        *map(str, core.rtl_sources(True)), str(QSTREAM), str(HBM), str(ME_WINDOW), str(TB),
        str(HARNESS), "-CFLAGS", "-O1", "-j", "4",
    ]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"Verilator build failed:\n{run.stdout[-4000:]}\n{run.stderr[-4000:]}")
    return obj / "Vtb_hdc_core_v41x_whbm"


def run(image_dir: Path, executable: Path, me0_hbm: bool = False,
        sim_log: Path | None = None, trace: bool = False) -> dict:
    args = (image_dir / "run.args").read_text().split()
    cmd = [str(executable), f"+DIR={image_dir}", *args, "+QRATE=32"]
    if trace:
        cmd.append("+TRACE")
    if sim_log is None:
        sim = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        log = sim.stdout + sim.stderr
    else:
        sim_log.parent.mkdir(parents=True, exist_ok=True)
        # Preserve progress and failures even if a long simulation is stopped.
        # Verilator's $display output otherwise remains in a buffered pipe.
        with sim_log.open("w") as fh:
            sim = subprocess.run(["stdbuf", "-oL", *cmd], stdout=fh,
                                 stderr=subprocess.STDOUT, timeout=3600)
        log = sim_log.read_text()
    token = core.SINGLE.search(log)
    stream = STREAM.search(log)
    me0 = ME0.search(log)
    if token is None or stream is None or (me0_hbm and me0 is None):
        raise RuntimeError(f"no complete token/stream record (exit {sim.returncode}):\n{log[-5000:]}")
    fields = dict(re.findall(r"(\w+)=(-?\d+)", stream.group(1)))
    stats = {key: int(value) for key, value in fields.items()}
    me0_stats = {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", me0.group(1))} if me0 else None
    names = ("input_token", "position", "next_token", "isa_next_token", "cycles",
             "fault", "logit_mismatches", "vm_mismatches", "kv_mismatches")
    step = dict(zip(names, map(int, token.groups())))
    passed = (sim.returncode == 0 and "PASS" in log and
              step["next_token"] == step["isa_next_token"] == 3118 and
              step["fault"] == 0 and step["logit_mismatches"] == 0 and
              step["vm_mismatches"] == 0 and step["kv_mismatches"] == 0 and
              stats.get("q_bad") == 0 and stats.get("qs_fault") == 0 and
              stats.get("q_words", 0) > 0 and stats.get("hbm_reads", 0) > 0 and
              (not me0_hbm or (me0_stats is not None and me0_stats.get("reads", 0) > 0 and
                                me0_stats.get("sectors") == 36 and me0_stats.get("bad") == 0 and
                                me0_stats.get("fault") == 0)))
    return {"status": "pass" if passed else "fail", "step": step, "stream": stats,
            "me0_hbm": me0_stats,
            "simulation_exit": sim.returncode,
            "simulation_log_sha256": hashlib.sha256(log.encode()).hexdigest(),
            "simulation_tail": log[-3000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-dir", type=Path, default=Path("/tmp/codex_v41x_whbm_img"))
    parser.add_argument("--object-dir", type=Path, default=Path("/tmp/codex_v41x_whbm_obj"))
    parser.add_argument("--reuse-images", action="store_true")
    parser.add_argument("--reuse-executable", action="store_true")
    parser.add_argument("--me0-hbm", action="store_true",
                        help="deliver L0.router ME bank 0 through a bounded timed HBM window")
    parser.add_argument("--sim-log", type=Path,
                        help="stream line-buffered simulation output here for progress inspection")
    parser.add_argument("--trace", action="store_true", help="record issued program counters in the simulation log")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    core.UNITS = tuple(core.X_UNITS)
    core.PARAMS["fp"] = "dpi"
    if not args.reuse_images:
        core.images(args.image_dir, "--hbm", "--multi", "3")
    exe = args.object_dir / "Vtb_hdc_core_v41x_whbm"
    if not args.reuse_executable:
        exe = build(args.object_dir, args.me0_hbm)
    record = run(args.image_dir, exe, args.me0_hbm, args.sim_log, args.trace)
    sources = [*core.rtl_sources(True), core.SVH, core.VLT, QSTREAM, HBM, ME_WINDOW, TB, HARNESS,
               ROOT / "tools/rtl_hdc_v41x_whbm_campaign.py",
               ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_images_v41x.py"]
    record.update({
        "schema": ("opentallas.rtl.hdc_v41x_me0_whbm_single.v1" if args.me0_hbm else
                   "opentallas.rtl.hdc_v41x_whbm_single.v1"),
        "claim_boundary": ("Reduced V4.1 single token with QE weights and only L0.router ME bank 0 delivered from separately modeled timed HBM; other ME banks and weight families remain ROM, and this does not model contention with KV/index or full-size throughput."
                           if args.me0_hbm else
                           "Reduced V4.1 single token, adopted all-unit X_IDX=1 debug indexer, QE weights delivered from HBM; no pooled indexer or full-size array claim."),
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

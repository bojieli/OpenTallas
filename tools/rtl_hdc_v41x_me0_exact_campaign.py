#!/usr/bin/env python3
"""Source-pinned exact reduced L0.router ME operation with one timed HBM bank."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RTL_SOURCES = [
    ROOT / "rtl/hdc/ot_hdc_fastfp.sv",
    ROOT / "rtl/hdc/ot_hdc_delay.sv",
    ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv",
    *[ROOT / f"rtl/hdc/v41x/ot_hdc_v41x_wgt_{s}.sv" for s in ("bdot", "red", "mac", "tile")],
    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv",
    ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv",
    ROOT / "rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv",
    ROOT / "rtl/test/tb_hdc_v41x_me0_exact.sv",
]
SOURCES = [
    *RTL_SOURCES,
    ROOT / "tools/v41x_me0_exact_fixture.py",
    ROOT / "tools/hdc_program_v41.py",
    ROOT / "tools/hdc_golden_v41.py",
    ROOT / "tools/hdc_golden.py",
    ROOT / "tools/hdc_images_v41x.py",
    Path(__file__).resolve(),
]
PASS = re.compile(r"ME0_PASS exact_rows=(\d+) rom_reads=(\d+) hbm_sectors=(\d+) cycles=(\d+)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def call(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mbank", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/codex_v41x_me0_exact"))
    ap.add_argument("--output", type=Path, default=Path("/tmp/codex_v41x_me0_exact.json"))
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    call([sys.executable, str(ROOT / "tools/v41x_me0_exact_fixture.py"), "--out", str(args.scratch), "--mbank", str(args.mbank)])
    exe = args.scratch / "tb.vvp"
    call(["iverilog", "-g2012", "-s", "tb_hdc_v41x_me0_exact", "-o", str(exe), *map(str, RTL_SOURCES)])
    arms = {}
    for mode, extra in (("rom", ["+ROM_ONLY"]), ("hbm", [])):
        log = call(["vvp", str(exe), f"+DIR={args.scratch}", *extra])
        m = PASS.search(log)
        if not m:
            raise RuntimeError(f"{mode} missing exact PASS:\n{log[-3000:]}")
        rows, reads, sectors, cycles = map(int, m.groups())
        if (rows, reads, sectors) != (12, 36, 36):
            raise RuntimeError(f"{mode} wrong coverage: {(rows, reads, sectors)}")
        arms[mode] = {"exact_rows": rows, "weight_reads": reads,
                      "hbm_sectors": sectors, "cycles": cycles,
                      "log_sha256": hashlib.sha256(log.encode()).hexdigest()}
    rec = {"schema": "opentallas.rtl.hdc_v41x_me0_exact.v1", "status": "pass",
           "claim_boundary": "One real reduced L0.router operation: ME bank 0 in timed HBM, remaining seven ME banks in ROM. No complete token, contention with QE/KV/index, or chip throughput claim.",
           "source_commit": call(["git", "rev-parse", "HEAD"]).strip(),
           "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
           "image_sha256": {"mbank.hex": sha(args.mbank),
                            **{name: sha(args.scratch / name) for name in ("x.hex", "y.hex", "mbank_slice.hex", "fixture.json")}},
           "arms": arms}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(arms))


if __name__ == "__main__":
    main()

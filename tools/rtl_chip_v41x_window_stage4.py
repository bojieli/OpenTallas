"""Source-pinned four-bank packed-window SRAM read gate (preloaded rows only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ROOT / "rtl/chip/ot_chip_v41x_window_stage4.sv",
    ROOT / "rtl/test/tb_chip_v41x_window_stage4.sv",
    ROOT / "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
    ROOT / "rtl/chip/ot_chip_v41x_window_row_codec.sv",
    ROOT / "rtl/test/tb_chip_v41x_window_banked_prefetch.sv",
    Path(__file__),
)
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="v41_window_stage4_") as name:
        image = Path(name) / "stage4.vvp"
        build = subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_window_stage4",
             "-o", str(image), *map(str, SOURCES[:2])],
            cwd=ROOT, capture_output=True, text=True, check=False)
        sim = subprocess.run(["vvp", str(image)], cwd=ROOT, capture_output=True,
                             text=True, check=False) if build.returncode == 0 else None
        integrated_image = Path(name) / "banked.vvp"
        integrated_build = subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_window_banked_prefetch",
             "-o", str(integrated_image), *map(str, (SOURCES[0], *SOURCES[2:5]))],
            cwd=ROOT, capture_output=True, text=True, check=False)
        integrated_sim = subprocess.run(
            ["vvp", str(integrated_image)], cwd=ROOT, capture_output=True,
            text=True, check=False) if integrated_build.returncode == 0 else None
    lint = subprocess.run(
        [str(VERILATOR), "--lint-only", "-Wall", "-Wno-UNUSED",
         "--top-module", "ot_chip_v41x_window_stage4", str(SOURCES[0])],
        cwd=ROOT, capture_output=True, text=True, check=False)
    stdout = sim.stdout if sim else ""
    integrated_stdout = integrated_sim.stdout if integrated_sim else ""
    match = re.search(r"WINDOW_STAGE4_PASS requests=(\d+) rows=(\d+) "
                      r"peak_rows_per_cycle=(\d+) users=(\d+) wrap=(\d+)", stdout)
    return {
        "claim": "Preloaded packed-window stage reads four exact rows per clock after the local bank-read pipeline; integrated HBM refill preserves exact rows and rejects poison. Full attention rate is not measured",
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCES},
        "iverilog_version": subprocess.run(["iverilog", "-V"], capture_output=True,
                                          text=True, check=False).stdout.splitlines()[0],
        "verilator_version": subprocess.run([str(VERILATOR), "--version"],
                                            capture_output=True, text=True,
                                            check=False).stdout.strip(),
        "build_returncode": build.returncode,
        "simulation_returncode": sim.returncode if sim else None,
        "lint_returncode": lint.returncode,
        "stdout": stdout.strip(),
        "integrated_stdout": integrated_stdout.strip(),
        "integrated_build_returncode": integrated_build.returncode,
        "integrated_simulation_returncode": integrated_sim.returncode if integrated_sim else None,
        "diagnostics": (build.stderr + (sim.stderr if sim else "") +
                        integrated_build.stderr + (integrated_sim.stderr if integrated_sim else "") +
                        lint.stderr).strip(),
        "requests": int(match.group(1)) if match else 0,
        "staged_rows": int(match.group(2)) if match else 0,
        "peak_rows_per_cycle": int(match.group(3)) if match else 0,
        "users": int(match.group(4)) if match else 0,
        "wrap": int(match.group(5)) if match else 0,
        "pass": bool(match) and build.returncode == 0 and sim is not None and
                sim.returncode == 0 and lint.returncode == 0 and
                integrated_build.returncode == 0 and integrated_sim is not None and
                integrated_sim.returncode == 0 and
                "WINDOW_BANKED_PREFETCH_PASS fetched=4 sectors=68 rows_per_beat=4 users=2 poison=2" in integrated_stdout and
                tuple(map(int, match.groups())) == (8, 7, 4, 2, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/rtl/chip_v41x_window_stage4.json")
    args = parser.parse_args()
    record = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"window stage4: {'PASS' if record['pass'] else 'FAIL'}; {args.output}")
    if not record["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

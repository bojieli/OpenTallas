"""Source-pinned boundary gate for absolute HBM and local KVT window rows."""

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
    ROOT / "rtl/chip/ot_chip_v41x_window_block_guard.sv",
    ROOT / "rtl/test/tb_chip_v41x_window_block_guard.sv",
    Path(__file__),
)
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="v41_window_block_guard_") as name:
        image = Path(name) / "guard.vvp"
        build = subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_window_block_guard",
             "-o", str(image), *map(str, SOURCES[:2])],
            capture_output=True, text=True, cwd=ROOT, check=False)
        sim = subprocess.run(["vvp", str(image)], capture_output=True, text=True,
                             cwd=ROOT, check=False) if build.returncode == 0 else None
    lint = subprocess.run(
        [str(VERILATOR), "--lint-only", "-Wall", "-Wno-UNUSED", "--top-module",
         "ot_chip_v41x_window_block_guard", str(SOURCES[0])],
        capture_output=True, text=True, cwd=ROOT, check=False)
    stdout = sim.stdout if sim else ""
    count = re.search(r"WINDOW_BLOCK_GUARD_PASS cases=(\d+)", stdout)
    return {
        "claim": "absolute HBM row and local KVT alias guard at 127/128/129 and ring wraps",
        "sources_sha256": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
        "iverilog_version": subprocess.run(["iverilog", "-V"], capture_output=True,
                                          text=True, check=False).stdout.splitlines()[0],
        "verilator_version": subprocess.run([str(VERILATOR), "--version"],
                                            capture_output=True, text=True,
                                            check=False).stdout.strip(),
        "build_returncode": build.returncode,
        "simulation_returncode": sim.returncode if sim else None,
        "simulation_stdout": stdout.strip(),
        "lint_returncode": lint.returncode,
        "diagnostics": (build.stderr + (sim.stderr if sim else "") + lint.stderr).strip(),
        "cases": int(count.group(1)) if count else 0,
        "pass": build.returncode == 0 and sim is not None and sim.returncode == 0
                and lint.returncode == 0 and count is not None and int(count.group(1)) == 135,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/rtl/chip_v41x_window_block_guard.json")
    args = parser.parse_args()
    record = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"window block guard: {'PASS' if record['pass'] else 'FAIL'}; {args.output}")
    if not record["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

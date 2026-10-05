#!/usr/bin/env python3
"""Exercise G2 runtime wiring at the adapter boundary, with real service/LQ8."""

from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/g2_runtime_boundary"
OUT.mkdir(parents=True, exist_ok=True)
packages = [
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
]
sources = packages + [
    "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv",
    "rtl/abi3/ot_a3_g2_cluster.sv",
    "rtl/test/tb_a3_g2_runtime_boundary.sv",
]
# Include hashes of library-resolved dependencies; logs identify elaborated design.
tracked = sorted(
    set(
        sources
        + [
            str(p.relative_to(ROOT))
            for d in ["rtl/abi3", "rtl/proto"]
            for p in (ROOT / d).glob("*.sv")
        ]
    )
)
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
cmd = [
    str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"),
    "--binary",
    "--timing",
    "-Wno-fatal",
    "-DOT_A3_FAKERAM_BEHAVIOURAL",
    "--top-module",
    "tb_a3_g2_runtime_boundary",
    "--Mdir",
    str(OUT / "obj"),
    "-o",
    "sim",
    "-y",
    str(ROOT / "rtl/abi3"),
    "-y",
    str(ROOT / "rtl"),
    "-y",
    str(ROOT / "rtl/proto"),
    *[str(ROOT / p) for p in sources],
]
with (OUT / "compile.log").open("w") as log:
    subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
r = subprocess.run([str(OUT / "obj/sim")], capture_output=True, text=True, timeout=120)
(OUT / "simulation.log").write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stdout + r.stderr
assert "PASS G2 runtime boundary" in r.stdout
for p, h in hashes.items():
    assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
result = {
    "status": "pass",
    "scope": "Actual G2 runtime generate branch, adapter outputs forced. Not program/descriptor dispatch qualification or physical closure. Behavioral SRAM and external services.",
    "sources": hashes,
    "command": cmd,
    "stdout": r.stdout,
}
(ROOT / "results/rtl/a3_g2_runtime_boundary.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(r.stdout)

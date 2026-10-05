#!/usr/bin/env python3
"""Exercise the production-tagged X_SU coefficient mux on checkpoint arithmetic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from rtl_v41x_rope_hbm_cache import emit_fixture  # noqa: E402

RTL = ROOT / "rtl/chip/ot_chip_v41x_rope_su_word.sv"
TB = ROOT / "rtl/test/tb_chip_v41x_rope_su_word.sv"
OUT = ROOT / "results/rtl/v41x_rope_su_word.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap() -> None:
    n = 8 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (n, n))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41_rope_su_word_") as td:
        temp = Path(td)
        fixtures = emit_fixture(temp)
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        cmd = [verilator, "--binary", "--timing", "-O0", "-Wno-fatal", "-Wno-TIMESCALEMOD",
               "--top-module", "tb_chip_v41x_rope_su_word", "-Mdir", str(temp / "obj"),
               str(RTL), str(TB), "-CFLAGS", "-O0", "-j", "4"]
        build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               timeout=180, preexec_fn=cap)
        if build.returncode:
            raise RuntimeError("build failed:\n" + build.stderr[-3000:])
        sim = subprocess.run([str(temp / "obj/Vtb_chip_v41x_rope_su_word"), f"+DIR={temp}"],
                             cwd=ROOT, capture_output=True, text=True,
                             timeout=60, preexec_fn=cap)
        match = re.search(r"ROPE_SU_WORD_PASS checks=(\d+)", sim.stdout)
        if sim.returncode or not match or int(match.group(1)) != 197:
            raise RuntimeError("simulation failed:\n" + sim.stdout[-3000:] + sim.stderr[-1000:])
    record = {
        "schema": "opentallas.rtl.v41x_rope_su_word.v1",
        "status": "pass",
        "claim_scope": "Tagged X_SU CLO/CHI cache-word selection with real 200K plain/YaRN and 1M plain coefficients; ordinary CROM bypass and stale/mismatched-cache fault. Core control and die HBM arbitration are outside this gate.",
        "checks": int(match.group(1)),
        "fixtures": fixtures,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          (RTL, TB, Path(__file__), ROOT / "tools/rtl_v41x_rope_hbm_cache.py",
                           ROOT / "tools/hdc_golden_v41.py",
                           ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json")},
    }
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "checks": record["checks"]}))


if __name__ == "__main__":
    main()

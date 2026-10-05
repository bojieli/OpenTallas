#!/usr/bin/env python3
"""Maximum full-shape ME/HE activation-depth and bank-address RTL gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/v41/ot_hdc_actquant.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv", "rtl/hdc/v41x/ot_hdc_v41x_hcp.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv")]
TB = ROOT / "rtl/test/tb_hdc_v41x_fullshape_depths.sv"
OUT = ROOT / "results/rtl/hdc_v41x_fullshape_depth_gate.json"
PATTERN = re.compile(r"PASS fullshape depths me_k=(\d+) he_k=(\d+) me_reads=(\d+) he_reads=(\d+) "
                     r"max_me_addr=(\d+) max_he_addr=(\d+) cycles=(\d+)")


def _cap():
    limit = 24 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def run(output: Path = OUT):
    with tempfile.TemporaryDirectory(prefix="v41_fullshape_depth_") as temp:
        obj = Path(temp) / "obj"
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        command = [verilator, "--binary", "--timing", "-O0", "-Wno-fatal", "-Wno-WIDTH",
                   "-Wno-UNUSED", "-Wno-TIMESCALEMOD", "--top-module",
                   "tb_hdc_v41x_fullshape_depths", "-Mdir", str(obj),
                   *map(str, RTL + [TB]), "-CFLAGS", "-O0", "-j", "4"]
        start = time.monotonic()
        build = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               timeout=600, preexec_fn=_cap)
        if build.returncode:
            raise RuntimeError("depth gate build failed: " + build.stderr[-2000:])
        build_seconds = round(time.monotonic() - start, 2)
        sim = subprocess.run([str(obj / "Vtb_hdc_v41x_fullshape_depths")], cwd=ROOT,
                             capture_output=True, text=True, timeout=60, preexec_fn=_cap)
        match = PATTERN.search(sim.stdout)
        if sim.returncode or not match:
            raise RuntimeError("depth gate simulation failed: " + sim.stdout[-1200:] + sim.stderr[-1000:])
        kme, khe, mre, hre, maddr, haddr, cycles = map(int, match.groups())
        if (kme, khe, mre, hre, maddr, haddr) != (5120, 2560, 640, 2560, 131179, 10319):
            raise RuntimeError("depth gate coverage mismatch: " + match.group(0))
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in RTL + [TB, Path(__file__), ROOT / "rtl/hdc/v41x/ot_hdc_core_v41x.sv"]}
    record = {"schema": "opentallas.rtl.v41x_fullshape_depth_gate.v1", "status": "pass",
              "claim_scope": "ME K=5120 and HE he_k=2560 adapter maximum-depth zero-weight gate, "
                             "including 18-bit ME bank address above 2^17. No checkpoint-backed "
                             "arithmetic, full layer, P&R timing, or token-rate claim.",
              "me_k": kme, "he_k": khe, "me_bank_reads": mre, "he_bank_reads": hre,
              "max_me_bank_address": maddr, "max_he_bank_address": haddr,
              "simulation_cycles": cycles, "build_seconds": build_seconds,
              "memory_cap_bytes": 24 * 1024**3, "source_sha256": pins}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

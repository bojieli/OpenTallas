#!/usr/bin/env python3
"""Exact reduced ME adapter regression with the banked activation store enabled."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = [
    ROOT / "rtl/hdc/ot_hdc_fastfp.sv",
    ROOT / "rtl/hdc/ot_hdc_delay.sv",
    ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv",
    *[ROOT / f"rtl/hdc/v41x/ot_hdc_v41x_wgt_{x}.sv" for x in ("bdot","red","mac","tile")],
    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_xbank.sv",
    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv",
    ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv",
    ROOT / "rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv",
    ROOT / "rtl/test/tb_hdc_v41x_me0_exact.sv",
]
OTHER = [ROOT / "tools/v41x_me0_exact_fixture.py", ROOT / "tools/hdc_program_v41.py",
         ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py",
         ROOT / "tools/hdc_images_v41x.py", Path(__file__).resolve()]
PASS = re.compile(r"ME0_PASS exact_rows=(\d+) rom_reads=(\d+) hbm_sectors=(\d+) cycles=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def call(cmd: list[str]) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd[:2])} failed: {r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mbank", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/v41_me_xbank_integration"))
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/v41x_me_xbank_reduced_exact.json")
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    call([sys.executable, str(ROOT / "tools/v41x_me0_exact_fixture.py"),
          "--out",str(a.scratch),"--mbank",str(a.mbank)])
    exe = a.scratch / "tb_xbank.vvp"
    call(["iverilog","-g2012","-s","tb_hdc_v41x_me0_exact",
          "-Ptb_hdc_v41x_me0_exact.XBANK=1","-o",str(exe),*map(str,RTL)])
    arms = {}
    for mode,extra in (("rom",["+ROM_ONLY"]),("hbm",[])):
        log = call(["vvp",str(exe),f"+DIR={a.scratch}",*extra])
        m = PASS.search(log)
        if not m or tuple(map(int,m.groups())) != (12,36,36,211):
            raise RuntimeError(f"{mode} unexpected exact result: {log[-2000:]}")
        arms[mode] = {"exact_rows":12,"weight_reads":36,"hbm_sectors":36,
                      "cycles":211,"log_sha256":hashlib.sha256(log.encode()).hexdigest()}
    record = {
        "schema":"opentallas.rtl.v41x.me-xbank-reduced-exact.v1",
        "status":"pass",
        "scope":"one reduced real L0.router ME op with banked activation memory; ROM and timed HBM weight bank0; not full-shape or chip throughput",
        "configuration":{"XBANK":1,"KMAX":512,"MG":8,"G":4,"RL":2},
        "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in RTL+OTHER},
        "fixture_sha256":{name:sha(a.scratch/name) for name in ("x.hex","y.hex","mbank_slice.hex","fixture.json")},
        "mbank_sha256":sha(a.mbank),"arms":arms,
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(f"wrote {a.output}: banked ROM/HBM exact at 211 cycles")


if __name__ == "__main__":
    main()

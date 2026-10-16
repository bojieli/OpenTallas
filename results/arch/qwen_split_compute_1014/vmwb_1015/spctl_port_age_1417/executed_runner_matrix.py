#!/usr/bin/env python3
"""Gate fixed port-to-controller argmax ages at the full TP8 shape.

The real shared controller is extracted by module name, with retained exact
component dependencies. External p_am stimulus is delayed four edges; no port
arithmetic or whole-head qualification is implied.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out")
    ap.add_argument("--exclude-local-positive", action="store_true")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    inputs = ["rtl/hdc/ot_qwen_me_spine_h_w12.sv", "tools/qwen_producer_train/component_sources.sv",
              "tools/qwen_vmwb/tb_spctl_port_age.sv", "tools/qwen_vmwb/run_spctl_port_age.py"]
    pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs}
    pattern = r"(?ms)^module ot_qwen_me_spctl_w12\b.*?\bendmodule"
    controller = re.search(pattern, (ROOT / inputs[0]).read_text()).group(0)
    source, count = re.subn(pattern, lambda _: controller, (ROOT / inputs[1]).read_text())
    assert count == 1
    extracted = out / "executed_component.sv"
    extracted.write_text(source)
    pins["executed_component.sv"] = hashlib.sha256(extracted.read_bytes()).hexdigest()
    (out / "source_pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    variants = [(extra, ami, rmax) for extra in (3, 4, 5) for ami in (0, 1) for rmax in (0, 1)]
    if a.exclude_local_positive:
        variants.remove((4, 1, 0))
    vl = os.environ.get("VL", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))

    def run(variant):
        extra, ami, rmax = variant
        name = f"e{extra}_ami{ami}_rmax{rmax}"
        obj = out / name
        command = [vl, "--binary", "--timing", "-j", "4", "-O1", "-Wno-fatal", "-Wno-WIDTH",
                   "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--top-module", "tb_spctl_port_age",
                   "--Mdir", str(obj), f"-GEXTRA={extra}", f"-GAMI={ami}", f"-GRMAX={rmax}",
                   str(ROOT / inputs[2]), str(extracted)]
        with (out / (name + ".build.log")).open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            return dict(name=name, build_rc=result.returncode, ok=False)
        binary = obj / "Vtb_spctl_port_age"
        result = subprocess.run([str(binary)], capture_output=True, text=True)
        (out / (name + ".log")).write_text(result.stdout + result.stderr)
        passed = "SPCTL_PORT_AGE PASS" in result.stdout and result.returncode == 0
        observed = re.search(r"SPCTL_PORT_AGE extra=(\d+) ami=(\d+) rmax=(\d+) updates=(\d+) writes=(\d+) errors=(\d+)", result.stdout)
        ok = observed is not None and passed == (extra == 4)
        return dict(name=name, build_rc=0, run_rc=result.returncode, observed=observed.group(0) if observed else None,
                    binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), ok=ok)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(run, variants))
    receipt = dict(scope=__doc__, source_pins=pins, runs=runs, ok=all(run["ok"] for run in runs))
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["runs"], indent=2), flush=True)
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

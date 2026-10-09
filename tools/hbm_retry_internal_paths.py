#!/usr/bin/env python3
"""Diagnose internal paths using the existing source-pinned corner STA scenes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--orfs", required=True)
p.add_argument("--source", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
orfs, src, out = map(Path, (a.orfs, a.source, a.out))
out.mkdir(parents=True, exist_ok=False)
receipts = {}
for corner in ("tt", "ss", "ff"):
    original = orfs / f"w18_sta_{corner}.tcl"
    text = original.read_text()
    check = "min" if corner == "ff" else "max"
    report = f"""puts \"INTERNAL_PATH_DIAGNOSTIC {corner}\"
report_checks -path_delay {check} -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -format full_clock_expanded
"""
    diagnostic = orfs / f"retry_internal_{corner}.tcl"
    diagnostic.write_text(text.rsplit("exit", 1)[0] + report + "exit\n")
    cmd = ["/usr/bin/time", "-v", "docker", "run", "--rm", "-v", f"{orfs}:/work",
           "-v", f"{src}:/src:ro", "openroad/orfs:asap7lock", "bash", "-lc",
           f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/{diagnostic.name}"]
    with (out / f"internal_{corner}.log").open("w") as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    receipts[corner] = {"rc": rc, "original_tcl_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                        "diagnostic_tcl_sha256": hashlib.sha256(diagnostic.read_bytes()).hexdigest()}
    (out / diagnostic.name).write_bytes(diagnostic.read_bytes())
(out / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")

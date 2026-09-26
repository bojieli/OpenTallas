#!/usr/bin/env python3
"""Show that the routed ot_host_if revision and the current one are the same
circuit in the routed configuration (MODE=0).

results/physical_abi3/asap7/host/ot_host_if/physical.json routes the revision
of rtl/host/ot_host_if.sv at commit ROUTED_COMMIT.  Later edits touched only
MODE=1 (ROM-array batch) logic, which a MODE=0 elaboration removes.  This tool
synthesizes both revisions with Yosys at MODE=0 (generic cells, flattened,
unattributed netlist) and compares the netlists byte for byte.  Writes
results/physical_abi3/asap7/host/ot_host_if/routed_revision_identity.json.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "rtl/host/ot_host_if.sv"
PHYS = ROOT / "results/physical_abi3/asap7/host/ot_host_if"
ROUTED_COMMIT = "a8186d18"


def netlist(src: Path, out: Path) -> str:
    script = (f"read_verilog -sv {src}\nchparam -set MODE 0 ot_host_if\nsynth -top ot_host_if -flatten\n"
              f"opt_clean -purge\nwrite_verilog -noattr {out}\n")
    subprocess.run(["yosys", "-q", "-p", script.replace("\n", "; ")], check=True, capture_output=True)
    return hashlib.sha256(out.read_bytes()).hexdigest()


def main() -> int:
    phys = json.loads((PHYS / "physical.json").read_text())
    routed_sha = phys["design"]["sources"][0]["sha256"]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        old = d / "routed.sv"
        old.write_bytes(subprocess.run(["git", "show", f"{ROUTED_COMMIT}:{SRC}"], cwd=ROOT, check=True,
                                       capture_output=True).stdout)
        assert hashlib.sha256(old.read_bytes()).hexdigest() == routed_sha, "commit does not hold the routed source"
        a = netlist(old, d / "a.v")
        b = netlist(ROOT / SRC, d / "b.v")
    ver = subprocess.run(["yosys", "-V"], capture_output=True, text=True).stdout.strip()
    rec = {"schema": "opentallas.routed-revision-identity.v1", "top": "ot_host_if", "parameters": {"MODE": 0},
           "routed_commit": ROUTED_COMMIT, "routed_source_sha256": routed_sha,
           "current_source_sha256": hashlib.sha256((ROOT / SRC).read_bytes()).hexdigest(),
           "method": "yosys synth -flatten, opt_clean -purge, write_verilog -noattr; byte comparison",
           "yosys": ver, "routed_netlist_sha256": a, "current_netlist_sha256": b, "identical": a == b}
    (PHYS / "routed_revision_identity.json").write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print("identical" if a == b else "DIFFERENT", a, b)
    return 0 if a == b else 1


if __name__ == "__main__":
    raise SystemExit(main())

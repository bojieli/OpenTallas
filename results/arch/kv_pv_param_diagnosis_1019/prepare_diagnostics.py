#!/usr/bin/env python3
"""Prepare PV proof diagnostics from exact original audit files; no production changes.

Run this only on the fleet, then run each generated Yosys script via ot-run.
The original source, native cells, parameters, ports, and 911 comparisons stay intact.
The five optional extra observations are zero invariants, not assumptions.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("original", type=Path)
    ap.add_argument("destination", type=Path)
    a = ap.parse_args()
    a.destination.mkdir(parents=True, exist_ok=True)
    names = ("cells.v", "gate.v", "gold1.il", "equiv.ys")
    hashes = {}
    for name in names:
        source = a.original / name
        hashes[name] = digest(source)
        (a.destination / name).write_bytes(source.read_bytes())
    original = (a.original / "equiv.ys").read_text()
    for label, passes in (("opt", "opt"), ("width_opt", "opt\nwreduce\nopt")):
        transformed = original.replace(
            "read_rtlil gold1.il\ncd gold",
            "read_rtlil gold1.il\ncd gold\n" + passes + "\ncd\ncd gold",
        )
        assert transformed != original
        (a.destination / f"equiv_{label}.ys").write_text(transformed)

    # Source state[3] and the four request nq low bits have reset value zero,
    # and every source transition from zero preserves zero. They have no routed
    # flop counterpart. Adding comparisons makes their invariants visible to
    # induction while keeping every original observable comparison.
    invariants = [("state3_zero", "u_ot_pr_core.state[3]")] + [
        (f"request_nq{i}_zero", f"u_ot_pr_core.u_req.nq[{i}]") for i in range(4)
    ]
    gold = "\n".join(
        f"add -wire S__proof_only_{name} 1\nconnect -set S__proof_only_{name} {signal}"
        for name, signal in invariants
    )
    gate = "cd gate\n" + "\n".join(
        f"add -wire S__proof_only_{name} 1\nconnect -set S__proof_only_{name} 1'0"
        for name, _ in invariants
    ) + "\ncd\n"
    observed = original.replace("read_rtlil gold1.il\ncd gold", "read_rtlil gold1.il\ncd gold\n" + gold)
    observed = observed.replace("setattr -set keep 1 w:S__*", gate + "setattr -set keep 1 w:S__*")
    (a.destination / "equiv_invariants.ys").write_text(observed)

    # This is a finite diagnostic base check, not an unbounded qualification.
    for label, script in (("original", original), ("invariants", observed)):
        miter = script.split("equiv_simple -seq")[0]
        miter += "equiv_miter -assert miter\nhierarchy -top miter\nflatten\nopt_clean\n"
        miter += "sat -seq 12 -prove-asserts -prove-skip 6 -set-def-inputs "
        miter += " ".join(f"-set-at {i} rst_n 0" for i in range(1, 7))
        miter += f" -show-inputs -show-outputs -dump_json bmc12_{label}_cex.json -verify\n"
        (a.destination / f"reset_bmc12_{label}.ys").write_text(miter)
    (a.destination / "input_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")


if __name__ == "__main__":
    main()

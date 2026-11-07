#!/usr/bin/env python3
"""Prepare the writer-chunk bench from pinned baseline bytes and candidate RTL.

Use --repo only with a clone/worktree you own. Alternatively --baseline-root
reads a source export without invoking git. No source file is modified.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess

PIN = "93c061c396c"
FILES = {
    "ot_dp_clk_landing_ca.sv": "8be032d56899a5f1fdbd4f413e44fc16540c9620fe3a91c934f3fd74511c8f76",
    "ot_meso_fifo.sv": "72750a546e10260ec6fa1e8ec69f34ae29302c5362eb3baa4df72bf28bd29396",
    "ot_dp_clk_landing.sv": "2f223b19bc4d65333738a9bf6f7df2829618b60c110003b763eb01f7b99b5d2c",
}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo", type=Path, help="your own git clone containing baseline ref")
    src.add_argument("--baseline-root", type=Path, help="source export with rtl/common at pinned bytes")
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rtl = a.out / "rtl"
    rtl.mkdir(exist_ok=True)
    baseline = {}
    for name, digest in FILES.items():
        rel = "rtl/common/" + name
        data = ((a.baseline_root / rel).read_bytes() if a.baseline_root else
                subprocess.check_output(["git", "-C", str(a.repo), "show", PIN + ":" + rel]))
        actual = hashlib.sha256(data).hexdigest()
        if actual != digest:
            raise SystemExit(f"baseline {rel}: sha256 {actual} != pinned {digest}")
        baseline[name] = data
        if name != "ot_dp_clk_landing_ca.sv":
            (rtl / name).write_bytes(data)
    body = baseline["ot_dp_clk_landing_ca.sv"].decode()
    names = re.findall(r"^module\s+(\w+)", body, re.M)
    for name in sorted(names, key=len, reverse=True):
        body = re.sub(r"\b" + re.escape(name) + r"\b", name + "_ref", body)
    body = body.replace("OT_MESO_CA_MUTANT_", "OT_MESO_CA_REFERENCE_DISABLED_MUTANT_")
    (rtl / "ca_reference.sv").write_text(body)
    candidate = a.candidate.read_bytes()
    # Read before writing: passing out/patched_ca.sv itself is supported.
    (a.out / "patched_ca.sv").write_bytes(candidate)
    print(f"Prepared reference {PIN}, {len(names)} renamed modules; candidate sha256 "
          + hashlib.sha256(candidate).hexdigest())

if __name__ == "__main__":
    main()

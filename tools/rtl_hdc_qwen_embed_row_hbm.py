#!/usr/bin/env python3
"""Source-pinned reduced embedding row/scale HBM sector gate."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/hbm/ot_hdc_qwen_embed_row_hbm.sv",
    "rtl/test/tb_hdc_qwen_embed_row_hbm.sv",
    "tools/rtl_hdc_qwen_embed_row_hbm.py",
)]
OUT = ROOT / "results/rtl/qwen_embed_row_hbm.json"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen_embed_row_hbm_") as tmp:
        binary = Path(tmp) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_embed_row_hbm",
                        "-o", str(binary), str(SOURCES[0]), str(SOURCES[1])],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        run = subprocess.run(["vvp", str(binary)], cwd=ROOT, check=True,
                             capture_output=True, text=True)
    assert "PASS Qwen embedding HBM row: token 3, 5 sectors" in run.stdout
    record = {
        "schema": "opentallas.qwen-embed-row-hbm.v1",
        "status": "pass",
        "observed": {"token": 3, "sectors": 5, "code_words": 2,
                     "scale_words": 1},
        "claim_boundary": "Reduced 128-code row, one BF16 scale, exact synchronous core read ports. HBM controller, package-level token exactness, full Qwen embedding and route are separate gates.",
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCES},
        "stdout": run.stdout.strip(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"{OUT}: pass")


if __name__ == "__main__":
    main()

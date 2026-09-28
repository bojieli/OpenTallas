"""Source-pinned exact selected compressed-KV row DMA gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FILES = (
    "rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv",
    "rtl/chip/ot_chip_v41x_ckv_selected_dma.sv",
    "rtl/test/tb_chip_v41x_ckv_selected_dma.sv",
    "runtime/prefill/v41_main_kv_row.py",
    "runtime/reference/fp4_kv.py",
    "runtime/reference/formats.py",
    "tools/gen_v41_ckv_decode.py",
    "tools/gen_v41_ckv_selected_vectors.py",
    "tools/rtl_v41_ckv_selected_campaign.py",
    "tests/fixtures/v41_ckv_selected/sectors.hex",
    "tests/fixtures/v41_ckv_selected/expected_fp8.hex",
    "tests/fixtures/v41_ckv_selected/expected_fp32.hex",
    "tests/test_v41_ckv_selected_dma.py",
    "docs/V41X_SELECTED_CKV_DMA.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    from tools.gen_v41_ckv_decode import generate as decoder
    from tools.gen_v41_ckv_selected_vectors import generate as vectors

    assert (ROOT / FILES[0]).read_text() == decoder(), "FP4 decode table is stale"
    sectors, fp8, fp32 = vectors()
    fix = ROOT / "tests/fixtures/v41_ckv_selected"
    assert (fix / "sectors.hex").read_text() == sectors, "sector fixture is stale"
    assert (fix / "expected_fp8.hex").read_text() == fp8, "FP8 fixture is stale"
    assert (fix / "expected_fp32.hex").read_text() == fp32, "FP32 fixture is stale"
    with tempfile.TemporaryDirectory(prefix="v41_ckv_selected_") as tmp:
        executable = str(Path(tmp) / "sim")
        compile_cmd = [
            "iverilog", "-g2012", "-s", "tb_chip_v41x_ckv_selected_dma",
            "-o", executable, *(str(ROOT / f) for f in FILES[:3]),
        ]
        subprocess.run(compile_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
        proc = subprocess.run(["vvp", executable], cwd=ROOT, check=True,
                              capture_output=True, text=True, timeout=60)
    assert "PASS" in proc.stdout and "FAIL" not in proc.stdout, proc.stdout
    assert "rows=2 sectors=26 checked=1024 fault=5 errors=0" in proc.stdout, proc.stdout
    return {
        "status": "pass_standalone_reduced_gate",
        "scope": "two 512-element selected CKV source rows, 9 sectors/row; no die integration or throughput claim",
        "contract": "opentallas.deepseek_v41.main_fp4_e2m1_s16_e4m3.row.v1",
        "rows_exact": 2,
        "elements_exact_fp8_and_fp32": 1024,
        "valid_hbm_sectors_read": 18,
        "additional_poison_probe_sectors": 8,
        "unpublished_source_rejected": True,
        "window_local_row_rejected": True,
        "nonfinite_scale_rejected": True,
        "source_pins": {f: sha(ROOT / f) for f in FILES},
        "sim_stdout": proc.stdout.strip(),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/rtl/v41x_ckv_selected_dma.json")
    args = p.parse_args()
    record = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(record["sim_stdout"])


if __name__ == "__main__":
    main()

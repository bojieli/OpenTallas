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
    "rtl/test/tb_chip_v41x_ckv_decode_exhaustive.sv",
    "runtime/prefill/v41_main_kv_row.py",
    "runtime/reference/fp4_kv.py",
    "runtime/reference/formats.py",
    "tools/gen_v41_ckv_decode.py",
    "tools/gen_v41_ckv_selected_vectors.py",
    "tools/rtl_v41_ckv_decode_synth.py",
    "tools/rtl_v41_ckv_selected_campaign.py",
    "tests/fixtures/v41_ckv_selected/sectors.hex",
    "tests/fixtures/v41_ckv_selected/expected_fp8.hex",
    "tests/fixtures/v41_ckv_selected/expected_fp32.hex",
    "tests/fixtures/v41_ckv_selected/decode_pairs.hex",
    "results/rtl/v41x_ckv_decode_synth.json",
    "tests/test_v41_ckv_selected_dma.py",
    "docs/V41X_SELECTED_CKV_DMA.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    from tools.gen_v41_ckv_decode import generate as decoder
    from tools.gen_v41_ckv_selected_vectors import generate as vectors

    assert (ROOT / "tests/fixtures/v41_ckv_selected/decode_pairs.hex").read_text() == decoder(), "FP4 decode truth fixture is stale"
    sectors, fp8, fp32 = vectors()
    fix = ROOT / "tests/fixtures/v41_ckv_selected"
    assert (fix / "sectors.hex").read_text() == sectors, "sector fixture is stale"
    assert (fix / "expected_fp8.hex").read_text() == fp8, "FP8 fixture is stale"
    assert (fix / "expected_fp32.hex").read_text() == fp32, "FP32 fixture is stale"
    synth = json.loads((ROOT / "results/rtl/v41x_ckv_decode_synth.json").read_text())
    assert synth["source_sha256"] == sha(ROOT / FILES[0]), "decoder synthesis source is stale"
    assert synth["script_sha256"] == sha(ROOT / "tools/rtl_v41_ckv_decode_synth.py"), "decoder synthesis script is stale"
    with tempfile.TemporaryDirectory(prefix="v41_ckv_selected_") as tmp:
        executable = str(Path(tmp) / "sim")
        compile_cmd = [
            "iverilog", "-g2012", "-s", "tb_chip_v41x_ckv_selected_dma",
            "-o", executable, *(str(ROOT / f) for f in FILES[:3]),
        ]
        subprocess.run(compile_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
        proc = subprocess.run(["vvp", executable], cwd=ROOT, check=True,
                              capture_output=True, text=True, timeout=60)
        exhaustive_exe = str(Path(tmp) / "decode")
        subprocess.run(["iverilog", "-g2012", "-s", "tb_chip_v41x_ckv_decode_exhaustive",
                        "-o", exhaustive_exe,
                        str(ROOT / FILES[0]), str(ROOT / FILES[3])],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        exact = subprocess.run(["vvp", exhaustive_exe], cwd=ROOT, check=True,
                               capture_output=True, text=True, timeout=60)
    assert "PASS" in proc.stdout and "FAIL" not in proc.stdout, proc.stdout
    assert "rows=2 sectors=26 checked=1024 fault=5 errors=0" in proc.stdout, proc.stdout
    assert "DECODE_EXHAUSTIVE checked=4096 errors=0" in exact.stdout, exact.stdout
    return {
        "status": "pass_standalone_reduced_gate",
        "scope": "two 512-element selected CKV rows on distinct stacks; remote-die fabric delivery, die integration and throughput remain open",
        "contract": "opentallas.deepseek_v41.main_fp4_e2m1_s16_e4m3.row.v1",
        "rows_exact": 2,
        "elements_exact_fp8_and_fp32": 1024,
        "decode_pairs_exhaustive": 4096,
        "valid_hbm_sectors_read": 18,
        "additional_poison_probe_sectors": 8,
        "unpublished_source_rejected": True,
        "window_local_row_rejected": True,
        "nonfinite_scale_rejected": True,
        "placement": "16-row groups striped over 4 dies x 4 stacks; owner die/stack and local row derived from global source ID",
        "remote_die_requires_fabric": True,
        "source_pins": {f: sha(ROOT / f) for f in FILES},
        "sim_stdout": proc.stdout.strip(),
        "decode_stdout": exact.stdout.strip(),
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

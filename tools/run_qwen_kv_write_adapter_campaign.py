"""Source-pinned SW8/SW16 Qwen KV write-adapter reduced RTL campaign."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv",
    "rtl/test/tb_hdc_qwen_kv_write_adapter.sv",
    "rtl/hdc/ot_hdc_core.sv",
    "rtl/hdc/ot_hdc_vstream.sv",
    "rtl/hdc/kv/ot_hdc_kv_stream.sv",
    "tools/hdc_program.py",
    "tools/qwen_kv_bank_prototype.py",
    "tests/test_qwen_kv_bank_prototype.py",
    "tools/run_qwen_kv_write_adapter_campaign.py",
    "tests/test_qwen_kv_write_adapter_record.py",
)
OUTPUT = ROOT / "results/rtl/qwen_kv_write_adapter_prototype.json"


def main() -> None:
    runs = {}
    with tempfile.TemporaryDirectory(prefix="qwen-kv-write-") as td:
        for sw in (8, 16):
            exe = Path(td) / f"kv{sw}.vvp"
            subprocess.run([
                "iverilog", "-g2012", "-s", "tb_hdc_qwen_kv_write_adapter",
                f"-Ptb_hdc_qwen_kv_write_adapter.SW={sw}", "-o", str(exe),
                *(str(ROOT / p) for p in SOURCES[:2]),
            ], check=True)
            out = subprocess.run(["vvp", str(exe)], check=True,
                                 capture_output=True, text=True).stdout.strip()
            assert out == f"PASS SW={sw}", out
            runs[str(sw)] = {"status": "pass", "stdout": out}
    rec = {
        "schema_version": 1,
        "status": "pass",
        "scope": "reduced functional adapter bench, not integrated Qwen token or physical closure",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "checks": ["K bank dispatch and new-tile zero mask", "V full 32-byte sector",
                   "partial-sector explicit read/modify/write", "ready/retire"],
        "runs": runs,
        "open_gates": ["vector-core numeric contract", "tail SRAM macro/BIST and read mux",
                       "finite-buffer throughput under arbitrary stalls", "tail flush scheduler",
                       "HBM read/write ordering", "full-context token campaign", "physical route"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(f"{OUTPUT.relative_to(ROOT)}: SW8/SW16 pass")


if __name__ == "__main__":
    main()

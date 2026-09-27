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
    "rtl/hdc/kv/ot_hdc_qwen_kv_tail_read_mux.sv",
    "rtl/test/tb_hdc_qwen_kv_tail_read_mux.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_tail_bank_port.sv",
    "rtl/test/tb_hdc_qwen_kv_tail_bank_port.sv",
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
            runs[str(sw)] = {}
            for kind, top, source_pair, expected in (
                ("write", "tb_hdc_qwen_kv_write_adapter", SOURCES[:2], f"PASS SW={sw}"),
                ("read", "tb_hdc_qwen_kv_tail_read_mux", SOURCES[2:4], f"PASS READ SW={sw}"),
                ("streamer_tail_port", "tb_hdc_qwen_kv_tail_bank_port", SOURCES[2:3] + SOURCES[4:6],
                 f"PASS TAIL_BANK_PORT SW={sw}"),
            ):
                exe = Path(td) / f"kv_{kind}{sw}.vvp"
                subprocess.run([
                    "iverilog", "-g2012", "-s", top,
                    f"-P{top}.SW={sw}", "-o", str(exe),
                    *(str(ROOT / p) for p in source_pair),
                ], check=True)
                out = subprocess.run(["vvp", str(exe)], check=True,
                                     capture_output=True, text=True).stdout.strip()
                assert out == expected, out
                runs[str(sw)][kind] = {"status": "pass", "stdout": out}
    rec = {
        "schema_version": 1,
        "status": "pass",
        "scope": "reduced functional adapter bench, not integrated Qwen token or physical closure",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "checks": ["K bank dispatch and new-tile zero mask", "two-parity one-cycle banked tail read",
                   "streamer compact tail row to vector bank and FP8-to-BF16 read port",
                   "V full 32-byte sector",
                   "partial-sector explicit read/modify/write", "ready/retire"],
        "runs": runs,
        "open_gates": ["vector-core numeric contract", "tail SRAM macro/BIST and read-before-write contract",
                       "finite-buffer throughput under arbitrary stalls", "tail flush scheduler",
                       "HBM read/write ordering", "full-context token campaign", "physical route"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(f"{OUTPUT.relative_to(ROOT)}: SW8/SW16 pass")


if __name__ == "__main__":
    main()

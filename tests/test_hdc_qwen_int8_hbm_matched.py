"""Keep the reduced same-program INT8 ROM/HBM verdict source-pinned."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_matched_verdict_and_current_sources():
    r = json.loads((ROOT / "results/rtl/qwen_int8_hbm_matched.json").read_text())
    assert r["status"] == "pass"
    assert r["rom_cycles"] == 281485
    assert r["hbm_cycles"] == 422093
    assert r["delta_cycles"] == r["hbm_cycles"] - r["rom_cycles"]
    assert r["rom"]["generated"] == r["hbm"]["generated"] == 1
    assert r["rom"]["steps_checked"] == r["hbm"]["steps_checked"] == 16
    for arm in ("rom", "hbm"):
        assert all(r[arm][k] == 0 for k in ("mismatches", "kv_mismatches", "vm_mismatches"))
    assert len(r["image_sha256"]) > 10
    traffic = r["embedding_hbm_traffic"]
    assert len(traffic) == 4
    assert sum(x["code_sectors"] for x in traffic) == 128
    assert sum(x["scale_sectors"] for x in traffic) == 32
    # This exact reduced replay belongs to its immutable source snapshot. The
    # merged full-shape core has changed since then; it needs a fresh RTL run
    # before the record can be described as current-source evidence.
    for name, digest in r["source_sha256"].items():
        source = subprocess.run(["git", "show", f"b849a7eb:{name}"], cwd=ROOT,
                                capture_output=True, check=True).stdout
        assert hashlib.sha256(source).hexdigest() == digest, name

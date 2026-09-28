"""Keep the reduced same-program INT8 ROM/HBM verdict source-pinned."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_matched_verdict_and_current_sources():
    r = json.loads((ROOT / "results/rtl/qwen_int8_hbm_matched.json").read_text())
    assert r["status"] == "pass"
    assert r["rom_cycles"] == 281485
    assert r["hbm_cycles"] == 421965
    assert r["delta_cycles"] == r["hbm_cycles"] - r["rom_cycles"]
    assert r["rom"]["generated"] == r["hbm"]["generated"] == 1
    assert r["rom"]["steps_checked"] == r["hbm"]["steps_checked"] == 16
    for arm in ("rom", "hbm"):
        assert all(r[arm][k] == 0 for k in ("mismatches", "kv_mismatches", "vm_mismatches"))
    assert len(r["image_sha256"]) > 10
    for name, digest in r["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name

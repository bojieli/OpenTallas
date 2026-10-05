"""tools/derive_hdc_common_kv_energy.py: the common-HBM-KV energy cross-check record."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("derive_hdc_common_kv_energy",
                                               ROOT / "tools/derive_hdc_common_kv_energy.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def test_committed_record_reproduces():
    assert M.OUT.read_text() == json.dumps(M.derive(), indent=2) + "\n"


def test_record_pins_its_source():
    rec = json.loads(M.OUT.read_text())
    assert rec["source_sha256"] == hashlib.sha256(M.SOURCE.read_bytes()).hexdigest()


def test_terms_sum_and_ratio():
    rec = M.derive()
    assert abs(sum(rec["terms_j"].values()) - rec["rom_common_hbm_kv_j"]) < 1e-15
    assert rec["hbm_over_rom"] == rec["hbm_comparator_j"] / rec["rom_common_hbm_kv_j"]
    # the KV swap moves the ROM step toward the comparator, never past it
    assert rec["terms_j"]["rom_original"] < rec["rom_common_hbm_kv_j"] < rec["hbm_comparator_j"]

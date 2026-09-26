"""DeepSeek-V4.1 ROM array: the layer-range split, what crosses a package
boundary, and the committed RTL record."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import hdc_program_v41_array as A  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not V.CHECKPOINT.exists(), reason="build the reduced V4.1 v2 fixture (tools/build_deepseek_v41_reduced_model.py)")
RECORD = ROOT / "results/rtl/hdc_v41_array_campaign.json"


_RATIO = [0, 0] + [2] * 18 + [1] * 20
_KV, _IDX = [2, 8, 14, 20], [2, 8, 14, 20, 24, 28, 32, 36]


class _M:
    """The reduced model's sharing structure, without its weights."""
    L = 40
    ratio = _RATIO
    kv_src, idx_src = _KV, _IDX
    kv_of = {L: max(s for s in _KV if s <= L) for L in range(40) if _RATIO[L]}
    idx_of = {L: max(s for s in _IDX if s <= L) for L in range(40) if _RATIO[L]}


def test_split_is_contiguous_and_complete():
    for n in (1, 2, 3, 4, 5, 8, 10, 40):
        parts = A.split(_M, n)
        assert len(parts) == n and all(parts)
        assert sum(parts, []) == list(range(40))


def test_shared_state_consumers():
    m = _M
    assert A.consumers(m, ("ckv", 20)) == list(range(20, 40))
    assert A.consumers(m, ("ik", 20)) == [24, 28, 32, 36]
    assert A.consumers(m, ("ik", 8)) == []                  # every ratio-2 indexer is its own source
    assert A.consumers(m, ("sel", 24)) == [25, 26, 27]
    assert A.consumers(m, ("sel", 2)) == [3, 4, 5, 6, 7]


def test_committed_record_passes_and_is_current():
    record = json.loads(RECORD.read_text())
    assert record["status"] == "pass"
    packages = set()
    full = [c for c in record["configurations"] if c["prompt_tokens"] == 8 and c["generated_tokens_per_user"] == 3]
    assert full and full[0]["golden_generated"][0] == [3118, 2400, 318]   # the single core's tokens
    for c in record["configurations"]:
        assert c["pass"], c["name"]
        gold = c["golden_generated"]
        assert all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in c["isa_pipeline"])
        for r in c["runs"]:
            assert r["pass"] and r["token_mismatches"] == 0 and r["logit_mismatches"] == 0
            assert r["state_mismatches"] == 0 and r["users_completed"] == r["users"]
            gen = {}
            for t in r["tokens"]:
                if t["position"] >= c["prompt_tokens"] - 1:
                    gen.setdefault(t["user"], []).append(t["token"])
            assert all(gen[u] == gold[u % 2] for u in gen) and len(gen) == r["users"]
            packages.add(r["packages"])
    assert max(packages) >= 4
    assert any(c["shared_state"] == "relay" for c in record["configurations"])
    wide = [c for c in record["configurations"] if c["body_packages"] >= 8]
    for c in wide:                                          # the 8-package multicast array, when recorded
        assert c["shared_state"] == "mcast" and c["lm_head_packages"] >= 2
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name

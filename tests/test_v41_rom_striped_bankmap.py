"""W10 item 1: row-striped V4.1 ROM bank map (tools/v41_rom_striped_bankmap.py)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_rom_striped_bankmap as S  # noqa: E402

SNAP = Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots" \
    / "dba1be0a40aa45a94ad051997016db3960a90277"
REC = ROOT / "results/uarch/v41_rom_striped_bankmap.json"


def _every_word_once(die, n):
    flat = []
    for b in die.bind:
        m, a = S.word_addresses(b)
        assert a.min() >= 0 and a.max() < S.DEPTH
        flat.append((m * S.DEPTH + a).ravel().astype(np.int32))
    flat = np.concatenate(flat)
    seen = np.bincount(flat, minlength=n * S.DEPTH)
    assert seen.max() == 1
    return int(flat.size)


def test_every_word_once_small_die():
    """Word-level bijection on a small die, including several rows of one tensor per macro (k-outer)."""
    n = 40
    die = S.Die(n, 8)
    mats = [dict(tensor="a", phase="a_proj", fmt="fp8", rows=50, K=320, words_per_row=10, split=""),
            dict(tensor="b", phase="a_proj", fmt="bf16", rows=20, K=160, words_per_row=10, split=""),
            dict(tensor="c", phase="wo_b", fmt="fp8", rows=7, K=64, words_per_row=2, split="")]
    loads = S.place_dense(die, mats)
    assert _every_word_once(die, n) == 50 * 10 + 20 * 10 + 7 * 2
    b = next(x for x in die.bind if x["tensor"] == "b")
    assert set(np.unique(b["macros"]).tolist()) <= set(die.bf.tolist())
    assert loads["a_proj"].max() == 30        # 20 BF16 rows over 8 macros -> 3 rows of 10 words
    tables = S.place_experts(die, [dict(layer=0, first=0, last=0)]) if n >= 1280 else None
    assert tables is None


@pytest.mark.skipif(not (SNAP / "model.safetensors.index.json").exists(), reason="checkpoint headers absent")
def test_busiest_die_binding_and_record():
    DIE = []
    dies, t_model = S.derive(SNAP, draws=1, seed=1, only=["layer_s01_r3"], keep=DIE)
    d = dies[0]
    assert d["macros"] == 13798 and d["bf16_macros"] == 4096 and d["capacity_ok"]
    assert _every_word_once(DIE[0], 13798) == d["weight_words"]
    rec = json.loads(REC.read_text())
    got = next(x for x in rec["dies"] if x["die"] == "layer_s01_r3")
    assert got["dense"] == d["dense"] and got["weight_words"] == d["weight_words"]
    assert rec["all_capacity_ok"]


@pytest.mark.xfail(strict=True, reason="W10 finding: whole-row ownership cannot reach the model's t_read "
                                       "(words / macros); see results/uarch/v41_rom_striped_bankmap.json")
def test_phase_read_cycles_equal_model():
    rec = json.loads(REC.read_text())
    assert all(r["equal"] for r in rec["phase_cycles_vs_model"].values())

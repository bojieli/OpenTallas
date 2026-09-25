"""4-die tensor-group package: golden, ISA group and the committed RTL record."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_program as P  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not G.CHECKPOINT.exists(), reason="build the reduced checkpoint: tools/build_qwen3_reduced_model.py")
RECORD = ROOT / "results/rtl/hdc_package_tp_campaign.json"


def test_fold_is_rank_order_left_to_right():
    p = [np.float32(1e8), np.float32(1.0), np.float32(-1e8), np.float32(1.0)]
    # ((1e8 + 1) + -1e8) + 1 = 1 (the 1 is absorbed), not the exact 2
    assert G.fold(p) == np.float32(1.0)


@needs_checkpoint
def test_tensor_split_golden_generates_the_oracle_tokens():
    model = G.Model(P.GR, 4)
    prompt, expected = G.prompt_and_expected()
    cache = [[] for _ in range(model.layers)]
    seq, gen = list(prompt), []
    for pos in range(len(prompt) + 2):
        lg = model.decode_token(seq[pos], pos, cache)
        if pos >= len(prompt) - 1:
            gen.append(int(np.argmax(lg)))
            seq.append(gen[-1])
    assert gen == list(expected[:3])


@needs_checkpoint
def test_isa_group_is_bit_exact_with_the_tensor_split_golden():
    model = G.Model(P.GR, 4)
    prompt, expected = G.prompt_and_expected()
    cache = [[] for _ in range(model.layers)]
    for pos, tok in enumerate(prompt[:-1]):
        model.decode_token(tok, pos, cache)
    lays = P.tp_layouts(model, 4)
    grp = P.TPGroup(lays, [l.kv_image(cache) for l in lays])
    got = grp.run([P.build_program(l) for l in lays], prompt[-1], len(prompt) - 1)
    ref = model.decode_token(prompt[-1], len(prompt) - 1, [list(c) for c in cache])
    assert got == expected[0]
    assert np.array_equal(G.bits(grp.logits()), G.bits(ref))


@needs_checkpoint
def test_segments_end_at_the_collectives():
    model = G.Model(P.GR, 4)
    lay = P.Layout(model, 4, 1)
    segs = P.segments(P.build_program(lay))
    kinds = [c[0] for _, c in segs]
    assert kinds == [P.COLL_ALLREDUCE] * 8 + [P.COLL_ARGMAX]
    assert segs[-1][1][3] == 1024                       # die 1's first vocabulary row


def test_committed_record_is_current_and_passes():
    record = json.loads(RECORD.read_text())
    assert record["status"] == "pass"
    for r in record["packages"]:
        assert r["pass"] and r["mismatches"] == 0 and r["kv_mismatches"] == 0
        assert r["steps_checked_bit_exact"] == 18 * r["users"]
        assert r["generated_ids_per_user"] == [[1073, 382, 93]]
    assert all(u["pass"] for u in record["one_shot_unit"])
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name

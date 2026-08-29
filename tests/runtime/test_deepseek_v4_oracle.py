"""Tests for the DeepSeek-V4-Flash reference oracle.

The tests are layered so that the parts which need neither the 156 GiB
checkpoint nor a GPU always run: the workload identities, the Hadamard
replacement, the head-split wrapper's structure and the report shape.  The
parts that do need the hardware are skipped rather than silently passed, so a
green run on a machine without the checkpoint never reads as evidence that the
oracle executed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.reference.deepseek_v4_oracle import (
    ADAPTATIONS,
    DEFAULT_SNAPSHOT,
    HADAMARD_WIDTH,
    SPARSE_ATTN_HEADS_PER_LAUNCH,
    VENDOR_SOURCE_SHA256,
    OracleError,
    make_head_split_sparse_attn,
    torch_hadamard_transform,
    verify_vendor_sources,
)

REPO = Path(__file__).resolve().parents[2]
WORKLOAD_DIR = REPO / "build" / "workloads" / "deepseek-v4-flash-0731"

torch = pytest.importorskip("torch")

snapshot_available = pytest.mark.skipif(
    not (DEFAULT_SNAPSHOT / "inference" / "model.py").exists(),
    reason="DeepSeek-V4-Flash snapshot is not present on this machine",
)
cuda_available = pytest.mark.skipif(
    not torch.cuda.is_available(), reason="no CUDA device"
)


# ---------------------------------------------------------------------------
# Hadamard replacement
# ---------------------------------------------------------------------------
def test_hadamard_matches_dense_sylvester_matrix() -> None:
    """The butterfly must equal an explicit Sylvester matrix product."""
    width = HADAMARD_WIDTH
    matrix = torch.ones(1, 1, dtype=torch.float32)
    while matrix.size(0) < width:
        matrix = torch.cat(
            (
                torch.cat((matrix, matrix), dim=1),
                torch.cat((matrix, -matrix), dim=1),
            ),
            dim=0,
        )
    generator = torch.Generator().manual_seed(4242)
    x = torch.randn(9, width, dtype=torch.float32, generator=generator).bfloat16()
    scale = width**-0.5
    expected = ((x.float() @ matrix.T) * scale).to(torch.bfloat16)
    got = torch_hadamard_transform(x, scale)
    assert torch.equal(got.view(torch.int16), expected.view(torch.int16))


def test_hadamard_preserves_shape_and_rejects_bad_input() -> None:
    x = torch.zeros(2, 3, 4, HADAMARD_WIDTH, dtype=torch.bfloat16)
    assert torch_hadamard_transform(x, 1.0).shape == x.shape
    with pytest.raises(OracleError):
        torch_hadamard_transform(torch.zeros(4, 128), 1.0)  # float32 input
    with pytest.raises(OracleError):
        torch_hadamard_transform(torch.zeros(4, 96, dtype=torch.bfloat16), 1.0)


def test_hadamard_matches_official_extension_when_available() -> None:
    fht = pytest.importorskip("fast_hadamard_transform")
    if not torch.cuda.is_available():
        pytest.skip("fast_hadamard_transform requires CUDA")
    generator = torch.Generator(device="cuda").manual_seed(7)
    x = torch.randn(
        5, 64, HADAMARD_WIDTH, dtype=torch.bfloat16, device="cuda",
        generator=generator,
    )
    official = fht.hadamard_transform(x, scale=HADAMARD_WIDTH**-0.5)
    ours = torch_hadamard_transform(x, HADAMARD_WIDTH**-0.5)
    assert torch.equal(official.view(torch.int16), ours.view(torch.int16))


# ---------------------------------------------------------------------------
# Head-split wrapper
# ---------------------------------------------------------------------------
def test_head_split_passes_through_below_the_launch_width() -> None:
    calls = []

    def fake(q, kv, attn_sink, topk_idxs, scale):  # noqa: ANN001
        calls.append(q.size(2))
        return torch.zeros_like(q)

    wrapped = make_head_split_sparse_attn(fake)
    q = torch.zeros(1, 2, SPARSE_ATTN_HEADS_PER_LAUNCH, 8)
    wrapped(q, torch.zeros(1, 4, 8), torch.zeros(q.size(2)), torch.zeros(1, 2, 4), 1.0)
    assert calls == [SPARSE_ATTN_HEADS_PER_LAUNCH]


def test_head_split_partitions_and_reassembles_every_head() -> None:
    """A stand-in kernel that stamps the head index proves the reassembly."""

    def fake(q, kv, attn_sink, topk_idxs, scale):  # noqa: ANN001
        # attn_sink carries the true head index for this launch, so the output
        # can only be right if the slicing and the concatenation agree.
        return attn_sink.view(1, 1, -1, 1).expand_as(q).contiguous()

    heads = 64
    wrapped = make_head_split_sparse_attn(fake)
    q = torch.zeros(1, 3, heads, 16)
    attn_sink = torch.arange(heads, dtype=torch.float32)
    out = wrapped(q, torch.zeros(1, 8, 16), attn_sink, torch.zeros(1, 3, 8), 1.0)
    assert out.shape == q.shape
    assert torch.equal(out[0, 0, :, 0], attn_sink)


def test_head_split_launch_width_is_the_vendor_tp4_head_count() -> None:
    # 64 heads over the vendor's supported world_size=4 gives 16 per rank.
    assert 64 % SPARSE_ATTN_HEADS_PER_LAUNCH == 0
    assert 64 // SPARSE_ATTN_HEADS_PER_LAUNCH == 4


# ---------------------------------------------------------------------------
# Recorded adaptations
# ---------------------------------------------------------------------------
def test_every_adaptation_states_reason_and_fidelity() -> None:
    assert ADAPTATIONS
    seen = set()
    for entry in ADAPTATIONS:
        assert {"id", "vendor_symbol", "change", "reason", "fidelity"} <= set(entry)
        assert entry["id"] not in seen
        seen.add(entry["id"])
        for key, value in entry.items():
            assert isinstance(value, str) and value.strip(), (entry["id"], key)


# ---------------------------------------------------------------------------
# Vendor source pinning
# ---------------------------------------------------------------------------
@snapshot_available
def test_vendor_sources_match_their_pinned_digests() -> None:
    observed = verify_vendor_sources(DEFAULT_SNAPSHOT)
    assert observed == VENDOR_SOURCE_SHA256


def test_vendor_source_verification_rejects_a_missing_tree(tmp_path: Path) -> None:
    with pytest.raises(OracleError):
        verify_vendor_sources(tmp_path)


# ---------------------------------------------------------------------------
# Workload identities
# ---------------------------------------------------------------------------
workloads_built = pytest.mark.skipif(
    not (WORKLOAD_DIR / "index.json").exists(),
    reason="run tools/build_deepseek_v4_workloads.py first",
)


@workloads_built
def test_workload_digests_match_their_bodies() -> None:
    from compiler.workloads.deepseek_v4 import LONG_PROMPT_TOKENS, Workload

    index = json.loads((WORKLOAD_DIR / "index.json").read_text())
    assert index["mandatory_context_tokens"] == LONG_PROMPT_TOKENS
    for workload_id, entry in index["workloads"].items():
        body = json.loads((WORKLOAD_DIR / entry["path"]).read_text())
        rebuilt = Workload(
            workload_id=body["workload_id"],
            kind=body["kind"],
            description=body["description"],
            rendered_text=body["rendered_text"],
            token_ids=tuple(body["token_ids"]),
            max_new_tokens=body["max_new_tokens"],
        )
        assert rebuilt.digest == entry["digest"] == body["digest"], workload_id
        assert len(body["token_ids"]) == entry["prompt_token_count"]


@workloads_built
def test_mandatory_two_hundred_thousand_token_workload_is_defined() -> None:
    from compiler.workloads.deepseek_v4 import LONG_PROMPT_TOKENS

    body = json.loads((WORKLOAD_DIR / "TA-DS-CTX-200K-1.json").read_text())
    assert len(body["token_ids"]) == LONG_PROMPT_TOKENS
    assert body["metadata"]["mandatory_contract"] is True
    assert body["kind"] == "long_natural"


@workloads_built
def test_stress_workload_is_not_a_substitute_for_the_natural_context() -> None:
    body = json.loads((WORKLOAD_DIR / "TA-DS-STRESS-1.json").read_text())
    assert body["kind"] == "repeated_special"
    assert len(set(body["token_ids"])) == 1
    assert "never a substitute" in body["description"]


@workloads_built
def test_prompts_carry_the_official_encoding_not_a_chat_template() -> None:
    chat = json.loads((WORKLOAD_DIR / "TA-DS-CHAT-1.json").read_text())
    # <｜begin▁of▁sentence｜> then <｜User｜>; the wire format has no
    # HuggingFace chat template behind it.
    assert chat["token_ids"][0] == 0
    assert chat["token_ids"][1] == 128_803
    assert chat["rendered_text"].startswith("<｜begin▁of▁sentence｜><｜User｜>")

    index = json.loads((WORKLOAD_DIR / "index.json").read_text())
    crosscheck = index.get("vendor_encoding_crosscheck")
    if crosscheck is not None:
        assert crosscheck["identical"] is True


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------
RESULTS = REPO / "results" / "abi3"


@pytest.mark.parametrize(
    "name",
    ["deepseek_v4_reference_oracle_short.json", "deepseek_v4_reference_oracle.json"],
)
def test_reference_oracle_report_shape(name: str) -> None:
    path = RESULTS / name
    if not path.exists():
        pytest.skip(f"{name} has not been produced on this machine")
    report = json.loads(path.read_text())
    assert report["schema"] == "opentallas.abi3.reference_oracle.v1"
    assert report["evidence_class"] == "external_reference_comparator"
    assert report["model_id"] == "deepseek-v4-flash-0731"
    assert report["selection"] == "greedy_lowest_token_id_argmax"
    assert "accelerator_execution" in report["not_a_claim"]
    assert report["vendor_source_sha256"] == VENDOR_SOURCE_SHA256
    assert report["head_split_verification"]["bitwise_identical"] is True

    # The routed-expert numeric path must be justified by a measurement, not
    # by a preference: whichever GEMM was used has to have passed its check.
    fp4 = report["fp4_gemm_verification"]
    assert fp4["fp8_gemm_agrees"] is True
    assert report["expert_numeric_path"] in {"fp4", "fp8"}
    if report["expert_numeric_path"] == "fp4":
        assert fp4["fp4_gemm_agrees"] is True
    else:
        assert fp4["fp4_gemm_agrees"] is False
        assert fp4["fp4_path_max_abs_error"] > fp4["tolerance"]

    for workload_id, result in report["results"].items():
        assert result["generated_token_count"] == len(result["generated_token_ids"])
        assert result["generated_token_count"] > 0, workload_id
        assert result["stop_reason"] in {"eos", "max_new_tokens"}
        assert isinstance(result["raw_decoded_text"], str)
        assert result["wall_seconds"] > 0
        assert result["peak_device_bytes"] > 0
    # A workload that could not run must say so rather than disappear.
    for workload_id, skipped in report.get("not_executed", {}).items():
        assert skipped["reason"] in {
            "time_budget_exhausted",
            "execution_failed",
            "engine_build_failed",
            "not_attempted",
        }
        assert skipped["detail"]
        assert workload_id not in report["results"]


# ---------------------------------------------------------------------------
# Live engine (needs the checkpoint and the GPU)
# ---------------------------------------------------------------------------
@snapshot_available
@cuda_available
def test_head_split_is_bitwise_identical_on_this_gpu() -> None:
    from runtime.reference.deepseek_v4_oracle import (
        import_vendor,
        verify_head_split_identity,
    )

    _, kernel_mod, _, _ = import_vendor(DEFAULT_SNAPSHOT)
    evidence = verify_head_split_identity(kernel_mod.sparse_attn)
    assert evidence["bitwise_identical"] is True
    assert evidence["max_abs_difference"] == 0.0


@pytest.fixture(scope="module")
def vendor_kernel():
    from runtime.reference.deepseek_v4_oracle import import_vendor

    _, kernel_mod, _, _ = import_vendor(DEFAULT_SNAPSHOT)
    torch.set_default_dtype(torch.bfloat16)
    torch.set_default_device("cuda")
    yield kernel_mod
    torch.set_default_device("cpu")
    torch.set_default_dtype(torch.float32)


@snapshot_available
@cuda_available
def test_act_quant_matches_a_torch_reference(vendor_kernel) -> None:
    """Block FP8 quantisation must be exact, not merely close."""
    generator = torch.Generator(device="cuda").manual_seed(31)
    x = torch.randn(64, 4096, dtype=torch.bfloat16, device="cuda", generator=generator)
    values, scales = vendor_kernel.act_quant(
        x, 128, "ue8m0", torch.float8_e8m0fnu
    )
    blocks = x.float().view(-1, 4096 // 128, 128)
    amax = blocks.abs().amax(-1).clamp_min(1e-4)
    expected_scale = torch.pow(2.0, torch.ceil(torch.log2(amax / 448.0)))
    expected = (blocks / expected_scale.unsqueeze(-1)).clamp(-448, 448).view(64, 4096)
    assert torch.equal(scales.float(), expected_scale)
    assert torch.equal(
        values.float(), expected.to(torch.float8_e4m3fn).float()
    )


@snapshot_available
@cuda_available
def test_hc_split_sinkhorn_matches_a_torch_reference(vendor_kernel) -> None:
    """The hyper-connection mixer feeds every block twice; it must be right."""
    hc, iters, eps = 4, 20, 1e-6
    generator = torch.Generator(device="cuda").manual_seed(32)
    mixes = torch.randn(
        1, 64, (2 + hc) * hc, dtype=torch.float32, device="cuda", generator=generator
    )
    scale = torch.randn(3, dtype=torch.float32, device="cuda", generator=generator)
    base = torch.randn(
        (2 + hc) * hc, dtype=torch.float32, device="cuda", generator=generator
    )
    pre, post, comb = vendor_kernel.hc_split_sinkhorn(
        mixes, scale, base, hc, iters, eps
    )

    flat = mixes.reshape(-1, (2 + hc) * hc)
    ref_pre = torch.sigmoid(flat[:, :hc] * scale[0] + base[:hc]) + eps
    ref_post = 2 * torch.sigmoid(flat[:, hc : 2 * hc] * scale[1] + base[hc : 2 * hc])
    ref_comb = (flat[:, 2 * hc :] * scale[2] + base[2 * hc :]).view(-1, hc, hc)
    ref_comb = ref_comb.softmax(-1) + eps
    ref_comb = ref_comb / (ref_comb.sum(-2, keepdim=True) + eps)
    for _ in range(iters - 1):
        ref_comb = ref_comb / (ref_comb.sum(-1, keepdim=True) + eps)
        ref_comb = ref_comb / (ref_comb.sum(-2, keepdim=True) + eps)

    assert (pre.flatten() - ref_pre.flatten()).abs().max() < 1e-5
    assert (post.flatten() - ref_post.flatten()).abs().max() < 1e-5
    assert (comb.reshape(-1, hc, hc) - ref_comb).abs().max() < 1e-5


@snapshot_available
@cuda_available
def test_sparse_attn_matches_a_torch_reference(vendor_kernel) -> None:
    """At the 16-head launch width the engine actually uses."""
    heads, head_dim, kv_len, topk, queries = 16, 512, 256, 64, 3
    generator = torch.Generator(device="cuda").manual_seed(33)
    q = torch.randn(
        1, queries, heads, head_dim, dtype=torch.bfloat16, device="cuda",
        generator=generator,
    )
    kv = torch.randn(
        1, kv_len, head_dim, dtype=torch.bfloat16, device="cuda", generator=generator
    )
    attn_sink = torch.randn(
        heads, dtype=torch.float32, device="cuda", generator=generator
    )
    idxs = torch.randint(
        -1, kv_len, (1, queries, topk), dtype=torch.int32, device="cuda",
        generator=generator,
    )
    scale = head_dim**-0.5
    got = vendor_kernel.sparse_attn(q, kv, attn_sink, idxs, scale)

    expected = torch.empty_like(got)
    for position in range(queries):
        selected = idxs[0, position]
        valid = selected >= 0
        gathered = kv[0, selected.clamp_min(0).long()].float()
        scores = (q[0, position].float() @ gathered.T) * scale
        scores = scores.masked_fill(~valid.unsqueeze(0), float("-inf"))
        top = scores.max(-1, keepdim=True).values
        weights = torch.exp(scores - top)
        denominator = weights.sum(-1) + torch.exp(attn_sink - top.squeeze(-1))
        expected[0, position] = (
            (weights @ gathered) / denominator.unsqueeze(-1)
        ).to(q.dtype)
    # One bfloat16 unit in the last place at the output magnitude.
    assert (got.float() - expected.float()).abs().max() <= 2**-8

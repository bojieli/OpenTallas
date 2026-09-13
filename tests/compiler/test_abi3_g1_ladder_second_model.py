"""WP-L: the G1 ladder and the shipped-prefix builder gain a second model.

docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md WP-L, gate DS41-R6.

These tests fix the two properties that make the addition safe rather than
merely present:

* the DEFAULT binding is unchanged -- every constant the three G1 builders used
  to carry as a literal is what the default preset rebinds them to, including
  each rung's artifact path, so an existing invocation writes an existing file;
* the V4.1 binding is ADDED, not substituted -- the gate board carries two
  workload bindings per rung and names both verdicts, and the shipped-prefix
  vector builder gains a geometry row without touching any existing row or the
  target list the vector images are generated from.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import abi3_g1_models as ladder_models  # noqa: E402

GATES = ROOT / "configs/gates/redesign_gates.json"


def _board() -> list[dict]:
    return json.loads(GATES.read_text(encoding="utf-8"))["gates"]


def _gate(gate_id: str) -> dict:
    for gate in _board():
        if gate["id"] == gate_id:
            return gate
    raise AssertionError(f"no gate {gate_id}")


# ---------------------------------------------------------------------------
# The presets
# ---------------------------------------------------------------------------
def test_default_preset_is_the_ladder_s_original_binding():
    model = ladder_models.resolve(None)
    assert model.key == "qwen3-8b"
    assert model.workload_id == "TA-QW-EOS-1"
    assert model.storage_classes == {
        "rom": "qwen3-8b-rom-single-chip",
        "hbm": "qwen3-8b-hbm-single-chip",
    }
    # The artifact paths the rungs already record.  A changed path here silently
    # orphans committed evidence, which is why it is asserted rather than
    # derived in the test.
    assert model.artifact("g1a", "operator_equivalence") == (
        ROOT / "results/rtl/abi3_g1a_operator_equivalence.json"
    )
    assert model.artifact("g1b", "layer_closure") == (
        ROOT / "results/rtl/abi3_g1b_layer_closure.json"
    )
    assert model.artifact("g1f", "reduced_end_to_end") == (
        ROOT / "results/rtl/abi3_g1f_reduced_end_to_end.json"
    )


def test_v41_preset_names_the_plan_s_artifacts_and_targets():
    model = ladder_models.resolve("deepseek-v4.1-flash")
    assert model.workload_id == "TA-DS41-EOS-1"
    assert model.reduced_workload_id == "TA-DS41-REDUCED-EOS-1"
    assert model.storage_classes == {
        "rom": "deepseek-v4.1-flash-rom-wafer",
        "hbm": "deepseek-v4.1-flash-hbm-cluster",
    }
    # Plan section 10.2: results/rtl/abi3_g1{a,b,c,d,e,f}_deepseek_v41_*.json.
    for rung, stem in (
        ("g1a", "operator_equivalence"),
        ("g1b", "layer_closure"),
        ("g1f", "reduced_end_to_end"),
    ):
        name = model.artifact(rung, stem).name
        assert name.startswith(f"abi3_{rung}_deepseek_v41_"), name


def test_an_unknown_model_is_refused_by_name():
    with pytest.raises(SystemExit) as raised:
        ladder_models.resolve("no-such-model")
    assert "unknown --model" in str(raised.value)


def test_require_present_names_every_missing_prerequisite_and_its_producer():
    model = ladder_models.resolve("deepseek-v4.1-flash")
    with pytest.raises(SystemExit) as raised:
        ladder_models.require_present(
            model,
            {"a thing": ROOT / "no/such/path/a.json"},
            "because the rung needs it",
        )
    text = str(raised.value)
    assert "a thing" in text
    assert "because the rung needs it" in text
    assert model.reduced_producer in text


# ---------------------------------------------------------------------------
# The board reports the second binding BESIDE the first
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("gate_id", "qwen_workload", "qwen_artifact"),
    [
        (
            "G1a",
            "TA-QW-EOS-1",
            "results/rtl/abi3_g1a_operator_equivalence.json",
        ),
        ("G1b", "TA-QW-EOS-1", "results/rtl/abi3_g1b_layer_closure.json"),
        (
            # The whole-run rung is bound to the GOVERNED workload id, not the
            # reduced one: its record declares the workload it stands for and
            # names the reduced id beside it, and the oracle field is what
            # carries the reduced ids.
            "G1f",
            "TA-QW-EOS-1",
            "results/rtl/abi3_g1f_reduced_end_to_end.json",
        ),
    ],
)
def test_rung_carries_two_bindings_with_qwen_s_first(
    gate_id, qwen_workload, qwen_artifact
):
    ev = _gate(gate_id)["evaluator"]
    bindings = ev["workload_bindings"]
    assert len(bindings) == 2, gate_id
    # Neither binding is implicit: the base evaluator no longer carries a
    # workload or an artifact of its own, so a reader cannot mistake one
    # model's evidence for the rung's.
    assert "workload" not in ev and "artifact" not in ev
    assert bindings[0]["workload"] == qwen_workload
    assert bindings[0]["artifact"] == qwen_artifact
    assert bindings[1]["workload"].startswith("TA-DS41")
    assert "deepseek_v41" in bindings[1]["artifact"]


def test_v41_binding_uses_its_own_oracle_on_the_whole_run_rung():
    bindings = _gate("G1f")["evaluator"]["workload_bindings"]
    assert bindings[0]["oracle"] == "results/abi3/qwen3_reduced_reference_oracle.json"
    assert (
        bindings[1]["oracle"]
        == "results/abi3/deepseek_v41_reduced_reference_oracle.json"
    )
    assert (
        bindings[1]["oracle_token_field"]
        == "results.TA-DS41-REDUCED-EOS-1.generated_token_ids"
    )


def test_evaluator_reports_both_bindings_and_fails_if_either_does():
    from tools.check_redesign_gates import evaluate

    board = _board()
    verdict = evaluate(_gate("G1a"), board)
    assert verdict["status"] == "fail"
    # Both labels appear: a satisfied Qwen binding would still be printed beside
    # an unsatisfied V4.1 one, which is the point of the binding list.
    assert "TA-QW-EOS-1:" in verdict["why"]
    assert "TA-DS41-EOS-1:" in verdict["why"]
    assert "workload binding(s)" in verdict["why"]


def test_single_binding_rungs_are_untouched():
    ev = _gate("G1e")["evaluator"]
    assert "workload_bindings" not in ev
    assert ev["workload"] == "TA-QW-EOS-1"


# ---------------------------------------------------------------------------
# The shipped-prefix vector builder
# ---------------------------------------------------------------------------
def test_v41_geometry_matches_the_pinned_release_and_is_not_v4_s():
    from compiler.frontend.deepseek_v4_releases import V41_FLASH
    from tools.build_abi3_shipped_prefix_vectors import TARGET_GEOMETRY

    geo = TARGET_GEOMETRY["deepseek-v4.1-flash-rom-wafer"]
    scalars = V41_FLASH.config_scalars
    assert geo.embed_width == int(scalars["hidden_size"]) == 5120
    assert geo.vocabulary == int(scalars["vocab_size"]) == 129_280
    assert geo.head_width == int(scalars["head_dim"]) == 512
    assert geo.query_heads == int(scalars["num_attention_heads"]) == 64
    assert geo.kv_heads == int(scalars["num_key_value_heads"]) == 1
    assert geo.kv_width == geo.kv_heads * geo.head_width
    # model_index 1 is the DeepSeek identity set.
    assert geo.model_index == 1
    # The trap this row exists to avoid: V4's residual stream is 4,096 and
    # V4.1's is 5,120, so a row copied from the V4 entry would pass the
    # embedding view check on the wrong width.
    assert geo.embed_width != TARGET_GEOMETRY["deepseek-v4-flash-rom-wafer"].embed_width


def test_adding_the_geometry_does_not_change_the_vector_set():
    from tools.build_abi3_deployment_rtl_vectors import TARGETS
    from tools.build_abi3_shipped_prefix_vectors import TARGET_GEOMETRY

    keys = [target.key for target in TARGETS]
    # The images are concatenated in TARGETS order and every existing target's
    # bases are the length of the image before it, so the vector set is
    # append-only in this list.  A geometry row for a target that is NOT in the
    # list cannot move a single byte of it.
    assert "deepseek-v4.1-flash-rom-wafer" not in keys
    assert "deepseek-v4.1-flash-rom-wafer" in TARGET_GEOMETRY
    # And the four rows the builder walks today are still exactly those.
    walked = [key for key in keys if key in TARGET_GEOMETRY]
    assert walked == [
        "qwen3-8b-rom-single-chip",
        "qwen3-8b-hbm-single-chip",
        "deepseek-v4-flash-rom-wafer",
        "deepseek-v4-flash-hbm-cluster",
    ]


def test_a_target_with_geometry_but_no_boundary_refuses_with_the_bootstrap():
    from tools.build_abi3_shipped_prefix_vectors import (
        _target_boundary,
        _target_counts,
    )

    for accessor, wanted in (
        (_target_boundary, "fail-stop boundary"),
        (_target_counts, "expected prefix counters"),
    ):
        with pytest.raises(SystemExit) as raised:
            accessor("deepseek-v4.1-flash-rom-wafer")
        text = str(raised.value)
        assert wanted in text
        assert "run this builder once" in text
    # The four walkable targets still resolve.
    for key in (
        "qwen3-8b-rom-single-chip",
        "qwen3-8b-hbm-single-chip",
        "deepseek-v4-flash-rom-wafer",
        "deepseek-v4-flash-hbm-cluster",
    ):
        assert _target_boundary(key) is not None
        assert _target_counts(key)["fetched"] > 0


def test_the_campaign_no_longer_freezes_its_case_count():
    from tools import rtl_abi3_shipped_prefix_campaign as campaign

    vectors = json.loads(
        (
            ROOT
            / "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json"
        ).read_text(encoding="utf-8")
    )
    assert len(vectors["cases"]) == campaign.STRUCTURAL_CHECKS_MEASURED_AT_CASES
    # The committed vector set is at the measured count, so the arithmetic runs.
    assert campaign.expected_integrated_checks(vectors) > 0
    # A vector set with a fifth case refuses rather than comparing against a
    # residue measured at four.
    five = dict(vectors)
    five["cases"] = list(vectors["cases"]) + [vectors["cases"][-1]]
    with pytest.raises(SystemExit) as raised:
        campaign.expected_integrated_checks(five)
    assert "re-measured" in str(raised.value)


# ---------------------------------------------------------------------------
# The reduced V4.1 fixture builder's derivations and its seed rule
# ---------------------------------------------------------------------------
def _reduced():
    return pytest.importorskip(
        "tools.build_deepseek_v41_reduced_model",
        reason="the reduced V4.1 builder needs numpy",
    )


def test_the_reduction_rule_classifies_every_released_field():
    """An unclassified field is a refusal, not a silently copied magnitude.

    The released inference config is flat and has ~60 fields.  A reduction that
    skipped one would carry a shipped magnitude into the fixture without saying
    so, which is how a "reduced" model ends up with a 384-expert router.
    """
    reduced = _reduced()
    full = json.loads(reduced.FULL_INFERENCE_CONFIG.read_text(encoding="utf-8"))
    classified = (
        set(reduced.KEPT_EXACTLY)
        | set(reduced.BLOCK_WIDTHS)
        | set(reduced.COUNT_FIELDS)
        | set(reduced.DERIVED_FIELDS)
        | {
            "vision_dim", "vision_n_heads", "vision_inter_dim",
            "vision_patch_size", "vision_rope_theta", "vision_downsample_ratio",
            "vision_max_n_token", "vision_min_pixels", "vision_max_wh_ratio",
        }
    )
    assert not set(full) - classified, sorted(set(full) - classified)


def test_widths_reduce_to_whole_quantization_blocks():
    """The release's own act_quant asserts N % 32 == 0, so 32 is the floor."""
    reduced = _reduced()
    root = json.loads(reduced.FULL_ROOT_CONFIG.read_text(encoding="utf-8"))
    block = reduced.quantization_block(root)
    assert block == 32
    full = json.loads(reduced.FULL_INFERENCE_CONFIG.read_text(encoding="utf-8"))
    body = reduced.reduced_body(full, factor=32, block=block, engram_factor=2048)
    for field in reduced.BLOCK_WIDTHS:
        value = int(body[field])
        assert value >= block, field
        assert value % block == 0, (field, value)
    # 2,304 / 32 is 72, which is NOT a whole block, so the rule must have
    # quantised it down rather than passing it through.
    assert int(full["moe_inter_dim"]) // 32 == 72
    assert body["moe_inter_dim"] == 64
    # The mode sequence is kept exactly, all 43 entries including the MTP tail.
    assert list(body["compress_ratios"]) == list(full["compress_ratios"])
    assert len(body["compress_ratios"]) == 43
    assert int(body["n_layers"]) == 40
    # And the RoPE fraction of a head is preserved rather than rounded.
    assert int(full["head_dim"]) // int(full["rope_head_dim"]) == (
        int(body["head_dim"]) // int(body["rope_head_dim"])
    )


def test_aggregate_refuses_a_seed_it_cannot_show_is_smallest(tmp_path):
    """A striped search establishes minimality or it refuses to name a winner."""
    reduced = _reduced()
    from runtime.abi3.capability import canonical_json

    def report(start, stride, tried, match, generated=()):
        path = tmp_path / f"class_{start}.json"
        path.write_bytes(
            canonical_json(
                {
                    "schema": (
                        "opentallas.abi3.deepseek_v41_reduced_seed_search.v1"
                    ),
                    "start": start,
                    "stride": stride,
                    "limit": 100,
                    "cap": 16,
                    "official_eos_token_ids": [0, 1],
                    "prompt_token_ids": [7, 8],
                    "seeds_tried": tried,
                    "highest_seed_tried": tried[-1] if tried else None,
                    "match": match,
                    "generated_token_ids": list(generated),
                    "seed_zero_generated_token_ids": None,
                    "wall_seconds": 1.0,
                }
            )
            + b"\n"
        )
        return path

    common = {"cap": 16, "eos": {0, 1}, "prompt": [7, 8]}

    # A class that stopped short of the winner cannot certify minimality.
    short = [report(0, 2, [0, 2, 4, 6], 6, [5, 0]), report(1, 2, [1], None)]
    with pytest.raises(reduced.ReducedModelError) as raised:
        reduced.aggregate_search(short, **common)
    assert "not scanned past it" in str(raised.value)

    # Scanned past it: the winner stands, with its minimality argument recorded.
    ok = [report(0, 2, [0, 2, 4, 6], 6, [5, 0]), report(1, 2, [1, 3, 5, 7], None)]
    out = reduced.aggregate_search(ok, **common)
    assert out["seed"] == 6
    assert out["seeds_tried"] == 8
    assert out["minimality_established"] is True

    # A missing residue class is refused outright.
    with pytest.raises(reduced.ReducedModelError) as missing:
        reduced.aggregate_search([ok[0]], **common)
    assert "not every class of stride" in str(missing.value)


def test_a_one_token_eos_is_not_an_accepted_shape():
    """The fixture has to exercise decode, not just prefill plus a stop."""
    reduced = _reduced()
    eos = {0, 1}
    assert not reduced.shape_matches([1], eos, 16)
    assert reduced.shape_matches([5, 1], eos, 16)
    assert not reduced.shape_matches([1, 5], eos, 16)
    assert not reduced.shape_matches([5, 6, 7], eos, 16)

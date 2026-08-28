from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator
import pytest

from compiler.frontend.deepseek_v4_generation import (
    GENERATION_SOURCE_SHA256,
    MODEL_SOURCE_SHA256,
    OFFICIAL_RNG_SEED,
    DeepSeekV4GenerationController,
    DeepSeekV4GenerationError,
    GenerationConfig,
    replay_generation_control,
)
from compiler.frontend.deepseek_v4_tokenizer import MODEL_MAX_LENGTH


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "compiler/models/deepseek-v4-flash-0731"
SCHEMA = ROOT / "schemas/compiler/deepseek_v4_generation_trace_v1.schema.json"
REPLAY_SCHEMA = ROOT / "schemas/compiler/deepseek_v4_generation_replay_v1.schema.json"
REPLAY_FIXTURE = (
    ROOT / "testdata/compiler/deepseek_v4_generation/greedy_replay.json"
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _accept_greedy(
    controller: DeepSeekV4GenerationController,
    candidates: list[int],
) -> dict[str, Any]:
    invocation = controller.next_invocation()
    assert invocation is not None
    controller.accept_model_result(
        invocation_id=invocation.invocation_id,
        candidate_token_ids=candidates,
        argmax_token_ids=candidates,
        processed_start_pos=invocation.start_pos,
        processed_stop_pos_exclusive=invocation.stop_pos_exclusive,
        logits_sha256=_digest(f"logits-{invocation.invocation_index}"),
        state_commit_sha256=_digest(f"state-{invocation.invocation_index}"),
    )
    return invocation.to_dict()


def _run_greedy(
    prompts: list[list[int]],
    config: GenerationConfig,
    candidates: list[list[int]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    controller = DeepSeekV4GenerationController(prompts, config)
    invocations = []
    for candidate_batch in candidates:
        if controller.complete:
            break
        invocations.append(_accept_greedy(controller, candidate_batch))
    assert controller.complete
    assert controller.next_invocation() is None
    return invocations, controller.result()


def _official_loop_oracle(
    prompts: list[list[int]],
    config: GenerationConfig,
    candidate_batches: list[list[int]],
) -> dict[str, Any]:
    """Small independent transcription of pinned generate.py for comparison."""

    prompt_lengths = [len(row) for row in prompts]
    total_length = min(
        config.max_context_tokens,
        config.max_new_tokens + max(prompt_lengths),
    )
    tokens: list[list[int | None]] = [
        row[:] + [None] * (total_length - len(row)) for row in prompts
    ]
    finished = [False] * len(prompts)
    previous_position = 0
    calls = []
    for candidate_position, candidates in zip(
        range(min(prompt_lengths), total_length), candidate_batches
    ):
        selected = []
        overrides = []
        for row, candidate in enumerate(candidates):
            override = candidate_position < prompt_lengths[row]
            token = prompts[row][candidate_position] if override else candidate
            tokens[row][candidate_position] = token
            selected.append(token)
            overrides.append(override)
            if not override and token == config.eos_token_id:
                finished[row] = True
        calls.append(
            {
                "phase": "prefill" if previous_position == 0 else "decode",
                "start_pos": previous_position,
                "stop_pos_exclusive": candidate_position,
                "candidate_position": candidate_position,
                "prompt_override_mask": overrides,
                "selected_token_ids": selected,
            }
        )
        previous_position = candidate_position
        if all(finished):
            break

    completions = []
    for row, prompt_length in enumerate(prompt_lengths):
        visible = tokens[row][
            prompt_length : prompt_length + config.max_new_tokens
        ]
        visible = [int(token) for token in visible if token is not None]
        if config.eos_token_id in visible:
            visible = visible[: visible.index(config.eos_token_id)]
        visible.append(config.eos_token_id)
        completions.append(visible)
    return {
        "calls": calls,
        "completions": completions,
        "committed_through_exclusive": previous_position,
    }


def test_source_hashes_are_exactly_bound_to_official_release() -> None:
    source = json.loads((TARGET / "checkpoint_source.json").read_text())
    expected = {record["path"]: record["sha256"] for record in source["expected_files"]}
    assert expected["inference/generate.py"] == GENERATION_SOURCE_SHA256
    assert expected["inference/model.py"] == MODEL_SOURCE_SHA256
    assert source["repository"] == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert source["revision"] == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"


def test_variable_prompt_batch_matches_official_loop_and_exposes_post_eos_state() -> None:
    config = GenerationConfig(
        max_batch_size=2,
        max_context_tokens=16,
        max_new_tokens=3,
        temperature=0,
    )
    prompts = [[0, 10, 11], [0, 20, 21, 22, 23]]
    candidates = [
        [30, 130],
        [1, 131],
        [40, 50],
        [41, 1],
    ]
    invocations, result = _run_greedy(prompts, config, candidates)
    oracle = _official_loop_oracle(prompts, config, candidates)

    assert [record["phase"] for record in invocations] == [
        call["phase"] for call in oracle["calls"]
    ]
    assert [
        (record["start_pos"], record["stop_pos_exclusive"])
        for record in invocations
    ] == [
        (call["start_pos"], call["stop_pos_exclusive"])
        for call in oracle["calls"]
    ]
    assert [record["prompt_override_mask"] for record in result["trace"]] == [
        call["prompt_override_mask"] for call in oracle["calls"]
    ]
    assert [record["selected_token_ids"] for record in result["trace"]] == [
        call["selected_token_ids"] for call in oracle["calls"]
    ]
    assert [row["completion_token_ids"] for row in result["sessions"]] == (
        oracle["completions"]
    )
    assert result["termination"] == "all_rows_generated_eos"
    assert result["trace"][0]["selected_token_ids"] == [30, 22]
    assert result["trace"][1]["selected_token_ids"] == [1, 23]
    assert result["trace"][2]["finished_before_mask"] == [True, False]
    assert result["trace"][3]["finished_after_mask"] == [True, True]

    first, second = result["sessions"]
    assert first["completion_token_ids"] == [30, 1]
    assert first["model_eos_position"] == 4
    assert first["model_eos_committed_to_state"] is True
    assert first["post_eos_positions_committed"] == 1
    assert second["completion_token_ids"] == [50, 1]
    assert second["model_eos_position"] == 6
    assert second["model_eos_committed_to_state"] is False
    assert second["post_eos_positions_committed"] == 0
    assert all(
        row["state_committed_through_exclusive"]
        == oracle["committed_through_exclusive"]
        == 6
        for row in result["sessions"]
    )


def test_prefill_and_decode_inputs_are_contiguous_and_candidate_is_deferred() -> None:
    controller = DeepSeekV4GenerationController(
        [[0, 10, 11]],
        GenerationConfig(
            max_batch_size=1,
            max_context_tokens=8,
            max_new_tokens=2,
        ),
    )
    prefill = controller.next_invocation()
    assert prefill is not None
    assert prefill.phase == "prefill"
    assert prefill.start_pos == 0
    assert prefill.stop_pos_exclusive == 3
    assert prefill.candidate_position == 3
    assert prefill.input_ids == ((0, 10, 11),)

    _accept_greedy(controller, [20])
    decode = controller.next_invocation()
    assert decode is not None
    assert decode.phase == "decode"
    assert decode.start_pos == 3
    assert decode.stop_pos_exclusive == 4
    assert decode.candidate_position == 4
    assert decode.input_ids == ((20,),)

    _accept_greedy(controller, [21])
    session = controller.result()["sessions"][0]
    assert session["completion_token_ids"] == [20, 21, 1]
    assert session["eos_origin"] == "host_appended_like_official_generate_py"
    assert session["stop_reason"] == "max_new_tokens"
    assert session["state_committed_through_exclusive"] == 4
    # Candidate 21 at position 4 is visible but is never sent through a later
    # model call, exactly like the official loop.
    assert session["completion_token_ids"][-2] == 21


def test_context_limit_is_distinct_from_model_eos_and_host_appends_terminator() -> None:
    _, result = _run_greedy(
        [[0, 10, 11]],
        GenerationConfig(
            max_batch_size=1,
            max_context_tokens=4,
            max_new_tokens=4,
        ),
        [[20]],
    )
    session = result["sessions"][0]
    assert session["completion_token_ids"] == [20, 1]
    assert session["eos_origin"] == "host_appended_like_official_generate_py"
    assert session["stop_reason"] == "max_context_tokens"
    assert session["model_eos_position"] is None
    assert result["termination"] == "length_limit"


def test_prompt_eos_is_an_override_not_a_generated_stop() -> None:
    controller = DeepSeekV4GenerationController(
        [[0, 10], [0, 20, 1, 21]],
        GenerationConfig(
            max_batch_size=2,
            max_context_tokens=8,
            max_new_tokens=2,
        ),
    )
    first = controller.next_invocation()
    assert first is not None
    assert first.prompt_override_mask == (False, True)
    _accept_greedy(controller, [30, 1])
    assert controller.pending_invocation is None
    assert not controller.complete
    second = controller.next_invocation()
    assert second is not None
    assert second.finished_before_mask == (False, False)
    assert second.prompt_override_mask == (False, True)
    _accept_greedy(controller, [1, 40])
    assert not controller.complete
    third = controller.next_invocation()
    assert third is not None
    assert third.finished_before_mask == (True, False)
    assert third.prompt_override_mask == (False, False)
    _accept_greedy(controller, [40, 1])
    assert controller.complete


def test_executor_commit_validation_is_atomic_and_retryable() -> None:
    controller = DeepSeekV4GenerationController(
        [[0, 10]],
        GenerationConfig(
            max_batch_size=1,
            max_context_tokens=4,
            max_new_tokens=1,
        ),
    )
    invocation = controller.next_invocation()
    assert invocation is not None
    with pytest.raises(DeepSeekV4GenerationError, match="commit span"):
        controller.accept_model_result(
            invocation_id=invocation.invocation_id,
            candidate_token_ids=[20],
            argmax_token_ids=[20],
            processed_start_pos=1,
            processed_stop_pos_exclusive=invocation.stop_pos_exclusive,
            logits_sha256=_digest("logits"),
            state_commit_sha256=_digest("state"),
        )
    assert controller.pending_invocation is invocation
    assert controller.next_invocation() is invocation

    with pytest.raises(DeepSeekV4GenerationError, match="differ from argmax"):
        controller.accept_model_result(
            invocation_id=invocation.invocation_id,
            candidate_token_ids=[20],
            argmax_token_ids=[21],
            processed_start_pos=invocation.start_pos,
            processed_stop_pos_exclusive=invocation.stop_pos_exclusive,
            logits_sha256=_digest("logits"),
            state_commit_sha256=_digest("state"),
        )
    assert controller.pending_invocation is invocation
    _accept_greedy(controller, [20])
    assert controller.complete


def test_stochastic_trace_requires_contiguous_hashed_rng_state() -> None:
    controller = DeepSeekV4GenerationController(
        [[0, 10]],
        GenerationConfig(
            max_batch_size=1,
            max_context_tokens=5,
            max_new_tokens=2,
            temperature=1.0,
        ),
    )
    first = controller.next_invocation()
    assert first is not None
    controller.accept_model_result(
        invocation_id=first.invocation_id,
        candidate_token_ids=[20],
        processed_start_pos=first.start_pos,
        processed_stop_pos_exclusive=first.stop_pos_exclusive,
        logits_sha256=_digest("logits-0"),
        state_commit_sha256=_digest("state-0"),
        rng_state_before_sha256=_digest("rng-a"),
        rng_state_after_sha256=_digest("rng-b"),
    )
    second = controller.next_invocation()
    assert second is not None
    with pytest.raises(DeepSeekV4GenerationError, match="discontinuous"):
        controller.accept_model_result(
            invocation_id=second.invocation_id,
            candidate_token_ids=[21],
            processed_start_pos=second.start_pos,
            processed_stop_pos_exclusive=second.stop_pos_exclusive,
            logits_sha256=_digest("logits-1"),
            state_commit_sha256=_digest("state-1"),
            rng_state_before_sha256=_digest("wrong"),
            rng_state_after_sha256=_digest("rng-c"),
        )
    assert controller.pending_invocation is second
    controller.accept_model_result(
        invocation_id=second.invocation_id,
        candidate_token_ids=[21],
        processed_start_pos=second.start_pos,
        processed_stop_pos_exclusive=second.stop_pos_exclusive,
        logits_sha256=_digest("logits-1"),
        state_commit_sha256=_digest("state-1"),
        rng_state_before_sha256=_digest("rng-b"),
        rng_state_after_sha256=_digest("rng-c"),
    )
    result = controller.result()
    assert result["sampling"] == {
        "algorithm": "pytorch_cuda_exponential_race",
        "exact_replay_status": "blocked_pending_pinned_torch_cuda_rng_stack",
        "official_expression": (
            "argmax(softmax(logits/max(temperature,1e-5))/Exponential(1))"
        ),
        "rng_seed": OFFICIAL_RNG_SEED,
    }
    assert result["trace"][1]["rng_state_before_sha256"] == _digest("rng-b")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"decode_mode": "dspark"}, "never calls forward_spec"),
        ({"top_p": 0.95}, "no top-p filter"),
        ({"temperature": -0.1}, "temperature"),
        ({"temperature": float("nan")}, "temperature"),
        ({"rng_seed": 7}, "torch.manual_seed"),
        ({"max_new_tokens": 0}, "max_new_tokens"),
        ({"max_context_tokens": MODEL_MAX_LENGTH + 1}, "max_context_tokens"),
    ],
)
def test_unsupported_or_implicit_generation_policy_fails_closed(
    kwargs: dict[str, Any], match: str
) -> None:
    defaults: dict[str, Any] = {
        "max_batch_size": 1,
        "max_context_tokens": 8,
        "max_new_tokens": 2,
    }
    defaults.update(kwargs)
    with pytest.raises(DeepSeekV4GenerationError, match=match):
        GenerationConfig(**defaults)


@pytest.mark.parametrize(
    ("prompts", "match"),
    [
        ([], "at least one row"),
        ([[]], "must not be empty"),
        ([[10, 11]], "official BOS"),
        ([[0, -1]], "0..129279"),
        ([[0, True]], "0..129279"),
        ([[0, 10, 11, 12]], "leaves no generation position"),
    ],
)
def test_prompt_contract_fails_closed(prompts: list[list[int]], match: str) -> None:
    with pytest.raises(DeepSeekV4GenerationError, match=match):
        DeepSeekV4GenerationController(
            prompts,
            GenerationConfig(
                max_batch_size=1,
                max_context_tokens=4,
                max_new_tokens=1,
            ),
        )


def test_trace_is_byte_deterministic_for_identical_executor_evidence() -> None:
    config = GenerationConfig(
        max_batch_size=1,
        max_context_tokens=8,
        max_new_tokens=2,
    )
    _, first = _run_greedy([[0, 10]], config, [[20], [1]])
    _, second = _run_greedy([[0, 10]], config, [[20], [1]])
    assert first == second
    assert first["trace_id"] == (
        "db7d2a480067079bd29f0c9051f2679f98f1956e5b606f68af34065a0d1736af"
    )
    assert first["control_scope"]["execution_status"] == (
        "control_trace_only_pending_model_operator_execution"
    )
    assert "DSpark target verification and speculative acceptance" in (
        first["control_scope"]["unresolved"]
    )


def test_generation_trace_schema_is_strict_and_accepts_both_sampling_modes() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    _, greedy = _run_greedy(
        [[0, 10]],
        GenerationConfig(
            max_batch_size=1,
            max_context_tokens=4,
            max_new_tokens=1,
        ),
        [[20]],
    )
    validator.validate(greedy)

    stochastic_controller = DeepSeekV4GenerationController(
        [[0, 10]],
        GenerationConfig(
            max_batch_size=1,
            max_context_tokens=4,
            max_new_tokens=1,
            temperature=0.7,
        ),
    )
    invocation = stochastic_controller.next_invocation()
    assert invocation is not None
    stochastic_controller.accept_model_result(
        invocation_id=invocation.invocation_id,
        candidate_token_ids=[20],
        processed_start_pos=invocation.start_pos,
        processed_stop_pos_exclusive=invocation.stop_pos_exclusive,
        logits_sha256=_digest("schema-logits"),
        state_commit_sha256=_digest("schema-state"),
        rng_state_before_sha256=_digest("schema-rng-before"),
        rng_state_after_sha256=_digest("schema-rng-after"),
    )
    validator.validate(stochastic_controller.result())


def test_committed_greedy_replay_is_schema_valid_and_deterministic() -> None:
    replay_schema = json.loads(REPLAY_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(replay_schema)
    request = json.loads(REPLAY_FIXTURE.read_text(encoding="utf-8"))
    Draft202012Validator(replay_schema).validate(request)
    result = replay_generation_control(request)
    assert result["trace_id"] == (
        "db7d2a480067079bd29f0c9051f2679f98f1956e5b606f68af34065a0d1736af"
    )
    assert result["sessions"][0]["completion_token_ids"] == [20, 1]


def test_replay_rejects_missing_extra_or_misbound_model_results() -> None:
    request = json.loads(REPLAY_FIXTURE.read_text(encoding="utf-8"))
    missing = json.loads(json.dumps(request))
    missing["model_results"].pop()
    with pytest.raises(DeepSeekV4GenerationError, match="ended before"):
        replay_generation_control(missing)

    extra = json.loads(json.dumps(request))
    extra["model_results"].append(extra["model_results"][-1])
    with pytest.raises(DeepSeekV4GenerationError, match="is extra"):
        replay_generation_control(extra)

    misbound = json.loads(json.dumps(request))
    misbound["model_results"][0]["invocation_id"] = _digest("wrong")
    with pytest.raises(DeepSeekV4GenerationError, match="does not match"):
        replay_generation_control(misbound)

    unknown = json.loads(json.dumps(request))
    unknown["model_results"][0]["unreviewed"] = True
    with pytest.raises(DeepSeekV4GenerationError, match="unknown"):
        replay_generation_control(unknown)


def test_generation_replay_cli_emits_canonical_control_trace(tmp_path: Path) -> None:
    output = tmp_path / "generation-trace.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "replay-deepseek-v4-generation",
            "--request",
            str(REPLAY_FIXTURE),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    trace = json.loads(output.read_text(encoding="ascii"))
    assert trace["trace_id"] == (
        "db7d2a480067079bd29f0c9051f2679f98f1956e5b606f68af34065a0d1736af"
    )
    assert "replayed 2 target-only model calls for 1 session" in result.stdout
    assert "pending_model_operator_execution" in result.stdout

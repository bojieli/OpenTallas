"""Tests for the host driver, the evidence gate and the agent sandbox."""

from __future__ import annotations

import pytest

from runtime.abi3.constants import StorageClass
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.agent import (
    AgentProtocolError,
    Sandbox,
    parse_turn,
    run_episode,
)
from runtime.driver import DriverError, GenerationDriver, validate_token_ids
from runtime.evidence import (
    ComparisonError,
    EvidenceClass,
    ExecutionRecord,
    Provenance,
    Quantity,
    TargetIdentity,
    WorkloadIdentity,
    build_comparison,
    check_comparable,
    check_token_legitimacy,
)
from runtime.sim.device import Device


# ---------------------------------------------------------------------------
# Agent sandbox
# ---------------------------------------------------------------------------
INVENTORY = "bolts,24\nnuts,17\nwashers,58\nscrews,131\nrivets,9\n"
INVENTORY_TOTAL = 239


def test_parse_accepts_exactly_one_bash_block():
    parsed = parse_turn("thinking\n```bash\nwc -l inventory.txt\n```\n")
    assert parsed.kind == "command"
    assert parsed.command == "wc -l inventory.txt"


def test_parse_accepts_answer_and_it_takes_precedence():
    parsed = parse_turn("```bash\nls\n```\nANSWER: 239")
    assert parsed.kind == "answer"
    assert parsed.answer == "239"


@pytest.mark.parametrize(
    "text",
    [
        "```bash\na\n```\n```bash\nb\n```",  # two blocks
        "```bash\n\n```",  # empty block
        "```bash\ncd /tmp\nls\n```",  # multiple commands in one block
    ],
)
def test_parse_is_fail_closed(text):
    with pytest.raises(AgentProtocolError):
        parse_turn(text)


def test_parse_reports_no_action_rather_than_inventing_one():
    parsed = parse_turn("I am not sure what to do here.")
    assert parsed.kind == "neither"
    assert parsed.command is None


def test_sandbox_executes_a_model_command_in_isolation():
    with Sandbox({"inventory.txt": INVENTORY}) as sandbox:
        result = sandbox.run("awk -F',' '{sum += $2} END {print sum}' inventory.txt")
        assert result.exit_code == 0
        assert result.stdout.strip() == str(INVENTORY_TOTAL)
        assert not result.timed_out
        # The sandbox root is private and disappears afterwards.
        root = sandbox.root
        assert (root / "inventory.txt").exists()
    assert not root.exists()


def test_sandbox_enforces_a_timeout():
    with Sandbox({"a.txt": "x"}, timeout_seconds=0.5) as sandbox:
        result = sandbox.run("sleep 5")
        assert result.timed_out
        assert result.exit_code == 124


def test_episode_stops_on_a_protocol_violation_without_executing():
    turns = ["```bash\nls\n```\n```bash\npwd\n```"]

    def generate(messages):
        return turns[len(messages) // 2]

    episode = run_episode(
        generate=generate, render_context=lambda m: m, sandbox_files={"a.txt": "x"}
    )
    assert episode.stop_reason == "protocol_violation"
    assert episode.protocol_violation is not None
    assert episode.answer is None


def test_episode_feeds_observations_back_and_terminates_on_answer():
    scripted = [
        "```bash\nawk -F',' '{sum += $2} END {print sum}' inventory.txt\n```",
        "ANSWER: 239",
    ]
    seen: list[list[dict]] = []

    def generate(messages):
        seen.append([dict(m) for m in messages])
        return scripted[len(messages) // 2]

    episode = run_episode(
        generate=generate,
        render_context=lambda m: m,
        sandbox_files={"inventory.txt": INVENTORY},
    )
    assert episode.stop_reason == "answered"
    assert episode.answer == "239"
    # The second turn saw the real command output, not a fabricated one.
    assert "239" in seen[1][-1]["content"]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def _fixture_device():
    capability = fixture_capability()
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    return Device(deployment, capability), capability


def test_driver_resolves_the_generation_policy_and_eos_set():
    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    assert driver.vocabulary_size == 16
    assert driver.eos_token_ids == (15,)


def test_driver_rejects_an_empty_prompt():
    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    with pytest.raises(DriverError):
        driver.generate([])


def test_driver_rejects_an_out_of_vocabulary_prompt_token():
    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    with pytest.raises(DriverError):
        driver.generate([999])


def test_validate_token_ids_flags_illegal_ids():
    problems = validate_token_ids([0, 5, 40], 16)
    assert len(problems) == 1
    assert "40" in problems[0]


# ---------------------------------------------------------------------------
# Evidence gate
# ---------------------------------------------------------------------------
def _record(
    *,
    target_id="a",
    deployment_digest="aa",
    tokens=(1, 2, 3),
    technology_view="view-x",
    evidence=EvidenceClass.FUNCTIONAL,
    workload_digest="wd",
    quantities=(),
    failure=None,
):
    return ExecutionRecord(
        evidence_class=evidence,
        workload=WorkloadIdentity(
            model_id="m",
            workload_id="w",
            workload_digest=workload_digest,
            prompt_token_count=4,
            max_new_tokens=8,
            generation_policy_digest="gp",
            numeric_profile="np",
            graph_id="gi",
            tokenizer_sha256="tk",
        ),
        target=TargetIdentity(
            target_id=target_id,
            backend="b",
            topology_class=0,
            node_count=1,
            capability_digest="cd",
            deployment_digest=deployment_digest,
            technology_view=technology_view,
        ),
        generated_token_ids=tuple(tokens),
        stop_reason="eos",
        counters={"instructions.retired": 10},
        quantities=tuple(quantities),
        failure=failure,
    )


def test_comparison_admits_two_targets_that_agree():
    left = _record(target_id="hbm", deployment_digest="aa")
    right = _record(target_id="rom", deployment_digest="bb")
    assert check_comparable(left, right) == []
    body = build_comparison(left, right, comparison_id="c1")
    assert body["token_agreement"]["identical"] is True
    assert body["depends_on_assumption"] is False


def test_comparison_refuses_mixed_evidence_classes():
    left = _record(deployment_digest="aa")
    right = _record(deployment_digest="bb", evidence=EvidenceClass.CYCLE)
    with pytest.raises(ComparisonError, match="evidence classes differ"):
        build_comparison(left, right, comparison_id="c")


def test_comparison_refuses_a_different_workload():
    left = _record(deployment_digest="aa")
    right = _record(deployment_digest="bb", workload_digest="other")
    with pytest.raises(ComparisonError, match="workload identity differs"):
        build_comparison(left, right, comparison_id="c")


def test_comparison_refuses_to_cross_technology_views():
    left = _record(deployment_digest="aa", technology_view="view-x")
    right = _record(deployment_digest="bb", technology_view="view-y")
    with pytest.raises(ComparisonError, match="technology views differ"):
        build_comparison(left, right, comparison_id="c")


def test_comparison_refuses_when_tokens_diverge():
    left = _record(deployment_digest="aa", tokens=(1, 2, 3))
    right = _record(deployment_digest="bb", tokens=(1, 9, 3))
    with pytest.raises(ComparisonError, match="different token sequences"):
        build_comparison(left, right, comparison_id="c")


def test_comparison_refuses_a_failed_execution():
    left = _record(deployment_digest="aa")
    right = _record(deployment_digest="bb", failure="engine trap")
    with pytest.raises(ComparisonError, match="failed execution"):
        build_comparison(left, right, comparison_id="c")


def test_comparison_labels_dependence_on_an_assumption():
    assumed = Quantity("link_bandwidth", 900.0, "GB/s", Provenance.ASSUMED, "estimate")
    left = _record(deployment_digest="aa", quantities=(assumed,))
    right = _record(deployment_digest="bb")
    body = build_comparison(left, right, comparison_id="c")
    assert body["depends_on_assumption"] is True


def test_token_legitimacy_rejects_an_interior_eos():
    problems = check_token_legitimacy(
        [1, 2, 15, 3], vocabulary_size=16, eos_token_ids=[15], stop_reason="eos"
    )
    assert any("interior positions" in p for p in problems)


def test_token_legitimacy_requires_eos_last_when_stop_reason_is_eos():
    problems = check_token_legitimacy(
        [1, 2, 3], vocabulary_size=16, eos_token_ids=[15], stop_reason="eos"
    )
    assert any("not\nin the authenticated EOS set" in p or "EOS set" in p for p in problems)


def test_token_legitimacy_accepts_a_clean_sequence():
    assert (
        check_token_legitimacy(
            [1, 2, 15], vocabulary_size=16, eos_token_ids=[15], stop_reason="eos"
        )
        == []
    )

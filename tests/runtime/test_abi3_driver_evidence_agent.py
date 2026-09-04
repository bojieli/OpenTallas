"""Tests for the host driver, the evidence gate and the agent sandbox."""

from __future__ import annotations

import pytest

from runtime.abi3.constants import StorageClass
from runtime.abi3.fixture import FIXTURE_VOCAB, build_fixture, fixture_capability
from runtime.abi3.records import EosReason
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
    assert driver.vocabulary_size == FIXTURE_VOCAB
    assert driver.eos_token_ids == (FIXTURE_VOCAB - 1,)


def test_driver_rejects_an_empty_prompt():
    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    with pytest.raises(DriverError):
        driver.generate([])


def test_driver_rejects_an_out_of_vocabulary_prompt_token():
    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    with pytest.raises(DriverError):
        driver.generate([FIXTURE_VOCAB + 991])


def test_driver_binds_every_frozen_runtime_symbol():
    """All fifteen of section 12.2, not the nine a request happens to carry.

    Four registry entries -- ``ACTIVE_EXPERT_COUNT``, ``SPARSE_INDEX_COUNT``,
    ``LAYER_COUNT`` and ``VOCABULARY_PARTITIONS`` -- were in the frozen
    registry and bound by nothing, so a loop bound or a view term naming one
    resolved to "symbol ... is unbound" at the moment it was read.  A frozen
    registry entry no implementation binds is not a registry entry; it is a
    trap waiting for the first program that uses it.
    """
    from runtime.abi3.descriptors import Symbol
    from runtime.sim.engines import load_engines

    load_engines()
    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    prompt = [1, 2, 3]
    result = driver.generate(prompt, max_new_tokens=1)
    assert result.failure is None, result.failure
    assert result.stop_reason == "max_new_tokens"
    assert len(result.generated_token_ids) == 1
    assert result.per_step[-1]["eos_reason"] == EosReason.MAX_NEW_TOKENS

    # Every symbol the registry defines is bound before the device sees the
    # request, and the device adds nothing that was missing.
    request = dict(driver.deployment_symbols)
    request.update(
        {
            int(Symbol.SPAN_TOKENS): len(prompt),
            int(Symbol.POSITION_START): 0,
            int(Symbol.POSITION_END): len(prompt),
            int(Symbol.CONTEXT_LENGTH): len(prompt),
            int(Symbol.PHASE): 0,
            int(Symbol.MAX_NEW_TOKENS): 1,
            int(Symbol.BATCH): 1,
            int(Symbol.GENERATION_INDEX): 0,
            int(Symbol.SPAN_LAST_INDEX): len(prompt) - 1,
        }
    )
    assert set(request) == {int(symbol) for symbol in Symbol}
    assert len(request) == 15
    assert device.last_request_descriptor is not None
    assert device.last_request_descriptor.symbol_map() == request
    assert device.last_request_descriptor.session_id == 1
    assert device.last_request_descriptor.transaction_id == 1
    assert device.live_request_descriptor_count == 0


def test_driver_retains_raw_completion_ticks_with_the_token_result():
    """Gate-2 timing must originate in the Gate-1 token transactions."""

    from runtime.sim.engines import load_engines

    load_engines()
    device, _ = _fixture_device()
    result = GenerationDriver(device).generate([1, 2, 3], max_new_tokens=3)

    assert result.failure is None
    assert result.request_start_tick == 0
    assert len(result.per_step) == len(result.generated_token_ids)
    commits = [step["completion_timestamp"] for step in result.per_step]
    assert commits
    assert commits[0] > result.request_start_tick
    assert all(right > left for left, right in zip(commits, commits[1:]))
    body = result.to_dict()
    assert body["request_start_tick"] == result.request_start_tick
    assert [step["completion_timestamp"] for step in body["per_step"]] == commits


def test_driver_reads_the_deployment_scalars_rather_than_inventing_them():
    """The six a request does not carry come off the deployment's descriptors.

    The fixture routes nothing, has no sparse attention and no partitioned
    vocabulary, so the honest values are the ones that say those things do not
    exist -- not a plausible number the host made up.
    """
    from runtime.abi3.descriptors import Symbol

    device, _ = _fixture_device()
    driver = GenerationDriver(device)
    bound = driver.deployment_symbols
    assert bound[int(Symbol.NODE_COUNT)] == device.node_count
    assert bound[int(Symbol.NODE_ID)] == 0
    assert bound[int(Symbol.ACTIVE_EXPERT_COUNT)] == 0
    assert bound[int(Symbol.SPARSE_INDEX_COUNT)] == 0
    assert bound[int(Symbol.VOCABULARY_PARTITIONS)] == 1


def test_driver_refuses_a_symbol_the_program_names_and_the_deployment_omits():
    """A named symbol nothing defines is a refusal, not a default.

    Binding a made-up value for a symbol the program actually reads is the
    silent wrong answer this boundary exists to prevent, so the driver says
    which symbol and why instead.
    """
    from runtime.abi3.descriptors import ExtendedDescriptorType, SelectorKind, Symbol

    device, _ = _fixture_device()
    # Point one loop's bound at a symbol the fixture states no value for.
    for descriptor in device.deployment.table.descriptors():
        if descriptor.descriptor_type == ExtendedDescriptorType.LOOP_CONTROL:
            descriptor.payload["bound_selector_kind"] = int(
                SelectorKind.RUNTIME_SYMBOL
            )
            descriptor.payload["bound_symbol_id"] = int(Symbol.SPARSE_INDEX_COUNT)
            break
    else:
        pytest.skip("the fixture declares no loop to retarget")
    with pytest.raises(DriverError, match="SPARSE_INDEX_COUNT"):
        GenerationDriver(device)


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
    generation_policy=None,
):
    # A comparison of two token streams is meaningless without knowing the two
    # runs stopped by the same rule, so the gate refuses a record that carries
    # no generation policy.  These fixtures predate that rule and were passing
    # by omission; every real record carries one.
    if generation_policy is None:
        generation_policy = {
            "selection_mode": "greedy_argmax_lowest_id",
            "tie_rule": "lowest_token_id",
            "eos_count": 1,
            "eos_token_0": 511,
            "vocabulary_size": 512,
        }
    return ExecutionRecord(
        evidence_class=evidence,
        workload=WorkloadIdentity(
            model_id="m",
            workload_id="w",
            workload_digest=workload_digest,
            prompt_token_count=4,
            max_new_tokens=8,
            generation_policy_digest="gp",
            generation_policy=dict(generation_policy),
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


def test_technology_views_may_differ_for_tokens_and_may_not_for_characterised_numbers():
    """The rule is about characterised numbers, not about tokens.

    Memory technology is this study's independent variable: a ROM target and an
    HBM target *have* to declare different technology views, and refusing that
    outright forbade the very comparison this module exists to govern. What may
    never cross a view is a number characterised against one -- synthesis, place
    and route, SPICE -- because such a number means nothing outside the view it
    was measured in. A functional token comparison carries no such number.
    """

    left = _record(deployment_digest="aa", technology_view="single_chip_rom_declared_v1")
    right = _record(deployment_digest="bb", technology_view="shared-hbm-sram-chip-v3")
    body = build_comparison(left, right, comparison_id="c")
    assert body["token_agreement"]["identical"] is True

    characterised = _record(
        deployment_digest="cc",
        technology_view="single_chip_rom_declared_v1",
        evidence=EvidenceClass.SYNTHESIS,
    )
    other_view = _record(
        deployment_digest="dd",
        technology_view="shared-hbm-sram-chip-v3",
        evidence=EvidenceClass.SYNTHESIS,
    )
    with pytest.raises(ComparisonError, match="technology views differ"):
        build_comparison(characterised, other_view, comparison_id="c")


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

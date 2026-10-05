"""The DeepSeek-V4.1-Flash workload set: declared length, identity and digest.

Three things are pinned here, one per sentence of WP-I.

*Declared length and declared identity.*  Every workload's id, kind, prompt
token count and generation horizon is written out as a literal below, and both
the materialised documents and a fresh build are required to reproduce the
table.  A workload is an input to every later gate, so a silent change to one of
these numbers would change what every comparison built on it was comparing.

*A reproducible digest.*  The digest is recomputed from the document's own
fields rather than read out of it, and the same rule is required to hold in the
V4 and Qwen modules, so a report can carry all three families under one identity
rule.

*Section 10's set and no more.*  The declared set is exactly
``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` section 10's four
families.  A test that only checked the workloads that exist would not notice a
missing one, so the set itself is asserted.

Nothing here executes a model.  The V4.1 targets do not exist yet (WP-E, WP-F,
WP-G) and neither does the oracle (WP-H); a workload is complete when it
constructs the right token sequences under a reproducible identity, which is
what is checked.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from compiler.frontend.deepseek_v41_tokenizer import (
    ADDED_TOKEN_DELTA,
    NON_SPECIAL_IN_V41,
    TOKENIZER_SHA256,
    DeepSeekV41TokenizerError,
    load_verified_deepseek_v41_tokenizer,
    release_record_pins,
)
from compiler.workloads import deepseek_v4 as v4_module
from compiler.workloads import qwen3 as qwen_module
from compiler.workloads.deepseek_v41 import (
    AGENT_MESSAGES,
    AGENT_SHELL_COMMAND,
    CONTEXT_LADDER,
    LONG_PROMPT_TOKENS,
    MODEL_ID,
    PREFIX_MAX_NEW_TOKENS,
    PREFIX_PROMPT_TOKENS,
    WORKLOAD_ID_PREFIX,
    DeepSeekV41WorkloadError,
    Workload,
    _ladder_id,
    build_chat_prefix_workload,
    build_workloads,
    index_document,
    resolve_identity,
)

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools" / "build_deepseek_v41_workloads.py"
PREFIX_BUILDER = ROOT / "tools" / "build_deepseek_v41_prefix_workloads.py"
ACCEPTANCE_DIR = ROOT / "build" / "workloads" / MODEL_ID
PREFIX_DIR = ROOT / "build" / "workloads" / f"{MODEL_ID}-prefix"
PINS = ROOT / "results" / "abi3" / "deepseek_v41_workload_pins.json"

#: Every V4.1 acceptance workload identity, as
#: ``tools/build_deepseek_v41_workloads.py`` produces it.  This table is the
#: hard invariant of WP-I.
LADDER: dict[str, tuple[str, int, int, str]] = {
    "TA-DS41-AGENT-1": (
        "agent",
        444,
        256,
        "fc7fad07376621f4defb9cf833b080238dd4e20a22a7f436b933e9f59c064b5e",
    ),
    "TA-DS41-CHAT-1": (
        "chat",
        104,
        512,
        "41fe4f024c7e98cf4b75916766726ba0f4451a533ac21967bfa69a964553d709",
    ),
    "TA-DS41-CHAT-1-P32": (
        "chat_prefix",
        32,
        4,
        "d02515463a5073dbbc37b3b10c5e10eb7ca4947f1c0672d627cdffe838e74a61",
    ),
    "TA-DS41-CTX-128K-1": (
        "long_natural",
        128_000,
        256,
        "e82c88dcf30c8951d14a3b5eb6d29a704645f065c713f6bc197f7748d52425bd",
    ),
    "TA-DS41-CTX-1K-1": (
        "long_natural",
        1_000,
        256,
        "34f87333671928ad4a14efe6b9442b53dcae47a6e4c05e1ea205d4fbae609281",
    ),
    "TA-DS41-CTX-200K-1": (
        "long_natural",
        200_000,
        256,
        "8895f768adda9d31b8b6809bd01f32d4a6a2cae646177d74d9eac8810fe670a0",
    ),
    "TA-DS41-CTX-32K-1": (
        "long_natural",
        32_000,
        256,
        "09c28b40a021515bc3d30bb4e5975cef2f688b04ac45acd75265744d17264100",
    ),
    "TA-DS41-CTX-8K-1": (
        "long_natural",
        8_000,
        256,
        "23fe1dee9c4a565cf26a6bdde9d8884cb028b9ea320232e433ce75dc845ac5bd",
    ),
    "TA-DS41-EOS-1": (
        "chat",
        8,
        16,
        "9b96672450c5c125b41d0a064c5dde8e46d8551a4ca289ec22f4b1d2a1106b26",
    ),
}

#: The sub-gate bisection prefixes, which are deliberately *not* in the
#: acceptance set.
SUB_GATE_LADDER: dict[str, tuple[str, int, int, str]] = {
    "TA-DS41-CHAT-1-P8": (
        "chat_prefix",
        8,
        4,
        "d0d4a5ca6a4ce3db1433d45253f3a62db641bed9d69f31e1780befcbba538afc",
    ),
}

#: The four families of plan section 10, by the workload that carries each.
PLAN_SECTIONS = {
    "TA-DS41-CHAT-1-P32": "10.1",
    "TA-DS41-EOS-1": "10.2",
    "TA-DS41-CTX-200K-1": "10.3",
    "TA-DS41-AGENT-1": "10.4",
}

#: Workloads that need no corpus window, so a test can rebuild them in seconds.
CHEAP_KINDS = {"chat", "agent", "chat_prefix"}

#: ``TA-DS41-`` id -> the ``TA-DS-`` id whose prompt token integers it equals.
V4_EQUIVALENCE = {
    "TA-DS41-CHAT-1": "TA-DS-CHAT-1",
    **{
        f"TA-DS41-CTX-{rung // 1000}K-1": f"TA-DS-CTX-{rung // 1000}K-1"
        for rung in CONTEXT_LADDER
    },
}

DOCUMENT_KEYS = {
    "workload_id",
    "kind",
    "description",
    "digest",
    "prompt_token_count",
    "max_new_tokens",
    "rendered_text_sha256",
    "token_ids",
    "rendered_text",
    "metadata",
}


def _built(directory: Path, tool: Path) -> Path:
    if not (directory / "index.json").is_file():
        pytest.skip(f"no built workloads at {directory}; run {tool.name}")
    return directory


def _snapshot() -> Path:
    identity = resolve_identity()
    owner, name = identity.repository.split("/", 1)
    snapshot = (
        Path.home()
        / ".cache/huggingface/hub"
        / f"models--{owner}--{name}"
        / "snapshots"
        / identity.revision
    )
    if not (snapshot / "tokenizer.json").is_file():
        pytest.skip(f"no local V4.1 tokenizer snapshot at {snapshot}")
    return snapshot


def _tokenizer():  # noqa: ANN202
    return load_verified_deepseek_v41_tokenizer(_snapshot())


def _renderer(snapshot: Path):  # noqa: ANN202
    """The released renderer, imported the way the builder imports it."""

    directory = str(snapshot / "encoding")
    if not (snapshot / "encoding" / "encoding.py").is_file():
        pytest.skip(f"no released renderer at {directory}")
    if directory not in sys.path:
        sys.path.insert(0, directory)
    import encoding as vendor  # noqa: PLC0415

    return vendor.encode_messages


def _encode_prompt(tokenizer, render):  # noqa: ANN001, ANN202
    def encode_prompt(messages, thinking_mode):  # noqa: ANN001
        text = render(messages, thinking_mode=thinking_mode)
        return text, tokenizer.encode(text, enforce_max_length=False)

    return encode_prompt


def _validate_document(document: dict) -> None:
    """The workload-document schema: ``Workload.to_dict`` is the definition."""

    assert set(document) == DOCUMENT_KEYS
    assert isinstance(document["workload_id"], str) and document["workload_id"]
    assert isinstance(document["kind"], str) and document["kind"]
    assert isinstance(document["description"], str) and document["description"]
    assert isinstance(document["max_new_tokens"], int)
    assert document["max_new_tokens"] > 0
    assert isinstance(document["metadata"], dict)
    assert isinstance(document["rendered_text"], str)

    token_ids = document["token_ids"]
    assert isinstance(token_ids, list) and token_ids
    assert all(isinstance(value, int) for value in token_ids)
    assert all(0 <= value < 129_280 for value in token_ids)
    assert document["prompt_token_count"] == len(token_ids)

    assert document["rendered_text_sha256"] == hashlib.sha256(
        document["rendered_text"].encode()
    ).hexdigest()
    rebuilt = Workload(
        workload_id=document["workload_id"],
        kind=document["kind"],
        description=document["description"],
        rendered_text=document["rendered_text"],
        token_ids=tuple(token_ids),
        max_new_tokens=document["max_new_tokens"],
    )
    assert rebuilt.digest == document["digest"]


# ---------------------------------------------------------------------------
# The declared set
# ---------------------------------------------------------------------------
def test_the_declared_set_is_plan_section_10s_and_nothing_more() -> None:
    """Section 10's four families, the reporting ladder, and no stress rung."""

    assert WORKLOAD_ID_PREFIX == "TA-DS41"
    assert MODEL_ID == "deepseek-v4.1-flash"
    assert LONG_PROMPT_TOKENS == 200_000
    assert CONTEXT_LADDER == (1_000, 8_000, 32_000, 128_000, LONG_PROMPT_TOKENS)
    expected = {
        f"{WORKLOAD_ID_PREFIX}-CHAT-1",
        f"{WORKLOAD_ID_PREFIX}-CHAT-1-P{PREFIX_PROMPT_TOKENS}",
        f"{WORKLOAD_ID_PREFIX}-AGENT-1",
        f"{WORKLOAD_ID_PREFIX}-EOS-1",
        *(_ladder_id(rung) for rung in CONTEXT_LADDER),
    }
    assert set(LADDER) == expected
    assert set(PLAN_SECTIONS) <= set(LADDER)
    # V4's stress workload is not inherited; section 10 does not ask for one.
    assert not any("STRESS" in workload_id for workload_id in LADDER)


def test_the_ladder_ids_name_their_own_lengths() -> None:
    assert _ladder_id(1_000) == "TA-DS41-CTX-1K-1"
    assert _ladder_id(LONG_PROMPT_TOKENS) == "TA-DS41-CTX-200K-1"
    assert _ladder_id(129) == "TA-DS41-CTX-129-1"
    for rung in CONTEXT_LADDER:
        kind, tokens, _horizon, _digest = LADDER[_ladder_id(rung)]
        assert (kind, tokens) == ("long_natural", rung)


def test_the_gate_workload_is_the_prefix_and_carries_its_own_horizon() -> None:
    """Plan section 10.1: 32 prompt tokens, 4 greedy tokens."""

    kind, tokens, horizon, _digest = LADDER[
        f"{WORKLOAD_ID_PREFIX}-CHAT-1-P{PREFIX_PROMPT_TOKENS}"
    ]
    assert (kind, tokens, horizon) == (
        "chat_prefix",
        PREFIX_PROMPT_TOKENS,
        PREFIX_MAX_NEW_TOKENS,
    )
    assert PREFIX_PROMPT_TOKENS == 32
    assert PREFIX_MAX_NEW_TOKENS == 4


def test_the_agent_transcript_is_multi_turn_and_reads_its_own_sandbox() -> None:
    """Plan section 10.4 asks for a transcript, not a tool-call opportunity."""

    roles = [message["role"] for message in AGENT_MESSAGES]
    assert roles == ["system", "user", "assistant", "tool"]
    assert AGENT_MESSAGES[0]["tools"]
    assert AGENT_MESSAGES[2]["tool_calls"]
    # The command is derived from the sandbox, so it cannot name a file the
    # sandbox does not contain.
    sandbox = v4_module.AGENT_SANDBOX_FILES
    assert len(sandbox) == 1
    assert AGENT_SHELL_COMMAND.endswith(next(iter(sandbox)))
    assert AGENT_MESSAGES[3]["content"] == next(iter(sandbox.values()))


# ---------------------------------------------------------------------------
# The committed build
# ---------------------------------------------------------------------------
def test_the_built_index_matches_the_pinned_identities() -> None:
    directory = _built(ACCEPTANCE_DIR, BUILDER)
    index = json.loads((directory / "index.json").read_text())
    identity = resolve_identity()
    assert index["schema"] == "opentallas.workload_index.v1"
    assert index["model_id"] == MODEL_ID == identity.model_id
    assert index["source"]["repository"] == identity.repository
    assert index["source"]["revision"] == identity.revision
    assert index["source"]["config_sha256"] == identity.config_sha256
    assert index["mandatory_context_tokens"] == LONG_PROMPT_TOKENS
    assert index["context_ladder"] == list(CONTEXT_LADDER)
    assert index["context_bound"] == identity.context_bound
    assert index["tokenizer"]["source"]["tokenizer_sha256"] == TOKENIZER_SHA256
    observed = {
        workload_id: (
            entry["kind"],
            entry["prompt_token_count"],
            entry["max_new_tokens"],
            entry["digest"],
        )
        for workload_id, entry in index["workloads"].items()
    }
    assert observed == LADDER


def test_every_workload_document_validates_against_the_schema() -> None:
    directory = _built(ACCEPTANCE_DIR, BUILDER)
    index = json.loads((directory / "index.json").read_text())
    for workload_id, entry in sorted(index["workloads"].items()):
        document = json.loads((directory / entry["path"]).read_text())
        _validate_document(document)
        assert document["workload_id"] == workload_id
        assert document["digest"] == entry["digest"]
        assert document["kind"] == entry["kind"]
        assert document["prompt_token_count"] == entry["prompt_token_count"]
        assert document["max_new_tokens"] == entry["max_new_tokens"]


def test_each_plan_family_document_names_its_section() -> None:
    directory = _built(ACCEPTANCE_DIR, BUILDER)
    for workload_id, section in sorted(PLAN_SECTIONS.items()):
        document = json.loads((directory / f"{workload_id}.json").read_text())
        assert document["metadata"]["plan_section"] == section


def test_the_mandatory_rung_names_its_counter_authority_without_copying_it() -> None:
    """Plan section 10.3's arithmetic is referenced, never mirrored.

    A second copy of the per-position KV bytes, the owner layers or the scan
    widths inside a workload document is exactly the mirrored-constant defect
    this program keeps paying for, so the document names the files and keys the
    checker must read and carries no figure of its own.
    """

    directory = _built(ACCEPTANCE_DIR, BUILDER)
    document = json.loads((directory / "TA-DS41-CTX-200K-1.json").read_text())
    metadata = document["metadata"]
    assert metadata["mandatory_contract"] is True
    authority = metadata["counter_authority"]
    assert authority["profile"] == "configs/models/candidates/deepseek-v4.1-flash.json"
    assert "metadata.global_kv_bytes_per_token" in authority["profile_keys"]
    assert "text_config.kv_source_layer_ids" in authority["released_config_keys"]
    flattened = json.dumps(authority)
    for figure in ("890", "16384", "16,384"):
        assert figure not in flattened
    # And every non-mandatory rung stays silent about it.
    for rung in CONTEXT_LADDER[:-1]:
        other = json.loads((directory / f"{_ladder_id(rung)}.json").read_text())
        assert "counter_authority" not in other["metadata"]


def test_the_eos_workload_does_not_claim_a_gold_it_has_not_seen() -> None:
    """The G1 prompt is pinned; that its gold ends in EOS is WP-H's to decide."""

    directory = _built(ACCEPTANCE_DIR, BUILDER)
    document = json.loads((directory / "TA-DS41-EOS-1.json").read_text())
    metadata = document["metadata"]
    assert metadata["gate"] == "G1"
    assert metadata["gold_status"].startswith("unverified")
    assert "40 layers" in metadata["reduced_model_contract"]
    # The question itself is the program's existing G1 question, not a new one.
    assert qwen_module.EOS_QUESTION in document["rendered_text"]


# ---------------------------------------------------------------------------
# A reproducible digest
# ---------------------------------------------------------------------------
def test_rebuilding_reproduces_the_pinned_identities() -> None:
    """The builder, not only the artifact, still produces this set.

    The corpus-free workloads plus the cheapest ladder rung are rebuilt; the
    long rungs are covered by the committed documents above, whose digests are
    recomputed from their own token IDs rather than read.
    """

    snapshot = _snapshot()
    tokenizer = _tokenizer()
    built = build_workloads(
        tokenizer, _encode_prompt(tokenizer, _renderer(snapshot)), ladder=(1_000,)
    )
    expected = {
        workload_id
        for workload_id, (kind, tokens, *_rest) in LADDER.items()
        if kind in CHEAP_KINDS or tokens == 1_000
    }
    assert set(built) == expected
    for workload_id, workload in built.items():
        kind, tokens, horizon, digest = LADDER[workload_id]
        assert (workload.kind, len(workload.token_ids)) == (kind, tokens)
        assert workload.max_new_tokens == horizon
        assert workload.digest == digest
    document = index_document(built)
    assert document["model_id"] == MODEL_ID
    assert document["source"]["revision"] == resolve_identity().revision


def test_the_digest_rule_is_the_one_the_other_two_families_use() -> None:
    """One identity rule across Qwen, V4 and V4.1, checked on one input."""

    fields = {
        "workload_id": "TA-XX-PROBE-1",
        "kind": "chat",
        "description": "a probe",
        "rendered_text": "probe",
        "token_ids": (1, 2, 3),
        "max_new_tokens": 7,
    }
    digests = {
        cls(**fields).digest
        for cls in (Workload, v4_module.Workload, qwen_module.Workload)
    }
    assert len(digests) == 1
    baseline = Workload(**fields).digest
    # And the rule covers the id, the kind, the tokens and the horizon - so two
    # prompts that differ in any of them cannot share an identity.
    for key, value in (
        ("workload_id", "TA-XX-PROBE-2"),
        ("kind", "agent"),
        ("token_ids", (1, 2, 4)),
        ("max_new_tokens", 8),
    ):
        assert Workload(**{**fields, key: value}).digest != baseline, key
    # The description is deliberately outside the digest: prose about a workload
    # is not part of what a comparison compares.
    assert Workload(**{**fields, "description": "other prose"}).digest == baseline


def test_a_second_build_is_byte_identical() -> None:
    """A workload is reproducible or it is not an identity."""

    directory = _built(ACCEPTANCE_DIR, BUILDER)
    with tempfile.TemporaryDirectory() as tmp:
        completed = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--ladder",
                "1000",
                "--output",
                tmp,
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        for workload_id in ("TA-DS41-CHAT-1-P32", "TA-DS41-CTX-1K-1", "TA-DS41-EOS-1"):
            again = (Path(tmp) / f"{workload_id}.json").read_bytes()
            assert again == (directory / f"{workload_id}.json").read_bytes()


# ---------------------------------------------------------------------------
# The prefix is an honest prefix
# ---------------------------------------------------------------------------
def test_the_gate_prefix_is_a_genuine_prefix_of_its_parent() -> None:
    directory = _built(ACCEPTANCE_DIR, BUILDER)
    parent = json.loads((directory / "TA-DS41-CHAT-1.json").read_text())
    prefix = json.loads(
        (directory / f"TA-DS41-CHAT-1-P{PREFIX_PROMPT_TOKENS}.json").read_text()
    )
    assert prefix["token_ids"] == parent["token_ids"][:PREFIX_PROMPT_TOKENS]
    assert parent["rendered_text"].startswith(prefix["rendered_text"])
    derived = prefix["metadata"]["derived_from"]
    assert derived["workload_id"] == "TA-DS41-CHAT-1"
    assert derived["digest"] == parent["digest"]
    assert derived["rule"] == "token_ids[:prefix_tokens]"
    assert prefix["digest"] != parent["digest"]


def test_the_sub_gate_prefixes_are_not_in_the_acceptance_set() -> None:
    directory = _built(PREFIX_DIR, PREFIX_BUILDER)
    index = json.loads((directory / "index.json").read_text())
    assert index["acceptance_set"] is False
    assert index["gate_prefix_tokens"] == PREFIX_PROMPT_TOKENS
    observed = {
        workload_id: (
            entry["kind"],
            entry["prompt_token_count"],
            entry["max_new_tokens"],
            entry["digest"],
        )
        for workload_id, entry in index["workloads"].items()
    }
    assert observed == SUB_GATE_LADDER
    assert set(SUB_GATE_LADDER).isdisjoint(LADDER)
    for workload_id, entry in sorted(index["workloads"].items()):
        _validate_document(json.loads((directory / entry["path"]).read_text()))
        assert entry["prompt_token_count"] < PREFIX_PROMPT_TOKENS


def test_a_sub_gate_rung_at_the_gate_is_refused() -> None:
    completed = subprocess.run(
        [sys.executable, str(PREFIX_BUILDER), "--tokens", str(PREFIX_PROMPT_TOKENS)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        check=False,
    )
    assert completed.returncode != 0
    assert "at or above plan section 10.1" in completed.stderr


# ---------------------------------------------------------------------------
# One prompt, two models
# ---------------------------------------------------------------------------
def test_v41_prompts_carry_v4s_token_ids_under_their_own_identity() -> None:
    """The same prompt integers, a different identity - and not the same gold.

    V4.1 renders a plain chat turn byte-identically to V4 and keeps V4's base
    vocabulary and merges, so these prompts are the same integers on both sides.
    That makes the two models' runs comparable.  It does not make V4's gold
    V4.1's gold, which is why the digests are required to differ.
    """

    v41_dir = _built(ACCEPTANCE_DIR, BUILDER)
    v4_dir = ROOT / "build" / "workloads" / "deepseek-v4-flash-0731"
    if not (v4_dir / "index.json").is_file():
        pytest.skip(
            f"no built V4 workloads at {v4_dir}; run "
            "tools/build_deepseek_v4_workloads.py"
        )
    for v41_id, v4_id in sorted(V4_EQUIVALENCE.items()):
        v41 = json.loads((v41_dir / f"{v41_id}.json").read_text())
        v4 = json.loads((v4_dir / f"{v4_id}.json").read_text())
        assert v41["token_ids"] == v4["token_ids"], v41_id
        assert v41["rendered_text"] == v4["rendered_text"], v41_id
        assert v41["digest"] != v4["digest"], v41_id
    # The agent transcript is the counter-example: V4.1's DSML tag names are not
    # V4's, so that prompt is genuinely different.
    v41_agent = json.loads((v41_dir / "TA-DS41-AGENT-1.json").read_text())
    v4_agent = json.loads((v4_dir / "TA-DS-AGENT-1.json").read_text())
    assert v41_agent["token_ids"] != v4_agent["token_ids"]
    assert "<｜DSML｜ calls>" in v41_agent["rendered_text"]


# ---------------------------------------------------------------------------
# Identity and the tokenizer boundary
# ---------------------------------------------------------------------------
def test_identity_comes_from_two_committed_documents_that_agree() -> None:
    identity = resolve_identity()
    assert identity.model_id == MODEL_ID
    assert identity.repository == "deepseek-ai/DeepSeek-V4.1-Flash"
    assert identity.authority == (
        "configs/models/candidates/deepseek-v4.1-flash.json",
        "data/inventory/deepseek-v4.1-flash.json",
    )
    profile = json.loads((ROOT / identity.authority[0]).read_text())
    inventory = json.loads((ROOT / identity.authority[1]).read_text())
    assert identity.revision == profile["source_revision"] == inventory["revision"]
    assert identity.config_sha256 == inventory["config_sha256"]
    assert identity.context_bound == profile["max_context_tokens"]
    assert max(CONTEXT_LADDER) <= identity.context_bound


def test_a_release_record_if_present_agrees_with_the_committed_documents() -> None:
    """WP-B's record is corroboration, not a dependency - but it must agree."""

    identity = resolve_identity()
    if identity.release_record is None:
        pytest.skip("no V4.1 release record resolves yet (WP-B)")
    from compiler.frontend.deepseek_v4_releases import resolve_release

    record = resolve_release(identity.release_record)
    assert record.repository == identity.repository
    assert record.revision == identity.revision
    assert record.config_sha256 == identity.config_sha256
    assert int(record.scalar("max_position_embeddings")) == identity.context_bound


def test_the_tokenizer_is_v4s_outside_nine_added_tokens() -> None:
    """The structural proof the V4.1 boundary rests on, restated as a test."""

    report = _tokenizer().validation_report
    proof = report["structural_proof_against_v4"]
    assert proof["base_vocabulary_entries"] == 128_000
    assert proof["merges"] == 127_741
    assert set(proof["changed_added_tokens"]) == {
        str(token_id) for token_id in ADDED_TOKEN_DELTA
    }
    assert len(ADDED_TOKEN_DELTA) == 9
    assert "model" in proof["token_id_bearing_keys_identical"]
    # The one entry that is more than a rename, and what it costs.
    assert proof["non_special_in_v41"] == NON_SPECIAL_IN_V41 == 128_799
    assert ADDED_TOKEN_DELTA[NON_SPECIAL_IN_V41]["v4"]["special"] is True
    assert ADDED_TOKEN_DELTA[NON_SPECIAL_IN_V41]["v4.1"]["special"] is False
    assert ADDED_TOKEN_DELTA[NON_SPECIAL_IN_V41]["v4.1"]["content"] == "<｜System｜>"


def test_the_released_config_tokens_are_read_and_not_inherited() -> None:
    """V4.1's ``pad_token_id`` is 2 where V4's is 1; nothing may inherit it."""

    from compiler.frontend.deepseek_v4_tokenizer import PAD_TOKEN_ID as V4_PAD

    tokenizer = _tokenizer()
    assert tokenizer.bos_token_id == 0
    assert tokenizer.eos_token_id == 1
    assert tokenizer.pad_token_id == 2
    assert tokenizer.pad_token_id != V4_PAD


def test_the_release_record_and_the_boundary_pin_one_tokenizer() -> None:
    pins = release_record_pins()
    if not pins["available"]:
        pytest.skip(f"no V4.1 release record: {pins.get('unavailable')}")
    assert pins["agreed"]["tokenizer_sha256"] == TOKENIZER_SHA256


def test_a_snapshot_that_is_not_the_pinned_revision_is_refused(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot()
    fake = tmp_path / "snapshot"
    fake.mkdir()
    (fake / "config.json").write_text('{"text_config": {}}')
    for name in ("tokenizer.json", "tokenizer_config.json"):
        (fake / name).write_bytes((snapshot / name).read_bytes())
    with pytest.raises(DeepSeekV41TokenizerError, match="which is not"):
        load_verified_deepseek_v41_tokenizer(fake)


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_a_ladder_past_the_context_bound_is_refused() -> None:
    beyond = resolve_identity().context_bound + 1
    with pytest.raises(DeepSeekV41WorkloadError, match="context bound"):
        build_workloads(object(), lambda *_: ("", []), ladder=(beyond,))


def test_a_prefix_longer_than_its_parent_is_refused() -> None:
    parent = Workload(
        workload_id="TA-DS41-CHAT-1",
        kind="chat",
        description="probe",
        rendered_text="ab",
        token_ids=(1, 2),
        max_new_tokens=4,
    )
    with pytest.raises(DeepSeekV41WorkloadError, match="cannot take a 3-token prefix"):
        build_chat_prefix_workload(parent, lambda ids: "ab", prefix_tokens=3)


def test_a_prefix_that_is_not_a_prefix_is_refused() -> None:
    parent = Workload(
        workload_id="TA-DS41-CHAT-1",
        kind="chat",
        description="probe",
        rendered_text="ab",
        token_ids=(1, 2),
        max_new_tokens=4,
    )
    with pytest.raises(DeepSeekV41WorkloadError, match="not a prefix"):
        build_chat_prefix_workload(parent, lambda ids: "zz", prefix_tokens=1)


def test_committed_documents_that_disagree_are_refused(tmp_path: Path) -> None:
    identity = resolve_identity()
    profile = json.loads((ROOT / identity.authority[0]).read_text())
    inventory = json.loads((ROOT / identity.authority[1]).read_text())
    inventory["revision"] = "0" * 40
    profile_path = tmp_path / "profile.json"
    inventory_path = tmp_path / "inventory.json"
    profile_path.write_text(json.dumps(profile))
    inventory_path.write_text(json.dumps(inventory))
    with pytest.raises(DeepSeekV41WorkloadError, match="disagree about which"):
        resolve_identity(profile_path=profile_path, inventory_path=inventory_path)


def test_a_missing_committed_document_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DeepSeekV41WorkloadError, match="missing at"):
        resolve_identity(profile_path=tmp_path / "absent.json")


# ---------------------------------------------------------------------------
# The pin record
# ---------------------------------------------------------------------------
def test_the_pin_record_claims_nothing_that_was_not_run() -> None:
    if not PINS.is_file():
        pytest.skip(f"no pin record at {PINS}; run {BUILDER.name} --pins")
    pins = json.loads(PINS.read_text())
    assert pins["schema"] == "opentallas.workload_pins.v1"
    assert pins["model_id"] == MODEL_ID
    assert pins["gate"] == "DS41-X4"
    assert pins["acceptance_set"] is True
    assert set(pins["not_a_claim"]) == {
        "accelerator_execution",
        "artifact_only_execution",
        "reference_oracle_gold",
        "timing_or_performance",
    }
    observed = {
        workload_id: (
            entry["kind"],
            entry["prompt_token_count"],
            entry["max_new_tokens"],
            entry["digest"],
        )
        for workload_id, entry in pins["workloads"].items()
    }
    assert observed == LADDER
    # The renderer is vendor code and the record says so rather than implying an
    # independent cross-check it does not have.
    assert pins["renderer"]["independent_crosscheck"] is False
    assert pins["renderer"]["module"] == "encoding/encoding.py"

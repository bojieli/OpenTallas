"""The DeepSeek-V4 token-ID workload ladders, one per release.

Two things are pinned here.  The first is that naming a second release did not
move the first: every Flash workload identity is written out below as a
literal, and both the committed documents and a fresh build are required to
reproduce it.  The second is that Pro has a ladder of its own, under ``TA-DSP``
ids, built from Pro's snapshot and Pro's checkpoint source.

The two releases ship the same ``tokenizer.json`` -- equal SHA-256, and
byte-identical under ``cmp`` -- so each rung's prompt token IDs are the same
integers on both sides.  Their identities are not, because the digest covers
the workload id, and ``test_shared_token_ids_do_not_share_an_identity`` is that
statement in executable form.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from compiler.frontend.deepseek_v4_encoding import (
    OFFICIAL_REPOSITORY as ENCODING_REPOSITORY,
    OFFICIAL_REVISION as ENCODING_REVISION,
)
from compiler.frontend.deepseek_v4_releases import (
    FLASH,
    PRO,
    DeepSeekV4ReleaseError,
)
from compiler.frontend.deepseek_v4_tokenizer import (
    VOCAB_SIZE,
    load_verified_deepseek_v4_tokenizer,
)
from compiler.workloads.deepseek_v4 import (
    CONTEXT_LADDER,
    DEFAULT_MODEL_ID,
    LONG_PROMPT_TOKENS,
    MODEL_ID,
    Workload,
    _ladder_id,
    build_workloads,
    index_document,
    workload_id_prefix,
)


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools" / "build_deepseek_v4_workloads.py"
WORKLOADS = ROOT / "build" / "workloads"
UNKNOWN_MODEL = "deepseek-v4-ultra-0901"

#: Every Flash workload identity, as it stands in the committed build.  These
#: are the hard invariant: the generalisation over releases is only correct if
#: it reproduces this table byte for byte.
FLASH_LADDER: dict[str, tuple[str, int, int, str]] = {
    "TA-DS-AGENT-1": (
        "agent",
        376,
        256,
        "0044a2560aae31da30b6540eb1b32d76f8c321e2adddb7212c1e954a728080c9",
    ),
    "TA-DS-CHAT-1": (
        "chat",
        104,
        512,
        "ee161c0614073a207c3dd08136357cf2317a25f9b6fd68a03c021359fc34f6b5",
    ),
    "TA-DS-CTX-128K-1": (
        "long_natural",
        128_000,
        256,
        "cf968b0d85987f936a2363d12aca6ff272a6b4dde752349efa80db8b74bc8c63",
    ),
    "TA-DS-CTX-1K-1": (
        "long_natural",
        1_000,
        256,
        "d6cadb742e205dc7871d058ee167cbe1d64fdb8a1535102278540ed44fafcab8",
    ),
    "TA-DS-CTX-200K-1": (
        "long_natural",
        200_000,
        256,
        "803f0c3a3e9bf7ef68ddff00947576d2fab5703d1f4387df1eb2ec11be2c59bd",
    ),
    "TA-DS-CTX-32K-1": (
        "long_natural",
        32_000,
        256,
        "0620c0ef1bb3061e86bef2a853f2b720602fdfa66fc9044cf0aec84b1fd44903",
    ),
    "TA-DS-CTX-8K-1": (
        "long_natural",
        8_000,
        256,
        "51883832f6bb16fce660a6cd68ce37ab6a0333ad3d32a255b15d6b1719298fe9",
    ),
    "TA-DS-STRESS-1": (
        "repeated_special",
        8_000,
        32,
        "55a732b8aa82f9da3024753f33ec808df5e3d432c53824e77a1924581a908816",
    ),
}

#: The same ladder under Pro's identity, produced by
#: ``tools/build_deepseek_v4_workloads.py --model deepseek-v4-pro-0813``.
PRO_LADDER: dict[str, tuple[str, int, int, str]] = {
    "TA-DSP-AGENT-1": (
        "agent",
        376,
        256,
        "40928af59fe0ae2e6e19c089d8f6195df1fcd98caf91ad445ad2920c1eb86f77",
    ),
    "TA-DSP-CHAT-1": (
        "chat",
        104,
        512,
        "4b1b10fa75e61c8f5d846ae0835495649f324dd0af6d7f5f6cbbced8340caaee",
    ),
    "TA-DSP-CTX-128K-1": (
        "long_natural",
        128_000,
        256,
        "be76b972071c606b97432fb7902d56b282fc661211c8792386119ccfce2fe35b",
    ),
    "TA-DSP-CTX-1K-1": (
        "long_natural",
        1_000,
        256,
        "216794cdd05bcdebc699220ca321b7a6c096ec0966552f0fc97911638f55c192",
    ),
    "TA-DSP-CTX-200K-1": (
        "long_natural",
        200_000,
        256,
        "53a4c95a607b5e95a5e0e6da14e2de146685a252417bbb9974377d735467bf9d",
    ),
    "TA-DSP-CTX-32K-1": (
        "long_natural",
        32_000,
        256,
        "58aed4621613fd49e8d781cb7a5827e45cda07687230e51fa114bbf63da92a5a",
    ),
    "TA-DSP-CTX-8K-1": (
        "long_natural",
        8_000,
        256,
        "4c5ff962a4b36f6cdfdc4d711b081d7c735ba8eb3c286468a41b744cab8992e9",
    ),
    "TA-DSP-STRESS-1": (
        "repeated_special",
        8_000,
        32,
        "9bffa2d54c9d259fa9dd11aaade3002e812cb8ecfe3a2f1c23c38f465b767f92",
    ),
}

LADDERS = {FLASH.model_id: FLASH_LADDER, PRO.model_id: PRO_LADDER}

#: The three workloads that need no corpus window, so a test can rebuild them
#: from the tokenizer in a second or two.
CHEAP_KINDS = {"chat", "agent", "repeated_special"}

#: ``Workload.to_dict``'s keys.  A materialised document carries these and
#: nothing else, whichever release built it.
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


def _built(model_id: str) -> Path:
    directory = WORKLOADS / model_id
    if not (directory / "index.json").is_file():
        pytest.skip(
            f"no built workloads at {directory}; run "
            f"tools/build_deepseek_v4_workloads.py --model {model_id}"
        )
    return directory


def _snapshot(release) -> Path:  # noqa: ANN001 - a DeepSeekV4Release
    if not (release.snapshot / "tokenizer.json").is_file():
        pytest.skip(f"no local tokenizer snapshot at {release.snapshot}")
    return release.snapshot


def _tokenizer(release):  # noqa: ANN001, ANN202
    return load_verified_deepseek_v4_tokenizer(_snapshot(release), release=release)


def _validate_document(document: dict) -> None:
    """The workload-document schema, applied to one materialised document.

    There is no JSON Schema file for a workload document; ``Workload.to_dict``
    is the definition, so this checks against it: the exact key set, the field
    types, and the three derived fields recomputed rather than trusted.
    """
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
    assert all(0 <= value < VOCAB_SIZE for value in token_ids)
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
# The Flash ladder is unchanged
# ---------------------------------------------------------------------------
def test_flash_is_still_the_default_release() -> None:
    assert DEFAULT_MODEL_ID == MODEL_ID == FLASH.model_id
    assert workload_id_prefix() == "TA-DS"
    assert workload_id_prefix(FLASH.model_id) == "TA-DS"


def test_flash_release_record_agrees_with_the_encoding_module_pin() -> None:
    """The two Flash pins that authenticate a snapshot must still agree.

    ``load_verified_deepseek_v4_tokenizer`` used to compare the checkpoint
    source against ``compiler.frontend.deepseek_v4_encoding``'s own Flash
    constants and now compares it against the release record. If those two
    drifted apart, the renderer and the tokenizer boundary would be
    authenticating different snapshots.
    """
    assert ENCODING_REPOSITORY == FLASH.repository
    assert ENCODING_REVISION == FLASH.revision


def test_committed_flash_ladder_matches_the_pinned_identities() -> None:
    directory = _built(FLASH.model_id)
    index = json.loads((directory / "index.json").read_text())
    assert index["model_id"] == FLASH.model_id
    assert index["source"] == {
        "repository": FLASH.repository,
        "revision": FLASH.revision,
    }
    assert index["tokenizer_sha256"] == FLASH.tokenizer_sha256
    assert index["mandatory_context_tokens"] == LONG_PROMPT_TOKENS
    assert index["context_ladder"] == list(CONTEXT_LADDER)
    observed = {
        workload_id: (
            entry["kind"],
            entry["prompt_token_count"],
            entry["max_new_tokens"],
            entry["digest"],
        )
        for workload_id, entry in index["workloads"].items()
    }
    assert observed == FLASH_LADDER


def test_rebuilding_flash_reproduces_the_pinned_identities() -> None:
    """The builder, not just the committed artifact, still produces Flash.

    Only the three corpus-free workloads are rebuilt here; the context ladder
    is covered by the committed documents above, and rebuilding a 200,000-token
    rung inside a unit test would cost minutes for an identity the same digest
    rule already pins.
    """
    tokenizer = _tokenizer(FLASH)
    built = build_workloads(tokenizer, ladder=())
    assert set(built) == {
        workload_id
        for workload_id, (kind, *_rest) in FLASH_LADDER.items()
        if kind in CHEAP_KINDS
    }
    for workload_id, workload in built.items():
        kind, tokens, max_new_tokens, digest = FLASH_LADDER[workload_id]
        assert (workload.kind, len(workload.token_ids)) == (kind, tokens)
        assert workload.max_new_tokens == max_new_tokens
        assert workload.digest == digest


# ---------------------------------------------------------------------------
# The Pro ladder exists, under its own identity
# ---------------------------------------------------------------------------
def test_pro_workload_ids_carry_the_pro_prefix() -> None:
    assert workload_id_prefix(PRO.model_id) == "TA-DSP"
    assert _ladder_id(200_000, "TA-DSP") == "TA-DSP-CTX-200K-1"
    assert _ladder_id(129, "TA-DSP") == "TA-DSP-CTX-129-1"
    assert set(FLASH_LADDER).isdisjoint(PRO_LADDER)


def test_committed_pro_ladder_covers_the_same_rungs_as_flash() -> None:
    directory = _built(PRO.model_id)
    index = json.loads((directory / "index.json").read_text())
    assert index["model_id"] == PRO.model_id
    assert index["source"] == {
        "repository": PRO.repository,
        "revision": PRO.revision,
    }
    assert index["mandatory_context_tokens"] == LONG_PROMPT_TOKENS
    assert index["context_ladder"] == list(CONTEXT_LADDER)
    assert index["materialised_ladder"] == list(CONTEXT_LADDER)
    assert max(CONTEXT_LADDER) <= PRO.scalar("max_position_embeddings")
    observed = {
        workload_id: (
            entry["kind"],
            entry["prompt_token_count"],
            entry["max_new_tokens"],
            entry["digest"],
        )
        for workload_id, entry in index["workloads"].items()
    }
    assert observed == PRO_LADDER

    # The same rungs, one for one, differing only in the identity prefix.
    assert sorted(
        workload_id.replace("TA-DSP-", "", 1) for workload_id in PRO_LADDER
    ) == sorted(
        workload_id.replace("TA-DS-", "", 1) for workload_id in FLASH_LADDER
    )


def test_pro_index_names_the_pro_tokenizer() -> None:
    index = json.loads((_built(PRO.model_id) / "index.json").read_text())
    assert index["tokenizer_sha256"] == PRO.tokenizer_sha256
    # Measured, not assumed: the two snapshots' tokenizer.json files have the
    # same SHA-256 and are byte-identical under cmp, so this digest is also
    # Flash's.  The tokenizer is shared; the workload identities are not.
    assert PRO.tokenizer_sha256 == FLASH.tokenizer_sha256


@pytest.mark.parametrize("model_id", sorted(LADDERS))
def test_every_workload_document_validates_against_the_schema(
    model_id: str,
) -> None:
    directory = _built(model_id)
    index = json.loads((directory / "index.json").read_text())
    assert index["schema"] == "opentallas.workload_index.v1"
    for workload_id, entry in sorted(index["workloads"].items()):
        document = json.loads((directory / entry["path"]).read_text())
        _validate_document(document)
        assert document["workload_id"] == workload_id
        assert document["digest"] == entry["digest"]
        assert document["kind"] == entry["kind"]
        assert document["prompt_token_count"] == entry["prompt_token_count"]
        assert document["max_new_tokens"] == entry["max_new_tokens"]


def test_shared_token_ids_do_not_share_an_identity() -> None:
    flash_dir = _built(FLASH.model_id)
    pro_dir = _built(PRO.model_id)
    flash_index = json.loads((flash_dir / "index.json").read_text())
    pro_index = json.loads((pro_dir / "index.json").read_text())
    for flash_id in sorted(flash_index["workloads"]):
        pro_id = flash_id.replace("TA-DS-", "TA-DSP-", 1)
        flash_body = json.loads(
            (flash_dir / flash_index["workloads"][flash_id]["path"]).read_text()
        )
        pro_body = json.loads(
            (pro_dir / pro_index["workloads"][pro_id]["path"]).read_text()
        )
        assert pro_body["token_ids"] == flash_body["token_ids"]
        assert pro_body["rendered_text"] == flash_body["rendered_text"]
        assert pro_body["digest"] != flash_body["digest"]


def test_rebuilding_pro_reproduces_the_pinned_identities() -> None:
    tokenizer = _tokenizer(PRO)
    built = build_workloads(tokenizer, release=PRO.model_id, ladder=(1_000,))
    expected = {
        workload_id
        for workload_id, (kind, tokens, *_rest) in PRO_LADDER.items()
        if kind in CHEAP_KINDS or tokens == 1_000
    }
    assert set(built) == expected
    for workload_id, workload in built.items():
        kind, tokens, max_new_tokens, digest = PRO_LADDER[workload_id]
        assert (workload.kind, len(workload.token_ids)) == (kind, tokens)
        assert workload.max_new_tokens == max_new_tokens
        assert workload.digest == digest
    document = index_document(built, release=PRO.model_id)
    assert document["model_id"] == PRO.model_id
    assert document["source"]["revision"] == PRO.revision


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_unknown_model_is_refused_by_the_workload_module() -> None:
    with pytest.raises(DeepSeekV4ReleaseError, match="unknown DeepSeek-V4 release"):
        workload_id_prefix(UNKNOWN_MODEL)
    with pytest.raises(DeepSeekV4ReleaseError, match="unknown DeepSeek-V4 release"):
        index_document({}, release=UNKNOWN_MODEL)
    with pytest.raises(DeepSeekV4ReleaseError, match="unknown DeepSeek-V4 release"):
        build_workloads(object(), release=UNKNOWN_MODEL, ladder=())


def test_unknown_model_is_refused_by_the_builder_cli() -> None:
    completed = subprocess.run(
        [sys.executable, str(BUILDER), "--model", UNKNOWN_MODEL],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode != 0
    assert "unknown DeepSeek-V4 release" in completed.stderr
    assert PRO.model_id in completed.stderr


def test_a_ladder_past_the_release_context_bound_is_refused() -> None:
    beyond = int(PRO.scalar("max_position_embeddings")) + 1
    with pytest.raises(ValueError, match="max_position_embeddings"):
        build_workloads(object(), release=PRO.model_id, ladder=(beyond,))

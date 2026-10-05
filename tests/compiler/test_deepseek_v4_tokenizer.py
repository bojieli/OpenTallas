from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from compiler.frontend.deepseek_v4_encoding import encode_messages
from compiler.frontend.deepseek_v4_tokenizer import (
    BASE_VOCAB_SIZE,
    BOS_TOKEN_ID,
    EOS_TOKEN_ID,
    MODEL_MAX_LENGTH,
    PAD_TOKEN_ID,
    PROTOCOL_TOKEN_IDS,
    TOKENIZER_CONFIG_SHA256,
    TOKENIZER_SHA256,
    TOKENIZERS_RUNTIME_VERSION,
    VOCAB_SIZE,
    DeepSeekV4TokenizerError,
    VerifiedDeepSeekV4Tokenizer,
    _runtime_version,
    _strict_json,
    load_verified_deepseek_v4_tokenizer,
)


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "compiler/models/deepseek-v4-flash-0731"
FIXTURES = ROOT / "testdata/compiler/deepseek_v4_encoding"
SNAPSHOT_ENV = "OPENTALLAS_DEEPSEEK_V4_TOKENIZER_SNAPSHOT"
SCHEMA = ROOT / "schemas/compiler/deepseek_v4_tokenizer_validation_v1.schema.json"


def _fixture_bytes(name: str) -> bytes:
    encoded = (FIXTURES / f"{name}.base64").read_bytes()
    return base64.b64decode(b"".join(encoded.split()), validate=True)


def _ids_digest(ids: list[int]) -> str:
    return hashlib.sha256(
        b"".join(token_id.to_bytes(4, "little") for token_id in ids)
    ).hexdigest()


@pytest.fixture(scope="module")
def official_snapshot() -> Path:
    raw_path = os.environ.get(SNAPSHOT_ENV)
    if not raw_path:
        pytest.skip(f"set {SNAPSHOT_ENV} for official tokenizer integration")
    path = Path(raw_path)
    if not path.is_dir():
        pytest.fail(f"{SNAPSHOT_ENV} is not a directory: {path}")
    return path


@pytest.fixture(scope="module")
def official_tokenizer(
    official_snapshot: Path,
) -> VerifiedDeepSeekV4Tokenizer:
    return load_verified_deepseek_v4_tokenizer(official_snapshot)


def test_official_source_pins_local_only_tokenizer_identity() -> None:
    source = json.loads((TARGET / "checkpoint_source.json").read_text())
    expected = {record["path"]: record for record in source["expected_files"]}

    assert source["repository"] == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert source["revision"] == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert source["remote_code_policy"] == "disabled"
    assert expected["tokenizer.json"] == {
        "path": "tokenizer.json",
        "sha256": TOKENIZER_SHA256,
        "size_bytes": 6_367_146,
    }
    assert expected["tokenizer_config.json"] == {
        "path": "tokenizer_config.json",
        "sha256": TOKENIZER_CONFIG_SHA256,
        "size_bytes": 801,
    }
    assert (BASE_VOCAB_SIZE, VOCAB_SIZE, MODEL_MAX_LENGTH) == (
        128_000,
        129_280,
        1_048_576,
    )
    assert (BOS_TOKEN_ID, EOS_TOKEN_ID, PAD_TOKEN_ID) == (0, 1, 1)
    assert len(PROTOCOL_TOKEN_IDS) == 14


def test_loader_has_no_transformers_or_network_auto_loading() -> None:
    module = sys.modules[load_verified_deepseek_v4_tokenizer.__module__]
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "AutoTokenizer" not in source
    assert "from_pretrained" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "huggingface_hub" not in source


def test_validation_report_schema_is_strict_and_valid() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False


def test_missing_or_wrong_sized_local_payload_fails_before_runtime(
    tmp_path: Path,
) -> None:
    with pytest.raises(DeepSeekV4TokenizerError, match="missing 'tokenizer.json'"):
        load_verified_deepseek_v4_tokenizer(tmp_path)

    (tmp_path / "tokenizer.json").write_bytes(b"not the official tokenizer")
    with pytest.raises(DeepSeekV4TokenizerError, match="size is"):
        load_verified_deepseek_v4_tokenizer(tmp_path)


def test_wrong_source_identity_fails_before_reading_snapshot(tmp_path: Path) -> None:
    source = json.loads((TARGET / "checkpoint_source.json").read_text())
    source["repository"] = "example/shape-compatible-model"
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(DeepSeekV4TokenizerError, match="source repository"):
        load_verified_deepseek_v4_tokenizer(tmp_path, source_path)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"a": 1, "a": 2}',
        b'{"a": NaN}',
        b"[]",
        b"\xff",
    ],
)
def test_tokenizer_metadata_json_is_strict(payload: bytes) -> None:
    with pytest.raises(DeepSeekV4TokenizerError):
        _strict_json(payload, "adversarial.json")


def test_runtime_version_is_an_explicit_execution_input(monkeypatch) -> None:
    assert _runtime_version() == TOKENIZERS_RUNTIME_VERSION
    monkeypatch.setattr(
        "compiler.frontend.deepseek_v4_tokenizer.metadata.version",
        lambda _: "99.0.0",
    )
    with pytest.raises(DeepSeekV4TokenizerError, match="99.0.0"):
        _runtime_version()


def test_verified_class_cannot_be_forged_by_direct_construction() -> None:
    with pytest.raises(DeepSeekV4TokenizerError, match="local loader"):
        VerifiedDeepSeekV4Tokenizer(
            object(), {}, _construction_key=object()
        )


def test_official_tokenizer_report_and_protocol_ids_are_exact(
    official_tokenizer: VerifiedDeepSeekV4Tokenizer,
) -> None:
    report = official_tokenizer.validation_report
    golden = json.loads(
        (FIXTURES / "tokenizer_golden.json").read_text(encoding="utf-8")
    )
    assert report["validation_id"] == golden["tokenizer_validation_id"]
    assert report["status"] == "verified_official_local_tokenizer"
    assert report["runtime"] == {
        "implementation": "tokenizers",
        "version": TOKENIZERS_RUNTIME_VERSION,
    }
    assert report["contract"]["protocol_token_ids"] == {
        label: token_id
        for label, (_, token_id) in sorted(PROTOCOL_TOKEN_IDS.items())
    }
    assert report["contract"]["total_vocab_size"] == VOCAB_SIZE
    Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(report)

    mutated = official_tokenizer.validation_report
    mutated["status"] = "forged"
    assert official_tokenizer.validation_report["status"] != "forged"


def test_all_official_prompt_fixtures_have_golden_token_streams(
    official_tokenizer: VerifiedDeepSeekV4Tokenizer,
) -> None:
    golden = json.loads(
        (FIXTURES / "tokenizer_golden.json").read_text(encoding="utf-8")
    )
    for record in golden["cases"]:
        case = record["case"]
        source = json.loads(_fixture_bytes(f"test_input_{case}.json"))
        if case == 1:
            messages = source["messages"]
            messages[0]["tools"] = source["tools"]
        else:
            messages = source
        prompt = encode_messages(
            messages, thinking_mode=record["thinking_mode"]
        )
        ids = official_tokenizer.encode(prompt)
        assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == (
            record["prompt_utf8_sha256"]
        )
        assert len(ids) == record["token_count"]
        assert ids[0] == record["first_token_id"] == BOS_TOKEN_ID
        assert ids[-1] == record["last_token_id"] == EOS_TOKEN_ID
        assert _ids_digest(ids) == record["token_ids_le32_sha256"]
        assert official_tokenizer.decode(ids) == prompt


def test_prompt_encoder_inserts_bos_once_and_tokenizer_adds_nothing(
    official_tokenizer: VerifiedDeepSeekV4Tokenizer,
) -> None:
    prompt, ids = official_tokenizer.encode_prompt(
        [{"role": "user", "content": "Hello"}], thinking_mode="chat"
    )
    assert prompt.startswith("<｜begin▁of▁sentence｜>")
    assert prompt.count("<｜begin▁of▁sentence｜>") == 1
    assert ids == [0, 128_803, 19_923, 128_804, 128_822]
    assert official_tokenizer.decode(ids) == prompt
    assert official_tokenizer.decode([0, 1], skip_special_tokens=True) == ""


@pytest.mark.parametrize(
    "token_ids",
    [
        [-1],
        [VOCAB_SIZE],
        [True],
        [1.5],
    ],
)
def test_decode_rejects_non_vocabulary_ids(
    official_tokenizer: VerifiedDeepSeekV4Tokenizer, token_ids: list
) -> None:
    with pytest.raises(DeepSeekV4TokenizerError, match="outside"):
        official_tokenizer.decode(token_ids)


def test_tokenizer_cli_emits_canonical_validation_report(
    official_snapshot: Path, tmp_path: Path
) -> None:
    output = tmp_path / "tokenizer-validation.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "validate-deepseek-v4-tokenizer",
            "--snapshot",
            str(official_snapshot),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="ascii"))
    assert report["validation_id"] == (
        "176e504a2a500bfccd88d6ef10b72c1d08853a90ff62d97d173faaa808dd5c23"
    )
    assert "validated official tokenizer" in result.stdout
    assert "local-only tokenizers 0.22.2" in result.stdout

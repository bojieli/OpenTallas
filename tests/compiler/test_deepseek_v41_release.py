"""The DeepSeek-V4.1-Flash release record and its committed checkpoint contract.

The record is the gate every later V4.1 stage passes through, so these tests are
about the record agreeing with things it did not write: the bytes committed under
``compiler/models/deepseek-v4.1-flash``, the governed inventory, the five
``SRC-DSV41-FLASH-*`` entries of ``docs/SOURCES.md``, and the two V4 records it
sits beside.  The tensor contract it implies is checked in
``test_deepseek_v41_tensor_specs.py``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest

from compiler.frontend.checkpoint import load_checkpoint_source
from compiler.frontend.deepseek_v4_releases import (
    CONFIG_LAYOUT_KEYS,
    FLASH,
    PRO,
    RELEASES,
    V41_FLASH,
    DeepSeekV4ReleaseError,
    resolve_release,
)
from compiler.frontend.deepseek_v41 import (
    CONFIG_SHA256,
    INDEX_SHA256,
    MODEL_ID,
    PAYLOAD_BYTES,
    TENSOR_COUNT,
    DeepSeekV41AdapterError,
    load_official_config,
    validate_official_config,
)


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "compiler/models/deepseek-v4.1-flash"
INVENTORY = ROOT / "data/inventory/deepseek-v4.1-flash.json"
SOURCES = ROOT / "docs/SOURCES.md"


@pytest.fixture(scope="module")
def official_config() -> dict:
    return load_official_config()


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def _sources_row(identifier: str) -> str:
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {identifier} |"):
            return line
    raise AssertionError(f"docs/SOURCES.md has no row {identifier}")


# -- identity -------------------------------------------------------------


def test_release_is_registered_under_its_own_model_id() -> None:
    assert RELEASES[MODEL_ID] is V41_FLASH
    assert resolve_release(MODEL_ID) is V41_FLASH
    assert resolve_release(V41_FLASH) is V41_FLASH
    assert MODEL_ID == "deepseek-v4.1-flash"
    # The two V4 records are still reachable and unchanged in identity.
    assert set(RELEASES) == {FLASH.model_id, PRO.model_id, V41_FLASH.model_id}


def test_committed_config_is_byte_exact_official_source() -> None:
    """The committed bytes are the released bytes, and nothing else is claimed."""

    payload = (TARGET / "config.json").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == CONFIG_SHA256
    assert len(payload) == V41_FLASH.config_bytes == 3_311

    inference = (TARGET / "inference_config.json").read_bytes()
    assert (
        hashlib.sha256(inference).hexdigest() == V41_FLASH.inference_config_sha256
    )
    assert len(inference) == 1_982

    # ``README.md`` here is this repository's own directory README, following the
    # convention both V4 target directories use -- not the released model card,
    # whose digest ``model_card_sha256`` pins and which is not committed.  A test
    # that confused the two would pass while the wrong file sat in the tree.
    readme = (TARGET / "README.md").read_bytes()
    assert hashlib.sha256(readme).hexdigest() != V41_FLASH.model_card_sha256
    for sibling_release in (FLASH, PRO):
        sibling = (
            TARGET.parent / sibling_release.model_id / "README.md"
        ).read_bytes()
        assert (
            hashlib.sha256(sibling).hexdigest() != sibling_release.model_card_sha256
        )
    text = readme.decode("utf-8")
    assert text.startswith("# Official DeepSeek V4.1 Flash compiler target")
    # The directory README must carry the release identity it documents.
    assert V41_FLASH.revision in text
    assert V41_FLASH.config_sha256 in text
    assert V41_FLASH.index_sha256 in text
    assert V41_FLASH.tensor_structure_sha256 in text
    assert V41_FLASH.model_card_sha256 in text
    assert f"{TENSOR_COUNT:,}" in text and f"{PAYLOAD_BYTES:,}" in text

    assert V41_FLASH.lock_identity_established == (
        V41_FLASH.checkpoint_lock_id is not None
    )


def test_checkpoint_source_contract_binds_the_whole_released_file_set() -> None:
    """The expectation half of the identity, and it is committed, not pending.

    ``load_official_config`` authenticates the config against this contract as
    well as against the record, so a source that named a different revision or a
    different ``config.json`` would fail the load rather than be ignored.
    """

    assert V41_FLASH.checkpoint_source_pending is False
    source = load_checkpoint_source(V41_FLASH.checkpoint_source_path)
    assert source["schema"] == "opentallas.checkpoint_source.v1"
    assert source["repository"] == V41_FLASH.repository
    assert source["revision"] == V41_FLASH.revision
    assert source["checkpoint_index"] == "model.safetensors.index.json"

    files = {item["path"]: item for item in source["expected_files"]}
    shards = [path for path in files if path.endswith(".safetensors")]
    assert len(shards) == V41_FLASH.shard_count == 48
    assert files["config.json"]["sha256"] == V41_FLASH.config_sha256
    assert files["config.json"]["size_bytes"] == V41_FLASH.config_bytes
    assert files["model.safetensors.index.json"]["sha256"] == V41_FLASH.index_sha256
    assert files["README.md"]["sha256"] == V41_FLASH.model_card_sha256
    assert files["inference/config.json"]["sha256"] == (
        V41_FLASH.inference_config_sha256
    )
    assert files["tokenizer.json"]["sha256"] == V41_FLASH.tokenizer_sha256
    assert files["tokenizer_config.json"]["sha256"] == (
        V41_FLASH.tokenizer_config_sha256
    )
    # Every digest is a real digest, and every shard carries header bytes beyond
    # the payload the index accounts for.
    assert all(len(item["sha256"]) == 64 for item in files.values())
    assert sum(files[path]["size_bytes"] for path in shards) > PAYLOAD_BYTES


def test_source_contract_agrees_with_the_committed_registry_witness() -> None:
    """The witness is an artifact, not a fetch: the listing is committed too.

    Every one of the 88 files is witnessed on content, in one of two ways, and
    the distinction matters because ``build_checkpoint_source.py`` reports the
    second class as "size alone":

    * 52 files carry an LFS ``sha256`` -- all 48 shards and four large binaries.
    * the other 36, the index among them, are plain Git objects, so the registry
      publishes a ``blobId``.  That is a SHA-1 over the blob, which this test
      recomputes locally; it is a weaker hash than SHA-256 but it is still a
      content witness rather than a size one.

    So the index's 510,286,023,000-byte ``metadata.total_size`` is content-bound
    at the pinned revision even though no LFS digest covers it.
    """

    listing = json.loads(
        (ROOT / "data/inventory/deepseek-v4.1-flash-registry-listing.json").read_text(
            encoding="utf-8"
        )
    )
    assert listing["sha"] == V41_FLASH.revision
    witness = {entry["rfilename"]: entry for entry in listing["siblings"]}
    source = load_checkpoint_source(V41_FLASH.checkpoint_source_path)
    files = {item["path"]: item for item in source["expected_files"]}
    assert sorted(files) == sorted(witness)
    assert len(files) == 88

    lfs_witnessed: list[str] = []
    blob_witnessed: list[str] = []
    for path, item in sorted(files.items()):
        entry = witness[path]
        assert entry["size"] == item["size_bytes"], path
        lfs = entry.get("lfs")
        if isinstance(lfs, dict) and isinstance(lfs.get("sha256"), str):
            assert lfs["sha256"] == item["sha256"], path
            lfs_witnessed.append(path)
        else:
            assert isinstance(entry.get("blobId"), str), path
            blob_witnessed.append(path)
    assert len(lfs_witnessed) == 52
    assert len(blob_witnessed) == 36
    assert lfs_witnessed + blob_witnessed
    # All 48 shards are in the stronger class.
    assert [path for path in lfs_witnessed if path.endswith(".safetensors")] == sorted(
        path for path in files if path.endswith(".safetensors")
    )
    # The index and the committed config are in the Git-object class, and their
    # blob ids are recomputed from the snapshot rather than trusted.
    snapshot = V41_FLASH.snapshot
    if not snapshot.is_dir():
        pytest.skip(f"no local snapshot at {snapshot}")
    for path in ("model.safetensors.index.json", "config.json"):
        assert path in blob_witnessed
        payload = (snapshot / path).read_bytes()
        blob = hashlib.sha1(
            b"blob " + str(len(payload)).encode() + b"\x00" + payload
        ).hexdigest()
        assert blob == witness[path]["blobId"], path
    # And the committed copy of the config is those same bytes.
    assert (TARGET / "config.json").read_bytes() == (snapshot / "config.json").read_bytes()


def test_record_agrees_with_the_governed_inventory(inventory: dict) -> None:
    assert inventory["repo"] == V41_FLASH.repository
    assert inventory["revision"] == V41_FLASH.revision
    assert inventory["config_sha256"] == CONFIG_SHA256
    assert inventory["index_sha256"] == INDEX_SHA256
    assert inventory["shard_count"] == V41_FLASH.shard_count == 48
    assert inventory["tensor_count"] == TENSOR_COUNT == 96_085
    assert (
        inventory["checkpoint_bytes"]
        == inventory["header_storage_bytes"]
        == PAYLOAD_BYTES
        == 510_286_023_000
    )


def test_record_agrees_with_the_five_registered_sources() -> None:
    """Every digest the record pins is the digest ``docs/SOURCES.md`` registers."""

    assert V41_FLASH.model_card_sha256 in _sources_row("SRC-DSV41-FLASH-CARD")
    assert V41_FLASH.config_sha256 in _sources_row("SRC-DSV41-FLASH-CONFIG")
    index_row = _sources_row("SRC-DSV41-FLASH-INDEX")
    assert V41_FLASH.index_sha256 in index_row
    assert f"{TENSOR_COUNT:,} tensors" in index_row
    assert f"{PAYLOAD_BYTES:,} bytes" in index_row
    for identifier in (
        "SRC-DSV41-FLASH-CARD",
        "SRC-DSV41-FLASH-REPORT",
        "SRC-DSV41-FLASH-CONFIG",
        "SRC-DSV41-FLASH-MODEL",
        "SRC-DSV41-FLASH-INDEX",
    ):
        assert V41_FLASH.revision in _sources_row(identifier) or "same revision" in (
            _sources_row(identifier)
        )


# -- the 40-layer Causal Encoder-Decoder ----------------------------------


def test_compress_ratio_table_is_the_published_encoder_decoder_split(
    official_config: dict,
) -> None:
    """20 + 20, with the encoder's ratio-2 groups and the decoder's ratio-1 ones.

    ``SRC-DSV41-FLASH-REPORT`` section 2.2 states three groups of six CSA2
    encoder layers at ratio 2 and five groups of four decoder layers at ratio 1;
    the model card states a 40-layer CED as 20 + 20.  Both are properties of the
    table, so they are read off it rather than restated as literals.
    """

    ratios = V41_FLASH.main_compress_ratios
    assert len(ratios) == V41_FLASH.num_hidden_layers == 40
    window_only = [layer for layer, ratio in enumerate(ratios) if ratio == 0]
    encoder = [layer for layer, ratio in enumerate(ratios) if ratio == 2]
    decoder = [layer for layer, ratio in enumerate(ratios) if ratio == 1]

    assert window_only == [0, 1]
    assert len(encoder) == 18 and encoder == list(range(2, 20))
    assert len(decoder) == 20 and decoder == list(range(20, 40))
    # The encoder half of the CED is the window-only prefix plus its CSA2 groups.
    assert len(window_only) + len(encoder) == len(decoder) == 20
    assert len(encoder) % 6 == 0 and len(decoder) % 4 == 0

    assert V41_FLASH.dspark_compress_ratios == (0, 0, 0)
    assert V41_FLASH.dspark_stage_count == 3
    assert (
        V41_FLASH.compress_ratios
        == official_config["text_config"]["compress_ratios"]
        == [*ratios, 0, 0, 0]
    )
    assert len(V41_FLASH.compress_ratios) == 43
    assert V41_FLASH.supported_compress_ratios == (0, 1, 2)


def test_unsupported_ratio_is_refused_against_this_releases_own_set() -> None:
    """The admissible pooling widths are the record's, not a frozen literal.

    V4's ratio 4 is a perfectly good ratio -- for V4.  Naming it on a record
    whose ``supported_compress_ratios`` is V4.1's must fail, and V4's own
    records must keep accepting it.
    """

    with pytest.raises(DeepSeekV4ReleaseError, match="unsupported compression ratios"):
        dataclass_replace(V41_FLASH, main_compress_ratios=(4,) * 40)
    assert set(FLASH.main_compress_ratios) <= set(FLASH.supported_compress_ratios)
    assert set(PRO.main_compress_ratios) <= set(PRO.supported_compress_ratios)
    assert FLASH.supported_compress_ratios == PRO.supported_compress_ratios == (0, 4, 128)


def dataclass_replace(record, **changes):
    import dataclasses

    return dataclasses.replace(record, **changes)


def test_layer_mode_lists_are_pinned_and_mutually_consistent(
    official_config: dict,
) -> None:
    """The four lists WP-B must pin, and the invariants the front end relies on."""

    text = official_config["text_config"]
    kv_sources = V41_FLASH.scalar("kv_source_layer_ids")
    index_sources = V41_FLASH.scalar("index_source_layer_ids")
    candidate = V41_FLASH.scalar("candidate_source_layer_id")
    engram_layers = V41_FLASH.scalar("engram_layer_ids")
    engram_rows = V41_FLASH.scalar("engram_num_embeddings")

    assert kv_sources == text["kv_source_layer_ids"] == [2, 8, 14, 20]
    assert index_sources == text["index_source_layer_ids"]
    assert index_sources == [2, 8, 14, 20, 24, 28, 32, 36]
    assert candidate == text["candidate_source_layer_id"] == 20
    assert engram_layers == text["engram_layer_ids"] == [1, 14]
    assert engram_rows == text["engram_num_embeddings"]
    assert engram_rows == [384_006_168, 384_016_682]

    ratios = V41_FLASH.main_compress_ratios
    # Every source layer exists, publishes a latent, and is also an index source.
    assert set(kv_sources) <= set(index_sources)
    assert all(0 <= layer < len(ratios) for layer in index_sources)
    assert all(ratios[layer] >= 1 for layer in kv_sources)
    # The candidate source is the last KV source: the pool is built where the
    # decoder's global KV is first published.
    assert candidate == max(kv_sources)
    assert ratios[candidate] == 1
    # Engram sits at layers that are not KV sources except where they coincide.
    assert all(0 <= layer < len(ratios) for layer in engram_layers)
    assert len(engram_layers) == len(engram_rows)
    assert engram_layers == sorted(engram_layers)


def test_engram_and_candidate_scalars_are_pinned(official_config: dict) -> None:
    text = official_config["text_config"]
    for key in (
        "candidate_block_size",
        "candidate_topk_blocks",
        "engram_compressed_vocab_size",
        "engram_head_dim",
        "engram_max_ngram_size",
        "engram_n_heads",
        "engram_pad_token_id",
        "engram_vocab_size",
    ):
        assert V41_FLASH.scalar(key) == text[key], key
    assert V41_FLASH.scalar("candidate_topk_blocks") == 2_048
    assert V41_FLASH.scalar("candidate_block_size") == 8
    assert V41_FLASH.scalar("engram_max_ngram_size") == 4
    assert V41_FLASH.scalar("engram_n_heads") == 8
    assert V41_FLASH.scalar("engram_head_dim") == 256


# -- the nested config layout ---------------------------------------------


def test_config_layout_locates_every_pinned_structure(official_config: dict) -> None:
    """V4.1 nests; V4 does not; neither front end assumes which."""

    assert set(V41_FLASH.config_layout) == set(CONFIG_LAYOUT_KEYS)
    assert V41_FLASH.config_path_for("architecture") == ("text_config",)
    assert V41_FLASH.config_path_for("rope_scaling") == ("text_config",)
    assert V41_FLASH.config_path_for("compress_ratios") == ("text_config",)
    assert V41_FLASH.config_path_for("quantization_config") == ()
    for structure in CONFIG_LAYOUT_KEYS:
        assert FLASH.config_path_for(structure) == ()
        assert PRO.config_path_for(structure) == ()

    assert (
        V41_FLASH.config_section(official_config, "architecture")
        is official_config["text_config"]
    )
    assert (
        V41_FLASH.config_section(official_config, "quantization_config")
        is official_config
    )
    assert set(V41_FLASH.config_sections) == {"", "vision_config"}


def test_a_missing_nested_section_fails_closed_rather_than_falling_back() -> None:
    """A flattened config must not pass a nested release's gate.

    This is the failure the layout field exists to prevent: if resolution fell
    back to the root, a V4-shaped config would satisfy a V4.1 record's scalars
    wherever the key names happen to coincide.
    """

    with pytest.raises(DeepSeekV4ReleaseError, match="no section 'text_config'"):
        V41_FLASH.config_section({"quantization_config": {}}, "architecture")
    with pytest.raises(DeepSeekV4ReleaseError, match="not one of the located"):
        V41_FLASH.config_path_for("engram_layer_ids")


def test_quantization_and_rope_are_pinned_where_the_release_puts_them(
    official_config: dict,
) -> None:
    assert official_config["quantization_config"] == dict(
        V41_FLASH.quantization_config
    )
    assert official_config["text_config"]["rope_scaling"] == dict(
        V41_FLASH.rope_scaling
    )
    # The FP8 scale block halves against V4, and expert_dtype moves inside the
    # quantization object; both are release facts the generator reads.
    assert V41_FLASH.quantization_config["weight_block_size"] == [32, 32]
    assert FLASH.quantization_config["weight_block_size"] == [128, 128]
    assert PRO.quantization_config["weight_block_size"] == [128, 128]
    assert V41_FLASH.quantization_config["expert_dtype"] == "fp4"
    assert "expert_dtype" not in FLASH.quantization_config
    assert FLASH.scalar("expert_dtype") == "fp4"
    # YaRN is the same interpolation under a renamed key.
    assert V41_FLASH.rope_scaling["rope_type"] == FLASH.rope_scaling["type"] == "yarn"
    assert {
        key: value for key, value in V41_FLASH.rope_scaling.items() if key != "rope_type"
    } == {key: value for key, value in FLASH.rope_scaling.items() if key != "type"}


def test_root_and_vision_sections_are_pinned(official_config: dict) -> None:
    for path, pinned in V41_FLASH.config_sections.items():
        section = official_config
        for key in filter(None, path.split(".")):
            section = section[key]
        for key, expected in pinned.items():
            assert section[key] == expected, f"{path}.{key}"
    assert V41_FLASH.config_sections[""]["architectures"] == ["DeepseekV41ForCausalLM"]
    assert V41_FLASH.config_sections[""]["model_type"] == "deepseek_v41"
    assert V41_FLASH.config_scalars["model_type"] == "deepseek_v41_text"
    vision = V41_FLASH.config_sections["vision_config"]
    assert vision["num_hidden_layers"] == 32
    assert vision["hidden_size"] == 1024
    assert vision["downsample_ratio"] == 3
    assert vision["patch_size"] == 14


def test_every_published_config_field_is_pinned_or_named_as_an_exception(
    official_config: dict,
) -> None:
    """Nothing in the released config is silently ignored.

    A field the release publishes and the record does not pin is a field the
    front end can start sizing by, or stop sizing by, without any test noticing.
    So coverage of the three sections is exhaustive, and the single exception is
    named here rather than left as a gap: ``transformers_version`` is a library
    version, affects no geometry, and would churn this record on every upstream
    release.  ``config_sha256`` pins it regardless.
    """

    non_architectural_root_keys = {"transformers_version"}

    text = official_config["text_config"]
    pinned = set(V41_FLASH.config_scalars)
    # ``compress_ratios`` is pinned through ``main_compress_ratios`` and
    # ``dspark_compress_ratios``, and ``rope_scaling`` through its own field.
    published = set(text) - {"compress_ratios", "rope_scaling"}
    assert published - pinned == set(), sorted(published - pinned)
    assert pinned - set(text) == set(), sorted(pinned - set(text))

    vision = official_config["vision_config"]
    assert set(vision) == set(V41_FLASH.config_sections["vision_config"])

    root_scalars = {
        key for key, value in official_config.items() if not isinstance(value, dict)
    }
    assert root_scalars - set(V41_FLASH.config_sections[""]) == (
        non_architectural_root_keys
    )
    assert official_config["transformers_version"] == "5.6.0"
    assert "transformers_version" not in V41_FLASH.config_sections[""]


# -- the gate refuses drift -----------------------------------------------


@pytest.mark.parametrize(
    "path,value",
    [
        (("text_config", "num_hidden_layers"), 41),
        (("text_config", "hidden_size"), 4096),
        (("text_config", "kv_source_layer_ids"), [2, 8, 14, 20, 26]),
        (("text_config", "index_source_layer_ids"), [2, 8, 14, 20]),
        (("text_config", "candidate_source_layer_id"), 14),
        (("text_config", "engram_layer_ids"), [1, 14, 27]),
        (("text_config", "engram_num_embeddings"), [384_006_168, 384_006_168]),
        (("text_config", "engram_n_heads"), 4),
        (("text_config", "rms_norm_eps"), 1e-6),
        (("text_config", "index_n_heads"), 64),
        (("text_config", "num_nextn_predict_layers"), 1),
        (("architectures",), ["DeepseekV4ForCausalLM"]),
        (("model_type",), "deepseek_v4"),
        (("vision_config", "num_hidden_layers"), 24),
    ],
)
def test_architecture_affecting_config_drift_fails_closed(
    official_config: dict, path: tuple, value: object
) -> None:
    import copy

    drifted = copy.deepcopy(official_config)
    node = drifted
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(DeepSeekV41AdapterError, match="differs"):
        validate_official_config(drifted)


def test_compress_ratio_drift_fails_closed(official_config: dict) -> None:
    import copy

    drifted = copy.deepcopy(official_config)
    drifted["text_config"]["compress_ratios"][20] = 2
    with pytest.raises(DeepSeekV41AdapterError, match="compress_ratios"):
        validate_official_config(drifted)


def test_quantization_block_drift_fails_closed(official_config: dict) -> None:
    import copy

    drifted = copy.deepcopy(official_config)
    drifted["quantization_config"]["weight_block_size"] = [128, 128]
    with pytest.raises(DeepSeekV41AdapterError, match="quantization_config"):
        validate_official_config(drifted)


def test_a_non_object_config_is_refused() -> None:
    with pytest.raises(DeepSeekV41AdapterError, match="must be an object"):
        validate_official_config([])


def test_no_model_number_is_written_into_the_front_end_source() -> None:
    """The V4.1 front end reads geometry; it does not carry it.

    Every number that names this checkpoint's shape belongs on the release
    record or in the released config.  The adapter is allowed the format
    constants it genuinely owns -- the MXFP4 block lives on the shared builder,
    not here -- so any four-or-more-digit literal in the module body is a frozen
    model number until proven otherwise.
    """

    source = (ROOT / "compiler/frontend/deepseek_v41.py").read_text(encoding="utf-8")
    body = "\n".join(
        line
        for line in source.splitlines()
        if not line.lstrip().startswith(("#", "*", '"""', "'''"))
    )
    # Strip the module docstring, which quotes the released field names.
    body = body.split('"""', 2)[-1] if body.count('"""') >= 2 else body
    offenders = sorted(set(re.findall(r"(?<![\w.])\d{4,}(?![\w.])", body)))
    assert offenders == [], f"frozen model numbers in the V4.1 adapter: {offenders}"

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from compiler.build import BuildError, build_deployment
from compiler.checking.inverse import InverseCheckError, check_rom_image
from compiler.ir.model import IRValidationError, load_strict_json, write_canonical_json
from compiler.microcode.isa import Instruction, MicrocodeError, decode, encode, verify


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "testdata/compiler/linear_fixture"
MODEL = FIXTURE / "model.ir.json"


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_compiler_is_byte_deterministic_and_payload_free_at_runtime(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = build_deployment(MODEL, first)
    second_manifest = build_deployment(MODEL, second)
    assert first_manifest == second_manifest
    assert _tree(first) == _tree(second)
    assert first_manifest["build_id"] == (
        "3e6944a33334e1be61aad73e139afd9c853b4f2fdcdf6a5eeaedd9f5400e527d"
    )

    runtime_ir = load_strict_json(first / "model.ir.json")
    assert all("values" not in tensor for tensor in runtime_ir["tensors"])
    assert (first / "rom_stage00_image.bin").read_bytes().hex() == (
        "0102ff0000ff0302020001fe00000000"
        "01000000fdffffff0500000000000000"
    )
    assert set(record["role"] for record in first_manifest["artifacts"]) == {
        "execution_expectations",
        "microcode",
        "microcode_disassembly",
        "operator_coverage",
        "rom_image",
        "rom_roundtrip_report",
        "semantic_ir",
        "source_lock",
        "tensor_manifest",
    }


def test_independent_rom_inverse_reconstructs_all_payloads(tmp_path: Path) -> None:
    deployment = tmp_path / "deployment"
    build_deployment(MODEL, deployment)
    report = check_rom_image(MODEL, deployment)
    assert report == load_strict_json(deployment / "roundtrip_report.json")
    assert report["status"] == "pass"
    assert report["payload_bytes"] == 24
    assert report["padding_bytes"] == 8
    assert [record["tensor_id"] for record in report["reconstructed_tensors"]] == [
        "projection_weight",
        "projection_bias",
    ]


def test_inverse_checker_rejects_nonzero_padding_even_with_updated_image_hash(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deployment"
    build_deployment(MODEL, deployment)
    image_path = deployment / "rom_stage00_image.bin"
    image = bytearray(image_path.read_bytes())
    image[-1] = 1
    image_path.write_bytes(image)
    manifest_path = deployment / "tensor_manifest.json"
    manifest = load_strict_json(manifest_path)
    manifest["image"]["sha256"] = hashlib.sha256(image).hexdigest()
    write_canonical_json(manifest_path, manifest)
    with pytest.raises(InverseCheckError, match="nonzero padding"):
        check_rom_image(MODEL, deployment)


def test_unsupported_operator_and_implicit_broadcast_fail_closed(
    tmp_path: Path,
) -> None:
    source = load_strict_json(MODEL)
    unsupported = copy.deepcopy(source)
    unsupported["operations"][1]["kind"] = "RMSNORM"
    unsupported_path = tmp_path / "unsupported.json"
    write_canonical_json(unsupported_path, unsupported)
    with pytest.raises(IRValidationError, match="unsupported kind"):
        build_deployment(unsupported_path, tmp_path / "unsupported-output")

    broadcast = copy.deepcopy(source)
    broadcast["tensors"][2]["shape"] = [3]
    broadcast_path = tmp_path / "broadcast.json"
    write_canonical_json(broadcast_path, broadcast)
    with pytest.raises(IRValidationError, match="forbids implicit broadcasting"):
        build_deployment(broadcast_path, tmp_path / "broadcast-output")


def test_duplicate_json_key_and_existing_output_fail_closed(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema":"opentallas.semantic_ir.v1","schema":"duplicate"}\n',
        encoding="utf-8",
    )
    with pytest.raises(IRValidationError, match="duplicate JSON key"):
        build_deployment(duplicate, tmp_path / "duplicate-output")

    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(BuildError, match="already exists"):
        build_deployment(MODEL, existing)


def test_microcode_crc_and_semantic_operand_tamper_fail_closed(tmp_path: Path) -> None:
    deployment = tmp_path / "deployment"
    build_deployment(MODEL, deployment)
    model_payload = load_strict_json(deployment / "model.ir.json")
    from compiler.ir.model import parse_model

    model = parse_model(model_payload, require_rom_values=False)
    payload = (deployment / "microcode_stage00.bin").read_bytes()
    corrupted = bytearray(payload)
    corrupted[-1] ^= 1
    with pytest.raises(MicrocodeError, match="CRC32"):
        decode(bytes(corrupted))

    instructions = list(decode(payload))
    first = instructions[0]
    instructions[0] = Instruction(
        first.opcode,
        destination=4,
        source0=first.source0,
        source1=first.source1,
    )
    reencoded = encode(tuple(instructions))
    reparsed = decode(reencoded)
    with pytest.raises(MicrocodeError, match="does not exactly lower"):
        verify(reparsed, model)


def test_compiler_schemas_are_strict_draft_2020_documents() -> None:
    schema_dir = ROOT / "schemas/compiler"
    schemas = sorted(schema_dir.glob("*.schema.json"))
    assert {path.name for path in schemas} == {
        "checkpoint_lock_v1.schema.json",
        "checkpoint_source_v1.schema.json",
        "deepseek_v4_checkpoint_validation_v1.schema.json",
        "deepseek_v4_tensor_contract_v1.schema.json",
        "deployment_manifest_v1.schema.json",
        "execution_request_v1.schema.json",
        "semantic_ir_v1.schema.json",
    }
    for path in schemas:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert value["additionalProperties"] is False

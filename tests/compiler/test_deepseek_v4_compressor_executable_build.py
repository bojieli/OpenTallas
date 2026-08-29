from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct

import pytest

from compiler.checking.deepseek_v4_compressor_executable import (
    DeepSeekV4CompressorExecutableCheckError,
    verify_deepseek_v4_compressor_executable_deployment,
)
from compiler.microcode.deepseek_v4_compressor import (
    APE_BYTES,
    PROGRAM_BYTES,
    PROGRAM_SHA256,
    assemble,
    decode,
    disassemble,
    encode,
    verify,
)
from compiler.scheduling.deepseek_v4_compressor import (
    NONCLAIMS,
    build_logical_schedule,
    build_logical_schedule_certificate,
    verify_logical_schedule,
    verify_logical_schedule_certificate,
)
from compiler.vertical_slice.deepseek_v4_compressor_executable import (
    CLAIM_BOUNDARY,
    OFFICIAL_APE_SHA256,
    OFFICIAL_APPLICATION_ID,
    OFFICIAL_VERIFICATION_ID,
    build_deepseek_v4_compressor_executable_deployment,
)


OFFICIAL_APE = Path(
    "/home/ubuntu/.cache/opentallas/deepseek-v4-flash-0731/canonical-mp4/"
    "ranks/rank-000/layers.2.attn.compressor.ape.bin"
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


@pytest.fixture(scope="module")
def synthetic_deployment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("compressor-build")
    ape = root / "synthetic-ape.f32le"
    ape.write_bytes(struct.pack("<4096I", *([0] * 4096)))
    deployment = root / "deployment"
    report = build_deepseek_v4_compressor_executable_deployment(
        ape,
        deployment,
        source_kind="synthetic",
    )
    assert report["evidence_eligible"] is False
    return deployment


def _rewrite_manifest_record(deployment: Path, relative: str, payload: bytes) -> None:
    path = deployment / relative
    path.write_bytes(payload)
    manifest_path = deployment / "deployment_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for record in manifest["artifacts"]:
        if record["path"] == relative:
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["size_bytes"] = len(payload)
            break
    else:  # pragma: no cover - test helper invariant
        raise AssertionError(relative)
    core = {key: manifest[key] for key in manifest if key != "build_id"}
    manifest["build_id"] = hashlib.sha256(_canonical(core)).hexdigest()
    manifest_path.write_bytes(_canonical(manifest))


def test_microcode_is_exact_fixed_width_roundtripping_program() -> None:
    program = assemble()
    payload = encode(program)
    assert len(payload) == PROGRAM_BYTES == 148
    assert hashlib.sha256(payload).hexdigest() == PROGRAM_SHA256
    assert PROGRAM_SHA256 == (
        "7fba505367f95ce4c39155678fe299999e13445813781c8b0e45ba1e6525a1fc"
    )
    decoded = decode(payload)
    verify(decoded)
    assert decoded == program
    assert disassemble(decoded).splitlines() == [
        "0000 RAW_STATE_PREPARE flags=0 source=0 destination=0 immediate=0",
        "0001 POOL_IF_READY flags=0 source=0 destination=0 immediate=0",
        "0002 F32_TO_BF16_IF_READY flags=0 source=0 destination=0 immediate=0",
        "0003 COMPRESSED_KV_COMMIT flags=0 source=0 destination=0 immediate=0",
        "0004 VALID_PREFIX_VIEW flags=0 source=0 destination=0 immediate=0",
        "0005 COMPLETE flags=0 source=0 destination=0 immediate=0",
    ]


def test_logical_schedule_is_causal_and_explicitly_not_physical() -> None:
    ape_sha256 = "0" * 64
    schedule = build_logical_schedule(ape_sha256=ape_sha256)
    certificate = build_logical_schedule_certificate(
        schedule,
        ape_sha256=ape_sha256,
    )
    verify_logical_schedule(schedule, ape_sha256=ape_sha256)
    verify_logical_schedule_certificate(
        certificate,
        schedule,
        ape_sha256=ape_sha256,
    )
    assert [slot["logical_slot"] for slot in schedule["slots"]] == list(range(6))
    assert schedule["slots"][3]["depends_on"] == [0, 2]
    assert schedule["slots"][5]["depends_on"] == [0, 1, 2, 3, 4]
    assert set(NONCLAIMS) >= {
        "cycles",
        "achieved_bandwidth",
        "throughput",
        "gpu_comparison",
        "rom_advantage",
    }


def test_synthetic_package_is_closed_and_known_answer_is_exact(
    synthetic_deployment: Path,
) -> None:
    report = verify_deepseek_v4_compressor_executable_deployment(
        synthetic_deployment
    )
    assert report == {
        "ape_sha256": (
            "4fe7b59af6de3b665b67788cc2f99892ab827efae3a467342b3bb4e3bc8e5bfe"
        ),
        "build_id": (
            "0ab4faa1400a848425337eb210c97a2099c5ea79ae359ca6f7da1c144cf9cde7"
        ),
        "evidence_eligible": False,
        "known_answer_sha256": (
            "89920f941c0a2938fef9cfe15254bf2ce58341a8712a0a6ce5173b7cfdcdb80c"
        ),
        "program_sha256": PROGRAM_SHA256,
        "schedule_sha256": (
            "f61f02da92d690857df29a231bbc58b896dfeee6b1c8c1c4a56bee0cb7c7d843"
        ),
        "source_kind": "synthetic",
        "status": "verified_logical_schedule_and_full_width_known_answer",
    }
    manifest = json.loads((synthetic_deployment / "deployment_manifest.json").read_text())
    assert manifest["claim_boundary"] == CLAIM_BOUNDARY
    assert len(manifest["artifacts"]) == 11
    known = json.loads((synthetic_deployment / "evidence/known_answer.json").read_text())
    assert known["expected"] == {
        "completed_rows_per_batch": 1,
        "converted_bf16_code": "0x4020",
        "converted_bf16_sha256": (
            "da38a9ffc905c62b3f92ca9d3addabd2616e113c9a19434633651cc9820d09c7"
        ),
        "pooled_binary32_code": "0x40200000",
        "pooled_f32_sha256": (
            "82e6cd231578fb0cf94081d02aea9c4532abcf21233eb80887ac2f041d12c019"
        ),
        "valid_prefix_lengths": [1],
        "valid_view_bf16_sha256": (
            "da38a9ffc905c62b3f92ca9d3addabd2616e113c9a19434633651cc9820d09c7"
        ),
    }


@pytest.mark.skipif(not OFFICIAL_APE.is_file(), reason="official canonical cache absent")
def test_optional_official_cache_gate_uses_exact_canonical_ape(tmp_path: Path) -> None:
    deployment = tmp_path / "official-deployment"
    report = build_deepseek_v4_compressor_executable_deployment(
        OFFICIAL_APE,
        deployment,
    )
    assert OFFICIAL_APE.stat().st_size == APE_BYTES
    assert hashlib.sha256(OFFICIAL_APE.read_bytes()).hexdigest() == OFFICIAL_APE_SHA256
    assert report["ape_sha256"] == OFFICIAL_APE_SHA256
    assert report["evidence_eligible"] is True
    binding = json.loads((deployment / "evidence/source_binding.json").read_text())
    assert binding["application_id"] == OFFICIAL_APPLICATION_ID
    assert binding["verification_id"] == OFFICIAL_VERIFICATION_ID
    assert binding["evidence_eligible"] is True


@pytest.mark.parametrize(
    ("relative", "mutation"),
    [
        ("program/compressor.bin", "program"),
        ("schedule/logical_schedule.json", "schedule"),
        ("parameters/layers.2.attn.compressor.ape.f32le", "ape"),
    ],
)
def test_independent_checker_rejects_semantic_mutation_even_after_rehash(
    synthetic_deployment: Path,
    tmp_path: Path,
    relative: str,
    mutation: str,
) -> None:
    corrupted = tmp_path / mutation
    shutil.copytree(synthetic_deployment, corrupted)
    payload = (corrupted / relative).read_bytes()
    if mutation == "schedule":
        value = json.loads(payload)
        value["slots"][3]["condition"] = "always"
        payload = _canonical(value)
    elif mutation == "program":
        changed = bytearray(payload)
        changed[-1] ^= 1
        payload = bytes(changed)
    else:
        changed = bytearray(payload)
        changed[0] ^= 1
        payload = bytes(changed)
    _rewrite_manifest_record(corrupted, relative, payload)
    with pytest.raises(DeepSeekV4CompressorExecutableCheckError):
        verify_deepseek_v4_compressor_executable_deployment(corrupted)


def test_publication_is_create_once_and_preserves_existing_target(
    tmp_path: Path,
) -> None:
    ape = tmp_path / "ape.f32le"
    ape.write_bytes(struct.pack("<4096I", *([0] * 4096)))
    output = tmp_path / "deployment"
    output.mkdir()
    marker = output / "marker"
    marker.write_bytes(b"preserve")
    with pytest.raises(Exception, match="already exists"):
        build_deepseek_v4_compressor_executable_deployment(
            ape,
            output,
            source_kind="synthetic",
        )
    assert marker.read_bytes() == b"preserve"

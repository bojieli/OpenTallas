#!/usr/bin/env python3
"""Reproduce the governed post-projection compressor executable evidence.

The driver builds the official full-width APE deployment in a private temporary
tree, independently verifies it, executes the deterministic one-group known
answer through an immutable initial state, validates the published successor,
and emits a path- and time-independent canonical report.  It measures no wall
time and makes no cycle, bandwidth, throughput, energy, PPA, or GPU claim.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.checking.deepseek_v4_compressor_executable import (  # noqa: E402
    verify_deepseek_v4_compressor_executable_deployment,
)
from compiler.vertical_slice.deepseek_v4_compressor_executable import (  # noqa: E402
    CLAIM_BOUNDARY,
    KNOWN_SESSION_ID,
    OFFICIAL_APE_SHA256,
    OFFICIAL_APPLICATION_ID,
    OFFICIAL_TENSOR_NAME,
    OFFICIAL_TENSOR_PATH,
    OFFICIAL_VERIFICATION_ID,
    build_deepseek_v4_compressor_executable_deployment,
    known_answer_inputs_from_ape,
)
from runtime.service_engine.deepseek_v4_compressor_executable import (  # noqa: E402
    build_deepseek_v4_compressor_request,
    build_initial_deepseek_v4_compressor_state,
    execute_deepseek_v4_compressor_executable_deployment,
    load_deepseek_v4_compressor_executable_deployment,
    load_deepseek_v4_compressor_state,
)
from runtime.service_engine.secure_artifacts import (  # noqa: E402
    canonical_json_bytes,
)


REPORT_SCHEMA = "opentallas.deepseek_v4_compressor_executable_audit.v1"
EXPECTED_REPORT_SHA256 = (
    "69c585d6a048604cd0a69e2bc1c2e99927aa25023f2a9526e5c04f224a36cc51"
)


class CompressorExecutableAuditError(RuntimeError):
    """Raised when any governed executable-evidence identity differs."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_record(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {"sha256": _sha256(payload), "size_bytes": len(payload)}


def build_report(ape_path: Path) -> dict[str, object]:
    """Run the official one-group artifact execution and return its report."""

    ape_payload = Path(ape_path).read_bytes()
    if len(ape_payload) != 16_384 or _sha256(ape_payload) != OFFICIAL_APE_SHA256:
        raise CompressorExecutableAuditError(
            "APE source differs from the official canonical layer-2 payload"
        )
    with tempfile.TemporaryDirectory(prefix="opentallas-compressor-audit-") as raw:
        root = Path(raw)
        deployment_dir = root / "deployment"
        initial_state_dir = root / "state-0"
        request_dir = root / "request"
        result_dir = root / "result"

        build_report = build_deepseek_v4_compressor_executable_deployment(
            ape_path,
            deployment_dir,
            source_kind="official",
        )
        independent_report = verify_deepseek_v4_compressor_executable_deployment(
            deployment_dir
        )
        if build_report != independent_report:
            raise CompressorExecutableAuditError(
                "builder and independent deployment reports differ"
            )
        deployment = load_deepseek_v4_compressor_executable_deployment(deployment_dir)
        initial = build_initial_deepseek_v4_compressor_state(
            deployment_dir,
            initial_state_dir,
        )
        projected_kv, projected_scores = known_answer_inputs_from_ape(
            deployment.ape_codes
        )
        request_manifest = build_deepseek_v4_compressor_request(
            deployment_dir,
            initial_state_dir,
            request_dir,
            projected_kv_f32_codes=projected_kv,
            projected_score_f32_codes=projected_scores,
            session_ids=(KNOWN_SESSION_ID,),
            start_pos=0,
        )
        execution = execute_deepseek_v4_compressor_executable_deployment(
            deployment_dir,
            initial_state_dir,
            request_dir,
            result_dir,
        )
        successor = load_deepseek_v4_compressor_state(
            execution.state_dir,
            expected_build_id=deployment.build_id,
        )
        if (
            execution.prior_state_id != initial.state_id
            or execution.request_id != request_manifest["request_id"]
            or successor.state_id != execution.state_id
            or successor.prior_state_id != initial.state_id
            or successor.transition_id != execution.transition_id
            or successor.sequence_number != 1
        ):
            raise CompressorExecutableAuditError(
                "published successor hash chain differs from the executed transition"
            )

        output_files = {
            "converted_bf16": _file_record(
                result_dir / "outputs/converted.bf16le"
            ),
            "pooled_f32": _file_record(result_dir / "outputs/pooled.f32le"),
            "valid_view_bf16": _file_record(
                result_dir / "outputs/valid_view.bf16le"
            ),
        }
        return {
            "artifact_execution": {
                "complete_group_count": execution.complete_group_count,
                "counters": execution.counters,
                "initial_state_id": initial.state_id,
                "output_files": output_files,
                "request_id": execution.request_id,
                "result_id": execution.result_id,
                "should_compress": execution.should_compress,
                "successor_sequence_number": successor.sequence_number,
                "successor_state_id": execution.state_id,
                "transition_id": execution.transition_id,
            },
            "claim_boundary": list(CLAIM_BOUNDARY),
            "deployment": independent_report,
            "method": {
                "input": (
                    "one active lane, four full-width projected rows; score is "
                    "bitwise sign-negated packaged APE; current KV halves are "
                    "binary32 constants 1, 2, 3, and 4"
                ),
                "known_answer": (
                    "512 exact binary32 2.5 values, 512 exact BF16 2.5 values, "
                    "one committed and exposed valid-prefix row"
                ),
                "timing_measurement": None,
            },
            "model_id": "deepseek-v4-flash-0731",
            "schema": REPORT_SCHEMA,
            "source": {
                "application_id": OFFICIAL_APPLICATION_ID,
                "canonical_relative_path": OFFICIAL_TENSOR_PATH,
                "payload_sha256": OFFICIAL_APE_SHA256,
                "tensor_name": OFFICIAL_TENSOR_NAME,
                "verification_id": OFFICIAL_VERIFICATION_ID,
            },
            "status": "exact_official_ape_post_projection_transactional_slice",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ape", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--allow-unfrozen-report",
        action="store_true",
        help="allow the first run before EXPECTED_REPORT_SHA256 is frozen",
    )
    arguments = parser.parse_args()
    report = build_report(arguments.ape)
    payload = canonical_json_bytes(report)
    digest = _sha256(payload)
    if EXPECTED_REPORT_SHA256.startswith("TO_BE_"):
        if not arguments.allow_unfrozen_report:
            raise CompressorExecutableAuditError(
                "report identity is not frozen; rerun with --allow-unfrozen-report, "
                "review it, then pin EXPECTED_REPORT_SHA256"
            )
    elif digest != EXPECTED_REPORT_SHA256:
        raise CompressorExecutableAuditError(
            f"report SHA-256 {digest} differs from {EXPECTED_REPORT_SHA256}"
        )
    output = Path(arguments.output)
    if output.exists():
        raise CompressorExecutableAuditError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
